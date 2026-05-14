"""CI/CD Pipeline 数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Pipeline(Base):
    """CI/CD Pipeline 配置。"""

    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    # CI 平台
    platform = Column(String(50), default="github")  # github, gitlab, jenkins, custom
    # 触发配置
    trigger_type = Column(String(50), default="webhook")  # webhook, schedule, manual
    cron_expr = Column(String(100), default="")  # 定时触发 cron
    webhook_secret = Column(String(200), default="")
    # 执行配置
    case_filter_tags = Column(String(200), default="")  # 按标签筛选用例
    env_name = Column(String(100), default="")  # 使用的环境
    base_url = Column(String(500), default="")
    # 通知
    notify_on_fail = Column(Integer, default=1)
    notify_webhook = Column(String(500), default="")  # 钉钉/飞书/Slack webhook
    # 徽章
    badge_enabled = Column(Integer, default=1)
    last_status = Column(String(20), default="unknown")  # unknown, passing, failing
    last_run_at = Column(DateTime, nullable=True)
    # 管理
    is_active = Column(Integer, default=1)
    description = Column(Text, default="")
    team_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PipelineRun(Base):
    """Pipeline 执行记录。"""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, nullable=False)
    trigger_source = Column(String(100), default="")  # push, schedule, manual, webhook
    commit_sha = Column(String(50), default="")
    branch = Column(String(100), default="")
    # 结果
    status = Column(String(20), default="pending")  # pending, running, passed, failed
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    elapsed_ms = Column(Integer, default=0)
    # 关联
    execution_id = Column(Integer, nullable=True)
    # 时间
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
