"""Pipeline Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PipelineCreate(BaseModel):
    name: str
    platform: str = "github"
    trigger_type: str = "webhook"
    cron_expr: str = ""
    webhook_secret: str = ""
    case_filter_tags: str = ""
    env_name: str = ""
    base_url: str = ""
    notify_on_fail: int = 1
    notify_webhook: str = ""
    badge_enabled: int = 1
    description: str = ""


class PipelineUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    trigger_type: str | None = None
    cron_expr: str | None = None
    webhook_secret: str | None = None
    case_filter_tags: str | None = None
    env_name: str | None = None
    base_url: str | None = None
    notify_on_fail: int | None = None
    notify_webhook: str | None = None
    badge_enabled: int | None = None
    is_active: int | None = None
    description: str | None = None


class PipelineResponse(BaseModel):
    id: int
    name: str
    platform: str
    trigger_type: str
    cron_expr: str
    webhook_secret: str
    case_filter_tags: str
    env_name: str
    base_url: str
    notify_on_fail: int
    notify_webhook: str
    badge_enabled: int
    last_status: str
    last_run_at: datetime | None
    is_active: int
    description: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    id: int
    pipeline_id: int
    trigger_source: str
    commit_sha: str
    branch: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    elapsed_ms: int
    execution_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class PipelineTrigger(BaseModel):
    """手动/Webhook 触发。"""
    commit_sha: str = ""
    branch: str = ""
    trigger_source: str = "manual"
