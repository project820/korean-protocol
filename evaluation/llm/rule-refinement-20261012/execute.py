#!/usr/bin/env python3
import argparse,datetime,hashlib,importlib.util,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUNNER=ROOT.parent/'runner.py'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
parser=argparse.ArgumentParser();parser.add_argument('--call',type=int,choices=(1,2,3,4),required=True);args=parser.parse_args()
manifest=json.loads((ROOT/'freeze-manifest.json').read_text())
for name,expected in manifest['frozen_sha256'].items():
 assert sha(ROOT/name)==expected,(name,'frozen artifact changed')
assert sha(RUNNER)==manifest['runner_sha256'],'existing runner changed'
spec=importlib.util.spec_from_file_location('real_runner',RUNNER);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
entry=manifest['calls'][args.call-1]
ledger=ROOT/f"attempt-{args.call:02d}.json"
with ledger.open('x') as f:
 json.dump({'call':args.call,'entry':entry,'attempt_started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixed_attempt_count_limit':4},f,ensure_ascii=False,indent=2)
case_file=ROOT/entry['gold'];cases=r.load_cases(case_file)
prompt=(ROOT/entry['prompt']).read_text()
r.build_prompt=lambda _:prompt
r.build_generation_prompt=lambda _:prompt
run_dir=ROOT/entry['directory']
print(json.dumps({'event':'starting_actual_call','call':args.call,'directory':str(run_dir),'case_count':len(cases),'requested_model':'gpt-6.1-sol','effort':'high'}),flush=True)
meta,parsed=r.run_condition(entry['condition'],cases,ROOT/'frozen-profile.md' if entry['condition']=='treatment' else None,run_dir,Path('/Users/m5max/.codex/auth.json'),600,mode=entry['mode'])
meta['environment_metadata']={'inherited_CODEX_overrides_removed':True,'CODEX_HOME':'temporary isolated directory, auth.json symlink only','temporary_project':True,'sandbox':'read-only','ignore_user_config':True,'ignore_rules':True,'ephemeral':True,'auth_contents_recorded':False,'environment_values_not_recorded':True}
meta['artifact_sha256']={p.name:sha(p) for p in run_dir.iterdir() if p.is_file() and p.name!='metadata.json'}
r.save_json(run_dir/'metadata.json',meta)
packet=[]
index={x.get('id'):x for x in parsed['results'] if isinstance(x,dict)}
for c in cases: packet.append({'case':c,'actual_output':index.get(c['id']),'semantic_rating':None})
save(ROOT/(entry['directory']+'-review-packet.json'),{'scope':entry['scope'],'condition':entry['condition'],'structure':{'valid':parsed['structure_valid'],'errors':parsed['errors']},'cases':packet,'overall_accuracy':None})
print(json.dumps({'event':'finished_actual_call','call':args.call,'exit_code':meta['exit_code'],'timeout':meta['timeout'],'launch_error':meta['launch_error'],'structure_valid':parsed['structure_valid'],'errors':parsed['errors'],'final_sha256':meta['artifact_sha256'].get('final.txt')}),flush=True)
if meta['exit_code']!=0 or meta['timeout'] or meta['launch_error']:raise SystemExit(2)
