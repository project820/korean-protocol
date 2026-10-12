# Independent coverage supplement plan

This supplement deliberately adds exactly six cases after the original 24-case suite was frozen. It does not replace or silently correct the original suite, its expected decisions, or its freeze record.

The separate author used only the assignment and fictional self-contained context. The author did not read existing source rules or examples, call another model, commit files, install dependencies, or test real readers. The cases record normative judgments rather than empirical reader evidence or expert endorsement.

## The supplement completes the assigned contrast coverage.

KI-SUP-ASP-01 accepts an equivalent expression of ongoing drawing. KI-SUP-ASP-02 rejects changing a sustained wearing state into the action of putting glasses on. KI-SUP-ASP-03 keeps an already-clear completed action. These cases distinguish ongoing action, completion, and a maintained result state without treating all 고 있다 expressions alike.

KI-SUP-CAU-01 accepts a rewrite that preserves the director and the actual performer. KI-SUP-CAU-02 keeps a natural lexical causative whose cause is a joke, not a command. KI-SUP-PAS-01 rejects a passive-to-active rewrite that reverses the explicit actor and affected person; its acceptable output uses only the actor already stated.

Each case has the original schema fields and an explicit context containing all facts needed for evaluation. An acceptable output is one valid example rather than an exact-string whitelist. A keep decision requires preserving the concise source without invention.

## The freeze preserves both suites for separate review.

The validation below checks six supplement cases, 24 original cases, and 30 unique IDs across both suites. It checks the original frozen cases, plan, and validator hashes before creating or verifying supplement-check.json. It refuses to replace an existing supplement freeze record.

Run the following command from this directory to verify the supplement. Replace verify with freeze only for the initial freeze before a freeze record exists. Run `python3 validate.py --verify` separately to verify the full original freeze record.

```sh
python3 - verify <<'PY'
import hashlib, json, sys
from collections import Counter
from pathlib import Path
root=Path.cwd()
mode=sys.argv[1]
def require(condition,message):
    if not condition:
        raise SystemExit(message)
def sha(name):
    return hashlib.sha256((root/name).read_bytes()).hexdigest()
data=json.loads((root/'supplement.json').read_text(encoding='utf-8'))
original=json.loads((root/'cases.json').read_text(encoding='utf-8'))
original_check=json.loads((root/'check.json').read_text(encoding='utf-8'))
require(data['schema_version']=='1.0' and data['suite_id']=='korean-independent-supplement-v1','Wrong supplement identity')
require(len(data['cases'])==6 and len(original['cases'])==24,'Wrong case counts')
require(sha('cases.json')==original_check['sha256']['cases.json'],'Original cases changed')
require(sha('plan.md')==original_check['sha256']['plan.md'],'Original plan changed')
require(sha('validate.py')==original_check['sha256']['validate.py'],'Original validator changed')
ids=[case['id'] for case in original['cases']+data['cases']]
require(len(set(ids))==30,'IDs must be unique across both suites')
fields={'id','family','case_type','explicit_context','source','candidate','expected_decision','acceptable_output','rejected_output','rationale','preserved_facts','prohibited_changes'}
decisions={'normal':'accept','failure':'reject','keep':'keep'}
for case in data['cases']:
    require(set(case)==fields,'Wrong fields: '+case['id'])
    require(case['case_type'] in decisions,'Unknown case type')
    require(case['expected_decision']==decisions[case['case_type']],'Wrong decision')
    for field in fields-{'preserved_facts','prohibited_changes'}:
        require(isinstance(case[field],str) and case[field].strip(),'Invalid '+field)
    for field in ['preserved_facts','prohibited_changes']:
        require(isinstance(case[field],list) and case[field] and all(isinstance(x,str) and x.strip() for x in case[field]),'Invalid '+field)
    if case['case_type']=='keep':
        require(case['source']==case['candidate']==case['acceptable_output'],'Keep must retain source')
    else:
        require(case['source']!=case['candidate'],'Revision must differ')
    if case['case_type']=='normal':
        require(case['candidate']==case['acceptable_output'],'Normal must accept candidate')
    if case['case_type']=='failure':
        require(case['candidate']==case['rejected_output'],'Failure must reject candidate')
    require(case['acceptable_output']!=case['rejected_output'],'Outputs must differ')
counts=Counter((case['family'],case['case_type']) for case in data['cases'])
required={('aspect_and_modality','normal'):1,('aspect_and_modality','failure'):1,('aspect_and_modality','keep'):1,('passive_and_causative','normal'):1,('passive_and_causative','failure'):1,('passive_and_causative','keep'):1}
require(counts==required,'Wrong supplement family/type coverage')
require({case['id'] for case in data['cases']}=={'KI-SUP-ASP-01','KI-SUP-ASP-02','KI-SUP-ASP-03','KI-SUP-CAU-01','KI-SUP-CAU-02','KI-SUP-PAS-01'},'Wrong assigned coverage IDs')
record={'schema_valid':True,'supplement_case_count':6,'original_case_count':24,'combined_unique_case_count':30,'case_type_counts':dict(sorted(Counter(case['case_type'] for case in data['cases']).items())),'original_sha256':original_check['sha256'],'sha256':{name:sha(name) for name in ['supplement.json','supplement-plan.md']},'scope':'Structural counts and frozen file identity only; semantics and integrated rule mapping require separate review.','freeze_status':'frozen_before_rule_mapping'}
check=root/'supplement-check.json'
if mode=='freeze':
    require(not check.exists(),'Refusing to replace supplement freeze')
    with check.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
elif mode=='verify':
    require(check.exists(),'Missing supplement freeze')
    require(json.loads(check.read_text(encoding='utf-8'))==record,'Supplement freeze mismatch')
else:
    raise SystemExit('Use freeze or verify')
print(json.dumps({'result':mode,'case_count':6,'combined_unique_case_count':30,'sha256':record['sha256']},ensure_ascii=False))
PY
```

The parent must assign a separate reviewer to map all six supplement IDs to the latest integrated rule IDs and text. The reviewer records the rules path and revision or SHA256, rule-derived candidate decisions, expected decisions, evidence, and covered/conflict/ambiguous/no-applicable-rule status. The reviewer distinguishes a rule defect from a case defect and writes any concerns into a separate review artifact outside this owned directory.

No reviewer may tune the frozen supplement or the original frozen 24 cases to the integrated rules. Structural validation does not establish semantic correctness or rule performance. This assignment ends with six supplement cases and adds no rule implementation.
