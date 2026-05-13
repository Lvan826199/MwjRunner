"""用例文件发现模块测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mwjrunner.cases.discovery import discover_case_files


@pytest.fixture
def case_dir(tmp_path: Path) -> Path:
    """创建包含多个用例文件的临时目录。"""
    (tmp_path / "health.yaml").write_text("name: health", encoding="utf-8")
    (tmp_path / "login.yml").write_text("name: login", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.yaml").write_text("name: nested", encoding="utf-8")
    (tmp_path / "_helper.yaml").write_text("name: helper", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# readme", encoding="utf-8")
    return tmp_path


def test_discover_single_file(tmp_path: Path) -> None:
    """单文件路径直接返回该文件。"""
    file = tmp_path / "test.yaml"
    file.write_text("name: test", encoding="utf-8")
    result = discover_case_files(file)
    assert result == [file]


def test_discover_directory(case_dir: Path) -> None:
    """目录递归发现 yaml/yml 文件，跳过 _ 开头文件。"""
    result = discover_case_files(case_dir)
    names = [f.name for f in result]
    assert "health.yaml" in names
    assert "login.yml" in names
    assert "nested.yaml" in names
    assert "_helper.yaml" not in names
    assert "readme.md" not in names


def test_discover_directory_sorted(case_dir: Path) -> None:
    """返回结果按路径字典序排列。"""
    result = discover_case_files(case_dir)
    assert result == sorted(result)


def test_discover_empty_directory(tmp_path: Path) -> None:
    """空目录返回空列表。"""
    result = discover_case_files(tmp_path)
    assert result == []


def test_discover_nonexistent_path(tmp_path: Path) -> None:
    """不存在的路径返回空列表。"""
    result = discover_case_files(tmp_path / "nonexistent")
    assert result == []


def test_discover_custom_pattern(case_dir: Path) -> None:
    """自定义 pattern 只匹配指定模式。"""
    result = discover_case_files(case_dir, patterns=("**/*.yml",))
    names = [f.name for f in result]
    assert "login.yml" in names
    assert "health.yaml" not in names
