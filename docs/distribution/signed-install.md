# 서명된 Korean Protocol 0.7.0을 설치한다

이 경로는 로컬에서 신뢰한 키로 공개 콘텐츠를 인증한다. source는 `https://project820.github.io/korean-protocol`이며 [manifest](https://project820.github.io/korean-protocol/stable/release.json)가 0.7.0·순번 3을 제공한다. 신규·기존 설치의 기본 절차는 [INSTALL.md](../../INSTALL.md)를 따른다.

## 키와 입력을 확인한다

공개키는 `distribution/trust/publisher.pub`이고 지문은 다음과 같다.

```text
SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc
```

첫 신뢰 경계는 검토한 저장소다. 같은 미확인 출처에서 받은 키와 지문만으로 발행자를 독립 인증하지 못한다. 서버가 보낸 새 키로 기존 신뢰를 교체하지 않는다.

| 입력 | 설치 동작 |
| --- | --- |
| `--source` | HTTPS manifest와 서명을 먼저 인증한 뒤 일곱 콘텐츠의 해시·크기를 검증한다. |
| `--signed-directory` | [발행 도구](publisher.md)의 `seal` 결과인 `stable/`·`releases/` 폴더를 로컬에서 인증한다. |
| 두 옵션을 함께 지정한다. | 로컬 서명 폴더에서 설치하고 source는 이후 갱신 주소로 저장한다. |

[공개 ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip)은 실행 코드와 안내를 담은 미서명 패키지다. 서명 정적 폴더를 요구하는 `--signed-directory`에 ZIP의 압축 해제 폴더를 그대로 지정하지 않는다.

## 공개 HTTPS 주소에서 설치한다

macOS 예약 갱신을 선택한 Codex 예시다. Claude Code에는 `--host claude-code`를 사용하며 기존 설치에는 같은 홈·상태 경로도 전달한다.

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
```

`plan`은 임시 다운로드·검증만 수행한다. `install`은 다시 인증한 뒤 쓰고 요청한 예약 작업을 등록한다. `--autoupdate scheduled`만 지정하면 파일만 생성하므로 `scheduler.registered`도 확인한다. Linux에는 `interval` 또는 `off`를 사용하며 예약 등록 옵션을 빼라.

## 로컬 서명 폴더에서 설치한다

`SIGNED_DIRECTORY`를 실제 정적 폴더로 바꾼다. 이미 신뢰한 공개키와 지문은 같은 것을 사용한다.

```sh
python3 -B distribution/agent_install.py plan \
  --host codex \
  --signed-directory SIGNED_DIRECTORY \
  --trust-key distribution/trust/publisher.pub \
  --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc \
  --autoupdate off
python3 -B distribution/agent_install.py install \
  --host codex \
  --signed-directory SIGNED_DIRECTORY \
  --trust-key distribution/trust/publisher.pub \
  --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc \
  --autoupdate off
```

신규 수락에는 만료·발행 시각·순번·호환 검사를 적용한다. 기존 캐시의 만료는 이미 설치한 규약을 지우는 조건이 아니다.

## 갱신 실행 방식과 간격을 정한다

`interval`은 반환된 `runtime_argv.run` 뒤에 `--`와 실제 호스트 명령을 붙여 시작할 때만 주기를 확인한다. 평소 `codex`나 `claude` 명령은 이 wrapper를 호출하지 않는다.

macOS의 등록 작업은 로그인 시와 매시 정각에 실행 기회를 갖는다. 성공 후 기본 다운로드 간격은 24시간이며 실패하면 재시도 간격이 1·2·4·8·16·24시간으로 늘어난다. 수동 `update`는 대기 시간을 무시하지만 버전 pin은 해제하지 않는다.

간격은 1~168시간이다. 아래 두 경로를 설치 JSON의 `runtime_argv`에 나온 실제 값으로 바꾼다. 예시는 시작 wrapper 방식의 간격을 6시간으로 바꾼다.

```sh
KPROTO_RUNTIME="/설치결과/관리런타임/runtime/kproto.py"
KPROTO_STATE="/설치결과/상태/경로"
python3 -B "$KPROTO_RUNTIME" --state-dir "$KPROTO_STATE" autoupdate configure --mode interval --interval-hours 6
```

예약 방식을 유지하려면 같은 런타임에 `autoupdate configure --mode scheduled --interval-hours 6`를 실행한 뒤 반환된 `scheduler_register`와 `scheduler_status`로 등록·소유 상태를 확인한다. 이미 다음 시도 시각이 정해졌으면 간격 변경만으로 즉시 다운로드된다고 설명하지 않는다.

자동 조회를 멈추려면 반환된 `runtime_commands.configure_off`를 사용한다. 이 OFF에서도 명시적인 수동 `update`는 원격 작업을 수행한다. 등록된 예약 작업은 소유권을 검사한 뒤 해제하며 수정된 외부 작업은 보존한다. 개인 endpoint의 shell 토큰을 LaunchAgent에 복사하지 않으며 `token_env`가 있으면 자동 등록을 거부한다.

## 기존 설치와 현재 대화를 보존한다

0.7.0 콘텐츠는 엔진 0.2.0 이상을 요구한다. 기존 엔진 0.1.0은 관리 도구를 먼저 [명시적으로 재설치](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)해야 한다. 서명 재설치에서 자동 갱신 옵션을 생략하면 `off`로 재설정된다.

재설치는 같은 호스트·홈·상태 폴더·신뢰 키를 사용한다. 규약·높임말 선택과 사용자 본문은 보존하며 직접 만든 외부 wrapper는 새 `runtime_argv.run`으로 교체한다. 기존 서명 설치를 미서명 로컬 snapshot으로 덮어쓰지 않는다.

`status`로 캐시·대상·복구 상태를 확인하고 현재 대화에는 그 검증 캐시만 참조한다. 규약 OFF이면 설치됐다는 이유로 적용하지 않는다. 새 세션 로딩·모델 준수·독자 이해도는 파일 인증과 별도다.

## 현재 증거와 과거 시험을 구분한다

[0.7.0 발행·갱신 기록](public-0.7.0-verification.md)은 게시자 서명·실제 HTTPS 갱신을 다룬다. [공개 예약 시험](public-scheduler-verification.json)은 이전 0.2.0 당시의 같은 버전 확인이며 0.7.0의 예약 업그레이드·재로그인·절전 복귀를 검증한 결과가 아니다. 현재 언어 효과와 미확인 범위는 [현재 검증 상태](../status/requirements.md)를 따른다.
