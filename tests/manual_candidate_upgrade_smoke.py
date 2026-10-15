"""Authenticate public 0.2.0, then test actual candidate bytes with a TEST signer.

Use an existing OpenSSL Python that honors subprocess-local SSL_CERT_FILE:
  python3 tests/manual_candidate_upgrade_smoke.py --runtime-root . \
      --output evaluation/release-0.7.0-20261015/candidate-upgrade.json

This is current-runtime/current-helper signed CONTENT upgrade evidence. The
0.7.0 candidate is never published, and the production private key is never
read. Both fixture releases are explicitly re-signed with a temporary TEST key.
The public baseline is authenticated separately with the pinned production key.
All installations, TLS keys, test signing keys, and proxy settings are temporary.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import functools
import hashlib
import http.client
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading


PUBLIC_SOURCE = 'https://project820.github.io/korean-protocol'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_version(module, files, version):
    """Require source JSON versions to agree with the numeric candidate release."""
    versions = {module.strict_json(data)['version'] for name, data in files.items()
                if name.endswith('.json')}
    if len(versions) != 1 or not re.fullmatch(re.escape(version) + r'(?:-[a-z0-9.-]+)?', next(iter(versions), '')):
        raise module.InputError('Content source versions do not match candidate release')
    return versions.pop()


def write_files(root, files):
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def outside_managed(module, data):
    require(data.count(module.BEGIN) == data.count(module.END) == 1,
            'Expected one managed block')
    start, end = data.index(module.BEGIN), data.index(module.END) + len(module.END)
    return data[:start] + data[end:]


def crash_snapshot(directories):
    """Read only filenames/stat data, without exposing crash report contents."""
    files = {}
    unavailable = []
    for folder in directories:
        try:
            for path in folder.iterdir():
                if 'python' in path.name.lower() and path.is_file():
                    info = path.stat()
                    files[str(path)] = (info.st_mtime_ns, info.st_size)
        except OSError:
            unavailable.append(str(folder))
    return files, unavailable


def authenticated_public(module, smoke, runtime_root, root):
    source = module.validate_source(PUBLIC_SOURCE)
    raw = module.download_worker(source + '/stable/release.json', {}, 65536)
    require(raw[:1] == b'\x01', 'Public baseline manifest download failed')
    manifest = module.validate_manifest(module.strict_json(raw[1:]))
    require(manifest['version'] == '0.2.0', 'Public stable is no longer the requested 0.2.0 baseline')
    payload = {'stable/release.json': raw[1:]}
    for name, limit in [('stable/release.json.sig', 16384)] + [
            ('releases/0.2.0/' + item['path'], item['size']) for item in manifest['files']]:
        fetched = module.download_worker(source + '/' + name, {}, limit)
        require(fetched[:1] == b'\x01', 'Public baseline download failed: ' + name)
        payload[name] = fetched[1:]
    write_files(root, payload)
    public, fingerprint = smoke.publisher_trust(module, runtime_root, None, None)
    checked_manifest, checked_payload = smoke.load_signed_static(module, root, public, fingerprint)
    require(checked_payload == payload, 'Public capture bytes changed during authentication')
    files = {name: payload['releases/0.2.0/' + name] for name in module.CONTENT_PATHS}
    return checked_manifest, files, public, fingerprint, payload


def test_static(module, files, version, sequence, key, fingerprint, root, engine_min=None):
    """Create a TEST signature without changing any source/content bytes."""
    source_version(module, files, version)
    bundle = root / 'releases' / version
    write_files(bundle, files)
    manifest = module.make_manifest(bundle, version, sequence, fingerprint)
    if engine_min is not None:
        manifest['compatibility']['engine_min'] = engine_min
    raw = module.json_bytes(manifest)
    signed = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'kproto-release-v1'],
                            input=raw, capture_output=True, check=True, timeout=10)
    write_files(root, {'stable/release.json': raw, 'stable/release.json.sig': signed.stdout})
    return manifest


@contextmanager
def local_tls(root, content):
    """Verify normal TLS through a localhost-only CONNECT fixture on random ports."""
    cert, key = root / 'test-ca.crt', root / 'test-ca.key'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                    '-days', '1', '-addext', 'subjectAltName=DNS:localhost'],
                   capture_output=True, check=True, timeout=30)
    requests, tunnels = [], []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            super().do_GET()

    class Server(http.server.ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False

    server = Server(('127.0.0.1', 0), functools.partial(Handler, directory=str(content)))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    class Tunnel(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_CONNECT(self):
            if self.path != 'localhost:443':
                self.send_error(403)
                return
            tunnels.append(self.path)
            try:
                with socket.create_connection(('127.0.0.1', server.server_address[1]), timeout=5) as upstream:
                    self.send_response(200, 'Connection established')
                    self.end_headers()
                    peers = (self.connection, upstream)
                    for peer in peers:
                        peer.settimeout(5)
                    while True:
                        readable, _, _ = select.select(peers, [], [], 5)
                        if not readable:
                            return
                        for incoming in readable:
                            data = incoming.recv(65536)
                            if not data:
                                return
                            (upstream if incoming is self.connection else self.connection).sendall(data)
            except OSError:
                return

    proxy = Server(('127.0.0.1', 0), Tunnel)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    stopped = False

    def stop_content():
        nonlocal stopped
        if not stopped:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            stopped = True

    try:
        thread.start()
        proxy_thread.start()
        connection = http.client.HTTPConnection('127.0.0.1', proxy.server_address[1], timeout=5)
        try:
            connection.request('CONNECT', 'elsewhere.invalid:443')
            response = connection.getresponse()
            require(response.status == 403, 'Proxy accepted a foreign authority')
            response.read()
        finally:
            connection.close()
        yield {'SSL_CERT_FILE': str(cert), 'HTTPS_PROXY': 'http://127.0.0.1:' + str(proxy.server_address[1]),
               'https_proxy': 'http://127.0.0.1:' + str(proxy.server_address[1]),
               'NO_PROXY': 'unused.invalid', 'no_proxy': 'unused.invalid'}, requests, tunnels, stop_content
    finally:
        stop_content()
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join(timeout=2)


def run_smoke(runtime_root, version='0.7.0'):
    runtime_root = runtime_root.resolve()
    code_names = ('runtime/kproto.py', 'distribution/agent_install.py', 'tests/manual_https_smoke.py',
                  'tests/manual_candidate_upgrade_smoke.py')
    code_hashes = {name: sha256((runtime_root / name).read_bytes()) for name in code_names}
    report = {'schema_version': 1, 'tested_at': datetime.now(timezone.utc).isoformat(),
              'test': 'actual candidate content upgrade under current runtime and helper',
              'runtime_root': str(runtime_root), 'code_sha256': code_hashes,
              'python_executable': sys.executable, 'python_version': sys.version.split()[0],
              'ssl_version': ssl.OPENSSL_VERSION, 'result': 'failed', 'hosts': {},
              'scope': {'public_production_upgrade': False, 'original_0_2_executable_migration': False,
                        'candidate_signature': 'temporary TEST key only', 'production_private_key_read': False,
                        'global_installation': False, 'global_trust_store_changed': False,
                        'scheduler_registered': False, 'model_compliance_tested': False}}
    diagnostic_dirs = [Path.home() / 'Library/Logs/DiagnosticReports', Path('/Library/Logs/DiagnosticReports')]
    before_crashes, unavailable_before = crash_snapshot(diagnostic_dirs)
    module = load_module(runtime_root / 'runtime/kproto.py', 'candidate_runtime')
    smoke = load_module(runtime_root / 'tests/manual_https_smoke.py', 'candidate_base_smoke')
    try:
        for tool in ('ssh-keygen', 'openssl'):
            require(shutil.which(tool), 'Required existing tool unavailable: ' + tool)
        candidate = module.content_files(runtime_root)
        candidate_source_version = source_version(module, candidate, version)
        with tempfile.TemporaryDirectory(prefix='kproto-actual-candidate-') as temporary:
            root = Path(temporary).resolve()
            public_root = root / 'authenticated-public'
            baseline_manifest, baseline, publisher, publisher_fp, public_payload = authenticated_public(
                module, smoke, runtime_root, public_root)
            report['public_baseline'] = {'source': PUBLIC_SOURCE, 'version': '0.2.0',
                'sequence': baseline_manifest['sequence'], 'fingerprint': publisher_fp,
                'manifest_sha256': sha256(public_payload['stable/release.json']),
                'signature_sha256': sha256(public_payload['stable/release.json.sig']),
                'authentication': 'Pinned publisher SSHSIG verified; all seven payload hashes verified',
                'files': {name: sha256(raw) for name, raw in baseline.items()}}
            report['candidate'] = {'version': version, 'source_version': candidate_source_version,
                                  'files': {name: sha256(raw) for name, raw in candidate.items()},
                                  'content_bytes_exactly_source': True}
            require(candidate != baseline, 'Candidate has no changed content from public baseline')
            signing_key = root / 'TEST-signing-key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(signing_key)],
                           capture_output=True, check=True, timeout=10)
            public_test = Path(str(signing_key) + '.pub')
            fingerprint = module.key_fingerprint(public_test)
            require(fingerprint != publisher_fp, 'TEST signer must differ from publisher')
            report['test_signer_fingerprint'] = fingerprint
            initial_static, served = root / 'test-initial', root / 'test-server'
            test_static(module, baseline, '0.2.0', 1, signing_key, fingerprint, initial_static)
            target_manifest = test_static(module, candidate, version, 2, signing_key, fingerprint, served)
            smoke.load_signed_static(module, initial_static, public_test, fingerprint)
            smoke.load_signed_static(module, served, public_test, fingerprint)
            report['test_manifests'] = {name: sha256((path / 'stable/release.json').read_bytes())
                                       for name, path in [('0.2.0', initial_static), (version, served)]}
            with local_tls(root, served) as (tls_env, requests, tunnels, stop_server):
                report['transport'] = {'scheme': 'https', 'source': 'https://localhost:443',
                                       'restricted_connect_proxy': True, 'foreign_authority_rejected': True,
                                       'default_certificate_validation': True, 'ssl_cert_file_subprocess_only': True,
                                       'direct_port_443_bind_tested': False}
                for host in ('codex', 'claude-code'):
                    host_report = {'steps': [], 'result': 'failed'}
                    report['hosts'][host] = host_report
                    host_root = root / host
                    home, host_home, state = [host_root / part for part in ('home', 'host-home', 'state')]
                    home.mkdir(parents=True)
                    host_home.mkdir()
                    target = host_home / ('AGENTS.md' if host == 'codex' else 'rules/korean-protocol.md')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    original = '사용자의 기존 승인 정책을 유지한다.\r\n# Local user rules\r\n'.encode()
                    suffix = b'\r\n# User appendix after installation\r\n'
                    target.write_bytes(original)
                    env = dict(os.environ, HOME=str(home), CODEX_HOME=str(host_home),
                               CLAUDE_CONFIG_DIR=str(host_home), PYTHONDONTWRITEBYTECODE='1', **tls_env)
                    env.pop('ALL_PROXY', None)
                    env.pop('all_proxy', None)

                    def command(label, argv, expected=0, env=env, host_report=host_report):
                        result = subprocess.run(argv, cwd=str(runtime_root), env=env,
                                                capture_output=True, timeout=75)
                        host_report['steps'].append({'step': label, 'argv': argv, 'exit_code': result.returncode,
                                                    'expected_exit_code': expected, 'stdout_bytes': len(result.stdout),
                                                    'stderr_bytes': len(result.stderr)})
                        require(result.returncode == expected, label + ' exit ' + str(result.returncode) +
                                ' instead of ' + str(expected) + ': ' + result.stderr.decode(errors='replace'))
                        return json.loads(result.stdout) if result.stdout else None

                    helper = [sys.executable, '-B', str(runtime_root / 'distribution/agent_install.py')]
                    common = ['--host', host, '--state-dir', str(state),
                              '--codex-home' if host == 'codex' else '--claude-home', str(host_home)]
                    # First install the authentic production-signed baseline in a separate temporary state.
                    production_state, production_home = host_root / 'production-state', host_root / 'production-home'
                    production_target = production_home / ('AGENTS.md' if host == 'codex' else 'rules/korean-protocol.md')
                    production_target.parent.mkdir(parents=True, exist_ok=True)
                    production_target.write_bytes(original)
                    prod_common = ['--host', host, '--state-dir', str(production_state),
                                   '--codex-home' if host == 'codex' else '--claude-home', str(production_home)]
                    installed_public = command('production-signed-0.2.0-local-install', helper + ['install'] + prod_common +
                        ['--signed-directory', str(public_root), '--trust-key', str(publisher), '--expected-fingerprint', publisher_fp])
                    require(installed_public['verified'] and installed_public['version'] == '0.2.0', 'Production baseline install was not verified')
                    command('production-baseline-uninstall', installed_public['management_argv']['uninstall'])
                    require(production_target.read_bytes() == original, 'Production baseline altered original user bytes')

                    installed = command('TEST-signed-0.2.0-install', helper + ['install'] + common +
                        ['--signed-directory', str(initial_static), '--trust-key', str(public_test),
                         '--expected-fingerprint', fingerprint, '--source', 'https://localhost:443', '--autoupdate', 'interval'])
                    require(installed['verified'] and installed['version'] == '0.2.0', 'TEST baseline was not verified')
                    manager = installed['management_argv']
                    runtime = installed['runtime_argv']['update'][:-1]
                    durable = Path(manager['status'][2]).parent
                    require((durable / 'runtime/kproto.py').read_bytes() == (runtime_root / 'runtime/kproto.py').read_bytes(), 'Persistent runtime differs from candidate')
                    require((durable / 'agent-install.py').read_bytes() == (runtime_root / 'distribution/agent_install.py').read_bytes(), 'Persistent helper differs from candidate')
                    host_report['persistent_code_sha256'] = {'runtime/kproto.py': sha256((durable / 'runtime/kproto.py').read_bytes()),
                                                          'agent-install.py': sha256((durable / 'agent-install.py').read_bytes())}
                    target.write_bytes(target.read_bytes() + suffix)
                    settings = command('OFF-and-honorifics-ON', manager['configure'] + ['--protocol', 'off', '--honorifics', 'on'])
                    require(not settings['enabled'] and settings['honorifics'], 'Application settings did not apply')
                    disabled = target.read_bytes()
                    require(outside_managed(module, disabled) == original + suffix, 'OFF changed user bytes')
                    require(baseline['profiles/coding-agent.md'].rstrip(b'\n') not in disabled, 'OFF still injects old profile')
                    before_gets = len(requests)
                    command('actual-candidate-HTTPS-update-while-OFF', installed['runtime_argv']['update'])
                    expected_requests = smoke.release_requests(target_manifest)
                    require(requests[before_gets:] == expected_requests, 'Candidate update did not fetch exact signed payload')
                    updated = command('candidate-status-while-OFF', manager['status'])
                    require(updated['version'] == version and updated['highest_sequence'] == 2 and updated['trust'] == 'signed', 'Actual candidate was not activated')
                    require(not updated['enabled'] and updated['honorifics'] and updated['content_verified'], 'OFF/honorifics/integrity did not survive update')
                    require(target.read_bytes() == disabled, 'OFF profile bytes changed during upgrade')
                    cache = state / 'releases' / updated['cache_id']
                    require(all((cache / name).read_bytes() == raw for name, raw in candidate.items()), 'Candidate cache differs from actual source')
                    host_report['upgrade'] = {'initial_version': '0.2.0', 'target_version': version, 'highest_sequence': 2,
                        'requests': requests[before_gets:], 'OFF_survived': True, 'honorifics_survived': True,
                        'all_seven_cached_files_match_source': True}
                    enabled = command('ON-inject-latest-verified-profile', manager['protocol_on'])
                    active = target.read_bytes()
                    require(enabled['verified'] and enabled['honorifics'] and outside_managed(module, active) == original + suffix, 'ON altered user bytes or verification')
                    require(candidate['profiles/coding-agent.md'].rstrip(b'\n') in active, 'ON did not inject complete latest candidate profile')
                    require(('전체 규칙·사전: ' + str(cache)).encode() in active and module.speech_overlay(True) in active, 'ON lacks correct cache locator or honorific overlay')
                    command('honorifics-OFF', manager['honorifics_off'])
                    require(module.speech_overlay(False) in target.read_bytes(), 'Honorific OFF overlay missing')
                    command('honorifics-ON', manager['honorifics_on'])
                    require(target.read_bytes() == active, 'Honorific toggle changed latest profile bytes')
                    host_report['ON'] = {'complete_current_profile_injected': True, 'honorific_both_options_verified': True,
                                         'user_prefix_suffix_preserved': True, 'installed_profile_sha256': sha256(active)}
                    # Signature failure must preserve authenticated active state and cache.
                    signature = served / 'stable/release.json.sig'
                    valid_signature = signature.read_bytes()
                    cache_before = smoke.static_files(module, cache)
                    state_before = (state / 'state.json').read_bytes()
                    signature.write_bytes(b'invalid TEST signature\n')
                    try:
                        command('reject-invalid-signature', installed['runtime_argv']['update'], expected=5)
                        require(target.read_bytes() == active and smoke.static_files(module, cache) == cache_before and
                                (state / 'state.json').read_bytes() == state_before, 'Invalid signature altered target/cache/state')
                    finally:
                        signature.write_bytes(valid_signature)
                    host_report['invalid_signature_preserved_target_cache_state'] = True
                    command('OFF-before-rollback', manager['protocol_off'])
                    command('rollback-public-content-cache-0.2.0', runtime + ['rollback', '--version', '0.2.0'])
                    rolled = command('rollback-status', manager['status'])
                    require(rolled['version'] == '0.2.0' and rolled['pin'] == '0.2.0' and not rolled['enabled'] and
                            rolled['honorifics'] and rolled['highest_sequence'] == 2, 'Rollback lost controls/pin/anti-replay sequence')
                    command('rollback-ON', manager['protocol_on'])
                    require(baseline['profiles/coding-agent.md'].rstrip(b'\n') in target.read_bytes(), 'Rollback ON profile differs from public baseline bytes')
                    command('rollback-candidate-cache', runtime + ['rollback', '--version', version])
                    require(target.read_bytes() == active, 'Returning to candidate changed ON bytes')
                    host_report['rollback'] = {'OFF_and_honorifics_survived': True, 'cached_0_2_profile_injected': True,
                                               'candidate_restored_exactly': True, 'highest_sequence_preserved': True}
                    # Defer offline checks until both hosts complete TLS upgrades.
                    host_report['_context'] = (command, installed, manager, cache, cache_before, target, active, original + suffix)
                    host_report['result'] = 'pass'
                stop_server()
                for host, host_report in report['hosts'].items():
                    command, installed, manager, cache, cache_before, target, active, user_bytes = host_report.pop('_context')
                    command('remove-cached-rollback-pin', installed['runtime_argv']['update'] + ['--unpin'])
                    command('offline-update-fails-safely', installed['runtime_argv']['update'], expected=3)
                    status = command('offline-verified-status', manager['status'])
                    require(status['version'] == version and status['verified'] and target.read_bytes() == active and
                            smoke.static_files(module, cache) == cache_before, 'Offline failure changed last verified state')
                    command('offline-wrapper-host-command', installed['runtime_argv']['run'] + ['--', sys.executable, '-c', 'raise SystemExit(0)'])
                    require(all((cache / name).read_bytes() == candidate[name] for name in module.CONTENT_PATHS), 'Offline cache unreadable')
                    command('uninstall-restores-user-bytes', manager['uninstall'])
                    require(target.read_bytes() == user_bytes, 'Uninstall did not preserve exact user prefix/suffix')
                    host_report['offline'] = {'last_verified_profile_cache_preserved': True, 'all_seven_files_readable': True,
                                              'wrapper_host_exit': 0, 'uninstall_restored_user_bytes': True}
                report['HTTPS_requests'] = requests
                report['CONNECT_tunnels'] = tunnels
            require(module.content_files(runtime_root) == candidate, 'Candidate source changed during smoke; repeat on stable source')
            require(all(sha256((runtime_root / name).read_bytes()) == digest for name, digest in code_hashes.items()), 'Runtime/helper/script changed during smoke; repeat')
            report['source_and_code_unchanged_during_smoke'] = True
            report['result'] = 'pass'
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, module.ProtocolError) as error:
        report['failure'] = str(error)
        for host_report in report['hosts'].values():
            host_report.pop('_context', None)
    after_crashes, unavailable_after = crash_snapshot(diagnostic_dirs)
    new_crashes = sorted(name for name, info in after_crashes.items() if before_crashes.get(name) != info)
    report['python_crash_report_check'] = {'directories': [str(path) for path in diagnostic_dirs],
        'existing_python_report_count': len(before_crashes), 'new_or_changed_python_reports': new_crashes,
        'unavailable_directories': sorted(set(unavailable_before + unavailable_after)),
        'contents_read': False, 'limitation': 'Immediate filename/stat comparison; delayed macOS report generation is not excluded'}
    if new_crashes:
        report.update(result='failed', failure='New Python crash report observed during smoke')
    report['temporary_material_removed'] = True
    report['limitations'] = ['No production signature or public production endpoint for candidate ' + version,
        'Current runtime/helper only; original 0.2 executable migration not exercised',
        'No real Codex/Claude model invocation, login, sleep/wake or scheduler registration',
        'Local CONNECT transports verified TLS; no direct port-443 listener or global trust change']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--candidate-version', default='0.7.0')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; preserve older evidence and choose a new path')
    report = run_smoke(args.runtime_root, args.candidate_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': report['result'], 'output': str(args.output.resolve()),
                      'failure': report.get('failure')}, ensure_ascii=False))
    return 0 if report['result'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
