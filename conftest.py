"""pytest 根配置文件。

定义仓库根目录常量，供各层级测试文件使用，避免通过 Path(__file__).parent * N 计算路径。
"""

from pathlib import Path

import pytest

# 仓库根目录：conftest.py 与 pytest.ini 同级，始终指向仓库根
REPO_ROOT = Path(__file__).parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """返回仓库根目录路径。"""
    return REPO_ROOT
