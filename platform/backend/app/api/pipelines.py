"""CI/CD Pipeline API。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.pipeline import Pipeline, PipelineRun
from app.models.user import User
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineRunResponse,
    PipelineTrigger,
    PipelineUpdate,
)

router = APIRouter(prefix="/api/pipelines", tags=["CI/CD Pipeline"])


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取 Pipeline 列表（团队隔离）。"""
    query = select(Pipeline).order_by(Pipeline.id.desc())
    query = team_filter(query, Pipeline, user)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取 Pipeline 详情。"""
    return await check_resource_access(db, Pipeline, pipeline_id, user)


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    data: PipelineCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """创建 Pipeline。"""
    p = Pipeline(**data.model_dump(), team_id=user.team_id)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: int, data: PipelineUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """更新 Pipeline。"""
    p = await check_resource_access(db, Pipeline, pipeline_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """删除 Pipeline。"""
    p = await check_resource_access(db, Pipeline, pipeline_id, user)
    await db.delete(p)
    await db.commit()


@router.post("/{pipeline_id}/trigger", response_model=PipelineRunResponse, status_code=201)
async def trigger_pipeline(
    pipeline_id: int, data: PipelineTrigger, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """触发 Pipeline 执行。"""
    p = await check_resource_access(db, Pipeline, pipeline_id, user)
    if not p.is_active:
        raise HTTPException(status_code=400, detail="Pipeline 已停用")

    run = PipelineRun(
        pipeline_id=pipeline_id,
        trigger_source=data.trigger_source,
        commit_sha=data.commit_sha,
        branch=data.branch,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    p.last_run_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{pipeline_id}/runs", response_model=list[PipelineRunResponse])
async def list_runs(pipeline_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取 Pipeline 执行记录。"""
    await check_resource_access(db, Pipeline, pipeline_id, user)
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.pipeline_id == pipeline_id).order_by(PipelineRun.id.desc())
    )
    return result.scalars().all()


@router.get("/{pipeline_id}/badge")
async def get_badge(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """获取通过率徽章（SVG）— 公开接口，无需认证。"""
    p = await db.get(Pipeline, pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline 不存在")

    color = "#999"
    label = "unknown"
    if p.last_status == "passing":
        color = "#4c1"
        label = "passing"
    elif p.last_status == "failing":
        color = "#e05d44"
        label = "failing"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="90" height="20">
  <rect width="90" height="20" rx="3" fill="#555"/>
  <rect x="45" width="45" height="20" rx="3" fill="{color}"/>
  <rect width="90" height="20" rx="3" fill="url(#g)"/>
  <text x="22" y="14" fill="#fff" font-size="11" text-anchor="middle">tests</text>
  <text x="67" y="14" fill="#fff" font-size="11" text-anchor="middle">{label}</text>
</svg>'''
    return Response(content=svg, media_type="image/svg+xml")
