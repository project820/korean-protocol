#!/usr/bin/env python3
"""Verify or rebuild frozen experimental profiles without external study data."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verify(root=HERE):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    errors = []
    for name, expected in manifest['files'].items():
        path = root / name
        if not path.is_file():
            errors.append(f'{name}: missing')
            continue
        data = path.read_bytes()
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            errors.append(f'{name}: frozen bytes differ')
    for target, parts in manifest['compositions'].items():
        if (root / target).is_file() and all((root / part).is_file() for part in parts):
            if (root / target).read_bytes() != b''.join((root / part).read_bytes() for part in parts):
                errors.append(f'{target}: component order or content differs')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='verify without writing (the default)')
    action.add_argument('--write', action='store_true', help='rebuild profiles from frozen components')
    args = parser.parse_args()
    if args.write:
        manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
        # Validate each component before replacing an output profile.
        components = {part for parts in manifest['compositions'].values() for part in parts}
        for name in components:
            data = (HERE / name).read_bytes()
            expected = manifest['files'][name]
            if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
                parser.error(f'{name}: frozen component differs')
        for target, parts in manifest['compositions'].items():
            (HERE / target).write_bytes(b''.join((HERE / part).read_bytes() for part in parts))
    errors = verify()
    if errors:
        parser.exit(1, '\n'.join(errors) + '\n')
    manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
    print(f"Verified {len(manifest['files'])} frozen files and {len(manifest['compositions'])} exact profile compositions.")


if __name__ == '__main__':
    main()
