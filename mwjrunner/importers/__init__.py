"""Postman Collection v2.1 导入器。

将 Postman Collection JSON 转换为 MwjRunner YAML 用例文件。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

_POSTMAN_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def import_postman_collection(
    collection_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """导入 Postman Collection 并生成 YAML 用例文件。

    Args:
        collection_path: Postman Collection JSON 文件路径
        output_dir: 输出 YAML 用例目录

    Returns:
        生成的 YAML 文件路径列表
    """
    collection_path = Path(collection_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _load_collection(collection_path)
    items = data.get("item", [])
    collection_variables = _parse_collection_variables(data.get("variable", []))

    generated: list[Path] = []
    _process_items(items, output_dir, generated, "", collection_variables)
    return generated


def _parse_collection_variables(raw: Any) -> dict[str, Any]:
    """解析集合级 variable 数组为变量字典。"""
    variables: dict[str, Any] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("key"):
                variables[str(item["key"])] = item.get("value", "")
    return variables


def _convert_postman_variables(value: Any) -> Any:
    """递归将 Postman 的 {{var}} 变量语法转换为 MwjRunner 的 ${var}。"""
    if isinstance(value, str):
        return _POSTMAN_VARIABLE_PATTERN.sub(r"${\1}", value)
    if isinstance(value, dict):
        return {key: _convert_postman_variables(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_convert_postman_variables(item) for item in value]
    return value


def _load_collection(path: Path) -> dict[str, Any]:
    """加载并校验 Postman Collection 文件。"""
    if not path.is_file():
        raise FileNotFoundError(f"Postman Collection 文件不存在: {path}")

    content = path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Postman Collection JSON 解析失败: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Postman Collection 顶层必须是对象")

    info = data.get("info", {})
    schema = info.get("schema", "")
    if "v2.1" not in schema and "v2.0" not in schema:
        # 宽松处理，仅警告
        pass

    return data


def _process_items(
    items: list[dict[str, Any]],
    output_dir: Path,
    generated: list[Path],
    _prefix: str,
    collection_variables: dict[str, Any] | None = None,
) -> None:
    """递归处理 Postman items（支持文件夹嵌套）。"""
    for item in items:
        if "item" in item:
            # 文件夹，递归处理
            folder_name = _safe_filename(item.get("name", "folder"))
            sub_dir = output_dir / folder_name
            sub_dir.mkdir(parents=True, exist_ok=True)
            _process_items(item["item"], sub_dir, generated, folder_name + "/", collection_variables)
        elif "request" in item:
            # 单个请求
            yaml_content = _convert_request_to_case(item, collection_variables)
            base_name = _safe_filename(item.get("name", "request"))
            file_path = _unique_path(output_dir, base_name, generated)
            file_path.write_text(
                yaml.dump(yaml_content, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            generated.append(file_path)


def _unique_path(output_dir: Path, base_name: str, generated: list[Path]) -> Path:
    """同名文件追加序号，避免同次导入互相覆盖。"""
    existing = set(generated)
    candidate = output_dir / f"{base_name}.yaml"
    counter = 2
    while candidate in existing:
        candidate = output_dir / f"{base_name}_{counter}.yaml"
        counter += 1
    return candidate


def _convert_request_to_case(
    item: dict[str, Any],
    collection_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """将单个 Postman request item 转换为 MwjRunner case 结构。"""
    name = item.get("name", "Unnamed Request")
    request = item.get("request", {})

    method = request.get("method", "GET")
    url = _convert_postman_variables(_parse_url(request.get("url", "")))
    headers = _convert_postman_variables(_parse_headers(request.get("header", [])))
    body = _convert_postman_variables(_parse_body(request.get("body")))

    step: dict[str, Any] = {
        "name": name,
        "request": {"method": method, "url": url},
    }

    if headers:
        step["request"]["headers"] = headers
    if body:
        step["request"].update(body)

    # 默认添加 status_code 断言
    step["assertions"] = [{"type": "status_code", "expected": 200}]

    case: dict[str, Any] = {
        "name": name,
        "tags": ["imported"],
    }
    if collection_variables:
        case["variables"] = dict(collection_variables)
    case["steps"] = [step]

    return case


def _parse_url(url: Any) -> str:
    """解析 Postman URL 对象或字符串。"""
    if isinstance(url, str):
        return url
    if isinstance(url, dict):
        raw = url.get("raw", "")
        if raw:
            return raw
        # 从 host + path 拼接（规范允许 host/path 为字符串或数组）
        raw_host = url.get("host", [])
        host = raw_host if isinstance(raw_host, str) else ".".join(raw_host)
        raw_path = url.get("path", [])
        path = raw_path.lstrip("/") if isinstance(raw_path, str) else "/".join(raw_path)
        protocol = url.get("protocol", "http")
        if host:
            return f"{protocol}://{host}/{path}"
        return f"/{path}"
    return "/"


def _parse_headers(headers: list[dict[str, Any]]) -> dict[str, str]:
    """解析 Postman headers 数组。"""
    result: dict[str, str] = {}
    for header in headers:
        if isinstance(header, dict) and not header.get("disabled", False):
            key = header.get("key", "")
            value = header.get("value", "")
            if key:
                result[key] = value
    return result


def _parse_body(body: dict[str, Any] | None) -> dict[str, Any] | None:
    """解析 Postman body 为 MwjRunner request 字段。"""
    if not body:
        return None

    mode = body.get("mode", "")

    if mode == "raw":
        raw = body.get("raw", "")
        options = body.get("options", {})
        language = options.get("raw", {}).get("language", "")
        if language == "json" or _looks_like_json(raw):
            try:
                return {"json": json.loads(raw)}
            except json.JSONDecodeError:
                pass
        return {"body": raw}

    if mode == "urlencoded":
        data = {}
        for item in body.get("urlencoded", []):
            if isinstance(item, dict) and not item.get("disabled", False):
                data[item.get("key", "")] = item.get("value", "")
        return {"data": data} if data else None

    if mode == "formdata":
        data = {}
        for item in body.get("formdata", []):
            if isinstance(item, dict) and not item.get("disabled", False) and item.get("type") == "text":
                data[item.get("key", "")] = item.get("value", "")
        return {"data": data} if data else None

    return None


def _looks_like_json(text: str) -> bool:
    """简单判断文本是否像 JSON。"""
    stripped = text.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )


def _safe_filename(name: str) -> str:
    """将名称转换为安全文件名。"""
    safe = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
    return safe[:64] or "unnamed"
