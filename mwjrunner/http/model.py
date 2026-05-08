"""HTTP 请求执行模块。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HttpRequest:
    """HTTP 请求快照。"""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: str | bytes | None = None
    timeout: float | None = None


@dataclass(frozen=True)
class HttpResponse:
    """HTTP 响应快照。"""

    status_code: int
    headers: dict[str, str]
    cookies: dict[str, str]
    body: bytes
    elapsed_ms: float

    @property
    def text(self) -> str:
        """获取响应文本内容。"""
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        """解析响应为 JSON。"""
        return json.loads(self.text)


@dataclass(frozen=True)
class HttpError:
    """HTTP 请求错误。"""

    error_type: str
    message: str
    request: HttpRequest


@dataclass(frozen=True)
class HttpResult:
    """HTTP 请求执行结果。"""

    request: HttpRequest
    response: HttpResponse | None = None
    error: HttpError | None = None

    @property
    def is_success(self) -> bool:
        """请求是否成功。"""
        return self.response is not None and self.error is None
