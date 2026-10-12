#!/usr/bin/env python3
import argparse,datetime,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUNNER=ROOT.parent/'runner.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
parser=argparse.ArgumentParser();parser.add_argument('--call',type=int,choices=(1,2,3,4),required=True);args=parser.parse_args()
manifest=json.loads((ROOT/'freeze-manifest.json').read_text())
for name,expected in manifest['frozen_sha256'].items():assert sha(ROOT/name)==expected,(name,'frozen artifact changed')
assert sha(RUNNER)==manifest['runner_sha256'],'existing runner changed'
amendment=json.loads((ROOT/'capacity-routing-freeze.json').read_text())
for name,expected in amendment['sha256'].items():assert sha(ROOT/name)==expected,(name,'amendment artifact changed')
assert len(list(ROOT.glob('attempt-opus-*.json')))<4,'all four Opus attempts already started'
assert len(list(ROOT.glob('attempt-??.json')))==1,'unexpected original attempts'
entry=manifest['calls'][args.call-1];ledger=ROOT/f"attempt-opus-{args.call:02d}.json"
with ledger.open('x') as f:json.dump({'condition_call':args.call,'original_entry':entry,'attempt_started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'replacement_model':'anthropic/claude-opus-5-5','replacement_effort':'high','fixed_total_attempt_limit':5,'original_sol_service_failure_count':1},f,ensure_ascii=False,indent=2)
spec=importlib.util.spec_from_file_location('real_runner',RUNNER);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
cases=r.load_cases(ROOT/entry['gold']);prompt=(ROOT/entry['prompt']).read_text()
r.build_prompt=lambda _:prompt;r.build_generation_prompt=lambda _:prompt
original_command=r.build_command
def opus_command(project,last):
 cmd=original_command(project,last);cmd[cmd.index('--model')+1]='anthropic/claude-opus-5-5';return cmd
r.build_command=opus_command
run_dir=ROOT/('opus-'+entry['directory'])
print(json.dumps({'event':'starting_actual_opus_call','condition_call':args.call,'directory':str(run_dir),'case_count':len(cases),'requested_model':'anthropic/claude-opus-5-5','effort':'high'}),flush=True)
meta,parsed=r.run_condition(entry['condition'],cases,ROOT/'frozen-profile.md' if entry['condition']=='treatment' else None,run_dir,Path('/Users/m5max/.codex/auth.json'),600,mode=entry['mode'])
meta['model_requested']='anthropic/claude-opus-5-5'
meta['capacity_replacement']=True
meta['capacity_failure_reference']='../01-edit26-treatment'
meta['amended_total_attempt_limit']=5
meta['environment_metadata']={'inherited_CODEX_overrides_removed':True,'CODEX_HOME':'temporary isolated directory, auth.json symlink only','temporary_project':True,'sandbox':'read-only','ignore_user_config':True,'ignore_rules':True,'ephemeral':True,'auth_contents_recorded':False,'environment_values_not_recorded':True}
streams='\n'.join((run_dir/n).read_text() for n in ['stdout.jsonl','stderr.txt'])
labels=re.findall(r'(?i)\bFALLBACK\b',streams)
meta['fallback_label_present_in_cli']=bool(labels)
if labels:meta['fallback_observed']='FALLBACK label present; inspect captured CLI stream'
meta['artifact_sha256']={p.name:sha(p) for p in run_dir.iterdir() if p.is_file() and p.name!='metadata.json'}
r.save_json(run_dir/'metadata.json',meta)
index={x.get('id'):x for x in parsed['results'] if isinstance(x,dict)}
save(ROOT/(run_dir.name+'-review-packet.json'),{'scope':entry['scope'],'condition':entry['condition'],'requested_model':'anthropic/claude-opus-5-5','criteria_only':True,'historical_Sol_comparison_is_not_causal':True,'structure':{'valid':parsed['structure_valid'],'errors':parsed['errors']},'cases':[{'case':c,'actual_output':index.get(c['id']),'semantic_rating':None} for c in cases],'overall_accuracy':None})
print(json.dumps({'event':'finished_actual_opus_call','condition_call':args.call,'exit_code':meta['exit_code'],'timeout':meta['timeout'],'launch_error':meta['launch_error'],'structure_valid':parsed['structure_valid'],'errors':parsed['errors'],'FALLBACK_label_present':bool(labels),'final_sha256':meta['artifact_sha256'].get('final.txt')}),flush=True)
if meta['exit_code']!=0 or meta['timeout'] or meta['launch_error'] or labels:raise SystemExit(2)
