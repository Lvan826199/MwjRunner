"""配置加载器。

配置优先级（高到低）：
1. CLI 参数
2. 环境配置文件（envs/<name>.yaml）
3. 项目配置文件（mwjrunner.yaml）
4. 内置默认值
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mwjrunner.auth import parse_oauth2_config
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
            raise ConfigLoadError(f"环境配置文件不存在: {env_file}\n请在项目 envs/ 目录下创建 {env}.yaml 文件。")
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

    if data is None:
        # 空配置文件视为无配置
        return {}
    if not isinstance(data, dict):
        raise ConfigLoadError(f"配置文件顶层必须是对象: {file_path}")
    return data


def _to_float(data: dict[str, Any], key: str) -> float:
    try:
        return float(data[key])
    except (TypeError, ValueError) as exc:
        raise ConfigLoadError(f"配置项 {key} 必须是数字: {data[key]!r}") from exc


def _to_int(data: dict[str, Any], key: str) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            return int(str(value))
        except (TypeError, ValueError) as exc:
            raise ConfigLoadError(f"配置项 {key} 必须是整数: {value!r}") from exc
    return value


def _to_bool(data: dict[str, Any], key: str) -> bool:
    value = data[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "on", "1"):
            return True
        if normalized in ("false", "no", "off", "0"):
            return False
    raise ConfigLoadError(f"配置项 {key} 必须是布尔值: {value!r}")


def _merge_config(config: ProjectConfig, data: dict[str, Any]) -> None:  # noqa: PLR0912
    """将配置数据合并到 config 对象（后加载的覆盖先加载的）。"""
    if "base_url" in data:
        config.base_url = data["base_url"]
    if "timeout" in data:
        config.timeout = _to_float(data, "timeout")
    if "verify_ssl" in data:
        config.verify_ssl = _to_bool(data, "verify_ssl")
    if "proxy" in data:
        config.proxy = data["proxy"]
    if "report_dir" in data:
        config.report_dir = data["report_dir"]
    if "retry" in data:
        config.retry = _to_int(data, "retry")
    if "fail_fast" in data:
        config.fail_fast = _to_bool(data, "fail_fast")
    if "workers" in data:
        config.workers = _to_int(data, "workers")
    if "timezone" in data:
        config.timezone = data["timezone"]

    # headers 和 variables 按 key 合并
    if "headers" in data and isinstance(data["headers"], dict):
        config.headers.update(data["headers"])
    if "variables" in data and isinstance(data["variables"], dict):
        config.variables.update(data["variables"])

    # auth 配置（oauth2 单独解析，保留 token_url/client_id 等字段）
    if "auth" in data and isinstance(data["auth"], dict):
        auth_data = data["auth"]
        if auth_data.get("type") == "oauth2":
            config.oauth2 = parse_oauth2_config(auth_data)
            config.auth = None
        else:
            config.auth = AuthConfig(
                type=auth_data.get("type", "bearer"),
                token=auth_data.get("token"),
                username=auth_data.get("username"),
                password=auth_data.get("password"),
            )
            config.oauth2 = None

    # quality_gate 配置
    if "quality_gate" in data and isinstance(data["quality_gate"], dict):
        config.quality_gate = data["quality_gate"]

    # notifications 配置
    if "notifications" in data and isinstance(data["notifications"], list):
        config.notifications = data["notifications"]
