# 에이전트가 Korean Protocol 0.7.0을 설치한다

사용자가 설치를 요청한 Codex 또는 Claude Code 한 곳에 설치한다. 저장소 열람만으로 설치하지 않는다. Python 3.9 이상과 POSIX 환경이 필요하며 서명 설치에는 OpenSSH `ssh-keygen`도 필요하다.

## 사용할 경로를 고른다

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

새 세션은 호스트가 발견하는 설치 지침을 읽는다. 파일 검증과 실제 모델의 모든 규칙 준수는 별개다. 설치 버전·대상·신뢰 방식·설정·갱신 연결과 새 세션 안내를 보고하고 반환된 `management_commands`와 `runtime_argv`를 남긴다. 이 지속 관리 도구는 원래 복제본이 없어져도 사용할 수 있다.

## 규약 적용과 높임말을 바꾼다

신규 설치의 기본값은 규약 ON·높임말 OFF다. 기존 설치는 현재 선택을 보존한다.

규약을 끄려면 다음 명령을 선택한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol off
```

규약을 켜고 높임말도 켜려면 다음 명령을 선택한다. 앞의 끄기 명령과 연속 실행하는 절차가 아니다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol on --honorifics on
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
