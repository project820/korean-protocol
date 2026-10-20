#!/usr/bin/env python3
"""Immutable three-arm output-format experiment; no model, effort or retry fallback.

Run ``python -m evaluation.output_formats.study --help``. Candidate-only freezing
precedes held-out authoring. Every network attempt receives its own directory;
rerunning a command skips existing attempts, including failed attempts. A new
experiment directory is required to retry them. Tool-assisted runs execute HTML
inside the offline browser verifier; Manim code receives static inspection only.
"""
import argparse
import base64
import concurrent.futures
import hashlib
import itertools
import json
import os
import random
import re
import shlex
import signal
import struct
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

MODELS = ('gpt-6.1-sol', 'anthropic/claude-opus-5-5')
EFFORTS = ('medium', 'high', 'xhigh')
ARMS = ('baseline', 'candidate', 'ste')
REPETITIONS = 2
REVIEW_EFFORT = 'high'
ENDPOINT = 'http://127.0.0.1:10100/v1/responses'
MAX_OUTPUT_TOKENS = 64000
COMMON = ('제공 자료와 작업 요청을 근거로 결과물을 한국어로 작성하라. '
          '사실·출처·주체·범위·조건·예외·수치·시간·의무·가능·미확인을 보존하라. '
          '실행하지 않은 코드와 렌더링을 실행하거나 확인했다고 쓰지 마라. '
          '자료에 없는 사실·실행 결과를 추가하지 마라. 작성 과정과 자기 평가는 붙이지 마라. '
          '도구를 사용할 수 없다. 요청된 코드와 스크립트는 본문에 포함하라.')
CONTRACTS = {
    'L1': '텍스트·문단·목록·번호 있는 절차로 작성하라. Markdown 제목·강조·인라인 코드 표기를 허용한다. '
          '개별 작업 요청이 이러한 표기를 명시적으로 제한하면 그 제한을 우선한다. '
          '표·도식·HTML·애니메이션은 만들지 마라.',
    'L2': '정적 Markdown 표 또는 Mermaid/ASCII 도식으로 설명하라. 의미를 유지하는 짧은 본문을 함께 쓸 수 있다.',
    'L3': '네트워크 없이 실행되는 단일 HTML/CSS/JavaScript 설명 도구를 하나의 html 코드 블록으로 제공하라. '
          '조작 상태·조건·결과·초기화 동작을 구현하고 한국어 표시를 사용하라. 외부 CDN과 API를 사용하지 마라.',
    'L4': '명시적으로 요청된 Manim Python 애니메이션 소스를 python 코드 블록으로 제공하라. '
          '각 장면의 동일한 장면 ID를 코드와 한국어 내레이션 스크립트 양쪽에 표시하고 장면 시간을 함께 제공하라. '
          '외부 네트워크 없이 렌더링할 수 있도록 작성하고 실행·렌더링 완료를 주장하지 마라.',
}
RUBRIC = '''원자료와 출력 A·B·C를 같은 기준으로 양방향 검토한다. 외부 지식으로 원자료를 보충하지 않는다.
의미 보존은 사실·출처·주체·범위·조건·예외·수치·시간 기산점·기한·의무·가능·미확인을 검사한다.
표·도식·UI 코드·시뮬레이션 상태·애니메이션·내레이션의 주장도 원자료와 대조한다. 도구 실행은 하지 않는다.
출력의 문맥·인용·질문·유보와 절의 수식 관계를 먼저 읽는다. 전언과 미확인을 확정 사실로 바꾸면 실패다.
자료에 없는 중요한 주장이나 요청 범위의 중요한 누락은 실패다. 입증되지 않은 해석은 unresolved로 기록한다.
명료성은 핵심 판단·대상 목록·제약의 선행 배치, 조건별 묶음, 시간 기산점·기한·예외, 독립 속성, 중복을 검사한다.
핵심 조건·판단·행동을 정확히 찾는 용이성을 비교한다. 문장 길이·불릿·표의 유무 자체를 점수로 삼지 않는다.
의미 오류와 명료성 비교를 분리한다. 더 명시적이어도 근거 없는 주장을 장점으로 삼지 않는다.
형식은 공통 표현 계약과 작업 요청으로 검토한다. 실제 브라우저·Manim 실행 여부는 판정하지 않는다.
L1의 Markdown 제목·강조·인라인 코드 표기는 개별 작업에서 명시적으로 제한하지 않았으면 허용한다. 허용된 표기의 존재만으로 형식을 실패·미해결로 판정하지 않는다.
경고는 금지·조건의 내용과 강도, 관련 행동 앞의 배치로 판단한다. 원자료나 작업 요청이 특정 표지를 요구하지 않으면 문자 그대로의 ‘주의’ 같은 고정 표제를 추가 요건으로 삼지 않는다. 명시된 표지와 보호 문자열의 보존 요구는 그대로 적용한다.
작업이 분리 방법을 명시적으로 지정하지 않으면 독립된 행·문단·목록 항목으로 대상·출처·확인 상태를 분명히 구분하고 근거 없는 공통 귀속을 만들지 않은 배치를 허용한다. 별도 표나 별도 열은 명시적으로 요구됐을 때만 필수다. 실제로 대상·출처·상태를 구분할 수 없거나 잘못 묶었으면 실패 또는 미해결로 기록한다. 허용된 분리 방식 사이의 배치 선호는 명료성에서 비교하며 새 형식 제약으로 삼지 않는다.
JSON만 반환한다. outputs의 각 A/B/C는 {"meaning":"pass|fail|unresolved","findings":[{"source_quote":"정확한 원문 인용 또는 추가 오류이면 빈 문자열","output_quote":"정확한 출력 인용 또는 누락이면 빈 문자열","reason":"구체적 설명"}]} 형식이다.
pass이면 findings는 빈 배열이다. fail/unresolved이면 findings에 최소 한 건과 비어 있지 않은 정확한 인용을 넣는다.
pairs는 A-B,A-C,B-C 각 한 건이다. 각 항목은 {"left":"A","right":"B","winner":"A|B|tie","reason":"정보 탐색을 설명하는 구체적 비교","evidence":[{"label":"A","quote":"A의 정확한 인용"},{"label":"B","quote":"B의 정확한 인용"}]} 형식이다.
각 비교에는 양쪽 출력의 비어 있지 않은 정확한 인용을 남긴다. 뜻이 같고 명료성 우열이 없으면 tie로 기록한다.
각 outputs 항목에는 format도 추가한다. format은 {"status":"pass|fail|unresolved","evidence":[{"output_quote":"정확한 출력 인용","reason":"표현 계약의 어느 요구와 대응하거나 충돌하는지"}],"scene_correspondence":[]} 형식이다.
형식 판정은 의미 판정과 분리한다. L4의 pass에는 scene_correspondence에 모든 장면별 {"scene_id":"공통 장면 ID","code_quote":"ID를 포함하는 정확한 코드 인용","narration_quote":"동일 ID를 포함하는 정확한 코드 밖 내레이션 인용","reason":"내용·순서·시간의 대응 검토"}를 남긴다. 코드와 내레이션 대응을 확인할 수 없으면 format은 unresolved다.
전체 형식은 {"outputs":{"A":...,"B":...,"C":...},"pairs":[...]}이다.'''
ACCEPTANCE = {
    'candidate_meaning': 'all development and evaluation outputs pass',
    'clarity': 'candidate wins > losses against each control in every held-out model/effort cohort',
    'completeness': 'all three arms, repetitions, generations, reviews and preflight valid',
    'installation': 'quality, separate media and separate host evidence all pass',
    'effort_evidence': 'explicit mismatch fails; absent echo is unknown, not backend verification',
}
METHODS = ('single-shot', 'tool-assisted-v1')
TOOL_POLICY = {
    'schema': 'shared-diagnostics/v1', 'max_revisions': 2,
    'max_output_tokens_per_call': MAX_OUTPUT_TOKENS,
    'max_output_tokens_per_generation': MAX_OUTPUT_TOKENS * 3,
    'html_timeout_seconds': 60, 'browser_timeout_seconds': 120,
    'repair_trigger': ['issues_found', 'review_required'],
    'selection': 'first diagnostics pass; otherwise last permitted raw output; never best-of',
    'errors': 'transport or tool infrastructure error ends the chain incomplete without retry',
    'availability': 'identical frozen checker and browser for all arms; no semantic review feedback',
    'scope': 'L1/L2 applicable static inspection only; L3 HTML and browser; L4 AST only; no semantic proof',
}
TOOL_COMMON = ('검증 도구는 모든 작성 지침에 같은 조건으로 적용된다. '
               'HTML 정적 검사·오프라인 브라우저 검사와 해당 형식의 정적 검사 결과를 제공받을 수 있다. '
               '검사에서 오류나 검토 사항을 찾으면 최대 두 번 결과물 전체를 스스로 수정한다. '
               '검사 결과도 원자료의 사실을 추가하는 근거가 아니다. 원자료의 보호 문자열을 검사 통과를 위해 바꾸지 마라. '
               '원자료·작업·작성 지침과 실제 검사 결과만 사용하라. 다른 작성 지침의 출력과 의미 평가는 제공하지 않는다.')
REVISION_COMMON = ('자기 수정 기회다. 아래 이전 원시 출력과 실제 형식 검사 결과를 검토하고 결과물 전체를 다시 작성하라. '
                   '원자료의 의미·조건·보호 문자열과 원래 작업 범위를 유지하라. '
                   '진단을 없애기 위해 근거를 삭제하거나 미확인 사실과 실행 결과를 만들지 마라. '
                   '수정 설명과 자기 평가는 붙이지 마라.')
REVIEW_POLICY = {
    'schema': 'exact-quote-repair/v1', 'max_corrections': 2,
    'max_output_tokens_per_call': MAX_OUTPUT_TOKENS,
    'max_output_tokens_per_review': MAX_OUTPUT_TOKENS * 3,
    'eligibility': 'complete valid original structure and decisions; only exact-quote string mismatches',
    'locks': 'every other parsed field, reason, list count/order, object order and all valid quotes',
    'selection': 'first fully valid correction; valid fail/unresolved are terminal without correction',
    'errors': 'malformed JSON, schema error, content drift, transport error or exhausted corrections stay incomplete',
}
QUOTE_CORRECTION_COMMON = ('기술적 인용 정정만 수행하라. 원래 판단·승자·이유·식별자·필드·항목 수와 순서를 바꾸지 마라. '
                           '아래 허용 JSON 경로의 잘못된 인용 문자열만 원자료 또는 해당 출력의 정확한 연속 문자열로 정정하라. '
                           '다른 인용은 이미 유효하므로 변경하지 마라. 새로운 의미·형식·명료성 판단을 하지 마라. '
                           '전체 JSON을 같은 키와 항목 순서로 반환하고 설명을 덧붙이지 마라.')


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)


def dump(path, value):
    save(path, encode(value))


def canonical_id(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())


def safe_path(root, name):
    root = Path(root).resolve()
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('unsafe evidence path: ' + str(name))
    path = root / relative
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        raise ValueError('unsafe evidence path: ' + str(name))
    return path


def snapshot(root, destination, selected=None):
    root, destination = Path(root).resolve(), Path(destination)
    if not root.is_dir():
        raise ValueError('bundle root must be a directory')
    names = sorted(selected) if selected is not None else sorted(
        p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and '.DS_Store' not in p.parts)
    if not names:
        raise ValueError('empty profile bundle')
    files = {}
    for name in names:
        data = safe_path(root, name).read_bytes()
        digest = sha(data)
        if selected is not None and selected[name] != digest:
            raise ValueError('source hash drift: ' + name)
        save(safe_path(destination, name), data)
        files[name] = digest
    return files


