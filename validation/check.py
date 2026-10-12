"""Check data integrity; counts describe design, not LLM or reader performance."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

STE_IDS = tuple(f'{section}.{rule}' for section, count in ((1,14),(2,2),(3,7),(4,5),(5,5),(6,6),(7,3),(8,7),(9,4)) for rule in range(1,count+1))
FILES = ('specification/rules.json','specification/ste-crosswalk.json','lexicon/core.json','lexicon/domains/software.json','examples/rule-cases.json','examples/lexicon-cases.json')


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON object key: '+key)
        result[key]=value
    return result


class Checker:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.gaps = []

    def error(self, code, path, message):
        self.errors.append({'code':code,'path':str(path),'message':message})

    def gap(self, path, message):
        self.gaps.append({'path':str(path),'message':message})

    def read(self, name):
        path = self.root/name
        try:
            value=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique_object)
        except FileNotFoundError:
            self.error('file_missing',name,'Required file does not exist.')
            return {}
        except (OSError, UnicodeError, ValueError) as exc:
            self.error('file_invalid',name,str(exc))
            return {}
        if not isinstance(value,dict):
            self.error('field_type',name,'JSON root must be an object.')
            return {}
        return value

    def string(self, obj, key, path, pattern=None):
        value=obj.get(key)
        if not isinstance(value,str) or not value.strip() or (pattern and not re.fullmatch(pattern,value)):
            self.error('field_type',f'{path}.{key}','Expected a nonempty string'+(' matching '+pattern if pattern else '')+'.')
            return ''
        return value

    def strings(self, obj, key, path, nonempty=False):
        value=obj.get(key)
        if not isinstance(value,list) or any(not isinstance(item,str) or not item.strip() for item in value) or (nonempty and not value):
            self.error('field_type',f'{path}.{key}','Expected a list of nonempty strings'+(' with at least one item.' if nonempty else '.'))
            return []
        if len(value)!=len(set(value)):
            self.error('duplicate_value',f'{path}.{key}','List values must be unique.')
        return value

    def objects(self, obj, key, path, nonempty=False):
        value=obj.get(key)
        if not isinstance(value,list):
            self.error('field_type',f'{path}.{key}','Expected a list of objects.')
            return []
        if nonempty and not value:
            self.error('field_type',f'{path}.{key}','Expected at least one object.')
        if any(not isinstance(item,dict) for item in value):
            self.error('field_type',f'{path}.{key}','Every item must be an object.')
        return [item for item in value if isinstance(item,dict)]

    def header(self, data, name, version=True):
        if data.get('schema_version')!='1.0':self.error('schema_version',name,'schema_version must be 1.0.')
        if version:self.string(data,'version',name,r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?')

    def example(self, obj, key, fields, path):
        value=obj.get(key)
        if not isinstance(value,dict):
            self.error('field_type',f'{path}.{key}','Expected an example object.')
            return
        for field in fields:self.string(value,field,f'{path}.{key}')

    def rules(self, data):
        name=FILES[0]
        self.header(data,name)
        result={}
        for index,rule in enumerate(self.objects(data,'rules',name,True)):
            path=f'{name}.rules[{index}]'
            key=self.string(rule,'id',path,r'KP-[A-Z]+-[0-9]{3}')
            if key in result:self.error('duplicate_id',path,key)
            if key:result[key]=rule
            for field in ('title','requirement','domain','status'):self.string(rule,field,path)
            if rule.get('status') not in ('proposed','designed','verified','deprecated'):self.error('field_value',path+'.status','Invalid rule status.')
            for field in ('scope','conditions','exceptions','ste_refs'):self.strings(rule,field,path,field=='scope')
            self.example(rule,'positive_example',('context','before','after'),path)
            self.example(rule,'negative_example',('context','text','reason'),path)
            self.example(rule,'counterexample',('context','text','why_allowed'),path)
            for ref in self.objects(rule,'references',path,True):
                for field in ('title','url','access'):self.string(ref,field,path+'.references')
            for ste_id in self.strings(rule,'ste_refs',path):
                if ste_id not in STE_IDS:self.error('unknown_ste_id',path+'.ste_refs',ste_id)
        return result

    def lexicon(self, datasets):
        result={}
        senses={}
        for name,data in datasets:
            self.header(data,name)
            for index,entry in enumerate(self.objects(data,'entries',name,True)):
                path=f'{name}.entries[{index}]'
                key=self.string(entry,'id',path,r'KPL-[A-Z0-9]+(?:-[A-Z0-9]+)*')
                if key in result:self.error('duplicate_id',path,key)
                if key:result[key]=entry
                for field in ('lemma','meaning','pos','status'):self.string(entry,field,path)
                sense=self.string(entry,'sense_id',path,r'[a-z][a-z0-9_]*')
                pair=(entry.get('lemma') if isinstance(entry.get('lemma'),str) else '',sense)
                if pair in senses:self.error('sense_collision',path,'The lemma/sense pair already exists in '+senses[pair]+'. Domains must not override core meanings.')
                senses[pair]=path
                if entry.get('pos') not in ('동사','형용사','명사','부사','의존표현','접속표현','관형표현','서술표현'):self.error('field_value',path+'.pos','Invalid part of speech.')
                if entry.get('status') not in ('preferred','allowed','restricted','deprecated'):self.error('field_value',path+'.status','Invalid entry status.')
                for field in ('domains','forms','frames','conditions','avoid_senses','provenance'):self.strings(entry,field,path,field in ('domains','forms','frames','provenance'))
                self.string(entry,'since',path,r'[0-9]+\.[0-9]+\.[0-9]+')
                if entry.get('status')=='deprecated':self.string(entry,'deprecated_since',path,r'[0-9]+\.[0-9]+\.[0-9]+')
                elif 'deprecated_since' not in entry or entry['deprecated_since'] is not None:self.error('field_type',path+'.deprecated_since','Active entries must explicitly use null.')
                examples=entry.get('examples')
                if not isinstance(examples,dict):self.error('field_type',path+'.examples','Expected an examples object.')
                else:
                    for kind in ('allowed','disallowed','exception'):
                        for example in self.objects(examples,kind,path+'.examples',kind=='allowed'):
                            for field in ('context','text')+(() if kind=='allowed' else ('reason',)):self.string(example,field,path+'.examples.'+kind)
                for alt in self.objects(entry,'alternatives',path):
                    self.string(alt,'entry_id',path+'.alternatives')
                    self.string(alt,'condition',path+'.alternatives')
                    if alt.get('relation') not in ('same_sense','contextual'):self.error('field_value',path+'.alternatives','Alternative relation must be same_sense or contextual.')
        for key,entry in result.items():
            for alt in entry.get('alternatives',[]) if isinstance(entry.get('alternatives'),list) else []:
                if not isinstance(alt,dict):continue
                target=result.get(alt.get('entry_id')) if isinstance(alt.get('entry_id'),str) else None
                if target is None:self.error('unknown_entry',key+'.alternatives',str(alt.get('entry_id')))
                elif target.get('status')=='deprecated':self.error('deprecated_target',key+'.alternatives','A deprecated entry cannot be a usable alternative.')
                elif alt.get('relation')=='same_sense' and (entry.get('sense_id')!=target.get('sense_id') or entry.get('meaning')!=target.get('meaning')):self.error('alternative_semantics',key+'.alternatives','same_sense requires matching sense_id and meaning; contextual alternatives require an explicit condition.')
        return result

    def cases(self, datasets, rules, entries):
        seen={}
        linked_rules=set()
        linked_entries=set()
        result={}
        for name,data,field,known,linked in ((FILES[4],datasets[0],'rule_ids',rules,linked_rules),(FILES[5],datasets[1],'entry_ids',entries,linked_entries)):
            self.header(data,name,False)
            for index,case in enumerate(self.objects(data,'cases',name)):
                path=f'{name}.cases[{index}]'
                key=self.string(case,'id',path)
                if key in seen:self.error('duplicate_case_id',path,'Case id already exists in '+seen[key]+'.')
                if key:seen[key]=path;result[key]=case
                self.string(case,'context',path)
                if 'origin' in case and case['origin']!='author':self.error('field_value',path+'.origin','Authored case files may only declare origin=author; independent reviews use a separate artifact.')
                original=self.string(case,'input',path)
                for ref in self.strings(case,field,path,True):
                    if ref not in known:self.error('unknown_rule' if field=='rule_ids' else 'unknown_entry',path+'.'+field,ref)
                    else:linked.add(ref)
                expected=case.get('expected')
                if not isinstance(expected,dict):self.error('field_type',path+'.expected','Expected an object.');continue
                self.string(expected,'reason',path+'.expected')
                decision=expected.get('decision')
                if decision not in ('keep','revise','clarify'):self.error('field_value',path+'.expected.decision','Expected keep, revise, or clarify.')
                if 'output' not in expected:self.error('field_type',path+'.expected.output','Explicit output is required.')
                if decision=='keep' and expected.get('output')!=original:self.error('case_invariant',path,'keep must preserve input exactly.')
                elif decision=='clarify' and expected.get('output') is not None:self.error('case_invariant',path,'clarify must use null output, never invent a replacement.')
                elif decision=='revise':self.string(expected,'output',path+'.expected')
        for key in rules:
            if key not in linked_rules:self.error('missing_case',key,'Rule has no linked case.')
        for key in entries:
            if key not in linked_entries:self.error('missing_case',key,'Entry has no linked case.')
        return result

    @staticmethod
    def measurement(case):
        measure=case.get('expected_measurement')
        if not isinstance(measure,dict):return False
        original=case.get('input')
        if not isinstance(original,str):return False
        if 'whitespace_tokens' in measure:
            if type(measure['whitespace_tokens']) is not int or measure['whitespace_tokens']!=len(original.split()):return False
        if 'review_units' in measure:
            units=measure.get('unit_texts')
            if type(measure['review_units']) is not int or not isinstance(units,list) or len(units)!=measure['review_units']:return False
            if any(not isinstance(unit,str) or not unit.strip() or unit not in original for unit in units):return False
        for field in ('parenthetical_contents_excluded','internal_content_review','literal_must_remain_identical','length_review_trigger','automatic_violation'):
            if field in measure and type(measure[field]) is not bool:return False
        if 'literal_text' in measure:
            literal=measure['literal_text']
            if not isinstance(literal,str) or not literal or literal not in original:return False
            if measure.get('literal_must_remain_identical') and (not isinstance(case.get('acceptable_output'),str) or literal not in case['acceptable_output']):return False
        return True

    def evidence(self, item, path, rules, cases):
        evidence=item.get('evidence')
        if not isinstance(evidence,list) or not evidence:
            self.error('verification_evidence',path,'verified requires a functional-review JSON artifact with current hashes and a matching review.')
            return False
        valid=False
        for ref in evidence:
            if not isinstance(ref,dict) or ref.get('kind')!='functional-review' or ref.get('result')!='pass' or not isinstance(ref.get('path'),str):
                self.error('verification_evidence',path,'Evidence must contain path, kind=functional-review, and result=pass.');continue
            proofpath=(self.root/ref['path']).resolve()
            try:proofpath.relative_to(self.root)
            except ValueError:self.error('verification_evidence',path,'Evidence path must stay inside the project.');continue
            proof=self.read(ref['path'])
            correct=True
            for field,name in (('reviewed_rules_sha256',FILES[0]),('reviewed_cases_sha256',FILES[4])):
                try:digest=hashlib.sha256((self.root/name).read_bytes()).hexdigest()
                except OSError:digest=None
                if proof.get(field)!=digest or digest is None:self.error('verification_evidence',path,'Evidence hash does not match '+name+'.');correct=False
            independent_path=proof.get('independent_cases_path')
            independent={}
            if not isinstance(independent_path,str) or not independent_path.strip():
                self.error('verification_evidence',path,'An independent case artifact path is required.');correct=False
            else:
                casepath=(self.root/independent_path).resolve()
                try:casepath.relative_to(self.root)
                except ValueError:
                    self.error('verification_evidence',path,'Independent cases must stay inside the project.');correct=False
                else:
                    casefile=self.read(independent_path)
                    try:casehash=hashlib.sha256(casepath.read_bytes()).hexdigest()
                    except OSError:casehash=None
                    if not casehash or casehash!=proof.get('independent_cases_sha256'):
                        self.error('verification_evidence',path,'Independent case hash does not match the current artifact.');correct=False
                    if casefile.get('schema_version')!='1.0' or casefile.get('purpose')!='functional-design-review':
                        self.error('verification_evidence',path,'Invalid independent case artifact header.');correct=False
                    for case in self.objects(casefile,'cases',path+'.independent_cases',True):
                        case_id=case.get('id')
                        ste_ids=case.get('ste_ids')
                        decision=case.get('expected_decision')
                        original=case.get('input')
                        acceptable=case.get('acceptable_output')
                        usable=(isinstance(case_id,str) and bool(case_id.strip()) and case_id not in independent
                            and isinstance(ste_ids,list) and bool(ste_ids) and all(isinstance(key,str) and key in STE_IDS for key in ste_ids)
                            and all(isinstance(case.get(field),str) and bool(case[field].strip()) for field in ('context','input','rationale'))
                            and type(case.get('independent')) is bool
                            and decision in ('keep','revise','clarify') and 'acceptable_output' in case and 'rejected_output' in case
                            and (case['rejected_output'] is None or isinstance(case['rejected_output'],str)) and acceptable!=case['rejected_output'])
                        if decision=='keep':usable=usable and acceptable==original
                        elif decision=='clarify':usable=usable and acceptable is None
                        elif decision=='revise':usable=usable and isinstance(acceptable,str) and bool(acceptable.strip())
                        if 'expected_measurement' in case:
                            usable=usable and self.measurement(case)
                        if not usable:
                            self.error('verification_evidence',path,'Independent case fields or decision invariants are invalid.');correct=False
                        elif case_id in cases:
                            self.error('verification_evidence',path,'Independent holdout IDs must not reuse authored case IDs.');correct=False
                        else:independent[case_id]=case
            spec_path=proof.get('reviewed_spec_path')
            if spec_path!='docs/spec/korean-rules.md':
                self.error('verification_evidence',path,'reviewed_spec_path must identify docs/spec/korean-rules.md.');correct=False
            else:
                try:spec_hash=hashlib.sha256((self.root/spec_path).read_bytes()).hexdigest()
                except OSError:spec_hash=None
                if not spec_hash or proof.get('reviewed_spec_sha256')!=spec_hash:
                    self.error('verification_evidence',path,'Measurement procedure hash does not match the current specification.');correct=False
            reviews=self.objects(proof,'reviews',path+'.evidence',True)
            matches=[]
            reviewed_ids=[]
            for review in reviews:
                review_id=review.get('ste_id')
                if not isinstance(review_id,str) or review_id not in STE_IDS or review_id in reviewed_ids:
                    self.error('verification_evidence',path,'Review source IDs must be current and unique; conflicting verdicts are not accepted.');correct=False
                reviewed_ids.append(review_id)
                ids=review.get('target_rule_ids')
                case_ids=review.get('case_ids')
                if review.get('ste_id')!=item.get('ste_id'):continue
                if not isinstance(ids,list) or ids!=item.get('target_rule_ids') or review.get('verdict')!='pass':continue
                if not isinstance(review.get('rationale'),str) or not review['rationale'].strip():continue
                if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():continue
                if not isinstance(case_ids,list) or not case_ids or any(not isinstance(key,str) or key not in independent for key in case_ids):continue
                if any(item.get('ste_id') not in independent[key]['ste_ids'] or not independent[key]['independent'] for key in case_ids):continue
                matches.append(review)
            if not matches:self.error('verification_evidence',path,'Evidence has no matching pass review with rationale, reviewer, and independent cases.');correct=False
            valid=valid or correct
        return valid

    def crosswalk(self, data, rules, cases):
        name=FILES[1]
        self.header(data,name,False)
        source=data.get('source')
        if not isinstance(source,dict) or type(source.get('rule_count')) is not int or source['rule_count']!=53:self.error('source_count',name,'Source rule_count must be the integer 53.')
        if isinstance(source,dict):
            for field in ('title','date','url'):
                if field in source:self.string(source,field,name+'.source')
            if 'issue' in source and (type(source['issue']) is not int or source['issue']<=0):self.error('field_type',name+'.source.issue','Issue must be a positive integer.')
        target=data.get('target')
        if type(target) not in (int,float) or not 0<=target<=1:self.error('field_type',name+'.target','Target must be a ratio between 0 and 1.')
        items=self.objects(data,'items',name,True)
        ids=[item.get('ste_id') for item in items]
        if any(not isinstance(key,str) for key in ids) or len(ids)!=53 or set(key for key in ids if isinstance(key,str))!=set(STE_IDS):self.error('ste_id_set',name,'Expected exactly the current 53 source IDs; 2.3 is obsolete.')
        counts={'designed_count':0,'verified_count':0,'partial_count':0,'unmapped_count':0}
        seen=set()
        for index,item in enumerate(items):
            path=f'{name}.items[{index}]'
            key=self.string(item,'ste_id',path)
            if key in seen:self.error('duplicate_id',path,key)
            seen.add(key)
            for field in ('function','korean_design'):self.string(item,field,path)
            targets=self.strings(item,'target_rule_ids',path)
            self.strings(item,'gaps',path)
            if not isinstance(item.get('evidence'),list):self.error('field_type',path+'.evidence','Expected an evidence list.')
            status=item.get('status')
            if status not in ('unmapped','partial','designed','verified'):self.error('field_value',path+'.status','Invalid coverage status.')
            mapped=True
            for target_id in targets:
                if target_id not in rules:self.error('unknown_rule',path+'.target_rule_ids',target_id);mapped=False
                elif not isinstance(rules[target_id].get('ste_refs'),list) or key not in rules[target_id]['ste_refs']:self.error('asymmetric_mapping',path,'Target rule '+target_id+' does not refer to '+key+'.');mapped=False
            for target_id,rule in rules.items():
                refs=rule.get('ste_refs')
                if isinstance(refs,list) and key in refs and target_id not in targets:
                    self.gap(path,'Rule '+target_id+' has a related source reference but is not selected as an actual functional contribution.')
            if status in ('designed','verified') and not targets:self.error('mapping_required',path,'Designed coverage requires target rules.');mapped=False
            if status=='unmapped' and targets:self.error('mapping_status',path,'unmapped must have no target rules.');mapped=False
            verified=status=='verified' and self.evidence(item,path,rules,cases)
            if key not in STE_IDS or ids.count(key)!=1 or not mapped:continue
            if status in ('designed','verified') and targets:counts['designed_count']+=1
            if verified and targets:counts['verified_count']+=1
            if status=='partial':counts['partial_count']+=1
            if status=='unmapped':counts['unmapped_count']+=1
            if status in ('unmapped','partial'):self.gap(path,'Source function is '+status+'.')
            for gap in item.get('gaps',[]) if isinstance(item.get('gaps'),list) else []:
                if isinstance(gap,str):self.gap(path,gap)
        counts.update(source_count=53,designed_ratio=counts['designed_count']/53,verified_ratio=counts['verified_count']/53,unconfirmed_count=53-counts['designed_count'],semantically_unconfirmed_count=53,verified_kind='verified_functional_design')
        return counts


def validate_root(root, require_coverage=None):
    check=Checker(root)
    data={name:check.read(name) for name in FILES}
    rules=check.rules(data[FILES[0]])
    entries=check.lexicon([(name,data[name]) for name in FILES[2:4]])
    cases=check.cases([data[name] for name in FILES[4:6]],rules,entries)
    coverage=check.crosswalk(data[FILES[1]],rules,cases)
    if require_coverage is not None:
        if type(require_coverage) not in (int,float) or not 0<=require_coverage<=1:check.error('field_type','--require-coverage','Threshold must be between 0 and 1.')
        elif coverage['designed_ratio']<require_coverage:check.error('coverage_threshold',FILES[1],f"Designed coverage {coverage['designed_count']}/53 is below {require_coverage:.0%}; this gate does not measure semantic performance.")
    return {'ok':not check.errors,'errors':check.errors,'gaps':check.gaps,'coverage':coverage,'semantic_verified':False,'limitations':['Static validation checks structure, references, and case invariants only.','verified_functional_design validates a recorded review artifact; it does not independently repeat that review.','LLM meaning preservation, reader comprehension, and 90% semantic performance require separate execution and human evaluation.']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--require-coverage',type=float,help='Optional minimum designed ratio; not a semantic-performance gate.')
    args=parser.parse_args(argv)
    report=validate_root(args.root,args.require_coverage)
    if args.json:print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(f"Integrity: {'PASS' if report['ok'] else 'FAIL'}; designed={report['coverage']['designed_count']}/53; verified functional design={report['coverage']['verified_count']}/53; semantic evaluation=unconfirmed")
        for error in report['errors']:print(f"ERROR {error['code']} {error['path']}: {error['message']}")
        print(f"Design gaps: {len(report['gaps'])}")
    return 0 if report['ok'] else 1


if __name__=='__main__':sys.exit(main())
