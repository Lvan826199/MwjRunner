"""Console 报告测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary


def test_console_reporter_renders_summary() -> None:
    result = RunResult(
        run_id="run-console-001",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(
            total_cases=1,
            passed_cases=1,
            total_steps=1,
            passed_steps=1,
            total_assertions=1,
            elapsed_ms=15.0,
        ),
    )

    output = ConsoleReporter().render(result)

    assert "MwjRunner 执行摘要" in output
    assert "run-console-001" in output
    assert "用例: 1, 通过: 1, 失败: 0, 错误: 0" in output
    assert "步骤: 1, 通过: 1, 失败: 0, 错误: 0" in output
    assert "断言: 1, 失败: 0" in output
    assert "耗时: 15.0 ms" in output


def test_console_reporter_renders_failure_details() -> None:
    assertion = AssertionResult(
        type="status_code",
        passed=False,
        expected=200,
        actual=500,
        message="status_code 断言失败: 期望 200, 实际 500",
    )
    step = StepResult(
        name="健康检查",
        status="failed",
        assertions=[assertion],
        errors=["响应状态码异常"],
    )
    case = CaseResult(
        name="健康检查用例",
        status="failed",
        steps=[step],
    )
    result = RunResult(
        run_id="run-console-002",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(
            total_cases=1,
            failed_cases=1,
            total_steps=1,
            failed_steps=1,
            total_assertions=1,
            failed_assertions=1,
            total_errors=1,
        ),
        cases=[case],
    )

    output = ConsoleReporter().render(result)

    assert "失败或错误明细" in output
    assert "健康检查用例 / 健康检查" in output
    assert "status_code 断言失败" in output
    assert "响应状态码异常" in output
