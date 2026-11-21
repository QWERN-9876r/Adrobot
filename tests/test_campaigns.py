import copy
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from adrobot.services.container import Services
from adrobot.infrastructure.seeding import seed_demo
from adrobot.infrastructure.models import Base, StreamHistory
from adrobot.infrastructure.demo import Demo
from adrobot.domain.errors import Problem
from adrobot.infrastructure.keitaro.schemas import validate_response
from adrobot.infrastructure.locking import resource_lock


class Remote:
    mode = 'live'
    identity = 'test-remote'

    def __init__(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        seed_demo(self.session)
        self.session.commit()
        self.demo = Demo(self.session)
        self.fail_after = None
        self.fail_verification = False
        self.writes = []
        self.race = False

    def call(self, path, method='GET', body=None):
        if path == '/offers' and self.race:
            stream = self.demo.call('/streams/11')
            changed = copy.deepcopy(stream['offers'])
            changed[0]['share'], changed[1]['share'] = 50, 16
            self.demo.call('/streams/11', 'PUT', {'offers': changed})
            self.session.commit()
            self.race = False
        if path == '/streams/11' and method == 'GET' and self.fail_verification and any(m == 'PUT' for _, m in self.writes):
            raise Problem('verification unavailable', 502)
        result = copy.deepcopy(self.demo.call(path, method, body))
        self.session.commit()
        if method != 'GET':
            self.writes.append((path, method))
            if self.fail_after == (path, method):
                self.fail_after = None
                raise Problem('response lost after mutation', 502)
        return result

    def close(self):
        self.session.close()
        self.engine.dispose()


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.folder.name) / 'test.sqlite3'))
        Base.metadata.create_all(self.engine)
        self.remote = Remote()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.remote.close)

    def run_manager(self, work):
        with Session(self.engine, expire_on_commit=False) as session:
            return work(Services(session, self.remote))

    def view(self):
        return self.run_manager(lambda manager: manager.streams.list(9)[1])

    def publish(self, view, **changes):
        return self.run_manager(lambda manager: manager.streams.publish(11, {**view, **changes}))

    def test_new_or_reactivated_offers_cannot_be_published_with_zero_share(self):
        for offer_id in (1, 4):
            with self.subTest(offer_id=offer_id):
                retained = {'offer_id': 2, 'share': 100, 'state': 'active'}
                self.remote.call('/streams/11', 'PUT', {'offers': [
                    retained, {'offer_id': 1, 'share': 0, 'state': 'disabled'},
                ]})
                self.remote.writes.clear()
                with self.assertRaises(Problem) as error:
                    self.publish(self.view(), offers=[retained, {
                        'offer_id': offer_id, 'share': 0, 'state': 'active',
                    }])
                self.assertEqual(error.exception.status, 400)
                self.assertEqual(self.remote.writes, [])

    def test_stale_pin_write_conflicts(self):
        original = self.view()
        saved = self.publish(original, pins=[1])
        self.assertNotEqual(saved['revision'], original['revision'])
        with self.assertRaises(Problem) as error:
            self.publish(original, pins=[2])
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(self.view()['pins'], [1])

    def test_external_disable_removes_pin(self):
        self.publish(self.view(), pins=[1])
        offers = self.remote.call('/streams/11')['offers']
        offers[0].update(state='disabled', share=0)
        offers[1]['share'] = 66
        self.remote.call('/streams/11', 'PUT', {'offers': offers})
        current = self.view()
        self.assertEqual(current['pins'], [])
        self.assertEqual(self.publish(current, pins=[2])['pins'], [2])

    def test_change_during_catalog_read_conflicts_without_put(self):
        original = self.view()
        self.remote.race = True
        with self.assertRaises(Problem) as error:
            self.publish(original, offers=[{'offer_id': 2, 'share': 100, 'state': 'active'}])
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(self.remote.writes, [])
        self.assertEqual(self.remote.call('/streams/11')['offers'][0]['share'], 50)

    def test_lost_put_response_is_reconciled(self):
        self.remote.fail_after = ('/streams/11', 'PUT')
        result = self.publish(self.view(), offers=[{'offer_id': 2, 'share': 100, 'state': 'active'}], pins=[2])
        self.assertEqual(result['operation_state'], 'ready')
        self.assertEqual(result['pins'], [2])
        self.assertEqual(result['removed'], [1, 3])
        self.assertEqual(self.remote.writes.count(('/streams/11', 'PUT')), 1)

    def test_restart_recovers_pins_and_archive_after_verification_failure(self):
        view = self.view()
        self.remote.fail_verification = True
        with self.assertRaises(Problem) as error:
            self.publish(view, offers=[{'offer_id': 2, 'share': 100, 'state': 'active'}], pins=[2])
        self.assertEqual(error.exception.code, 'uncertain')
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(StreamHistory, (self.remote.identity, 11)).data['pending'])
        self.remote.fail_verification = False
        result = self.view()  # New Manager and Session, as after a restart.
        self.assertEqual(result['pins'], [2])
        self.assertEqual(result['removed'], [1, 3])
        self.assertEqual(result['operation_state'], 'ready')
        self.assertEqual(self.remote.writes.count(('/streams/11', 'PUT')), 1)

    def test_different_remote_result_requires_explicit_acceptance(self):
        view = self.view()
        self.remote.fail_verification = True
        with self.assertRaises(Problem):
            self.publish(view, offers=[{'offer_id': 2, 'share': 100, 'state': 'active'}])
        self.remote.fail_verification = False
        self.remote.call('/streams/11', 'PUT', {'offers': view['offers']})
        uncertain = self.view()
        self.assertEqual(uncertain['operation_state'], 'uncertain')
        with self.assertRaises(Problem) as error:
            self.publish(uncertain)
        self.assertEqual(error.exception.code, 'uncertain')
        accepted = self.run_manager(lambda manager: manager.streams.accept_remote(11))
        self.assertEqual(accepted['operation_state'], 'ready')
        self.assertEqual(accepted['offers'], view['offers'])

    def creation(self, key='operation-test-123456'):
        return dict(operation_id=key, name='Test', country='AU', offers=1, domains=1, groups=1, sources=1)

    def test_lost_creation_response_resumes_without_duplicate(self):
        data = self.creation()
        self.remote.fail_after = ('/campaigns', 'POST')
        with self.assertRaises(Problem):
            self.run_manager(lambda manager: manager.campaigns.create(data))
        created = self.run_manager(lambda manager: manager.campaigns.create(data))
        repeated = self.run_manager(lambda manager: manager.campaigns.create(data))
        self.assertEqual(created['id'], repeated['id'])
        self.assertEqual(created['state'], 'active')
        self.assertEqual(self.remote.writes.count(('/campaigns', 'POST')), 1)
        self.assertEqual(self.remote.writes.count(('/streams', 'POST')), 2)

    def test_unconfirmed_absent_creation_is_not_sent_twice(self):
        original = self.remote.call
        attempts = []
        def fail_before_create(path, method='GET', body=None):
            if path == '/campaigns' and method == 'POST':
                attempts.append(body)
                raise Problem('connection failed before response', 502)
            return original(path, method, body)
        self.remote.call = fail_before_create
        for _ in range(2):
            with self.assertRaises(Problem) as error:
                self.run_manager(lambda manager: manager.campaigns.create(self.creation()))
            self.assertEqual(error.exception.code, 'uncertain')
        self.assertEqual(len(attempts), 1)

    def test_lost_stream_response_resumes_without_duplicate(self):
        self.remote.fail_after = ('/streams', 'POST')
        with self.assertRaises(Problem):
            self.run_manager(lambda manager: manager.campaigns.create(self.creation()))
        created = self.run_manager(lambda manager: manager.campaigns.create(self.creation()))
        self.assertEqual(created['state'], 'active')
        self.assertEqual(self.remote.writes.count(('/streams', 'POST')), 2)

    def test_lost_enable_response_is_verified_without_second_enable(self):
        self.remote.fail_after = ('/campaigns/12/enable', 'POST')
        result = self.run_manager(lambda manager: manager.campaigns.create(self.creation()))
        self.assertEqual(result['state'], 'active')
        self.assertEqual(self.remote.writes.count(('/campaigns/12/enable', 'POST')), 1)

    def test_failed_enable_stays_unconfirmed_when_campaign_is_disabled(self):
        original = self.remote.call

        def call(path, method='GET', body=None):
            if path == '/campaigns/12/enable' and method == 'POST':
                raise Problem('enable unavailable', 502)
            return original(path, method, body)

        self.remote.call = call
        with self.assertRaises(Problem) as error:
            self.run_manager(lambda manager: manager.campaigns.create(self.creation()))
        self.assertEqual(error.exception.code, 'uncertain')
        self.assertEqual(original('/campaigns/12')['state'], 'disabled')

    def test_idempotency_key_cannot_change_payload(self):
        data = self.creation()
        self.run_manager(lambda manager: manager.campaigns.create(data))
        with self.assertRaises(Problem) as error:
            self.run_manager(lambda manager: manager.campaigns.create({**data, 'name': 'different'}))
        self.assertEqual(error.exception.code, 'conflict')

    def test_resource_locks_do_not_block_unrelated_reads(self):
        with Session(self.engine) as a, Session(self.engine) as b:
            with resource_lock(a, 'test', 'stream:1'):
                with resource_lock(b, 'test', 'stream:2'):
                    self.assertTrue(self.run_manager(lambda manager: manager.catalog.load())['offers'])
                with self.assertRaises(Problem) as error:
                    with resource_lock(b, 'test', 'stream:1'):
                        self.fail('same resource acquired twice')
                self.assertEqual(error.exception.code, 'busy')

    def test_malformed_upstream_response_is_controlled_error(self):
        for value in ({}, [None], [{'id': 'invalid', 'name': 'Test'}]):
            with self.subTest(value=value), self.assertRaises(Problem) as error:
                validate_response('/offers', 'GET', value)
            self.assertEqual(error.exception.code, 'upstream_contract')


if __name__ == '__main__':
    unittest.main()
