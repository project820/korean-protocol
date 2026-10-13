"""Durable signed publication receipts and content-only GitHub Release archives."""
import io
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from distribution import actions_release as a
from distribution import release
from runtime import kproto as k

RECEIPT_NAMESPACE = 'kproto-publication-receipt-v1'
RECEIPT_FILES = ('publication-receipt.json', 'publication-receipt.json.sig')
CONTENT_ASSET = 'signed-content.zip'
TAG = re.compile(r'kproto-history-([0-9]+\.[0-9]+\.[0-9]+)-([1-9][0-9]*)')


def validate_receipt(value):
    fields = {'schema_version', 'kind', 'repository', 'workflow', 'ref', 'run_id', 'signing_attempt',
              'head_sha', 'artifact_id', 'published_at', 'version', 'sequence', 'manifest_sha256', 'content_tree_sha256'}
    if (not isinstance(value, dict) or set(value) != fields or type(value['schema_version']) is not int or
            value['schema_version'] != 1 or value['kind'] != 'publication' or value['workflow'] != a.WORKFLOW or
            value['ref'] != 'refs/heads/main'):
        raise k.InputError('Publication receipt schema is invalid')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value['repository']):
        raise k.InputError('Publication receipt repository is invalid')
    for field in ('run_id', 'signing_attempt', 'artifact_id', 'sequence'):
        if type(value[field]) is not int or not 1 <= value[field] <= 9007199254740991:
            raise k.InputError('Publication receipt numeric identity is invalid')
    if not re.fullmatch('[a-f0-9]{40}', value['head_sha']):
        raise k.InputError('Publication receipt commit identity is invalid')
    for field in ('manifest_sha256', 'content_tree_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', value[field]):
            raise k.InputError('Publication receipt content digest is invalid')
    k.version_tuple(value['version'])
    # GitHub job timestamps are ISO UTC seconds.
    from datetime import datetime
    datetime.strptime(value['published_at'], '%Y-%m-%dT%H:%M:%SZ')
    return value


def verify_receipt(directory, public, fingerprint, static):
    release._fingerprint(public, fingerprint)
    raw = k.read_bytes(Path(directory) / RECEIPT_FILES[0], 65536)
    value = validate_receipt(k.strict_json(raw))
    with tempfile.TemporaryDirectory(prefix='kproto-receipt-verify-') as temporary:
        allowed = Path(temporary) / 'allowed'
        allowed.write_bytes(b'kproto-publication-receipt ' + k.read_bytes(public).strip() + b'\n')
        result = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed),
            '-I', 'kproto-publication-receipt', '-n', RECEIPT_NAMESPACE,
            '-s', str(Path(directory) / RECEIPT_FILES[1])], input=raw, capture_output=True)
        if result.returncode:
            raise k.TrustError('Publication receipt signature is invalid')
    manifest, _ = a.authenticated_history(static, public, fingerprint)
    files = a.static_files(static)
    if (value['version'] != manifest['version'] or value['sequence'] != manifest['sequence'] or
            value['manifest_sha256'] != k.digest(files['stable/release.json']) or
            value['content_tree_sha256'] != a.tree_digest(files)):
        raise k.TrustError('Publication receipt does not bind the exact retained content tree')
    return value


