"""WebSocket 协议适配器。

基于 websockets 库实现 WebSocket 连接、发送和接收。
"""

from __future__ import annotations

import json
import time

from mwjrunner.protocols import (
    ProtocolAdapter,
    ProtocolError,
    ProtocolRequest,
    ProtocolResponse,
    ProtocolResult,
)


class WebSocketAdapter(ProtocolAdapter):
    """WebSocket 协议适配器。"""

    @property
    def protocol_name(self) -> str:
        return "websocket"

    def execute(self, request: ProtocolRequest) -> ProtocolResult:
        """执行 WebSocket 请求。

        支持的 action:
        - send_recv: 连接、发送消息、接收响应、关闭
        - send: 连接、发送消息、关闭（不等待响应）
        """
        try:
            import websockets.sync.client as ws_client  # noqa: PLC0415
        except ImportError:
            return ProtocolResult(
                request=request,
                error=ProtocolError(
                    error_type="dependency_missing",
                    message="websockets 未安装，请运行 uv add websockets",
                ),
            )

        action = request.action or "send_recv"
        timeout = request.options.get("timeout", 10)

        try:
            start = time.perf_counter()

            with ws_client.connect(
                request.target,
                open_timeout=timeout,
                additional_headers=request.headers or None,
            ) as conn:
                # 发送
                if request.payload is not None:
                    message = request.payload if isinstance(request.payload, str) else json.dumps(request.payload)
                    conn.send(message)

                # 接收
                received = None
                if action == "send_recv":
                    received = conn.recv(timeout=timeout)

            elapsed = (time.perf_counter() - start) * 1000

            # 尝试解析 JSON
            parsed_payload = received
            if isinstance(received, str):
                try:
                    parsed_payload = json.loads(received)
                except json.JSONDecodeError:
                    parsed_payload = received

            return ProtocolResult(
                request=request,
                response=ProtocolResponse(
                    status="ok",
                    payload=parsed_payload,
                    elapsed_ms=elapsed,
                ),
            )

        except Exception as exc:
            return ProtocolResult(
                request=request,
                error=ProtocolError(
                    error_type="websocket_error",
                    message=f"WebSocket 执行失败: {exc}",
                ),
            )
