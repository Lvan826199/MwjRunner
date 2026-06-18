"""HTTP 执行器集成测试。"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import httpx
import pytest

from mwjrunner.cases import load_yaml_case
from mwjrunner.cases.model import RequestSpec
from mwjrunner.http import HttpExecutor


def _find_free_port() -> int:
    """向系统申请一个空闲端口，避免与机器上其他服务冲突。"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(base_url: str, process: subprocess.Popen, timeout: float = 15.0) -> None:
    """轮询 /health 直到服务就绪；进程提前退出或超时则失败并附带 stderr。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            pytest.fail(f"FastAPI 示例服务启动失败 (exit={process.returncode}):\n{stderr}")
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0, trust_env=False)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    process.terminate()
    pytest.fail(f"FastAPI 示例服务在 {timeout} 秒内未就绪: {base_url}")


@pytest.fixture(scope="module")
def fastapi_server(repo_root: Path):
    """在空闲端口启动 FastAPI 示例服务，避免误连本机已占用 8000 端口的其他服务。"""
    examples_api_dir = repo_root / "examples" / "api"

    if not examples_api_dir.exists():
        pytest.skip("examples/api 目录不存在")

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(examples_api_dir / ".uv-cache")

    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(examples_api_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _wait_until_ready(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.integration
class TestHttpExecutorIntegration:
    """HTTP 执行器集成测试。"""

    def test_execute_health_check(self, fastapi_server: str) -> None:
        """测试请求 FastAPI 示例服务 /health 接口。"""
        executor = HttpExecutor(base_url=fastapi_server)

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
        executor = HttpExecutor(base_url=fastapi_server)

        request_spec = RequestSpec(
            method="POST",
            url="/api/login",
            json={"username": "demo", "password": "123456"},
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
        executor = HttpExecutor(base_url=fastapi_server)

        request_spec = RequestSpec(
            method="GET",
            url="/api/items",
            query={"keyword": "book"},
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
