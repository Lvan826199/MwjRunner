"""变量替换和 JSONPath 提取。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from mwjrunner.assertions.builtin import resolve_json_path
from mwjrunner.cases.model import ExtractSpec
from mwjrunner.http.model import HttpResult

_VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class VariableError(Exception):
    """变量替换或提取失败。"""


@dataclass(frozen=True)
class ExtractResult:
    """单个变量提取结果。"""

    name: str
    type: str
    path: str
    value: Any = None
    extracted: bool = False
    optional: bool = False
    message: str = ""


class VariableEngine:
    """管理变量上下文、变量替换和响应提取。"""

    def __init__(self, variables: dict[str, Any] | None = None) -> None:
        self.variables: dict[str, Any] = dict(variables or {})

    def render(self, value: Any) -> Any:
        """递归替换对象中的 ${var_name} 变量。"""
        if isinstance(value, str):
            return self._render_string(value)
        if isinstance(value, dict):
            return {key: self.render(item_value) for key, item_value in value.items()}
        if isinstance(value, list):
            return [self.render(item) for item in value]
        return value

    def extract_all(self, specs: list[ExtractSpec], result: HttpResult) -> list[ExtractResult]:
        """按声明顺序提取变量,并写入变量上下文。"""
        return [self.extract(spec, result) for spec in specs]

    def extract(self, spec: ExtractSpec, result: HttpResult) -> ExtractResult:
        """从 HTTP 响应中提取单个变量。"""
        if spec.type != "json_path":
            message = f"不支持的提取类型: {spec.type}"
            if spec.optional:
                return ExtractResult(spec.name, spec.type, spec.path, optional=True, message=message)
            raise VariableError(message)
        if result.response is None:
            message = "响应为空,无法提取变量"
            if spec.optional:
                return ExtractResult(spec.name, spec.type, spec.path, optional=True, message=message)
            raise VariableError(message)

        try:
            value = resolve_json_path(result.response.json(), spec.path)
        except json.JSONDecodeError as exc:
            body_preview = result.response.text[:80] or "(空)"
            message = (
                f"响应 JSON 解析失败,无法提取变量"
                f" (status_code={result.response.status_code}, body={body_preview})"
            )
            if spec.optional:
                return ExtractResult(spec.name, spec.type, spec.path, optional=True, message=message)
            raise VariableError(message) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            message = str(exc)
            if spec.optional:
                return ExtractResult(spec.name, spec.type, spec.path, optional=True, message=message)
            raise VariableError(message) from exc

        self.variables[spec.name] = value
        return ExtractResult(
            name=spec.name,
            type=spec.type,
            path=spec.path,
            value=value,
            extracted=True,
            optional=spec.optional,
            message="变量提取成功",
        )

    def _render_string(self, value: str) -> Any:
        matches = list(_VARIABLE_PATTERN.finditer(value))
        if not matches:
            return value
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            return self._get_variable(matches[0].group(1))

        def replace(match: re.Match[str]) -> str:
            return str(self._get_variable(match.group(1)))

        return _VARIABLE_PATTERN.sub(replace, value)

    def _get_variable(self, name: str) -> Any:
        if name not in self.variables:
            raise VariableError(f"变量未定义: {name}")
        return self.variables[name]
