"""配置模型。"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuthConfig:
    """认证配置。"""

    type: str  # "bearer" 或 "basic"
    token: str | None = None  # bearer 模式使用
    username: str | None = None  # basic 模式使用
    password: str | None = None  # basic 模式使用

    def to_header_value(self) -> str | None:
        """生成 Authorization header 值。"""
        if self.type == "bearer":
            if self.token is None:
                return None
            return f"Bearer {self.token}"
        if self.type == "basic":
            if self.username is None or self.password is None:
                return None
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            return f"Basic {credentials}"
        return None


@dataclass
class ProjectConfig:
    """项目运行配置，合并后的最终结果。"""

    base_url: str | None = None
    timeout: float | None = None
    verify_ssl: bool = True
    proxy: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    report_dir: str = "reports"
    report_types: tuple[str, ...] = ("console",)
    retry: int = 0
    fail_fast: bool = False
    workers: int = 1
    timezone: str = "Asia/Shanghai"
    auth: AuthConfig | None = None
    quality_gate: dict[str, Any] | None = None
