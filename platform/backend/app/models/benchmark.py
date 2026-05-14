"""性能基准测试数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Benchmark(Base):
    """性能基准测试记录。"""

    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    # 目标
    target_url = Column(String(500), nullable=False)
    method = Column(String(10), default="GET")
    headers = Column(Text, default="{}")
    body = Column(Text, default="")
    # 压测参数
    concurrency = Column(Integer, default=10)  # 并发数
    total_requests = Column(Integer, default=100)  # 总请求数
    duration_seconds = Column(Integer, default=0)  # 持续时间（0=按总数）
    # 状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    # 结果统计
    total_sent = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    p50_latency_ms = Column(Float, default=0.0)
    p90_latency_ms = Column(Float, default=0.0)
    p95_latency_ms = Column(Float, default=0.0)
    p99_latency_ms = Column(Float, default=0.0)
    min_latency_ms = Column(Float, default=0.0)
    max_latency_ms = Column(Float, default=0.0)
    rps = Column(Float, default=0.0)  # 每秒请求数
    elapsed_ms = Column(Float, default=0.0)
    # 错误分布
    error_distribution = Column(Text, default="{}")  # {"timeout": 5, "500": 3}
    # 时间
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
