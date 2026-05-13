"""SQLAlchemy 模型基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.case import TestCase  # noqa: E402, F401
