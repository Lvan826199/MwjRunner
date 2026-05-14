"""Webhook 自动触发 API。"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.pipeline import Pipeline, PipelineRun

router = APIRouter(prefix="/api/webhooks", tags=["Webhook 触发"])


@router.post("/github/{pipeline_id}")
async def github_webhook(
    pipeline_id: int,
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """GitHub Webhook 接收端点。"""
    pipeline = await db.get(Pipeline, pipeline_id)
    if not pipeline or not pipeline.is_active:
        raise HTTPException(status_code=404, detail="Pipeline 不存在或已停用")

    body = await request.body()

    # 验证签名
    if pipeline.webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="缺少签名")
        expected = "sha256=" + hmac.new(
            pipeline.webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="签名验证失败")

    payload = json.loads(body)

    # 只处理 push 和 pull_request 事件
    if x_github_event not in ("push", "pull_request", "workflow_dispatch"):
        return {"status": "ignored", "event": x_github_event}

    commit_sha = ""
    branch = ""
    if x_github_event == "push":
        commit_sha = payload.get("after", "")[:12]
        branch = payload.get("ref", "").replace("refs/heads/", "")
    elif x_github_event == "pull_request":
        pr = payload.get("pull_request", {})
        commit_sha = pr.get("head", {}).get("sha", "")[:12]
        branch = pr.get("head", {}).get("ref", "")

    run = PipelineRun(
        pipeline_id=pipeline_id,
        trigger_source=f"github:{x_github_event}",
        commit_sha=commit_sha,
        branch=branch,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    pipeline.last_run_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)

    return {"status": "triggered", "run_id": run.id, "commit": commit_sha, "branch": branch}


@router.post("/gitlab/{pipeline_id}")
async def gitlab_webhook(
    pipeline_id: int,
    request: Request,
    x_gitlab_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """GitLab Webhook 接收端点。"""
    pipeline = await db.get(Pipeline, pipeline_id)
    if not pipeline or not pipeline.is_active:
        raise HTTPException(status_code=404, detail="Pipeline 不存在或已停用")

    # 验证 Token
    if pipeline.webhook_secret:
        if x_gitlab_token != pipeline.webhook_secret:
            raise HTTPException(status_code=401, detail="Token 验证失败")

    payload = await request.json()
    event_type = payload.get("object_kind", "push")

    commit_sha = ""
    branch = ""
    if event_type == "push":
        commit_sha = payload.get("after", "")[:12]
        branch = payload.get("ref", "").replace("refs/heads/", "")
    elif event_type == "merge_request":
        mr = payload.get("object_attributes", {})
        commit_sha = mr.get("last_commit", {}).get("id", "")[:12]
        branch = mr.get("source_branch", "")

    run = PipelineRun(
        pipeline_id=pipeline_id,
        trigger_source=f"gitlab:{event_type}",
        commit_sha=commit_sha,
        branch=branch,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    pipeline.last_run_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)

    return {"status": "triggered", "run_id": run.id, "commit": commit_sha, "branch": branch}


@router.post("/generic/{pipeline_id}")
async def generic_webhook(
    pipeline_id: int,
    request: Request,
    x_webhook_secret: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """通用 Webhook 接收端点（Jenkins / 自定义 CI）。"""
    pipeline = await db.get(Pipeline, pipeline_id)
    if not pipeline or not pipeline.is_active:
        raise HTTPException(status_code=404, detail="Pipeline 不存在或已停用")

    if pipeline.webhook_secret:
        if x_webhook_secret != pipeline.webhook_secret:
            raise HTTPException(status_code=401, detail="Secret 验证失败")

    payload = await request.json()

    run = PipelineRun(
        pipeline_id=pipeline_id,
        trigger_source=payload.get("source", "generic"),
        commit_sha=payload.get("commit_sha", "")[:12],
        branch=payload.get("branch", ""),
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    pipeline.last_run_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)

    return {"status": "triggered", "run_id": run.id}
