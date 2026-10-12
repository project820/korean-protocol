#!/usr/bin/env python3
"""Real Codex CLI evaluation; structural validation never scores meaning."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile


CLI = '/Users/m5max/.local/bin/codex'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def freeze_inputs(cases_path, profile_path, out, plan_name='plan.md'):
    out = Path(out)
    frozen = out / 'frozen-profile.md'
    frozen.write_bytes(Path(profile_path).read_bytes())
    save_json(out / 'frozen-inputs.json', {'cases_sha256': digest(cases_path),
              'profile_sha256': digest(frozen), 'case_count': len(load_cases(cases_path)),
              'plan': plan_name, 'plan_sha256': digest(Path(__file__).with_name(plan_name))})
    return frozen


def load_cases(path):
    cases = json.loads(Path(path).read_text(encoding='utf-8'))['cases']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate case ids')
    return cases


def build_prompt(cases):
    public = [{k: c[k] for k in ('id', 'context', 'source')} for c in cases]
    return ('당신은 한국어 문장의 편집자입니다. 각 원문을 주어진 문맥에서 판단하세요. '
            '명확하고 자연스러우면 keep, 같은 뜻으로 더 명확하게 고칠 수 있으면 rewrite, '
            '뜻이나 필요한 행동을 정할 정보가 없으면 clarify를 선택하세요. '
            '원문의 사실, 조건, 부정 범위, 시점, 가능성, 허락과 의무를 유지하세요. '
            '문맥에 없는 사실, 원인, 절차를 만들지 마세요. clarify의 text에는 확인 질문을 쓰세요. '
            '각 id를 한 번씩 순서대로 처리하세요. 도구를 사용하거나 파일을 읽지 말고 아래 입력만 평가하세요. '
            '최종 출력은 JSON 객체 하나이며 results 배열의 각 항목은 id, action, text, reason 문자열을 포함합니다. '
            'reason은 선택 이유를 간단히 설명하세요. 별도 서문이나 Markdown을 넣지 마세요.\n'
            + json.dumps({'cases': public}, ensure_ascii=False, indent=2) + '\n')


def build_generation_prompt(cases):
    public = [{k: c[k] for k in ('id', 'facts', 'request')} for c in cases]
    return ('각 요청에 대한 한국어 답변을 새로 작성하세요. 제공한 사실과 요청만 바탕으로 답하세요. '
            '도구를 사용하거나 파일을 읽지 마세요. 각 id를 한 번씩 순서대로 처리하세요. '
            '최종 출력은 JSON 객체 하나이며 results 배열의 항목은 id와 text 문자열입니다. '
            'text에는 사용자가 읽을 자연스러운 한국어 답변을 쓰세요. 별도 서문이나 Markdown 포장은 넣지 마세요.\n'
            + json.dumps({'cases': public}, ensure_ascii=False, indent=2) + '\n')


def parse_response(raw, cases, mode='edit'):
    errors = []
    rows = []
    try:
        value = json.loads(raw)
        rows = value['results']
        if not isinstance(rows, list):
            raise ValueError('results must be an array')
        if [r.get('id') for r in rows] != [c['id'] for c in cases]:
            errors.append('missing, duplicate, reordered, or unknown case ids')
        for row in rows:
            required = ('id', 'text') if mode == 'generation' else ('id', 'action', 'text', 'reason')
            if any(not isinstance(row.get(k), str) for k in required):
                errors.append('required fields must be strings')
            if mode == 'edit' and row.get('action') not in ('keep', 'rewrite', 'clarify'):
                errors.append('invalid action')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append(str(exc))
    return {'structure_valid': not errors, 'errors': errors, 'results': rows}


def make_home(path, auth):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    (path / 'auth.json').symlink_to(Path(auth).resolve())
    return path


def build_command(project, last_message):
    return [CLI, 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
            '--skip-git-repo-check', '--sandbox', 'read-only', '--json', '--color', 'never',
            '--cd', str(project), '--model', 'gpt-6.1-sol',
            '-c', 'model_provider="subscription_router"',
            '-c', 'model_reasoning_effort="high"',
            '-c', 'model_providers.subscription_router.name="Subscription Router"',
            '-c', 'model_providers.subscription_router.base_url="http://127.0.0.1:10100/v1"',
            '-c', 'model_providers.subscription_router.wire_api="responses"',
            '-c', 'model_providers.subscription_router.requires_openai_auth=true',
            '-c', 'model_providers.subscription_router.supports_websockets=false',
            '--output-last-message', str(last_message), '-']


def capture(command, prompt, out, timeout=600, env=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timed_out = False
    error = None
    try:
        completed = subprocess.run(command, input=prompt, text=True, capture_output=True,
                                   timeout=timeout, env=env)
        stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr, code = exc.stdout or '', exc.stderr or '', None
    except OSError as exc:
        stdout, stderr, code = '', '', None
        error = str(exc)
    for name, stream in [('stdout.jsonl', stdout), ('stderr.txt', stderr)]:
        if isinstance(stream, bytes):
            stream = stream.decode('utf-8', errors='replace')
        (out / name).write_text(stream, encoding='utf-8')
    meta = {'command': command, 'started_at': started,
            'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'exit_code': code, 'timeout': timed_out, 'launch_error': error,
            'execution': 'real subprocess', 'provider_requested': 'subscription_router',
            'model_requested': 'gpt-6.1-sol', 'reasoning_effort': 'high',
            'upstream_provider_observed': None, 'fallback_observed': None,
            'routing_limit': 'CLI config shows requested localhost router; upstream/fallback is not returned by CLI.',
            'prompt_sha256': digest(out / 'prompt.txt')}
    save_json(out / 'metadata.json', meta)
    return meta


def run_condition(condition, cases, profile, out, auth, timeout, mode='edit'):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    # No parent CODEX_* overrides can silently inject configuration/instructions.
    for key in list(env):
        if key.startswith('CODEX_'):
            env.pop(key)
    with tempfile.TemporaryDirectory(prefix='korean-protocol-isolated-') as td:
        project = Path(td) / 'project'
        project.mkdir()
        if profile:
            (project / 'AGENTS.md').write_bytes(Path(profile).read_bytes())
            snapshot = out / 'instructions-snapshot'
            snapshot.mkdir()
            (snapshot / 'AGENTS.md').write_bytes(Path(profile).read_bytes())
        home = make_home(Path(td) / 'codex-home', auth)
        env['CODEX_HOME'] = str(home)
        prompt = build_generation_prompt(cases) if mode == 'generation' else build_prompt(cases)
        meta = capture(build_command(project, out / 'final.txt'), prompt, out,
                       timeout=timeout, env=env)
    meta.update({'condition': condition, 'profile_sha256': digest(profile) if profile else None,
                 'global_user_config_loaded': False, 'global_user_agents_loaded': False,
                 'authentication': 'existing auth.json symlink; credential contents never recorded',
                 'samples_per_condition': 1, 'case_count': len(cases), 'task_mode': mode})
    save_json(out / 'metadata.json', meta)
    raw = (out / 'final.txt').read_text(encoding='utf-8') if (out / 'final.txt').exists() else ''
    parsed = parse_response(raw, cases, mode=mode)
    save_json(out / 'parsed.json', parsed)
    return meta, parsed


def review_packet(cases, baseline, treatment, out, mode='edit'):
    # Randomized anew for each packet; previous packet identity cannot unblind it.
    conditions = ['baseline', 'treatment'] if secrets.randbelow(2) else ['treatment', 'baseline']
    outputs = {'baseline': baseline, 'treatment': treatment}
    indexes = [{r['id']: r for r in p['results'] if isinstance(r, dict) and 'id' in r}
               for p in (outputs[conditions[0]], outputs[conditions[1]])]
    packet = []
    for case in cases:
        packet.append(dict(case, A=indexes[0].get(case['id']), B=indexes[1].get(case['id']),
                           ratings={'A': None, 'B': None}))
    save_json(out / 'blind-review.json', packet)
    save_json(out / 'condition-key.json', dict(zip(('A', 'B'), conditions)))
    lines = ['# 수동 독립 검토 원자료', '', 'A/B 조건 이름은 별도 key에 저장했다. 점수는 아직 없다.', '']
    for row in packet:
        if mode == 'generation':
            lines += ['## ' + row['id'], '', '제공 사실: ' + ' / '.join(row['facts']), '',
                      '요청: ' + row['request'], '', '필수 사실: ' + ', '.join(row['required_facts']), '',
                      '금지 추론: ' + ', '.join(row['forbidden_inferences']), '',
                      '발화 목적: ' + row['speech_purpose'], '', '간결성 기준: ' + row['concision_criteria'], '']
        else:
            lines += ['## ' + row['id'], '', '문맥: ' + row['context'], '',
                  '원문: ' + row['source'], '', '필수 의미: ' + row['required_meaning'], '',
                  '허용 판단: ' + ', '.join(row['allowed_actions']), '']
        for label in ('A', 'B'):
            value = row[label]
            lines += [label + ': ' + (json.dumps(value, ensure_ascii=False) if value else '미완료/누락'), '']
    (out / 'blind-review.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('holdout.json'))
    parser.add_argument('--auth', type=Path, default=Path.home() / '.codex/auth.json')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--mode', choices=('edit', 'generation'), default='edit')
    args = parser.parse_args()
    if not args.auth.is_file():
        parser.error('Existing auth.json is unavailable; no credentials were read.')
    cases = load_cases(args.cases)
    args.output.mkdir(parents=True, exist_ok=False)
    if args.smoke:
        meta, parsed = run_condition('smoke-excluded', cases[:1], None, args.output / 'smoke',
                                     args.auth, args.timeout)
        print(json.dumps({'exit_code': meta['exit_code'], 'structure_valid': parsed['structure_valid']}))
        return
    if not args.profile or not args.profile.is_file():
        parser.error('A ready coding-agent profile is required for the comparison.')
    frozen_profile = freeze_inputs(args.cases, args.profile, args.output,
                                   'generation-plan.md' if args.mode == 'generation' else 'plan.md')
    baseline_meta, baseline = run_condition('baseline', cases, None, args.output / 'baseline',
                                            args.auth, args.timeout, mode=args.mode)
    treatment_meta, treatment = run_condition('treatment', cases, frozen_profile, args.output / 'treatment',
                                              args.auth, args.timeout, mode=args.mode)
    review_packet(cases, baseline, treatment, args.output, mode=args.mode)
    print(json.dumps({'baseline_exit': baseline_meta['exit_code'],
                      'treatment_exit': treatment_meta['exit_code'],
                      'baseline_structure': baseline['structure_valid'],
                      'treatment_structure': treatment['structure_valid']}))


if __name__ == '__main__':
    main()
