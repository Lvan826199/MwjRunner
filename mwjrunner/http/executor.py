"""HTTP 请求执行器。"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from mwjrunner.cases.model import RequestSpec
from mwjrunner.http.model import HttpError, HttpRequest, HttpResponse, HttpResult

SENSITIVE_KEYS = ("token", "password", "cookie", "secret", "authorization")
REDACTED = "***REDACTED***"


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
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
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
                headers=self._redact_mapping(dict(response.headers)),
                cookies=self._redact_cookies(dict(response.cookies)),
                body=self._redact_response_body(response),
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
            return json.dumps(self._redact_value(request_spec.json), ensure_ascii=False)
        if request_spec.data is not None:
            redacted_data = self._redact_value(request_spec.data)
            if isinstance(redacted_data, (dict, list)):
                return json.dumps(redacted_data, ensure_ascii=False)
            return str(redacted_data)
        if request_spec.body is not None:
            return self._redact_body(request_spec.body)
        return None

    def _build_request_snapshot(self, request_spec: RequestSpec) -> HttpRequest:
        """构建请求快照(用于错误场景)。"""
        return HttpRequest(
            method=request_spec.method,
            url=self._redact_url(self._build_url(request_spec.url)),
            headers=self._redact_mapping(request_spec.headers),
            query=self._redact_mapping(request_spec.query),
            cookies=self._redact_cookies(request_spec.cookies),
            body=self._build_body(request_spec),
            timeout=request_spec.timeout or self.default_timeout,
        )

    def _redact_url(self, url: str) -> str:
        """脱敏 URL 查询参数快照。"""
        parts = urlsplit(url)
        if not parts.query:
            return url

        redacted_pairs = [
            (key, self._redact_value(value, key)) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
        redacted_query = urlencode(redacted_pairs, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted_query, parts.fragment))

    def _redact_body(self, body: str | bytes) -> str | bytes:
        """脱敏原始请求体快照。"""
        if isinstance(body, bytes):
            try:
                redacted_text = self._redact_body(body.decode("utf-8"))
            except UnicodeDecodeError:
                return body
            return redacted_text.encode("utf-8")

        try:
            redacted_json = self._redact_value(json.loads(body))
        except json.JSONDecodeError:
            return body
        return json.dumps(redacted_json, ensure_ascii=False)

    def _redact_response_body(self, response: httpx.Response) -> bytes:
        """构建脱敏后的响应体快照。"""
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            return response.content

        try:
            redacted_json = self._redact_value(response.json())
        except json.JSONDecodeError:
            return response.content
        return json.dumps(redacted_json, ensure_ascii=False).encode("utf-8")

    def _redact_mapping(self, values: dict[str, Any]) -> dict[str, Any]:
        """按字段名脱敏映射数据。"""
        return {key: self._redact_value(value, key) for key, value in values.items()}

    def _redact_cookies(self, cookies: dict[str, Any]) -> dict[str, str]:
        """脱敏 Cookie 值。"""
        return {str(key): REDACTED for key in cookies}

    def _redact_value(self, value: Any, key: str | None = None) -> Any:
        """递归脱敏敏感字段。"""
        if key is not None and self._is_sensitive_key(key):
            return REDACTED
        if isinstance(value, dict):
            return {item_key: self._redact_value(item_value, str(item_key)) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        return value

    def _is_sensitive_key(self, key: str) -> bool:
        """判断字段名是否敏感。"""
        normalized_key = key.lower().replace("-", "_")
        return any(sensitive_key in normalized_key for sensitive_key in SENSITIVE_KEYS)
