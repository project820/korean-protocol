"""Reproduce a temporary localhost HTTPS content update without global changes.

Example:
  python3 tests/manual_https_smoke.py --runtime-root /ABS/INTEGRATED_REPO \
      --port 443 --output docs/distribution/https-smoke.json

Port 443 requires an ordinary unprivileged bind; this script never invokes sudo
or stops an existing listener. Private keys and CA material exist only in a
TemporaryDirectory and are removed on exit. SSL_CERT_FILE is subprocess-local.
Use --via-local-proxy with a Python whose default SSL context honors
SSL_CERT_FILE to test real TLS through an ephemeral loopback CONNECT fixture.
This mode does not prove direct binding to 443 or external release hosting.
"""
import argparse
from datetime import datetime, timezone
import errno
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
import time


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run_smoke(runtime_root, port, via_local_proxy=False):
    runtime_root = runtime_root.resolve()
    runtime_file = runtime_root / 'runtime/kproto.py'
    script_hash = sha256(Path(__file__).read_bytes())
    report = {
        'schema_version': 1,
        'tested_at': datetime.now(timezone.utc).isoformat(),
        'test': 'temporary localhost TLS signed-content CLI update',
        'runtime_root': str(runtime_root),
        'runtime_sha256': sha256(runtime_file.read_bytes()),
        'script_sha256': script_hash,
        'python_version': sys.version.split()[0],
        'python_executable': sys.executable,
        'ssl_version': ssl.OPENSSL_VERSION,
        'transport': {'scheme': 'https', 'host': '127.0.0.1', 'port': port},
        'result': 'blocked',
        'steps': [],
        'scope': {
            'actual_https': False,
            'intended_transport': 'https',
            'temporary_ca_and_signing_keys_only': True,
            'ssl_cert_file_subprocess_only': True,
            'user_trust_store_changed': False,
            'real_user_global_installed': False,
            'launchctl_registered': False,
            'external_endpoint_tested': False,
            'model_compliance_tested': False,
            'private_keys_preserved': False,
        },
    }
    openssl, ssh_keygen = shutil.which('openssl'), shutil.which('ssh-keygen')
    if not openssl or not ssh_keygen:
        report['blocker'] = 'Required installed tool is unavailable: openssl or ssh-keygen'
        return report
    spec = importlib.util.spec_from_file_location('smoke_kproto', runtime_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        random_port=probe.getsockname()[1]
    try:
        module.validate_source('https://127.0.0.1:' + str(random_port))
        report['random_port_preflight']={'port':random_port,'source_validation':'accepted'}
    except module.ProtocolError as error:
        report['random_port_preflight']={'port':random_port,'source_validation':'rejected','exit_code':error.code,'reason':str(error)}
    try:
        module.validate_source('https://127.0.0.1:' + str(port))
    except module.ProtocolError as error:
        report['blocker'] = 'Authoritative source validation rejects the requested HTTPS port'
        report['source_validation_exit'] = error.code
        return report

    requests = []
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            super().do_GET()

    server = None
    server_thread = None
    proxy = None
    proxy_thread = None
    tunnels = []
    with tempfile.TemporaryDirectory(prefix='kproto-https-smoke-') as temporary:
        root = Path(temporary).resolve()
        home, codex_home, state, content = [root/name for name in ('home','codex','state','content')]
        for folder in (home, codex_home, state, content):
            folder.mkdir(mode=0o700)
        try:
            # Bind first, without elevation or modification of an existing socket.
            server = http.server.ThreadingHTTPServer(('127.0.0.1',0 if via_local_proxy else port), functools.partial(Handler,directory=str(content)))
        except OSError as error:
            report['blocker'] = 'Ordinary localhost bind failed; existing listener was not changed'
            report['bind_errno'] = error.errno
            report['bind_error_name'] = errno.errorcode.get(error.errno,'UNKNOWN')
            report['temporary_material_removed'] = True
            return report
        try:
            def checked_tool(args):
                process = subprocess.run(args,capture_output=True,timeout=30)
                if process.returncode:
                    raise RuntimeError(Path(args[0]).name + ' fixture preparation failed with exit ' + str(process.returncode))
                return process.stdout

            pki = root/'pki'
            pki.mkdir(mode=0o700)
            ca_key, ca_cert = pki/'ca.key', pki/'ca.crt'
            server_key, server_csr, server_cert = pki/'server.key', pki/'server.csr', pki/'server.crt'
            ca_config = pki/'ca.cnf'
            ca_config.write_text('[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ca\n[dn]\nCN=Korean Protocol temporary smoke CA\n[ca]\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\n')
            server_config = pki/'server.cnf'
            server_config.write_text('[req]\nprompt=no\ndistinguished_name=dn\nreq_extensions=server\n[dn]\nCN=localhost\n[server]\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n')
            checked_tool([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(ca_key),'-out',str(ca_cert),'-config',str(ca_config)])
            checked_tool([openssl,'req','-new','-newkey','rsa:2048','-nodes','-keyout',str(server_key),'-out',str(server_csr),'-config',str(server_config)])
            checked_tool([openssl,'x509','-req','-in',str(server_csr),'-CA',str(ca_cert),'-CAkey',str(ca_key),'-CAcreateserial','-days','1','-out',str(server_cert),'-extfile',str(server_config),'-extensions','server'])
            other_ca = pki/'unrelated-ca.crt'
            checked_tool([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(pki/'unrelated-ca.key'),'-out',str(other_ca),'-config',str(ca_config)])
            report['ca_certificate_sha256'] = sha256(ca_cert.read_bytes())
            report['server_certificate_sha256'] = sha256(server_cert.read_bytes())

            signing_key = root/'fixture-signing-key'
            checked_tool([ssh_keygen,'-q','-t','ed25519','-N','','-f',str(signing_key)])
            public_key = Path(str(signing_key)+'.pub')
            fingerprint = module.key_fingerprint(public_key)
            report['signer_fingerprint'] = fingerprint
            bundles = {}
            for version, sequence in [('0.2.0',1),('0.2.1',2)]:
                bundle = content/'releases'/version
                bundle.mkdir(parents=True)
                for name in module.CONTENT_PATHS:
                    destination = bundle/name
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes((runtime_root/name).read_bytes())
                if sequence==2:
                    with (bundle/'pack/protocol.md').open('ab') as output:
                        output.write(b'\n<!-- Local HTTPS smoke fixture 0.2.1; not a published release. -->\n')
                manifest = module.make_manifest(bundle,version,sequence,fingerprint)
                manifest_bytes = module.json_bytes(manifest)
                (bundle/'release.json').write_bytes(manifest_bytes)
                signature = subprocess.run([ssh_keygen,'-Y','sign','-f',str(signing_key),'-n','kproto-release-v1'],input=manifest_bytes,capture_output=True,timeout=10)
                if signature.returncode:
                    raise RuntimeError('Temporary release signing failed')
                (bundle/'release.json.sig').write_bytes(signature.stdout)
                bundles[version] = bundle
                report.setdefault('releases',{})[version] = {
                    'sequence':sequence,
                    'manifest_sha256':sha256(manifest_bytes),
                    'files':{item['path']:{'sha256':item['sha256'],'bytes':item['size']} for item in manifest['files']},
                    'fixture_only':True,
                }
            stable = content/'stable'
            stable.mkdir()
            for name in ('release.json','release.json.sig'):
                (stable/name).write_bytes((bundles['0.2.1']/name).read_bytes())
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(str(server_cert),str(server_key))
            server.socket = tls.wrap_socket(server.socket,server_side=True)
            server_thread = threading.Thread(target=server.serve_forever,daemon=True)
            server_thread.start()
            source = 'https://127.0.0.1:' + str(port)
            if via_local_proxy:
                # This fixture transports encrypted TLS bytes; the production
                # downloader still verifies https://localhost:443 normally.
                tls_port = server.server_address[1]

                class TunnelHandler(http.server.BaseHTTPRequestHandler):
                    def setup(self):
                        super().setup()
                        self.connection.settimeout(5)

                    def log_message(self, fmt, *args):
                        pass

                    def do_CONNECT(self):
                        if self.path != 'localhost:443':
                            self.send_error(403)
                            return
                        tunnels.append(self.path)
                        try:
                            with socket.create_connection(('127.0.0.1',tls_port),timeout=5) as upstream:
                                self.send_response(200,'Connection established')
                                self.end_headers()
                                peers = (self.connection,upstream)
                                deadline = time.monotonic()+30
                                for peer in peers:
                                    peer.settimeout(5)
                                while time.monotonic()<deadline:
                                    readable,_,_ = select.select(peers,[],[],5)
                                    if not readable:
                                        return
                                    for incoming in readable:
                                        data = incoming.recv(65536)
                                        if not data:
                                            return
                                        outgoing = upstream if incoming is self.connection else self.connection
                                        outgoing.sendall(data)
                        except OSError:
                            # Closed connections are expected in negative TLS
                            # and server-offline checks. Never forward elsewhere.
                            return

                proxy = http.server.ThreadingHTTPServer(('127.0.0.1',0),TunnelHandler)
                proxy_thread = threading.Thread(target=proxy.serve_forever,daemon=True)
                proxy_thread.start()
                # The fixture must not be an unrestricted forwarding proxy.
                rejected = http.client.HTTPConnection('127.0.0.1',proxy.server_address[1],timeout=5)
                try:
                    rejected.request('CONNECT','elsewhere.invalid:443')
                    response = rejected.getresponse()
                    report['proxy_rejects_other_authority'] = response.status == 403
                    response.read()
                finally:
                    rejected.close()
                if not report['proxy_rejects_other_authority'] or tunnels:
                    raise RuntimeError('Local proxy did not reject a foreign authority')
                source = 'https://localhost:443'
                report['transport'] = {
                    'scheme':'https','host':'localhost','port':443,
                    'via_local_connect_proxy':True,
                    'proxy_listener_port':proxy.server_address[1],
                    'tls_listener_port':tls_port,
                    'direct_port_443_bind_tested':False,
                }
            original = '사용자의 기존 승인 정책을 유지한다.\n'.encode('utf-8')
            target = codex_home/'AGENTS.md'
            target.write_bytes(original)
            env = dict(os.environ,HOME=str(home),CODEX_HOME=str(codex_home),SSL_CERT_FILE=str(ca_cert))
            env['NO_PROXY'] = '127.0.0.1,localhost'
            env['no_proxy'] = env['NO_PROXY']
            if via_local_proxy:
                proxy_url = 'http://127.0.0.1:' + str(proxy.server_address[1])
                env.pop('ALL_PROXY',None)
                env.pop('all_proxy',None)
                env.update(HTTPS_PROXY=proxy_url,https_proxy=proxy_url,
                           NO_PROXY='unused.invalid',no_proxy='unused.invalid')

            def cli(label,args,expected=0,environment=env,state_root=state):
                process = subprocess.run([sys.executable,'-m','runtime.kproto','--state-dir',str(state_root)]+args,cwd=str(runtime_root),env=environment,capture_output=True,timeout=75)
                entry = {'step':label,'exit_code':process.returncode,'expected_exit_code':expected,'stdout_bytes':len(process.stdout),'stderr_bytes':len(process.stderr)}
                report['steps'].append(entry)
                if process.returncode!=expected:
                    raise RuntimeError(label+' returned exit '+str(process.returncode)+' instead of '+str(expected))
                return process.stdout

            cli('signed-install-local-bundle',['install','--bundle',str(bundles['0.2.0']),'--host','codex','--scope','user','--codex-home',str(codex_home),'--trust-key',str(public_key),'--expected-fingerprint',fingerprint])
            initial = json.loads(cli('initial-status',['status','--json']))
            if initial['version']!='0.2.0' or initial['trust']!='signed':
                raise RuntimeError('Initial signed state was not installed')
            cli('configure-source',['autoupdate','configure','--mode','interval','--source',source])

            # A trusted leaf is required; first prove an unrelated CA fails safely.
            unrelated = dict(env,SSL_CERT_FILE=str(server_config))
            before_failed = target.read_bytes()
            before_gets = len(requests)
            cli('reject-invalid-ca-file',['update'],expected=3,environment=unrelated)
            if target.read_bytes()!=before_failed or len(requests)!=before_gets:
                raise RuntimeError('Untrusted TLS changed active profile')
            cli('reject-valid-unrelated-ca',['update'],expected=3,
                environment=dict(env,SSL_CERT_FILE=str(other_ca)))
            if target.read_bytes()!=before_failed or len(requests)!=before_gets:
                raise RuntimeError('Unrelated CA allowed HTTP or changed active profile')
            report['negative_tls_requests_reached_http'] = len(requests)-before_gets
            cli('actual-https-update',['update'])
            report['scope']['actual_https']=True
            updated = json.loads(cli('updated-status',['status','--json']))
            if updated['version']!='0.2.1' or updated['highest_sequence']!=2 or updated['trust']!='signed':
                raise RuntimeError('HTTPS update did not activate authenticated version 0.2.1')
            installed = target.read_bytes()
            if not installed.startswith(original):
                raise RuntimeError('Installer changed original user instructions')
            advertised = re.findall(r'^전체 규칙·사전: (.+)$',installed.decode('utf-8'),re.MULTILINE)
            if len(advertised)!=1:
                raise RuntimeError('Installed profile did not advertise one cache root')
            cache = Path(advertised[0])
            expected_cache = state/'releases'/updated['cache_id']
            locators = {}
            for name in ('lexicon/core.json','lexicon/domains/software.json'):
                path = cache/name
                locators[name] = {'exists':path.is_file(),'sha256':sha256(path.read_bytes()),'manifest_sha256_matches':sha256(path.read_bytes())==report['releases']['0.2.1']['files'][name]['sha256'],'absolute_file_locator_in_body':str(path) in installed.decode('utf-8')}
            if not cache.is_absolute() or cache!=expected_cache or not all(item['exists'] and item['manifest_sha256_matches'] for item in locators.values()):
                raise RuntimeError('Advertised cache root did not resolve controlled dictionaries')
            report['dictionary_locator'] = {
                'render_function':'Controller._activate',
                'render_behavior':'Full profile body plus absolute cache directory footer; relative dictionary names resolve against that advertised cache root.',
                'absolute_cache_directory_advertised':True,
                'advertised_root_matches_active_cache':True,
                'files':locators,
                'model_file_read_observed':False,
            }
            report['initial_version'] = initial['version']
            report['updated_version'] = updated['version']
            report['highest_sequence'] = updated['highest_sequence']
            report['installed_profile_sha256'] = sha256(installed)
            report['original_user_bytes_preserved'] = True

            signature_path = stable/'release.json.sig'
            valid_signature = signature_path.read_bytes()
            signature_path.write_bytes(b'invalid smoke signature\n')
            try:
                cli('reject-invalid-release-signature-over-https',['update'],expected=5)
                if target.read_bytes()!=installed:
                    raise RuntimeError('Invalid release signature changed active profile')
            finally:
                signature_path.write_bytes(valid_signature)

            # A fresh installation has no retry backoff from negative tests.
            # Let the normal host wrapper trigger the first automatic update.
            auto_state, auto_home = root/'auto-state', root/'auto-codex'
            auto_state.mkdir(mode=0o700)
            auto_home.mkdir(mode=0o700)
            cli('auto-install-initial',['install','--bundle',str(bundles['0.2.0']),
                '--host','codex','--scope','user','--codex-home',str(auto_home),
                '--trust-key',str(public_key),'--expected-fingerprint',fingerprint],state_root=auto_state)
            cli('auto-configure',['autoupdate','configure','--mode','interval','--source',source],state_root=auto_state)
            before_auto_gets = len(requests)
            cli('wrapper-triggered-https-update',['run','--',sys.executable,'-c','raise SystemExit(0)'],state_root=auto_state)
            automatic = json.loads(cli('auto-updated-status',['status','--json'],state_root=auto_state))
            if automatic['version']!='0.2.1' or len(requests)<=before_auto_gets:
                raise RuntimeError('Host wrapper did not trigger the authenticated HTTPS update')
            report['automatic_update'] = {'trigger':'run host wrapper','version':automatic['version'],
                'trust':automatic['trust'],'new_http_requests':len(requests)-before_auto_gets,
                'host_exit':0,'scheduler_registered':False}

            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)
            server = None
            cli('offline-update-fails-safely',['update'],expected=3)
            offline = json.loads(cli('offline-status',['status','--json']))
            if offline['version']!='0.2.1' or target.read_bytes()!=installed:
                raise RuntimeError('Offline update changed last known good profile')
            cli('disable-autoupdate',['autoupdate','configure','--mode','off'])
            cli('offline-wrapper-local-host',['run','--',sys.executable,'-c','raise SystemExit(0)'])
            report['offline'] = {'server_stopped':True,'version':offline['version'],'installed_profile_unchanged':True,'cached_dictionaries_still_readable':all((cache/name).is_file() for name in locators),'wrapper_host_exit':0}
            report['requests'] = requests
            if via_local_proxy:
                report['connect_tunnels'] = tunnels
                if not tunnels:
                    raise RuntimeError('Local CONNECT transport was not exercised')
            report['runtime_unchanged_during_smoke'] = sha256(runtime_file.read_bytes())==report['runtime_sha256']
            if not report['runtime_unchanged_during_smoke']:
                raise RuntimeError('Authoritative runtime changed during smoke; repeat on a stable snapshot')
            report['result'] = 'pass'
        except (RuntimeError,subprocess.SubprocessError,OSError,ValueError,module.ProtocolError) as error:
            report['result'] = 'failed'
            report['failure'] = str(error)
        finally:
            report['requests'] = list(requests)
            report['connect_tunnels'] = list(tunnels)
            if proxy is not None:
                proxy.shutdown()
                proxy.server_close()
                if proxy_thread is not None:
                    proxy_thread.join(timeout=2)
            if server is not None:
                if server_thread is not None:
                    server.shutdown()
                    server_thread.join(timeout=2)
                server.server_close()
    report['temporary_material_removed'] = True
    report['limitation'] = 'Localhost TLS and CLI wiring only; no public release endpoint, launchd registration, real user installation or model compliance validation.'
    return report


