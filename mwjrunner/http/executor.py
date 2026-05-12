"""HTTP 请求执行器。"""

from __future__ import annotations

import json
import time
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from mwjrunner.cases.model import RequestSpec
from mwjrunner.http.model import HttpError, HttpRequest, HttpResponse, HttpResult
from mwjrunner.utils.masking import redact_body, redact_cookies, redact_mapping, redact_url, redact_value


class HttpExecutor:
    """HTTP 请求执行器。"""

    def __init__(self, base_url: str | None = None, default_timeout: float = 30.0) -> None:
        """初始化 HTTP 执行器。

        Args:
            base_url: 基础 URL, 用于拼接相对路径
            default_timeout: 默认超时时间(秒)
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
        request_snapshot = self._build_request_snapshot(request_spec)

        if httpx is None:
            return HttpResult(
                request=request_snapshot,
                error=HttpError(
                    error_type="dependency_missing",
                    message="httpx 未安装, 请运行 uv add httpx",
                    request=request_snapshot,
                ),
            )

        url = self._build_url(request_spec.url)
        timeout = request_spec.timeout or self.default_timeout

        try:
            start_time = time.perf_counter()
            transport = httpx.HTTPTransport()
            with httpx.Client(
                timeout=timeout, follow_redirects=True, transport=transport
            ) as client:
                response = client.request(
                    method=request_spec.method,
                    url=url,
                    headers=request_spec.headers,
                    params=request_spec.query,
                    cookies=request_spec.cookies,
                    json=request_spec.json,
                    data=request_spec.data,
                    content=request_spec.body,
                )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            response_snapshot = HttpResponse(
                status_code=response.status_code,
                headers=redact_mapping(dict(response.headers)),
                cookies=redact_cookies(dict(response.cookies)),
                body=self._redact_response_body(response),
                elapsed_ms=elapsed_ms,
                raw_body=response.content,
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
            return json.dumps(redact_value(request_spec.json), ensure_ascii=False)
        if request_spec.data is not None:
            redacted_data = redact_value(request_spec.data)
            if isinstance(redacted_data, (dict, list)):
                return json.dumps(redacted_data, ensure_ascii=False)
            return str(redacted_data)
        if request_spec.body is not None:
            return redact_body(request_spec.body)
        return None

    def _build_request_snapshot(self, request_spec: RequestSpec) -> HttpRequest:
        """构建请求快照(用于错误场景)。"""
        return HttpRequest(
            method=request_spec.method,
            url=redact_url(self._build_url(request_spec.url)),
            headers=redact_mapping(request_spec.headers),
            query=redact_mapping(request_spec.query),
            cookies=redact_cookies(request_spec.cookies),
            body=self._build_body(request_spec),
            timeout=request_spec.timeout or self.default_timeout,
        )

    def _redact_mapping(self, values: dict[str, object]) -> dict[str, object]:
        """按字段名脱敏映射数据。"""
        return redact_mapping(values)

    def _redact_response_body(self, response: httpx.Response) -> bytes:
        """构建脱敏后的响应体快照。"""
        redacted_body = redact_body(response.content)
        if isinstance(redacted_body, bytes):
            return redacted_body
        return redacted_body.encode("utf-8")
