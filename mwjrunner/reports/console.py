"""终端报告输出。"""

from __future__ import annotations

from mwjrunner.reports.model import RunResult
from mwjrunner.utils.masking import redact_text


class ConsoleReporter:
    """渲染终端摘要报告。"""

    def render(self, result: RunResult) -> str:
        """渲染终端报告文本。"""
        summary = result.summary
        lines = [
            "MwjRunner 执行摘要",
            f"run_id: {result.run_id}",
            (
                f"用例: {summary.total_cases}, 通过: {summary.passed_cases}, "
                f"失败: {summary.failed_cases}, 错误: {summary.error_cases}"
            ),
            (
                f"步骤: {summary.total_steps}, 通过: {summary.passed_steps}, "
                f"失败: {summary.failed_steps}, 错误: {summary.error_steps}"
            ),
            f"断言: {summary.total_assertions}, 失败: {summary.failed_assertions}",
            f"错误: {summary.total_errors}",
            f"耗时: {summary.elapsed_ms} ms",
        ]
        details = self._render_failure_details(result)
        if details:
            lines.append("")
            lines.append("失败或错误明细")
            lines.extend(details)
        return redact_text("\n".join(lines))

    def write(self, result: RunResult) -> None:
        """输出终端报告文本。"""
        print(self.render(result))

    def _render_failure_details(self, result: RunResult) -> list[str]:
        details: list[str] = []
        for error in result.errors:
            details.append(f"- 运行错误: {error}")
        for case in result.cases:
            for error in case.errors:
                details.append(f"- {case.name}: {error}")
            for step in case.steps:
                prefix = f"{case.name} / {step.name}"
                for assertion in step.assertions:
                    if not assertion.passed:
                        details.append(f"- {prefix}: {assertion.message}")
                for error in step.errors:
                    details.append(f"- {prefix}: {error}")
        return details