def snapshot_locator_check(runtime_root):
    """Inspect the real installed profile even when TLS prerequisites are blocked."""
    runtime_root=runtime_root.resolve()
    result={'transport':'none','trust':'local-snapshot','actual_https':False,'model_file_read_observed':False}
    source=(runtime_root/'runtime/kproto.py').read_text()
    result['render_function']='Controller._activate'
    result['render_line']=next(index for index,line in enumerate(source.splitlines(),1) if '전체 규칙·사전: ' in line)
    with tempfile.TemporaryDirectory(prefix='kproto-locator-smoke-') as temporary:
        root=Path(temporary).resolve()
        home,codex_home,state=[root/name for name in ('home','codex','state')]
        for path in (home,codex_home,state):
            path.mkdir(mode=0o700)
        target=codex_home/'AGENTS.md'
        original='사용자의 기존 승인 정책을 유지한다.\n'.encode('utf-8')
        target.write_bytes(original)
        env=dict(os.environ,HOME=str(home),CODEX_HOME=str(codex_home))
        command=[sys.executable,'-m','runtime.kproto','--state-dir',str(state)]
        install=subprocess.run(command+['install','--bundle',str(runtime_root),'--host','codex','--scope','user','--codex-home',str(codex_home),'--local-snapshot','--version','0.2.0'],cwd=str(runtime_root),env=env,capture_output=True,timeout=30)
        result['install_exit_code']=install.returncode
        if install.returncode:
            result['result']='failed'
            return result
        status=subprocess.run(command+['status','--json'],cwd=str(runtime_root),env=env,capture_output=True,timeout=15)
        result['status_exit_code']=status.returncode
        if status.returncode:
            result['result']='failed'
            return result
        active=json.loads(status.stdout)
        installed=target.read_bytes()
        advertised=re.findall(r'^전체 규칙·사전: (.+)$',installed.decode('utf-8'),re.MULTILINE)
        result['absolute_cache_directory_advertised']=len(advertised)==1 and Path(advertised[0]).is_absolute()
        if not result['absolute_cache_directory_advertised']:
            result['result']='failed'
            return result
        cache=Path(advertised[0])
        result['advertised_root_matches_active_cache']=cache==state/'releases'/active['cache_id']
        result['installed_version']=active['version']
        result['original_user_bytes_preserved']=installed.startswith(original)
        result['installed_profile_sha256']=sha256(installed)
        files={}
        for name in ('lexicon/core.json','lexicon/domains/software.json'):
            resolved=cache/name
            files[name]={'cached_file_exists':resolved.is_file(),'source_sha256':sha256((runtime_root/name).read_bytes()),'cached_sha256':sha256(resolved.read_bytes()),'explicit_absolute_file_locator_in_body':str(resolved) in installed.decode('utf-8')}
            files[name]['source_hash_matches_cache']=files[name]['source_sha256']==files[name]['cached_sha256']
        result['files']=files
        result['result']='pass' if result['advertised_root_matches_active_cache'] and result['original_user_bytes_preserved'] and all(item['cached_file_exists'] and item['source_hash_matches_cache'] for item in files.values()) else 'failed'
        result['locator_contract']='Relative lexicon/core.json and lexicon/domains/software.json resolve against the footer-advertised absolute cache directory; file-specific absolute locators are not inserted.'
    result['temporary_material_removed']=True
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--port',type=int,default=443)
    parser.add_argument('--via-local-proxy',action='store_true',help='Use an ephemeral loopback CONNECT fixture for https://localhost:443 without a privileged listener')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=run_smoke(args.runtime_root,args.port,args.via_local_proxy)
    report['dictionary_locator_local_snapshot']=snapshot_locator_check(args.runtime_root)
    if report['result']=='blocked':
        report['main_https_branches']='not executed because prerequisite bind failed; script syntax and independent locator branch were checked only'
    compile(Path(__file__).read_text(),str(Path(__file__)),'exec')
    report['script_validation']={'python_compile':'pass','actual_https_branch_executed':report['scope']['actual_https']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'result':report['result'],'output':str(args.output.resolve()),'steps':len(report['steps']),'blocker':report.get('blocker'),'failure':report.get('failure')},ensure_ascii=False))
    return 0 if report['result']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
