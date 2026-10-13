import importlib
import importlib.util
import argparse
import io
import http.client
import json
import multiprocessing
import os
import plistlib
from pathlib import Path
import shutil
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stderr
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

    @contextmanager
    def https_proxy(self,response=b'HTTP/1.1 200 OK\r\nContent-Length: 7\r\n\r\ncontent',stall=None):
        """Serve real TLS through the proxy selected by the fresh worker."""
        openssl=shutil.which('openssl')
        self.assertIsNotNone(openssl,'TLS fixture requires OpenSSL')
        cert=self.root/'tls-cert.pem'
        key=self.root/'tls-key.pem'
        generated=subprocess.run([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-subj','/CN=example.test','-days','1','-addext','subjectAltName=DNS:example.test'],capture_output=True)
        self.assertEqual(0,generated.returncode,generated.stderr)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert,key)
        # Xcode's LibreSSL default loader ignores SSL_CERT_FILE. Explicitly trust
        # this fixture CA without disabling hostname or certificate verification.
        bootstrap=self.root/'tls-worker.py'
        bootstrap.write_text('import ssl, runpy\nssl._create_default_https_context=lambda: ssl.create_default_context(cafile='+repr(str(cert))+')\nrunpy.run_path('+repr(str(Path(self.k.__file__).resolve()))+',run_name="__main__")\n')
        reached=threading.Event()
        stop=threading.Event()
        requests=[]

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    connect=self.rfile.readline()
                    if not connect.startswith(b'CONNECT example.test:443 '):
                        return
                    while self.rfile.readline() not in (b'\r\n',b'\n',b''):
                        pass
                    if stall=='proxy':
                        reached.set()
                        stop.wait(5)
                        return
                    self.wfile.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
                    self.wfile.flush()
                    with tls.wrap_socket(self.connection,server_side=True) as connection:
                        with connection.makefile('rb') as request:
                            lines=[request.readline()]
                            while True:
                                line=request.readline()
                                if line in (b'\r\n',b'\n',b''):
                                    break
                                lines.append(line)
                        requests.append(b''.join(lines))
                        connection.sendall(response)
                        reached.set()
                        if stall=='body':
                            stop.wait(5)
                except (OSError,ssl.SSLError):
                    pass

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads=True
            block_on_close=False

        server=Server(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        thread.start()
        proxy='http://127.0.0.1:'+str(server.server_address[1])
        try:
            with mock.patch.dict(os.environ,{'HTTPS_PROXY':proxy,'https_proxy':proxy,'NO_PROXY':'','no_proxy':'','SSL_CERT_FILE':str(cert)}),mock.patch.object(self.k,'__file__',str(bootstrap)):
                yield reached,requests
        finally:
            stop.set()
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_speech_controls_preserve_compact_status_and_procedure_actor(self):
        self.install()
        for honorifics in (False, True):
            with self.subTest(honorifics=honorifics):
                self.controller.configure_application(honorifics=honorifics)
                active=self.target.read_bytes()
                self.assertIn('새 설명·보고 문장의 종결형만'.encode(),active)
                self.assertIn('기존 문체는 보존한다.'.encode(),active)
                self.assertIn('표기된 담당자 없음.'.encode(),active)
                self.assertIn('종결형을 맞추려고 문장을 늘리지 않는다.'.encode(),active)
                self.assertIn('절차 주체를 분명히 쓴다.'.encode(),active)
                self.assertIn('모델 자신의 실행 계획으로 바꾸지 않는다.'.encode(),active)

    def test_application_controls_preserve_cache_user_bytes_and_survive_reinstall(self):
        self.install()
        state = self.controller.status()
        self.assertTrue(state.get('enabled'))
        self.assertFalse(state['honorifics'])
        self.assertIn('~다/~한다'.encode(), self.target.read_bytes())
        cache = self.controller.root / 'releases' / state['cache_id']
        cached = {str(p.relative_to(cache)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in cache.rglob('*') if p.is_file()}
        self.target.write_bytes(b'# Manual\r\n' + self.target.read_bytes())
        self.assertTrue(self.controller.configure_application(enabled=False, honorifics=True))
        self.assertTrue(self.controller.status()['installed'])
        self.assertFalse(self.controller.status()['enabled'])
        self.assertNotIn('뜻과 조건'.encode(), self.target.read_bytes())
        self.assertNotIn(str(cache).encode(), self.target.read_bytes())
        self.install()
        self.assertFalse(self.controller.status()['enabled'])
        restarted = self.k.Controller(self.controller.root)
        self.assertTrue(restarted.configure_application(enabled=True))
        self.assertTrue(restarted.status()['honorifics'])
        self.assertFalse(restarted.configure_application(enabled=True, honorifics=True))
        self.assertIn('~습니다/~ㅂ니다'.encode(), self.target.read_bytes())
        self.assertEqual(cached, {str(p.relative_to(cache)): (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in cache.rglob('*') if p.is_file()})
        restarted.uninstall()
        self.assertEqual(b'# Manual\r\n' + self.original, self.target.read_bytes())

    def test_off_preserves_settings_across_cached_rollback(self):
        self.install()
        self.controller.configure_application(enabled=False, honorifics=True)
        (self.bundle / 'profiles/coding-agent.md').write_text('새 내용이다.\n')
        self.install('0.2.0')
        self.controller.rollback('0.1.0')
        self.assertFalse(self.controller.status()['enabled'])
        self.assertTrue(self.controller.status()['honorifics'])
        self.assertNotIn('뜻과 조건'.encode(), self.target.read_bytes())
        self.controller.configure_application(enabled=True)
        self.assertIn('뜻과 조건'.encode(), self.target.read_bytes())

    def test_configuration_failure_rolls_back_host_and_settings(self):
        self.install()
        before = self.target.read_bytes()
        state_before = self.controller.state_path.read_bytes()
        write = self.k.atomic_write
        def interrupted(path, data, **kwargs):
            if Path(path) == self.controller.state_path:
                raise OSError('injected state failure')
            return write(path, data, **kwargs)
        with mock.patch.object(self.k, 'atomic_write', side_effect=interrupted):
            with self.assertRaises(self.k.WriteError):
                self.controller.configure_application(enabled=False, honorifics=True)
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(state_before, self.controller.state_path.read_bytes())

    def test_cached_tamper_is_rejected_before_reactivation(self):
        self.install()
        self.controller.configure_application(enabled=False)
        cache = self.controller.root / 'releases' / self.controller.status()['cache_id']
        (cache / 'profiles/coding-agent.md').write_bytes(b'tampered')
        before = self.target.read_bytes()
        with self.assertRaises(self.k.TrustError):
            self.controller.configure_application(enabled=True)
        self.assertEqual(before, self.target.read_bytes())
        self.assertFalse(self.controller.status()['enabled'])

    def test_interrupted_new_cache_creation_does_not_poison_valid_retry(self):
        write=self.k.atomic_write
        count=0
        def interrupted(path,data,**kwargs):
            nonlocal count
            if 'releases' in Path(path).parts:
                count+=1
                if count==2:
                    raise OSError('injected cache write failure')
            return write(path,data,**kwargs)
        with mock.patch.object(self.k,'atomic_write',side_effect=interrupted):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(self.original,self.target.read_bytes())
        try:
            retried=self.install()
        except self.k.ProtocolError as error:
            self.fail('Valid retry must recover after partial cache write: '+str(error))
        self.assertTrue(retried)
        self.assertTrue(self.controller.status()['installed'])

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
        with self.https_proxy(response=b'secret-response-token\r\n\r\n') as (_,requests):
            with mock.patch.dict(os.environ, {'KPROTO_TEST_TOKEN': 'super-secret-token'}):
                with self.assertRaises(self.k.NetworkError) as result:
                    self.controller.fetch('https://example.test/release.json', 100)
        self.assertNotIn('super-secret-token', str(result.exception))
        self.assertEqual(1,len(requests))
        self.assertIn(b'Authorization: Bearer super-secret-token',requests[0])

    def test_download_worker_masks_exception_details(self):
        for error in (OSError('super-secret-token'),http.client.BadStatusLine('secret-response-token')):
            with self.subTest(error=type(error).__name__),mock.patch('urllib.request.OpenerDirector.open',side_effect=error):
                self.assertEqual(b'\x00',self.k.download_worker('https://example.test',{},100))

    def test_fetch_real_https_preserves_proxy_and_body_limit(self):
        self.controller.configure(source='https://example.test')
        with self.https_proxy() as (_,requests):
            self.assertEqual(b'content',self.controller.fetch('https://example.test/release.json',7))
            with self.assertRaises(self.k.NetworkError):
                self.controller.fetch('https://example.test/release.json',6)
        self.assertEqual(2,len(requests))

    def test_fetch_real_https_refuses_redirect(self):
        self.controller.configure(source='https://example.test')
        with self.https_proxy(response=b'HTTP/1.1 302 Found\r\nLocation: https://elsewhere.test/secret\r\nContent-Length: 0\r\n\r\n') as (_,requests):
            with self.assertRaises(self.k.NetworkError):
                self.controller.fetch('https://example.test/release.json',100)
        self.assertEqual(1,len(requests))

    def test_fetch_uses_fresh_interpreter_and_private_stdin(self):
        self.controller.configure(source='https://example.test',token_env='KPROTO_TEST_TOKEN')
        worker=mock.Mock()
        worker.communicate.return_value=(b'\x01content',None)
        worker.poll.return_value=0
        worker.returncode=0
        with mock.patch.dict(os.environ,{'KPROTO_TEST_TOKEN':'private-test-token'}), \
                mock.patch.object(multiprocessing,'get_context',side_effect=AssertionError('Python fork is unsafe')), \
                mock.patch.object(self.k.subprocess,'Popen',return_value=worker) as launch:
            self.assertEqual(b'content',self.controller.fetch('https://example.test/release.json',100))
        command=launch.call_args.args[0]
        self.assertEqual(['-I','-B'],command[1:3])
        self.assertEqual(str(Path(self.k.__file__).resolve()),command[3])
        self.assertNotIn('private-test-token',' '.join(command))
        self.assertNotIn('https://example.test',' '.join(command))
        self.assertEqual(subprocess.DEVNULL,launch.call_args.kwargs['stderr'])
        request=json.loads(worker.communicate.call_args.kwargs['input'])
        self.assertEqual('Bearer private-test-token',request['headers']['Authorization'])

    def test_dynamic_agent_runtime_fetch_uses_native_proxy_discovery(self):
        bundle=Path(self.k.__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('agent_install_fetch_fixture',bundle/'distribution/agent_install.py')
        agent=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)
        runtime=agent.load_runtime(bundle)
        self.assertNotIn(runtime.__name__,sys.modules,'Fixture must retain the installer nonimportable module contract')
        controller=runtime.Controller(self.root/'dynamic-state')
        controller.configure(source='https://127.0.0.1')
        launch=subprocess.Popen
        workers=[]

        def record(*args,**kwargs):
            worker=launch(*args,**kwargs)
            workers.append(worker)
            return worker

        # Keep the normal environment: on macOS this calls native system proxy
        # discovery, safely in the newly exec'd interpreter rather than a fork.
        with mock.patch.object(runtime.subprocess,'Popen',side_effect=record):
            with self.assertRaises(runtime.NetworkError):
                controller.fetch('https://127.0.0.1/release.json',100,deadline=time.monotonic()+2)
        self.assertEqual(1,len(workers))
        self.assertIn(workers[0].returncode,(0,-9),'Worker must exit safely or be killed at the deadline, without a native crash')
        with self.https_proxy(),mock.patch.object(runtime,'__file__',self.k.__file__):
            controller.configure(source='https://example.test')
            self.assertEqual(b'content',controller.fetch('https://example.test/release.json',100))

    def test_fetch_rejects_unbounded_input_before_launching_worker(self):
        self.controller.configure(source='https://example.test',token_env='KPROTO_TEST_TOKEN')
        with mock.patch.object(self.k.subprocess,'Popen') as launch:
            for maximum in (-1,self.k.MAX_FILE_BYTES+1,True):
                with self.subTest(maximum=maximum),self.assertRaises(self.k.InputError):
                    self.controller.fetch('https://example.test/release.json',maximum)
            with mock.patch.dict(os.environ,{'KPROTO_TEST_TOKEN':'x'*self.k.MAX_DOWNLOAD_REQUEST_BYTES}):
                with self.assertRaises(self.k.InputError):
                    self.controller.fetch('https://example.test/release.json',100)
        launch.assert_not_called()

    def test_fresh_worker_rejects_malformed_and_oversized_private_input(self):
        command=[sys.executable,'-I','-B',str(Path(self.k.__file__).resolve()),'--download-worker']
        for request in (b'private-invalid-json',b'x'*(self.k.MAX_DOWNLOAD_REQUEST_BYTES+1),self.k.json_bytes({'url':'https://example.test','headers':{},'maximum':self.k.MAX_FILE_BYTES+1})):
            with self.subTest(size=len(request)):
                result=subprocess.run(command,input=request,capture_output=True,timeout=2)
                self.assertEqual(0,result.returncode)
                self.assertEqual(b'\x00',result.stdout)
                self.assertEqual(b'',result.stderr)

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
        with mock.patch('urllib.request.OpenerDirector.open',side_effect=http.client.BadStatusLine('secret-response-token')):
            self.assertEqual(b'\x00',self.k.download_worker('https://example.test/release.json',{},100))
        with self.assertRaises(self.k.InputError):
            self.k.strict_json(b'['*1100+b'0'+b']'*1100)

    def test_total_fetch_deadline_terminates_blocked_reader(self):
        self.controller.configure(source='https://example.test')
        launch=subprocess.Popen
        for stall in ('proxy','body'):
            with self.subTest(stall=stall),self.https_proxy(response=b'HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nx',stall=stall) as (reached,_):
                workers=[]

                def record(*args,**kwargs):
                    worker=launch(*args,**kwargs)
                    workers.append(worker)
                    return worker

                start=time.monotonic()
                with mock.patch.object(self.k.subprocess,'Popen',side_effect=record):
                    with self.assertRaisesRegex(self.k.NetworkError,'time budget'):
                        self.controller.fetch('https://example.test/release.json',100,deadline=start+0.6)
                self.assertTrue(reached.is_set(),'Fresh worker must reach the blocking network path')
                self.assertLess(time.monotonic()-start,1.5)
                self.assertEqual(1,len(workers))
                self.assertIsNotNone(workers[0].returncode,'Timed-out worker must be reaped')
                self.assertTrue(workers[0].stdin.closed)
                self.assertTrue(workers[0].stdout.closed)

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
        (home/'config.toml').write_text('project_doc_max_bytes = 1536\n')
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
        self.assertEqual(1336,self.controller.status()['budget'])
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

    def test_claude_user_target_uses_explicit_environment_and_default_home(self):
        args=argparse.Namespace(host='claude-code',scope='user',project_root=None,claude_home=None)
        with mock.patch.dict(os.environ, {'HOME':str(self.root),'CLAUDE_CONFIG_DIR':str(self.root/'env-claude')}):
            self.assertEqual(self.root/'env-claude/rules/korean-protocol.md',self.k.host_target(args))
            args.claude_home=self.root/'explicit-claude'
            self.assertEqual(self.root/'explicit-claude/rules/korean-protocol.md',self.k.host_target(args))
        args.claude_home=None
        with mock.patch.dict(os.environ, {'HOME':str(self.root)}, clear=True):
            self.assertEqual(self.root/'.claude/rules/korean-protocol.md',self.k.host_target(args))

    def test_claude_project_target_requires_root_and_ignores_user_home(self):
        args=argparse.Namespace(host='claude-code',scope='project',project_root=self.target.parent)
        self.assertEqual(self.target.parent/'.claude/rules/korean-protocol.md',self.k.host_target(args))
        args.project_root=None
        with self.assertRaises(self.k.InputError):
            self.k.host_target(args)

    def test_claude_install_reinstall_and_uninstall_preserve_rules_and_claude_md(self):
        for scope in ('user','project'):
            with self.subTest(scope=scope):
                home=self.root/('claude-'+scope)
                project=self.root/('repo-'+scope)
                root=home if scope=='user' else project/'.claude'
                (root/'rules').mkdir(parents=True)
                target=root/'rules/korean-protocol.md'
                original=b'# User rule\r\n'
                target.write_bytes(original)
                (root/'rules/other.md').write_bytes(b'Other rule\n')
                claude_md=(home if scope=='user' else project)/'CLAUDE.md'
                claude_md.write_bytes(b'Existing main instructions\n')
                ctrl=self.k.Controller(self.root/('state-'+scope))
                context={'host':'claude-code','scope':scope,'project_root':str(project) if scope=='project' else None,'claude_home':str(home)}
                ctrl.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
                installed=target.read_bytes()
                ctrl.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
                self.assertEqual(installed,target.read_bytes())
                self.assertTrue(installed.startswith(original))
                self.assertFalse(installed.startswith(b'---'))
                self.assertEqual(self.k.MAX_TOTAL_BYTES,ctrl.status()['budget'])
                self.assertEqual('installer-file-safety',ctrl.status()['budget_kind'])
                target.write_bytes(b'# Added outside block\n'+installed)
                ctrl.uninstall()
                self.assertEqual(b'# Added outside block\n'+original,target.read_bytes())
                self.assertEqual(b'Other rule\n',(root/'rules/other.md').read_bytes())
                self.assertEqual(b'Existing main instructions\n',claude_md.read_bytes())

    def test_claude_cli_persists_resolved_config_home_in_isolated_home(self):
        for explicit in (False,True):
            with self.subTest(explicit=explicit):
                home=self.root/('isolated-'+str(explicit))
                home.mkdir()
                state=self.root/('cli-claude-state-'+str(explicit))
                command=[shutil.which('python3'),'-m','runtime.kproto','--state-dir',str(state),'install','--bundle',str(self.bundle),'--local-snapshot','--host','claude-code','--scope','user','--version','0.2.0']
                selected=home/('explicit' if explicit else 'env-config')
                if explicit:
                    command+=['--claude-home',str(selected)]
                with mock.patch.dict(os.environ,{'HOME':str(home),'CLAUDE_CONFIG_DIR':str(home/'env-config')}):
                    result=subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(0,result.returncode,result.stderr)
                record=json.loads((state/'state.json').read_text())
                self.assertEqual('0.2.0',record['version'])
                self.assertEqual(str(selected),record['host_context']['claude_home'])
                self.assertEqual(str(selected/'rules/korean-protocol.md'),record['target'])
                self.assertTrue((selected/'rules/korean-protocol.md').exists())
                self.assertFalse((home/'.claude/CLAUDE.md').exists())

    def test_claude_project_cli_install_and_uninstall_are_isolated_from_home(self):
        home=self.root/'project-isolated-home'
        home.mkdir()
        project=self.root/'isolated-project'
        project.mkdir()
        (project/'CLAUDE.md').write_bytes(b'User project instructions\n')
        state=self.root/'project-cli-state'
        target=project/'.claude/rules/korean-protocol.md'
        command=[shutil.which('python3'),'-B','-m','runtime.kproto','--state-dir',str(state)]
        with mock.patch.dict(os.environ,{'HOME':str(home),'CLAUDE_CONFIG_DIR':str(home/'custom-config')}):
            result=subprocess.run(command+['install','--bundle',str(self.bundle),'--local-snapshot','--host','claude-code','--scope','project','--project-root',str(project),'--version','0.2.0'],capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertTrue(target.exists())
            record=json.loads((state/'state.json').read_text())
            self.assertNotIn('claude_home',record['host_context'])
            result=subprocess.run(command+['uninstall'],capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(b'',target.read_bytes())
        self.assertFalse((home/'custom-config').exists())
        self.assertFalse((home/'.claude').exists())
        self.assertEqual(b'User project instructions\n',(project/'CLAUDE.md').read_bytes())

    def test_claude_project_install_ignores_symlinked_user_config_home(self):
        home=self.root/'project-home'
        home.mkdir()
        outside=self.root/'outside-config'
        outside.mkdir()
        marker=outside/'CLAUDE.md'
        marker.write_bytes(b'Unrelated user instructions\n')
        link=home/'config-link'
        link.symlink_to(outside,target_is_directory=True)
        project=self.root/'safe-project'
        project.mkdir()
        target=project/'.claude/rules/korean-protocol.md'
        state=self.root/'project-symlink-env-state'
        command=[shutil.which('python3'),'-B','-m','runtime.kproto','--state-dir',str(state),'install','--bundle',str(self.bundle),'--local-snapshot','--host','claude-code','--scope','project','--project-root',str(project),'--version','0.2.0']
        with mock.patch.dict(os.environ,{'HOME':str(home),'CLAUDE_CONFIG_DIR':str(link)}):
            result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertTrue(target.exists())
        record=json.loads((state/'state.json').read_text())
        self.assertNotIn('claude_home',record['host_context'])
        ctrl=self.k.Controller(state)
        context={'host':'claude-code','scope':'project','project_root':str(project),'claude_home':str(link)}
        ctrl.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
        self.assertNotIn('claude_home',ctrl.status()['host_context'])
        self.assertEqual(b'Unrelated user instructions\n',marker.read_bytes())
        self.assertFalse((outside/'rules').exists())

    def test_claude_project_install_rejects_symlinked_project_rules(self):
        project=self.root/'linked-project-rules'
        (project/'.claude').mkdir(parents=True)
        outside=self.root/'outside-rules'
        outside.mkdir()
        (project/'.claude/rules').symlink_to(outside,target_is_directory=True)
        args=argparse.Namespace(host='claude-code',scope='project',project_root=project)
        with self.assertRaises(self.k.InputError):
            self.k.host_target(args)
        self.assertFalse((outside/'korean-protocol.md').exists())

    def test_claude_install_rejects_existing_yaml_frontmatter_and_preserves_state(self):
        home=self.root/'frontmatter-claude'
        target=home/'rules/korean-protocol.md'
        target.parent.mkdir(parents=True)
        context={'host':'claude-code','scope':'user','project_root':None,'claude_home':str(home)}
        for index,original in enumerate((b'---\npaths: ["src/**"]\n---\nUser scoped rule\n',
                         b'---\r\npaths: ["src/**"]\r\n---\r\nUser scoped rule\r\n',
                         b'\xef\xbb\xbf---\npaths: ["src/**"]\n---\nUser scoped rule\n',
                         b' \r\n---\npaths: ["src/**"]\n---\nUser scoped rule\n')):
            with self.subTest(original=original):
                target.write_bytes(original)
                ctrl=self.k.Controller(self.root/('frontmatter-state-'+str(index)))
                state_before=ctrl.status()
                with self.assertRaisesRegex(self.k.ConflictError,'frontmatter'):
                    ctrl.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
                self.assertEqual(original,target.read_bytes())
                self.assertEqual(state_before,ctrl.status())

    def test_codex_install_preserves_existing_frontmatter(self):
        original=b'---\npaths: ["src/**"]\n---\nUser instruction\n'
        self.target.write_bytes(original)
        context={'host':'codex','scope':'project','project_root':str(self.target.parent),'codex_home':str(self.root/'codex-home')}
        self.controller.install_snapshot(self.bundle,self.target,'0.2.0',host_context=context)
        self.assertTrue(self.target.read_bytes().startswith(original))

    def test_claude_file_budget_preserves_large_rule_and_refuses_exceeding_installer_bound(self):
        home=self.root/'large-claude'
        target=home/'rules/korean-protocol.md'
        target.parent.mkdir(parents=True)
        original=b'x'*(40*1024)
        target.write_bytes(original)
        context={'host':'claude-code','scope':'user','project_root':None,'claude_home':str(home)}
        self.controller.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
        self.assertTrue(target.read_bytes().startswith(original))
        self.controller.uninstall()
        target.write_bytes(b'x'*(self.k.MAX_TOTAL_BYTES-10))
        before=target.read_bytes()
        with self.assertRaises(self.k.InputError):
            self.controller.install_snapshot(self.bundle,target,'0.2.0',host_context=context)
        self.assertEqual(before,target.read_bytes())

    def test_claude_host_context_freezes_environment_home_before_rollback(self):
        home=self.root/'first-claude'
        target=home/'rules/korean-protocol.md'
        context={'host':'claude-code','scope':'user','project_root':None}
        with mock.patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':str(home)}):
            self.controller.install_snapshot(self.bundle,target,'0.1.0',host_context=context)
        with mock.patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':str(self.root/'different-claude')}):
            self.controller.install_snapshot(self.bundle,target,'0.2.0')
            self.controller.rollback('0.1.0')
        self.assertEqual(str(home),self.controller.status()['host_context']['claude_home'])
        self.assertEqual(str(target),self.controller.status()['target'])
        self.assertFalse((self.root/'different-claude').exists())

    def test_claude_rejects_symlink_home_rules_directory_and_target(self):
        outside=self.root/'outside'
        outside.mkdir()
        for component in ('home','rules','target'):
            with self.subTest(component=component):
                home=self.root/('linked-'+component)
                target=home/'rules/korean-protocol.md'
                if component=='home':
                    home.symlink_to(outside,target_is_directory=True)
                elif component=='rules':
                    home.mkdir()
                    (home/'rules').symlink_to(outside,target_is_directory=True)
                else:
                    target.parent.mkdir(parents=True)
                    other=outside/'user.md'
                    other.write_bytes(b'Untouched\n')
                    target.symlink_to(other)
                args=argparse.Namespace(host='claude-code',scope='user',project_root=None,claude_home=home)
                with self.assertRaises(self.k.InputError):
                    self.controller.install_snapshot(self.bundle,self.k.host_target(args),'0.2.0',host_context=vars(args))
        self.assertEqual(b'Untouched\n',(outside/'user.md').read_bytes())


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

    def test_off_signed_update_rollback_and_restart_preserve_settings_for_both_hosts(self):
        for host in ('codex','claude-code'):
            with self.subTest(host=host):
                ctrl=self.k.Controller(self.root/('signed-controls-'+host))
                public=Path(str(self.key)+'.pub')
                ctrl.trust_key(public,self.k.key_fingerprint(public))
                home=self.root/(host+'-home')
                target=home/('AGENTS.md' if host=='codex' else 'rules/korean-protocol.md')
                target.parent.mkdir(parents=True)
                original=b'# User instructions\r\n'
                target.write_bytes(original)
                context={'host':host,'scope':'user','project_root':None,
                         'codex_home' if host=='codex' else 'claude_home':str(home)}
                self.sign('0.1.0',1)
                ctrl.install_signed(self.bundle,target,host_context=context)
                ctrl.configure(mode='interval',source='https://example.test/kproto')
                config_before=ctrl.config_path.read_bytes()
                ctrl.configure_application(enabled=False,honorifics=True)
                self.assertEqual(config_before,ctrl.config_path.read_bytes())
                target.write_bytes(b'# Later manual instruction\n'+target.read_bytes())
                self.sign('0.2.0',2)
                def download(url,maximum,deadline=None):
                    name=url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1]
                    return (self.bundle/name).read_bytes()
                with mock.patch.object(ctrl,'fetch',side_effect=download):
                    self.assertTrue(ctrl.update(scheduled=True))
                self.assertFalse(ctrl.status()['enabled'])
                self.assertTrue(ctrl.status()['honorifics'])
                self.assertNotIn('뜻과 조건'.encode(),target.read_bytes())
                ctrl.rollback('0.1.0')
                self.assertFalse(ctrl.status()['enabled'])
                restarted=self.k.Controller(ctrl.root)
                restarted.configure_application(enabled=True)
                self.assertEqual(2,restarted.status()['highest_sequence'])
                self.assertEqual('0.1.0',restarted.status()['pin'])
                self.assertIn('~습니다/~ㅂ니다'.encode(),target.read_bytes())
                self.assertTrue(target.read_bytes().startswith(b'# Later manual instruction\n'+original))
                self.sign('0.0.9',1)
                with self.assertRaises(self.k.TrustError):
                    restarted.install_signed(self.bundle,target)

    def test_off_cache_signature_and_key_tamper_cannot_reactivate(self):
        self.sign()
        self.controller.install_signed(self.bundle,self.target)
        self.controller.configure_application(enabled=False)
        cache=self.controller.root/'releases'/self.controller.status()['cache_id']
        before=self.target.read_bytes()
        state_before=self.controller.state_path.read_bytes()
        signature=cache/'release.json.sig'
        original=signature.read_bytes()
        signature.write_bytes(b'invalid signature')
        with self.assertRaises(self.k.TrustError):
            self.controller.configure_application(enabled=True)
        signature.write_bytes(original)
        public=self.controller.root/'trust/public_key'
        original=public.read_bytes()
        other=self.root/'other-key'
        subprocess.run([self.ssh,'-q','-t','ed25519','-N','','-f',str(other)],check=True,capture_output=True)
        public.write_bytes(Path(str(other)+'.pub').read_bytes())
        with self.assertRaises(self.k.TrustError):
            self.controller.configure_application(enabled=True)
        public.write_bytes(original)
        self.assertEqual(before,self.target.read_bytes())
        self.assertEqual(state_before,self.controller.state_path.read_bytes())

    def test_real_signature_verification_rejects_manifest_tampering(self):
        self.sign()
        self.controller.install_signed(self.bundle, self.target)
        installed = self.target.read_bytes()
        self.manifest.write_bytes(self.manifest.read_bytes().replace(b'"version": "0.1.0"',b'"version": "0.2.0"'))
        with self.assertRaises(self.k.TrustError):
            self.controller.install_signed(self.bundle, self.target)
        self.assertEqual(installed,self.target.read_bytes())

    def test_claude_signed_remote_update_and_rollback_keep_recorded_home(self):
        home=self.root/'signed-claude'
        target=home/'rules/korean-protocol.md'
        context={'host':'claude-code','scope':'user','project_root':None}
        self.sign('0.1.0',1)
        with mock.patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':str(home)}):
            self.controller.install_signed(self.bundle,target,host_context=context)
        self.controller.configure(mode='interval',source='https://example.test/kproto')
        (self.bundle/'profiles/coding-agent.md').write_text('업데이트한 규약이다.\n')
        self.sign('0.2.0',2)

        def download(url,maximum,deadline=None):
            name=url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1]
            return (self.bundle/name).read_bytes()

        with mock.patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':str(self.root/'later-claude')}):
            with mock.patch.object(self.controller,'fetch',side_effect=download):
                self.assertTrue(self.controller.update())
            self.assertIn('업데이트한 규약이다.'.encode(),target.read_bytes())
            self.controller.rollback('0.1.0')
        self.assertEqual('signed',self.controller.status()['trust'])
        self.assertEqual(str(home),self.controller.status()['host_context']['claude_home'])
        self.assertIn('뜻과 조건을 유지한다.'.encode(),target.read_bytes())
        self.assertFalse((self.root/'later-claude').exists())

    def test_claude_signed_update_rejects_user_added_frontmatter_and_preserves_state(self):
        home=self.root/'signed-frontmatter-claude'
        target=home/'rules/korean-protocol.md'
        context={'host':'claude-code','scope':'user','project_root':None,'claude_home':str(home)}
        self.sign('0.1.0',1)
        self.controller.install_signed(self.bundle,target,host_context=context)
        self.controller.configure(mode='interval',source='https://example.test/kproto')
        target.write_bytes(b'---\npaths: ["src/**"]\n---\n'+target.read_bytes())
        before=target.read_bytes()
        state_before=self.controller.state_path.read_bytes()
        self.sign('0.2.0',2)

        def download(url,maximum,deadline=None):
            name=url.rsplit('/',1)[1] if '/stable/' in url else url.split('/releases/0.2.0/',1)[1]
            return (self.bundle/name).read_bytes()

        with mock.patch.object(self.controller,'fetch',side_effect=download):
            with self.assertRaisesRegex(self.k.ConflictError,'frontmatter'):
                self.controller.update()
        self.assertEqual(before,target.read_bytes())
        self.assertEqual(state_before,self.controller.state_path.read_bytes())
        self.assertFalse(self.controller.status()['recovery_required'])

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
