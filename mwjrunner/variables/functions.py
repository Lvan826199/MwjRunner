"""内置函数化数据生成。

支持在变量表达式中使用 ${__func_name(args)} 语法调用内置函数。
所有函数通过白名单注册，禁止 eval/exec。
"""

from __future__ import annotations

import hashlib
import random
import string
import time
import uuid
from collections.abc import Callable
from typing import Any


class FunctionRegistry:
    """内置函数注册表。"""

    def __init__(self) -> None:
        self._functions: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._functions[name] = func

    def call(self, name: str, args: list[str]) -> Any:
        """调用已注册函数。"""
        func = self._functions.get(name)
        if func is None:
            raise ValueError(f"未注册的内置函数: __{name}")
        return func(*args)

    def has(self, name: str) -> bool:
        return name in self._functions


# --- 内置函数实现 ---


def _timestamp(*args: str) -> str:
    """返回当前时间戳（秒）。可选参数 'ms' 返回毫秒级。"""
    if args and args[0] == "ms":
        return str(int(time.time() * 1000))
    return str(int(time.time()))


def _uuid(*_args: str) -> str:
    """返回 UUID4 字符串。"""
    return str(uuid.uuid4())


def _random_phone(*_args: str) -> str:
    """返回随机中国手机号。"""
    prefixes = ["130", "131", "132", "133", "135", "136", "137", "138", "139",
                "150", "151", "152", "153", "155", "156", "157", "158", "159",
                "170", "176", "177", "178", "180", "181", "182", "183", "185",
                "186", "187", "188", "189"]
    prefix = random.choice(prefixes)
    suffix = "".join(random.choices(string.digits, k=8))
    return prefix + suffix


def _random_int(*args: str) -> str:
    """返回随机整数。参数: min, max（默认 0-9999）。"""
    min_val = int(args[0]) if len(args) > 0 and args[0] else 0
    max_val = int(args[1]) if len(args) > 1 and args[1] else 9999
    return str(random.randint(min_val, max_val))


def _random_str(*args: str) -> str:
    """返回随机字符串。参数: length（默认 8）。"""
    length = int(args[0]) if args and args[0] else 8
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _md5(*args: str) -> str:
    """返回字符串的 MD5 哈希。参数: 待哈希字符串。"""
    text = args[0] if args else ""
    return hashlib.md5(text.encode()).hexdigest()


def create_default_function_registry() -> FunctionRegistry:
    """创建包含所有内置函数的注册表。"""
    registry = FunctionRegistry()
    registry.register("timestamp", _timestamp)
    registry.register("uuid", _uuid)
    registry.register("random_phone", _random_phone)
    registry.register("random_int", _random_int)
    registry.register("random_str", _random_str)
    registry.register("md5", _md5)
    return registry
