import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

IDS = [f'{section}.{rule}' for section, count in [(1,14),(2,2),(3,7),(4,5),(5,5),(6,6),(7,3),(8,7),(9,4)] for rule in range(1,count+1)]


def fixture(root):
    rule = {'id':'KP-WRD-001','title':'가능성 보존','requirement':'가능성을 사실로 바꾸지 않는다.','domain':'words','scope':['chat'],'conditions':['뜻을 보존할 때'],'exceptions':['문맥에서 알 수 있는 행위자는 생략한다.'],'positive_example':{'context':'경고','before':'문제가 있을 가능성이 있습니다.','after':'문제가 있을 수 있습니다.'},'negative_example':{'context':'경고','text':'문제가 있습니다.','reason':'가능성을 사실로 바꾼다.'},'counterexample':{'context':'경고','text':'문제가 있을 수 있습니다.','why_allowed':'가능성을 보존한다.'},'ste_refs':['1.1'],'references':[{'title':'기준','url':'https://example.org/rules','access':'public'}],'status':'proposed'}
    entry = {'id':'KPL-CORE-CHECK','lemma':'확인하다','sense_id':'check','pos':'동사','meaning':'상태를 살피다.','status':'preferred','domains':['core'],'forms':['확인한다'],'frames':['대상을 확인하다'],'conditions':[],'avoid_senses':[],'alternatives':[],'examples':{'allowed':[{'context':'상태 확인','text':'설정을 확인한다.'}],'disallowed':[],'exception':[]},'provenance':['규약 후보'],'since':'0.2.0','deprecated_since':None}
    software = dict(entry, id='KPL-SW-REVIEW', lemma='검토하다', sense_id='review', domains=['software'], meaning='변경 내용을 살피다.')
    items = [{'ste_id':key,'function':'작성 기능','korean_design':'한국어 설계','target_rule_ids':['KP-WRD-001'] if key=='1.1' else [],'status':'designed' if key=='1.1' else 'unmapped','evidence':[],'gaps':[] if key=='1.1' else ['설계 필요']} for key in IDS]
    case = {'id':'CASE-1','rule_ids':['KP-WRD-001'],'context':'경고','input':'문제가 있을 수 있습니다.','expected':{'decision':'keep','output':'문제가 있을 수 있습니다.','reason':'가능성을 보존한다.'}}
    lexcase = {'id':'LEX-1','entry_ids':[entry['id'],software['id']],'context':'상태 확인','input':'설정을 확인한다.','expected':{'decision':'keep','output':'설정을 확인한다.','reason':'허용 의미이다.'}}
    data = {'specification/rules.json':{'schema_version':'1.0','version':'0.2.0-draft','rules':[rule]},'specification/ste-crosswalk.json':{'schema_version':'1.0','source':{'rule_count':53},'target':0.9,'items':items},'lexicon/core.json':{'schema_version':'1.0','version':'0.2.0-draft','entries':[entry]},'lexicon/domains/software.json':{'schema_version':'1.0','version':'0.2.0-draft','entries':[software]},'examples/rule-cases.json':{'schema_version':'1.0','cases':[case]},'examples/lexicon-cases.json':{'schema_version':'1.0','cases':[lexcase]}}
    for name, value in data.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    for name in ('LICENSE','NOTICE.md'):
        (root/name).write_bytes((Path(__file__).resolve().parents[1]/name).read_bytes())
    return data


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)

    def check(self, threshold=None):
        from validation.check import validate_root
        return validate_root(self.root, require_coverage=threshold)

    def change(self, name, callback):
        callback(self.data[name])
        (self.root/name).write_text(json.dumps(self.data[name],ensure_ascii=False),encoding='utf-8')

    def assertError(self, code):
        self.assertIn(code,[e['code'] for e in self.check()['errors']])


