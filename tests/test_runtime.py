import importlib
import io
import http.client
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path('runtime/kproto.py').exists(), 'runtime installer is not implemented')
        self.k = importlib.import_module('runtime.kproto')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        for path in self.k.CONTENT_PATHS:
            p = self.bundle / path
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix=='.json':
                array='rules' if path.startswith('specification/') else 'entries'
                p.write_text(json.dumps({'schema_version':'1.0','version':'0.1.0',array:[{'id':'fixture'}]}),encoding='utf-8')
            else:
                p.write_text('뜻과 조건을 유지한다.\n',encoding='utf-8')
        self.target = self.root / 'project' / 'AGENTS.md'
        self.target.parent.mkdir()
        self.original = '사용자의 승인 정책을 유지한다.\r\n'.encode('utf-8')
        self.target.write_bytes(self.original)
        self.controller = self.k.Controller(self.root / 'state')

    def install(self, version='0.1.0'):
        return self.controller.install_snapshot(self.bundle, self.target, version)

    def test_install_is_idempotent_and_preserves_original_bytes(self):
        self.install()
        installed = self.target.read_bytes()
        self.assertTrue(installed.startswith(self.original))
        self.assertIn('뜻과 조건을 유지한다.'.encode(), installed)
        self.install()
        self.assertEqual(installed, self.target.read_bytes())
        self.assertEqual(1, installed.count(self.k.BEGIN))

    def test_uninstall_preserves_user_changes_outside_block(self):
        self.install()
        self.target.write_bytes(b'# Added by user\n' + self.target.read_bytes())
        self.controller.uninstall()
        self.assertEqual(b'# Added by user\n' + self.original, self.target.read_bytes())

    def test_user_edit_inside_block_blocks_update(self):
        self.install()
        self.target.write_bytes(self.target.read_bytes().replace('뜻과'.encode(), '사실과'.encode()))
        edited = self.target.read_bytes()
        with self.assertRaises(self.k.ConflictError):
            self.install('0.2.0')
        self.assertEqual(edited, self.target.read_bytes())
        self.assertEqual('0.1.0', self.controller.status()['version'])

    def test_rollback_pins_cached_version_and_preserves_sequence(self):
        self.install()
        (self.bundle / 'profiles/coding-agent.md').write_text('수정한 규약이다.\n')
        self.install('0.2.0')
        self.controller.rollback('0.1.0')
        state = self.controller.status()
        self.assertEqual('0.1.0', state['version'])
        self.assertEqual('0.1.0', state['pin'])
        self.assertIn('뜻과 조건을 유지한다.'.encode(), self.target.read_bytes())

    def test_offline_and_off_keep_profile_without_network(self):
        self.install()
        self.controller.configure(mode='off')
        with mock.patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertFalse(self.controller.update(scheduled=True))
            self.assertEqual('0.1.0', self.controller.status()['version'])

    def test_pin_suppresses_scheduled_network(self):
        self.install()
        self.controller.configure(mode='interval', source='https://example.test/kproto')
        self.controller.pin('0.1.0')
        with mock.patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertFalse(self.controller.update(scheduled=True))

    def test_rejects_symlink_target_and_payload(self):
        other = self.root / 'other'
        other.write_text('do not overwrite')
        link = self.target.parent / 'linked.md'
        link.symlink_to(other)
        with self.assertRaises(self.k.InputError):
            self.controller.install_snapshot(self.bundle, link, '0.1.0')
        payload = self.bundle / 'profiles/chat.md'
        payload.unlink()
        payload.symlink_to(other)
        with self.assertRaises(self.k.InputError):
            self.install()
        self.assertEqual('do not overwrite', other.read_text())

    def test_rejects_hardlinked_target(self):
        other = self.root / 'hardlink'
        os.link(self.target, other)
        with self.assertRaises(self.k.InputError):
            self.install()

    def test_rejects_profile_over_budget_and_invalid_json(self):
        (self.bundle / 'profiles/coding-agent.md').write_bytes(b'x' * (28 * 1024 + 1))
        with self.assertRaises(self.k.InputError):
            self.install()
        (self.bundle / 'profiles/coding-agent.md').write_text('본문')
        (self.bundle / 'lexicon/core.json').write_text('{"a":1,"a":2}')
        with self.assertRaises(self.k.InputError):
            self.install()

    def test_explicit_target_budget_is_not_silently_truncated(self):
        self.target.write_bytes(b'x' * 32760)
        with self.assertRaises(self.k.InputError):
            self.install()
        self.assertEqual(b'x' * 32760, self.target.read_bytes())

    def test_failed_state_commit_recovers_previous_profile(self):
        self.install()
        installed = self.target.read_bytes()
        write = self.k.atomic_write

        def interrupted(path, data, **kwargs):
            if Path(path).name == 'state.json':
                raise OSError('injected state write failure')
            return write(path, data, **kwargs)

        with mock.patch.object(self.k, 'atomic_write', side_effect=interrupted):
            with self.assertRaises(self.k.WriteError):
                self.install('0.2.0')
        self.assertEqual(installed, self.target.read_bytes())
        self.assertEqual('0.1.0', self.controller.status()['version'])

    def test_process_interrupt_journal_recovers_before_next_write(self):
        self.install()
        installed = self.target.read_bytes()
        write = self.k.atomic_write

        def interrupted(path, data, **kwargs):
            if Path(path).name == 'state.json':
                raise KeyboardInterrupt()
            return write(path, data, **kwargs)

        with mock.patch.object(self.k, 'atomic_write', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.install('0.2.0')
        self.assertTrue(self.controller.status()['recovery_required'])
        self.controller.recover()
        self.assertEqual(installed, self.target.read_bytes())
        self.assertEqual('0.1.0', self.controller.status()['version'])

    def test_lock_blocks_concurrent_writer(self):
        self.install()
        with self.controller.lock():
            with self.assertRaises(self.k.ConflictError):
                self.install('0.2.0')

    def test_target_is_not_claimed_by_second_state(self):
        self.install()
        other = self.k.Controller(self.root / 'state2')
        with self.assertRaises(self.k.ConflictError):
            other.install_snapshot(self.bundle, self.target, '0.1.0')

    def test_rejects_credential_url_and_masks_token_on_network_failure(self):
        for url in ['http://example.test', 'https://u:p@example.test', 'https://example.test/?token=secret']:
            with self.assertRaises(self.k.InputError):
                self.controller.configure(source=url)
        self.install()
        self.controller.configure(source='https://example.test', token_env='KPROTO_TEST_TOKEN')
        self.controller.trust_key = lambda *args: None
        with mock.patch.dict(os.environ, {'KPROTO_TEST_TOKEN': 'super-secret-token'}):
            with mock.patch('urllib.request.OpenerDirector.open', side_effect=OSError('super-secret-token')):
                with self.assertRaises(self.k.NetworkError) as result:
                    self.controller.fetch('https://example.test/release.json', 100)
        self.assertNotIn('super-secret-token', str(result.exception))

    def test_cli_status_reads_local_state(self):
        self.install()
        p = subprocess.run([shutil.which('python3'), '-m', 'runtime.kproto', '--state-dir', str(self.root/'state'), 'status', '--json'], capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertEqual('0.1.0', json.loads(p.stdout)['version'])

    def test_generated_launchd_job_has_fixed_local_command_and_no_secrets(self):
        self.install()
        output = self.root/'schedule.plist'
        config=self.controller.configure(mode='scheduled',source='https://example.test',token_env='KPROTO_TEST_TOKEN',emit=output)
        job=plistlib.loads(output.read_bytes())
        self.assertTrue(job['RunAtLoad'])
        self.assertEqual(86400,job['StartInterval'])
        self.assertIn('--scheduled',job['ProgramArguments'])
        self.assertEqual('generated',config['scheduler']['status'])
        self.assertFalse(config['scheduler']['registered'])
        self.assertNotIn('EnvironmentVariables',job)
        self.controller.configure(mode='off')
        self.assertFalse(output.exists())
        self.assertEqual('disabled',self.controller.status()['scheduler']['status'])

    def test_modified_launchd_output_is_preserved_when_disabled(self):
        output=self.root/'schedule.plist'
        self.controller.configure(mode='scheduled',emit=output)
        output.write_bytes(output.read_bytes()+b'\n<!-- user -->')
        before=output.read_bytes()
        with self.assertRaises(self.k.ConflictError):
            self.controller.configure(mode='off')
        self.assertEqual(before,output.read_bytes())

    def test_cli_does_not_charge_global_against_codex_project_budget(self):
        home=self.root/'codex-home'
        home.mkdir()
        (home/'AGENTS.md').write_bytes(b'x'*32760)
        p=subprocess.run([shutil.which('python3'),'-m','runtime.kproto','--state-dir',str(self.root/'cli-state'),'install','--bundle',str(self.bundle),'--local-snapshot','--host','codex','--scope','project','--project-root',str(self.target.parent),'--codex-home',str(home)],capture_output=True,text=True)
        self.assertEqual(0,p.returncode,p.stderr)
        self.assertTrue(self.target.read_bytes().startswith(self.original))
        self.assertEqual(b'x'*32760,(home/'AGENTS.md').read_bytes())

    def test_abrupt_process_exit_releases_lock_and_journal_can_recover(self):
        self.install()
        installed=self.target.read_bytes()
        code='''
import os,sys
from pathlib import Path
from runtime import kproto
c=kproto.Controller(Path(sys.argv[1]))
write=kproto.atomic_write
def interrupted(path,data,**kwargs):
 if Path(path).name=='state.json': os._exit(23)
 return write(path,data,**kwargs)
kproto.atomic_write=interrupted
c.install_snapshot(Path(sys.argv[2]),Path(sys.argv[3]),'0.2.0')
'''
        p=subprocess.run([shutil.which('python3'),'-c',code,str(self.root/'state'),str(self.bundle),str(self.target)])
        self.assertEqual(23,p.returncode)
        self.assertTrue(self.controller.status()['recovery_required'])
        self.controller.recover()
        self.assertEqual(installed,self.target.read_bytes())

    def test_content_schema_mismatch_and_non_object_are_rejected(self):
        rules=self.bundle/'specification/rules.json'
        for data in [[],{'schema_version':'2.0','version':'0.1.0','rules':[]},{'schema_version':'1.0','version':'0.1.0','rules':'wrong'}]:
            rules.write_text(json.dumps(data))
            with self.assertRaises(self.k.ProtocolError):
                self.install()
        self.assertEqual(self.original,self.target.read_bytes())

    def test_uninstall_preserves_user_newline_added_before_block(self):
        self.target.write_bytes(b'Original without newline')
        self.install()
        self.target.write_bytes(self.target.read_bytes().replace(self.k.BEGIN,b'User-added line\n'+self.k.BEGIN))
        self.controller.uninstall()
        self.assertEqual(b'Original without newline\nUser-added line\n',self.target.read_bytes())

    def test_current_project_budget_is_rechecked_after_install(self):
        home=self.root/'home'
        home.mkdir()
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
        installed=self.target.read_bytes()
        (home/'config.toml').write_text('project_doc_max_bytes = 64\n')
        with self.assertRaises(self.k.InputError):
            self.install('0.2.0')
        self.assertEqual(installed,self.target.read_bytes())

    def test_bad_http_response_and_nested_json_have_safe_errors(self):
        self.controller.configure(source='https://example.test')
        with mock.patch('urllib.request.OpenerDirector.open',side_effect=http.client.BadStatusLine('secret-response-token')):
            with self.assertRaises(self.k.NetworkError) as result:
                self.controller.fetch('https://example.test/release.json',100)
        self.assertNotIn('secret-response-token',str(result.exception))
        with self.assertRaises(self.k.InputError):
            self.k.strict_json(b'['*1100+b'0'+b']'*1100)

    def test_total_fetch_deadline_terminates_blocked_reader(self):
        self.controller.configure(source='https://example.test')
        import time

        def blocked(*args,**kwargs):
            time.sleep(2)
            raise OSError('late')

        start=time.monotonic()
        with mock.patch('urllib.request.OpenerDirector.open',side_effect=blocked):
            with self.assertRaises(self.k.NetworkError):
                self.controller.fetch('https://example.test/release.json',100,deadline=start+0.1)
        self.assertLess(time.monotonic()-start,1)

    def test_host_context_is_absolute_across_working_directory_changes(self):
        home=self.root/'home'
        home.mkdir()
        elsewhere=self.root/'elsewhere'
        elsewhere.mkdir()
        original_cwd=Path.cwd()
        try:
            os.chdir(self.root)
            context={'host':'codex','scope':'project','project_root':'project','codex_home':'home'}
            self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
            (home/'config.toml').write_text('project_doc_max_bytes = 64\n')
            os.chdir(elsewhere)
            with self.assertRaises(self.k.InputError):
                self.install('0.2.0')
        finally:
            os.chdir(original_cwd)
        self.assertEqual(str(home),self.controller.status()['host_context']['codex_home'])

    def test_new_codex_override_changes_discovery_and_blocks_update(self):
        home=self.root/'home'
        home.mkdir()
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
        installed=self.target.read_bytes()
        override=self.target.parent/'AGENTS.override.md'
        override.write_text('사용자가 새 지침을 만들었다.')
        with self.assertRaises(self.k.ConflictError):
            self.install('0.2.0')
        self.assertEqual(installed,self.target.read_bytes())
        self.assertEqual('사용자가 새 지침을 만들었다.',override.read_text())

    def test_user_scope_ignores_project_cap_and_preserves_large_global(self):
        home=self.root/'home'
        home.mkdir()
        (home/'config.toml').write_text('project_doc_max_bytes = 256\n')
        target=home/'AGENTS.md'
        original=b'x'*400
        target.write_bytes(original)
        context={'host':'codex','scope':'user','project_root':None,'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,target,'0.1.0',host_context=context)
        self.assertTrue(target.read_bytes().startswith(original))
        self.assertEqual(self.k.MAX_TOTAL_BYTES,self.controller.status()['budget'])

    def test_project_ancestor_chain_charges_selected_override_only(self):
        home=self.root/'home'
        home.mkdir()
        (home/'AGENTS.md').write_bytes(b'g'*400)
        (home/'config.toml').write_text('project_doc_max_bytes = 1024\n')
        project=self.root/'repo'
        project.mkdir()
        (project/'.git').mkdir()
        (project/'AGENTS.md').write_bytes(b'ignored'*200)
        selected=project/'AGENTS.override.md'
        selected.write_bytes(b'a'*200)
        child=project/'child'
        child.mkdir()
        target=child/'AGENTS.md'
        context={'host':'codex','scope':'project','project_root':str(child),'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,target,'0.1.0',host_context=context)
        self.assertEqual(824,self.controller.status()['budget'])
        installed=target.read_bytes()
        selected.write_bytes(b'a'*1000)
        with self.assertRaises(self.k.InputError):
            self.controller.install_snapshot(self.bundle,target,'0.2.0')
        self.assertEqual(installed,target.read_bytes())

    def test_project_chain_ignores_ancestors_above_git_root(self):
        home=self.root/'home'
        home.mkdir()
        (home/'config.toml').write_text('project_doc_max_bytes = 1024\n')
        (self.root/'AGENTS.md').write_bytes(b'x'*5000)
        (self.target.parent/'.git').write_text('gitdir: /unused/metadata\n')
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
        self.assertEqual(1024,self.controller.status()['budget'])

    def test_large_user_file_journal_recovers_after_state_commit_interrupt(self):
        home=self.root/'home'
        home.mkdir()
        target=home/'AGENTS.md'
        target.write_bytes(b'x'*(32*1024*100))
        context={'host':'codex','scope':'user','project_root':None,'codex_home':str(home)}
        self.controller.install_snapshot(self.bundle,target,'0.1.0',host_context=context)
        installed=target.read_bytes()
        write=self.k.atomic_write

        def interrupted(path,data,**kwargs):
            if Path(path).name=='state.json':
                raise KeyboardInterrupt()
            return write(path,data,**kwargs)

        with mock.patch.object(self.k,'atomic_write',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.controller.install_snapshot(self.bundle,target,'0.2.0')
        self.controller.recover()
        self.assertEqual(installed,target.read_bytes())
        self.assertEqual('0.1.0',self.controller.status()['version'])

    def test_project_config_cannot_exceed_installer_read_safety_bound(self):
        home=self.root/'home'
        home.mkdir()
        (home/'config.toml').write_text('project_doc_max_bytes = 8388608\n')
        self.target.write_bytes(b'x'*(self.k.MAX_TOTAL_BYTES-10))
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(home)}
        before=self.target.read_bytes()
        with self.assertRaises(self.k.InputError):
            self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
        self.assertEqual(before,self.target.read_bytes())

    def test_custom_project_root_markers_require_a_verified_adapter(self):
        home=self.root/'home'
        home.mkdir()
        (home/'config.toml').write_text('project_root_markers = [".jj"]\n')
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(home)}
        with self.assertRaises(self.k.CompatibilityError):
            self.controller.install_snapshot(self.bundle,self.target,'0.1.0',host_context=context)
        self.assertEqual(self.original,self.target.read_bytes())


class SignedRuntimeTests(RuntimeTests):
    def setUp(self):
        super().setUp()
        self.ssh = shutil.which('ssh-keygen')
        if not self.ssh:
            self.skipTest('OpenSSH verifier not installed')
        self.key = self.root / 'fixture-key'
        p = subprocess.run([self.ssh, '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key)], capture_output=True)
        if p.returncode:
            self.skipTest('OpenSSH test key generation unavailable')
        self.controller.trust_key(Path(str(self.key)+'.pub'), self.k.key_fingerprint(Path(str(self.key)+'.pub')))

    def sign(self, version='0.1.0', sequence=1):
        manifest = self.k.make_manifest(self.bundle, version, sequence, self.k.key_fingerprint(Path(str(self.key)+'.pub')))
        self.manifest = self.bundle/'release.json'
        self.manifest.write_bytes(self.k.json_bytes(manifest))
        p = subprocess.run([self.ssh,'-Y','sign','-f',str(self.key),'-n','kproto-release-v1'], input=self.manifest.read_bytes(), capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr)
        (self.bundle/'release.json.sig').write_bytes(p.stdout)

    def test_real_signature_verification_rejects_manifest_tampering(self):
        self.sign()
        self.controller.install_signed(self.bundle, self.target)
        installed = self.target.read_bytes()
        self.manifest.write_bytes(self.manifest.read_bytes().replace(b'"version": "0.1.0"',b'"version": "0.2.0"'))
        with self.assertRaises(self.k.TrustError):
            self.controller.install_signed(self.bundle, self.target)
        self.assertEqual(installed,self.target.read_bytes())

    def test_real_signature_rejects_payload_tampering(self):
        self.sign()
        (self.bundle/'profiles/chat.md').write_text('변조')
        with self.assertRaises(self.k.TrustError):
            self.controller.install_signed(self.bundle,self.target)

    def test_signed_update_replay_and_rollback_highwater(self):
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,self.target)
        self.sign('0.2.0',2)
        self.controller.install_signed(self.bundle,self.target)
        self.controller.rollback('0.1.0')
        self.assertEqual(2,self.controller.status()['highest_sequence'])
        self.sign('0.0.9',1)
        with self.assertRaises(self.k.TrustError):
            self.controller.install_signed(self.bundle,self.target)

    def test_rejects_unknown_payload_path_before_writing(self):
        self.sign()
        m=json.loads(self.manifest.read_text())
        m['files'][0]['path']='../outside.py'
        self.manifest.write_bytes(self.k.json_bytes(m))
        p=subprocess.run([self.ssh,'-Y','sign','-f',str(self.key),'-n','kproto-release-v1'],input=self.manifest.read_bytes(),capture_output=True)
        (self.bundle/'release.json.sig').write_bytes(p.stdout)
        with self.assertRaises(self.k.InputError):
            self.controller.install_signed(self.bundle,self.target)

    def test_remote_update_uses_authenticated_allowlist_and_retains_offline_copy(self):
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(mode='interval',source='https://example.test/kproto')
        self.sign('0.2.0',2)

        def local_download(url,maximum,deadline=None):
            if '/stable/' in url:
                return (self.bundle/url.rsplit('/',1)[1]).read_bytes()
            return (self.bundle/url.split('/releases/0.2.0/',1)[1]).read_bytes()

        with mock.patch.object(self.controller,'fetch',side_effect=local_download):
            self.assertTrue(self.controller.update())
        self.assertEqual('0.2.0',self.controller.status()['version'])
        self.assertEqual(2,self.controller.status()['highest_sequence'])
        installed=self.target.read_bytes()
        with mock.patch.object(self.controller,'fetch',side_effect=self.k.NetworkError('offline')):
            with self.assertRaises(self.k.NetworkError):
                self.controller.update()
        self.assertEqual(installed,self.target.read_bytes())

    def test_wrong_signature_namespace_is_rejected(self):
        self.sign()
        p=subprocess.run([self.ssh,'-Y','sign','-f',str(self.key),'-n','wrong-namespace'],input=self.manifest.read_bytes(),capture_output=True)
        (self.bundle/'release.json.sig').write_bytes(p.stdout)
        with self.assertRaises(self.k.TrustError):
            self.controller.install_signed(self.bundle,self.target)

    def test_wrapper_retains_host_exit_code_after_update_failure(self):
        self.sign()
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(mode='interval',source='https://example.test')
        installed=self.target.read_bytes()
        with mock.patch.object(self.k.Controller,'fetch',side_effect=self.k.NetworkError('offline')):
            output=io.StringIO()
            with redirect_stderr(output):
                code=self.k.main(['--state-dir',str(self.root/'state'),'run','--',shutil.which('python3'),'-c','import sys;sys.exit(11)'])
        self.assertEqual(11,code)
        self.assertIn('local profile retained',output.getvalue())
        self.assertEqual(installed,self.target.read_bytes())

    def test_pin_changed_during_download_prevents_apply(self):
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(mode='interval',source='https://example.test/kproto')
        self.sign('0.2.0',2)
        pinned=False

        def download(url,maximum,deadline=None):
            nonlocal pinned
            if not pinned:
                self.controller.pin('0.1.0')
                pinned=True
            return (self.bundle/(url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1])).read_bytes()

        with mock.patch.object(self.controller,'fetch',side_effect=download):
            self.assertFalse(self.controller.update())
        self.assertEqual('0.1.0',self.controller.status()['version'])
        self.assertEqual('0.1.0',self.controller.status()['pin'])

    def test_configure_off_during_download_is_preserved_and_cancels_apply(self):
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(mode='interval',source='https://example.test/kproto')
        self.sign('0.2.0',2)
        disabled=False

        def download(url,maximum,deadline=None):
            nonlocal disabled
            if not disabled:
                self.controller.configure(mode='off')
                disabled=True
            return (self.bundle/(url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1])).read_bytes()

        with mock.patch.object(self.controller,'fetch',side_effect=download):
            self.assertFalse(self.controller.update(scheduled=True))
        self.assertEqual('off',self.controller.status()['autoupdate'])
        self.assertEqual('0.1.0',self.controller.status()['version'])

    def test_signed_manifest_cannot_override_payload_schema_compatibility(self):
        self.sign()
        payload=self.bundle/'specification/rules.json'
        document=json.loads(payload.read_text())
        document['schema_version']='2.0'
        payload.write_bytes(self.k.json_bytes(document))
        manifest=json.loads(self.manifest.read_bytes())
        entry=next(e for e in manifest['files'] if e['path']=='specification/rules.json')
        entry['size']=len(payload.read_bytes())
        entry['sha256']=self.k.digest(payload.read_bytes())
        self.manifest.write_bytes(self.k.json_bytes(manifest))
        signed=subprocess.run([self.ssh,'-Y','sign','-f',str(self.key),'-n','kproto-release-v1'],input=self.manifest.read_bytes(),capture_output=True)
        (self.bundle/'release.json.sig').write_bytes(signed.stdout)
        with self.assertRaises(self.k.CompatibilityError):
            self.controller.install_signed(self.bundle,self.target)
        self.assertEqual(self.original,self.target.read_bytes())

    def test_wrapper_starts_host_after_update_filesystem_failure(self):
        self.sign()
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(mode='interval',source='https://example.test')
        output=io.StringIO()
        with mock.patch.object(self.k.Controller,'update',side_effect=OSError('disk full')):
            with redirect_stderr(output):
                code=self.k.main(['--state-dir',str(self.root/'state'),'run','--',shutil.which('python3'),'-c','import sys;sys.exit(11)'])
        self.assertEqual(11,code)

    def test_last_payload_after_total_deadline_is_not_activated(self):
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure(source='https://example.test/kproto')
        self.sign('0.2.0',2)
        clock=[0]

        def download(url,maximum,deadline=None):
            name=url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1]
            if name=='pack/protocol.md':
                clock[0]=61
            return (self.bundle/name).read_bytes()

        with mock.patch.object(self.k.time,'monotonic',side_effect=lambda:clock[0]):
            with mock.patch.object(self.controller,'fetch',side_effect=download):
                with self.assertRaises(self.k.NetworkError):
                    self.controller.update()
        self.assertEqual('0.1.0',self.controller.status()['version'])


if __name__ == '__main__':
    unittest.main()
