"""环境配置 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.environment import Environment
from app.schemas.environment import (
    EnvironmentCreate,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentUpdate,
)

router = APIRouter(prefix="/api/environments", tags=["环境配置"])


@router.get("", response_model=list[EnvironmentListResponse])
async def list_environments(db: AsyncSession = Depends(get_db)):
    """获取环境列表。"""
    result = await db.execute(select(Environment).order_by(Environment.name))
    return result.scalars().all()


@router.get("/{env_id}", response_model=EnvironmentResponse)
async def get_environment(env_id: int, db: AsyncSession = Depends(get_db)):
    """获取环境详情。"""
    env = await db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    return env


@router.post("", response_model=EnvironmentResponse, status_code=201)
async def create_environment(data: EnvironmentCreate, db: AsyncSession = Depends(get_db)):
    """创建环境。"""
    # 检查名称唯一
    existing = await db.execute(select(Environment).where(Environment.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"环境名称 '{data.name}' 已存在")
    env = Environment(**data.model_dump())
    db.add(env)
    await db.commit()
    await db.refresh(env)
    return env


@router.put("/{env_id}", response_model=EnvironmentResponse)
async def update_environment(env_id: int, data: EnvironmentUpdate, db: AsyncSession = Depends(get_db)):
    """更新环境。"""
    env = await db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(env, field, value)
    await db.commit()
    await db.refresh(env)
    return env


@router.delete("/{env_id}", status_code=204)
async def delete_environment(env_id: int, db: AsyncSession = Depends(get_db)):
    """删除环境。"""
    env = await db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    await db.delete(env)
    await db.commit()


@router.post("/{env_id}/clone", response_model=EnvironmentResponse, status_code=201)
async def clone_environment(env_id: int, new_name: str, db: AsyncSession = Depends(get_db)):
    """克隆环境配置。"""
    env = await db.get(Environment, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
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
    )
    db.add(new_env)
    await db.commit()
    await db.refresh(new_env)
    return new_env
