import http.server
import json
import subprocess
import sys
import os
import tempfile
import socketserver
import hashlib
import uuid
import httpx
from datetime import datetime

SUPABASE_URL = 'https://oikzwjqyctureqkcigrx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pa3p3anF5Y3R1cmVxa2NpZ3J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyMTYwMTUsImV4cCI6MjA5Nzc5MjAxNX0.-bL4yor0cSne_O7u84JQWKgkEK6ds3SbbrDAA4Rf_HE'

TOKEN_CACHE = {}

CALLBACK_HTML = '''<!DOCTYPE html><html><body><script>
(function(){
try{var h=new URLSearchParams(location.hash.slice(1));var t=h.get('access_token');if(t&&window.opener){window.opener.postMessage({type:"oauth",token:t},"*")}
}catch(e){}window.close()})()
</script></body></html>'''

def supabase(table):
    return SupabaseTable(table)

class SupabaseTable:
    def __init__(self, table):
        self.table = table
        self.base = f'{SUPABASE_URL}/rest/v1/{table}'
        self.headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

    def select(self, columns='*'):
        return self._query('GET', params={'select': columns})

    def insert(self, data):
        return self._query('POST', json=data)

    def eq(self, column, value):
        return self._query('GET', params={column: f'eq.{value}'})

    def _query(self, method, json=None, params=None):
        with httpx.Client() as client:
            if method == 'GET' and params and 'select' not in params:
                pass
            r = client.request(method, self.base, headers=self.headers, json=json, params=params)
            if r.status_code >= 400:
                raise Exception(f'Supabase error: {r.text}')
            return r.json()

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

BLOCKED_MODULES = [
    'os', 'subprocess', 'shutil', 'ctypes', 'signal', 'multiprocessing',
    'threading', 'socket', 'fcntl', 'code', 'codeop', 'compileall',
    'py_compile', 'zipfile', 'tarfile', 'pickle', 'shelve', 'marshal',
    'tempfile', 'fileinput', 'filecmp', 'mmap', '_thread', 'faulthandler',
    'importlib', 'pkgutil', 'pdb', 'traceback', 'inspect',
    'webbrowser', 'turtle', 'antigravity',
]

BLOCKED_PATTERNS = [
    'import os', 'from os', 'import subprocess', 'from subprocess',
    'import shutil', 'from shutil', 'import ctypes', 'from ctypes',
    'import sys', 'from sys', 'import socket', 'from socket',
    'import threading', 'from threading', 'import multiprocessing', 'from multiprocessing',
    '__import__', 'compile(', 'exec(', 'eval(',
    'open("/', "open('/", 'open("c:', "open('c:",
    '__builtins__', '__builtins__.',
]

def is_code_safe(code):
    for pat in BLOCKED_PATTERNS:
        if pat in code:
            return False, f'Code contains blocked pattern: {pat}'
    return True, ''

def hash_pass(password, salt=None):
    if not salt: salt = uuid.uuid4().hex[:16]
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f'{salt}${h}'

def check_pass(password, stored):
    salt, h = stored.split('$')
    return hash_pass(password, salt) == stored

def gen_token():
    return uuid.uuid4().hex + uuid.uuid4().hex

