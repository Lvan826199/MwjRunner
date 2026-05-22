"""WebSocket 实时推送模块。"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token

router = APIRouter()


class ConnectionManager:
    """管理 WebSocket 连接。"""

    def __init__(self):
        # team_id -> set of connections
        self._connections: dict[int | None, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, team_id: int | None):
        await websocket.accept()
        async with self._lock:
            if team_id not in self._connections:
                self._connections[team_id] = set()
            self._connections[team_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, team_id: int | None):
        async with self._lock:
            if team_id in self._connections:
                self._connections[team_id].discard(websocket)
                if not self._connections[team_id]:
                    del self._connections[team_id]

    async def broadcast(self, event: str, data: Any, team_id: int | None = None):
        """广播消息。team_id=None 表示全局广播。"""
        message = json.dumps({"event": event, "data": data}, default=str)
        targets: set[WebSocket] = set()

        async with self._lock:
            if team_id is None:
                # 广播给所有连接
                for conns in self._connections.values():
                    targets.update(conns)
            else:
                # 广播给指定团队 + admin（team_id=None 的连接）
                targets.update(self._connections.get(team_id, set()))
                targets.update(self._connections.get(None, set()))

        for ws in targets:
            with contextlib.suppress(Exception):
                await ws.send_text(message)

    async def send_personal(self, websocket: WebSocket, event: str, data: Any):
        message = json.dumps({"event": event, "data": data}, default=str)
        with contextlib.suppress(Exception):
            await websocket.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 入口。通过 query param token 认证。"""
    token = websocket.query_params.get("token", "")
    team_id: int | None = None

    try:
        payload = decode_access_token(token)
        team_id = payload.get("team_id")
        user_role = payload.get("role", "")
        # admin 用 team_id=None 表示可接收所有消息
        if user_role == "admin":
            team_id = None
    except (jwt.InvalidTokenError, Exception):
        await websocket.close(code=4001, reason="认证失败")
        return

    await manager.connect(websocket, team_id)
    try:
        while True:
            # 保持连接，接收 ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, team_id)


async def notify_execution_update(execution_id: int, status: str, team_id: int | None, **extra):
    """通知执行状态变更。"""
    await manager.broadcast(
        "execution:update",
        {"id": execution_id, "status": status, **extra},
        team_id=team_id,
    )


async def notify_execution_created(execution_id: int, case_name: str, team_id: int | None):
    """通知新执行创建。"""
    await manager.broadcast(
        "execution:created",
        {"id": execution_id, "case_name": case_name},
        team_id=team_id,
    )
