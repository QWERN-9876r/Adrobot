"""Initialize SQLite or adopt the database from the standalone Python app."""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    schemas = {
        "demo": ({"id", "path", "data"}, ["id"]),
        "history": ({"tracker", "stream", "data"}, ["tracker", "stream"]),
    }
    for table, (expected_columns, expected_pk) in schemas.items():
        if table in existing:
            columns = {column["name"] for column in inspector.get_columns(table)}
            primary_key = inspector.get_pk_constraint(table)["constrained_columns"]
            if columns != expected_columns or primary_key != expected_pk:
                raise RuntimeError(f"Неизвестная структура таблицы {table}. Проверьте путь ADROBOT_DB.")
    if "demo" not in existing:
        op.create_table(
            "demo",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("path", sa.Text, nullable=False),
            sa.Column("data", sa.JSON, nullable=False),
        )
    if "history" not in existing:
        op.create_table(
            "history",
            sa.Column("tracker", sa.Text, primary_key=True),
            sa.Column("stream", sa.Integer, primary_key=True),
            sa.Column("data", sa.JSON, nullable=False),
        )


def downgrade():
    raise RuntimeError("Начальная миграция сохраняет существующие таблицы. Для отката используйте резервную копию.")
