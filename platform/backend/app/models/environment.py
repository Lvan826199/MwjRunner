"""环境配置数据模型。"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Environment(Base):
    """环境配置表。"""

    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)  # dev, test, prod
    label = Column(String(100), default="")  # 显示名称
    base_url = Column(String(500), default="")
    timeout = Column(Integer, default=30)
    # 认证
    auth_type = Column(String(20), default="")  # bearer, basic, oauth2, 空
    auth_token = Column(String(500), default="")
    auth_username = Column(String(100), default="")
    auth_password = Column(String(200), default="")
    # 全局 headers（JSON 字符串）
    headers = Column(Text, default="{}")
    # 全局变量（JSON 字符串）
    variables = Column(Text, default="{}")
    # 描述
    description = Column(Text, default="")
    # 状态
    is_active = Column(Integer, default=1)
    team_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
