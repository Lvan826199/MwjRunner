"""环境配置 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EnvironmentCreate(BaseModel):
    name: str
    label: str = ""
    base_url: str = ""
    timeout: int = 30
    auth_type: str = ""
    auth_token: str = ""
    auth_username: str = ""
    auth_password: str = ""
    headers: str = "{}"
    variables: str = "{}"
    description: str = ""


class EnvironmentUpdate(BaseModel):
    label: str | None = None
    base_url: str | None = None
    timeout: int | None = None
    auth_type: str | None = None
    auth_token: str | None = None
    auth_username: str | None = None
    auth_password: str | None = None
    headers: str | None = None
    variables: str | None = None
    description: str | None = None
    is_active: int | None = None


class EnvironmentResponse(BaseModel):
    id: int
    name: str
    label: str
    base_url: str
    timeout: int
    auth_type: str
    auth_token: str
    auth_username: str
    auth_password: str
    headers: str
    variables: str
    description: str
    is_active: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class EnvironmentListResponse(BaseModel):
    id: int
    name: str
    label: str
    base_url: str
    auth_type: str
    is_active: int
    created_at: datetime | None

    model_config = {"from_attributes": True}
