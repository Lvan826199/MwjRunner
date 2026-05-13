"""用例过滤模块。"""

from __future__ import annotations

from mwjrunner.cases.model import TestCase


def filter_cases(
    cases: list[TestCase],
    *,
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    priority: list[str] | None = None,
) -> list[TestCase]:
    """按标签和优先级过滤用例。

    - tags: 匹配任一标签即保留（OR）
    - exclude_tags: 匹配任一标签即排除
    - priority: 匹配任一优先级即保留
    - 三个条件依次应用：先 include tags，再 exclude tags，再 priority
    """
    result = cases

    if tags:
        tag_set = set(tags)
        result = [c for c in result if tag_set & set(c.tags)]

    if exclude_tags:
        exclude_set = set(exclude_tags)
        result = [c for c in result if not (exclude_set & set(c.tags))]

    if priority:
        priority_set = set(priority)
        result = [c for c in result if c.priority in priority_set]

    return result
