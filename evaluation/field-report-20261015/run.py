#!/usr/bin/env python3
"""Private paired report study: prepare, run once, verify offline.

Before prepare, place source.md, criteria.json, claim-ledger.json and
token-budget.json in --study-dir. Only repository output/<private-directory>
or an external system temporary directory is accepted. Nothing is published.

Token-budget schema: profile_sha256, ceiling=6000, counters={name: count},
source_tokens={name: count}, model_probe={profile_sha256, model_requested,
effort, request_file, response_file, request_sha256, response_sha256}.
Counters measure core_prompt(candidate_text); source_tokens are separate.
The probe files must contain probe_request(...) and its actual SSE response.
All local core counts and actual minimal probe input_tokens must be <=6000.
Full report request usage is measured without applying this core-only limit.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import http.client
import ipaddress
import socket
import threading
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R1 = ROOT / 'evaluation/readme-structure-r1-20261015/run.py'
SPEC = importlib.util.spec_from_file_location('field_frozen_r1', R1)
frozen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frozen)
BASELINE = ROOT / 'evaluation/readme-structure-r2-20261015/candidate-profile.md'
BASELINE_SHA256 = '339b95abf9afce14298f326dc710fdf8816534844d6f4200b6faff90aa835023'
ARMS = ('baseline', 'candidate')
TOKEN_CEILING = 6000
TASK = frozen.TASK
sha, require, now = frozen.sha, frozen.require, frozen.old.now


def dump(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def write(path, raw):
    with path.open('xb') as file:
        file.write(raw)


def read_json(path):
    return json.loads(path.read_bytes())


def encoded(body):
    return json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def validate_study_dir(path):
    path = path.resolve()
    output = ROOT / 'output'
    # Ignore TMPDIR/TEMP/TMP: these can name a synced or public directory.
    temporary_roots = {Path(name).resolve() for name in ('/tmp', '/var/tmp')}
    if sys.platform == 'darwin':
        darwin_temp = subprocess.run(['/usr/bin/getconf', 'DARWIN_USER_TEMP_DIR'],
                                     check=True, capture_output=True, text=True, timeout=5).stdout.strip()
        if darwin_temp:
            temporary_roots.add(Path(darwin_temp).resolve())
    inside_output = path.is_relative_to(output) and path != output
    outside_repo_temp = any(path.is_relative_to(base) and path != base for base in temporary_roots)
    outside_repo_temp = outside_repo_temp and not path.is_relative_to(ROOT)
    require(inside_output or outside_repo_temp, 'Use a private study under output/<name> or external temporary directory')
    return path


def core_prompt(profile):
    return '작성 지침\n\n' + profile + '\n\n작업 요청\n' + TASK


def body(prompt, model, effort):
    return {'model': model,
            'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}],
            'reasoning': {'effort': effort}, 'store': False, 'stream': True, 'tools': []}


def probe_request(profile, model, effort):
    return encoded(body(core_prompt(profile.decode('utf-8')) + '\n\n토큰 확인 요청\n확인', model, effort))


def effort_identity(response, requested):
    returned = (response.get('reasoning') or {}).get('effort')
    return {'requested_effort': requested, 'returned_effort': returned,
            'effort_verification': ('unverified' if returned is None else
                                    'verified' if returned == requested else 'mismatch')}


def extract_strict(raw, model, effort=None):
    # A private module instance allows one fixed per-study model in concurrent calls.
    # The frozen r1 file and its historical model constant are never edited.
    frozen.MODEL = model
    response, final = frozen.extract_strict(raw)
    events = [json.loads(line[6:]) for line in raw.decode('utf-8').splitlines()
              if line.startswith('data: ') and line[6:] != '[DONE]']

    def validate_metadata(value):
        if isinstance(value, dict):
            if 'model' in value:
                require(value['model'] == model, 'Stream model differs from requested model')
            reasoning = value.get('reasoning')
            if isinstance(reasoning, dict) and 'effort' in reasoning:
                require(effort is None or reasoning['effort'] == effort,
                        'Returned effort differs from requested effort')
            kind = value.get('type', '')
            require(isinstance(kind, str), 'Invalid stream item type')
            require(not any('tool' in part or part.endswith('_call') or part == 'function_call'
                            for part in kind.split('.')), 'Unexpected tool event or item')
            for key, child in value.items():
                if 'fallback' in key.lower():
                    require(not child, 'Response reports fallback routing')
                validate_metadata(child)
        elif isinstance(value, list):
            for child in value:
                validate_metadata(child)

    validate_metadata(events)
    return response, final


def local_file(study, name):
    path = (study / name).resolve()
    require(path.is_relative_to(study) and path != study, 'Evidence file escapes private study')
    return path


def validate_token_budget(study, candidate, model, effort):
    budget = read_json(study / 'token-budget.json')
    profile_hash = sha(candidate)
    require(budget.get('profile_sha256') == profile_hash and budget.get('ceiling') == TOKEN_CEILING,
            'Token budget profile hash or ceiling mismatch')
    counters = budget.get('counters')
    require(isinstance(counters, dict) and bool(counters)
            and all(type(n) is int and 0 <= n <= TOKEN_CEILING for n in counters.values()),
            'Every local core token counter must pass 6000')
    source_counts = budget.get('source_tokens')
    require(isinstance(source_counts, dict) and bool(source_counts)
            and all(type(n) is int and n >= 0 for n in source_counts.values()),
            'Report source token counts separately')
    probe = budget.get('model_probe', {})
    require(probe.get('profile_sha256') == profile_hash
            and probe.get('model_requested') == model and probe.get('effort') == effort,
            'Actual token probe profile or model/effort mismatch')
    request = local_file(study, probe['request_file']).read_bytes()
    raw = local_file(study, probe['response_file']).read_bytes()
    require(request == probe_request(candidate, model, effort)
            and sha(request) == probe.get('request_sha256')
            and sha(raw) == probe.get('response_sha256'), 'Actual token probe request/response mismatch')
    response, final = extract_strict(raw, model, effort)
    count = (response.get('usage') or {}).get('input_tokens')
    require(type(count) is int and 0 <= count <= TOKEN_CEILING,
            'Actual minimal core token probe exceeds 6000 or has no usage')
    return {'counters': counters, 'source_tokens': source_counts,
            'probe_effort_identity': effort_identity(response, effort),
            'probe_output': final, 'probe_usage': response['usage'],
            'probe_files': {probe['request_file']: sha(request), probe['response_file']: sha(raw)}}


def runner_artifacts():
    return {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
            (Path(__file__).resolve(), R1, frozen.OLD / 'run.py')}


def request_for(study, arm, model, effort):
    profile = (study / 'inputs' / (arm + '.md')).read_bytes().decode('utf-8')
    source = (study / 'inputs/source.md').read_bytes().decode('utf-8')
    return encoded(body(core_prompt(profile) + '\n\n원문\n' + source, model, effort))


def prepare(study, candidate, model, effort):
    study = validate_study_dir(study)
    candidate = candidate.resolve()
    require(bool(model.strip()) and bool(effort.strip()), 'Specify exact model and effort')
    require(not any((study / name).exists() for name in
                    ('plan.json', 'freeze.json', 'inputs', 'requests', 'run', 'records', 'outputs')),
            'Preparation cannot overwrite existing evidence')
    candidate_bytes = candidate.read_bytes()
    baseline = BASELINE.read_bytes()
    require(sha(baseline) == BASELINE_SHA256, 'Frozen r2 baseline drift')
    require(bool(candidate_bytes.decode('utf-8').strip()) and candidate_bytes != baseline,
            'Candidate must contain the entire nonempty distinct skill')
    materials = {name: (study / name).read_bytes()
                 for name in ('source.md', 'criteria.json', 'claim-ledger.json', 'token-budget.json')}
    require(bool(materials['source.md'].decode('utf-8').strip()), 'Empty report source')
    for name in ('criteria.json', 'claim-ledger.json'):
        require(isinstance(json.loads(materials[name]), (dict, list)), 'Invalid ' + name)
    budget = validate_token_budget(study, candidate_bytes, model, effort)
    study.chmod(0o700)
    (study / 'inputs').mkdir(mode=0o700)
    (study / 'requests').mkdir(mode=0o700)
    for name, raw in {**materials, 'baseline.md': baseline, 'candidate.md': candidate_bytes}.items():
        write(study / 'inputs' / name, raw)
    requests = {}
    for repeat in (1, 2):
        for arm in ARMS:
            name = f'{repeat:02}-{arm}'
            raw = request_for(study, arm, model, effort)
            write(study / 'requests' / (name + '.json'), raw)
            requests[name] = {'sha256': sha(raw), 'bytes': len(raw), 'arm': arm, 'repeat': repeat}
    plan = {'frozen_at': now(), 'runner_artifacts': runner_artifacts(),
            'baseline_path': str(BASELINE.relative_to(ROOT)), 'baseline_sha256': BASELINE_SHA256,
            'candidate_path': str(candidate), 'model_requested': model, 'effort': effort,
            'task': TASK, 'planned_calls': 4, 'repeats_per_arm': 2, 'conditions': list(ARMS),
            'source_model': 'unknown; historical user-supplied output',
            'input_sha256': {path.name: sha(path.read_bytes()) for path in (study / 'inputs').iterdir()},
            'token_budget': budget, 'core_token_ceiling': TOKEN_CEILING,
            'requests': requests, 'max_concurrency': 2, 'timeout_seconds': 600, 'retry_count': 0,
            'isolation': 'One user message, entire profile, identical neutral task and original source; no tools, prior answers/history, hidden references, criteria or claim ledger.',
            'scope': 'Controlled instruction-text comparison; installed skill loading and upstream model identity are not independently attested.',
            'output_policy': 'Exact terminal output_text retained, including semantic failures; invalid transport/model/status responses fail without replacement.',
            'budget_basis': 'Full candidate skill plus wrapper; source tokens and full generation usage are separate nonblocking measurements.'}
    dump(study / 'plan.json', plan)
    dump(study / 'freeze.json', {'plan_sha256': sha((study / 'plan.json').read_bytes())})
    verify(study, require_complete=False, for_dispatch=True)
    return plan


def verify(study, require_complete=True, archived_runner=None, for_dispatch=False):
    study = validate_study_dir(study)
    plan = read_json(study / 'plan.json')
    require(sha((study / 'plan.json').read_bytes()) == read_json(study / 'freeze.json')['plan_sha256'],
            'Frozen plan drift')
    artifacts = dict(runner_artifacts())
    if archived_runner is not None:
        require(not for_dispatch, 'Archived runner is verify-only')
        # Hash the retained bytes only; never import or execute historical code.
        artifacts[str(Path(__file__).resolve().relative_to(ROOT))] = sha(archived_runner.read_bytes())
    require(artifacts == plan['runner_artifacts'], 'Runner/parser drift')
    require(sha(BASELINE.read_bytes()) == plan['baseline_sha256'] == BASELINE_SHA256,
            'Frozen r2 baseline drift')
    if for_dispatch:
        require(sha(Path(plan['candidate_path']).read_bytes()) == plan['input_sha256']['candidate.md'],
                'Candidate skill drift')
    for name, expected in plan['input_sha256'].items():
        require(sha((study / 'inputs' / name).read_bytes()) == expected, 'Frozen input drift: ' + name)
        if name not in ('baseline.md', 'candidate.md'):
            require(sha((study / name).read_bytes()) == expected, 'Study input drift: ' + name)
    budget = validate_token_budget(study, (study / 'inputs/candidate.md').read_bytes(),
                                   plan['model_requested'], plan['effort'])
    if archived_runner is not None and 'probe_effort_identity' not in plan['token_budget']:
        budget.pop('probe_effort_identity')
    require(budget == plan['token_budget'], 'Token probe evidence drift')
    for name, slot in plan['requests'].items():
        raw = (study / 'requests' / (name + '.json')).read_bytes()
        require(sha(raw) == slot['sha256'] and len(raw) == slot['bytes']
                and raw == request_for(study, slot['arm'], plan['model_requested'], plan['effort']),
                'Frozen request drift: ' + name)
    if not require_complete:
        return plan
    expected = set(plan['requests'])
    require({p.stem for p in (study / 'records').glob('*.json')} == expected,
            'Missing or unexpected response records')
    completed = set()
    failed = []
    for name in expected:
        record = read_json(study / 'records' / (name + '.json'))
        require(record['id'] == name and record['request_sha256'] == plan['requests'][name]['sha256']
                and record['requested_model'] == plan['model_requested'] and record['effort'] == plan['effort']
                and record['retry_count'] == 0, 'Response record input mismatch')
        directory = study / 'run' / name
        require({path.name: sha(path.read_bytes()) for path in directory.iterdir()}
                == record['artifact_sha256'], 'Private response artifact drift')
        raw_path = directory / 'response.raw'
        if raw_path.exists():
            require(sha(raw_path.read_bytes()) == record['response_sha256'], 'Raw response drift')
        if record['status'] == 'completed':
            response, final = extract_strict(raw_path.read_bytes(), plan['model_requested'], plan['effort'])
            identity = effort_identity(response, plan['effort'])
            if archived_runner is None:
                require(all(record.get(key) == value for key, value in identity.items()),
                        'Response effort metadata drift')
            output = final.encode('utf-8')
            require((study / 'outputs' / (name + '.txt')).read_bytes() == output
                    and (directory / 'output.txt').read_bytes() == output
                    and sha(output) == record['output_sha256']
                    and response.get('usage') == record.get('usage'), 'Exact output or usage drift')
            completed.add(name)
        else:
            require(record['status'] == 'failed' and bool(record.get('error')), 'Invalid failure record')
            failed.append(name)
    require({p.stem for p in (study / 'outputs').glob('*.txt')} == completed, 'Output inventory mismatch')
    require(not failed, 'Requests failed; retained evidence cannot be replaced: ' + ', '.join(sorted(failed)))
    return plan


def retain_terminal(directory, raw, record):
    """Retain terminal text even when strict status/identity validation will fail."""
    events = [json.loads(line[6:]) for line in raw.decode('utf-8').splitlines()
              if line.startswith('data: ') and line[6:] != '[DONE]']
    terminals = [event['response'] for event in events if event.get('type') in
                 ('response.completed', 'response.failed', 'response.incomplete')]
    if not terminals:
        return
    parsed = terminals[-1]
    dump(directory / 'response.json', parsed)
    record.update(effort_identity(parsed, record['effort']))
    record.update(returned_model=parsed.get('model'), response_status=parsed.get('status'),
                  response_id=parsed.get('id'), usage=parsed.get('usage'))
    items = parsed.get('output') or [event['item'] for event in events
                                    if event.get('type') == 'response.output_item.done']
    parts = [part['text'] for item in items if item.get('type') == 'message'
             for part in item.get('content', []) if part.get('type') == 'output_text']
    if len(parts) == 1 and isinstance(parts[0], str):
        write(directory / 'output.txt', parts[0].encode('utf-8'))


def transfer(endpoint, request_bytes, file, record, timeout):
    """POST directly to literal HTTP loopback under one total transport deadline."""
    url = urlsplit(endpoint)
    require(url.scheme == 'http' and url.hostname is not None
            and url.username is None and url.password is None and not url.fragment,
            'Endpoint must use direct HTTP loopback')
    try:
        loopback = ipaddress.ip_address(url.hostname).is_loopback
    except ValueError:
        loopback = False
    require(loopback, 'Endpoint must use literal loopback')
    require(isinstance(timeout, (int, float)) and timeout > 0, 'Invalid transport deadline')
    deadline = time.monotonic() + timeout
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)
    connected = None
    response = None
    expired = threading.Event()

    def expire():
        expired.set()
        if connected is not None:
            try:
                # close alone does not interrupt a socket makefile blocked on headers/trailers.
                connected.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        connection.connect()
        connected = connection.sock  # Keep this reference even if HTTPConnection detaches it.
        require(not expired.is_set() and time.monotonic() < deadline, 'Request deadline exceeded')
        connection.request('POST', url.path + ('?' + url.query if url.query else ''),
                           body=request_bytes,
                           headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
        response = connection.getresponse()
        record['http_status'] = response.status
        while True:
            try:
                chunk = response.read1(65536)
            except Exception as error:
                partial = getattr(error, 'partial', None)
                if isinstance(partial, bytes):
                    file.write(partial)
                raise
            if chunk:
                file.write(chunk)
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError('Request deadline exceeded')
            if not chunk:
                if response.length not in (None, 0):
                    raise http.client.IncompleteRead(b'', response.length)
                break
        require(response.status == 200, 'Unexpected HTTP status')
    except Exception as error:
        if expired.is_set() or time.monotonic() >= deadline:
            raise TimeoutError('Request deadline exceeded') from error
        raise
    finally:
        timer.cancel()
        timer.join()
        if response is not None:
            response.close()
        connection.close()
        if connected is not None:
            connected.close()


def execute(study, name):
    directory = study / 'run' / name
    directory.mkdir(mode=0o700, exist_ok=False)
    plan = read_json(study / 'plan.json')
    record = {'id': name, 'requested_model': plan['model_requested'], 'effort': plan['effort'],
              'request_sha256': plan['requests'][name]['sha256'], 'retry_count': 0,
              'started_at': now(), 'tools': [], 'previous_response_id_sent': False,
              **effort_identity({}, plan['effort'])}
    started = time.monotonic()
    try:
        verify(study, require_complete=False, for_dispatch=True)
        request_bytes = (study / 'requests' / (name + '.json')).read_bytes()
        with (directory / 'response.raw').open('xb') as file:
            transfer(frozen.old.ENDPOINT, request_bytes, file, record, plan['timeout_seconds'])
        raw = (directory / 'response.raw').read_bytes()
        # Preserve extractable terminal text even if strict identity validation fails.
        retain_terminal(directory, raw, record)
        parsed, final = extract_strict(raw, plan['model_requested'], plan['effort'])
        write(study / 'outputs' / (name + '.txt'), final.encode('utf-8'))
        record.update(status='completed', output_sha256=sha(final.encode('utf-8')),
                      characters=len(final), full_request_input_tokens=(parsed.get('usage') or {}).get('input_tokens'))
    except Exception as error:
        record.update(status='failed', error=type(error).__name__)
        dump(directory / 'error.json', {'type': type(error).__name__, 'message': str(error)})
    if (directory / 'response.raw').exists():
        record['response_sha256'] = sha((directory / 'response.raw').read_bytes())
    record['artifact_sha256'] = {path.name: sha(path.read_bytes()) for path in directory.iterdir()}
    record.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - started, 3))
    dump(study / 'records' / (name + '.json'), record)
    print(name, record['status'], flush=True)
    return record


def run(study):
    study = validate_study_dir(study)
    plan = verify(study, require_complete=False, for_dispatch=True)
    require(not any((study / folder).exists() for folder in ('run', 'outputs', 'records')),
            'Run cannot overwrite existing evidence')
    for folder in ('run', 'outputs', 'records'):
        (study / folder).mkdir(mode=0o700, exist_ok=False)
    with ThreadPoolExecutor(max_workers=plan['max_concurrency']) as pool:
        list(pool.map(lambda name: execute(study, name), plan['requests']))
    return verify(study)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'verify'))
    parser.add_argument('--study-dir', type=Path, required=True)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--model')
    parser.add_argument('--effort')
    parser.add_argument('--archived-runner', type=Path, help='Verify-only retained runner bytes; never executed')
    args = parser.parse_args()
    if args.archived_runner is not None and args.action != 'verify':
        parser.error('--archived-runner is accepted only for verify')
    if args.action == 'prepare':
        if not all((args.candidate, args.model, args.effort)):
            parser.error('prepare requires --candidate, --model and --effort')
        prepare(args.study_dir, args.candidate, args.model, args.effort)
        print('Frozen four private requests; no generation calls made.')
    else:
        plan = verify(args.study_dir, require_complete=False, archived_runner=args.archived_runner,
                      for_dispatch=args.action == 'run')
        require(args.model is None or args.model == plan['model_requested'], 'Requested model differs from plan')
        require(args.effort is None or args.effort == plan['effort'], 'Requested effort differs from plan')
        require(args.candidate is None or args.candidate.resolve() == Path(plan['candidate_path']),
                'Requested candidate differs from plan')
        run(args.study_dir) if args.action == 'run' else verify(args.study_dir, archived_runner=args.archived_runner)
        probe = read_json(args.study_dir / 'inputs/token-budget.json')['model_probe']
        probe_response, _ = extract_strict(local_file(args.study_dir.resolve(), probe['response_file']).read_bytes(),
                                           plan['model_requested'], plan['effort'])
        print('token-probe', json.dumps(effort_identity(probe_response, plan['effort'])))
        for path in sorted((args.study_dir / 'run').glob('*/response.json')):
            print(path.parent.name, json.dumps(effort_identity(read_json(path), plan['effort'])))
        print('Verified frozen private study evidence.')


if __name__ == '__main__':
    main()
