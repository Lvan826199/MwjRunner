"""协议适配器基类和注册表。

MwjRunner 通过协议适配器支持不同通信协议（HTTP、WebSocket、gRPC 等）。
每个协议适配器负责执行请求并返回统一的结果模型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProtocolRequest:
    """协议无关的请求描述。"""

    protocol: str
    action: str  # "send", "connect", "call" 等
    target: str  # URL, endpoint, service method
    headers: dict[str, str] = field(default_factory=dict)
    payload: Any = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtocolResponse:
    """协议无关的响应结果。"""

    status: str  # "ok", "error"
    payload: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtocolError:
    """协议执行错误。"""

    error_type: str
    message: str


@dataclass(frozen=True)
class ProtocolResult:
    """协议执行结果。"""

    request: ProtocolRequest
    response: ProtocolResponse | None = None
    error: ProtocolError | None = None

    @property
    def is_success(self) -> bool:
        # 部分适配器将协议级错误包装为 status="error" 的响应（error 为 None），需一并判定
        return self.response is not None and self.error is None and self.response.status != "error"


class ProtocolAdapter(ABC):
    """协议适配器基类。"""

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """协议名称标识。"""

    @abstractmethod
    def execute(self, request: ProtocolRequest) -> ProtocolResult:
        """执行协议请求。"""


class ProtocolRegistry:
    """协议适配器注册表。"""

    def __init__(self) -> None:
        self._adapters: dict[str, ProtocolAdapter] = {}

    def register(self, adapter: ProtocolAdapter) -> None:
        self._adapters[adapter.protocol_name] = adapter

    def get(self, protocol: str) -> ProtocolAdapter | None:
        return self._adapters.get(protocol)

    def supported_protocols(self) -> list[str]:
        return list(self._adapters.keys())
