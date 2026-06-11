"""用例文件发现模块。"""

from __future__ import annotations

from pathlib import Path

DEFAULT_PATTERNS = ("**/*.yaml", "**/*.yml")

# 目录递归时排除的非用例内容：项目配置文件与环境/报告目录
_EXCLUDED_FILE_NAMES = ("mwjrunner.yaml", "mwjrunner.yml")
_EXCLUDED_DIR_NAMES = ("envs", "reports")


def discover_case_files(
    path: str | Path,
    *,
    patterns: tuple[str, ...] | None = None,
) -> list[Path]:
    """发现指定路径下的用例文件。

    如果 path 是文件，直接返回该文件。
    如果 path 是目录，递归发现匹配 patterns 的文件（跳过 _ 开头的文件，
    并排除 mwjrunner.yaml 配置文件和 envs/、reports/ 目录）。
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
            if not file_path.is_file() or file_path.name.startswith("_"):
                continue
            if file_path.name in _EXCLUDED_FILE_NAMES:
                continue
            relative_parts = file_path.relative_to(target).parts[:-1]
            if any(part in _EXCLUDED_DIR_NAMES for part in relative_parts):
                continue
            found.add(file_path)

    return sorted(found)
