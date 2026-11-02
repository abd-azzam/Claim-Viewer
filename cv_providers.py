"""Claim Viewer model connections; keys use the app's Windows DPAPI helper."""
import json
import uuid
import urllib.request
import urllib.parse
import urllib.error
import time

# Cloudflare in front of some providers rejects a bare urllib request with 403 "error code: 1010".
# A normal browser User-Agent and Accept is all it wants; nothing else about the request changes.
UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}


def _catalog_urls(provider, base):
    """Where the model list really lives. OpenCode serves /models under /inference/v1, not under the
    /inference/openai/v1 base its chat endpoint uses, so try the known root first and the base after."""
    urls = []
    if provider == 'opencode' and 'opencode.ai/inference' in base:
        urls.append('https://opencode.ai/inference/v1/models')
    urls.append(base.rstrip('/') + '/models')
    return list(dict.fromkeys(urls))


class Providers:
    def __init__(self, path, encrypt, decrypt, write):
        self.path, self.encrypt, self.decrypt, self.write = path, encrypt, decrypt, write
        self.catalogs = {}

    def read(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding='utf-8'))

    def list(self):
        return [dict({k: v for k, v in p.items() if k != 'secret'}, id=i, has_key=bool(p.get('secret')))
                for i, p in self.read().items()]

    def save(self, text):
        p = json.loads(text)
        if not all(str(p.get(k, '')).strip() for k in ('name', 'base', 'model')):
            raise ValueError('Enter a connection name, base URL and model ID.')
        url = urllib.parse.urlsplit(p['base'].strip())
        url.port  # Reject malformed numeric ports before storing the connection.
        if not url.hostname or url.username or url.password or url.query or url.fragment or not (
                url.scheme == 'https' or (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1'))):
            raise ValueError('Use HTTPS, or HTTP for a local server.')
        if p.get('protocol') not in ('chat', 'anthropic', 'responses'):
            raise ValueError('Choose an API protocol.')
        data = self.read()
        ident = p.get('id') or uuid.uuid4().hex
        old = data.get(ident, {})
        same = p['base'].strip().rstrip('/') == old.get('base', '').rstrip('/') and p.get('provider', '') == old.get('provider', '')
        secret = self.encrypt(p['key'].strip()) if p.get('key', '').strip() else old.get('secret', '') if same else ''
        data[ident] = {k: str(p.get(k, '')).strip() for k in ('name', 'base', 'model', 'protocol', 'provider')}
        data[ident]['secret'] = secret
        data[ident]['all_models'] = bool(p.get('all_models'))
        self.catalogs.pop(ident, None)
        self.write(str(self.path), json.dumps(data, indent=2))
        return ident

    def delete(self, ident):
        data = self.read()
        data.pop(ident, None)
        self.write(str(self.path), json.dumps(data, indent=2))

    def models(self, text):
        p = json.loads(text)
        old = self.read().get(p.get('id'), {})
        # A stored credential must never follow a provider or endpoint change.
        same = p.get('base', '').rstrip('/') == old.get('base', '').rstrip('/') and p.get('provider') == old.get('provider')
        key = p.get('key', '').strip() or (self.decrypt(old['secret']) if same and old.get('secret') else '')
        base = p.get('base', '').rstrip('/')
        url = urllib.parse.urlsplit(base)
        url.port
        if url.username or url.password or url.query or url.fragment or not url.hostname or not (
                url.scheme == 'https' or (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1'))):
            raise ValueError('Use HTTPS, or HTTP for a local server.')
        endpoint_list = _catalog_urls(p.get('provider'), base)
        headers = dict(UA)
        if key:
            headers['Authorization'] = 'Bearer ' + key
        if p.get('protocol') == 'anthropic':
            headers = dict(UA, **{'x-api-key': key, 'anthropic-version': '2023-06-01'})
        last = None
        for endpoint in endpoint_list:
            try:
                with urllib.request.urlopen(urllib.request.Request(endpoint, headers=headers), timeout=20) as response:
                    result = json.load(response)
                ids = list(dict.fromkeys(m['id'] for m in result.get('data', [])
                                         if isinstance(m, dict) and isinstance(m.get('id'), str)))
                if ids:
                    return ids
            except urllib.error.HTTPError as e:
                last = e
                try:
                    body = e.read().decode('utf-8', 'replace')[:120]
                except Exception:
                    body = ''
                if e.code != 404:
                    last = ValueError('HTTP %s %s' % (e.code, body))
                    break
            except Exception as e:
                last = e
                break
        if isinstance(last, urllib.error.HTTPError):
            raise ValueError('HTTP %s' % last.code)
        raise last if last else ValueError('the provider listed no models')

    def choices(self):
        choices, labels, errors = [], {}, []
        for p in self.list():
            models = [p['model']]
            if p.get('all_models'):
                cached = self.catalogs.get(p['id'])
                try:
                    if not cached or time.monotonic() - cached[0] > 300:
                        cached = (time.monotonic(), self.models(json.dumps(p)))
                        self.catalogs[p['id']] = cached
                    models = list(dict.fromkeys(models + cached[1]))
                except Exception as e:
                    errors.append(p['name'] + ': model list unavailable (' + str(e)[:140] + '); saved model remains available.')
                    if cached:
                        models = list(dict.fromkeys(models + cached[1]))
            for model in models:
                ident = 'profile:' + p['id'] + (':' + urllib.parse.quote(model, safe='') if model != p['model'] else '')
                choices.append(ident)
                labels[ident] = p['name'] + ' / ' + model
        return choices, labels, errors

    def stream(self, ident, messages, state):
        return self.chat(ident, messages, state)

    def chat(self, ident, messages, state=None):
        ident, _, selected = ident.partition(':')
        p = self.read().get(ident)
        if not p:
            raise ValueError('This model connection no longer exists. Choose another model.')
        key = self.decrypt(p['secret']) if p.get('secret') else ''
        model = urllib.parse.unquote(selected) if selected else p['model']
        headers = dict(UA, **{'Content-Type': 'application/json'})
        msgs = [{'role': m['role'], 'content': str(m['content'])} for m in messages]
        protocol = p['protocol']
        if protocol == 'anthropic':
            endpoint = 'messages'
            headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
            body = {'model': model, 'max_tokens': 8192,
                    'system': '\n'.join(m['content'] for m in msgs if m['role'] in ('system', 'developer')),
                    'messages': [m for m in msgs if m['role'] in ('user', 'assistant')]}
        elif protocol == 'responses':
            endpoint = 'responses'
            headers['Authorization'] = 'Bearer ' + key
            body = {'model': model, 'input': msgs, 'max_output_tokens': 8192, 'store': False}
        else:
            endpoint = 'chat/completions'
            headers['Authorization'] = 'Bearer ' + key
            body = {'model': model, 'messages': msgs, 'stream': False}
        base = p['base'].rstrip('/')
        url = base if base.endswith('/' + endpoint) else base + '/' + endpoint
        if state is not None:
            body['stream'] = True
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=180) as response:
            if state is not None:
                for raw in response:
                    line = raw.decode('utf-8', 'replace').strip()
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        break
                    event = json.loads(data)
                    if event.get('error') or event.get('type') == 'error':
                        raise ValueError(str(event.get('error', 'Provider stream failed')))
                    if protocol == 'anthropic':
                        delta = event.get('delta') or {}
                        state['r'] += delta.get('thinking', '')
                        state['c'] += delta.get('text', '')
                        if delta.get('stop_reason') == 'max_tokens':
                            state['finish'] = 'length'
                    elif protocol == 'responses':
                        kind = event.get('type', '')
                        if kind == 'response.output_text.delta':
                            state['c'] += event.get('delta', '')
                        elif kind in ('response.reasoning_summary_text.delta', 'response.reasoning_text.delta'):
                            state['r'] += event.get('delta', '')
                        elif kind in ('response.failed', 'response.incomplete'):
                            raise ValueError('Provider response did not complete')
                    else:
                        for choice in event.get('choices', []):
                            delta = choice.get('delta') or {}
                            state['r'] += delta.get('reasoning_content') or delta.get('reasoning') or ''
                            state['c'] += delta.get('content') or ''
                            if choice.get('finish_reason'):
                                state['finish'] = choice['finish_reason']
                return
            result = json.load(response)
        if protocol == 'anthropic':
            text = '\n'.join(b.get('text', '') for b in result.get('content', []) if b.get('type') == 'text')
            reasoning = '\n'.join(b.get('thinking', '') for b in result.get('content', []) if b.get('type') == 'thinking')
        elif protocol == 'responses':
            text = '\n'.join(b.get('text', '') for o in result.get('output', []) for b in o.get('content', []) if b.get('type') == 'output_text')
            reasoning = '\n'.join(b.get('text', '') for o in result.get('output', []) if o.get('type') == 'reasoning' for b in o.get('summary', []) if b.get('type') == 'summary_text')
        else:
            message = result['choices'][0]['message']
            text = message.get('content') or ''
            reasoning = message.get('reasoning_content') or message.get('reasoning') or ''
        if not text.strip():
            raise ValueError('The provider returned no answer text. Check the model ID and API protocol.')
        return {'ok': True, 'text': text, 'model': model, 'reasoning': reasoning if isinstance(reasoning, str) else ''}
