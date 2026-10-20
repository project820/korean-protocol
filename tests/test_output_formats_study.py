"""Evidence and isolation tests for the new, independent output-format study."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'evaluation/output_formats/study.py'


def stream(model='gpt-6.1-sol', effort='medium', text='원시 결과', status='completed'):
    response = {'model': model, 'status': status, 'output': [
        {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': text}]}]}
    if effort is not None:
        response['reasoning'] = {'effort': effort}
    return ('data: ' + json.dumps({'type': 'response.' + status, 'response': response}) + '\n\n').encode()


def cases(prefix):
    return [{'id': f'{prefix}{i:02d}', 'source': f'{prefix} 원문 {i}', 'task': '자료를 설명한다.',
             'modality': f'L{(i - 1) // 3 + 1}', 'mode': 'rewrite' if i % 2 else 'compose'}
            for i in range(1, 13)]


def verdict():
    return {'outputs': {k: {'meaning': 'pass', 'findings': [], 'format': {
                'status': 'pass', 'evidence': [{'output_quote': '결과', 'reason': '표현 계약과 대응한다.'}],
                'scene_correspondence': []}} for k in 'ABC'},
            'pairs': [{'left': a, 'right': b, 'winner': 'tie', 'reason': '각 출력에서 같은 조건을 찾는다.',
                       'evidence': [{'label': a, 'quote': '결과'}, {'label': b, 'quote': '결과'}]}
                      for a, b in [('A', 'B'), ('A', 'C'), ('B', 'C')]]}


class OutputFormatStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('output_formats_study', MODULE)
            cls.s = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.s)
        else:
            cls.s = None

    def setUp(self):
        self.assertIsNotNone(self.s, 'the independent output-format runner has not been implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, method='single-shot', checker_source=None, browser_source=None):
        candidate = self.root / 'candidate'
        (candidate / 'references').mkdir(parents=True)
        (candidate / 'SKILL.md').write_text('---\nname: korean-protocol\n---\n후보 작성 규칙', encoding='utf-8')
        (candidate / 'references/all.md').write_text('빠뜨리지 않을 전체 참조', encoding='utf-8')
        baseline = self.root / 'baseline'
        baseline.mkdir()
        (baseline / 'SKILL.md').write_text('기존 작성 규칙', encoding='utf-8')
        ste = self.root / 'ste.md'
        ste.write_text('STE 한국어 실험 적용 규칙', encoding='utf-8')
        provenance = self.root / 'ste-source.json'
        provenance.write_text(json.dumps({'source': 'https://www.asd-ste100.org/', 'edition': '9',
                                          'rules': ['one subject'], 'korean_application': '실험 적용'}))
        run = self.root / 'run'
        self.s.freeze_candidate(run, candidate)
        dataset = self.root / 'cases.json'
        dataset.write_text(json.dumps({'development': cases('D'), 'evaluation': cases('E'),
                                        'evaluation_authored_at': self.s.now()}))
        kwargs = {}
        if method != 'single-shot':
            checker = self.root / 'checker.py'
            checker.write_text(checker_source or 'import json\nprint(json.dumps({"status":"no_findings","diagnostics":[]}))\n')
            oracle = self.root / 'oracle.json'
            data = self.s.read(dataset)
            oracle.write_text(json.dumps({'dataset_sha256': self.s.sha(dataset.read_bytes()), 'cases': {
                c['id']: {'source_sha256': self.s.sha(c['source'].encode()), 'kind': 'numeric', 'spec': {}}
                for c in data['development'] + data['evaluation'] if c['modality'] == 'L3'}}))
            browser = MODULE.with_name('browser_check.mjs')
            if browser_source:
                browser = self.root / 'fixture-browser.mjs';browser.write_text(browser_source)
            kwargs = {'method': method, 'tools': {'html_checker': checker,
                'browser_checker': browser, 'oracle': oracle}}
        self.s.freeze(run, baseline, ste, provenance, dataset, **kwargs)
        return run, candidate

    def test_runner_is_independent_of_historical_rounds(self):
        text = MODULE.read_text()
        self.assertNotIn('clarity-20261016', text)
        self.assertNotIn('spec_from_file_location', text)

    def test_full_matrix_has_six_cohorts_three_arms_and_two_repetitions(self):
        run, _ = self.fixture()
        plan = self.s.verify(run)
        jobs = list(self.s.jobs(plan))
        self.assertEqual(864, len(jobs))
        self.assertEqual(864, len({self.s.ident(j) for j in jobs}))
        self.assertEqual({'medium', 'high', 'xhigh'}, {j['effort'] for j in jobs})
        self.assertEqual(288, plan['expected_reviews'])

    def test_full_reference_bundle_is_supplied_to_every_candidate_request(self):
        run, _ = self.fixture()
        plan = self.s.verify(run)
        job = next(j for j in self.s.jobs(plan) if j['arm'] == 'candidate')
        request = self.s.generation_request(run, plan, job)
        prompt = request['input'][0]['content'][0]['text']
        self.assertIn('빠뜨리지 않을 전체 참조', prompt)
        self.assertEqual([], request['tools'])
        self.assertEqual(64000, request['max_output_tokens'])

    def test_freeze_snapshot_survives_source_edits_but_rejects_snapshot_edits(self):
        run, candidate = self.fixture()
        (candidate / 'SKILL.md').write_text('후속 편집')
        self.s.verify(run)
        path = run / 'frozen/candidate/SKILL.md'
        path.write_text('증거 변경')
        with self.assertRaisesRegex(ValueError, 'hash|drift'):
            self.s.verify(run)

    def test_heldout_must_be_authored_after_candidate_freeze(self):
        with self.assertRaisesRegex(ValueError, 'authored|freeze'):
            self.s.validate_dataset({'development': cases('D'), 'evaluation': cases('E'),
                                     'evaluation_authored_at': '2020-01-01T00:00:00+00:00'},
                                    '2026-01-01T00:00:00+00:00')

    def test_duplicate_normalized_sources_are_rejected(self):
        d = {'development': cases('D'), 'evaluation': cases('E'), 'evaluation_authored_at': self.s.now()}
        d['evaluation'][0]['source'] = '  D  원문  1  '
        with self.assertRaisesRegex(ValueError, 'duplicate|overlap'):
            self.s.validate_dataset(d, '2020-01-01T00:00:00+00:00')

    def test_request_does_not_contain_other_arms_or_answers(self):
        run, _ = self.fixture()
        plan = self.s.verify(run)
        first = list(self.s.jobs(plan, 'development'))[:3]
        prompts = [self.s.generation_request(run, plan, j)['input'][0]['content'][0]['text'] for j in first]
        self.assertIn('기존 작성 규칙', prompts[0])
        self.assertNotIn('후보 작성 규칙', prompts[0])
        self.assertIn('후보 작성 규칙', prompts[1])
        self.assertNotIn('기존 작성 규칙', prompts[1])
        self.assertNotIn('후보 작성 규칙', prompts[2])

    def test_extract_records_unknown_returned_effort_without_claiming_it(self):
        response, text = self.s.extract(stream(effort=None), 'gpt-6.1-sol', 'medium')
        self.assertIsNone(response.get('reasoning', {}).get('effort'))
        self.assertEqual('원시 결과', text)

    def test_extract_rejects_mismatch_incomplete_tools_and_fallback(self):
        for raw in [stream(model='other'), stream(effort='high'), stream(status='incomplete'),
                    stream().replace(b'"status": "completed"', b'"fallback": true, "status": "completed"'),
                    stream().replace(b'"type": "message"', b'"type": "function_call"')]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.s.extract(raw, 'gpt-6.1-sol', 'medium')

    def test_failed_transport_keeps_partial_raw_and_never_retries(self):
        class Broken(io.BytesIO):
            def read1(self, size):
                if self.tell():
                    raise TimeoutError('fixture timeout')
                return super().read(size)
        attempt = self.root / 'attempt'
        request = self.s.body('입력', 'gpt-6.1-sol', 'medium')
        with patch.object(self.s, 'open_request', return_value=Broken(b'data: partial\n')) as call:
            rec = self.s.call(attempt, request, timeout=1)
            self.assertEqual('error', rec['status'])
            self.assertEqual(b'data: partial\n', (attempt / 'response.raw').read_bytes())
            with self.assertRaises(FileExistsError):
                self.s.call(attempt, request, timeout=1)
            self.assertEqual(1, call.call_count)

    def test_review_requires_exact_clarity_and_meaning_evidence(self):
        outputs = {k: '결과' for k in 'ABC'}
        good = verdict()
        self.s.validate_review(good, '원문', outputs)
        good['pairs'][0]['evidence'][0]['quote'] = '지어낸 인용'
        with self.assertRaisesRegex(ValueError, 'quote|evidence'):
            self.s.validate_review(good, '원문', outputs)
        bad = verdict()
        bad['outputs']['A'].update({'meaning': 'fail', 'findings': [
            {'source_quote': '없는 원문', 'output_quote': '결과', 'reason': '추가'}]})
        with self.assertRaisesRegex(ValueError, 'quote|evidence'):
            self.s.validate_review(bad, '원문', outputs)

    def test_clarity_can_supply_more_than_two_grounded_quotes(self):
        outputs = {label: '결과와 조건을 확인한다.' for label in 'ABC'}
        result = verdict()
        result['pairs'][0]['evidence'].extend([
            {'label': 'A', 'quote': '조건'}, {'label': 'B', 'quote': '확인한다.'}])
        result['pairs'][1]['evidence'].append({'label': 'C', 'quote': '조건'})
        self.s.validate_review(result, '원자료', outputs)
        result['pairs'][0]['evidence'][-1]['quote'] = '없는 근거'
        with self.assertRaisesRegex(ValueError, 'quote'):
            self.s.validate_review(result, '원자료', outputs)

    def test_aggregate_never_accepts_missing_ste_or_flags_only_report(self):
        run, _ = self.fixture()
        report = self.s.aggregate(run)
        self.assertEqual('incomplete', report['comparison_status'])
        self.assertEqual('not_passed', report['quality_gate'])
        self.assertEqual(864, report['expected_generations'])
        (run / 'summary.json').write_text(json.dumps({'quality_gate': 'pass', 'media_gate': 'pass', 'host_gate': 'pass'}))
        frozen = self.s.read(run / 'candidate-freeze.json')
        with self.assertRaisesRegex(ValueError, 'incomplete|gate|evidence'):
            self.s.validate_installation_evidence(run, frozen['files'], frozen['candidate_id'])

    def test_catalog_requires_all_requested_efforts_and_responses(self):
        catalog = {'data': [{'id': m, 'reasoning_efforts': [{'value': x} for x in self.s.EFFORTS],
                             'api_types': ['responses']} for m in self.s.MODELS]}
        self.s.validate_catalog(catalog)
        catalog['data'][1]['reasoning_efforts'].pop()
        with self.assertRaisesRegex(ValueError, 'effort|support'):
            self.s.validate_catalog(catalog)

    def fake_backend(self, request, timeout):
        body = json.loads(request.data)
        prompt = body['input'][0]['content'][0]['text']
        if prompt.startswith(self.s.RUBRIC):
            packet = json.loads(prompt[len(self.s.RUBRIC) + 2:])
            result = verdict()
            candidate = next(label for label, value in packet['outputs'].items() if '결과 candidate' in value)
            if packet['modality'] == 'L4':
                for label in 'ABC':
                    result['outputs'][label]['format']['scene_correspondence'] = [{
                        'scene_id': 'Scene1', 'code_quote': 'class Scene1(Scene):',
                        'narration_quote': 'Scene1 내레이션: 결과', 'reason': '동일 장면의 결과를 설명한다.'}]
            for pair in result['pairs']:
                if candidate in (pair['left'], pair['right']):
                    pair['winner'] = candidate
            text = json.dumps(result, ensure_ascii=False)
        elif prompt.startswith('다음 문장만'):
            text = '연결을 확인했다.'
        else:
            arm = 'candidate' if '후보 작성 규칙' in prompt else 'baseline' if '기존 작성 규칙' in prompt else 'ste'
            text = '결과 ' + arm
            if '단일 HTML/CSS/JavaScript' in prompt:
                text += '\n```html\n<!doctype html><html lang="ko"><meta name="viewport" content="width=device-width"><body><button>결과</button></body></html>\n```'
            elif 'Manim Python' in prompt:
                text += '\n```python\nfrom manim import Scene\nclass Scene1(Scene):\n    def construct(self):\n        self.wait(1)\n```\nScene1 내레이션: 결과'
        return io.BytesIO(stream(body['model'], body['reasoning']['effort'], text))

    def complete_fixture(self):
        run, _ = self.fixture()
        catalog = {'data': [{'id': m, 'reasoning_efforts': list(self.s.EFFORTS),
                             'api_types': ['responses']} for m in self.s.MODELS]}
        self.s.dump(run / 'preflight/catalog.json', catalog)
        with patch.object(self.s, 'open_request', side_effect=self.fake_backend):
            self.assertTrue(self.s.preflight(run)['passed'])
            for split in ('development', 'evaluation'):
                self.s.generate(run, split, workers=4)
                self.s.review(run, split, workers=4)
        return run

    def test_complete_mock_matrix_rederives_quality_but_not_media_or_host(self):
        run = self.complete_fixture()
        report = self.s.aggregate(run)
        self.assertEqual('complete', report['comparison_status'])
        self.assertEqual('pass', report['quality_gate'])
        self.assertEqual(864, report['completed_generations'])
        self.assertEqual(288, report['valid_reviews'])
        self.assertEqual('not_checked', report['media_gate'])
        self.assertEqual('not_checked', report['host_gate'])
        self.assertEqual(6, len(report['evaluation_pairs']))
        # A stored "pass" cannot substitute for recomputing the damaged raw evidence.
        self.s.dump(run / 'summary.json', report)
        output = next((run / 'runs').glob('*-ste/output.md'))
        output.write_text('改ざん')
        changed = self.s.aggregate(run)
        self.assertEqual('incomplete', changed['comparison_status'])
        self.assertEqual('not_passed', changed['quality_gate'])

    def test_development_gate_withholds_heldout_network_calls(self):
        run, _ = self.fixture()
        catalog = {'data': [{'id': m, 'reasoning_efforts': list(self.s.EFFORTS),
                             'api_types': ['responses']} for m in self.s.MODELS]}
        self.s.dump(run / 'preflight/catalog.json', catalog)
        with patch.object(self.s, 'open_request', side_effect=self.fake_backend) as call:
            self.s.preflight(run)
            count = call.call_count
            with self.assertRaisesRegex(ValueError, 'development gate'):
                self.s.generate(run, 'evaluation')
            self.assertEqual(count, call.call_count)

    def test_plan_edits_are_detected(self):
        run, _ = self.fixture()
        plan = self.s.read(run / 'plan.json')
        plan['created'] = '2020-01-01T00:00:00+00:00'
        (run / 'plan.json').write_bytes(self.s.encode(plan))
        with self.assertRaisesRegex(ValueError, 'hash|drift'):
            self.s.verify(run)

    def test_sol_authentication_is_local_unredirected_and_not_saved(self):
        auth = self.root / '.codex/auth.json'
        auth.parent.mkdir()
        auth.write_text(json.dumps({'tokens': {'access_token': 'secret-fixture-token'}}))
        request = self.s.urllib.request.Request(self.s.ENDPOINT, data=self.s.encode(
            self.s.body('원문', self.s.MODELS[0], 'medium')))
        with patch.object(self.s.Path, 'home', return_value=self.root), patch.object(
                self.s.urllib.request, 'build_opener') as opener:
            self.s.open_request(request, 1)
            self.assertEqual('Bearer secret-fixture-token', request.unredirected_hdrs['Authorization'])
            self.assertNotIn('Authorization', request.headers)
            self.assertIsInstance(opener.call_args[0][0], self.s.NoRedirect)
        bad = self.s.urllib.request.Request('https://other.example/responses', data=request.data)
        with self.assertRaisesRegex(ValueError, 'destination'):
            self.s.open_request(bad, 1)

    def test_http_errors_preserve_body_without_exception_details(self):
        request = self.s.body('입력', self.s.MODELS[0], 'medium')
        failure = self.s.urllib.error.HTTPError(self.s.ENDPOINT, 401, 'secret-fixture-token', {}, io.BytesIO(b'unauthorized'))
        with patch.object(self.s, 'open_request', side_effect=failure):
            record = self.s.call(self.root / 'failed', request)
        self.assertEqual(b'unauthorized', (self.root / 'failed/response.raw').read_bytes())
        self.assertNotIn('secret-fixture-token', json.dumps(record))

    def test_prompt_inventory_routes_new_assets_but_excludes_optional_provenance(self):
        files = {name: 'abc' for name in [
            'skills/korean-protocol/SKILL.md',
            'skills/korean-protocol/references/meaning-boundaries.md',
            'skills/korean-protocol/references/output-formats.md',
            'skills/korean-protocol/references/interactive-html.md',
            'skills/korean-protocol/references/video-script.md',
            'skills/korean-protocol/assets/interactive-explainer.html',
            'skills/korean-protocol/agents/openai.yaml',
            'specification/rules.json', 'lexicon/large.json', 'support/server.py']}
        inventory = self.s.prompt_inventory(files)
        self.assertEqual(3, len(inventory['L1']))
        self.assertEqual(5, len(inventory['L3']))
        self.assertEqual(4, len(inventory['L4']))
        self.assertTrue(all(not n.startswith(('specification/', 'lexicon/', 'support/'))
                            for names in inventory.values() for n in names))

    def test_candidate_wrong_format_blocks_quality_even_with_good_meaning(self):
        run = self.complete_fixture()
        target = next(j for j in self.s.jobs(self.s.verify(run))
                      if j['arm'] == 'candidate' and j['case']['modality'] == 'L3')
        directory = run / 'runs' / self.s.ident(target)
        # Rebuild a fully linked but invalid candidate response; no mere hash failure.
        raw = stream(target['model'], target['effort'], '결과 candidate')
        (directory / 'response.raw').write_bytes(raw)
        (directory / 'output.md').write_text('결과 candidate')
        rec = self.s.read(directory / 'record.json')
        rec.update(response_sha256=self.s.sha(raw), output_sha256=self.s.sha('결과 candidate'.encode()))
        (directory / 'record.json').write_bytes(self.s.encode(rec))
        report = self.s.aggregate(run)
        self.assertEqual('not_passed', report['quality_gate'])
        self.assertTrue(report['format_failures'])

    def test_placeholder_media_evidence_is_rejected_even_with_valid_sha(self):
        artifact = self.root / 'a.png'
        artifact.write_bytes(b'a')
        evidence = {'candidate_id': 'abc', 'checks': [
            {'id': x, 'status': 'pass', 'details': 'passed',
             'artifacts': [{'path': 'a.png', 'sha256': self.s.sha(b'a')}]} for x in
            ['static', 'interactive', 'animation']]}
        with self.assertRaises((ValueError, KeyError, OSError)):
            self.s.validate_external_evidence(self.root, evidence, 'abc', ['static', 'interactive', 'animation'])

    def host_fixture(self, run, host='claude'):
        plan = self.s.verify(run)
        names = sorted(set(n for names in plan['prompt_files']['candidate'].values() for n in names))
        command = (['claude', '--model', 'claude-opus-5-5', '--effort', 'medium'] if host == 'claude' else
                   ['codex', '--model', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="medium"'])
        request = {'candidate_id': plan['candidate']['candidate_id'], 'source_hashes': plan['candidate']['files'],
                   'loaded_files': names, 'skill_root': '/tmp/staged-skill', 'command': command,
                   'routing': 'http://127.0.0.1:10100', 'prompt': '/korean-protocol 요청' if host == 'claude' else '$korean-protocol 요청',
                   'host_frontmatter_adapter': host == 'claude'}
        events = []
        for index, name in enumerate(names):
            body = (run / 'frozen/candidate' / name).read_text()
            if host == 'claude' and name.endswith('SKILL.md'):
                body = body.replace('name: korean-protocol\n',
                    'name: korean-protocol\ndisable-model-invocation: true\nuser-invocable: true\n', 1)
            if host == 'claude':
                events += [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': str(index),
                    'name': 'Read', 'input': {'file_path': '/tmp/staged-skill/' + name}}]}},
                    {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': str(index), 'content': body}]}}]
            else:
                events += [{'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'cat /tmp/staged-skill/' + name,
                    'aggregated_output': body, 'exit_code': 0}}]
        events += [{'type': 'result', 'result': '결과'}] if host == 'claude' else [
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '결과'}}]
        artifacts = {'request': self.s.encode(request), 'events': b''.join(self.s.encode(e).replace(b'\n', b'') + b'\n' for e in events),
                     'exit': self.s.encode({'exit_code': 0}), 'output': '결과'.encode()}
        result = {'id': host}
        for role, data in artifacts.items():
            path = run / 'host-smoke' / host / role
            self.s.save(path, data)
            result[role] = {'path': path.relative_to(run).as_posix(), 'sha256': self.s.sha(data)}
        return result

    def test_host_trace_accepts_only_authorized_claude_frontmatter_adapter(self):
        run, _ = self.fixture()
        check = self.host_fixture(run)
        self.s._validate_host(run, self.s.verify(run), check)
        events = run / check['events']['path']
        raw = events.read_bytes().replace('후보 작성 규칙'.encode(), '변경한 본문'.encode())
        events.write_bytes(raw)
        check['events']['sha256'] = self.s.sha(raw)
        with self.assertRaisesRegex(ValueError, 'full skill file read'):
            self.s._validate_host(run, self.s.verify(run), check)

    def test_malformed_host_command_is_a_gate_failure(self):
        run, _ = self.fixture()
        check = self.host_fixture(run, 'codex')
        request = self.s.read(run / check['request']['path'])
        request['command'] = ['codex', '--model']
        data = self.s.encode(request)
        (run / check['request']['path']).write_bytes(data)
        check['request']['sha256'] = self.s.sha(data)
        with self.assertRaises(ValueError):
            self.s._validate_host(run, self.s.verify(run), check)

    def test_codex_cat_paths_resolve_against_recorded_project(self):
        run, _ = self.fixture()
        check = self.host_fixture(run, 'codex')
        request = self.s.read(run / check['request']['path'])
        request['project'] = '/tmp'
        data = self.s.encode(request)
        (run / check['request']['path']).write_bytes(data)
        check['request']['sha256'] = self.s.sha(data)
        events = run / check['events']['path']
        content = events.read_text().replace('cat /tmp/staged-skill/', 'cat staged-skill/')
        events.write_text(content)
        check['events']['sha256'] = self.s.sha(content.encode())
        self.s._validate_host(run, self.s.verify(run), check)

    def assisted_job(self, run, modality='L4', arm='candidate'):
        return next(j for j in self.s.jobs(self.s.verify(run), 'development')
                    if j['case']['modality'] == modality and j['arm'] == arm)

    def test_assisted_method_freezes_shared_tools_and_three_call_budget(self):
        run, _ = self.fixture('tool-assisted-v1')
        plan = self.s.verify(run)
        self.assertEqual('tool-assisted-v1', plan['method'])
        self.assertEqual(2, plan['tool_policy']['max_revisions'])
        self.assertEqual(192000, plan['tool_policy']['max_output_tokens_per_generation'])
        self.assertTrue(all('frozen/tools/' + name in plan['files'] for name in
                            ['check_html.py', 'browser_check.mjs', 'oracle.json']))
        request = self.s.generation_request(run, plan, self.assisted_job(run))
        self.assertNotIn('도구를 사용할 수 없다', request['input'][0]['content'][0]['text'])

    def test_assisted_static_failure_gets_one_self_revision_in_all_three_arms(self):
        good = '결과\n```python\nfrom manim import Scene\nclass Scene1(Scene):\n    def construct(self):\n        self.wait(1)\n```\nScene1 내레이션: 결과'
        original_root = self.root
        for arm in ('baseline', 'candidate', 'ste'):
            with self.subTest(arm=arm):
                self.root = original_root / arm
                self.root.mkdir()
                run, _ = self.fixture('tool-assisted-v1')
                plan = self.s.verify(run)
                job = self.assisted_job(run, arm=arm)
                calls = []
                def backend(request, timeout):
                    request = json.loads(request.data);calls.append(request)
                    text = '```python\nclass Broken(:\n```' if len(calls) == 1 else good
                    return io.BytesIO(stream(job['model'], job['effort'], text))
                with patch.object(self.s, 'open_request', side_effect=backend):
                    result = self.s.assisted_generate(run, plan, job)
                self.assertEqual('completed', result['status'])
                self.assertEqual(1, result['selected_attempt'])
                selected, record = self.s.generation_result(run, plan, job)
                self.assertEqual(good, (selected / 'output.md').read_text())
                self.assertEqual(2, len(calls))
                self.assertTrue(all(x['reasoning']['effort'] == job['effort'] and x['model'] == job['model']
                                    and x['max_output_tokens'] == 64000 for x in calls))
                self.assertIn('class Broken(:', calls[1]['input'][0]['content'][0]['text'])
                self.assertNotIn('outputs', calls[1]['input'][0]['content'][0]['text'])
        self.root = original_root

    def test_assisted_no_findings_uses_initial_output_without_extra_model_call(self):
        run, _ = self.fixture('tool-assisted-v1');plan = self.s.verify(run);job = self.assisted_job(run, 'L1')
        with patch.object(self.s, 'open_request', side_effect=self.fake_backend) as calls:
            result = self.s.assisted_generate(run, plan, job)
        self.assertEqual(0, result['selected_attempt']);self.assertEqual(1, calls.call_count)
        self.assertEqual('pass', result['diagnostic_status'])

    def test_assisted_exhausts_exactly_two_revisions_and_keeps_all_raws(self):
        run, _ = self.fixture('tool-assisted-v1');plan = self.s.verify(run);job = self.assisted_job(run)
        with patch.object(self.s, 'open_request', side_effect=lambda request, timeout: io.BytesIO(
                stream(job['model'], job['effort'], '```python\nclass Broken(:\n```'))) as calls:
            result = self.s.assisted_generate(run, plan, job)
        self.assertEqual(3, calls.call_count);self.assertEqual(2, result['selected_attempt'])
        self.assertEqual('issues_found', result['diagnostic_status'])
        root = run / 'runs' / self.s.ident(job)
        self.assertEqual(3, len(list((root / 'attempts').glob('*/response.raw'))))
        with self.assertRaises(FileExistsError):
            self.s.assisted_generate(run, plan, job)

    def test_assisted_transport_error_does_not_use_another_revision_as_retry(self):
        run, _ = self.fixture('tool-assisted-v1');plan = self.s.verify(run);job = self.assisted_job(run)
        count = 0
        def backend(request, timeout):
            nonlocal count
            count += 1
            if count == 2: raise TimeoutError('model fixture error')
            return io.BytesIO(stream(job['model'], job['effort'], '```python\nclass Broken(:\n```'))
        with patch.object(self.s, 'open_request', side_effect=backend):
            result = self.s.assisted_generate(run, plan, job)
        self.assertEqual('error', result['status']);self.assertEqual(2, count)
        with self.assertRaisesRegex(ValueError, 'incomplete|error'):
            self.s.generation_result(run, plan, job)

    def test_assisted_chain_rejects_changed_diagnostic_or_hidden_attempt(self):
        run, _ = self.fixture('tool-assisted-v1');plan = self.s.verify(run);job = self.assisted_job(run, 'L1')
        with patch.object(self.s, 'open_request', side_effect=self.fake_backend):
            self.s.assisted_generate(run, plan, job)
        root = run / 'runs' / self.s.ident(job)
        report = root / 'attempts/0/diagnostics/report.json'
        report.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash|diagnostic'):
            self.s.generation_result(run, plan, job)

    def test_browser_receipt_cannot_pass_without_bound_static_capture_and_exact_probes(self):
        run, _ = self.fixture('tool-assisted-v1');plan = self.s.verify(run);job = self.assisted_job(run, 'L3')
        receipt = {'tool': 'playwright', 'status': 'pass', 'console_errors': [], 'actions': {}}
        with self.assertRaises(ValueError):
            self.s.validate_browser_receipt(run, plan, job, self.root, receipt, 'html', 'output')

    def fake_browser_source(self):
        import struct,zlib,base64
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,200,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\xff'*960)*200))+chunk(b'IEND',b'')
        return '''import fs from 'node:fs';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';
const a={};for(let i=2;i<process.argv.length;i+=2)a[process.argv[i].slice(2)]=process.argv[i+1];
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');const data=fs.readFileSync(a.dataset);const d=JSON.parse(data);const c=[...d.development,...d.evaluation].find(x=>x.id===a.case);const html=fs.readFileSync(a.html);const p=a.output;fs.mkdirSync(p);
const image=Buffer.from('PNG','base64');fs.writeFileSync(p+'/screen.png',image);const shot={path:'screen.png',sha256:sha(image)};
const text={javascript_enabled:false,html_sha256:sha(html),title:'단위 테스트',body:html.toString(),screenshot:shot};const raw=JSON.stringify(text);fs.writeFileSync(p+'/static.json',raw);
const snapshot={body:'단위 테스트',inputs:[],buttons:[],results:[],viewport:{width:320,height:200,scroll_width:320}};
const r={tool:'playwright',case_id:a.case,output_sha256:a['output-sha256'],html_sha256:sha(html),verifier_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),dataset_sha256:sha(data),source_sha256:sha(c.source),oracle_sha256:sha(fs.readFileSync(a.oracle)),status:'pass',console_errors:[],blocked_requests:[],observations:[],initial_snapshot:snapshot,final_snapshot:snapshot,screenshot:shot,static_visible_text:{path:'static.json',sha256:sha(raw),javascript_enabled:false},actions:Object.fromEntries(['initial','change','invalid','reset','narrow','keyboard'].map(k=>[k,{status:'pass',observations:{fixture:true}}]))};
fs.writeFileSync(p+'/receipt.json',JSON.stringify(r));'''.replace('PNG',base64.b64encode(png).decode())

    def bound_failed_browser_receipt(self, run, plan, job, html, body='毎週ではなく毎週', inputs=None, buttons=None):
        import struct,zlib
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,200,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\xff'*960)*200))+chunk(b'IEND',b'')
        directory=self.root/'bound-browser';directory.mkdir()
        self.s.save(directory/'screen.png',png)
        screenshot={'path':'screen.png','sha256':self.s.sha(png)}
        static={'javascript_enabled':False,'html_sha256':self.s.sha(html.encode()),'body':body,'title':'시험','screenshot':screenshot}
        self.s.dump(directory/'static.json',static)
        snapshot={'body':body,'inputs':inputs or [],'buttons':buttons or [],'results':[],
                  'viewport':{'width':1280,'height':900,'scroll_width':1280}}
        actions={name:{'status':'fail','observations':{'error':'Numeric controls were not recognized','snapshot':snapshot}}
                 for name in ['initial','change','invalid','reset','narrow','keyboard']}
        actions['initial']['observations']['error']='Cannot unambiguously identify numeric field 0 from labels/IDs/bounds'
        actions['narrow']={'status':'pass','observations':{'viewport':{'width':320,'height':900,'scroll_width':320},'controls':[]}}
        receipt={'tool':'playwright','case_id':job['case']['id'],'output_sha256':self.s.sha(html.encode()),
                 'html_sha256':self.s.sha(html.encode()),'verifier_sha256':plan['files']['frozen/tools/browser_check.mjs'],
                 'dataset_sha256':plan['files']['frozen/dataset.json'],'source_sha256':self.s.sha(job['case']['source'].encode()),
                 'oracle_sha256':plan['files']['frozen/tools/oracle.json'],'console_errors':[],'blocked_requests':[],
                 'observations':[],'initial_snapshot':snapshot,'final_snapshot':snapshot,'actions':actions,
                 'static_visible_text':{'path':'static.json','sha256':self.s.sha((directory/'static.json').read_bytes()),'javascript_enabled':False},
                 'screenshot':screenshot,'status':'fail'}
        return directory,receipt

    def test_assisted_html_process_feedback_and_bound_browser_are_replayed(self):
        checker = '''import json,sys,hashlib
from pathlib import Path
bad='CHECKER_BAD' in Path(sys.argv[1]).read_text()
print(json.dumps({'schema_version':1,'file':sys.argv[1],'sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'language':'ko','status':'issues_found' if bad else 'no_findings','diagnostics':[{'code':'fixture_bad','severity':'error','snippet':'CHECKER_BAD'}] if bad else []}))
raise SystemExit(1 if bad else 0)
'''
        run, _ = self.fixture('tool-assisted-v1', checker, self.fake_browser_source())
        plan = self.s.verify(run);job = self.assisted_job(run, 'L3');count = 0
        def backend(request, timeout):
            nonlocal count
            count += 1
            text = '<html lang="ko"><meta name="viewport" content="width=device-width"><body>'+('CHECKER_BAD' if count == 1 else '수정한 출력')+'</body></html>'
            return io.BytesIO(stream(job['model'], job['effort'], text))
        with patch.object(self.s, 'open_request', side_effect=backend):
            selected = self.s.assisted_generate(run, plan, job)
        self.assertEqual(1, selected['selected_attempt']);self.assertEqual(2,count)
        directory, record = self.s.generation_result(run, plan, job)
        self.assertEqual('pass', record['diagnostic_status'])
        receipt = directory / 'diagnostics/browser/receipt.json'
        changed = self.s.read(receipt);changed['actions'] = {}
        receipt.write_bytes(self.s.encode(changed))
        with self.assertRaisesRegex(ValueError, 'diagnostic|evidence'):
            self.s.generation_result(run, plan, job)

    def test_assisted_checker_infrastructure_error_never_triggers_rewrite(self):
        run, _ = self.fixture('tool-assisted-v1', 'raise SystemExit(2)\n')
        plan = self.s.verify(run);job = self.assisted_job(run, 'L3')
        raw='<html lang="ko"><meta name="viewport" content="width=device-width"><body>자료</body></html>'
        with patch.object(self.s, 'open_request', return_value=io.BytesIO(stream(job['model'],job['effort'],raw))) as calls:
            result = self.s.assisted_generate(run,plan,job)
        self.assertEqual('error', result['status']);self.assertEqual('error',result['diagnostic_status'])
        self.assertEqual(1,calls.call_count)
        self.assertTrue((run/'runs'/self.s.ident(job)/'attempts/0/diagnostics/html/stderr.raw').exists())

    def test_protected_text_requires_exact_source_membership_without_whole_source_allowlist(self):
        case={'source':'이름은 `JOB  42`다. 경로는 `/tmp/a  b`다.','protected_text':['JOB  42']}
        self.assertEqual(['/tmp/a  b','JOB  42'],self.s.protected_source_text(case))
        case['protected_text']=['원자료에 없는 일본어']
        with self.assertRaisesRegex(ValueError,'source'):
            self.s.protected_source_text(case)

    def test_assisted_final_review_flags_remain_unresolved_after_two_opportunities(self):
        checker = '''import json,sys,hashlib
from pathlib import Path
print(json.dumps({'schema_version':1,'file':sys.argv[1],'sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'language':'ko','status':'review_required','diagnostics':[{'code':'protected_review','severity':'review','snippet':'원문'}]}))
raise SystemExit(1)
'''
        run, _ = self.fixture('tool-assisted-v1', checker, self.fake_browser_source())
        plan = self.s.verify(run);job = self.assisted_job(run, 'L3')
        output='<html lang="ko"><meta name="viewport" content="width=device-width"><body>원문</body></html>'
        with patch.object(self.s, 'open_request', side_effect=lambda req, timeout: io.BytesIO(stream(job['model'],job['effort'],output))) as calls:
            result=self.s.assisted_generate(run,plan,job)
        self.assertEqual(3,calls.call_count);self.assertEqual('review_required',result['diagnostic_status'])
        selected,record=self.s.generation_result(run,plan,job)
        self.assertEqual('review_required',record['diagnostic_status'])
        report=self.s.aggregate(run)
        self.assertEqual('not_passed',report['quality_gate'])
        self.assertEqual('review_required',report['tool_failures'][0]['status'])

    def test_assisted_rejects_tool_drift_before_model_or_process_calls(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run)
        (run/'frozen/tools/check_html.py').write_text('changed')
        with patch.object(self.s,'open_request') as call, self.assertRaisesRegex(ValueError,'tool hash drift'):
            self.s.assisted_generate(run,plan,job)
        self.assertFalse(call.called)

    def test_diagnostic_timeout_preserves_partial_bytes(self):
        result=self.s._run_tool(self.root/'timed-tool',[self.s.sys.executable,'-u','-c',
            'import time;print("partial diagnostic",flush=True);time.sleep(5)'],0.2)
        self.assertTrue(result['timed_out'])
        self.assertIn(b'partial diagnostic',(self.root/'timed-tool/stdout.raw').read_bytes())
        self.assertTrue((self.root/'timed-tool/stderr.raw').exists())

    def test_assisted_chain_rejects_an_extra_unselected_attempt(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L1')
        with patch.object(self.s,'open_request',side_effect=self.fake_backend):
            self.s.assisted_generate(run,plan,job)
        (run/'runs'/self.s.ident(job)/'attempts/1').mkdir()
        with self.assertRaisesRegex(ValueError,'hidden|missing'):
            self.s.generation_result(run,plan,job)

    def test_missing_controls_in_complete_snapshot_are_repairable_artifact_failure(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html lang="ko"><body><h1>毎週ではなく毎週</h1></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html)
        self.assertFalse(self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html))

    def test_observed_empty_body_is_artifact_failure_instead_of_missing_data(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html lang="ko"><body></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,body='')
        self.assertFalse(self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html))

    def test_ambiguous_existing_numeric_controls_remain_infrastructure_failure(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><input><input><input></body></html>'
        inputs=[{'id':'a'+str(i),'visible':True,'type':'number'}for i in range(3)]
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,inputs=inputs)
        with self.assertRaisesRegex(ValueError,'identify|oracle'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_nonstandard_controls_remain_unknown_infrastructure_failure(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><div role="spinbutton" contenteditable="true">1000</div></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,body='1000')
        with self.assertRaisesRegex(ValueError,'identify|oracle'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_aria_checkbox_is_not_proven_absent_native_ui(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><div role="checkbox" tabindex="0">선택한다</div></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,body='선택한다')
        with self.assertRaisesRegex(ValueError,'identify|oracle'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_inline_focusable_control_is_not_proven_absent_native_ui(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><div onclick="change()" tabindex="0">값을 변경한다</div></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,body='값을 변경한다')
        with self.assertRaisesRegex(ValueError,'identify|oracle'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_unquoted_custom_role_is_not_proven_absent_native_ui(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><div role=spinbutton>1000</div></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,body='1000')
        with self.assertRaisesRegex(ValueError,'identify|oracle'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_missing_snapshot_body_remains_infrastructure_failure(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html)
        del receipt['initial_snapshot']['body']
        with self.assertRaises(ValueError):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_media_and_host_checks_require_hashed_artifacts(self):
        with self.assertRaisesRegex(ValueError, 'artifact|check|evidence'):
            self.s.validate_external_evidence(self.root, {'candidate_id': 'abc', 'checks': [
                {'id': x, 'status': 'pass', 'artifacts': []} for x in ['static', 'interactive', 'animation']]},
                'abc', ['static', 'interactive', 'animation'])

    def test_viewer_escapes_untrusted_output_and_preserves_three_columns(self):
        run, _ = self.fixture()
        page = self.s.viewer(run)
        text = page.read_text()
        self.assertIn('원자료', text)
        self.assertIn('STE', text)
        self.assertIn('baseline', text)
        self.assertIn('textContent', text)

    def quote_review_fixture(self):
        run,_=self.fixture();plan=self.s.verify(run);job=next(self.s.triads(plan,'development'))
        for arm in self.s.ARMS:
            generation=dict(job,arm=arm)
            def backend(request,timeout):
                payload=json.loads(request.data)
                return io.BytesIO(stream(payload['model'],payload['reasoning']['effort'],'**문서로 확인한 사항**\n결과'))
            with patch.object(self.s,'open_request',side_effect=backend):
                self.s.call(run/'runs'/self.s.ident(generation),self.s.generation_request(run,plan,generation))
        packet,links,request=self.s.review_materials(run,plan,job)
        bad=verdict();bad['outputs']['A']['format']['evidence'][0]['output_quote']='**文서로 확인한 사항**'
        bad['outputs']['A']['format']['evidence'][0]['reason']='허용된 Markdown 강조로 상태별 구획을 표시했다.'
        good=json.loads(json.dumps(bad));good['outputs']['A']['format']['evidence'][0]['output_quote']='**문서로 확인한 사항**'
        return run,plan,job,packet,bad,good

    def execute_quote_review(self,run,plan,job,responses):
        requests=[]
        def backend(request,timeout):
            payload=json.loads(request.data);requests.append(payload)
            response=responses[min(len(requests)-1,len(responses)-1)]
            text=response if isinstance(response,str)else json.dumps(response,ensure_ascii=False)
            return io.BytesIO(stream(payload['model'],payload['reasoning']['effort'],text))
        with patch.object(self.s,'open_request',side_effect=backend):
            result=self.s.review_one(run,plan,job)
        return result,requests

    def test_exact_quote_repair_corrects_actual_d01_glyph_without_regrading(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        result,requests=self.execute_quote_review(run,plan,job,[bad,good])
        self.assertEqual('completed',result['status']);self.assertEqual(1,result['selected_attempt'])
        directory,selected,record=self.s.review_result(run,plan,job)
        self.assertEqual(good,selected);self.assertEqual('1',directory.name);self.assertEqual(2,len(requests))
        self.assertIn('**文서로 확인한 사항**',(directory.parent/'0/output.md').read_text())
        self.assertEqual(bad['outputs']['A']['format']['evidence'][0]['reason'],selected['outputs']['A']['format']['evidence'][0]['reason'])
        self.assertEqual(2,record['model_attempts'])

    def test_quote_repair_is_blind_same_judge_budget_and_all_labels_are_locked(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        result,requests=self.execute_quote_review(run,plan,job,[bad,good])
        self.assertTrue(all(r['model']==self.s.MODELS[1-job['model_index']] and r['reasoning']['effort']=='high'and r['max_output_tokens']==64000 for r in requests))
        prompt=requests[1]['input'][0]['content'][0]['text']
        self.assertIn(json.dumps(packet,ensure_ascii=False),prompt)
        self.assertIn('outputs',prompt);self.assertIn('output_quote',prompt)
        for hint in ['"arm":','"candidate"','"baseline"','"ste"','blind-key']:
            self.assertNotIn(hint,prompt)
        analysis=self.s.review_quote_analysis(bad,packet['source'],packet['outputs'],packet['modality'])
        self.assertEqual([['outputs','A','format','evidence',0,'output_quote']],analysis['bad_paths'])
        self.assertEqual({'A','B','C'},set(analysis['decision_projection']['outputs']))

    def test_valid_fail_and_unresolved_reviews_never_receive_technical_retry(self):
        parent=self.root
        for status in ['fail','unresolved']:
            with self.subTest(status=status):
                self.root=parent/status;self.root.mkdir()
                run,plan,job,packet,bad,good=self.quote_review_fixture()
                good['outputs']['A']['meaning']=status;good['outputs']['A']['findings']=[{
                    'source_quote':packet['source'],'output_quote':'결과','reason':'원자료와 출력의 판단 근거다.'}]
                result,requests=self.execute_quote_review(run,plan,job,[good])
                self.assertEqual('completed',result['status']);self.assertEqual(0,result['selected_attempt']);self.assertEqual(1,len(requests))
                self.assertEqual(status,self.s.review_result(run,plan,job)[1]['outputs']['A']['meaning'])
        self.root=parent

    def test_technical_quote_correction_rejects_grade_reason_count_and_valid_quote_drift(self):
        parent=self.root
        for drift in ['grade','reason','count','valid_quote','order']:
            with self.subTest(drift=drift):
                self.root=parent/drift;self.root.mkdir()
                run,plan,job,packet,bad,good=self.quote_review_fixture()
                changed=json.loads(json.dumps(good))
                if drift=='grade':changed['pairs'][0]['winner']='A'
                elif drift=='reason':changed['outputs']['A']['format']['evidence'][0]['reason']='새로운 판단 이유다.'
                elif drift=='count':changed['pairs'][0]['evidence'].append(dict(changed['pairs'][0]['evidence'][0]))
                elif drift=='valid_quote':changed['outputs']['B']['format']['evidence'][0]['output_quote']='문서로 확인한 사항'
                elif drift=='order':changed['pairs'].reverse()
                result,requests=self.execute_quote_review(run,plan,job,[bad,changed,good])
                self.assertEqual('error',result['status']);self.assertEqual(2,len(requests))
                self.assertEqual('locked_content_drift',result['validation_status'])
                with self.assertRaisesRegex(ValueError,'incomplete|invalid'):
                    self.s.review_result(run,plan,job)
        self.root=parent

    def test_quote_repair_exhausts_two_corrections_without_overwrite_or_fallback(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        result,requests=self.execute_quote_review(run,plan,job,[bad,bad,bad])
        self.assertEqual('error',result['status']);self.assertEqual(3,len(requests))
        self.assertEqual('quote_mismatch',result['validation_status'])
        root=run/'reviews'/self.s.ident(dict(job,arm='blind'))
        self.assertEqual(3,len(list((root/'attempts').glob('*/response.raw'))))
        with self.assertRaises(FileExistsError):self.s.review_one(run,plan,job)

    def test_malformed_json_and_missing_decisions_are_never_quote_repair_eligible(self):
        parent=self.root
        for error in ['syntax','missing_decision','missing_reason']:
            with self.subTest(error=error):
                self.root=parent/error;self.root.mkdir()
                run,plan,job,packet,bad,good=self.quote_review_fixture()
                initial=json.loads(json.dumps(bad))
                if error=='syntax':initial='{"outputs":'
                elif error=='missing_decision':del initial['pairs'][0]['winner']
                elif error=='missing_reason':del initial['outputs']['A']['format']['evidence'][0]['reason']
                result,requests=self.execute_quote_review(run,plan,job,[initial,good])
                self.assertEqual('error',result['status']);self.assertEqual(1,len(requests))
                self.assertEqual('schema_error',result['validation_status'])
        self.root=parent

    def test_review_chain_rejects_tampered_attempt_hash_and_hidden_attempt(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        self.execute_quote_review(run,plan,job,[bad,good])
        root=run/'reviews'/self.s.ident(dict(job,arm='blind'))
        (root/'attempts/2').mkdir()
        with self.assertRaisesRegex(ValueError,'hidden|attempt'):
            self.s.review_result(run,plan,job)

    def test_unspecified_logical_separation_is_not_a_separate_table_requirement(self):
        self.assertIn('독립된 행',self.s.RUBRIC)
        self.assertIn('문단',self.s.RUBRIC)
        self.assertIn('명시적으로',self.s.RUBRIC)
        self.assertEqual('all development and evaluation outputs pass',self.s.ACCEPTANCE['candidate_meaning'])

    def test_exact_quote_repair_applies_identically_to_all_three_blind_labels(self):
        parent=self.root
        for label in 'ABC':
            with self.subTest(label=label):
                self.root=parent/label;self.root.mkdir()
                run,plan,job,packet,unused,unused_good=self.quote_review_fixture()
                bad=verdict();bad['outputs'][label]['format']['evidence'][0]['output_quote']='**文서로 확인한 사항**'
                good=json.loads(json.dumps(bad));good['outputs'][label]['format']['evidence'][0]['output_quote']='**문서로 확인한 사항**'
                result,requests=self.execute_quote_review(run,plan,job,[bad,good])
                self.assertEqual('completed',result['status']);self.assertEqual(2,len(requests))
                self.assertEqual(good,self.s.review_result(run,plan,job)[1])
                self.assertNotIn('"arm":',requests[1]['input'][0]['content'][0]['text'])
        self.root=parent

    def test_second_correction_locks_quotes_that_first_correction_already_fixed(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        bad['outputs']['B']['format']['evidence'][0]['output_quote']='두 번째 잘못된 인용'
        partly=json.loads(json.dumps(bad));partly['outputs']['A']['format']['evidence'][0]['output_quote']='**문서로 확인한 사항**'
        changed=json.loads(json.dumps(partly));changed['outputs']['A']['format']['evidence'][0]['output_quote']='문서로 확인한 사항'
        changed['outputs']['B']['format']['evidence'][0]['output_quote']='결과'
        result,requests=self.execute_quote_review(run,plan,job,[bad,partly,changed])
        self.assertEqual('error',result['status']);self.assertEqual(3,len(requests))
        self.assertEqual('locked_content_drift',result['validation_status'])

    def test_review_transport_failure_does_not_retry_the_correction(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture();requests=[]
        def backend(request,timeout):
            payload=json.loads(request.data);requests.append(payload)
            if len(requests)==2:raise TimeoutError('review transport fixture')
            return io.BytesIO(stream(payload['model'],payload['reasoning']['effort'],json.dumps(bad,ensure_ascii=False)))
        with patch.object(self.s,'open_request',side_effect=backend):result=self.s.review_one(run,plan,job)
        self.assertEqual('error',result['status']);self.assertEqual('transport_error',result['validation_status'])
        self.assertEqual(2,len(requests))

    def test_review_validation_hash_tamper_is_not_accepted_by_aggregate(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        self.execute_quote_review(run,plan,job,[bad,good])
        root=run/'reviews'/self.s.ident(dict(job,arm='blind'))
        (root/'attempts/0/validation.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'validation|evidence'):
            self.s.review_result(run,plan,job)
        self.assertEqual(0,self.s.aggregate(run)['valid_reviews'])

    def test_duplicate_json_decision_keys_are_not_repairable(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        raw=json.dumps(bad,ensure_ascii=False).replace('"meaning": "pass"','"meaning": "fail", "meaning": "pass"',1)
        result,requests=self.execute_quote_review(run,plan,job,[raw,good])
        self.assertEqual('schema_error',result['validation_status']);self.assertEqual(1,len(requests))

    def test_bad_quote_cannot_be_erased_to_whitespace(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        good['outputs']['A']['format']['evidence'][0]['output_quote']=' '
        result,requests=self.execute_quote_review(run,plan,job,[bad,good])
        self.assertEqual('error',result['status']);self.assertEqual(2,len(requests))
        self.assertEqual('locked_content_drift',result['validation_status'])

    def test_bad_nonempty_meaning_quote_cannot_be_erased_to_empty(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        bad=verdict();bad['outputs']['A']['meaning']='fail';bad['outputs']['A']['findings']=[{
            'source_quote':'원자료에 없는 인용','output_quote':'결과','reason':'원자료에 대한 기존 실패 판단이다.'}]
        erased=json.loads(json.dumps(bad));erased['outputs']['A']['findings'][0]['source_quote']=''
        result,requests=self.execute_quote_review(run,plan,job,[bad,erased])
        self.assertEqual('error',result['status']);self.assertEqual(2,len(requests))
        self.assertEqual('locked_content_drift',result['validation_status'])

    def test_originally_empty_addition_slot_is_valid_and_stays_locked(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        bad['outputs']['B']['meaning']='fail';bad['outputs']['B']['findings']=[{
            'source_quote':'','output_quote':'결과','reason':'추가 내용이라는 기존 판단이다.'}]
        good=json.loads(json.dumps(bad));good['outputs']['A']['format']['evidence'][0]['output_quote']='**문서로 확인한 사항**'
        result,requests=self.execute_quote_review(run,plan,job,[bad,good])
        self.assertEqual('completed',result['status'])
        self.assertEqual('',self.s.review_result(run,plan,job)[1]['outputs']['B']['findings'][0]['source_quote'])

    def test_original_whitespace_only_quote_is_schema_invalid_without_repair(self):
        run,plan,job,packet,bad,good=self.quote_review_fixture()
        bad['outputs']['A']['format']['evidence'][0]['output_quote']=' \n '
        result,requests=self.execute_quote_review(run,plan,job,[bad,good])
        self.assertEqual('schema_error',result['validation_status']);self.assertEqual(1,len(requests))

    def test_new_browser_recognizer_ambiguity_messages_are_infrastructure(self):
        parent=self.root
        errors=['Global tool reset controls are ambiguous','Transition buttons are ambiguous: start',
                'Current state is unknown or conflicting in observed state/status evidence']
        for index,error in enumerate(errors):
            with self.subTest(error=error):
                self.root=parent/str(index);self.root.mkdir()
                run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
                html='<html><body><input aria-label="a"><button>초기화</button></body></html>'
                directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,
                    inputs=[{'id':'a','type':'number','visible':True}],buttons=[{'text':'초기화','visible':True}])
                snapshot=receipt['initial_snapshot']
                receipt['actions']={name:{'status':'pass','observations':{'tested':True}}for name in receipt['actions']}
                receipt['actions']['reset']={'status':'fail','observations':{'error':error,'snapshot':snapshot}}
                with self.assertRaisesRegex(ValueError,'oracle|incomplete'):
                    self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)
        self.root=parent

    def test_explicit_recognizer_conflict_is_not_downgraded_by_empty_control_inventory(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body>관측 상태</body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html)
        receipt['actions']['initial']['observations']['error']='Current state is unknown or conflicting in observed state/status evidence'
        with self.assertRaisesRegex(ValueError,'oracle|incomplete'):
            self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html)

    def test_recognized_disabled_global_reset_stays_repairable_artifact_failure(self):
        run,_=self.fixture('tool-assisted-v1');plan=self.s.verify(run);job=self.assisted_job(run,'L3')
        html='<html><body><button disabled>전체 초기화</button></body></html>'
        directory,receipt=self.bound_failed_browser_receipt(run,plan,job,html,
            buttons=[{'text':'전체 초기화','visible':True,'disabled':True}])
        receipt['actions']={name:{'status':'pass','observations':{'tested':True}}for name in receipt['actions']}
        receipt['actions']['reset']={'status':'fail','observations':{
            'error':'Observed global tool reset is not visible and enabled','snapshot':receipt['initial_snapshot']}}
        self.assertFalse(self.s.validate_browser_receipt(run,plan,job,directory,receipt,html,html))


if __name__ == '__main__':
    unittest.main()
