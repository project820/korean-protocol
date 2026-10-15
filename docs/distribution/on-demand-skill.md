# 필요한 작업에서 Korean Protocol 스킬을 호출한다

Korean Protocol v0.8.0 스킬은 사용자가 선택한 한국어 작성·재작성 작업에 적용한다. **사용자 범위에 설치하고 명시적으로 호출**하는 방식이다. 신규 사용자는 [설치 안내](../../INSTALL.md)를 따른다. 기존 0.7 사용자는 먼저 [상시 지침을 OFF로 전환](../../INSTALL.md#기존-07-상시-지침에서-전환한다)한다.

## 설치 범위를 고른다

| 범위 | Codex | Claude Code |
| --- | --- | --- |
| 다른 프로젝트에서도 쓴다. | `~/.agents/skills/korean-protocol`에 설치한다. | `~/.claude/skills/korean-protocol`에 설치한다. 별도 `CLAUDE_CONFIG_DIR`이 있으면 그 아래 `skills/`를 사용한다. |
| 한 프로젝트에서만 쓴다. | 프로젝트의 `.agents/skills/korean-protocol`에 설치한다. | 프로젝트의 `.claude/skills/korean-protocol`에 설치한다. |

처음에는 사용자 범위를 권장한다. 같은 이름의 프로젝트 스킬이 이미 있으면 중복 발견·우선순위를 확인한 뒤 하나의 적용본을 선택한다. Codex는 같은 이름의 스킬을 병합하지 않는다. [Codex 문서](https://learn.chatgpt.com/docs/build-skills)와 [Claude Code 문서](https://code.claude.com/docs/en/skills)는 발견 위치와 명시적 호출을 설명한다.

## 검증한 파일을 복사한다

이 절은 **Python 3가 있는 로컬 환경의 사용자 범위 설치**다. [저장소 복제](../../INSTALL.md#v080-스킬을-설치한다)를 마친 저장소 루트에서 실행한다. 아래 명령은 0.7을 끄지 않으므로 기존 사용자는 전환 절차를 먼저 마친다. 다른 호스트·기기·사용자 계정에 자동 설치하지 않는다.

설치할 호스트 하나를 선택한다. 두 곳 모두 원하면 아래 복사 명령을 호스트별로 한 번씩 실행한다.

```sh
export KP_SKILL_HOST=codex
```

Claude Code를 선택하려면 위 명령 대신 다음을 사용한다.

```sh
export KP_SKILL_HOST=claude-code
```

다음 명령은 태그 `v0.8.0`에서 파일을 읽고 `SKILL.md` 해시를 대조한 뒤 복사한다. **기존 폴더나 링크가 있으면 덮어쓰지 않고 중단**한다. 기존 설치를 갱신할 때는 차이·출처·사용자 수정을 확인하고 백업한 뒤 별도로 교체한다.

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import os
import subprocess

version = 'v0.8.0'
expected = '3637cbb6c4efb79ed6d9ef059fdf17d64115bdd0574fd279876cd95d6137815a'
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

이 스킬은 명령·스크립트를 실행하는 설치기가 아니라 작성 지침이다. 위 Python은 파일 복사용 명령이며 호스트 지침·신뢰 키·예약 갱신 설정을 변경하지 않는다. 복사 중 오류가 나면 설치 완료로 표시하지 않고 대상 파일과 `INSTALLATION.json`을 확인한다.

Codex에는 `agents/openai.yaml`의 `allow_implicit_invocation: false`를 그대로 설치한다. Claude Code에는 수동 호출용 YAML 두 줄만 추가하며 검증한 규약 본문은 유지한다. 사전·규칙 참고 파일은 해당 판단이 필요할 때만 읽는다. 이 파일들이 빠지면 다른 프로젝트에서 조회 경로가 끊어지므로 `SKILL.md`만 복사하지 않는다.

## 설치와 호출을 확인한다

1. **파일을 확인한다.** `INSTALLATION.json`의 커밋·해시와 실제 파일을 대조한다. Codex는 원본 `SKILL.md`와 바이트가 같아야 한다. Claude Code는 수동 호출용 YAML 외의 본문이 같아야 한다.
2. **호스트에서 발견되는지 확인한다.** 새 대화의 스킬 목록에 `korean-protocol`이 있는지 본다. 다른 프로젝트에서도 쓰려면 그 프로젝트의 새 대화에서도 확인한다. 목록에 없으면 호스트를 다시 시작한다.
3. **명시적으로 호출한다.** 아래 요청문에 같은 원문을 붙인다.

| 호스트 | 호출문 |
| --- | --- |
| Codex | `$korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |
| Claude Code | `/korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |

```text
반납 대상은 노트북, 모니터, 출입카드이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다.
```

결과에서 물품 세 개가 앞쪽의 개별 목록에 있는지, 총무팀과 `7월 5일 18:00`이 유지되는지 확인한다. 파일·발견·로딩·출력은 각각 확인한다. 모델이 “적용했다”고 말한 것만으로 확인하지 않는다.

Codex에서 읽기 근거를 더 확인하려면 다음처럼 요청한다. 사용자 설치 경로를 대상으로 하며 프로젝트에 새 스킬을 만들지 않는다.

```text
$korean-protocol 설치된 사용자 스킬의 SKILL.md와 원문 전체를 읽고 정리해줘.
앞부분 발췌나 파일 크기 확인으로 읽기를 대신하지 마.
사실·조건·양태를 유지하고 결과 본문만 출력해줘.
```

도구 기록에서 읽은 경로와 전체 본문을 확인한다. Claude Code에서는 메시지 맨 앞의 `/korean-protocol`로 명시적 호출을 확인한다. 자동 호출을 끄면 Claude가 스스로 호출하는 방식은 사용하지 않는다.

## 적용을 선택하고 문체를 지정한다

스킬을 사용할 때는 호출하고, 사용하지 않을 때는 새 대화에서 호출하지 않는다. 호출 후 이미 읽은 규약은 대화에 남는다. “OFF”라고 말하거나 파일을 바꿔도 과거 컨텍스트가 지워지지 않는다.

높임말을 원하면 “높임말로 써줘”를 요청에 덧붙인다. 스킬은 기존 문서의 확립된 문체와 사용자의 지정 문체를 우선하며, 새 글은 별도 지정이 없으면 높임 없이 쓴다. 0.7 관리 도구의 높임말 설정은 스킬에 동기화되지 않는다.

## 갱신과 검증 범위를 확인한다

v0.8.0은 태그에 고정한 수동 설치다. 자동 갱신기를 등록하지 않는다. 새 버전은 파일 차이·검증 결과를 검토한 뒤 백업하고 교체한다. 0.7의 서명 검증·콘텐츠 갱신은 스킬에 적용되지 않는다.

[v0.8.0 비교 기록](../../evaluation/session-reports-20261015/README.md)은 실제 세션 보고서의 원문·KP·STE 1:1:1 결과다. `SKILL.md`는 `o200k_base` 7,410토큰, `cl100k_base` 11,368토큰이다. 호출하지 않은 대화에는 이 부담이 없다. 호출한 대화에는 원문·호스트 지침·도구·대화 이력이 더해진다.

로컬 macOS의 호스트 확인은 중간본 `909dc9d` 설치 때 수행했다. Codex의 두 임시 작업 폴더 발견, Codex·Claude Code의 짧은 실제 호출, Codex의 전체 파일 읽기를 해시로 대조했다. 이 확인은 다른 운영체제·계정·원격 호스트나 모든 문서의 품질을 보장하지 않는다.
