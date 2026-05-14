"""持续性能测试 API — 定时压测 + 基线对比。"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.benchmark import Benchmark
from app.models.user import User

router = APIRouter(prefix="/api/perf", tags=["持续性能测试"])


class BaselineCreate(BaseModel):
    benchmark_id: int
    name: str = ""


class BaselineResponse(BaseModel):
    id: int
    name: str
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    rps: float
    created_at: str


class PerfCompareResponse(BaseModel):
    baseline: dict
    current: dict
    regression: bool
    details: list[dict]


@router.post("/baselines", status_code=201)
async def create_baseline(
    data: BaselineCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """将某次压测结果设为性能基线。"""
    bench = await check_resource_access(db, Benchmark, data.benchmark_id, user)
    if bench.status != "completed":
        raise HTTPException(status_code=400, detail="只能将已完成的压测设为基线")

    # 存储基线信息到 benchmark 的 error_distribution 字段（复用，或新增字段）
    # 这里简化：在 benchmark 上标记为 baseline
    baseline_meta = {
        "is_baseline": True,
        "baseline_name": data.name or f"Baseline-{bench.id}",
        "set_at": datetime.utcnow().isoformat(),
    }

    # 将 baseline 信息追加到 error_distribution（JSON 扩展）
    existing = {}
    try:
        existing = json.loads(bench.error_distribution or "{}")
    except json.JSONDecodeError:
        pass
    existing["_baseline"] = baseline_meta
    bench.error_distribution = json.dumps(existing)
    await db.commit()

    return {
        "id": bench.id,
        "name": baseline_meta["baseline_name"],
        "avg_latency_ms": bench.avg_latency_ms,
        "p95_latency_ms": bench.p95_latency_ms,
        "p99_latency_ms": bench.p99_latency_ms,
        "rps": bench.rps,
        "created_at": baseline_meta["set_at"],
    }


@router.get("/baselines")
async def list_baselines(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取所有性能基线。"""
    query = team_filter(
        select(Benchmark).where(Benchmark.status == "completed"),
        Benchmark, user,
    )
    result = await db.execute(query)
    benchmarks = result.scalars().all()

    baselines = []
    for b in benchmarks:
        try:
            meta = json.loads(b.error_distribution or "{}")
        except json.JSONDecodeError:
            continue
        if meta.get("_baseline", {}).get("is_baseline"):
            baselines.append({
                "id": b.id,
                "name": meta["_baseline"].get("baseline_name", ""),
                "target_url": b.target_url,
                "avg_latency_ms": b.avg_latency_ms,
                "p95_latency_ms": b.p95_latency_ms,
                "p99_latency_ms": b.p99_latency_ms,
                "rps": b.rps,
                "created_at": meta["_baseline"].get("set_at", ""),
            })
    return baselines


@router.get("/compare/{baseline_id}/{current_id}")
async def compare_performance(
    baseline_id: int,
    current_id: int,
    threshold: float = 0.2,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """对比当前压测与基线，检测性能回归。

    threshold: 回归阈值（默认 20%），超过则标记为回归。
    """
    baseline = await check_resource_access(db, Benchmark, baseline_id, user)
    current = await check_resource_access(db, Benchmark, current_id, user)

    if baseline.status != "completed" or current.status != "completed":
        raise HTTPException(status_code=400, detail="两次压测都必须已完成")

    details = []
    regression = False

    metrics = [
        ("avg_latency_ms", "平均延迟", True),   # True = 越大越差
        ("p95_latency_ms", "P95 延迟", True),
        ("p99_latency_ms", "P99 延迟", True),
        ("rps", "RPS", False),                    # False = 越小越差
    ]

    for attr, label, higher_is_worse in metrics:
        base_val = getattr(baseline, attr) or 0
        curr_val = getattr(current, attr) or 0

        if base_val == 0:
            change_pct = 0
        else:
            change_pct = (curr_val - base_val) / base_val

        is_regression = False
        if higher_is_worse and change_pct > threshold:
            is_regression = True
            regression = True
        elif not higher_is_worse and change_pct < -threshold:
            is_regression = True
            regression = True

        details.append({
            "metric": label,
            "baseline": round(base_val, 2),
            "current": round(curr_val, 2),
            "change_pct": round(change_pct * 100, 1),
            "regression": is_regression,
        })

    return {
        "baseline": {"id": baseline.id, "name": baseline.name},
        "current": {"id": current.id, "name": current.name},
        "regression": regression,
        "threshold_pct": threshold * 100,
        "details": details,
    }


@router.get("/history")
async def perf_history(
    target_url: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某目标 URL 的性能历史趋势。"""
    query = team_filter(
        select(Benchmark)
        .where(Benchmark.status == "completed")
        .order_by(Benchmark.id.desc())
        .limit(limit),
        Benchmark, user,
    )
    if target_url:
        query = query.where(Benchmark.target_url == target_url)

    result = await db.execute(query)
    benchmarks = result.scalars().all()

    return [
        {
            "id": b.id,
            "name": b.name,
            "target_url": b.target_url,
            "concurrency": b.concurrency,
            "total_requests": b.total_requests,
            "avg_latency_ms": b.avg_latency_ms,
            "p95_latency_ms": b.p95_latency_ms,
            "p99_latency_ms": b.p99_latency_ms,
            "rps": b.rps,
            "success_rate": round(b.success_count / b.total_sent, 3) if b.total_sent else 0,
            "created_at": str(b.created_at),
        }
        for b in benchmarks
    ]
