"""OpenAPI (Swagger) 用例生成器。

从 OpenAPI 2.0/3.0 规范文件生成 MwjRunner YAML 用例骨架。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def generate_from_openapi(
    spec_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """从 OpenAPI 规范生成 YAML 用例文件。

    Args:
        spec_path: OpenAPI 规范文件路径（JSON 或 YAML）
        output_dir: 输出 YAML 用例目录

    Returns:
        生成的 YAML 文件路径列表
    """
    spec_path = Path(spec_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    spec = _load_spec(spec_path)
    version = _detect_version(spec)

    if version == "2":
        return _generate_from_v2(spec, output_dir)
    return _generate_from_v3(spec, output_dir)


def _load_spec(path: Path) -> dict[str, Any]:
    """加载 OpenAPI 规范文件。"""
    if not path.is_file():
        raise FileNotFoundError(f"OpenAPI 规范文件不存在: {path}")

    content = path.read_text(encoding="utf-8")

    if path.suffix in (".json",):
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAPI JSON 解析失败: {exc}") from exc
    else:
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ValueError(f"OpenAPI YAML 解析失败: {exc}") from exc


def _detect_version(spec: dict[str, Any]) -> str:
    """检测 OpenAPI 版本。"""
    if "openapi" in spec:
        return "3"
    if "swagger" in spec:
        return "2"
    return "3"


def _generate_from_v3(spec: dict[str, Any], output_dir: Path) -> list[Path]:
    """从 OpenAPI 3.x 生成用例。"""
    paths = spec.get("paths", {})
    generated: list[Path] = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            case = _build_case(
                path=path,
                method=method.upper(),
                operation=operation,
                spec=spec,
            )

            file_path = _unique_output_path(output_dir, _make_filename(method, path), generated)
            file_path.write_text(
                yaml.dump(case, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            generated.append(file_path)

    return generated


def _unique_output_path(output_dir: Path, filename: str, generated: list[Path]) -> Path:
    """同名文件追加序号，避免同次生成互相覆盖（如 /users/{id} 与 /users/id）。"""
    existing = set(generated)
    candidate = output_dir / filename
    stem = candidate.stem
    counter = 2
    while candidate in existing:
        candidate = output_dir / f"{stem}_{counter}.yaml"
        counter += 1
    return candidate


def _generate_from_v2(spec: dict[str, Any], output_dir: Path) -> list[Path]:
    """从 Swagger 2.0 生成用例。"""
    paths = spec.get("paths", {})
    base_path = spec.get("basePath", "")
    generated: list[Path] = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            full_path = base_path.rstrip("/") + path if base_path else path
            case = _build_case(
                path=full_path,
                method=method.upper(),
                operation=operation,
                spec=spec,
            )

            file_path = _unique_output_path(output_dir, _make_filename(method, path), generated)
            file_path.write_text(
                yaml.dump(case, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            generated.append(file_path)

    return generated


def _build_case(
    path: str,
    method: str,
    operation: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    """构建单个用例结构。"""
    operation_id = operation.get("operationId", f"{method}_{path}")
    summary = operation.get("summary", operation_id)
    tags = operation.get("tags", ["generated"])

    step: dict[str, Any] = {
        "name": summary,
        "request": {
            "method": method,
            "url": path,
        },
    }

    # 解析请求体
    body = _extract_request_body(operation, spec)
    if body:
        step["request"]["json"] = body

    # 解析 query 参数
    query = _extract_query_params(operation)
    if query:
        step["request"]["query"] = query

    # 解析 headers
    headers = _extract_header_params(operation)
    if headers:
        step["request"]["headers"] = headers

    # 默认断言
    expected_status = _guess_success_status(operation)
    step["assertions"] = [{"type": "status_code", "expected": expected_status}]

    case: dict[str, Any] = {
        "name": summary,
        "tags": tags if isinstance(tags, list) else [tags],
        "steps": [step],
    }

    return case


def _extract_request_body(operation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    """提取请求体示例。"""
    # OpenAPI 3.x
    request_body = operation.get("requestBody", {})
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        example = json_content.get("example")
        if example:
            return example
        if schema:
            return _generate_example_from_schema(schema, spec)

    # Swagger 2.0 body parameter
    parameters = operation.get("parameters", [])
    for param in parameters:
        if isinstance(param, dict) and param.get("in") == "body":
            schema = param.get("schema", {})
            example = param.get("example")
            if example:
                return example
            return _generate_example_from_schema(schema, spec)

    return None


def _extract_query_params(operation: dict[str, Any]) -> dict[str, str]:
    """提取 query 参数。"""
    params: dict[str, str] = {}
    for param in operation.get("parameters", []):
        if isinstance(param, dict) and param.get("in") == "query":
            name = param.get("name", "")
            example = param.get("example", param.get("default", ""))
            if name:
                params[name] = str(example) if example else f"${{{name}}}"
    return params


def _extract_header_params(operation: dict[str, Any]) -> dict[str, str]:
    """提取 header 参数。"""
    headers: dict[str, str] = {}
    for param in operation.get("parameters", []):
        if isinstance(param, dict) and param.get("in") == "header":
            name = param.get("name", "")
            example = param.get("example", param.get("default", ""))
            if name:
                headers[name] = str(example) if example else f"${{{name}}}"
    return headers


def _guess_success_status(operation: dict[str, Any]) -> int:
    """猜测成功状态码。"""
    responses = operation.get("responses", {})
    # YAML 中未加引号的状态码会被解析为 int 键，统一归一为字符串再匹配
    normalized = {str(key) for key in responses}
    for code in ("200", "201", "204", "202"):
        if code in normalized:
            return int(code)
    return 200


def _generate_example_from_schema(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    """从 schema 生成示例数据。"""
    schema = _resolve_ref(schema, spec)

    if schema.get("example"):
        return schema["example"]

    schema_type = schema.get("type", "object")
    if schema_type != "object":
        return None

    properties = schema.get("properties", {})
    if not properties:
        return None

    result: dict[str, Any] = {}
    for prop_name, raw_schema in properties.items():
        resolved_schema = _resolve_ref(raw_schema, spec)
        result[prop_name] = _generate_value(prop_name, resolved_schema)

    return result


def _generate_value(name: str, schema: dict[str, Any]) -> Any:  # noqa: PLR0911
    """根据 schema 类型生成示例值。"""
    example = schema.get("example")
    if example is not None:
        return example

    schema_type = schema.get("type", "string")
    if schema_type == "string":
        fmt = schema.get("format", "")
        if fmt == "email":
            return "user@example.com"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "date":
            return "2026-01-01"
        if fmt in {"uri", "url"}:
            return "https://example.com"
        return f"${{{name}}}"
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "array":
        return []
    return f"${{{name}}}"


def _resolve_ref(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """解析 $ref 引用。"""
    ref = schema.get("$ref")
    if not ref or not isinstance(ref, str):
        return schema

    # removeprefix 按前缀剥离（lstrip 是按字符集剥离，会破坏首段名称）
    parts = ref.removeprefix("#/").split("/")
    current: Any = spec
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, {})
        else:
            return schema
    return current if isinstance(current, dict) else schema


def _make_filename(method: str, path: str) -> str:
    """生成文件名。"""
    safe_path = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    safe_path = "".join(c for c in safe_path if c.isalnum() or c in "_-")
    return f"{method.lower()}_{safe_path}.yaml" if safe_path else f"{method.lower()}_root.yaml"
