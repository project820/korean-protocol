"""Exercise exact local Git 0.2 executables against the current helper locally.

No public writes or downloads occur. TEST signatures cover exact historical
content and exact current candidate bytes. Generated schedulers are never
registered. The old engine rejects the new engine requirement before payload
download; users replace saved runtime routes with the returned current routes.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

from manual_candidate_upgrade_smoke import (
    crash_snapshot, load_module, local_tls, outside_managed, require, sha256,
    source_version, test_static, write_files,
)


HISTORICAL_COMMIT = '2067f541d2cc97d94f4a8625de2015d2330aeb1b'


def git_bytes(root, revision, name):
    return subprocess.run(['git', 'show', revision + ':' + name], cwd=str(root),
                          capture_output=True, check=True, timeout=15).stdout


def run_migration(runtime_root):
    runtime_root = runtime_root.resolve()
    current = load_module(runtime_root / 'runtime/kproto.py', 'migration_current_runtime')
    names = ('runtime/kproto.py', 'runtime/__init__.py', 'distribution/agent_install.py') + current.CONTENT_PATHS
    current_code = {name: sha256((runtime_root / name).read_bytes()) for name in
                    ('runtime/kproto.py', 'distribution/agent_install.py',
                     'tests/manual_candidate_upgrade_smoke.py', 'tests/manual_historical_helper_migration.py')}
    report = {'schema_version': 1, 'tested_at': datetime.now(timezone.utc).isoformat(),
              'test': 'actual historical 0.2 helper/runtime migration with generated-only scheduler',
              'runtime_root': str(runtime_root), 'python_executable': sys.executable,
              'python_version': sys.version.split()[0], 'result': 'failed', 'hosts': {},
              'current_code_sha256': current_code,
              'scope': {'historical_source': 'exact local Git object specified by parent',
                        'candidate_signature': 'ephemeral TEST signature only',
                        'production_signature_reused': False, 'network_downloads': False,
                        'public_publication': False, 'production_private_key_read': False,
                        'global_install': False, 'global_trust_store_changed': False,
                        'launchctl_registration': False, 'automatic_code_upgrade': False,
                        'external_wrapper_automatically_rewritten': False}}
    diagnostics = [Path.home() / 'Library/Logs/DiagnosticReports', Path('/Library/Logs/DiagnosticReports')]
    crash_before, unavailable_before = crash_snapshot(diagnostics)
    try:
        resolved = subprocess.run(['git', 'rev-parse', HISTORICAL_COMMIT + '^{commit}'],
                                  cwd=str(runtime_root), capture_output=True, check=True, timeout=15).stdout.decode().strip()
        require(resolved == HISTORICAL_COMMIT, 'Historical commit does not resolve exactly')
        tree = subprocess.run(['git', 'rev-parse', HISTORICAL_COMMIT + '^{tree}'],
                              cwd=str(runtime_root), capture_output=True, check=True, timeout=15).stdout.decode().strip()
        historical = {name: git_bytes(runtime_root, HISTORICAL_COMMIT, name) for name in names}
        baseline = {name: historical[name] for name in current.CONTENT_PATHS}
        candidate = current.content_files(runtime_root)
        require(source_version(current, baseline, '0.2.0').startswith('0.2.0'), 'Historical source version differs')
        require(source_version(current, candidate, '0.7.0') == '0.7.0-draft', 'Candidate source version differs')
        prior = json.loads((runtime_root / 'evaluation/release-0.3.0-20261013/candidate-upgrade-smoke.json').read_bytes())
        require(prior['result'] == 'pass' and prior['public_baseline']['version'] == '0.2.0', 'Prior authenticated public baseline evidence missing')
        require({name: sha256(raw) for name, raw in baseline.items()} == prior['public_baseline']['files'],
                'Git historical content differs from independently authenticated public 0.2.0 bytes')
        report['historical'] = {'commit': resolved, 'tree': tree,
                               'files_sha256': {name: sha256(raw) for name, raw in historical.items()},
                               'seven_content_hashes_match_prior_authenticated_public_baseline': True,
                               'baseline_evidence_sha256': sha256((runtime_root / 'evaluation/release-0.3.0-20261013/candidate-upgrade-smoke.json').read_bytes())}
        report['candidate_content_sha256'] = {name: sha256(raw) for name, raw in candidate.items()}
        with tempfile.TemporaryDirectory(prefix='kproto-historical-migration-') as temporary:
            root = Path(temporary).resolve()
            old_source = root / 'exact-0.2-source'
            write_files(old_source, historical)
            require(all((old_source / name).read_bytes() == raw for name, raw in historical.items()),
                    'Extracted historical executable/content bytes differ from Git')
            test_key = root / 'TEST-signing-key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(test_key)],
                           capture_output=True, check=True, timeout=10)
            test_public = Path(str(test_key) + '.pub')
            fingerprint = current.key_fingerprint(test_public)
            require(fingerprint != current.key_fingerprint(runtime_root / 'distribution/trust/publisher.pub'),
                    'TEST key differs from publisher key')
            report['TEST_signer_fingerprint'] = fingerprint
            initial, served = root / 'initial-static', root / 'served-candidate'
            test_static(current, baseline, '0.2.0', 1, test_key, fingerprint, initial, engine_min='0.1.0')
            test_static(current, candidate, '0.7.0', 2, test_key, fingerprint, served)
            with local_tls(root, served) as (tls_env, requests, tunnels, stop_server):
                for host in ('codex', 'claude-code'):
                    evidence = {'steps': [], 'result': 'failed'}
                    report['hosts'][host] = evidence
                    host_root = root / host
                    home, host_home, state = [host_root / name for name in ('home', 'host-home', 'state')]
                    home.mkdir(parents=True)
                    host_home.mkdir()
                    target = host_home / ('AGENTS.md' if host == 'codex' else 'rules/korean-protocol.md')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    original = '사용자의 승인 정책은 그대로 보존한다.\r\n'.encode()
                    suffix = b'\r\n# Manually appended user instructions\r\n'
                    target.write_bytes(original)
                    env = dict(os.environ, HOME=str(home), CODEX_HOME=str(host_home), CLAUDE_CONFIG_DIR=str(host_home),
                               PYTHONDONTWRITEBYTECODE='1', **tls_env)
                    env.pop('ALL_PROXY', None)
                    env.pop('all_proxy', None)

                    def command(label, argv, expected=0):
                        result = subprocess.run(argv, cwd=str(runtime_root), env=env, capture_output=True, timeout=75)
                        evidence['steps'].append({'step': label, 'argv': argv, 'exit_code': result.returncode,
                                                  'expected_exit_code': expected, 'stdout_bytes': len(result.stdout),
                                                  'stderr_bytes': len(result.stderr)})
                        require(result.returncode == expected, label + ': unexpected exit ' + str(result.returncode))
                        return json.loads(result.stdout) if result.stdout else None

                    common = ['--host', host, '--state-dir', str(state),
                              '--codex-home' if host == 'codex' else '--claude-home', str(host_home)]
                    old_install = command('actual-Git-0.2-helper-signed-install-generated-scheduler',
                        [sys.executable, '-B', str(old_source / 'distribution/agent_install.py'), 'install'] + common +
                        ['--signed-directory', str(initial), '--trust-key', str(test_public),
                         '--expected-fingerprint', fingerprint, '--source', 'https://localhost:443', '--autoupdate', 'scheduled'])
                    require(old_install['version'] == '0.2.0' and old_install['verified'], 'Actual old helper install failed verification')
                    old_helper = Path(old_install['management_argv']['status'][2])
                    old_runtime = Path(old_install['runtime_argv']['run'][2])
                    old_tool_bytes = {str(path.relative_to(old_helper.parent)): path.read_bytes()
                                      for path in old_helper.parent.rglob('*') if path.is_file()}
                    require(old_helper.read_bytes() == historical['distribution/agent_install.py'] and
                            old_runtime.read_bytes() == historical['runtime/kproto.py'], 'Old persistent executable differs from Git')
                    old_config = current.strict_json((state / 'config.json').read_bytes())
                    scheduler = Path(old_config['scheduler']['path'])
                    old_plist = scheduler.read_bytes()
                    old_job = plistlib.loads(old_plist)
                    require(old_job['ProgramArguments'][1] == str(old_runtime) and
                            not old_config['scheduler'].get('launch_agent') and not old_config['scheduler']['registered'],
                            'Expected generated-only historical scheduler')
                    target.write_bytes(target.read_bytes() + suffix)
                    migrated = command('current-0.7-helper-configure-OFF-honorifics-ON',
                        [sys.executable, '-B', str(runtime_root / 'distribution/agent_install.py'), 'configure'] + common +
                        ['--protocol', 'off', '--honorifics', 'on'])
                    new_manager, new_routes = migrated['management_argv'], migrated['runtime_argv']
                    new_helper = Path(new_manager['status'][2])
                    new_runtime = Path(new_routes['run'][2])
                    require(new_helper != old_helper and new_runtime != old_runtime, 'Current helper did not return distinct current executable routes')
                    require(new_helper.read_bytes() == (runtime_root / 'distribution/agent_install.py').read_bytes() and
                            new_runtime.read_bytes() == (runtime_root / 'runtime/kproto.py').read_bytes(), 'New executable differs from candidate')
                    require(not migrated['enabled'] and migrated['honorifics'] and migrated['version'] == '0.2.0', 'Initial current controls failed')
                    disabled = target.read_bytes()
                    require(outside_managed(current, disabled) == original + suffix, 'Migration altered user bytes')
                    new_job = plistlib.loads(scheduler.read_bytes())
                    require(new_job['ProgramArguments'][1] == str(new_runtime), 'Generated scheduler did not migrate to current durable runtime')
                    require({key: val for key, val in old_job.items() if key != 'ProgramArguments'} ==
                            {key: val for key, val in new_job.items() if key != 'ProgramArguments'}, 'Scheduler migration changed unrelated job fields')
                    require(old_job['ProgramArguments'][:1] + old_job['ProgramArguments'][2:] ==
                            new_job['ProgramArguments'][:1] + new_job['ProgramArguments'][2:], 'Scheduler migration changed unrelated arguments')
                    new_config = current.strict_json((state / 'config.json').read_bytes())
                    require(new_config['mode'] == 'scheduled' and new_config['source'] == old_config['source'] and
                            not new_config['scheduler'].get('launch_agent') and not new_config['scheduler']['registered'], 'Migration changed source/mode or registered job')
                    evidence['migration'] = {'old_helper_sha256': sha256(old_helper.read_bytes()),
                        'old_runtime_sha256': sha256(old_runtime.read_bytes()), 'new_helper_sha256': sha256(new_helper.read_bytes()),
                        'new_runtime_sha256': sha256(new_runtime.read_bytes()), 'new_management_and_wrapper_routes_returned': True,
                        'old_owned_executables_preserved': True, 'generated_scheduler_runtime_replaced': True,
                        'scheduler_other_fields_and_arguments_preserved': True, 'scheduler_registered': False,
                        'generated_plist_before_sha256': sha256(old_plist), 'generated_plist_after_sha256': sha256(scheduler.read_bytes())}
                    # The exact old engine must fail closed before new payload bytes.
                    before_gets = len(requests)
                    before_old_update = (state / 'state.json').read_bytes()
                    command('old-engine-rejects-new-minimum-before-payload', old_install['runtime_argv']['update'], expected=6)
                    stale_bytes = target.read_bytes()
                    stale_state = current.strict_json((state / 'state.json').read_bytes())
                    require(requests[before_gets:] == ['/stable/release.json', '/stable/release.json.sig'],
                            'Old incompatible engine downloaded candidate payload')
                    require(stale_state['protocol_enabled'] is False and stale_state['honorifics'] is True and
                            stale_state['version'] == '0.2.0' and stale_bytes == disabled and
                            (state / 'state.json').read_bytes() == before_old_update,
                            'Old incompatible engine changed installed baseline or controls')
                    require(outside_managed(current, stale_bytes) == original + suffix, 'Old engine changed user bytes')
                    evidence['old_engine_compatibility_guard'] = {'actual_old_executable_invoked': True,
                        'candidate_manifest_rejected_with_exit_6': True, 'candidate_payload_not_downloaded': True,
                        'baseline_state_target_controls_preserved': True,
                        'required_action': 'Use the returned current management and runtime routes after explicit helper upgrade'}
                    command('current-runtime-signed-candidate-update-preserves-OFF', new_routes['update'])
                    updated = command('current-durable-helper-candidate-status', new_manager['status'])
                    require(updated['version'] == '0.7.0' and updated['highest_sequence'] == 2 and
                            not updated['enabled'] and updated['honorifics'] and updated['content_verified'] and
                            target.read_bytes() == disabled, 'Current candidate update lost controls or integrity')
                    command('current-wrapper-preserves-OFF-and-host-exit', new_routes['run'] + ['--', sys.executable, '-c', 'raise SystemExit(0)'])
                    require(target.read_bytes() == disabled, 'Current wrapper changed OFF profile')
                    enabled = command('current-helper-ON-injects-candidate-honorifics', new_manager['protocol_on'])
                    require(enabled['verified'] and current.speech_overlay(True) in target.read_bytes() and
                            candidate['profiles/coding-agent.md'].rstrip(b'\n') in target.read_bytes(), 'Current ON lacks candidate/honorifics')
                    command('current-helper-uninstall-preserves-user-bytes', new_manager['uninstall'])
                    require(target.read_bytes() == original + suffix, 'Migrated uninstall altered user bytes')
                    require({str(path.relative_to(old_helper.parent)): path.read_bytes() for path in old_helper.parent.rglob('*') if path.is_file()} == old_tool_bytes,
                            'Current migration modified old owned executables/metadata')
                    require(not (home / 'Library/LaunchAgents').exists(), 'Unexpected actual LaunchAgent path')
                    evidence['supported_current_path'] = {'OFF_honorific_survive_candidate_update': True,
                        'new_wrapper_host_exit': 0, 'ON_complete_candidate_and_honorific_overlay': True,
                        'exact_user_prefix_suffix_preserved_after_uninstall': True, 'old_tool_tree_bytes_preserved': True,
                        'actual_LaunchAgent_directory_created': False}
                    evidence['result'] = 'pass'
                report['localhost_HTTPS_requests'] = requests
                report['localhost_CONNECT_tunnels'] = tunnels
            require(current.content_files(runtime_root) == candidate and
                    all(sha256((runtime_root / name).read_bytes()) == digest for name, digest in current_code.items()),
                    'Current source changed during historical migration smoke')
            report['current_source_unchanged_during_smoke'] = True
            report['result'] = 'pass'
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, current.ProtocolError) as error:
        report['failure'] = str(error)
    after_crashes, unavailable_after = crash_snapshot(diagnostics)
    changed = sorted(name for name, info in after_crashes.items() if crash_before.get(name) != info)
    report['python_crash_report_check'] = {'existing_python_report_count': len(crash_before),
        'new_or_changed_reports': changed, 'unavailable_directories': sorted(set(unavailable_before + unavailable_after)),
        'contents_read': False, 'limitation': 'Immediate filename/stat check excludes no delayed report generation'}
    if changed:
        report.update(result='failed', failure='New Python crash report observed')
    report['temporary_material_removed'] = True
    report['limitations'] = ['Local Git source is exact; publication attribution is supplied task context',
        'TEST signatures only; no production-signed 0.7 release or public upgrade',
        'Generated owned scheduler migration tested; actually registered launchd migration not exercised',
        'External user wrappers require explicit replacement using returned current runtime routes',
        'No automatic code replacement through content updates, real model invocation, login, or sleep/wake']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; preserve earlier evidence')
    report = run_migration(args.runtime_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': report['result'], 'failure': report.get('failure'), 'output': str(args.output.resolve())}))
    return 0 if report['result'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
