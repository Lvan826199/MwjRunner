"""Worker 和任务分片 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkerRegister(BaseModel):
    worker_id: str
    name: str = ""
    host: str = ""
    port: int = 0
    max_concurrency: int = 4
    tags: str = ""


class WorkerHeartbeat(BaseModel):
    worker_id: str
    status: str = "online"
    current_tasks: int = 0


class WorkerResponse(BaseModel):
    id: int
    worker_id: str
    name: str
    host: str
    port: int
    status: str
    max_concurrency: int
    current_tasks: int
    tags: str
    last_heartbeat: datetime | None
    registered_at: datetime | None

    model_config = {"from_attributes": True}


class TaskShardResponse(BaseModel):
    id: int
    execution_id: int
    worker_id: str
    shard_index: int
    total_shards: int
    case_paths: str
    tags_filter: str
    status: str
    exit_code: int | None
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    elapsed_ms: float
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class TaskShardResult(BaseModel):
    """Worker 上报分片执行结果。"""
    shard_id: int
    status: str
    exit_code: int = 0
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    elapsed_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""


class DistributedExecutionCreate(BaseModel):
    """分布式执行请求。"""
    case_ids: list[int] = []
    base_url: str = ""
    env_name: str = ""
    tags: str = ""
    shard_count: int = 0  # 0 = 自动按 Worker 数分片
    variables: dict[str, str] = {}