def freeze_candidate(run_dir, candidate_root, candidate_files=None):
    run_dir = Path(run_dir)
    if (run_dir / 'candidate-freeze.json').exists() or (run_dir / 'plan.json').exists():
        raise FileExistsError('candidate already frozen; use a new run directory')
    files = snapshot(candidate_root, run_dir / 'frozen/candidate', candidate_files)
    result = {'created': now(), 'candidate_id': canonical_id(files), 'files': files}
    dump(run_dir / 'candidate-freeze.json', result)
    return result


def prompt_inventory(files):
    """Keep package provenance complete while loading only the routed skill guidance."""
    skills = [name for name in files if Path(name).name == 'SKILL.md']
    if len(skills) != 1:
        raise ValueError('profile requires exactly one SKILL.md')
    prefix = str(Path(skills[0]).parent)
    prefix = '' if prefix == '.' else prefix + '/'
    inventory = {}
    for modality in CONTRACTS:
        selected = []
        for name in sorted(files):
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix):]
            if relative == 'SKILL.md':
                selected.append(name)
            elif relative.startswith(('references/', 'assets/')):
                if relative in ('references/interactive-html.md', 'assets/interactive-explainer.html'):
                    if modality == 'L3':
                        selected.append(name)
                elif relative == 'references/video-script.md':
                    if modality == 'L4':
                        selected.append(name)
                else:
                    selected.append(name)
        inventory[modality] = selected
    return inventory


def _timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return result


def validate_dataset(dataset, frozen_at):
    if _timestamp(dataset.get('evaluation_authored_at', '')) <= _timestamp(frozen_at):
        raise ValueError('held-out evaluation must be authored after candidate freeze')
    seen, ids = set(), set()
    for split in ('development', 'evaluation'):
        cases = dataset.get(split)
        if not isinstance(cases, list) or len(cases) != 12:
            raise ValueError(split + ' must contain exactly 12 cases')
        for case in cases:
            for field in ('id', 'source', 'task', 'modality', 'mode'):
                if not isinstance(case.get(field), str) or not case[field].strip():
                    raise ValueError(split + ': missing ' + field)
            if not case['id'].replace('-', '').replace('_', '').isalnum():
                raise ValueError('case ID must be path-safe')
            if case['id'] in ids:
                raise ValueError('duplicate case ID')
            ids.add(case['id'])
            source = ' '.join(unicodedata.normalize('NFKC', case['source']).split())
            if source in seen:
                raise ValueError('duplicate normalized source or source overlap')
            seen.add(source)
            if case['modality'] not in CONTRACTS or case['mode'] not in ('rewrite', 'compose'):
                raise ValueError('invalid modality or mode')
        if any(sum(c['modality'] == level for c in cases) != 3 for level in CONTRACTS):
            raise ValueError(split + ' requires three cases per modality')
        if sum(c['mode'] == 'rewrite' for c in cases) != 6:
            raise ValueError(split + ' requires six rewrite and six compose cases')


def freeze(run_dir, baseline, ste, provenance, dataset, method='single-shot', tools=None):
    run_dir = Path(run_dir)
    if (run_dir / 'plan.json').exists():
        raise FileExistsError('plan already frozen; use a new run directory')
    candidate = read(run_dir / 'candidate-freeze.json')
    data = read(dataset)
    validate_dataset(data, candidate['created'])
    if method not in METHODS:
        raise ValueError('unknown evaluation method')
    origin = read(provenance)
    if any(not origin.get(key) for key in ('source', 'edition', 'rules', 'korean_application')):
        raise ValueError('STE provenance requires source, edition, rules and korean_application')
    baseline_files = snapshot(baseline, run_dir / 'frozen/baseline')
    save(run_dir / 'frozen/ste/profile.md', Path(ste).read_bytes())
    save(run_dir / 'frozen/ste/provenance.json', Path(provenance).read_bytes())
    save(run_dir / 'frozen/dataset.json', Path(dataset).read_bytes())
    save(run_dir / 'frozen/study.py', Path(__file__).read_bytes())
    from evaluation.output_formats import media
    save(run_dir / 'frozen/media.py', Path(media.__file__).read_bytes())
    if method == 'tool-assisted-v1':
        if not tools or set(tools) != {'html_checker', 'browser_checker', 'oracle'}:
            raise ValueError('tool-assisted method requires HTML checker, browser checker and source-bound oracle')
        for key, name in [('html_checker', 'check_html.py'), ('browser_checker', 'browser_check.mjs'), ('oracle', 'oracle.json')]:
            save(run_dir / 'frozen/tools' / name, Path(tools[key]).read_bytes())
        validate_oracle(read(run_dir / 'frozen/tools/oracle.json'), data, sha(Path(dataset).read_bytes()))
    files = {p.relative_to(run_dir).as_posix(): sha(p.read_bytes())
             for p in sorted((run_dir / 'frozen').rglob('*')) if p.is_file()}
    files['candidate-freeze.json'] = sha((run_dir / 'candidate-freeze.json').read_bytes())
    common = COMMON if method == 'single-shot' else COMMON.replace('도구를 사용할 수 없다.', TOOL_COMMON)
    plan = {'created': now(), 'candidate': candidate, 'baseline_files': baseline_files, 'method': method,
            'review_policy': REVIEW_POLICY, 'quote_correction_common': QUOTE_CORRECTION_COMMON,
            'tool_policy': TOOL_POLICY if method == 'tool-assisted-v1' else None,
            'revision_common': REVISION_COMMON if method == 'tool-assisted-v1' else None,
            'prompt_files': {'candidate': prompt_inventory(candidate['files']),
                             'baseline': prompt_inventory(baseline_files)},
            'models': list(MODELS), 'efforts': list(EFFORTS), 'arms': list(ARMS),
            'repetitions': REPETITIONS, 'review_effort': REVIEW_EFFORT,
            'max_output_tokens': MAX_OUTPUT_TOKENS, 'endpoint': ENDPOINT,
            'auth_mode': 'existing Codex login in memory for Sol only; reject redirects',
            'common': common, 'contracts': CONTRACTS, 'rubric': RUBRIC,
            'acceptance': ACCEPTANCE, 'dataset': data, 'files': files,
            'expected_generations': len(MODELS) * len(EFFORTS) * 24 * REPETITIONS * len(ARMS),
            'expected_reviews': len(MODELS) * len(EFFORTS) * 24 * REPETITIONS,
            'ste_provenance': origin,
            'heldout_policy': 'synthetic held-out cases; no human-reader evidence; a changed candidate requires fresh held-out sources'}
    dump(run_dir / 'plan.json', plan)
    save(run_dir / 'plan.sha256', (sha((run_dir / 'plan.json').read_bytes()) + '\n').encode())
    return plan


def verify(run_dir):
    run_dir = Path(run_dir)
    plan = read(run_dir / 'plan.json')
    if (run_dir / 'plan.sha256').read_text().strip() != sha((run_dir / 'plan.json').read_bytes()):
        raise ValueError('plan hash drift')
    for name, digest in plan['files'].items():
        if sha(safe_path(run_dir, name).read_bytes()) != digest:
            raise ValueError('frozen hash drift: ' + name)
    if sha(Path(__file__).read_bytes()) != plan['files']['frozen/study.py']:
        raise ValueError('runner hash drift; execute frozen runner or start new run')
    from evaluation.output_formats import media
    if sha(Path(media.__file__).read_bytes()) != plan['files']['frozen/media.py']:
        raise ValueError('media inspector hash drift')
    method = plan.get('method', 'single-shot')
    if method not in METHODS or plan.get('tool_policy') != (TOOL_POLICY if method == 'tool-assisted-v1' else None):
        raise ValueError('tool method/policy drift')
    if plan.get('revision_common') != (REVISION_COMMON if method == 'tool-assisted-v1' else None):
        raise ValueError('revision instructions drift')
    if plan.get('review_policy') != REVIEW_POLICY or plan.get('quote_correction_common') != QUOTE_CORRECTION_COMMON:
        raise ValueError('technical review policy drift')
    common = COMMON if method == 'single-shot' else COMMON.replace('도구를 사용할 수 없다.', TOOL_COMMON)
    if any(plan.get(key) != expected for key, expected in (
        ('models', list(MODELS)), ('efforts', list(EFFORTS)), ('arms', list(ARMS)),
        ('repetitions', REPETITIONS), ('max_output_tokens', MAX_OUTPUT_TOKENS),
        ('review_effort', REVIEW_EFFORT), ('endpoint', ENDPOINT), ('common', common),
        ('contracts', CONTRACTS), ('rubric', RUBRIC), ('acceptance', ACCEPTANCE))):
        raise ValueError('frozen policy drift')
    candidate = read(run_dir / 'candidate-freeze.json')
    if candidate != plan['candidate'] or canonical_id(candidate['files']) != candidate['candidate_id']:
        raise ValueError('candidate hash drift')
    if plan['prompt_files'] != {'candidate': prompt_inventory(candidate['files']),
                                'baseline': prompt_inventory(plan['baseline_files'])}:
        raise ValueError('prompt inventory drift')
    if read(run_dir / 'frozen/dataset.json') != plan['dataset']:
        raise ValueError('dataset drift')
    validate_dataset(plan['dataset'], candidate['created'])
    if method == 'tool-assisted-v1':
        validate_oracle(read(run_dir / 'frozen/tools/oracle.json'), plan['dataset'],
                        sha((run_dir / 'frozen/dataset.json').read_bytes()))
    return plan


def validate_oracle(oracle, dataset, dataset_hash):
    if oracle.get('dataset_sha256') != dataset_hash:
        raise ValueError('tool oracle dataset hash mismatch')
    expected = {case['id']: sha(case['source'].encode()) for split in ('development', 'evaluation')
                for case in dataset[split] if case['modality'] == 'L3'}
    if set(oracle.get('cases', {})) != set(expected) or any(
            oracle['cases'][name].get('source_sha256') != digest for name, digest in expected.items()):
        raise ValueError('tool oracle source coverage/hash mismatch')


def jobs(plan, split=None):
    for part in ([split] if split else ['development', 'evaluation']):
        for mi, effort, case, repetition, arm in itertools.product(
                range(len(MODELS)), EFFORTS, plan['dataset'][part], range(REPETITIONS), ARMS):
            yield {'split': part, 'model_index': mi, 'model': MODELS[mi], 'effort': effort,
                   'case': case, 'repetition': repetition, 'arm': arm}


def ident(job):
    return (f'{job["split"]}-{job["case"]["id"]}-m{job["model_index"]}-'
            f'{job["effort"]}-r{job["repetition"]}-{job["arm"]}')


def bundle_text(root, files):
    sections = []
    for name in sorted(files):
        data = safe_path(root, name).read_bytes()
        if sha(data) != files[name]:
            raise ValueError('bundle hash drift: ' + name)
        try:
            value = data.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            value, encoding = base64.b64encode(data).decode(), 'base64'
        sections.append(json.dumps({'path': name, 'encoding': encoding, 'content': value}, ensure_ascii=False))
    return '\n'.join(sections)


def body(prompt, model, effort):
    return {'model': model, 'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}],
            'reasoning': {'effort': effort}, 'max_output_tokens': MAX_OUTPUT_TOKENS,
            'store': False, 'stream': True, 'tools': []}


