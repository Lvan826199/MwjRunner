"""断言注册表。"""

from __future__ import annotations

import logging
from collections.abc import Callable

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.cases.model import AssertionSpec
from mwjrunner.http.model import HttpResult

AssertionHandler = Callable[[AssertionSpec, HttpResult], AssertionResult]

_logger = logging.getLogger("mwjrunner.assertions")


class AssertionRegistry:
    """按断言类型注册和执行断言。"""

    def __init__(self) -> None:
        self._handlers: dict[str, AssertionHandler] = {}

    def register(self, assertion_type: str, handler: AssertionHandler) -> None:
        """注册断言处理函数。重复注册会覆盖并记录告警。"""
        existing = self._handlers.get(assertion_type)
        if existing is not None and existing is not handler:
            _logger.warning("断言类型 %s 已注册, 新处理函数将覆盖原实现", assertion_type)
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
        try:
            return handler(spec, result)
        except Exception as exc:
            # 单条断言的实现异常不应中断整个运行，转为失败结果
            _logger.exception("断言执行异常: type=%s", spec.type)
            return AssertionResult(
                type=spec.type,
                passed=False,
                expected=spec.expected,
                actual=None,
                path=spec.path,
                target=spec.target,
                mode=spec.mode,
                message=f"断言执行异常: {exc}",
            )

    def execute_all(self, specs: list[AssertionSpec], result: HttpResult) -> list[AssertionResult]:
        """按声明顺序执行多条断言。"""
        results: list[AssertionResult] = []
        for spec in specs:
            assertion_result = self.execute(spec, result)
            results.append(assertion_result)
            if not assertion_result.passed and spec.mode == "hard":
                break
        return results
