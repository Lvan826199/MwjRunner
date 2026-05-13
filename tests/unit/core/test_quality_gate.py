"""质量门禁单元测试。"""

from __future__ import annotations

from datetime import datetime

import pytest

from mwjrunner.core.quality_gate import (
    QualityGateConfig,
    evaluate_quality_gate,
    parse_quality_gate_config,
)
from mwjrunner.reports.model import CaseResult, RunResult, Summary


def _run_result(
    total: int = 10,
    passed: int = 8,
    failed: int = 1,
    error: int = 1,
) -> RunResult:
    cases = (
        [CaseResult(name=f"pass_{i}", status="passed") for i in range(passed)]
        + [CaseResult(name=f"fail_{i}", status="failed") for i in range(failed)]
        + [CaseResult(name=f"error_{i}", status="error") for i in range(error)]
    )
    return RunResult(
        run_id="test-run",
        started_at=datetime(2026, 1, 1),
        ended_at=datetime(2026, 1, 1),
        summary=Summary(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            error_cases=error,
        ),
        cases=cases,
    )


@pytest.mark.unit
class TestQualityGate:
    """质量门禁测试。"""

    def test_all_pass_no_gate(self) -> None:
        result = _run_result(total=5, passed=5, failed=0, error=0)
        config = QualityGateConfig(max_failure_rate=0.1)
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is True

    def test_failure_rate_exceeded(self) -> None:
        result = _run_result(total=10, passed=5, failed=4, error=1)
        config = QualityGateConfig(max_failure_rate=0.1)
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is False
        assert any("失败率" in v for v in gate.violations)

    def test_failure_rate_within_threshold(self) -> None:
        result = _run_result(total=10, passed=9, failed=1, error=0)
        config = QualityGateConfig(max_failure_rate=0.2)
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is True

    def test_error_rate_exceeded(self) -> None:
        result = _run_result(total=10, passed=5, failed=0, error=4)
        config = QualityGateConfig(max_error_rate=0.1)
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is False
        assert any("错误率" in v for v in gate.violations)

    def test_empty_result_passes(self) -> None:
        result = _run_result(total=0, passed=0, failed=0, error=0)
        config = QualityGateConfig(max_failure_rate=0.1)
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is True

    def test_no_thresholds_always_passes(self) -> None:
        result = _run_result(total=10, passed=0, failed=10, error=0)
        config = QualityGateConfig()
        gate = evaluate_quality_gate(result, config)
        assert gate.passed is True

    def test_parse_config_from_dict(self) -> None:
        data = {"max_failure_rate": 0.1, "max_error_rate": 0.05, "max_response_time_ms": 2000}
        config = parse_quality_gate_config(data)
        assert config is not None
        assert config.max_failure_rate == 0.1
        assert config.max_error_rate == 0.05
        assert config.max_response_time_ms == 2000.0

    def test_parse_config_none(self) -> None:
        assert parse_quality_gate_config(None) is None

    def test_parse_config_empty(self) -> None:
        assert parse_quality_gate_config({}) is None
