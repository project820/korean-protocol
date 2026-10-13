import argparse,datetime,hashlib,importlib.util,json,os,subprocess,sys,tempfile,threading,http.server
from pathlib import Path
REPO=Path('/Users/m5max/.codex/worktrees/editing-information/ASD-STE100 Kor')
OUT=REPO/'evaluation/release-0.3.0-20261013'
SOURCE='https://project820.github.io/korean-protocol'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path); obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
m=load(REPO/'runtime/kproto.py','public_runtime');smoke=load(REPO/'tests/manual_https_smoke.py','public_smoke');candidate=load(REPO/'tests/manual_candidate_upgrade_smoke.py','public_candidate')
def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def save(path,obj):
 with path.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def cmd(hr,env,label,argv,expected=0,parse=True):
 p=subprocess.run(argv,env=env,cwd=REPO,capture_output=True,timeout=90)
 hr['steps'].append({'step':label,'argv':argv,'exit_code':p.returncode,'expected_exit_code':expected,'stdout_bytes':len(p.stdout),'stderr_bytes':len(p.stderr)})
 require(p.returncode==expected,label+': '+str(p.returncode)+' '+p.stderr.decode(errors='replace'))
 return json.loads(p.stdout) if parse and p.stdout.strip() else None
def env_for(h):
 e=dict(os.environ,HOME=h['home'],CODEX_HOME=h['host_home'],CLAUDE_CONFIG_DIR=h['host_home'],PYTHONDONTWRITEBYTECODE='1')
 return e