def publication(api, run_id, rehearsal=False, allow_missing=False):
    if not re.fullmatch('[1-9][0-9]{0,19}', str(run_id)):
        raise k.InputError('Archive run ID must be a positive integer')
    try:
        run = api.request('/actions/runs/' + str(run_id))
        jobs = list(api.pages('/actions/runs/' + str(run_id) + '/jobs?filter=all', 'jobs'))
    except a.APIError as error:
        if error.status == 404 and allow_missing:
            return None
        raise
    if (run.get('event') != 'workflow_dispatch' or run.get('path') != a.WORKFLOW or
            run.get('head_branch') != 'main' or run.get('head_repository', {}).get('full_name') != api.repository):
        raise k.TrustError('Archive source must be this repository release workflow on main')
    published = [job for job in jobs if job.get('name') == 'publish' and job.get('conclusion') == 'success']
    if rehearsal:
        if published or run.get('status') != 'completed' or run.get('conclusion') != 'success':
            raise k.TrustError('Rehearsal requires a successful signing dry-run without publication')
        signers = [job for job in jobs if job.get('name') == 'sign' and job.get('conclusion') == 'success']
    else:
        if not published:
            raise k.TrustError('Archive source has no successful Pages publication')
        deployed = max(published, key=lambda job: job['completed_at'])
        signers = [job for job in jobs if job.get('name') == 'sign' and job.get('conclusion') == 'success' and
                   job['run_attempt'] <= deployed['run_attempt'] and job['completed_at'] <= deployed['started_at']]
    if not signers:
        raise k.TrustError('Archive source has no successful signing job')
    signer = max(signers, key=lambda job: (job['run_attempt'], job['completed_at']))
    return dict(run, signing_attempt=signer['run_attempt'], published_at=None if rehearsal else deployed['completed_at'])


def artifact(api, run, prefix, attempt=None):
    expected = prefix + '-' + str(run['id']) + '-' + str(attempt or run['signing_attempt'])
    matches = [item for item in api.pages('/actions/runs/' + str(run['id']) + '/artifacts', 'artifacts')
               if item.get('name') == expected and item.get('workflow_run', {}).get('id') == run['id']]
    if len(matches) != 1 or matches[0].get('expired') is not False:
        raise k.TrustError('Publication artifact is missing or expired before durable archival')
    return matches[0]


def zip_content(static):
    output = io.BytesIO()
    files = a.static_files(static)
    if sum(map(len, files.values())) > a.MAX_ARCHIVE:
        raise k.InputError('Content archive exceeds the 64 MiB limit')
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    value = output.getvalue()
    if len(value) > a.MAX_ARCHIVE:
        raise k.InputError('Content archive exceeds the 64 MiB limit')
    return value


def extract_receipt(data, output):
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            if item.filename not in RECEIPT_FILES or item.filename in files or item.file_size > 65536 or stat.S_ISLNK(item.external_attr >> 16):
                raise k.InputError('Publication receipt artifact contains unlisted files')
            files[item.filename] = archive.read(item)
    if set(files) != set(RECEIPT_FILES):
        raise k.InputError('Publication receipt artifact is incomplete')
    release._write_tree(output, files)


def body_schema(body):
    value = k.strict_json(body.encode())
    fields = {'schema_version', 'repository', 'run_id', 'signing_attempt', 'head_sha',
              'artifact_id', 'content_sha256', 'version', 'sequence', 'rehearsal'}
    if not isinstance(value, dict) or set(value) != fields or type(value['schema_version']) is not int or value['schema_version'] != 1 or type(value['rehearsal']) is not bool:
        raise k.InputError('Durable archive provenance schema is invalid')
    for field in ('run_id', 'signing_attempt', 'artifact_id', 'sequence'):
        if type(value[field]) is not int or value[field] <= 0:
            raise k.InputError('Durable archive identity is invalid')
    if not re.fullmatch('[a-f0-9]{64}', value['content_sha256']) or not re.fullmatch('[a-f0-9]{40}', value['head_sha']):
        raise k.InputError('Durable archive digest or commit is invalid')
    k.version_tuple(value['version'])
    return value


