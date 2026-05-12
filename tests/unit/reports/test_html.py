"""HTML 报告测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.reports.html import HtmlReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary
from mwjrunner.variables.engine import ExtractResult


def _result() -> RunResult:
    step = StepResult(
        name="健康检查",
        status="passed",
        request=HttpRequest(method="GET", url="http://127.0.0.1:8000/health"),
        response=HttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            cookies={},
            body=b'{"status":"ok"}',
            elapsed_ms=8.0,
        ),
        assertions=[
            AssertionResult(type="status_code", passed=True, expected=200, actual=200, message="status_code 断言通过"),
        ],
        extracts=[
            ExtractResult(name="token", type="json_path", path="$.data.token", value="***REDACTED***", extracted=True),
        ],
    )
    case = CaseResult(name="健康检查用例", status="passed", source_file="examples/cases/health.yaml", steps=[step])
    return RunResult(
        run_id="run-html-001",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(
            total_cases=1, passed_cases=1, total_steps=1,
            passed_steps=1, total_assertions=1, elapsed_ms=8.0,
        ),
        cases=[case],
    )


def _failed_result() -> RunResult:
    step = StepResult(
        name="故意写错",
        status="failed",
        request=HttpRequest(method="GET", url="http://127.0.0.1:8000/health"),
        response=HttpResponse(status_code=200, headers={}, cookies={}, body=b'{"status":"ok"}', elapsed_ms=5.0),
        assertions=[
            AssertionResult(
                type="json_path", passed=False, expected="down",
                actual="ok", path="$.status", message="json_path 断言失败",
            ),
        ],
    )
    case = CaseResult(name="失败用例", status="failed", steps=[step])
    return RunResult(
        run_id="run-html-002",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(
            total_cases=1, failed_cases=1, total_steps=1,
            failed_steps=1, total_assertions=1, failed_assertions=1,
            elapsed_ms=5.0,
        ),
        cases=[case],
    )


def test_html_reporter_renders_valid_html() -> None:
    output = HtmlReporter().render(_result())

    assert "<!DOCTYPE html>" in output
    assert "<html" in output
    assert "</html>" in output
    assert "MwjRunner 测试报告" in output
    assert "run-html-001" in output


def test_html_reporter_shows_summary_stats() -> None:
    output = HtmlReporter().render(_result())

    assert "总用例" in output
    assert "通过用例" in output
    assert "总断言" in output


def test_html_reporter_escapes_xss_payload() -> None:
    step = StepResult(
        name='<script>alert("xss")</script>',
        status="passed",
        request=HttpRequest(method="GET", url="/health?q=<img onerror=alert(1)>"),
        response=HttpResponse(status_code=200, headers={}, cookies={}, body=b"ok", elapsed_ms=1.0),
    )
    case = CaseResult(name='<img src=x onerror="alert(1)">', status="passed", steps=[step])
    result = RunResult(
        run_id="xss-test",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(total_cases=1, passed_cases=1, total_steps=1, passed_steps=1, elapsed_ms=1.0),
        cases=[case],
    )
    output = HtmlReporter().render(result)

    assert "<script>" not in output
    assert 'onerror="alert(1)"' not in output
    assert "&lt;script&gt;" in output


def test_html_reporter_renders_failed_case_open() -> None:
    output = HtmlReporter().render(_failed_result())

    assert '<details class="case" open>' in output


def test_html_reporter_renders_passed_case_closed() -> None:
    output = HtmlReporter().render(_result())

    assert '<details class="case">' in output
    assert '<details class="case" open>' not in output


def test_html_reporter_writes_file(tmp_path) -> None:
    output_file = tmp_path / "report.html"

    HtmlReporter().write(_result(), output_file)

    content = output_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "run-html-001" in content


def test_html_reporter_handles_empty_run() -> None:
    result = RunResult(
        run_id="empty-run",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(),
    )
    output = HtmlReporter().render(result)

    assert "<!DOCTYPE html>" in output
    assert "无用例结果" in output


def test_html_reporter_handles_none_response() -> None:
    step = StepResult(name="无响应步骤", status="error", errors=["HTTP 请求失败"], elapsed_ms=0.0)
    case = CaseResult(name="错误用例", status="error", steps=[step])
    result = RunResult(
        run_id="no-resp",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(total_cases=1, error_cases=1, total_steps=1, error_steps=1, total_errors=1, elapsed_ms=0.0),
        cases=[case],
    )
    output = HtmlReporter().render(result)

    assert "<!DOCTYPE html>" in output
    assert "HTTP 请求失败" in output
