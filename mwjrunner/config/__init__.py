"""配置管理模块。"""

from mwjrunner.config.loader import load_config
from mwjrunner.config.model import ProjectConfig

__all__ = ["ProjectConfig", "load_config"]
