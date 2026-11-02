"""Provider streams must expose text before the response closes, without a network call."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cv_providers import Providers


class Response:
    def __init__(self, events):
        self.lines = [('data: ' + json.dumps(event) + '\n').encode() for event in events]

    def __enter__(self):
        return iter(self.lines)

    def __exit__(self, *args):
        pass


class ProviderStreaming(unittest.TestCase):
    def test_protocols(self):
        cases = {
            'openai': [{'choices': [{'delta': {'reasoning_content': 'Reason', 'content': 'Answer'}, 'finish_reason': 'stop'}]}],
            'anthropic': [{'delta': {'thinking': 'Reason'}}, {'delta': {'text': 'Answer'}}],
            'responses': [{'type': 'response.reasoning_summary_text.delta', 'delta': 'Reason'},
                          {'type': 'response.output_text.delta', 'delta': 'Answer'}],
        }
        for protocol, events in cases.items():
            with self.subTest(protocol=protocol):
                service = Providers.__new__(Providers)
                service.read = lambda: {'test': {'protocol': protocol, 'model': 'test', 'base': 'https://example.invalid/v1'}}
                state = {'r': '', 'c': ''}
                def request(req, **kwargs):
                    self.assertTrue(json.loads(req.data)['stream'])
                    return Response(events)
                with patch('cv_providers.urllib.request.urlopen', request):
                    service.stream('test', [{'role': 'user', 'content': 'Question'}], state)
                self.assertEqual((state['r'], state['c']), ('Reason', 'Answer'))

    def test_provider_errors_are_not_silently_ignored(self):
        service = Providers.__new__(Providers)
        service.read = lambda: {'test': {'protocol': 'openai', 'model': 'test', 'base': 'https://example.invalid/v1'}}
        with patch('cv_providers.urllib.request.urlopen', lambda *a, **k: Response([{'error': {'message': 'Rejected'}}])):
            with self.assertRaisesRegex(ValueError, 'Rejected'):
                service.stream('test', [], {'r': '', 'c': ''})


if __name__ == '__main__':
    unittest.main()
