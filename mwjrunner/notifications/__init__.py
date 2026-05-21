"""通知扩展模块。

支持执行完成后通过钉钉、企业微信 webhook 或邮件发送通知。
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Any

import httpx

from mwjrunner.reports.model import RunResult


@dataclass(frozen=True)
class NotifyConfig:
    """通知配置。"""

    type: str  # "dingtalk", "wecom", "email"
    webhook_url: str | None = None
    # 邮件配置
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = None
    recipients: list[str] = field(default_factory=list)
    subject: str = "MwjRunner 执行报告"


@dataclass(frozen=True)
class NotifyResult:
    """通知发送结果。"""

    success: bool
    message: str = ""


def send_notification(result: RunResult, config: NotifyConfig) -> NotifyResult:
    """根据配置发送通知。"""
    if config.type == "dingtalk":
        return _send_dingtalk(result, config)
    if config.type == "wecom":
        return _send_wecom(result, config)
    if config.type == "email":
        return _send_email(result, config)
    return NotifyResult(success=False, message=f"不支持的通知类型: {config.type}")


def build_summary_text(result: RunResult) -> str:
    """构建通知摘要文本。"""
    s = result.summary
    status = "通过" if s.failed_cases == 0 and s.error_cases == 0 else "失败"
    lines = [
        f"MwjRunner 执行报告 [{status}]",
        f"运行ID: {result.run_id}",
        f"用例: {s.total_cases} 总计, {s.passed_cases} 通过, {s.failed_cases} 失败, {s.error_cases} 错误",
        f"步骤: {s.total_steps} 总计, {s.passed_steps} 通过",
        f"断言: {s.total_assertions} 总计, {s.failed_assertions} 失败",
        f"耗时: {s.elapsed_ms:.0f}ms",
    ]
    return "\n".join(lines)


def _send_dingtalk(result: RunResult, config: NotifyConfig) -> NotifyResult:
    """发送钉钉 webhook 通知。"""
    if not config.webhook_url:
        return NotifyResult(success=False, message="钉钉 webhook_url 未配置")

    text = build_summary_text(result)
    payload = {
        "msgtype": "text",
        "text": {"content": text},
    }

    return _post_webhook(config.webhook_url, payload)


def _send_wecom(result: RunResult, config: NotifyConfig) -> NotifyResult:
    """发送企业微信 webhook 通知。"""
    if not config.webhook_url:
        return NotifyResult(success=False, message="企业微信 webhook_url 未配置")

    text = build_summary_text(result)
    payload = {
        "msgtype": "text",
        "text": {"content": text},
    }

    return _post_webhook(config.webhook_url, payload)


def _send_email(result: RunResult, config: NotifyConfig) -> NotifyResult:
    """发送邮件通知。"""
    if not config.smtp_host or not config.smtp_user or not config.smtp_password:
        return NotifyResult(success=False, message="邮件 SMTP 配置不完整")
    if not config.recipients:
        return NotifyResult(success=False, message="邮件收件人列表为空")

    text = build_summary_text(result)
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = config.subject
    msg["From"] = config.smtp_user
    msg["To"] = ", ".join(config.recipients)

    try:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as server:
            server.login(config.smtp_user, config.smtp_password)
            server.sendmail(config.smtp_user, config.recipients, msg.as_string())
        return NotifyResult(success=True, message="邮件发送成功")
    except Exception as exc:
        return NotifyResult(success=False, message=f"邮件发送失败: {exc}")


def _post_webhook(url: str, payload: dict[str, Any]) -> NotifyResult:
    """发送 webhook POST 请求。"""
    try:
        transport = httpx.HTTPTransport()
        with httpx.Client(timeout=10, transport=transport) as client:
            response = client.post(url, json=payload)
        if response.status_code == 200:
            return NotifyResult(success=True, message="通知发送成功")
        return NotifyResult(success=False, message=f"webhook 返回 {response.status_code}: {response.text[:200]}")
    except Exception as exc:
        return NotifyResult(success=False, message=f"webhook 请求失败: {exc}")


def parse_notify_configs(data: list[dict[str, Any]] | None) -> list[NotifyConfig]:
    """从配置列表解析通知配置。"""
    if not data:
        return []
    configs: list[NotifyConfig] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        configs.append(NotifyConfig(
            type=item.get("type", ""),
            webhook_url=item.get("webhook_url"),
            smtp_host=item.get("smtp_host"),
            smtp_port=int(item.get("smtp_port", 465)),
            smtp_user=item.get("smtp_user"),
            smtp_password=item.get("smtp_password"),
            recipients=item.get("recipients", []),
            subject=item.get("subject", "MwjRunner 执行报告"),
        ))
    return configs
