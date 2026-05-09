# T9 Console JSON Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build M1 report primitives: structured run results, Console report output, JSON report output, and exit-code mapping.

**Architecture:** Add a focused `mwjrunner/reports/` package that only consumes structured result objects and never performs case loading, HTTP execution, assertion execution, or scheduling. Report models remain serializable with the Python standard library and can embed already-redacted HTTP snapshots, assertion results, and extract results from existing modules. CLI integration remains out of scope for T9.

**Tech Stack:** Python 3.13, dataclasses, standard-library `json`, `pathlib`, pytest for development tests only, UV command execution.

---

## File Structure

- Create `mwjrunner/reports/model.py`: report dataclasses and `to_dict()` helpers.
- Create `mwjrunner/reports/console.py`: `ConsoleReporter` that renders and prints a text summary.
- Create `mwjrunner/reports/json.py`: `JsonReporter` that converts `RunResult` to JSON text and writes files.
- Create `mwjrunner/reports/exit_code.py`: stable exit-code constants and `resolve_exit_code()`.
- Create `mwjrunner/reports/__init__.py`: public exports.
- Create `tests/unit/reports/__init__.py`: unit test package marker.
- Create `tests/unit/reports/test_model.py`: report model serialization tests.
- Create `tests/unit/reports/test_console.py`: Console reporter tests.
- Create `tests/unit/reports/test_json.py`: JSON reporter tests.
- Create `tests/unit/reports/test_exit_code.py`: exit-code mapping tests.
- Modify `doc/下一步计划.md`: mark T9 complete after implementation and add a later logging module task.

## Task 1: Report model serialization

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\model.py`
- Create: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`
- Create: `E:\Y_pythonProject\MwjRunner\tests\unit\reports\__init__.py`
- Test: `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_model.py`

- [ ] **Step 1: Write the failing model serialization test**

Create `E:\Y_pythonProject\MwjRunner\tests\unit\reports\__init__.py` with empty content.

Create `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_model.py`:

```python
"""报告结果模型测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary
from mwjrunner.variables.engine import ExtractResult


def test_run_result_to_dict_contains_required_report_sections() -> None:
    """测试运行结果可以序列化为 JSON 报告所需结构。"""
    started_at = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    ended_at = datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC)
    request = HttpRequest(
        method="GET",
        url="http://127.0.0.1:8000/health",
        headers={"authorization": "***REDACTED***"},
        query={"token": "***REDACTED***"},
    )
    response = HttpResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        cookies={"session": "***REDACTED***"},
        body=b'{"status":"ok"}',
        elapsed_ms=12.5,
    )
    assertion = AssertionResult(
        type="status_code",
        passed=True,
        expected=200,
        actual=200,
        message="status_code 断言通过",
    )
    extract = ExtractResult(
        name="token",
        type="json_path",
        path="$.data.token",
        value="***REDACTED***",
        extracted=True,
        message="变量提取成功",
    )
    step = StepResult(
        name="健康检查",
        status="passed",
        request=request,
        response=response,
        assertions=[assertion],
        extracts=[extract],
        elapsed_ms=12.5,
    )
    case = CaseResult(
        name="健康检查用例",
        source_file="examples/cases/health.yaml",
        status="passed",
        steps=[step],
    )
    summary = Summary(
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        error_cases=0,
        total_steps=1,
        passed_steps=1,
        failed_steps=0,
        error_steps=0,
        total_assertions=1,
        failed_assertions=0,
        total_errors=0,
        elapsed_ms=12.5,
    )
    result = RunResult(
        run_id="run-001",
        started_at=started_at,
        ended_at=ended_at,
        summary=summary,
        cases=[case],
    )

    data = result.to_dict()

    assert data["run_id"] == "run-001"
    assert data["started_at"] == "2026-05-09T10:00:00+00:00"
    assert data["ended_at"] == "2026-05-09T10:00:01+00:00"
    assert data["summary"]["total_cases"] == 1
    assert data["cases"][0]["steps"][0]["request"]["headers"]["authorization"] == "***REDACTED***"
    assert data["cases"][0]["steps"][0]["response"]["status_code"] == 200
    assert data["cases"][0]["steps"][0]["assertions"][0]["passed"] is True
    assert data["cases"][0]["steps"][0]["extracts"][0]["extracted"] is True
    assert data["errors"] == []
```

