#!/usr/bin/env python3
"""Run one frozen generation condition; validate structure, never meaning."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SHARED_PATH = HERE.parent / 'runner.py'
SPEC = importlib.util.spec_from_file_location('scope_shared_runner', SHARED_PATH)
shared = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shared)
PUBLIC_FIELDS = ('id', 'facts', 'request')
MODELS = ('gpt-6.1-sol', 'anthropic/claude-opus-5-5')
MOUNT_PATHS = ('AGENTS.md', 'lexicon/core.json', 'lexicon/domains/software.json')
BOUNDARY = ('Read boundaries are prompt instructions and require raw tool-trace audit; '
            'the CLI read-only sandbox does not guarantee cwd-only reads.')


def public_cases(path):
    cases = shared.load_cases(path)
    if len(cases) != 12:
        raise ValueError('This frozen evaluation requires exactly 12 cases.')
    public = []
    for case in cases:
        if any(not isinstance(case.get(key), str) or not case[key].strip()
               for key in ('id', 'request')):
            raise ValueError('Case id and request must be nonempty strings.')
        facts = case.get('facts')
        if isinstance(facts, str):
            valid_facts = bool(facts.strip())
        else:
            valid_facts = (isinstance(facts, list) and bool(facts)
                           and all(isinstance(item, str) and item.strip() for item in facts))
        if not valid_facts:
            raise ValueError('Case facts must be a nonempty string or list of nonempty strings.')
        public.append({key: case[key] for key in PUBLIC_FIELDS})
    return public


def build_prompt(cases):
    public = [{key: case[key] for key in PUBLIC_FIELDS} for case in cases]
    return (
        '각 요청에 대한 한국어 답변을 새로 작성하세요. 제공한 사실과 요청을 바탕으로 답하세요. '
        '각 id를 한 번씩 입력 순서대로 처리하세요. '
        '현재 작업 디렉터리에 제공된 로컬 어휘집이 있으면 관련 항목을 읽을 수 있습니다. '
        '어휘집 경로는 lexicon/core.json과 lexicon/domains/software.json입니다. '
        '로컬 파일을 읽는 도구는 현재 작업 디렉터리 안에서만 사용하세요. '
        '필요한 항목만 찾아 읽고 파일 전체를 출력하지 마세요. '
        '어휘집이 없으면 입력만으로 답하세요. 외부 파일, 인터넷, 다른 모델이나 에이전트는 사용하지 마세요. '
        '최종 출력은 JSON 객체 하나이며 results 배열의 각 항목은 id와 text 문자열만 포함합니다. '
        'text에는 사용자가 읽을 자연스러운 한국어 답변을 쓰세요. '
        '별도 서문이나 Markdown 포장을 넣지 마세요.\n'
        + json.dumps({'cases': public}, ensure_ascii=False, indent=2) + '\n'
    )


def source_contract(args, prompt):
    sources = {'runner': Path(__file__), 'shared_runner': SHARED_PATH,
               'cases': args.cases, 'profile': args.profile, 'core': args.core,
               'software': args.software, 'plan': args.plan, 'adjudication': args.adjudication}
    contract = {name + '_sha256': shared.digest(path) for name, path in sources.items()}
    contract.update(prompt_sha256=hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                    case_count=12, task_mode='generation', permitted_models=list(MODELS),
                    reasoning_effort='high')
    return contract


def validate_manifest(path, contract, model):
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    for key, expected in contract.items():
        if manifest.get(key) != expected:
            raise ValueError('Frozen manifest mismatch: ' + key)
    if model not in manifest['permitted_models']:
        raise ValueError('Requested model is not frozen in the manifest.')
    return manifest


def snapshot_sources(args, out):
    snapshot = out / 'inputs-snapshot'
    snapshot.mkdir()
    for name, source in zip(MOUNT_PATHS, (args.profile, args.core, args.software)):
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    return snapshot


def mounted_hashes(project):
    return {str(path.relative_to(project)): shared.digest(path)
            for path in sorted(project.rglob('*')) if path.is_file()}


def mount_condition(condition, snapshot, project):
    project.mkdir()
    if condition == 'treatment':
        for name in MOUNT_PATHS:
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((snapshot / name).read_bytes())
    return mounted_hashes(project)


def make_command(project, final, model):
    command = shared.build_command(project, final)
    command[command.index('--model') + 1] = model
    command[-1:-1] = ['-c', 'web_search="disabled"',
                      '-c', 'features.multi_agent=false', '-c', 'approval_policy="never"']
    return command


def parse_result(raw, cases):
    parsed = shared.parse_response(raw, cases, mode='generation')
    if parsed['structure_valid']:
        value = json.loads(raw)
        if set(value) != {'results'}:
            parsed['errors'].append('output object must contain only results')
    if isinstance(parsed['results'], list):
        for row in parsed['results']:
            if not isinstance(row, dict):
                continue
            if set(row) != {'id', 'text'}:
                parsed['errors'].append('generation rows must contain only id and text')
            if isinstance(row.get('text'), str) and not row['text'].strip():
                parsed['errors'].append('text must be a nonempty string')
    parsed['structure_valid'] = not parsed['errors']
    parsed['semantic_evaluation'] = 'not performed; independent gold adjudication required'
    return parsed


def execute(args):
    cases = public_cases(args.cases)
    prompt = build_prompt(cases)
    contract = source_contract(args, prompt)
    if not args.prepare_only:
        if not args.manifest:
            raise ValueError('--manifest is required before an actual model invocation.')
        validate_manifest(args.manifest, contract, args.model)
        if not args.auth.is_file():
            raise ValueError('Existing auth.json is unavailable; no credentials were read.')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    snapshot = snapshot_sources(args, out)
    shared.save_json(out / 'freeze-contract.json', contract)
    shared.save_json(out / 'public-input.json', {'cases': cases})
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    meta = {'condition': args.condition, 'model_requested': args.model,
            'reasoning_effort': 'high', 'task_mode': 'generation', 'case_count': len(cases),
            'samples_per_condition': 1, 'prepared_only': args.prepare_only,
            'global_user_config_loaded': False, 'global_user_agents_loaded': False,
            'read_boundary_limit': BOUNDARY, 'trace_audit': 'required; not performed',
            'trace_audit_source': 'stdout.jsonl tool calls and results',
            'semantic_evaluation': 'not performed', 'automatic_fallback': False,
            'upstream_provider_observed': None, 'fallback_observed': None,
            'input_contract': contract}
    with tempfile.TemporaryDirectory(prefix='scope-condition-isolated-') as td:
        project = Path(td) / 'project'
        mounted = mount_condition(args.condition, snapshot, project)
        expected = dict(zip(MOUNT_PATHS, (contract['profile_sha256'], contract['core_sha256'],
                                         contract['software_sha256']))) if args.condition == 'treatment' else {}
        if mounted != expected:
            raise ValueError('Actual mounted files differ from frozen source hashes.')
        meta['mounted_files_sha256'] = mounted
        shared.save_json(out / 'mounted-inputs.json', {'condition': args.condition,
                         'files_sha256': mounted, 'workspace_path': str(project)})
        if args.prepare_only:
            shared.save_json(out / 'metadata.json', meta)
            return meta, None
        # Recheck after snapshot preparation, immediately before any CLI launch.
        validate_manifest(args.manifest, source_contract(args, prompt), args.model)
        env = {key: value for key, value in os.environ.items() if not key.startswith('CODEX_')}
        env['CODEX_HOME'] = str(shared.make_home(Path(td) / 'codex-home', args.auth))
        shared.save_json(out / 'metadata.json', meta)
        captured = shared.capture(make_command(project, out / 'final.txt', args.model),
                                  prompt, out, timeout=args.timeout, env=env)
        # The shared helper records a Sol default; preserve this invocation's requested model.
        meta = {**captured, **meta}
        meta['execution_completed'] = (meta['exit_code'] == 0 and not meta['timeout']
                                       and meta['launch_error'] is None)
        meta['authentication'] = 'existing auth.json symlink; credential contents never recorded'
        meta['mounted_files_sha256_after'] = mounted_hashes(project)
        meta['mounted_files_unchanged'] = mounted == meta['mounted_files_sha256_after']
    shared.save_json(out / 'metadata.json', meta)
    final = out / 'final.txt'
    parsed = parse_result(final.read_text(encoding='utf-8') if final.exists() else '', cases)
    shared.save_json(out / 'parsed.json', parsed)
    return meta, parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition', choices=('baseline', 'treatment'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=HERE / 'cases.json')
    parser.add_argument('--profile', type=Path, default=ROOT / 'profiles/coding-agent.md')
    parser.add_argument('--core', type=Path, default=ROOT / 'lexicon/core.json')
    parser.add_argument('--software', type=Path, default=ROOT / 'lexicon/domains/software.json')
    parser.add_argument('--plan', type=Path, default=HERE / 'plan.md')
    parser.add_argument('--adjudication', type=Path, default=HERE / 'gold-adjudication.json')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--model', choices=MODELS, default=MODELS[0])
    parser.add_argument('--auth', type=Path, default=Path.home() / '.codex/auth.json')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive.')
    try:
        meta, parsed = execute(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({'condition': args.condition, 'prepared_only': args.prepare_only,
                      'exit_code': meta.get('exit_code'),
                      'structure_valid': parsed['structure_valid'] if parsed else None}))
    if parsed is not None and (not meta['execution_completed'] or not parsed['structure_valid']
                               or not meta['mounted_files_unchanged']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
