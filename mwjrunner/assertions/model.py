"""自研断言结果模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AssertionResult:
    """单条断言执行结果。"""

    type: str
    passed: bool
    expected: Any
    actual: Any
    path: str | None = None
    target: str | None = None
    mode: str = "soft"
    message: str = ""
