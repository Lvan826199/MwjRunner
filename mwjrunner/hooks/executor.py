"""Hook 执行器。"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HookResult:
    """Hook 执行结果。"""

    success: bool
    error: str | None = None


def run_hooks(
    hook_paths: list[str],
    context: dict[str, Any],
    *,
    stop_on_failure: bool = True,
) -> HookResult:
    """执行一组 hook 函数。

    Args:
        hook_paths: hook 函数的模块路径列表，支持 "module.function" 和 "module:function"
        context: 变量上下文 dict，hook 可读写
        stop_on_failure: True 时首个失败即中止（setup 场景）；
            False 时全部执行并聚合错误（teardown 清理场景）

    Returns:
        HookResult，success=True 表示全部成功
    """
    errors: list[str] = []
    for hook_path in hook_paths:
        result = _run_single_hook(hook_path, context)
        if not result.success:
            if stop_on_failure:
                return result
            errors.append(result.error or f"Hook '{hook_path}' 执行失败")
    if errors:
        return HookResult(success=False, error="; ".join(errors))
    return HookResult(success=True)


def _run_single_hook(hook_path: str, context: dict[str, Any]) -> HookResult:
    """执行单个 hook 函数。"""
    try:
        func = _load_hook_function(hook_path)
        func(context)
        return HookResult(success=True)
    except Exception as exc:
        return HookResult(success=False, error=f"Hook '{hook_path}' 执行失败: {exc}")


def _split_hook_path(module_path: str) -> tuple[str, str]:
    """拆分 hook 路径为 (模块名, 函数名)。

    支持 "module:function"（手册/示例使用的格式）和 "module.function" 两种写法。
    """
    if ":" in module_path:
        module_name, _, func_name = module_path.partition(":")
        if not module_name or not func_name:
            raise ImportError(f"Hook 路径格式错误: '{module_path}'，应为 'module:function' 格式")
        return module_name, func_name
    if "." not in module_path:
        raise ImportError(f"Hook 路径格式错误: '{module_path}'，应为 'module.function' 或 'module:function' 格式")
    module_name, func_name = module_path.rsplit(".", 1)
    return module_name, func_name


def _load_hook_function(module_path: str) -> Any:
    """通过模块路径加载 hook 函数。

    例如 "myproject.hooks.setup_auth" 或 "myproject.hooks:setup_auth"
    都会导入 myproject.hooks 模块并获取 setup_auth 属性。
    """
    module_name, func_name = _split_hook_path(module_path)

    # 正式安装场景下 sys.path 不含项目目录，临时注入 cwd 以便导入项目本地 hooks
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

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
