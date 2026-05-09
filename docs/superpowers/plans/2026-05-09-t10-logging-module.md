# T10 Logging Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MwjRunner's logging module with run_id-aware console/file logging and sensitive-field redaction.

**Architecture:** Add a focused `mwjrunner/logging/` package that wraps Python standard-library `logging` behind project APIs. The module owns logging configuration, run_id injection, and log-message redaction, while staying independent from execution, assertions, HTTP, variables, and reports. T10 keeps redaction local to logging; T11 will later consolidate shared redaction for reports and logs.

**Tech Stack:** Python 3.13, standard-library `logging`, `dataclasses`, `pathlib`, `re`, pytest for development tests only, UV command execution.

---

## File Structure

- Create `mwjrunner/logging/config.py`: `LogConfig` dataclass and log-level normalization.
- Create `mwjrunner/logging/redaction.py`: recursive sensitive-data redaction and string redaction.
- Create `mwjrunner/logging/context.py`: `RunIdFilter` that injects `run_id` into log records.
- Create `mwjrunner/logging/setup.py`: `configure_logging()` and handler setup.
- Create `mwjrunner/logging/__init__.py`: public logging module exports.
- Create `tests/unit/logging/__init__.py`: unit test package marker.
- Create `tests/unit/logging/test_redaction.py`: redaction behavior tests.
- Create `tests/unit/logging/test_setup.py`: logger setup, run_id, file logging, level, and report-independence tests.
- Modify `doc/下一步计划.md`: mark T10 complete after implementation.
- Modify `doc/开发问题跟踪.md`: add any P0-P3 issues discovered during implementation.

---

### Task 1: Redaction primitives

**Files:**
- Create: `mwjrunner/logging/redaction.py`
- Create: `mwjrunner/logging/__init__.py`
- Create: `tests/unit/logging/__init__.py`
- Test: `tests/unit/logging/test_redaction.py`

- [ ] **Step 1: Write the failing redaction tests**

Create `tests/unit/logging/__init__.py` as an empty file.

Create `tests/unit/logging/test_redaction.py`:

```python
"""日志脱敏测试。"""

from __future__ import annotations

from mwjrunner.logging.redaction import REDACTED, redact_text, redact_value


def test_redact_value_masks_sensitive_mapping_keys() -> None:
    data = {
        "Authorization": "Bearer raw-token",
        "username": "admin",
        "password": "raw-password",
        "nested": {
            "access_token": "raw-access-token",
            "profile": {"name": "admin", "secret": "raw-secret"},
        },
        "items": [
            {"refresh_token": "raw-refresh-token"},
            {"name": "public"},
        ],
    }

    result = redact_value(data)

    assert result["Authorization"] == REDACTED
    assert result["username"] == "admin"
    assert result["password"] == REDACTED
    assert result["nested"]["access_token"] == REDACTED
    assert result["nested"]["profile"]["name"] == "admin"
    assert result["nested"]["profile"]["secret"] == REDACTED
    assert result["items"][0]["refresh_token"] == REDACTED
    assert result["items"][1]["name"] == "public"


def test_redact_value_masks_cookie_values() -> None:
    data = {
        "Cookie": "session=raw-cookie",
        "set-cookie": "session=raw-set-cookie",
        "x-trace-id": "trace-001",
    }

    result = redact_value(data)

    assert result["Cookie"] == REDACTED
    assert result["set-cookie"] == REDACTED
    assert result["x-trace-id"] == "trace-001"


def test_redact_text_masks_key_value_patterns() -> None:
    message = (
        "login token=raw-token password: raw-password "
        "authorization=Bearer raw-auth cookie: session=raw-cookie user=admin"
    )

    result = redact_text(message)

    assert "raw-token" not in result
    assert "raw-password" not in result
    assert "raw-auth" not in result
    assert "raw-cookie" not in result
    assert "user=admin" in result
    assert result.count(REDACTED) == 4
```

- [ ] **Step 2: Run redaction tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/logging/test_redaction.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mwjrunner.logging'` or missing redaction symbols.

- [ ] **Step 3: Implement redaction primitives**

Create `mwjrunner/logging/redaction.py`:

