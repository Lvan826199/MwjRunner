"""OAuth2 认证流程支持。

支持 client_credentials 和 password grant 自动获取 token。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class OAuth2Config:
    """OAuth2 认证配置。"""

    grant_type: str  # "client_credentials" 或 "password"
    token_url: str
    client_id: str
    client_secret: str = ""
    username: str = ""
    password: str = ""
    scope: str = ""


@dataclass(frozen=True)
class OAuth2Token:
    """OAuth2 Token 结果。"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    error: str | None = None


def obtain_token(config: OAuth2Config) -> OAuth2Token:
    """通过 OAuth2 流程获取 access_token。"""
    data: dict[str, str] = {
        "grant_type": config.grant_type,
        "client_id": config.client_id,
    }

    if config.client_secret:
        data["client_secret"] = config.client_secret
    if config.scope:
        data["scope"] = config.scope

    if config.grant_type == "password":
        data["username"] = config.username
        data["password"] = config.password

    try:
        transport = httpx.HTTPTransport()
        with httpx.Client(timeout=15, transport=transport) as client:
            response = client.post(config.token_url, data=data)

        if response.status_code != 200:
            return OAuth2Token(
                access_token="",
                error=f"Token 请求失败: HTTP {response.status_code} - {response.text[:200]}",
            )

        body = response.json()
        return OAuth2Token(
            access_token=body.get("access_token", ""),
            token_type=body.get("token_type", "Bearer"),
            expires_in=body.get("expires_in"),
        )
    except Exception as exc:
        return OAuth2Token(access_token="", error=f"OAuth2 请求异常: {exc}")


def parse_oauth2_config(data: dict[str, Any] | None) -> OAuth2Config | None:
    """从配置字典解析 OAuth2 配置。"""
    if not data or not isinstance(data, dict):
        return None
    if data.get("type") != "oauth2":
        return None
    return OAuth2Config(
        grant_type=data.get("grant_type", "client_credentials"),
        token_url=data.get("token_url", ""),
        client_id=data.get("client_id", ""),
        client_secret=data.get("client_secret", ""),
        username=data.get("username", ""),
        password=data.get("password", ""),
        scope=data.get("scope", ""),
    )
