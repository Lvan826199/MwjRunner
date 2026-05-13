"""gRPC 协议适配器骨架。

首期提供接口定义和基础实现框架，完整 gRPC 支持需后续补齐。
"""

from __future__ import annotations

from mwjrunner.protocols import (
    ProtocolAdapter,
    ProtocolError,
    ProtocolRequest,
    ProtocolResult,
)


class GrpcAdapter(ProtocolAdapter):
    """gRPC 协议适配器（骨架）。"""

    @property
    def protocol_name(self) -> str:
        return "grpc"

    def execute(self, request: ProtocolRequest) -> ProtocolResult:
        """gRPC 执行（首期返回未实现提示）。"""
        return ProtocolResult(
            request=request,
            error=ProtocolError(
                error_type="not_implemented",
                message="gRPC 协议支持将在后续版本实现，当前仅提供适配器骨架",
            ),
        )
