"""执行历史和趋势报告。

记录每次运行结果摘要到本地 history.json，支持趋势查询。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from mwjrunner.reports.model import RunResult


@dataclass
class HistoryEntry:
    """单次运行历史记录。"""

    run_id: str
    started_at: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    elapsed_ms: float
    pass_rate: float


def record_history(result: RunResult, history_file: Path | None = None) -> Path:
    """将运行结果追加到历史文件。"""
    if history_file is None:
        history_file = Path("reports") / "history.json"

    history_file.parent.mkdir(parents=True, exist_ok=True)

    entries = load_history(history_file)

    s = result.summary
    total = s.total_cases or 1
    entry = HistoryEntry(
        run_id=result.run_id,
        started_at=result.started_at.isoformat(),
        total_cases=s.total_cases,
        passed_cases=s.passed_cases,
        failed_cases=s.failed_cases,
        error_cases=s.error_cases,
        elapsed_ms=s.elapsed_ms,
        pass_rate=round(s.passed_cases / total, 4) if total > 0 else 0.0,
    )
    entries.append(entry)

    # 保留最近 100 条
    entries = entries[-100:]

    history_file.write_text(
        json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return history_file


def load_history(history_file: Path) -> list[HistoryEntry]:
    """加载历史记录。"""
    if not history_file.is_file():
        return []
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        return [HistoryEntry(**item) for item in data]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def get_trend(history_file: Path, last_n: int = 10) -> list[dict[str, Any]]:
    """获取最近 N 次运行趋势。"""
    entries = load_history(history_file)
    recent = entries[-last_n:]
    return [asdict(e) for e in recent]
