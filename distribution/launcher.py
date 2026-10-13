"""Interactive, offline coding-agent preview launcher using Python's stdlib."""
import argparse
from pathlib import Path
import subprocess
import sys
import types


PREVIEW_VERSION = '0.2.0'
HOST_NAMES = {'codex': 'Codex', 'claude-code': 'Claude Code'}


def find_bundle(script):
    directory = Path(script).absolute().parent
    for candidate in (directory, directory.parent):
        if (candidate / 'runtime/kproto.py').is_file():
            return candidate
    raise FileNotFoundError('같은 배포 폴더에서 runtime/kproto.py를 찾을 수 없습니다.')


def load_runtime(bundle):
    path = bundle / 'runtime/kproto.py'
    module = types.ModuleType('_korean_protocol_launcher_runtime')
    module.__file__ = str(path)
    # Compile in memory so merely viewing or declining creates no bytecode files.
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def default_state_dir(runtime, host='codex'):
    return runtime.default_state_dir().parent / ('korean-protocol-' + host)


def read_status(runtime, state_dir):
    """Inspect through runtime readers without its directory-creating constructor."""
    root = runtime.safe_path(state_dir)
    values = []
    for name in ('state.json', 'config.json'):
        path = root / name
        value = runtime.strict_json(runtime.read_bytes(path, runtime.MAX_TOTAL_BYTES)) if path.exists() else {}
        if not isinstance(value, dict):
            raise runtime.InputError('설치 상태 파일은 JSON 객체여야 합니다.')
        values.append(value)
    state, config = values
    return dict(state, installed=bool(state.get('target')),
                autoupdate=config.get('mode', 'off'),
                recovery_required=(root / 'journal.json').exists())


def show_status(runtime, state_dir, codex_home, host='codex', claude_home=None):
    target = runtime.host_target(argparse.Namespace(
        host=host, scope='user', project_root=None, codex_home=codex_home, claude_home=claude_home))
    status = read_status(runtime, state_dir)
    print('\n' + HOST_NAMES[host] + ' 사용자 범위 대상: ' + str(target))
    print('상태 폴더: ' + str(state_dir))
    print('설치 상태: ' + ('설치됨' if status['installed'] else '미설치'))
    if status['installed']:
        print('설치 기록의 대상: ' + str(status['target']))
        print('설치 버전: ' + str(status.get('version', '확인 불가')))
        print('설치 기록의 신뢰 상태: ' + str(status.get('trust', '확인 불가')))
    print('이 배포의 유형: 서명 없는 미리보기 · 오프라인 로컬 파일')
    print('자동 업데이트: 설치 시 끔 / 현재 상태 ' + str(status['autoupdate']))
    if status['recovery_required']:
        print('복구 기록이 있습니다. 실행기가 변경 작업 전에 복구를 처리합니다.')
    return status


def run_runtime(bundle, state_dir, action, codex_home, host='codex', claude_home=None):
    command = [sys.executable, str(bundle / 'runtime/kproto.py'),
               '--state-dir', str(state_dir), action]
    if action == 'install':
        command += ['--bundle', str(bundle), '--host', host, '--scope', 'user',
                    '--profile', 'coding-agent', '--local-snapshot', '--version', PREVIEW_VERSION,
                    '--autoupdate', 'off']
        if host == 'codex' and codex_home is not None:
            command += ['--codex-home', str(codex_home)]
        if host == 'claude-code' and claude_home is not None:
            command += ['--claude-home', str(claude_home)]
    # Capture stderr so a Ctrl-C in the child does not emit its Python traceback.
    result = subprocess.run(command, shell=False, stderr=subprocess.PIPE, text=True)
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    print('실행기 종료 코드: ' + str(result.returncode))
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description='Korean Protocol 오프라인 Codex·Claude Code 미리보기 메뉴')
    parser.add_argument('--host', choices=['codex', 'claude-code'], help='설치할 코딩 에이전트를 지정합니다.')
    parser.add_argument('--state-dir', type=Path, help='격리된 설치 상태 폴더를 지정합니다.')
    parser.add_argument('--codex-home', type=Path, help='Codex 사용자 지침 폴더를 지정합니다.')
    parser.add_argument('--claude-home', type=Path, help='Claude Code 사용자 설정 폴더를 지정합니다.')
    args = parser.parse_args(argv)
    runtime = None
    try:
        host = args.host
        if host is None:
            print('Korean Protocol · 코딩 에이전트 선택')
            while host is None:
                print('\n1. Codex\n2. Claude Code\n0. 종료')
                choice = input('번호를 입력하세요: ').strip()
                if choice == '0':
                    return 0
                host = {'1': 'codex', '2': 'claude-code'}.get(choice)
                if host is None:
                    print('0, 1, 2 중 하나를 입력하세요.')
        bundle = find_bundle(__file__)
        runtime = load_runtime(bundle)
        state_dir = (args.state_dir or default_state_dir(runtime, host)).absolute()
        codex_home = args.codex_home.absolute() if args.codex_home is not None else None
        claude_home = args.claude_home.absolute() if args.claude_home is not None else None
        print('Korean Protocol · ' + HOST_NAMES[host] + ' 미리보기')
        show_status(runtime, state_dir, codex_home, host, claude_home)
        while True:
            print('\n1. ' + HOST_NAMES[host] + ' 사용자 범위에 설치\n2. 설치 상태 확인\n3. 설치한 규약 제거\n0. 종료')
            choice = input('번호를 입력하세요: ').strip()
            if choice == '0':
                return 0
            if choice == '2':
                show_status(runtime, state_dir, codex_home, host, claude_home)
            elif choice in ('1', '3'):
                status = show_status(runtime, state_dir, codex_home, host, claude_home)
                if choice == '1':
                    print('기존 지침에 규약 블록을 추가합니다. 기존 지침 보존은 실행기가 검사합니다.')
                    prompt = '이 파일에 서명 없는 미리보기를 설치할까요? [y/n]: '
                else:
                    if status['installed']:
                        print('제거 대상: ' + str(status['target']))
                    print('실행기는 설치한 규약 블록만 제거하고 기존 지침을 보존합니다.')
                    prompt = '설치한 규약을 제거할까요? [y/n]: '
                if input(prompt).strip().lower() != 'y':
                    print('취소했습니다. 파일을 변경하지 않았습니다.')
                    continue
                code = run_runtime(bundle, state_dir, 'install' if choice == '1' else 'uninstall', codex_home, host, claude_home)
                if code:
                    return code
            else:
                print('0, 1, 2, 3 중 하나를 입력하세요.')
    except EOFError:
        print('\n입력이 끝나 종료합니다.')
        return 0
    except KeyboardInterrupt:
        print('\n중단했습니다.')
        return 130
    except OSError as exc:
        print('로컬 파일 또는 실행기를 열 수 없습니다: ' + str(exc))
        return 8
    except Exception as exc:
        if runtime is not None and isinstance(exc, runtime.ProtocolError):
            print('실행기 오류: ' + str(exc))
            return exc.code
        raise


if __name__ == '__main__':
    sys.exit(main())
