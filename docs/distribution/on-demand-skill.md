# 필요한 작업에서 Korean Protocol 스킬을 호출한다

원문·KP·STE 정식 비교는 **미완료**다.

**Korean Protocol v0.11.0은 사용자 범위에 설치하고 명시적으로 호출한다.**
[설치 안내](../../INSTALL.md)에 따라 파일 13개를 함께 복사한다.
기존 0.7 사용자는 먼저 [상시 지침을 OFF로 전환](../../INSTALL.md#기존-07-상시-지침에서-전환한다)한다.

## 준비: 설치 범위를 고른다

| 범위 | Codex | Claude Code |
| --- | --- | --- |
| 다른 프로젝트에서도 쓴다. | `~/.agents/skills/korean-protocol`에 설치한다. | `~/.claude/skills/korean-protocol`에 설치한다. 별도 `CLAUDE_CONFIG_DIR`이 있으면 그 아래 `skills/`를 사용한다. |
| 한 프로젝트에서만 쓴다. | 프로젝트의 `.agents/skills/korean-protocol`에 설치한다. | 프로젝트의 `.claude/skills/korean-protocol`에 설치한다. |

처음에는 사용자 범위를 권장한다.
같은 이름의 프로젝트 스킬이 있으면 우선순위를 확인하고 적용본 하나를 선택한다.
Codex는 같은 이름의 스킬을 병합하지 않는다.

[Codex 문서](https://learn.chatgpt.com/docs/build-skills)와 [Claude Code 문서](https://code.claude.com/docs/en/skills)에서 발견 위치와 호출 설정을 확인한다.

## 검증한 파일을 복사한다

이 절은 **Python 3가 있는 로컬 환경의 사용자 범위 설치**다.
[저장소 복제](../../INSTALL.md#v0110-스킬을-설치한다)를 마친 저장소 루트에서 실행한다.
아래 명령은 0.7을 끄지 않으므로 기존 사용자는 전환을 먼저 마친다.

설치할 호스트 하나를 선택한다. 두 곳 모두 원하면 아래 복사 명령을 호스트별로 한 번씩 실행한다.

```sh
export KP_SKILL_HOST=codex
```

Claude Code를 선택하려면 위 명령 대신 다음을 사용한다.

```sh
export KP_SKILL_HOST=claude-code
```

다음 명령은 태그 `v0.11.0`에서 파일을 읽고 해시를 대조한다.
**기존 폴더나 링크가 있으면 중단한다.**
기존 스킬은 아래 갱신 절차를 먼저 따른다.

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import os
import subprocess

version = 'v0.11.0'
expected = 'c09172014b872636afad1cac194e9c634a99e9fe165711cdd405a5249dd983c6'
host = os.environ.get('KP_SKILL_HOST')
if host not in ('codex', 'claude-code'):
    raise SystemExit('KP_SKILL_HOST를 codex 또는 claude-code로 지정한다.')
try:
    revision = subprocess.check_output(
        ['git', 'rev-parse', '--verify', f'{version}^{{commit}}'], text=True).strip()
except subprocess.CalledProcessError:
    raise SystemExit(f'태그 {version}이 없다. 저장소를 새로 복제하거나 git fetch --tags를 실행한다.')
if host == 'codex':
    target = Path.home() / '.agents/skills/korean-protocol'
else:
    config = Path(os.environ.get('CLAUDE_CONFIG_DIR') or str(Path.home() / '.claude'))
    target = config / 'skills/korean-protocol'
if target.exists() or target.is_symlink():
    raise SystemExit(f'기존 설치를 보존한다. 차이 확인과 백업이 필요하다: {target}')

files = {
    'SKILL.md': 'skills/korean-protocol/SKILL.md',
    'agents/openai.yaml': 'skills/korean-protocol/agents/openai.yaml',
    'references/meaning-boundaries.md': 'skills/korean-protocol/references/meaning-boundaries.md',
    'references/output-formats.md': 'skills/korean-protocol/references/output-formats.md',
    'references/interactive-html.md': 'skills/korean-protocol/references/interactive-html.md',
    'references/video-script.md': 'skills/korean-protocol/references/video-script.md',
    'assets/interactive-explainer.html': 'skills/korean-protocol/assets/interactive-explainer.html',
    'scripts/check_html.py': 'skills/korean-protocol/scripts/check_html.py',
    'specification/rules.json': 'specification/rules.json',
    'lexicon/core.json': 'lexicon/core.json',
    'lexicon/domains/software.json': 'lexicon/domains/software.json',
    'LICENSE': 'LICENSE',
    'NOTICE.md': 'NOTICE.md',
}
contents = {name: subprocess.check_output(['git', 'show', f'{revision}:{source}'])
            for name, source in files.items()}
skill = contents['SKILL.md']
if hashlib.sha256(skill).hexdigest() != expected:
    raise SystemExit('검증한 규약 해시와 다르므로 설치를 중단한다.')
if host == 'claude-code':
    contents['SKILL.md'] = skill.replace(
        b'---\n',
        b'---\ndisable-model-invocation: true\nuser-invocable: true\n', 1)
    assert contents['SKILL.md'].split(b'---\n', 2)[2] == skill.split(b'---\n', 2)[2]

target.mkdir(parents=True)
for name, data in contents.items():
    path = target / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
manifest = {
    'version': version,
    'source_commit': revision,
    'host': host,
    'source_profile_sha256': expected,
    'explicit_only': True,
    'files': {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
}
(target / 'INSTALLATION.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'설치 파일을 복사했다: {target}')
print('새 대화에서 스킬 발견과 실제 호출을 확인한다.')
PY
```

위 Python은 파일 복사용 명령이다.
호스트 지침·신뢰 키·예약 갱신 설정은 보존한다.
복사 중 오류가 나면 대상 파일과 `INSTALLATION.json`을 확인한다.

Codex는 `agents/openai.yaml`의 `allow_implicit_invocation: false`를 그대로 설치한다.
Claude Code에는 수동 호출용 YAML 두 줄만 추가한다.
검증한 규약 본문은 유지한다.

다른 프로젝트에서 참고 파일을 읽을 수 있도록 파일 13개를 함께 복사한다.

## 설치와 호출을 확인한다

1. **파일을 확인한다.**
   `INSTALLATION.json`의 커밋·해시와 실제 파일을 대조한다.
   Codex는 원본 `SKILL.md`와 바이트가 같아야 한다.
   Claude Code는 수동 호출용 YAML 외의 본문이 같아야 한다.
2. **호스트에서 발견되는지 확인한다.**
   새 대화의 스킬 목록에 `korean-protocol`이 있는지 본다.
   다른 프로젝트에서도 그 프로젝트의 새 대화에서 확인한다.
   목록에 없으면 호스트를 다시 시작한다.
3. **명시적으로 호출한다.**
   아래 요청문에 같은 원문을 붙인다.

| 호스트 | 호출문 |
| --- | --- |
| Codex | `$korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |
| Claude Code | `/korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |

```text
반납 대상은 노트북, 모니터, 출입카드이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다.
```

물품 세 개가 앞쪽의 개별 목록에 있는지 확인한다.
총무팀과 `7월 5일 18:00`의 보존을 확인한다.
모델의 자기 선언만으로 적용을 확인하지 않는다.

Codex에서 읽기 근거를 더 확인하려면 다음처럼 요청한다. 사용자 설치 경로를 대상으로 하며 프로젝트에 새 스킬을 만들지 않는다.

```text
$korean-protocol 설치된 사용자 스킬의 SKILL.md와 원문 전체를 읽고 정리해줘.
앞부분 발췌나 파일 크기 확인으로 읽기를 대신하지 마.
사실·조건·양태를 유지하고 결과 본문만 출력해줘.
```

도구 기록에서 읽은 경로와 전체 본문을 확인한다.
Claude Code는 메시지 맨 앞의 `/korean-protocol`로 명시적 호출을 확인한다.

## 적용을 선택하고 문체를 지정한다

사용을 멈출 때는 새 대화에서 호출하지 않는다.
호출 후 이미 읽은 규약은 현재 대화에 남는다.

높임말을 원하면 “높임말로 써줘”를 요청에 덧붙인다.
기존 문서의 확립된 문체와 사용자의 지정 문체를 우선한다.
새 글은 별도 지정이 없으면 높임 없이 쓴다.

## 기존 v0.10.1 스킬이 있으면 갱신한다

스킬은 태그에 고정한 **수동 설치**다. 자동 갱신기는 없다.

1. **기존 설치의 출처와 차이를 확인한다.**
   `INSTALLATION.json`의 커밋과 사용자 수정 내용을 확인한다.
2. **기존 스킬 폴더를 백업한다.**
   원래 설치 경로를 비운 뒤 위 복사 명령을 실행한다.
3. **새 설치의 파일과 호출을 확인한다.**
   위 확인 절차를 새 대화에서 수행한다.

## v0.11.0의 검증 범위를 확인한다

v0.11.0은 0절 “읽는 형태를 맞춘다”를 추가했다.
작업 결과 보고의 요청자 결정 사항은 마지막 절에 둔다.
설치 파일 구성은 v0.10.1과 같으며 `SKILL.md`만 바뀌었다.

[진단용 파일럿](../../evaluation/kp-lean-pilot-20261113/README.md)에서 사용자가 2026-11-13에 후보 5를 채택했다.
모델 검토의 수락 기준을 통과해 채택한 결과가 아니다.

| 비교군 | 의미 통과 | 1,000자당 문체 위반 |
| --- | --- | --- |
| v0.11.0 | 17/20 | 2.3 |
| v0.10.1 | 19/20 | 4.6 |
| STE | 17/20 | 3.7 |

같은 조건으로 생성한 사례 5개·모델 4개·반복 1회의 진단이다.
검토 모델은 1개이며 후보와 검토 기준에 같은 사용자 의견을 반영했다.
명료성 수치는 후보에 유리하고 일부 예시도 파일럿 사례에서 왔다.

- **의미 실패:** 시험 결과의 한정 조건을 참고로 옮긴 1건이 남았다.
- **의미 실패:** 원문에 없는 관계·결정을 만든 2건이 남았다.
- **읽기 시간:** 사람 읽기 시간은 **미측정**이다.

## 참고

`SKILL.md`는 `o200k_base` 6,453토큰, `cl100k_base` 9,729토큰이다.
크기는 이전 버전보다 약 38% 늘었다.
호출한 대화에는 원문과 호스트 지침·도구·대화 이력이 더해진다.

의미 경계 참고 파일은 판단이 헷갈릴 때만 읽는다.
출력 형식 참조는 해당 형식을 선택할 때만 읽는다.
0.7의 서명 검증·콘텐츠 갱신·높임말 설정은 스킬에 적용되지 않는다.

**과거 기록:** v0.10.0·v0.10.1의 비교 상태는 [변경·검증 상태](output-formats-candidate-status.md)에 남겼다.
후보 ZIP의 검증·설치 조건은 [패키지 기록](output-formats-package.md)에 남겼다.
[v0.9.0 비교](../../evaluation/clarity-20261016-r60/README.md)는 수락 기준을 통과하지 못했다.

로컬 macOS 호스트 확인은 중간본 `909dc9d` 설치 때 수행했다.
Codex의 임시 작업 폴더 2곳에서 스킬 발견을 확인했다.
Codex·Claude Code의 짧은 호출과 Codex의 전체 파일 읽기를 확인했다.
이 기록은 v0.11.0 설치·호출 검증을 대신하지 않는다.
