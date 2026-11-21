"""Validate configuration/schema and own the database engine lifecycle."""
from contextlib import asynccontextmanager
import os
from alembic.migration import MigrationContext
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from sqlalchemy.orm import Session
from adrobot.config import ROOT
from adrobot.infrastructure.database import make_engine
from adrobot.infrastructure.keitaro.client import Keitaro
from adrobot.infrastructure.seeding import seed_demo


@asynccontextmanager
async def lifespan(application: FastAPI):
    url, key = os.getenv("KEITARO_URL"), os.getenv("KEITARO_API_KEY")
    if bool(url) != bool(key):
        raise RuntimeError("Задайте обе переменные KEITARO_URL и KEITARO_API_KEY или оставьте обе незаданными для демо-режима.")
    tracker = Keitaro(url, key) if url and key else None
    engine = make_engine()
    try:
        with engine.connect() as connection:
            config = Config(str(ROOT / "alembic.ini"))
            expected = set(ScriptDirectory.from_config(config).get_heads())
            if set(MigrationContext.configure(connection).get_current_heads()) != expected:
                raise RuntimeError("Перед запуском примените миграции командой alembic upgrade head.")
        if tracker is None:
            with Session(engine) as session, session.begin():
                seed_demo(session)
        application.state.engine = engine
        application.state.tracker = tracker
        yield
    finally:
        engine.dispose()