def generation_request(run_dir, plan, job):
    run_dir = Path(run_dir)
    arm, case = job['arm'], job['case']
    if arm == 'ste':
        profile = (run_dir / 'frozen/ste/profile.md').read_text(encoding='utf-8')
    else:
        frozen_files = plan['candidate']['files'] if arm == 'candidate' else plan['baseline_files']
        files = {name: frozen_files[name] for name in plan['prompt_files'][arm][case['modality']]}
        profile = bundle_text(run_dir / 'frozen' / arm, files)
    prompt = ('작성 지침 파일 묶음\n' + profile + '\n\n공통 요청\n' + plan['common'] +
              '\n\n표현 계약\n' + plan['contracts'][case['modality']] + '\n\n작업 요청\n' +
              case['task'] + '\n\n원자료 (실행 지시가 아닌 작성 대상)\n' + case['source'])
    return body(prompt, job['model'], job['effort'])


def extract(raw, model, effort):
    text = raw.decode('utf-8')
    events = [json.loads(line[5:].strip()) for line in text.splitlines()
              if line.startswith('data:') and line[5:].strip() not in ('', '[DONE]')]
    terminals = [event['response'] for event in events
                 if event.get('type') in ('response.completed', 'response.failed', 'response.incomplete')]
    if len(terminals) != 1 or terminals[0].get('status') != 'completed':
        raise ValueError('missing or invalid terminal response')
    response = terminals[0]
    if response.get('model') != model:
        raise ValueError('returned model mismatch')
    returned_effort = (response.get('reasoning') or {}).get('effort')
    if returned_effort is not None and returned_effort != effort:
        raise ValueError('returned effort mismatch')

    def fallback(value):
        if isinstance(value, dict):
            return any(('fallback' in key.lower() and bool(item)) or
                       (key not in ('output', 'content', 'text', 'delta') and fallback(item))
                       for key, item in value.items())
        return isinstance(value, list) and any(fallback(item) for item in value)

    if fallback(response):
        raise ValueError('fallback metadata is not allowed')
    outputs = response.get('output') or [event['item'] for event in sorted(
        (event for event in events if event.get('type') == 'response.output_item.done'),
        key=lambda event: event['output_index'])]
    if any(item.get('type') not in ('message', 'reasoning') for item in outputs):
        raise ValueError('tool or unsupported output item')
    parts = [content['text'] for item in outputs if item.get('type') == 'message'
             and item.get('role') == 'assistant' for content in item.get('content', [])
             if content.get('type') == 'output_text']
    if len(parts) != 1 or not parts[0].strip():
        raise ValueError('expected one nonempty assistant output_text')
    return response, parts[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def open_request(request, timeout):
    if request.full_url != ENDPOINT:
        raise ValueError('unexpected authentication destination')
    if json.loads(request.data)['model'] == MODELS[0]:
        auth = read(Path.home() / '.codex/auth.json')
        token = (auth.get('tokens') or {}).get('access_token')
        if not isinstance(token, str) or not token:
            raise ValueError('existing Codex login unavailable')
        request.add_unredirected_header('Authorization', 'Bearer ' + token)
    # Proxy settings are inherited. Authentication never follows a redirect.
    return urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout)


