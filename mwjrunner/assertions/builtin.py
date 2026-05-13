"""内置 HTTP 断言。"""

from __future__ import annotations

import json
from typing import Any

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.assertions.registry import AssertionRegistry
from mwjrunner.cases.model import AssertionSpec
from mwjrunner.http.model import HttpResult


def assert_status_code(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言 HTTP 状态码。"""
    actual = result.response.status_code if result.response is not None else None
    passed = actual == spec.expected
    return AssertionResult(
        type=spec.type,
        passed=passed,
        expected=spec.expected,
        actual=actual,
        path=spec.path,
        target=spec.target,
        mode=spec.mode,
        message="status_code 断言通过" if passed else f"status_code 断言失败: 期望 {spec.expected}, 实际 {actual}",
    )


def assert_json_path(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言 JSON 响应中的简单 JSONPath。"""
    actual: Any = None
    error_message: str | None = None

    if result.response is None:
        error_message = "响应为空,无法执行 json_path 断言"
    elif spec.path is None:
        error_message = "json_path 断言缺少 path"
    else:
        try:
            actual = resolve_json_path(result.response.json(), spec.path)
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
            error_message = str(exc)

    passed = error_message is None and actual == spec.expected
    if passed:
        message = "json_path 断言通过"
    elif error_message is not None:
        message = f"json_path 断言失败: {error_message}"
    else:
        message = f"json_path 断言失败: path {spec.path} 期望 {spec.expected}, 实际 {actual}"

    return AssertionResult(
        type=spec.type,
        passed=passed,
        expected=spec.expected,
        actual=actual,
        path=spec.path,
        target=spec.target,
        mode=spec.mode,
        message=message,
    )


def assert_body_contains(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应体文本包含期望内容。"""
    actual = result.response.text if result.response is not None else None
    expected_text = str(spec.expected)
    passed = actual is not None and expected_text in actual
    return AssertionResult(
        type=spec.type,
        passed=passed,
        expected=spec.expected,
        actual=actual,
        path=spec.path,
        target=spec.target,
        mode=spec.mode,
        message="body_contains 断言通过" if passed else f"body_contains 断言失败: 响应体不包含 {expected_text}",
    )


def assert_json_schema(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应体符合 JSON Schema。"""
    import jsonschema

    if result.response is None:
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=spec.expected,
            actual=None,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message="json_schema 断言失败: 响应为空",
        )

    try:
        response_data = result.response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=spec.expected,
            actual=None,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message=f"json_schema 断言失败: 响应体非 JSON - {exc}",
        )

    schema = spec.expected
    if not isinstance(schema, dict):
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=spec.expected,
            actual=response_data,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message="json_schema 断言失败: expected 必须是 JSON Schema 对象",
        )

    try:
        jsonschema.validate(instance=response_data, schema=schema)
        return AssertionResult(
            type=spec.type,
            passed=True,
            expected=schema,
            actual=response_data,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message="json_schema 断言通过",
        )
    except jsonschema.ValidationError as exc:
        path_str = ".".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "$"
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=schema,
            actual=response_data,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message=f"json_schema 断言失败: 路径 {path_str} - {exc.message}",
        )
    except jsonschema.SchemaError as exc:
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=schema,
            actual=response_data,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message=f"json_schema 断言失败: Schema 无效 - {exc.message}",
        )


