"""Observed-label recognition tests; no model or browser dependency is required."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'evaluation/output_formats/browser_check.mjs'


def button(text, index, **kwargs):
    return {'text': text, 'index': index, 'visible': True, 'disabled': False,
            'id': 'opaque-' + str(index), 'type': 'button', **kwargs}


class BrowserControlRecognitionTests(unittest.TestCase):
    def recognize(self, buttons, operation='reset', pattern=None):
        request = {'buttons': buttons, 'operation': operation}
        if pattern is not None:
            request['pattern'] = pattern
        result = subprocess.run(['node', str(CHECKER), '--recognize-controls'],
                                input=json.dumps(request, ensure_ascii=False),
                                capture_output=True, text=True)
        try:
            body = json.loads(result.stdout)
        except ValueError:
            self.fail('Recognizer must return JSON: ' + result.stderr)
        return result.returncode, body

    def test_observed_start_is_not_global_screen_reset(self):
        buttons = [button('검사 시작', 0), button('화면을 시작 상태로 되돌린다', 4)]
        code, result = self.recognize(buttons, 'action', '검사.*시작|시작')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['control']['index'], 0)

    def test_global_tool_reset_takes_priority_over_domain_initialization(self):
        buttons = [button('초기화를 선택한다(현재 가능하다)', 3),
                   button('설명 도구를 처음 상태로 되돌린다', 4)]
        code, result = self.recognize(buttons)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['control']['index'], 4)

    def test_domain_initialization_can_be_selected(self):
        buttons = [button('초기화를 선택한다(현재 가능하다)', 3), button('도구 초기화', 4)]
        code, result = self.recognize(buttons, 'action', '초기화')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['control']['index'], 3)

    def test_observed_multiline_domain_transition_is_not_global_reset(self):
        buttons = [button('초기화\n완료 → 대기\n가능', 3), button('도구 초기화', 4)]
        code, result = self.recognize(buttons, 'action', '초기화')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['control']['index'], 3)

    def test_single_numeric_reset_label_is_still_supported(self):
        for text in ['초기값으로 되돌린다', '초기화', '리셋', 'reset']:
            with self.subTest(text=text):
                code, result = self.recognize([button(text, 0)])
                self.assertEqual(code, 0, result)

    def test_native_single_reset_control_is_supported(self):
        code, result = self.recognize([button('다시 계산한다', 0, type='reset')])
        self.assertEqual(code, 0, result)

    def test_disabled_or_hidden_global_reset_does_not_fall_back_to_domain(self):
        for availability in [{'disabled': True}, {'visible': False}]:
            with self.subTest(availability=availability):
                code, result = self.recognize([button('초기화', 3), button('도구 초기화', 4, **availability)])
                self.assertEqual(code, 1, result)
                self.assertEqual(result['status'], 'unrecognized')

    def test_two_explicit_global_resets_remain_ambiguous(self):
        code, result = self.recognize([button('도구 초기화', 1), button('화면을 처음 상태로 되돌린다', 2)])
        self.assertEqual(code, 1, result)

    def test_two_unscoped_resets_remain_ambiguous_even_with_friendly_id(self):
        code, result = self.recognize([button('초기화', 1, id='tool-reset'), button('초기화', 2)])
        self.assertEqual(code, 1, result)

    def test_two_domain_actions_remain_ambiguous(self):
        code, result = self.recognize([button('검사 시작', 1), button('시작한다', 2)], 'action', '시작')
        self.assertEqual(code, 1, result)

    def recognize_state(self, results):
        request = {'operation': 'state', 'state': {'results': results},
                   'spec': {'states': ['대기', '확인 중', '완료']}}
        result = subprocess.run(['node', str(CHECKER), '--recognize-controls'],
                                input=json.dumps(request, ensure_ascii=False), capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_current_state_ignores_decorative_hidden_ancestor_regions(self):
        regions = [{'tag': 'span', 'id': '', 'text': '대기', 'aria_hidden': True},
                   {'tag': 'strong', 'id': 'currentState', 'text': '확인 중'},
                   {'tag': 'p', 'id': '', 'text': '현재 상태: 확인 중', 'aria_live': 'polite'}]
        code, result = self.recognize_state(regions)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['current']['name'], '확인 중')

    def test_current_output_takes_precedence_over_unlabelled_state_list_values(self):
        regions = [{'tag': 'span', 'id': '', 'text': name} for name in ['대기', '확인 중', '완료']]
        regions.append({'tag': 'output', 'id': 'opaque-display', 'text': '확인 중'})
        code, result = self.recognize_state(regions)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['current']['name'], '확인 중')

    def test_conflicting_current_state_evidence_remains_unknown(self):
        regions = [{'tag': 'output', 'id': '', 'text': '대기'},
                   {'tag': 'p', 'id': '', 'text': '현재 상태: 완료', 'aria_live': 'polite'}]
        code, result = self.recognize_state(regions)
        self.assertEqual(code, 1, result)

    def test_unlabelled_different_state_values_remain_unknown(self):
        code, result = self.recognize_state([{'tag': 'span', 'id': '', 'text': name} for name in ['대기', '완료']])
        self.assertEqual(code, 1, result)


MACHINE_FIXTURE = '''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>상태를 확인한다</title>
<style>body{max-width:36rem;margin:auto;padding:1rem}button{display:block;max-width:100%;margin:1rem 0;white-space:normal}</style>
</head><body><h1>검사 상태를 확인한다</h1>
<div aria-hidden="true"><span id="decorative-waiting" class="state">대기</span><span class="state">확인 중</span><span class="state">완료</span></div>
<output id="state" aria-live="polite">대기</output>
<button type="button">검사 시작</button><button type="button">통과</button>
<button type="button">취소</button><button type="button">초기화를 선택한다</button>
<button type="button">화면을 시작 상태로 되돌린다</button>
<script>
const buttons=[...document.querySelectorAll('button')];let state='대기';
function show(){document.getElementById('state').textContent=state;
buttons[0].disabled=state!=='대기';buttons[1].disabled=state!=='확인 중';
buttons[2].disabled=state!=='확인 중';buttons[3].disabled=state!=='완료';}
buttons[0].onclick=()=>{if(state==='대기')state='확인 중';show()};
buttons[1].onclick=()=>{if(state==='확인 중')state='완료';show()};
buttons[2].onclick=()=>{if(state==='확인 중')state='대기';show()};
buttons[3].onclick=()=>{if(state==='완료')state='대기';show()};
buttons[4].onclick=()=>{state='대기';show()};show();
</script></body></html>'''

NUMERIC_FIXTURE = '''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>총액을 계산한다</title>
<style>body{max-width:36rem;margin:auto;padding:1rem}input,button{display:block;max-width:100%;box-sizing:border-box}button{white-space:normal}</style>
</head><body><h1>총액을 계산한다</h1><form id="calculator">
<label for="a">매주 더하는 금액 a</label><input id="a" type="number" min="1000" max="5000" step="1" value="1000">
<label for="n">기간 n (주)</label><input id="n" type="number" min="1" max="12" step="1" value="1">
<button id="reset-calculator" type="button">초기값으로 되돌린다</button></form>
<output id="result" aria-live="polite">11000원</output><p id="error" role="alert" hidden>입력 범위와 정수를 확인해야 한다.</p>
<script>
const form=document.getElementById('calculator'),a=document.getElementById('a'),n=document.getElementById('n');
function update(){const valid=[a,n].every(x=>x.value!==''&&x.validity.valid);
[a,n].forEach(x=>x.setAttribute('aria-invalid',String(!x.validity.valid||x.value==='')));
document.getElementById('error').hidden=valid;document.getElementById('result').textContent=valid?(10000+Number(a.value)*Number(n.value))+'원':'계산을 보류한다';}
form.oninput=update;form.onchange=update;document.getElementById('reset-calculator').onclick=()=>{HTMLFormElement.prototype.reset.call(form);update()};update();
</script></body></html>'''

PLAYER_FIXTURE = '''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>재생 상태를 확인한다</title>
<style>body{max-width:36rem;margin:auto;padding:1rem}button{display:block;max-width:100%;margin:1rem 0;white-space:normal}</style>
</head><body><h1>재생 상태를 확인한다</h1><output id="state" aria-live="polite">정지</output>
<button type="button">시작</button><button type="button">멈춤</button>
<button type="button">계속</button><button type="button">종료</button><button type="button">도구 초기화</button>
<div id="history"></div><script>
const buttons=[...document.querySelectorAll('button')];let state='정지',entries=[];
function show(){document.getElementById('state').textContent=state;document.getElementById('history').textContent=entries.join(' / ');
buttons[0].disabled=state!=='정지';buttons[1].disabled=state!=='재생';buttons[2].disabled=state!=='일시정지';buttons[3].disabled=state==='정지';}
function move(next){state=next;entries.push(state);show()}
buttons[0].onclick=()=>move('재생');buttons[1].onclick=()=>move('일시정지');
buttons[2].onclick=()=>move('재생');buttons[3].onclick=()=>move('정지');
buttons[4].onclick=()=>{state='정지';entries=[];show()};show();
</script></body></html>'''


@unittest.skipUnless(os.environ.get('KP_PLAYWRIGHT_MODULE_ROOT'), 'Set KP_PLAYWRIGHT_MODULE_ROOT to an existing Playwright node_modules directory.')
class BrowserMechanicalIntegrationTests(unittest.TestCase):
    def run_browser(self, case_id, html, extended=False):
        # Keep each raw receipt and original fixture in a new directory for audit.
        directory = ROOT / 'output/kp-output-formats-20261020/browser-recognition-regression' / ('mechanical-' + uuid.uuid4().hex)
        directory.mkdir(parents=True, exist_ok=False)
        artifact = directory / 'artifact.html'
        artifact.write_text(html)
        command = ['node', str(CHECKER), '--case', case_id, '--html', str(artifact), '--output', str(directory / 'browser'),
                   '--output-sha256', hashlib.sha256(html.encode()).hexdigest(),
                   '--playwright-module-dir', os.environ['KP_PLAYWRIGHT_MODULE_ROOT']]
        if extended:
            source = '화면의 초기 상태는 대기다. 대기에서 검사 시작은 확인 중으로, 확인 중에서 통과는 완료로, 취소는 대기로 이동한다. 완료에서 초기화는 대기로 이동한다. 도구 전체 초기화는 어느 상태에서도 화면의 초기 상태로 되돌린다.'
            dataset = directory / 'dataset.json'
            dataset.write_text(json.dumps([{'id': 'D09', 'modality': 'L3', 'source': source}], ensure_ascii=False))
            spec = {'states': ['대기', '확인 중', '완료'], 'initial': '대기',
                    'actions': {'start': '시작', 'pass': '통과', 'cancel': '취소', 'initialize': '초기화'},
                    'chain': [['start', '확인 중'], ['pass', '완료'], ['initialize', '대기']],
                    'branch': [['start', '확인 중'], ['cancel', '대기']], 'invalid': 'pass',
                    'invalidCases': [{'setup': [], 'action': 'pass'}, {'setup': ['start'], 'action': 'initialize'}],
                    'resetSetups': [['start'], ['start', 'pass']], 'keyboardReturn': 'cancel'}
            oracle = directory / 'oracle.json'
            oracle.write_text(json.dumps({'cases': {'D09': {'kind': 'machine', 'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'spec': spec}}}, ensure_ascii=False))
            command += ['--dataset', str(dataset), '--oracle', str(oracle)]
        (directory / 'command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2))
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (directory / 'stdout.raw').write_text(result.stdout)
        (directory / 'stderr.raw').write_text(result.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((directory / 'browser/receipt.json').read_text())

    def test_domain_initialization_and_multiple_invalid_reset_cases(self):
        receipt = self.run_browser('D09', MACHINE_FIXTURE, extended=True)
        self.assertEqual(receipt['status'], 'pass')
        self.assertFalse(any(region['id'].startswith('decorative-') for region in receipt['initial_snapshot']['results']))
        change = receipt['actions']['change']['observations']
        self.assertEqual([step['name'] for step in change], ['start', 'pass', 'initialize', 'start', 'cancel'])
        self.assertEqual(change[2]['control']['control']['text'], '초기화를 선택한다')
        invalid = receipt['actions']['invalid']['observations']['cases']
        self.assertEqual([case['attempt'] for case in invalid], ['pass', 'initialize'])
        self.assertEqual(invalid[1]['before']['name'], '확인 중')
        reset = receipt['actions']['reset']['observations']['cases']
        self.assertEqual([case['setup'] for case in reset], [['start'], ['start', 'pass']])
        self.assertTrue(all(case['control']['text'] == '화면을 시작 상태로 되돌린다' for case in reset))

    def test_legacy_single_machine_scenarios_remain_supported(self):
        receipt = self.run_browser('D09', MACHINE_FIXTURE)
        self.assertEqual(receipt['status'], 'pass')
        self.assertEqual(receipt['actions']['invalid']['observations']['attempt'], 'pass')
        self.assertIn('control', receipt['actions']['reset']['observations'])

    def test_numeric_single_unscoped_reset_remains_supported(self):
        receipt = self.run_browser('D07', NUMERIC_FIXTURE)
        self.assertEqual(receipt['status'], 'pass')
        self.assertEqual(receipt['actions']['reset']['observations']['control']['text'], '초기값으로 되돌린다')

    def test_legacy_player_actions_and_history_reset_remain_supported(self):
        receipt = self.run_browser('E09', PLAYER_FIXTURE)
        self.assertEqual(receipt['status'], 'pass')
        self.assertEqual(receipt['actions']['reset']['observations']['history'], [{'id': 'history', 'text': ''}])


if __name__ == '__main__':
    unittest.main()
