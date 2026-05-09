"""报告退出码映射测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.reports.exit_code import (
    ASSERTION_FAILED_EXIT_CODE,
    ERROR_EXIT_CODE,
    SUCCESS_EXIT_CODE,
    resolve_exit_code,
)
from mwjrunner.reports.model import RunResult, Summary


def _run_result(summary: Summary, errors: list[str] | None = None) -> RunResult:
    return RunResult(
        run_id="run-exit-code",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=summary,
        errors=errors or [],
    )


def test_exit_code_success() -> None:
    result = _run_result(Summary(total_cases=1, passed_cases=1))

    assert resolve_exit_code(result) == SUCCESS_EXIT_CODE


def test_exit_code_assertion_failed() -> None:
    result = _run_result(Summary(total_cases=1, failed_cases=1, failed_assertions=1))

    assert resolve_exit_code(result) == ASSERTION_FAILED_EXIT_CODE


def test_exit_code_error() -> None:
    result = _run_result(Summary(total_cases=1, error_cases=1, total_errors=1))

    assert resolve_exit_code(result) == ERROR_EXIT_CODE


def test_exit_code_error_has_priority_over_assertion_failure() -> None:
    result = _run_result(
        Summary(total_cases=1, failed_cases=1, error_cases=1, failed_assertions=1, total_errors=1),
        errors=["加载错误"],
    )

    assert resolve_exit_code(result) == ERROR_EXIT_CODE