- [ ] **Step 2: Run the failing model test**

Run:

```bash
uv run pytest tests/unit/reports/test_model.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mwjrunner.reports'`.

- [ ] **Step 3: Implement report model dataclasses**

Create `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\model.py`:

```python
"""报告结果模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.variables.engine import ExtractResult


@dataclass(frozen=True)
class Summary:
    """运行摘要统计。"""

    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    error_steps: int = 0
    total_assertions: int = 0
    failed_assertions: int = 0
    total_errors: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "error_cases": self.error_cases,
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "error_steps": self.error_steps,
            "total_assertions": self.total_assertions,
            "failed_assertions": self.failed_assertions,
            "total_errors": self.total_errors,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class StepResult:
    """单个步骤报告结果。"""

    name: str
    status: str
    request: HttpRequest | None = None
    response: HttpResponse | None = None
    assertions: list[AssertionResult] = field(default_factory=list)
    extracts: list[ExtractResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "name": self.name,
            "status": self.status,
            "request": _request_to_dict(self.request),
            "response": _response_to_dict(self.response),
            "assertions": [_assertion_to_dict(assertion) for assertion in self.assertions],
            "extracts": [_extract_to_dict(extract) for extract in self.extracts],
            "errors": list(self.errors),
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class CaseResult:
    """单个用例报告结果。"""

    name: str
    status: str
    source_file: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "name": self.name,
            "source_file": self.source_file,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class RunResult:
    """一次运行的报告结果。"""

    run_id: str
    started_at: datetime
    ended_at: datetime | None
    summary: Summary
    cases: list[CaseResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON 可序列化字典。"""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at is not None else None,
            "summary": self.summary.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "errors": list(self.errors),
        }


def _request_to_dict(request: HttpRequest | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "query": dict(request.query),
        "cookies": dict(request.cookies),
        "body": _body_to_json_value(request.body),
        "timeout": request.timeout,
    }


def _response_to_dict(response: HttpResponse | None) -> dict[str, Any] | None:
    if response is None:
        return None
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "cookies": dict(response.cookies),
        "body": response.text,
        "elapsed_ms": response.elapsed_ms,
    }


def _assertion_to_dict(assertion: AssertionResult) -> dict[str, Any]:
    return {
        "type": assertion.type,
        "passed": assertion.passed,
        "expected": assertion.expected,
        "actual": assertion.actual,
        "path": assertion.path,
        "target": assertion.target,
        "mode": assertion.mode,
        "message": assertion.message,
    }


def _extract_to_dict(extract: ExtractResult) -> dict[str, Any]:
    return {
        "name": extract.name,
        "type": extract.type,
        "path": extract.path,
        "value": extract.value,
        "extracted": extract.extracted,
        "optional": extract.optional,
        "message": extract.message,
    }


def _body_to_json_value(body: str | bytes | None) -> str | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return body
```

Create `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`:

```python
"""报告模块。"""

from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary

__all__ = [
    "CaseResult",
    "RunResult",
    "StepResult",
    "Summary",
]
```

- [ ] **Step 4: Run the model test**

Run:

```bash
uv run pytest tests/unit/reports/test_model.py -q
```

Expected: PASS.

## Task 2: Console reporter

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\console.py`
- Modify: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`
- Test: `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_console.py`

- [ ] **Step 1: Write the failing Console reporter tests**

Create `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_console.py`:

