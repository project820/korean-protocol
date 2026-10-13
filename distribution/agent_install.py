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
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
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


def read_file(path, owned=False, maximum=LIMIT):
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
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise AgentError('Expected a bounded, unlinked regular file: ' + str(path))
        if owned and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022):
            raise AgentError('Managed file must be owned by user and not writable by others: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
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
            metadata['schema'] != 1 or not isinstance(metadata['version'], str) or
            not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', metadata['version']) or
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
    if tool.name != TOOL_NAME and tool.name != tool_name(metadata['files']):
        raise AgentError('Management directory differs from its content identity', 5)
    return metadata


def tool_name(hashes):
    return TOOL_NAME + '-' + digest(json.dumps(hashes, sort_keys=True).encode())


def managed_bundle(bundle):
    return bundle.name == TOOL_NAME or re.fullmatch(TOOL_NAME + r'-[0-9a-f]{64}', bundle.name) is not None


def tool_files(bundle):
    return {'agent-install.py': read_file(__file__),
            'runtime/kproto.py': read_file(bundle / 'runtime/kproto.py')}


def selected_tool(root, bundle, host):
    files = tool_files(bundle)
    proposed = root / tool_name({name: digest(raw) for name, raw in files.items()})
    legacy = safe_path(root / TOOL_NAME)
    if legacy.exists():
        verify_tool(legacy, host)
    # Existing managers remain executable; inspect their ownership before adding
    # code beside them, and never overwrite a manager with different bytes.
    for existing in sorted(root.glob(TOOL_NAME + '-*')):
        if re.fullmatch(TOOL_NAME + r'-[0-9a-f]{64}', existing.name):
            verify_tool(safe_path(existing), host)
    if managed_bundle(bundle):
        verify_tool(bundle, host)
        return bundle
    return safe_path(proposed)


def load_runtime(bundle):
    if managed_bundle(bundle):
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
            release = json_object(cache / 'release.json', owned=True)
            files = runtime.content_files(cache)
            hashes = {name: digest(data) for name, data in files.items()}
            if state.get('trust') == 'local-snapshot':
                manifest_hashes = release.get('files')
                if release.get('snapshot_version') != state.get('version'):
                    raise AgentError('Cached snapshot version differs from recorded installation', 5)
            elif state.get('trust') == 'signed':
                reader.root = root
                manifest, _, _ = reader._load_signed(cache, fresh=False)
                manifest_hashes = {entry['path']: entry['sha256'] for entry in manifest['files']}
            else:
                raise AgentError('Unknown recorded release trust', 5)
            if (metadata.get('version') != state.get('version') or metadata.get('trust') != state.get('trust') or
                    metadata.get('hash') != release_hash or cache_id != str(state.get('version')) + '-' + release_hash or
                    metadata.get('files') != hashes or manifest_hashes != hashes):
                raise AgentError('Cached protocol integrity check failed', 5)
            verified = True
    return dict(state, installed=bool(state.get('target')), verified=verified,
                autoupdate=config.get('mode', 'off'), source=config.get('source'),
                scheduler=config.get('scheduler', {'status': 'disabled', 'registered': False}),
                recovery_required=journal_path.exists())


def persist_tool(runtime, root, host, bundle):
    files = tool_files(bundle)
    tool = selected_tool(root, bundle, host)
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


def capture_signed(runtime, directory, key, fingerprint, root):
    directory = safe_path(directory)
    key_data = read_file(key, maximum=16384)
    try:
        fields = key_data.decode('ascii').strip().split()
    except UnicodeError:
        raise AgentError('Trust key must use ASCII public key encoding') from None
    actual = runtime.key_fingerprint(key)
    if actual != fingerprint:
        raise runtime.TrustError('Public key fingerprint differs from expected trust anchor')
    trust = safe_path(root / 'trust/public_key')
    if trust.exists():
        read_file(trust, owned=True)
        if runtime.key_fingerprint(trust) != fingerprint:
            raise runtime.TrustError('Existing trust anchor cannot be replaced by this installer')
    raw = read_file(directory / 'stable/release.json', maximum=65536)
    manifest = runtime.validate_manifest(runtime.strict_json(raw))
    if manifest['signing']['key_id'] != fingerprint:
        raise runtime.TrustError('Manifest signer does not match selected trust anchor')
    signature = read_file(directory / 'stable/release.json.sig', maximum=16384)
    files = runtime.content_files(directory / 'releases' / manifest['version'])
    for entry in manifest['files']:
        data = files[entry['path']]
        if len(data) != entry['size'] or digest(data) != entry['sha256']:
            raise runtime.TrustError('Content hash or size differs from authenticated manifest')
        if entry['path'].endswith('.json') and not re.fullmatch(
                re.escape(manifest['version']) + r'(?:-[a-z0-9.-]+)?', runtime.strict_json(data)['version']):
            raise runtime.TrustError('Content source version differs from signed release version')
    verifier = shutil.which('ssh-keygen')
    if not verifier:
        raise runtime.TrustError('OpenSSH signature verifier is unavailable')
    allowed = ('kproto-release namespaces="kproto-release-v1" ' + fields[0] + ' ' + fields[1] + '\n').encode()
    descriptors = []
    try:
        for data in (allowed, signature):
            reader, writer = os.pipe()
            descriptors.append(reader)
            try:
                # Inputs are bounded below one PIPE_BUF so this cannot block.
                if len(data) > 4096:
                    raise runtime.TrustError('Signature or signer exceeds read-only verification limit')
                os.write(writer, data)
            finally:
                os.close(writer)
        checked = subprocess.run([str(Path(verifier).resolve()), '-Y', 'verify', '-f', '/dev/fd/' + str(descriptors[0]),
                                  '-I', 'kproto-release', '-n', 'kproto-release-v1', '-s', '/dev/fd/' + str(descriptors[1])],
                                 input=raw, capture_output=True, timeout=10, pass_fds=descriptors,
                                 env={name: value for name, value in os.environ.items() if name in ('LANG', 'LC_ALL', 'SYSTEMROOT')})
        if checked.returncode:
            raise runtime.TrustError('Content publisher signature is invalid')
    except subprocess.SubprocessError:
        raise runtime.TrustError('OpenSSH signature verification failed') from None
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
    return manifest, raw, files, signature, key_data


@contextmanager
def mutation_guard(runtime, root, host, signed, target=None):
    runtime.Controller(root)
    path = safe_path(root / 'agent-action.lock')
    parent = runtime.open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise AgentError('Installer action lock has unsafe ownership or type')
        try:
            runtime.fcntl.flock(fd, runtime.fcntl.LOCK_EX | runtime.fcntl.LOCK_NB)
        except BlockingIOError:
            raise AgentError('Another installer action owns this state', 7) from None
        current = read_status(runtime, root, host, verify_cache=target is not None)
        if target is not None and current.get('target') and current['target'] != str(target):
            raise AgentError('Installed host target changed before installation', 7)
        if target is not None and not signed and (current.get('trust') == 'signed' or (root / 'trust/public_key').exists()):
            raise AgentError('Existing signed trust requires explicit signed installation; local downgrade is refused', 5)
        yield
    finally:
        os.close(fd)


def preserve_trust(runtime, controller, public, fingerprint):
    fields = read_file(public, maximum=16384).decode('ascii').strip().split()
    public_bytes = (fields[0] + ' ' + fields[1] + '\n').encode()
    allowed_bytes = ('kproto-release namespaces="kproto-release-v1" ' + fields[0] + ' ' + fields[1] + '\n').encode()
    # Trust rotation is outside this helper's scope. Check and create under the
    # same runtime lock so concurrent installers cannot replace another anchor.
    with controller.lock():
        folder = safe_path(controller.root / 'trust')
        key = safe_path(folder / 'public_key')
        allowed = safe_path(folder / 'allowed_signers')
        if key.exists():
            check_directory(folder)
            read_file(key, owned=True, maximum=16384)
            if runtime.key_fingerprint(key) != fingerprint:
                raise runtime.TrustError('Existing trust anchor cannot be replaced by this installer')
            if read_file(allowed, owned=True, maximum=16384) != allowed_bytes:
                raise runtime.TrustError('Existing allowed signer differs from selected trust anchor')
            return
        if folder.exists():
            check_directory(folder)
        else:
            folder.mkdir(mode=0o700)
        if allowed.exists():
            raise runtime.TrustError('Incomplete existing trust metadata is preserved')
        runtime.atomic_write(key, public_bytes, expected=b'')
        runtime.atomic_write(allowed, allowed_bytes, expected=b'')


@contextmanager
def signed_stage(runtime, captured, fingerprint):
    manifest, raw, files, signature, key_data = captured
    # Use isolated scratch state for the runtime's complete loader. This never
    # creates target/trust/installation state until authentication succeeds.
    with tempfile.TemporaryDirectory(prefix='kproto-agent-verify-') as temporary:
        temporary = Path(temporary).resolve()
        bundle = temporary / 'bundle'
        for name, data in dict(files, **{'release.json': raw, 'release.json.sig': signature}).items():
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        key = temporary / 'public_key'
        key.write_bytes(key_data)
        verifier = runtime.Controller(temporary / 'state')
        verifier.trust_key(key, fingerprint)
        verifier._load_signed(bundle)
        yield bundle, key


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
    parser.add_argument('--signed-directory', type=Path, help='Sealed static stable/releases directory')
    parser.add_argument('--trust-key', type=Path)
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--source')
    parser.add_argument('--autoupdate', choices=['off', 'interval', 'scheduled'], default='off')
    runtime = None
    tool = None
    result = {'ok': False, 'verified': False}
    try:
        args = parser.parse_args(argv)
        result.update(action=args.action, host=args.host)
        bundle = find_bundle(__file__)
        runtime = load_runtime(bundle)
        managed = managed_bundle(bundle)
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
        tool = selected_tool(root, bundle, args.host)
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
        captured = None
        if args.action not in ('plan', 'install') and (args.signed_directory or args.trust_key or args.expected_fingerprint or args.source or args.autoupdate != 'off'):
            raise AgentError('Signed installation options apply only to plan/install')
        if args.action in ('plan', 'install'):
            if args.signed_directory:
                if not args.trust_key or not args.expected_fingerprint:
                    raise AgentError('Signed directory requires --trust-key and --expected-fingerprint')
                args.trust_key = safe_path(args.trust_key)
                if args.source is not None:
                    args.source = runtime.validate_source(args.source)
                if args.autoupdate != 'off' and not args.source:
                    raise AgentError('Automatic updates require --source')
                if args.autoupdate == 'scheduled' and sys.platform != 'darwin':
                    raise AgentError('Scheduler generation currently supports macOS only', 6)
                captured = capture_signed(runtime, args.signed_directory, args.trust_key, args.expected_fingerprint, root)
                result.update(content_verified=True, planned_version=captured[0]['version'])
            else:
                if status.get('trust') == 'signed' or (root / 'trust/public_key').exists():
                    raise AgentError('Existing signed trust requires explicit signed installation; local downgrade is refused', 5)
                if args.trust_key or args.expected_fingerprint or args.source or args.autoupdate != 'off':
                    raise AgentError('Local snapshots cannot configure signed trust or remote updates')
                runtime.content_files(bundle)
                result.update(content_verified=False, planned_version=VERSION)
            result['install_validated'] = False
        if args.action == 'install':
            context = {'host': args.host, 'scope': 'user', 'project_root': None}
            context['codex_home' if args.host == 'codex' else 'claude_home'] = str(args.codex_home if args.host == 'codex' else args.claude_home)
            if captured is not None:
                with signed_stage(runtime, captured, args.expected_fingerprint) as (stage, public), mutation_guard(runtime, root, args.host, True, target):
                    tool = persist_tool(runtime, root, args.host, bundle)
                    tool_available = True
                    durable = load_runtime(tool)
                    runtime = durable
                    controller = durable.Controller(root)
                    preserve_trust(durable, controller, public, args.expected_fingerprint)
                    result['changed'] = controller.install_signed(stage, target, 'coding-agent',
                                                                 durable.host_budget(args, target), host_context=context)
                    controller.configure(mode=args.autoupdate, source=args.source)
            else:
                with mutation_guard(runtime, root, args.host, False, target):
                    tool = persist_tool(runtime, root, args.host, bundle)
                    tool_available = True
                    durable = load_runtime(tool)
                    runtime = durable
                    controller = durable.Controller(root)
                    result['changed'] = controller.install_snapshot(bundle, target, VERSION, 'coding-agent',
                                                                    durable.host_budget(args, target), host_context=context)
                    controller.configure(mode='off')
            result['install_validated'] = True
        elif args.action == 'uninstall':
            if not status['installed'] and not status['recovery_required']:
                raise AgentError('No installed protocol', 4)
            with mutation_guard(runtime, root, args.host, False):
                runtime.Controller(root).uninstall()
            result['changed'] = True
        result.update(read_status(runtime, root, args.host))
        if result['installed'] and not result['target_matches']:
            result['verified'] = False
        if args.action == 'plan':
            result['proposed_writes'] = [str(root), str(tool), str(target)]
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
        tool = tool or Path(result['state_dir']) / TOOL_NAME
        common = ['--host', result['host'], '--state-dir', result['state_dir']]
        home = args.codex_home if args.host == 'codex' else args.claude_home
        common += ['--codex-home' if args.host == 'codex' else '--claude-home', str(home)]
        routes = {action: [sys.executable, '-B', str(tool / 'agent-install.py'), action] + common
                  for action in ('status', 'uninstall')}
        result['management_argv'] = routes
        result['management_commands'] = {action: shlex.join(command) for action, command in routes.items()}
        base = [sys.executable, '-B', str(tool / 'runtime/kproto.py'), '--state-dir', result['state_dir']]
        result['runtime_argv'] = {'update': base + ['update'], 'run': base + ['run'],
                                  'configure_off': base + ['autoupdate', 'configure', '--mode', 'off']}
        result['runtime_commands'] = {action: shlex.join(command) for action, command in result['runtime_argv'].items()}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return return_code


if __name__ == '__main__':
    sys.exit(main())
