import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ModelEvaluationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('llm_runner', ROOT / 'evaluation/llm/runner.py')
        self.assertTrue(spec.origin and pathlib.Path(spec.origin).exists(), 'runner implementation is missing')
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)

    def test_prompt_excludes_oracle_and_contains_same_cases(self):
        cases = self.runner.load_cases(ROOT / 'evaluation/llm/holdout.json')
        self.assertEqual(sum(c['set'] == 'holdout' for c in cases), 24)
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        prompt = self.runner.build_prompt(cases)
        self.assertNotIn('required_meaning', prompt)
        self.assertNotIn('allowed_actions', prompt)
        for case in cases:
            self.assertIn(case['source'], prompt)

    def test_parse_checks_structure_without_scoring_semantics(self):
        cases = [{'id': 'x'}]
        valid = json.dumps({'results': [{'id': 'x', 'action': 'rewrite', 'text': '창작한 사실', 'reason': '설명'}]})
        parsed = self.runner.parse_response(valid, cases)
        self.assertTrue(parsed['structure_valid'])
        self.assertNotIn('semantic_score', parsed)
        invalid = self.runner.parse_response('{bad', cases)
        self.assertFalse(invalid['structure_valid'])
        duplicate = json.dumps({'results': [{'id': 'x', 'action': 'keep', 'text': 'a', 'reason': ''}]*2})
        self.assertFalse(self.runner.parse_response(duplicate, cases)['structure_valid'])

    def test_command_and_isolated_home_preserve_auth_without_user_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            auth = base / 'private-auth.json'
            auth.write_text('private fixture')
            home = self.runner.make_home(base / 'isolated-home', auth)
            self.assertTrue((home / 'auth.json').is_symlink())
            self.assertFalse((home / 'AGENTS.md').exists())
            command = self.runner.build_command(base / 'project', base / 'final.txt')
            for flag in ['--ephemeral', '--ignore-user-config', '--ignore-rules', '--json', 'read-only']:
                self.assertIn(flag, command)
            self.assertIn('model_provider="subscription_router"', command)

    def test_capture_retains_nonzero_exit_and_actual_stream(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td)
            command = ['python3', '-c', 'import sys; print(sys.stdin.read()); print("failure",file=sys.stderr);sys.exit(7)']
            meta = self.runner.capture(command, 'actual prompt', out, timeout=5)
            self.assertEqual(meta['exit_code'], 7)
            self.assertEqual((out / 'stdout.jsonl').read_text(), 'actual prompt\n')
            self.assertEqual((out / 'stderr.txt').read_text(), 'failure\n')
            self.assertEqual((out / 'prompt.txt').read_text(), 'actual prompt')

    def test_model_project_has_no_repository_ancestor_and_profile_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            auth = base / 'auth-fixture'
            auth.write_text('fixture')
            profile = base / 'profile.md'
            profile.write_text('local instructions')
            projects = []

            def fake_command(project, final):
                projects.append(project)
                self.assertEqual((project / 'AGENTS.md').read_text(), 'local instructions')
                return ['python3', '-c', 'print("real isolated process")']

            with patch.object(self.runner, 'build_command', fake_command):
                self.runner.run_condition('treatment', [{'id': 'x', 'context': '', 'source': ''}],
                                          profile, base / 'out', auth, 5)
            self.assertNotIn(str(base / 'out'), str(projects[0]))
            self.assertEqual((base / 'out/instructions-snapshot/AGENTS.md').read_text(), 'local instructions')

    def test_frozen_profile_survives_source_updates(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            profile = base / 'profile.md'
            profile.write_text('first version')
            cases = ROOT / 'evaluation/llm/holdout.json'
            self.assertTrue(callable(getattr(self.runner, 'freeze_inputs', None)), 'immutable input snapshot is missing')
            frozen = self.runner.freeze_inputs(cases, profile, base)
            profile.write_text('new source version')
            self.assertEqual(frozen.read_text(), 'first version')
            meta = json.loads((base / 'frozen-inputs.json').read_text())
            self.assertEqual(meta['profile_sha256'], self.runner.digest(frozen))

    def test_generation_prompt_excludes_rubric_and_parses_natural_reply_without_action(self):
        cases = self.runner.load_cases(ROOT / 'evaluation/llm/generation-holdout.json')
        self.assertEqual(len(cases), 12)
        self.assertTrue(callable(getattr(self.runner, 'build_generation_prompt', None)), 'generation prompt is missing')
        prompt = self.runner.build_generation_prompt(cases)
        for field in ['required_facts', 'forbidden_inferences', 'speech_purpose', 'concision_criteria']:
            self.assertNotIn(field, prompt)
        for case in cases:
            self.assertIn(case['request'], prompt)
            self.assertIn(case['facts'][0], prompt)
        raw = json.dumps({'results': [{'id': c['id'], 'text': '자연스러운 한국어 답변입니다.'} for c in cases]})
        parsed = self.runner.parse_response(raw, cases, mode='generation')
        self.assertTrue(parsed['structure_valid'])
        self.assertNotIn('semantic_score', parsed)

    def test_generation_packet_preserves_facts_request_and_oracle_separately(self):
        cases = self.runner.load_cases(ROOT / 'evaluation/llm/generation-holdout.json')[:1]
        parsed = {'results': [{'id': cases[0]['id'], 'text': '실제 출력입니다.'}]}
        with tempfile.TemporaryDirectory() as td:
            self.runner.review_packet(cases, parsed, parsed, pathlib.Path(td), mode='generation')
            packet = json.loads((pathlib.Path(td) / 'blind-review.json').read_text())
            self.assertEqual(packet[0]['facts'], cases[0]['facts'])
            self.assertEqual(packet[0]['required_facts'], cases[0]['required_facts'])
            key = json.loads((pathlib.Path(td) / 'condition-key.json').read_text())
            self.assertEqual(set(key.values()), {'baseline', 'treatment'})


if __name__ == '__main__':
    unittest.main()
