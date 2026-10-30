#!/usr/bin/env python3
"""One-click start/stop client. Default target is the user's existing lab SSH alias."""
import argparse
import base64
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
REMOTE = r'''
import base64, json, os
from pathlib import Path
import subprocess, sys
payload = json.load(sys.stdin)
root = Path.home() / '.local' / 'share' / 'pdev-demo'
root.mkdir(parents=True, exist_ok=True)
state_file = root / '.demo' / 'state.json'
state = json.loads(state_file.read_text()) if state_file.exists() else {}
alive = False
pid = state.get('pid')
if isinstance(pid, int) and pid > 1:
    try:
        alive = b'service.demo_host' in Path('/proc/%d/cmdline' % pid).read_bytes()
    except OSError:
        pass
if not alive:
    for name, content in payload.get('files', {}).items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Invalid source path')
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(content))
args = [sys.executable, '-m', 'service.demo_host', payload['action'],
        '--hours', str(payload['hours']), '--access', payload['access']]
result = subprocess.run(args, cwd=root)
raise SystemExit(result.returncode)
'''


def sources():
    names = ['index.html', 'lesson.html']
    for folder in ('lab', 'assets', 'service', 'tests'):
        names.extend(str(path.relative_to(ROOT)) for path in (ROOT / folder).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    return {name: base64.b64encode((ROOT / name).read_bytes()).decode() for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status'), nargs='?', default='start')
    parser.add_argument('--ssh-host', default='factlab-dev0-out')
    parser.add_argument('--local', action='store_true', help='Use this computer instead of SSH.')
    parser.add_argument('--access', choices=('tunnel', 'lan'), default='tunnel')
    parser.add_argument('--hours', type=float, default=4)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    if args.action == 'stop' and not args.local and (ROOT / '.demo' / 'state.json').exists():
        subprocess.run([sys.executable, '-m', 'service.demo_host', 'stop'], cwd=ROOT, capture_output=True)
    if args.local:
        if args.action == 'start' and sys.platform == 'darwin':
            import shutil, time
            docker = shutil.which('docker')
            if not docker:
                raise OSError('本机备用模式需要预先安装 Docker Desktop；实验室模式无需它。')
            ready = subprocess.run([docker, 'info'], capture_output=True).returncode == 0
            if not ready:
                print('正在打开 Docker Desktop…', flush=True)
                subprocess.run(['open', '-a', 'Docker'], check=True)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if subprocess.run([docker, 'info'], capture_output=True).returncode == 0:
                        ready = True; break
                    time.sleep(2)
            if not ready:
                raise OSError('Docker Desktop 未就绪；请在彩排时完成初始化。')
            if subprocess.run([docker, 'image', 'inspect', 'fibolab-judge:local'], capture_output=True).returncode != 0:
                print('首次准备本机判题镜像…', flush=True)
                subprocess.run([docker, 'build', '-f', 'service/Dockerfile.judge', '-t', 'fibolab-judge:local', '.'], cwd=ROOT, check=True)
        command = [sys.executable, '-m', 'service.demo_host', args.action, '--access', args.access, '--hours', str(args.hours)]
        print('正在' + ('启动' if args.action == 'start' else '查询/停止') + '本机演示服务…', flush=True)
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    else:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*', args.ssh_host):
            parser.error('Invalid SSH host alias.')
        print(f'正在连接 {args.ssh_host}；首次启动通常需要约一分钟…', flush=True)
        payload = {'action': args.action, 'access': args.access, 'hours': args.hours,
                   'files': sources() if args.action == 'start' else {}}
        command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15',
                   args.ssh_host, 'python3 -c ' + shlex.quote(REMOTE)]
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, timeout=110)
    if result.returncode != 0:
        print('未能启动/连接服务：\n' + result.stderr + result.stdout, file=sys.stderr)
        print('若临时公网连接不可用，可双击「局域网演示.command」。不要在演出现场首次测试网络。', file=sys.stderr)
        return 1
    try:
        state = json.loads(result.stdout)
    except ValueError:
        print('服务器未返回有效状态：' + result.stdout + result.stderr, file=sys.stderr)
        return 1
    if state.get('phase') != 'ready':
        print('服务状态：' + state.get('phase', '尚未启动'))
        return 0 if args.action != 'start' else 1
    if args.action == 'stop':
        print('服务仍在退出，请稍后再点「结束演示」。')
        return 1
    local = ROOT / '.demo'
    local.mkdir(exist_ok=True)
    from datetime import datetime
    ends = datetime.fromtimestamp(state['expiresAt'] / 1000).astimezone().strftime('%m-%d %H:%M')
    instructions = ('课堂演示已就绪\n\n课件：' + state['slidesUrl'] + '\n学生：' + state['studentUrl'] +
                    '\n教师（私人链接，请勿发给学生）：' + state['teacherUrl'] +
                    '\n局域网备用入口：' + state['lanUrl'] + '\n自动停止时间：' + ends +
                    '\n\n学生二维码在课件第 6 页，现场链接由本次启动自动生成。\n结束后双击「结束演示.command」。\n')
    links_file = local / '本次演示链接.txt'
    links_file.write_text(instructions)
    links_file.chmod(0o600)
    print('已就绪。\n课件：' + state['slidesUrl'] + '\n学生：' + state['studentUrl'] +
          '\n自动停止：' + ends + '\n教师私人链接已保存在 .demo/本次演示链接.txt。')
    if not args.no_open:
        webbrowser.open(state['teacherUrl'])
        webbrowser.open(state['slidesUrl'])
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (subprocess.SubprocessError, OSError) as error:
        print('连接失败：' + str(error), file=sys.stderr)
        sys.exit(1)
