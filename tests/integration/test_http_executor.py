"""HTTP 执行器集成测试。"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from mwjrunner.cases import load_yaml_case
from mwjrunner.http import HttpExecutor


@pytest.fixture(scope="module")
def fastapi_server():
    """启动 FastAPI 示例服务。"""
    examples_api_dir = Path(__file__).parent.parent.parent.parent / "examples" / "api"

    if not examples_api_dir.exists():
        pytest.skip("examples/api 目录不存在")

    # 启动服务
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(examples_api_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 等待服务启动
    time.sleep(2)

    yield "http://127.0.0.1:8000"

    # 停止服务
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.integration
class TestHttpExecutorIntegration:
    """HTTP 执行器集成测试。"""

    def test_execute_health_check(self, fastapi_server: str) -> None:
        """测试请求 FastAPI 示例服务 /health 接口。"""
        executor = HttpExecutor(base_url=fastapi_server)

        # 构建简单的 RequestSpec
        from mwjrunner.cases.model import RequestSpec

        request_spec = RequestSpec(method="GET", url="/health")

        result = executor.execute(request_spec)

        assert result.is_success
        assert result.response is not None
        assert result.response.status_code == 200
        assert result.error is None

        # 验证响应内容
        response_json = result.response.json()
        assert response_json["status"] == "ok"

    def test_execute_with_yaml_case(self, fastapi_server: str, tmp_path: Path) -> None:
        """测试使用 YAML 用例请求 FastAPI 服务。"""
        case_file = tmp_path / "health.yaml"
        case_file.write_text(
            """
name: 健康检查
steps:
  - name: 请求健康检查接口
    request:
      method: GET
      url: /health
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)
        executor = HttpExecutor(base_url=fastapi_server)

        result = executor.execute(case.steps[0].request)

        assert result.is_success
        assert result.response is not None
        assert result.response.status_code == 200

    def test_execute_post_with_json(self, fastapi_server: str) -> None:
        """测试 POST 请求携带 JSON 数据。"""
        from mwjrunner.cases.model import RequestSpec

        executor = HttpExecutor(base_url=fastapi_server)

        request_spec = RequestSpec(
            method="POST",
            url="/api/login",
            json={"username": "admin", "password": "admin123"},
        )

        result = executor.execute(request_spec)

        assert result.is_success
        assert result.response is not None
        assert result.response.status_code == 200

        response_json = result.response.json()
        assert response_json["code"] == 0
        assert "token" in response_json["data"]

    def test_execute_with_query_params(self, fastapi_server: str) -> None:
        """测试 GET 请求携带查询参数。"""
        from mwjrunner.cases.model import RequestSpec

        executor = HttpExecutor(base_url=fastapi_server)

        request_spec = RequestSpec(
            method="GET",
            url="/api/items",
            query={"keyword": "笔记本"},
        )

        result = executor.execute(request_spec)

        assert result.is_success
        assert result.response is not None
        assert result.response.status_code == 200

        response_json = result.response.json()
        assert response_json["code"] == 0
        assert len(response_json["data"]) > 0

    def test_execute_timeout(self, fastapi_server: str) -> None:
        """测试请求超时。"""
        from mwjrunner.cases.model import RequestSpec

        executor = HttpExecutor(base_url=fastapi_server)

        # 使用极短的超时时间
        request_spec = RequestSpec(
            method="GET",
            url="/health",
            timeout=0.001,
        )

        result = executor.execute(request_spec)

        # 超时可能成功也可能失败，取决于网络速度
        # 如果失败，应该是 timeout 错误
        if not result.is_success:
            assert result.error is not None
            assert result.error.error_type == "timeout"

    def test_execute_network_error(self) -> None:
        """测试网络错误。"""
        from mwjrunner.cases.model import RequestSpec

        # 使用不存在的服务器
        executor = HttpExecutor(base_url="http://localhost:9999")

        request_spec = RequestSpec(method="GET", url="/test")

        result = executor.execute(request_spec)

        # 网络错误可能返回错误或 502 响应（取决于是否有代理）
        if result.is_success:
            # 如果有代理返回 502，也算预期行为
            assert result.response is not None
            assert result.response.status_code in (502, 503, 504)
        else:
            assert result.error is not None
            assert result.error.error_type in ("network_error", "http_error")
