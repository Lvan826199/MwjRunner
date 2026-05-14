"""Worker 管理和分布式执行 API。"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import TestCase
from app.models.execution import Execution
from app.models.worker import TaskShard, Worker
from app.schemas.worker import (
    DistributedExecutionCreate,
    TaskShardResponse,
    TaskShardResult,
    WorkerHeartbeat,
    WorkerRegister,
    WorkerResponse,
)

router = APIRouter(prefix="/api/workers", tags=["Worker 管理"])

# Worker 超时阈值（秒）
HEARTBEAT_TIMEOUT = 60


@router.get("", response_model=list[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    """获取 Worker 列表。"""
    result = await db.execute(select(Worker).order_by(Worker.registered_at.desc()))
    workers = result.scalars().all()
    # 自动标记超时 Worker
    now = datetime.utcnow()
    for w in workers:
        if w.status != "offline" and w.last_heartbeat:
            if (now - w.last_heartbeat).total_seconds() > HEARTBEAT_TIMEOUT:
                w.status = "offline"
    await db.commit()
    return workers


@router.post("/register", response_model=WorkerResponse, status_code=201)
async def register_worker(data: WorkerRegister, db: AsyncSession = Depends(get_db)):
    """Worker 注册（幂等）。"""
    result = await db.execute(select(Worker).where(Worker.worker_id == data.worker_id))
    existing = result.scalar_one_or_none()
    if existing:
        existing.name = data.name or existing.name
        existing.host = data.host or existing.host
        existing.port = data.port or existing.port
        existing.max_concurrency = data.max_concurrency
        existing.tags = data.tags
        existing.status = "online"
        existing.last_heartbeat = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    worker = Worker(
        worker_id=data.worker_id,
        name=data.name,
        host=data.host,
        port=data.port,
        max_concurrency=data.max_concurrency,
        tags=data.tags,
        status="online",
        last_heartbeat=datetime.utcnow(),
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


@router.post("/heartbeat")
async def worker_heartbeat(data: WorkerHeartbeat, db: AsyncSession = Depends(get_db)):
    """Worker 心跳上报。"""
    result = await db.execute(select(Worker).where(Worker.worker_id == data.worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker 未注册")
    worker.status = data.status
    worker.current_tasks = data.current_tasks
    worker.last_heartbeat = datetime.utcnow()
    await db.commit()
    return {"status": "ok"}


@router.delete("/{worker_id}")
async def remove_worker(worker_id: str, db: AsyncSession = Depends(get_db)):
    """移除 Worker。"""
    result = await db.execute(select(Worker).where(Worker.worker_id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker 不存在")
    await db.delete(worker)
    await db.commit()
    return {"status": "removed"}


# --- 分布式执行 ---

@router.post("/dispatch", status_code=201)
async def dispatch_execution(
    data: DistributedExecutionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """分布式执行：将用例分片分发到可用 Worker。"""
    # 获取在线 Worker
    result = await db.execute(select(Worker).where(Worker.status == "online"))
    online_workers = result.scalars().all()
    if not online_workers:
        raise HTTPException(status_code=400, detail="没有可用的在线 Worker")

    # 获取用例列表
    if data.case_ids:
        cases_result = await db.execute(select(TestCase).where(TestCase.id.in_(data.case_ids)))
        cases = cases_result.scalars().all()
    else:
        cases_result = await db.execute(select(TestCase))
        cases = cases_result.scalars().all()

    if not cases:
        raise HTTPException(status_code=400, detail="没有可执行的用例")

    # 确定分片数
    shard_count = data.shard_count if data.shard_count > 0 else len(online_workers)
    shard_count = min(shard_count, len(cases))  # 不超过用例数

    # 创建执行记录
    from uuid import uuid4
    run_id = f"dist-{uuid4().hex[:8]}"
    execution = Execution(
        run_id=run_id,
        case_name=f"分布式执行 ({len(cases)} 用例 / {shard_count} 分片)",
        status="running",
        base_url=data.base_url,
        env_name=data.env_name,
        tags=data.tags,
        workers=shard_count,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 分片：均匀分配用例到各分片
    case_ids_list = [c.id for c in cases]
    shards_data = _split_into_shards(case_ids_list, shard_count)

    # 创建分片记录并分配 Worker
    shards = []
    for i, shard_case_ids in enumerate(shards_data):
        worker = online_workers[i % len(online_workers)]
        shard = TaskShard(
            execution_id=execution.id,
            worker_id=worker.worker_id,
            shard_index=i,
            total_shards=shard_count,
            case_paths=json.dumps(shard_case_ids),
            tags_filter=data.tags,
            status="pending",
        )
        db.add(shard)
        shards.append(shard)
    await db.commit()

    return {
        "execution_id": execution.id,
        "run_id": run_id,
        "shard_count": shard_count,
        "workers_used": len(set(s.worker_id for s in shards)),
        "total_cases": len(cases),
    }


@router.get("/shards/{execution_id}", response_model=list[TaskShardResponse])
async def get_shards(execution_id: int, db: AsyncSession = Depends(get_db)):
    """获取执行的分片列表。"""
    result = await db.execute(
        select(TaskShard).where(TaskShard.execution_id == execution_id).order_by(TaskShard.shard_index)
    )
    return result.scalars().all()


@router.post("/shards/report")
async def report_shard_result(data: TaskShardResult, db: AsyncSession = Depends(get_db)):
    """Worker 上报分片执行结果。"""
    shard = await db.get(TaskShard, data.shard_id)
    if not shard:
        raise HTTPException(status_code=404, detail="分片不存在")
    shard.status = data.status
    shard.exit_code = data.exit_code
    shard.total_cases = data.total_cases
    shard.passed_cases = data.passed_cases
    shard.failed_cases = data.failed_cases
    shard.error_cases = data.error_cases
    shard.elapsed_ms = data.elapsed_ms
    shard.stdout = data.stdout[-5000:]
    shard.stderr = data.stderr[-2000:]
    shard.finished_at = datetime.utcnow()
    await db.commit()

    # 检查是否所有分片完成，汇总结果
    await _try_finalize_execution(shard.execution_id, db)
    return {"status": "ok"}


async def _try_finalize_execution(execution_id: int, db: AsyncSession) -> None:
    """检查所有分片是否完成，汇总到执行记录。"""
    result = await db.execute(select(TaskShard).where(TaskShard.execution_id == execution_id))
    shards = result.scalars().all()

    if any(s.status in ("pending", "running") for s in shards):
        return  # 还有未完成的分片

    execution = await db.get(Execution, execution_id)
    if not execution:
        return

    # 汇总统计
    execution.total_cases = sum(s.total_cases for s in shards)
    execution.passed_cases = sum(s.passed_cases for s in shards)
    execution.failed_cases = sum(s.failed_cases for s in shards)
    execution.error_cases = sum(s.error_cases for s in shards)
    execution.elapsed_ms = max((s.elapsed_ms for s in shards), default=0)

    # 确定最终状态
    if any(s.status == "failed" or (s.exit_code and s.exit_code > 0) for s in shards):
        execution.status = "failed"
        execution.exit_code = 1
    elif any(s.status == "error" for s in shards):
        execution.status = "error"
        execution.exit_code = 2
    else:
        execution.status = "passed"
        execution.exit_code = 0

    execution.finished_at = datetime.utcnow()
    await db.commit()


def _split_into_shards(items: list[int], count: int) -> list[list[int]]:
    """将列表均匀分成 count 份。"""
    shards: list[list[int]] = [[] for _ in range(count)]
    for i, item in enumerate(items):
        shards[i % count].append(item)
    return [s for s in shards if s]
