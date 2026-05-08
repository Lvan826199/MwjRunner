"""自研断言模块。"""

from mwjrunner.assertions.builtin import (
    assert_body_contains,
    assert_json_path,
    assert_status_code,
    create_default_registry,
    resolve_json_path,
)
from mwjrunner.assertions.model import AssertionResult
from mwjrunner.assertions.registry import AssertionHandler, AssertionRegistry

__all__ = [
    "AssertionHandler",
    "AssertionRegistry",
    "AssertionResult",
    "assert_body_contains",
    "assert_json_path",
    "assert_status_code",
    "create_default_registry",
    "resolve_json_path",
]
