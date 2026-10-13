"""Offline checks for consuming publisher artifacts in the manual HTTPS smoke."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from runtime import kproto as k

_spec = importlib.util.spec_from_file_location('manual_https_smoke', Path(__file__).with_name('manual_https_smoke.py'))
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


@unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH signing is required')
class SignedStaticSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kproto-smoke-offline-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        key = self.root / 'fixture-signer'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        self.public = key.with_suffix('.pub')
        self.fingerprint = k.key_fingerprint(self.public)
        self.static = self.root / 'static'
        repo = Path(__file__).resolve().parents[1]
        manifest = k.make_manifest(repo, '0.2.0', 1, self.fingerprint)
        self.payload = {'releases/0.2.0/' + name: (repo / name).read_bytes()
                        for name in k.CONTENT_PATHS}
        self.payload['stable/release.json'] = k.json_bytes(manifest)
        signed = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'kproto-release-v1'],
                                input=self.payload['stable/release.json'], check=True, capture_output=True)
        self.payload['stable/release.json.sig'] = signed.stdout
        for name, raw in self.payload.items():
            path = self.static / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def load(self, **overrides):
        arguments = dict(module=k, signed_static=self.static, public_key=self.public,
                         fingerprint=self.fingerprint)
        arguments.update(overrides)
        return smoke.load_signed_static(**arguments)

    def test_authenticated_capture_preserves_every_publisher_byte_and_source_mtime(self):
        before = {name: (self.static / name).stat().st_mtime_ns for name in self.payload}
        manifest, payload = self.load()
        self.assertEqual(('0.2.0', 1), (manifest['version'], manifest['sequence']))
        self.assertEqual(self.payload, payload)
        self.assertEqual(before, {name: (self.static / name).stat().st_mtime_ns for name in self.payload})
        self.assertEqual(self.payload, smoke.static_files(k, self.static))

    def test_relative_publisher_key_is_absolute_before_runtime_cwd_changes(self):
        key, fingerprint = smoke.publisher_trust(
            k, self.root, Path(os.path.relpath(self.public)), self.fingerprint)
        self.assertEqual(self.public, key.resolve())
        self.assertTrue(key.is_absolute())
        self.assertEqual(self.fingerprint, fingerprint)

    def test_https_request_expectation_follows_authenticated_manifest_order(self):
        manifest, _ = self.load()
        manifest['files'].reverse()
        expected = ['/stable/release.json', '/stable/release.json.sig']
        expected.extend('/releases/0.2.0/' + item['path'] for item in manifest['files'])
        self.assertEqual(expected, smoke.release_requests(manifest))

    def test_rejects_wrong_fingerprint_before_accepting_content(self):
        with self.assertRaises(k.TrustError):
            self.load(fingerprint='SHA256:' + 'A' * 43)

    def test_rejects_signature_and_payload_tampering_without_changing_source(self):
        for name in ('stable/release.json.sig', 'releases/0.2.0/pack/protocol.md'):
            path = self.static / name
            with self.subTest(name=name):
                path.write_bytes(b'invalid signature\n' if name.endswith('.sig') else self.payload[name] + b'tampered\n')
                before = smoke.static_files(k, self.static)
                with self.assertRaises(k.TrustError):
                    self.load()
                self.assertEqual(before, smoke.static_files(k, self.static))
                path.write_bytes(self.payload[name])

    def test_rejects_unlisted_files_and_symlink_directories(self):
        extra = self.static / 'unlisted'
        extra.write_bytes(b'not publisher content')
        with self.assertRaises(k.InputError):
            self.load()
        # Use a separate tree; retain the original test files for failure diagnosis.
        linked = self.root / 'linked'
        linked.mkdir()
        (linked / 'stable').symlink_to(self.static / 'stable', target_is_directory=True)
        with self.assertRaises(k.ProtocolError):
            self.load(signed_static=linked)


if __name__ == '__main__':
    unittest.main()