def read_archive(api, record, public, fingerprint, output, rehearsal=False):
    provenance = body_schema(record['body'])
    prefix = 'kproto-rehearsal-' if rehearsal else 'kproto-history-'
    expected_tag = prefix + provenance['version'] + '-' + str(provenance['sequence'])
    if (record.get('tag_name') != expected_tag or provenance['repository'] != api.repository or
            provenance['rehearsal'] != rehearsal or record.get('draft') is not rehearsal):
        raise k.TrustError('Durable archive namespace or completion state is invalid')
    expected_assets = {CONTENT_ASSET} if rehearsal else {CONTENT_ASSET, *RECEIPT_FILES}
    assets = list(api.pages('/releases/' + str(record['id']) + '/assets'))
    if len(assets) != len(expected_assets) or {asset['name'] for asset in assets} != expected_assets:
        raise k.InputError('Durable archive assets are incomplete or contain unlisted files')
    content, receipt_data = None, {}
    for asset in assets:
        limit = a.MAX_ARCHIVE if asset['name'] == CONTENT_ASSET else 65536
        if type(asset['size']) is not int or not 0 < asset['size'] <= limit:
            raise k.InputError('Durable archive asset exceeds its size limit')
        data = api.request('/releases/assets/' + str(asset['id']), binary=True)
        if len(data) != asset['size'] or len(data) > limit:
            raise k.TrustError('Durable archive asset length differs from API metadata')
        if asset['name'] == CONTENT_ASSET:
            content = data
        else:
            receipt_data[asset['name']] = data
    if k.digest(content) != provenance['content_sha256']:
        raise k.TrustError('Durable archive content digest differs from provenance')
    a.extract_artifact(content, output)
    manifest, _ = a.authenticated_history(output, public, fingerprint)
    if manifest['version'] != provenance['version'] or manifest['sequence'] != provenance['sequence']:
        raise k.TrustError('Signed manifest differs from durable archive identity')
    if not rehearsal:
        with tempfile.TemporaryDirectory(prefix='kproto-archive-receipt-') as temporary:
            directory = Path(temporary).resolve() / 'publication'
            release._write_tree(directory, receipt_data)
            receipt = verify_receipt(directory, public, fingerprint, output)
        for field in ('repository', 'run_id', 'signing_attempt', 'head_sha', 'artifact_id', 'version', 'sequence'):
            if receipt[field] != provenance[field]:
                raise k.TrustError('Signed receipt differs from durable archive provenance')
    run = publication(api, provenance['run_id'], rehearsal, allow_missing=not rehearsal)
    if run is not None:
        if run['head_sha'] != provenance['head_sha'] or run['signing_attempt'] != provenance['signing_attempt']:
            raise k.TrustError('Durable archive differs from authenticated workflow identity')
        if not rehearsal and run['published_at'] != receipt['published_at']:
            raise k.TrustError('Signed receipt differs from actual publication time')
    if rehearsal:
        # Draft GitHub releases need not have created their tag yet.
        if record.get('target_commitish') != provenance['head_sha']:
            raise k.TrustError('Rehearsal draft differs from its verified source commit')
    else:
        ref = api.request('/git/ref/tags/' + expected_tag)
        if ref.get('object', {}).get('type') != 'commit' or ref['object']['sha'] != provenance['head_sha']:
            raise k.TrustError('Durable archive tag differs from its verified source commit')
    return provenance


def verify_live_stable(api, static):
    if api.request('').get('private') is not False:
        raise k.TrustError('Durable publication history requires the live public Pages endpoint')
    owner, name = api.repository.split('/')
    origin = 'https://' + owner.lower() + '.github.io/' + name + '/stable/'
    for filename in ('release.json', 'release.json.sig'):
        try:
            with urllib.request.build_opener(k.NoRedirect()).open(origin + filename, timeout=30) as response:
                live = response.read(65537)
        except (urllib.error.URLError, OSError):
            raise k.NetworkError('Live Pages history could not be verified; release is blocked') from None
        if len(live) > 65536 or live != k.read_bytes(Path(static) / 'stable' / filename, 65536):
            raise k.TrustError('Durable archive differs from live Pages stable history; recovery is required')


