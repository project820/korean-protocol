"""Offline private practical-report study checks; all text here is synthetic."""
import http.client
import importlib.util
import json
import io
import os
import socketserver
import threading
import time
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'evaluation/field-report-20261015/run.py'


def load_runner():
    spec = importlib.util.spec_from_file_location('field_report', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def terminal(model='test-model', text='  Synthetic result\r\n  ', **changes):
    response = dict(id='offline', status='completed', model=model,
                    usage={'input_tokens': 20000, 'output_tokens': 10},
                    output=[{'type': 'message', 'role': 'assistant', 'status': 'completed',
                             'content': [{'type': 'output_text', 'text': text}]}])
    response.update(changes)
    return ('data: ' + json.dumps({'type': 'response.completed', 'response': response})
            + '\n\ndata: [DONE]\n\n').encode()


@contextmanager
def local_http(respond):
    """Serve only synthetic local traffic, and join every fixture thread."""
    requests = []
    stop = threading.Event()

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            stream = self.request.makefile('rb')
            try:
                first = stream.readline()
                headers = {}
                while (line := stream.readline()) not in (b'\r\n', b''):
                    key, value = line.decode().split(':', 1)
                    headers[key.lower()] = value.strip()
                data = stream.read(int(headers.get('content-length', 0)))
                requests.append((first, headers, data))
                respond(self.request, stop)
            except (OSError, ValueError):
                pass
            finally:
                stream.close()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = False

    server = Server(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}/v1/responses', requests
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join()


def reply(raw, status=200, headers=b''):
    def respond(sock, stop):
        sock.sendall(f'HTTP/1.1 {status} Synthetic\r\nContent-Length: {len(raw)}\r\n'.encode()
                     + headers + b'Connection: close\r\n\r\n' + raw)
    return respond


class FieldReportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNNER.exists(), 'Private field-report runner is missing')
        self.runner = load_runner()
        # A failed fixture patch must never send synthetic requests to the real service.
        self.runner.frozen.old.ENDPOINT = 'http://127.0.0.1:0/v1/responses'
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.study = self.directory / 'study'
        self.study.mkdir()
        self.candidate = self.directory / 'SKILL.md'
        self.candidate.write_bytes(b'---\nname: synthetic\n---\nEntire synthetic skill.\n')
        (self.study / 'source.md').write_bytes(b'PRIVATE-SYNTHETIC-SOURCE\r\n' * 5000)
        for name in ('criteria.json', 'claim-ledger.json'):
            self.runner.dump(self.study / name, {'synthetic': True})
        probe_dir = self.study / 'token-probe'
        probe_dir.mkdir()
        request = self.runner.probe_request(self.candidate.read_bytes(), 'test-model', 'high')
        raw = terminal(text='confirmed', usage={'input_tokens': 100, 'output_tokens': 1})
        (probe_dir / 'request.json').write_bytes(request)
        (probe_dir / 'response.raw').write_bytes(raw)
        profile_hash = self.runner.sha(self.candidate.read_bytes())
        self.budget = dict(profile_sha256=profile_hash, ceiling=6000,
                           counters={'synthetic': 99}, source_tokens={'synthetic': 25000},
                           model_probe=dict(profile_sha256=profile_hash,
                                            model_requested='test-model', effort='high',
                                            request_file='token-probe/request.json',
                                            response_file='token-probe/response.raw',
                                            request_sha256=self.runner.sha(request),
                                            response_sha256=self.runner.sha(raw)))
        self.runner.dump(self.study / 'token-budget.json', self.budget)

    def prepare(self):
        return self.runner.prepare(self.study, self.candidate, 'test-model', 'high')

    def test_prepare_freezes_four_private_stateless_requests_and_neutral_pairs(self):
        with patch.object(self.runner, 'transfer', side_effect=AssertionError('network')):
            plan = self.prepare()
            self.runner.verify(self.study, require_complete=False)
        self.assertEqual(4, plan['planned_calls'])
        self.assertEqual('unknown; historical user-supplied output', plan['source_model'])
        self.assertEqual('unverified', plan['token_budget']['probe_effort_identity']['effort_verification'])
        for repeat in (1, 2):
            bodies = []
            for arm in self.runner.ARMS:
                raw = (self.study / 'requests' / f'{repeat:02}-{arm}.json').read_bytes()
                body = json.loads(raw)
                self.assertEqual([], body['tools'])
                self.assertEqual(1, len(body['input']))
                self.assertNotIn('previous_response_id', body)
                self.assertNotIn('criteria', body['input'][0]['content'][0]['text'])
                self.assertIn('PRIVATE-SYNTHETIC-SOURCE', body['input'][0]['content'][0]['text'])
                bodies.append(body)
            for body, arm in zip(bodies, self.runner.ARMS):
                prompt = body['input'][0]['content'][0]['text']
                profile = (self.study / 'inputs' / f'{arm}.md').read_bytes().decode()
                body['input'][0]['content'][0]['text'] = prompt.replace(profile, 'SAME-PROFILE', 1)
            self.assertEqual(*bodies)
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.prepare()

    def test_input_plan_request_and_probe_drift_fail_offline(self):
        self.prepare()
        paths = [self.study / name for name in ('source.md', 'criteria.json', 'claim-ledger.json',
                                               'token-budget.json', 'plan.json',
                                               'requests/01-baseline.json',
                                               'inputs/candidate.md', 'token-probe/response.raw')]
        for path in paths:
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.runner.verify(self.study, require_complete=False)
            path.write_bytes(raw)

    def test_budget_checks_probe_and_all_counters_but_excludes_long_source(self):
        for mutation in ('counter', 'profile', 'model', 'missing-probe'):
            original = (self.study / 'token-budget.json').read_bytes()
            budget = json.loads(original)
            if mutation == 'counter':
                budget['counters']['second-counter'] = 6001
            elif mutation == 'profile':
                budget['model_probe']['profile_sha256'] = 'wrong'
            elif mutation == 'model':
                budget['model_probe']['model_requested'] = 'fallback'
            else:
                budget['model_probe']['response_file'] = 'missing.raw'
            (self.study / 'token-budget.json').write_text(json.dumps(budget))
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, FileNotFoundError)):
                self.prepare()
            (self.study / 'token-budget.json').write_bytes(original)
        self.prepare()

    def test_probe_rejects_contradictory_returned_effort(self):
        raw = terminal(reasoning={'effort': 'low'}, usage={'input_tokens': 100, 'output_tokens': 1})
        (self.study / 'token-probe/response.raw').write_bytes(raw)
        self.budget['model_probe']['response_sha256'] = self.runner.sha(raw)
        (self.study / 'token-budget.json').write_text(json.dumps(self.budget))
        with self.assertRaisesRegex(ValueError, 'effort differs'):
            self.prepare()

    def test_public_study_directory_is_rejected_before_writing(self):
        for path in (ROOT / 'evaluation/private-report', ROOT / 'output', ROOT / 'tests/private'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'private study'):
                self.runner.validate_study_dir(path)

    def test_parser_reuses_frozen_strict_checks_and_dynamic_model(self):
        raw = terminal()
        parsed, text = self.runner.extract_strict(raw, 'test-model')
        self.assertEqual('test-model', parsed['model'])
        self.assertEqual('  Synthetic result\r\n  ', text)
        for invalid in (terminal(model='fallback'), terminal(status='incomplete'),
                        terminal(metadata={'fallback_used': True}),
                        raw + raw, b'data: {"type":"response.created"}\n',
                        terminal(output=[{'type': 'function_call'}])):
            with self.subTest(raw=invalid[:70]), self.assertRaises(ValueError):
                self.runner.extract_strict(invalid, 'test-model')

    def make_run_directories(self):
        for folder in ('run', 'outputs', 'records'):
            (self.study / folder).mkdir()

    def test_local_http_retains_exact_terminal_output_and_never_overwrites(self):
        self.prepare()
        with local_http(reply(terminal())) as (url, requests):
            with patch.object(self.runner.frozen.old, 'ENDPOINT', url):
                self.runner.run(self.study)
        self.assertEqual(4, len(requests))
        self.runner.verify(self.study)
        for path in (self.study / 'outputs').glob('*.txt'):
            self.assertEqual(b'  Synthetic result\r\n  ', path.read_bytes())
        record = self.runner.read_json(self.study / 'records/01-baseline.json')
        self.assertEqual('high', record['requested_effort'])
        self.assertIsNone(record['returned_effort'])
        self.assertEqual('unverified', record['effort_verification'])
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.runner.run(self.study)

    def test_partial_and_model_mismatch_retain_raw_failed_evidence_without_retry(self):
        self.prepare()
        self.make_run_directories()
        for slot, raw, partial in [('01-baseline', terminal(), True),
                                   ('01-candidate', terminal(model='fallback'), False)]:
            def respond(sock, stop):
                data = raw[:30] if partial else raw
                sock.sendall(f'HTTP/1.1 200 OK\r\nContent-Length: {len(raw)}\r\n'
                             'Connection: close\r\n\r\n'.encode() + data)
            with local_http(respond) as (url, requests):
                with patch.object(self.runner.frozen.old, 'ENDPOINT', url):
                    record = self.runner.execute(self.study, slot)
            self.assertEqual(1, len(requests))
            self.assertEqual('failed', record['status'])
            self.assertEqual(raw[:30] if partial else raw,
                             (self.study / 'run' / slot / 'response.raw').read_bytes())
        self.assertEqual(b'  Synthetic result\r\n  ',
                         (self.study / 'run/01-candidate/output.txt').read_bytes())
        with self.assertRaisesRegex(ValueError, 'Missing|failed|records'):
            self.runner.verify(self.study)

    def test_incomplete_terminal_text_is_retained_as_failed_output(self):
        self.prepare()
        for folder in ('run', 'outputs', 'records'):
            (self.study / folder).mkdir()
        raw = terminal(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
        raw = raw.replace(b'"type": "response.completed"', b'"type": "response.incomplete"')
        with local_http(reply(raw)) as (url, _):
            with patch.object(self.runner.frozen.old, 'ENDPOINT', url):
                record = self.runner.execute(self.study, '01-candidate')
        self.assertEqual('failed', record['status'])
        self.assertEqual(b'  Synthetic result\r\n  ',
                         (self.study / 'run/01-candidate/output.txt').read_bytes())
        self.assertFalse((self.study / 'outputs/01-candidate.txt').exists())

    def test_historical_verify_uses_frozen_candidate_but_dispatch_checks_live_skill(self):
        self.prepare()
        self.candidate.write_bytes(b'Updated current skill')
        self.runner.verify(self.study, require_complete=False)
        with self.assertRaisesRegex(ValueError, 'Candidate skill drift'):
            self.runner.verify(self.study, require_complete=False, for_dispatch=True)

    def test_archived_runner_verification_hashes_bytes_without_execution(self):
        self.prepare()
        archive = self.directory / 'runner-at-generation.py'
        archive.write_bytes(RUNNER.read_bytes())
        artifacts = self.runner.runner_artifacts()
        runner_key = str(RUNNER.relative_to(ROOT))
        changed = {**artifacts, runner_key: 'changed-code'}
        with patch.object(self.runner, 'runner_artifacts', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'Runner/parser drift'):
                self.runner.verify(self.study, require_complete=False)
            self.runner.verify(self.study, require_complete=False, archived_runner=archive)
            with self.assertRaisesRegex(ValueError, 'verify-only'):
                self.runner.verify(self.study, require_complete=False, archived_runner=archive,
                                   for_dispatch=True)
            with self.assertRaisesRegex(ValueError, 'Runner/parser drift'):
                self.runner.run(self.study)
            changed[str(self.runner.R1.relative_to(ROOT))] = 'changed-parser'
            with self.assertRaisesRegex(ValueError, 'Runner/parser drift'):
                self.runner.verify(self.study, require_complete=False, archived_runner=archive)
            changed.update(artifacts)
            archive.write_bytes(archive.read_bytes() + b'changed archive')
            with self.assertRaisesRegex(ValueError, 'Runner/parser drift'):
                self.runner.verify(self.study, require_complete=False, archived_runner=archive)

    def test_event_metadata_and_tool_calls_cannot_hide_behind_terminal_output(self):
        events = [
            {'type': 'response.created', 'response': {'model': 'wrong'}},
            {'type': 'response.in_progress', 'response': {'reasoning': {'effort': 'low'}}},
        ]
        for tool in ('web_search_call', 'file_search_call', 'code_interpreter_call', 'mcp_call'):
            events.extend([{'type': 'response.' + tool + '.in_progress'},
                           {'type': 'response.output_item.done', 'item': {'type': tool}}])
        for event in events:
            raw = ('data: ' + json.dumps(event) + '\n\n').encode() + terminal()
            with self.subTest(event=event), self.assertRaises(ValueError):
                self.runner.extract_strict(raw, 'test-model', 'high')
        with self.assertRaises(ValueError):
            self.runner.extract_strict(terminal(reasoning={'effort': 'low'}), 'test-model', 'high')
        response, _ = self.runner.extract_strict(terminal(), 'test-model', 'high')
        self.assertEqual({'requested_effort': 'high', 'returned_effort': None,
                          'effort_verification': 'unverified'}, self.runner.effort_identity(response, 'high'))
        response, _ = self.runner.extract_strict(terminal(reasoning={'effort': 'high'}), 'test-model', 'high')
        self.assertEqual('verified', self.runner.effort_identity(response, 'high')['effort_verification'])

    def test_tmpdir_cannot_expand_external_temporary_scope(self):
        with patch.dict(os.environ, {'TMPDIR': str(Path.home())}):
            with self.assertRaises(ValueError):
                self.runner.validate_study_dir(Path.home() / 'Sync/public-study')

    def test_transport_does_not_follow_redirects_and_retains_status_body(self):
        raw = b'private redirect body'
        with local_http(reply(raw, 302, b'Location: http://example.invalid/private\r\n')) as (url, requests):
            file, record = io.BytesIO(), {}
            with self.assertRaisesRegex(ValueError, 'HTTP status'):
                self.runner.transfer(url, b'private request', file, record, 1)
        self.assertEqual(raw, file.getvalue())
        self.assertEqual(302, record['http_status'])
        self.assertEqual(1, len(requests))

    def test_transport_rejects_nonloopback_before_connecting(self):
        with self.assertRaisesRegex(ValueError, 'loopback'):
            self.runner.transfer('http://example.com/v1/responses', b'private', io.BytesIO(), {}, 1)

    def test_transport_ignores_proxy_environment(self):
        with local_http(reply(b'proxy must not see this')) as (proxy, proxy_requests):
            with local_http(reply(terminal())) as (url, requests):
                with patch.dict(os.environ, {'HTTP_PROXY': proxy, 'http_proxy': proxy,
                                            'ALL_PROXY': proxy, 'all_proxy': proxy,
                                            'NO_PROXY': '', 'no_proxy': ''}):
                    output, record = io.BytesIO(), {}
                    self.runner.transfer(url, b'private synthetic', output, record, 1)
        self.assertEqual([], proxy_requests)
        self.assertEqual(b'private synthetic', requests[0][2])
        self.assertEqual(terminal(), output.getvalue())

    def test_transport_retains_non200_and_truncated_bodies(self):
        for status in (202, 500):
            for truncated in (False, True):
                raw = b'partial private error'
                def respond(sock, stop):
                    size = len(raw) + (20 if truncated else 0)
                    sock.sendall(f'HTTP/1.1 {status} Synthetic\r\nContent-Length: {size}\r\n'
                                 'Connection: close\r\n\r\n'.encode() + raw)
                with local_http(respond) as (url, _):
                    output, record = io.BytesIO(), {}
                    with self.subTest(status=status, truncated=truncated), self.assertRaises(Exception):
                        self.runner.transfer(url, b'private', output, record, 1)
                self.assertEqual(raw, output.getvalue())
                self.assertEqual(status, record['http_status'])

    def test_transport_deadline_covers_headers_body_and_chunk_trailers(self):
        threads_before = {thread.ident for thread in threading.enumerate()}
        for phase in ('headers', 'body', 'trailers'):
            def respond(sock, stop):
                if phase == 'headers':
                    sock.sendall(b'HTTP/1.1 200 OK\r\n')
                    chunk = b'X-Drip: x\r\n'
                elif phase == 'body':
                    sock.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 99999\r\n\r\n')
                    chunk = b'x'
                else:
                    sock.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
                                 b'4\r\nkept\r\n0\r\n')
                    chunk = b'X-Drip: x\r\n'
                while not stop.wait(.025):
                    sock.sendall(chunk)
            with local_http(respond) as (url, _):
                output, record = io.BytesIO(), {}
                started = time.monotonic()
                with self.subTest(phase=phase), self.assertRaises(TimeoutError):
                    self.runner.transfer(url, b'private', output, record, .15)
                self.assertLess(time.monotonic() - started, .8)
                if phase == 'trailers':
                    self.assertEqual(b'kept', output.getvalue())
                if phase == 'body':
                    self.assertTrue(output.getvalue())
            self.assertEqual(threads_before, {thread.ident for thread in threading.enumerate()})


if __name__ == '__main__':
    unittest.main()
