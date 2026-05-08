"""断言注册表。"""

from __future__ import annotations

from collections.abc import Callable

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.cases.model import AssertionSpec
from mwjrunner.http.model import HttpResult

AssertionHandler = Callable[[AssertionSpec, HttpResult], AssertionResult]


class AssertionRegistry:
    """按断言类型注册和执行断言。"""

    def __init__(self) -> None:
        self._handlers: dict[str, AssertionHandler] = {}

    def register(self, assertion_type: str, handler: AssertionHandler) -> None:
        """注册断言处理函数。"""
        self._handlers[assertion_type] = handler

    def get(self, assertion_type: str) -> AssertionHandler | None:
        """获取断言处理函数。"""
        return self._handlers.get(assertion_type)

    def execute(self, spec: AssertionSpec, result: HttpResult) -> AssertionResult:
        """执行单条断言。"""
        handler = self.get(spec.type)
        if handler is None:
            return AssertionResult(
                type=spec.type,
                passed=False,
                expected=spec.expected,
                actual=None,
                path=spec.path,
                target=spec.target,
                mode=spec.mode,
                message=f"未知断言类型: {spec.type}",
            )
        return handler(spec, result)

    def execute_all(self, specs: list[AssertionSpec], result: HttpResult) -> list[AssertionResult]:
        """按声明顺序执行多条断言。"""
        results: list[AssertionResult] = []
        for spec in specs:
            assertion_result = self.execute(spec, result)
            results.append(assertion_result)
            if not assertion_result.passed and spec.mode == "hard":
                break
        return results
