"""Persistent students and attempts. First successful attempts are never overwritten."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
import uuid


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL, first_pass_id INTEGER, first_pass_at INTEGER,
                    verified_at INTEGER
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(id),
                    code TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}', score INTEGER NOT NULL DEFAULT 0,
                    passed INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'running', created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_student ON attempts(student_id, id);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, name):
        token, student_id = secrets.token_urlsafe(32), str(uuid.uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO students(id,name,token_hash,created_at) VALUES (?,?,?,?)',
                       (student_id, name, self._hash(token), self.now()))
        return {'id': student_id, 'name': name, 'token': token}

    @staticmethod
    def now():
        return time.time_ns() // 1_000_000

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute('SELECT id,name FROM students WHERE token_hash=?', (self._hash(token),)).fetchone()
            return dict(row) if row else None

    def begin(self, student_id, code):
        with self.connect() as db:
            attempt = db.execute('INSERT INTO attempts(student_id,code,created_at) VALUES (?,?,?)',
                                 (student_id, code, self.now()))
            return attempt.lastrowid

    def finish(self, attempt_id, result, status='judged'):
        with self.connect() as db:
            db.execute('UPDATE attempts SET result=?,score=?,passed=?,status=? WHERE id=?',
                       (json.dumps(result), result['score'], int(result['passed']), status, attempt_id))
            if result['passed']:
                attempt = db.execute('SELECT student_id,created_at FROM attempts WHERE id=?', (attempt_id,)).fetchone()
                db.execute('UPDATE students SET first_pass_id=?,first_pass_at=? WHERE id=? AND (first_pass_id IS NULL OR first_pass_id>?)',
                           (attempt_id, attempt['created_at'], attempt['student_id'], attempt_id))

    def submit(self, student_id, code, result):
        attempt_id = self.begin(student_id, code)
        self.finish(attempt_id, result)
        return attempt_id

    def recover_incomplete(self):
        result = {'score': 0, 'passed': False, 'tests': [], 'feedback': 'The server restarted during judging. Please resubmit.'}
        with self.connect() as db:
            db.execute("UPDATE attempts SET status='error',result=? WHERE status='running'", (json.dumps(result),))

    def standings(self):
        with self.connect() as db:
            rows = db.execute('''
                SELECT s.id,s.name,s.first_pass_at,s.verified_at,
                    MAX(a.score) AS score, COUNT(a.id) AS attempts,
                    (SELECT passed FROM attempts WHERE student_id=s.id ORDER BY id DESC LIMIT 1) AS latest_passed,
                    (SELECT status FROM attempts WHERE student_id=s.id ORDER BY id DESC LIMIT 1) AS latest_status,
                    MAX(a.created_at) AS last_submitted_at
                FROM students s JOIN attempts a ON a.student_id=s.id GROUP BY s.id
                ORDER BY s.first_pass_id IS NULL, s.first_pass_id, s.created_at, s.id
            ''').fetchall()
        return [{'id': row['id'], 'name': row['name'], 'score': row['score'], 'attempts': row['attempts'],
                 'passed': row['first_pass_at'] is not None, 'firstPassedAt': row['first_pass_at'],
                 'latestPassed': bool(row['latest_passed']), 'latestStatus': row['latest_status'], 'lastSubmittedAt': row['last_submitted_at'],
                 'verifiedAt': row['verified_at'], 'rank': index + 1 if row['first_pass_at'] is not None else None}
                for index, row in enumerate(rows)]

    def details(self, student_id):
        with self.connect() as db:
            student = db.execute('SELECT id,name,first_pass_id FROM students WHERE id=?', (student_id,)).fetchone()
            if student is None:
                raise ValueError('Student not found.')
            attempts = db.execute('SELECT id,code,result,status,created_at FROM attempts WHERE student_id=? ORDER BY id DESC', (student_id,)).fetchall()
        return {'id': student['id'], 'name': student['name'], 'firstPassedAttemptId': student['first_pass_id'],
                'attempts': [{'id': a['id'], 'code': a['code'], 'result': json.loads(a['result']), 'status': a['status'], 'createdAt': a['created_at']} for a in attempts]}

    def verify(self, student_id):
        with self.connect() as db:
            row = db.execute('SELECT first_pass_id FROM students WHERE id=?', (student_id,)).fetchone()
            if not row or row['first_pass_id'] is None:
                raise ValueError('A fully correct submission is required before TA confirmation.')
            db.execute('UPDATE students SET verified_at=COALESCE(verified_at,?) WHERE id=?', (self.now(), student_id))
