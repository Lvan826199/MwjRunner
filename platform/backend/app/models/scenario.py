"""场景编排数据模型。"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Scenario(Base):
    """场景编排表。"""

    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    # 步骤定义（JSON 数组）
    steps = Column(Text, default="[]")
    # 全局变量（JSON）
    variables = Column(Text, default="{}")
    # 管理
    tags = Column(String(200), default="")
    is_active = Column(Integer, default=1)
    team_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScenarioRun(Base):
    """场景执行记录。"""

    __tablename__ = "scenario_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")  # pending, running, passed, failed
    total_steps = Column(Integer, default=0)
    passed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    elapsed_ms = Column(Integer, default=0)
    # 详细结果（JSON）
    step_results = Column(Text, default="[]")
    team_id = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
