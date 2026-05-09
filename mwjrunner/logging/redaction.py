"""日志敏感信息脱敏。"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"
SENSITIVE_KEYS = (
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "cookie",
    "set_cookie",
)

_TEXT_PATTERNS = tuple(
    re.compile(rf"(?i)({key.replace('_', '[-_]?')}\s*[:=]\s*)(Bearer\s+[^\s,;]+|[^\s,;]+)") for key in SENSITIVE_KEYS
)


def redact_value(value: Any, key: str | None = None) -> Any:
    """递归脱敏常见敏感字段。"""
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {item_key: redact_value(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    """脱敏字符串中的常见 key=value 和 key: value 片段。"""
    redacted = text
    for pattern in _TEXT_PATTERNS:
        redacted = pattern.sub(rf"\1{REDACTED}", redacted)
    return redacted


def is_sensitive_key(key: str) -> bool:
    """判断字段名是否敏感。"""
    normalized_key = key.lower().replace("-", "_")
    return any(sensitive_key in normalized_key for sensitive_key in SENSITIVE_KEYS)
