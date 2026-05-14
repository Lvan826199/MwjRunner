"""用户认证和团队管理 API。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import Team, User
from app.schemas.user import (
    LoginRequest,
    LoginResponse,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(tags=["用户与权限"])

# 简易 token 存储（生产环境应使用 JWT 或 Redis）
_tokens: dict[str, int] = {}


def hash_password(password: str) -> str:
    """SHA-256 哈希密码。"""
    return hashlib.sha256(password.encode()).hexdigest()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """从 Authorization header 获取当前用户。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    token = auth[7:]
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


# ===== 认证 =====

@router.post("/api/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录。"""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or user.password_hash != hash_password(data.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")

    token = secrets.token_hex(32)
    _tokens[token] = user.id
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return LoginResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/api/auth/logout")
async def logout(request: Request):
    """用户登出。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        _tokens.pop(auth[7:], None)
    return {"status": "ok"}


@router.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息。"""
    return user


# ===== 用户管理 =====

@router.get("/api/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    """获取用户列表。"""
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.post("/api/users", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """创建用户。"""
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name or data.username,
        email=data.email,
        role=data.role,
        team_id=data.team_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """更新用户。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/api/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """删除用户。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user)
    await db.commit()


# ===== 团队管理 =====

@router.get("/api/teams", response_model=list[TeamResponse])
async def list_teams(db: AsyncSession = Depends(get_db)):
    """获取团队列表。"""
    result = await db.execute(select(Team).order_by(Team.id))
    return result.scalars().all()


@router.post("/api/teams", response_model=TeamResponse, status_code=201)
async def create_team(data: TeamCreate, db: AsyncSession = Depends(get_db)):
    """创建团队。"""
    existing = await db.execute(select(Team).where(Team.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="团队名已存在")
    team = Team(**data.model_dump())
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.put("/api/teams/{team_id}", response_model=TeamResponse)
async def update_team(team_id: int, data: TeamUpdate, db: AsyncSession = Depends(get_db)):
    """更新团队。"""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/api/teams/{team_id}", status_code=204)
async def delete_team(team_id: int, db: AsyncSession = Depends(get_db)):
    """删除团队。"""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    await db.delete(team)
    await db.commit()
