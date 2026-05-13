"""引擎调用封装。"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core import ENGINE_COMMAND


@dataclass
class EngineResult:
    """引擎执行结果。"""

    exit_code: int
    stdout: str
    stderr: str
    report: dict[str, Any] | None = None


async def run_engine(
    path: str,
    *,
    base_url: str | None = None,
    env: str | None = None,
    tags: str | None = None,
    workers: int | None = None,
    report_dir: str | None = None,
) -> EngineResult:
    """异步调用 mwjrunner CLI。"""
    cmd = [ENGINE_COMMAND, "run", path, "--report", "console,json"]

    if base_url:
        cmd.extend(["--base-url", base_url])
    if env:
        cmd.extend(["--env", env])
    if tags:
        cmd.extend(["--tags", tags])
    if workers:
        cmd.extend(["--workers", str(workers)])
    if report_dir:
        cmd.extend(["--report-dir", report_dir])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    result = EngineResult(
        exit_code=process.returncode or 0,
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )

    # 尝试读取 JSON 报告
    if report_dir:
        result.report = _find_json_report(Path(report_dir))

    return result


def _find_json_report(report_dir: Path) -> dict[str, Any] | None:
    """查找最新的 JSON 报告文件。"""
    if not report_dir.is_dir():
        return None
    json_files = sorted(report_dir.glob("*/result.json"), reverse=True)
    if not json_files:
        return None
    try:
        return json.loads(json_files[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
