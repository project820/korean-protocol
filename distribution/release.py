"""Prepare deterministic content releases, then verify an external SSHSIG to seal.

Run ``python3 -m distribution.release --help``. This command never reads private
keys, publishes files, or changes installed protocol state.
"""
import argparse
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

from runtime import kproto as k
from validation.check import FILES
from validation.compile import PROFILE_PATHS, compile_profiles


def _new_output(output):
    output = k.safe_path(output)
    if output.exists():
        raise k.ConflictError('Output already exists; choose a new directory')
    if not output.parent.is_dir():
        raise k.InputError('Output parent must already exist')
    return output


def _write_tree(output, files):
    """Reserve a new directory and write only exclusive, descriptor-relative files."""
    output = _new_output(output)
    parent = k.open_directory(output.parent)
    try:
        os.mkdir(output.name, 0o755, dir_fd=parent)
        root = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        for name, data in sorted(files.items()):
            directory = os.dup(root)
            try:
                parts = PurePosixPath(name).parts
                for part in parts[:-1]:
                    try:
                        os.mkdir(part, 0o755, dir_fd=directory)
                    except FileExistsError:
                        pass
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    os.close(directory)
                    directory = next_fd
                fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=directory)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(directory)
        expected = os.fstat(root)
        actual = k.safe_path(output).stat()
        if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
            raise k.ConflictError('Output directory changed during write')
    finally:
        os.close(root)
    return output


def _source_version(files, version):
    versions = {k.strict_json(data)['version'] for name, data in files.items() if name.endswith('.json')}
    if len(versions) != 1:
        raise k.InputError('Content source versions must agree')
    source_version = versions.pop()
    if not re.fullmatch(re.escape(version) + r'(?:-[a-z0-9.-]+)?', source_version):
        raise k.InputError('Content source version must match the numeric release version')
    return source_version


def _validated_source(root, version):
    """Validate a captured snapshot, including referenced local review evidence."""
    root = k.safe_path(root)
    files = k.content_files(root)
    source_version = _source_version(files, version)
    with tempfile.TemporaryDirectory(prefix='kproto-source-') as temporary:
        snapshot = Path(temporary).resolve() / 'source'
        snapshot.mkdir()
        captured = dict(files)

        def capture(name):
            if not isinstance(name, str) or not name or '\\' in name:
                raise k.InputError('Source evidence path is invalid')
            parts = PurePosixPath(name)
            if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
                raise k.InputError('Source evidence path must stay inside the source directory')
            if name not in captured:
                captured[name] = k.read_bytes(root / name)
            return k.strict_json(captured[name]) if name.endswith('.json') else None

        for name in FILES:
            if not isinstance(capture(name), dict):
                raise k.InputError('Source validation JSON must be a top-level object')
        crosswalk = k.strict_json(captured[FILES[1]])
        for item in crosswalk.get('items', []):
            if not isinstance(item, dict) or item.get('status') != 'verified':
                continue
            for reference in item.get('evidence', []):
                if not isinstance(reference, dict):
                    raise k.InputError('Source evidence reference is invalid')
                proof = capture(reference.get('path'))
                if not isinstance(proof, dict):
                    raise k.InputError('Source review evidence must be a JSON object')
                for field in ('independent_cases_path', 'reviewed_spec_path'):
                    capture(proof.get(field))
        for name, data in captured.items():
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        compiled = Path(temporary).resolve() / 'compiled'
        compile_profiles(snapshot, compiled)
        for name in PROFILE_PATHS:
            if k.read_bytes(compiled / name) != files[name]:
                raise k.InputError('Compiled content is stale: ' + name)
    return files, source_version


def _fingerprint(public_key, fingerprint):
    if k.key_fingerprint(public_key) != fingerprint:
        raise k.TrustError('Public key fingerprint differs from expected trust anchor')


