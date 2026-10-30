"""Small classroom API and optional static frontend server (Python 3.11+)."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit
import mimetypes

from .grader import DockerGrader, JudgeUnavailable
from .store import Store
from .runner import failure

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 90_000


def create_server(host, port, store, grader, admin_token, allowed_origins, session=None):
    slots = threading.BoundedSemaphore(2)
    active_students = set()
    active_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'FiboLab/1.0'

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, fmt, *args):
            logging.info('%s %s', self.address_string(), fmt % args)

        def send_data(self, status, data):
            raw = json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.common_headers()
            self.end_headers()
            self.wfile.write(raw)

        def common_headers(self):
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            origin = self.headers.get('Origin')
            if origin in allowed_origins:
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')

        def origin_allowed(self):
            origin = self.headers.get('Origin')
            # Same-origin deployments should also list their public origin. Loopback works locally.
            if not origin or origin in allowed_origins:
                return True
            return origin in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}

        def bearer(self):
            value = self.headers.get('Authorization', '')
            return value[7:] if value.startswith('Bearer ') else ''

        def teacher(self):
            return bool(admin_token) and hmac.compare_digest(self.bearer(), admin_token)

        def read_json(self):
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('Use application/json.')
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_BODY:
                raise ValueError('Request body is empty or too large.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object.')
            return payload

        def do_OPTIONS(self):
            if not self.origin_allowed():
                return self.send_data(403, {'error': 'This website origin is not allowed.'})
            self.send_response(204)
            self.common_headers()
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

        def do_GET(self):
            path = urlsplit(self.path).path
            if not self.origin_allowed():
                return self.send_data(403, {'error': 'This website origin is not allowed.'})
            if path == '/api/health':
                try:
                    grader.check()
                except JudgeUnavailable as error:
                    return self.send_data(503, {'error': str(error)})
                return self.send_data(200, {'ok': True})
            if path == '/api/session' and session is not None:
                return self.send_data(200, {key: session.get(key) for key in ('expiresAt', 'studentUrl', 'phase')})
            if path == '/api/standings':
                return self.send_data(200, {'students': store.standings()})
            if path.startswith('/api/teacher/students/'):
                if not self.teacher():
                    return self.send_data(401, {'error': 'Enter the teacher access key.'})
                try:
                    return self.send_data(200, store.details(path.rsplit('/', 1)[-1]))
                except ValueError as error:
                    return self.send_data(404, {'error': str(error)})
            return self.static_file(path)

        def do_POST(self):
            if not self.origin_allowed():
                return self.send_data(403, {'error': 'This website origin is not allowed.'})
            try:
                data = self.read_json()
                path = urlsplit(self.path).path
                if path == '/api/students':
                    name = data.get('name')
                    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
                        raise ValueError('Enter a display name between 1 and 40 characters.')
                    return self.send_data(201, store.register(name.strip()))
                if path == '/api/teacher/verify':
                    if not self.teacher():
                        return self.send_data(401, {'error': 'Enter the teacher access key.'})
                    student_id = data.get('studentId')
                    if not isinstance(student_id, str):
                        raise ValueError('Student ID is required.')
                    store.verify(student_id)
                    return self.send_data(200, {'ok': True})
                if path != '/api/submissions':
                    return self.send_data(404, {'error': 'Endpoint not found.'})
                student = store.authenticate(self.bearer())
                if not student:
                    return self.send_data(401, {'error': 'Please register your name again on this browser.'})
                code = data.get('code')
                if not isinstance(code, str) or not code.strip() or len(code) > 20_000:
                    raise ValueError('Submit between 1 and 20,000 characters of Python code.')
                with active_lock:
                    if student['id'] in active_students:
                        return self.send_data(429, {'error': 'Your previous submission is still running.'})
                    active_students.add(student['id'])
                acquired = False
                try:
                    acquired = slots.acquire(blocking=False)
                    if not acquired:
                        return self.send_data(429, {'error': 'The judge is busy. Please retry in a few seconds.'})
                    attempt_id = store.begin(student['id'], code)
                    try:
                        result = grader(code)
                    except JudgeUnavailable as error:
                        store.finish(attempt_id, failure(str(error)), status='error')
                        raise
                    store.finish(attempt_id, result)
                    result['attemptId'] = attempt_id
                    return self.send_data(201, result)
                finally:
                    if acquired:
                        slots.release()
                    with active_lock:
                        active_students.discard(student['id'])
            except (ValueError, UnicodeError) as error:
                return self.send_data(400, {'error': str(error)})
            except JudgeUnavailable as error:
                return self.send_data(503, {'error': str(error)})
            except Exception:
                logging.exception('Submission request failed')
                return self.send_data(500, {'error': 'Server error. Please retry or ask the TA.'})

        def static_file(self, path):
            relative = unquote(path).lstrip('/')
            if not relative or relative.endswith('/'):
                relative += 'index.html'
            target = (ROOT / relative).resolve()
            allowed = (target in {ROOT / 'index.html', ROOT / 'lesson.html'} or
                       target.is_relative_to(ROOT / 'assets') or target.is_relative_to(ROOT / 'lab'))
            if not allowed or not target.is_relative_to(ROOT) or not target.is_file():
                return self.send_data(404, {'error': 'File not found.'})
            raw = target.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(len(raw)))
            self.common_headers()
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer((host, port), Handler)
    # Wait for bounded in-flight graders so their container cleanup cannot be abandoned.
    server.daemon_threads = False
    server.block_on_close = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    token = os.environ.get('FIBOLAB_ADMIN_TOKEN', '')
    if len(token) < 16:
        parser.error('Set FIBOLAB_ADMIN_TOKEN to a teacher key of at least 16 characters.')
    origins = {origin.strip().rstrip('/') for origin in os.environ.get('FIBOLAB_ALLOWED_ORIGINS', '').split(',') if origin.strip()}
    store = Store(os.environ.get('FIBOLAB_DB', str(ROOT / 'data' / 'fibolab.sqlite')))
    store.recover_incomplete()
    grader = DockerGrader(os.environ.get('FIBOLAB_JUDGE_IMAGE', 'fibolab-judge:local'))
    grader.check()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    server = create_server(args.host, args.port, store, grader, token, origins)
    logging.info('FiboLab listening on http://%s:%s', args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
