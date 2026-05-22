"""通知集成模块 — 支持钉钉、飞书、Slack、邮件。"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.users import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/notifications", tags=["通知集成"])


class NotifyPayload(BaseModel):
    channel: str  # dingtalk, feishu, slack, email
    webhook_url: str = ""
    # email 专用
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    to_emails: list[str] = []
    # 内容
    title: str = ""
    content: str = ""


class NotifyTestRequest(BaseModel):
    channel: str
    webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    to_emails: list[str] = []


@router.post("/send")
async def send_notification(payload: NotifyPayload, _user: User = Depends(get_current_user)):
    """发送通知。"""
    return await dispatch_notification(payload)


@router.post("/test")
async def test_notification(data: NotifyTestRequest, _user: User = Depends(get_current_user)):
    """测试通知通道连通性。"""
    payload = NotifyPayload(
        channel=data.channel,
        webhook_url=data.webhook_url,
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
        smtp_user=data.smtp_user,
        smtp_pass=data.smtp_pass,
        to_emails=data.to_emails,
        title="[MwjRunner] 通知测试",
        content="这是一条测试通知，如果您收到此消息说明通知通道配置正确。",
    )
    return await dispatch_notification(payload)


@router.get("/channels")
async def list_channels(_user: User = Depends(get_current_user)):
    """获取支持的通知通道列表。"""
    return {
        "channels": [
            {"id": "dingtalk", "name": "钉钉机器人", "config_fields": ["webhook_url"]},
            {"id": "feishu", "name": "飞书机器人", "config_fields": ["webhook_url"]},
            {"id": "slack", "name": "Slack Webhook", "config_fields": ["webhook_url"]},
            {
                "id": "email",
                "name": "邮件",
                "config_fields": ["smtp_host", "smtp_port", "smtp_user", "smtp_pass", "to_emails"],
            },
        ]
    }


async def dispatch_notification(payload: NotifyPayload) -> dict:
    """分发通知到对应通道。"""
    try:
        if payload.channel == "dingtalk":
            return await _send_dingtalk(payload)
        if payload.channel == "feishu":
            return await _send_feishu(payload)
        if payload.channel == "slack":
            return await _send_slack(payload)
        if payload.channel == "email":
            return await _send_email(payload)
        return {"success": False, "error": f"不支持的通道: {payload.channel}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _send_dingtalk(payload: NotifyPayload) -> dict:
    """发送钉钉机器人消息。"""
    body = {
        "msgtype": "markdown",
        "markdown": {
            "title": payload.title,
            "text": f"### {payload.title}\n\n{payload.content}",
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(payload.webhook_url, json=body, timeout=10)
        result = resp.json()
        if result.get("errcode", 0) == 0:
            return {"success": True}
        return {"success": False, "error": result.get("errmsg", "未知错误")}


async def _send_feishu(payload: NotifyPayload) -> dict:
    """发送飞书机器人消息。"""
    body = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": payload.title}},
            "elements": [
                {"tag": "markdown", "content": payload.content},
            ],
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(payload.webhook_url, json=body, timeout=10)
        result = resp.json()
        if result.get("code", 0) == 0:
            return {"success": True}
        return {"success": False, "error": result.get("msg", "未知错误")}


async def _send_slack(payload: NotifyPayload) -> dict:
    """发送 Slack Webhook 消息。"""
    body = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": payload.title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": payload.content}},
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(payload.webhook_url, json=body, timeout=10)
        if resp.status_code == 200:
            return {"success": True}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}


async def _send_email(payload: NotifyPayload) -> dict:
    """发送邮件通知。"""
    if not payload.to_emails:
        return {"success": False, "error": "收件人为空"}

    msg = MIMEText(payload.content, "html", "utf-8")
    msg["Subject"] = payload.title
    msg["From"] = payload.smtp_user
    msg["To"] = ", ".join(payload.to_emails)

    try:
        if payload.smtp_port == 465:
            server = smtplib.SMTP_SSL(payload.smtp_host, payload.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(payload.smtp_host, payload.smtp_port, timeout=10)
            server.starttls()
        server.login(payload.smtp_user, payload.smtp_pass)
        server.sendmail(payload.smtp_user, payload.to_emails, msg.as_string())
        server.quit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def notify_pipeline_result(pipeline_name: str, status: str, webhook_url: str, channel: str = "dingtalk", **extra):
    """Pipeline 执行完成后自动通知（内部调用）。"""
    emoji = "✅" if status == "passed" else "❌"
    content = f"{emoji} **{pipeline_name}** 执行{status}\n\n"
    if extra.get("commit_sha"):
        content += f"- Commit: `{extra['commit_sha']}`\n"
    if extra.get("branch"):
        content += f"- Branch: `{extra['branch']}`\n"
    if extra.get("passed_cases") is not None:
        content += f"- 通过: {extra['passed_cases']}, 失败: {extra.get('failed_cases', 0)}\n"

    payload = NotifyPayload(
        channel=channel,
        webhook_url=webhook_url,
        title=f"[MwjRunner] {pipeline_name} - {status}",
        content=content,
    )
    await dispatch_notification(payload)