def call(directory, request, timeout=300):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    raw_request = encode(request)
    save(directory / 'request.json', raw_request)
    record = {'started': now(), 'request_sha256': sha(raw_request),
              'requested_model': request['model'], 'requested_effort': request['reasoning']['effort'],
              'returned_model': None, 'returned_effort': None, 'effort_evidence': 'unknown', 'retry_count': 0}
    started = time.monotonic()
    deadline = started + timeout
    # Open raw evidence before connecting so failed connections also leave an artifact.
    with (directory / 'response.raw').open('xb') as raw_file:
        try:
            req = urllib.request.Request(ENDPOINT, data=raw_request,
                                         headers={'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
            with open_request(req, min(timeout, 30)) as response:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('total response deadline')
                    # HTTPResponse.read1 performs one socket read; bound it by remaining total time.
                    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                    if sock is not None:
                        sock.settimeout(min(30, remaining))
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    raw_file.write(chunk)
                    raw_file.flush()
            raw_file.flush()
            response_data, output = extract((directory / 'response.raw').read_bytes(),
                                            request['model'], request['reasoning']['effort'])
            save(directory / 'output.md', output.encode('utf-8'))
            returned_effort = (response_data.get('reasoning') or {}).get('effort')
            record.update(status='completed', output_sha256=sha(output.encode('utf-8')),
                          returned_model=response_data.get('model'), returned_effort=returned_effort,
                          effort_evidence='echoed' if returned_effort is not None else 'unknown',
                          usage=response_data.get('usage'))
        except urllib.error.HTTPError as error:
            raw_file.write(error.read(65536))
            record.update(status='error', error=f'HTTPError: {error.code}')
        except Exception as error:
            # Exception strings can contain transport details; persist only the type and a local category.
            record.update(status='error', error=type(error).__name__,
                          failure_category='transport_or_response_validation')
    record.update(response_sha256=sha((directory / 'response.raw').read_bytes()), finished=now(),
                  seconds=round(time.monotonic() - started, 3))
    dump(directory / 'record.json', record)
    return record


def validate_catalog(catalog):
    rows = catalog.get('data') if isinstance(catalog, dict) else catalog
    models = {row['id']: row for row in rows}
    for model in MODELS:
        row = models.get(model, {})
        efforts = {item['value'] if isinstance(item, dict) else item
                   for item in row.get('reasoning_efforts', row.get('capabilities', {}).get('reasoning_effort', []))}
        if not set(EFFORTS).issubset(efforts) or 'responses' not in row.get('api_types', []):
            raise ValueError('catalog does not support model/effort/responses: ' + model)
    return True


def record_valid(directory, expected_request):
    directory = Path(directory)
    record = read(directory / 'record.json')
    if record.get('status') != 'completed' or record.get('retry_count') != 0:
        raise ValueError('failed or retried attempt')
    for name, key in [('request.json', 'request_sha256'), ('response.raw', 'response_sha256'),
                      ('output.md', 'output_sha256')]:
        if sha((directory / name).read_bytes()) != record.get(key):
            raise ValueError('attempt hash drift: ' + name)
    if read(directory / 'request.json') != expected_request:
        raise ValueError('request condition mismatch')
    response, output = extract((directory / 'response.raw').read_bytes(),
                               expected_request['model'], expected_request['reasoning']['effort'])
    returned = (response.get('reasoning') or {}).get('effort')
    if (output.encode('utf-8') != (directory / 'output.md').read_bytes() or
            record.get('requested_model') != expected_request['model'] or
            record.get('requested_effort') != expected_request['reasoning']['effort'] or
            record.get('returned_model') != response['model'] or
            record.get('returned_effort') != returned or
            record.get('effort_evidence') != ('echoed' if returned is not None else 'unknown')):
        raise ValueError('response/record linkage drift')
    return record


def revision_request(run_dir, plan, job, previous_output, diagnostics):
    original = generation_request(run_dir, plan, job)['input'][0]['content'][0]['text']
    prompt = (original + '\n\n' + REVISION_COMMON + '\n\n이전 원시 출력\n' + previous_output +
              '\n\n실제 형식 검사 결과 (원자료와 별도)\n' + json.dumps(diagnostics['feedback'], ensure_ascii=False))
    return body(prompt, job['model'], job['effort'])


def _run_tool(directory, command, timeout):
    """Run a frozen diagnostic, retaining partial bytes on every exit path."""
    directory.mkdir(parents=True, exist_ok=False)
    dump(directory / 'command.json', {'command': command, 'timeout_seconds': timeout})
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    save(directory / 'stdout.raw', stdout)
    save(directory / 'stderr.raw', stderr)
    result = {'exit_code': process.returncode, 'timed_out': timed_out,
              'seconds': round(time.monotonic() - started, 3),
              'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)}
    dump(directory / 'process.json', result)
    return result


def _process_evidence(directory, command, timeout):
    if read(directory / 'command.json') != {'command': command, 'timeout_seconds': timeout}:
        raise ValueError('diagnostic command/policy drift')
    result = read(directory / 'process.json')
    for name in ('stdout', 'stderr'):
        if sha((directory / (name + '.raw')).read_bytes()) != result[name + '_sha256']:
            raise ValueError('diagnostic process output hash drift')
    if result['timed_out']:
        raise ValueError('diagnostic infrastructure timeout')
    return result


def protected_source_text(case):
    values = case.get('protected_text', [])
    if not isinstance(values, list) or any(not isinstance(value, str) or not value or value not in case['source'] or value == case['source'] for value in values):
        raise ValueError('protected text must be exact nonempty source members')
    # Inline literals preserve their exact spaces. The entire source is never an allowlist.
    return sorted(set(values + re.findall(r'`([^`]+)`', case['source'])))


def _browser_snapshot_complete(snapshot):
    viewport = snapshot.get('viewport', {}) if isinstance(snapshot, dict) else {}
    return (isinstance(snapshot, dict) and isinstance(snapshot.get('body'), str) and
            all(isinstance(snapshot.get(name), list) for name in ('inputs', 'buttons', 'results')) and
            all(isinstance(viewport.get(name), (int, float)) and viewport[name] > 0
                for name in ('width', 'height', 'scroll_width')))


def _observed_controls_absent(snapshot, html_text):
    """An observed empty native UI is a repairable defect; custom UI stays unknown."""
    if not _browser_snapshot_complete(snapshot):
        return False
    controls = snapshot['inputs'] + snapshot['buttons']
    if any(not isinstance(item, dict) or not isinstance(item.get('visible'), bool) for item in controls):
        return False
    if any(item['visible'] for item in controls):
        return False
    # These surfaces are outside the native-control inventory. Their absence from
    # that inventory is not proof that the requested interaction is missing.
    custom_surface = (r'<(?:canvas|svg|iframe|object|embed|details|summary)\b|<\w+-[\w-]+\b|'
                      r'<a\b[^>]*\bhref\s*=|\bcontenteditable\b|\bcustomElements\b|\battachShadow\b|'
                      r'\bgetContext\b|\b(?:role|tabindex)\s*=|\bon[a-z][a-z0-9_]*\s*=')
    return re.search(custom_surface, html_text, re.I) is None


def validate_browser_receipt(run_dir, plan, job, directory, receipt, html_text, output_text):
    """Require source-bound real probes and static captures, never a pass flag alone."""
    root = Path(run_dir)
    directory = Path(directory)
    expected = {'tool': 'playwright', 'case_id': job['case']['id'],
                'output_sha256': sha(output_text.encode()), 'html_sha256': sha(html_text.encode()),
                'verifier_sha256': plan['files']['frozen/tools/browser_check.mjs'],
                'dataset_sha256': plan['files']['frozen/dataset.json'],
                'source_sha256': sha(job['case']['source'].encode()),
                'oracle_sha256': plan['files']['frozen/tools/oracle.json']}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError('browser receipt tool/case/source/oracle binding mismatch')
    actions = receipt.get('actions', {})
    if set(actions) != {'initial', 'change', 'invalid', 'reset', 'narrow', 'keyboard'} or any(
            item.get('status') not in ('pass', 'fail') or not item.get('observations') for item in actions.values()):
        raise ValueError('browser required probes are incomplete')
    if not isinstance(receipt.get('console_errors'), list) or not isinstance(receipt.get('blocked_requests'), list):
        raise ValueError('browser error/request evidence missing')
    if receipt.get('observations'):
        raise ValueError('browser infrastructure or oracle failure')
    for key in ('initial_snapshot', 'final_snapshot'):
        if not _browser_snapshot_complete(receipt.get(key)):
            raise ValueError('browser runtime snapshots missing or incomplete')
    infrastructure_markers = ('Cannot unambiguously identify', 'cannot be identified',
                              'not unambiguously recognized', 'option is ambiguous', 'no unambiguous execute')
    explicit_ambiguity = ('Global tool reset controls are ambiguous',
                          'Transition buttons are ambiguous: ',
                          'Current state is unknown or conflicting in observed state/status evidence')
    for item in actions.values():
        observation = item['observations']
        if not isinstance(observation, dict):
            continue
        error = str(observation.get('error', ''))
        # An explicit recognizer conflict is unknown even if its inventory is empty.
        if any(error.startswith(marker) for marker in explicit_ambiguity):
            raise ValueError('browser oracle recognition is ambiguous; incomplete, not self-repair feedback')
        if any(marker in error for marker in infrastructure_markers):
            if not _observed_controls_absent(observation.get('snapshot'), html_text):
                raise ValueError('browser oracle could not identify the output UI; incomplete, not self-repair feedback')
    static_link = receipt.get('static_visible_text', {})
    if static_link.get('javascript_enabled') is not False:
        raise ValueError('browser static JS-disabled capture missing')
    static = json.loads(hashed_artifact(directory, static_link))
    if (static.get('javascript_enabled') is not False or static.get('html_sha256') != expected['html_sha256'] or
            not isinstance(static.get('body'), str) or not isinstance(static.get('title'), str)):
        raise ValueError('browser static capture linkage mismatch')
    validate_png(hashed_artifact(directory, static['screenshot']))
    validate_png(hashed_artifact(directory, receipt['screenshot']))
    passing = (not receipt['console_errors'] and not receipt['blocked_requests'] and
               all(item['status'] == 'pass' for item in actions.values()))
    if receipt.get('status') != ('pass' if passing else 'fail'):
        raise ValueError('browser status disagrees with actual probes')
    return passing


def _diagnostic_report(run_dir, plan, job, attempt, execute=False):
    from evaluation.output_formats import media
    run_dir, attempt = Path(run_dir), Path(attempt)
    verify_tool_files(run_dir, plan)
    directory = attempt / 'diagnostics'
    output = (attempt / 'output.md').read_text(encoding='utf-8')
    inspection = media.inspect_output(job['case']['modality'], output)
    if execute:
        directory.mkdir(parents=True, exist_ok=False)
        dump(directory / 'static.json', inspection)
    elif read(directory / 'static.json') != inspection:
        raise ValueError('diagnostic static result drift')
    findings = [{'tool': 'static', 'severity': 'error', 'message': text} for text in inspection['findings']]
    infrastructure = []
    tools = []
    if job['case']['modality'] == 'L3':
        try:
            code = media.extract_html(output)
        except ValueError:
            code = None
        if code is not None:
            if execute:
                save(directory / 'artifact.html', code.encode())
                dump(directory / 'protected.json', protected_source_text(job['case']))
            elif ((directory / 'artifact.html').read_bytes() != code.encode() or
                    read(directory / 'protected.json') != protected_source_text(job['case'])):
                raise ValueError('diagnostic artifact/protected source drift')
            command = [sys.executable, str(run_dir / 'frozen/tools/check_html.py'), str(directory / 'artifact.html'),
                       '--language', 'ko', '--protected-text', str(directory / 'protected.json')]
            if execute:
                try:
                    _run_tool(directory / 'html', command, TOOL_POLICY['html_timeout_seconds'])
                except OSError as error:
                    dump(directory / 'html-launch-error.json', {'error': type(error).__name__})
            try:
                process = _process_evidence(directory / 'html', command, TOOL_POLICY['html_timeout_seconds'])
                result = read(directory / 'html/stdout.raw')
                if (result.get('schema_version') != 1 or result.get('sha256') != sha(code.encode()) or
                        result.get('language') != 'ko' or result.get('file') != str(directory / 'artifact.html')):
                    raise ValueError('HTML diagnostic source binding mismatch')
                status = result.get('status')
                if (status not in ('no_findings', 'issues_found', 'review_required') or
                        process['exit_code'] != (0 if status == 'no_findings' else 1)):
                    raise ValueError('HTML diagnostic process/schema failure')
                diagnostics = result.get('diagnostics')
                if not isinstance(diagnostics, list) or any(item.get('severity') not in ('error', 'review', 'info') for item in diagnostics):
                    raise ValueError('HTML diagnostic findings schema failure')
                findings.extend({'tool': 'html', **item} for item in diagnostics)
                if status != 'no_findings' and not any(item['severity'] in ('error', 'review') for item in diagnostics):
                    raise ValueError('HTML status lacks supporting diagnostics')
                if status == 'no_findings' and any(item['severity'] in ('error', 'review') for item in diagnostics):
                    raise ValueError('HTML no-findings status contradicts diagnostics')
                tools.append({'tool': 'html', 'status': status})
            except (OSError, ValueError, KeyError, TypeError) as error:
                infrastructure.append({'tool': 'html', 'error': type(error).__name__})
            # A broken checker is infrastructure failure, not feedback for another model attempt.
            if not infrastructure:
                browser_dir = directory / 'browser'
                command = ['node', str(run_dir / 'frozen/tools/browser_check.mjs'), '--html', str(directory / 'artifact.html'),
                           '--case', job['case']['id'], '--output', str(browser_dir), '--output-sha256', sha(output.encode()),
                           '--dataset', str(run_dir / 'frozen/dataset.json'), '--oracle', str(run_dir / 'frozen/tools/oracle.json')]
                if execute:
                    try:
                        _run_tool(directory / 'browser-process', command, TOOL_POLICY['browser_timeout_seconds'])
                    except OSError as error:
                        dump(directory / 'browser-launch-error.json', {'error': type(error).__name__})
                try:
                    process = _process_evidence(directory / 'browser-process', command, TOOL_POLICY['browser_timeout_seconds'])
                    receipt = read(browser_dir / 'receipt.json')
                    passing = validate_browser_receipt(run_dir, plan, job, browser_dir, receipt, code, output)
                    if process['exit_code'] != (0 if passing else 1):
                        raise ValueError('browser process/receipt mismatch')
                    tools.append({'tool': 'browser', 'status': 'pass' if passing else 'issues_found'})
                    for name, action in receipt['actions'].items():
                        if action['status'] != 'pass':
                            findings.append({'tool': 'browser', 'severity': 'error', 'code': name,
                                             'observations': action['observations']})
                    for error in receipt['console_errors'] + receipt['blocked_requests']:
                        findings.append({'tool': 'browser', 'severity': 'error', 'observations': error})
                except (OSError, ValueError, KeyError, TypeError) as error:
                    infrastructure.append({'tool': 'browser', 'error': type(error).__name__})
    status = ('error' if infrastructure else 'issues_found' if any(item['severity'] == 'error' for item in findings)
              else 'review_required' if any(item['severity'] == 'review' for item in findings) else 'pass')
    artifacts = {p.relative_to(directory).as_posix(): sha(p.read_bytes()) for p in sorted(directory.rglob('*'))
                 if p.is_file() and p.name != 'report.json'}
    return {'schema': 'generation-diagnostics/v1', 'output_sha256': sha(output.encode()),
            'policy_sha256': sha(encode(plan['tool_policy'])), 'status': status,
            'tools': tools, 'infrastructure_errors': infrastructure, 'artifacts': artifacts,
            'feedback': {'scope': TOOL_POLICY['scope'], 'status': status, 'findings': findings}}


def collect_diagnostics(run_dir, plan, job, attempt):
    result = _diagnostic_report(run_dir, plan, job, attempt, execute=True)
    dump(Path(attempt) / 'diagnostics/report.json', result)
    return result


def verify_tool_files(run_dir, plan):
    for name in ('check_html.py', 'browser_check.mjs', 'oracle.json'):
        relative = 'frozen/tools/' + name
        if sha(safe_path(run_dir, relative).read_bytes()) != plan['files'].get(relative):
            raise ValueError('frozen diagnostic tool hash drift: ' + name)


def assisted_generate(run_dir, plan, job, timeout=300):
    verify_tool_files(run_dir, plan)
    root = Path(run_dir) / 'runs' / ident(job)
    root.mkdir(parents=True, exist_ok=False)
    entries, previous_output, diagnostics = [], None, None
    for index in range(TOOL_POLICY['max_revisions'] + 1):
        request = (generation_request(run_dir, plan, job) if index == 0 else
                   revision_request(run_dir, plan, job, previous_output, diagnostics))
        attempt = root / 'attempts' / str(index)
        record = call(attempt, request, timeout)
        entry = {'index': index, 'record_sha256': sha((attempt / 'record.json').read_bytes())}
        entries.append(entry)
        if record['status'] != 'completed':
            result = {'status': 'error', 'selected_attempt': None, 'diagnostic_status': 'not_run', 'attempts': entries}
            break
        diagnostics = collect_diagnostics(run_dir, plan, job, attempt)
        entry['diagnostics_sha256'] = sha((attempt / 'diagnostics/report.json').read_bytes())
        if diagnostics['status'] == 'error':
            result = {'status': 'error', 'selected_attempt': None, 'diagnostic_status': 'error', 'attempts': entries}
            break
        if diagnostics['status'] == 'pass' or index == TOOL_POLICY['max_revisions']:
            result = {'status': 'completed', 'selected_attempt': index, 'diagnostic_status': diagnostics['status'], 'attempts': entries}
            break
        previous_output = (attempt / 'output.md').read_text(encoding='utf-8')
    result.update(method='tool-assisted-v1', policy_sha256=sha(encode(plan['tool_policy'])),
                  requested_model=job['model'], requested_effort=job['effort'],
                  max_output_tokens_per_call=MAX_OUTPUT_TOKENS,
                  max_output_tokens_per_generation=TOOL_POLICY['max_output_tokens_per_generation'],
                  selected_output_sha256=record.get('output_sha256') if result['selected_attempt'] is not None else None)
    dump(root / 'selection.json', result)
    return result


def generation_result(run_dir, plan, job):
    root = Path(run_dir) / 'runs' / ident(job)
    if plan.get('method', 'single-shot') == 'single-shot':
        return root, record_valid(root, generation_request(run_dir, plan, job))
    verify_tool_files(run_dir, plan)
    selection = read(root / 'selection.json')
    if (selection.get('status') != 'completed' or selection.get('method') != 'tool-assisted-v1' or
            selection.get('policy_sha256') != sha(encode(plan['tool_policy'])) or
            selection.get('requested_model') != job['model'] or selection.get('requested_effort') != job['effort'] or
            selection.get('max_output_tokens_per_call') != MAX_OUTPUT_TOKENS or
            selection.get('max_output_tokens_per_generation') != TOOL_POLICY['max_output_tokens_per_generation']):
        raise ValueError('assisted generation incomplete or error')
    entries = selection.get('attempts', [])
    selected = selection.get('selected_attempt')
    if not isinstance(selected, int) or selected < 0 or selected > 2 or len(entries) != selected + 1:
        raise ValueError('assisted deterministic selection mismatch')
    actual = {p.name for p in (root / 'attempts').iterdir() if p.is_dir()}
    if actual != {str(i) for i in range(selected + 1)}:
        raise ValueError('assisted hidden or missing attempt')
    previous_output, previous_diagnostics, unknown_efforts = None, None, 0
    for index, entry in enumerate(entries):
        attempt = root / 'attempts' / str(index)
        if entry.get('index') != index or sha((attempt / 'record.json').read_bytes()) != entry.get('record_sha256'):
            raise ValueError('assisted record hash drift')
        request = (generation_request(run_dir, plan, job) if index == 0 else
                   revision_request(run_dir, plan, job, previous_output, previous_diagnostics))
        record = record_valid(attempt, request)
        unknown_efforts += record['effort_evidence'] == 'unknown'
        if sha((attempt / 'diagnostics/report.json').read_bytes()) != entry.get('diagnostics_sha256'):
            raise ValueError('assisted diagnostics hash drift')
        diagnostics = read(attempt / 'diagnostics/report.json')
        if diagnostics != _diagnostic_report(run_dir, plan, job, attempt):
            raise ValueError('assisted diagnostic evidence drift')
        if diagnostics['status'] == 'error' or (index < selected and diagnostics['status'] not in TOOL_POLICY['repair_trigger']):
            raise ValueError('assisted revision was not authorized by diagnostics')
        previous_output, previous_diagnostics = (attempt / 'output.md').read_text(encoding='utf-8'), diagnostics
    if diagnostics['status'] != selection.get('diagnostic_status') or (selected < 2 and diagnostics['status'] != 'pass'):
        raise ValueError('assisted selection does not follow stop rule')
    if selection.get('selected_output_sha256') != record['output_sha256']:
        raise ValueError('assisted selected raw output hash drift')
    return attempt, {**record, 'diagnostic_status': diagnostics['status'], 'model_attempts': selected + 1,
                     'attempt_unknown_effort_echoes': unknown_efforts,
                     'selection_sha256': sha((root / 'selection.json').read_bytes())}


def preflight(run_dir, timeout=300):
    run_dir = Path(run_dir)
    verify(run_dir)
    catalog_path = run_dir / 'preflight/catalog.json'
    if not catalog_path.exists():
        req = urllib.request.Request(ENDPOINT.replace('/responses', '/models'))
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(4 * 1024 * 1024)
        save(catalog_path, raw)
    validate_catalog(read(catalog_path))
    records = []
    for index, model in enumerate(MODELS):
        for effort in EFFORTS:
            directory = run_dir / 'preflight' / f'm{index}-{effort}'
            request = body('다음 문장만 그대로 출력하라: 연결을 확인했다.', model, effort)
            if not directory.exists():
                call(directory, request, timeout)
            try:
                record = record_valid(directory, request)
                records.append({'id': directory.name, 'status': 'completed',
                                'record_sha256': sha((directory / 'record.json').read_bytes()),
                                'returned_effort': record['returned_effort'],
                                'effort_evidence': record['effort_evidence']})
            except (ValueError, OSError, KeyError) as error:
                records.append({'id': directory.name, 'status': 'error', 'error': type(error).__name__})
    result = {'passed': all(r['status'] == 'completed' for r in records),
              'catalog_sha256': sha(catalog_path.read_bytes()), 'records': records}
    if not (run_dir / 'preflight.json').exists():
        dump(run_dir / 'preflight.json', result)
    return result


def require_preflight(run_dir):
    run_dir = Path(run_dir)
    saved = read(run_dir / 'preflight.json')
    catalog_path = run_dir / 'preflight/catalog.json'
    if not saved.get('passed') or sha(catalog_path.read_bytes()) != saved['catalog_sha256']:
        raise ValueError('valid preflight required')
    validate_catalog(read(catalog_path))
    expected_ids = {f'm{index}-{effort}' for index in range(2) for effort in EFFORTS}
    if {r['id'] for r in saved['records']} != expected_ids or len(saved['records']) != 6:
        raise ValueError('incomplete preflight')
    for item in saved['records']:
        index, effort = item['id'].split('-', 1)
        directory = run_dir / 'preflight' / item['id']
        record_valid(directory, body('다음 문장만 그대로 출력하라: 연결을 확인했다.', MODELS[int(index[1:])], effort))
        if sha((directory / 'record.json').read_bytes()) != item['record_sha256']:
            raise ValueError('preflight hash drift')
    return saved


def generate(run_dir, split='development', workers=2, limit=None, timeout=300):
    run_dir = Path(run_dir)
    plan = verify(run_dir)
    require_preflight(run_dir)
    if split == 'evaluation' and aggregate(run_dir)['development_gate'] != 'pass':
        raise ValueError('development gate must pass before held-out generation')
    pending = [job for job in jobs(plan, split) if not (run_dir / 'runs' / ident(job)).exists()]
    if limit is not None:
        pending = pending[:limit]

    def run(job):
        if plan.get('method') == 'tool-assisted-v1':
            return assisted_generate(run_dir, plan, job, timeout)
        return call(run_dir / 'runs' / ident(job), generation_request(run_dir, plan, job), timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, pending))


def _review_object(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('review schema: ' + name)


def _review_text(value, name, empty=False):
    if not isinstance(value, str) or (not value.strip() and not (empty and value == '')):
        raise ValueError('review schema text: ' + name)
    try:
        value.encode('utf-8')
    except UnicodeError as error:
        raise ValueError('review schema UTF-8: ' + name) from error


def _review_structure(verdict, outputs, modality):
    """Validate the whole shape/decisions before any quote repair is eligible."""
    _review_object(verdict, ('outputs', 'pairs'), 'root')
    _review_object(verdict['outputs'], outputs, 'outputs')
    for label, result in verdict['outputs'].items():
        _review_object(result, ('meaning', 'findings', 'format'), 'output ' + label)
        if result['meaning'] not in ('pass', 'fail', 'unresolved') or not isinstance(result['findings'], list):
            raise ValueError('review meaning/findings schema')
        if (result['meaning'] == 'pass') != (len(result['findings']) == 0):
            raise ValueError('review meaning/findings inconsistency')
        for finding in result['findings']:
            _review_object(finding, ('source_quote', 'output_quote', 'reason'), 'finding')
            _review_text(finding['source_quote'], 'source_quote', empty=True)
            _review_text(finding['output_quote'], 'output_quote', empty=True)
            _review_text(finding['reason'], 'finding reason')
            if not (finding['source_quote'] or finding['output_quote']):
                raise ValueError('missing finding evidence')
        formatting = result['format']
        _review_object(formatting, ('status', 'evidence', 'scene_correspondence'), 'format')
        if formatting['status'] not in ('pass', 'fail', 'unresolved') or not isinstance(formatting['evidence'], list) or not formatting['evidence']:
            raise ValueError('review format schema')
        for item in formatting['evidence']:
            _review_object(item, ('output_quote', 'reason'), 'format evidence')
            _review_text(item['output_quote'], 'format quote')
            _review_text(item['reason'], 'format reason')
        scenes = formatting['scene_correspondence']
        if not isinstance(scenes, list) or (modality not in (None, 'L4') and scenes):
            raise ValueError('review scene correspondence schema')
        if modality == 'L4' and formatting['status'] == 'pass' and not scenes:
            raise ValueError('L4 scene correspondence evidence missing')
        for item in scenes:
            _review_object(item, ('scene_id', 'code_quote', 'narration_quote', 'reason'), 'scene')
            for key, value in item.items():
                _review_text(value, key)
            if item['scene_id'] not in item['code_quote'] or item['scene_id'] not in item['narration_quote']:
                raise ValueError('L4 scene ID relation mismatch')
    pairs = verdict['pairs']
    if not isinstance(pairs, list) or len(pairs) != 3:
        raise ValueError('review pairs schema')
    for pair in pairs:
        _review_object(pair, ('left', 'right', 'winner', 'reason', 'evidence'), 'pair')
        labels = {pair['left'], pair['right']}
        if len(labels) != 2 or not labels.issubset(outputs) or pair['winner'] not in (*labels, 'tie'):
            raise ValueError('invalid pair verdict')
        _review_text(pair['reason'], 'pair reason')
        evidence = pair['evidence']
        if not isinstance(evidence, list) or len(evidence) < 2:
            raise ValueError('both clarity evidence quotes are required')
        for item in evidence:
            _review_object(item, ('label', 'quote'), 'pair evidence')
            if item['label'] not in labels:
                raise ValueError('pair evidence label mismatch')
            _review_text(item['quote'], 'pair quote')
        if {item['label'] for item in evidence} != labels:
            raise ValueError('both clarity evidence labels are required')
    expected = {frozenset(pair) for pair in itertools.combinations(outputs, 2)}
    if {frozenset((pair['left'], pair['right'])) for pair in pairs} != expected:
        raise ValueError('review pairs mismatch')


def validate_review(verdict, source, outputs, modality=None, _bad_paths=None):
    _review_structure(verdict, outputs, modality)

    def quote(path, value, corpus):
        if value not in corpus:
            if _bad_paths is None:
                raise ValueError('fabricated evidence quote at ' + json.dumps(path))
            _bad_paths.append(path)

    for label, result in verdict['outputs'].items():
        for index, finding in enumerate(result['findings']):
            prefix = ['outputs', label, 'findings', index]
            quote(prefix + ['source_quote'], finding['source_quote'], source)
            quote(prefix + ['output_quote'], finding['output_quote'], outputs[label])
        formatting = result['format']
        for index, item in enumerate(formatting['evidence']):
            quote(['outputs', label, 'format', 'evidence', index, 'output_quote'], item['output_quote'], outputs[label])
        if formatting['scene_correspondence']:
            from evaluation.output_formats import media
            blocks = media.code_blocks(outputs[label], {'python', 'py'})
            if len(blocks) != 1:
                raise ValueError('L4 correspondence lacks one code artifact')
            prose = outputs[label].replace(blocks[0], '')
            for index, item in enumerate(formatting['scene_correspondence']):
                prefix = ['outputs', label, 'format', 'scene_correspondence', index]
                quote(prefix + ['code_quote'], item['code_quote'], blocks[0])
                quote(prefix + ['narration_quote'], item['narration_quote'], prose)
    for index, pair in enumerate(verdict['pairs']):
        for evidence_index, item in enumerate(pair['evidence']):
            quote(['pairs', index, 'evidence', evidence_index, 'quote'], item['quote'], outputs[item['label']])


def _review_lock(verdict, paths):
    masked = json.loads(json.dumps(verdict, ensure_ascii=True, allow_nan=False))
    for index, path in enumerate(paths):
        parent = masked
        for token in path[:-1]:
            parent = parent[token]
        if not isinstance(parent[path[-1]], str) or not parent[path[-1]].strip():
            raise ValueError('permitted nonempty quote leaf was erased or changed type')
        parent[path[-1]] = {'permitted_quote_leaf': index}
    # JSON object and array order, every reason, count and non-whitelisted leaf remain locked.
    return sha(json.dumps(masked, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode())


def review_quote_analysis(verdict, source, outputs, modality=None):
    bad_paths = []
    validate_review(verdict, source, outputs, modality, _bad_paths=bad_paths)
    projection = {'outputs': {label: {'meaning': verdict['outputs'][label]['meaning'],
                   'format': verdict['outputs'][label]['format']['status']} for label in sorted(outputs)},
                  'pairs': {''.join(sorted((pair['left'], pair['right']))): pair['winner']
                            for pair in sorted(verdict['pairs'], key=lambda pair: ''.join(sorted((pair['left'], pair['right']))))}}
    return {'status': 'quote_mismatch' if bad_paths else 'valid', 'bad_paths': bad_paths,
            'decision_projection': projection, 'decision_sha256': sha(encode(projection)),
            'locked_sha256': _review_lock(verdict, bad_paths)}


def parse_verdict(text):
    # Parse wrappers without editing the preserved model output.
    text = text.strip()
    if text.startswith('```json\n') and text.endswith('```'):
        text = text[8:-3].strip()
    elif text.startswith('```\n') and text.endswith('```'):
        text = text[4:-3].strip()
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('non-JSON numeric constant')
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def triads(plan, split=None):
    return (job for job in jobs(plan, split) if job['arm'] == 'baseline')


def review_materials(run_dir, plan, job):
    run_dir = Path(run_dir)
    blind_job = dict(job, arm='blind')
    arms = list(ARMS)
    random.Random(sha(ident(blind_job).encode())).shuffle(arms)
    packet = {'source': job['case']['source'], 'task': job['case']['task'], 'modality': job['case']['modality'],
              'contract': plan['contracts'][job['case']['modality']], 'outputs': {}}
    links = {}
    for label, arm in zip('ABC', arms):
        generation = dict(job, arm=arm)
        directory, record = generation_result(run_dir, plan, generation)
        output = (directory / 'output.md').read_bytes()
        packet['outputs'][label] = output.decode('utf-8')
        links[label] = {'arm': arm, 'id': ident(generation), 'sha256': sha(output),
                        'record_sha256': sha((directory / 'record.json').read_bytes())}
        if plan.get('method') == 'tool-assisted-v1':
            links[label]['selection_sha256'] = record['selection_sha256']
    reviewer = MODELS[1 - job['model_index']]
    request = body(plan['rubric'] + '\n\n' + json.dumps(packet, ensure_ascii=False), reviewer, REVIEW_EFFORT)
    return packet, links, request


def review_correction_request(original_request, previous_raw, bad_paths):
    prompt = (original_request['input'][0]['content'][0]['text'] + '\n\n' + QUOTE_CORRECTION_COMMON +
              '\n\n정정할 수 있는 JSON 경로\n' + json.dumps(bad_paths, ensure_ascii=False) +
              '\n\n이전 원시 판정 (판단과 이유는 잠금)\n' + previous_raw)
    return body(prompt, original_request['model'], original_request['reasoning']['effort'])


def _review_validation(raw, packet, previous=None, previous_analysis=None):
    try:
        parsed = parse_verdict(raw)
    except (ValueError, KeyError, TypeError):
        return None, {'status': 'schema_error', 'bad_paths': [], 'error': 'malformed or ambiguous JSON'}
    if previous is not None:
        try:
            unchanged = _review_lock(parsed, previous_analysis['bad_paths']) == previous_analysis['locked_sha256']
        except (ValueError, KeyError, TypeError, IndexError):
            unchanged = False
        if not unchanged:
            return None, {'status': 'locked_content_drift', 'bad_paths': [],
                          'error': 'a decision, reason, structure, order or non-whitelisted quote changed'}
    try:
        analysis = review_quote_analysis(parsed, packet['source'], packet['outputs'], packet['modality'])
    except (ValueError, KeyError, TypeError, IndexError):
        return None, {'status': 'schema_error', 'bad_paths': [], 'error': 'review shape or non-quote relation invalid'}
    if previous_analysis is not None and analysis['decision_sha256'] != previous_analysis['decision_sha256']:
        return None, {'status': 'locked_content_drift', 'bad_paths': [], 'error': 'decision projection changed'}
    return parsed, analysis


def review_one(run_dir, plan, job, timeout=300, materials=None):
    """Judge once; only invalid exact-quote leaves can receive bounded correction."""
    if plan.get('review_policy') != REVIEW_POLICY:
        raise ValueError('technical review policy drift')
    packet, links, original_request = materials or review_materials(run_dir, plan, job)
    root = Path(run_dir) / 'reviews' / ident(dict(job, arm='blind'))
    root.mkdir(parents=True, exist_ok=False)
    dump(root / 'packet.json', packet)
    dump(root / 'blind-key.json', links)
    entries, previous, previous_analysis, previous_raw = [], None, None, None
    initial_decision = None
    for index in range(REVIEW_POLICY['max_corrections'] + 1):
        request = (original_request if index == 0 else
                   review_correction_request(original_request, previous_raw, previous_analysis['bad_paths']))
        attempt = root / 'attempts' / str(index)
        record = call(attempt, request, timeout)
        parsed = None
        if record['status'] != 'completed':
            analysis = {'status': 'transport_error', 'bad_paths': [], 'error': record.get('error')}
        else:
            raw = (attempt / 'output.md').read_text(encoding='utf-8')
            parsed, analysis = _review_validation(raw, packet, previous, previous_analysis)
        dump(attempt / 'validation.json', analysis)
        entries.append({'index': index, 'record_sha256': sha((attempt / 'record.json').read_bytes()),
                        'validation_sha256': sha((attempt / 'validation.json').read_bytes())})
        if index == 0:
            initial_decision = analysis.get('decision_sha256')
        if analysis['status'] == 'valid':
            dump(attempt / 'verdict.json', parsed)
            result = {'status': 'completed', 'selected_attempt': index, 'validation_status': 'valid',
                      'selected_output_sha256': record['output_sha256'],
                      'selected_verdict_sha256': sha((attempt / 'verdict.json').read_bytes())}
            break
        if analysis['status'] != 'quote_mismatch' or index == REVIEW_POLICY['max_corrections']:
            result = {'status': 'error', 'selected_attempt': None, 'validation_status': analysis['status'],
                      'selected_output_sha256': None, 'selected_verdict_sha256': None}
            dump(root / 'invalid-review.json', {'status': analysis['status'], 'attempts': index + 1})
            break
        previous, previous_analysis, previous_raw = parsed, analysis, raw
    result.update(policy_sha256=sha(encode(plan['review_policy'])), attempts=entries,
                  packet_sha256=sha((root / 'packet.json').read_bytes()),
                  blind_key_sha256=sha((root / 'blind-key.json').read_bytes()),
                  decision_sha256=initial_decision, requested_model=original_request['model'],
                  requested_effort=original_request['reasoning']['effort'],
                  max_output_tokens_per_call=MAX_OUTPUT_TOKENS,
                  max_output_tokens_per_review=REVIEW_POLICY['max_output_tokens_per_review'])
    dump(root / 'selection.json', result)
    return result


def review_result(run_dir, plan, job):
    """Replay immutable quote-only eligibility, locks, requests and first-valid stop."""
    root = Path(run_dir) / 'reviews' / ident(dict(job, arm='blind'))
    packet, links, original_request = review_materials(run_dir, plan, job)
    selection = read(root / 'selection.json')
    if (plan.get('review_policy') != REVIEW_POLICY or selection.get('status') != 'completed' or
            selection.get('validation_status') != 'valid' or selection.get('policy_sha256') != sha(encode(plan['review_policy']))):
        raise ValueError('review incomplete or invalid')
    if (read(root / 'packet.json') != packet or read(root / 'blind-key.json') != links or
            sha((root / 'packet.json').read_bytes()) != selection.get('packet_sha256') or
            sha((root / 'blind-key.json').read_bytes()) != selection.get('blind_key_sha256')):
        raise ValueError('review packet/output linkage drift')
    if (selection.get('requested_model') != original_request['model'] or
            selection.get('requested_effort') != original_request['reasoning']['effort'] or
            selection.get('max_output_tokens_per_call') != MAX_OUTPUT_TOKENS or
            selection.get('max_output_tokens_per_review') != REVIEW_POLICY['max_output_tokens_per_review']):
        raise ValueError('review model/effort/budget mismatch')
    selected = selection.get('selected_attempt')
    entries = selection.get('attempts', [])
    if not isinstance(selected, int) or isinstance(selected, bool) or not 0 <= selected <= REVIEW_POLICY['max_corrections'] or len(entries) != selected + 1:
        raise ValueError('review attempt selection mismatch')
    if {path.name for path in (root / 'attempts').iterdir() if path.is_dir()} != {str(index) for index in range(selected + 1)}:
        raise ValueError('review hidden or missing attempt')
    previous, previous_analysis, previous_raw, unknown = None, None, None, 0
    for index, entry in enumerate(entries):
        attempt = root / 'attempts' / str(index)
        request = (original_request if index == 0 else
                   review_correction_request(original_request, previous_raw, previous_analysis['bad_paths']))
        if entry.get('index') != index or sha((attempt / 'record.json').read_bytes()) != entry.get('record_sha256'):
            raise ValueError('review attempt record hash drift')
        record = record_valid(attempt, request)
        unknown += record['effort_evidence'] == 'unknown'
        raw = (attempt / 'output.md').read_text(encoding='utf-8')
        parsed, analysis = _review_validation(raw, packet, previous, previous_analysis)
        if (sha((attempt / 'validation.json').read_bytes()) != entry.get('validation_sha256') or
                read(attempt / 'validation.json') != analysis):
            raise ValueError('review quote-validation evidence drift')
        if index == 0 and analysis.get('decision_sha256') != selection.get('decision_sha256'):
            raise ValueError('review original decision projection drift')
        if index < selected:
            if analysis['status'] != 'quote_mismatch':
                raise ValueError('review correction was not eligible; valid grades are terminal')
            previous, previous_analysis, previous_raw = parsed, analysis, raw
        elif analysis['status'] != 'valid':
            raise ValueError('selected review is invalid')
    if (read(attempt / 'verdict.json') != parsed or
            sha((attempt / 'verdict.json').read_bytes()) != selection.get('selected_verdict_sha256') or
            record['output_sha256'] != selection.get('selected_output_sha256')):
        raise ValueError('selected review raw/verdict hash drift')
    return attempt, parsed, {**record, 'model_attempts': selected + 1,
                            'exact_quote_corrections': selected, 'attempt_unknown_effort_echoes': unknown,
                            'review_selection_sha256': sha((root / 'selection.json').read_bytes())}


def review(run_dir, split='development', workers=2, limit=None, timeout=300):
    run_dir = Path(run_dir)
    plan = verify(run_dir)
    require_preflight(run_dir)
    pending = [job for job in triads(plan, split)
               if not (run_dir / 'reviews' / ident(dict(job, arm='blind'))).exists()]
    ready = []
    for job in pending:
        try:
            materials = review_materials(run_dir, plan, job)
            ready.append((job, materials))
        except (OSError, ValueError, KeyError):
            continue
    if limit is not None:
        ready = ready[:limit]

    def run(item):
        job, materials = item
        return review_one(run_dir, plan, job, timeout, materials)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, ready))


def hashed_artifact(run_dir, artifact):
    path = safe_path(run_dir, artifact['path'])
    data = path.read_bytes()
    if sha(data) != artifact['sha256']:
        raise ValueError('external artifact hash drift')
    return data


def validate_png(data):
    """Check actual PNG chunks, CRCs and compressed pixels, not a filename/flag."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('rendered evidence must be a PNG screenshot')
    cursor, pixels, dimensions, ended = 8, b'', None, False
    while cursor + 12 <= len(data):
        size = struct.unpack('>I', data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        chunk = data[cursor + 8:cursor + 8 + size]
        end = cursor + 12 + size
        if end > len(data) or zlib.crc32(kind + chunk) & 0xffffffff != struct.unpack('>I', data[end - 4:end])[0]:
            raise ValueError('invalid screenshot PNG checksum')
        if kind == b'IHDR':
            if size != 13:
                raise ValueError('invalid PNG header')
            dimensions = struct.unpack('>II', chunk[:8])
        elif kind == b'IDAT':
            pixels += chunk
        elif kind == b'IEND':
            ended = True
            break
        cursor = end
    if not ended or dimensions is None or min(dimensions) < 160 or max(dimensions) < 240 or not pixels:
        raise ValueError('screenshot lacks usable dimensions/pixels')
    try:
        decoded = zlib.decompress(pixels)
    except zlib.error as error:
        raise ValueError('invalid screenshot compressed pixels') from error
    if len(decoded) < dimensions[0] * dimensions[1]:
        raise ValueError('screenshot pixel buffer is incomplete')
    return dimensions


def _external_job(run_dir, plan, entry, modality):
    matching = [job for job in jobs(plan) if ident(job) == entry.get('generation_id')]
    if len(matching) != 1 or matching[0]['case']['modality'] != modality:
        raise ValueError('media evidence generation/modality mismatch')
    job = matching[0]
    directory, record = generation_result(run_dir, plan, job)
    output = (directory / 'output.md').read_text(encoding='utf-8')
    if sha(output.encode()) != entry.get('output_sha256'):
        raise ValueError('media evidence output hash mismatch')
    from evaluation.output_formats import media
    return job, output, media.inspect_output(modality, output)


def _validate_media(run_dir, plan, checks):
    from evaluation.output_formats import media
    by_id = {check['id']: check for check in checks}
    examples = by_id['static'].get('examples', [])
    covered_arms = set()
    for entry in examples:
        job, output, inspection = _external_job(run_dir, plan, entry, 'L2')
        receipt = json.loads(hashed_artifact(run_dir, entry['receipt']))
        if (receipt.get('renderer') not in ('mermaid-cli', 'markdown-browser', 'ascii-browser') or
                receipt.get('source_sha256') != sha(output.encode()) or receipt.get('exit_code') != 0):
            raise ValueError('static rendering receipt mismatch')
        validate_png(hashed_artifact(run_dir, receipt['screenshot']))
        covered_arms.add(job['arm'])
    if covered_arms != set(ARMS):
        raise ValueError('static representative rendering missing a comparison arm')
    interactive = by_id['interactive'].get('checks', [])
    expected = {ident(job) for job in jobs(plan) if job['case']['modality'] == 'L3'}
    if {entry.get('generation_id') for entry in interactive} != expected or len(interactive) != len(expected):
        raise ValueError('interactive evidence requires every L3 output in all arms')
    for entry in interactive:
        job, output, inspection = _external_job(run_dir, plan, entry, 'L3')
        if inspection['status'] == 'static_failed':
            if entry.get('status') != 'static_failed' or job['arm'] == 'candidate':
                raise ValueError('candidate interactive static checks failed')
            continue
        receipt = json.loads(hashed_artifact(run_dir, entry['receipt']))
        code_hash = sha(media.extract_html(output).encode())
        if plan.get('method') == 'tool-assisted-v1':
            validate_browser_receipt(run_dir, plan, job, safe_path(run_dir, entry['receipt']['path']).parent,
                                     receipt, media.extract_html(output), output)
        if (receipt.get('tool') != 'playwright' or receipt.get('output_sha256') != entry['output_sha256'] or
                receipt.get('html_sha256') != code_hash or not isinstance(receipt.get('console_errors'), list)):
            raise ValueError('interactive runtime receipt mismatch')
        actions = receipt.get('actions', {})
        required_actions = {'initial', 'change', 'invalid', 'reset', 'narrow', 'keyboard'}
        if set(actions) != required_actions or any(
                action.get('status') not in ('pass', 'fail') or not action.get('observations')
                for action in actions.values()):
            raise ValueError('interactive action observations are incomplete')
        runtime_pass = not receipt['console_errors'] and not receipt.get('blocked_requests', []) and all(a['status'] == 'pass' for a in actions.values())
        if receipt.get('status') != ('pass' if runtime_pass else 'fail'):
            raise ValueError('interactive runtime status disagrees with observations')
        validate_png(hashed_artifact(run_dir, receipt['screenshot']))
        if job['arm'] == 'candidate' and not runtime_pass:
            raise ValueError('candidate interactive runtime failed')
    # L4 is a source+script deliverable. Never require or imply a Manim render.
    animation = by_id['animation']
    if animation.get('render_status') not in ('not_verified', 'verified_separately'):
        raise ValueError('animation render status must be explicit')
    expected = {ident(job) for job in jobs(plan) if job['case']['modality'] == 'L4'}
    if set(animation.get('generation_ids', [])) != expected or len(animation['generation_ids']) != len(expected):
        raise ValueError('animation source correspondence coverage is incomplete')
    for job in jobs(plan):
        if job['case']['modality'] != 'L4':
            continue
        directory, record = generation_result(run_dir, plan, job)
        output = (directory / 'output.md').read_text(encoding='utf-8')
        inspection = media.inspect_output('L4', output)
        packet, links, request = review_materials(run_dir, plan, job)
        review_dir, verdict, review_record = review_result(run_dir, plan, job)
        label = next(label for label, link in links.items() if link['arm'] == job['arm'])
        if job['arm'] == 'candidate' and (inspection['status'] != 'static_checks_only' or
                verdict['outputs'][label]['format']['status'] != 'pass'):
            raise ValueError('candidate animation source/script correspondence failed')


def _text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _text_values(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in ('text', 'content'):
                yield from _text_values(item)


def _cat_paths(command, project):
    tokens = shlex.split(command)
    if tokens and Path(tokens[0]).name in ('sh', 'bash', 'zsh') and '-lc' in tokens:
        at = tokens.index('-lc')
        if at + 1 >= len(tokens):
            return set()
        tokens = shlex.split(tokens[at + 1])
    if not tokens or Path(tokens[0]).name != 'cat':
        return set()
    # Accept only literal complete cat operands, resolved against the recorded cwd.
    if any(any(mark in token for mark in ('$', '`', ';', '&', '|', '>', '<', '*', '?')) for token in tokens[1:]):
        return set()
    return {(Path(project) / token).resolve() for token in tokens[1:] if not token.startswith('-')}


def _claude_frontmatter_read(value):
    match = re.search(r'(?ms)^---\n(.*?)^---(?:\n|$)', value)
    if match is None:
        raise ValueError('Claude read lacks skill frontmatter')
    header = match.group(1)
    for line in ('disable-model-invocation: true\n', 'user-invocable: true\n'):
        if header.count(line) != 1:
            raise ValueError('Claude manual-only frontmatter adapter mismatch')
        header = header.replace(line, '', 1)
    return value[:match.start(1)] + header + value[match.end(1):]


def _validate_host(run_dir, plan, check):
    host = check['id']
    request = json.loads(hashed_artifact(run_dir, check['request']))
    events = [json.loads(line) for line in hashed_artifact(run_dir, check['events']).decode().splitlines() if line.strip()]
    exit_result = json.loads(hashed_artifact(run_dir, check['exit']))
    output = hashed_artifact(run_dir, check['output']).decode('utf-8')
    expected_files = set(itertools.chain.from_iterable(plan['prompt_files']['candidate'].values()))
    expected_files.update(name for name in plan['candidate']['files'] if '/scripts/' in name or name.startswith('scripts/'))
    if (request.get('candidate_id') != plan['candidate']['candidate_id'] or
            request.get('source_hashes') != plan['candidate']['files'] or
            set(request.get('loaded_files', [])) != expected_files or exit_result.get('exit_code') != 0 or not output.strip()):
        raise ValueError('host source/exit/output evidence mismatch')
    command = request.get('command', [])
    if not isinstance(command, list) or not command or host not in Path(command[0]).name:
        raise ValueError('host executable mismatch')
    if '--model' not in command or command.index('--model') + 1 >= len(command):
        raise ValueError('host requested model is missing')
    model = command[command.index('--model') + 1]
    if host == 'codex':
        if model != MODELS[0] or 'model_reasoning_effort="medium"' not in command:
            raise ValueError('Codex host model/effort mismatch')
        marker = '$korean-protocol'
    else:
        if (model not in (MODELS[1], 'claude-opus-5-5') or '--effort' not in command or
                command.index('--effort') + 1 >= len(command) or
                command[command.index('--effort') + 1] != 'medium' or
                request.get('routing') != 'http://127.0.0.1:10100'):
            raise ValueError('Claude host model/effort/OpenCodex routing mismatch')
        marker = '/korean-protocol'
    if marker not in request.get('prompt', '') or not Path(request.get('skill_root', '')).is_absolute():
        raise ValueError('host skill invocation/discovery request missing')
    loaded, final_outputs = {}, []
    uses = {}
    for event in events:
        if host == 'codex':
            item = event.get('item', {})
            if event.get('type') == 'item.completed' and item.get('type') == 'command_execution' and item.get('exit_code') == 0:
                paths = _cat_paths(item.get('command', ''), request.get('project', '/'))
                for name in expected_files:
                    relative = name.split('skills/korean-protocol/', 1)[-1]
                    absolute = (Path(request['skill_root']) / relative).resolve()
                    if absolute in paths:
                        loaded.setdefault(name, []).append(item.get('aggregated_output', ''))
            if item.get('type') == 'agent_message':
                final_outputs.append(item.get('text', ''))
        else:
            content = event.get('message', {}).get('content', [])
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'tool_use' and item.get('name') == 'Read':
                        uses[item['id']] = item.get('input', {}).get('file_path')
                    elif item.get('type') == 'tool_result' and item.get('tool_use_id') in uses and not item.get('is_error'):
                        actual_path = uses[item['tool_use_id']]
                        for name in expected_files:
                            relative = name.split('skills/korean-protocol/', 1)[-1]
                            if actual_path and Path(actual_path).resolve() == (Path(request['skill_root']) / relative).resolve():
                                raw = '\n'.join(_text_values(item.get('content')))
                                loaded.setdefault(name, []).append(re.sub(r'(?m)^\s*\d+[→\t]', '', raw))
            if event.get('type') == 'result' and not event.get('is_error'):
                final_outputs.append(event.get('result', ''))
    for name in expected_files:
        expected = safe_path(Path(run_dir) / 'frozen/candidate', name).read_text(encoding='utf-8')
        observed = loaded.get(name, [])
        if host == 'claude' and Path(name).name == 'SKILL.md' and request.get('host_frontmatter_adapter') is True:
            observed = [_claude_frontmatter_read(value) for value in observed]
        if not any(expected.strip() in value for value in observed):
            raise ValueError('host event trace lacks exact full skill file read: ' + name)
    if not any(value.strip() == output.strip() for value in final_outputs):
        raise ValueError('host final output is detached from event trace')


def validate_external_evidence(run_dir, evidence, candidate_id, required_ids):
    if evidence.get('candidate_id') != candidate_id:
        raise ValueError('external evidence candidate mismatch')
    checks = evidence.get('checks', [])
    if {check.get('id') for check in checks} != set(required_ids) or len(checks) != len(required_ids):
        raise ValueError('external evidence check coverage mismatch')
    if any(check.get('artifacts') is not None for check in checks):
        raise ValueError('generic artifact/pass flags are not executable check evidence')
    plan = verify(run_dir)
    if candidate_id != plan['candidate']['candidate_id']:
        raise ValueError('external candidate identity drift')
    if set(required_ids) == {'static', 'interactive', 'animation'}:
        _validate_media(run_dir, plan, checks)
    elif set(required_ids) == {'codex', 'claude'}:
        for check in checks:
            _validate_host(run_dir, plan, check)
    else:
        raise ValueError('unknown external evidence check set')
    return True


def aggregate(run_dir):
    run_dir = Path(run_dir)
    plan = verify(run_dir)
    summary = {'candidate_id': plan['candidate']['candidate_id'],
               'method': plan.get('method', 'single-shot'),
               'plan_sha256': sha((run_dir / 'plan.json').read_bytes()),
               'comparison_status': 'incomplete', 'quality_gate': 'not_passed',
               'development_gate': 'not_passed', 'media_gate': 'not_checked', 'host_gate': 'not_checked',
               'expected_generations': len(list(jobs(plan))),
               'expected_reviews': len(list(triads(plan))),
               'completed_generations': 0, 'valid_reviews': 0, 'errors': [], 'missing': [],
               'meaning': {}, 'formats': {}, 'format_failures': [], 'format_review_failures': [],
               'evaluation_pairs': {}, 'unknown_effort_echoes': 0, 'evidence_files': {},
               'generation_model_calls': 0, 'review_model_calls': 0, 'exact_quote_corrections': 0,
               'tool_failures': []}
    preflight_ok = False
    try:
        require_preflight(run_dir)
        preflight_ok = True
    except (OSError, ValueError, KeyError) as error:
        summary['errors'].append({'id': 'preflight', 'error': type(error).__name__})
    generation_counts = {split: 0 for split in ('development', 'evaluation')}
    review_counts = {split: 0 for split in ('development', 'evaluation')}
    for job in jobs(plan):
        directory = run_dir / 'runs' / ident(job)
        if not directory.exists():
            summary['missing'].append(ident(job))
            continue
        try:
            directory, record = generation_result(run_dir, plan, job)
            summary['completed_generations'] += 1
            summary['generation_model_calls'] += record.get('model_attempts', 1)
            generation_counts[job['split']] += 1
            summary['unknown_effort_echoes'] += record.get('attempt_unknown_effort_echoes', record['effort_evidence'] == 'unknown')
            if record.get('diagnostic_status', 'pass') != 'pass':
                summary['tool_failures'].append({'id': ident(job), 'arm': job['arm'], 'split': job['split'],
                    'status': record['diagnostic_status']})
            from evaluation.output_formats import media
            inspection = media.inspect_output(job['case']['modality'],
                (directory / 'output.md').read_text(encoding='utf-8'))
            if inspection['status'] == 'static_failed':
                summary['format_failures'].append({'id': ident(job), 'arm': job['arm'],
                    'split': job['split'], 'findings': inspection['findings']})
        except (OSError, ValueError, KeyError) as error:
            summary['errors'].append({'id': ident(job), 'error': type(error).__name__})
    for job in triads(plan):
        key = ident(dict(job, arm='blind'))
        directory = run_dir / 'reviews' / key
        if not directory.exists():
            summary['missing'].append(key)
            continue
        try:
            selected_review, verdict, record = review_result(run_dir, plan, job)
            links = read(directory / 'blind-key.json')
            summary['valid_reviews'] += 1
            summary['review_model_calls'] += record['model_attempts']
            summary['exact_quote_corrections'] += record['exact_quote_corrections']
            review_counts[job['split']] += 1
            summary['unknown_effort_echoes'] += record['attempt_unknown_effort_echoes']
            meaning = summary['meaning'].setdefault(job['split'], {
                arm: {status: 0 for status in ('pass', 'fail', 'unresolved')} for arm in ARMS})
            for label, result in verdict['outputs'].items():
                meaning[links[label]['arm']][result['meaning']] += 1
                formats = summary['formats'].setdefault(job['split'], {
                    arm: {status: 0 for status in ('pass', 'fail', 'unresolved')} for arm in ARMS})
                formats[links[label]['arm']][result['format']['status']] += 1
                if result['format']['status'] != 'pass':
                    summary['format_review_failures'].append({'id': links[label]['id'],
                        'arm': links[label]['arm'], 'split': job['split'], 'format': result['format']})
            if job['split'] == 'evaluation':
                cohort = job['model'] + ':' + job['effort']
                pairs = summary['evaluation_pairs'].setdefault(cohort, {
                    arm: {status: 0 for status in ('win', 'loss', 'tie')} for arm in ('baseline', 'ste')})
                for pair in verdict['pairs']:
                    left, right = links[pair['left']]['arm'], links[pair['right']]['arm']
                    if 'candidate' in (left, right):
                        control = right if left == 'candidate' else left
                        result = ('tie' if pair['winner'] == 'tie' else
                                  'win' if links[pair['winner']]['arm'] == 'candidate' else 'loss')
                        pairs[control][result] += 1
        except (OSError, ValueError, KeyError, TypeError) as error:
            summary['errors'].append({'id': key, 'error': type(error).__name__})
    per_split_g = len(list(jobs(plan, 'development')))
    per_split_r = len(list(triads(plan, 'development')))
    dev_meaning = summary['meaning'].get('development', {}).get('candidate', {})
    dev_formats = summary['formats'].get('development', {}).get('candidate', {})
    if (preflight_ok and generation_counts['development'] == per_split_g and
            review_counts['development'] == per_split_r and dev_meaning == {
                'pass': per_split_r, 'fail': 0, 'unresolved': 0} and
            dev_formats == {'pass': per_split_r, 'fail': 0, 'unresolved': 0} and
            not any(item['arm'] == 'candidate' and item['split'] == 'development'
                    for item in summary['format_failures'] + summary['tool_failures'])):
        summary['development_gate'] = 'pass'
    complete = (preflight_ok and not summary['errors'] and not summary['missing'] and
                summary['completed_generations'] == summary['expected_generations'] and
                summary['valid_reviews'] == summary['expected_reviews'])
    if complete:
        summary['comparison_status'] = 'complete'
    evaluation_meaning = summary['meaning'].get('evaluation', {}).get('candidate', {})
    if (complete and summary['development_gate'] == 'pass' and
            evaluation_meaning == {'pass': per_split_r, 'fail': 0, 'unresolved': 0} and
            summary['formats'].get('evaluation', {}).get('candidate') == {
                'pass': per_split_r, 'fail': 0, 'unresolved': 0} and
            not any(item['arm'] == 'candidate' for item in summary['format_failures']) and
            not any(item['arm'] == 'candidate' for item in summary['tool_failures']) and
            len(summary['evaluation_pairs']) == len(MODELS) * len(EFFORTS) and
            all(counts['win'] > counts['loss'] for cohort in summary['evaluation_pairs'].values()
                for counts in cohort.values())):
        summary['quality_gate'] = 'pass'
    for kind, required in [('media', ['static', 'interactive', 'animation']),
                           ('host', ['codex', 'claude'])]:
        path = run_dir / (kind + '-evidence.json')
        if path.exists():
            try:
                validate_external_evidence(run_dir, read(path), summary['candidate_id'], required)
                summary[kind + '_gate'] = 'pass'
                summary['evidence_files'][path.name] = sha(path.read_bytes())
            except (OSError, ValueError, KeyError, TypeError):
                summary[kind + '_gate'] = 'not_passed'
    return summary


def validate_installation_evidence(run_dir, expected_source_hashes, candidate_id, expected_package_sha256=None):
    run_dir = Path(run_dir)
    plan = verify(run_dir)
    candidate = plan['candidate']
    if candidate['files'] != expected_source_hashes or candidate['candidate_id'] != candidate_id:
        raise ValueError('installation candidate source hashes mismatch')
    result = aggregate(run_dir)
    if result['comparison_status'] != 'complete' or any(result[key] != 'pass' for key in
            ('quality_gate', 'media_gate', 'host_gate')):
        raise ValueError('installation evidence incomplete or gate not passed')
    if expected_package_sha256 is not None:
        binding = read(run_dir / 'package-binding.json')
        if binding != {'candidate_id': candidate_id, 'package_sha256': expected_package_sha256}:
            raise ValueError('installation package binding mismatch')
    return result


def viewer(run_dir):
    run_dir = Path(run_dir)
    plan = verify(run_dir)
    rows = []
    for job in triads(plan):
        row = {'name': ident(dict(job, arm='')).rstrip('-'), 'source': job['case']['source'],
               'task': job['case']['task'], 'modality': job['case']['modality']}
        for arm in ARMS:
            try:
                directory, record = generation_result(run_dir, plan, dict(job, arm=arm))
                row[arm] = (directory / 'output.md').read_text(encoding='utf-8')
            except (OSError, ValueError, KeyError, TypeError):
                row[arm] = '유효한 완료 실행 결과 없음'
        rows.append(row)
    data = json.dumps(rows, ensure_ascii=False).replace('<', '\\u003c')
    page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><title>원자료 · KP · STE</title>
<style>body{font:16px system-ui;margin:24px}select{max-width:100%;padding:8px}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui}section{border:1px solid #ccc;padding:16px}@media(max-width:800px){main{grid-template-columns:1fr}}</style>
<h1>원자료 · KP · STE</h1><p>원시 출력과 코드를 보존한다. STE는 한국어 실험 적용본이다. 렌더링과 호스트 검사는 별도 증거를 사용한다.</p>
<select id="case" aria-label="비교 사례"></select> <select id="arm" aria-label="KP 프로필"><option value="candidate">KP 후보</option><option value="baseline">기존 KP 0.9.0</option></select>
<p id="task"></p><main><section><h2>원자료</h2><pre id="source"></pre></section><section><h2>KP</h2><pre id="kp"></pre></section><section><h2>STE</h2><pre id="ste"></pre></section></main>
<script>const rows=DATA;const cs=document.getElementById('case'),arm=document.getElementById('arm');rows.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=r.name;cs.append(o)});function draw(){const r=rows[cs.value];for(const k of ['source','ste','task'])document.getElementById(k).textContent=r[k];document.getElementById('kp').textContent=r[arm.value]}cs.onchange=arm.onchange=draw;draw();</script></html>'''.replace('DATA', data)
    path = run_dir / 'viewer.html'
    path.write_text(page, encoding='utf-8')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'verify', 'preflight', 'generate', 'review', 'aggregate', 'viewer'])
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--candidate-only', action='store_true')
    parser.add_argument('--candidate', type=Path, help='candidate root; repository root when --candidate-files is used')
    parser.add_argument('--candidate-files', type=Path, help='JSON mapping of relative paths to source SHA256 hashes')
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--ste', type=Path)
    parser.add_argument('--ste-provenance', type=Path)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--method', choices=METHODS, default='single-shot')
    parser.add_argument('--html-checker', type=Path)
    parser.add_argument('--browser-checker', type=Path)
    parser.add_argument('--oracle', type=Path)
    parser.add_argument('--split', choices=['development', 'evaluation'], default='development')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--timeout', type=float, default=300)
    args = parser.parse_args(argv)
    if args.workers < 1 or args.workers > 16 or args.timeout <= 0 or (args.limit is not None and args.limit < 1):
        parser.error('workers must be 1..16; timeout and limit must be positive')
    if args.command == 'freeze':
        if args.candidate_only:
            if args.candidate is None:
                parser.error('--candidate is required for candidate-only freeze')
            selected = read(args.candidate_files) if args.candidate_files else None
            result = freeze_candidate(args.run_dir, args.candidate, selected)
        else:
            if not all((args.baseline, args.ste, args.ste_provenance, args.dataset)):
                parser.error('--baseline, --ste, --ste-provenance and --dataset are required')
            tool_files = None
            if args.method == 'tool-assisted-v1':
                if not all((args.html_checker, args.browser_checker, args.oracle)):
                    parser.error('tool-assisted freeze requires --html-checker, --browser-checker and --oracle')
                tool_files = {'html_checker': args.html_checker, 'browser_checker': args.browser_checker, 'oracle': args.oracle}
            result = freeze(args.run_dir, args.baseline, args.ste, args.ste_provenance, args.dataset, args.method, tool_files)
    elif args.command in ('generate', 'review'):
        result = globals()[args.command](args.run_dir, args.split, args.workers, args.limit, args.timeout)
    elif args.command == 'preflight':
        result = preflight(args.run_dir, args.timeout)
    else:
        result = globals()[args.command](args.run_dir)
    if args.command == 'aggregate':
        # Derived report is replaceable; immutable raw evidence and frozen inputs are never overwritten.
        (args.run_dir / 'summary.json').write_bytes(encode(result))
    print(json.dumps(str(result) if isinstance(result, Path) else result, ensure_ascii=False, indent=2))
    if args.command == 'preflight' and not result['passed']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
