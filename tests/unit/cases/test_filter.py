"""用例过滤模块测试。"""

from __future__ import annotations

from mwjrunner.cases.filter import filter_cases
from mwjrunner.cases.model import RequestSpec, TestCase, TestStep


def _case(name: str, tags: list[str] | None = None, priority: str | None = None) -> TestCase:
    return TestCase(
        name=name,
        steps=[TestStep(name="s", request=RequestSpec(method="GET", url="/"))],
        tags=tags or [],
        priority=priority,
    )


def test_no_filter_returns_all() -> None:
    cases = [_case("a"), _case("b")]
    assert filter_cases(cases) == cases


def test_tags_include() -> None:
    cases = [_case("a", tags=["smoke"]), _case("b", tags=["regression"]), _case("c", tags=["smoke", "auth"])]
    result = filter_cases(cases, tags=["smoke"])
    assert [c.name for c in result] == ["a", "c"]


def test_tags_or_logic() -> None:
    cases = [_case("a", tags=["smoke"]), _case("b", tags=["auth"]), _case("c", tags=["wip"])]
    result = filter_cases(cases, tags=["smoke", "auth"])
    assert [c.name for c in result] == ["a", "b"]


def test_exclude_tags() -> None:
    cases = [_case("a", tags=["smoke"]), _case("b", tags=["wip"]), _case("c", tags=["smoke", "wip"])]
    result = filter_cases(cases, exclude_tags=["wip"])
    assert [c.name for c in result] == ["a"]


def test_priority_filter() -> None:
    cases = [_case("a", priority="P0"), _case("b", priority="P1"), _case("c", priority="P2")]
    result = filter_cases(cases, priority=["P0", "P1"])
    assert [c.name for c in result] == ["a", "b"]


def test_combined_filter() -> None:
    cases = [
        _case("a", tags=["smoke"], priority="P0"),
        _case("b", tags=["smoke"], priority="P2"),
        _case("c", tags=["regression"], priority="P0"),
    ]
    result = filter_cases(cases, tags=["smoke"], priority=["P0"])
    assert [c.name for c in result] == ["a"]


def test_filter_empty_result() -> None:
    cases = [_case("a", tags=["smoke"])]
    result = filter_cases(cases, tags=["regression"])
    assert result == []
