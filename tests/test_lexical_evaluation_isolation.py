"""Verify frozen catalog overrides without changing local instruction mounts."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'evaluation/llm/lexical-meaning-use-20261013'
SPEC = importlib.util.spec_from_file_location('lexical_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class LexicalIsolationTests(unittest.TestCase):
    def test_command_disables_frozen_catalog_and_preserves_local_read_tools(self):
        skills = runner.load_disabled_skills(HERE / 'disabled-skills.json')
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / 'codex-home'
            command = runner.make_command(Path(td) / 'project', Path(td) / 'final.txt',
                                          'gpt-6.1-sol', home, skills)
            self.assertEqual(command[-1], '-')
            self.assertEqual(command[command.index('--model') + 1], 'gpt-6.1-sol')
            self.assertEqual(command[command.index('--sandbox') + 1], 'read-only')
            for flag in ('--ignore-user-config', '--ignore-rules', '--ephemeral'):
                self.assertIn(flag, command)
            for override in runner.ISOLATION_FEATURES:
                self.assertIn(override, command)
            self.assertNotIn('features.shell_tool=false', command)
            self.assertNotIn('project_doc_max_bytes=0', command)
            config = next(value for value in command if value.startswith('skills.config='))
            paths = re.findall(r'\{path=("(?:\\.|[^"\\])*"),enabled=false\}', config)
            self.assertEqual(len(paths), len(skills))
            actual = [json.loads(value) for value in paths]
            expected = [str(home.resolve() / skill['path']) if skill['scope'] == 'system'
                        else skill['path'] for skill in skills]
            self.assertEqual(actual, expected)
            self.assertTrue(all(str(home.resolve()) in path for path, skill in zip(actual, skills)
                                if skill['scope'] == 'system'))

    def test_prepare_contract_freezes_registry_and_condition_mounts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cases = root / 'cases.json'
            cases.write_text(json.dumps({'cases': [{'id': str(i), 'facts': ['fact'],
                                                     'request': 'request'} for i in range(12)]}))
            sources = {}
            for field in ('profile', 'core', 'software', 'plan', 'adjudication'):
                path = root / field
                path.write_text(field)
                sources[field] = path
            registry = root / 'disabled-skills.json'
            registry.write_bytes((HERE / 'disabled-skills.json').read_bytes())
            contracts = []
            for condition in ('baseline', 'ste', 'treatment'):
                args = argparse.Namespace(cases=cases, condition=condition,
                                          output=root / condition, disabled_skills=registry,
                                          model='gpt-6.1-sol', prepare_only=True, **sources)
                meta, parsed = runner.execute(args)
                self.assertIsNone(parsed)
                contracts.append(meta['input_contract'])
                expected = (set() if condition == 'baseline' else {'AGENTS.md'}
                            if condition == 'ste' else set(runner.MOUNT_PATHS))
                self.assertEqual(set(meta['mounted_files_sha256']), expected)
                self.assertEqual(meta['input_contract']['disabled_skills_sha256'],
                                 runner.shared.digest(registry))
                self.assertEqual(meta['disabled_skill_count'], 57)
                if condition in ('ste', 'treatment'):
                    self.assertEqual((args.output / 'inputs-snapshot/AGENTS.md').read_text(), 'profile')
            self.assertEqual(contracts[0], contracts[1])
            self.assertEqual(contracts[1], contracts[2])
            registry.write_text(registry.read_text() + '\n')
            changed = runner.source_contract(args, runner.build_prompt(runner.public_cases(cases)))
            self.assertNotEqual(changed['disabled_skills_sha256'], contracts[0]['disabled_skills_sha256'])

    def test_registry_rejects_paths_outside_isolated_system_home(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'registry.json'
            for invalid in ('/absolute/SKILL.md', 'skills/.system/../other/SKILL.md',
                            'skills/unbundled/SKILL.md'):
                path.write_text(json.dumps({'skills': [{'scope': 'system', 'path': invalid}]}))
                with self.assertRaises(ValueError):
                    runner.load_disabled_skills(path)
            path.write_text(json.dumps({'skills': [{'scope': 'user', 'path': 'relative/SKILL.md'}]}))
            with self.assertRaises(ValueError):
                runner.load_disabled_skills(path)


if __name__ == '__main__':
    unittest.main()
