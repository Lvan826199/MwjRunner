"""执行记录数据模型。"""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Execution(Base):
    """执行记录表。"""

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), nullable=False, unique=True)
    case_id = Column(Integer, nullable=True)
    case_name = Column(String(255), default="")
    status = Column(String(20), default="running")  # running, passed, failed, error, timeout
    exit_code = Column(Integer, nullable=True)
    # 统计
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    error_cases = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    total_assertions = Column(Integer, default=0)
    failed_assertions = Column(Integer, default=0)
    elapsed_ms = Column(Float, default=0.0)
    # 参数
    base_url = Column(String(500), default="")
    env_name = Column(String(50), default="")
    tags = Column(String(200), default="")
    workers = Column(Integer, default=1)
    # 报告路径
    report_dir = Column(String(500), default="")
    # 日志
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    # 权限
    team_id = Column(Integer, nullable=True)
    # 时间
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
