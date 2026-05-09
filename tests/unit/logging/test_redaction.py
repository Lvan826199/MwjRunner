"""日志脱敏测试。"""

from __future__ import annotations

from mwjrunner.logging.redaction import REDACTED, redact_text, redact_value


def test_redact_value_masks_sensitive_mapping_keys() -> None:
    data = {
        "Authorization": "Bearer raw-token",
        "username": "admin",
        "password": "raw-password",
        "nested": {
            "access_token": "raw-access-token",
            "profile": {"name": "admin", "secret": "raw-secret"},
        },
        "items": [
            {"refresh_token": "raw-refresh-token"},
            {"name": "public"},
        ],
    }

    result = redact_value(data)

    assert result["Authorization"] == REDACTED
    assert result["username"] == "admin"
    assert result["password"] == REDACTED
    assert result["nested"]["access_token"] == REDACTED
    assert result["nested"]["profile"]["name"] == "admin"
    assert result["nested"]["profile"]["secret"] == REDACTED
    assert result["items"][0]["refresh_token"] == REDACTED
    assert result["items"][1]["name"] == "public"


def test_redact_value_masks_cookie_values() -> None:
    data = {
        "Cookie": "session=raw-cookie",
        "set-cookie": "session=raw-set-cookie",
        "x-trace-id": "trace-001",
    }

    result = redact_value(data)

    assert result["Cookie"] == REDACTED
    assert result["set-cookie"] == REDACTED
    assert result["x-trace-id"] == "trace-001"


def test_redact_text_masks_key_value_patterns() -> None:
    message = (
        "login token=raw-token password: raw-password "
        "authorization=Bearer raw-auth cookie: session=raw-cookie user=admin"
    )

    result = redact_text(message)

    assert "raw-token" not in result
    assert "raw-password" not in result
    assert "raw-auth" not in result
    assert "raw-cookie" not in result
    assert "user=admin" in result
    assert result.count(REDACTED) == 4
