"""用例管理数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class TestCase(Base):
    """用例元数据表。"""

    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    folder = Column(String(500), default="/")
    filename = Column(String(255), nullable=False)
    tags = Column(String(500), default="")
    priority = Column(String(10), default="P2")
    status = Column(String(20), default="idle")  # idle, passed, failed, error
    last_run_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=False, default="")
    team_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
