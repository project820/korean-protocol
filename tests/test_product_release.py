"""Product publication stays separate from signed-history storage."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from distribution import actions_release as actions
from distribution import product_release as product
from runtime import kproto as k


class ProductAPI:
    repository = 'project820/korean-protocol'

    def __init__(self):
        self.records, self.assets, self.calls = [], {}, []
        self.next_id = 1
        self.main = 'a'*40
        self.refs = {}
        self.corrupt_upload = False

    def pages(self, path):
        if path == '/releases':
            return iter(self.records)
        return iter([dict(id=key, name=name, size=len(data))
                     for key, (release_id, name, data) in self.assets.items()
                     if path == '/releases/'+str(release_id)+'/assets'])

    def request(self, path, binary=False, method='GET', data=None, upload=False):
        self.calls.append((path, method, data))
        if path == '':
            return {'full_name': self.repository, 'private': False}
        if path == '/commits/main':
            return {'sha': self.main}
        if path.startswith('/git/ref/tags/'):
            tag = path.removeprefix('/git/ref/tags/')
            if tag not in self.refs:
                raise actions.APIError(404)
            return {'object': {'type': 'commit', 'sha': self.refs[tag]}}
        if path == '/releases' and method == 'POST':
            record = dict(data, id=10)
            self.records.append(record)
            return record
        if '/assets?name=' in path:
            name = path.split('name=')[1]
            self.assets[self.next_id] = (10, name, data+b'bad' if self.corrupt_upload else data)
            self.next_id += 1
            return {}
        if path.startswith('/releases/assets/'):
            return self.assets[int(path.rsplit('/',1)[1])][2]
        if path == '/releases/10' and method == 'PATCH':
            self.records[0].update(data)
            self.refs[self.records[0]['tag_name']] = self.records[0]['target_commitish']
            return self.records[0]
        if path in ('/releases/10', '/releases/latest'):
            return self.records[0]
        raise AssertionError((path, method))


class ProductStoreTests(unittest.TestCase):
    def setUp(self):
        self.api = ProductAPI()
        self.assets = {'korean-protocol-0.7.0-draft.zip': b'zip',
                       'KOREAN-PROTOCOL.md': b'chat', 'SHA256SUMS': b'checksums'}
        self.body = 'Korean notes\n'

    def store(self):
        return product.store(self.api, '0.7.0', self.api.main, self.body, self.assets)

    def test_stages_verifies_and_publishes_as_explicit_latest(self):
        self.assertEqual('v0.7.0', self.store())
        creates = [data for path, method, data in self.api.calls if path == '/releases' and method == 'POST']
        self.assertEqual(True, creates[0]['draft'])
        self.assertEqual('false', creates[0]['make_latest'])
        self.assertEqual('Korean Protocol 0.7.0', creates[0]['name'])
        self.assertFalse(self.api.records[0]['draft'])
        self.assertEqual('true', self.api.records[0]['make_latest'])
        self.assertEqual(set(self.assets), {item[1] for item in self.api.assets.values()})
        self.assertEqual('v0.7.0', self.store())
        self.assertEqual(1, len(self.api.records))
        self.assertEqual(3, len(self.api.assets))

    def test_interrupted_draft_resumes_only_missing_identical_assets(self):
        self.api.corrupt_upload = True
        with self.assertRaises(k.TrustError):
            self.store()
        self.assertTrue(self.api.records[0]['draft'])
        with self.assertRaises(k.TrustError):
            self.store()
        self.assertFalse(any(method == 'PATCH' for _, method, _ in self.api.calls))

    def test_existing_draft_body_source_asset_or_tag_conflicts_fail_closed(self):
        for field, value in (('body', 'different'), ('target_commitish', 'b'*40),
                             ('name', 'wrong'), ('prerelease', True)):
            self.api = ProductAPI()
            self.store()
            self.api.records[0][field] = value
            before = len(self.api.calls)
            with self.subTest(field=field), self.assertRaises(k.TrustError):
                self.store()
            self.assertTrue(all(method == 'GET' for _, method, _ in self.api.calls[before:]))
        self.api = ProductAPI()
        self.api.refs['v0.7.0'] = 'b'*40
        with self.assertRaises(k.TrustError):
            self.store()
        self.assertEqual([], self.api.records)

    def test_unexpected_duplicate_missing_or_tampered_published_assets_are_preserved(self):
        for change in ('unexpected', 'duplicate', 'missing', 'tampered'):
            self.api = ProductAPI()
            self.store()
            if change in ('unexpected', 'duplicate'):
                self.api.assets[99] = (10, 'extra' if change == 'unexpected' else 'SHA256SUMS', b'x')
            elif change == 'missing':
                self.api.assets.pop(1)
            else:
                owner, name, data = self.api.assets[1]
                self.api.assets[1] = (owner, name, b'bad')
            before = len(self.api.calls)
            with self.subTest(change=change), self.assertRaises(k.TrustError):
                self.store()
            self.assertTrue(all(method == 'GET' for _, method, _ in self.api.calls[before:]))

    def test_concurrent_notes_change_or_newer_product_during_upload_blocks_promotion(self):
        for change in ('notes', 'newer'):
            self.api = ProductAPI()
            original = self.api.request
            def request(path, **kwargs):
                result = original(path, **kwargs)
                if '/assets?name=' in path:
                    if change == 'notes':
                        self.api.records[0]['body'] = 'concurrent authored notes'
                    else:
                        self.api.records.append({'tag_name':'v0.8.0','draft':False})
                return result
            with patch.object(self.api, 'request', side_effect=request), self.subTest(change=change), self.assertRaises(k.TrustError):
                self.store()
            self.assertTrue(self.api.records[0]['draft'])
            self.assertFalse(any(method == 'PATCH' for _,method,_ in self.api.calls))

    def test_latest_and_published_metadata_must_match_after_publication(self):
        original = self.api.request
        def request(path, **kwargs):
            result = original(path, **kwargs)
            return dict(result, tag_name='v0.6.0') if path == '/releases/latest' else result
        with patch.object(self.api, 'request', side_effect=request), self.assertRaisesRegex(k.TrustError, 'Latest'):
            self.store()

    def test_newer_product_and_oversize_assets_block_before_creation(self):
        self.api.records.append({'tag_name':'v0.8.0','draft':False})
        with self.assertRaises(k.TrustError):
            self.store()
        self.api = ProductAPI()
        self.assets['SHA256SUMS'] = b'x'*65537
        with self.assertRaises(k.InputError):
            self.store()
        self.assertEqual([], self.api.records)


class ProductContentTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]

    def test_public_assets_are_reproducible_and_checksums_bind_download_bytes(self):
        first = product.assets(self.repo, '0.7.0', 'a'*40)
        self.assertEqual(first, product.assets(self.repo, '0.7.0', 'a'*40))
        self.assertEqual({'korean-protocol-0.7.0-draft.zip','KOREAN-PROTOCOL.md','SHA256SUMS'}, set(first))
        for line in first['SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ',1)
            self.assertEqual(digest, hashlib.sha256(first[name]).hexdigest())
        import io
        with zipfile.ZipFile(io.BytesIO(first['korean-protocol-0.7.0-draft.zip'])) as archive:
            self.assertEqual(first['KOREAN-PROTOCOL.md'], archive.read('korean-protocol-0.7.0-draft/KOREAN-PROTOCOL.md'))
            for name in k.CONTENT_PATHS:
                self.assertEqual((self.repo/name).read_bytes(), archive.read('korean-protocol-0.7.0-draft/'+name))

    def test_seven_signed_hashes_and_version_must_match_source(self):
        manifest = k.make_manifest(self.repo, '0.7.0', 3, 'SHA256:fixture')
        product.verify_content(self.repo, '0.7.0', manifest)
        for change in ('version','hash','missing'):
            current = k.strict_json(k.json_bytes(manifest))
            if change == 'version': current['version'] = '0.6.0'
            elif change == 'hash': current['files'][0]['sha256'] = '0'*64
            else: current['files'].pop()
            with self.subTest(change=change), self.assertRaises(k.TrustError):
                product.verify_content(self.repo, '0.7.0', current)

    def test_source_must_be_exact_trusted_main_and_snapshot_must_match_commit(self):
        api = ProductAPI()
        with patch.object(product, 'git', return_value=b'a'*40+b'\n'):
            with self.assertRaisesRegex(k.TrustError, 'source'):
                product.authenticate_source(api, self.repo, api.main)
        api.main = 'b'*40
        with self.assertRaisesRegex(k.TrustError, 'main'):
            product.authenticate_source(api, self.repo, 'a'*40)
        with self.assertRaises(k.InputError):
            product.authenticate_source(api, self.repo, 'main')

    def test_exact_source_snapshot_authenticates_and_local_tool_edits_fail(self):
        api = ProductAPI()
        def snapshot(root, *args):
            if args == ('rev-parse', 'HEAD'):
                return (api.main+'\n').encode()
            return (self.repo/args[-1].split(':',1)[1]).read_bytes()
        with patch.object(product, 'git', side_effect=snapshot):
            product.authenticate_source(api, self.repo, api.main)
        original = snapshot
        def changed(root, *args):
            return b'changed' if args[-1].endswith(':distribution/build.py') else original(root,*args)
        with patch.object(product, 'git', side_effect=changed), self.assertRaisesRegex(k.TrustError, 'local changes'):
            product.authenticate_source(api, self.repo, api.main)

    def test_missing_or_different_signed_history_prevents_remote_writes(self):
        api = ProductAPI()
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary).resolve()
            with patch.object(product, 'authenticate_source'), patch.object(product.history, 'latest', return_value=None):
                with self.assertRaisesRegex(k.TrustError, 'signed history'):
                    product.publish(api, self.repo, work, api.main, '0.7.0')
            manifest = k.make_manifest(self.repo, '0.7.0', 3, 'SHA256:fixture')
            manifest['files'][0]['sha256'] = '0'*64
            def history(api, public, fingerprint, static):
                (static/'stable').mkdir(parents=True)
                (static/'stable/release.json').write_bytes(k.json_bytes(manifest))
                return {'head_sha':'b'*40,'sequence':3}
            with patch.object(product, 'authenticate_source'), patch.object(product.history, 'latest', side_effect=history):
                with self.assertRaisesRegex(k.TrustError, 'signed content'):
                    product.publish(api, self.repo, work, api.main, '0.7.0')
        self.assertFalse(any(method != 'GET' for _,method,_ in api.calls))

    def test_same_work_retry_reauthenticates_history_and_resumes_draft(self):
        api = ProductAPI()
        manifest = k.make_manifest(self.repo, '0.7.0', 3, 'SHA256:fixture')
        def history(api, public, fingerprint, static):
            (static/'stable').mkdir(parents=True, exist_ok=False)
            (static/'stable/release.json').write_bytes(k.json_bytes(manifest))
            return {'head_sha':'b'*40,'sequence':3}
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary).resolve()
            original = api.request
            failures = []
            def interrupted(path, **kwargs):
                if '/assets?name=' in path and not failures:
                    failures.append(True)
                    raise k.NetworkError('interrupted')
                return original(path, **kwargs)
            with patch.object(product, 'authenticate_source'), patch.object(product.history, 'latest', side_effect=history):
                with patch.object(api, 'request', side_effect=interrupted), self.assertRaises(k.NetworkError):
                    product.publish(api, self.repo, work, api.main, '0.7.0')
                self.assertTrue(api.records[0]['draft'])
                self.assertEqual('v0.7.0', product.publish(api, self.repo, work, api.main, '0.7.0'))
                self.assertEqual([], list(work.iterdir()))

    def test_product_notes_keep_distinct_unsigned_and_signed_source_provenance(self):
        files = {'example':b'download'}
        result = product.notes('project820/korean-protocol', '0.7.0', 'a'*40,
                               {'head_sha':'b'*40,'sequence':3}, b'signed manifest', files)
        self.assertIn('미서명', result)
        self.assertIn('발행자 인증이 아니다', result)
        self.assertNotIn('습니다', result)
        self.assertNotIn('합니다', result)
        self.assertIn('kproto-history-0.7.0-3', result)
        metadata = k.strict_json(result.split('<!-- kproto-product-v1\n',1)[1].split('-->',1)[0].encode())
        self.assertEqual('a'*40, metadata['source_sha'])
        self.assertEqual('b'*40, metadata['signed_content_source_sha'])
        self.assertEqual(hashlib.sha256(b'download').hexdigest(), metadata['assets']['example'])

    def test_product_workflow_runs_after_archive_and_never_during_historical_recovery(self):
        workflow = (self.repo/'.github/workflows/release.yml').read_text()
        job = workflow.split('\n  product:\n',1)[1]
        self.assertIn('needs: archive', job)
        self.assertIn("needs.archive.result == 'success'", job)
        self.assertIn('!inputs.archive_only', job)
        self.assertIn('python3 -m distribution.product_release',job)
        self.assertIn('contents: write', job)
        self.assertNotIn('KPROTO_SIGNING_KEY', job)


if __name__ == '__main__':
    unittest.main()
