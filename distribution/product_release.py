"""Publish verified-source, unsigned user downloads separately from signed archives."""
import argparse
import io
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import zipfile

from distribution import actions_release as a
from distribution import build as package
from distribution import history_store as history
from runtime import kproto as k

SOURCE_TOOLS = ('distribution/build.py', 'distribution/product_release.py',
                'distribution/actions_release.py', 'distribution/history_store.py',
                'distribution/release.py', 'runtime/kproto.py', '.github/workflows/release.yml')
PRODUCT_TAG = re.compile(r'v([0-9]+\.[0-9]+\.[0-9]+)')


def git(root, *arguments):
    result = subprocess.run(['git', '-C', str(root), *arguments], capture_output=True)
    if result.returncode:
        raise k.TrustError('Product source Git identity could not be authenticated')
    return result.stdout


def authenticate_source(api, root, source_sha):
    """Bind every packaged byte and publication tool to the actual main commit."""
    if not re.fullmatch('[a-f0-9]{40}', source_sha):
        raise k.InputError('Product source must be a full commit SHA')
    metadata = api.request('')
    if metadata.get('full_name') != api.repository or metadata.get('private') is not False:
        raise k.TrustError('Product publication requires this live public repository')
    if api.request('/commits/main').get('sha') != source_sha:
        raise k.TrustError('Product source differs from the current trusted main commit')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != source_sha:
        raise k.TrustError('Product source checkout differs from the requested commit')
    for name in sorted(set(package.INPUTS) | set(SOURCE_TOOLS)):
        if k.read_bytes(Path(root)/name) != git(root, 'show', source_sha+':'+name):
            raise k.TrustError('Product source has local changes: '+name)


def verify_content(root, version, manifest):
    k.version_tuple(version)
    if (manifest.get('version') != version or
            {item['path'] for item in manifest['files']} != set(k.CONTENT_PATHS) or
            len(manifest['files']) != len(k.CONTENT_PATHS)):
        raise k.TrustError('Product version or seven signed content files differ')
    for item in manifest['files']:
        data = k.read_bytes(Path(root)/item['path'])
        if len(data) != item['size'] or k.digest(data) != item['sha256']:
            raise k.TrustError('Product source differs from signed content: '+item['path'])


def assets(root, version, source_sha):
    """Build bounded deterministic downloads; checksums are not signatures."""
    k.version_tuple(version)
    prefix = 'korean-protocol-'+version+'-draft'
    if prefix != package.PREFIX:
        raise k.TrustError('Product version differs from the offline package version')
    with tempfile.TemporaryDirectory(prefix='kproto-product-build-') as temporary:
        output = Path(temporary).resolve()/(prefix+'.zip')
        package.build(root, output, source_ref=source_sha)
        archive_bytes = k.read_bytes(output, a.MAX_ARCHIVE)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        chat = archive.read(prefix+'/KOREAN-PROTOCOL.md')
    files = {prefix+'.zip': archive_bytes, 'KOREAN-PROTOCOL.md': chat}
    files['SHA256SUMS'] = ''.join(k.digest(data)+'  '+name+'\n'
                                  for name, data in sorted(files.items())).encode()
    validate_assets(version, files)
    return files


def validate_assets(version, files):
    expected = {'korean-protocol-'+version+'-draft.zip': a.MAX_ARCHIVE,
                'KOREAN-PROTOCOL.md': 4*k.MAX_FILE_BYTES, 'SHA256SUMS': 65536}
    if set(files) != set(expected):
        raise k.InputError('Product assets differ from the exact public allowlist')
    for name, data in files.items():
        if not isinstance(data, bytes) or not 0 < len(data) <= expected[name]:
            raise k.InputError('Product asset exceeds its size limit: '+name)


