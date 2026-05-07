"""用例加载模块单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mwjrunner.cases import CaseLoadError, load_yaml_case


@pytest.mark.unit
class TestYAMLCaseLoader:
    """YAML 用例加载器测试。"""

    def test_load_valid_minimal_case(self, tmp_path: Path) -> None:
        """测试加载最小有效用例。"""
        case_file = tmp_path / "minimal.yaml"
        case_file.write_text(
            """
name: 最小用例
steps:
  - name: 步骤1
    request:
      method: GET
      url: /test
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert case.name == "最小用例"
        assert len(case.steps) == 1
        assert case.steps[0].name == "步骤1"
        assert case.steps[0].request.method == "GET"
        assert case.steps[0].request.url == "/test"

    def test_load_case_with_tags_and_variables(self, tmp_path: Path) -> None:
        """测试加载包含 tags 和 variables 的用例。"""
        case_file = tmp_path / "full.yaml"
        case_file.write_text(
            """
name: 完整用例
tags: [smoke, auth]
variables:
  base_url: http://localhost:8000
  timeout: 10
steps:
  - name: 登录
    request:
      method: POST
      url: /login
      json:
        username: test
        password: pass123
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert case.name == "完整用例"
        assert case.tags == ["smoke", "auth"]
        assert case.variables == {"base_url": "http://localhost:8000", "timeout": 10}
        assert len(case.steps) == 1

    def test_load_case_with_assertions(self, tmp_path: Path) -> None:
        """测试加载包含断言的用例。"""
        case_file = tmp_path / "with_assertions.yaml"
        case_file.write_text(
            """
name: 断言用例
steps:
  - name: 健康检查
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: ok
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert len(case.steps[0].assertions) == 2
        assert case.steps[0].assertions[0].type == "status_code"
        assert case.steps[0].assertions[0].expected == 200
        assert case.steps[0].assertions[1].type == "json_path"
        assert case.steps[0].assertions[1].path == "$.status"
        assert case.steps[0].assertions[1].expected == "ok"

    def test_load_case_with_extract_shorthand(self, tmp_path: Path) -> None:
        """测试加载包含提取变量简写语法的用例。"""
        case_file = tmp_path / "with_extract.yaml"
        case_file.write_text(
            """
name: 提取用例
steps:
  - name: 登录
    request:
      method: POST
      url: /login
    extract:
      token: $.data.token
      user_id: $.data.user_id
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert len(case.steps[0].extract) == 2
        assert case.steps[0].extract[0].name == "token"
        assert case.steps[0].extract[0].type == "json_path"
        assert case.steps[0].extract[0].path == "$.data.token"
        assert case.steps[0].extract[1].name == "user_id"

    def test_load_case_with_extract_object_syntax(self, tmp_path: Path) -> None:
        """测试加载包含提取变量对象语法的用例。"""
        case_file = tmp_path / "with_extract_obj.yaml"
        case_file.write_text(
            """
name: 提取用例对象语法
steps:
  - name: 登录
    request:
      method: POST
      url: /login
    extract:
      token:
        type: json_path
        path: $.data.token
        optional: false
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert len(case.steps[0].extract) == 1
        assert case.steps[0].extract[0].name == "token"
        assert case.steps[0].extract[0].type == "json_path"
        assert case.steps[0].extract[0].path == "$.data.token"
        assert case.steps[0].extract[0].optional is False

    def test_missing_name_raises_error(self, tmp_path: Path) -> None:
        """测试缺少 name 字段时抛出错误。"""
        case_file = tmp_path / "no_name.yaml"
        case_file.write_text(
            """
steps:
  - name: 步骤1
    request:
      method: GET
      url: /test
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "name" in exc_info.value.field
        assert "必填字段" in exc_info.value.message

    def test_missing_steps_raises_error(self, tmp_path: Path) -> None:
        """测试缺少 steps 字段时抛出错误。"""
        case_file = tmp_path / "no_steps.yaml"
        case_file.write_text(
            """
name: 无步骤用例
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "steps" in exc_info.value.field
        assert "缺少必填字段" in exc_info.value.message

    def test_empty_steps_raises_error(self, tmp_path: Path) -> None:
        """测试空 steps 列表时抛出错误。"""
        case_file = tmp_path / "empty_steps.yaml"
        case_file.write_text(
            """
name: 空步骤用例
steps: []
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "steps" in exc_info.value.field
        assert "非空列表" in exc_info.value.message

    def test_missing_request_raises_error(self, tmp_path: Path) -> None:
        """测试步骤缺少 request 字段时抛出错误。"""
        case_file = tmp_path / "no_request.yaml"
        case_file.write_text(
            """
name: 无请求用例
steps:
  - name: 步骤1
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "request" in exc_info.value.field
        assert "缺少必填字段" in exc_info.value.message

    def test_missing_method_raises_error(self, tmp_path: Path) -> None:
        """测试请求缺少 method 字段时抛出错误。"""
        case_file = tmp_path / "no_method.yaml"
        case_file.write_text(
            """
name: 无方法用例
steps:
  - name: 步骤1
    request:
      url: /test
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "method" in exc_info.value.field
        assert "缺少必填字段" in exc_info.value.message

    def test_missing_url_raises_error(self, tmp_path: Path) -> None:
        """测试请求缺少 url 字段时抛出错误。"""
        case_file = tmp_path / "no_url.yaml"
        case_file.write_text(
            """
name: 无URL用例
steps:
  - name: 步骤1
    request:
      method: GET
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "url" in exc_info.value.field
        assert "缺少必填字段" in exc_info.value.message

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path) -> None:
        """测试无效 YAML 语法时抛出错误。"""
        case_file = tmp_path / "invalid.yaml"
        case_file.write_text(
            """
name: 无效YAML
steps:
  - name: 步骤1
    request:
      method: GET
      url: /test
    invalid_indent
""",
            encoding="utf-8",
        )

        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case(case_file)

        assert "yaml" in exc_info.value.field.lower()
        assert "YAML 解析失败" in exc_info.value.message

    def test_file_not_found_raises_error(self) -> None:
        """测试文件不存在时抛出错误。"""
        with pytest.raises(CaseLoadError) as exc_info:
            load_yaml_case("nonexistent.yaml")

        assert "file" in exc_info.value.field
        assert "无法读取用例文件" in exc_info.value.message

    def test_method_normalized_to_uppercase(self, tmp_path: Path) -> None:
        """测试 HTTP method 自动转换为大写。"""
        case_file = tmp_path / "lowercase_method.yaml"
        case_file.write_text(
            """
name: 小写方法用例
steps:
  - name: 步骤1
    request:
      method: get
      url: /test
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert case.steps[0].request.method == "GET"

    def test_timeout_converted_to_float(self, tmp_path: Path) -> None:
        """测试 timeout 转换为 float。"""
        case_file = tmp_path / "timeout.yaml"
        case_file.write_text(
            """
name: 超时用例
steps:
  - name: 步骤1
    request:
      method: GET
      url: /test
      timeout: 5
""",
            encoding="utf-8",
        )

        case = load_yaml_case(case_file)

        assert case.steps[0].request.timeout == 5.0
        assert isinstance(case.steps[0].request.timeout, float)
