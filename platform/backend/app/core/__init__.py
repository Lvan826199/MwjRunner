"""平台核心配置。"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'platform.db'}"

# 引擎路径（默认使用系统 PATH 中的 mwjrunner）
ENGINE_COMMAND = "mwjrunner"
