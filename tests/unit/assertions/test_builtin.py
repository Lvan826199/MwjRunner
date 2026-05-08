"""自研断言模块单元测试。"""

from __future__ import annotations

import pytest

from mwjrunner.assertions import AssertionRegistry, create_default_registry
from mwjrunner.cases.model import AssertionSpec
from mwjrunner.http.model import HttpRequest, HttpResponse, HttpResult


def _http_result(status_code: int = 200, body: bytes = b'{"status":"ok"}') -> HttpResult:
    return HttpResult(
        request=HttpRequest(method="GET", url="/health"),
        response=HttpResponse(
            status_code=status_code,
            headers={"content-type": "application/json"},
            cookies={},
            body=body,
            elapsed_ms=12.3,
        ),
    )


@pytest.mark.unit
class TestAssertions:
    """自研断言测试。"""

    def test_status_code_passed(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="status_code", expected=200)

        result = registry.execute(spec, _http_result(status_code=200))

        assert result.passed is True
        assert result.actual == 200
        assert result.expected == 200

    def test_status_code_failed(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="status_code", expected=200)

        result = registry.execute(spec, _http_result(status_code=500))

        assert result.passed is False
        assert result.actual == 500
        assert "期望 200" in result.message
        assert "实际 500" in result.message

    def test_json_path_passed(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="json_path", path="$.data.items[0].name", expected="book")
        response = _http_result(body=b'{"data":{"items":[{"name":"book"}]}}')

        result = registry.execute(spec, response)

        assert result.passed is True
        assert result.actual == "book"
        assert result.path == "$.data.items[0].name"

    def test_json_path_failed_with_actual_value(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="json_path", path="$.status", expected="ok")

        result = registry.execute(spec, _http_result(body=b'{"status":"fail"}'))

        assert result.passed is False
        assert result.actual == "fail"
        assert "期望 ok" in result.message
        assert "实际 fail" in result.message

    def test_json_path_failed_when_path_missing(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="json_path", path="$.missing", expected="ok")

        result = registry.execute(spec, _http_result())

        assert result.passed is False
        assert result.actual is None
        assert "未找到字段 missing" in result.message

    def test_json_path_failed_when_list_index_out_of_range(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="json_path", path="$.items[2]", expected="book")

        result = registry.execute(spec, _http_result(body=b'{"items":["pen"]}'))

        assert result.passed is False
        assert result.actual is None
        assert "索引" in result.message or "range" in result.message

    def test_body_contains_passed(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="body_contains", expected="ok")

        result = registry.execute(spec, _http_result())

        assert result.passed is True
        assert "ok" in result.actual

    def test_body_contains_failed(self) -> None:
        registry = create_default_registry()
        spec = AssertionSpec(type="body_contains", expected="missing")

        result = registry.execute(spec, _http_result())

        assert result.passed is False
        assert "不包含 missing" in result.message

    def test_unknown_assertion_type_returns_structured_failure(self) -> None:
        registry = AssertionRegistry()
        spec = AssertionSpec(type="unknown", expected=True)

        result = registry.execute(spec, _http_result())

        assert result.passed is False
        assert result.type == "unknown"
        assert "未知断言类型" in result.message

    def test_hard_mode_stops_following_assertions(self) -> None:
        registry = create_default_registry()
        specs = [
            AssertionSpec(type="status_code", expected=201, mode="hard"),
            AssertionSpec(type="body_contains", expected="ok"),
        ]

        results = registry.execute_all(specs, _http_result(status_code=200))

        assert len(results) == 1
        assert results[0].passed is False

    def test_soft_mode_continues_following_assertions(self) -> None:
        registry = create_default_registry()
        specs = [
            AssertionSpec(type="status_code", expected=201, mode="soft"),
            AssertionSpec(type="body_contains", expected="ok"),
        ]

        results = registry.execute_all(specs, _http_result(status_code=200))

        assert len(results) == 2
        assert results[0].passed is False
        assert results[1].passed is True
