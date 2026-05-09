"""JSON 报告测试。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary


def _result() -> RunResult:
    step = StepResult(
        name="健康检查",
        status="passed",
        request=HttpRequest(method="GET", url="/health"),
        response=HttpResponse(status_code=200, headers={}, cookies={}, body=b'{"status":"ok"}', elapsed_ms=8.0),
    )
    case = CaseResult(name="健康检查用例", status="passed", steps=[step])
    return RunResult(
        run_id="run-json-001",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(total_cases=1, passed_cases=1, total_steps=1, passed_steps=1, elapsed_ms=8.0),
        cases=[case],
    )


def test_json_reporter_renders_json_report() -> None:
    output = JsonReporter().render(_result())

    data = json.loads(output)

    assert data["run_id"] == "run-json-001"
    assert data["summary"]["total_cases"] == 1
    assert data["cases"][0]["steps"][0]["request"]["url"] == "/health"
    assert data["cases"][0]["steps"][0]["response"]["status_code"] == 200
    assert "assertions" in data["cases"][0]["steps"][0]
    assert "extracts" in data["cases"][0]["steps"][0]
    assert "errors" in data


def test_json_reporter_writes_json_file(tmp_path) -> None:
    output_file = tmp_path / "mwjrunner-report.json"

    JsonReporter().write(_result(), output_file)

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["run_id"] == "run-json-001"
