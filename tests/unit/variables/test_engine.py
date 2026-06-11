"""变量替换和提取模块单元测试。"""

from __future__ import annotations

import hashlib

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


@pytest.mark.unit
class TestBuiltinFunctions:
    """内置函数化数据生成测试。"""

    def test_timestamp_returns_digits(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__timestamp()}")
        assert result.isdigit()
        assert len(result) == 10

    def test_timestamp_ms(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__timestamp(ms)}")
        assert result.isdigit()
        assert len(result) == 13

    def test_uuid_format(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__uuid()}")
        assert len(result) == 36
        assert result.count("-") == 4

    def test_random_phone_format(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__random_phone()}")
        assert len(result) == 11
        assert result.isdigit()

    def test_random_int_default_range(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__random_int()}")
        assert 0 <= int(result) <= 9999

    def test_random_int_custom_range(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__random_int(100, 200)}")
        assert 100 <= int(result) <= 200

    def test_random_str_default_length(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__random_str()}")
        assert len(result) == 8

    def test_random_str_custom_length(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__random_str(16)}")
        assert len(result) == 16

    def test_md5_hash(self) -> None:
        engine = VariableEngine()
        result = engine.render("${__md5(hello)}")
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_function_in_mixed_string(self) -> None:
        engine = VariableEngine({"name": "test"})
        result = engine.render("user_${name}_${__uuid()}")
        assert result.startswith("user_test_")
        assert len(result) > len("user_test_")

    def test_unknown_function_raises_error(self) -> None:
        engine = VariableEngine()
        with pytest.raises(VariableError, match="未注册的内置函数"):
            engine.render("${__nonexistent()}")


class TestT70Fixes:
    """T70 隐藏 bug 修复回归测试。"""

    def _http_result(self, body: bytes) -> HttpResult:
        return HttpResult(
            request=HttpRequest(method="GET", url="/demo"),
            response=HttpResponse(status_code=200, headers={}, cookies={}, body=body, elapsed_ms=1.0, raw_body=body),
        )

    def test_unresolved_expression_raises_error(self) -> None:
        """拼写错误的变量表达式不再被静默原样输出。"""
        engine = VariableEngine({"name": "demo"})
        with pytest.raises(VariableError, match="无法解析的变量表达式"):
            engine.render("/api/${user.name}")

    def test_quoted_function_argument_is_unwrapped(self) -> None:
        """引号包裹的函数参数应剥离引号（${__timestamp('ms')} 返回毫秒级）。"""
        engine = VariableEngine()
        seconds = int(engine.render("${__timestamp()}"))
        millis = int(engine.render("${__timestamp('ms')}"))
        assert millis > seconds * 100

    def test_quoted_argument_keeps_comma(self) -> None:
        engine = VariableEngine()
        result = engine.render('${__md5("a,b")}')
        assert result == hashlib.md5(b"a,b").hexdigest()

    def test_empty_positional_argument_uses_default(self) -> None:
        """${__random_int(,100)} 空位走默认 min=0，不再错位成 min=100。"""
        engine = VariableEngine()
        for _ in range(20):
            value = int(engine.render("${__random_int(,100)}"))
            assert 0 <= value <= 100

    def test_regex_extract_invalid_pattern_raises_variable_error(self) -> None:
        """非法正则转为 VariableError，不再逃逸为引擎内部错误。"""
        engine = VariableEngine()
        spec = ExtractSpec(name="value", type="regex", path="([invalid")
        with pytest.raises(VariableError, match="正则表达式无效"):
            engine.extract(spec, self._http_result(b"hello"))

    def test_regex_extract_optional_group_not_matched(self) -> None:
        """模式含捕获组但未参与匹配时按提取失败处理，不回退 group(0)。"""
        engine = VariableEngine()
        spec = ExtractSpec(name="value", type="regex", path="(a)?b")
        with pytest.raises(VariableError, match="捕获组未参与匹配"):
            engine.extract(spec, self._http_result(b"b"))

    def test_cookie_extract_returns_raw_value(self) -> None:
        """响应快照保留原始 cookie，提取得到真实值而非脱敏占位符。"""
        result = HttpResult(
            request=HttpRequest(method="GET", url="/demo"),
            response=HttpResponse(
                status_code=200,
                headers={},
                cookies={"session_id": "real-session-value"},
                body=b"{}",
                elapsed_ms=1.0,
            ),
        )
        engine = VariableEngine()
        extract = engine.extract(ExtractSpec(name="sid", type="cookie", path="session_id"), result)
        assert extract.value == "real-session-value"
        assert engine.variables["sid"] == "real-session-value"
