"""Mock 规则数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class MockRule(Base):
    """Mock 规则表。"""

    __tablename__ = "mock_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    # 匹配条件
    method = Column(String(10), default="GET")
    path = Column(String(500), nullable=False)  # 路径模式，支持 /api/users/:id
    # 请求匹配（JSON 字符串，可选）
    match_headers = Column(Text, default="{}")
    match_query = Column(Text, default="{}")
    match_body = Column(Text, default="")  # JSONPath 表达式或精确匹配
    # 响应配置
    response_status = Column(Integer, default=200)
    response_headers = Column(Text, default='{"Content-Type": "application/json"}')
    response_body = Column(Text, default="{}")
    response_delay_ms = Column(Integer, default=0)  # 模拟延迟
    # 管理
    priority = Column(Integer, default=0)  # 优先级，数值越大越优先
    is_active = Column(Integer, default=1)
    hit_count = Column(Integer, default=0)
    description = Column(Text, default="")
    team_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