def latest(api, public, fingerprint, output):
    records = []
    for record in api.pages('/releases'):
        match = TAG.fullmatch(record.get('tag_name', ''))
        if not match:
            continue
        if record.get('draft') is not False:
            raise k.TrustError('Incomplete durable publication archive exists; recovery is required')
        records.append((int(match[2]), record))
    if not records:
        return None
    if len(records) > a.MAX_VERSIONS or len({sequence for sequence, _ in records}) != len(records):
        raise k.TrustError('Durable archive history exceeds bounds or has conflicting sequences')
    _, record = max(records, key=lambda item: item[0])
    result = read_archive(api, record, public, fingerprint, output)
    verify_live_stable(api, output)
    return result


def store(api, provenance, assets):
    """Create a draft, write only missing exact assets, then complete publication."""
    rehearsal = provenance['rehearsal']
    tag = ('kproto-rehearsal-' if rehearsal else 'kproto-history-') + provenance['version'] + '-' + str(provenance['sequence'])
    body = k.json_bytes(provenance).decode()
    records = [record for record in api.pages('/releases') if record.get('tag_name') == tag]
    if len(records) > 1:
        raise k.TrustError('Durable archive tag is ambiguous')
    if records:
        record = records[0]
        if record.get('body') != body or record.get('target_commitish') != provenance['head_sha']:
            raise k.TrustError('Existing durable archive differs; preserve it and resolve the conflict')
    else:
        record = api.request('/releases', method='POST', data={'tag_name': tag, 'target_commitish': provenance['head_sha'],
            'name': tag, 'body': body, 'draft': True, 'prerelease': rehearsal, 'make_latest': 'false'})
    existing = list(api.pages('/releases/' + str(record['id']) + '/assets'))
    if len({asset['name'] for asset in existing}) != len(existing) or any(asset['name'] not in assets for asset in existing):
        raise k.TrustError('Existing archive contains unexpected or duplicate assets')
    for asset in existing:
        if asset.get('size') != len(assets[asset['name']]) or api.request('/releases/assets/' + str(asset['id']), binary=True) != assets[asset['name']]:
            raise k.TrustError('Existing archive asset bytes differ; preserve it and resolve the conflict')
    names = {asset['name'] for asset in existing}
    if record.get('draft') is False and names != set(assets):
        raise k.TrustError('Completed archive is incomplete; refusing to modify it')
    for name, data in assets.items():
        if name not in names:
            api.request('/releases/' + str(record['id']) + '/assets?name=' + urllib.parse.quote(name, safe=''),
                        method='POST', data=data, upload=True)
    uploaded = list(api.pages('/releases/' + str(record['id']) + '/assets'))
    if len(uploaded) != len(assets) or {item['name'] for item in uploaded} != set(assets):
        raise k.TrustError('Archive upload did not produce the exact expected assets')
    for item in uploaded:
        if item.get('size') != len(assets[item['name']]) or api.request('/releases/assets/' + str(item['id']), binary=True) != assets[item['name']]:
            raise k.TrustError('Archive upload bytes differ; incomplete draft is preserved')
    if not rehearsal and record.get('draft') is True:
        api.request('/releases/' + str(record['id']), method='PATCH', data={'draft': False, 'make_latest': 'false'})
    return tag


def completed_for_run(api, run_id, public, fingerprint, output):
    for record in api.pages('/releases'):
        if TAG.fullmatch(record.get('tag_name', '')) and record.get('draft') is False:
            metadata = body_schema(record['body'])
            if metadata['run_id'] == int(run_id):
                return read_archive(api, record, public, fingerprint, output)
    return None


