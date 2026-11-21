"""Persist creation attempts before sending remote writes."""
from alembic import op
import sqlalchemy as sa
import json

revision = '0002_operations'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for tracker, stream, raw in connection.execute(sa.text('SELECT tracker, stream, data FROM history')):
        try:
            data = json.loads(raw)
            valid = isinstance(data, dict) and all(
                isinstance(data.get(key), list) and all(type(item) is int and item > 0 for item in data[key])
                for key in ('known', 'pins'))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise RuntimeError(f'Некорректная история потока {stream}. Восстановите данные перед миграцией.')
    op.create_table('creation_operations',
                    sa.Column('tracker', sa.Text, primary_key=True),
                    sa.Column('key', sa.Text, primary_key=True),
                    sa.Column('payload', sa.JSON, nullable=False),
                    sa.Column('data', sa.JSON, nullable=False))


def downgrade():
    raise RuntimeError('Журнал содержит незавершённые операции. Для отката используйте резервную копию.')
