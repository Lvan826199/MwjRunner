"""用例文件发现模块。"""

from __future__ import annotations

from pathlib import Path

DEFAULT_PATTERNS = ("**/*.yaml", "**/*.yml")


def discover_case_files(
    path: str | Path,
    *,
    patterns: tuple[str, ...] | None = None,
) -> list[Path]:
    """发现指定路径下的用例文件。

    如果 path 是文件，直接返回该文件。
    如果 path 是目录，递归发现匹配 patterns 的文件（跳过 _ 开头的文件）。
    返回按路径字典序排列的文件列表。
    """
    target = Path(path)

    if target.is_file():
        return [target]

    if not target.is_dir():
        return []

    if patterns is None:
        patterns = DEFAULT_PATTERNS

    found: set[Path] = set()
    for pattern in patterns:
        for file_path in target.glob(pattern):
            if file_path.is_file() and not file_path.name.startswith("_"):
                found.add(file_path)

    return sorted(found)
