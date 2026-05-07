"""HTTP 请求执行器。"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from mwjrunner.cases.model import RequestSpec
from mwjrunner.http.model import HttpError, HttpRequest, HttpResponse, HttpResult


class HttpExecutor:
    """HTTP 请求执行器。"""

    def __init__(self, base_url: str | None = None, default_timeout: float = 30.0) -> None:
        """初始化 HTTP 执行器。

        Args:
            base_url: 基础 URL，用于拼接相对路径
            default_timeout: 默认超时时间（秒）
        """
        self.base_url = base_url
        self.default_timeout = default_timeout

    def execute(self, request_spec: RequestSpec) -> HttpResult:
        """执行 HTTP 请求。

        Args:
            request_spec: 请求规格

        Returns:
            HTTP 请求执行结果
        """
        if httpx is None:
            return HttpResult(
                request=self._build_request_snapshot(request_spec),
                error=HttpError(
                    error_type="dependency_missing",
                    message="httpx 未安装，请运行 uv add httpx",
                    request=self._build_request_snapshot(request_spec),
                ),
            )

        # 构建完整 URL
        url = self._build_url(request_spec.url)

        # 构建请求快照
        request_snapshot = HttpRequest(
            method=request_spec.method,
            url=url,
            headers=request_spec.headers,
            query=request_spec.query,
            cookies=request_spec.cookies,
            body=self._build_body(request_spec),
            timeout=request_spec.timeout or self.default_timeout,
        )

        # 执行请求
        try:
            start_time = time.perf_counter()
            response = httpx.request(
                method=request_spec.method,
                url=url,
                headers=request_spec.headers,
                params=request_spec.query,
                cookies=request_spec.cookies,
                json=request_spec.json,
                data=request_spec.data,
                content=request_spec.body,
                timeout=request_spec.timeout or self.default_timeout,
                follow_redirects=True,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 构建响应快照
            response_snapshot = HttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                body=response.content,
                elapsed_ms=elapsed_ms,
            )

            return HttpResult(request=request_snapshot, response=response_snapshot)

        except httpx.TimeoutException as exc:
            return HttpResult(
                request=request_snapshot,
                error=HttpError(
                    error_type="timeout",
                    message=f"请求超时: {exc}",
                    request=request_snapshot,
                ),
            )
        except httpx.NetworkError as exc:
            return HttpResult(
                request=request_snapshot,
                error=HttpError(
                    error_type="network_error",
                    message=f"网络错误: {exc}",
                    request=request_snapshot,
                ),
            )
        except httpx.HTTPError as exc:
            return HttpResult(
                request=request_snapshot,
                error=HttpError(
                    error_type="http_error",
                    message=f"HTTP 错误: {exc}",
                    request=request_snapshot,
                ),
            )
        except Exception as exc:
            return HttpResult(
                request=request_snapshot,
                error=HttpError(
                    error_type="unknown_error",
                    message=f"未知错误: {exc}",
                    request=request_snapshot,
                ),
            )

    def _build_url(self, url: str) -> str:
        """构建完整 URL。"""
        if self.base_url and not url.startswith(("http://", "https://")):
            return urljoin(self.base_url, url)
        return url

    def _build_body(self, request_spec: RequestSpec) -> str | bytes | None:
        """构建请求体快照。"""
        if request_spec.json is not None:
            import json

            return json.dumps(request_spec.json, ensure_ascii=False)
        if request_spec.data is not None:
            return str(request_spec.data)
        if request_spec.body is not None:
            return request_spec.body
        return None

    def _build_request_snapshot(self, request_spec: RequestSpec) -> HttpRequest:
        """构建请求快照（用于错误场景）。"""
        return HttpRequest(
            method=request_spec.method,
            url=self._build_url(request_spec.url),
            headers=request_spec.headers,
            query=request_spec.query,
            cookies=request_spec.cookies,
            body=self._build_body(request_spec),
            timeout=request_spec.timeout or self.default_timeout,
        )
