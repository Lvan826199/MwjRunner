"""JSON 报告输出。"""

from __future__ import annotations

import json
from pathlib import Path

from mwjrunner.reports.model import RunResult


class JsonReporter:
    """渲染和写入 JSON 报告。"""

    def render(self, result: RunResult) -> str:
        """渲染 JSON 报告文本。"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    def write(self, result: RunResult, output_file: str | Path) -> None:
        """写入 JSON 报告文件。"""
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(result) + "\n", encoding="utf-8")
