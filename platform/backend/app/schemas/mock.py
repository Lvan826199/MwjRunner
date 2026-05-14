"""Mock 规则 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MockRuleCreate(BaseModel):
    name: str
    method: str = "GET"
    path: str
    match_headers: str = "{}"
    match_query: str = "{}"
    match_body: str = ""
    response_status: int = 200
    response_headers: str = '{"Content-Type": "application/json"}'
    response_body: str = "{}"
    response_delay_ms: int = 0
    priority: int = 0
    description: str = ""


class MockRuleUpdate(BaseModel):
    name: str | None = None
    method: str | None = None
    path: str | None = None
    match_headers: str | None = None
    match_query: str | None = None
    match_body: str | None = None
    response_status: int | None = None
    response_headers: str | None = None
    response_body: str | None = None
    response_delay_ms: int | None = None
    priority: int | None = None
    is_active: int | None = None
    description: str | None = None


class MockRuleResponse(BaseModel):
    id: int
    name: str
    method: str
    path: str
    match_headers: str
    match_query: str
    match_body: str
    response_status: int
    response_headers: str
    response_body: str
    response_delay_ms: int
    priority: int
    is_active: int
    hit_count: int
    description: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class MockGenerateRequest(BaseModel):
    """从用例自动生成 Mock 规则。"""
    case_id: int
