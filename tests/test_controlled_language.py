"""Publication contracts for controlled Korean and speech-act preservation."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from validation.compile import compile_profiles

ROOT = Path(__file__).resolve().parents[1]
POLITE_ENDING = re.compile(r'(니다|세요|십시오|에요|예요|해요|어요|아요|까요)[.?!]?(\s|$)')
NORMALIZATION_MARKERS = ('기본 문체', '짧게', '짧은')


class ControlledLanguageTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads((ROOT / 'specification/rules.json').read_text())['rules']
        self.cases = json.loads((ROOT / 'examples/rule-cases.json').read_text())['cases']

    def test_compiled_profiles_scope_plain_default_and_keep_source_register(self):
        with tempfile.TemporaryDirectory() as folder:
            compile_profiles(ROOT, folder)
            for name in ('coding-agent', 'chat', 'work-document'):
                text = (Path(folder) / 'profiles' / (name + '.md')).read_text()
                self.assertIn('기존 글을 고칠 때는 확립된 문체를 유지한다', text)
                self.assertIn('사용자가 지정한 높임·장르', text)
                self.assertIn('짧은 명사형으로 쓴다', text)
                self.assertIn('확인할 수 없는 필수 정보만 묻는다', text)

    def test_plain_style_cases_preserve_each_speech_act(self):
        by_id = {case['id']: case for case in self.cases}
        expected = {
            'KP-KO-005-PLAIN-PERMISSION': '백업한 파일은 삭제해도 된다.',
            'KP-KO-005-PLAIN-REQUEST': '파일을 저장해 주기 바란다.',
            'KP-KO-005-PLAIN-QUESTION': '서버 배포가 끝났는가?',
            'KP-KO-005-PLAIN-DIRECTIVE': '다음 명령을 실행하라.',
            'KP-KO-005-PLAIN-PROHIBITION': '작업 중에는 전원 케이블을 뽑지 마라.',
        }
        for case_id, output in expected.items():
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            self.assertEqual(['KP-KO-005'], by_id[case_id]['rule_ids'])
            self.assertEqual('revise', by_id[case_id]['expected']['decision'])
            self.assertEqual(output, by_id[case_id]['expected']['output'])
            self.assertIn('기본 문체', by_id[case_id]['context'])

    def test_user_honorifics_quotes_and_source_register_remain_exact(self):
        by_id = {case['id']: case for case in self.cases}
        for case_id in ('KP-KO-005-USER-HONORIFICS', 'KP-KO-005-QUOTE', 'KP-KO-005-SOURCE-REGISTER'):
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            case = by_id[case_id]
            self.assertEqual('keep', case['expected']['decision'])
            self.assertEqual(case['input'], case['expected']['output'])

    def test_register_changes_only_with_explicit_normalization(self):
        pairs = [(case['id'], case['context'], case['input'], case['expected']['output'])
                 for case in self.cases if case['expected']['decision'] == 'revise']
        pairs += [(rule['id'], rule['positive_example']['context'], rule['positive_example']['before'],
                   rule['positive_example']['after']) for rule in self.rules]
        for key, context, before, after in pairs:
            if POLITE_ENDING.search(before) and not POLITE_ENDING.search(after):
                self.assertTrue(any(marker in context for marker in NORMALIZATION_MARKERS),
                                key + ' changes register without a normalization instruction')

    def test_controlled_structure_cases_cover_actions_terms_and_result(self):
        by_id = {case['id']: case for case in self.cases}
        expected = {
            'KP-PROC-001-INDEPENDENT': '1. 파일을 저장한다.\n2. 창을 닫는다.',
            'KP-WRD-002-CONSISTENT': '배포를 준비했다. 배포는 아직 시작하지 않았다.',
            'KP-DESC-001-RESULT': '배포에 실패했다. 인증 오류가 발생했다.',
            'KP-DESC-005-SURPLUS': '설정을 저장했다.',
        }
        for case_id, output in expected.items():
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            self.assertEqual(output, by_id[case_id]['expected']['output'])

    def test_missing_record_does_not_assert_absence_or_nonperformance(self):
        rule = next(rule for rule in self.rules if rule['id'] == 'KP-VER-008')
        self.assertTrue('미확인·미기록을 실제 부재·미수행으로 단정하지 않는다.' in rule['requirement'])
        by_id = {case['id']: case for case in self.cases}
        expected = {
            'KP-VER-008-ROLE-UNRECORDED': '회의록에 품질 검사 담당자가 적혀 있지 않다.',
            'KP-VER-008-TEST-UNRECORDED': '시험 기록을 확인하지 못했다.',
        }
        for case_id, output in expected.items():
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            self.assertEqual('author', by_id[case_id]['origin'])
            self.assertEqual('revise', by_id[case_id]['expected']['decision'])
            self.assertEqual(output, by_id[case_id]['expected']['output'])

    def test_concise_status_regressions_preserve_referent_scope_and_speech_act(self):
        by_id = {case['id']: case for case in self.cases}
        expected = {
            'KP-TXT-006-USER-ROLE-STATUS': '표기된 담당자 없음.',
            'KP-TXT-006-TEST-STATUS': '시험 기록 없음.',
            'KP-TXT-006-CHECK-STATUS': '타입 검사 통과.',
            'KP-TXT-006-DEPLOY-STATUS': '배포 미완료.',
            'KP-TXT-006-ACTION-NOT-STATUS': '밸브를 연다.',
        }
        for case_id, output in expected.items():
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            self.assertEqual('author', by_id[case_id]['origin'])
            self.assertEqual(output, by_id[case_id]['expected']['output'])
        self.assertEqual('user_regression', by_id['KP-TXT-006-USER-ROLE-STATUS']['case_type'])
        boundary = by_id.get('KP-TXT-006-CONDITION-CLAUSE')
        self.assertIsNotNone(boundary, 'condition boundary case is missing')
        self.assertEqual('keep', boundary['expected']['decision'])

    def test_all_72_rules_conditions_and_exceptions_fit_existing_budget(self):
        self.assertEqual(72, len(self.rules))
        with tempfile.TemporaryDirectory() as folder:
            compile_profiles(ROOT, folder)
            for name in ('coding-agent', 'chat', 'work-document'):
                path = Path(folder) / 'profiles' / (name + '.md')
                self.assertLessEqual(path.stat().st_size, 28 * 1024)
                text = path.read_text()
                for rule in self.rules:
                    self.assertIn(rule['id'] + ' ' + rule['requirement'], text)
                    for sentence in rule['conditions'] + rule['exceptions']:
                        self.assertIn(sentence, text)

    def test_compiled_profiles_state_request_scoped_output_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            compile_profiles(ROOT, folder)
            for name in ('coding-agent', 'chat', 'work-document'):
                text = (Path(folder) / 'profiles' / (name + '.md')).read_text()
                self.assertIn('요청에 필요한 결과·판단·행동만 쓴다', text)
                self.assertIn('요청과 무관한 입력 사실 재진술·명칭 통일 안내·작성 과정·누락 정보는 쓰지 않는다', text)
                self.assertIn('미기록을 부재·미배정으로 바꾸지 않는다', text)
        rules = {rule['id']: rule for rule in self.rules}
        self.assertIn('이미 밝힌 범위·양태', rules['KP-DESC-005']['requirement'])
        self.assertIn('번호 순서로 드러난 선행 조건', rules['KP-DESC-005']['requirement'])
        self.assertIn('실제 모호성', rules['KP-DESC-005']['exceptions'][0])
        self.assertIn('동시 유지·전역 조건', rules['KP-DESC-005']['exceptions'][0])
        self.assertIn('누가 맡았는지 묻고', rules['KP-EDIT-002']['requirement'])

    def test_compiled_profiles_keep_provided_verification_status(self):
        with tempfile.TemporaryDirectory() as folder:
            compile_profiles(ROOT, folder)
            for name in ('coding-agent', 'chat', 'work-document'):
                text = (Path(folder) / 'profiles' / (name + '.md')).read_text()
                self.assertIn('누락 정보는 쓰지 않는다. 제시된 검증 상태는 남긴다.', text)

    def test_output_contract_cases_drop_surplus_and_keep_needed_relations(self):
        by_id = {case['id']: case for case in self.cases}
        # id: (decision, rules that must be linked, required substrings, forbidden substrings)
        contract = {
            'KP-DESC-005-INPUT-RECITAL': ('revise', {'KP-DESC-005'}, ('3번 서버', '미완료'), ('요청', '통일', '아래')),
            'KP-DESC-005-MODALITY-ONCE': ('revise', {'KP-DESC-005', 'KP-VER-008'}, ('수 있다',), ('항상',)),
            'KP-DESC-005-LIMIT-ONCE': ('revise', {'KP-DESC-005'}, ('10MB까지',), ('넘는',)),
            'KP-DESC-005-IRRELEVANT-MISSING': ('revise', {'KP-DESC-005'}, ('단위 시험 통과',), ('작성자',)),
            'KP-DESC-005-SEQUENCE-PREREQ': ('revise', {'KP-DESC-005', 'KP-PROC-001'}, ('1. 전원을 끈다.', '2. 덮개를 연다.'), ('끈 뒤',)),
            'KP-DESC-005-GLOBAL-CONDITION': ('keep', {'KP-DESC-005', 'KP-PROC-005'}, ('모든 단계',), ()),
            'KP-DESC-005-SAFETY-REPEAT': ('keep', {'KP-DESC-005'}, ('경고',), ()),
            'KP-EDIT-002-ROLE-ASK': ('revise', {'KP-EDIT-002', 'KP-VER-008'}, ('누구',), ('지정', '배정')),
            'KP-EDIT-002-ROLE-DELEGATED': ('keep', {'KP-EDIT-002'}, ('지정',), ()),
        }
        for case_id, (decision, rule_ids, required, forbidden) in contract.items():
            self.assertTrue(case_id in by_id, case_id + ' is missing')
            case = by_id[case_id]
            output = case['expected']['output']
            self.assertEqual('author', case['origin'])
            self.assertEqual(decision, case['expected']['decision'], case_id)
            self.assertTrue(rule_ids <= set(case['rule_ids']), case_id)
            for part in required:
                self.assertIn(part, output, case_id)
            for part in forbidden:
                self.assertIn(part, case['input'], case_id + ' forbidden text must come from input')
                self.assertNotIn(part, output, case_id)
            if decision == 'revise':
                self.assertLess(len(output), len(case['input']), case_id + ' must be shorter')


if __name__ == '__main__':
    unittest.main()
