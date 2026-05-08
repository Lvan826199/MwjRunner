"""变量替换和提取模块单元测试。"""

from __future__ import annotations

import pytest

from mwjrunner.cases.model import ExtractSpec
from mwjrunner.http.model import HttpRequest, HttpResponse, HttpResult
from mwjrunner.variables import VariableEngine, VariableError


def _http_result(body: bytes = b'{"data":{"token":"abc123"}}') -> HttpResult:
    return HttpResult(
        request=HttpRequest(method="POST", url="/api/login"),
        response=HttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            cookies={},
            body=body,
            elapsed_ms=10.0,
        ),
    )


@pytest.mark.unit
class TestVariableEngine:
    """变量引擎测试。"""

    def test_render_string_variable_keeps_original_type(self) -> None:
        engine = VariableEngine({"timeout": 5})

        result = engine.render("${timeout}")

        assert result == 5

    def test_render_nested_object(self) -> None:
        engine = VariableEngine({"username": "demo", "token": "abc123"})

        result = engine.render(
            {
                "json": {"username": "${username}"},
                "headers": {"Authorization": "Bearer ${token}"},
                "tags": ["${username}", "fixed"],
            }
        )

        assert result == {
            "json": {"username": "demo"},
            "headers": {"Authorization": "Bearer abc123"},
            "tags": ["demo", "fixed"],
        }

    def test_render_missing_variable_raises_clear_error(self) -> None:
        engine = VariableEngine()

        with pytest.raises(VariableError, match="变量未定义: token"):
            engine.render("Bearer ${token}")

    def test_extract_json_path_sets_variable(self) -> None:
        engine = VariableEngine()
        spec = ExtractSpec(name="token", type="json_path", path="$.data.token")

        result = engine.extract(spec, _http_result())

        assert result.extracted is True
        assert result.value == "abc123"
        assert engine.variables["token"] == "abc123"

    def test_extract_optional_missing_path_returns_result(self) -> None:
        engine = VariableEngine()
        spec = ExtractSpec(name="token", type="json_path", path="$.missing", optional=True)

        result = engine.extract(spec, _http_result())

        assert result.extracted is False
        assert result.optional is True
        assert "未找到字段 missing" in result.message
        assert "token" not in engine.variables

    def test_extract_required_missing_path_raises_clear_error(self) -> None:
        engine = VariableEngine()
        spec = ExtractSpec(name="token", type="json_path", path="$.missing")

        with pytest.raises(VariableError, match="未找到字段 missing"):
            engine.extract(spec, _http_result())

    def test_extract_required_invalid_json_raises_variable_error(self) -> None:
        engine = VariableEngine()
        spec = ExtractSpec(name="token", type="json_path", path="$.data.token")

        with pytest.raises(VariableError, match="响应 JSON 解析失败"):
            engine.extract(spec, _http_result(body=b"not-json"))
