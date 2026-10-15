#!/usr/bin/env python3
"""Run fixed README sources through two stateless OpenCodex conditions.

No CLI, user config, prior messages, tools, authored answers, retries or repairs.
Wire requests/responses stay in a private evidence directory. Public outputs are
exact output_text bytes; metadata records their hashes and the model response.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_COMMIT = '9b2508c2113549c6e3b6d65a9d2af1ec9f6e8a18'
MODEL = 'anthropic/claude-opus-5-5'
ENDPOINT = 'http://127.0.0.1:10100/v1/responses'
KP_FILES = ('profiles/coding-agent.md', 'lexicon/core.json', 'lexicon/domains/software.json')
TASK = ('다음 원문을 제공한 작성 지침에 따라 한국어로 정리해줘. '
        '사실·조건·수치·기한·행위 주체·의무·자동 처리·확실성은 유지해줘. '
        '정리한 본문만 출력하고 설명이나 자기 평가는 덧붙이지 마.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, data):
    with path.open('x', encoding='utf-8') as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def frozen_file(path):
    return subprocess.check_output(['git', 'show', SOURCE_COMMIT + ':' + path], cwd=ROOT)


def freeze():
    source = frozen_file('README.md').decode('utf-8')
    table = source[source.index('<table>'):source.index('</table>') + len('</table>')]
    titles = re.findall(r'<a id="([^"]+)"></a>(\d+)\. ([^<]+)</th>', table)
    rows = re.findall(r'<tr>\s*<td valign="top">(.*?)</td>', table, re.S)
    if len(rows) != 6 or len(titles) != 6 or any('<' in row for row in rows):
        raise ValueError('Expected exactly six plain source cells in frozen README')
    cases = [dict(id=f'{int(n):02}', title=title, anchor=anchor, source=html.unescape(row))
             for (anchor, n, title), row in zip(titles, rows)]
    dump(HERE / 'cases.json', cases)
    plan = {
        'frozen_at': now(), 'source_commit': SOURCE_COMMIT, 'source_path': 'README.md',
        'source_sha256': sha(frozen_file('README.md')),
        'cases_sha256': sha((HERE / 'cases.json').read_bytes()),
        'model_requested': MODEL, 'effort': 'medium', 'temperature': 'provider default (not sent)',
        'seed': 'not sent', 'samples_per_source_per_condition': 1, 'planned_calls': 12,
        'source_count': 6, 'conditions': ['kp', 'ste'], 'task': TASK,
        'kp_inputs': {path: sha(frozen_file(path)) for path in KP_FILES},
        'ste_profile_sha256': sha((HERE / 'ste-profile.md').read_bytes()),
        'runner_sha256': sha(Path(__file__).read_bytes()),
        'output_policy': 'Keep first completed response unchanged, including semantic failures; no automatic retry.',
        'isolation': 'Each request contains one user message, its condition and one source. No CLI, tools, memory, AGENTS, prior responses or authored example answers are loaded. Provider system defaults and proxy translation are outside this boundary.',
        'scope': 'KP coding-agent profile and both complete dictionaries are supplied as text. This is a controlled prompt test, not an installation or on-demand dictionary retrieval test. STE is a Korean adaptation of public principles, not full English-standard conformance.',
        'review_policy': 'Compare every source proposition in both directions, including conditions, scope, actor, deadlines, modality, automatic actions and uncertainty. Keep review separate from outputs.'}
    dump(HERE / 'plan.json', plan)
    return cases, plan


def request_body(case, condition):
    if condition == 'kp':
        profile = '\n\n'.join('참조 파일: ' + path + '\n' + frozen_file(path).decode('utf-8')
                              for path in KP_FILES)
    elif condition == 'ste':
        profile = (HERE / 'ste-profile.md').read_text(encoding='utf-8')
    else:
        raise ValueError('Unknown condition')
    prompt = '작성 지침과 참조 자료\n\n' + profile + '\n\n작업 요청\n' + TASK + '\n\n원문\n' + case['source']
    return {'model': MODEL, 'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}],
            'reasoning': {'effort': 'medium'}, 'store': False, 'stream': True, 'tools': []}


def extract(raw):
    events = []
    for line in raw.decode('utf-8').splitlines():
        if line.startswith('data: ') and line[6:] != '[DONE]':
            events.append(json.loads(line[6:]))
    terminal = [event['response'] for event in events
                if event.get('type') in ('response.completed', 'response.failed', 'response.incomplete')]
    if not terminal:
        raise ValueError('No terminal response event')
    response = terminal[-1]
    if response.get('status') != 'completed':
        raise ValueError('Response not completed: ' + str(response.get('status')))
    outputs = response.get('output') or [e['item'] for e in sorted(
        (e for e in events if e.get('type') == 'response.output_item.done'),
        key=lambda e: e['output_index'])]
    messages = [o for o in outputs if o.get('type') == 'message' and o.get('role') == 'assistant']
    parts = [c['text'] for o in messages for c in o.get('content', []) if c.get('type') == 'output_text']
    if len(messages) != 1 or len(parts) != 1 or not parts[0].strip():
        raise ValueError('Expected one nonempty assistant output_text, without postprocessing')
    return response, parts[0]


def execute(slot, private):
    case, condition = slot
    name = case['id'] + '-' + condition
    directory = private / name
    directory.mkdir(parents=True, exist_ok=False)
    raw_request = json.dumps(request_body(case, condition), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    (directory / 'request.json').write_bytes(raw_request)
    record = {'id': name, 'source_id': case['id'], 'condition': condition,
              'started_at': now(), 'requested_model': MODEL, 'effort': 'medium',
              'request_sha256': sha(raw_request), 'source_sha256': sha(case['source'].encode()),
              'retry_count': 0, 'tools': [], 'previous_response_id_sent': False}
    start = time.monotonic()
    try:
        req = urllib.request.Request(ENDPOINT, data=raw_request,
                                     headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
        with urllib.request.urlopen(req, timeout=600) as response:
            record['http_status'] = response.status
            raw = response.read()
        (directory / 'response.raw').write_bytes(raw)
        record['response_sha256'] = sha(raw)
        parsed, final = extract(raw)
        dump(directory / 'response.json', parsed)
        if parsed.get('model') != MODEL:
            record['returned_model'] = parsed.get('model')
            raise ValueError('Returned model differs from requested model')
        record.update(returned_model=parsed.get('model'), response_id=parsed.get('id'),
                      status=parsed.get('status'), usage=parsed.get('usage'),
                      output_sha256=sha(final.encode('utf-8')), characters=len(final),
                      fallback_observation='No model substitution in response metadata; upstream identity is not independently attested.')
        with (HERE / 'outputs' / (name + '.txt')).open('xb') as file:
            file.write(final.encode('utf-8'))
    except Exception as exc:
        record['status'] = 'failed'
        record['error'] = type(exc).__name__ + ': ' + str(exc)
    record['elapsed_seconds'] = round(time.monotonic() - start, 3)
    record['finished_at'] = now()
    dump(HERE / 'records' / (name + '.json'), record)
    print(name, record['status'], record.get('characters'), record.get('error', ''), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'run'])
    parser.add_argument('--private-evidence', type=Path)
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze()
        print('Frozen six README sources and two conditions; no model calls made.')
        return
    if args.private_evidence is None:
        parser.error('--private-evidence is required for run')
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
    plan = json.loads((HERE / 'plan.json').read_text(encoding='utf-8'))
    assert sha((HERE / 'cases.json').read_bytes()) == plan['cases_sha256']
    assert sha(Path(__file__).read_bytes()) == plan['runner_sha256']
    assert sha((HERE / 'ste-profile.md').read_bytes()) == plan['ste_profile_sha256']
    assert all(sha(frozen_file(p)) == h for p, h in plan['kp_inputs'].items())
    (HERE / 'outputs').mkdir(exist_ok=False)
    (HERE / 'records').mkdir(exist_ok=False)
    args.private_evidence.mkdir(parents=True, exist_ok=False)
    slots = [(case, condition) for case in cases for condition in ('kp', 'ste')]
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda slot: execute(slot, args.private_evidence), slots))
    if any(row['status'] != 'completed' for row in records):
        raise SystemExit('At least one request failed; inspect records without replacing successful outputs.')


if __name__ == '__main__':
    main()
