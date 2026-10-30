import tempfile
import unittest
from pathlib import Path

from service import runner
from service.store import Store

GOOD = '''def fibonacci(n):
    result = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result
'''


class GradingTests(unittest.TestCase):
    def test_actual_python_list_outputs(self):
        result = runner.grade(GOOD)
        self.assertTrue(result['passed'])
        self.assertEqual(result['score'], 50)
        self.assertEqual([row['input'] for row in result['tests']], [0, 1, 2, 8, 20])
        self.assertEqual(result['tests'][3]['actual'], [0, 1, 1, 2, 3, 5, 8, 13])

    def test_regex_shaped_but_wrong_code_fails(self):
        result = runner.grade(GOOD.replace('return result', 'wrong = 999\n    return wrong'))
        self.assertFalse(result['passed'])
        self.assertTrue(all(not row['passed'] for row in result['tests']))
        self.assertLess(result['score'], 50)

    def test_wrong_state_update_and_boundaries(self):
        result = runner.grade(GOOD.replace('a, b = b, a + b', 'a = b\n        b = a + b'))
        self.assertFalse(result['passed'])
        self.assertFalse(result['tests'][3]['passed'])

    def test_valid_while_and_different_variable_names(self):
        code = '''def fibonacci(n):
    values = []
    previous, current = 0, 1
    while len(values) < n:
        values.append(previous)
        previous, current = current, previous + current
    return values
'''
        self.assertTrue(runner.grade(code)['passed'])

    def test_comments_do_not_count_as_loop_and_recursion_rejected(self):
        self.assertFalse(runner.grade('def fibonacci(n):\n    # for while\n    return []')['passed'])
        recursive = 'def fibonacci(n):\n    return fibonacci(n-1) if n else []'
        self.assertFalse(runner.grade(recursive)['passed'])

    def test_recursion_cannot_hide_behind_allowed_builtin_name(self):
        code = 'def fibonacci(n):\n    for _ in range(1):\n        pass\n    if n < 2:\n        return [0] if n else []\n    list = fibonacci\n    result = list(n - 1)\n    result.append(1 if n == 2 else result[-1] + result[-2])\n    return result\n'
        self.assertFalse(runner.grade(code)['passed'])

    def test_imports_and_file_calls_rejected(self):
        for code in ['import os\n' + GOOD, 'def fibonacci(n):\n    return open("/etc/passwd").read()']:
            with self.subTest(code=code):
                self.assertFalse(runner.grade(code)['passed'])

    def test_syntax_and_runtime_errors_reported(self):
        self.assertIn('Syntax', runner.grade('def fibonacci(:')['feedback'])
        result = runner.grade('def fibonacci(n):\n    for i in range(n):\n        missing += 1\n    return missing')
        self.assertFalse(result['passed'])
        self.assertIn('Error', result['tests'][0]['error'])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'lab.sqlite'
        self.store = Store(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_registration_token_and_empty_board(self):
        student = self.store.register('Alex')
        self.assertEqual(self.store.authenticate(student['token'])['id'], student['id'])
        self.assertIsNone(self.store.authenticate('invalid-token'))
        self.assertEqual(self.store.standings(), [])

    def test_first_correct_order_survives_resubmissions_and_restart(self):
        a, b = self.store.register('Alex'), self.store.register('Bea')
        good = runner.grade(GOOD)
        bad = runner.grade('def fibonacci(n):\n    return []')
        self.store.submit(b['id'], 'bad', bad)
        self.store.submit(a['id'], GOOD, good)
        self.store.submit(b['id'], GOOD, good)
        self.store.submit(a['id'], 'bad retry', bad)
        rows = Store(self.path).standings()
        self.assertEqual([row['name'] for row in rows], ['Alex', 'Bea'])
        self.assertEqual(rows[0]['score'], 50)
        self.assertFalse(rows[0]['latestPassed'])
        self.assertTrue(rows[0]['passed'])
        self.assertEqual(rows[0]['attempts'], 2)
        self.assertNotIn('code', rows[0])
        self.assertNotIn('token', rows[0])

    def test_received_order_wins_even_if_second_judge_finishes_first(self):
        a, b = self.store.register('Alex'), self.store.register('Bea')
        first = self.store.begin(a['id'], GOOD)
        second = self.store.begin(b['id'], GOOD)
        self.assertEqual(self.store.standings()[0]['latestStatus'], 'running')
        good = runner.grade(GOOD)
        self.store.finish(second, good)
        self.store.finish(first, good)
        self.assertEqual([r['name'] for r in self.store.standings()], ['Alex', 'Bea'])

    def test_teacher_inspection_and_confirmation(self):
        student = self.store.register('Alex')
        self.store.submit(student['id'], GOOD, runner.grade(GOOD))
        details = self.store.details(student['id'])
        self.assertEqual(details['attempts'][0]['code'], GOOD)
        self.store.verify(student['id'])
        self.assertIsNotNone(self.store.standings()[0]['verifiedAt'])

    def test_cannot_verify_failed_submission(self):
        student = self.store.register('Alex')
        self.store.submit(student['id'], 'bad', runner.grade('bad'))
        with self.assertRaises(ValueError):
            self.store.verify(student['id'])
