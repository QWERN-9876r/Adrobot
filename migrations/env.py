"""Run migrations against the same SQLite database as the application."""
from alembic import context

from adrobot.infrastructure.models import Base
from adrobot.infrastructure.database import make_engine


def run_migrations():
    engine = make_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Эта миграция требует подключения к SQLite для проверки существующих таблиц.")
run_migrations()
