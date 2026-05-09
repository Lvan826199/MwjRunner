"""日志上下文。"""

from __future__ import annotations

import logging


class RunIdFilter(logging.Filter):
    """为日志记录注入 run_id。"""

    def __init__(self, run_id: str = "-") -> None:
        super().__init__()
        self.run_id = run_id or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        """注入 run_id 并允许日志继续输出。"""
        record.run_id = self.run_id
        return True
