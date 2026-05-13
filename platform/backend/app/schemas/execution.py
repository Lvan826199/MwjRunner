"""执行记录 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExecutionCreate(BaseModel):
    case_id: int | None = None
    case_path: str = ""
    base_url: str = ""
    env_name: str = ""
    tags: str = ""
    workers: int = 1
    variables: dict[str, str] = {}


class ExecutionResponse(BaseModel):
    id: int
    run_id: str
    case_id: int | None
    case_name: str
    status: str
    exit_code: int | None
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    total_steps: int
    total_assertions: int
    failed_assertions: int
    elapsed_ms: float
    base_url: str
    env_name: str
    tags: str
    workers: int
    report_dir: str
    stdout: str
    stderr: str
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    id: int
    run_id: str
    case_name: str
    status: str
    exit_code: int | None
    total_cases: int
    passed_cases: int
    failed_cases: int
    elapsed_ms: float
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
