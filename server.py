import http.server
import json
import subprocess
import sys
import os
import tempfile
import socketserver
import hashlib
import uuid
import random
import smtplib
import httpx
from datetime import datetime, timedelta
from email.mime.text import MIMEText

SUPABASE_URL = 'https://oikzwjqyctureqkcigrx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pa3p3anF5Y3R1cmVxa2NpZ3J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyMTYwMTUsImV4cCI6MjA5Nzc5MjAxNX0.-bL4yor0cSne_O7u84JQWKgkEK6ds3SbbrDAA4Rf_HE'

TOKEN_CACHE = {}

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USER or 'noreply@uscrovis.xyz')

def gen_code():
    return str(random.randint(100000, 999999))

def send_verification_code(email, code):
    if not SMTP_USER or not SMTP_PASS:
        print(f'[SMTP] Not configured — would send code {code} to {email}')
        return False
    msg = MIMEText(f'Welcome to Uscrovis!\n\nYour verification code is: {code}\n\nThis code expires in 10 minutes.\n\nIf you did not request this, please ignore this email.')
    msg['Subject'] = 'Uscrovis — Verify Your Email'
    msg['From'] = SMTP_FROM
    msg['To'] = email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f'[SMTP] Code sent to {email}')
        return True
    except Exception as e:
        print(f'[SMTP] Error: {e}')
        return False

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

    def patch(self, data, column, value):
        with httpx.Client() as client:
            r = client.patch(
                self.base,
                headers=self.headers,
                json=data,
                params={column: f'eq.{value}'}
            )
            if r.status_code >= 400:
                raise Exception(f'Supabase error: {r.text}')
            return r.json() if r.text else None

    def _query(self, method, json=None, params=None):
        with httpx.Client() as client:
            if method == 'GET' and params and 'select' not in params:
                params['select'] = '*'
            r = client.request(method, self.base, headers=self.headers, json=json, params=params)
            if r.status_code >= 400:
                raise Exception(f'Supabase error: {r.text}')
            return r.json() if r.text else None

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
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            if not email or not password:
                return self.send_error_json('Email and password required')
            if '@' not in email or '.' not in email:
                return self.send_error_json('Invalid email address')
            if len(password) < 8:
                return self.send_error_json('Password must be at least 8 characters')
            try:
                existing = supabase('users').eq('username', email)
                if existing and len(existing) > 0:
                    return self.send_error_json('This email is already registered')
                code = gen_code()
                supabase('users').insert({
                    'username': email,
                    'password': hash_pass(password),
                    'email_verified': False,
                    'verification_code': code,
                    'code_sent_at': datetime.now().isoformat(),
                    'created_at': datetime.now().isoformat()
                })
                sent = send_verification_code(email, code)
                if not sent:
                    # SMTP not configured — auto-verify for development
                    supabase('users').patch(
                        {'email_verified': True, 'verification_code': ''},
                        'username', email
                    )
                    users = supabase('users').eq('username', email)
                    if users and len(users) > 0:
                        uid = users[0]['id']
                        token = gen_token()
                        TOKEN_CACHE[token] = email
                        supabase('sessions').insert({
                            'token': token, 'user_id': uid,
                            'created_at': datetime.now().isoformat()
                        })
                        return self.send_json({'token': token, 'user': email})
                return self.send_json({'message': 'Verification code sent', 'email': email})
            except Exception as e:
                return self.send_error_json(f'Error: {str(e)}')

        elif path == '/api/verify-email':
            email = data.get('email', '').strip().lower()
            code = data.get('code', '').strip()
            if not email or not code:
                return self.send_error_json('Email and code required')
            try:
                users = supabase('users').eq('username', email)
                if not users or len(users) == 0:
                    return self.send_error_json('User not found')
                user = users[0]
                if user.get('email_verified'):
                    return self.send_error_json('Email already verified')
                stored_code = user.get('verification_code', '')
                if stored_code != code:
                    return self.send_error_json('Invalid verification code')
                supabase('users').patch(
                    {'email_verified': True, 'verification_code': ''},
                    'username', email
                )
                token = gen_token()
                TOKEN_CACHE[token] = email
                supabase('sessions').insert({
                    'token': token, 'user_id': user['id'],
                    'created_at': datetime.now().isoformat()
                })
                return self.send_json({'token': token, 'user': email})
            except Exception as e:
                return self.send_error_json(f'Error: {str(e)}')

        elif path == '/api/login':
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            if not email or not password:
                return self.send_error_json('Email and password required')
            try:
                users = supabase('users').eq('username', email)
                if not users or len(users) == 0:
                    return self.send_error_json('No account with this email')
                user = users[0]
                if not check_pass(password, user['password']):
                    return self.send_error_json('Incorrect password')
                if not user.get('email_verified'):
                    return self.send_error_json('Please verify your email first')
                token = gen_token()
                TOKEN_CACHE[token] = email
                supabase('sessions').insert({
                    'token': token, 'user_id': user['id'],
                    'created_at': datetime.now().isoformat()
                })
                return self.send_json({'token': token, 'user': email})
            except Exception as e:
                return self.send_error_json(f'Error: {str(e)}')

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