def prepare_receipt(api, run_id, public, fingerprint, work):
    static = Path(work) / 'receipt-static'
    existing = completed_for_run(api, run_id, public, fingerprint, static)
    if existing:
        # Nothing needs re-signing or rewriting when the completed archive exists.
        (Path(work) / 'receipt-already-archived').write_text('verified\n')
        return
    run = publication(api, run_id)
    item = artifact(api, run, 'kproto-static')
    a.extract_artifact(api.request('/actions/artifacts/' + str(item['id']) + '/zip', binary=True), static)
    manifest, _ = a.authenticated_history(static, public, fingerprint)
    files = a.static_files(static)
    receipt = dict(schema_version=1, kind='publication', repository=api.repository, workflow=a.WORKFLOW,
        ref='refs/heads/main', run_id=run['id'], signing_attempt=run['signing_attempt'], head_sha=run['head_sha'],
        artifact_id=item['id'], published_at=run['published_at'], version=manifest['version'], sequence=manifest['sequence'],
        manifest_sha256=k.digest(files['stable/release.json']), content_tree_sha256=a.tree_digest(files))
    validate_receipt(receipt)
    release._write_tree(Path(work) / 'publication', {RECEIPT_FILES[0]: k.json_bytes(receipt)})


def sign_receipt(work, secret, public, fingerprint):
    if (Path(work) / 'receipt-already-archived').exists():
        return
    directory = Path(work) / 'publication'
    validate_receipt(k.strict_json(k.read_bytes(directory / RECEIPT_FILES[0], 65536)))
    a.sign_file(directory / RECEIPT_FILES[0], secret, public, RECEIPT_NAMESPACE)
    verify_receipt(directory, public, fingerprint, Path(work) / 'receipt-static')


def archive_run(api, run_id, public, fingerprint, work, rehearsal=False, receipt_run_id=None, receipt_attempt='1'):
    if not re.fullmatch('[1-9][0-9]{0,19}', str(run_id)):
        raise k.InputError('Archive run ID must be a positive integer')
    if rehearsal and api.request('').get('private') is not True:
        raise k.TrustError('Draft storage rehearsal requires a private repository')
    if not rehearsal:
        existing = completed_for_run(api, run_id, public, fingerprint, Path(work) / 'archived')
        if existing:
            return existing
    run = publication(api, run_id, rehearsal)
    item = artifact(api, run, 'kproto-static')
    static = Path(work) / 'archive-static'
    a.extract_artifact(api.request('/actions/artifacts/' + str(item['id']) + '/zip', binary=True), static)
    manifest, _ = a.authenticated_history(static, public, fingerprint)
    content = zip_content(static)
    assets = {CONTENT_ASSET: content}
    if not rehearsal:
        receipt_run = {'id': int(receipt_run_id or run_id)}
        receipt_jobs = [job for job in api.pages('/actions/runs/' + str(receipt_run['id']) + '/jobs?filter=all', 'jobs')
                        if job.get('name') == 'receipt' and job.get('conclusion') == 'success' and
                        job['run_attempt'] <= int(receipt_attempt)]
        if not receipt_jobs:
            raise k.TrustError('Archive has no successful receipt signing job')
        actual_attempt = max(job['run_attempt'] for job in receipt_jobs)
        receipt_item = artifact(api, receipt_run, 'kproto-publication-receipt', actual_attempt)
        directory = Path(work) / 'archive-publication'
        extract_receipt(api.request('/actions/artifacts/' + str(receipt_item['id']) + '/zip', binary=True), directory)
        receipt = verify_receipt(directory, public, fingerprint, static)
        expected = {'repository': api.repository, 'run_id': run['id'], 'signing_attempt': run['signing_attempt'],
                    'head_sha': run['head_sha'], 'artifact_id': item['id'], 'published_at': run['published_at']}
        if any(receipt[field] != value for field, value in expected.items()):
            raise k.TrustError('Signed receipt differs from actual published workflow')
        assets.update({name: k.read_bytes(directory / name, 65536) for name in RECEIPT_FILES})
    provenance = dict(schema_version=1, repository=api.repository, run_id=run['id'],
        signing_attempt=run['signing_attempt'], head_sha=run['head_sha'], artifact_id=item['id'],
        content_sha256=k.digest(content), version=manifest['version'], sequence=manifest['sequence'], rehearsal=rehearsal)
    return store(api, provenance, assets)
