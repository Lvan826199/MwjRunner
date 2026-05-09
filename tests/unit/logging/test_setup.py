"""日志初始化测试。"""

from __future__ import annotations

import logging

import pytest

from mwjrunner.logging import LogConfig, configure_logging
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
