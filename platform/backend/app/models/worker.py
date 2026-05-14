"""Worker 节点数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Worker(Base):
    """Worker 节点注册表。"""

    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), default="")
    host = Column(String(200), default="")
    port = Column(Integer, default=0)
    status = Column(String(20), default="online")  # online, offline, busy
    max_concurrency = Column(Integer, default=4)
    current_tasks = Column(Integer, default=0)
    tags = Column(String(200), default="")  # 支持按标签分配任务
    last_heartbeat = Column(DateTime, server_default=func.now())
    registered_at = Column(DateTime, server_default=func.now())


class TaskShard(Base):
    """任务分片表：一次执行拆分为多个分片分发到不同 Worker。"""

    __tablename__ = "task_shards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(Integer, nullable=False)
    worker_id = Column(String(50), default="")
    shard_index = Column(Integer, default=0)
    total_shards = Column(Integer, default=1)
    # 分片内容
    case_paths = Column(Text, default="")  # JSON 列表
    tags_filter = Column(String(200), default="")
    # 状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    exit_code = Column(Integer, nullable=True)
    # 统计
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    error_cases = Column(Integer, default=0)
    elapsed_ms = Column(Float, default=0.0)
    # 日志
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    # 时间
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
