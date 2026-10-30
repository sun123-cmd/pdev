"""Host-side Docker client. There is deliberately no host execution fallback."""
import json
import subprocess
import uuid

from .runner import failure


class JudgeUnavailable(Exception):
    pass


class DockerGrader:
    def __init__(self, image='fibolab-judge:local', timeout=5):
        self.image = image
        self.timeout = timeout

    def check(self):
        try:
            subprocess.run(['docker', 'image', 'inspect', self.image], check=True,
                           capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as error:
            raise JudgeUnavailable('Start Docker and build the judge image before starting the service.') from error

    def __call__(self, code):
        name = 'fibolab-' + uuid.uuid4().hex
        command = ['docker', 'run', '--rm', '--pull=never', '-i', '--name', name,
                   '--network=none', '--read-only', '--cap-drop=ALL',
                   '--security-opt=no-new-privileges', '--user=65534:65534',
                   '--memory=96m', '--memory-swap=96m', '--cpus=1', '--pids-limit=32',
                   '--ulimit=nofile=64:64', '--log-driver=none', self.image]
        try:
            process = subprocess.run(command, input=json.dumps({'code': code}),
                                     text=True, capture_output=True, timeout=self.timeout)
            if process.returncode in (125, 126, 127):
                raise JudgeUnavailable('The isolated judge is unavailable. Please ask the TA to check Docker.')
            if process.returncode != 0:
                return failure('Execution stopped: memory limit or runtime failure. Simplify the loop.')
            try:
                result = json.loads(process.stdout)
                if not isinstance(result.get('passed'), bool) or not isinstance(result.get('score'), int):
                    raise ValueError('Invalid judge result')
                return result
            except (ValueError, AttributeError) as error:
                raise JudgeUnavailable('The judge returned an invalid result. Please retry or ask the TA.') from error
        except subprocess.TimeoutExpired:
            return failure('Execution exceeded the time limit. Check for an infinite loop.')
        except OSError as error:
            raise JudgeUnavailable('Docker is unavailable on the server.') from error
        finally:
            # Also removes containers left running after the client timed out.
            try:
                subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass


class BubblewrapGrader:
    """Rootless Linux judge for lab hosts that already provide Bubblewrap."""
    def __init__(self, timeout=5):
        self.timeout = timeout

    def check(self):
        result = self('def fibonacci(n):\n    return []')
        if 'tests' not in result:
            raise JudgeUnavailable('The rootless judge could not run Python.')

    def __call__(self, code):
        import os
        from pathlib import Path
        import shutil
        import signal
        bwrap, prlimit = shutil.which('bwrap'), shutil.which('prlimit')
        if not bwrap or not prlimit:
            raise JudgeUnavailable('This host needs Bubblewrap and prlimit, or a working Docker judge.')
        command = [prlimit, '--as=134217728', '--cpu=2', '--nofile=64:64',
                   bwrap, '--unshare-all', '--die-with-parent', '--new-session',
                   '--ro-bind', '/usr', '/usr']
        for directory in ('/lib', '/lib64'):
            if Path(directory).exists():
                command.extend(['--ro-bind', directory, directory])
        command.extend(['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--chdir', '/tmp',
                        '--ro-bind', str(Path(__file__).with_name('runner.py').resolve()), '/judge.py',
                        '/usr/bin/python3', '-I', '-B', '/judge.py'])
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, start_new_session=True)
        try:
            output, error = process.communicate(json.dumps({'code': code}), timeout=self.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return failure('Execution exceeded the time limit. Check for an infinite loop.')
        if process.returncode != 0:
            if 'bwrap:' in error or 'prlimit:' in error:
                raise JudgeUnavailable('The rootless sandbox could not start: ' + error.strip()[:250])
            return failure('Execution stopped at a resource limit. Check the loop and memory use.')
        try:
            result = json.loads(output)
            if not isinstance(result.get('passed'), bool) or not isinstance(result.get('score'), int):
                raise ValueError('Invalid judge result')
            return result
        except (ValueError, AttributeError) as error:
            raise JudgeUnavailable('The rootless judge returned an invalid result.') from error


def available_grader():
    """Detect once at startup; never execute user input on the API host."""
    import shutil
    if shutil.which('bwrap') and shutil.which('prlimit'):
        grader = BubblewrapGrader()
        grader.check()
        return grader
    grader = DockerGrader()
    grader.check()
    return grader