def notes(repository, version, source_sha, provenance, manifest_bytes, files):
    archive_tag = 'kproto-history-'+version+'-'+str(provenance['sequence'])
    base = 'https://github.com/'+repository
    downloads = base+'/releases/download/v'+version+'/'
    metadata = dict(schema_version=1, kind='unsigned-user-product', repository=repository,
                    version=version, source_sha=source_sha, signed_history_tag=archive_tag,
                    signed_content_source_sha=provenance['head_sha'],
                    signed_manifest_sha256=k.digest(manifest_bytes),
                    assets={name: k.digest(data) for name, data in sorted(files.items())})
    changes = ('V7 r2의 정보 배열과 표현 운영 지침을 반영했다. '
               '대상·조건·수량·기한을 드러내고 복원 가능한 생략을 허용한다.'
               if version == '0.7.0' else '공개 서명본과 같은 규약·사전을 설치 도구와 채팅용 파일로 제공한다.')
    return ('한국어 규약과 사전을 Codex·Claude Code·일반 채팅에서 사용한다.\n\n'
            '### 변경 사항\n\n'+changes+'\n\n'
            '### 설치\n\n'
            '1. ['+'오프라인 ZIP]('+downloads+'korean-protocol-'+version+'-draft.zip)을 내려받아 압축을 푼다. '
            '`START-HERE.md`와 `INSTALL.md`를 따라 설치한다.\n'
            '2. 일반 채팅은 [KOREAN-PROTOCOL.md]('+downloads+'KOREAN-PROTOCOL.md)를 첨부하고 '
            'ZIP의 `CHAT-START.md`를 따른다.\n'
            '3. [SHA256SUMS]('+downloads+'SHA256SUMS)로 다운로드한 두 파일의 손상을 확인한다.\n\n'
            '### 제한과 출처\n\n'
            'ZIP·채팅 파일은 미서명 연구·개발 초안이며 SHA256SUMS는 발행자 인증이 아니다. '
            'LLM의 규약 준수나 독자 효과를 보장하지 않는다. '
            '원격 갱신은 [서명 설치 안내]('+base+'/blob/'+source_sha+'/docs/distribution/signed-install.md)를 따른다.\n\n'
            '설치 도구·안내의 원본은 [`'+source_sha[:7]+'`]('+base+'/commit/'+source_sha+')이며, '
            '일곱 콘텐츠 파일은 [서명 이력]('+base+'/releases/tag/'+archive_tag+')과 해시가 같다. '
            '서명 이력의 원본 커밋은 `'+provenance['head_sha']+'`이다.\n\n'
            '<!-- kproto-product-v1\n'+k.json_bytes(metadata).decode()+'-->\n')


def check_tag(api, tag, source_sha, required=False):
    try:
        value = api.request('/git/ref/tags/'+tag)
    except a.APIError as error:
        if error.status == 404 and not required:
            return
        raise
    if value.get('object') != {'type': 'commit', 'sha': source_sha}:
        # GitHub also includes URL fields in the object.
        item = value.get('object', {})
        if item.get('type') != 'commit' or item.get('sha') != source_sha:
            raise k.TrustError('Product tag differs from the verified source commit')


def verify_assets(api, record, files, complete):
    uploaded = list(api.pages('/releases/'+str(record['id'])+'/assets'))
    names = [item['name'] for item in uploaded]
    if len(set(names)) != len(names) or set(names)-set(files) or (complete and set(names) != set(files)):
        raise k.TrustError('Product release has unexpected, duplicate, or missing assets')
    for item in uploaded:
        expected = files[item['name']]
        if type(item.get('size')) is not int or item['size'] != len(expected):
            raise k.TrustError('Product release asset size differs; preserve existing artifacts')
        actual = api.request('/releases/assets/'+str(item['id']), binary=True)
        if actual != expected:
            raise k.TrustError('Product release asset bytes differ; preserve existing artifacts')
    return set(names)


def reject_newer(records, version):
    if any(PRODUCT_TAG.fullmatch(record.get('tag_name', '')) and
           k.version_tuple(record['tag_name'][1:]) > k.version_tuple(version) for record in records):
        raise k.TrustError('A newer product release exists; Latest downgrade is forbidden')


