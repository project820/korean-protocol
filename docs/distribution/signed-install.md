# 서명 배포물에서 설치한다

이 경로는 발행자가 서명한 배포물을 저장소의 공개키와 지문으로 검증해 설치한다. 공개 HTTPS 배포 주소는 `https://project820.github.io/korean-protocol`이며, 공개키는 `distribution/trust/publisher.pub`, 지문은 `SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc`이다. 에이전트 설치 절차는 [INSTALL.md](../../INSTALL.md)를 따른다.

현재 원본 0.7.0-draft는 V7 r2를 채택한다. 아래 명령은 공개 서버가 실제로 제공하는 서명본을 설치하므로 결과의 버전·서명·설치 대상·예약 등록 상태를 확인한다. 콘텐츠 0.7.0의 발행과 갱신 증거는 [현재 검증 상태](../status/requirements.md)에서 구분한다.

## 설치할 입력을 확인한다

공개키와 지문을 같은 미확인 출처에서 함께 받으면 그 둘만으로 발행자를 독립적으로 인증하지 못한다. 첫 신뢰 경계는 `https://github.com/project820/korean-protocol` 저장소다. 설치기는 배포 주소가 보낸 키를 신뢰 기준으로 사용하지 않고, 로컬에 지정한 공개키와 지문만 사용한다. 개인키는 설치하지 않는다.

서명 입력은 두 가지다. `--source`만 지정하면 공개 HTTPS 주소에서 배포물을 내려받아 설치한다. `--signed-directory`를 지정하면 [발행 도구](publisher.md)의 `seal` 결과 폴더를 오프라인으로 설치하며, 이때 `--source`는 이후 갱신 주소로만 사용한다. 정적 폴더에는 `stable/release.json`, `stable/release.json.sig`와 `releases/<version>/`의 콘텐츠가 필요하다.

## 공개 HTTPS 주소에서 설치한다

저장소 루트에서 실행하는 Codex 예시다. Claude Code에서는 `--host claude-code`를 사용한다.

```sh
python3 -B distribution/agent_install.py plan --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate scheduled --register-scheduler
python3 -B distribution/agent_install.py install --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate scheduled --register-scheduler
```

위 명령은 macOS용이다. `plan`은 manifest와 서명을 먼저 내려받아 검증한 뒤 콘텐츠를 받아 해시·크기·버전을 확인한다. 모든 다운로드와 검증은 임시 폴더에서 이루어지며, 호스트 지침·설치 상태·예약 작업은 바뀌지 않는다. `install`은 같은 검증을 다시 수행한 뒤 설치하고 예약 작업을 등록한다. Linux에서는 `--autoupdate interval` 또는 `--autoupdate off`를 사용한다.

잘못된 서명·다른 키·유효하지 않은 주소는 설치 성공으로 처리하지 않는다. 기존 설치의 신뢰 키와 다른 키를 지정하면 설치를 거부하며, 신뢰 키를 자동 교체하지 않는다.

## 로컬 서명 폴더에서 설치한다

`seal` 결과 폴더를 이미 확보했으면 네트워크 없이 서명을 확인해 설치할 수 있다. 대문자 값은 실제 경로로 바꾼다.

```sh
python3 -B distribution/agent_install.py plan --host codex --signed-directory SIGNED_DIRECTORY --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate off
python3 -B distribution/agent_install.py install --host codex --signed-directory SIGNED_DIRECTORY --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate off
```

이 경로의 `plan`과 `install`은 서명·콘텐츠를 로컬에서 확인한다. 자동 갱신을 함께 켜려면 `--source https://project820.github.io/korean-protocol`과 `--autoupdate interval` 또는 `scheduled`를 지정한다.

## 실행 시 갱신과 예약 갱신을 구분한다

`interval`은 지속 관리 런타임의 `run` 경로로 호스트를 시작할 때 갱신 주기를 확인한다. JSON 결과의 `runtime_argv.run` 뒤에 `--`와 실제 호스트 명령을 붙여 실행하며, 평소의 `codex` 또는 `claude` 명령을 그대로 실행하는 것만으로 이 wrapper가 호출된다고 가정하지 않는다. 사용자가 요청한 설치 범위 안에서 에이전트가 시작 명령 연결을 완료했는지 별도로 확인한다. 사용자가 연결을 원하지 않으면 `--autoupdate off`를 제시한다.

macOS의 `--autoupdate scheduled`는 예약 파일만 만든다. 설치와 함께 OS에 등록하려면 같은 명령에 `--register-scheduler`를 추가한다. `plan`은 이 옵션을 받아도 파일을 쓰거나 작업을 등록하지 않는다.

설치기는 `~/Library/LaunchAgents/`에 자신이 소유하는 작업을 등록한다. 실행 코드는 설치 상태 폴더에 보존한 관리 런타임을 사용한다. 등록 작업은 로그인 시와 매시 정각에 갱신 주기를 확인하며, 실제 다운로드 간격은 기본 24시간이다. macOS의 calendar 예약은 절전 중 놓친 실행을 깨어날 때 합쳐 실행한다. 같은 레이블의 기존 작업이나 수정된 예약 파일이 있으면 덮어쓰지 않는다.

