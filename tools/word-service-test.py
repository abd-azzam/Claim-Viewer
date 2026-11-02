"""Isolated TLS transport checks. No production API, OS trust, or installation."""
import http.client
import importlib.util
import json
from pathlib import Path
import shutil
import ssl
import tempfile
import threading
import unittest

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixture_word_service', APP / 'word_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class FakeApi:
    def __init__(self):
        self.calls = []

    def word_sources(self, *args):
        self.calls.append(('word_sources', args))
        return [{'id': 'fixture', 'title': 'Fixture source'}]

    def word_action(self, *args):
        self.calls.append(('word_action', args))
        return {'ok': True, 'message': 'Fixture only'}


class WordServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='word-service-fixture-', dir=APP / 'tools')
        cls.root = Path(cls.tmp.name)
        (cls.root / 'word').mkdir()
        for name in ('localhost.pem', 'localhost-key.pem'):
            shutil.copy2(APP / 'word' / name, cls.root / 'word' / name)
        (cls.root / 'word/service-config.json').write_text(json.dumps({'token': 'fixture-token'}))
        (cls.root / 'word/addin.html').write_text('<!doctype html><title>Fixture add-in</title>')
        cls.api = FakeApi()
        cls.server = service.make_server(cls.root, cls.api, port=0)
        cls.port = cls.server.server_port
        cls.tls = ssl.create_default_context(cafile=str(cls.root / 'word/localhost.pem'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def request(self, method='POST', path='/api', data=None, token='fixture-token', origin=None, length=None):
        conn = http.client.HTTPSConnection('localhost', self.port, context=self.tls, timeout=5)
        headers = {'Authorization': 'Bearer ' + token}
        if origin is not None:
            headers['Origin'] = origin
        if length is not None:
            headers['Content-Length'] = length
        body = json.dumps(data).encode() if isinstance(data, dict) else data
        try:
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_binds_only_to_loopback(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')

    def test_second_service_cannot_share_word_connection_port(self):
        with self.assertRaises(OSError):
            service.make_server(self.root, self.api, port=self.port)

    def test_authenticated_whitelisted_result_over_verified_tls(self):
        code, headers, body = self.request(data={'method': 'word_sources', 'args': []},
                                         origin=f'https://localhost:{self.port}')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['result'], [{'id': 'fixture', 'title': 'Fixture source'}])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')

    def test_wrong_token_origin_and_method_do_not_reach_api(self):
        cases = [dict(token='wrong', data={'method': 'word_sources'}),
                 dict(origin='https://unrelated.example', data={'method': 'word_sources'}),
                 dict(data={'method': 'read_private_file'}),
                 dict(token='wrong', data={'method': 'shutdown'})]
        for case in cases:
            with self.subTest(case=case):
                before = len(self.api.calls)
                code, _, body = self.request(**case)
                self.assertEqual(code, 403)
                self.assertIn('error', json.loads(body))
                self.assertEqual(len(self.api.calls), before)

    def test_whitelisted_static_asset_and_path_traversal(self):
        code, _, body = self.request(method='GET', path='/word/addin.html')
        self.assertEqual(code, 200)
        self.assertIn(b'Fixture add-in', body)
        code, _, body = self.request(method='GET', path='/word/addin.html?_host_Info=Word')
        self.assertEqual(code, 200)
        self.assertIn(b'Fixture add-in', body)
        for path in ['/../word/service-config.json', '/word/../ai.json',
                     '/word/%2e%2e/ai.json', '/word/localhost-key.pem', '/word/service-config.json']:
            with self.subTest(path=path):
                code, _, _ = self.request(method='GET', path=path)
                self.assertEqual(code, 404)

    def test_bad_json_argument_shape_and_content_length_are_structured_errors(self):
        for params in [dict(data=b'not json'), dict(data={'method': 'word_sources', 'args': {}}),
                       dict(data=b'{}', length='not-a-number')]:
            with self.subTest(params=params):
                code, _, body = self.request(**params)
                self.assertEqual(code, 400)
                self.assertIn('error', json.loads(body))

    def test_empty_or_oversized_body_is_rejected_before_read(self):
        for length in ('0', '4000001'):
            with self.subTest(length=length):
                code, _, body = self.request(data=b'', length=length)
                self.assertEqual(code, 413)
                self.assertIn('error', json.loads(body))


if __name__ == '__main__':
    unittest.main(verbosity=2)
