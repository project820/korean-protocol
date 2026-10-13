"""GitHub Actions adapter for signed releases; all publication gates fail closed."""
import argparse
from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

from distribution import release
from runtime import kproto as k

WORKFLOW = '.github/workflows/release.yml'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_VERSIONS = 32


class APIError(k.NetworkError):
    def __init__(self, status):
        super().__init__('GitHub API request failed')
        self.status = status


def boolean(value):
    if value not in ('true', 'false'):
        raise k.InputError('Boolean inputs must be true or false')
    return value == 'true'


def publication_attempt(publish, attempt):
    if publish and attempt != '1':
        raise k.TrustError('Publication reruns are forbidden; start a fresh workflow_dispatch to recheck release history')


def validate_dispatch(archive_only, publish, archive_run_id):
    if archive_only:
        if publish or not re.fullmatch('[1-9][0-9]{0,19}', archive_run_id):
            raise k.InputError('archive_only requires a positive original run ID and cannot publish Pages')
    elif archive_run_id:
        raise k.InputError('archive_run_id is reserved for archive_only recovery')


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise k.InputError('Invalid repository identity')
        if not token:
            raise k.InputError('GitHub token is required for release-history verification')
        self.repository, self.token = repository, token

    def request(self, path, binary=False, method='GET', data=None, upload=False):
        base = 'https://uploads.github.com/repos/' if upload else 'https://api.github.com/repos/'
        body = data if isinstance(data, bytes) else k.json_bytes(data) if data is not None else None
        request = urllib.request.Request(base + self.repository + path, data=body, method=method,
            headers={'Authorization': 'Bearer ' + self.token,
                     'Accept': 'application/octet-stream' if binary and path.startswith('/releases/assets/') else 'application/vnd.github+json',
                     'Content-Type': 'application/octet-stream' if upload else 'application/json',
                     'X-GitHub-Api-Version': '2022-11-28'})
        # Artifact download uses a signed storage redirect. urllib does not strip
        # Authorization on cross-host redirects, so handle the redirect explicitly.
        class CaptureRedirect(urllib.request.HTTPRedirectHandler):
            destination = None

            def redirect_request(self, req, fp, code, msg, headers, newurl):
                self.destination = newurl
                return None

        handler = CaptureRedirect()
        try:
            response = urllib.request.build_opener(handler).open(request, timeout=30)
        except urllib.error.HTTPError as error:
            destination = handler.destination
            if not binary or error.code != 302 or not isinstance(destination, str) or not destination.startswith('https://'):
                raise APIError(error.code) from None
            error.close()
            response = urllib.request.urlopen(urllib.request.Request(handler.destination), timeout=30)
        with response:
            data = response.read(MAX_ARCHIVE + 1)
        if len(data) > MAX_ARCHIVE:
            raise k.InputError('GitHub response exceeds release-history size limit')
        return data if binary else k.strict_json(data)

    def pages(self, path, field=None):
        for page in range(1, 101):
            result = self.request(path + ('&' if '?' in path else '?') + 'per_page=100&page=' + str(page))
            items = result[field] if field else result
            yield from items
            if len(items) < 100:
                return
        raise k.TrustError('Release-history pagination limit reached; publication is blocked')

    def published_run(self):
        latest = None
        try:
            runs = list(self.pages('/actions/workflows/release.yml/runs?branch=main&status=completed', 'workflow_runs'))
        except APIError as error:
            if error.status == 404:
                return None
            raise
        for run in runs:
            if run.get('event') != 'workflow_dispatch' or run.get('path') != WORKFLOW:
                continue
            try:
                jobs = list(self.pages('/actions/runs/' + str(run['id']) + '/jobs?filter=all', 'jobs'))
            except APIError as error:
                if error.status == 404:
                    continue
                raise
            for published in jobs:
                if published.get('name') != 'publish' or published.get('conclusion') != 'success':
                    continue
                # A failed-job-only rerun can publish attempt 2 using the sealed
                # artifact from sign attempt 1. Bind that artifact to the actual
                # successful sign job, not the overall run's current attempt.
                signers = [job for job in jobs if job.get('name') == 'sign' and
                           job.get('conclusion') == 'success' and
                           job['run_attempt'] <= published['run_attempt'] and
                           job['completed_at'] <= published['started_at']]
                if not signers:
                    raise k.TrustError('Published run has no authenticated successful signing job')
                signer = max(signers, key=lambda job: (job['run_attempt'], job['completed_at']))
                candidate = dict(run, signing_attempt=signer['run_attempt'], published_at=published['completed_at'])
                if latest is None or candidate['published_at'] > latest['published_at']:
                    latest = candidate
        return latest


