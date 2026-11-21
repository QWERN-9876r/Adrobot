"""Acceptance tests for the creator requirements, independent of the validator."""
import copy
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from adrobot.infrastructure.models import Base
from adrobot.services.container import Services
from adrobot.domain.errors import Problem
from test_campaigns import Remote


class SpecificationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.folder.name) / 'spec.sqlite3'))
        Base.metadata.create_all(self.engine)
        self.remote = Remote()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.remote.close)
        self.data = dict(operation_id='spec-creation-123456', name='Germany', country='DE',
                         offers=4, domains=1, groups=1, sources=1)

    def create(self):
        with Session(self.engine, expire_on_commit=False) as session:
            return Services(session, self.remote).campaigns.create(self.data)

    def test_unknown_country_is_rejected_before_any_tracker_write(self):
        self.data['country'] = 'ZZ'
        with self.assertRaises(Problem) as error:
            self.create()
        self.assertEqual(error.exception.status, 400)
        self.assertEqual(self.remote.writes, [])

    def test_lowercase_country_is_saved_in_uppercase(self):
        self.data['country'] = 'au'
        campaign = self.create()
        streams = self.remote.call(f"/campaigns/{campaign['id']}/streams")
        self.assertEqual(streams[0]['filters'][0]['payload'], ['AU'])

    def test_creator_produces_exact_required_configuration(self):
        campaign = self.create()
        self.assertEqual(campaign['name'], 'Germany')
        self.assertEqual(campaign['state'], 'active')
        self.assertEqual(campaign['type'], 'position')
        self.assertEqual(campaign['domain_id'], 1)
        self.assertEqual(str(campaign['group_id']), '1')
        self.assertEqual(campaign['traffic_source_id'], 1)
        streams = self.remote.call(f"/campaigns/{campaign['id']}/streams")
        self.assertEqual(len(streams), 2)
        first, second = sorted(streams, key=lambda stream: stream['position'])
        self.assertEqual((first['position'], second['position']), (1, 2))
        self.assertEqual((first['type'], second['type']), ('regular', 'default'))
        self.assertEqual(first['schema'], 'redirect')
        self.assertEqual(first['action_type'], 'http')
        self.assertEqual(first['action_payload'], 'https://www.google.com/')
        self.assertEqual(first['filters'], [{'name': 'country', 'mode': 'accept', 'payload': ['DE']}])
        self.assertEqual(first['offers'], [])
        self.assertEqual(second['schema'], 'landings')
        self.assertEqual(second['action_type'], 'http')
        self.assertEqual(second['filters'], [])
        self.assertEqual(second['offers'], [{'offer_id': 4, 'share': 100, 'state': 'active'}])
        for stream in streams:
            self.assertEqual(stream['state'], 'active')
            self.assertEqual(stream['campaign_id'], campaign['id'])
            self.assertEqual(stream['landings'], [])
            self.assertEqual(stream['triggers'], [])

    def test_invalid_saved_streams_are_never_enabled(self):
        corruptions = [
            ('reversed positions', lambda rows: (rows[0].update(position=2), rows[1].update(position=1))),
            ('duplicate positions', lambda rows: rows[1].update(position=1)),
            ('wrong action', lambda rows: rows[0].update(action_type='curl')),
            ('wrong URL', lambda rows: rows[0].update(action_payload='https://example.org/')),
            ('extra filter', lambda rows: rows[0]['filters'].append({'name': 'device_type', 'mode': 'accept', 'payload': ['mobile']})),
            ('wrong country', lambda rows: rows[0]['filters'][0].update(payload=['FR'])),
            ('reject country', lambda rows: rows[0]['filters'][0].update(mode='reject')),
            ('filtered fallback', lambda rows: rows[1].update(filters=[{'name': 'country', 'mode': 'accept', 'payload': ['US']}])),
            ('landing', lambda rows: rows[1].update(landings=[{'landing_id': 3, 'share': 100}])),
            ('trigger', lambda rows: rows[0].update(triggers=[{'action': 'disable'}])),
            ('wrong offer', lambda rows: rows[1]['offers'][0].update(offer_id=2)),
            ('wrong share', lambda rows: rows[1]['offers'][0].update(share=50)),
            ('extra offer', lambda rows: rows[1]['offers'].append({'offer_id': 2, 'share': 0, 'state': 'active'})),
            ('disabled stream', lambda rows: rows[1].update(state='disabled')),
            ('other campaign', lambda rows: rows[0].update(campaign_id=999)),
            ('third stream', lambda rows: rows.append(copy.deepcopy(rows[0]))),
        ]
        for index, (label, corrupt) in enumerate(corruptions):
            with self.subTest(label=label):
                remote = Remote()
                self.addCleanup(remote.close)
                self.remote = remote
                original = remote.call
                def call(path, method='GET', body=None):
                    result = original(path, method, body)
                    if path == '/campaigns/12/streams' and method == 'GET' and len(result) == 2:
                        corrupt(result)
                    return result
                remote.call = call
                self.data['operation_id'] = f'spec-invalid-{index:08d}'
                with self.assertRaises(Problem) as error:
                    self.create()
                self.assertEqual(error.exception.code, 'configuration_mismatch')
                self.assertNotIn(('/campaigns/12/enable', 'POST'), remote.writes)

    def test_settings_changed_at_enable_are_detected_even_if_disable_reply_is_lost(self):
        original = self.remote.call
        def call(path, method='GET', body=None):
            result = original(path, method, body)
            if path == '/campaigns/12/enable' and method == 'POST':
                original('/campaigns/12', 'PUT', {'traffic_source_id': 999})
            if path == '/campaigns/12/disable' and method == 'POST':
                raise Problem('disable response lost', 502)
            return result
        self.remote.call = call
        with self.assertRaises(Problem) as error:
            self.create()
        self.assertEqual(error.exception.code, 'configuration_mismatch')
        self.assertEqual(original('/campaigns/12')['state'], 'disabled')

    def test_unavailable_offer_creates_nothing(self):
        self.data['offers'] = 999
        with self.assertRaises(Problem):
            self.create()
        self.assertEqual(self.remote.writes, [])

    def test_editor_archives_external_removal_and_restores_offer(self):
        with Session(self.engine, expire_on_commit=False) as session:
            Services(session, self.remote).streams.list(9)
        self.remote.call('/streams/11', 'PUT', {'offers': [{'offer_id': 2, 'share': 100, 'state': 'active'}]})
        with Session(self.engine, expire_on_commit=False) as session:
            streams = Services(session, self.remote).streams
            view = streams.list(9)[1]
            self.assertEqual(view['removed'], [1, 3])
            saved = streams.publish(11, {**view, 'offers': [
                {'offer_id': 2, 'share': 50, 'state': 'active'},
                {'offer_id': 1, 'share': 50, 'state': 'active'}]})
            self.assertEqual(saved['removed'], [3])
            self.assertEqual(sum(offer['share'] for offer in saved['offers']), 100)

    def test_editor_rejects_redirect_stream_mutations(self):
        with Session(self.engine, expire_on_commit=False) as session:
            streams = Services(session, self.remote).streams
            view = streams.list(9)[0]
            with self.assertRaises(Problem):
                streams.publish(view['id'], {**view, 'offers': [], 'pins': []})
        self.assertEqual(self.remote.writes, [])
