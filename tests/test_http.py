import json
import os
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from service.grader import BubblewrapGrader, DockerGrader
from service.server import create_server
from service.store import Store
from test_lab import GOOD


@unittest.skipUnless(os.environ.get('FIBOLAB_DOCKER_TESTS') == '1' or os.environ.get('FIBOLAB_BWRAP_TESTS') == '1', 'Enable FIBOLAB_DOCKER_TESTS or FIBOLAB_BWRAP_TESTS for real sandbox HTTP tests')
class LiveServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = create_server('127.0.0.1', 0, Store(self.tmp.name + '/lab.db'),
                                    (BubblewrapGrader(timeout=3) if os.environ.get('FIBOLAB_BWRAP_TESTS') == '1' else DockerGrader(timeout=3)), 'teacher-secret', {'https://class.example'})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, data=None, token=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if origin:
            headers['Origin'] = origin
        req = Request(self.url + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            with urlopen(req, timeout=15) as response:
                return response.status, json.load(response), response.headers
        except HTTPError as error:
            return error.code, json.load(error), error.headers

    def test_real_submission_shared_board_and_teacher_verification(self):
        status, user, _ = self.request('/api/students', {'name': 'Alex <script>'})
        self.assertEqual(status, 201)
        status, result, _ = self.request('/api/submissions', {'code': GOOD}, user['token'])
        self.assertEqual(status, 201)
        self.assertTrue(result['passed'])
        _, board, headers = self.request('/api/standings', origin='https://class.example')
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'https://class.example')
        self.assertEqual(board['students'][0]['rank'], 1)
        self.assertNotIn('code', board['students'][0])
        self.assertEqual(self.request('/api/teacher/students/' + user['id'])[0], 401)
        _, details, _ = self.request('/api/teacher/students/' + user['id'], token='teacher-secret')
        self.assertEqual(details['attempts'][0]['code'], GOOD)
        self.assertEqual(self.request('/api/teacher/verify', {'studentId': user['id']}, 'teacher-secret')[0], 200)
        self.assertIsNotNone(self.request('/api/standings')[1]['students'][0]['verifiedAt'])

    def test_invalid_tokens_origins_and_payloads(self):
        self.assertEqual(self.request('/api/submissions', {'code': GOOD})[0], 401)
        self.assertEqual(self.request('/api/students', {'name': 17})[0], 400)
        self.assertEqual(self.request('/api/students', {'name': 'Alex'}, origin='https://evil.example')[0], 403)
        _, user, _ = self.request('/api/students', {'name': 'Alex'})
        self.assertEqual(self.request('/api/submissions', {'code': 'x' * 20001}, user['token'])[0], 400)

    def test_wrong_answer_and_timeout(self):
        _, user, _ = self.request('/api/students', {'name': 'Bea'})
        wrong = GOOD.replace('return result', 'wrong = 999\n    return wrong')
        status, result, _ = self.request('/api/submissions', {'code': wrong}, user['token'])
        self.assertEqual(status, 201)
        self.assertFalse(result['passed'])
        code = 'def fibonacci(n):\n    while True:\n        pass'
        status, result, _ = self.request('/api/submissions', {'code': code}, user['token'])
        self.assertEqual(status, 201)
        self.assertIn('limit', result['feedback'])
        self.assertFalse(self.request('/api/standings')[1]['students'][0]['passed'])

    def test_stop_waits_for_active_judge_cleanup(self):
        _, user, _ = self.request('/api/students', {'name': 'Active student'})
        worker = threading.Thread(target=lambda: self.request('/api/submissions',
            {'code': 'def fibonacci(n):\n    while True:\n        pass'}, user['token']), daemon=True)
        worker.start()
        for _ in range(100):
            rows = self.request('/api/standings')[1]['students']
            if rows and rows[0]['latestStatus'] == 'running':
                break
            time.sleep(.02)
        else:
            self.fail('Submission never entered the running state')
        self.server.shutdown()
        self.server.server_close()
        worker.join(timeout=.2)
        try:
            self.assertFalse(worker.is_alive(), 'Stopping must wait for the active judge to finish cleanup')
        finally:
            worker.join(timeout=15)

    def test_static_pages_and_server_source_not_exposed(self):
        with urlopen(self.url + '/lab/') as response:
            self.assertIn(b'FiboLab', response.read())
        self.assertEqual(self.request('/service/server.py')[0], 404)
        self.assertEqual(self.request('/lab/%2e%2e/service/server.py')[0], 404)
