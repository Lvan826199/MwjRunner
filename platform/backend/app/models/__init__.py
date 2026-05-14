"""SQLAlchemy 模型基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.benchmark import Benchmark  # noqa: E402, F401
from app.models.case import TestCase  # noqa: E402, F401
from app.models.environment import Environment  # noqa: E402, F401
from app.models.execution import Execution  # noqa: E402, F401
from app.models.mock import MockRule  # noqa: E402, F401
from app.models.worker import TaskShard, Worker  # noqa: E402, F401
