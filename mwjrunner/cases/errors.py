"""用例加载错误。"""

from __future__ import annotations


class CaseLoadError(Exception):
    """用例文件加载或校验失败。"""

    def __init__(self, file_path: str, field: str, message: str, suggestion: str) -> None:
        self.file_path = file_path
        self.field = field
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return f"用例加载失败: {self.message}\n文件: {self.file_path}\n字段: {self.field}\n建议: {self.suggestion}"
