"""执行管理 API 路由。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.api.ws import notify_execution_created, notify_execution_update
from app.core import STORAGE_DIR
from app.core.database import async_session, get_db
from app.core.permissions import check_resource_access, team_filter
from app.models.case import TestCase
from app.models.execution import Execution
from app.models.user import User
from app.schemas.execution import ExecutionCreate, ExecutionListResponse, ExecutionResponse

router = APIRouter(prefix="/api/executions", tags=["执行管理"])


@router.get("", response_model=list[ExecutionListResponse])
async def list_executions(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取执行记录列表（团队隔离）。"""
    query = select(Execution).order_by(Execution.started_at.desc()).limit(limit)
    query = team_filter(query, Execution, user)
    if status:
        query = query.where(Execution.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取执行详情。"""
    return await check_resource_access(db, Execution, execution_id, user)


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    data: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发用例执行。"""
    # 确定用例路径
    case_name = ""
    case_path = data.case_path

    if data.case_id:
        # 团队鉴权：禁止触发其他团队的用例（IDOR 防护）
        case = await check_resource_access(db, TestCase, data.case_id, user)
        case_name = case.name
        # 将用例内容写入临时文件
        case_path = _write_case_to_storage(case)

    if not case_path:
        raise HTTPException(status_code=400, detail="请指定用例 ID 或路径")

    # 创建执行记录
    run_id = _generate_run_id()
    report_dir = str(STORAGE_DIR / "reports" / run_id)

    execution = Execution(
        run_id=run_id,
        case_id=data.case_id,
        case_name=case_name or Path(case_path).stem,
        status="running",
        base_url=data.base_url,
        env_name=data.env_name,
        tags=data.tags,
        workers=data.workers,
        report_dir=report_dir,
        team_id=user.team_id,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 后台执行
    background_tasks.add_task(
        _run_engine_task,
        execution_id=execution.id,
        case_path=case_path,
        base_url=data.base_url,
        env_name=data.env_name,
        tags=data.tags,
        workers=data.workers,
        variables=data.variables,
        report_dir=report_dir,
    )

    # WebSocket 通知
    background_tasks.add_task(notify_execution_created, execution.id, execution.case_name, user.team_id)

    return execution


@router.get("/{execution_id}/report")
async def get_execution_report(
    execution_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """获取执行的 JSON 报告。"""
    execution = await check_resource_access(db, Execution, execution_id, user)
    if not execution.report_dir:
        raise HTTPException(status_code=404, detail="报告目录未配置")

    report_dir = Path(execution.report_dir)
    if not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="报告目录不存在")

    # 查找 result.json
    json_files = list(report_dir.glob("*/result.json"))
    if not json_files:
        raise HTTPException(status_code=404, detail="JSON 报告文件不存在")

    try:
        return json.loads(json_files[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"报告解析失败: {exc}") from exc


async def _run_engine_task(  # noqa: PLR0912 PLR0915
    execution_id: int,
    case_path: str,
    base_url: str,
    env_name: str,
    tags: str,
    workers: int,
    variables: dict[str, str],
    report_dir: str,
) -> None:
    """后台执行引擎任务。"""
    cmd = ["mwjrunner", "run", case_path, "--report", "json,html", "--report-dir", report_dir]

    if base_url:
        cmd.extend(["--base-url", base_url])
    if env_name:
        cmd.extend(["--env", env_name])
    if tags:
        cmd.extend(["--tags", tags])
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    for key, value in variables.items():
        cmd.extend(["--var", f"{key}={value}"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        exit_code = process.returncode or 0
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
    except TimeoutError:
        exit_code = -1
        stdout_text = ""
        stderr_text = "执行超时（600秒）"
    except Exception as exc:
        exit_code = -1
        stdout_text = ""
        stderr_text = f"执行异常: {exc}"

    # 解析报告
    summary = _parse_report_summary(Path(report_dir))

    # 确定状态
    if exit_code == -1:
        status = "timeout"
    elif exit_code == 0:
        status = "passed"
    elif exit_code == 1:
        status = "failed"
    else:
        status = "error"

    # 更新数据库
    async with async_session() as db:
        execution = await db.get(Execution, execution_id)
        if execution:
            execution.status = status
            execution.exit_code = exit_code
            execution.stdout = stdout_text[-5000:]  # 限制长度
            execution.stderr = stderr_text[-2000:]
            execution.finished_at = datetime.utcnow()
            execution.total_cases = summary.get("total_cases", 0)
            execution.passed_cases = summary.get("passed_cases", 0)
            execution.failed_cases = summary.get("failed_cases", 0)
            execution.error_cases = summary.get("error_cases", 0)
            execution.total_steps = summary.get("total_steps", 0)
            execution.total_assertions = summary.get("total_assertions", 0)
            execution.failed_assertions = summary.get("failed_assertions", 0)
            execution.elapsed_ms = summary.get("elapsed_ms", 0.0)
            await db.commit()

            # WebSocket 通知执行完成
            await notify_execution_update(
                execution_id,
                status,
                execution.team_id,
                passed_cases=execution.passed_cases,
                failed_cases=execution.failed_cases,
                elapsed_ms=execution.elapsed_ms,
            )

    # 更新用例状态
    if summary and execution and execution.case_id:
        async with async_session() as db:
            case = await db.get(TestCase, execution.case_id)
            if case:
                case.status = status
                case.last_run_at = datetime.utcnow()
                await db.commit()


def _write_case_to_storage(case: TestCase) -> str:
    """将用例内容写入存储目录。"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    case_dir = STORAGE_DIR / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    file_path = case_dir / case.filename
    file_path.write_text(case.content, encoding="utf-8")
    return str(file_path)


def _generate_run_id() -> str:
    return f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"


def _parse_report_summary(report_dir: Path) -> dict:
    """解析报告目录中的 JSON 报告 summary。"""
    if not report_dir.is_dir():
        return {}
    json_files = list(report_dir.glob("*/result.json"))
    if not json_files:
        return {}
    try:
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        return data.get("summary", {})
    except (json.JSONDecodeError, OSError):
        return {}
