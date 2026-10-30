import os
from pathlib import Path
import tempfile
import unittest

from service.demo_host import public_links, read_state, write_state, selected_links


class DemoTests(unittest.TestCase):
    def test_student_link_never_contains_teacher_key(self):
        links = public_links('https://demo.example/', 'private-teacher-key')
        self.assertEqual(links['studentUrl'], 'https://demo.example/lab/')
        self.assertEqual(links['slidesUrl'], 'https://demo.example/')
        self.assertNotIn('private-teacher-key', links['studentUrl'])
        self.assertIn('#key=private-teacher-key', links['teacherUrl'])

    def test_lan_fallback_changes_existing_tunnel_links(self):
        state = {'lanUrl': 'http://10.0.0.8:8080', **public_links('https://old.trycloudflare.com', 'secret')}
        result = selected_links(state, 'lan')
        self.assertEqual(result['slidesUrl'], 'http://10.0.0.8:8080/')
        self.assertEqual(result['studentUrl'], 'http://10.0.0.8:8080/lab/')
        self.assertEqual(result['teacherUrl'], 'http://10.0.0.8:8080/lab/?view=teacher#key=secret')
        self.assertEqual(state['slidesUrl'], 'https://old.trycloudflare.com/')

    def test_state_is_atomic_private_and_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'state.json'
            write_state(target, {'phase': 'ready', 'pid': 123})
            self.assertEqual(read_state(target)['phase'], 'ready')
            if os.name == 'posix':
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_state(Path(folder) / 'missing'), {})


@unittest.skipUnless(os.environ.get('FIBOLAB_BWRAP_TESTS') == '1', 'Linux Bubblewrap tests require FIBOLAB_BWRAP_TESTS=1')
class BubblewrapTests(unittest.TestCase):
    def test_real_outputs_wrong_answer_and_timeout(self):
        from service.grader import BubblewrapGrader
        from test_lab import GOOD
        grader = BubblewrapGrader(timeout=3)
        grader.check()
        self.assertTrue(grader(GOOD)['passed'])
        self.assertFalse(grader(GOOD.replace('return result', 'return [999]'))['passed'])
        result = grader('def fibonacci(n):\n    while True:\n        pass')
        self.assertFalse(result['passed'])
        self.assertIn('limit', result['feedback'])
