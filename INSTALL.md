# Korean Protocol을 스킬로 설치하고 호출한다

신규 사용자는 **Korean Protocol v0.8.0 호출형 스킬**을 설치한다. 사용자 범위에 설치하면 같은 컴퓨터·사용자 계정의 다른 프로젝트에서도 쓴다. 기존 **v0.7.0 상시 지침과는 별개**다. 0.7 ZIP·서명 콘텐츠·자동 갱신기에는 이 스킬이 없다.

## 설치할 호스트를 고른다

| 호스트 | 사용자 스킬 위치 | 호출문 |
| --- | --- | --- |
| Codex | `~/.agents/skills/korean-protocol/` | `$korean-protocol 이 보고서를 정리해줘.` |
| Claude Code | `~/.claude/skills/korean-protocol/` | `/korean-protocol 이 보고서를 정리해줘.` |

사용자가 요청한 호스트만 설치한다. 두 곳 모두 요청받으면 각 위치에 설치한다. Claude Code가 별도 `CLAUDE_CONFIG_DIR`을 쓰면 그 설정 디렉터리의 `skills/`를 사용한다. 다른 기기·원격 호스트·ChatGPT로 자동 전달하지 않는다. [공식 Codex 위치](https://learn.chatgpt.com/docs/build-skills)와 [Claude Code 위치·호출 설정](https://code.claude.com/docs/en/skills)을 따른다.

## v0.8.0 스킬을 설치한다

1. 아래 **기존 0.7 전환 절차**로 상시 설치 여부를 확인한다. 설치가 있으면 규약만 OFF로 전환한다.
2. 저장소 태그 `v0.8.0`에서 스킬과 참고 파일을 함께 복사한다.
3. Codex의 `allow_implicit_invocation: false`를 유지한다. Claude Code에는 `disable-model-invocation: true`와 `user-invocable: true`를 YAML에 추가한다. 규약 본문은 바꾸지 않는다.
4. 새 대화에서 스킬 발견과 짧은 실제 호출을 확인한다.

설치 기준은 태그와 `SKILL.md`의 SHA-256이다. 이동하는 `main`을 설치 기준으로 쓰지 않는다.

```text
태그: v0.8.0
SKILL.md SHA-256: 3637cbb6c4efb79ed6d9ef059fdf17d64115bdd0574fd279876cd95d6137815a
```

새 디렉터리에 복제한다. 이미 복제한 저장소의 변경 사항을 지우거나 강제로 덮어쓰지 않는다.

```sh
git clone https://github.com/project820/korean-protocol.git korean-protocol-skill
cd korean-protocol-skill
git checkout --detach v0.8.0
```

[수동 복사 명령](docs/distribution/on-demand-skill.md#검증한-파일을-복사한다)은 태그의 파일을 읽고 해시를 대조한 뒤 사용자 범위에 설치한다. 기존 폴더가 있으면 중단한다. 파일을 직접 복사할 때도 아래 파일 목록과 호스트 설정을 따른다.

| 원본 파일 | 스킬 폴더에 둘 위치 |
| --- | --- |
| `skills/korean-protocol/SKILL.md` | `SKILL.md` |
| `skills/korean-protocol/agents/openai.yaml` | `agents/openai.yaml` |
| `specification/rules.json` | `specification/rules.json` |
| `lexicon/core.json` | `lexicon/core.json` |
| `lexicon/domains/software.json` | `lexicon/domains/software.json` |
| `LICENSE`·`NOTICE.md` | 같은 파일명을 유지한다. |

참고 파일은 드문 표현 판단에만 조회하며 매번 전체를 읽지 않는다. 설치 폴더가 있으면 차이와 출처를 먼저 확인한다. 기존 파일은 백업하고 사용자의 수정 여부를 확인하기 전까지 교체하지 않는다.

## 기존 0.7 상시 지침에서 전환한다

**스킬 폴더를 복사하는 것만으로 0.7이 꺼지지는 않는다.** 아래 순서로 중복 적용을 없앤다.

1. 기존 설치의 `management_commands.status`를 실행해 호스트·홈·`state_dir`·대상 파일·`installed`·`enabled`·`honorifics`·`autoupdate`를 기록한다. 별도 홈·상태 경로는 그대로 사용한다.
2. `installed=true`이면 같은 설치의 `management_commands.protocol_off`를 실행한다. 규약만 끄며 높임말·신뢰 키·캐시·자동 갱신 선택은 보존한다. 제거 또는 재설치를 전환의 기본 절차로 사용하지 않는다.
3. 같은 `status`에서 `installed=true`, `enabled=false`와 대상 경로를 확인한다. 높임말·자동 갱신 선택이 이전과 같은지도 확인한다. `verified=false`만 보고 실패라고 판단하지 않는다. OFF일 때의 [상태 의미](docs/distribution/application-controls.md#상태를-구분한다)를 따른다.
4. 새 스킬을 설치한 뒤 **새 대화**에서 호출한다. 이미 열린 대화에 읽힌 0.7 지침은 파일 변경으로 지워지지 않는다.

기본 경로의 Codex 설치를 확인·전환할 때는 검토한 checkout에서 다음 명령을 사용한다. `configure`는 **앞의 상태에서 설치를 확인했을 때만** 실행한다.

```sh
python3 -B distribution/agent_install.py status --host codex
```

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol off
python3 -B distribution/agent_install.py status --host codex
```

Claude Code는 모든 명령의 `--host codex`를 `--host claude-code`로 바꾼다. 별도 설치는 기존 `--codex-home` 또는 `--claude-home`과 `--state-dir`을 모든 명령에 동일하게 전달한다. 관리 명령이 실패하거나 대상이 다르면 중단하고 경로·소유권을 확인한다. 새 설치로 덮어쓰거나 관리 블록을 임의 편집하지 않는다.

`installed=false`이면 **그 조회 경로에는 설치가 없다는 뜻**이다. 다른 사용자 홈, 별도 상태 폴더, 프로젝트의 `AGENTS.md`·`AGENTS.override.md`·`CLAUDE.md`·`.claude/rules/`에 직접 넣은 0.7 지침도 확인한다. 활성 0.7 블록이 있으면 그 블록만 백업해 비활성화하고 다른 지침은 보존한다. 경로를 확인하기 전까지 없는 설치를 새로 만들지 않는다. 평가 스냅샷과 과거 기록을 활성 지침으로 오인해 삭제하지 않는다.

0.7의 자동 갱신은 OFF 선택을 보존하지만 새 스킬을 갱신하지 않는다. 스킬 사용 중 0.7을 다시 ON으로 켜면 중복 적용된다. 0.7로 돌아가려면 스킬을 호출하지 않는 새 대화에서 기존 설치의 `protocol_on`을 선택한다. [기존 0.7 관리 설정](docs/distribution/application-controls.md)을 따른다.

## 설치 후 호출하고 확인한다

| 호스트 | 새 대화에 입력한다. |
| --- | --- |
| Codex | `$korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |
| Claude Code | `/korean-protocol 아래 원문을 의미와 조건을 유지하며 정리해줘.` |

호출문 뒤에 원문이나 파일을 제공한다. 자동 호출은 꺼 두며, 사용하지 않을 때는 새 대화에서 호출하지 않는다. 높임말은 “높임말로 써줘”처럼 요청한다. 0.7의 높임말 설정을 스킬이 읽거나 동기화하지 않는다.

[확인 예문](docs/distribution/on-demand-skill.md#설치와-호출을-확인한다)으로 파일·발견·호출·출력을 나눠 검사한다. 스킬 목록에 없으면 호스트를 다시 시작한다. 모델의 자기 선언만으로 적용을 확인하지 않는다.

## 갱신과 검증 범위를 구분한다

스킬은 태그 `v0.8.0`에 고정한 **수동 설치**다. 자동 갱신하지 않는다. 새 버전으로 바꾸려면 설치 파일의 출처·차이를 확인하고 백업한 뒤 교체한다. 서명된 0.7 콘텐츠의 발행자 인증이나 자동 갱신은 이 복사본에 적용되지 않는다.

중간본 `909dc9d` 스킬을 설치한 사용자는 기존 폴더를 백업한 뒤 위 절차로 v0.8.0 파일을 복사한다. 두 설치의 `INSTALLATION.json`에 남은 커밋으로 출처를 구분한다.

v0.8.0의 [원문·KP·STE 1:1:1 비교](evaluation/session-reports-20261015/README.md)와 호스트 설치 확인은 별도다. 비교 결과는 모든 호스트·운영체제·문서의 준수를 입증하지 않는다. ChatGPT와 기존 0.7 오프라인 패키지는 아래의 기존 관리 경로를 사용한다.

<details>
<summary>기존 0.7 상시 설치·서명·자동 갱신 명령을 확인한다.</summary>

## 기존 0.7 관리 절차를 사용한다

이하 명령은 **기존 0.7 상시 지침을 유지·복구할 때만** 사용한다. 새 스킬 설치·전환 절차가 아니다. 0.7 ZIP에서 이 문서를 열었다면 ZIP의 `START-HERE.md`와 아래 관리 절차를 따른다. 스킬을 사용하려면 위의 저장소 기반 설치를 선택한다.

## 설치 전 조건을 확인한다

사용자가 설치를 요청한 Codex 또는 Claude Code 한 곳에 설치한다. 저장소 열람만으로 설치하지 않는다. Python 3.9 이상과 POSIX 환경이 필요하며 서명 설치에는 OpenSSH `ssh-keygen`도 필요하다.

<a id="사용할-경로를-고른다"></a>

## 기존 0.7의 설치 경로를 고른다

| 목적 | 경로와 결과 |
| --- | --- |
| 코딩 에이전트에 새로 설치한다. | 아래 공개 HTTPS 서명 설치를 따른다. |
| 기존 설치를 갱신한다. | 기존 설치의 관리 도구를 먼저 갱신하고 같은 호스트·홈·상태 경로를 사용한다. |
| 네트워크 없이 설치한다. | [공개 ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip)의 미서명 로컬 설치를 선택한다. |
| ChatGPT에서 사용한다. | [채팅용 파일](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md)을 받고 [시작 안내](distribution/CHAT-START.md)를 따른다. 로컬 설치 명령을 실행하지 않는다. |

규약 원본은 `0.7.0-draft`, 공개 콘텐츠는 `0.7.0·순번 3`, 관리 엔진은 `0.2.0`이다. 서로 다른 버전 번호를 설치 실패로 오인하지 않는다. 데이터·호환 계약은 [배포 계약](docs/distribution/README.md)을 따른다.

공개 [v0.7.0 릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)의 ZIP·채팅 파일·[SHA256SUMS](https://github.com/project820/korean-protocol/releases/download/v0.7.0/SHA256SUMS)는 원본 `7e01d53`의 고정 산출물이다. 최신 main 문서의 수정이 이미 그 파일에 들어 있다고 설명하지 않는다. 체크섬은 손상 확인용이며 발행자 서명이 아니다.

## 설치할 에이전트와 경로를 정한다

현재 도구가 Codex이면 `--host codex`, Claude Code이면 `--host claude-code`를 사용한다. 두 CLI가 있다는 이유로 둘 다 바꾸지 않는다. 대상 도구를 식별할 수 없을 때만 사용자에게 확인한다.

검토한 저장소 복제본에서 명령을 실행한다.

```sh
git clone https://github.com/project820/korean-protocol.git
cd korean-protocol
```

Codex의 기본 홈은 `CODEX_HOME` 또는 `~/.codex`, Claude Code의 기본 홈은 `CLAUDE_CONFIG_DIR` 또는 `~/.claude`다. 기본 상태 폴더는 호스트별로 분리한다. 별도 경로를 썼으면 모든 명령에 같은 `--codex-home` 또는 `--claude-home`과 `--state-dir`을 전달한다. 설치·갱신·제거 중 발견된 다른 홈으로 임의 이동하지 않는다.

## 신뢰 기준을 확인한다

저장소의 `distribution/trust/publisher.pub`와 다음 지문을 사용한다.

```text
SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc
```

첫 신뢰 경계는 검토한 `https://github.com/project820/korean-protocol` 저장소다. 같은 미확인 출처에서 받은 키와 지문만으로 발행자를 독립 인증하지 못한다. 기존 설치의 키를 배포 서버가 보낸 다른 키로 교체하지 않는다.

## 기존 설치의 관리 도구를 먼저 갱신한다

먼저 기존 관리 명령의 `status`로 호스트·홈·상태 폴더·신뢰 방식·규약·높임말·자동 갱신 상태를 확인한다. 상태 확인이 실패하면 경로나 소유권 문제를 해결하기 전에 새 설치로 덮어쓰지 않는다.

콘텐츠 0.7.0은 엔진 0.2.0 이상을 요구한다. 엔진 0.1.0은 새 콘텐츠를 거부하고 기존 설치본을 유지하며 콘텐츠 자동 갱신은 관리 코드를 바꾸지 않는다. 검토한 최신 설치 도구에서 아래 `install`을 같은 경로로 다시 실행해 관리 도구를 갱신한다.

규약·높임말 선택과 사용자 본문은 보존한다. **서명 재설치의 자동 갱신 방식은 이번 `--autoupdate` 값으로 다시 설정하며 생략하면 `off`가 된다.** 기존 예약 갱신을 유지하려면 `scheduled --register-scheduler`를, 시작 wrapper를 유지하려면 `interval`을 명시한다. 기존 갱신 시간 간격은 상태 폴더에 보존하지만 재설치 후 연결 상태도 다시 확인한다.

기존 서명 설치를 서명 옵션 없는 로컬 설치로 바꾸지 않는다. 기존 미서명 설치의 신뢰 방식을 유지하려면 같은 경로에서 아래 로컬 설치를 사용한다. 서명 방식으로 전환하라는 요청이 있을 때만 검토한 키·지문을 명시한다.

## 공개 배포에서 서명 설치한다

source는 `https://project820.github.io/korean-protocol`이다. [현재 manifest](https://project820.github.io/korean-protocol/stable/release.json)를 콘텐츠보다 먼저 인증하며 결과의 실제 버전을 확인한다. 아래는 macOS에서 예약 갱신을 선택한 Codex 예시다.

```sh
python3 -B distribution/agent_install.py plan \
  --host codex \
  --source https://project820.github.io/korean-protocol \
  --trust-key distribution/trust/publisher.pub \
  --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc \
  --autoupdate scheduled \
  --register-scheduler
python3 -B distribution/agent_install.py install \
  --host codex \
  --source https://project820.github.io/korean-protocol \
  --trust-key distribution/trust/publisher.pub \
  --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc \
  --autoupdate scheduled \
  --register-scheduler
python3 -B distribution/agent_install.py status --host codex
```

Claude Code에는 모든 명령의 `--host claude-code`를 사용한다. ZIP에서는 `distribution/agent_install.py` 대신 루트 `agent-install.py`를 사용한다. 각 명령은 JSON을 출력하며 실패 종료 코드와 원인을 그대로 보고한다.

`plan`은 임시 다운로드·검증만 수행하며 호스트 지침·설치 상태·예약 작업을 바꾸지 않는다. `install`은 다시 검증한 뒤 설치한다. 잘못된 서명·다른 키·만료·주소·호환 오류를 성공으로 표시하지 않는다.

## 자동 갱신 방식과 간격을 선택한다

| 선택 | 설치 옵션과 실제 동작 |
| --- | --- |
| macOS 예약 갱신을 사용한다. | `--autoupdate scheduled --register-scheduler`를 함께 지정한다. 등록 작업은 로그인 시와 매시 정각에 갱신 시각을 확인한다. |
| 호스트 시작 때 확인한다. | `--autoupdate interval`을 지정한다. 반환된 `runtime_argv.run` 뒤에 `--`와 실제 `codex` 또는 `claude` 명령을 붙여 실행한다. 평소 호스트 명령만 실행하면 갱신 wrapper를 거치지 않는다. |
| 자동 조회를 끈다. | `--autoupdate off`를 지정하고 `--register-scheduler`를 빼라. 명시적인 수동 `update`는 별도 원격 작업이다. |

기본 성공 갱신 간격은 24시간이며 관리 런타임의 `autoupdate configure --interval-hours`로 1~168시간을 선택한다. 간격과 실제 실행 기회를 구분하며 Linux에는 시작 wrapper만 제공한다. 명령과 예약 재등록 절차는 [서명 설치 안내](docs/distribution/signed-install.md)를 따른다. `scheduler.registered=false`를 등록 성공으로 보고하지 않는다.

## 오프라인 미서명 설치를 명시적으로 선택한다

로컬 원본 또는 압축을 푼 ZIP을 사용한다. 이 경로는 `trust=local-snapshot`, 콘텐츠 0.7.0으로 기록하며 자동 갱신을 끈다. 발행자 인증으로 보고하지 않는다.

```sh
python3 -B distribution/agent_install.py plan --host codex
python3 -B distribution/agent_install.py install --host codex
python3 -B distribution/agent_install.py status --host codex
```

ZIP에서는 루트 `agent-install.py`를 실행한다. 메뉴를 선호하면 ZIP 루트의 `python3 start.py`를 사용한다. 이미 검증한 정적 서명 폴더가 있으면 [`--signed-directory` 경로](docs/distribution/signed-install.md#로컬-서명-폴더에서-설치한다)로 오프라인 서명 설치도 할 수 있다.

## 설치 결과를 확인하고 현재 대화에 적용한다

`status`에서 `installed`, `version`, `trust`, `enabled`, `honorifics`, `content_verified`, `verified`, `target_matches`, `recovery_required`와 자동 갱신 연결을 함께 확인한다. 규약 OFF이면 콘텐츠 검증에 성공해도 `verified=false`일 수 있다. [설정별 상태 의미](docs/distribution/application-controls.md)를 따른다.

현재 대화에 적용할 때는 상태 검사를 통과한 설치 대상의 관리 본문과 `state_dir/releases/<cache_id>/profiles/coding-agent.md`를 참조한다. 사전도 같은 검증 캐시의 `lexicon/`에서 읽는다. 미검증 checkout의 프로필을 설치본이라고 간주하지 않으며 규약 OFF이면 임의로 켜지 않는다. 사용자 요청과 상위 지침은 계속 따른다.

새 세션은 호스트가 발견하는 설치 지침을 읽는다. 새 세션의 로딩 정보나 읽기 기록을 확인할 수 있을 때 그 근거를 보고하며, 근거가 없으면 로딩을 확인하지 못했다고 보고한다. 모델의 자기 선언이나 짧은 샘플 출력만으로 로딩을 증명하지 않는다. 파일 검증과 실제 모델의 모든 규칙 준수는 별개다. 설치 버전·대상·신뢰 방식·설정·갱신 연결과 새 세션 안내를 보고하고 반환된 `management_commands`와 `runtime_argv`를 남긴다. 이 지속 관리 도구는 원래 복제본이 없어져도 사용할 수 있다.

<a id="설치-후-사용과-onoff를-먼저-확인한다"></a>

## 규약 적용과 높임말을 바꾼다

신규 설치의 기본값은 규약 ON·높임말 OFF다. 기존 설치는 현재 선택을 보존한다.

규약을 끄려면 다음 명령을 선택한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol off
```

규약만 켜려면 다음 명령을 선택한다. 앞의 끄기 명령과 연속 실행하는 절차가 아니다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol on
```

높임말만 바꾸려면 원하는 명령 하나를 선택한다. 규약 ON/OFF는 유지한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --honorifics on
```

```sh
python3 -B distribution/agent_install.py configure --host codex --honorifics off
```

선택한 변경 뒤 같은 경로의 상태를 확인한다.

```sh
python3 -B distribution/agent_install.py status --host codex
```

규약 OFF와 자동 갱신 OFF는 서로 다르다. 진행 중인 대화의 지침을 파일 변경으로 지울 수 없으므로 새 세션에서 확인한다. 자세한 상태·명령은 [적용 설정](docs/distribution/application-controls.md)을 따른다.

## 설치를 관리하거나 제거한다

요청한 설치만 반환된 지속 관리 도구의 `uninstall`로 제거한다. 저장소가 남아 있으면 같은 홈·상태 경로를 지정해 다음 명령도 사용할 수 있다.

```sh
python3 -B distribution/agent_install.py uninstall --host codex
```

소유한 규약 관리 블록과 예약 연결만 제거하며 사용자 본문·상태·백업·캐시·관리 도구는 보존한다. 관리 본문이나 예약 파일이 수정됐으면 덮어쓰지 않고 충돌을 보고한다.

직접 작성한 코드·규약·사전·문서는 MIT License로 제공한다. 재배포할 때 저장소·ZIP의 `LICENSE`와 `NOTICE.md`, 캐시와 지속 관리 코드의 고지를 함께 보존한다. 제3자 ASD-STE100 자료의 권리는 바뀌지 않는다.

</details>
