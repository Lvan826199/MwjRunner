"""Hook 执行器。"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HookResult:
    """Hook 执行结果。"""

    success: bool
    error: str | None = None


def run_hooks(
    hook_paths: list[str],
    context: dict[str, Any],
) -> HookResult:
    """执行一组 hook 函数。

    Args:
        hook_paths: hook 函数的模块路径列表，例如 ["myproject.hooks.setup_auth"]
        context: 变量上下文 dict，hook 可读写

    Returns:
        HookResult，success=True 表示全部成功
    """
    for hook_path in hook_paths:
        result = _run_single_hook(hook_path, context)
        if not result.success:
            return result
    return HookResult(success=True)


def _run_single_hook(hook_path: str, context: dict[str, Any]) -> HookResult:
    """执行单个 hook 函数。"""
    try:
        func = _load_hook_function(hook_path)
        func(context)
        return HookResult(success=True)
    except Exception as exc:
        return HookResult(success=False, error=f"Hook '{hook_path}' 执行失败: {exc}")


def _load_hook_function(module_path: str) -> Any:
    """通过模块路径加载 hook 函数。

    例如 "myproject.hooks.setup_auth" 会导入 myproject.hooks 模块并获取 setup_auth 属性。
    """
    if "." not in module_path:
        raise ImportError(f"Hook 路径格式错误: '{module_path}'，应为 'module.function' 格式")

    module_name, func_name = module_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(f"无法导入 hook 模块 '{module_name}': {exc}") from exc

    func = getattr(module, func_name, None)
    if func is None:
        raise ImportError(f"模块 '{module_name}' 中未找到函数 '{func_name}'")
    if not callable(func):
        raise ImportError(f"'{module_path}' 不是可调用对象")
    return func