class ValidationTests(FixtureTests):
    def test_valid_draft_reports_gaps_without_claiming_semantic_proof(self):
        report = self.check()
        self.assertEqual([],report['errors'])
        self.assertEqual(1,report['coverage']['designed_count'])
        self.assertEqual(0,report['coverage']['verified_count'])
        self.assertEqual(52,report['coverage']['unconfirmed_count'])
        self.assertFalse(report['semantic_verified'])
        self.assertTrue(report['gaps'])

    def test_missing_file_is_actionable(self):
        (self.root/'lexicon/core.json').rename(self.root/'lexicon/missing.json')
        self.assertError('file_missing')

    def test_invalid_type_does_not_crash(self):
        self.change('specification/rules.json',lambda d:d.update(rules='not a list'))
        self.assertError('field_type')

    def test_duplicate_rule_id_is_rejected(self):
        self.change('specification/rules.json',lambda d:d['rules'].append(d['rules'][0]))
        self.assertError('duplicate_id')

    def test_obsolete_ste_id_is_rejected_even_when_count_is_53(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(ste_id='2.3'))
        self.assertError('ste_id_set')

    def test_unknown_target_rule_is_rejected(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(target_rule_ids=['KP-MISSING-001']))
        self.assertError('unknown_rule')

    def test_asymmetric_mapping_is_rejected(self):
        self.change('specification/rules.json',lambda d:d['rules'][0].update(ste_refs=['1.2']))
        self.assertError('asymmetric_mapping')

    def test_unmapped_draft_reverse_reference_is_a_gap(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(status='unmapped',target_rule_ids=[]))
        report=self.check()
        self.assertEqual([],report['errors'])
        self.assertEqual(0,report['coverage']['designed_count'])
        self.assertTrue(report['gaps'])

    def test_related_reverse_reference_does_not_inflate_or_block_actual_design(self):
        second=json.loads(json.dumps(self.data['specification/rules.json']['rules'][0]))
        second['id']='KP-WRD-002'
        self.change('specification/rules.json',lambda d:d['rules'].append(second))
        secondcase=json.loads(json.dumps(self.data['examples/rule-cases.json']['cases'][0]))
        secondcase.update(id='CASE-2',rule_ids=['KP-WRD-002'])
        self.change('examples/rule-cases.json',lambda d:d['cases'].append(secondcase))
        report=self.check()
        self.assertEqual([],report['errors'])
        self.assertEqual(1,report['coverage']['designed_count'])
        self.assertTrue(report['gaps'])

    def test_blank_verified_evidence_cannot_inflate_score(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(status='verified'))
        self.assertError('verification_evidence')
        self.assertEqual(0,self.check()['coverage']['verified_count'])

    def test_number_only_evidence_cannot_inflate_score(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(status='verified',evidence=[90]))
        self.assertError('verification_evidence')

    def proof(self):
        path=self.root/'evaluation'
        path.mkdir()
        holdout={'schema_version':'1.0','purpose':'functional-design-review','cases':[{'id':'HOLDOUT-1','independent':True,'ste_ids':['1.1'],'context':'경고','input':'문제가 있을 수 있습니다.','expected_decision':'keep','acceptable_output':'문제가 있을 수 있습니다.','rejected_output':'문제가 있습니다.','rationale':'가능성을 사실로 바꾸지 않는다.'}]}
        (path/'functional-cases.json').write_text(json.dumps(holdout,ensure_ascii=False))
        (self.root/'docs/spec').mkdir(parents=True)
        spec=self.root/'docs/spec/korean-rules.md'
        spec.write_text('측정 절차와 기능 대응 기준')
        proof={'reviewed_spec_path':'docs/spec/korean-rules.md','reviewed_spec_sha256':hashlib.sha256(spec.read_bytes()).hexdigest(),'reviewed_rules_sha256':hashlib.sha256((self.root/'specification/rules.json').read_bytes()).hexdigest(),'reviewed_cases_sha256':hashlib.sha256((self.root/'examples/rule-cases.json').read_bytes()).hexdigest(),'independent_cases_path':'evaluation/functional-cases.json','independent_cases_sha256':hashlib.sha256((path/'functional-cases.json').read_bytes()).hexdigest(),'reviews':[{'ste_id':'1.1','target_rule_ids':['KP-WRD-001'],'verdict':'pass','rationale':'조건과 예외가 독립 사례의 뜻을 보존한다.','case_ids':['HOLDOUT-1'],'reviewer':'independent-reviewer'}]}
        (path/'functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.change('specification/ste-crosswalk.json',lambda d:d['items'][0].update(status='verified',evidence=[{'path':'evaluation/functional-review.json','kind':'functional-review','result':'pass'}]))
        return holdout,proof

    def test_current_functional_review_is_counted_without_semantic_claim(self):
        self.proof()
        report=self.check()
        self.assertEqual([],report['errors'])
        self.assertEqual(1,report['coverage']['verified_count'])
        self.assertFalse(report['semantic_verified'])

    def test_shared_regression_case_is_not_independent_review_evidence(self):
        holdout,proof=self.proof()
        holdout['cases'][0]['independent']=False
        path=self.root/'evaluation/functional-cases.json'
        path.write_text(json.dumps(holdout,ensure_ascii=False))
        proof['independent_cases_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root/'evaluation/functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.assertError('verification_evidence')
        self.assertEqual(0,self.check()['coverage']['verified_count'])

    def test_false_whitespace_measurement_cannot_verify_design(self):
        holdout,proof=self.proof()
        holdout['cases'][0]['expected_measurement']={'whitespace_tokens':99}
        path=self.root/'evaluation/functional-cases.json'
        path.write_text(json.dumps(holdout,ensure_ascii=False))
        proof['independent_cases_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root/'evaluation/functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.assertError('verification_evidence')

    def test_conflicting_review_verdicts_cannot_inflate_verified_count(self):
        holdout,proof=self.proof()
        conflict=dict(proof['reviews'][0],verdict='fail')
        proof['reviews'].append(conflict)
        (self.root/'evaluation/functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.assertError('verification_evidence')
        self.assertEqual(0,self.check()['coverage']['verified_count'])

    def test_stale_spec_cannot_verify_changed_measurement_procedure(self):
        self.proof()
        (self.root/'docs/spec/korean-rules.md').write_text('측정 절차를 변경했다.')
        self.assertError('verification_evidence')
        self.assertEqual(0,self.check()['coverage']['verified_count'])

    def test_stale_review_cannot_verify_changed_rule(self):
        self.proof()
        self.change('specification/rules.json',lambda d:d['rules'][0].update(requirement='가능성을 단정한다.'))
        self.assertError('verification_evidence')
        self.assertEqual(0,self.check()['coverage']['verified_count'])

    def test_unlinked_holdout_cannot_verify_a_source_function(self):
        holdout,proof=self.proof()
        holdout['cases'][0]['ste_ids']=['1.2']
        path=self.root/'evaluation/functional-cases.json'
        path.write_text(json.dumps(holdout,ensure_ascii=False))
        proof['independent_cases_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root/'evaluation/functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.assertError('verification_evidence')

    def test_invalid_holdout_cannot_verify_meaning_changing_keep(self):
        holdout,proof=self.proof()
        holdout['cases'][0]['acceptable_output']='문제가 있습니다.'
        path=self.root/'evaluation/functional-cases.json'
        path.write_text(json.dumps(holdout,ensure_ascii=False))
        proof['independent_cases_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root/'evaluation/functional-review.json').write_text(json.dumps(proof,ensure_ascii=False))
        self.assertError('verification_evidence')

    def test_coverage_threshold_is_explicit(self):
        report=self.check(0.9)
        self.assertIn('coverage_threshold',[e['code'] for e in report['errors']])
        self.assertEqual([],self.check()['errors'])

    def test_keep_case_cannot_change_permission_to_command(self):
        self.change('examples/rule-cases.json',lambda d:d['cases'][0].update(input='파일을 삭제해도 됩니다.',expected={'decision':'keep','output':'파일을 삭제하세요.','reason':'단순화'}))
        self.assertError('case_invariant')

    def test_clarify_case_cannot_invent_actor(self):
        self.change('examples/rule-cases.json',lambda d:d['cases'][0].update(expected={'decision':'clarify','output':'관리자가 설정을 삭제합니다.','reason':'행위자가 알려지지 않음'}))
        self.assertError('case_invariant')

    def test_authored_case_cannot_masquerade_as_independent_evidence(self):
        self.change('examples/rule-cases.json',lambda d:d['cases'][0].update(origin='independent'))
        self.assertError('field_value')

    def test_every_rule_requires_linked_case(self):
        self.change('examples/rule-cases.json',lambda d:d.update(cases=[]))
        self.assertError('missing_case')

    def test_case_ids_are_unique_across_casefiles(self):
        self.change('examples/lexicon-cases.json',lambda d:d['cases'][0].update(id='CASE-1'))
        self.assertError('duplicate_case_id')

    def test_same_sense_alternative_cannot_change_meaning(self):
        self.change('lexicon/core.json',lambda d:d['entries'][0].update(alternatives=[{'entry_id':'KPL-SW-REVIEW','relation':'same_sense','condition':'항상'}]))
        self.assertError('alternative_semantics')

    def test_unknown_alternative_is_rejected(self):
        self.change('lexicon/core.json',lambda d:d['entries'][0].update(alternatives=[{'entry_id':'KPL-NONE','relation':'contextual','condition':'문맥이 같을 때'}]))
        self.assertError('unknown_entry')

    def test_descriptive_expression_has_an_explicit_editorial_category(self):
        self.change('lexicon/core.json',lambda d:d['entries'][0].update(pos='서술표현'))
        self.assertEqual([],self.check()['errors'])

    def test_domain_cannot_override_core_sense(self):
        self.change('lexicon/domains/software.json',lambda d:d['entries'][0].update(lemma='확인하다',sense_id='check'))
        self.assertError('sense_collision')

    def test_deprecated_alternative_is_not_a_usable_target(self):
        self.change('lexicon/domains/software.json',lambda d:d['entries'][0].update(status='deprecated',deprecated_since='0.2.0'))
        self.change('lexicon/core.json',lambda d:d['entries'][0].update(alternatives=[{'entry_id':'KPL-SW-REVIEW','relation':'contextual','condition':'변경 검토 때'}]))
        self.assertError('deprecated_target')

    def test_present_source_publication_fields_cannot_be_blank(self):
        self.change('specification/ste-crosswalk.json',lambda d:d['source'].update(title=''))
        self.assertError('field_type')

    def test_publication_fields_cannot_be_blank(self):
        self.change('specification/rules.json',lambda d:d['rules'][0].update(requirement=' '))
        self.assertError('field_type')

    def test_malformed_nested_reference_is_reported_without_crashing(self):
        self.change('lexicon/core.json',lambda d:d['entries'][0].update(alternatives=[{'entry_id':[],'relation':'contextual','condition':'문맥 확인'}]))
        self.assertTrue(self.check()['errors'])

    def test_malformed_ste_reference_list_is_reported_without_crashing(self):
        self.change('specification/rules.json',lambda d:d['rules'][0].update(ste_refs=None))
        self.assertError('field_type')

    def test_duplicate_json_keys_are_rejected_instead_of_overwritten(self):
        (self.root/'specification/rules.json').write_text('{"schema_version":"1.0","schema_version":"9.0","version":"0.2.0","rules":[]}')
        self.assertError('file_invalid')

    def test_cli_returns_nonzero_and_json_for_invalid_data(self):
        self.change('specification/rules.json',lambda d:d.update(rules=None))
        result=subprocess.run([sys.executable,'-m','validation.check','--root',str(self.root),'--json'],capture_output=True,text=True)
        self.assertEqual(1,result.returncode)
        self.assertTrue(json.loads(result.stdout)['errors'])


class CompilerTests(FixtureTests):
    def compile(self, output=None, budget=30*1024):
        from validation.compile import compile_profiles
        return compile_profiles(self.root,output or self.root,budget=budget)

    def test_profiles_embed_rules_and_meaning_guards(self):
        result=self.compile()
        self.assertEqual({'profiles/coding-agent.md','profiles/chat.md','profiles/work-document.md','pack/protocol.md'},set(result))
        for name in result:
            text=(self.root/name).read_text(encoding='utf-8')
            self.assertIn('가능성을 사실로 바꾸지 않는다.',text)
            self.assertIn('사용자의 상위 지침',text)
            self.assertIn('허락을 명령',text)
            self.assertIn('행위자',text)
        self.assertIn('lexicon/core.json',(self.root/'profiles/chat.md').read_text())

    def test_pack_preserves_notices_without_changing_profiles(self):
        self.compile()
        profiles = {name:(self.root/name).read_bytes() for name in
                    ('profiles/coding-agent.md','profiles/chat.md','profiles/work-document.md')}
        pack = (self.root/'pack/protocol.md').read_bytes()
        for name in ('LICENSE','NOTICE.md'):
            self.assertIn((self.root/name).read_bytes(),pack)
            with (self.root/name).open('a',encoding='utf-8') as handle:
                handle.write('Additional fixture notice.\n')
        self.compile()
        for name,original in profiles.items():
            self.assertEqual(original,(self.root/name).read_bytes())
            self.assertNotIn(b'Additional fixture notice.',original)
        pack = (self.root/'pack/protocol.md').read_bytes()
        for name in ('LICENSE','NOTICE.md'):
            self.assertIn((self.root/name).read_bytes(),pack)

    def test_missing_license_or_notice_prevents_any_compiled_output(self):
        for name in ('LICENSE','NOTICE.md'):
            with self.subTest(name=name):
                path = self.root/name
                original = path.read_bytes()
                path.rename(path.with_suffix('.missing'))
                with self.assertRaises(FileNotFoundError):
                    self.compile()
                self.assertFalse((self.root/'profiles/chat.md').exists())
                path.write_bytes(original)

    def test_invalid_input_does_not_write_profiles(self):
        self.change('examples/rule-cases.json',lambda d:d.update(cases=[]))
        with self.assertRaises(ValueError):self.compile()
        self.assertFalse((self.root/'profiles/chat.md').exists())

    def test_budget_failure_does_not_silently_truncate_or_partial_write(self):
        with self.assertRaises(ValueError):self.compile(budget=40)
        self.assertFalse((self.root/'profiles/chat.md').exists())

    def test_default_30_KiB_budget_keeps_full_boundary_text_and_rejects_one_more_byte(self):
        from validation.compile import compile_profiles
        baseline = self.root / 'baseline-output'
        compile_profiles(self.root, baseline)
        largest = max((baseline / 'profiles' / (name + '.md')).stat().st_size
                      for name in ('coding-agent', 'chat', 'work-document'))
        padding = 'x' * (30 * 1024 - largest)
        self.change('specification/rules.json', lambda data: data['rules'][0].update(
            requirement=data['rules'][0]['requirement'] + padding))
        output = self.root / 'boundary-output'
        compile_profiles(self.root, output)
        profiles = [output / 'profiles' / (name + '.md') for name in ('coding-agent', 'chat', 'work-document')]
        self.assertEqual(30 * 1024, max(path.stat().st_size for path in profiles))
        for path in profiles:
            self.assertIn(padding, path.read_text())
        self.change('specification/rules.json', lambda data: data['rules'][0].update(
            requirement=data['rules'][0]['requirement'] + 'x'))
        refused = self.root / 'refused-output'
        with self.assertRaisesRegex(ValueError, '30720-byte budget'):
            compile_profiles(self.root, refused)
        self.assertFalse(refused.exists())

    def test_compiler_omits_source_metadata_and_cases(self):
        self.change('specification/rules.json',lambda d:d['rules'][0]['references'][0].update(title='SECRET-RESEARCH-METADATA'))
        self.compile()
        for name in ['profiles/chat.md','pack/protocol.md']:
            self.assertNotIn('SECRET-RESEARCH-METADATA',(self.root/name).read_text())

    def test_detailed_pack_includes_authored_examples_and_exceptions(self):
        self.compile()
        text=(self.root/'pack/protocol.md').read_text()
        self.assertIn('문제가 있을 가능성이 있습니다.',text)
        self.assertIn('가능성을 사실로 바꾼다.',text)
        self.assertIn('문맥에서 알 수 있는 행위자는 생략한다.',text)

    def test_compilation_preserves_unrelated_existing_temporary_file(self):
        destination=self.root/'profiles/chat.md.tmp'
        destination.parent.mkdir()
        destination.write_text('사용자가 작성 중인 내용')
        self.compile()
        self.assertTrue(destination.exists())
        self.assertEqual('사용자가 작성 중인 내용',destination.read_text())

    def test_profiles_are_deterministic(self):
        self.compile()
        before=(self.root/'profiles/chat.md').read_bytes()
        self.compile()
        self.assertEqual(before,(self.root/'profiles/chat.md').read_bytes())


if __name__=='__main__':unittest.main()
