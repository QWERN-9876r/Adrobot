import io
import logging
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from adrobot.domain.errors import Problem
from adrobot.infrastructure.keitaro.client import Keitaro


class RequestLoggingTests(unittest.TestCase):
    def run_call(self, response=None, error=None, path='/campaigns', body=None):
        client = Keitaro('https://tracker.example', 'SECRET-API-KEY')
        with patch('adrobot.infrastructure.keitaro.client.build_opener') as opener:
            if error:
                opener.return_value.open.side_effect = error
            else:
                remote = MagicMock()
                remote.status = 200
                remote.read.return_value = response
                opener.return_value.open.return_value.__enter__.return_value = remote
            with self.assertLogs('adrobot.keitaro', level=logging.INFO) as captured:
                try:
                    client.call(path, 'POST' if body else 'GET', body)
                except Problem:
                    pass
        self.assertTrue(any('request_started' in line for line in captured.output))
        self.assertTrue(any('request_finished' in line for line in captured.output))
        return '\n'.join(captured.output)

    def test_success_logs_metadata_without_secrets(self):
        log = self.run_call(b'{"id":1,"name":"Test","state":"active"}', path='/campaigns/1?token=QUERY-SECRET&offset=1')
        self.assertIn('status=200 outcome=success', log)
        self.assertIn('duration_ms=', log)
        self.assertIn('path=/campaigns', log)
        self.assertNotIn('QUERY-SECRET', log)
        self.assertIn('offset=1', log)
        self.assertIn('http_request', log)
        self.assertIn('http_response', log)
        self.assertNotIn('SECRET-API-KEY', log)

    def test_http_failure_never_logs_response_body_or_request_body(self):
        error = HTTPError('https://tracker.example', 403, 'SECRET-API-KEY', {}, io.BytesIO(b'RESPONSE-SECRET'))
        log = self.run_call(error=error, body={'password': 'BODY-SECRET'})
        self.assertIn('status=403 outcome=error', log)
        self.assertIn('RESPONSE-SECRET', log)
        for secret in ['SECRET-API-KEY', 'BODY-SECRET']:
            self.assertNotIn(secret, log)

    def test_dns_failure_has_classification(self):
        log = self.run_call(error=URLError(socket.gaierror('sensitive message')))
        self.assertIn('status=- outcome=error', log)
        self.assertIn('error=gaierror', log)
        self.assertIn('sensitive message', log)

    def test_contract_and_invalid_json_failures_are_logged(self):
        for content, classification in [(b'{}', 'upstream_contract'), (b'not-json', 'JSONDecodeError')]:
            with self.subTest(content=content):
                log = self.run_call(content)
                self.assertIn('status=200 outcome=error', log)
                self.assertIn('error=' + classification, log)

    def test_diagnostics_include_complete_payload_and_mask_nested_credentials(self):
        from adrobot.infrastructure.keitaro.debug import diagnostic
        import json
        content = {'headers': {'Api-Key': 'key', 'Set-Cookie': 'session=private'},
                   'body': {'offers': [{'offer_id': 123, 'share': 100}],
                            'nested': {'access_token': 'private', 'password': 'private'},
                            'name': 'A' * 20000}}
        result = json.loads(diagnostic(content, 'key'))
        self.assertEqual(result['headers']['Api-Key'], '[REDACTED]')
        self.assertEqual(result['headers']['Set-Cookie'], '[REDACTED]')
        self.assertEqual(result['body']['nested']['access_token'], '[REDACTED]')
        self.assertEqual(result['body']['offers'][0]['share'], 100)
        self.assertEqual(len(result['body']['name']), 20000)
