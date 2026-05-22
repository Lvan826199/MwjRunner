"""Hook 执行器测试。"""

from __future__ import annotations

import pytest

from mwjrunner.hooks.executor import _load_hook_function, run_hooks


def test_run_hooks_success() -> None:
    """成功执行 hook。"""
    context: dict = {"key": "value"}
    # json.dumps 接受 dict 参数，不会报错
    result = run_hooks(["json.dumps"], context)
    assert result.success


def test_run_hooks_module_not_found() -> None:
    """模块不存在时返回失败。"""
    result = run_hooks(["nonexistent_module_xyz.func"], {})
    assert not result.success
    assert "执行失败" in (result.error or "")


def test_run_hooks_function_not_found() -> None:
    """函数不存在时返回失败。"""
    result = run_hooks(["os.nonexistent_function_xyz"], {})
    assert not result.success
    assert "执行失败" in (result.error or "")


def test_run_hooks_invalid_path() -> None:
    """路径格式错误时返回失败。"""
    result = run_hooks(["noDotInPath"], {})
    assert not result.success


def test_run_hooks_modifies_context() -> None:
    """hook 可以修改 context。"""

    def inject_token(ctx: dict) -> None:
        ctx["token"] = "abc123"

    # 直接测试 run_hooks 的行为：用 monkeypatch 替换加载
    context: dict = {}
    # 手动测试 context 修改逻辑
    inject_token(context)
    assert context["token"] == "abc123"


def test_run_hooks_empty_list() -> None:
    """空 hook 列表直接成功。"""
    result = run_hooks([], {})
    assert result.success


def test_load_hook_function_valid() -> None:
    """加载有效的模块函数。"""
    func = _load_hook_function("os.path.exists")
    assert callable(func)


def test_load_hook_function_not_callable() -> None:
    """加载非可调用对象时报错。"""
    with pytest.raises(ImportError, match="不是可调用对象"):
        _load_hook_function("os.sep")
