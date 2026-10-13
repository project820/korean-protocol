from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from distribution import actions_release as actions
from distribution import release
from runtime import kproto as k
from validation.check import FILES


class FakeGitHub:
    repository = 'project820/korean-protocol'

    def __init__(self, private=True, published=None, artifact=None):
        self.private, self.published, self.artifact = private, published, artifact

    def request(self, path):
        if path == '':
            return {'full_name': self.repository, 'private': self.private}
        return self.artifact

    def published_run(self):
        return self.published


class PublicationGateTests(unittest.TestCase):
    def test_private_repository_rejects_requested_publication(self):
        with self.assertRaisesRegex(k.TrustError, 'private'):
            actions.preflight(FakeGitHub(), True, True, True, '', True)

    def test_publication_reruns_are_rejected_but_signing_rehearsals_can_retry(self):
        actions.publication_attempt(True, '1')
        actions.publication_attempt(False, '2')
        for attempt in ('2', '3', '', '01'):
            with self.subTest(attempt=attempt), self.assertRaisesRegex(k.TrustError, 'fresh workflow_dispatch'):
                actions.publication_attempt(True, attempt)

    def test_actual_deployment_guard_requires_public_visibility_and_fresh_dispatch(self):
        workflow = (Path(__file__).resolve().parents[1] / actions.WORKFLOW).read_text()
        guard = workflow.split('      - name: Verify live repository visibility and reject publication reruns\n', 1)[1]
        guard = guard.split('      - name: Publish sealed Pages artifact', 1)[0]
        self.assertIn('GH_TOKEN: ${{ github.token }}', guard)
        script = '\n'.join(line[10:] for line in guard.split('        run: |\n', 1)[1].splitlines())
        with tempfile.TemporaryDirectory(prefix='kproto-publish-guard-test-') as temporary:
            stub = Path(temporary) / 'gh'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$GUARD_RESPONSE"\nexit "$GUARD_API_EXIT"\n')
            stub.chmod(0o755)
            for attempt, visibility, api_exit, expected in (('1', 'false', '0', 0), ('1', 'true', '0', 1),
                    ('1', '', '1', 1), ('2', 'false', '0', 1)):
                environment = dict(os.environ, PATH=temporary + os.pathsep + os.environ['PATH'],
                                   GITHUB_REPOSITORY=FakeGitHub.repository, GITHUB_RUN_ATTEMPT=attempt,
                                   GUARD_RESPONSE=visibility, GUARD_API_EXIT=api_exit, GH_TOKEN='fixture-token')
                result = subprocess.run(['bash', '-e', '-c', script], env=environment, capture_output=True)
                with self.subTest(attempt=attempt, visibility=visibility, api_exit=api_exit):
                    self.assertEqual(expected, result.returncode)
                    self.assertNotIn(b'fixture-token', result.stdout + result.stderr)

    def test_disabled_pages_and_first_publication_guard_reject_publish(self):
        for enabled, allow, message in ((False, True, 'PAGES_ENABLED'), (True, False, 'ALLOW_FIRST')):
            with self.subTest(enabled=enabled), self.assertRaisesRegex(k.TrustError, message):
                actions.preflight(FakeGitHub(private=False), True, enabled, True, '', allow)

    def test_explicit_first_dry_run_is_allowed_in_private_repository(self):
        self.assertIsNone(actions.preflight(FakeGitHub(), False, False, True, ''))

    def test_ambiguous_history_and_malformed_artifact_inputs_are_rejected(self):
        for first, artifact in ((False, ''), (True, '17'), (False, '17; echo bad'), (False, '-1')):
            with self.subTest(first=first, artifact=artifact), self.assertRaises(k.InputError):
                actions.preflight(FakeGitHub(), False, False, first, artifact)

    def test_existing_publication_forbids_first_release_reset(self):
        with self.assertRaisesRegex(k.TrustError, 'reset'):
            actions.preflight(FakeGitHub(published={'id': 4}), False, False, True, '')

    def test_previous_artifact_must_be_unexpired_latest_publication(self):
        run = {'id': 4, 'run_attempt': 2, 'signing_attempt': 2}
        artifact = {'name': 'kproto-static-4-2', 'expired': False, 'workflow_run': {'id': 4}}
        self.assertEqual(artifact, actions.preflight(FakeGitHub(published=run, artifact=artifact), False, False, False, '17'))
        for change in ({'expired': True}, {'name': 'kproto-static-3-1'}, {'workflow_run': {'id': 3}}):
            with self.subTest(change=change), self.assertRaises(k.TrustError):
                actions.preflight(FakeGitHub(published=run, artifact=dict(artifact, **change)), False, False, False, '17')
        with self.assertRaises(k.TrustError):
            actions.preflight(FakeGitHub(), False, False, False, '17')

    def test_published_history_ignores_successful_signing_dry_runs(self):
        api = actions.GitHub(FakeGitHub.repository, 'fixture-token')
        runs = [{'id': i, 'event': 'workflow_dispatch', 'path': actions.WORKFLOW} for i in (8, 7, 6)]
        def pages(path, field):
            if field == 'workflow_runs':
                return iter(runs)
            return iter([{'name': 'publish', 'conclusion': 'success' if '/7/' in path else 'skipped',
                          'run_attempt': 1, 'started_at': '2026-10-13T01:02:00Z', 'completed_at': '2026-10-13T01:03:00Z'},
                         {'name': 'sign', 'conclusion': 'success', 'run_attempt': 1, 'completed_at': '2026-10-13T01:01:00Z'}])
        with patch.object(api, 'pages', side_effect=pages):
            self.assertEqual(7, api.published_run()['id'])

    def test_partial_publish_rerun_uses_successful_signing_attempt_artifact(self):
        api = actions.GitHub(FakeGitHub.repository, 'fixture-token')
        run = {'id': 4, 'run_attempt': 2, 'event': 'workflow_dispatch', 'path': actions.WORKFLOW}
        jobs = [{'name': 'sign', 'conclusion': 'success', 'run_attempt': 1, 'completed_at': '2026-10-13T01:01:00Z'},
                {'name': 'publish', 'conclusion': 'failure', 'run_attempt': 1,
                 'started_at': '2026-10-13T01:02:00Z', 'completed_at': '2026-10-13T01:03:00Z'},
                {'name': 'publish', 'conclusion': 'success', 'run_attempt': 2,
                 'started_at': '2026-10-13T01:04:00Z', 'completed_at': '2026-10-13T01:05:00Z'}]
        with patch.object(api, 'pages', side_effect=lambda path, field: iter([run] if field == 'workflow_runs' else jobs)):
            published = api.published_run()
        artifact = {'name': 'kproto-static-4-1', 'expired': False, 'workflow_run': {'id': 4}}
        self.assertEqual(1, published['signing_attempt'])
        self.assertEqual(artifact, actions.preflight(FakeGitHub(published=published, artifact=artifact), False, False, False, '17'))

    def test_history_selects_latest_publication_time_and_preserves_failed_rerun_evidence(self):
        api = actions.GitHub(FakeGitHub.repository, 'fixture-token')
        runs = [{'id': i, 'event': 'workflow_dispatch', 'path': actions.WORKFLOW, 'conclusion': 'failure'} for i in (8, 7)]
        def pages(path, field):
            if field == 'workflow_runs':
                self.assertIn('status=completed', path)
                return iter(runs)
            timestamp = '2026-10-13T02:' if '/7/' in path else '2026-10-13T01:'
            return iter([{'name': 'sign', 'conclusion': 'success', 'run_attempt': 1, 'completed_at': timestamp + '01:00Z'},
                         {'name': 'publish', 'conclusion': 'success', 'run_attempt': 1,
                          'started_at': timestamp + '02:00Z', 'completed_at': timestamp + '03:00Z'},
                         {'name': 'sign', 'conclusion': 'failure', 'run_attempt': 2}])
        with patch.object(api, 'pages', side_effect=pages):
            self.assertEqual(7, api.published_run()['id'])

    def test_network_failure_never_falls_back_to_first_release(self):
        api = FakeGitHub()
        with patch.object(api, 'published_run', side_effect=OSError('network')):
            with self.assertRaises(OSError):
                actions.preflight(api, False, False, True, '')

    def test_artifact_redirect_does_not_forward_github_authorization(self):
        import urllib.error
        api = actions.GitHub(FakeGitHub.repository, 'fixture-token')
        requests = []
        def opener(handler):
            def first(request, timeout):
                requests.append(request)
                handler.destination = 'https://storage.fixture/archive.zip?fixture'
                raise urllib.error.HTTPError(request.full_url, 302, 'fixture', None, io.BytesIO())
            return SimpleNamespace(open=first)
        def storage(request, timeout):
            requests.append(request)
            return io.BytesIO(b'fixture-archive')
        with patch('urllib.request.build_opener', side_effect=opener), patch('urllib.request.urlopen', side_effect=storage):
            self.assertEqual(b'fixture-archive', api.request('/actions/artifacts/17/zip', binary=True))
            self.assertEqual(b'fixture-archive', api.request('/releases/assets/17', binary=True))
        self.assertTrue(requests[0].has_header('Authorization'))
        self.assertFalse(requests[1].has_header('Authorization'))
        self.assertEqual('application/vnd.github+json', requests[0].get_header('Accept'))
        self.assertEqual('application/octet-stream', requests[2].get_header('Accept'))
        self.assertFalse(requests[3].has_header('Authorization'))

    def test_pages_first_publication_requires_exact_404(self):
        import urllib.error
        for code in (401, 403, 500):
            with self.subTest(code=code), patch('urllib.request.OpenerDirector.open',
                    side_effect=urllib.error.HTTPError('https://fixture', code, 'fixture', None, None)):
                with self.assertRaises(k.NetworkError):
                    actions.confirm_empty_pages(FakeGitHub.repository)
        with patch('urllib.request.OpenerDirector.open',
                side_effect=urllib.error.HTTPError('https://fixture', 404, 'fixture', None, None)):
            actions.confirm_empty_pages(FakeGitHub.repository)


@unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH signing is required')
class ActionsSigningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kproto-actions-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.key = self.root / 'signer'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key)], check=True, capture_output=True)
        self.public = self.key.with_suffix('.pub')
        self.fingerprint = k.key_fingerprint(self.public)
        self.content = k.content_files(Path(__file__).resolve().parents[1])

    def static(self, version, sequence, history=None):
        output = self.root / ('static-' + version)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        manifest = k.make_manifest(Path(__file__).resolve().parents[1], version, sequence, self.fingerprint)
        manifest['issued_at'] = (now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        manifest['expires_at'] = (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        content = dict(self.content)
        for name, data in self.content.items():
            if name.endswith('.json'):
                value = k.strict_json(data)
                value['version'] = version + '-draft'
                content[name] = k.json_bytes(value)
        for item in manifest['files']:
            item['size'] = len(content[item['path']])
            item['sha256'] = k.digest(content[item['path']])
        payload = {'releases/' + version + '/' + name: data for name, data in content.items()}
        payload['stable/release.json'] = k.json_bytes(manifest)
        payload.update(history or {})
        release._write_tree(output, payload)
        actions.sign(output, self.key.read_text(), self.public)
        return output

    def test_signing_verifies_pinned_key_and_removes_ephemeral_private_key(self):
        with patch.dict(os.environ, {'RUNNER_TEMP': str(self.root)}):
            output = self.static('0.2.0', 1)
        release._load_static(output, self.public, self.fingerprint)
        self.assertEqual([], list(self.root.glob('kproto-key-*')))
        self.assertEqual(9, len([path for path in output.rglob('*') if path.is_file()]))
        with self.assertRaises(k.InputError):
            actions.sign(output, '', self.public)

    def test_actions_private_first_release_runs_prepare_sign_and_seal(self):
        source = self.root / 'source'
        source.mkdir()
        repo = Path(__file__).resolve().parents[1]
        names = set(k.CONTENT_PATHS) | set(FILES) | {
            'evaluation/functional-review.json', 'evaluation/functional-cases.json', 'docs/spec/korean-rules.md',
            'LICENSE', 'NOTICE.md'}
        for name in names:
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((repo / name).read_bytes())
        # Keep this fictional first release independent of current draft metadata.
        for name in ('specification/rules.json', 'lexicon/core.json',
                     'lexicon/domains/software.json'):
            path = source / name
            current = k.strict_json(path.read_bytes())['version']
            path.write_bytes(path.read_bytes().replace(
                ('"version": "' + current + '"').encode(),
                b'"version": "0.2.0-draft"', 1))
        proof_path = source / 'evaluation/functional-review.json'
        proof = k.strict_json(proof_path.read_bytes())
        proof['reviewed_rules_sha256'] = k.digest((source/'specification/rules.json').read_bytes())
        proof_path.write_bytes(k.json_bytes(proof))
        trust = source / 'distribution/trust'
        trust.mkdir(parents=True)
        (trust / 'publisher.pub').write_bytes(self.public.read_bytes())
        (trust / 'publisher.json').write_bytes(k.json_bytes({'fingerprint': self.fingerprint}))
        work = self.root / 'work'
        work.mkdir()
        environment = {'GITHUB_REF': 'refs/heads/main', 'GITHUB_REPOSITORY': FakeGitHub.repository,
                       'INPUT_VERSION': '0.2.0', 'INPUT_FIRST_RELEASE': 'true', 'INPUT_PUBLISH': 'false',
                       'INPUT_PREVIOUS_ARTIFACT_ID': '', 'KPROTO_SIGNING_KEY': self.key.read_text(),
                       'RUNNER_TEMP': str(work)}
        with patch.dict(os.environ, environment), patch.object(actions, 'GitHub', return_value=FakeGitHub()), \
                patch('distribution.history_store.latest', return_value=None):
            for command in ('prepare', 'sign', 'seal'):
                actions.execute(command, source, work)
        self.assertEqual(9, len([path for path in (work / 'ready').rglob('*') if path.is_file()]))
        release._load_static(work / 'ready', self.public, self.fingerprint)
        self.assertEqual([], list(work.glob('kproto-key-*')))

    def test_wrong_secret_is_rejected_and_cleaned_without_key_output(self):
        other = self.root / 'other'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(other)], check=True, capture_output=True)
        with patch.dict(os.environ, {'RUNNER_TEMP': str(self.root)}), self.assertRaises(k.TrustError):
            actions.sign(self.root, other.read_text(), self.public)
        self.assertEqual([], list(self.root.glob('kproto-key-*')))

    def test_authenticated_history_preserves_all_old_versions(self):
        first = self.static('0.2.0', 1)
        _, payload = actions.authenticated_history(first, self.public, self.fingerprint)
        second = self.static('0.3.0', 2, payload)
        latest, history = actions.authenticated_history(second, self.public, self.fingerprint)
        self.assertEqual(2, latest['sequence'])
        self.assertEqual(18, len(history))
        self.assertEqual((first / 'releases/0.2.0/pack/protocol.md').read_bytes(), history['releases/0.2.0/pack/protocol.md'])
        (second / 'releases/0.2.0/pack/protocol.md').write_bytes(b'tampered')
        with self.assertRaises(k.TrustError):
            actions.authenticated_history(second, self.public, self.fingerprint)

    def test_history_rejects_extra_files_and_sequence_gaps(self):
        first = self.static('0.2.0', 1)
        _, payload = actions.authenticated_history(first, self.public, self.fingerprint)
        third = self.static('0.3.0', 3, payload)
        with self.assertRaisesRegex(k.TrustError, 'monotonic'):
            actions.authenticated_history(third, self.public, self.fingerprint)
        (first / 'source-leak.txt').write_text('private source')
        with self.assertRaisesRegex(k.InputError, 'unlisted'):
            actions.authenticated_history(first, self.public, self.fingerprint)

    def test_archive_rejects_traversal_symlinks_and_duplicate_files(self):
        for kind in ('traversal', 'symlink', 'duplicate'):
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as archive:
                item = zipfile.ZipInfo('../outside' if kind == 'traversal' else 'file')
                if kind == 'symlink':
                    item.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(item, b'fixture')
                if kind == 'duplicate':
                    archive.writestr('file', b'fixture')
            with self.subTest(kind=kind), self.assertRaises(k.InputError):
                actions.extract_artifact(data.getvalue(), self.root / ('output-' + kind))


if __name__ == '__main__':
    unittest.main()
