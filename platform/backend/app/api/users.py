"""用户认证和团队管理 API。"""

from __future__ import annotations

from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, Team, User
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(tags=["用户与权限"])

# 每用户最大活跃 Refresh Token 数
MAX_REFRESH_TOKENS_PER_USER = 5


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """从 Authorization header 解析 JWT 获取当前用户。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    token = auth[7:]
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 类型错误")

    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def require_role(*roles: str):
    """角色校验依赖工厂。"""
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return checker


# ===== 认证 =====

@router.post("/api/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 access_token + refresh_token。"""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")

    # 生成 Token
    access_token = create_access_token(user.id, user.username, user.role, user.team_id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)

    # 持久化 Refresh Token
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))

    # 清理超出限制的旧 Token
    old_tokens = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == 0)
        .order_by(RefreshToken.created_at.desc())
    )
    active_tokens = old_tokens.scalars().all()
    if len(active_tokens) > MAX_REFRESH_TOKENS_PER_USER:
        for t in active_tokens[MAX_REFRESH_TOKENS_PER_USER:]:
            t.revoked = 1

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/api/auth/refresh", response_model=RefreshResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """用 Refresh Token 换取新的 Access Token + Refresh Token。"""
    try:
        payload = decode_refresh_token(data.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh Token 无效")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token 类型错误")

    jti = payload["jti"]
    user_id = int(payload["sub"])

    # 检查是否已吊销
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    token_record = result.scalar_one_or_none()
    if not token_record or token_record.revoked:
        raise HTTPException(status_code=401, detail="Refresh Token 已吊销")

    # 吊销旧 Token（单次使用轮换）
    token_record.revoked = 1

    # 获取用户
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    # 生成新 Token 对
    access_token = create_access_token(user.id, user.username, user.role, user.team_id)
    new_refresh_token, new_jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=expires_at))

    await db.commit()
    return RefreshResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/api/auth/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """登出，吊销当前 Refresh Token。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = decode_access_token(token)
            # 吊销该用户最近的一个 Refresh Token
            user_id = int(payload["sub"])
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == user_id, RefreshToken.revoked == 0)
                .values(revoked=1)
            )
            await db.commit()
        except jwt.InvalidTokenError:
            pass
    return {"status": "ok"}


@router.post("/api/auth/logout-all")
async def logout_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """登出所有设备，吊销该用户所有 Refresh Token。"""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == 0)
        .values(revoked=1)
    )
    await db.commit()
    return {"status": "ok"}


@router.post("/api/auth/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码，吊销所有 Token。"""
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password_hash = hash_password(data.new_password)
    # 吊销所有 Refresh Token
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == 0)
        .values(revoked=1)
    )
    await db.commit()
    return {"status": "ok", "message": "密码修改成功，请重新登录"}


@router.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息。"""
    return user


# ===== 用户管理（仅 admin） =====

@router.get("/api/users", response_model=list[UserResponse])
async def list_users(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（仅管理员）。"""
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.post("/api/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（仅管理员）。"""
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
async def update_user(
    user_id: int,
    data: UserUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新用户（仅管理员）。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/api/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（仅管理员）。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user)
    await db.commit()


# ===== 团队管理（仅 admin） =====

@router.get("/api/teams", response_model=list[TeamResponse])
async def list_teams(db: AsyncSession = Depends(get_db)):
    """获取团队列表。"""
    result = await db.execute(select(Team).order_by(Team.id))
    return result.scalars().all()


@router.post("/api/teams", response_model=TeamResponse, status_code=201)
async def create_team(
    data: TeamCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """创建团队（仅管理员）。"""
    existing = await db.execute(select(Team).where(Team.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="团队名已存在")
    team = Team(**data.model_dump())
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.put("/api/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    data: TeamUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新团队（仅管理员）。"""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/api/teams/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """删除团队（仅管理员）。"""
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    await db.delete(team)
    await db.commit()