```python
"""日志敏感信息脱敏。"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"
SENSITIVE_KEYS = (
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "cookie",
    "set_cookie",
)

_TEXT_PATTERNS = tuple(
    re.compile(rf"(?i)({key.replace('_', '[-_]?')}\s*[:=]\s*)([^\s,;]+)") for key in SENSITIVE_KEYS
)


def redact_value(value: Any, key: str | None = None) -> Any:
    """递归脱敏常见敏感字段。"""
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {item_key: redact_value(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    """脱敏字符串中的常见 key=value 和 key: value 片段。"""
    redacted = text
    for pattern in _TEXT_PATTERNS:
        redacted = pattern.sub(rf"\1{REDACTED}", redacted)
    return redacted


def is_sensitive_key(key: str) -> bool:
    """判断字段名是否敏感。"""
    normalized_key = key.lower().replace("-", "_")
    return any(sensitive_key in normalized_key for sensitive_key in SENSITIVE_KEYS)
```

Create `mwjrunner/logging/__init__.py`:

```python
"""日志模块。"""

from mwjrunner.logging.redaction import REDACTED, is_sensitive_key, redact_text, redact_value

__all__ = [
    "REDACTED",
    "is_sensitive_key",
    "redact_text",
    "redact_value",
]
```

- [ ] **Step 4: Run redaction tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/logging/test_redaction.py -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit redaction primitives**

Run:

```bash
git add "mwjrunner/logging/redaction.py" "mwjrunner/logging/__init__.py" "tests/unit/logging/__init__.py" "tests/unit/logging/test_redaction.py"
git commit -m "$(cat <<'EOF'
feat: 添加日志脱敏基础能力

实现日志模块内的敏感字段递归脱敏和字符串脱敏，为后续日志输出提供安全基础。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

### Task 2: Log configuration and run_id context

**Files:**
- Create: `mwjrunner/logging/config.py`
- Create: `mwjrunner/logging/context.py`
- Modify: `mwjrunner/logging/__init__.py`
- Test: `tests/unit/logging/test_setup.py`

- [ ] **Step 1: Write failing config and context tests**

Create `tests/unit/logging/test_setup.py`:

```python
"""日志初始化测试。"""

from __future__ import annotations

import logging

import pytest

from mwjrunner.logging import LogConfig
from mwjrunner.logging.config import normalize_log_level
from mwjrunner.logging.context import RunIdFilter


def test_log_config_defaults() -> None:
    config = LogConfig(run_id="run-logging-001")

    assert config.level == "INFO"
    assert config.run_id == "run-logging-001"
    assert config.log_file is None
    assert config.console is True


def test_normalize_log_level_accepts_supported_levels() -> None:
    assert normalize_log_level("debug") == logging.DEBUG
    assert normalize_log_level("INFO") == logging.INFO
    assert normalize_log_level("warning") == logging.WARNING
    assert normalize_log_level("ERROR") == logging.ERROR
    assert normalize_log_level("critical") == logging.CRITICAL


def test_normalize_log_level_rejects_unknown_level() -> None:
    with pytest.raises(ValueError, match="不支持的日志级别"):
        normalize_log_level("verbose")


