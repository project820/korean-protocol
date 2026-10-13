"""No model calls: validate isolation, freeze gates, and structural evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('lexicon_evaluator', HERE / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def fixture(self, base, condition='treatment', prepare_only=True):
        values = {'cases.json': {'cases': [dict(id=f'x{i}', explicit_context='context',
                  source='source', candidate='candidate', target_concept='concept',
                  expected_action='SECRET-GOLD', reason='SECRET-REASON') for i in range(12)]},
                  'core.json': {'entries': [{'id': 'KPL-0001'}]},
                  'software.json': {'entries': [{'id': 'KPL-SW-0001'}]},
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

    def test_prepare_excludes_gold_and_never_calls_model(self):
        for condition in ('baseline', 'treatment'):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as td:
                args = self.fixture(Path(td), condition)
                with patch.object(runner.shared, 'capture') as capture:
                    meta, parsed = runner.execute(args)
                capture.assert_not_called()
                self.assertIsNone(parsed)
                self.assertEqual(set(meta['mounted_files_sha256']),
                                 set(runner.MOUNT_PATHS) if condition == 'treatment' else set())
                for path in args.output.rglob('*'):
                    if path.is_file():
                        contents = path.read_text()
                        self.assertNotIn('SECRET-', contents)
                        self.assertNotIn('AUTH-DO-NOT-PRINT', contents)
                self.assertIn('not guarantee cwd-only reads', meta['read_boundary_limit'])

    def test_conditions_build_identical_public_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td))
            cases = runner.public_cases(args.cases)
            self.assertEqual(set(cases[0]), set(runner.PUBLIC_FIELDS))
            self.assertNotIn('expected_action', runner.build_prompt(cases))
            prompt = runner.build_prompt(cases)
            runner.execute(args)
            args.condition = 'baseline'
            args.output = Path(td) / 'baseline'
            runner.execute(args)
            self.assertEqual((args.output / 'prompt.txt').read_text(), prompt)
            self.assertEqual((Path(td) / 'output/prompt.txt').read_text(), prompt)

    def test_freeze_and_auth_gates_prevent_execution(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            with patch.object(runner.shared, 'capture') as capture:
                with self.assertRaisesRegex(ValueError, '--manifest is required'):
                    runner.execute(args)
                contract = runner.source_contract(args, runner.build_prompt(runner.public_cases(args.cases)))
                args.manifest = Path(td) / 'manifest.json'
                runner.shared.save_json(args.manifest, contract)
                args.profile.write_text('Unexpected source update')
                with self.assertRaisesRegex(ValueError, 'profile_sha256'):
                    runner.execute(args)
            capture.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_mocked_capture_sees_only_mounted_files_and_isolated_home(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.fixture(Path(td), prepare_only=False)
            args.model = 'anthropic/claude-opus-5-5'
            contract = runner.source_contract(args, runner.build_prompt(runner.public_cases(args.cases)))
            args.manifest = Path(td) / 'manifest.json'
            runner.shared.save_json(args.manifest, contract)

            def capture(command, prompt, out, timeout, env):
                project = Path(command[command.index('--cd') + 1])
                self.assertEqual(set(str(p.relative_to(project)) for p in project.rglob('*') if p.is_file()),
                                 set(runner.MOUNT_PATHS))
                self.assertNotIn('SECRET-', prompt)
                self.assertEqual([k for k in env if k.startswith('CODEX_')], ['CODEX_HOME'])
                self.assertTrue((Path(env['CODEX_HOME']) / 'auth.json').is_symlink())
                rows = [dict(id=c['id'], action='keep', text='made-up meaning', reason='reason',
                             used_entry_ids=['KPL-0001']) for c in runner.public_cases(args.cases)]
                (out / 'final.txt').write_text(json.dumps({'results': rows}), encoding='utf-8')
                trace = '{"type":"item.completed","item":{"type":"command_execution"}}\n'
                (out / 'stdout.jsonl').write_text(trace, encoding='utf-8')
                return {'exit_code': 0, 'timeout': False, 'launch_error': None,
                        'model_requested': 'gpt-6.1-sol', 'execution': 'mocked subprocess'}

            with patch.dict(runner.os.environ, {'CODEX_INJECTED': 'excluded'}), \
                    patch.object(runner.shared, 'capture', capture):
                meta, parsed = runner.execute(args)
            self.assertTrue(meta['execution_completed'])
            self.assertTrue(parsed['structure_valid'])
            self.assertEqual(meta['model_requested'], args.model)
            self.assertEqual(meta['mounted_files_sha256'], meta['mounted_files_sha256_after'])
            self.assertNotIn('semantic_score', parsed)
            self.assertIsNone(meta['upstream_provider_observed'])
            self.assertIn('command_execution', (args.output / 'stdout.jsonl').read_text())

    def test_command_selects_model_and_disables_web_and_other_agents(self):
        command = runner.make_command(Path('/temporary/project'), Path('/outside/final.txt'),
                                      'anthropic/claude-opus-5-5')
        self.assertEqual(command[command.index('--model') + 1], 'anthropic/claude-opus-5-5')
        for value in ('read-only', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                      'web_search="disabled"', 'features.multi_agent=false', 'approval_policy="never"',
                      'model_providers.subscription_router.base_url="http://127.0.0.1:10100/v1"'):
            self.assertIn(value, command)

    def test_entry_ids_validate_structure_without_semantic_claims(self):
        cases = [{'id': 'x'}]
        row = dict(id='x', action='keep', text='incorrect meaning', reason='reason', used_entry_ids=[])
        self.assertTrue(runner.parse_result(json.dumps({'results': [row]}), cases, set(),
                                           'baseline')['structure_valid'])
        for value in (None, 'KPL-0001', [1], ['unknown'], ['KPL-0001', 'KPL-0001']):
            with self.subTest(value=value):
                row['used_entry_ids'] = value
                parsed = runner.parse_result(json.dumps({'results': [row]}), cases,
                                             {'KPL-0001'}, 'treatment')
                self.assertFalse(parsed['structure_valid'])
        row['used_entry_ids'] = ['KPL-0001']
        self.assertFalse(runner.parse_result(json.dumps({'results': [row]}), cases,
                                            {'KPL-0001'}, 'baseline')['structure_valid'])


if __name__ == '__main__':
    unittest.main()
