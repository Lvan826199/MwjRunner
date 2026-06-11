"""报告结果模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.http.model import HttpRequest, HttpResponse
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
from mwjrunner.variables.engine import ExtractResult


@dataclass(frozen=True)
class Summary:
    """运行摘要统计。"""

    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    skipped_cases: int = 0
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    error_steps: int = 0
    total_assertions: int = 0
    failed_assertions: int = 0
    total_errors: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "error_cases": self.error_cases,
            "skipped_cases": self.skipped_cases,
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "error_steps": self.error_steps,
            "total_assertions": self.total_assertions,
            "failed_assertions": self.failed_assertions,
            "total_errors": self.total_errors,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class StepResult:
    """单个步骤报告结果。"""

    name: str
    status: str
    request: HttpRequest | None = None
    response: HttpResponse | None = None
    assertions: list[AssertionResult] = field(default_factory=list)
    extracts: list[ExtractResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "name": self.name,
            "status": self.status,
            "request": _request_to_dict(self.request),
            "response": _response_to_dict(self.response),
            "assertions": [_assertion_to_dict(assertion) for assertion in self.assertions],
            "extracts": [_extract_to_dict(extract) for extract in self.extracts],
            "errors": [redact_text(error) for error in self.errors],
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class CaseResult:
    """单个用例报告结果。"""

    name: str
    status: str
    source_file: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "name": self.name,
            "source_file": self.source_file,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "errors": [redact_text(error) for error in self.errors],
        }


@dataclass(frozen=True)
class RunResult:
    """一次运行的报告结果。"""

    run_id: str
    started_at: datetime
    ended_at: datetime | None
    summary: Summary
    cases: list[CaseResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at is not None else None,
            "summary": self.summary.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "errors": [redact_text(error) for error in self.errors],
        }


def _request_to_dict(request: HttpRequest | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return {
        "method": request.method,
        "url": redact_url(request.url),
        "headers": redact_mapping(request.headers),
        "query": redact_mapping(request.query),
        "cookies": redact_cookies(request.cookies),
        "body": _body_to_json_value(redact_body(request.body)) if request.body is not None else None,
        "timeout": request.timeout,
    }


def _response_to_dict(response: HttpResponse | None) -> dict[str, Any] | None:
    if response is None:
        return None
    return {
        "status_code": response.status_code,
        "headers": redact_mapping(response.headers),
        "cookies": redact_cookies(response.cookies),
        "body": _body_to_json_value(redact_body(response.body)),
        "elapsed_ms": response.elapsed_ms,
    }


def _assertion_to_dict(assertion: AssertionResult) -> dict[str, Any]:
    sensitive_result = _has_sensitive_part(assertion.path, assertion.target)
    return {
        "type": assertion.type,
        "passed": assertion.passed,
        "expected": REDACTED if sensitive_result else _redact_field_value(assertion.expected),
        "actual": REDACTED if sensitive_result else _redact_field_value(assertion.actual),
        "path": assertion.path,
        "target": assertion.target,
        "mode": assertion.mode,
        "message": _redact_assertion_message(assertion, sensitive_result),
    }


def _redact_field_value(value: Any) -> Any:
    """脱敏断言的 expected/actual 值；字符串可能内嵌 JSON 响应体，走 redact_body。"""
    if isinstance(value, str):
        redacted = redact_body(value)
        return redacted if isinstance(redacted, str) else value
    return redact_value(value)


def _redact_assertion_message(assertion: AssertionResult, sensitive_result: bool) -> str:
    """脱敏断言 message；path/target 敏感时同时清除内嵌的 expected/actual 原始值。"""
    message = redact_text(assertion.message)
    if sensitive_result:
        for raw in (assertion.actual, assertion.expected):
            raw_text = str(raw) if raw is not None else ""
            if raw_text and raw_text in message:
                message = message.replace(raw_text, REDACTED)
    return message


def _extract_to_dict(extract: ExtractResult) -> dict[str, Any]:
    sensitive_result = _has_sensitive_part(extract.name, extract.path)
    return {
        "name": extract.name,
        "type": extract.type,
        "path": extract.path,
        "value": REDACTED if sensitive_result else redact_value(extract.value),
        "extracted": extract.extracted,
        "optional": extract.optional,
        "message": redact_text(extract.message),
    }


def _has_sensitive_part(*parts: str | None) -> bool:
    return any(part is not None and is_sensitive_key(part) for part in parts)


def _body_to_json_value(body: str | bytes | None) -> str | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return body
