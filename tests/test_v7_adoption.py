"""Canonical V7 publication preserves full sources without growing host budgets."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from validation.compile import compile_profiles

ROOT = Path(__file__).resolve().parents[1]


class V7AdoptionTests(unittest.TestCase):
    def test_reviewed_publication_keeps_scope_exceptions_and_modality(self):
        rules = {rule['id']: rule for rule in json.loads((ROOT / 'specification/rules.json').read_text())['rules']}
        protected = {
            'KP-EDIT-001': ('간결화·용어 교체로 문장을 수정할 때', '사실 정정·내용 변경', '구조·목록·기한으로 재편한 결과는 출력 전'),
            'KP-EDIT-002': ('배정을 제안하지 않는다',),
            'KP-EDIT-004': ('전체 재작성·명료화', '필요할 때 분리·목록화', '같은 행동·상태임이 확인될 때만'),
            'KP-EDIT-005': ('규약 시험 결과나 수정 성과',),
            'KP-WRD-003': ('등록 뜻을 유지하면', '다른 뜻의 활용'),
            'KP-NAM-001': ('그 차이에 맞춰 쓰고',),
            'KP-NAM-002': ('기본 어휘 밖', '한 번 인용한 외부 고유명'),
            'KP-VER-004': ('여러 시점의 상태를 비교하거나', '날짜나 기준을 밝혀'),
            'KP-VER-007': ('문맥상 구별하고 서로 치환하지 않는다',),
            'KP-VER-008': ('결과로 보고하거나 고칠 때', '추정·가능성·확인·전언을 서로 구별한다'),
            'KP-SYN-006': ('문장을 나누거나', '기존 연결을 유지한다', '접속어 없이'),
            'KP-SYN-007': ('범위가 미정인', '그 범위를 바꾸지 않는 주변만 필요할 때', '제목·도입부+항목', '공통 조건이 모든 항목에 적용됨'),
            'KP-KO-001': ('역할이 하나로 회복되고',),
            'KP-KO-005': ('허락·발화 기능',),
            'KP-NUM-001': ('가능·허용 한도',),
            'KP-NUM-004': ('기본값을 무조건 값으로 바꾸지 않는다',),
            'KP-NUM-006': ('확인된 날짜·시각 기준을 밝힌다', '기간 기준은 추정해 채우지 않는다', '상대 시점', '미정인 기산 사건'),
            'KP-PROC-004': ('단독 단서를 뒤로 떨어뜨리지 않는다', '대상·조건별'),
            'KP-DESC-005': ('제시된 검증 상태', '제목·도입부·예고·맺음말·요약', '다른 위치의 UI 안내', '실제 모호성 해소', '위험 행동 직전 안전 경고'),
            'KP-TXT-001': ('등 여러 대상', '출처·제한은 적용 대상과 연결', '문장 안의 독립 항목도 분리', '범위는 KP-SYN-007', '선택·순서·공통 서술어', '목록으로 늘리지 않는다'),
            'KP-TXT-002': ('다른 역할은 도입부로 구별한다',),
            'KP-TXT-006': ('상태 보고·확인 항목·UI·표의 짧은 표현에서', '문장·도입부', '행동·시점이 달라지는 축약은 하지 않는다'),
        }
        for rule_id, clauses in protected.items():
            for clause in clauses:
                with self.subTest(rule=rule_id, clause=clause):
                    self.assertIn(clause, rules[rule_id]['publication']['text'])
        for rule_id, trigger in {
            'KP-EDIT-001': '구조·목록·기한 표시로 재편한 결과를 출력할 때',
            'KP-PROC-003': '하나의 조건 아래 두 개 이상의 후속 행동·결과가 있을 때',
            'KP-PROC-004': '대상·조건에 따라 기한이 달라질 때',
            'KP-NUM-006': '독자가 지켜야 할 마감·대기 시간·확인 기한이 있을 때',
        }.items():
            self.assertIn(trigger, rules[rule_id]['conditions'])

    def test_header_retains_workflow_user_settings_and_v7_precedence(self):
        from validation.compile import GUARDS
        self.assertIn('작성: 앵커 추출 → 목적별 정보 묶기 → 조건·참조 배치 → 분할·목록 → 중복 제거 → 양방향 대조.', GUARDS)
        self.assertIn('사용자가 지정하지 않으면 높임 없는 기본 문체', GUARDS)
        self.assertIn('경쟁 후보 없이 행위자가 하나로 회복되면 주체를 생략한다', GUARDS)
        self.assertIn('기존 규칙과 충돌하면 V7', GUARDS)
        self.assertNotIn('불가 설명으로 끝내지 않는다', GUARDS)

    def test_canonical_rules_adopt_r2_without_r3_length_quota(self):
        source = json.loads((ROOT / 'specification/rules.json').read_text())
        self.assertEqual('0.7.0-draft', source['version'])
        self.assertEqual(72, len(source['rules']))
        text = '\n'.join(rule['requirement'] for rule in source['rules'])
        for clause in ('대상 제목과 목록을 첫 본문 블록', '원문의 시간 구절', '기산 사건',
                       '공통 규칙', '진행 상태', '자동 처리', '대체 관계'):
            self.assertIn(clause, text)
        self.assertNotIn('원문보다 짧', text)

    def test_profiles_fit_unchanged_budget_and_pack_keeps_complete_sources(self):
        rules = json.loads((ROOT / 'specification/rules.json').read_text())['rules']
        with tempfile.TemporaryDirectory() as output:
            compile_profiles(ROOT, output)
            pack = (Path(output) / 'pack/protocol.md').read_text()
            for name in ('coding-agent', 'chat', 'work-document'):
                path = Path(output) / 'profiles' / (name + '.md')
                self.assertLessEqual(path.stat().st_size, 30 * 1024)
                text = path.read_text()
                for rule in rules:
                    publication = rule.get('publication')
                    self.assertIn(rule['id'], text)
                    if publication:
                        self.assertIn(publication['text'], text)
                    self.assertIn(rule['requirement'], pack)
                    for clause in rule['conditions'] + rule['exceptions']:
                        self.assertIn(clause, pack)

    def test_stale_publication_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'source'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            path = root / 'specification/rules.json'
            source = json.loads(path.read_text())
            rule = next(rule for rule in source['rules'] if rule.get('publication'))
            rule['exceptions'].append('새로 추가한 예외도 반드시 배포한다.')
            path.write_text(json.dumps(source, ensure_ascii=False))
            output = Path(temporary) / 'output'
            with self.assertRaisesRegex(ValueError, 'publication'):
                compile_profiles(root, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
