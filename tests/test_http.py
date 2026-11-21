import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from adrobot.api.app import create_app
from adrobot.config import ROOT


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'ADROBOT_DB': str(Path(self.folder.name) / 'api.sqlite3'),
                                                   'KEITARO_URL': '', 'KEITARO_API_KEY': ''})
        self.environment.start()
        command.upgrade(Config(str(ROOT / 'alembic.ini')), 'head')
        self.app = create_app(8000)
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()

    async def asyncTearDown(self):
        await self.lifespan.__aexit__(None, None, None)
        self.environment.stop()
        self.folder.cleanup()

    async def request(self, path, method='GET', data=None, origin='http://127.0.0.1:8000', raw=False):
        body = json.dumps(data).encode() if data is not None else b''
        headers = [(b'host', b'127.0.0.1:8000'), (b'origin', origin.encode()),
                   (b'content-type', b'application/json'), (b'content-length', str(len(body)).encode())]
        scope = dict(type='http', asgi={'version': '3.0', 'spec_version': '2.4'}, http_version='1.1',
                     method=method, scheme='http', path=path, raw_path=path.encode(), query_string=b'',
                     root_path='', headers=headers, server=('127.0.0.1', 8000), client=('127.0.0.1', 12345))
        messages = []
        delivered = False
        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            await asyncio.Event().wait()
        async def send(message):
            messages.append(message)
        await self.app(scope, receive, send)
        status = next(message['status'] for message in messages if message['type'] == 'http.response.start')
        content = b''.join(message.get('body', b'') for message in messages if message['type'] == 'http.response.body')
        return status, content if raw else json.loads(content)

    async def test_create_retry_publish_conflict_and_archive(self):
        status, catalog = await self.request('/api/catalog')
        self.assertEqual(status, 200)
        self.assertIn('AU', catalog['countries'])
        self.assertNotIn('ZZ', catalog['countries'])
        data = dict(operation_id='http-operation-123456', name='HTTP test', country='AU', offers=1, domains=1, groups=1, sources=1)
        status, campaign = await self.request('/api/campaigns', 'POST', data)
        self.assertEqual(status, 200)
        self.assertEqual((await self.request('/api/campaigns', 'POST', data))[1]['id'], campaign['id'])
        _, streams = await self.request(f"/api/campaigns/{campaign['id']}/streams")
        stream = streams[1]
        path = f"/api/streams/{stream['id']}"
        status, saved = await self.request(path, 'PUT', {**stream, 'pins': [1]})
        self.assertEqual(status, 200)
        self.assertNotEqual(saved['revision'], stream['revision'])
        self.assertEqual((await self.request(path, 'PUT', stream))[0], 409)
        status, saved = await self.request(path, 'PUT', {**saved, 'offers': [], 'pins': []})
        self.assertEqual(status, 200)
        self.assertEqual(saved['removed'], [1])
        self.assertEqual(saved['operation_state'], 'ready')

    async def test_origin_and_input_validation(self):
        status, _ = await self.request('/api/campaigns', 'POST', {}, origin='https://untrusted.invalid')
        self.assertEqual(status, 403)
        status, _ = await self.request('/api/campaigns', 'POST', dict(operation_id='http-operation-123456', name='Test', country='AU', offers=True, domains=1, groups=1, sources=1))
        self.assertEqual(status, 400)

    async def test_empty_campaign_list_can_be_refreshed(self):
        status, rows = await self.request('/api/campaigns')
        self.assertEqual(status, 200)
        self.assertEqual(rows[0]['id'], 9)
        # The list endpoint returns current records rather than a startup cache.
        from sqlalchemy.orm import Session
        from adrobot.infrastructure.demo import Demo
        with Session(self.app.state.engine) as session, session.begin():
            Demo(session).call('/campaigns/9', 'DELETE')
        self.assertEqual((await self.request('/api/campaigns'))[1], [])

    async def test_brand_images_and_unknown_paths(self):
        for name in ('adrobot-icon.png', 'favicon-32.png'):
            status, content = await self.request('/brand/' + name, raw=True)
            self.assertEqual(status, 200)
            self.assertTrue(content.startswith(bytes.fromhex('89504e470d0a1a0a')))
        self.assertEqual((await self.request('/brand/unknown.png'))[0], 404)
