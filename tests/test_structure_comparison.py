"""Offline checks for experimental isolation, frozen inputs and raw capture."""
import importlib.util
import http.client
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'structure_comparison', ROOT / 'evaluation/readme-structure-r1-20261015/run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def terminal(text='  ## 원문\r\n\r\n- 조건 유지  \n', **overrides):
    response = dict(id='synthetic-offline-only', status='completed', model=runner.MODEL,
                    usage={'input_tokens': 10, 'output_tokens': 8},
                    output=[{'type': 'message', 'role': 'assistant', 'status': 'completed',
                             'content': [{'type': 'output_text', 'text': text}]}])
    response.update(overrides)
    return ('data: ' + json.dumps({'type': 'response.completed', 'response': response},
                                  ensure_ascii=False) + '\n\ndata: [DONE]\n\n').encode('utf-8')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.new = self.directory / 'experiment'
        self.new.mkdir()
        self.old = self.directory / 'old'
        self.old.mkdir()
        (self.new / 'candidate-profile.md').write_bytes(b'CANDIDATE PROFILE\r\n')
        runner.dump(self.new / 'criteria.json', {'meaning_gate': 'preserve', 'structure_gate': 'check'})
        runner.dump(self.new / 'token-budget.json',
                    {'profile_sha256': runner.sha((self.new / 'candidate-profile.md').read_bytes()),
                     'ceiling': 6000, 'passed': True, 'counters': {'fixture': 10}})
        self.cases = [dict(id=f'{n:02}', title='TITLE MUST NOT ENTER PROMPT',
                           anchor=f'case-{n}', source=f'Actual source {n}') for n in range(1, 7)]
        self.material = {'profiles/coding-agent.md': b'BASELINE PROFILE\n',
                         'lexicon/core.json': b'CORE FULL DICTIONARY',
                         'lexicon/domains/software.json': b'SOFTWARE FULL DICTIONARY',
                         'README.md': b'FROZEN README'}
        for target, value in (('cases.json', self.cases), ('ste-profile.md', 'STE')):
            if isinstance(value, list):
                runner.dump(self.old / target, value)
            else:
                (self.old / target).write_text(value, encoding='utf-8')
        (self.old / 'run.py').write_bytes(b'OLD RUNNER')
        baseline = dict(runner_sha256=runner.sha(b'OLD RUNNER'),
                        cases_sha256=runner.sha((self.old / 'cases.json').read_bytes()),
                        source_commit=runner.old.SOURCE_COMMIT, model_requested=runner.MODEL,
                        effort='medium', task=runner.TASK, conditions=['kp', 'ste'],
                        source_sha256=runner.sha(self.material['README.md']),
                        kp_inputs={p: runner.sha(self.material[p]) for p in runner.old.KP_FILES})
        runner.dump(self.old / 'plan.json', baseline)
        for folder in ('records', 'outputs'):
            (self.old / folder).mkdir()
        for case in self.cases:
            for arm in ('kp', 'ste'):
                name = case['id'] + '-' + arm
                raw = ('Saved output ' + name).encode('utf-8')
                (self.old / 'outputs' / (name + '.txt')).write_bytes(raw)
                runner.dump(self.old / 'records' / (name + '.json'),
                            dict(status='completed', returned_model=runner.MODEL,
                                 source_sha256=runner.sha(case['source'].encode('utf-8')),
                                 output_sha256=runner.sha(raw)))
        for name, value in (('HERE', self.new), ('OLD', self.old),
                            ('frozen_file', self.material.__getitem__)):
            active = patch.object(runner, name, value)
            active.start()
            self.addCleanup(active.stop)


class PromptTests(Fixture):
    def test_full_dictionary_arm_is_not_available(self):
        with self.assertRaisesRegex(ValueError, 'Unknown arm'):
            runner.request_body(self.cases[0], 'candidate-full')

    def test_profile_only_arms_have_no_dictionary_or_case_title(self):
        baseline = runner.request_body(self.cases[0], 'baseline-profile')
        candidate = runner.request_body(self.cases[0], 'candidate-profile')
        for body in (baseline, candidate):
            prompt = body['input'][0]['content'][0]['text']
            self.assertEqual(1, len(body['input']))
            self.assertEqual([], body['tools'])
            self.assertNotIn('previous_response_id', body)
            self.assertNotIn('instructions', body)
            self.assertNotIn(self.cases[0]['title'], prompt)
            self.assertNotIn('lexicon/', prompt)
            self.assertNotIn('FULL DICTIONARY', prompt)
            self.assertTrue(prompt.endswith(self.cases[0]['source']))
            self.assertIn(runner.TASK, prompt)
        baseline['input'][0]['content'][0]['text'] = baseline['input'][0]['content'][0]['text'].replace(
            'BASELINE PROFILE\n', 'CANDIDATE PROFILE\r\n', 1)
        self.assertEqual(baseline, candidate)


