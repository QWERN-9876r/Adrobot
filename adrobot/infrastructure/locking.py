"""Per-resource locks shared by local processes using the same SQLite database."""
from contextlib import contextmanager
import fcntl
import hashlib
from pathlib import Path
import tempfile

from adrobot.domain.errors import Problem


@contextmanager
def resource_lock(session, tracker, resource):
    database = session.get_bind().url.database
    root = Path(database + '.locks') if database and database != ':memory:' else Path(tempfile.gettempdir()) / 'adrobot-test-locks'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = hashlib.sha256(f'{tracker}:{resource}'.encode()).hexdigest()
    with (root / name).open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Problem('Эта операция уже выполняется. Повторите после её завершения.', 409, 'busy') from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
