"""场景编排 API。"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import async_session, get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.case import TestCase
from app.models.scenario import Scenario, ScenarioRun
from app.models.user import User

router = APIRouter(prefix="/api/scenarios", tags=["场景编排"])


class ScenarioCreate(BaseModel):
    name: str
    description: str = ""
    steps: str = "[]"
    variables: str = "{}"
    tags: str = ""


class ScenarioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: str | None = None
    variables: str | None = None
    tags: str | None = None
    is_active: int | None = None


@router.get("")
async def list_scenarios(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取场景列表。"""
    query = select(Scenario).order_by(Scenario.id.desc())
    query = team_filter(query, Scenario, user)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取场景详情。"""
    return await check_resource_access(db, Scenario, scenario_id, user)


@router.post("", status_code=201)
async def create_scenario(
    data: ScenarioCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """创建场景。"""
    s = Scenario(**data.model_dump(), team_id=user.team_id)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: int, data: ScenarioUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """更新场景。"""
    s = await check_resource_access(db, Scenario, scenario_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """删除场景。"""
    s = await check_resource_access(db, Scenario, scenario_id, user)
    await db.delete(s)
    await db.commit()


@router.post("/{scenario_id}/run", status_code=201)
async def run_scenario(
    scenario_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """执行场景。"""
    s = await check_resource_access(db, Scenario, scenario_id, user)

    run = ScenarioRun(
        scenario_id=scenario_id,
        status="running",
        started_at=datetime.utcnow(),
        team_id=user.team_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(_execute_scenario, run.id, s.steps, s.variables)
    return run


@router.get("/{scenario_id}/runs")
async def list_scenario_runs(
    scenario_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """获取场景执行记录。"""
    await check_resource_access(db, Scenario, scenario_id, user)
    result = await db.execute(
        select(ScenarioRun).where(ScenarioRun.scenario_id == scenario_id).order_by(ScenarioRun.id.desc())
    )
    return result.scalars().all()


async def _execute_scenario(run_id: int, steps_json: str, variables_json: str):  # noqa: PLR0912 PLR0915
    """后台执行场景编排。"""
    import httpx  # noqa: PLC0415

    async with async_session() as db:
        run = await db.get(ScenarioRun, run_id)
        if not run:
            return

        try:
            steps = json.loads(steps_json)
            variables = json.loads(variables_json)
        except json.JSONDecodeError:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            await db.commit()
            return

        context: dict[str, str] = dict(variables)
        step_results = []
        total = len(steps)
        passed = 0
        failed = 0
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, step in enumerate(steps):
                step_start = time.perf_counter()
                step_name = step.get("name", f"步骤{i + 1}")
                case_id = step.get("case_id")
                delay_ms = step.get("delay_ms", 0)

                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)

                # 获取用例
                case = await db.get(TestCase, case_id) if case_id else None
                if not case:
                    step_results.append(
                        {
                            "name": step_name,
                            "status": "skipped",
                            "error": f"用例 {case_id} 不存在",
                        }
                    )
                    failed += 1
                    continue

                # 解析用例 YAML
                import yaml  # noqa: PLC0415

                try:
                    case_data = yaml.safe_load(case.content)
                except Exception:
                    step_results.append({"name": step_name, "status": "error", "error": "YAML 解析失败"})
                    failed += 1
                    continue

                case_steps = case_data.get("steps", [])
                step_passed = True

                for cs in case_steps:
                    req = cs.get("request", {})
                    if not req:
                        continue

                    method = req.get("method", "GET").upper()
                    url = _interpolate(req.get("url", ""), context)
                    headers = {k: _interpolate(v, context) for k, v in req.get("headers", {}).items()}
                    body = req.get("body")
                    if body and isinstance(body, str):
                        body = _interpolate(body, context)

                    try:
                        resp = await client.request(method, url, headers=headers, content=body)
                        # 提取变量
                        extracts = step.get("extract", {})
                        for var_name, json_path in extracts.items():
                            try:
                                resp_data = resp.json()
                                value = _json_path_extract(resp_data, json_path)
                                if value is not None:
                                    context[var_name] = str(value)
                            except Exception:
                                pass

                        # 简单断言
                        assertions = cs.get("assertions", [])
                        for a in assertions:
                            if a.get("type") == "status_code" and resp.status_code != a.get("expected"):
                                step_passed = False
                    except Exception:
                        step_passed = False

                elapsed = (time.perf_counter() - step_start) * 1000
                if step_passed:
                    passed += 1
                    step_results.append({"name": step_name, "status": "passed", "elapsed_ms": round(elapsed, 1)})
                else:
                    failed += 1
                    step_results.append({"name": step_name, "status": "failed", "elapsed_ms": round(elapsed, 1)})

                # 如果配置了 stop_on_fail
                if not step_passed and step.get("stop_on_fail", False):
                    break

        total_elapsed = (time.perf_counter() - start_time) * 1000
        run.status = "passed" if failed == 0 else "failed"
        run.total_steps = total
        run.passed_steps = passed
        run.failed_steps = failed
        run.elapsed_ms = int(total_elapsed)
        run.step_results = json.dumps(step_results, ensure_ascii=False)
        run.finished_at = datetime.utcnow()
        await db.commit()


def _interpolate(text: str, context: dict[str, str]) -> str:
    """替换 {{var}} 占位符。"""

    def replacer(match):
        key = match.group(1).strip()
        return context.get(key, match.group(0))

    return re.sub(r"\{\{(.+?)\}\}", replacer, text)


def _json_path_extract(data: Any, path: str) -> Any:
    """简单 JSONPath 提取（支持 $.key.subkey 格式）。"""
    if not path.startswith("$."):
        return None
    keys = path[2:].split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            idx = int(key)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current