```python
"""Console 报告测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.assertions.model import AssertionResult
from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary


def test_console_reporter_renders_summary() -> None:
    result = RunResult(
        run_id="run-console-001",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(
            total_cases=1,
            passed_cases=1,
            total_steps=1,
            passed_steps=1,
            total_assertions=1,
            elapsed_ms=15.0,
        ),
    )

    output = ConsoleReporter().render(result)

    assert "MwjRunner 执行摘要" in output
    assert "run-console-001" in output
    assert "用例: 1, 通过: 1, 失败: 0, 错误: 0" in output
    assert "步骤: 1, 通过: 1, 失败: 0, 错误: 0" in output
    assert "断言: 1, 失败: 0" in output
    assert "耗时: 15.0 ms" in output


def test_console_reporter_renders_failure_details() -> None:
    assertion = AssertionResult(
        type="status_code",
        passed=False,
        expected=200,
        actual=500,
        message="status_code 断言失败: 期望 200, 实际 500",
    )
    step = StepResult(
        name="健康检查",
        status="failed",
        assertions=[assertion],
        errors=["响应状态码异常"],
    )
    case = CaseResult(
        name="健康检查用例",
        status="failed",
        steps=[step],
    )
    result = RunResult(
        run_id="run-console-002",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(total_cases=1, failed_cases=1, total_steps=1, failed_steps=1, total_assertions=1, failed_assertions=1, total_errors=1),
        cases=[case],
    )

    output = ConsoleReporter().render(result)

    assert "失败或错误明细" in output
    assert "健康检查用例 / 健康检查" in output
    assert "status_code 断言失败" in output
    assert "响应状态码异常" in output
```

- [ ] **Step 2: Run the failing Console tests**

Run:

```bash
uv run pytest tests/unit/reports/test_console.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mwjrunner.reports.console'`.

- [ ] **Step 3: Implement ConsoleReporter**

Create `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\console.py`:

```python
"""终端报告输出。"""

from __future__ import annotations

from mwjrunner.reports.model import RunResult


class ConsoleReporter:
    """渲染终端摘要报告。"""

    def render(self, result: RunResult) -> str:
        """渲染终端报告文本。"""
        summary = result.summary
        lines = [
            "MwjRunner 执行摘要",
            f"run_id: {result.run_id}",
            f"用例: {summary.total_cases}, 通过: {summary.passed_cases}, 失败: {summary.failed_cases}, 错误: {summary.error_cases}",
            f"步骤: {summary.total_steps}, 通过: {summary.passed_steps}, 失败: {summary.failed_steps}, 错误: {summary.error_steps}",
            f"断言: {summary.total_assertions}, 失败: {summary.failed_assertions}",
            f"错误: {summary.total_errors}",
            f"耗时: {summary.elapsed_ms} ms",
        ]
        details = self._render_failure_details(result)
        if details:
            lines.append("")
            lines.append("失败或错误明细")
            lines.extend(details)
        return "\n".join(lines)

    def write(self, result: RunResult) -> None:
        """输出终端报告文本。"""
        print(self.render(result))

    def _render_failure_details(self, result: RunResult) -> list[str]:
        details: list[str] = []
        for error in result.errors:
            details.append(f"- 运行错误: {error}")
        for case in result.cases:
            for error in case.errors:
                details.append(f"- {case.name}: {error}")
            for step in case.steps:
                prefix = f"{case.name} / {step.name}"
                for assertion in step.assertions:
                    if not assertion.passed:
                        details.append(f"- {prefix}: {assertion.message}")
                for error in step.errors:
                    details.append(f"- {prefix}: {error}")
        return details
```

Update `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`:

```python
"""报告模块。"""

from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary

__all__ = [
    "CaseResult",
    "ConsoleReporter",
    "RunResult",
    "StepResult",
    "Summary",
]
```

- [ ] **Step 4: Run Console tests**

Run:

```bash
uv run pytest tests/unit/reports/test_console.py -q
```

Expected: PASS.

## Task 3: JSON reporter

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\json.py`
- Modify: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`
- Test: `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_json.py`

- [ ] **Step 1: Write the failing JSON reporter tests**

Create `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_json.py`:

