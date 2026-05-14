"""Mock 规则管理 API。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.case import TestCase
from app.models.mock import MockRule
from app.schemas.mock import (
    MockGenerateRequest,
    MockRuleCreate,
    MockRuleResponse,
    MockRuleUpdate,
)

router = APIRouter(prefix="/api/mocks", tags=["Mock 服务"])


@router.get("", response_model=list[MockRuleResponse])
async def list_mock_rules(db: AsyncSession = Depends(get_db)):
    """获取 Mock 规则列表。"""
    result = await db.execute(select(MockRule).order_by(MockRule.priority.desc(), MockRule.id.desc()))
    return result.scalars().all()


@router.get("/{rule_id}", response_model=MockRuleResponse)
async def get_mock_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """获取 Mock 规则详情。"""
    rule = await db.get(MockRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    return rule


@router.post("", response_model=MockRuleResponse, status_code=201)
async def create_mock_rule(data: MockRuleCreate, db: AsyncSession = Depends(get_db)):
    """创建 Mock 规则。"""
    rule = MockRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=MockRuleResponse)
async def update_mock_rule(rule_id: int, data: MockRuleUpdate, db: AsyncSession = Depends(get_db)):
    """更新 Mock 规则。"""
    rule = await db.get(MockRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_mock_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """删除 Mock 规则。"""
    rule = await db.get(MockRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    await db.delete(rule)
    await db.commit()


@router.post("/generate", response_model=list[MockRuleResponse], status_code=201)
async def generate_from_case(data: MockGenerateRequest, db: AsyncSession = Depends(get_db)):
    """从用例自动生成 Mock 规则。"""
    case = await db.get(TestCase, data.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    if not case.content:
        raise HTTPException(status_code=400, detail="用例内容为空")

    import yaml
    try:
        case_data = yaml.safe_load(case.content)
    except yaml.YAMLError:
        raise HTTPException(status_code=400, detail="用例 YAML 解析失败")

    steps = case_data.get("steps", [])
    if not steps:
        raise HTTPException(status_code=400, detail="用例无 steps")

    generated = []
    for i, step in enumerate(steps):
        request = step.get("request", {})
        if not request:
            continue
        method = request.get("method", "GET").upper()
        url = request.get("url", "")
        if not url:
            continue

        # 从断言中推断响应
        assertions = step.get("assertions", [])
        response_status = 200
        response_body = "{}"
        for a in assertions:
            if a.get("type") == "status_code":
                response_status = a.get("expected", 200)
            if a.get("type") == "json_path":
                # 尝试构建响应体
                pass

        rule = MockRule(
            name=f"{case.name} - {step.get('name', f'步骤{i+1}')}",
            method=method,
            path=url,
            response_status=response_status,
            response_body=response_body,
            description=f"自动生成自用例: {case.name}",
        )
        db.add(rule)
        generated.append(rule)

    await db.commit()
    for r in generated:
        await db.refresh(r)
    return generated


@router.post("/{rule_id}/reset-hits")
async def reset_hit_count(rule_id: int, db: AsyncSession = Depends(get_db)):
    """重置命中计数。"""
    rule = await db.get(MockRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    rule.hit_count = 0
    await db.commit()
    return {"status": "ok"}
