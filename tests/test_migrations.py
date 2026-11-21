import asyncio
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from adrobot.api.app import create_app
from adrobot.config import ROOT


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = str(Path(self.folder.name) / 'legacy.sqlite3')
        self.env = patch.dict(os.environ, {'ADROBOT_DB': self.path, 'KEITARO_URL': '', 'KEITARO_API_KEY': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = Config(str(ROOT / 'alembic.ini'))

    def test_fresh_database_upgrade_is_repeatable(self):
        command.upgrade(self.config, 'head')
        command.upgrade(self.config, 'head')
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('SELECT version_num FROM alembic_version').fetchone()[0], '0002_operations')
            self.assertEqual(connection.execute('SELECT count(*) FROM creation_operations').fetchone()[0], 0)

    def test_legacy_json_and_history_are_preserved(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute('CREATE TABLE demo (id INTEGER PRIMARY KEY, path TEXT, data TEXT)')
            connection.execute('CREATE TABLE history (tracker TEXT, stream INTEGER, data TEXT, PRIMARY KEY(tracker,stream))')
            connection.execute('INSERT INTO demo VALUES (42, ?, ?)', ('/campaigns', json.dumps({'id': 42, 'name': 'Legacy', 'state': 'active'})))
            connection.execute('INSERT INTO history VALUES (?, 99, ?)', ('demo', json.dumps({'known': [1, 2], 'pins': [1]})))
        command.upgrade(self.config, 'head')
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(json.loads(connection.execute('SELECT data FROM history').fetchone()[0]), {'known': [1, 2], 'pins': [1]})
            self.assertEqual(json.loads(connection.execute('SELECT data FROM demo WHERE id=42').fetchone()[0])['name'], 'Legacy')

    def test_migration_rejects_corrupt_history(self):
        command.upgrade(self.config, '0001_baseline')
        with sqlite3.connect(self.path) as connection:
            connection.execute('INSERT INTO history VALUES (?, 99, ?)', ('demo', '{bad json'))
        with self.assertRaisesRegex(RuntimeError, 'Некорректная история'):
            command.upgrade(self.config, 'head')
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('SELECT version_num FROM alembic_version').fetchone()[0], '0001_baseline')

    def test_startup_rejects_old_schema(self):
        command.upgrade(self.config, '0001_baseline')
        application = create_app()
        async def start():
            async with application.router.lifespan_context(application):
                self.fail('outdated database was accepted')
        with self.assertRaisesRegex(RuntimeError, 'миграции'):
            asyncio.run(start())

    def test_startup_accepts_current_schema(self):
        command.upgrade(self.config, 'head')
        application = create_app()
        async def start():
            async with application.router.lifespan_context(application):
                self.assertIsNotNone(application.state.engine)
        asyncio.run(start())
