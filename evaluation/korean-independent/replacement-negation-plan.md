# Explicit negation keep evidence replacement

This artifact adds exactly one fictional keep case, KI-NEG-04, as replacement evidence for the negation keep cell previously represented by KI-NEG-03. The original 24 cases and six-case supplement remain frozen and unchanged. This artifact does not silently change KI-NEG-03 or its expected decision.

The separate author used only the new assignment and self-contained fictional facts. The author did not read source rules or old reviews, call another model, commit files, install dependencies, or change other files. This case expresses a normative author judgment and provides no empirical reader evidence or expert endorsement.

The source reports zero blinking occurrences during one fixed five-minute observation. Its negation and quantifier jointly exclude every occurrence within that bounded period. Its rejected output reports one occurrence and directly contradicts the given zero count. The case contains no permission construction, obligation claim, diagnosis, or inference about times outside the stated period.

## The independent reviewer preserves provenance.

A separate reviewer must map KI-NEG-04 to the latest integrated rule IDs and supporting text, record the rules revision or SHA256, and compare the rule-derived decision with the expected keep decision. The reviewer records case concerns or rule conflicts in a separate artifact without changing this replacement or either earlier suite.

An acceptable output is one valid example rather than an exact-string whitelist. Keep requires preserving the source without unsupported explanation, cause, diagnosis, or follow-up action.

## The reproducible check validates the freeze.

Run the following command from this directory to verify the replacement schema, original hashes, supplement hashes, and 31 distinct combined IDs. Replace verify with freeze only for the initial freeze before replacement-negation-check.json exists. The command refuses to overwrite an existing freeze record.

```sh
python3 - verify <<'PY'
import hashlib, json, sys
from pathlib import Path
root=Path.cwd()
mode=sys.argv[1]
def require(condition,message):
    if not condition:
        raise SystemExit(message)
def sha(name):
    return hashlib.sha256((root/name).read_bytes()).hexdigest()
data=json.loads((root/'replacement-negation.json').read_text(encoding='utf-8'))
original=json.loads((root/'cases.json').read_text(encoding='utf-8'))
supplement=json.loads((root/'supplement.json').read_text(encoding='utf-8'))
oldcheck=json.loads((root/'check.json').read_text(encoding='utf-8'))
suppcheck=json.loads((root/'supplement-check.json').read_text(encoding='utf-8'))
require(data['schema_version']=='1.0' and data['suite_id']=='korean-independent-negation-replacement-v1','Wrong replacement identity')
require(len(data['cases'])==1 and len(original['cases'])==24 and len(supplement['cases'])==6,'Wrong case counts')
for name,expected in oldcheck['sha256'].items():
    require(sha(name)==expected,'Original file changed: '+name)
for name,expected in suppcheck['sha256'].items():
    require(sha(name)==expected,'Supplement file changed: '+name)
require(suppcheck['original_sha256']==oldcheck['sha256'],'Original freeze identity changed')
ids=[c['id'] for c in original['cases']+supplement['cases']+data['cases']]
require(len(ids)==31 and len(set(ids))==31,'Expected 31 unique combined IDs')
c=data['cases'][0]
fields={'id','family','case_type','explicit_context','source','candidate','expected_decision','acceptable_output','rejected_output','rationale','preserved_facts','prohibited_changes'}
require(set(c)==fields,'Wrong fields')
require(c['id']=='KI-NEG-04' and c['family']=='negation_and_quantifier_scope','Wrong cell')
require(c['case_type']=='keep' and c['expected_decision']=='keep','Must be keep')
require(c['source']==c['candidate']==c['acceptable_output'],'Keep must preserve source')
require(c['rejected_output']!=c['acceptable_output'],'Outputs must differ')
for field in fields-{'preserved_facts','prohibited_changes'}:
    require(isinstance(c[field],str) and c[field].strip(),'Invalid '+field)
for field in ['preserved_facts','prohibited_changes']:
    require(isinstance(c[field],list) and c[field] and all(isinstance(x,str) and x.strip() for x in c[field]),'Invalid '+field)
baseline=['cases.json','plan.md','validate.py','check.json','supplement.json','supplement-plan.md','supplement-check.json']
record={'schema_valid':True,'replacement_case_count':1,'original_case_count':24,'supplement_case_count':6,'combined_unique_case_count':31,'replacement_id':'KI-NEG-04','replaces_evidence_for':'KI-NEG-03','baseline_sha256':{name:sha(name) for name in baseline},'sha256':{name:sha(name) for name in ['replacement-negation.json','replacement-negation-plan.md']},'freeze_status':'frozen_before_rule_mapping','scope':'Structural checks and frozen file identity only; semantics and rule mapping require separate review.'}
check=root/'replacement-negation-check.json'
if mode=='freeze':
    require(not check.exists(),'Refusing to overwrite freeze')
    with check.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
elif mode=='verify':
    require(check.exists(),'Missing freeze')
    require(json.loads(check.read_text(encoding='utf-8'))==record,'Freeze mismatch')
else:
    raise SystemExit('Use freeze or verify')
print(json.dumps({'result':mode,'replacement_case_count':1,'combined_unique_case_count':31,'sha256':record['sha256']},ensure_ascii=False))
PY
```

The check records hashes for the seven existing suite files and the two newly authored replacement files. Structural validity and frozen identity do not establish semantic correctness or integrated rule performance. This assignment adds no further cases or rule changes.
