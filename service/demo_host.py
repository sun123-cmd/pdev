"""Temporary demo lifecycle. Leaves no service running after stop or the deadline."""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import quote

from .grader import available_grader
from .server import create_server
from .store import Store

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / '.demo'


def read_state(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def write_state(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with open(temporary, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        json.dump(data, stream)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def public_links(base, key):
    base = base.rstrip('/')
    return {'slidesUrl': base + '/', 'studentUrl': base + '/lab/',
            'teacherUrl': base + '/lab/?view=teacher#key=' + quote(key, safe='')}


def selected_links(state, access):
    if access != 'lan' or not state.get('lanUrl'):
        return state
    result = state.copy()
    base = state['lanUrl'].rstrip('/')
    fragment = state.get('teacherUrl', '').partition('#')[2]
    result.update({'slidesUrl': base + '/', 'studentUrl': base + '/lab/',
                   'teacherUrl': base + '/lab/?view=teacher#' + fragment})
    return result


def own_process(pid):
    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        proc = Path(f'/proc/{pid}/cmdline')
        if proc.exists():
            return b'service.demo_host' in proc.read_bytes()
        command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'command='], text=True)
        return 'service.demo_host' in command
    except (OSError, subprocess.SubprocessError):
        return False


def lan_address():
    if sys.platform == 'darwin':
        # Prefer Wi-Fi over a VPN's default route for students on the same LAN.
        for device in ('en0', 'en1'):
            try:
                address = subprocess.check_output(['/usr/sbin/ipconfig', 'getifaddr', device], text=True, stderr=subprocess.DEVNULL).strip()
                if address:
                    return address
            except (OSError, subprocess.SubprocessError):
                pass
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(('1.1.1.1', 80))
        return connection.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        connection.close()


def run(args):
    runtime = args.runtime
    runtime.mkdir(parents=True, exist_ok=True)
    # An OS lock prevents two launchers from starting duplicate sessions.
    import fcntl
    lock = (runtime / 'session.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    state_path = runtime / 'state.json'
    state = {'phase': 'starting', 'pid': os.getpid(), 'expiresAt': int((time.time() + args.hours * 3600) * 1000)}
    write_state(state_path, state)
    stopping = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopping.set())
    server = tunnel = tunnel_stream = None
    try:
        grader = available_grader()
        store = Store(runtime / 'class.sqlite')
        store.recover_incomplete()
        key_path = runtime / 'teacher.json'
        key = read_state(key_path).get('key') or secrets.token_urlsafe(32)
        write_state(key_path, {'key': key})
        origins = set()
        server = create_server('0.0.0.0', 0, store, grader, key, origins, session=state)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        lan_url = f'http://{lan_address()}:{server.server_port}'
        origins.add(lan_url)
        state.update({'lanUrl': lan_url, 'port': server.server_port})
        base = lan_url
        if args.access == 'tunnel':
            import shutil
            cloudflared = shutil.which('cloudflared')
            if not cloudflared:
                raise RuntimeError('cloudflared is unavailable. Start with --access lan instead.')
            log_path = runtime / 'tunnel.log'
            tunnel_stream = log_path.open('w')
            config = runtime / 'cloudflared.yml'
            config.write_text('{}\n')
            tunnel = subprocess.Popen([cloudflared, '--config', str(config), '--no-autoupdate', 'tunnel',
                                       '--protocol', 'http2', '--url', f'http://127.0.0.1:{server.server_port}'],
                                      stdin=subprocess.DEVNULL, stdout=tunnel_stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline and not stopping.is_set():
                text = log_path.read_text(errors='replace')
                found = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
                if found and ('Registered tunnel connection' in text):
                    base = found.group()
                    break
                if tunnel.poll() is not None:
                    raise RuntimeError('The temporary tunnel could not start. See .demo/tunnel.log; use LAN mode if needed.')
                stopping.wait(.25)
            else:
                raise RuntimeError('The temporary tunnel did not become ready. Use LAN mode or retry before class.')
        origins.add(base)
        state.update(public_links(base, key))
        state['phase'] = 'ready'
        write_state(state_path, state)
        while not stopping.is_set() and time.time() * 1000 < state['expiresAt']:
            if tunnel and tunnel.poll() is not None:
                raise RuntimeError('The public tunnel stopped. Restart the demo or use the LAN URL.')
            stopping.wait(.5)
        state['phase'] = 'stopped'
    except Exception as error:
        logging.exception('Demo session failed')
        state.update({'phase': 'error', 'error': str(error)})
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel.kill()
                tunnel.wait()
        if tunnel_stream:
            tunnel_stream.close()
        if server:
            server.shutdown()
            server.server_close()
        state['stoppedAt'] = int(time.time() * 1000)
        write_state(state_path, state)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'run', 'status', 'stop'))
    parser.add_argument('--runtime', type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument('--hours', type=float, default=4)
    parser.add_argument('--access', choices=('tunnel', 'lan'), default='tunnel')
    args = parser.parse_args()
    args.runtime = args.runtime.resolve()
    if not 0 < args.hours <= 12:
        parser.error('Session duration must be greater than zero and at most 12 hours.')
    state_path = args.runtime / 'state.json'
    state = read_state(state_path)
    if args.action == 'run':
        run(args)
        return
    if args.action == 'stop':
        if own_process(state.get('pid')):
            os.kill(state['pid'], signal.SIGTERM)
            deadline = time.monotonic() + 20
            while own_process(state['pid']) and time.monotonic() < deadline:
                time.sleep(.1)
        print(json.dumps(read_state(state_path)))
        return
    if args.action == 'status':
        if state.get('phase') in ('ready', 'starting') and not own_process(state.get('pid')):
            state.update({'phase': 'stopped'})
        print(json.dumps(state))
        return
    if state.get('phase') == 'ready' and own_process(state.get('pid')):
        print(json.dumps(selected_links(state, args.access)))
        return
    args.runtime.mkdir(parents=True, exist_ok=True)
    with (args.runtime / 'session.log').open('a') as log:
        child = subprocess.Popen([sys.executable, '-m', 'service.demo_host', 'run', '--runtime', str(args.runtime),
                                  '--hours', str(args.hours), '--access', args.access], cwd=ROOT,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 70
    while time.monotonic() < deadline:
        state = read_state(state_path)
        if state.get('pid') == child.pid and state.get('phase') in ('ready', 'error'):
            print(json.dumps(selected_links(state, args.access)))
            if state['phase'] == 'error':
                sys.exit(1)
            return
        if child.poll() is not None:
            raise SystemExit('Demo supervisor exited; inspect .demo/session.log.')
        time.sleep(.2)
    os.kill(child.pid, signal.SIGTERM)
    raise SystemExit('Startup timed out. Session was stopped; inspect .demo/session.log.')


if __name__ == '__main__':
    main()
