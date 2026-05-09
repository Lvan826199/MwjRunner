"""日志配置。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


@dataclass(frozen=True)
class LogConfig:
    """MwjRunner 日志配置。"""

    level: str = "INFO"
    run_id: str = "-"
    log_file: Path | None = None
    console: bool = True


def normalize_log_level(level: str) -> int:
    """转换日志级别名称为 logging 标准级别。"""
    normalized_level = level.upper()
    if normalized_level not in _SUPPORTED_LEVELS:
        supported = ", ".join(_SUPPORTED_LEVELS)
        raise ValueError(f"不支持的日志级别: {level}, 支持的级别: {supported}")
    return _SUPPORTED_LEVELS[normalized_level]