설치 결과의 `scheduler`는 실제 launchd 상태를 확인한다. 파일 생성만 된 `registered: false`를 등록 성공으로 보고하지 않는다. 상태를 확인할 수 없거나 실행 작업과 파일의 소유 정보가 다르면 오류·충돌로 표시한다. `launchctl print` 형식이 바뀌어 실행 경로를 확인할 수 없을 때도 해제·교체를 거부한다.

지속 관리 JSON의 `scheduler_register`, `scheduler_status`, `scheduler_unregister` 명령으로 등록·확인·해제를 수행한다. `configure_off`와 `uninstall`도 자신이 소유한 등록 작업을 해제한다. 직접 수정한 작업은 보존하고 충돌을 보고한다. 개인 endpoint의 shell 토큰을 예약 작업에 복사하지 않으며, `token_env`가 설정된 상태의 자동 등록은 거부한다. Linux·Windows 예약 등록은 지원하지 않는다.

`--autoupdate off`는 서명 배포물을 설치하되 자동 갱신을 끈다. 설치한 규약은 네트워크 없이 유지되며, manifest 만료는 이미 설치한 규약을 지우는 조건이 아니다. 원격에서 새로 수락할 때는 만료·서명·순번·버전 검사를 적용한다.

## 관리 코드와 규약 콘텐츠를 분리한다

설치기는 관리 코드의 해시를 이름에 포함한 새 폴더에 관리 도구를 보존한다. 이전 `agent-tool` 폴더는 검증하고 그대로 남긴다. 규약 업데이트가 Python 코드를 바꾸지 않으며 관리 코드 교체는 새 설치 도구를 명시적으로 실행할 때만 진행한다.

콘텐츠 0.7.0은 엔진 0.2.0 이상을 요구한다. 엔진 0.1.0의 자동 갱신은 새 콘텐츠를 거부하고 기존 설치본을 유지한다. [최신 INSTALL.md](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)에 따라 기존 설치와 같은 경로·설정으로 `install`을 다시 실행한 뒤 `status`로 콘텐츠 버전과 검증 상태를 확인한다.

설치 후 JSON의 `management_commands`로 상태·제거를 관리한다. 명시적인 갱신 요청은 `runtime_argv.update`로 실행하고, 자동 갱신 해제는 `runtime_argv.configure_off`로 실행한다. 설치용 복제본 경로를 관리 명령에 직접 적어 두지 않는다. 설치 상태의 `verified`, `target_matches`, 복구 필요 여부를 확인하며 파일 검증 성공을 LLM의 모든 규칙 준수와 동일시하지 않는다.

## 첫 공개 이전의 예약 실행 기록을 보존한다

[임시 설치 시험](scheduler-registration-verification.json)은 실제 macOS에서 예약 등록과 고정 실행 경로를 확인했다. 갱신 시각 전 실행은 종료 코드 0으로 끝났고, 미공개 endpoint 조회는 종료 코드 3으로 끝나면서 기존 규약을 보존했다. `configure_off` 후 plist와 launchd 작업이 없어졌으며 제거 후 원래 사용자 지침을 복원했다. 시험용 Codex 홈과 별도 상태 폴더만 사용했다.

이 초기 기록은 첫 공개 이전의 시험이다. 물리적 절전·복귀나 재로그인은 실행하지 않았다. 실제 다음 버전의 공개 예약 갱신도 아직 시험하지 않았다.

## 0.2.0 공개 다운로드와 예약 실행 기록을 보존한다

2026-10-13 [익명 다운로드 확인](public-download-verification.json)은 인증 정보 없이 공개 주소에서 `0.2.0` 순번 `1` 배포물 9개 파일을 받았다. manifest 서명을 콘텐츠보다 먼저 검증했고, 모든 콘텐츠 해시가 발행 원본 `91526bb`와 일치했다. 이 manifest는 2026-11-12T06:51:53Z에 만료된다.

같은 날 [공개 배포 예약 실행 시험](public-scheduler-verification.json)은 임시 서명 Codex 설치본의 실제 macOS LaunchAgent를 사용했다. 공개 endpoint 조회 실행이 종료 코드 0으로 끝났고 기존 규약을 보존했다. `configure_off` 후 plist와 작업이 없어졌으며, 제거 후 원래 사용자 지침을 복원했다. 같은 버전의 인증된 확인이므로 새 버전으로의 예약 갱신이나 재로그인·절전 복귀를 검증한 결과는 아니다.

당시 최종 예약 실행은 설치기의 `--source` 원격 설치와 예약 등록을 함께 실행했다. 같은 날 [공개 주소 설치 확인](public-install-verification.json)은 당시 설치기로 Codex·Claude Code 임시 환경에 익명 서명 설치를 수행했다. `plan`의 호스트 상태 보존, 같은 버전 수동 갱신, wrapper 시작, 재설치 보존, 제거 후 사용자 지침 복원을 확인했다. 당시 전체 자동 테스트 310개와 독립 보안 검토를 통과했으며 상세 범위는 [공개 배포 점검](../status/completion-audit-20261013-public.md)에 기록했다.
