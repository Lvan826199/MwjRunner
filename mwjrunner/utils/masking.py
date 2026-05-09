"""统一敏感信息脱敏工具。"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    re.compile(rf"(?i)({key.replace('_', '[-_]?')}\s*[:=]\s*)(Bearer\s+[^\s,;&]+|[^\s,;&]+)") for key in SENSITIVE_KEYS
)


def is_sensitive_key(key: str) -> bool:
    """判断字段名是否敏感。"""
    normalized_key = key.lower().replace("-", "_")
    return any(sensitive_key in normalized_key for sensitive_key in SENSITIVE_KEYS)


def redact_text(text: str) -> str:
    """脱敏字符串中的常见 key=value 和 key: value 片段。"""
    redacted = text
    for pattern in _TEXT_PATTERNS:
        redacted = pattern.sub(rf"\1{REDACTED}", redacted)
    return redacted


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


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """按字段名脱敏映射数据。"""
    return {key: redact_value(value, str(key)) for key, value in values.items()}


def redact_cookies(cookies: Mapping[str, Any]) -> dict[str, str]:
    """脱敏 Cookie 值。"""
    return {str(key): REDACTED for key in cookies}


def redact_url(url: str) -> str:
    """脱敏 URL 查询参数。"""
    parts = urlsplit(url)
    if not parts.query:
        return url

    redacted_pairs = [(key, redact_value(value, key)) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    redacted_query = urlencode(redacted_pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted_query, parts.fragment))


def redact_body(body: str | bytes) -> str | bytes:
    """脱敏 JSON 或文本请求/响应体。"""
    if isinstance(body, bytes):
        try:
            redacted_text = redact_body(body.decode("utf-8"))
        except UnicodeDecodeError:
            return body
        return redacted_text.encode("utf-8")

    try:
        redacted_json = redact_value(json.loads(body))
    except json.JSONDecodeError:
        return redact_text(body)
    return json.dumps(redacted_json, ensure_ascii=False)
