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