def preflight(api, publish, enabled, first_release, artifact_id, allow_first=False, durable=None, durable_checked=False):
    if first_release and (artifact_id or durable) or not first_release and not (artifact_id or durable):
        raise k.InputError('Choose exactly one of first_release=true or previous_artifact_id')
    if artifact_id and not re.fullmatch(r'[1-9][0-9]{0,19}', artifact_id):
        raise k.InputError('previous_artifact_id must be a positive numeric artifact ID')
    metadata = api.request('')
    if metadata.get('full_name') != api.repository:
        raise k.TrustError('Repository identity differs from the authenticated GitHub response')
    if publish and metadata.get('private') is not False:
        raise k.TrustError('Publication is blocked while the repository is private')
    if publish and not enabled:
        raise k.TrustError('Publication requires KPROTO_PAGES_ENABLED=true')
    previous_run = api.published_run()
    if durable:
        if previous_run and (previous_run['id'] != durable['run_id'] or
                previous_run['signing_attempt'] != durable['signing_attempt']):
            raise k.TrustError('Durable archive conflicts with the latest actual publication; archive recovery is required')
        return durable
    if first_release:
        if previous_run:
            raise k.TrustError('Published history exists; first-release reset is forbidden')
        if publish and not allow_first:
            raise k.TrustError('First publication requires KPROTO_ALLOW_FIRST_PUBLICATION=true')
        return None
    if not previous_run:
        raise k.TrustError('No successful prior Pages publication was found')
    if durable_checked:
        raise k.TrustError('Successful publication has no durable archive; archive recovery is required')
    artifact = api.request('/actions/artifacts/' + artifact_id)
    expected = 'kproto-static-' + str(previous_run['id']) + '-' + str(previous_run['signing_attempt'])
    if (artifact.get('expired') is not False or artifact.get('name') != expected or
            artifact.get('workflow_run', {}).get('id') != previous_run['id']):
        raise k.TrustError('Previous artifact must belong to the latest successful publication; expired or missing history blocks release (90-day retention)')
    return artifact


def extract_artifact(data, output):
    files, total = {}, 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            name = item.filename
            if item.is_dir():
                continue
            path = PurePosixPath(name)
            mode = item.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in name or str(path) != name or
                    name in files or stat.S_ISLNK(mode) or item.file_size > k.MAX_FILE_BYTES):
                raise k.InputError('Previous artifact contains an invalid file')
            total += item.file_size
            if total > MAX_ARCHIVE or len(files) >= MAX_VERSIONS * 9:
                raise k.InputError('Previous artifact exceeds history limits')
            files[name] = archive.read(item)
    release._write_tree(output, files)


