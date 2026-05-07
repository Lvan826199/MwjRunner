"""用例模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RequestSpec:
    """单个步骤的 HTTP 请求配置。"""

    method: str
    url: str
    headers: dict[str, Any] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)
    cookies: dict[str, Any] = field(default_factory=dict)
    json: Any | None = None
    data: Any | None = None
    body: str | bytes | None = None
    timeout: float | None = None


@dataclass(frozen=True)
class AssertionSpec:
    """断言配置。"""

    type: str
    expected: Any
    path: str | None = None
    target: str | None = None
    mode: str = "soft"


@dataclass(frozen=True)
class ExtractSpec:
    """变量提取配置。"""

    name: str
    type: str
    path: str
    optional: bool = False


@dataclass(frozen=True)
class TestStep:
    """用例步骤。"""

    name: str
    request: RequestSpec
    assertions: list[AssertionSpec] = field(default_factory=list)
    extract: list[ExtractSpec] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TestCase:
    """单个测试用例。"""

    name: str
    steps: list[TestStep]
    variables: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    source_file: str | None = None
