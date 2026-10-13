import importlib.util
import io
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class AgentInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kproto agent ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / 'temporary clone'
        self.bundle.mkdir()
        (self.bundle / 'runtime').mkdir()
        shutil.copy2(ROOT / 'runtime/kproto.py', self.bundle / 'runtime/kproto.py')
        self.script = self.bundle / 'agent-install.py'
        shutil.copy2(ROOT / 'distribution/agent_install.py', self.script)
        spec = importlib.util.spec_from_file_location('agent_install', self.script)
        self.agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.agent)
        self.runtime = self.agent.load_runtime(self.bundle)
        for name in self.runtime.CONTENT_PATHS:
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith('.json'):
                array = 'rules' if name.startswith('specification/') else 'entries'
                path.write_text(json.dumps({'schema_version': '1.0', 'version': '0.1.0', array: [{'id': 'fixture'}]}))
            else:
                path.write_text('뜻과 조건을 유지한다.\n')
        self.home = self.root / 'isolated HOME'
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), CODEX_HOME=str(self.home / '.codex'),
                        CLAUDE_CONFIG_DIR=str(self.home / '.claude'), XDG_DATA_HOME=str(self.home / '.local/share'), PYTHONDONTWRITEBYTECODE='1')
        self.state = self.root / 'state'
        self.codex = self.home / '.codex'
        self.claude = self.home / '.claude'

    def run_cli(self, action, host='codex', state=True, extras=(), script=None):
        command = [sys.executable, str(script or self.script), action, '--host', host]
        if state:
            command += ['--state-dir', str(self.state)]
        command += list(extras)
        result = subprocess.run(command, env=self.env, cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual('', result.stderr, result.stderr)
        output = json.loads(result.stdout)
        return result.returncode, output

    def tree(self):
        return {str(path.relative_to(self.root)): path.read_bytes() if path.is_file() else None
                for path in self.root.rglob('*')}

    def target(self, host):
        return self.codex / 'AGENTS.md' if host == 'codex' else self.claude / 'rules/korean-protocol.md'

    def test_plan_and_status_have_no_writes_for_both_hosts(self):
        for host in ('codex', 'claude-code'):
            for action in ('plan', 'status'):
                with self.subTest(host=host, action=action):
                    before = self.tree()
                    code, value = self.run_cli(action, host, state=False)
                    self.assertEqual(0, code, value)
                    self.assertFalse(value['installed'])
                    self.assertFalse(value['verified'])
                    self.assertFalse(value['tool_available'])
                    self.assertTrue(value['state_dir'].endswith('korean-protocol-' + host))
                    self.assertEqual(str(self.target(host)), value['target'])
                    self.assertEqual(before, self.tree())

    def test_both_hosts_install_idempotently_and_uninstall_preserving_existing_bytes(self):
        for host in ('codex', 'claude-code'):
            with self.subTest(host=host):
                self.state = self.root / ('state-' + host)
                target = self.target(host)
                target.parent.mkdir(parents=True, exist_ok=True)
                original = '기존 사용자 지침이다.\r\n'.encode()
                target.write_bytes(original)
                code, value = self.run_cli('install', host)
                self.assertEqual(0, code, value)
                self.assertTrue(value['installed'])
                self.assertTrue(value['verified'])
                self.assertTrue(value['changed'])
                self.assertEqual('off', value['autoupdate'])
                self.assertEqual('local-snapshot', value['trust'])
                self.assertEqual('0.2.0', value['version'])
                installed = target.read_bytes()
                self.assertTrue(installed.startswith(original))
                code, value = self.run_cli('install', host)
                self.assertEqual(0, code, value)
                self.assertFalse(value['changed'])
                self.assertEqual(installed, target.read_bytes())
                target.write_bytes(b'# New user instruction\n' + installed)
                code, value = self.run_cli('uninstall', host)
                self.assertEqual(0, code, value)
                self.assertFalse(value['installed'])
                self.assertFalse(value['verified'])
                self.assertEqual(b'# New user instruction\n' + original, target.read_bytes())
                self.assertTrue(Path(value['management_argv']['status'][2]).exists())

    def test_management_survives_original_clone_removal_for_both_hosts(self):
        routes = {}
        for host in ('codex', 'claude-code'):
            self.state = self.root / ('persistent-' + host)
            code, value = self.run_cli('install', host)
            self.assertEqual(0, code, value)
            routes[host] = value['management_argv']
        shutil.rmtree(self.bundle)
        for host, commands in routes.items():
            with self.subTest(host=host):
                before = self.tree()
                result = subprocess.run(commands['status'], env=self.env, cwd=self.root,
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)['verified'])
                self.assertEqual(before, self.tree())
                result = subprocess.run(commands['uninstall'], env=self.env, cwd=self.root,
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse(json.loads(result.stdout)['installed'])
                self.assertEqual(b'', self.target(host).read_bytes())

    def test_wrong_host_cannot_inspect_or_remove_existing_installation(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        for action in ('plan', 'status', 'install', 'uninstall'):
            before = self.tree()
            code, value = self.run_cli(action, 'claude-code')
            self.assertEqual(7, code, value)
            self.assertFalse(value['ok'])
            self.assertEqual(before, self.tree())

    def test_existing_unowned_or_incomplete_tool_is_never_overwritten(self):
        tool = self.state / 'agent-tool'
        tool.mkdir(parents=True, mode=0o700)
        (tool / 'agent-install.py').write_bytes(b'unrelated bytes')
        before = self.tree()
        code, value = self.run_cli('install')
        self.assertNotEqual(0, code, value)
        self.assertEqual(before, self.tree())
        self.assertFalse(self.target('codex').exists())

    def test_symlinks_in_state_runtime_target_and_tool_are_rejected(self):
        other = self.root / 'other'
        other.mkdir()
        for action in ('plan', 'status', 'install', 'uninstall'):
            self.state.symlink_to(other, target_is_directory=True)
            code, value = self.run_cli(action)
            self.assertEqual(2, code, value)
            self.state.unlink()
        target = self.target('codex')
        target.parent.mkdir()
        target.symlink_to(other / 'missing')
        code, value = self.run_cli('install')
        self.assertEqual(2, code, value)
        self.assertFalse(self.state.exists())
        target.unlink()
        self.state.mkdir(mode=0o700)
        (self.state / 'agent-tool').symlink_to(other, target_is_directory=True)
        before = self.tree()
        code, value = self.run_cli('install')
        self.assertEqual(2, code, value)
        self.assertEqual(before, self.tree())

    def test_stale_or_tampered_management_engine_is_not_replaced_or_executed(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        tool = Path(value['management_argv']['status'][2]).parent
        engine = tool / 'runtime/kproto.py'
        engine.write_bytes(engine.read_bytes() + b'\nraise RuntimeError("must not run")\n')
        before = self.tree()
        for action in ('status', 'install', 'uninstall'):
            code, value = self.run_cli(action)
            self.assertEqual(5, code, value)
            self.assertEqual(before, self.tree())
        code, value = self.run_cli('status', script=tool / 'agent-install.py')
        self.assertEqual(5, code, value)
        self.assertEqual(before, self.tree())

    def test_cache_or_managed_block_edit_fails_verification_and_preserves_files(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        cache_file = self.state / 'releases' / value['cache_id'] / 'profiles/coding-agent.md'
        cache_original = cache_file.read_bytes()
        cache_file.write_bytes(b'modified protocol content\n')
        before = self.tree()
        code, value = self.run_cli('status')
        self.assertEqual(5, code, value)
        self.assertEqual(before, self.tree())
        code, value = self.run_cli('uninstall')
        self.assertEqual(0, code, value)
        self.assertFalse(value['installed'])
        cache_file.write_bytes(cache_original)
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        target = self.target('codex')
        target.write_bytes(target.read_bytes().replace('뜻과'.encode(), '사실과'.encode()))
        before = self.tree()
        for action in ('status', 'install', 'uninstall'):
            code, value = self.run_cli(action)
            self.assertEqual(7, code, value)
            self.assertEqual(before, self.tree())

    def test_failed_application_keeps_management_routes_for_retry(self):
        target = self.target('claude-code')
        target.parent.mkdir(parents=True)
        target.write_bytes(b'---\npaths: restricted\n---\nexisting user rule\n')
        original = target.read_bytes()
        code, value = self.run_cli('install', 'claude-code')
        self.assertEqual(7, code, value)
        self.assertEqual(original, target.read_bytes())
        helper = Path(value['management_argv']['status'][2])
        self.assertTrue(helper.exists())
        code, value = self.run_cli('status', 'claude-code', script=helper)
        self.assertEqual(0, code, value)
        self.assertFalse(value['installed'])
        target.write_bytes(b'existing user rule\n')
        code, value = self.run_cli('install', 'claude-code')
        self.assertEqual(0, code, value)
        self.assertTrue(value['verified'])

    def test_nonwritable_by_others_state_and_managed_files_are_required(self):
        self.state.mkdir(mode=0o777)
        self.state.chmod(0o777)
        before = self.tree()
        code, value = self.run_cli('install')
        self.assertEqual(2, code, value)
        self.assertEqual(before, self.tree())
        self.state.chmod(0o700)
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        tool_file = Path(value['runtime_argv']['update'][2])
        tool_file.chmod(0o666)
        code, value = self.run_cli('status')
        self.assertEqual(2, code, value)

    def test_cache_content_and_metadata_tamper_cannot_bypass_snapshot_hashes(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        cache = self.state / 'releases' / value['cache_id']
        profile = cache / 'profiles/coding-agent.md'
        profile.write_bytes(b'modified protocol content\n')
        metadata_path = cache / 'metadata.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['files']['profiles/coding-agent.md'] = self.agent.digest(profile.read_bytes())
        metadata_path.write_text(json.dumps(metadata))
        before = self.tree()
        code, value = self.run_cli('status')
        self.assertEqual(5, code, value)
        self.assertFalse(value['verified'])
        self.assertEqual(before, self.tree())

    def test_active_codex_override_drift_is_not_verified_but_removal_uses_recorded_target(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        override = self.codex / 'AGENTS.override.md'
        override.write_bytes(b'new active override\n')
        before = self.tree()
        code, value = self.run_cli('status')
        self.assertEqual(0, code, value)
        self.assertTrue(value['installed'])
        self.assertFalse(value['verified'])
        self.assertFalse(value['target_matches'])
        self.assertEqual(str(override), value['selected_target'])
        self.assertEqual(str(self.codex / 'AGENTS.md'), value['target'])
        self.assertEqual(before, self.tree())
        code, value = self.run_cli('install')
        self.assertEqual(7, code, value)
        self.assertEqual(before, self.tree())
        code, value = self.run_cli('uninstall')
        self.assertEqual(0, code, value)
        self.assertEqual(b'new active override\n', override.read_bytes())
        self.assertEqual(b'', (self.codex / 'AGENTS.md').read_bytes())

    def test_argument_errors_return_json_and_do_not_write(self):
        before = self.tree()
        result = subprocess.run([sys.executable, str(self.script), 'install'], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(2, result.returncode)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual('', result.stderr)
        self.assertEqual(before, self.tree())

    def test_partial_runtime_failure_reports_durable_status_and_never_claims_success(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(self.agent, 'load_runtime', return_value=self.runtime), \
                mock.patch.object(self.runtime.Controller, 'configure', side_effect=self.runtime.WriteError('configuration failure')), \
                redirect_stdout(output):
            code = self.agent.main(['install', '--host', 'codex', '--state-dir', str(self.state)])
        value = json.loads(output.getvalue())
        self.assertEqual(8, code)
        self.assertFalse(value['ok'])
        self.assertTrue(Path(value['management_argv']['status'][2]).exists())
        code, value = self.run_cli('status')
        self.assertEqual(0, code, value)
        self.assertTrue(value['verified'])


    def signed_static(self, version='0.3.0', sequence=1, key=None):
        key = key or self.root / 'test signing key'
        if not key.exists():
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True, capture_output=True)
        public = Path(str(key) + '.pub')
        fingerprint = self.runtime.key_fingerprint(public)
        manifest = self.runtime.make_manifest(self.bundle, version, sequence, fingerprint)
        static = self.root / ('sealed-' + version + '-' + key.name)
        (static / 'stable').mkdir(parents=True)
        raw = self.runtime.json_bytes(manifest)
        (static / 'stable/release.json').write_bytes(raw)
        signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'kproto-release-v1'], input=raw, check=True, capture_output=True).stdout
        (static / 'stable/release.json.sig').write_bytes(signature)
        for name in self.runtime.CONTENT_PATHS:
            dest = static / 'releases' / version / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = (self.bundle / name).read_bytes()
            if name.endswith('.json'):
                value = json.loads(data)
                value['version'] = version
                data = self.runtime.json_bytes(value)
                # Manifest must authenticate the version-adjusted fixture.
                entry = next(item for item in manifest['files'] if item['path'] == name)
                entry.update(size=len(data), sha256=self.runtime.digest(data))
            dest.write_bytes(data)
        raw = self.runtime.json_bytes(manifest)
        (static / 'stable/release.json').write_bytes(raw)
        signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'kproto-release-v1'], input=raw, check=True, capture_output=True).stdout
        (static / 'stable/release.json.sig').write_bytes(signature)
        return ['--signed-directory', str(static), '--trust-key', str(public), '--expected-fingerprint', fingerprint]

    def test_signed_plan_and_install_for_both_hosts(self):
        extras = self.signed_static() + ['--source', 'https://updates.example/protocol', '--autoupdate', 'interval']
        for host in ('codex', 'claude-code'):
            self.state = self.root / ('signed-state-' + host)
            before = self.tree()
            code, value = self.run_cli('plan', host, extras=extras)
            self.assertEqual(0, code, value)
            self.assertTrue(value['content_verified'])
            self.assertFalse(value['install_validated'])
            self.assertEqual(before, self.tree())
            code, value = self.run_cli('install', host, extras=extras)
            self.assertEqual(0, code, value)
            self.assertTrue(value['verified'])
            self.assertEqual('signed', value['trust'])
            self.assertEqual('0.3.0', value['version'])
            self.assertEqual('interval', value['autoupdate'])
            self.assertEqual('https://updates.example/protocol', value['source'])

    def test_bad_signed_inputs_do_not_mutate_state_or_target(self):
        extras = self.signed_static()
        signature = Path(extras[1]) / 'stable/release.json.sig'
        valid = signature.read_bytes()
        scenarios = [extras + ['--source', 'http://invalid.example'],
                     extras[:-1] + ['SHA256:wrong']]
        other = self.root / 'other key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(other)], check=True, capture_output=True)
        scenarios.append(extras[:2] + ['--trust-key', str(other) + '.pub', '--expected-fingerprint', self.runtime.key_fingerprint(Path(str(other) + '.pub'))])
        for arguments in scenarios:
            before = self.tree()
            code, value = self.run_cli('install', extras=arguments)
            self.assertNotEqual(0, code, value)
            self.assertEqual(before, self.tree())
        signature.write_bytes(b'invalid signature')
        before = self.tree()
        code, value = self.run_cli('install', extras=extras)
        self.assertNotEqual(0, code, value)
        self.assertEqual(before, self.tree())
        signature.write_bytes(valid)
        payload = Path(extras[1]) / 'releases/0.3.0/profiles/coding-agent.md'
        payload.write_bytes(b'altered payload')
        before = self.tree()
        code, value = self.run_cli('install', extras=extras)
        self.assertNotEqual(0, code, value)
        self.assertEqual(before, self.tree())

    def test_non_ascii_public_key_reports_json_without_writes(self):
        extras = self.signed_static()
        key = Path(extras[3])
        key.write_bytes(b'\xffinvalid key')
        before = self.tree()
        code, value = self.run_cli('install', extras=extras)
        self.assertNotEqual(0, code, value)
        self.assertIn('key', value['error'].lower())
        self.assertEqual(before, self.tree())

    def test_signed_plan_and_install_do_not_fetch_remote_source(self):
        extras = self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'interval']
        with mock.patch.dict(os.environ, self.env), mock.patch.object(self.agent, 'load_runtime', return_value=self.runtime), \
                mock.patch.object(self.runtime.Controller, 'fetch', side_effect=AssertionError('Unrequested network')) as fetch:
            for action in ('plan', 'install'):
                with redirect_stdout(io.StringIO()):
                    code = self.agent.main([action, '--host', 'codex', '--state-dir', str(self.state)] + extras)
                self.assertEqual(0, code)
            fetch.assert_not_called()

    def test_unsigned_remote_modes_are_rejected_without_writes(self):
        for extras in (['--autoupdate', 'interval'], ['--autoupdate', 'scheduled'], ['--source', 'https://updates.example']):
            before = self.tree()
            code, value = self.run_cli('install', extras=extras)
            self.assertNotEqual(0, code, value)
            self.assertEqual(before, self.tree())

    def test_signed_upgrade_preserves_existing_anchor_and_rejects_rotation(self):
        initial = self.signed_static()
        code, value = self.run_cli('install', extras=initial)
        self.assertEqual(0, code, value)
        next_release = self.signed_static('0.4.0', 2)
        code, value = self.run_cli('install', extras=next_release)
        self.assertEqual(0, code, value)
        self.assertEqual('0.4.0', value['version'])
        rotated = self.signed_static('0.5.0', 3, self.root / 'replacement key')
        before = self.tree()
        code, value = self.run_cli('install', extras=rotated)
        self.assertNotEqual(0, code, value)
        self.assertEqual(before, self.tree())

    def test_unsigned_install_cannot_downgrade_existing_signed_state(self):
        code, value = self.run_cli('install', extras=self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'interval'])
        self.assertEqual(0, code, value)
        before = self.tree()
        code, value = self.run_cli('install')
        self.assertNotEqual(0, code, value)
        self.assertEqual(before, self.tree())

    def test_unsigned_preflight_race_cannot_downgrade_signed_install(self):
        extras = self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'interval']
        original = self.runtime.content_files
        installed = {}
        def raced_content(bundle):
            if Path(bundle) == self.bundle and not installed:
                code, value = self.run_cli('install', extras=extras)
                self.assertEqual(0, code, value)
                installed.update(value)
                installed['tree'] = self.tree()
            return original(bundle)
        with mock.patch.dict(os.environ, self.env), mock.patch.object(self.agent, 'load_runtime', return_value=self.runtime), \
                mock.patch.object(self.runtime, 'content_files', side_effect=raced_content), redirect_stdout(io.StringIO()):
            code = self.agent.main(['install', '--host', 'codex', '--state-dir', str(self.state)])
        self.assertEqual(5, code)
        self.assertEqual(installed['tree'], self.tree())
        self.assertEqual('signed', json.loads((self.state / 'state.json').read_text())['trust'])

    def test_anchor_recheck_under_lock_preserves_concurrent_anchor(self):
        extras = self.signed_static()
        replacement = self.root / 'concurrent key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(replacement)], check=True, capture_output=True)
        replacement_public = Path(str(replacement) + '.pub')
        replacement_fingerprint = self.runtime.key_fingerprint(replacement_public)
        original = self.agent.preserve_trust
        captured = {}
        def raced_trust(runtime, controller, public, fingerprint):
            controller.trust_key(replacement_public, replacement_fingerprint)
            captured['key'] = (self.state / 'trust/public_key').read_bytes()
            captured['allowed'] = (self.state / 'trust/allowed_signers').read_bytes()
            return original(runtime, controller, public, fingerprint)
        with mock.patch.dict(os.environ, self.env), mock.patch.object(self.agent, 'load_runtime', return_value=self.runtime), \
                mock.patch.object(self.agent, 'preserve_trust', side_effect=raced_trust), redirect_stdout(io.StringIO()):
            code = self.agent.main(['install', '--host', 'codex', '--state-dir', str(self.state)] + extras)
        self.assertEqual(5, code)
        self.assertEqual(captured['key'], (self.state / 'trust/public_key').read_bytes())
        self.assertEqual(captured['allowed'], (self.state / 'trust/allowed_signers').read_bytes())
        self.assertFalse(self.target('codex').exists())

    def test_fifo_action_lock_is_rejected_without_blocking(self):
        self.state.mkdir(mode=0o700)
        os.mkfifo(self.state / 'agent-action.lock', mode=0o600)
        try:
            result = subprocess.run([sys.executable, '-B', str(self.script), 'install', '--host', 'codex', '--state-dir', str(self.state)],
                                    env=self.env, capture_output=True, text=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('Installer blocked while opening an untrusted FIFO lock')
        self.assertEqual('', result.stderr)
        self.assertEqual(2, result.returncode, result.stdout)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertFalse(self.target('codex').exists())

    def test_other_helper_action_holds_exclusive_guard(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        with self.agent.mutation_guard(self.runtime, self.state, 'codex', False):
            before = self.tree()
            code, value = self.run_cli('uninstall')
            self.assertEqual(7, code, value)
            self.assertEqual(before, self.tree())

    def test_new_helper_preserves_and_coexists_with_different_legacy_helper(self):
        code, value = self.run_cli('install')
        self.assertEqual(0, code, value)
        current = Path(value['management_argv']['status'][2]).parent
        legacy = self.state / 'agent-tool'
        current.rename(legacy)
        helper = legacy / 'agent-install.py'
        helper.write_bytes(helper.read_bytes() + b'\n# Previous installer release fixture.\n')
        metadata_path = legacy / 'owner.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['version'] = '0.1.9'
        metadata['files']['agent-install.py'] = self.agent.digest(helper.read_bytes())
        metadata_path.write_text(json.dumps(metadata))
        before = {str(path.relative_to(legacy)): path.read_bytes() for path in legacy.rglob('*') if path.is_file()}
        code, value = self.run_cli('install', extras=self.signed_static())
        self.assertEqual(0, code, value)
        self.assertNotEqual(str(helper), value['management_argv']['status'][2])
        self.assertEqual(before, {str(path.relative_to(legacy)): path.read_bytes() for path in legacy.rglob('*') if path.is_file()})
        code, value = self.run_cli('status', script=helper)
        self.assertEqual(0, code, value)
        self.assertTrue(value['verified'])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS scheduler only')
    def test_signed_scheduler_registration_plan_has_no_writes_or_launchctl(self):
        extras = self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'scheduled', '--register-scheduler']
        before = self.tree()
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(self.agent, 'load_runtime', return_value=self.runtime), \
                mock.patch.object(self.runtime, 'launchctl', side_effect=AssertionError('launchctl must not run in a new plan')), \
                redirect_stdout(io.StringIO()) as output:
            code = self.agent.main(['plan', '--host', 'codex', '--state-dir', str(self.state), *extras])
        value = json.loads(output.getvalue())
        self.assertEqual(0, code, value)
        self.assertTrue(value['scheduler_registration_requested'])
        self.assertTrue(any('/Library/LaunchAgents/' in path for path in value['proposed_writes']))
        self.assertEqual(before, self.tree())
        self.assertIn('scheduler_register', value['runtime_argv'])

    def test_registration_opt_in_rejects_missing_signed_scheduled_source(self):
        for extras in (['--register-scheduler'], ['--register-scheduler', '--autoupdate', 'scheduled'],
                       ['--register-scheduler', '--source', 'https://updates.example']):
            before = self.tree()
            code, value = self.run_cli('install', extras=extras)
            self.assertEqual(2, code, value)
            self.assertFalse(value['ok'])
            self.assertEqual(before, self.tree())

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS scheduler only')
    def test_signed_opt_in_registers_durable_runtime_and_failure_returns_cleanup_commands(self):
        extras = self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'scheduled', '--register-scheduler']
        load = self.agent.load_runtime
        called = []
        def patched_load(bundle):
            module = load(bundle)
            def register(ctrl):
                called.append((Path(module.__file__), ctrl.root, ctrl._state()['trust'], ctrl._config()['mode']))
                raise module.WriteError('modeled registration failure')
            module.Controller.register_scheduler = register
            return module
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(self.agent, 'load_runtime', side_effect=patched_load), \
                redirect_stdout(io.StringIO()) as output:
            code = self.agent.main(['install', '--host', 'codex', '--state-dir', str(self.state), *extras])
        value = json.loads(output.getvalue())
        self.assertEqual(8, code, value)
        self.assertFalse(value['ok'])
        self.assertEqual(1, len(called))
        path, root, trust, mode = called[0]
        self.assertIn(root, path.parents)
        self.assertNotIn(self.bundle, path.parents)
        self.assertEqual(('signed', 'scheduled'), (trust, mode))
        self.assertTrue(Path(value['runtime_argv']['scheduler_unregister'][2]).is_file())
        code, value = self.run_cli('status')
        self.assertEqual(0, code, value)
        self.assertTrue(value['verified'])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS scheduler only')
    def test_signed_scheduled_and_management_survive_clone_removal(self):
        extras = self.signed_static() + ['--source', 'https://updates.example', '--autoupdate', 'scheduled']
        code, value = self.run_cli('install', extras=extras)
        self.assertEqual(0, code, value)
        scheduler = value['scheduler']
        self.assertFalse(scheduler['registered'])
        job = plistlib.loads(Path(scheduler['path']).read_bytes())
        self.assertIn(str(self.state), job['ProgramArguments'])
        self.assertNotIn(str(self.bundle), ' '.join(job['ProgramArguments']))
        self.assertEqual(value['runtime_argv']['update'][2], job['ProgramArguments'][1])
        shutil.rmtree(self.bundle)
        commands = value['management_argv']
        result = subprocess.run(commands['status'], env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['verified'])
        disabled = value['runtime_argv']['configure_off']
        result = subprocess.run(disabled, env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = subprocess.run(value['runtime_argv']['run'] + ['--', sys.executable, '-c', 'print("wrapper survived")'], env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('wrapper survived', result.stdout)


if __name__ == '__main__':
    unittest.main()
