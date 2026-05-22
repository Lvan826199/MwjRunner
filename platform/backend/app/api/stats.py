"""统计数据 API — 仪表盘数据源。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import team_filter
from app.models.case import TestCase
from app.models.environment import Environment
from app.models.execution import Execution
from app.models.pipeline import Pipeline
from app.models.user import User

router = APIRouter(prefix="/api/stats", tags=["统计数据"])


@router.get("/overview")
async def get_overview(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """总览统计。"""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 用例统计
    case_query = select(TestCase)
    case_query = team_filter(case_query, TestCase, user)

    total_cases = await db.scalar(team_filter(select(func.count(TestCase.id)), TestCase, user))

    by_priority = {}
    priority_result = await db.execute(
        team_filter(
            select(TestCase.priority, func.count(TestCase.id)).group_by(TestCase.priority),
            TestCase,
            user,
        )
    )
    for row in priority_result.all():
        by_priority[row[0]] = row[1]

    by_status = {}
    status_result = await db.execute(
        team_filter(
            select(TestCase.status, func.count(TestCase.id)).group_by(TestCase.status),
            TestCase,
            user,
        )
    )
    for row in status_result.all():
        by_status[row[0]] = row[1]

    # 执行统计
    team_filter(select(Execution), Execution, user)

    today_count = await db.scalar(
        team_filter(
            select(func.count(Execution.id)).where(Execution.started_at >= today_start),
            Execution,
            user,
        )
    )

    range_query = team_filter(
        select(
            func.count(Execution.id),
            func.sum(sql_case((Execution.status == "passed", 1), else_=0)),
            func.avg(Execution.elapsed_ms),
        ).where(Execution.started_at >= since),
        Execution,
        user,
    )
    range_result = await db.execute(range_query)
    row = range_result.one()
    total_in_range = row[0] or 0
    passed_in_range = row[1] or 0
    avg_elapsed = row[2] or 0
    pass_rate = (passed_in_range / total_in_range) if total_in_range > 0 else 0

    # 环境数
    env_count = await db.scalar(team_filter(select(func.count(Environment.id)), Environment, user))

    # Pipeline 数
    pipeline_total = await db.scalar(team_filter(select(func.count(Pipeline.id)), Pipeline, user))
    pipeline_active = await db.scalar(
        team_filter(
            select(func.count(Pipeline.id)).where(Pipeline.is_active == 1),
            Pipeline,
            user,
        )
    )

    return {
        "cases": {
            "total": total_cases or 0,
            "by_priority": by_priority,
            "by_status": by_status,
        },
        "executions": {
            "today": today_count or 0,
            "total_in_range": total_in_range,
            "pass_rate": round(pass_rate, 3),
            "avg_elapsed_ms": round(avg_elapsed, 1),
        },
        "environments": {"total": env_count or 0},
        "pipelines": {"total": pipeline_total or 0, "active": pipeline_active or 0},
    }


@router.get("/trend")
async def get_trend(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """执行趋势数据（按天聚合）。"""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    query = team_filter(
        select(
            func.date(Execution.started_at).label("date"),
            func.count(Execution.id).label("total"),
            func.sum(sql_case((Execution.status == "passed", 1), else_=0)).label("passed"),
            func.sum(sql_case((Execution.status == "failed", 1), else_=0)).label("failed"),
            func.avg(Execution.elapsed_ms).label("avg_elapsed_ms"),
        )
        .where(Execution.started_at >= since)
        .group_by(func.date(Execution.started_at))
        .order_by(func.date(Execution.started_at)),
        Execution,
        user,
    )
    result = await db.execute(query)

    trend = []
    for row in result.all():
        total = row[1] or 0
        passed = row[2] or 0
        trend.append(
            {
                "date": str(row[0]),
                "total": total,
                "passed": passed,
                "failed": row[3] or 0,
                "pass_rate": round(passed / total, 3) if total > 0 else 0,
                "avg_elapsed_ms": round(row[4] or 0, 1),
            }
        )
    return {"trend": trend}


@router.get("/tags")
async def get_tags(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标签分布统计。"""
    query = team_filter(select(TestCase.tags), TestCase, user)
    result = await db.execute(query)

    tag_counts: dict[str, int] = {}
    for row in result.all():
        tags_str = row[0] or ""
        for tag in tags_str.split(","):
            stripped = tag.strip()
            if stripped:
                tag_counts[stripped] = tag_counts.get(stripped, 0) + 1

    return {"tags": [{"name": k, "count": v} for k, v in sorted(tag_counts.items(), key=lambda x: -x[1])]}
