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
