"""报告结果模型测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary
from mwjrunner.variables.engine import ExtractResult


def test_run_result_to_dict_contains_required_report_sections() -> None:
    """测试运行结果可以序列化为 JSON 报告所需结构。"""
    started_at = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    ended_at = datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC)
    request = HttpRequest(
        method="GET",
        url="http://127.0.0.1:8000/health",
        headers={"authorization": "***REDACTED***"},
        query={"token": "***REDACTED***"},
    )
    response = HttpResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        cookies={"session": "***REDACTED***"},
        body=b'{"status":"ok"}',
        elapsed_ms=12.5,
    )
    assertion = AssertionResult(
        type="status_code",
        passed=True,
        expected=200,
        actual=200,
        message="status_code 断言通过",
    )
    extract = ExtractResult(
        name="token",
        type="json_path",
        path="$.data.token",
        value="***REDACTED***",
        extracted=True,
        message="变量提取成功",
    )
    step = StepResult(
        name="健康检查",
        status="passed",
        request=request,
        response=response,
        assertions=[assertion],
        extracts=[extract],
        elapsed_ms=12.5,
    )
    case = CaseResult(
        name="健康检查用例",
        source_file="examples/cases/health.yaml",
        status="passed",
        steps=[step],
    )
    summary = Summary(
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        error_cases=0,
        total_steps=1,
        passed_steps=1,
        failed_steps=0,
        error_steps=0,
        total_assertions=1,
        failed_assertions=0,
        total_errors=0,
        elapsed_ms=12.5,
    )
    result = RunResult(
        run_id="run-001",
        started_at=started_at,
        ended_at=ended_at,
        summary=summary,
        cases=[case],
    )

    data = result.to_dict()

    assert data["run_id"] == "run-001"
    assert data["started_at"] == "2026-05-09T10:00:00+00:00"
    assert data["ended_at"] == "2026-05-09T10:00:01+00:00"
    assert data["summary"]["total_cases"] == 1
    assert data["cases"][0]["steps"][0]["request"]["headers"]["authorization"] == "***REDACTED***"
    assert data["cases"][0]["steps"][0]["response"]["status_code"] == 200
    assert data["cases"][0]["steps"][0]["assertions"][0]["passed"] is True
    assert data["cases"][0]["steps"][0]["extracts"][0]["extracted"] is True
    assert data["errors"] == []