class FreezeTests(Fixture):
    def test_prepare_and_verify_make_no_network_calls_and_copy_exact_sources(self):
        with patch.object(runner.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            plan = runner.prepare()
            cases, loaded = runner.verify(require_complete=False)
        self.assertEqual(self.cases, cases)
        self.assertEqual(plan, loaded)
        self.assertEqual((self.old / 'cases.json').read_bytes(), (self.new / 'cases.json').read_bytes())
        self.assertEqual(12, len(plan['request_sha256']))
        self.assertEqual(12, plan['planned_calls'])
        self.assertEqual(plan['criteria_sha256'], runner.read_json(self.new / 'freeze.json')['criteria_sha256'])
        self.assertEqual(plan['token_budget_sha256'], runner.read_json(self.new / 'freeze.json')['token_budget_sha256'])
        self.assertIn('not installed-profile', plan['scope']['limits'])
        with self.assertRaisesRegex(ValueError, 'cannot overwrite'):
            runner.prepare()

    def test_frozen_candidate_cases_plan_dictionary_old_output_and_runner_drift_fail(self):
        runner.prepare()
        for path in (self.new / 'candidate-profile.md', self.new / 'criteria.json',
                     self.new / 'token-budget.json', self.new / 'cases.json',
                     self.new / 'plan.json', self.old / 'outputs/01-kp.txt'):
            before = path.read_bytes()
            path.write_bytes(before + b' ')
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                runner.verify(require_complete=False)
            path.write_bytes(before)
        with patch.object(runner, 'frozen_file', lambda path: self.material[path] + b'changed'):
            with self.assertRaisesRegex(ValueError, 'dictionary drift'):
                runner.verify(require_complete=False)
        with patch.object(runner, '__file__', str(self.old / 'run.py')):
            with self.assertRaisesRegex(ValueError, 'Runner drift'):
                runner.verify(require_complete=False)


class RawCaptureTests(Fixture):
    def prepare_capture(self, raw):
        runner.prepare()
        (self.new / 'outputs').mkdir()
        (self.new / 'records').mkdir()
        private = self.directory / 'private-wire'
        private.mkdir()

        class Response:
            status = 200

            def __init__(self):
                self.remaining = raw

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, count):
                chunk, self.remaining = self.remaining[:count], self.remaining[count:]
                return chunk

        return private, Response

    def test_exact_capture_preserves_raw_terminal_whitespace_without_editorial(self):
        text = '  ## 원문\r\n\r\n- 조건 유지  \n'
        raw = terminal(text)
        private, response = self.prepare_capture(raw)
        with patch.object(runner.urllib.request, 'urlopen', return_value=response()) as network:
            record = runner.execute((self.cases[0], 'candidate-profile'), private)
        self.assertEqual(1, network.call_count)
        self.assertEqual('completed', record['status'])
        self.assertEqual(text.encode('utf-8'), (self.new / 'outputs/01-candidate-profile.txt').read_bytes())
        self.assertEqual(raw, (private / '01-candidate-profile/response.raw').read_bytes())
        self.assertEqual(runner.sha(raw), record['response_sha256'])
        self.assertNotIn(str(private), json.dumps(record))
        self.assertTrue(record['token_budget_pass'])
        with self.assertRaises(FileExistsError):
            runner.execute((self.cases[0], 'candidate-profile'), private)

    def test_invalid_truncated_and_substituted_responses_fail_without_retry_or_output(self):
        for raw in (b'data: {"type":"response.created"}\n\n',
                    terminal(model='other-model'), terminal(incomplete_details={'reason': 'max_output_tokens'}),
                    terminal(status='incomplete'), terminal() + b'data: {bad json}\n'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                runner.extract_strict(raw)

    def test_terminal_completion_does_not_hide_extra_messages_content_or_stream_errors(self):
        message = {'type': 'message', 'role': 'assistant', 'status': 'completed',
                   'content': [{'type': 'output_text', 'text': '본문'}]}
        foreign_message = dict(message, role='user')
        refusal_content = dict(message, content=message['content'] + [{'type': 'refusal', 'refusal': 'no'}])
        tool_call = {'type': 'function_call', 'name': 'unexpected-tool', 'status': 'completed'}
        samples = [terminal(output=[message, foreign_message]), terminal(output=[refusal_content]),
                   terminal(output=[message, tool_call]),
                   b'data: {"type":"error","message":"broken"}\n\n' + terminal()]
        for raw in samples:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                runner.extract_strict(raw)

    def test_model_mismatch_retains_failure_and_private_wire_without_output(self):
        raw = terminal(model='other-model')
        private, response = self.prepare_capture(raw)
        with patch.object(runner.urllib.request, 'urlopen', return_value=response()) as network:
            record = runner.execute((self.cases[0], 'candidate-profile'), private)
        self.assertEqual(1, network.call_count)
        self.assertEqual('failed', record['status'])
        self.assertEqual('other-model', record['returned_model'])
        self.assertFalse((self.new / 'outputs/01-candidate-profile.txt').exists())
        self.assertEqual(raw, (private / '01-candidate-profile/response.raw').read_bytes())
        self.assertNotIn(str(private), json.dumps(record))

    def test_input_drift_after_preflight_is_recorded_without_dispatch(self):
        private, _ = self.prepare_capture(terminal())
        (self.new / 'candidate-profile.md').write_bytes(b'Unexpected edit')
        with patch.object(runner.urllib.request, 'urlopen') as network:
            record = runner.execute((self.cases[0], 'candidate-profile'), private)
        network.assert_not_called()
        self.assertEqual('failed', record['status'])
        self.assertIn('request-validation', record['error'])
        self.assertFalse((self.new / 'outputs/01-candidate-profile.txt').exists())

    def test_criteria_drift_after_preflight_is_recorded_without_dispatch(self):
        private, _ = self.prepare_capture(terminal())
        (self.new / 'criteria.json').write_bytes(b'{}')
        with patch.object(runner.urllib.request, 'urlopen') as network:
            record = runner.execute((self.cases[0], 'candidate-profile'), private)
        network.assert_not_called()
        self.assertEqual('failed', record['status'])
        self.assertIn('request-validation', record['error'])
        self.assertFalse((self.new / 'outputs/01-candidate-profile.txt').exists())

    def test_partial_transport_bytes_are_retained_without_retry(self):
        private, response = self.prepare_capture(terminal())
        broken = response()
        broken.read = lambda count: (_ for _ in ()).throw(http.client.IncompleteRead(b'partial-wire'))
        with patch.object(runner.urllib.request, 'urlopen', return_value=broken) as network:
            record = runner.execute((self.cases[0], 'candidate-profile'), private)
        self.assertEqual(1, network.call_count)
        self.assertEqual('failed', record['status'])
        self.assertEqual(b'partial-wire', (private / '01-candidate-profile/response.raw').read_bytes())
        self.assertEqual(runner.sha(b'partial-wire'), record['response_sha256'])

    def test_offline_verifier_accepts_complete_fixture_and_rejects_output_drift(self):
        private, response = self.prepare_capture(terminal())
        with patch.object(runner.urllib.request, 'urlopen', side_effect=lambda *a, **kw: response()) as network:
            for case in self.cases:
                for arm in runner.ARMS:
                    runner.execute((case, arm), private)
        self.assertEqual(12, network.call_count)
        runner.verify()
        output = self.new / 'outputs/01-candidate-profile.txt'
        output.write_bytes(output.read_bytes().strip())
        with self.assertRaisesRegex(ValueError, 'Output drift'):
            runner.verify()

    def test_candidate_budget_failure_preserves_completed_response_and_exact_output(self):
        text = '  budget failure must retain this text\r\n'
        raw = terminal(text, usage={'input_tokens': 6001, 'output_tokens': 10})
        private, response = self.prepare_capture(raw)
        with patch.object(runner.urllib.request, 'urlopen', side_effect=lambda *a, **kw: response()):
            for case in self.cases:
                for arm in runner.ARMS:
                    record = runner.execute((case, arm), private)
                    self.assertEqual('completed', record['status'])
                    if arm == 'candidate-profile':
                        self.assertFalse(record['token_budget_pass'])
                    else:
                        self.assertNotIn('token_budget_pass', record)
        output = self.new / 'outputs/01-candidate-profile.txt'
        self.assertEqual(text.encode('utf-8'), output.read_bytes())
        with self.assertRaisesRegex(ValueError, 'budget gate failed; raw outputs retained'):
            runner.verify()
        self.assertEqual(text.encode('utf-8'), output.read_bytes())

    def test_token_budget_rejects_missing_usage_and_accepts_exact_ceiling(self):
        for usage in (None, {}, {'input_tokens': True}, {'input_tokens': -1}, {'input_tokens': 6001}):
            with self.subTest(usage=usage):
                self.assertFalse(runner.candidate_budget_pass(usage))
        self.assertTrue(runner.candidate_budget_pass({'input_tokens': 6000}))

    def test_prepare_rejects_unpassed_or_wrong_profile_token_budget(self):
        path = self.new / 'token-budget.json'
        original = runner.read_json(path)
        for change in ({'passed': False}, {'profile_sha256': 'wrong'}, {'ceiling': 6001}, {'counters': {}}):
            path.write_text(json.dumps(dict(original, **change)), encoding='utf-8')
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, '[Tt]oken budget'):
                runner.prepare()


if __name__ == '__main__':
    unittest.main()
