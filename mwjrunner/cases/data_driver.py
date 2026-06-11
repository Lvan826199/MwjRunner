"""数据驱动展开模块。"""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from mwjrunner.cases.errors import CaseLoadError
from mwjrunner.cases.model import TestCase


def expand_data_driven(case: TestCase) -> list[TestCase]:
    """将数据驱动用例展开为多个独立 case instance。

    如果用例没有 data 或 data_file，返回原始用例列表。
    每组数据生成一个独立 case instance，数据注入到 case variables。
    """
    if case.data is None and case.data_file is None:
        return [case]

    data_rows = _load_data(case)
    if not data_rows:
        # 区分"未配置数据驱动"与"配置了但数据为空"，避免静默退化为无数据执行
        raise CaseLoadError(
            case.source_file or "<unknown>",
            "data" if case.data is not None else "data_file",
            "数据驱动已配置但数据为空。",
            "请提供至少一组数据，或移除 data/data_file 字段。",
        )

    instances: list[TestCase] = []
    for index, row in enumerate(data_rows):
        merged_variables = {**case.variables, **row}
        instance = replace(
            case,
            name=f"{case.name} [data#{index}]",
            variables=merged_variables,
            data=None,
            data_file=None,
        )
        instances.append(instance)
    return instances


def _load_data(case: TestCase) -> list[dict[str, Any]]:
    """加载数据驱动数据。优先使用 inline data，其次 data_file。"""
    if case.data is not None:
        return case.data

    if case.data_file is not None:
        return _load_data_file(case.data_file, case.source_file)

    return []


def _load_data_file(data_file: str, source_file: str | None) -> list[dict[str, Any]]:
    """从外部文件加载数据。路径相对于用例文件所在目录解析。"""
    base_dir = Path(source_file).parent if source_file is not None else Path.cwd()

    file_path = base_dir / data_file
    if not file_path.is_file():
        raise CaseLoadError(
            source_file or "<unknown>",
            "data_file",
            f"数据文件不存在: {file_path}",
            "请确认 data_file 路径正确，路径相对于用例文件所在目录。",
        )

    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return _load_json_data(file_path, source_file)
    if suffix == ".csv":
        return _load_csv_data(file_path, source_file)
    raise CaseLoadError(
        source_file or "<unknown>",
        "data_file",
        f"不支持的数据文件格式: {suffix}",
        "支持的格式: .json, .csv",
    )


def _load_json_data(file_path: Path, source_file: str | None) -> list[dict[str, Any]]:
    """加载 JSON 数据文件（list of objects）。"""
    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseLoadError(
            source_file or "<unknown>",
            "data_file",
            f"JSON 数据文件读取失败: {exc}",
            "请确认文件为有效 JSON 格式，内容为 list of objects。",
        ) from exc

    if not isinstance(data, list):
        raise CaseLoadError(
            source_file or "<unknown>",
            "data_file",
            "JSON 数据文件内容必须是数组。",
            "请使用 [{...}, {...}] 格式。",
        )
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise CaseLoadError(
                source_file or "<unknown>",
                f"data_file[{index}]",
                "JSON 数据文件每条记录必须是对象。",
                '请使用 {"key": "value"} 格式。',
            )
    return data


def _load_csv_data(file_path: Path, source_file: str | None) -> list[dict[str, Any]]:
    """加载 CSV 数据文件（首行为字段名）。"""
    try:
        with file_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]
    except OSError as exc:
        raise CaseLoadError(
            source_file or "<unknown>",
            "data_file",
            f"CSV 数据文件读取失败: {exc}",
            "请确认文件存在且可读。",
        ) from exc
