"""报告插件接口。

允许用户注册自定义报告器，扩展报告输出能力。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from mwjrunner.reports.model import RunResult


class ReporterPlugin(ABC):
    """报告器插件基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """报告器名称标识（用于 --report 参数）。"""

    @abstractmethod
    def render(self, result: RunResult) -> str:
        """渲染报告内容为字符串。"""

    @abstractmethod
    def write(self, result: RunResult, output_path: Path) -> None:
        """将报告写入文件。"""


class ReporterRegistry:
    """报告器注册表。"""

    def __init__(self) -> None:
        self._plugins: dict[str, ReporterPlugin] = {}

    def register(self, plugin: ReporterPlugin) -> None:
        """注册报告器插件。"""
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> ReporterPlugin | None:
        """获取报告器插件。"""
        return self._plugins.get(name)

    def available(self) -> list[str]:
        """列出所有可用报告器名称。"""
        return list(self._plugins.keys())

    def write_all(self, result: RunResult, report_dir: Path, report_types: tuple[str, ...]) -> None:
        """按配置输出所有报告。"""
        for report_type in report_types:
            plugin = self.get(report_type)
            if plugin:
                output_path = report_dir / result.run_id / f"report.{report_type}"
                plugin.write(result, output_path)