```python
"""JSON 报告测试。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from mwjrunner.http.model import HttpRequest, HttpResponse
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary


def _result() -> RunResult:
    step = StepResult(
        name="健康检查",
        status="passed",
        request=HttpRequest(method="GET", url="/health"),
        response=HttpResponse(status_code=200, headers={}, cookies={}, body=b'{"status":"ok"}', elapsed_ms=8.0),
    )
    case = CaseResult(name="健康检查用例", status="passed", steps=[step])
    return RunResult(
        run_id="run-json-001",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=Summary(total_cases=1, passed_cases=1, total_steps=1, passed_steps=1, elapsed_ms=8.0),
        cases=[case],
    )


def test_json_reporter_renders_json_report() -> None:
    output = JsonReporter().render(_result())

    data = json.loads(output)

    assert data["run_id"] == "run-json-001"
    assert data["summary"]["total_cases"] == 1
    assert data["cases"][0]["steps"][0]["request"]["url"] == "/health"
    assert data["cases"][0]["steps"][0]["response"]["status_code"] == 200
    assert "assertions" in data["cases"][0]["steps"][0]
    assert "extracts" in data["cases"][0]["steps"][0]
    assert "errors" in data


def test_json_reporter_writes_json_file(tmp_path) -> None:
    output_file = tmp_path / "mwjrunner-report.json"

    JsonReporter().write(_result(), output_file)

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["run_id"] == "run-json-001"
```

- [ ] **Step 2: Run the failing JSON tests**

Run:

```bash
uv run pytest tests/unit/reports/test_json.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mwjrunner.reports.json'`.

- [ ] **Step 3: Implement JsonReporter**

Create `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\json.py`:

```python
"""JSON 报告输出。"""

from __future__ import annotations

import json
from pathlib import Path

from mwjrunner.reports.model import RunResult


class JsonReporter:
    """渲染和写入 JSON 报告。"""

    def render(self, result: RunResult) -> str:
        """渲染 JSON 报告文本。"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    def write(self, result: RunResult, output_file: str | Path) -> None:
        """写入 JSON 报告文件。"""
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(result) + "\n", encoding="utf-8")
```

Update `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`:

```python
"""报告模块。"""

from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary

__all__ = [
    "CaseResult",
    "ConsoleReporter",
    "JsonReporter",
    "RunResult",
    "StepResult",
    "Summary",
]
```

- [ ] **Step 4: Run JSON tests**

Run:

```bash
uv run pytest tests/unit/reports/test_json.py -q
```

Expected: PASS.