def _load_static(prepared, public_key, fingerprint, signature=None, fresh=True):
    prepared = k.safe_path(prepared)
    raw = k.read_bytes(prepared / 'stable/release.json', 65536)
    manifest = k.validate_manifest(k.strict_json(raw), fresh=fresh)
    files = k.content_files(prepared / 'releases' / manifest['version'])
    _source_version(files, manifest['version'])
    sig = k.read_bytes(signature or prepared / 'stable/release.json.sig', 16384)
    with tempfile.TemporaryDirectory(prefix='kproto-verify-') as temporary:
        temporary = Path(temporary).resolve()
        bundle = temporary / 'bundle'
        _write_tree(bundle, dict(files, **{'release.json': raw, 'release.json.sig': sig}))
        controller = k.Controller(temporary / 'state')
        controller.trust_key(public_key, fingerprint)
        controller._load_signed(bundle, fresh=fresh)
    return manifest, raw, files, sig


def _check_sequence(manifest, public_key, fingerprint, previous, first_release):
    if bool(previous) == bool(first_release):
        raise k.InputError('Choose exactly one of --first-release or --previous')
    if first_release:
        if manifest['sequence'] != 1:
            raise k.InputError('First release sequence must be 1')
        return
    prior, _, _, _ = _load_static(previous, public_key, fingerprint, fresh=False)
    if manifest['sequence'] <= prior['sequence']:
        raise k.TrustError('Release sequence must increase beyond the previous signed release')
    if k.version_tuple(manifest['version']) <= k.version_tuple(prior['version']):
        raise k.TrustError('Release version must increase beyond the previous signed release')
    if manifest['issued_at'] < prior['issued_at']:
        raise k.TrustError('Release issue time must not precede the previous signed release')


def prepare(root, output, version, sequence, issued_at, expires_at, public_key,
            fingerprint, previous=None, first_release=False):
    _new_output(output)
    k.version_tuple(version)
    _fingerprint(public_key, fingerprint)
    files, source_version = _validated_source(root, version)
    # Runtime metadata creation is reused, but wall-clock defaults are replaced.
    manifest = k.make_manifest(root, version, sequence, fingerprint)
    manifest['issued_at'], manifest['expires_at'] = issued_at, expires_at
    for entry in manifest['files']:
        data = files[entry['path']]
        entry['size'], entry['sha256'] = len(data), k.digest(data)
    k.validate_manifest(manifest)
    _check_sequence(manifest, public_key, fingerprint, previous, first_release)
    payload = {'releases/' + version + '/' + name: data for name, data in files.items()}
    payload['stable/release.json'] = k.json_bytes(manifest)
    _write_tree(output, payload)
    return source_version


def seal(prepared, signature, output, public_key, fingerprint,
         previous=None, first_release=False):
    _new_output(output)
    _fingerprint(public_key, fingerprint)
    manifest, raw, files, sig = _load_static(prepared, public_key, fingerprint, signature)
    _check_sequence(manifest, public_key, fingerprint, previous, first_release)
    payload = {'releases/' + manifest['version'] + '/' + name: data for name, data in files.items()}
    payload['stable/release.json'] = raw
    payload['stable/release.json.sig'] = sig
    _write_tree(output, payload)
    return _source_version(files, manifest['version'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('prepare', 'seal'):
        command_parser = sub.add_parser(command)
        command_parser.add_argument('--output', type=Path, required=True)
        command_parser.add_argument('--public-key', type=Path, required=True)
        command_parser.add_argument('--fingerprint', required=True, help='Independently verified SHA256 fingerprint')
        history = command_parser.add_mutually_exclusive_group(required=True)
        history.add_argument('--first-release', action='store_true')
        history.add_argument('--previous', type=Path, help='Previous sealed static directory, authenticated before use')
        if command == 'prepare':
            command_parser.add_argument('--root', type=Path, default=Path('.'))
            command_parser.add_argument('--version', required=True)
            command_parser.add_argument('--sequence', type=int, required=True)
            command_parser.add_argument('--issued-at', required=True)
            command_parser.add_argument('--expires-at', required=True)
        else:
            command_parser.add_argument('--prepared', type=Path, required=True)
            command_parser.add_argument('--signature', type=Path, required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        source_version = (prepare if command == 'prepare' else seal)(**args)
    except (k.ProtocolError, OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return error.code if isinstance(error, k.ProtocolError) else 2
    print(command + ': ' + str(Path(args['output']).absolute()) + '; source version=' + source_version)
    return 0


if __name__ == '__main__':
    sys.exit(main())