def test_run_id_filter_injects_run_id() -> None:
    record = logging.LogRecord(
        name="mwjrunner",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    result = RunIdFilter("run-filter-001").filter(record)

    assert result is True
    assert record.run_id == "run-filter-001"
```

- [ ] **Step 2: Run setup tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: FAIL with missing `LogConfig`, `normalize_log_level`, or `RunIdFilter`.

- [ ] **Step 3: Implement config and context modules**

Create `mwjrunner/logging/config.py`:

```python
"""日志配置。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


@dataclass(frozen=True)
class LogConfig:
    """MwjRunner 日志配置。"""

    level: str = "INFO"
    run_id: str = "-"
    log_file: Path | None = None
    console: bool = True


def normalize_log_level(level: str) -> int:
    """转换日志级别名称为 logging 标准级别。"""
    normalized_level = level.upper()
    if normalized_level not in _SUPPORTED_LEVELS:
        supported = ", ".join(_SUPPORTED_LEVELS)
        raise ValueError(f"不支持的日志级别: {level}，支持的级别: {supported}")
    return _SUPPORTED_LEVELS[normalized_level]
```

Create `mwjrunner/logging/context.py`:

```python
"""日志上下文。"""

from __future__ import annotations

import logging


class RunIdFilter(logging.Filter):
    """为日志记录注入 run_id。"""

    def __init__(self, run_id: str = "-") -> None:
        super().__init__()
        self.run_id = run_id or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        """注入 run_id 并允许日志继续输出。"""
        record.run_id = self.run_id
        return True
```

Update `mwjrunner/logging/__init__.py`:

```python
"""日志模块。"""

from mwjrunner.logging.config import LogConfig, normalize_log_level
from mwjrunner.logging.context import RunIdFilter
from mwjrunner.logging.redaction import REDACTED, is_sensitive_key, redact_text, redact_value

__all__ = [
    "REDACTED",
    "LogConfig",
    "RunIdFilter",
    "is_sensitive_key",
    "normalize_log_level",
    "redact_text",
    "redact_value",
]
```

- [ ] **Step 4: Run setup tests to verify config and context pass**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 5: Run all logging tests**

Run:

```bash
uv run pytest tests/unit/logging -q
```

Expected: PASS with `7 passed`.

- [ ] **Step 6: Commit config and context**

Run:

```bash
git add "mwjrunner/logging/config.py" "mwjrunner/logging/context.py" "mwjrunner/logging/__init__.py" "tests/unit/logging/test_setup.py"
git commit -m "$(cat <<'EOF'
feat: 添加日志配置和 run_id 上下文

封装日志级别配置与 run_id 注入能力，为日志初始化和报告关联提供稳定接口。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

### Task 3: Logger setup with console and file handlers

**Files:**
- Create: `mwjrunner/logging/setup.py`
- Modify: `mwjrunner/logging/__init__.py`
- Modify: `tests/unit/logging/test_setup.py`

- [ ] **Step 1: Add failing logger setup tests**

Append to `tests/unit/logging/test_setup.py`:

```python
from mwjrunner.logging import configure_logging


def test_configure_logging_writes_run_id_to_console(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(LogConfig(run_id="run-console-001"))

    logger.info("hello")

    captured = capsys.readouterr()
    assert "run_id=run-console-001" in captured.err
    assert "hello" in captured.err


def test_configure_logging_writes_file_with_run_id(tmp_path) -> None:
    log_file = tmp_path / "logs" / "mwjrunner.log"
    logger = configure_logging(LogConfig(run_id="run-file-001", log_file=log_file, console=False))

    logger.info("file log")

    content = log_file.read_text(encoding="utf-8")
    assert "run_id=run-file-001" in content
    assert "file log" in content


def test_configure_logging_honors_log_level(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(LogConfig(level="ERROR", run_id="run-level-001"))

    logger.info("hidden info")
    logger.error("visible error")

    captured = capsys.readouterr()
    assert "hidden info" not in captured.err
    assert "visible error" in captured.err


def test_configure_logging_replaces_existing_handlers(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(LogConfig(run_id="run-first"))
    logger = configure_logging(LogConfig(run_id="run-second"))

    logger.warning("single message")

    captured = capsys.readouterr()
    assert captured.err.count("single message") == 1
    assert "run_id=run-second" in captured.err
    assert "run_id=run-first" not in captured.err
```

- [ ] **Step 2: Run setup tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: FAIL with missing `configure_logging`.

- [ ] **Step 3: Implement logger setup**

Create `mwjrunner/logging/setup.py`:

```python
"""日志初始化。"""

from __future__ import annotations

import logging
import sys

from mwjrunner.logging.config import LogConfig, normalize_log_level
from mwjrunner.logging.context import RunIdFilter

_LOG_FORMAT = "%(asctime)s %(levelname)s [run_id=%(run_id)s] %(name)s - %(message)s"
_LOGGER_NAME = "mwjrunner"


def configure_logging(config: LogConfig) -> logging.Logger:
    """初始化并返回 MwjRunner 项目 logger。"""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    logger.filters.clear()
    logger.propagate = False

    level = normalize_log_level(config.level)
    logger.setLevel(level)

    run_id_filter = RunIdFilter(config.run_id)
    formatter = logging.Formatter(_LOG_FORMAT)

    if config.console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(run_id_filter)
        logger.addHandler(console_handler)

    if config.log_file is not None:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(run_id_filter)
        logger.addHandler(file_handler)

    return logger
```

Update `mwjrunner/logging/__init__.py`:

```python
"""日志模块。"""

from mwjrunner.logging.config import LogConfig, normalize_log_level
from mwjrunner.logging.context import RunIdFilter
from mwjrunner.logging.redaction import REDACTED, is_sensitive_key, redact_text, redact_value
from mwjrunner.logging.setup import configure_logging

__all__ = [
    "REDACTED",
    "LogConfig",
    "RunIdFilter",
    "configure_logging",
    "is_sensitive_key",
    "normalize_log_level",
    "redact_text",
    "redact_value",
]
```

- [ ] **Step 4: Run setup tests to verify logger setup passes**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: PASS with `8 passed`.

- [ ] **Step 5: Run all logging tests**

Run:

```bash
uv run pytest tests/unit/logging -q
```

Expected: PASS with `11 passed`.

- [ ] **Step 6: Commit logger setup**

Run:

```bash
git add "mwjrunner/logging/setup.py" "mwjrunner/logging/__init__.py" "tests/unit/logging/test_setup.py"
git commit -m "$(cat <<'EOF'
feat: 添加日志初始化能力

支持控制台和文件日志输出，并在日志格式中稳定注入 run_id。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

### Task 4: Redacting log formatter

**Files:**
- Modify: `mwjrunner/logging/setup.py`
- Modify: `tests/unit/logging/test_setup.py`

- [ ] **Step 1: Add failing log-output redaction tests**

Append to `tests/unit/logging/test_setup.py`:

```python

def test_configure_logging_redacts_sensitive_console_output(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(LogConfig(run_id="run-redact-console"))

    logger.info("login token=raw-token password: raw-password user=admin")

    captured = capsys.readouterr()
    assert "raw-token" not in captured.err
    assert "raw-password" not in captured.err
    assert "token=***REDACTED***" in captured.err
    assert "password: ***REDACTED***" in captured.err
    assert "user=admin" in captured.err


def test_configure_logging_redacts_sensitive_file_output(tmp_path) -> None:
    log_file = tmp_path / "mwjrunner.log"
    logger = configure_logging(LogConfig(run_id="run-redact-file", log_file=log_file, console=False))

    logger.warning("authorization=Bearer raw-auth cookie: raw-cookie trace=public")

    content = log_file.read_text(encoding="utf-8")
    assert "raw-auth" not in content
    assert "raw-cookie" not in content
    assert "authorization=***REDACTED***" in content
    assert "cookie: ***REDACTED***" in content
    assert "trace=public" in content
```

- [ ] **Step 2: Run setup tests to verify redaction tests fail**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: FAIL because raw sensitive values still appear in log output.

- [ ] **Step 3: Implement redacting formatter**

Update `mwjrunner/logging/setup.py`:

```python
"""日志初始化。"""

from __future__ import annotations

import logging
import sys

from mwjrunner.logging.config import LogConfig, normalize_log_level
from mwjrunner.logging.context import RunIdFilter
from mwjrunner.logging.redaction import redact_text

_LOG_FORMAT = "%(asctime)s %(levelname)s [run_id=%(run_id)s] %(name)s - %(message)s"
_LOGGER_NAME = "mwjrunner"


class RedactingFormatter(logging.Formatter):
    """输出日志前脱敏消息内容。"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化并脱敏日志文本。"""
        formatted = super().format(record)
        return redact_text(formatted)


def configure_logging(config: LogConfig) -> logging.Logger:
    """初始化并返回 MwjRunner 项目 logger。"""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    logger.filters.clear()
    logger.propagate = False

    level = normalize_log_level(config.level)
    logger.setLevel(level)

    run_id_filter = RunIdFilter(config.run_id)
    formatter = RedactingFormatter(_LOG_FORMAT)

    if config.console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(run_id_filter)
        logger.addHandler(console_handler)

    if config.log_file is not None:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(run_id_filter)
        logger.addHandler(file_handler)

    return logger
```

- [ ] **Step 4: Run setup tests to verify redaction passes**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py -q
```

Expected: PASS with `10 passed`.

- [ ] **Step 5: Run all logging tests**

Run:

```bash
uv run pytest tests/unit/logging -q
```

Expected: PASS with `13 passed`.

- [ ] **Step 6: Commit redacting formatter**

Run:

```bash
git add "mwjrunner/logging/setup.py" "tests/unit/logging/test_setup.py"
git commit -m "$(cat <<'EOF'
feat: 脱敏日志输出内容

在日志格式化阶段统一脱敏敏感字段，避免控制台和文件日志泄露凭据。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

### Task 5: Report independence and documentation completion

**Files:**
- Modify: `tests/unit/logging/test_setup.py`
- Modify: `doc/下一步计划.md`
- Modify: `doc/开发问题跟踪.md` if implementation discovers P0-P3 issues

- [ ] **Step 1: Add report-independence test**

Append to `tests/unit/logging/test_setup.py`:

```python

def test_logging_setup_does_not_import_reports() -> None:
    import mwjrunner.logging.config as logging_config
    import mwjrunner.logging.context as logging_context
    import mwjrunner.logging.redaction as logging_redaction
    import mwjrunner.logging.setup as logging_setup

    imported_modules = {
        logging_config.__name__,
        logging_context.__name__,
        logging_redaction.__name__,
        logging_setup.__name__,
    }

    assert "mwjrunner.reports" not in imported_modules
    assert not any(name.startswith("mwjrunner.reports.") for name in imported_modules)
```

- [ ] **Step 2: Run report-independence test**

Run:

```bash
uv run pytest tests/unit/logging/test_setup.py::test_logging_setup_does_not_import_reports -q
```

Expected: PASS.

- [ ] **Step 3: Mark T10 complete in plan document**

Update `doc/下一步计划.md` current T10 section from:

```markdown
状态：待开始
```

to:

```markdown
状态：已完成
```

Insert after the T10 `目标` block and before `范围`:

```markdown
实际结果：

- 新增 `mwjrunner/logging/` 包，包含日志配置、run_id 上下文、敏感信息脱敏和日志初始化入口。
- 支持控制台日志和文件日志输出。
- 日志格式包含 `run_id`，用于后续关联 JSON / HTML 报告。
- 日志输出阶段会脱敏 token、password、cookie、secret、authorization 等敏感字段。
- 日志模块不依赖 `mwjrunner.reports`，保持日志与报告生成解耦。
- 补充日志脱敏、日志级别、控制台输出、文件输出和模块边界单元测试。
```

- [ ] **Step 4: Run all logging tests**

Run:

```bash
uv run pytest tests/unit/logging -q
```

Expected: PASS with `14 passed`.

- [ ] **Step 5: Run full unit tests**

Run:

```bash
uv run pytest tests/unit -q
```

Expected: PASS. Existing expected baseline before T10 was `52 passed, 1 skipped`; after T10 it should include the new logging tests.

- [ ] **Step 6: Run targeted Ruff checks**

Run:

```bash
uv run ruff format --check mwjrunner/logging tests/unit/logging
uv run ruff check mwjrunner/logging tests/unit/logging
```

Expected: formatting check passes and Ruff reports `All checks passed!`.

- [ ] **Step 7: Commit final T10 documentation and tests**

Run:

```bash
git add "tests/unit/logging/test_setup.py" "doc/下一步计划.md" "doc/开发问题跟踪.md"
git commit -m "$(cat <<'EOF'
docs: 完成 T10 日志模块记录

同步日志模块完成状态和问题跟踪信息，确保后续任务计划与实现保持一致。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

### Task 6: T10 final review and quality gate

**Files:**
- Review all changed files from T10 implementation.
- No new files expected unless review discovers a required fix.

- [ ] **Step 1: Check worktree and diff**

Run:

```bash
git status -sb
git diff --stat
git diff
git diff --cached
```

Expected: clean working tree, or only intentional review fixes.

- [ ] **Step 2: Run complete validation**

Run:

```bash
uv run pytest tests/unit -q
uv run ruff format --check mwjrunner/logging tests/unit/logging
uv run ruff check mwjrunner/logging tests/unit/logging
```

Expected: all commands pass.

- [ ] **Step 3: Perform MwjRunner code review**

Use project `code-review` skill with this scope:

```text
T10 日志模块实现提交前审查，重点检查日志模块与报告模块解耦、pytest/Allure 核心禁用、run_id 注入、控制台/文件日志、敏感信息脱敏、文档同步和 P0-P3 问题跟踪。
```

Expected: P0/P1 为无。如发现 P0/P1， fix before continuing.

- [ ] **Step 4: Commit any review fixes**

If review finds fixable issues, stage only the specific files changed and commit:

```bash
git add "specific/file.py" "specific/test_file.py" "specific/doc.md"
git commit -m "$(cat <<'EOF'
fix: 修复 T10 日志审查问题

根据提交前审查修复日志模块边界、脱敏或文档一致性问题。

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds, or no commit is needed if no issues were found.

- [ ] **Step 5: Final status check**

Run:

```bash
git status -sb
```

Expected: clean working tree on `master` ahead of remote by the new T10 commits.
