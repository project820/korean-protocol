"""Build unsigned on-demand skill candidates and install only verified evidence.

This module deliberately does not import or change the signed 0.7 distributor.
"""
import argparse
import hashlib
import importlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile


VERSION = '0.11.0-candidate'
SKILL_PREFIX = 'skills/korean-protocol/'
ZIP_PREFIX = 'korean-protocol/'
SUPPORT = ('specification/rules.json', 'lexicon/core.json',
           'lexicon/domains/software.json', 'LICENSE', 'NOTICE.md')
FORBIDDEN = {'evaluation', 'ste', 'raw', 'private', '__pycache__', '.git'}
SHA256 = re.compile(r'^[0-9a-f]{64}$')
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def _relative(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('invalid relative path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('invalid relative path: ' + name)
    if any(part.casefold() in FORBIDDEN or part.startswith('.')
           or re.search(r'(^|[-_.])(evaluation|ste|raw|private)([-_.]|$)', part.casefold())
           for part in path.parts):
        raise ValueError('forbidden package path: ' + name)
    return path


def _source_destination(source):
    _relative(source)
    if source.startswith(SKILL_PREFIX):
        destination = source[len(SKILL_PREFIX):]
        if destination in ('MANIFEST.json', 'INSTALLATION.json'):
            raise ValueError('reserved package path: ' + destination)
        return str(_relative(destination))
    if source in SUPPORT:
        return source
    raise ValueError('source is outside the package allowlist: ' + source)


def _read_file(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('symlink is not permitted: ' + str(path))
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError('missing, nonregular or oversized file: ' + str(path))
    return path.read_bytes()


def build_package(root, output, version=VERSION, base_commit=None):
    """Snapshot current bytes, including uncommitted resources; never claim a tag."""
    root, output = Path(root).absolute(), Path(output).absolute()
    skill = root / 'skills/korean-protocol'
    if not skill.is_dir() or skill.is_symlink():
        raise ValueError('skill directory is missing or a symlink')
    sources = list(SUPPORT)
    for path in sorted(skill.rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink is not permitted: ' + str(path))
        if path.is_file():
            sources.append(path.relative_to(root).as_posix())
    payload, hashes = {}, {}
    for source in sorted(sources):
        destination = _source_destination(source)
        if destination in payload:
            raise ValueError('duplicate package destination: ' + destination)
        data = _read_file(root / source)
        payload[destination], hashes[source] = data, digest(data)
    _validate_invocation(payload)
    if sum(map(len, payload.values())) > MAX_TOTAL:
        raise ValueError('package is oversized')
    if base_commit is None:
        base_commit = subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40,64}', base_commit):
        raise ValueError('base commit must be a complete Git object id')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-candidate(?:[.-][a-zA-Z0-9]+)*', version):
        raise ValueError('unsigned working-tree package must use a candidate version')
    manifest = {
        'schema': 'korean-protocol-skill-package/v1', 'version': version,
        'name': 'korean-protocol', 'explicit_only': True,
        'candidate_id': digest(canonical(hashes)), 'source_hashes': hashes,
        'files': {name: digest(data) for name, data in sorted(payload.items())},
        'provenance': {'kind': 'working-tree-candidate', 'base_commit': base_commit,
                       'release_tag': None, 'publisher_authenticated': False},
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        entries = {'MANIFEST.json': canonical(manifest) + b'\n'}
        entries.update({ZIP_PREFIX + name: data for name, data in payload.items()})
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    data = stream.getvalue()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {'package': str(output), 'package_sha256': digest(data), 'manifest': manifest}


def _yaml_mapping(data):
    """Parse the package's strict YAML subset without a production dependency.

    Only nested mappings with two-space indentation and single-line scalars
    are accepted. Reject aliases, tags, merge keys, flow collections, block
    scalars and duplicate keys instead of guessing the host parser's meaning.
    """
    result = {}
    stack = [(0, result)]
    for line_number, line in enumerate(data.decode('utf-8').splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if '\t' in line:
            raise ValueError('unsupported YAML tab at line ' + str(line_number))
        indent = len(line) - len(line.lstrip(' '))
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        if indent != stack[-1][0]:
            raise ValueError('unsupported YAML indentation at line ' + str(line_number))
        match = re.fullmatch(r' *([A-Za-z_][A-Za-z0-9_-]*):(?: +(.*))?', line)
        if not match:
            raise ValueError('unsupported YAML mapping at line ' + str(line_number))
        key, raw = match.groups()
        mapping = stack[-1][1]
        if key in mapping:
            raise ValueError('duplicate YAML key: ' + key)
        raw = (raw or '').strip()
        if not raw or raw.startswith('#'):
            mapping[key] = {}
            stack.append((indent + 2, mapping[key]))
            continue
        if raw.startswith('"'):
            value = json.loads(raw)
            if not isinstance(value, str):
                raise ValueError('unsupported YAML quoted scalar')
        elif raw.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", raw):
                raise ValueError('unsupported YAML single-quoted scalar')
            value = raw[1:-1].replace("''", "'")
        else:
            raw = raw.split(' #', 1)[0].rstrip()
            if raw[0] in '!&*{[|>@`%?+-.0123456789' or ': ' in raw:
                raise ValueError('unsupported YAML scalar for ' + key + ' at line ' + str(line_number))
            if raw.lower() in ('yes', 'no', 'on', 'off'):
                raise ValueError('ambiguous YAML scalar for ' + key)
            value = {'false': False, 'true': True, 'null': None, '~': None}.get(raw.lower(), raw)
        mapping[key] = value
    return result


def _validate_invocation(payload):
    skill = payload.get('SKILL.md', b'')
    policy = payload.get('agents/openai.yaml', b'')
    if not skill.startswith(b'---\n') or b'\n---\n' not in skill[4:]:
        raise ValueError('SKILL.md requires YAML frontmatter')
    front = _yaml_mapping(skill[4:].split(b'\n---\n', 1)[0])
    if front.get('name') != 'korean-protocol':
        raise ValueError('skill name must remain korean-protocol')
    if not isinstance(front.get('description'), str) or not front['description'].strip():
        raise ValueError('skill description must be a nonempty string')
    policy = _yaml_mapping(policy).get('policy')
    if not isinstance(policy, dict) or policy.get('allow_implicit_invocation') is not False:
        raise ValueError('Codex implicit invocation must be disabled')
    if {'disable-model-invocation', 'user-invocable'} & front.keys():
        raise ValueError('source profile must retain the shared Codex frontmatter')


def verify_package(package):
    """Verify every member without extracting archive paths."""
    package = Path(package)
    if package.stat().st_size > MAX_TOTAL + 1024 * 1024:
        raise ValueError('package is oversized')
    with zipfile.ZipFile(package) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len(set(names)) or 'MANIFEST.json' not in names:
            raise ValueError('duplicate entries or missing package manifest')
        if sum(entry.file_size for entry in infos) > MAX_TOTAL:
            raise ValueError('package is oversized')
        for entry in infos:
            _relative(entry.filename)
            if entry.file_size > MAX_FILE or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('oversized file or symlink in package')
        manifest = _json(archive.read('MANIFEST.json'))
        if manifest.get('schema') != 'korean-protocol-skill-package/v1':
            raise ValueError('unsupported manifest schema')
        provenance = manifest.get('provenance', {})
        if (manifest.get('name') != 'korean-protocol' or manifest.get('explicit_only') is not True
                or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-candidate(?:[.-][a-zA-Z0-9]+)*', manifest.get('version', ''))
                or provenance.get('kind') != 'working-tree-candidate'
                or not re.fullmatch(r'[0-9a-f]{40,64}', provenance.get('base_commit', ''))
                or provenance.get('release_tag') is not None
                or provenance.get('publisher_authenticated') is not False):
            raise ValueError('invalid unsigned candidate provenance')
        hashes = manifest.get('source_hashes')
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError('source hashes are missing')
        expected = {}
        for source, checksum in hashes.items():
            destination = _source_destination(source)
            if destination in expected or not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
                raise ValueError('duplicate destination or invalid hash')
            expected[destination] = checksum
        if not set(SUPPORT).issubset(hashes) or not (SKILL_PREFIX + 'SKILL.md') in hashes:
            raise ValueError('required source files are missing')
        if manifest.get('files') != expected or manifest.get('candidate_id') != digest(canonical(hashes)):
            raise ValueError('manifest hash mapping mismatch')
        if set(names) != {'MANIFEST.json'} | {ZIP_PREFIX + name for name in expected}:
            raise ValueError('archive inventory differs from manifest')
        payload = {name: archive.read(ZIP_PREFIX + name) for name in expected}
    if any(digest(data) != expected[name] for name, data in payload.items()):
        raise ValueError('package file hash mismatch')
    _validate_invocation(payload)
    return manifest, payload


def require_quality(run_dir, source_hashes, candidate_id, package_sha256, verifier=None):
    """Recompute the independent study gate; report booleans are insufficient."""
    if verifier is None:
        # Direct script execution still imports the repository's evaluator.
        root = str(Path(__file__).resolve().parents[1])
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            verifier = importlib.import_module('evaluation.output_formats.study').validate_installation_evidence
        except (ImportError, AttributeError) as exc:
            raise ValueError('independent quality verifier is unavailable') from exc
    result = verifier(Path(run_dir).resolve(), source_hashes, candidate_id, package_sha256)
    if not isinstance(result, dict) or result.get('comparison_status') != 'complete' or result.get('quality_gate') != 'pass':
        raise ValueError('independent quality evidence did not pass')
    return result


def default_targets(hosts, home=None):
    home = Path(home) if home is not None else Path.home()
    targets = {}
    for host in hosts:
        if host == 'codex':
            target = home / '.agents/skills/korean-protocol'
        elif host == 'claude-code':
            target = Path(os.environ.get('CLAUDE_CONFIG_DIR') or home / '.claude') / 'skills/korean-protocol'
        else:
            raise ValueError('unsupported host: ' + host)
        targets[host] = target.absolute()
    return targets


def _tree_hashes(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('installed tree contains a symlink: ' + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(_read_file(path))
    return result


def _inspect_existing(target, payload):
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
        raise ValueError('installation target contains a symlink')
    if not target.exists():
        return {}
    if not target.is_dir() or not (target / 'INSTALLATION.json').is_file():
        raise ValueError('existing installation has no trusted local manifest')
    record = _json((target / 'INSTALLATION.json').read_bytes())
    tracked = record.get('files')
    if not isinstance(tracked, dict) or not tracked or 'SKILL.md' not in tracked:
        raise ValueError('existing installation manifest has no file inventory')
    actual = _tree_hashes(target)
    for name, checksum in tracked.items():
        _relative(name)
        if not isinstance(checksum, str) or not SHA256.fullmatch(checksum) or actual.get(name) != checksum:
            raise ValueError('tracked installation file was modified or removed: ' + name)
    extras = {name: checksum for name, checksum in actual.items()
              if name not in tracked and name != 'INSTALLATION.json'}
    for extra in extras:
        if any(extra == name or extra.startswith(name + '/') or name.startswith(extra + '/') for name in payload):
            raise ValueError('unmanaged file conflicts with package: ' + extra)
    return extras


def _write_json(path, value):
    path.write_bytes(canonical(value) + b'\n')


def install_package(package, targets, backup_root, run_dir, dry_run=False, verifier=None):
    """Preflight all hosts, stage outside skills roots, then activate or recover."""
    manifest, payload = verify_package(package)
    package_hash = digest(Path(package).read_bytes())
    require_quality(run_dir, manifest['source_hashes'], manifest['candidate_id'], package_hash, verifier)
    if not targets or set(targets) - {'codex', 'claude-code'}:
        raise ValueError('choose codex and/or claude-code explicitly')
    targets = {host: Path(path).absolute() for host, path in targets.items()}
    if len(set(targets.values())) != len(targets):
        raise ValueError('host targets must differ')
    backup_root = Path(backup_root).absolute()
    active_roots = {target.parent for target in targets.values()}
    homes = {Path.home()}
    for target in targets.values():
        if target.parent.name == 'skills' and target.parent.parent.name in ('.agents', '.claude', '.codex'):
            homes.add(target.parent.parent.parent)
    for home in homes:
        active_roots.update(home / folder / 'skills' for folder in ('.agents', '.claude', '.codex'))
    if os.environ.get('CLAUDE_CONFIG_DIR'):
        active_roots.add(Path(os.environ['CLAUDE_CONFIG_DIR']).absolute() / 'skills')
    if any(backup_root == root or root in backup_root.parents for root in active_roots):
        raise ValueError('backup directory must be outside active skills roots')
    for target in targets.values():
        if target.name != 'korean-protocol':
            raise ValueError('target directory name must be korean-protocol')
        if backup_root == target.parent or target.parent in backup_root.parents:
            raise ValueError('backup directory must be outside active skills roots')
        if backup_root.is_symlink() or any(parent.is_symlink() for parent in backup_root.parents):
            raise ValueError('backup directory contains a symlink')
    before_hashes = {host: _tree_hashes(target) if target.exists() else None
                     for host, target in targets.items()}
    extras = {host: _inspect_existing(target, payload) for host, target in targets.items()}
    for host, target in targets.items():
        current = _tree_hashes(target) if target.exists() else None
        if current != before_hashes[host]:
            raise ValueError('installation changed during preflight: ' + str(target))
    result = {'status': 'planned', 'candidate_id': manifest['candidate_id'],
              'package_sha256': package_hash, 'targets': {k: str(v) for k, v in targets.items()},
              'unmanaged_files': {host: sorted(files) for host, files in extras.items()}}
    if dry_run:
        return result
    transaction = backup_root / uuid.uuid4().hex
    transaction.mkdir(parents=True, exist_ok=False)
    journal = {'schema': 'korean-protocol-install-transaction/v1', 'status': 'staging', 'hosts': {}}
    for host, target in targets.items():
        host_dir = transaction / host
        staged = host_dir / 'staged'
        staged.mkdir(parents=True)
        for name in extras[host]:
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target / name, path)
        installed = dict(payload)
        if host == 'claude-code':
            installed['SKILL.md'] = payload['SKILL.md'].replace(
                b'---\n', b'---\ndisable-model-invocation: true\nuser-invocable: true\n', 1)
        for name, data in installed.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _write_json(staged / 'INSTALLATION.json', {
            'schema': 'korean-protocol-skill-installation/v1', 'version': manifest['version'],
            'host': host, 'explicit_only': True, 'candidate_id': manifest['candidate_id'],
            'package_sha256': package_hash, 'source_hashes': manifest['source_hashes'],
            'provenance': manifest['provenance'],
            'files': {name: digest(data) for name, data in installed.items()},
        })
        journal['hosts'][host] = {'target': str(target), 'had_previous': target.exists(),
                                  'installed_hashes': _tree_hashes(staged),
                                  'before_hashes': before_hashes[host],
                                  'activated': False}
    journal_path = transaction / 'transaction.json'
    _write_json(journal_path, journal)
    try:
        # Recheck both trees before the first mutation.
        for host, target in targets.items():
            before = _tree_hashes(target) if target.exists() else None
            if before != journal['hosts'][host]['before_hashes']:
                raise ValueError('installation changed during staging: ' + str(target))
        for host, target in targets.items():
            current = _tree_hashes(target) if target.exists() else None
            if current != journal['hosts'][host]['before_hashes']:
                raise ValueError('installation changed before activation: ' + str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                os.replace(target, transaction / host / 'previous')
            os.replace(transaction / host / 'staged', target)
            journal['hosts'][host]['activated'] = True
            _write_json(journal_path, journal)
    except Exception:
        for host, target in reversed(list(targets.items())):
            previous = transaction / host / 'previous'
            if journal['hosts'][host]['activated'] and target.exists():
                os.replace(target, transaction / host / 'failed-activation')
            if previous.exists():
                os.replace(previous, target)
        journal['status'] = 'failed-restored'
        _write_json(journal_path, journal)
        raise
    journal['status'] = 'installed'
    _write_json(journal_path, journal)
    result.update(status='installed', transaction=str(transaction))
    return result


def rollback_installation(transaction):
    """Restore both previous trees only if no user file changed after install."""
    transaction = Path(transaction).absolute()
    journal_path = transaction / 'transaction.json'
    journal = _json(journal_path.read_bytes())
    if journal.get('schema') != 'korean-protocol-install-transaction/v1' or journal.get('status') != 'installed':
        raise ValueError('transaction is not an active installation')
    for host, record in journal['hosts'].items():
        target = Path(record['target'])
        if not target.is_dir() or _tree_hashes(target) != record['installed_hashes']:
            raise ValueError('installed tree changed after installation: ' + str(target))
        if record['had_previous']:
            previous = transaction / host / 'previous'
            if not previous.is_dir() or _tree_hashes(previous) != record['before_hashes']:
                raise ValueError('backup tree changed after installation: ' + str(previous))
    restored = []
    try:
        for host, record in reversed(list(journal['hosts'].items())):
            target = Path(record['target'])
            os.replace(target, transaction / host / 'rolled-back-installation')
            restored.append(host)
            if record['had_previous']:
                os.replace(transaction / host / 'previous', target)
    except Exception:
        for host in reversed(restored):
            record = journal['hosts'][host]
            target = Path(record['target'])
            if target.exists():
                os.replace(target, transaction / host / 'previous')
            os.replace(transaction / host / 'rolled-back-installation', target)
        raise
    journal['status'] = 'rolled-back'
    _write_json(journal_path, journal)
    return {'status': 'rolled-back', 'transaction': str(transaction)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--version', default=VERSION)
    verify = sub.add_parser('verify')
    verify.add_argument('--package', type=Path, required=True)
    for name in ('plan', 'install'):
        command = sub.add_parser(name)
        command.add_argument('--package', type=Path, required=True)
        command.add_argument('--evidence', type=Path, required=True)
        command.add_argument('--host', choices=('codex', 'claude-code'), action='append', required=True)
        command.add_argument('--home', type=Path, default=Path.home())
        command.add_argument('--backup-root', type=Path,
                             default=Path.home() / '.local/state/korean-protocol/skill-backups')
    rollback = sub.add_parser('rollback')
    rollback.add_argument('--transaction', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'build':
            result = build_package(args.root, args.output, args.version)
        elif args.command == 'verify':
            manifest, _ = verify_package(args.package)
            result = {'status': 'verified-bytes', 'manifest': manifest,
                      'package_sha256': digest(args.package.read_bytes()),
                      'publisher_authenticated': False}
        elif args.command == 'rollback':
            result = rollback_installation(args.transaction)
        else:
            result = install_package(args.package, default_targets(args.host, args.home),
                                     args.backup_root, args.evidence, dry_run=args.command == 'plan')
    except (ValueError, OSError, KeyError, ImportError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
