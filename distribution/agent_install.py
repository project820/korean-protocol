"""Offline, noninteractive coding-agent installation and durable management."""
import sys
# macOS Python writes imported stdlib bytecode below HOME unless disabled.
# Read-only plan/status must avoid those side effects as well as state writes.
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import types

VERSION = '0.2.0'
TOOL_NAME = 'agent-tool'
TOOL_FILES = ('agent-install.py', 'runtime/kproto.py')
LIMIT = 4 * 1024 * 1024


class AgentError(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def safe_path(path):
    path = Path(os.path.abspath(os.path.expanduser(str(path))))
    for item in reversed((path,) + tuple(path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise AgentError('Symbolic links are not supported: ' + str(item))
        if item != path and not stat.S_ISDIR(info.st_mode):
            raise AgentError('Parent path is not a directory: ' + str(item))
    return path


def read_file(path, owned=False):
    path = safe_path(path)
    if os.name != 'posix':
        raise AgentError('Descriptor-based path protection requires POSIX', 6)
    parent_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > LIMIT:
            raise AgentError('Expected a bounded, unlinked regular file: ' + str(path))
        if owned and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022):
            raise AgentError('Managed file must be owned by user and not writable by others: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise AgentError('File exceeds size limit: ' + str(path))
        return data
    finally:
        os.close(fd)


def json_object(path, owned=False):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AgentError('JSON contains duplicate keys: ' + str(path))
            result[key] = value
        return result
    try:
        value = json.loads(read_file(path, owned).decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError, RecursionError):
        raise AgentError('Invalid JSON object: ' + str(path)) from None
    if not isinstance(value, dict):
        raise AgentError('Expected a JSON object: ' + str(path))
    return value


def check_directory(path):
    path = safe_path(path)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise AgentError('Managed directory must be owned by user and not writable by others: ' + str(path))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def find_bundle(script):
    directory = safe_path(script).parent
    for candidate in (directory, directory.parent):
        if (candidate / 'runtime/kproto.py').exists():
            return candidate
    raise AgentError('Cannot find runtime/kproto.py beside this installer', 4)


def verify_tool(tool, host=None, expected=None):
    check_directory(tool)
    check_directory(tool / 'runtime')
    metadata = json_object(tool / 'owner.json', owned=True)
    if (set(metadata) != {'schema', 'version', 'host', 'state_dir', 'files'} or
            metadata['schema'] != 1 or metadata['version'] != VERSION or
            metadata['host'] not in ('codex', 'claude-code') or
            metadata['state_dir'] != str(tool.parent) or
            not isinstance(metadata['files'], dict) or set(metadata['files']) != set(TOOL_FILES)):
        raise AgentError('Unrecognized or stale management tool; preserve it and use its original release', 7)
    if host is not None and metadata['host'] != host:
        raise AgentError('State directory belongs to a different host', 7)
    for name in TOOL_FILES:
        raw = read_file(tool / name, owned=True)
        if digest(raw) != metadata['files'][name]:
            raise AgentError('Management tool integrity check failed: ' + name, 5)
        if expected is not None and raw != expected[name]:
            raise AgentError('Management tool differs from this release; existing tool preserved', 7)
    return metadata


def load_runtime(bundle):
    if bundle.name == TOOL_NAME:
        check_directory(bundle.parent)
        verify_tool(bundle)
    path = bundle / 'runtime/kproto.py'
    module = types.ModuleType('_korean_protocol_agent_runtime')
    module.__file__ = str(path)
    exec(compile(read_file(path), str(path), 'exec'), module.__dict__)
    return module


def read_status(runtime, root, host, verify_cache=True):
    if root.exists():
        check_directory(root)
    state_path = safe_path(root / 'state.json')
    config_path = safe_path(root / 'config.json')
    state = json_object(state_path, owned=True) if state_path.exists() else {}
    config = json_object(config_path, owned=True) if config_path.exists() else {}
    journal_path = safe_path(root / 'journal.json')
    contexts = [state]
    if journal_path.exists():
        journal = json_object(journal_path, owned=True)
        contexts += [journal.get('old_state', {}), journal.get('new_state', {})]
        if not isinstance(journal.get('new_state'), dict) or not any(
                value.get('target') == journal.get('target') for value in contexts
                if isinstance(value, dict) and value.get('target')):
            raise AgentError('Recovery target has no verified host ownership', 7)
    for value in contexts:
        if not isinstance(value, dict):
            raise AgentError('Invalid recovery state', 2)
        context = value.get('host_context', {})
        if not isinstance(context, dict):
            raise AgentError('Invalid recorded host context', 2)
        if value.get('target') and (context.get('host') != host or context.get('scope') != 'user'):
            raise AgentError('State owns a different or unverified host/scope', 7)
        if value.get('target') and (not isinstance(value['target'], str) or not Path(value['target']).is_absolute()):
            raise AgentError('Invalid recorded target path')
    verified = False
    if state.get('target') and not journal_path.exists():
        # Reuse runtime marker/hash validation without its writing constructor.
        reader = object.__new__(runtime.Controller)
        reader._split(read_file(state['target']), state)
        if verify_cache:
            cache_id = state.get('cache_id')
            if not isinstance(cache_id, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{64}', cache_id):
                raise AgentError('Invalid recorded cache identity', 5)
            cache = safe_path(root / 'releases' / cache_id)
            metadata = json_object(cache / 'metadata.json', owned=True)
            release_hash = digest(read_file(cache / 'release.json', owned=True))
            files = runtime.content_files(cache)
            if (metadata.get('version') != state.get('version') or metadata.get('trust') != state.get('trust') or
                    metadata.get('hash') != release_hash or cache_id != str(state.get('version')) + '-' + release_hash or
                    metadata.get('files') != {name: digest(data) for name, data in files.items()}):
                raise AgentError('Cached protocol integrity check failed', 5)
            verified = True
    return dict(state, installed=bool(state.get('target')), verified=verified,
                autoupdate=config.get('mode', 'off'), recovery_required=journal_path.exists())


def persist_tool(runtime, root, host, bundle):
    files = {'agent-install.py': read_file(__file__),
             'runtime/kproto.py': read_file(bundle / 'runtime/kproto.py')}
    tool = root / TOOL_NAME
    controller = runtime.Controller(root)
    with controller.lock():
        if tool.exists():
            verify_tool(tool, host, files)
            return tool
        # A new reserved directory is the ownership boundary. Never replace an
        # existing incomplete tool: it may contain unrelated or modified files.
        tool.mkdir(mode=0o700)
        (tool / 'runtime').mkdir(mode=0o700)
        for name, data in files.items():
            runtime.atomic_write(tool / name, data, expected=b'')
        metadata = {'schema': 1, 'version': VERSION, 'host': host, 'state_dir': str(root),
                    'files': {name: digest(data) for name, data in files.items()}}
        runtime.atomic_write(tool / 'owner.json', runtime.json_bytes(metadata), expected=b'')
        verify_tool(tool, host, files)
    return tool


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise AgentError(message)


def main(argv=None):
    parser = JsonParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'install', 'status', 'uninstall'])
    parser.add_argument('--host', required=True, choices=['codex', 'claude-code'])
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--claude-home', type=Path)
    runtime = None
    result = {'ok': False}
    try:
        args = parser.parse_args(argv)
        result.update(action=args.action, host=args.host)
        bundle = find_bundle(__file__)
        runtime = load_runtime(bundle)
        managed = bundle.name == TOOL_NAME
        default_root = bundle.parent if managed else runtime.default_state_dir().parent / ('korean-protocol-' + args.host)
        root = safe_path(args.state_dir or default_root)
        if managed and root != bundle.parent:
            raise AgentError('Persistent helper can manage only its recorded state directory', 7)
        if (args.host == 'codex' and args.claude_home is not None) or (args.host == 'claude-code' and args.codex_home is not None):
            raise AgentError('Home option does not match --host')
        args.scope, args.project_root = 'user', None
        args.codex_home = safe_path(args.codex_home or os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) if args.host == 'codex' else None
        args.claude_home = runtime.claude_home(args) if args.host == 'claude-code' else None
        target = runtime.safe_path(runtime.host_target(args))
        result.update(state_dir=str(root), target=str(target), selected_target=str(target), profile='coding-agent')
        tool = safe_path(root / TOOL_NAME)
        tool_available = tool.exists()
        if tool_available:
            verify_tool(tool, args.host)
        status = read_status(runtime, root, args.host, verify_cache=args.action != 'uninstall')
        result['target_matches'] = not status['installed'] or status['target'] == str(target)
        if status['installed'] and status['target'] != str(target):
            # Removal must address the recorded file even if discovery changed.
            if args.action == 'install':
                raise AgentError('Current host target differs from installed target; existing instructions preserved', 7)
            result['target'] = status['target']
        if args.action in ('plan', 'install'):
            runtime.content_files(bundle)
        if args.action == 'install':
            tool = persist_tool(runtime, root, args.host, bundle)
            tool_available = True
            context = {'host': args.host, 'scope': 'user', 'project_root': None}
            context['codex_home' if args.host == 'codex' else 'claude_home'] = str(args.codex_home if args.host == 'codex' else args.claude_home)
            controller = runtime.Controller(root)
            result['changed'] = controller.install_snapshot(bundle, target, VERSION, 'coding-agent',
                                                            runtime.host_budget(args, target), host_context=context)
            controller.configure(mode='off')
        elif args.action == 'uninstall':
            if not status['installed'] and not status['recovery_required']:
                raise AgentError('No installed protocol', 4)
            runtime.Controller(root).uninstall()
            result['changed'] = True
        result.update(read_status(runtime, root, args.host))
        if result['installed'] and not result['target_matches']:
            result['verified'] = False
        if args.action == 'plan':
            result['proposed_writes'] = [str(root), str(root / TOOL_NAME), str(target)]
        result.update(ok=True, tool_available=tool_available, snapshot_version=VERSION)
        return_code = 0
    except (AgentError, OSError) as exc:
        result.update(error=str(exc), code=getattr(exc, 'code', 8))
        return_code = result['code']
    except Exception as exc:
        if runtime is None or not isinstance(exc, runtime.ProtocolError):
            raise
        result.update(error=str(exc), code=exc.code)
        return_code = exc.code
    # Return durable management routes even when application failed after tool
    # persistence. The helper intentionally retains its code after uninstall.
    if 'state_dir' in result:
        tool = Path(result['state_dir']) / TOOL_NAME
        common = ['--host', result['host'], '--state-dir', result['state_dir']]
        home = args.codex_home if args.host == 'codex' else args.claude_home
        common += ['--codex-home' if args.host == 'codex' else '--claude-home', str(home)]
        routes = {action: [sys.executable, '-B', str(tool / 'agent-install.py'), action] + common
                  for action in ('status', 'uninstall')}
        result['management_argv'] = routes
        result['management_commands'] = {action: shlex.join(command) for action, command in routes.items()}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return return_code


if __name__ == '__main__':
    sys.exit(main())