def authenticated_history(previous, public_key, fingerprint):
    """Authenticate every retained payload and reject every unlisted file."""
    current, raw, files, signature = release._load_static(previous, public_key, fingerprint, fresh=False)
    payload = {'releases/' + current['version'] + '/' + name: value for name, value in files.items()}
    payload['history/' + current['version'] + '/release.json'] = raw
    payload['history/' + current['version'] + '/release.json.sig'] = signature
    expected = {'stable/release.json', 'stable/release.json.sig'} | {
        'releases/' + current['version'] + '/' + name for name in k.CONTENT_PATHS}
    manifests = [current]
    history_root = Path(previous) / 'history'
    if history_root.exists():
        k.safe_path(history_root)
        for version_path in sorted(history_root.iterdir()):
            k.safe_path(version_path)
            k.version_tuple(version_path.name)
            if version_path.name == current['version'] or not version_path.is_dir():
                raise k.InputError('Invalid archived release version')
            with tempfile.TemporaryDirectory(prefix='kproto-history-') as temporary:
                static = Path(temporary).resolve() / 'static'
                archived = {'stable/' + name: k.read_bytes(version_path / name) for name in ('release.json', 'release.json.sig')}
                archived.update({'releases/' + version_path.name + '/' + name:
                                 k.read_bytes(Path(previous) / 'releases' / version_path.name / name) for name in k.CONTENT_PATHS})
                release._write_tree(static, archived)
                manifest, _, _, _ = release._load_static(static, public_key, fingerprint, fresh=False)
                if manifest['version'] != version_path.name:
                    raise k.TrustError('Archived manifest version differs from its directory')
            manifests.append(manifest)
            for name, value in archived.items():
                destination = ('history/' + version_path.name + '/' + name.removeprefix('stable/')) if name.startswith('stable/') else name
                payload[destination] = value
                expected.add(destination)
    if len(manifests) > MAX_VERSIONS:
        raise k.InputError('Release history reached the 32-version limit; publication is blocked')
    manifests.sort(key=lambda manifest: manifest['sequence'])
    for earlier, later in zip(manifests, manifests[1:]):
        if (earlier['sequence'] + 1 != later['sequence'] or
                k.version_tuple(earlier['version']) >= k.version_tuple(later['version']) or
                earlier['issued_at'] > later['issued_at']):
            raise k.TrustError('Archived release history is not monotonic')
    if manifests[0]['sequence'] != 1 or manifests[-1] != current:
        raise k.TrustError('Archived release history is incomplete')
    actual = set()
    for path in Path(previous).rglob('*'):
        k.safe_path(path)
        if path.is_file():
            actual.add(path.relative_to(previous).as_posix())
    if actual != expected:
        raise k.InputError('Previous artifact contains unlisted files or missing history')
    return current, payload


def static_files(path):
    return {file.relative_to(path).as_posix(): k.read_bytes(file) for file in Path(path).rglob('*') if file.is_file()}


def tree_digest(files):
    return k.digest(k.json_bytes({name: k.digest(value) for name, value in sorted(files.items())}))


def sign_file(path, secret, public_key, namespace):
    if not secret:
        raise k.InputError('KPROTO_SIGNING_KEY is not configured')
    # The temporary key is never printed, exported, or copied to an artifact.
    with tempfile.TemporaryDirectory(prefix='kproto-key-', dir=os.environ.get('RUNNER_TEMP')) as temporary:
        key = Path(temporary) / 'publisher'
        fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(secret.rstrip('\r\n') + '\n')
        child_env = dict(os.environ)
        child_env.pop('KPROTO_SIGNING_KEY', None)
        actual = subprocess.run(['ssh-keygen', '-y', '-f', str(key)], capture_output=True, env=child_env)
        trusted = k.read_bytes(public_key).decode('ascii').split()[:2]
        if actual.returncode or actual.stdout.decode('ascii').split()[:2] != trusted:
            raise k.TrustError('Signing secret does not match the checked-in public key')
        result = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', namespace,
                                 str(path)], capture_output=True, env=child_env)
        if result.returncode:
            raise k.TrustError('OpenSSH release signing failed')


def sign(prepared, secret, public_key):
    sign_file(Path(prepared) / 'stable/release.json', secret, public_key, 'kproto-release-v1')


def confirm_empty_pages(repository):
    owner, name = repository.split('/')
    url = 'https://' + owner.lower() + '.github.io/' + name + '/stable/release.json'
    try:
        with urllib.request.build_opener(k.NoRedirect()).open(url, timeout=30):
            raise k.TrustError('Pages already serves a release; first-publication reset is forbidden')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise k.NetworkError('First publication requires a verified Pages 404') from None


