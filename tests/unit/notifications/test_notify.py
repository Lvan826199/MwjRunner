"""通知模块单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mwjrunner.notifications import (
    NotifyConfig,
    NotifyResult,
    build_summary_text,
    parse_notify_configs,
    send_notification,
)
from mwjrunner.reports.model import RunResult, Summary


def _run_result(passed: int = 8, failed: int = 1, error: int = 1) -> RunResult:
    return RunResult(
        run_id="test-run-001",
        started_at=datetime(2026, 1, 1),
        ended_at=datetime(2026, 1, 1),
        summary=Summary(
            total_cases=passed + failed + error,
            passed_cases=passed,
            failed_cases=failed,
            error_cases=error,
            total_steps=10,
            passed_steps=8,
            total_assertions=20,
            failed_assertions=2,
            elapsed_ms=1500.0,
        ),
    )


@pytest.mark.unit
class TestBuildSummaryText:
    """摘要文本构建测试。"""

    def test_failed_status(self) -> None:
        text = build_summary_text(_run_result(failed=2))
        assert "[失败]" in text
        assert "test-run-001" in text

    def test_passed_status(self) -> None:
        text = build_summary_text(_run_result(passed=10, failed=0, error=0))
        assert "[通过]" in text

    def test_contains_stats(self) -> None:
        text = build_summary_text(_run_result())
        assert "10 总计" in text
        assert "1500ms" in text


@pytest.mark.unit
class TestSendNotification:
    """通知发送测试。"""

    def test_unsupported_type(self) -> None:
        config = NotifyConfig(type="unknown")
        result = send_notification(_run_result(), config)
        assert result.success is False
        assert "不支持" in result.message

    def test_dingtalk_missing_url(self) -> None:
        config = NotifyConfig(type="dingtalk")
        result = send_notification(_run_result(), config)
        assert result.success is False
        assert "webhook_url" in result.message

    def test_wecom_missing_url(self) -> None:
        config = NotifyConfig(type="wecom")
        result = send_notification(_run_result(), config)
        assert result.success is False
        assert "webhook_url" in result.message

    def test_email_missing_smtp(self) -> None:
        config = NotifyConfig(type="email")
        result = send_notification(_run_result(), config)
        assert result.success is False
        assert "SMTP" in result.message

    def test_email_missing_recipients(self) -> None:
        config = NotifyConfig(
            type="email",
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_password="pass",
        )
        result = send_notification(_run_result(), config)
        assert result.success is False
        assert "收件人" in result.message

    @patch("mwjrunner.notifications.httpx.Client")
    def test_dingtalk_success(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        config = NotifyConfig(type="dingtalk", webhook_url="https://oapi.dingtalk.com/robot/send?token=xxx")
        result = send_notification(_run_result(), config)
        assert result.success is True


@pytest.mark.unit
class TestParseNotifyConfigs:
    """通知配置解析测试。"""

    def test_parse_empty(self) -> None:
        assert parse_notify_configs(None) == []
        assert parse_notify_configs([]) == []

    def test_parse_dingtalk(self) -> None:
        data = [{"type": "dingtalk", "webhook_url": "https://example.com/hook"}]
        configs = parse_notify_configs(data)
        assert len(configs) == 1
        assert configs[0].type == "dingtalk"
        assert configs[0].webhook_url == "https://example.com/hook"

    def test_parse_email(self) -> None:
        data = [{"type": "email", "smtp_host": "smtp.qq.com", "smtp_port": 465, "smtp_user": "a@b.com", "smtp_password": "p", "recipients": ["c@d.com"]}]
        configs = parse_notify_configs(data)
        assert configs[0].type == "email"
        assert configs[0].recipients == ["c@d.com"]
