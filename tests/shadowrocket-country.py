import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI, Request

SOURCE = Path(__file__).resolve().parents[1] / 'setup/shadowrocket/client_country.py'
spec = importlib.util.spec_from_file_location('tolf_client_country', SOURCE)
country = importlib.util.module_from_spec(spec)
spec.loader.exec_module(country)


class CountryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'registry'
        self.path.write_text(''.join([
            'ripencc|RU|ipv4|5.8.0.0|256|20260101|allocated\n',
            'ripencc|RU|ipv4|5.8.1.0|256|20260101|assigned\n',
            'ripencc|LV|ipv4|5.179.0.0|256|20260101|allocated\n',
            'ripencc|RU|ipv6|2a00:1::|32|20260101|allocated\n',
            'ripencc|LV|ipv6|2a00:2::|32|20260101|legacy\n',
            'ripencc|LV|ipv4|5.180.0.0|256|20260101|reserved\n',
            'ripencc|US|ipv4|8.8.8.0|256|20260101|allocated\n',
            'ripencc|LV|ipv4|invalid|bad|20260101|allocated\n',
        ]))
        self.registry = country.CountryRanges(self.path)

    def test_country_boundaries_and_families(self):
        for address, expected in [('5.8.0.0', 'RU'), ('5.8.1.255', 'RU'), ('5.8.2.0', None), ('5.179.0.1', 'LV'), ('2a00:1::1', 'RU'), ('2a00:2::1', 'LV'), ('8.8.8.8', None), ('5.180.0.1', None)]:
            self.assertEqual(self.registry.country_code(address), expected, address)

    def test_private_invalid_and_unavailable_do_not_guess(self):
        for address in ['127.0.0.1', '10.0.0.1', '::1', 'not-an-ip', None]:
            self.assertIsNone(self.registry.country_code(address))
        self.path.unlink()
        self.assertIsNone(self.registry.country_code('5.8.0.1'))
        self.path.write_text('invalid\n')
        self.assertIsNone(self.registry.country_code('5.8.0.1'))

    def test_registry_refreshes(self):
        self.assertEqual(self.registry.country_code('5.179.0.1'), 'LV')
        self.path.write_text('ripencc|RU|ipv4|5.179.0.0|256|20260101|allocated\n')
        self.assertEqual(self.registry.country_code('5.179.0.1'), 'RU')

    def test_route_uses_actual_client_and_is_not_cached(self):
        app = FastAPI()
        country.register(app, self.registry)
        endpoint = next(route.endpoint for route in app.routes if route.path == '/client-country')
        request = Request({'type': 'http', 'client': ('5.8.0.1', 1234), 'headers': [(b'x-country-code', b'LV'), (b'x-forwarded-for', b'5.179.0.1')]})
        response = endpoint(request)
        self.assertEqual(json.loads(response.body), {'countryCode': 'RU'})
        self.assertIn('no-store', response.headers['cache-control'])


if __name__ == '__main__':
    unittest.main()
