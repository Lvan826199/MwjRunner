"""core 执行编排测试。"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from mwjrunner.core.runner import RunExecutor, run_from_args
from mwjrunner.http.model import HttpRequest, HttpResponse, HttpResult
from mwjrunner.reports.exit_code import ERROR_EXIT_CODE, INTERNAL_ERROR_EXIT_CODE, SUCCESS_EXIT_CODE


class FakeHttpExecutor:
    """用于隔离网络请求的 HTTP 执行器。"""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url

    def execute(self, request_spec):
        if request_spec.url == "/api/login":
            return HttpResult(
                request=HttpRequest(
                    method=request_spec.method,
                    url=f"{self.base_url}{request_spec.url}",
                    headers=request_spec.headers,
                    body=json.dumps(request_spec.json, ensure_ascii=False),
                ),
                response=HttpResponse(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    cookies={},
                    body=b'{"code":0,"message":"success","data":{"token":"***REDACTED***"}}',
                    raw_body=b'{"code":0,"message":"success","data":{"token":"demo-token"}}',
                    elapsed_ms=10.0,
                ),
            )
        if request_spec.url == "/api/profile":
            return HttpResult(
                request=HttpRequest(
                    method=request_spec.method,
                    url=f"{self.base_url}{request_spec.url}",
                    headers=request_spec.headers,
                ),
                response=HttpResponse(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    cookies={},
                    body=b'{"code":0,"data":{"username":"demo","nickname":"\xe7\xa4\xba\xe4\xbe\x8b\xe7\x94\xa8\xe6\x88\xb7"}}',
                    raw_body='{"code":0,"data":{"username":"demo","nickname":"示例用户"}}'.encode(),
                    elapsed_ms=12.0,
                ),
            )
        return HttpResult(
            request=HttpRequest(method=request_spec.method, url=f"{self.base_url}{request_spec.url}"),
            response=HttpResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                cookies={},
                body=b'{"status":"ok"}',
                raw_body=b'{"status":"ok"}',
                elapsed_ms=8.0,
            ),
        )


@pytest.fixture(autouse=True)
def patch_http_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    """替换 core runner 内的 HTTP 执行器, 避免单元测试依赖真实服务。"""
    monkeypatch.setattr("mwjrunner.core.runner.HttpExecutor", FakeHttpExecutor)


def test_run_executor_success_writes_json_report(tmp_path: Path) -> None:
    case_file = tmp_path / "health.yaml"
    report_dir = tmp_path / "reports"
    case_file.write_text(
        """
name: 健康检查
steps:
  - name: 服务健康状态
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: ok
""",
        encoding="utf-8",
    )

    exit_code = RunExecutor(
        path=case_file,
        base_url="http://127.0.0.1:8000",
        report="json",
        report_dir=report_dir,
    ).run()

    assert exit_code == SUCCESS_EXIT_CODE
    result_file = next(report_dir.glob("*/result.json"))
    report = json.loads(result_file.read_text(encoding="utf-8"))
    assert report["summary"]["passed_cases"] == 1
    assert report["summary"]["failed_assertions"] == 0


def test_run_executor_assertion_failed_returns_1(tmp_path: Path) -> None:
    case_file = tmp_path / "health_fail.yaml"
    case_file.write_text(
        """
name: 健康检查失败示例
steps:
  - name: 故意写错健康状态
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: down
""",
        encoding="utf-8",
    )

    result = RunExecutor(path=case_file, base_url="http://127.0.0.1:8000", report="json", report_dir=tmp_path).execute()

    assert result.summary.failed_cases == 1
    assert result.summary.failed_assertions == 1
    assert result.cases[0].steps[0].assertions[1].actual == "ok"


def test_run_executor_load_error_returns_error_exit_code(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.yaml"

    exit_code = RunExecutor(path=missing_file, report="json", report_dir=tmp_path).run()

    assert exit_code == ERROR_EXIT_CODE


def test_run_from_args_unsupported_option_returns_error_exit_code(tmp_path: Path) -> None:
    case_file = tmp_path / "health.yaml"
    case_file.write_text(
        """
name: 健康检查
steps:
  - name: 服务健康状态
    request:
      method: GET
      url: /health
""",
        encoding="utf-8",
    )
    args = Namespace(
        path=case_file,
        base_url="http://127.0.0.1:8000",
        report="json",
        report_dir=tmp_path,
        var=[],
        env=None,
        tags="smoke",
        exclude_tags=None,
        priority=None,
        workers=None,
        retry=None,
        fail_fast=False,
    )

    exit_code = run_from_args(args)

    assert exit_code == ERROR_EXIT_CODE


def test_run_executor_extracts_token_and_redacts_report(tmp_path: Path) -> None:
    case_file = tmp_path / "login_profile.yaml"
    report_dir = tmp_path / "reports"
    case_file.write_text(
        """
name: 登录后获取用户信息
variables:
  username: demo
  password: "123456"
steps:
  - name: 登录成功
    request:
      method: POST
      url: /api/login
      json:
        username: ${username}
        password: ${password}
    extract:
      token: $.data.token
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.code
        expected: 0
  - name: 获取用户信息
    request:
      method: GET
      url: /api/profile
      headers:
        Authorization: Bearer ${token}
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.data.username
        expected: demo
""",
        encoding="utf-8",
    )

    exit_code = RunExecutor(
        path=case_file,
        base_url="http://127.0.0.1:8000",
        report="json",
        report_dir=report_dir,
    ).run()

    assert exit_code == SUCCESS_EXIT_CODE
    result_file = next(report_dir.glob("*/result.json"))
    report_text = result_file.read_text(encoding="utf-8")
    assert "demo-token" not in report_text
    assert "123456" not in report_text
    assert "***REDACTED***" in report_text
    report = json.loads(report_text)
    assert report["cases"][0]["steps"][1]["request"]["headers"]["Authorization"] == "***REDACTED***"
    assert report["cases"][0]["steps"][0]["extracts"][0]["value"] == "***REDACTED***"


def test_run_executor_variable_error_returns_error_case(tmp_path: Path) -> None:
    case_file = tmp_path / "variable_error.yaml"
    case_file.write_text(
        """
name: 变量错误
steps:
  - name: 缺少变量
    request:
      method: GET
      url: /api/${missing}
""",
        encoding="utf-8",
    )

    result = RunExecutor(path=case_file, base_url="http://127.0.0.1:8000", report="json", report_dir=tmp_path).execute()

    assert result.summary.error_cases == 1
    assert result.summary.total_errors == 1
    assert "变量未定义" in result.cases[0].steps[0].errors[0]


def test_run_executor_internal_error_returns_internal_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case_file = tmp_path / "internal_error.yaml"
    case_file.write_text(
        """
name: 内部错误
steps:
  - name: 触发内部错误
    request:
      method: GET
      url: /health
""",
        encoding="utf-8",
    )

    def raise_unexpected_error(_path: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr("mwjrunner.core.runner.load_yaml_case", raise_unexpected_error)

    exit_code = RunExecutor(path=case_file, report="json", report_dir=tmp_path).run()

    assert exit_code == INTERNAL_ERROR_EXIT_CODE
