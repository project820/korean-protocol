"""Test exact local 0.3 content to current candidate with ephemeral TEST signatures.

The default baseline is a pinned local Git commit, not a claim of published
provenance. --baseline-root can point at captured, independently authenticated
release content. All installs and signing material stay in temporary directories.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from manual_candidate_upgrade_smoke import (
    load_module, outside_managed, require, sha256, source_version, test_static,
)


BASELINE_COMMIT = '52008bdd1eabf0d5e3d359898bedcaebaf057e0a'


def run_migration(runtime_root, baseline_root=None, version='0.7.0'):
    runtime_root = Path(runtime_root).resolve()
    module = load_module(runtime_root / 'runtime/kproto.py', 'offline_migration_runtime')
    code_hashes = {name: sha256((runtime_root / name).read_bytes()) for name in
                   ('runtime/kproto.py', 'distribution/agent_install.py',
                    'tests/manual_offline_candidate_migration.py', 'tests/manual_candidate_upgrade_smoke.py')}
    candidate = module.content_files(runtime_root)
    source_version(module, candidate, version)
    baseline = ({name: (Path(baseline_root) / name).read_bytes() for name in module.CONTENT_PATHS}
                if baseline_root else {name: subprocess.run(
                    ['git', 'show', BASELINE_COMMIT + ':' + name], cwd=runtime_root,
                    check=True, capture_output=True, timeout=15).stdout for name in module.CONTENT_PATHS})
    source_version(module, baseline, '0.3.0')
    require(candidate != baseline, 'Candidate must differ from the 0.3.0 baseline')
    report = {'schema_version': 1, 'tested_at': datetime.now(timezone.utc).isoformat(),
              'test': 'offline TEST-signed 0.3.0 to actual candidate content migration',
              'result': 'failed', 'hosts': {},
              'baseline_origin': str(Path(baseline_root).resolve()) if baseline_root else 'local Git ' + BASELINE_COMMIT,
              'baseline_files_sha256': {name: sha256(raw) for name, raw in baseline.items()},
              'candidate_files_sha256': {name: sha256(raw) for name, raw in candidate.items()},
              'current_code_sha256': code_hashes,
              'candidate_version': version,
              'limitations': ['Both releases use an ephemeral TEST signer; no production publication is proved',
                              'Current helper/runtime handles legacy signed content; old executables are not invoked',
                              'No network, model invocation, global install, or scheduler registration occurs']}
    with tempfile.TemporaryDirectory(prefix='kproto-offline-migration-') as temporary:
        root = Path(temporary).resolve()
        key = root / 'TEST-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       capture_output=True, check=True, timeout=10)
        public = Path(str(key) + '.pub')
        fingerprint = module.key_fingerprint(public)
        require(fingerprint != module.key_fingerprint(runtime_root / 'distribution/trust/publisher.pub'),
                'TEST signer must differ from publisher')
        initial, latest = root / 'initial', root / 'latest'
        test_static(module, baseline, '0.3.0', 2, key, fingerprint, initial)
        test_static(module, candidate, version, 3, key, fingerprint, latest)
        for host in ('codex', 'claude-code'):
            host_root = root / host
            home, state = host_root / 'home', host_root / 'state'
            target = home / ('AGENTS.md' if host == 'codex' else 'rules/korean-protocol.md')
            target.parent.mkdir(parents=True)
            original, suffix = '사용자 지침을 보존한다.\r\n'.encode(), b'\r\n# User appendix\r\n'
            target.write_bytes(original)
            common = ['--host', host, '--state-dir', str(state),
                      '--codex-home' if host == 'codex' else '--claude-home', str(home)]
            env = dict(os.environ, HOME=str(home), CODEX_HOME=str(home), CLAUDE_CONFIG_DIR=str(home),
                       PYTHONDONTWRITEBYTECODE='1')
            steps = []

            def command(argv):
                result = subprocess.run(argv, cwd=runtime_root, env=env, capture_output=True, timeout=30)
                steps.append({'action': argv[3] if len(argv) > 3 else '', 'exit_code': result.returncode})
                require(result.returncode == 0, 'Migration command failed: ' + result.stdout.decode(errors='replace'))
                return json.loads(result.stdout) if result.stdout else None

            helper = [sys.executable, '-B', str(runtime_root / 'distribution/agent_install.py')]
            trust = ['--trust-key', str(public), '--expected-fingerprint', fingerprint]
            installed = command(helper + ['install'] + common + ['--signed-directory', str(initial)] + trust)
            require(installed['verified'] and installed['version'] == '0.3.0', 'Legacy signed install failed')
            target.write_bytes(target.read_bytes() + suffix)
            manager = installed['management_argv']
            command(manager['configure'] + ['--protocol', 'off', '--honorifics', 'on'])
            disabled = target.read_bytes()
            upgraded = command(helper + ['install'] + common + ['--signed-directory', str(latest)] + trust)
            require(upgraded['version'] == version and upgraded['highest_sequence'] == 3 and
                    upgraded['content_verified'] and not upgraded['enabled'] and upgraded['honorifics'],
                    'Candidate migration lost signed state or application settings')
            require(target.read_bytes() == disabled, 'OFF bytes changed during migration')
            cache = state / 'releases' / upgraded['cache_id']
            require(all((cache / name).read_bytes() == raw for name, raw in candidate.items()),
                    'Candidate cache differs from exact source bytes')
            command(manager['protocol_on'])
            active = target.read_bytes()
            require(candidate['profiles/coding-agent.md'].rstrip(b'\n') in active and
                    module.speech_overlay(True) in active and outside_managed(module, active) == original + suffix,
                    'ON profile, honorifics, or user bytes differ')
            runtime = upgraded['runtime_argv']['update'][:-1]
            command(runtime + ['rollback', '--version', '0.3.0'])
            require(baseline['profiles/coding-agent.md'].rstrip(b'\n') in target.read_bytes(),
                    'Cached legacy rollback lacks exact baseline profile')
            command(runtime + ['rollback', '--version', version])
            require(target.read_bytes() == active, 'Cached candidate rollback changed profile bytes')
            command(upgraded['management_argv']['uninstall'])
            require(target.read_bytes() == original + suffix, 'Uninstall changed user bytes')
            report['hosts'][host] = {'result': 'pass', 'steps': steps, 'signed_sequence': 3,
                'all_seven_cached_files_match_source': True, 'OFF_and_honorifics_preserved': True,
                'ON_injects_complete_candidate': True, 'cached_legacy_and_candidate_rollback_pass': True,
                'uninstall_preserves_user_bytes': True}
    require(module.content_files(runtime_root) == candidate, 'Candidate source changed during migration')
    require(all(sha256((runtime_root / name).read_bytes()) == digest for name, digest in code_hashes.items()),
            'Current helper/runtime/driver changed during migration')
    report.update(result='pass', temporary_material_removed=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--candidate-version', default='0.7.0')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; preserve earlier evidence')
    report = run_migration(args.runtime_root, args.baseline_root, args.candidate_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'result': report['result'], 'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()
