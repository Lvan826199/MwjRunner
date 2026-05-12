"""HTML 报告生成器。"""

from __future__ import annotations

from pathlib import Path

from mwjrunner.reports._html_template import render_html_report
from mwjrunner.reports.model import RunResult


class HtmlReporter:
    """渲染和写入单文件 HTML 报告。"""

    def render(self, result: RunResult) -> str:
        """渲染完整 HTML 报告字符串。"""
        data = result.to_dict()
        return render_html_report(data)

    def write(self, result: RunResult, output_file: str | Path) -> None:
        """写入 HTML 报告文件。"""
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(result), encoding="utf-8")
