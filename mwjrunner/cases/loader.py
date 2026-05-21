"""YAML 用例加载和校验。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mwjrunner.cases.errors import CaseLoadError
from mwjrunner.cases.model import AssertionSpec, ExtractSpec, RequestSpec, TestCase, TestStep


def load_yaml_case(file_path: str | Path) -> TestCase:
    """加载单个 YAML 用例文件。"""
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CaseLoadError(
            str(path),
            "file",
            f"无法读取用例文件: {exc}",
            "请确认用例文件路径存在,并且当前用户有读取权限。",
        ) from exc

    try:
        raw_case = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise CaseLoadError(
            str(path),
            "yaml",
            f"YAML 解析失败: {exc}",
            "请检查 YAML 缩进、冒号、引号和列表格式。",
        ) from exc

    return parse_case(raw_case, str(path))


def parse_case(raw_case: Any, source_file: str) -> TestCase:
    """将 YAML 原始对象转换成内部用例模型。"""
    if not isinstance(raw_case, dict):
        raise _error(
            source_file, "$", "用例文件顶层必须是对象。", "请使用 name、tags、variables、steps 等字段定义用例。"
        )

    name = _required_string(raw_case, "name", source_file, "请在用例顶层增加 name 字段,例如 name: 健康检查。")
    tags = _optional_string_list(raw_case, "tags", source_file)
    variables = _optional_mapping(raw_case, "variables", source_file)
    priority = _optional_string(raw_case, "priority", source_file)
    data = _optional_data_list(raw_case, "data", source_file)
    data_file = _optional_string(raw_case, "data_file", source_file)
    retry = _optional_int(raw_case, "retry", source_file)
    hooks = _optional_hooks(raw_case, "hooks", source_file)
    auth = _optional_auth(raw_case, "auth", source_file)
    steps = _parse_steps(raw_case.get("steps"), source_file)

    return TestCase(
        name=name,
        tags=tags,
        variables=variables,
        steps=steps,
        priority=priority,
        source_file=source_file,
        data=data,
        data_file=data_file,
        retry=retry,
        hooks=hooks,
        auth=auth,
    )


def _parse_steps(raw_steps: Any, source_file: str) -> list[TestStep]:
    if raw_steps is None:
        raise _error(source_file, "steps", "缺少必填字段 steps。", "请增加 steps 列表,并至少包含一个请求步骤。")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise _error(
            source_file, "steps", "steps 必须是非空列表。", "请按 steps: 下方缩进编写 - name: ... 的步骤列表。"
        )

    steps: list[TestStep] = []
    for index, raw_step in enumerate(raw_steps):
        field = f"steps[{index}]"
        if not isinstance(raw_step, dict):
            raise _error(
                source_file, field, "step 必须是对象。", "请使用 name、request、assertions、extract 等字段定义步骤。"
            )
        name = _required_string(raw_step, "name", source_file, f"请在 {field} 增加 name 字段。", field)
        request = _parse_request(raw_step.get("request"), source_file, f"{field}.request")
        assertions = _parse_assertions(raw_step.get("assertions", []), source_file, f"{field}.assertions")
        extract = _parse_extract(raw_step.get("extract", {}), source_file, f"{field}.extract")
        variables = _optional_mapping(raw_step, "variables", source_file, field)
        steps.append(TestStep(name=name, request=request, assertions=assertions, extract=extract, variables=variables))
    return steps


def _parse_request(raw_request: Any, source_file: str, field: str) -> RequestSpec:
    if raw_request is None:
        raise _error(source_file, field, "缺少必填字段 request。", "请为步骤增加 request,并填写 method 和 url。")
    if not isinstance(raw_request, dict):
        raise _error(source_file, field, "request 必须是对象。", "请使用 request.method 和 request.url 定义请求。")

    method = _required_string(raw_request, "method", source_file, f"请在 {field} 增加 method,例如 method: GET。", field)
    url = _required_string(raw_request, "url", source_file, f"请在 {field} 增加 url,例如 url: /health。", field)
    headers = _optional_mapping(raw_request, "headers", source_file, field)
    query = _optional_mapping(raw_request, "query", source_file, field)
    cookies = _optional_mapping(raw_request, "cookies", source_file, field)
    timeout = raw_request.get("timeout")
    if timeout is not None and not isinstance(timeout, int | float):
        raise _error(source_file, f"{field}.timeout", "timeout 必须是数字。", "请填写秒数,例如 timeout: 5。")

    return RequestSpec(
        method=method.upper(),
        url=url,
        headers=headers,
        query=query,
        cookies=cookies,
        json=raw_request.get("json"),
        data=raw_request.get("data"),
        body=raw_request.get("body"),
        timeout=float(timeout) if timeout is not None else None,
        files=_parse_files(raw_request.get("files"), source_file, f"{field}.files"),
    )


def _parse_files(raw_files: Any, source_file: str, field: str) -> list[dict[str, str]] | None:
    if raw_files is None:
        return None
    if not isinstance(raw_files, list):
        raise _error(source_file, field, "files 必须是列表。", "请使用 files: [{field: file, path: ./a.txt}] 格式。")
    files: list[dict[str, str]] = []
    for index, item in enumerate(raw_files):
        item_field = f"{field}[{index}]"
        if not isinstance(item, dict):
            raise _error(
                source_file,
                item_field,
                "files 每项必须是对象。",
                "请使用 {field: file, path: ./a.txt} 格式。",
            )
        if "path" not in item or not isinstance(item["path"], str):
            raise _error(source_file, f"{item_field}.path", "files 每项必须包含 path 字段。", "请填写文件路径。")
        files.append({k: str(v) for k, v in item.items()})
    return files


def _parse_assertions(raw_assertions: Any, source_file: str, field: str) -> list[AssertionSpec]:
    if raw_assertions is None:
        return []
    if not isinstance(raw_assertions, list):
        raise _error(
            source_file, field, "assertions 必须是列表。", "请使用 assertions: 下方缩进编写 - type: status_code。"
        )

    assertions: list[AssertionSpec] = []
    for index, raw_assertion in enumerate(raw_assertions):
        item_field = f"{field}[{index}]"
        if not isinstance(raw_assertion, dict):
            raise _error(source_file, item_field, "断言必须是对象。", "请使用 type、expected、path 等字段定义断言。")
        assertion_type = _required_string(
            raw_assertion, "type", source_file, f"请在 {item_field} 增加 type 字段。", item_field
        )
        if "expected" not in raw_assertion:
            raise _error(
                source_file,
                f"{item_field}.expected",
                "断言缺少 expected 字段。",
                "请填写断言期望值,例如 expected: 200。",
            )
        path = raw_assertion.get("path")
        if assertion_type == "json_path" and not isinstance(path, str):
            raise _error(
                source_file,
                f"{item_field}.path",
                "json_path 断言必须填写 path。",
                "请填写 JSONPath,例如 path: $.status。",
            )
        mode = raw_assertion.get("mode", "soft")
        if not isinstance(mode, str):
            raise _error(source_file, f"{item_field}.mode", "断言 mode 必须是字符串。", "请填写 soft 或 hard。")
        target = raw_assertion.get("target")
        if target is not None and not isinstance(target, str):
            raise _error(
                source_file,
                f"{item_field}.target",
                "断言 target 必须是字符串。",
                "请填写响应字段目标名称,或删除 target 字段。",
            )
        assertions.append(
            AssertionSpec(
                type=assertion_type,
                expected=raw_assertion["expected"],
                path=path,
                target=target,
                mode=mode,
            )
        )
    return assertions


def _parse_extract(raw_extract: Any, source_file: str, field: str) -> list[ExtractSpec]:
    if raw_extract is None:
        return []
    if not isinstance(raw_extract, dict):
        raise _error(
            source_file, field, "extract 必须是对象。", "请使用 extract: token: $.data.token 的形式定义提取变量。"
        )

    extracts: list[ExtractSpec] = []
    for name, raw_value in raw_extract.items():
        item_field = f"{field}.{name}"
        if not isinstance(name, str) or not name:
            raise _error(source_file, field, "extract 变量名必须是非空字符串。", "请使用有意义的变量名,例如 token。")
        if isinstance(raw_value, str):
            extracts.append(ExtractSpec(name=name, type="json_path", path=raw_value))
            continue
        if isinstance(raw_value, dict):
            extract_type = raw_value.get("type", "json_path")
            path = raw_value.get("path")
            optional = raw_value.get("optional", False)
            if not isinstance(extract_type, str):
                raise _error(
                    source_file,
                    f"{item_field}.type",
                    "extract type 必须是字符串。",
                    "请填写 json_path、header、cookie 或 regex。",
                )
            if not isinstance(path, str) or not path:
                raise _error(
                    source_file,
                    f"{item_field}.path",
                    "extract path 必须是非空字符串。",
                    "请填写提取路径,例如 path: $.data.token。",
                )
            if not isinstance(optional, bool):
                raise _error(
                    source_file, f"{item_field}.optional", "extract optional 必须是布尔值。", "请填写 true 或 false。"
                )
            extracts.append(ExtractSpec(name=name, type=extract_type, path=path, optional=optional))
            continue
        raise _error(
            source_file,
            item_field,
            "extract 值必须是字符串或对象。",
            "请使用 token: $.data.token 或 token: {type: json_path, path: $.data.token}。",
        )
    return extracts


def _required_string(raw: dict[str, Any], key: str, source_file: str, suggestion: str, parent: str = "") -> str:
    field = f"{parent}.{key}" if parent else key
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _error(source_file, field, f"缺少必填字段 {field} 或字段不是非空字符串。", suggestion)
    return value


def _optional_string_list(raw: dict[str, Any], key: str, source_file: str, parent: str = "") -> list[str]:
    field = f"{parent}.{key}" if parent else key
    value = raw.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _error(source_file, field, f"{field} 必须是字符串列表。", f"请使用 {key}: [smoke, auth] 的形式。")
    return value


def _optional_mapping(raw: dict[str, Any], key: str, source_file: str, parent: str = "") -> dict[str, Any]:
    field = f"{parent}.{key}" if parent else key
    value = raw.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _error(source_file, field, f"{field} 必须是对象。", f"请使用 {key}: 下方缩进编写键值对。")
    return value


def _optional_string(raw: dict[str, Any], key: str, source_file: str, parent: str = "") -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        field = f"{parent}.{key}" if parent else key
        raise _error(source_file, field, f"{field} 必须是字符串。", "请填写字符串值。")
    return value


def _optional_int(raw: dict[str, Any], key: str, source_file: str, parent: str = "") -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        field = f"{parent}.{key}" if parent else key
        raise _error(source_file, field, f"{field} 必须是整数。", f"请填写整数值,例如 {key}: 2。")
    return value


def _optional_data_list(raw: dict[str, Any], key: str, source_file: str) -> list[dict[str, Any]] | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, list):
        raise _error(source_file, key, f"{key} 必须是列表。", "请使用 data: [{...}, {...}] 格式。")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise _error(
                source_file, f"{key}[{index}]", "data 每条记录必须是对象。", "请使用 {key: value} 格式。"
            )
    return value


def _optional_hooks(raw: dict[str, Any], key: str, source_file: str) -> dict[str, str | list[str]]:
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _error(source_file, key, f"{key} 必须是对象。", "请使用 hooks: before_case: module.func 格式。")
    valid_keys = {"before_case", "after_case", "before_step", "after_step"}
    for hook_key, hook_value in value.items():
        if hook_key not in valid_keys:
            raise _error(
                source_file, f"{key}.{hook_key}",
                f"不支持的 hook 类型: {hook_key}。",
                f"支持的类型: {', '.join(sorted(valid_keys))}。",
            )
        if isinstance(hook_value, str):
            continue
        if isinstance(hook_value, list) and all(isinstance(v, str) for v in hook_value):
            continue
        raise _error(
            source_file, f"{key}.{hook_key}",
            "hook 值必须是字符串或字符串列表。",
            "请使用模块路径,例如 myproject.hooks.setup。",
        )
    return value


def _optional_auth(raw: dict[str, Any], key: str, source_file: str) -> dict[str, Any] | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _error(source_file, key, f"{key} 必须是对象。", "请使用 auth: type: bearer, token: xxx 格式。")
    auth_type = value.get("type")
    if auth_type not in ("bearer", "basic"):
        raise _error(
            source_file, f"{key}.type",
            f"不支持的认证类型: {auth_type}。",
            "支持的类型: bearer, basic。",
        )
    return value


def _error(source_file: str, field: str, message: str, suggestion: str) -> CaseLoadError:
    return CaseLoadError(source_file, field, message, suggestion)