def assert_response_time(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应时间不超过阈值（毫秒）。"""
    actual = result.response.elapsed_ms if result.response is not None else None
    if actual is None:
        return AssertionResult(
            type=spec.type,
            passed=False,
            expected=spec.expected,
            actual=None,
            path=spec.path,
            target=spec.target,
            mode=spec.mode,
            message="response_time 断言失败: 响应为空,无法获取耗时",
        )
    threshold = spec.expected
    passed = actual <= threshold
    return AssertionResult(
        type=spec.type,
        passed=passed,
        expected=threshold,
        actual=actual,
        path=spec.path,
        target=spec.target,
        mode=spec.mode,
        message="response_time 断言通过" if passed else f"response_time 断言失败: 实际耗时 {actual}ms 超过阈值 {threshold}ms",
    )


def assert_regex(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应体匹配正则表达式。"""
    import re

    actual = result.response.text if result.response is not None else None
    if actual is None:
        return AssertionResult(
            type=spec.type, passed=False, expected=spec.expected, actual=None,
            path=spec.path, target=spec.target, mode=spec.mode,
            message="regex 断言失败: 响应为空",
        )
    pattern = str(spec.expected)
    match = re.search(pattern, actual)
    passed = match is not None
    return AssertionResult(
        type=spec.type, passed=passed, expected=pattern, actual=match.group(0) if match else None,
        path=spec.path, target=spec.target, mode=spec.mode,
        message="regex 断言通过" if passed else f"regex 断言失败: 响应体不匹配模式 {pattern}",
    )


def assert_header(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应 header 值。"""
    if result.response is None:
        return AssertionResult(
            type=spec.type, passed=False, expected=spec.expected, actual=None,
            path=spec.path, target=spec.target, mode=spec.mode,
            message="header 断言失败: 响应为空",
        )
    header_name = spec.path or spec.target or ""
    # header 名称不区分大小写
    actual = None
    for key, value in result.response.headers.items():
        if key.lower() == header_name.lower():
            actual = value
            break
    passed = actual == spec.expected
    return AssertionResult(
        type=spec.type, passed=passed, expected=spec.expected, actual=actual,
        path=header_name, target=spec.target, mode=spec.mode,
        message="header 断言通过" if passed else f"header 断言失败: {header_name} 期望 {spec.expected}, 实际 {actual}",
    )


def assert_cookie(spec: AssertionSpec, result: HttpResult) -> AssertionResult:
    """断言响应 cookie 值。"""
    if result.response is None:
        return AssertionResult(
            type=spec.type, passed=False, expected=spec.expected, actual=None,
            path=spec.path, target=spec.target, mode=spec.mode,
            message="cookie 断言失败: 响应为空",
        )
    cookie_name = spec.path or spec.target or ""
    actual = result.response.cookies.get(cookie_name)
    passed = actual == spec.expected
    return AssertionResult(
        type=spec.type, passed=passed, expected=spec.expected, actual=actual,
        path=cookie_name, target=spec.target, mode=spec.mode,
        message="cookie 断言通过" if passed else f"cookie 断言失败: {cookie_name} 期望 {spec.expected}, 实际 {actual}",
    )


def create_default_registry() -> AssertionRegistry:
    """创建包含内置断言的注册表。"""
    registry = AssertionRegistry()
    registry.register("status_code", assert_status_code)
    registry.register("json_path", assert_json_path)
    registry.register("body_contains", assert_body_contains)
    registry.register("contains", assert_body_contains)
    registry.register("json_schema", assert_json_schema)
    registry.register("response_time", assert_response_time)
    registry.register("regex", assert_regex)
    registry.register("header", assert_header)
    registry.register("cookie", assert_cookie)
    return registry


def resolve_json_path(data: Any, path: str) -> Any:
    """解析 M1 所需的简单 JSONPath。"""
    if not path.startswith("$"):
        raise ValueError(f"JSONPath 必须以 $ 开头: {path}")
    if path == "$":
        return data

    current = data
    for token in _parse_path_tokens(path):
        if isinstance(token, str):
            if not isinstance(current, dict):
                raise TypeError(f"路径 {path} 中 {token} 的上级不是对象")
            if token not in current:
                raise KeyError(f"路径 {path} 未找到字段 {token}")
            current = current[token]
            continue
        if not isinstance(current, list):
            raise TypeError(f"路径 {path} 中索引 {token} 的上级不是列表")
        if token >= len(current):
            raise IndexError(f"路径 {path} 中索引 {token} 超出列表范围")
        current = current[token]
    return current


def _parse_path_tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    index = 1
    while index < len(path):
        char = path[index]
        if char == ".":
            next_index = index + 1
            while next_index < len(path) and path[next_index] not in ".[":
                next_index += 1
            key = path[index + 1 : next_index]
            if not key:
                raise ValueError(f"JSONPath 字段名为空: {path}")
            tokens.append(key)
            index = next_index
            continue
        if char == "[":
            end_index = path.find("]", index)
            if end_index == -1:
                raise ValueError(f"JSONPath 缺少 ]: {path}")
            raw_index = path[index + 1 : end_index]
            if not raw_index.isdigit():
                raise ValueError(f"JSONPath 仅支持数字列表索引: {path}")
            tokens.append(int(raw_index))
            index = end_index + 1
            continue
        raise ValueError(f"不支持的 JSONPath 语法: {path}")
    return tokens
