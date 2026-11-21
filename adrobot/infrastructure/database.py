"""Database engine factory."""
import os
from pathlib import Path
from sqlalchemy import URL, create_engine
from adrobot.config import ROOT

def make_engine():
    path = os.getenv("ADROBOT_DB", str(ROOT / "adrobot.sqlite3"))
    if path != ':memory:':
        path = str(Path(path).expanduser().resolve())
    return create_engine(URL.create("sqlite+pysqlite", database=path))
