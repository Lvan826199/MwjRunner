"""质量门禁。

根据运行结果统计和配置阈值判断是否通过质量门禁。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mwjrunner.reports.model import RunResult


@dataclass(frozen=True)
class QualityGateConfig:
    """质量门禁配置。"""

    max_failure_rate: float | None = None
    max_error_rate: float | None = None
    max_response_time_ms: float | None = None


@dataclass(frozen=True)
class QualityGateResult:
    """质量门禁判断结果。"""

    passed: bool
    violations: list[str] = field(default_factory=list)


def evaluate_quality_gate(result: RunResult, config: QualityGateConfig) -> QualityGateResult:
    """评估运行结果是否通过质量门禁。"""
    violations: list[str] = []
    # fail-fast 跳过的用例不计入分母，避免稀释失败率/错误率
    total = result.summary.total_cases - result.summary.skipped_cases

    if total <= 0:
        return QualityGateResult(passed=True)

    # 失败率检查
    if config.max_failure_rate is not None:
        failure_rate = result.summary.failed_cases / total
        if failure_rate > config.max_failure_rate:
            violations.append(f"失败率 {failure_rate:.1%} 超过阈值 {config.max_failure_rate:.1%}")

    # 错误率检查
    if config.max_error_rate is not None:
        error_rate = result.summary.error_cases / total
        if error_rate > config.max_error_rate:
            violations.append(f"错误率 {error_rate:.1%} 超过阈值 {config.max_error_rate:.1%}")

    # 响应时间检查
    if config.max_response_time_ms is not None:
        max_elapsed = _get_max_response_time(result)
        if max_elapsed is not None and max_elapsed > config.max_response_time_ms:
            violations.append(f"最大响应时间 {max_elapsed:.0f}ms 超过阈值 {config.max_response_time_ms:.0f}ms")

    return QualityGateResult(passed=len(violations) == 0, violations=violations)


def parse_quality_gate_config(data: dict[str, Any] | None) -> QualityGateConfig | None:
    """从配置字典解析质量门禁配置。"""
    if not data or not isinstance(data, dict):
        return None
    return QualityGateConfig(
        max_failure_rate=_parse_float(data.get("max_failure_rate")),
        max_error_rate=_parse_float(data.get("max_error_rate")),
        max_response_time_ms=_parse_float(data.get("max_response_time_ms")),
    )


def _get_max_response_time(result: RunResult) -> float | None:
    """获取所有步骤中的最大响应时间。"""
    max_time: float | None = None
    for case in result.cases:
        for step in case.steps:
            if step.response and step.response.elapsed_ms and (max_time is None or step.response.elapsed_ms > max_time):
                max_time = step.response.elapsed_ms
    return max_time


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