def verify_record(record, expected):
    if (any(record.get(key) != value for key, value in expected.items()) or
            type(record.get('draft')) is not bool):
        raise k.TrustError('Existing product release differs from verified source or notes')


def store(api, version, source_sha, body, files):
    """Resume an identical draft; never overwrite a conflicting release or asset."""
    k.version_tuple(version)
    validate_assets(version, files)
    if not re.fullmatch('[a-f0-9]{40}', source_sha):
        raise k.InputError('Product source must be a full commit SHA')
    tag, title = 'v'+version, 'Korean Protocol '+version
    records = list(api.pages('/releases'))
    reject_newer(records, version)
    matches = [record for record in records if record.get('tag_name') == tag]
    if len(matches) > 1:
        raise k.TrustError('Product release tag is ambiguous')
    check_tag(api, tag, source_sha)
    expected = {'tag_name': tag, 'name': title, 'body': body,
                'target_commitish': source_sha, 'prerelease': False}
    if matches:
        record = matches[0]
        verify_record(record, expected)
    else:
        record = api.request('/releases', method='POST', data={
            'tag_name': tag, 'target_commitish': source_sha, 'name': title, 'body': body,
            'draft': True, 'prerelease': False, 'make_latest': 'false'})
    names = verify_assets(api, record, files, complete=record.get('draft') is False)
    for name, data in sorted(files.items()):
        if name not in names:
            api.request('/releases/'+str(record['id'])+'/assets?name='+urllib.parse.quote(name, safe=''),
                        method='POST', data=data, upload=True)
    verify_assets(api, record, files, complete=True)
    reject_newer(list(api.pages('/releases')), version)
    record = api.request('/releases/'+str(record['id']))
    verify_record(record, expected)
    check_tag(api, tag, source_sha, required=record['draft'] is False)
    if record.get('draft') is True:
        api.request('/releases/'+str(record['id']), method='PATCH', data={'draft': False, 'make_latest': 'true'})
    published = api.request('/releases/'+str(record['id']))
    verify_record(published, expected)
    if published.get('draft') is not False:
        raise k.TrustError('Product publication did not complete; inspect the retained draft')
    verify_assets(api, published, files, complete=True)
    if api.request('/releases/latest').get('tag_name') != tag:
        raise k.TrustError('Product release is not the verified Latest release')
    check_tag(api, tag, source_sha, required=True)
    return tag


def publish(api, root, work, source_sha, version):
    authenticate_source(api, root, source_sha)
    public = Path(root)/'distribution/trust/publisher.pub'
    fingerprint = k.strict_json(k.read_bytes(Path(root)/'distribution/trust/publisher.json'))['fingerprint']
    work = k.safe_path(work)
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='kproto-product-history-', dir=work) as temporary:
        static = Path(temporary).resolve()/'static'
        provenance = history.latest(api, public, fingerprint, static)
        if provenance is None:
            raise k.TrustError('Product release requires authenticated published signed history')
        manifest_bytes = k.read_bytes(static/'stable/release.json')
        manifest = k.strict_json(manifest_bytes)
        verify_content(root, version, manifest)
    files = assets(root, version, source_sha)
    body = notes(api.repository, version, source_sha, provenance, manifest_bytes, files)
    # Verify main again after downloads/build before the first remote write.
    authenticate_source(api, root, source_sha)
    return store(api, version, source_sha, body, files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--source-sha', default=os.environ.get('GITHUB_SHA'), required=not bool(os.environ.get('GITHUB_SHA')))
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    try:
        if os.environ.get('GITHUB_REF', 'refs/heads/main') != 'refs/heads/main':
            raise k.TrustError('Product release must run on main')
        api = a.GitHub(os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GH_TOKEN', ''))
        tag = publish(api, args.root.resolve(), args.work.resolve(), args.source_sha, args.version)
    except (OSError, ValueError, k.ProtocolError) as error:
        parser.exit(1, str(error)+'\n')
    print(tag)


if __name__ == '__main__':
    main()
