"""Temporary-directory package/install checks; no user skill installation occurs."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile


class SkillPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module('distribution.skill_package')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kp-skill-package-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        self.contents = {
            'skills/korean-protocol/SKILL.md': b'---\nname: korean-protocol\ndescription: Explicit Korean writing skill\n---\n\nBody stays identical.\n',
            'skills/korean-protocol/agents/openai.yaml': b'policy:\n  allow_implicit_invocation: false\n',
            'skills/korean-protocol/references/meaning-boundaries.md': b'meaning',
            'skills/korean-protocol/references/output-formats.md': b'formats',
            'skills/korean-protocol/assets/report.html': b'<html>template</html>',
            'specification/rules.json': b'{}', 'lexicon/core.json': b'{}',
            'lexicon/domains/software.json': b'{}', 'LICENSE': b'license', 'NOTICE.md': b'notice',
        }
        for name, data in self.contents.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.package = self.root / 'candidate.zip'
        self.build()
        self.targets = {'codex': self.root / 'agents/skills/korean-protocol',
                        'claude-code': self.root / 'claude/skills/korean-protocol'}
        self.backups = self.root / 'backups'
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.verifier = mock.Mock(return_value={'comparison_status': 'complete', 'quality_gate': 'pass'})

    def build(self):
        return self.module.build_package(self.source, self.package, base_commit='a' * 40)

    def install(self, **kwargs):
        return self.module.install_package(self.package, self.targets, self.backups,
                                           self.evidence, verifier=self.verifier, **kwargs)

    def test_build_is_deterministic_and_includes_all_resources(self):
        first = self.package.read_bytes()
        result = self.build()
        self.assertEqual(first, self.package.read_bytes())
        manifest, payload = self.module.verify_package(self.package)
        self.assertIn('assets/report.html', payload)
        self.assertEqual(manifest['source_hashes'], {
            name: hashlib.sha256(data).hexdigest() for name, data in self.contents.items()})
        self.assertEqual(result['package_sha256'], hashlib.sha256(first).hexdigest())
        self.assertEqual(manifest['provenance']['base_commit'], 'a' * 40)
        self.assertEqual(manifest['provenance']['kind'], 'working-tree-candidate')

    def test_script_is_hashed_and_bundled_without_evaluation_sources(self):
        source_name = 'skills/korean-protocol/scripts/check_html.py'
        script = self.source / source_name
        script.parent.mkdir(parents=True)
        script_bytes = b'raise RuntimeError("packaging must not execute this script")\n'
        script.write_bytes(script_bytes)
        unrelated = self.source / 'evaluation/output_formats/ste.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('evaluation-only control profile')
        self.build()
        manifest, payload = self.module.verify_package(self.package)
        self.assertEqual(payload['scripts/check_html.py'], script_bytes)
        self.assertEqual(manifest['source_hashes'][source_name], hashlib.sha256(script_bytes).hexdigest())
        self.assertEqual(manifest['files']['scripts/check_html.py'], hashlib.sha256(script_bytes).hexdigest())
        self.assertNotIn('evaluation/output_formats/ste.md', manifest['source_hashes'])
        with zipfile.ZipFile(self.package) as archive:
            self.assertEqual(archive.read('korean-protocol/scripts/check_html.py'), script_bytes)
            self.assertEqual(archive.getinfo('korean-protocol/scripts/check_html.py').external_attr >> 16 & 0o777, 0o644)
            self.assertEqual(set(archive.namelist()), {'MANIFEST.json'} | {
                'korean-protocol/' + name for name in payload})

    def test_forbidden_or_symlinked_source_is_rejected(self):
        forbidden = self.source / 'skills/korean-protocol/raw'
        forbidden.mkdir()
        (forbidden / 'recording.txt').write_text('private')
        with self.assertRaisesRegex(ValueError, 'forbidden'):
            self.build()
        (forbidden / 'recording.txt').unlink()
        forbidden.rmdir()
        (self.source / 'skills/korean-protocol/link').symlink_to(self.source / 'LICENSE')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.build()

    def test_tampered_package_is_rejected(self):
        with zipfile.ZipFile(self.package) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries['korean-protocol/SKILL.md'] += b'tampered'
        with zipfile.ZipFile(self.package, 'w') as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.install()
        self.assertFalse(self.backups.exists())

    def test_dry_run_does_not_write_and_requires_quality(self):
        result = self.install(dry_run=True)
        self.assertEqual(result['status'], 'planned')
        self.assertFalse(self.backups.exists())
        self.assertFalse(self.targets['codex'].exists())
        self.assertEqual(self.verifier.call_args.args[1], self.module.verify_package(self.package)[0]['source_hashes'])
        self.verifier.return_value = {'comparison_status': 'incomplete', 'quality_gate': 'fail'}
        with self.assertRaisesRegex(ValueError, 'quality'):
            self.install()

    def test_relative_evidence_path_is_resolved_before_verification(self):
        previous_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            self.module.require_quality(Path('evidence'), {'source': 'hash'},
                                        'candidate', 'package', verifier=self.verifier)
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(self.verifier.call_args.args[0], self.evidence.resolve())

    def test_flags_without_recomputed_evidence_cannot_install(self):
        (self.evidence / 'report.json').write_text('{"comparison_status":"complete","quality_gate":"pass"}')
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.module.install_package(self.package, self.targets, self.backups, self.evidence)
        self.assertFalse(self.targets['codex'].exists())

    def test_two_hosts_install_with_identical_body_and_rollback(self):
        result = self.install()
        codex = (self.targets['codex'] / 'SKILL.md').read_bytes()
        claude = (self.targets['claude-code'] / 'SKILL.md').read_bytes()
        self.assertEqual(codex.split(b'---\n', 2)[2], claude.split(b'---\n', 2)[2])
        self.assertIn(b'disable-model-invocation: true', claude)
        self.assertIn(b'user-invocable: true', claude)
        for path in self.targets.values():
            record = json.loads((path / 'INSTALLATION.json').read_text())
            self.assertIn('references/output-formats.md', record['files'])
            self.assertIn('assets/report.html', record['files'])
        self.module.rollback_installation(Path(result['transaction']))
        self.assertTrue(all(not path.exists() for path in self.targets.values()))

    def test_existing_legacy_files_and_unmanaged_extra_are_preserved(self):
        target = self.targets['codex']
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('old')
        (target / 'notes.txt').write_text('user note')
        (target / 'INSTALLATION.json').write_text(json.dumps({'version': 'v0.9.0', 'files': {
            'SKILL.md': hashlib.sha256(b'old').hexdigest()}}))
        result = self.install()
        self.assertEqual((target / 'notes.txt').read_text(), 'user note')
        self.module.rollback_installation(Path(result['transaction']))
        self.assertEqual((target / 'SKILL.md').read_text(), 'old')
        self.assertEqual((target / 'notes.txt').read_text(), 'user note')

    def test_modified_tracked_file_and_unknown_install_are_not_overwritten(self):
        target = self.targets['codex']
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('user edited')
        (target / 'INSTALLATION.json').write_text(json.dumps({'files': {
            'SKILL.md': hashlib.sha256(b'original').hexdigest()}}))
        with self.assertRaisesRegex(ValueError, 'modified'):
            self.install()
        self.assertEqual((target / 'SKILL.md').read_text(), 'user edited')
        (target / 'INSTALLATION.json').unlink()
        with self.assertRaisesRegex(ValueError, 'manifest'):
            self.install()

    def test_unmanaged_package_collision_and_backup_inside_skills_are_rejected(self):
        self.install()
        target = self.targets['codex']
        record = json.loads((target / 'INSTALLATION.json').read_text())
        del record['files']['assets/report.html']
        (target / 'INSTALLATION.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.install()
        with self.assertRaisesRegex(ValueError, 'backup'):
            self.module.install_package(self.package, self.targets, target.parent / 'backups',
                                        self.evidence, verifier=self.verifier)

    def test_failed_second_activation_restores_both_hosts(self):
        self.install()
        before = {host: (target / 'INSTALLATION.json').read_bytes() for host, target in self.targets.items()}
        real_replace = self.module.os.replace
        def fail_second(source, destination):
            if Path(destination) == self.targets['claude-code'] and Path(source).name == 'staged':
                raise OSError('injected second-host failure')
            return real_replace(source, destination)
        with mock.patch.object(self.module.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'second-host'):
                self.install()
        self.assertEqual(before, {host: (target / 'INSTALLATION.json').read_bytes() for host, target in self.targets.items()})

    def test_rollback_refuses_later_user_edits(self):
        result = self.install()
        (self.targets['codex'] / 'notes.txt').write_text('new user work')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.module.rollback_installation(Path(result['transaction']))
        self.assertEqual((self.targets['codex'] / 'notes.txt').read_text(), 'new user work')

    def test_claude_config_override_is_used(self):
        with mock.patch.dict('os.environ', {'CLAUDE_CONFIG_DIR': str(self.root / 'custom-claude')}):
            targets = self.module.default_targets(['claude-code'], home=self.root)
        self.assertEqual(targets['claude-code'], self.root / 'custom-claude/skills/korean-protocol')

    def test_edit_after_preflight_is_not_overwritten(self):
        self.install()
        original = self.module._inspect_existing
        def concurrent_edit(target, payload):
            result = original(target, payload)
            if target == self.targets['codex']:
                (target / 'SKILL.md').write_text('concurrent user edit')
            return result
        with mock.patch.object(self.module, '_inspect_existing', side_effect=concurrent_edit):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.install()
        self.assertEqual((self.targets['codex'] / 'SKILL.md').read_text(), 'concurrent user edit')

    def test_candidate_metadata_cannot_claim_signed_release(self):
        with zipfile.ZipFile(self.package) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(entries['MANIFEST.json'])
        manifest['provenance']['publisher_authenticated'] = True
        entries['MANIFEST.json'] = json.dumps(manifest).encode()
        with zipfile.ZipFile(self.package, 'w') as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.module.verify_package(self.package)

    def test_private_named_file_is_not_packaged(self):
        (self.source / 'skills/korean-protocol/references/private-notes.md').write_text('private')
        with self.assertRaisesRegex(ValueError, 'forbidden'):
            self.build()

    def test_backup_under_other_default_host_skills_is_rejected(self):
        targets = self.module.default_targets(['codex'], home=self.root)
        with self.assertRaisesRegex(ValueError, 'backup'):
            self.module.install_package(self.package, targets, self.root / '.claude/skills/archive',
                                        self.evidence, verifier=self.verifier)

    def test_false_outside_policy_does_not_disable_implicit_invocation(self):
        policy = self.source / 'skills/korean-protocol/agents/openai.yaml'
        policy.write_text('example:\n  allow_implicit_invocation: false\npolicy:\n  allow_implicit_invocation: true\n')
        with self.assertRaisesRegex(ValueError, 'implicit invocation'):
            self.build()

    def test_duplicate_yaml_fields_are_rejected(self):
        variants = [
            b'policy:\n  allow_implicit_invocation: false\npolicy:\n  allow_implicit_invocation: true\n',
            b'policy:\n  allow_implicit_invocation: false\n  allow_implicit_invocation: true\n',
        ]
        for data in variants:
            with self.subTest(policy=data):
                (self.source / 'skills/korean-protocol/agents/openai.yaml').write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'duplicate YAML'):
                    self.build()
        (self.source / 'skills/korean-protocol/agents/openai.yaml').write_bytes(
            self.contents['skills/korean-protocol/agents/openai.yaml'])
        for field in (b'name: another-name\n', b'description: another description\n'):
            with self.subTest(frontmatter=field):
                skill = self.contents['skills/korean-protocol/SKILL.md'].replace(b'---\n', b'---\n' + field, 1)
                (self.source / 'skills/korean-protocol/SKILL.md').write_bytes(skill)
                with self.assertRaisesRegex(ValueError, 'duplicate YAML'):
                    self.build()

    def test_description_must_be_a_nonempty_scalar(self):
        for field in (b'', b'description: \n', b'description: ""\n', b'description: false\n',
                      b'description: False\n', b'description: 123\n'):
            with self.subTest(description=field):
                skill = self.contents['skills/korean-protocol/SKILL.md'].replace(
                    b'description: Explicit Korean writing skill\n', field)
                (self.source / 'skills/korean-protocol/SKILL.md').write_bytes(skill)
                with self.assertRaisesRegex(ValueError, 'description'):
                    self.build()

    def test_quoted_false_and_yaml_aliases_cannot_set_invocation_policy(self):
        for value in ('"false"', '*explicit', '!!bool false', 'off', 'no'):
            with self.subTest(value=value):
                (self.source / 'skills/korean-protocol/agents/openai.yaml').write_text(
                    'policy:\n  allow_implicit_invocation: ' + value + '\n')
                with self.assertRaises(ValueError):
                    self.build()

    def test_edit_during_first_host_activation_blocks_second_host(self):
        self.install()
        original_replace = self.module.os.replace
        before_codex = (self.targets['codex'] / 'INSTALLATION.json').read_bytes()
        def edit_second_host(source, destination):
            result = original_replace(source, destination)
            if Path(destination) == self.targets['codex'] and Path(source).name == 'staged':
                (self.targets['claude-code'] / 'SKILL.md').write_text('later user edit')
            return result
        with mock.patch.object(self.module.os, 'replace', side_effect=edit_second_host):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.install()
        self.assertEqual((self.targets['codex'] / 'INSTALLATION.json').read_bytes(), before_codex)
        self.assertEqual((self.targets['claude-code'] / 'SKILL.md').read_text(), 'later user edit')


if __name__ == '__main__':
    unittest.main()
