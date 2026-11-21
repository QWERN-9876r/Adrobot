"""SQLAlchemy persistence models."""
from sqlalchemy import JSON, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class DemoRecord(Base):
    __tablename__ = "demo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON)


class StreamHistory(Base):
    __tablename__ = "history"

    tracker: Mapped[str] = mapped_column(Text, primary_key=True)
    stream: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class CreationOperation(Base):
    __tablename__ = 'creation_operations'

    tracker: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    data: Mapped[dict] = mapped_column(JSON)
