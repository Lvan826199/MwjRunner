"""统一脱敏工具测试。"""

from __future__ import annotations

from mwjrunner.utils.masking import (
    REDACTED,
    is_sensitive_key,
    redact_body,
    redact_cookies,
    redact_mapping,
    redact_text,
    redact_url,
    redact_value,
)


def test_is_sensitive_key_matches_common_sensitive_names() -> None:
    assert is_sensitive_key("Authorization") is True
    assert is_sensitive_key("access_token") is True
    assert is_sensitive_key("refresh-token") is True
    assert is_sensitive_key("client_secret") is True
    assert is_sensitive_key("set-cookie") is True
    assert is_sensitive_key("username") is False


def test_redact_value_masks_nested_values() -> None:
    data = {
        "username": "admin",
        "password": "raw-password",
        "nested": {"access_token": "raw-access-token"},
        "items": [{"refresh_token": "raw-refresh-token"}],
        "tuple_items": ({"secret": "raw-secret"},),
    }

    result = redact_value(data)

    assert result["username"] == "admin"
    assert result["password"] == REDACTED
    assert result["nested"]["access_token"] == REDACTED
    assert result["items"][0]["refresh_token"] == REDACTED
    assert result["tuple_items"][0]["secret"] == REDACTED


def test_redact_text_masks_key_value_fragments() -> None:
    message = (
        "token=raw-token password: raw-password Authorization: Bearer raw-auth client_secret=raw-secret user=admin"
    )

    result = redact_text(message)

    assert "raw-token" not in result
    assert "raw-password" not in result
    assert "raw-auth" not in result
    assert "raw-secret" not in result
    assert "user=admin" in result
    assert result.count(REDACTED) == 4


def test_redact_mapping_masks_sensitive_keys() -> None:
    result = redact_mapping({"Authorization": "Bearer raw-token", "X-Trace-Id": "trace-001"})

    assert result["Authorization"] == REDACTED
    assert result["X-Trace-Id"] == "trace-001"


def test_redact_cookies_masks_all_cookie_values() -> None:
    result = redact_cookies({"session": "raw-cookie", "trace": "raw-trace"})

    assert result == {"session": REDACTED, "trace": REDACTED}


def test_redact_url_masks_sensitive_query_values() -> None:
    result = redact_url("https://example.com/api?token=raw-token&keyword=admin")

    assert "raw-token" not in result
    assert "token=%2A%2A%2AREDACTED%2A%2A%2A" in result
    assert "keyword=admin" in result


def test_redact_body_masks_json_body() -> None:
    result = redact_body('{"password": "raw-password", "username": "admin"}')

    assert "raw-password" not in result
    assert "admin" in result
    assert REDACTED in result


def test_redact_body_masks_text_body() -> None:
    result = redact_body("token=raw-token&password=raw-password&username=admin")

    assert "raw-token" not in result
    assert "raw-password" not in result
    assert "username=admin" in result


def test_redact_body_masks_utf8_bytes() -> None:
    result = redact_body(b"authorization=Bearer raw-auth")

    assert isinstance(result, bytes)
    assert b"raw-auth" not in result
    assert REDACTED.encode("utf-8") in result


def test_redact_text_masks_json_quoted_keys() -> None:
    """JSON 引号键场景（"token": "abc"）必须被文本兜底脱敏覆盖。"""
    result = redact_text('{"token": "abc123", "password": "hunter2", "name": "demo"}')

    assert "abc123" not in result
    assert "hunter2" not in result
    assert '"name": "demo"' in result
    assert REDACTED in result


def test_redact_text_masks_plain_key_value() -> None:
    result = redact_text("access_token: secret-value, user: demo")

    assert "secret-value" not in result
    assert "user: demo" in result


def test_redact_url_masks_userinfo_password() -> None:
    result = redact_url("https://user:s3cret@host:8443/path?a=1")

    assert "s3cret" not in result
    assert "user" in result
    assert "host:8443" in result
    assert "a=1" in result
