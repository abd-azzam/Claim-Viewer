"""Deterministic provider tests. Uses temp files, fake crypto, and mocked HTTP only."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('claim_viewer_providers', APP / 'cv_providers.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='provider-fixture-', dir=APP / 'tools')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'providers.json'
        self.encrypted = []

        def encrypt(key):
            self.encrypted.append(key)
            return 'fake-crypto:' + base64.b64encode(key.encode()).decode()

        def decrypt(value):
            assert value.startswith('fake-crypto:')
            return base64.b64decode(value.split(':', 1)[1]).decode()

        def write(path, text):
            self.assertEqual(Path(path), self.path)
            Path(path).write_text(text, encoding='utf-8')

        self.providers = module.Providers(self.path, encrypt, decrypt, write)

    def save(self, **values):
        data = dict(name='Fixture model', base='https://provider.example/v1',
                    model='fixture-model', protocol='chat', key='fixture-secret-key')
        data.update(values)
        return self.providers.save(json.dumps(data))

    def request(self, ident, response):
        captured = []

        def urlopen(request, timeout):
            captured.append((request, timeout))
            return io.BytesIO(json.dumps(response).encode())

        messages = [dict(role='system', content='System guidance'),
                    dict(role='developer', content='Developer guidance'),
                    dict(role='user', content='Question'),
                    dict(role='assistant', content='Prior answer')]
        with patch.object(module.urllib.request, 'urlopen', side_effect=urlopen):
            reply = self.providers.chat(ident, messages)
        self.assertEqual(len(captured), 1)
        return reply, captured[0][0], messages

    def test_multiple_profiles_edit_delete_and_no_plaintext_key_exposure(self):
        a = self.save(name='A')
        b = self.save(name='B', key='another-fixture-key')
        self.assertNotEqual(a, b)
        listed = self.providers.list()
        self.assertEqual({p['id'] for p in listed}, {a, b})
        self.assertTrue(all(p['has_key'] for p in listed))
        self.assertNotIn('secret', json.dumps(listed))
        self.assertNotIn('fixture-secret-key', json.dumps(listed))
        self.assertNotIn('fixture-secret-key', self.path.read_text())
        self.assertNotIn('another-fixture-key', self.path.read_text())
        self.assertEqual(self.save(id=a, name='Renamed'), a)
        self.assertEqual(len(self.providers.list()), 2)
        self.providers.delete(a)
        self.assertEqual([p['id'] for p in self.providers.list()], [b])
        self.providers.delete('missing')
        self.assertEqual(len(self.providers.list()), 1)

    def test_blank_key_keeps_existing_secret(self):
        ident = self.save()
        before = self.providers.read()[ident]['secret']
        calls = len(self.encrypted)
        self.save(id=ident, key='   ', model='updated-model')
        self.assertEqual(self.providers.read()[ident]['secret'], before)
        self.assertEqual(len(self.encrypted), calls)

    def test_chat_payload_and_answer_extraction(self):
        ident = self.save()
        reply, request, messages = self.request(ident, {'choices': [{'message': {'content': 'Chat answer'}}]})
        body = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://provider.example/v1/chat/completions')
        self.assertEqual(body['messages'], messages)
        self.assertFalse(body['stream'])
        self.assertEqual(body['model'], 'fixture-model')
        self.assertEqual(request.get_header('Authorization'), 'Bearer fixture-secret-key')
        self.assertEqual(reply['text'], 'Chat answer')

    def test_responses_payload_and_text_only_extraction(self):
        ident = self.save(protocol='responses', base='https://provider.example/v1/responses/')
        reply, request, messages = self.request(ident, {'output': [
            {'type': 'reasoning', 'summary': []},
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'First'},
                                          {'type': 'refusal', 'refusal': 'ignore'},
                                          {'type': 'output_text', 'text': 'Second'}]}]})
        body = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://provider.example/v1/responses')
        self.assertEqual(body['input'], messages)
        self.assertFalse(body['store'])
        self.assertEqual(reply['text'], 'First\nSecond')

    def test_anthropic_roles_payload_headers_and_text_extraction(self):
        ident = self.save(protocol='anthropic')
        reply, request, messages = self.request(ident, {'content': [
            {'type': 'thinking', 'thinking': 'ignore'},
            {'type': 'text', 'text': 'First'}, {'type': 'text', 'text': 'Second'}]})
        body = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://provider.example/v1/messages')
        self.assertEqual(body['system'], 'System guidance\nDeveloper guidance')
        self.assertEqual(body['messages'], messages[2:])
        self.assertEqual(body['max_tokens'], 8192)
        self.assertEqual(request.get_header('X-api-key'), 'fixture-secret-key')
        self.assertEqual(request.get_header('Anthropic-version'), '2023-06-01')
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(reply['text'], 'First\nSecond')

    def test_empty_answer_and_missing_profile_fail_loudly(self):
        ident = self.save()
        with self.assertRaisesRegex(ValueError, 'no answer text'):
            self.request(ident, {'choices': [{'message': {'content': '   '}}]})
        with self.assertRaisesRegex(ValueError, 'no longer exists'):
            self.providers.chat('missing', [])

    def test_reasoning_is_retained_separately_from_the_answer(self):
        cases=[('chat',{'choices':[{'message':{'content':'Answer','reasoning_content':'Provider explanation'}}]}),
               ('anthropic',{'content':[{'type':'thinking','thinking':'Provider explanation'},{'type':'text','text':'Answer'}]}),
               ('responses',{'output':[{'type':'reasoning','summary':[{'type':'summary_text','text':'Provider explanation'}]},{'type':'message','content':[{'type':'output_text','text':'Answer'}]}]})]
        for protocol,response in cases:
            with self.subTest(protocol=protocol):
                ident=self.save(protocol=protocol)
                reply,request,messages=self.request(ident,response)
                self.assertEqual(reply['text'],'Answer')
                self.assertEqual(reply['reasoning'],'Provider explanation')

    def test_missing_reasoning_does_not_invent_an_explanation(self):
        reply,_,_=self.request(self.save(),{'choices':[{'message':{'content':'Answer'}}]})
        self.assertEqual(reply['reasoning'],'')

    def test_failed_model_catalog_keeps_saved_model_and_reports_error(self):
        ident=self.save(all_models=True)
        self.providers.catalogs[ident]=(0,['cached-model'])
        with patch.object(self.providers,'models',side_effect=ValueError('catalog offline')):
            choices,labels,errors=self.providers.choices()
        self.assertEqual(len(choices),2)
        self.assertIn('catalog offline',errors[0])

    def test_rejects_invalid_protocol_and_missing_required_fields(self):
        for values in [dict(protocol='unsupported'), dict(name=''), dict(base=''), dict(model='')]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.save(**values)
        self.assertFalse(self.path.exists())

    def test_rejects_insecure_and_malformed_urls(self):
        for url in ['http://remote.example/v1', 'file:///tmp/model', 'ftp://provider.example',
                    'https://', 'http://localhost:8080@remote.example/v1',
                    'http://127.0.0.1:8080@remote.example/v1', 'http://localhost:bad/v1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.save(base=url)

    def test_accepts_loopback_http_and_https(self):
        for url in ['http://localhost:8080/v1', 'http://127.0.0.1:11434/v1', 'https://provider.example/v1']:
            with self.subTest(url=url):
                ident = self.save(base=url)
                self.assertEqual(self.providers.read()[ident]['base'], url)


    def test_one_opencode_key_exposes_entire_catalog_and_routes_chosen_model(self):
        ident = self.save(provider='opencode', base='https://opencode.ai/inference/openai/v1', all_models=True)
        catalog = {'data': [{'id': 'model/' + str(i)} for i in range(75)]}
        with patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(catalog).encode())) as fetch:
            choices, labels, errors = self.providers.choices()
        self.assertEqual(len(choices), 76)
        self.assertFalse(errors)
        self.assertEqual(fetch.call_args.args[0].full_url, 'https://opencode.ai/inference/v1/models')
        reply, request, _ = self.request(ident + ':model%2F74', {'choices': [{'message': {'content': 'Answer'}}]})
        self.assertEqual(json.loads(request.data)['model'], 'model/74')
        self.assertEqual(reply['model'], 'model/74')

    def test_catalog_failure_keeps_saved_model_and_reports_warning(self):
        ident = self.save(all_models=True)
        with patch.object(module.urllib.request, 'urlopen', side_effect=OSError('offline')):
            choices, _, errors = self.providers.choices()
        self.assertEqual(choices, ['profile:' + ident])
        self.assertTrue(errors)

    def test_model_discovery_does_not_send_saved_key_to_changed_endpoint(self):
        ident = self.save(provider='opencode')
        for base, provider, expected in [('https://provider.example/v1','opencode',True),
                                         ('https://other.example/v1','opencode',False),
                                         ('https://provider.example/v1','custom',False)]:
            with patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"data":[{"id":"fixture"}]}')) as fetch:
                self.providers.models(json.dumps(dict(id=ident, base=base, provider=provider)))
                self.assertEqual(bool(fetch.call_args.args[0].get_header('Authorization')), expected)

if __name__ == '__main__':
    unittest.main(verbosity=2)
