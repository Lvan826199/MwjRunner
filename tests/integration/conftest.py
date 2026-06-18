"""集成测试共享夹具。"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import httpx
import pytest


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