def prepare():
 base=Path(tempfile.mkdtemp(prefix='kproto-public-upgrade-030-')).resolve()
 report={'schema_version':1,'test':'actual public production-signed 0.2.0 to 0.3.0 upgrade under current runtime/helper','phase':'baseline-ready','tested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'temporary_root':str(base),'public_source':SOURCE,'python_executable':sys.executable,'python_version':sys.version,'hosts':{},'scope':{'production_private_key_read':False,'TEST_resigning':False,'global_configuration_changed':False,'global_trust_store_changed':False,'scheduler_registered':False,'real_model_invocation':False},'code_sha256':{n:sha((REPO/n).read_bytes()) for n in ['runtime/kproto.py','distribution/agent_install.py','tests/manual_https_smoke.py','tests/manual_candidate_upgrade_smoke.py']}}
 report['candidate_source_sha256']={n:sha(b) for n,b in m.content_files(REPO).items()}
 baseline,files,key,fp,payload=candidate.authenticated_public(m,smoke,REPO,base/'authenticated-public-020')
 require(baseline['sequence']==1,'Unexpected baseline sequence')
 report['baseline']={'version':baseline['version'],'sequence':baseline['sequence'],'fingerprint':fp,'public_key_sha256':sha(key.read_bytes()),'manifest_sha256':sha(payload['stable/release.json']),'signature_sha256':sha(payload['stable/release.json.sig']),'content_sha256':{n:sha(b) for n,b in files.items()},'authentication':'Pinned production SSHSIG verified and seven signed file sizes/hashes/schema/version checked','capture':str(base/'authenticated-public-020')}
 for host in ['codex','claude-code']:
  root=base/host;home=root/'home';hh=root/'host-home';state=root/'state';home.mkdir(parents=True);hh.mkdir()
  target=hh/('AGENTS.md' if host=='codex' else 'rules/korean-protocol.md');target.parent.mkdir(parents=True,exist_ok=True)
  original='사용자의 기존 승인 정책을 유지한다.\r\n# Local user rules\r\n'.encode();suffix=b'\r\n# User appendix after installation\r\n';target.write_bytes(original)
  hr={'home':str(home),'host_home':str(hh),'state':str(state),'target':str(target),'steps':[],'original_hex':original.hex(),'suffix_hex':suffix.hex()};report['hosts'][host]=hr;e=env_for(hr)
  common=['--host',host,'--state-dir',str(state),'--codex-home' if host=='codex' else '--claude-home',str(hh)]
  installed=cmd(hr,e,'public-0.2.0-HTTPS-install',[sys.executable,'-B',str(REPO/'distribution/agent_install.py'),'install']+common+['--source',SOURCE,'--trust-key',str(key),'--expected-fingerprint',fp,'--autoupdate','interval'])
  require(installed['version']=='0.2.0' and installed['highest_sequence']==1 and installed['verified'],'Baseline install not verified seq 1')
  hr['installed']=installed; manager=installed['management_argv'];durable=Path(manager['status'][2]).parent
  hr['persistent_code_sha256']={n:sha((durable/n).read_bytes()) for n in ['runtime/kproto.py','agent-install.py']}
  require(hr['persistent_code_sha256']['runtime/kproto.py']==report['code_sha256']['runtime/kproto.py'] and hr['persistent_code_sha256']['agent-install.py']==report['code_sha256']['distribution/agent_install.py'],'Copied runtime/helper differs')
  target.write_bytes(target.read_bytes()+suffix)
  status=cmd(hr,e,'controls-OFF-honorifics-ON',manager['configure']+['--protocol','off','--honorifics','on'])
  require(not status['enabled'] and status['honorifics'] and status['content_verified'],'Controls failed')
  cache=state/'releases'/status['cache_id'];require(all((cache/n).read_bytes()==b for n,b in files.items()),'Baseline cache differs from authenticated capture')
  require(candidate.outside_managed(m,target.read_bytes())==original+suffix,'User bytes changed during prepare')
  hr['baseline_status']=status;hr['OFF_sha256']=sha(target.read_bytes());hr['user_sha256']=sha(original+suffix)
  hr['baseline_ready']=True
 save(base/'context.json',report);save(OUT/'public-upgrade-baseline.json',report)
 print(json.dumps({'result':'ready','context':str(base/'context.json'),'baseline':'0.2.0','sequence':1,'hosts':list(report['hosts'])}))

def finish(context_path):
 report=json.loads(context_path.read_text());base=Path(report['temporary_root']);report['phase']='public-upgrade';report['upgrade_tested_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();report['result']='failed'
 report['scope']['public_production_upgrade']=True
 report['scope']['original_0_2_executable_migration']=False
 diag=[Path('/Users/m5max/Library/Logs/DiagnosticReports'),Path('/Library/Logs/DiagnosticReports')]
 before,unavailable=candidate.crash_snapshot(diag)
 try:
  require(all(sha((REPO/n).read_bytes())==v for n,v in report['code_sha256'].items()),'Current runtime/helper/source scripts changed after baseline prepare')
  source=m.content_files(REPO);require({n:sha(b) for n,b in source.items()}==report['candidate_source_sha256'],'Candidate source changed after prepare')
  key,fp=smoke.publisher_trust(m,REPO,None,None);require(fp==report['baseline']['fingerprint'] and sha(key.read_bytes())==report['baseline']['public_key_sha256'],'Publisher public key changed')
  raw=m.download_worker(SOURCE+'/stable/release.json',{},65536);require(raw[:1]==b'\x01','Public 0.3 manifest download failed')
  manifest=m.validate_manifest(m.strict_json(raw[1:]));require(manifest['version']=='0.3.0' and manifest['sequence']==2,'Public stable is not 0.3.0 seq 2')
  payload={'stable/release.json':raw[1:]}
  for name,limit in [('stable/release.json.sig',16384)]+[('releases/0.3.0/'+item['path'],item['size']) for item in manifest['files']]:
   value=m.download_worker(SOURCE+'/'+name,{},limit);require(value[:1]==b'\x01','Public capture failed: '+name);payload[name]=value[1:]
  capture=base/'authenticated-public-030';candidate.write_files(capture,payload);verified,captured=smoke.load_signed_static(m,capture,key,fp);require(captured==payload,'Authentication capture changed')
  files={n:payload['releases/0.3.0/'+n] for n in m.CONTENT_PATHS};require(files==source,'Public 0.3.0 bytes differ from candidate source')
  for n in ['release.json','release.json.sig']:
   with (OUT/('public-upgrade-0.3.0-'+n)).open('xb') as f:f.write(payload['stable/'+n])
  report['target']={'source':SOURCE,'version':'0.3.0','sequence':2,'fingerprint':fp,'manifest_sha256':sha(payload['stable/release.json']),'signature_sha256':sha(payload['stable/release.json.sig']),'content_sha256':{n:sha(b) for n,b in files.items()},'authentication':'Pinned production SSHSIG verified; seven files checked for exact signed size/hash/schema/version','public_bytes_exactly_candidate':True}
  offline_connects=[]
  class Deny(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_CONNECT(self):
    offline_connects.append(self.path);self.send_error(502,'Test endpoint unavailable')
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Deny);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for host,hr in report['hosts'].items():
    env=env_for(hr);installed=hr['installed'];manager=installed['management_argv'];target=Path(hr['target']);state=Path(hr['state']);user=bytes.fromhex(hr['original_hex'])+bytes.fromhex(hr['suffix_hex']);disabled=target.read_bytes()
    require(sha(disabled)==hr['OFF_sha256'],'Prepared OFF profile changed before upgrade')
    cmd(hr,env,'actual-public-production-HTTPS-update-while-OFF',installed['runtime_argv']['update'])
    updated=cmd(hr,env,'public-0.3-status-while-OFF',manager['status'])
    require(updated['version']=='0.3.0' and updated['highest_sequence']==2 and updated['trust']=='signed' and updated['content_verified'],'Public upgrade failed authentication/version/sequence')
    require(not updated['enabled'] and updated['honorifics'] and target.read_bytes()==disabled,'OFF/honorific setting or profile changed during upgrade')
    cache=state/'releases'/updated['cache_id'];require(all((cache/n).read_bytes()==b for n,b in files.items()),'Public cache differs from exact candidate bytes')
    cache_before=smoke.static_files(m,cache);require(cache_before['release.json']==payload['stable/release.json'] and cache_before['release.json.sig']==payload['stable/release.json.sig'],'Cache differs from public manifest/signature')
    hr['upgrade']={'from_version':'0.2.0','from_sequence':1,'to_version':'0.3.0','highest_sequence':2,'public_source':updated.get('source'),'OFF_survived':True,'honorifics_survived':True,'OFF_profile_unchanged':True,'all_seven_cached_files_match_source':True,'cached_manifest_signature_match_public':True,'cache_id':updated['cache_id'],'cache_sha256':{n:sha(b) for n,b in cache_before.items()}}
    enabled=cmd(hr,env,'ON-inject-public-0.3-verified-profile',manager['protocol_on']);active=target.read_bytes()
    require(enabled['verified'] and enabled['enabled'] and enabled['honorifics'] and candidate.outside_managed(m,active)==user,'ON verification/controls/user bytes failed')
    require(files['profiles/coding-agent.md'].rstrip(b'\n') in active and ('전체 규칙·사전: '+str(cache)).encode() in active and m.speech_overlay(True) in active,'ON lacks current complete public profile/cache/honorific overlay')
    cmd(hr,env,'honorifics-OFF',manager['honorifics_off']);require(m.speech_overlay(False) in target.read_bytes(),'Plain overlay missing')
    cmd(hr,env,'honorifics-ON',manager['honorifics_on']);require(target.read_bytes()==active,'Honorific roundtrip profile differs')
    hr['ON']={'complete_current_profile_injected':True,'honorific_both_options_verified':True,'user_prefix_suffix_preserved':True,'installed_profile_sha256':sha(active)}
    offline=dict(env,HTTPS_PROXY='http://127.0.0.1:'+str(server.server_address[1]),https_proxy='http://127.0.0.1:'+str(server.server_address[1]),NO_PROXY='unused.invalid',no_proxy='unused.invalid');offline.pop('ALL_PROXY',None);offline.pop('all_proxy',None);before_connects=len(offline_connects)
    cmd(hr,offline,'offline-public-update-fails-safely',installed['runtime_argv']['update'],expected=3)
    require(len(offline_connects)>before_connects and all(v=='project820.github.io:443' for v in offline_connects[before_connects:]),'Offline update did not reach restricted refusal proxy for original public authority')
    status=cmd(hr,offline,'offline-verified-status',manager['status']);require(status['version']=='0.3.0' and status['highest_sequence']==2 and status['verified'] and status['enabled'] and status['honorifics'],'Offline status lost verified state/settings')
    require(target.read_bytes()==active and smoke.static_files(m,cache)==cache_before,'Offline failure changed cached signed content or installed profile')
    cmd(hr,offline,'offline-wrapper-host-command',installed['runtime_argv']['run']+['--',sys.executable,'-c','raise SystemExit(0)'],parse=False)
    require(target.read_bytes()==active and smoke.static_files(m,cache)==cache_before,'Offline wrapper changed last verified profile/cache')
    hr['offline']={'network_failure_exit':3,'original_public_source_preserved':True,'proxy_refused_authorities':offline_connects[before_connects:],'last_verified_profile_cache_preserved':True,'all_seven_files_readable':True,'wrapper_host_exit':0}
    cmd(hr,env,'uninstall-restores-exact-user-bytes',manager['uninstall']);require(target.read_bytes()==user,'Uninstall altered user prefix/suffix')
    hr['uninstall']={'restored_exact_user_bytes':True,'user_sha256':sha(target.read_bytes())};hr['result']='pass'
  finally:
   server.shutdown();server.server_close();thread.join(timeout=2)
  require(m.content_files(REPO)==source,'Candidate source changed during live upgrade')
  require(all(sha((REPO/n).read_bytes())==v for n,v in report['code_sha256'].items()),'Current code changed during upgrade')
  after,unavailable_after=candidate.crash_snapshot(diag);new=sorted(n for n,info in after.items() if before.get(n)!=info)
  report['python_crash_report_check']={'contents_read':False,'new_or_changed_python_reports':new,'unavailable_directories':sorted(set(unavailable+unavailable_after)),'limitation':'Immediate filename/stat check does not exclude delayed macOS report generation'}
  require(not new,'New Python crash report observed')
  report['source_and_code_unchanged_during_smoke']=True;report['result']='pass'
 except Exception as error:
  report['failure']=str(error)
 report['limitations']=['Current runtime/helper installation only; original 0.2 runtime/helper migration is separate evidence.','No real Codex/Claude model invocation, login, scheduler registration or sleep/wake.','Offline failure used subprocess-only localhost CONNECT refusal without changing source, global proxy, or trust store.']
 if report['result']=='pass':
  import shutil
  shutil.rmtree(base);report['temporary_material_removed']=not base.exists()
 else:report['temporary_material_removed']=False
 report['driver_sha256']=sha(Path(__file__).read_bytes())
 save(OUT/'public-upgrade-result.json',report)
 (OUT/'public-upgrade-driver.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({'result':report['result'],'output':str(OUT/'public-upgrade-result.json'),'failure':report.get('failure')},ensure_ascii=False))
 return 0 if report['result']=='pass' else 1

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','finish']);p.add_argument('--context',type=Path);a=p.parse_args()
 if a.phase=='prepare':prepare()
 else:raise SystemExit(finish(a.context))
