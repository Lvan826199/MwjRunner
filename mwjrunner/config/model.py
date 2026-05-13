"""配置模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
