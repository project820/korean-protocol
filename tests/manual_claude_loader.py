"""Install into temporary homes and inspect real Claude Code discovery locally.

The local HTTP fixture deliberately rejects requests; it performs no inference.
Only hashes and rule counts are retained, never request headers or raw prompts.
"""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


def run(root, binary):
    root = root.resolve()
    rules = json.loads((root/'specification/rules.json').read_text())['rules']
    profile = (root/'profiles/coding-agent.md').read_bytes()
    report = {'test':'installed Claude Code rules in local fixture requests',
              'model_inference_performed':False,'temporary_environment_only':True,
              'profile_sha256':hashlib.sha256(profile).hexdigest(),
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'rules_sha256':hashlib.sha256((root/'specification/rules.json').read_bytes()).hexdigest(),
              'runtime_sha256':hashlib.sha256((root/'runtime/kproto.py').read_bytes()).hexdigest(),
              'cli_version':subprocess.check_output([str(binary),'--version'],text=True).strip(),
              'records':[]}
    for scope in ('user','project','custom-config-user'):
        captured = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass

            def do_POST(self):
                size = int(self.headers.get('Content-Length','0'))
                if not 0 <= size <= 4*1024*1024:
                    self.send_error(413)
                    return
                raw = self.rfile.read(size)
                if self.path.split('?')[0].endswith('/messages'):
                    captured.append(raw)
                self.send_response(400)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"Local loader fixture: no inference."}}')

        with tempfile.TemporaryDirectory(prefix='kproto claude loader ') as temporary:
            base = Path(temporary).resolve()
            home,project = base/'home',base/'project'
            config = base/'custom-config' if scope=='custom-config-user' else home/'.claude'
            for directory in (home,project,config):
                directory.mkdir(parents=True,exist_ok=True)
            env = {k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR')}
            env.update(HOME=str(home),CLAUDE_CONFIG_DIR=str(config))
            state = base/'state'
            command = [sys.executable,str(root/'runtime/kproto.py'),'--state-dir',str(state),
                       'install','--bundle',str(root),'--host','claude-code',
                       '--scope','project' if scope=='project' else 'user',
                       '--local-snapshot','--version','0.2.0','--autoupdate','off']
            if scope=='project':
                command += ['--project-root',str(project)]
            installed = subprocess.run(command,env=env,cwd=project,capture_output=True,timeout=20)
            if installed.returncode:
                raise RuntimeError('Temporary Claude installation failed: '+str(installed.returncode))
            target = (project/'.claude/rules/korean-protocol.md') if scope=='project' else config/'rules/korean-protocol.md'
            assert profile.rstrip(b'\n') in target.read_bytes()
            server = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            env.update(ANTHROPIC_BASE_URL='http://127.0.0.1:'+str(server.server_port),
                       ANTHROPIC_API_KEY='kproto-local-fixture-only',
                       CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',
                       DISABLE_AUTOUPDATER='1',DISABLE_TELEMETRY='1')
            process = subprocess.Popen([str(binary),'-p','Local loader probe only. Do not use tools.',
                '--model','claude-opus-5-5','--tools','','--max-turns','1',
                '--output-format','json','--setting-sources','user,project',
                '--settings','{"disableAllHooks":true}'],cwd=project,env=env,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                stdout,stderr = process.communicate(timeout=25)
            except subprocess.TimeoutExpired:
                process.terminate()
                stdout,stderr = process.communicate(timeout=5)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            requests = []
            for raw in captured:
                text = json.dumps(json.loads(raw),ensure_ascii=False)
                requests.append({'sha256':hashlib.sha256(raw).hexdigest(),
                    'rule_ids':sum(rule['id'] in text for rule in rules),
                    'requirements':sum(rule['requirement'] in text for rule in rules)})
            report['records'].append({'scope':scope,'install_exit':installed.returncode,
                'cli_exit':process.returncode,'fixture_http_status':400,'requests':requests,
                'stdout_bytes':len(stdout),'stderr_bytes':len(stderr),
                'pass':any(r['rule_ids']==len(rules) and r['requirements']==len(rules) for r in requests)})
    report['result'] = 'pass' if all(r['pass'] for r in report['records']) else 'incomplete'
    report['limitation'] = 'Observed loader requests, not model compliance; HTTP 400 and CLI nonzero are intentional.'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--claude-binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = run(args.runtime_root,args.claude_binary)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'result':result['result'],'scopes':len(result['records'])}))
    sys.exit(0 if result['result']=='pass' else 1)
