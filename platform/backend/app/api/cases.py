"""用例管理 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import TestCase
from app.schemas.case import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate, FolderNode

router = APIRouter(prefix="/api/cases", tags=["用例管理"])


@router.get("", response_model=list[CaseListResponse])
async def list_cases(
    folder: str | None = None,
    tags: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取用例列表。"""
    query = select(TestCase).order_by(TestCase.folder, TestCase.name)
    if folder:
        query = query.where(TestCase.folder == folder)
    if tags:
        query = query.where(TestCase.tags.contains(tags))
    if priority:
        query = query.where(TestCase.priority == priority)
    if search:
        query = query.where(TestCase.name.contains(search))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/folders", response_model=list[FolderNode])
async def list_folders(db: AsyncSession = Depends(get_db)):
    """获取用例目录树。"""
    result = await db.execute(select(TestCase.folder).distinct())
    folders = sorted(set(row[0] for row in result.all()))

    # 构建树结构
    root_children: list[FolderNode] = []
    for folder_path in folders:
        parts = [p for p in folder_path.strip("/").split("/") if p]
        _insert_path(root_children, parts, "")
    return root_children


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    """获取用例详情。"""
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return case


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """创建用例。"""
    filename = _safe_filename(data.name) + ".yaml"
    case = TestCase(
        name=data.name,
        folder=data.folder,
        filename=filename,
        tags=data.tags,
        priority=data.priority,
        content=data.content or _default_content(data.name),
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: int, data: CaseUpdate, db: AsyncSession = Depends(get_db)):
    """更新用例。"""
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=204)
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    """删除用例。"""
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    await db.delete(case)
    await db.commit()


def _insert_path(children: list[FolderNode], parts: list[str], prefix: str) -> None:
    """递归插入路径到树结构。"""
    if not parts:
        return
    current = parts[0]
    full_path = f"{prefix}/{current}" if prefix else f"/{current}"
    for child in children:
        if child.label == current:
            _insert_path(child.children, parts[1:], full_path)
            return
    node = FolderNode(label=current, path=full_path)
    children.append(node)
    _insert_path(node.children, parts[1:], full_path)


def _safe_filename(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "_")
    return "".join(c for c in safe if c.isalnum() or c in "_-")[:64] or "unnamed"


def _default_content(name: str) -> str:
    return f"""name: {name}
tags: []
priority: P2
steps:
  - name: 请求示例
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
"""
