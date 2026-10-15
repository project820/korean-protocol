import io
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import urllib.parse

from distribution import actions_release as a
from distribution import history_store as h
from runtime import kproto as k
from tests import test_actions_release as fixtures


class MemoryGitHub:
    repository = 'project820/korean-protocol'

    def __init__(self):
        self.private = False
        self.records, self.assets, self.runs, self.jobs, self.artifacts, self.downloads, self.refs = [], {}, {}, {}, {}, {}, {}
        self.missing = False
        self.metadata_error = None
        self.fail_asset = None
        self.fail_patch = False
        self.latest_id = None
        self.mutations = []

    def request(self, path, binary=False, method='GET', data=None, upload=False):
        if method == 'POST' and path == '/releases':
            record = dict(data, id=len(self.records) + 1)
            self.records.append(record)
            self.assets[record['id']] = []
            self.mutations.append(('create', record['id']))
            return record
        if method == 'POST' and '/assets?name=' in path:
            release_id = int(path.split('/')[2])
            name = urllib.parse.unquote(path.split('name=')[1])
            if name == self.fail_asset:
                raise a.APIError(503)
            asset = {'id': 100 + len(self.downloads), 'name': name, 'size': len(data)}
            self.assets[release_id].append(asset)
            self.downloads[asset['id']] = data
            self.mutations.append(('upload', name))
            return asset
        if method == 'PATCH':
            if self.fail_patch:
                raise a.APIError(503)
            record = next(item for item in self.records if item['id'] == int(path.split('/')[2]))
            record.update(data)
            if data.get('make_latest') == 'true':
                self.latest_id = record['id']
            self.refs[record['tag_name']] = record['target_commitish']
            self.mutations.append(('complete', record['id']))
            return record
        if path == '/releases/latest':
            if self.latest_id is None:
                raise a.APIError(404)
            return next(item for item in self.records if item['id'] == self.latest_id)
        if path.startswith('/releases/') and path.split('/')[-1].isdigit() and not binary:
            return next(item for item in self.records if item['id'] == int(path.split('/')[-1]))
        if path == '':
            return {'private': self.private, 'full_name': self.repository}
        if path.startswith('/actions/runs/'):
            if self.metadata_error:
                raise a.APIError(self.metadata_error)
            if self.missing:
                raise a.APIError(404)
            return self.runs[int(path.split('/')[3])]
        if path.startswith('/actions/artifacts/'):
            return self.downloads[int(path.split('/')[3])]
        if path.startswith('/releases/assets/'):
            return self.downloads[int(path.split('/')[-1])]
        if path.startswith('/git/ref/tags/'):
            tag = path.removeprefix('/git/ref/tags/')
            if tag not in self.refs:
                raise a.APIError(404)
            return {'object': {'type': 'commit', 'sha': self.refs[tag]}}
        raise AssertionError(path)

    def pages(self, path, field=None):
        if path == '/releases':
            return iter(self.records)
        if path.startswith('/releases/'):
            return iter(self.assets[int(path.split('/')[2])])
        if path.startswith('/actions/runs/'):
            if self.metadata_error:
                raise a.APIError(self.metadata_error)
            if self.missing:
                raise a.APIError(404)
            run_id = int(path.split('/')[3])
            return iter(self.artifacts.get(run_id, []) if path.endswith('/artifacts') else self.jobs[run_id])
        raise AssertionError(path)


@unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH signing is required')
class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ActionsSigningTests('test_signing_verifies_pinned_key_and_removes_ephemeral_private_key')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.public, self.key = self.fixture.root, self.fixture.public, self.fixture.key
        self.fingerprint = self.fixture.fingerprint
        self.api = MemoryGitHub()
        self.static = self.fixture.static('0.2.0', 1)
        self.run_id = 4
        self.api.runs[4] = dict(id=4, event='workflow_dispatch', path=a.WORKFLOW, head_branch='main',
            head_repository={'full_name': self.api.repository}, head_sha='a' * 40, status='completed', conclusion='success')
        self.api.jobs[4] = [dict(name='sign', conclusion='success', run_attempt=1, completed_at='2026-10-13T01:01:00Z'),
            dict(name='publish', conclusion='success', run_attempt=1, started_at='2026-10-13T01:02:00Z', completed_at='2026-10-13T01:03:00Z')]
        self.api.artifacts[4] = [dict(id=17, name='kproto-static-4-1', expired=False, workflow_run={'id': 4})]
        self.api.downloads[17] = h.zip_content(self.static)

    def signed_receipt(self, name='receipt-work'):
        work = self.root / name
        work.mkdir()
        h.prepare_receipt(self.api, 4, self.public, self.fingerprint, work)
        h.sign_receipt(work, self.key.read_text(), self.public, self.fingerprint)
        return work

    def completed(self):
        work = self.signed_receipt()
        receipt_files = a.static_files(work / 'publication')
        body = dict(schema_version=1, repository=self.api.repository, run_id=4, signing_attempt=1, head_sha='a' * 40,
            artifact_id=17, content_sha256=k.digest(self.api.downloads[17]), version='0.2.0', sequence=1, rehearsal=False)
        h.store(self.api, body, {h.CONTENT_ASSET: self.api.downloads[17], **receipt_files})
        return self.api.records[0], work

    def legacy(self):
        record, work = self.completed()
        metadata = next((item for item in self.api.assets[record['id']]
                         if item['name'] == 'archive-provenance.json'), None)
        if metadata:
            record['body'] = self.api.downloads[metadata['id']].decode()
            self.api.assets[record['id']].remove(metadata)
        record['name'] = record['tag_name']
        self.api.latest_id = None
        return record, work

    def test_new_archives_use_readable_notes_and_separate_provenance(self):
        record, _ = self.completed()
        self.assertIn('배포 검증 기록', record['name'])
        self.assertIn('목적', record['body'])
        self.assertIn('사용', record['body'])
        self.assertIn('검증', record['body'])
        self.assertFalse(record['body'].startswith('{'))
        self.assertIn('archive-provenance.json', {item['name'] for item in self.api.assets[record['id']]})
        self.assertIsNone(self.api.latest_id)
        self.assertEqual('false', record['make_latest'])
        h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'new-layout')

    def test_legacy_migration_preserves_signed_assets_and_is_idempotent(self):
        record, _ = self.legacy()
        original = {item['name']: self.api.downloads[item['id']] for item in self.api.assets[record['id']]}
        h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'migration')
        for item in self.api.assets[record['id']]:
            if item['name'] in original:
                self.assertEqual(original[item['name']], self.api.downloads[item['id']])
        self.assertIn('배포 검증 기록', record['name'])
        before = list(self.api.mutations)
        h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'repeat')
        self.assertEqual(before, self.api.mutations)
        h.completed_for_run(self.api, 4, self.public, self.fingerprint, self.root / 'lookup')

    def test_interrupted_migration_is_readable_and_resumes(self):
        record, _ = self.legacy()
        self.api.fail_patch = True
        with self.assertRaises(a.APIError):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'interrupted')
        self.assertTrue(record['body'].startswith('{'))
        h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'midpoint')
        self.api.fail_patch = False
        h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'resume')
        self.assertFalse(record['body'].startswith('{'))
        self.assertEqual(1, sum(item['name'] == 'archive-provenance.json' for item in self.api.assets[record['id']]))

    def test_migration_authenticates_legacy_before_any_mutation(self):
        record, _ = self.legacy()
        asset = next(item for item in self.api.assets[record['id']] if item['name'] == h.RECEIPT_FILES[1])
        self.api.downloads[asset['id']] = b'x' * asset['size']
        before = list(self.api.mutations)
        with self.assertRaises(k.TrustError):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'tampered')
        self.assertEqual(before, self.api.mutations)

    def test_failed_metadata_upload_preserves_readable_legacy_archive(self):
        record, _ = self.legacy()
        before = list(self.api.mutations)
        self.api.fail_asset = 'archive-provenance.json'
        with self.assertRaises(a.APIError):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'upload-failure')
        self.assertEqual(before, self.api.mutations)
        h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'still-legacy')

    def test_migration_preserves_authored_notes_and_rejects_extra_or_partial_assets(self):
        record, _ = self.completed()
        record['body'] = '사용자가 작성한 릴리스 노트입니다.'
        before = list(self.api.mutations)
        with self.assertRaisesRegex(k.TrustError, 'authored'):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'authored')
        self.assertEqual(before, self.api.mutations)
        self.api.assets[record['id']].append(dict(id=999, name='extra.txt', size=1))
        with self.assertRaises(k.InputError):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'extra-migrate')
        self.api.assets[record['id']].pop()
        self.api.assets[record['id']].pop(0)
        with self.assertRaises(k.InputError):
            h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'partial-migrate')
        self.assertEqual(before, self.api.mutations)

    def test_migration_detects_authenticated_asset_change_before_patching(self):
        record, _ = self.legacy()
        original_request = self.api.request
        def request(path, **kwargs):
            result = original_request(path, **kwargs)
            if kwargs.get('upload'):
                record['body'] = record['body'].replace('"artifact_id": 17', '"artifact_id": 18')
            return result
        with patch.object(self.api, 'request', side_effect=request):
            with self.assertRaises(k.TrustError):
                h.migrate_presentation(self.api, record, self.public, self.fingerprint, self.root / 'concurrent')
        self.assertEqual(('upload', 'archive-provenance.json'), self.api.mutations[-1])
        self.assertEqual(record['tag_name'], record['name'])

    def test_new_metadata_tampering_missing_extra_and_oversize_fail_closed(self):
        record, _ = self.completed()
        asset = next(item for item in self.api.assets[record['id']] if item['name'] == 'archive-provenance.json')
        raw = self.api.downloads[asset['id']]
        changed = k.strict_json(raw)
        changed['run_id'] = 5
        self.api.downloads[asset['id']] = k.json_bytes(changed)
        asset['size'] = len(self.api.downloads[asset['id']])
        with self.assertRaisesRegex(k.TrustError, 'receipt'):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'metadata-tamper')
        self.api.downloads[asset['id']], asset['size'] = raw, len(raw)
        self.api.assets[record['id']].append(dict(id=999, name='extra.txt', size=1))
        with self.assertRaises(k.InputError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'extra')
        self.api.assets[record['id']].pop()
        asset['size'] = 65537
        with self.assertRaises(k.InputError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'oversize')
        self.api.assets[record['id']].remove(asset)
        with self.assertRaises(k.InputError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'missing')

    def test_transitional_metadata_must_match_legacy_body(self):
        record, _ = self.completed()
        asset = next(item for item in self.api.assets[record['id']] if item['name'] == 'archive-provenance.json')
        changed = k.strict_json(self.api.downloads[asset['id']])
        changed['artifact_id'] += 1
        record['body'] = k.json_bytes(changed).decode()
        with self.assertRaises(k.TrustError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'midpoint-conflict')

    def test_maintenance_cli_migrates_only_the_explicit_archive(self):
        record, _ = self.legacy()
        trust = self.root / 'distribution/trust'
        trust.mkdir(parents=True)
        (trust / 'publisher.pub').write_bytes(self.public.read_bytes())
        (trust / 'publisher.json').write_bytes(k.json_bytes({'fingerprint': self.fingerprint}))
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': self.api.repository, 'GH_TOKEN': 'fixture-token'}), \
                patch.object(a, 'GitHub', return_value=self.api):
            result = a.main(['present-history', '--root', str(self.root), '--work', str(self.root / 'cli'),
                             '--tag', record['tag_name']])
        self.assertEqual(0, result)
        self.assertIn('배포 검증 기록', record['name'])
        self.assertEqual('false', record['make_latest'])

    def test_post_publication_receipt_requires_successful_publish_and_binds_tree(self):
        work = self.signed_receipt()
        receipt = h.verify_receipt(work / 'publication', self.public, self.fingerprint, self.static)
        self.assertEqual('publication', receipt['kind'])
        self.assertEqual(a.tree_digest(a.static_files(self.static)), receipt['content_tree_sha256'])
        self.api.jobs[4][1]['conclusion'] = 'failure'
        blocked = self.root / 'failed-publication'
        blocked.mkdir()
        with self.assertRaisesRegex(k.TrustError, 'successful Pages'):
            h.prepare_receipt(self.api, 4, self.public, self.fingerprint, blocked)
        self.assertFalse((blocked / 'publication').exists())

    def test_durable_archive_survives_expired_artifacts_and_deleted_run_metadata(self):
        record, _ = self.completed()
        self.api.missing = True
        self.api.artifacts[4][0]['expired'] = True
        restored = self.root / 'restored'
        value = h.read_archive(self.api, record, self.public, self.fingerprint, restored)
        self.assertEqual(1, value['sequence'])
        self.assertEqual(a.static_files(self.static), a.static_files(restored))
        before = list(self.api.mutations)
        recovery = self.root / 'recovery'
        recovery.mkdir()
        h.archive_run(self.api, 4, self.public, self.fingerprint, recovery)
        self.assertEqual(before, self.api.mutations)

    def test_complete_receipt_to_archive_flow_uses_verified_job_artifact(self):
        work = self.signed_receipt()
        self.api.jobs[4].append(dict(name='receipt', conclusion='success', run_attempt=1,
                                   completed_at='2026-10-13T01:04:00Z'))
        self.api.artifacts[4].append(dict(id=18, name='kproto-publication-receipt-4-1', expired=False,
                                          workflow_run={'id': 4}))
        self.api.downloads[18] = h.zip_content(work / 'publication')
        archive_work = self.root / 'archive-job'
        archive_work.mkdir()
        tag = h.archive_run(self.api, 4, self.public, self.fingerprint, archive_work, receipt_run_id='4', receipt_attempt='2')
        self.assertEqual('kproto-history-0.2.0-1', tag)
        self.assertFalse(self.api.records[0]['draft'])
        restored = self.root / 'archive-job-restored'
        h.read_archive(self.api, self.api.records[0], self.public, self.fingerprint, restored)
        self.assertEqual(a.static_files(self.static), a.static_files(restored))

    def test_non404_metadata_failures_do_not_authorize_fallback(self):
        record, _ = self.completed()
        self.api.metadata_error = 503
        with self.assertRaises(a.APIError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'unavailable')

    def test_valid_receipt_does_not_hide_conflicting_live_publication_metadata(self):
        record, _ = self.completed()
        self.api.jobs[4][1]['conclusion'] = 'failure'
        with self.assertRaisesRegex(k.TrustError, 'successful Pages'):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'conflict')

    def test_receipt_rejects_wrong_namespace_and_wrong_repository(self):
        work = self.signed_receipt()
        receipt_path = work / 'publication' / h.RECEIPT_FILES[0]
        signature = receipt_path.with_name(h.RECEIPT_FILES[1])
        signature.unlink()
        a.sign_file(receipt_path, self.key.read_text(), self.public, 'kproto-release-v1')
        with self.assertRaisesRegex(k.TrustError, 'signature'):
            h.verify_receipt(work / 'publication', self.public, self.fingerprint, self.static)
        value = k.strict_json(receipt_path.read_bytes())
        value['kind'] = 'rehearsal'
        with self.assertRaises(k.InputError):
            h.validate_receipt(value)

    def test_old_history_deletion_cannot_pass_receipt_tree_binding(self):
        _, old = a.authenticated_history(self.static, self.public, self.fingerprint)
        second = self.fixture.static('0.3.0', 2, old)
        self.api.downloads[17] = h.zip_content(second)
        work = self.signed_receipt()
        altered = k.strict_json((work / 'publication' / h.RECEIPT_FILES[0]).read_bytes())
        altered['content_tree_sha256'] = '0' * 64
        signature = work / 'publication' / h.RECEIPT_FILES[1]
        signature.unlink()
        (work / 'publication' / h.RECEIPT_FILES[0]).write_bytes(k.json_bytes(altered))
        a.sign_file(work / 'publication' / h.RECEIPT_FILES[0], self.key.read_text(), self.public, h.RECEIPT_NAMESPACE)
        with self.assertRaisesRegex(k.TrustError, 'retained content tree'):
            h.verify_receipt(work / 'publication', self.public, self.fingerprint, second)

    def test_partial_upload_remains_draft_and_recovery_is_idempotent(self):
        work = self.signed_receipt()
        body = dict(schema_version=1, repository=self.api.repository, run_id=4, signing_attempt=1, head_sha='a' * 40,
            artifact_id=17, content_sha256=k.digest(self.api.downloads[17]), version='0.2.0', sequence=1, rehearsal=False)
        assets = {h.CONTENT_ASSET: self.api.downloads[17], **a.static_files(work / 'publication')}
        self.api.fail_asset = h.RECEIPT_FILES[1]
        with self.assertRaises(a.APIError):
            h.store(self.api, body, assets)
        self.assertTrue(self.api.records[0]['draft'])
        self.api.fail_asset = None
        h.store(self.api, body, assets)
        self.assertFalse(self.api.records[0]['draft'])
        before = list(self.api.mutations)
        h.store(self.api, body, assets)
        self.assertEqual(before, self.api.mutations)
        with self.assertRaises(k.TrustError):
            h.store(self.api, body, dict(assets, **{h.CONTENT_ASSET: b'changed'}))
        self.assertEqual(before, self.api.mutations)

    def test_incomplete_archive_forbids_reset_and_rehearsals_are_ignored(self):
        self.api.records = [{'tag_name': 'kproto-history-0.2.0-1', 'draft': True}]
        with self.assertRaisesRegex(k.TrustError, 'Incomplete'):
            h.latest(self.api, self.public, self.fingerprint, self.root / 'pending')
        self.api.records = [{'tag_name': 'kproto-rehearsal-0.2.0-1', 'draft': True}]
        self.assertIsNone(h.latest(self.api, self.public, self.fingerprint, self.root / 'ignored'))

    def test_latest_archive_selects_sequence_and_checks_live_pages_high_watermark(self):
        first = {'tag_name': 'kproto-history-0.2.0-1', 'draft': False, 'id': 1}
        second = {'tag_name': 'kproto-history-0.3.0-2', 'draft': False, 'id': 2}
        self.api.records = [first, second]
        with patch.object(h, 'read_archive', return_value={'sequence': 2}) as read, \
                patch.object(h, 'verify_live_stable') as live:
            h.latest(self.api, self.public, self.fingerprint, self.root / 'latest')
        self.assertEqual(second, read.call_args.args[1])
        live.assert_called_once()
        with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(b'newer-live-release')):
            with self.assertRaisesRegex(k.TrustError, 'live Pages'):
                h.verify_live_stable(self.api, self.static)
        self.api.private = True
        with self.assertRaisesRegex(k.TrustError, 'public Pages'):
            h.verify_live_stable(self.api, self.static)

    def test_rehearsal_is_private_draft_only_and_needs_no_tag(self):
        self.api.private = True
        self.api.jobs[4][1]['conclusion'] = 'skipped'
        work = self.root / 'rehearsal'
        work.mkdir()
        h.archive_run(self.api, 4, self.public, self.fingerprint, work, rehearsal=True)
        record = self.api.records[0]
        self.assertTrue(record['draft'])
        self.assertTrue(record['tag_name'].startswith('kproto-rehearsal-'))
        self.assertEqual({h.CONTENT_ASSET}, {item['name'] for item in self.api.assets[record['id']]})
        self.assertEqual({}, self.api.refs)
        h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'rehearsal-restored', rehearsal=True)
        with self.assertRaises(k.TrustError):
            h.read_archive(self.api, record, self.public, self.fingerprint, self.root / 'masquerading')

    def test_archive_recovery_inputs_are_validated_before_signing(self):
        a.validate_dispatch(False, True, '')
        a.validate_dispatch(True, False, '4')
        for archive_only, publish, original in ((False, True, '4'), (True, True, '4'), (True, False, ''), (True, False, '4;bad')):
            with self.subTest(archive_only=archive_only, publish=publish, original=original), self.assertRaises(k.InputError):
                a.validate_dispatch(archive_only, publish, original)

    def test_expired_optional_job_metadata_does_not_block_signed_durable_history(self):
        api = a.GitHub(self.api.repository, 'fixture-token')
        runs = [{'id': 4, 'event': 'workflow_dispatch', 'path': a.WORKFLOW}]
        for status in (404, 403, 503):
            def pages(path, field):
                if field == 'workflow_runs':
                    return iter(runs)
                raise a.APIError(status)
            with self.subTest(status=status), patch.object(api, 'pages', side_effect=pages):
                if status == 404:
                    self.assertIsNone(api.published_run())
                else:
                    with self.assertRaises(a.APIError):
                        api.published_run()

    def test_newer_live_publication_without_matching_archive_blocks_advancement(self):
        api = fixtures.FakeGitHub(published={'id': 5, 'signing_attempt': 1})
        durable = {'run_id': 4, 'signing_attempt': 1}
        with self.assertRaisesRegex(k.TrustError, 'conflicts'):
            a.preflight(api, False, False, False, '', durable=durable, durable_checked=True)
        with self.assertRaisesRegex(k.TrustError, 'no durable archive'):
            a.preflight(api, False, False, False, '17', durable_checked=True)
        api.published = None
        self.assertEqual(durable, a.preflight(api, False, False, False, '', durable=durable, durable_checked=True))


if __name__ == '__main__':
    unittest.main()
