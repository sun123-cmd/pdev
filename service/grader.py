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
