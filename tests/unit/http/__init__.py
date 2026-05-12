"""HTTP 执行器单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import httpx  # noqa: F401
except ImportError:
    HTTPX_INSTALLED = False
else:
    HTTPX_INSTALLED = True

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

        if HTTPX_INSTALLED:
            pytest.skip("httpx 已安装,跳过依赖缺失测试")

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

    def test_default_timeout(self) -> None:
        """测试默认超时时间。"""
        executor = HttpExecutor()
        assert executor.default_timeout == 30.0

        executor_custom = HttpExecutor(default_timeout=10.0)
        assert executor_custom.default_timeout == 10.0
