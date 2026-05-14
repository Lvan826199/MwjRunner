"""性能基准测试 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BenchmarkCreate(BaseModel):
    name: str
    target_url: str
    method: str = "GET"
    headers: str = "{}"
    body: str = ""
    concurrency: int = 10
    total_requests: int = 100
    duration_seconds: int = 0


class BenchmarkResponse(BaseModel):
    id: int
    name: str
    target_url: str
    method: str
    headers: str
    body: str
    concurrency: int
    total_requests: int
    duration_seconds: int
    status: str
    total_sent: int
    success_count: int
    fail_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    rps: float
    elapsed_ms: float
    error_distribution: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}
