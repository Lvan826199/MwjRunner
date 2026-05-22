"""JWT 认证与密码安全模块。"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

# 配置（可通过环境变量覆盖）
JWT_SECRET = os.getenv("JWT_SECRET", "mwjrunner-dev-secret-change-in-prod!")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "mwjrunner-refresh-secret-change!!")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))


def hash_password(password: str) -> str:
    """bcrypt 哈希密码。"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码。兼容旧 SHA-256 哈希。"""
    # 兼容旧 SHA-256 格式（64 字符 hex）
    if len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed):
        import hashlib  # noqa: PLC0415

        return hashlib.sha256(password.encode()).hexdigest() == hashed
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, username: str, role: str, team_id: int | None) -> str:
    """创建 Access Token。"""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "team_id": team_id,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """创建 Refresh Token，返回 (token, jti, expires_at)。"""
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": now,
        "jti": jti,
        "type": "refresh",
    }
    token = jwt.encode(payload, JWT_REFRESH_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def decode_access_token(token: str) -> dict:
    """解码 Access Token，失败抛出异常。"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    """解码 Refresh Token，失败抛出异常。"""
    return jwt.decode(token, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
