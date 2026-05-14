"""用户/团队 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    email: str = ""
    role: str = "member"
    team_id: int | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    role: str | None = None
    team_id: int | None = None
    is_active: int | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    email: str
    role: str
    team_id: int | None
    is_active: int
    last_login_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TeamCreate(BaseModel):
    name: str
    description: str = ""
    max_members: int = 50


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    max_members: int | None = None


class TeamResponse(BaseModel):
    id: int
    name: str
    description: str
    max_members: int
    created_at: datetime | None

    model_config = {"from_attributes": True}
