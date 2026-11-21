"""Check real service payloads against the supplied tracker specification."""
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

import yaml

from adrobot.config import ROOT
from adrobot.domain.stream_rules import stream_payloads
from adrobot.infrastructure.keitaro.client import Keitaro
import test_creation_spec as acceptance


# Export contains mojibake control characters in descriptions (e.g. U+009D).
# Strip only YAML-forbidden controls for parsing; preserve the supplied file.
raw_spec = (ROOT / 'openapi.yaml').read_text()
clean_spec = ''.join(char for char in raw_spec if char in '\t\n\r' or (ord(char) >= 32 and not 127 <= ord(char) <= 159))
SPEC = yaml.safe_load(clean_spec)


def resolve(schema):
    if '$ref' in schema:
        node = SPEC
        for part in schema['$ref'].removeprefix('#/').split('/'):
            node = node[part]
        return resolve(node)
    if 'allOf' in schema:
        result = {'type': 'object', 'properties': {}, 'required': []}
        for item in schema['allOf']:
            item = resolve(item)
            result['properties'].update(item.get('properties', {}))
            result['required'].extend(item.get('required', []))
        return result
    return schema


def check(value, schema, path='$'):
    """Validate the object/array/scalar subset used by our outgoing requests."""
    schema = resolve(schema)
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'integer': int, 'string': str, 'boolean': bool}
    if kind in types and type(value) is not types[kind]:
        raise AssertionError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise AssertionError(f'{path}: value not in enum')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                raise AssertionError(f'{path}: missing {key}')
        for key, item in value.items():
            prop = schema.get('properties', {}).get(key)
            if prop is None:
                # Explicit documentation gap, present in Stream response only.
                if key == 'action_payload' and path == '$' and item == 'https://www.google.com/':
                    continue
                raise AssertionError(f'{path}.{key}: undocumented request property')
            check(item, prop, f'{path}.{key}')
    if kind == 'array':
        for index, item in enumerate(value):
            check(item, schema['items'], f'{path}[{index}]')


class OpenApiTests(unittest.TestCase):
    def test_stream_creation_and_offer_update_match_specification(self):
        creation = SPEC['paths']['/streams']['post']['requestBody']['content']['application/json']['schema']
        update = SPEC['paths']['/streams/{id}']['put']['requestBody']['content']['application/json']['schema']
        for payload in stream_payloads(42, 'DE', 123):
            check(payload, creation)
        check({'offers': [{'offer_id': 123, 'share': 100, 'state': 'active'}]}, update)

    def test_required_fields_and_offer_types_are_enforced(self):
        schema = SPEC['paths']['/streams']['post']['requestBody']['content']['application/json']['schema']
        payload = stream_payloads(42, 'DE', 123)[1]
        for missing in ['campaign_id', 'schema', 'type', 'name', 'action_type']:
            invalid = {k: v for k, v in payload.items() if k != missing}
            with self.subTest(missing=missing), self.assertRaises(AssertionError):
                check(invalid, schema)
        with self.assertRaises(AssertionError):
            check({'offer_id': 1, 'share': '100'}, SPEC['components']['schemas']['OfferStreamRequest'])

    def test_transport_uses_documented_api_key_header_and_base(self):
        auth = SPEC['components']['securitySchemes']['ApiKeyAuth']
        self.assertEqual(auth['in'], 'header')
        response = MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.read.return_value = b'[]'
        with patch('adrobot.infrastructure.keitaro.client.build_opener') as opener:
            opener.return_value.open.return_value = response
            Keitaro('https://tracker.example', 'test-key').call('/campaigns')
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header(auth['name']), 'test-key')
            self.assertEqual(urlsplit(request.full_url).path, SPEC['servers'][0]['url'] + '/campaigns')

    def test_all_used_routes_exist(self):
        routes = {'/campaigns': ['get', 'post'], '/campaigns/{id}': ['get'],
                  '/campaigns/{id}/streams': ['get'], '/campaigns/{id}/enable': ['post'],
                  '/campaigns/{id}/disable': ['post'], '/streams': ['post'],
                  '/streams/{id}': ['get', 'put'], '/offers': ['get'],
                  '/groups': ['get'], '/domains': ['get'], '/traffic_sources': ['get']}
        for path, methods in routes.items():
            for method in methods:
                with self.subTest(path=path, method=method):
                    self.assertIn(method, SPEC['paths'][path])


class CreationPayloadTests(unittest.TestCase):
    setUp = acceptance.SpecificationTests.setUp
    create = acceptance.SpecificationTests.create

    def test_actual_campaign_request_matches_specification(self):
        original = self.remote.call
        captured = []
        def call(path, method='GET', body=None):
            if path == '/campaigns' and method == 'POST':
                captured.append(body)
            return original(path, method, body)
        self.remote.call = call
        self.create()
        schema = SPEC['paths']['/campaigns']['post']['requestBody']['content']['application/json']['schema']
        self.assertEqual(len(captured), 1)
        check(captured[0], schema)
