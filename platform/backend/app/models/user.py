"""多租户和权限管理数据模型。"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Team(Base):
    """团队/租户。"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    max_members = Column(Integer, default=50)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    """用户。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    display_name = Column(String(100), default="")
    email = Column(String(200), default="")
    role = Column(String(20), default="member")  # admin, manager, member
    team_id = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RefreshToken(Base):
    """Refresh Token 持久化存储。"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    jti = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
