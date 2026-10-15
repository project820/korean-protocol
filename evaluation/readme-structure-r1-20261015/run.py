#!/usr/bin/env python3
"""Two stateless profile-text arms; retain exact first responses, with no retries.

The profile-only arms form a matched comparison. Old full-dictionary outputs
are historical references, not a paired rule-effect comparison across scopes.
Neither profile-text arm proves installation or automatic retrieval behavior.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'evaluation/readme-model-comparison-20261015'
SPEC = importlib.util.spec_from_file_location('frozen_readme_runner', OLD / 'run.py')
old = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(old)
sha, TASK, frozen_file, extract = old.sha, old.TASK, old.frozen_file, old.extract
MODEL = old.MODEL
ARMS = ('baseline-profile', 'candidate-profile')
TOKEN_CEILING = 6000


def dump(path, value):
    with path.open('x', encoding='utf-8', newline='') as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_json(path):
    return json.loads(path.read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def request_body(case, arm):
    require(arm in ARMS, 'Unknown arm')
    profile = (frozen_file(old.KP_FILES[0]) if arm == 'baseline-profile'
               else (HERE / 'candidate-profile.md').read_bytes())
    materials = ['참조 파일: ' + old.KP_FILES[0] + '\n' + profile.decode('utf-8')]
    prompt = ('작성 지침과 참조 자료\n\n' + '\n\n'.join(materials)
              + '\n\n작업 요청\n' + TASK + '\n\n원문\n' + case['source'])
    return {'model': MODEL,
            'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}],
            'reasoning': {'effort': 'medium'}, 'store': False, 'stream': True, 'tools': []}


def encoded_request(case, arm):
    return json.dumps(request_body(case, arm), ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def old_artifact_hashes():
    names = ['run.py', 'plan.json', 'cases.json', 'ste-profile.md']
    names += [f'{folder}/{n:02}-{arm}.{suffix}'
              for folder, suffix in (('outputs', 'txt'), ('records', 'json'))
              for n in range(1, 7) for arm in ('kp', 'ste')]
    return {name: sha((OLD / name).read_bytes()) for name in names}


def validate_token_budget():
    raw = (HERE / 'token-budget.json').read_bytes()
    budget = json.loads(raw)
    require(budget.get('profile_sha256') == sha((HERE / 'candidate-profile.md').read_bytes()),
            'Token budget profile hash mismatch')
    require(budget.get('ceiling') == TOKEN_CEILING and budget.get('passed') is True
            and bool(budget.get('counters')), 'Candidate profile token budget has not passed')
    return raw


def candidate_budget_pass(usage):
    count = usage.get('input_tokens') if isinstance(usage, dict) else None
    return type(count) is int and 0 <= count <= TOKEN_CEILING


def validate_old():
    plan = read_json(OLD / 'plan.json')
    require(sha((OLD / 'run.py').read_bytes()) == plan['runner_sha256'], 'Old runner drift')
    require(sha((OLD / 'cases.json').read_bytes()) == plan['cases_sha256'], 'Old sources drift')
    require(plan['source_commit'] == old.SOURCE_COMMIT, 'Old source commit mismatch')
    require(plan['model_requested'] == MODEL and plan['effort'] == 'medium', 'Old model mismatch')
    require(plan['task'] == TASK and plan['conditions'] == ['kp', 'ste'], 'Old request mismatch')
    require(sha(frozen_file('README.md')) == plan['source_sha256'], 'Frozen README drift')
    require(all(sha(frozen_file(p)) == h for p, h in plan['kp_inputs'].items()),
            'Old profile or dictionary drift')
    cases = read_json(OLD / 'cases.json')
    require([case['id'] for case in cases] == [f'{n:02}' for n in range(1, 7)],
            'Expected six original cases')
    for case in cases:
        for arm in ('kp', 'ste'):
            name = case['id'] + '-' + arm
            record = read_json(OLD / 'records' / (name + '.json'))
            require(record['status'] == 'completed' and record['returned_model'] == MODEL,
                    'Old response status or model mismatch')
            require(record['source_sha256'] == sha(case['source'].encode('utf-8')),
                    'Old response source mismatch')
            require(record['output_sha256'] == sha((OLD / 'outputs' / (name + '.txt')).read_bytes()),
                    'Old output drift')
    return cases, plan


def prepare():
    cases, baseline = validate_old()
    candidate = (HERE / 'candidate-profile.md').read_bytes()
    criteria = (HERE / 'criteria.json').read_bytes()
    require(isinstance(json.loads(criteria), dict), 'Invalid acceptance criteria')
    token_budget = validate_token_budget()
    require(bool(candidate.decode('utf-8').strip()), 'Empty candidate profile')
    require(candidate != frozen_file(old.KP_FILES[0]), 'Candidate equals baseline profile')
    require(not any((HERE / name).exists() for name in
                    ('cases.json', 'plan.json', 'freeze.json', 'outputs', 'records')),
            'Preparation cannot overwrite existing evidence')
    plan = {
        'frozen_at': old.now(), 'source_commit': old.SOURCE_COMMIT,
        'source_count': 6, 'planned_calls': 12, 'samples_per_source_per_condition': 1,
        'conditions': list(ARMS), 'model_requested': MODEL, 'effort': 'medium',
        'temperature': 'provider default (not sent)', 'seed': 'not sent', 'task': TASK,
        'source_sha256': baseline['source_sha256'], 'cases_sha256': baseline['cases_sha256'],
        'runner_sha256': sha(Path(__file__).read_bytes()),
        'candidate_profile_sha256': sha(candidate), 'kp_inputs': baseline['kp_inputs'],
        'criteria_sha256': sha(criteria),
        'token_budget_sha256': sha(token_budget), 'candidate_input_token_ceiling': TOKEN_CEILING,
        'old_artifacts': old_artifact_hashes(), 'max_concurrency': 2, 'retry_count': 0,
        'request_sha256': {case['id'] + '-' + arm: sha(encoded_request(case, arm))
                           for case in cases for arm in ARMS},
        'pairing': {'baseline-profile': 'candidate-profile for the same source; only profile text differs'},
        'scope': {
            'baseline-profile': 'Released frozen profile text only; no dictionaries.',
            'candidate-profile': 'Candidate profile text only; no dictionaries.',
            'historical_reference': 'Old full-dictionary outputs remain unchanged historical references. Differences across full-dictionary and profile-only scopes do not establish paired causal effects of rule changes.',
            'limits': 'Profile-only arms are controlled text-load tests, not installed-profile, automatic retrieval, or product runtime proof.'},
        'isolation': 'One user message per call. No tools, previous responses, case titles, authored example outputs, CLI, AGENTS, memory, or installation state. Proxy/provider system defaults are outside this boundary.',
        'output_policy': 'Exact terminal output_text, including whitespace and semantic failures. No retry, repair, editing, or replacement. Invalid/incomplete/model-mismatched responses fail and retain private raw evidence.',
    }
    with (HERE / 'cases.json').open('xb') as file:
        file.write((OLD / 'cases.json').read_bytes())
    dump(HERE / 'plan.json', plan)
    dump(HERE / 'freeze.json', {'plan_sha256': sha((HERE / 'plan.json').read_bytes()),
                              'criteria_sha256': sha(criteria), 'token_budget_sha256': sha(token_budget)})
    verify(require_complete=False)
    return plan


def verify(require_complete=True):
    plan = read_json(HERE / 'plan.json')
    seal = read_json(HERE / 'freeze.json')
    require(sha((HERE / 'plan.json').read_bytes()) == seal['plan_sha256'],
            'Frozen plan drift')
    require(plan['criteria_sha256'] == seal['criteria_sha256'], 'Acceptance criteria seal mismatch')
    require(plan['token_budget_sha256'] == seal['token_budget_sha256'], 'Token budget seal mismatch')
    require(sha(Path(__file__).read_bytes()) == plan['runner_sha256'], 'Runner drift')
    require(sha((HERE / 'candidate-profile.md').read_bytes()) == plan['candidate_profile_sha256'],
            'Candidate profile drift')
    require(sha((HERE / 'criteria.json').read_bytes()) == plan['criteria_sha256'],
            'Acceptance criteria drift')
    require(sha(validate_token_budget()) == plan['token_budget_sha256'], 'Token budget drift')
    require(old_artifact_hashes() == plan['old_artifacts'], 'Old evidence drift')
    require(sha((HERE / 'cases.json').read_bytes()) == plan['cases_sha256'], 'Source drift')
    require(all(sha(frozen_file(p)) == h for p, h in plan['kp_inputs'].items()),
            'Frozen profile or dictionary drift')
    cases = read_json(HERE / 'cases.json')
    expected = {case['id'] + '-' + arm: (case, arm) for case in cases for arm in ARMS}
    require({name: sha(encoded_request(case, arm)) for name, (case, arm) in expected.items()}
            == plan['request_sha256'], 'Frozen request drift')
    if not require_complete:
        return cases, plan
    require({p.stem for p in (HERE / 'records').glob('*.json')} == set(expected),
            'Missing or unexpected response records')
    completed = set()
    budget_failures = []
    for name, (case, arm) in expected.items():
        record = read_json(HERE / 'records' / (name + '.json'))
        require(record['id'] == name and record['source_id'] == case['id']
                and record['condition'] == arm, 'Response label mismatch')
        require(record['request_sha256'] == plan['request_sha256'][name]
                and record['source_sha256'] == sha(case['source'].encode('utf-8')),
                'Response input mismatch')
        require(record['requested_model'] == MODEL and record['effort'] == 'medium'
                and record['retry_count'] == 0 and record['tools'] == []
                and record['previous_response_id_sent'] is False, 'Response isolation mismatch')
        if record['status'] == 'completed':
            completed.add(name)
            raw = (HERE / 'outputs' / (name + '.txt')).read_bytes()
            require(record['returned_model'] == MODEL and record['response_status'] == 'completed',
                    'Response model or terminal status mismatch')
            require(sha(raw) == record['output_sha256']
                    and len(raw.decode('utf-8')) == record['characters'], 'Output drift')
            if arm == 'candidate-profile':
                passed = candidate_budget_pass(record.get('usage'))
                require(record.get('token_budget_pass') is passed
                        and record.get('token_budget_ceiling') == TOKEN_CEILING,
                        'Candidate input token budget record mismatch')
                if not passed:
                    budget_failures.append(name)
        else:
            require(record['status'] == 'failed' and bool(record.get('error')), 'Invalid failure record')
    require({p.stem for p in (HERE / 'outputs').glob('*.txt')} == completed,
            'Missing or unexpected output files')
    require(len(completed) == 12, 'At least one request failed; retained records must not be replaced')
    require(not budget_failures, 'Candidate input token budget gate failed; raw outputs retained: '
            + ', '.join(budget_failures))
    return cases, plan


def extract_strict(raw):
    response, final = extract(raw)
    events = [json.loads(line[6:]) for line in raw.decode('utf-8').splitlines()
              if line.startswith('data: ') and line[6:] != '[DONE]']
    terminals = [event for event in events if event.get('type') in
                 ('response.completed', 'response.failed', 'response.incomplete')]
    require(len(terminals) == 1 and terminals[0]['type'] == 'response.completed',
            'Ambiguous or incomplete terminal event')
    require(not response.get('incomplete_details') and not response.get('error'),
            'Response reports truncation or error')
    items = response.get('output') or [event['item'] for event in events
                                       if event.get('type') == 'response.output_item.done']
    require(all(item.get('status', 'completed') == 'completed' for item in items),
            'Incomplete output item')
    require(not any(event.get('type') in ('error', 'response.error') or event.get('error')
                    for event in events), 'Stream reports an error')
    messages = [item for item in items if item.get('type') == 'message']
    require(len(messages) == 1 and messages[0].get('role') == 'assistant',
            'Unexpected extra message')
    require(all(item.get('type') in ('message', 'reasoning') for item in items),
            'Unexpected non-text output item')
    content = messages[0].get('content', [])
    require(len(content) == 1 and content[0].get('type') == 'output_text',
            'Unexpected extra message content')
    require(response.get('model') == MODEL, 'Returned model differs from requested model')
    return response, final


def execute(slot, private):
    case, arm = slot
    name = case['id'] + '-' + arm
    directory = private / name
    directory.mkdir(exist_ok=False)
    record = {'id': name, 'source_id': case['id'], 'condition': arm,
              'started_at': old.now(), 'requested_model': MODEL, 'effort': 'medium',
              'source_sha256': sha(case['source'].encode('utf-8')),
              'retry_count': 0, 'tools': [], 'previous_response_id_sent': False}
    start = time.monotonic()
    stage = 'request-validation'
    try:
        plan = read_json(HERE / 'plan.json')
        seal = read_json(HERE / 'freeze.json')
        require(sha((HERE / 'plan.json').read_bytes()) == seal['plan_sha256'],
                'Frozen plan drift before dispatch')
        require(plan['criteria_sha256'] == seal['criteria_sha256'], 'Acceptance criteria seal mismatch')
        require(plan['token_budget_sha256'] == seal['token_budget_sha256'], 'Token budget seal mismatch')
        require(sha((HERE / 'criteria.json').read_bytes()) == plan['criteria_sha256'],
                'Acceptance criteria drift before dispatch')
        require(sha(validate_token_budget()) == plan['token_budget_sha256'],
                'Token budget drift before dispatch')
        raw_request = encoded_request(case, arm)
        record['request_sha256'] = sha(raw_request)
        with (directory / 'request.json').open('xb') as file:
            file.write(raw_request)
        require(record['request_sha256'] == plan['request_sha256'][name],
                'Request drift before dispatch')
        stage = 'transport'
        request = urllib.request.Request(old.ENDPOINT, data=raw_request,
                                        headers={'Content-Type': 'application/json',
                                                 'Accept': 'text/event-stream'})
        with (directory / 'response.raw').open('xb') as file:
            try:
                response = urllib.request.urlopen(request, timeout=600)
            except urllib.error.HTTPError as error:
                record['http_status'] = error.code
                file.write(error.read())
                raise
            with response:
                record['http_status'] = response.status
                while True:
                    try:
                        chunk = response.read(65536)
                    except Exception as error:
                        partial = getattr(error, 'partial', None)
                        if isinstance(partial, bytes):
                            file.write(partial)
                        raise
                    if not chunk:
                        break
                    file.write(chunk)
        raw = (directory / 'response.raw').read_bytes()
        stage = 'terminal-validation'
        parsed, final = extract(raw)
        record.update(returned_model=parsed.get('model'), response_id=parsed.get('id'),
                      response_status=parsed.get('status'), usage=parsed.get('usage'))
        dump(directory / 'response.json', parsed)
        extract_strict(raw)
        stage = 'output-write'
        with (HERE / 'outputs' / (name + '.txt')).open('xb') as file:
            file.write(final.encode('utf-8'))
        record.update(status='completed', output_sha256=sha(final.encode('utf-8')),
                      characters=len(final),
                      fallback_observation='Response metadata names the requested model; upstream identity is not independently attested.')
        if arm == 'candidate-profile':
            record.update(token_budget_ceiling=TOKEN_CEILING,
                          token_budget_pass=candidate_budget_pass(parsed.get('usage')),
                          token_budget_basis='Returned usage.input_tokens for the complete request; missing usage fails the gate. Raw text remains unchanged.')
    except Exception as error:
        record.update(status='failed', error=type(error).__name__ + ' during ' + stage)
        dump(directory / 'error.json', {'type': type(error).__name__, 'message': str(error)})
    if (directory / 'response.raw').exists():
        record['response_sha256'] = sha((directory / 'response.raw').read_bytes())
    record.update(elapsed_seconds=round(time.monotonic() - start, 3), finished_at=old.now())
    dump(HERE / 'records' / (name + '.json'), record)
    print(name, record['status'], flush=True)
    return record


def run(private):
    cases, _ = verify(require_complete=False)
    require(not (HERE / 'outputs').exists() and not (HERE / 'records').exists()
            and not private.exists(), 'Run cannot overwrite existing evidence')
    private.mkdir(parents=True, exist_ok=False, mode=0o700)
    (HERE / 'outputs').mkdir(exist_ok=False)
    (HERE / 'records').mkdir(exist_ok=False)
    slots = [(case, arm) for case in cases for arm in ARMS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda slot: execute(slot, private), slots))
    verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'verify'])
    parser.add_argument('--private-evidence', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        print('Frozen six sources and two profile-only arms; no model calls made.')
    elif args.action == 'verify':
        verify()
        print('Verified frozen inputs, token budget and all 12 public records/outputs offline.')
    else:
        if args.private_evidence is None:
            parser.error('--private-evidence is required for run')
        run(args.private_evidence.resolve())


if __name__ == '__main__':
    main()