def execute(command, root, work):
    root, work = k.safe_path(root), k.safe_path(work)
    public = root / 'distribution/trust/publisher.pub'
    fingerprint = k.strict_json(k.read_bytes(root / 'distribution/trust/publisher.json'))['fingerprint']
    release._fingerprint(public, fingerprint)
    prepared, previous, state = work / 'prepared', work / 'previous', work / 'state.json'
    if command == 'prepare':
        if os.environ.get('GITHUB_REF') != 'refs/heads/main':
            raise k.TrustError('Only main may prepare an Actions release')
        publish = boolean(os.environ.get('INPUT_PUBLISH', 'false'))
        validate_dispatch(boolean(os.environ.get('ARCHIVE_ONLY', 'false')), publish, os.environ.get('ARCHIVE_RUN_ID', ''))
        publication_attempt(publish, os.environ.get('GITHUB_RUN_ATTEMPT', ''))
        first = boolean(os.environ.get('INPUT_FIRST_RELEASE', 'false'))
        api = GitHub(os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GH_TOKEN', ''))
        from distribution import history_store
        durable = history_store.latest(api, public, fingerprint, work / 'durable')
        if first and durable:
            raise k.TrustError('Durable publication history exists; first-release reset is forbidden')
        artifact = preflight(api, publish, os.environ.get('PAGES_ENABLED') == 'true', first,
                             os.environ.get('INPUT_PREVIOUS_ARTIFACT_ID', ''),
                             os.environ.get('ALLOW_FIRST_PUBLICATION') == 'true', durable=durable, durable_checked=True)
        sequence = 1
        if artifact:
            if durable:
                release._write_tree(previous, static_files(work / 'durable'))
            else:
                extract_artifact(api.request('/actions/artifacts/' + str(artifact['id']) + '/zip', binary=True), previous)
            prior, _ = authenticated_history(previous, public, fingerprint)
            if prior['sequence'] >= MAX_VERSIONS:
                raise k.InputError('Release history reached the 32-version limit; publication is blocked')
            sequence = prior['sequence'] + 1
        elif publish:
            confirm_empty_pages(api.repository)
        version = os.environ.get('INPUT_VERSION', '')
        now = datetime.now(timezone.utc).replace(microsecond=0)
        release.prepare(root, prepared, version, sequence, now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ'), public, fingerprint,
                        previous=previous if artifact else None, first_release=first)
        with state.open('xb') as handle:
            handle.write(k.json_bytes({'first_release': first}))
    elif command == 'sign':
        sign(prepared, os.environ.get('KPROTO_SIGNING_KEY', ''), public)
    elif command == 'seal':
        metadata = k.strict_json(k.read_bytes(state))
        first = metadata['first_release']
        ready = work / 'ready'
        release.seal(prepared, prepared / 'stable/release.json.sig', ready, public, fingerprint,
                     previous=previous if not first else None, first_release=first)
        if not first:
            _, payload = authenticated_history(previous, public, fingerprint)
            for name, data in payload.items():
                destination = ready / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as handle:
                    handle.write(data)
        authenticated_history(ready, public, fingerprint)
    elif command == 'receipt-sign':
        from distribution import history_store
        history_store.sign_receipt(work, os.environ.get('KPROTO_SIGNING_KEY', ''), public, fingerprint)
    else:
        from distribution import history_store
        api = GitHub(os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GH_TOKEN', ''))
        archive_only = boolean(os.environ.get('ARCHIVE_ONLY', 'false'))
        if command != 'rehearse':
            validate_dispatch(archive_only, boolean(os.environ.get('INPUT_PUBLISH', 'false')), os.environ.get('ARCHIVE_RUN_ID', ''))
        run_id = os.environ.get('ARCHIVE_RUN_ID') or os.environ.get('GITHUB_RUN_ID', '')
        if command == 'receipt-prepare':
            history_store.prepare_receipt(api, run_id, public, fingerprint, work)
        else:
            if boolean(os.environ.get('ARCHIVE_ONLY', 'false')) and boolean(os.environ.get('INPUT_PUBLISH', 'false')):
                raise k.InputError('archive_only cannot request a new Pages publication')
            history_store.archive_run(api, run_id, public, fingerprint, work, rehearsal=command == 'rehearse',
                receipt_run_id=os.environ.get('GITHUB_RUN_ID') or str(run_id),
                receipt_attempt=os.environ.get('GITHUB_RUN_ATTEMPT', '1'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'sign', 'seal', 'receipt-prepare', 'receipt-sign', 'archive', 'rehearse'))
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        execute(args.command, args.root, args.work)
    except (k.ProtocolError, OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile):
        # Never expose raw HTTP responses, environment values, or subprocess output.
        print('Actions release failed; check inputs, trust key, publication gates, and signed receipt/archive recovery (32 versions / 64 MiB).', file=sys.stderr)
        return 2
    print(args.command + ': verified')
    return 0


if __name__ == '__main__':
    sys.exit(main())
