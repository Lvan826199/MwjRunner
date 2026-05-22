"""性能基准测试 API。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.benchmark import Benchmark
from app.models.user import User
from app.schemas.benchmark import BenchmarkCreate, BenchmarkResponse

router = APIRouter(prefix="/api/benchmarks", tags=["性能基准"])


@router.get("", response_model=list[BenchmarkResponse])
async def list_benchmarks(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取压测记录列表（团队隔离）。"""
    query = select(Benchmark).order_by(Benchmark.id.desc())
    query = team_filter(query, Benchmark, user)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{bench_id}", response_model=BenchmarkResponse)
async def get_benchmark(bench_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取压测详情。"""
    return await check_resource_access(db, Benchmark, bench_id, user)


@router.post("", response_model=BenchmarkResponse, status_code=201)
async def create_benchmark(
    data: BenchmarkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建并启动压测。"""
    bench = Benchmark(**data.model_dump(), team_id=user.team_id)
    db.add(bench)
    await db.commit()
    await db.refresh(bench)
    background_tasks.add_task(run_benchmark, bench.id)
    return bench


@router.delete("/{bench_id}", status_code=204)
async def delete_benchmark(bench_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """删除压测记录。"""
    bench = await check_resource_access(db, Benchmark, bench_id, user)
    await db.delete(bench)
    await db.commit()


async def run_benchmark(bench_id: int):  # noqa: PLR0915
    """后台执行压测任务。"""
    from app.core.database import async_session_factory  # noqa: PLC0415

    async with async_session_factory() as db:
        bench = await db.get(Benchmark, bench_id)
        if not bench:
            return

        bench.status = "running"
        bench.started_at = datetime.utcnow()
        await db.commit()

        headers = {}
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            headers = json.loads(bench.headers)

        latencies: list[float] = []
        errors: dict[str, int] = {}
        success = 0
        fail = 0

        start_time = time.perf_counter()

        async def send_request(client: httpx.AsyncClient):
            nonlocal success, fail
            req_start = time.perf_counter()
            try:
                resp = await client.request(
                    method=bench.method,
                    url=bench.target_url,
                    headers=headers,
                    content=bench.body if bench.body else None,
                    timeout=30.0,
                )
                latency = (time.perf_counter() - req_start) * 1000
                latencies.append(latency)
                if resp.status_code < 400:
                    success += 1
                else:
                    fail += 1
                    key = str(resp.status_code)
                    errors[key] = errors.get(key, 0) + 1
            except httpx.TimeoutException:
                latencies.append((time.perf_counter() - req_start) * 1000)
                fail += 1
                errors["timeout"] = errors.get("timeout", 0) + 1
            except Exception as e:
                latencies.append((time.perf_counter() - req_start) * 1000)
                fail += 1
                key = type(e).__name__
                errors[key] = errors.get(key, 0) + 1

        try:
            async with httpx.AsyncClient() as client:
                sem = asyncio.Semaphore(bench.concurrency)

                async def limited_request():
                    async with sem:
                        await send_request(client)

                tasks = [asyncio.create_task(limited_request()) for _ in range(bench.total_requests)]
                await asyncio.gather(*tasks)
        except Exception:
            bench.status = "failed"
            bench.finished_at = datetime.utcnow()
            await db.commit()
            return

        elapsed = (time.perf_counter() - start_time) * 1000

        # 计算统计
        latencies.sort()
        n = len(latencies)
        bench.total_sent = n
        bench.success_count = success
        bench.fail_count = fail
        bench.elapsed_ms = elapsed
        bench.rps = (n / (elapsed / 1000)) if elapsed > 0 else 0

        if n > 0:
            bench.avg_latency_ms = sum(latencies) / n
            bench.min_latency_ms = latencies[0]
            bench.max_latency_ms = latencies[-1]
            bench.p50_latency_ms = latencies[int(n * 0.5)]
            bench.p90_latency_ms = latencies[int(n * 0.9)]
            bench.p95_latency_ms = latencies[int(n * 0.95)]
            bench.p99_latency_ms = latencies[min(int(n * 0.99), n - 1)]

        bench.error_distribution = json.dumps(errors)
        bench.status = "completed"
        bench.finished_at = datetime.utcnow()
        await db.commit()