## Task 4: Exit-code mapping

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\exit_code.py`
- Modify: `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`
- Test: `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_exit_code.py`

- [ ] **Step 1: Write the failing exit-code tests**

Create `E:\Y_pythonProject\MwjRunner\tests\unit\reports\test_exit_code.py`:

```python
"""报告退出码映射测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from mwjrunner.reports.exit_code import ASSERTION_FAILED_EXIT_CODE, ERROR_EXIT_CODE, SUCCESS_EXIT_CODE, resolve_exit_code
from mwjrunner.reports.model import RunResult, Summary


def _run_result(summary: Summary, errors: list[str] | None = None) -> RunResult:
    return RunResult(
        run_id="run-exit-code",
        started_at=datetime(2026, 5, 9, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=UTC),
        summary=summary,
        errors=errors or [],
    )


def test_exit_code_success() -> None:
    result = _run_result(Summary(total_cases=1, passed_cases=1))

    assert resolve_exit_code(result) == SUCCESS_EXIT_CODE


def test_exit_code_assertion_failed() -> None:
    result = _run_result(Summary(total_cases=1, failed_cases=1, failed_assertions=1))

    assert resolve_exit_code(result) == ASSERTION_FAILED_EXIT_CODE


def test_exit_code_error() -> None:
    result = _run_result(Summary(total_cases=1, error_cases=1, total_errors=1))

    assert resolve_exit_code(result) == ERROR_EXIT_CODE


def test_exit_code_error_has_priority_over_assertion_failure() -> None:
    result = _run_result(
        Summary(total_cases=1, failed_cases=1, error_cases=1, failed_assertions=1, total_errors=1),
        errors=["加载错误"],
    )

    assert resolve_exit_code(result) == ERROR_EXIT_CODE
```

- [ ] **Step 2: Run the failing exit-code tests**

Run:

```bash
uv run pytest tests/unit/reports/test_exit_code.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mwjrunner.reports.exit_code'`.

- [ ] **Step 3: Implement exit-code mapping**

Create `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\exit_code.py`:

```python
"""报告退出码映射。"""

from __future__ import annotations

from mwjrunner.reports.model import RunResult

SUCCESS_EXIT_CODE = 0
ASSERTION_FAILED_EXIT_CODE = 1
ERROR_EXIT_CODE = 2


def resolve_exit_code(result: RunResult) -> int:
    """根据运行结果返回稳定退出码。"""
    if result.errors or result.summary.total_errors > 0 or result.summary.error_cases > 0 or result.summary.error_steps > 0:
        return ERROR_EXIT_CODE
    if result.summary.failed_assertions > 0 or result.summary.failed_cases > 0 or result.summary.failed_steps > 0:
        return ASSERTION_FAILED_EXIT_CODE
    return SUCCESS_EXIT_CODE
```

Update `E:\Y_pythonProject\MwjRunner\mwjrunner\reports\__init__.py`:

```python
"""报告模块。"""

from mwjrunner.reports.console import ConsoleReporter
from mwjrunner.reports.exit_code import ASSERTION_FAILED_EXIT_CODE, ERROR_EXIT_CODE, SUCCESS_EXIT_CODE, resolve_exit_code
from mwjrunner.reports.json import JsonReporter
from mwjrunner.reports.model import CaseResult, RunResult, StepResult, Summary

__all__ = [
    "ASSERTION_FAILED_EXIT_CODE",
    "CaseResult",
    "ConsoleReporter",
    "ERROR_EXIT_CODE",
    "JsonReporter",
    "RunResult",
    "SUCCESS_EXIT_CODE",
    "StepResult",
    "Summary",
    "resolve_exit_code",
]
```

- [ ] **Step 4: Run exit-code tests**

Run:

```bash
uv run pytest tests/unit/reports/test_exit_code.py -q
```

Expected: PASS.

## Task 5: Documentation sync and logging task planning

**Files:**
- Modify: `E:\Y_pythonProject\MwjRunner\doc\下一步计划.md`

- [ ] **Step 1: Read the plan document**

Read `E:\Y_pythonProject\MwjRunner\doc\下一步计划.md` and locate current T9 and the later task pool.

- [ ] **Step 2: Update current stage and completed T9**

Move T9 into completed tasks with this actual result text:

```markdown
### T9：实现 Console 和 JSON 报告

状态：已完成

优先级：P1

目标：

输出终端摘要和结构化 JSON 报告。

实际结果：

- 新增 `mwjrunner/reports/` 包，包含报告结果模型、Console 报告、JSON 报告和退出码映射。
- `RunResult`、`Summary`、`CaseResult`、`StepResult` 支持转换为 JSON 可序列化字典。
- `ConsoleReporter` 输出运行摘要、统计信息、失败断言和错误明细。
- `JsonReporter` 输出包含 case、step、request、response、assertions、extracts、errors 的结构化 JSON。
- 退出码映射为成功 0、断言失败 1、加载或执行错误 2，错误优先级高于断言失败。
- 补充报告模型、Console 报告、JSON 报告和退出码单元测试。

验收标准：

- 运行成功时退出码为 0。
- 断言失败时退出码为 1。
- 加载错误时退出码为 2。
- JSON 报告包含 case、step、request、response、assertions、extracts、errors。
```

- [ ] **Step 3: Add logging module future task**

Add a later task after T9 or in the following task pool:

```markdown
### T10：实现日志模块

状态：待开始

优先级：P1

目标：

建立 MwjRunner 自有日志初始化和输出能力，让执行过程、报告和后续 CI 排查可以通过 run_id 关联。

范围：

- 日志初始化模块。
- 控制台日志和文件日志。
- run_id 注入日志上下文。
- 复用敏感信息脱敏策略。
- 日志级别配置。

验收标准：

- 每次运行可以生成带 run_id 的日志。
- 控制台和文件日志不明文输出 token、password、cookie、secret、authorization 等敏感字段。
- 日志模块不反向依赖报告模块。
```

- [ ] **Step 4: Set next current task**

Set the current task to T10 logging if the document currently has no higher-priority unfinished task. If there are existing higher-priority tasks, keep their order and place T10 in the task pool.

## Task 6: Full verification and review

**Files:**
- No code files created in this task.

- [ ] **Step 1: Run report unit tests**

Run:

```bash
uv run pytest tests/unit/reports -q
```

Expected: all report tests pass.

- [ ] **Step 2: Run all unit tests**

Run:

```bash
uv run pytest tests/unit -q
```

Expected: all unit tests pass.

- [ ] **Step 3: Run integration tests**

Run:

```bash
NO_PROXY=127.0.0.1,localhost uv run pytest tests/integration -q
```

Expected: existing integration tests pass or skip as before. A known cookie deprecation warning is non-blocking.

- [ ] **Step 4: Run targeted Ruff checks on changed Python files**

Run after implementation:

```bash
uv run ruff check mwjrunner/reports tests/unit/reports
uv run ruff format --check mwjrunner/reports tests/unit/reports
```

Expected: both commands pass.

- [ ] **Step 5: Run project code review skill before commit**

Use project `code-review` skill with this scope:

```text
T9 Console 和 JSON 报告实现提交前审查，重点检查报告与执行逻辑分离、pytest/Allure 核心禁用、退出码映射、JSON 报告字段、敏感信息脱敏和日志模块计划。
```

Expected: no P0/P1 issues before committing.

## Task 7: Commit and push

**Files:**
- Stage exact T9 files only.

- [ ] **Step 1: Inspect final status and diff**

Run:

```bash
git status --short
git diff --stat
git diff --cached --stat
```

Expected: only T9 report implementation, report tests, plan/spec docs, and `doc/下一步计划.md` changes are present.

- [ ] **Step 2: Stage exact files**

Run:

```bash
git add -- "mwjrunner/reports/__init__.py" "mwjrunner/reports/model.py" "mwjrunner/reports/console.py" "mwjrunner/reports/json.py" "mwjrunner/reports/exit_code.py" "tests/unit/reports/__init__.py" "tests/unit/reports/test_model.py" "tests/unit/reports/test_console.py" "tests/unit/reports/test_json.py" "tests/unit/reports/test_exit_code.py" "doc/下一步计划.md" "docs/superpowers/plans/2026-05-09-t9-console-json-report.md"
```

- [ ] **Step 3: Commit with Chinese message**

Run:

```bash
git commit -m "$(cat <<'EOF'
feat: 实现 T9 Console 和 JSON 报告

新增报告结果模型、Console 报告、JSON 报告和退出码映射，为后续执行编排提供稳定的结构化报告基础。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

- [ ] **Step 4: Push current branch**

Run:

```bash
git push
```

Expected: push succeeds.

## Self-Review

- Spec coverage: Tasks 1-4 implement result models, ConsoleReporter, JsonReporter, and exit-code mapping. Task 5 updates `doc/下一步计划.md` and adds the logging module as a future task. Task 6 verifies tests and static checks. Task 7 commits and pushes with a Chinese commit message.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain. Each code step includes concrete file content.
- Type consistency: `Summary`, `RunResult`, `CaseResult`, `StepResult`, `ConsoleReporter`, `JsonReporter`, and `resolve_exit_code` names are consistent across tests, implementation, exports, and documentation.