def get_user_for_token(token):
    if token in TOKEN_CACHE:
        return TOKEN_CACHE[token]
    try:
        sessions = supabase('sessions').eq('token', token)
        if sessions and len(sessions) > 0:
            users = supabase('users').eq('id', sessions[0]['user_id'])
            if users and len(users) > 0:
                username = users[0]['username']
                TOKEN_CACHE[token] = username
                return username
    except: pass
    return None

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

    def get_token(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '): return auth[7:]
        return None

    def require_auth(self):
        token = self.get_token()
        if not token: return None
        return get_user_for_token(token)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.end_headers()

    def do_POST(self):
        data = self.read_body()
        path = self.path

        if path == '/api/register':
            username = data.get('username', '').strip()
            password = data.get('password', '')
            if not username or not password:
                return self.send_error_json('الاسم وكلمة المرور مطلوبان')
            if len(password) < 8:
                return self.send_error_json('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
            try:
                existing = supabase('users').eq('username', username)
                if existing and len(existing) > 0:
                    return self.send_error_json('المستخدم موجود بالفعل')
                supabase('users').insert({
                    'username': username,
                    'password': hash_pass(password),
                    'created_at': datetime.now().isoformat()
                })
                users = supabase('users').eq('username', username)
                if not users or len(users) == 0:
                    return self.send_error_json('فشل إنشاء المستخدم')
                user_id = users[0]['id']
                token = gen_token()
                TOKEN_CACHE[token] = username
                supabase('sessions').insert({
                    'token': token,
                    'user_id': user_id,
                    'created_at': datetime.now().isoformat()
                })
                return self.send_json({'token': token, 'user': username})
            except Exception as e:
                return self.send_error_json(f'خطأ: {str(e)}')

        elif path == '/api/login':
            username = data.get('username', '').strip()
            password = data.get('password', '')
            try:
                users = supabase('users').eq('username', username)
                if not users or len(users) == 0:
                    return self.send_error_json('المستخدم غير موجود')
                user = users[0]
                if not check_pass(password, user['password']):
                    return self.send_error_json('كلمة المرور خطأ')
                token = gen_token()
                TOKEN_CACHE[token] = username
                supabase('sessions').insert({
                    'token': token,
                    'user_id': user['id'],
                    'created_at': datetime.now().isoformat()
                })
                return self.send_json({'token': token, 'user': username})
            except Exception as e:
                return self.send_error_json(f'خطأ: {str(e)}')

        elif path == '/api/run':
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
                self.send_json({'output': '', 'error': 'تجاوز الوقت (10 ثوان)'})
            except Exception as e:
                self.send_json({'output': '', 'error': str(e)})

        elif path == '/api/oauth-login':
            supabase_token = data.get('token', '')
            if not supabase_token:
                return self.send_error_json('Missing token')
            try:
                headers = {
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {supabase_token}'
                }
                with httpx.Client() as client:
                    resp = client.get(f'{SUPABASE_URL}/auth/v1/user', headers=headers)
                    if resp.status_code != 200:
                        return self.send_error_json('Invalid OAuth token')
                    user_data = resp.json()
                email = user_data.get('email', '')
                if not email:
                    return self.send_error_json('Email not found from provider')
                username = email
                existing = supabase('users').eq('username', username)
                if existing and len(existing) > 0:
                    user_row = existing[0]
                else:
                    supabase('users').insert({
                        'username': username,
                        'password': '',
                        'created_at': datetime.now().isoformat()
                    })
                    users = supabase('users').eq('username', username)
                    if not users or len(users) == 0:
                        return self.send_error_json('Failed to create user')
                    user_row = users[0]
                token = gen_token()
                TOKEN_CACHE[token] = user_row['username']
                supabase('sessions').insert({
                    'token': token,
                    'user_id': user_row['id'],
                    'created_at': datetime.now().isoformat()
                })
                return self.send_json({'token': token, 'user': user_row['username'], 'email': email})
            except Exception as e:
                return self.send_error_json(f'OAuth error: {str(e)}')

        else: self.send_error_json('غير معروف')

    def do_GET(self):
        raw_path = self.path
        parsed = raw_path.split('?', 1)
        path = parsed[0]
        qs = parsed[1] if len(parsed) > 1 else ''
        token = self.get_token()
        username = get_user_for_token(token) if token else None

        if path == '/api/me':
            if not username: return self.send_error_json('غير مصرح', 401)
            return self.send_json({'user': username})

        if path == '/auth/callback':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(CALLBACK_HTML.encode())
            return

        if path == '/': self.path = '/index.html'
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
