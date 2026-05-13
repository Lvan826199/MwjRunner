"""用例管理 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CaseCreate(BaseModel):
    name: str
    folder: str = "/"
    tags: str = ""
    priority: str = "P2"
    content: str = ""


class CaseUpdate(BaseModel):
    name: str | None = None
    folder: str | None = None
    tags: str | None = None
    priority: str | None = None
    content: str | None = None


class CaseResponse(BaseModel):
    id: int
    name: str
    folder: str
    filename: str
    tags: str
    priority: str
    status: str
    last_run_at: datetime | None
    content: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    id: int
    name: str
    folder: str
    filename: str
    tags: str
    priority: str
    status: str
    last_run_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class FolderNode(BaseModel):
    label: str
    path: str
    children: list[FolderNode] = []
