"""报告退出码映射。"""

from __future__ import annotations

from mwjrunner.reports.model import RunResult

SUCCESS_EXIT_CODE = 0
ASSERTION_FAILED_EXIT_CODE = 1
ERROR_EXIT_CODE = 2
INTERNAL_ERROR_EXIT_CODE = 3


def resolve_exit_code(result: RunResult) -> int:
    """根据运行结果返回稳定退出码。"""
    if (
        result.errors
        or result.summary.total_errors > 0
        or result.summary.error_cases > 0
        or result.summary.error_steps > 0
    ):
        return ERROR_EXIT_CODE
    if result.summary.failed_assertions > 0 or result.summary.failed_cases > 0 or result.summary.failed_steps > 0:
        return ASSERTION_FAILED_EXIT_CODE
    return SUCCESS_EXIT_CODE
