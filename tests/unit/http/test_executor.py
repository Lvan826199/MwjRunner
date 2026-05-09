"""HTTP 执行器单元测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

from mwjrunner.cases import load_yaml_case
from mwjrunner.http import HttpExecutor


@pytest.mark.unit
class TestHttpExecutor:
    """HTTP 执行器测试。"""

    def test_execute_without_httpx(self, tmp_path: Path) -> None:
        """测试未安装 httpx 时返回依赖缺失错误。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 请求
    request:
      method: GET
      url: /test
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor()

        # 如果 httpx 已安装, 跳过此测试
        if importlib.util.find_spec("httpx") is not None:
            pytest.skip("httpx 已安装, 跳过依赖缺失测试")

        result = executor.execute(case.steps[0].request)

        assert not result.is_success
        assert result.error is not None
        assert result.error.error_type == "dependency_missing"
        assert "httpx" in result.error.message

    def test_build_url_with_base_url(self) -> None:
        """测试 base_url 拼接。"""
        executor = HttpExecutor(base_url="http://localhost:8000")

        assert executor._build_url("/health") == "http://localhost:8000/health"
        assert executor._build_url("health") == "http://localhost:8000/health"
        assert executor._build_url("http://example.com/test") == "http://example.com/test"
        assert executor._build_url("https://example.com/test") == "https://example.com/test"

    def test_build_url_without_base_url(self) -> None:
        """测试无 base_url 时直接返回原 URL。"""
        executor = HttpExecutor()

        assert executor._build_url("/health") == "/health"
        assert executor._build_url("http://example.com/test") == "http://example.com/test"

    def test_build_body_from_json(self, tmp_path: Path) -> None:
        """测试从 json 字段构建请求体。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 请求
    request:
      method: POST
      url: /test
      json:
        key: value
        中文: 测试
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor()

        body = executor._build_body(case.steps[0].request)

        assert body is not None
        assert '"key": "value"' in body or '"key":"value"' in body
        assert "中文" in body

    def test_build_body_from_data(self, tmp_path: Path) -> None:
        """测试从 data 字段构建请求体。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 请求
    request:
      method: POST
      url: /test
      data:
        key: value
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor()

        body = executor._build_body(case.steps[0].request)

        assert body is not None
        assert "key" in body

    def test_build_body_from_body_field(self, tmp_path: Path) -> None:
        """测试从 body 字段构建请求体。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 请求
    request:
      method: POST
      url: /test
      body: "raw body content"
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor()

        body = executor._build_body(case.steps[0].request)

        assert body == "raw body content"

    def test_build_body_from_body_field_redacts_text(self, tmp_path: Path) -> None:
        """测试从 body 字段构建请求体时脱敏文本。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 请求
    request:
      method: POST
      url: /test
      body: "token=raw-token&username=admin"
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor()

        body = executor._build_body(case.steps[0].request)

        assert body == "token=***REDACTED***&username=admin"

    def test_default_timeout(self) -> None:
        """测试默认超时时间。"""
        executor = HttpExecutor()
        assert executor.default_timeout == 30.0

        executor_custom = HttpExecutor(default_timeout=10.0)
        assert executor_custom.default_timeout == 10.0

    def test_request_snapshot_redacts_sensitive_fields(self, tmp_path: Path) -> None:
        """测试请求快照脱敏敏感字段。"""
        case_file = tmp_path / "test.yaml"
        case_file.write_text(
            """
name: 测试用例
steps:
  - name: 登录
    request:
      method: POST
      url: /api/login?token=raw-query-token&keyword=admin
      headers:
        Authorization: Bearer raw-token
        X-Trace-Id: trace-001
      cookies:
        session: raw-cookie
      json:
        username: admin
        password: raw-password
        nested:
          access_token: raw-access-token
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor(base_url="http://localhost:8000")

        snapshot = executor._build_request_snapshot(case.steps[0].request)

        assert snapshot.method == "POST"
        assert snapshot.url.startswith("http://localhost:8000/api/login?")
        assert "raw-query-token" not in snapshot.url
        assert "keyword=admin" in snapshot.url
        assert snapshot.headers["Authorization"] == "***REDACTED***"
        assert snapshot.headers["X-Trace-Id"] == "trace-001"
        assert snapshot.cookies["session"] == "***REDACTED***"
        assert snapshot.body is not None
        assert "raw-password" not in snapshot.body
        assert "raw-access-token" not in snapshot.body
        assert "***REDACTED***" in snapshot.body

    def test_response_snapshot_redacts_sensitive_headers(self) -> None:
        """测试响应快照响应头敏感字段脱敏。"""
        executor = HttpExecutor()

        headers = executor._redact_mapping({"set-cookie": "session=raw-cookie", "x-trace-id": "trace-001"})

        assert headers["set-cookie"] == "***REDACTED***"
        assert headers["x-trace-id"] == "trace-001"

    def test_response_body_redacts_json_sensitive_fields(self) -> None:
        """测试响应体 JSON 敏感字段脱敏。"""
        executor = HttpExecutor()
        response = httpx.Response(
            status_code=200,
            headers={"content-type": "application/json", "set-cookie": "session=raw-cookie"},
            json={
                "code": 0,
                "data": {
                    "token": "raw-token",
                    "profile": {"name": "admin", "secret": "raw-secret"},
                },
            },
        )

        body = executor._redact_response_body(response).decode("utf-8")

        assert "raw-token" not in body
        assert "raw-secret" not in body
        assert "admin" in body
        assert "***REDACTED***" in body

    def test_response_body_redacts_text_sensitive_fields(self) -> None:
        """测试响应体文本敏感字段脱敏。"""
        executor = HttpExecutor()
        response = httpx.Response(
            status_code=200,
            headers={"content-type": "text/plain"},
            content=b"token=raw-token&username=admin",
        )

        body = executor._redact_response_body(response).decode("utf-8")

        assert body == "token=***REDACTED***&username=admin"
