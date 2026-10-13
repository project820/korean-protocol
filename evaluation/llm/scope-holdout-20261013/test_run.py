"""Offline checks for public inputs, frozen sources, and isolated generation."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('scope_holdout_evaluator', HERE / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def fixture(self, base, condition='treatment', prepare_only=True):
        values = {'cases.json': {'cases': [dict(id=f'x{i}', facts=['provided fact'],
                  request='requested answer', required_meaning='SECRET-GOLD',
                  expected_action='SECRET-ACTION', example='SECRET-EXAMPLE') for i in range(12)]},
                  'core.json': {'entries': [{'id': 'core-entry'}]},
                  'software.json': {'entries': [{'id': 'software-entry'}]},
                  'gold.json': {'gold': 'SECRET-ADJUDICATION'}}
        for name, value in values.items():
            (base / name).write_text(json.dumps(value), encoding='utf-8')
        (base / 'profile.md').write_text('Frozen profile', encoding='utf-8')
        (base / 'plan.md').write_text('Frozen plan', encoding='utf-8')
        (base / 'auth.json').write_text('AUTH-DO-NOT-PRINT', encoding='utf-8')
        return argparse.Namespace(condition=condition, output=base / 'output',
               cases=base / 'cases.json', core=base / 'core.json', software=base / 'software.json',
               adjudication=base / 'gold.json', plan=base / 'plan.md', profile=base / 'profile.md',
               auth=base / 'auth.json', prepare_only=prepare_only, manifest=None,
               model='gpt-6.1-sol', timeout=5)

    def freeze(self, args):
        contract = runner.source_contract(args, runner.build_prompt(runner.public_cases(args.cases)))
        args.manifest = args.cases.parent / 'manifest.json'
        runner.shared.save_json(args.manifest, contract)
        return contract

    def test_public_gold_exclusion_and_identical_condition_prompts(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td))
            cases = runner.public_cases(args.cases)
            self.assertEqual(set(cases[0]), {'id', 'facts', 'request'})
            prompt = runner.build_prompt(cases)
            self.assertEqual(prompt, runner.build_prompt(runner.shared.load_cases(args.cases)))
            for condition in ('baseline', 'treatment'):
                args.condition = condition
                args.output = Path(td) / condition
                with patch.object(runner.shared, 'capture') as capture:
                    meta, parsed = runner.execute(args)
                capture.assert_not_called()
                self.assertIsNone(parsed)
                self.assertEqual((args.output / 'prompt.txt').read_text(), prompt)
                for path in args.output.rglob('*'):
                    if path.is_file():
                        self.assertNotIn('SECRET-', path.read_text())
                        self.assertNotIn('AUTH-DO-NOT-PRINT', path.read_text())
                self.assertEqual(set(meta['mounted_files_sha256']),
                                 set(runner.MOUNT_PATHS) if condition == 'treatment' else set())

    def test_public_facts_accepts_string_or_string_list_and_rejects_bad_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td))
            value = json.loads(args.cases.read_text())
            for facts in ('provided fact', ['provided fact']):
                value['cases'][0]['facts'] = facts
                runner.shared.save_json(args.cases, value)
                self.assertEqual(runner.public_cases(args.cases)[0]['facts'], facts)
            for facts in ('', ' ', [], [''], [1], {'fact': 'text'}):
                value['cases'][0]['facts'] = facts
                runner.shared.save_json(args.cases, value)
                with self.subTest(facts=facts), self.assertRaises(ValueError):
                    runner.public_cases(args.cases)

    def test_manifest_mutations_reject_before_launch_or_output_creation(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            contract = self.freeze(args)
            with patch.object(runner.shared, 'capture') as capture:
                for key in contract:
                    changed = {**contract, key: 'mutated'}
                    runner.shared.save_json(args.manifest, changed)
                    with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                        runner.execute(args)
                    self.assertFalse(args.output.exists())
            capture.assert_not_called()

    def test_source_change_during_preparation_rejects_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            self.freeze(args)
            original_snapshot = runner.snapshot_sources

            def snapshot_then_mutate(args, out):
                snapshot = original_snapshot(args, out)
                args.adjudication.write_text('{"gold": "changed"}', encoding='utf-8')
                return snapshot

            with patch.object(runner, 'snapshot_sources', snapshot_then_mutate), \
                    patch.object(runner.shared, 'capture') as capture:
                with self.assertRaisesRegex(ValueError, 'adjudication_sha256'):
                    runner.execute(args)
            capture.assert_not_called()

    def test_case_count_and_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td))
            value = json.loads(args.cases.read_text())
            runner.shared.save_json(args.cases, {'cases': value['cases'][:11]})
            with self.assertRaisesRegex(ValueError, 'exactly 12'):
                runner.public_cases(args.cases)
            value['cases'][1]['id'] = value['cases'][0]['id']
            runner.shared.save_json(args.cases, value)
            with self.assertRaisesRegex(ValueError, 'Duplicate case ids'):
                runner.public_cases(args.cases)

    def test_source_mutation_rejects_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            self.freeze(args)
            args.profile.write_text('Changed profile', encoding='utf-8')
            with patch.object(runner.shared, 'capture') as capture:
                with self.assertRaisesRegex(ValueError, 'profile_sha256'):
                    runner.execute(args)
            capture.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_manifest_and_auth_are_required_for_actual_calls(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            with patch.object(runner.shared, 'capture') as capture:
                with self.assertRaisesRegex(ValueError, '--manifest is required'):
                    runner.execute(args)
                self.freeze(args)
                args.auth = Path(td) / 'missing-auth.json'
                with self.assertRaisesRegex(ValueError, 'auth.json is unavailable'):
                    runner.execute(args)
            capture.assert_not_called()

    def test_input_mounts_exact_and_isolated_home_at_mocked_launch(self):
        for condition in ('baseline', 'treatment'):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as td:
                args = self.fixture(Path(td), condition, prepare_only=False)
                args.model = 'anthropic/claude-opus-5-5'
                contract = self.freeze(args)

                def capture(command, prompt, out, timeout, env):
                    project = Path(command[command.index('--cd') + 1])
                    mounted = runner.mounted_hashes(project)
                    expected = dict(zip(runner.MOUNT_PATHS,
                                        (contract['profile_sha256'], contract['core_sha256'],
                                         contract['software_sha256']))) if condition == 'treatment' else {}
                    self.assertEqual(mounted, expected)
                    self.assertNotIn('SECRET-', prompt)
                    self.assertEqual([k for k in env if k.startswith('CODEX_')], ['CODEX_HOME'])
                    self.assertTrue((Path(env['CODEX_HOME']) / 'auth.json').is_symlink())
                    rows = [dict(id=c['id'], text='incorrect meaning')
                            for c in runner.public_cases(args.cases)]
                    (out / 'final.txt').write_text(json.dumps({'results': rows}), encoding='utf-8')
                    (out / 'stdout.jsonl').write_text('{"type":"item.completed"}\n', encoding='utf-8')
                    return {'exit_code': 0, 'timeout': False, 'launch_error': None,
                            'model_requested': 'gpt-6.1-sol', 'execution': 'mocked subprocess'}

                with patch.dict(runner.os.environ, {'CODEX_INJECTED': 'excluded'}), \
                        patch.object(runner.shared, 'capture', capture):
                    meta, parsed = runner.execute(args)
                self.assertTrue(meta['execution_completed'])
                self.assertTrue(parsed['structure_valid'])
                self.assertEqual(meta['model_requested'], args.model)
                self.assertEqual(meta['mounted_files_sha256'], meta['mounted_files_sha256_after'])
                self.assertEqual(meta['trace_audit'], 'required; not performed')
                self.assertIn('does not guarantee cwd-only reads', meta['read_boundary_limit'])
                self.assertNotIn('semantic_score', parsed)
                self.assertIsNone(meta['upstream_provider_observed'])

    def test_output_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td))
            args.output.mkdir()
            sentinel = args.output / 'existing.txt'
            sentinel.write_text('preserve me', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                runner.execute(args)
            self.assertEqual(sentinel.read_text(), 'preserve me')

    def test_generation_structure_is_strict_but_not_semantic_grading(self):
        cases = [{'id': 'x'}]
        valid = {'results': [{'id': 'x', 'text': 'incorrect meaning'}]}
        self.assertTrue(runner.parse_result(json.dumps(valid), cases)['structure_valid'])
        invalid = [ {'results': [{'id': 'x', 'text': 'answer', 'action': 'keep'}]},
                    {'results': [{'id': 'x', 'text': 'answer', 'reason': 'extra'}]},
                    {'results': [{'id': 'x', 'text': ''}]},
                    {'results': [{'id': 'y', 'text': 'answer'}]},
                    {'results': [{'id': 'x', 'text': 1}]},
                    {'results': [None]}, {'results': []}, {'results': 'text'},
                    {'results': valid['results'], 'score': 100} ]
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(runner.parse_result(json.dumps(value), cases)['structure_valid'])

    def test_command_routes_requested_model_high_without_global_config(self):
        command = runner.make_command(Path('/temporary/project'), Path('/outside/final.txt'),
                                      'anthropic/claude-opus-5-5')
        self.assertEqual(command[command.index('--model') + 1], 'anthropic/claude-opus-5-5')
        for value in ('read-only', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                      'web_search="disabled"', 'features.multi_agent=false', 'approval_policy="never"',
                      'model_reasoning_effort="high"',
                      'model_providers.subscription_router.base_url="http://127.0.0.1:10100/v1"'):
            self.assertIn(value, command)


if __name__ == '__main__':
    unittest.main()
