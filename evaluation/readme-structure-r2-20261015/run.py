#!/usr/bin/env python3
"""Run round 2 with the unchanged, tested round-1 harness in a new evidence folder."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('structure_harness',
    HERE.parent / 'readme-structure-r1-20261015' / 'run.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
harness.HERE = HERE

if __name__ == '__main__':
    harness.main()
