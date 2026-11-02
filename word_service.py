"""Local HTTPS transport for the Word-hosted task pane. Never listens on the LAN."""
import hmac
import json
import pathlib
import socket
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 38491

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

METHODS = {'word_action', 'word_sources', 'ai_models', 'ai_status', 'ai_connections', 'ai_chat'}
FILES = {'/word/addin.html': ('word/addin.html', 'text/html'),
         '/word/word.css': ('word/word.css', 'text/css'),
         '/word/word.js': ('word/word.js', 'text/javascript'),
         '/word/office-bridge.js': ('word/office-bridge.js', 'text/javascript'),
         '/lib/provider-settings.css': ('lib/provider-settings.css', 'text/css'),
         '/lib/provider-settings.js': ('lib/provider-settings.js', 'text/javascript')}
for size in (16, 32, 80):
    FILES[f'/word/icon-{size}.png'] = (f'word/icon-{size}.png', 'image/png')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log document text, source metadata or credentials.

    def send(self, status, content, kind='application/json'):
        if isinstance(content, dict):
            content = json.dumps(content).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind+'; charset=utf-8' if not kind.startswith('image/') else kind)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = self.path.partition('?')[0]
        if path == '/health':
            return self.send(200, {'service': 'Claim Viewer Word', 'version': 1})
        resource = FILES.get(path)
        if not resource:
            return self.send(404, {'error': 'Not found'})
        return self.send(200, (self.root / resource[0]).read_bytes(), resource[1])

    def do_POST(self):
        if self.path != '/api':
            return self.send(404, {'error': 'Not found'})
        auth = self.headers.get('Authorization', '')
        if not hmac.compare_digest(auth.encode(), ('Bearer '+self.token).encode()):
            return self.send(403, {'error': 'Open the Claim Viewer add-in from Word again to reconnect.'})
        origin = self.headers.get('Origin')
        if origin and origin != f'https://localhost:{self.server.server_port}':
            return self.send(403, {'error': 'Origin not allowed'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.send(400, {'error': 'Invalid request length'})
        if length < 1 or length > 4_000_000:
            return self.send(413, {'error': 'Request is empty or too large.'})
        try:
            request = json.loads(self.rfile.read(length))
            method = request['method']
            if method == 'shutdown':
                self.send(200, {'result': {'ok': True}})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if method not in METHODS:
                return self.send(403, {'error': 'Method not allowed'})
            args = request.get('args', [])
            if not isinstance(args, list):
                raise ValueError('Invalid arguments')
            result = getattr(self.api, method)(*args)
            self.send(200, {'result': result})
        except Exception as e:
            self.send(400, {'error': str(e)[:300]})

def make_server(root, api, port=PORT):
    root = pathlib.Path(root)
    config = json.loads((root/'word/service-config.json').read_text(encoding='utf-8'))
    handler = type('WordHandler', (Handler,), {'root': root, 'api': api, 'token': config['token']})
    server = LocalServer(('127.0.0.1', port), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(root/'word/localhost.pem', root/'word/localhost-key.pem')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server

def serve(root, api):
    server = make_server(root, api)
    server.serve_forever()
