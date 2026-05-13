"""数据驱动展开模块测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mwjrunner.cases.data_driver import expand_data_driven
from mwjrunner.cases.errors import CaseLoadError
from mwjrunner.cases.model import RequestSpec, TestCase, TestStep


def _make_case(
    name: str = "test",
    data: list[dict] | None = None,
    data_file: str | None = None,
    source_file: str | None = None,
) -> TestCase:
    return TestCase(
        name=name,
        steps=[TestStep(name="step1", request=RequestSpec(method="GET", url="/health"))],
        variables={"base_var": "hello"},
        data=data,
        data_file=data_file,
        source_file=source_file,
    )


def test_no_data_returns_original() -> None:
    """无 data 和 data_file 时返回原始用例。"""
    case = _make_case()
    result = expand_data_driven(case)
    assert len(result) == 1
    assert result[0].name == "test"


def test_inline_data_expands() -> None:
    """inline data 展开为多个 instance。"""
    case = _make_case(data=[{"user": "a"}, {"user": "b"}, {"user": "c"}])
    result = expand_data_driven(case)
    assert len(result) == 3
    assert result[0].name == "test [data#0]"
    assert result[0].variables["user"] == "a"
    assert result[0].variables["base_var"] == "hello"
    assert result[2].variables["user"] == "c"


def test_inline_data_overrides_variables() -> None:
    """data 中的变量覆盖 case variables。"""
    case = _make_case(
        data=[{"base_var": "overridden"}],
    )
    result = expand_data_driven(case)
    assert result[0].variables["base_var"] == "overridden"


def test_json_data_file(tmp_path: Path) -> None:
    """JSON 数据文件加载。"""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps([{"x": 1}, {"x": 2}]), encoding="utf-8")
    case = _make_case(data_file="data.json", source_file=str(tmp_path / "case.yaml"))
    result = expand_data_driven(case)
    assert len(result) == 2
    assert result[0].variables["x"] == 1
    assert result[1].variables["x"] == 2


def test_csv_data_file(tmp_path: Path) -> None:
    """CSV 数据文件加载。"""
    data_file = tmp_path / "data.csv"
    data_file.write_text("name,age\nalice,30\nbob,25\n", encoding="utf-8")
    case = _make_case(data_file="data.csv", source_file=str(tmp_path / "case.yaml"))
    result = expand_data_driven(case)
    assert len(result) == 2
    assert result[0].variables["name"] == "alice"
    assert result[1].variables["age"] == "25"


def test_data_file_not_found(tmp_path: Path) -> None:
    """数据文件不存在时抛出 CaseLoadError。"""
    case = _make_case(data_file="missing.json", source_file=str(tmp_path / "case.yaml"))
    with pytest.raises(CaseLoadError, match="数据文件不存在"):
        expand_data_driven(case)


def test_unsupported_data_file_format(tmp_path: Path) -> None:
    """不支持的数据文件格式。"""
    data_file = tmp_path / "data.xlsx"
    data_file.write_text("", encoding="utf-8")
    case = _make_case(data_file="data.xlsx", source_file=str(tmp_path / "case.yaml"))
    with pytest.raises(CaseLoadError, match="不支持的数据文件格式"):
        expand_data_driven(case)


def test_json_data_file_invalid_format(tmp_path: Path) -> None:
    """JSON 数据文件内容不是数组。"""
    data_file = tmp_path / "data.json"
    data_file.write_text('{"key": "value"}', encoding="utf-8")
    case = _make_case(data_file="data.json", source_file=str(tmp_path / "case.yaml"))
    with pytest.raises(CaseLoadError, match="必须是数组"):
        expand_data_driven(case)
