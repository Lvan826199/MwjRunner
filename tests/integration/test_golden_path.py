"""发布黄金路径集成回归。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mwjrunner.cli import main
from mwjrunner.reports.exit_code import ASSERTION_FAILED_EXIT_CODE, SUCCESS_EXIT_CODE


def _load_single_json_report(report_dir: Path) -> dict:
    result_files = list(report_dir.glob("*/result.json"))
    assert len(result_files) == 1
    return json.loads(result_files[0].read_text(encoding="utf-8"))


@pytest.mark.integration
def test_cli_golden_path_login_extract_json_report_and_redaction(
    fastapi_server: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """黄金路径：登录提取 token、复用变量、生成报告且敏感信息脱敏。"""
    report_dir = tmp_path / "reports"

    exit_code = main(
        [
            "run",
            "examples/cases/login_profile.yaml",
            "--base-url",
            fastapi_server,
            "--report",
            "console,json",
            "--report-dir",
            str(report_dir),
            "--retry",
            "0",
        ]
    )

    captured = capsys.readouterr()
    console_output = captured.out + captured.err
    assert exit_code == SUCCESS_EXIT_CODE
    assert "demo-token" not in console_output
    assert "123456" not in console_output

    report_file = next(report_dir.glob("*/result.json"))
    report_text = report_file.read_text(encoding="utf-8")
    assert "demo-token" not in report_text
    assert "123456" not in report_text
    assert "***REDACTED***" in report_text

    report = json.loads(report_text)
    assert report["summary"]["passed_cases"] == 1
    assert report["summary"]["failed_assertions"] == 0
    assert report["cases"][0]["steps"][0]["extracts"][0]["value"] == "***REDACTED***"
    assert report["cases"][0]["steps"][1]["request"]["headers"]["Authorization"] == "***REDACTED***"


@pytest.mark.integration
def test_cli_golden_path_failure_diagnostics_and_exit_code(
    fastapi_server: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """失败路径：断言失败返回退出码 1，并输出可定位的失败诊断。"""
    report_dir = tmp_path / "reports"

    exit_code = main(
        [
            "run",
            "examples/cases/health_fail.yaml",
            "--base-url",
            fastapi_server,
            "--report",
            "console,json",
            "--report-dir",
            str(report_dir),
            "--retry",
            "0",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == ASSERTION_FAILED_EXIT_CODE
    assert "失败或错误明细" in captured.out
    assert "健康检查失败示例 / 故意写错健康状态" in captured.out
    assert "json_path 断言失败" in captured.out
    assert "body_contains 断言失败" in captured.out

    report = _load_single_json_report(report_dir)
    assert report["summary"]["failed_cases"] == 1
    assert report["summary"]["failed_assertions"] == 2
