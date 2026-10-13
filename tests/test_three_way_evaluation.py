"""Keep experimental conditions isolated rather than reusing KP vocabulary in STE."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('three_way',ROOT/'evaluation/llm/controlled-korean-20261013/run.py')
runner=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

class IsolationTests(unittest.TestCase):
    def test_ste_mounts_reference_only_and_baseline_is_empty(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); snapshot=root/'snapshot'; snapshot.mkdir()
            for name in runner.MOUNT_PATHS:
                p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('reference' if name=='AGENTS.md' else 'KP lexicon')
            self.assertEqual({},runner.mount_condition('baseline',snapshot,root/'baseline'))
            ste=runner.mount_condition('ste',snapshot,root/'ste')
            self.assertEqual({'AGENTS.md'},set(ste))
            self.assertFalse((root/'ste/lexicon').exists())
            kp=runner.mount_condition('treatment',snapshot,root/'kp')
            self.assertEqual(set(runner.MOUNT_PATHS),set(kp))

    def test_expected_mounts_match_actual_condition(self):
        contract={'profile_sha256':'p','core_sha256':'c','software_sha256':'s'}
        self.assertEqual({},runner.expected_mounts('baseline',contract))
        self.assertEqual({'AGENTS.md':'p'},runner.expected_mounts('ste',contract))
        self.assertEqual(dict(zip(runner.MOUNT_PATHS,['p','c','s'])),runner.expected_mounts('treatment',contract))

if __name__=='__main__': unittest.main()
