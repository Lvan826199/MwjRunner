"""HTTP 请求执行器。"""

from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path
from typing import IO

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from mwjrunner.cases.model import RequestSpec
from mwjrunner.http.model import HttpError, HttpRequest, HttpResponse, HttpResult
from mwjrunner.utils.masking import redact_body, redact_cookies, redact_mapping, redact_url, redact_value


class HttpExecutor:
    """HTTP 请求执行器。"""

    def __init__(
        self,
        base_url: str | None = None,
        default_timeout: float = 30.0,
        default_headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
        proxy: str | None = None,
    ) -> None:
        """初始化 HTTP 执行器。

        Args:
            base_url: 基础 URL, 用于拼接相对路径
            default_timeout: 默认超时时间(秒)
            default_headers: 全局默认请求头（请求级 header 优先）
            verify_ssl: 是否校验 SSL 证书
            proxy: 代理地址（如 http://127.0.0.1:7890）
        """
        self.base_url = base_url
        self.default_timeout = default_timeout
        self.default_headers = dict(default_headers or {})
        self.verify_ssl = verify_ssl
        self.proxy = proxy

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
        timeout = request_spec.timeout if request_spec.timeout is not None else self.default_timeout
        request_headers = self._merge_headers(request_spec)

        try:
            # 准备文件上传
            files_param = None
            opened_files = []
            if request_spec.files:
                files_param, opened_files = self._prepare_files(request_spec.files)

            # 显式构造 transport 以绕过系统代理；代理仅在配置中显式声明时启用
            transport = httpx.HTTPTransport(verify=self.verify_ssl, proxy=self.proxy)

            # 如果 body 是 dict/list，序列化为 JSON 字符串
            body_content = request_spec.body
            if body_content is not None and isinstance(body_content, (dict, list)):
                body_content = json.dumps(body_content, ensure_ascii=False)
                if not any(key.lower() == "content-type" for key in request_headers):
                    request_headers["Content-Type"] = "application/json"

            try:
                with httpx.Client(
                    timeout=timeout,
                    follow_redirects=True,
                    transport=transport,
                    cookies=request_spec.cookies,
                ) as client:
                    start_time = time.perf_counter()
                    response = client.request(
                        method=request_spec.method,
                        url=url,
                        headers=request_headers,
                        params=request_spec.query,
                        json=request_spec.json if not files_param else None,
                        data=request_spec.data,
                        content=body_content if not files_param else None,
                        files=files_param,
                    )
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
            finally:
                for f in opened_files:
                    f.close()

            # 快照保留原始 headers/cookies 供断言和提取使用，脱敏统一在报告序列化层执行
            response_snapshot = HttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=self._collect_cookies(response),
                body=self._redact_response_body(response),
                elapsed_ms=elapsed_ms,
                raw_body=response.content,
                encoding=response.encoding,
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
        """构建完整 URL。

        显式拼接 base_url 与相对路径，保留 base_url 中的路径前缀
        （如 base_url 为 http://host/api/v1 时，/users 拼为 http://host/api/v1/users）。
        """
        if self.base_url and not url.startswith(("http://", "https://")):
            return f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        return url

    def _merge_headers(self, request_spec: RequestSpec) -> dict[str, str]:
        """合并全局默认 headers 与请求级 headers，请求级优先（大小写不敏感）。"""
        merged = dict(self.default_headers)
        if request_spec.headers:
            request_keys = {key.lower() for key in request_spec.headers}
            merged = {key: value for key, value in merged.items() if key.lower() not in request_keys}
            merged.update(request_spec.headers)
        return merged

    @staticmethod
    def _collect_cookies(response: httpx.Response) -> dict[str, str]:
        """采集响应 cookies；同名跨域 cookie 冲突时逐个取值兜底。"""
        try:
            return dict(response.cookies)
        except Exception:
            cookies: dict[str, str] = {}
            for name in response.cookies:
                try:
                    cookies[name] = response.cookies[name]
                except Exception:
                    continue
            return cookies

    def _prepare_files(
        self, file_specs: list[dict[str, str]]
    ) -> tuple[list[tuple[str, tuple[str, IO[bytes], str]]], list[IO[bytes]]]:
        """准备文件上传参数。

        Args:
            file_specs: 文件配置列表，每项包含 field_name 和 path，可选 content_type

        Returns:
            (httpx files 参数, 需要关闭的文件句柄列表)
        """
        files_param: list[tuple[str, tuple[str, IO[bytes], str]]] = []
        opened: list[IO[bytes]] = []

        try:
            for spec in file_specs:
                field_name = spec.get("field", spec.get("field_name", "file"))
                file_path_str = spec.get("path", "")
                content_type = spec.get("content_type", "")

                file_path = Path(file_path_str)
                if not file_path.is_file():
                    raise FileNotFoundError(f"上传文件不存在: {file_path}")

                if not content_type:
                    guessed, _ = mimetypes.guess_type(str(file_path))
                    content_type = guessed or "application/octet-stream"

                fh = file_path.open("rb")
                opened.append(fh)
                files_param.append((field_name, (file_path.name, fh, content_type)))
        except Exception:
            for fh in opened:
                fh.close()
            raise

        return files_param, opened

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
            # 如果 body 是 dict/list，先序列化再脱敏
            if isinstance(request_spec.body, (dict, list)):
                return json.dumps(redact_value(request_spec.body), ensure_ascii=False)
            return redact_body(request_spec.body)
        return None

    def _build_request_snapshot(self, request_spec: RequestSpec) -> HttpRequest:
        """构建请求快照(用于错误场景)。"""
        return HttpRequest(
            method=request_spec.method,
            url=redact_url(self._build_url(request_spec.url)),
            headers=redact_mapping(self._merge_headers(request_spec)),
            query=redact_mapping(request_spec.query),
            cookies=redact_cookies(request_spec.cookies),
            body=self._build_body(request_spec),
            timeout=request_spec.timeout if request_spec.timeout is not None else self.default_timeout,
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
