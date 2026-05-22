"""环境配置 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.environment import Environment
from app.models.user import User
from app.schemas.environment import (
    EnvironmentCreate,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentUpdate,
)

router = APIRouter(prefix="/api/environments", tags=["环境配置"])


@router.get("", response_model=list[EnvironmentListResponse])
async def list_environments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取环境列表。"""
    query = select(Environment).order_by(Environment.name)
    query = team_filter(query, Environment, user)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{env_id}", response_model=EnvironmentResponse)
async def get_environment(
    env_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取环境详情。"""
    return await check_resource_access(db, Environment, env_id, user)


@router.post("", response_model=EnvironmentResponse, status_code=201)
async def create_environment(
    data: EnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建环境。"""
    # 检查名称唯一
    existing = await db.execute(select(Environment).where(Environment.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"环境名称 '{data.name}' 已存在")
    env = Environment(**data.model_dump(), team_id=user.team_id)
    db.add(env)
    await db.commit()
    await db.refresh(env)
    return env


@router.put("/{env_id}", response_model=EnvironmentResponse)
async def update_environment(
    env_id: int,
    data: EnvironmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新环境。"""
    env = await check_resource_access(db, Environment, env_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(env, field, value)
    await db.commit()
    await db.refresh(env)
    return env


@router.delete("/{env_id}", status_code=204)
async def delete_environment(
    env_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除环境。"""
    env = await check_resource_access(db, Environment, env_id, user)
    await db.delete(env)
    await db.commit()


@router.post("/{env_id}/clone", response_model=EnvironmentResponse, status_code=201)
async def clone_environment(
    env_id: int,
    new_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """克隆环境配置。"""
    env = await check_resource_access(db, Environment, env_id, user)
    # 检查新名称唯一
    existing = await db.execute(select(Environment).where(Environment.name == new_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"环境名称 '{new_name}' 已存在")
    new_env = Environment(
        name=new_name,
        label=f"{env.label} (副本)",
        base_url=env.base_url,
        timeout=env.timeout,
        auth_type=env.auth_type,
        auth_token=env.auth_token,
        auth_username=env.auth_username,
        auth_password=env.auth_password,
        headers=env.headers,
        variables=env.variables,
        description=env.description,
        team_id=user.team_id,
    )
    db.add(new_env)
    await db.commit()
    await db.refresh(new_env)
    return new_env
