import http.server
import json
import subprocess
import sys
import os
import tempfile
import socketserver
import time
from collections import defaultdict

BLOCKED_PATTERNS = [
    'import os', 'from os', 'import subprocess', 'from subprocess',
    'import shutil', 'from shutil', 'import ctypes', 'from ctypes',
    'import sys', 'from sys', 'import socket', 'from socket',
    'import threading', 'from threading', 'import multiprocessing', 'from multiprocessing',
    '__import__', 'compile(', 'exec(', 'eval(',
    'open("/', "open('/", 'open("c:', "open('c:",
    '__builtins__', '__builtins__.',
]

RATE_LIMIT = 10
RATE_WINDOW = 60
_rate_map = defaultdict(list)

def is_rate_limited(ip):
    now = time.time()
    _rate_map[ip] = [t for t in _rate_map[ip] if now - t < RATE_WINDOW]
    if len(_rate_map[ip]) >= RATE_LIMIT:
        return True
    _rate_map[ip].append(now)
    return False

def is_code_safe(code):
    for pat in BLOCKED_PATTERNS:
        if pat in code:
            return False, f'Code contains blocked pattern: {pat}'
    return True, ''

class Handler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_json(self, msg, code=400):
        self.send_json({'error': msg}, code)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/run':
            ip = self.client_address[0]
            if is_rate_limited(ip):
                return self.send_json({'output': '', 'error': 'Rate limit exceeded (10 runs per minute)'})
            data = self.read_body()
            code = data.get('code', '')
            safe, reason = is_code_safe(code)
            if not safe:
                return self.send_json({'output': '', 'error': f'Security error: {reason}'})
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(code); fname = f.name
                res = subprocess.run(
                    [sys.executable, '-I', fname],
                    capture_output=True, text=True, timeout=10
                )
                os.unlink(fname)
                self.send_json({'output': res.stdout, 'error': res.stderr})
            except subprocess.TimeoutExpired:
                os.unlink(fname)
                self.send_json({'output': '', 'error': 'Timeout (10 seconds)'})
            except Exception as e:
                self.send_json({'output': '', 'error': str(e)})
        else:
            self.send_error_json('Not found')

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, format, *args): pass

PORT = int(os.environ.get('PORT', '8000'))

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    print(f'[SERVER] http://0.0.0.0:{PORT}')
    sys.stdout.flush()
    ThreadedServer(('0.0.0.0', PORT), Handler).serve_forever()
