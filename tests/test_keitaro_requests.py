import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit
from adrobot.domain.errors import Problem
from adrobot.infrastructure.keitaro.client import Keitaro
from adrobot.infrastructure.keitaro.schemas import validate_response


class RequestTests(unittest.TestCase):
    def test_campaign_state_changes_accept_documented_object_and_live_singleton_array(self):
        for action, state in [('enable', 'active'), ('disable', 'disabled')]:
            campaign = {'id': 12, 'name': 'Test', 'state': state}
            for payload in (campaign, [campaign]):
                with self.subTest(action=action, payload=payload):
                    self.assertEqual(validate_response(f'/campaigns/12/{action}', 'POST', payload), campaign)

    def test_campaign_state_change_rejects_a_different_or_ambiguous_campaign(self):
        campaign = {'id': 12, 'name': 'Test', 'state': 'active'}
        for payload in ([], [campaign, campaign], [{**campaign, 'id': 13}]):
            with self.subTest(payload=payload), self.assertRaises(Problem):
                validate_response('/campaigns/12/enable', 'POST', payload)

    def request(self, path, method='GET', body=None):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'[]' if method == 'GET' else b'{"id":1,"name":"Test","state":"active"}'
        with patch('adrobot.infrastructure.keitaro.client.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = response
            result = Keitaro('https://tracker.example', 'test-key').call(path, method, body)
            return opener.return_value.open.call_args.args[0], result

    def test_campaign_list_matches_curl(self):
        request, result = self.request('/campaigns')
        self.assertEqual(request.full_url, 'https://tracker.example/admin_api/v1/campaigns?offset=0&limit=1000')
        self.assertEqual(dict(request.header_items()), {'Accept': 'application/json', 'Api-Key': 'test-key', 'User-Agent': 'Adrobot/0.1'})
        self.assertIsNone(request.data)
        self.assertEqual(result, [])

    def test_campaign_list_reads_past_a_server_page_cap(self):
        pages = [[{'id': i, 'name': str(i), 'state': 'active'} for i in (1, 2)],
                 [{'id': 3, 'name': '3', 'state': 'active'}], []]
        with patch('adrobot.infrastructure.keitaro.client.build_opener') as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.side_effect = [json.dumps(page).encode() for page in pages]
            campaigns = Keitaro('https://tracker.example', 'test-key').call('/campaigns')
        self.assertEqual([row['id'] for row in campaigns], [1, 2, 3])
        requests = [call.args[0] for call in opener.return_value.open.call_args_list]
        self.assertEqual([parse_qs(urlsplit(request.full_url).query)['offset'][0]
                          for request in requests], ['0', '2', '3'])

    def test_explicit_pagination_is_preserved(self):
        request, _ = self.request('/campaigns?offset=0&limit=25')
        self.assertEqual(parse_qs(urlsplit(request.full_url).query), {'offset': ['0'], 'limit': ['25']})

    def test_post_has_json_content_type_without_pagination(self):
        request, _ = self.request('/campaigns', 'POST', {'name': 'Test'})
        self.assertEqual(request.full_url, 'https://tracker.example/admin_api/v1/campaigns')
        self.assertEqual(request.headers['Content-Type'], 'application/json')
        self.assertEqual(request.headers['Accept'], 'application/json')
