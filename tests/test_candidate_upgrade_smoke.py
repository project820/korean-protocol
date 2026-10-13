"""Offline guardrails for the actual-candidate HTTPS smoke helper."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from runtime import kproto as k

_spec = importlib.util.spec_from_file_location('candidate_smoke', Path(__file__).with_name('manual_candidate_upgrade_smoke.py'))
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)
_base_spec = importlib.util.spec_from_file_location('base_smoke', Path(__file__).with_name('manual_https_smoke.py'))
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)


class CandidateSmokeGuardTests(unittest.TestCase):
    def test_actual_candidate_source_versions_agree(self):
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual('0.3.0-draft', smoke.source_version(k, k.content_files(repo), '0.3.0'))

    def test_mismatched_versions_fail_before_signing_or_writes(self):
        for versions in [('0.2.0', '0.3.0-draft'), ('0.2.0', '0.2.0')]:
            with self.subTest(versions=versions), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                files = {'specification/rules.json': k.json_bytes({'version': versions[0]}),
                         'lexicon/core.json': k.json_bytes({'version': versions[1]})}
                with mock.patch.object(smoke.subprocess, 'run') as process, self.assertRaises(k.InputError):
                    smoke.test_static(k, files, '0.3.0', 2, root / 'never-read-key', 'unused', root)
                process.assert_not_called()
                self.assertEqual([], list(root.iterdir()))

    def test_outside_managed_preserves_CRLF_prefix_and_suffix_exactly(self):
        prefix, suffix = '사용자 규칙\r\n'.encode(), b'\r\n# Manual appendix\r\n'
        self.assertEqual(prefix + suffix, smoke.outside_managed(k, prefix + k.BEGIN + b'\nmanaged\n' + k.END + suffix))
        for invalid in (prefix, prefix + k.BEGIN, k.BEGIN + k.END + k.BEGIN + k.END):
            with self.assertRaises(RuntimeError):
                smoke.outside_managed(k, invalid)

    def test_crash_scan_does_not_read_contents_and_reports_unavailable_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'Python-TEST.ips').write_bytes(b'do not read report contents')
            (root / 'node-TEST.ips').write_bytes(b'not Python')
            missing = root / 'missing'
            with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('report contents read')):
                captured, unavailable = smoke.crash_snapshot([root, missing])
            self.assertEqual([str(root / 'Python-TEST.ips')], list(captured))
            self.assertEqual([str(missing)], unavailable)

    @unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH signing required')
    def test_TEST_signing_preserves_all_actual_candidate_bytes_and_authenticates(self):
        repo = Path(__file__).resolve().parents[1]
        original = k.content_files(repo)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            key = root / 'TEST-key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                           capture_output=True, check=True)
            public = Path(str(key) + '.pub')
            fingerprint = k.key_fingerprint(public)
            static = root / 'static'
            manifest = smoke.test_static(k, original, '0.3.0', 2, key, fingerprint, static)
            checked, payload = base.load_signed_static(k, static, public, fingerprint)
            self.assertEqual(manifest, checked)
            self.assertEqual(original, {name: payload['releases/0.3.0/' + name] for name in k.CONTENT_PATHS})
            self.assertEqual(original, k.content_files(repo))
            self.assertNotEqual(k.key_fingerprint(repo / 'distribution/trust/publisher.pub'), fingerprint)


if __name__ == '__main__':
    unittest.main()
