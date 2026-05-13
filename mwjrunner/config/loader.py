"""配置加载器。

配置优先级（高到低）：
1. CLI 参数
2. 系统环境变量
3. 环境配置文件（envs/<name>.yaml）
4. 项目配置文件（mwjrunner.yaml）
5. 内置默认值
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mwjrunner.config.model import AuthConfig, ProjectConfig


class ConfigLoadError(Exception):
    """配置加载错误。"""


def load_config(
    *,
    env: str | None = None,
    project_dir: Path | None = None,
) -> ProjectConfig:
    """加载并合并配置。

    Args:
        env: 环境名称，对应 envs/<env>.yaml
        project_dir: 项目根目录，默认为当前工作目录
    """
    if project_dir is None:
        project_dir = Path.cwd()

    config = ProjectConfig()

    # 加载项目配置文件
    project_config_file = project_dir / "mwjrunner.yaml"
    if project_config_file.is_file():
        project_data = _load_yaml_file(project_config_file)
        _merge_config(config, project_data)

    # 加载环境配置文件
    if env is not None:
        env_file = project_dir / "envs" / f"{env}.yaml"
        if not env_file.is_file():
            raise ConfigLoadError(
                f"环境配置文件不存在: {env_file}\n"
                f"请在项目 envs/ 目录下创建 {env}.yaml 文件。"
            )
        env_data = _load_yaml_file(env_file)
        _merge_config(config, env_data)

    return config


def _load_yaml_file(file_path: Path) -> dict[str, Any]:
    """加载 YAML 配置文件。"""
    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except OSError as exc:
        raise ConfigLoadError(f"无法读取配置文件: {file_path} - {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"配置文件 YAML 解析失败: {file_path} - {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigLoadError(f"配置文件顶层必须是对象: {file_path}")
    return data


def _merge_config(config: ProjectConfig, data: dict[str, Any]) -> None:
    """将配置数据合并到 config 对象（后加载的覆盖先加载的）。"""
    if "base_url" in data:
        config.base_url = data["base_url"]
    if "timeout" in data:
        config.timeout = float(data["timeout"])
    if "verify_ssl" in data:
        config.verify_ssl = bool(data["verify_ssl"])
    if "proxy" in data:
        config.proxy = data["proxy"]
    if "report_dir" in data:
        config.report_dir = data["report_dir"]
    if "retry" in data:
        config.retry = int(data["retry"])
    if "fail_fast" in data:
        config.fail_fast = bool(data["fail_fast"])
    if "workers" in data:
        config.workers = int(data["workers"])
    if "timezone" in data:
        config.timezone = data["timezone"]

    # headers 和 variables 按 key 合并
    if "headers" in data and isinstance(data["headers"], dict):
        config.headers.update(data["headers"])
    if "variables" in data and isinstance(data["variables"], dict):
        config.variables.update(data["variables"])

    # auth 配置
    if "auth" in data and isinstance(data["auth"], dict):
        auth_data = data["auth"]
        config.auth = AuthConfig(
            type=auth_data.get("type", "bearer"),
            token=auth_data.get("token"),
            username=auth_data.get("username"),
            password=auth_data.get("password"),
        )

    # quality_gate 配置
    if "quality_gate" in data and isinstance(data["quality_gate"], dict):
        config.quality_gate = data["quality_gate"]
