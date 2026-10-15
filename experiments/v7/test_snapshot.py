"""Check integrity failure paths without model calls or unpublished fixtures."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('v7_snapshot', HERE / 'build_profiles.py')
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


class SnapshotTests(unittest.TestCase):
    def test_published_snapshot_is_complete(self):
        self.assertEqual([], snapshot.verify(HERE))

    def test_component_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'v7'
            shutil.copytree(HERE, root)
            with (root / 'r2-supplement.md').open('ab') as output:
                output.write(b'changed')
            errors = snapshot.verify(root)
            self.assertIn('r2-supplement.md: frozen bytes differ', errors)
            self.assertIn('profile-v7-r2.md: component order or content differs', errors)

    def test_missing_parent_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'v7'
            shutil.copytree(HERE, root)
            (root / 'parent-v6-profile.md').rename(root / 'unused-parent.md')
            self.assertIn('parent-v6-profile.md: missing', snapshot.verify(root))


if __name__ == '__main__':
    unittest.main()
