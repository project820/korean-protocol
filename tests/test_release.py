import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from distribution import release
from runtime import kproto as k
from validation.check import FILES
from validation.compile import compile_profiles


@unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH signing is required')
class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kproto-release-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        repo = Path(__file__).resolve().parents[1]
        names = set(k.CONTENT_PATHS) | set(FILES) | {
            'evaluation/functional-review.json', 'evaluation/functional-cases.json',
            'docs/spec/korean-rules.md', 'LICENSE', 'NOTICE.md',
        }
        for name in names:
            destination = self.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((repo / name).read_bytes())
        # Keep fictional first-release history independent of the current draft.
        # Only top-level metadata changes; all rule/lexicon entries stay intact.
        for name in ('specification/rules.json', 'lexicon/core.json',
                     'lexicon/domains/software.json'):
            path = self.source / name
            value = json.loads(path.read_text())
            current = value['version']
            path.write_bytes(path.read_bytes().replace(
                ('"version": "' + current + '"').encode(),
                b'"version": "0.2.0-draft"', 1))
        # Repair only the copied fixture proof for that metadata-only adjustment.
        proof_path = self.source / 'evaluation/functional-review.json'
        proof = json.loads(proof_path.read_text())
        proof['reviewed_rules_sha256'] = k.digest(
            (self.source / 'specification/rules.json').read_bytes())
        proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
        self.key = self.root / 'signer'
        result = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key)], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.public = self.key.with_suffix('.pub')
        self.fingerprint = k.key_fingerprint(self.public)
        self.unsigned = self.root / 'unsigned'
        self.ready = self.root / 'ready'
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.issued = (now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.expires = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    def prepare(self, **overrides):
        arguments = dict(root=self.source, output=self.unsigned, version='0.2.0',
                         sequence=1, issued_at=self.issued, expires_at=self.expires,
                         public_key=self.public, fingerprint=self.fingerprint, first_release=True)
        arguments.update(overrides)
        return release.prepare(**arguments)

    def sign(self, manifest=None, key=None):
        manifest = manifest or self.unsigned / 'stable/release.json'
        result = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key or self.key),
                                 '-n', 'kproto-release-v1', str(manifest)], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return Path(str(manifest) + '.sig')

    def seal(self, **overrides):
        arguments = dict(prepared=self.unsigned, signature=self.unsigned / 'stable/release.json.sig',
                         output=self.ready, public_key=self.public, fingerprint=self.fingerprint,
                         first_release=True)
        arguments.update(overrides)
        return release.seal(**arguments)

    def test_real_source_seals_exact_allowlist_and_installs_for_both_hosts(self):
        self.assertEqual('0.2.0-draft', self.prepare())
        self.sign()
        self.assertEqual('0.2.0-draft', self.seal())
        expected = {'releases/0.2.0/' + name for name in k.CONTENT_PATHS}
        expected |= {'stable/release.json', 'stable/release.json.sig'}
        self.assertEqual(expected, {p.relative_to(self.ready).as_posix() for p in self.ready.rglob('*') if p.is_file()})
        self.assertEqual((self.unsigned / 'stable/release.json').read_bytes(),
                         (self.ready / 'stable/release.json').read_bytes())
        bundle = self.root / 'install-bundle'
        shutil.copytree(self.ready / 'releases/0.2.0', bundle)
        for name in ('release.json', 'release.json.sig'):
            shutil.copyfile(self.ready / 'stable' / name, bundle / name)
        for host in ('codex', 'claude-code'):
            home = self.root / (host + '-home')
            home.mkdir()
            context = dict(host=host, scope='user', project_root=None)
            context['codex_home' if host == 'codex' else 'claude_home'] = str(home)
            target = k.host_target(argparse.Namespace(**context))
            target.parent.mkdir(parents=True, exist_ok=True)
            original = '사용자의 기존 지침을 보존한다.\n'.encode()
            target.write_bytes(original)
            controller = k.Controller(self.root / (host + '-state'))
            controller.trust_key(self.public, self.fingerprint)
            controller.install_signed(bundle, target, host_context=context)
            self.assertTrue(target.read_bytes().startswith(original))
            self.assertEqual(1, target.read_bytes().count(k.BEGIN))
            self.assertEqual('signed', controller.status()['trust'])
            self.assertEqual(1, controller.status()['highest_sequence'])

    def test_prepare_has_deterministic_manifest_and_payload_bytes(self):
        self.prepare()
        other = self.root / 'second'
        self.prepare(output=other)
        for path in self.unsigned.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (other / path.relative_to(self.unsigned)).read_bytes())
        self.assertFalse((other / 'stable/release.json.sig').exists())

    def test_rejects_stale_profiles_and_pack_before_output(self):
        for name in ('profiles/chat.md', 'pack/protocol.md'):
            path = self.source / name
            before = path.read_bytes()
            path.write_bytes(before + b'changed\n')
            with self.assertRaisesRegex(k.InputError, 'Compiled content is stale'):
                self.prepare()
            self.assertFalse(self.unsigned.exists())
            path.write_bytes(before)

    def test_missing_license_or_notice_prevents_release_output(self):
        for name in ('LICENSE','NOTICE.md'):
            with self.subTest(name=name):
                path = self.source/name
                original = path.read_bytes()
                path.rename(path.with_suffix('.missing'))
                with self.assertRaises(k.MissingError):
                    self.prepare()
                self.assertFalse(self.unsigned.exists())
                path.write_bytes(original)

    def test_compiler_receives_captured_notices_when_source_changes(self):
        originals = {name:(self.source/name).read_bytes() for name in ('LICENSE','NOTICE.md')}

        def compile_snapshot(snapshot, output):
            for name,original in originals.items():
                self.assertEqual(original,(snapshot/name).read_bytes())
                (self.source/name).write_bytes(original+b'Concurrent fixture change.\n')
            return compile_profiles(snapshot, output)

        with patch.object(release, 'compile_profiles', side_effect=compile_snapshot):
            self.assertEqual('0.2.0-draft',self.prepare())
        pack = (self.unsigned/'releases/0.2.0/pack/protocol.md').read_bytes()
        for original in originals.values():
            self.assertIn(original,pack)
        self.assertNotIn(b'Concurrent fixture change.',pack)

    def test_changed_license_or_notice_requires_recompiled_pack(self):
        for name in ('LICENSE','NOTICE.md'):
            with self.subTest(name=name):
                path = self.source/name
                original = path.read_bytes()
                path.write_bytes(original+b'Changed fixture notice.\n')
                with self.assertRaisesRegex(k.InputError, 'Compiled content is stale: pack/protocol.md'):
                    self.prepare()
                self.assertFalse(self.unsigned.exists())
                path.write_bytes(original)

    def test_source_version_and_schema_mismatch_are_rejected(self):
        path = self.source / 'lexicon/core.json'
        original = json.loads(path.read_bytes())
        for field, value in (('version', '0.3.0-draft'), ('schema_version', '2.0')):
            changed = dict(original)
            changed[field] = value
            path.write_bytes(k.json_bytes(changed))
            with self.assertRaises(k.ProtocolError):
                self.prepare()
            self.assertFalse(self.unsigned.exists())
        path.write_bytes(k.json_bytes(original))
        with self.assertRaisesRegex(k.InputError, 'numeric release version'):
            self.prepare(version='0.3.0')

    def test_project_structure_validation_failure_prevents_output(self):
        path = self.source / 'examples/rule-cases.json'
        value = json.loads(path.read_bytes())
        value['cases'][0]['rule_ids'] = ['UNKNOWN-RULE']
        path.write_bytes(k.json_bytes(value))
        with self.assertRaisesRegex(ValueError, 'Input validation failed'):
            self.prepare()
        self.assertFalse(self.unsigned.exists())

    def test_existing_output_is_preserved_for_prepare_and_seal(self):
        self.unsigned.mkdir()
        sentinel = self.unsigned / 'existing'
        sentinel.write_bytes(b'keep')
        with self.assertRaises(k.ConflictError):
            self.prepare()
        self.assertEqual(b'keep', sentinel.read_bytes())
        prepared = self.root / 'other'
        self.prepare(output=prepared)
        signature = self.sign(prepared / 'stable/release.json')
        with self.assertRaises(k.ConflictError):
            self.seal(prepared=prepared, signature=signature, output=self.unsigned)
        self.assertEqual(b'keep', sentinel.read_bytes())

    def test_rejects_symlink_source_payload_evidence_output_and_parent(self):
        for name in ('profiles/chat.md', 'evaluation/functional-review.json', 'LICENSE', 'NOTICE.md'):
            path = self.source / name
            real = self.root / 'real'
            real.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(real)
            with self.assertRaises(k.InputError):
                self.prepare()
            path.unlink()
            path.write_bytes(real.read_bytes())
        self.unsigned.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(k.InputError):
            self.prepare()
        link = self.root / 'linked-parent'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(k.InputError):
            self.prepare(output=link / 'child')

    def test_tampered_payload_and_manifest_do_not_create_sealed_output(self):
        self.prepare()
        self.sign()
        path = self.unsigned / 'releases/0.2.0/profiles/chat.md'
        original = path.read_bytes()
        path.write_bytes(original + b'changed')
        with self.assertRaises(k.TrustError):
            self.seal()
        self.assertFalse(self.ready.exists())
        path.write_bytes(original)
        manifest = self.unsigned / 'stable/release.json'
        manifest.write_bytes(manifest.read_bytes() + b' ')
        with self.assertRaises(k.TrustError):
            self.seal()
        self.assertFalse(self.ready.exists())

    def test_wrong_fingerprint_wrong_signer_and_invalid_signature_are_rejected(self):
        with self.assertRaises(k.TrustError):
            self.prepare(fingerprint='SHA256:' + 'A' * 43)
        self.prepare()
        other_key = self.root / 'other-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(other_key)], check=True, capture_output=True)
        signature = self.sign(key=other_key)
        with self.assertRaises(k.TrustError):
            self.seal()
        signature.write_bytes(b'invalid signature')
        with self.assertRaises(k.TrustError):
            self.seal()
        self.assertFalse(self.ready.exists())

    def test_manifest_dates_and_first_release_sequence_are_explicit(self):
        for change in ({'issued_at': self.expires}, {'expires_at': self.issued},
                       {'issued_at': '2026-10-12'}, {'sequence': 2}, {'first_release': False}):
            with self.subTest(change=change), self.assertRaises(k.ProtocolError):
                self.prepare(**change)
        self.assertFalse(self.unsigned.exists())

    def test_previous_signed_release_is_required_to_increase_sequence_and_version(self):
        self.prepare()
        self.sign()
        self.seal()
        manifest, _, _, _ = release._load_static(self.ready, self.public, self.fingerprint)
        newer = dict(manifest, version='0.3.0', sequence=2)
        release._check_sequence(newer, self.public, self.fingerprint, self.ready, False)
        for change in ({'sequence': 1}, {'version': '0.2.0'}, {'issued_at': '2000-01-01T00:00:00Z'}):
            with self.subTest(change=change), self.assertRaises(k.TrustError):
                release._check_sequence(dict(newer, **change), self.public, self.fingerprint, self.ready, False)
        unsigned_previous = self.root / 'unsigned-previous'
        self.prepare(output=unsigned_previous)
        with self.assertRaises(k.ProtocolError):
            release._check_sequence(newer, self.public, self.fingerprint, unsigned_previous, False)
        with self.assertRaises(k.InputError):
            self.seal(output=self.root / 'second-ready', previous=self.ready, first_release=True)
        with self.assertRaises(k.TrustError):
            self.seal(output=self.root / 'second-ready', previous=self.ready, first_release=False)

    def test_later_release_prepares_and_seals_against_authenticated_previous(self):
        self.prepare()
        self.sign()
        self.seal()
        for name in ('specification/rules.json', 'lexicon/core.json', 'lexicon/domains/software.json'):
            path = self.source / name
            value = json.loads(path.read_bytes())
            value['version'] = '0.3.0-draft'
            path.write_bytes(k.json_bytes(value))
        proof = self.source / 'evaluation/functional-review.json'
        review = json.loads(proof.read_bytes())
        review['reviewed_rules_sha256'] = k.digest((self.source / 'specification/rules.json').read_bytes())
        proof.write_bytes(k.json_bytes(review))
        compile_profiles(self.source, self.source)
        prepared = self.root / 'next-prepared'
        release.prepare(self.source, prepared, '0.3.0', 2, self.issued, self.expires,
                        self.public, self.fingerprint, previous=self.ready)
        signature = self.sign(prepared / 'stable/release.json')
        next_ready = self.root / 'next-ready'
        release.seal(prepared, signature, next_ready, self.public, self.fingerprint, previous=self.ready)
        value = json.loads((next_ready / 'stable/release.json').read_bytes())
        self.assertEqual(2, value['sequence'])
        self.assertEqual('0.3.0', value['version'])

    def test_prepare_and_seal_cli_work_with_external_detached_signature(self):
        common = ['--public-key', str(self.public), '--fingerprint', self.fingerprint, '--first-release']
        args = [sys.executable, '-m', 'distribution.release', 'prepare', '--root', str(self.source),
                '--output', str(self.unsigned), '--version', '0.2.0', '--sequence', '1',
                '--issued-at', self.issued, '--expires-at', self.expires] + common
        result = subprocess.run(args, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('source version=0.2.0-draft', result.stdout)
        signature = self.sign()
        result = subprocess.run([sys.executable, '-m', 'distribution.release', 'seal',
                                 '--prepared', str(self.unsigned), '--signature', str(signature),
                                 '--output', str(self.ready)] + common,
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.ready / 'stable/release.json.sig').is_file())


if __name__ == '__main__':
    unittest.main()
