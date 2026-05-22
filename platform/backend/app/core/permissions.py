"""权限控制模块 — RBAC + 团队数据隔离。"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.user import User


def require_role(*roles: str):
    """角色校验依赖工厂。"""
    from app.api.users import get_current_user  # noqa: PLC0415

    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return checker


def team_filter(query: Select, model, user: User) -> Select:
    """为查询注入团队隔离条件。admin 可看全部，其他角色只看本团队。"""
    if user.role == "admin":
        return query
    return query.where(model.team_id == user.team_id)


async def check_resource_access(db: AsyncSession, model, resource_id: int, user: User):
    """检查用户是否有权访问指定资源。无权返回 404（避免信息泄露）。"""
    resource = await db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    if user.role != "admin" and hasattr(resource, "team_id") and resource.team_id and resource.team_id != user.team_id:
        raise HTTPException(status_code=404, detail="资源不存在")
    return resource
