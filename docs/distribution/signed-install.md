# 서명 배포물에서 설치한다

이 경로는 발행자가 서명한 정적 배포 폴더와 별도로 확인한 공개키 지문이 있을 때 사용한다. 프로젝트 공개키와 지문은 distribution/trust/에 등록했으며, HTTPS 갱신 주소는 아직 게시하지 않았다. 일반 미리보기 설치는 [INSTALL.md](../../INSTALL.md)를 따르며 자동 갱신을 끈다.

## 설치할 입력을 확인한다

`--signed-directory`는 [발행 도구](https://github.com/project820/korean-protocol/blob/main/docs/distribution/publisher.md)의 `seal` 결과 폴더를 가리킨다. `stable/release.json`, `stable/release.json.sig`와 `releases/<version>/`의 콘텐츠가 필요하다. 개인키는 설치하지 않는다. 공개키와 지문을 같은 미확인 다운로드에서 얻은 것만으로 발행자를 인증했다고 설명하지 않는다.

Codex 예시의 경로·지문·주소는 실제 값으로 바꾼다. Claude Code에서는 `--host claude-code`를 사용한다.

```sh
python3 -B distribution/agent_install.py plan --host codex --signed-directory SIGNED_DIRECTORY --trust-key VERIFIED_PUBLIC_KEY --expected-fingerprint VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate interval
python3 -B distribution/agent_install.py install --host codex --signed-directory SIGNED_DIRECTORY --trust-key VERIFIED_PUBLIC_KEY --expected-fingerprint VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate interval
```

위 주소는 자리표시자다. 원격 자동 갱신을 요청할 때는 실제 같은 origin HTTPS 주소를 지정한다. `plan`과 기본 `install`은 서명·콘텐츠를 로컬에서 확인한다. `--register-scheduler`를 요청하면 등록된 launchd 작업이 갱신 주기에 따라 원격 조회를 시작할 수 있다. 잘못된 서명·다른 키·유효하지 않은 주소는 설치 성공으로 처리하지 않는다. 기존 설치의 신뢰 키를 새 키로 자동 교체하지 않는다.

## 실행 시 갱신과 예약 갱신을 구분한다

`interval`은 지속 관리 런타임의 `run` 경로로 호스트를 시작할 때 갱신 주기를 확인한다. JSON 결과의 `runtime_argv.run` 뒤에 `--`와 실제 호스트 명령을 붙여 실행하며, 평소의 `codex` 또는 `claude` 명령을 그대로 실행하는 것만으로 이 wrapper가 호출된다고 가정하지 않는다. 사용자가 요청한 설치 범위 안에서 에이전트가 시작 명령 연결을 완료했는지 별도로 확인한다.

macOS의 `--autoupdate scheduled`는 예약 파일만 만든다. 설치와 함께 OS에 등록하려면 같은 명령에 `--register-scheduler`를 추가한다. `plan`은 이 옵션을 받아도 파일을 쓰거나 작업을 등록하지 않는다.

```sh
python3 -B distribution/agent_install.py install --host codex --signed-directory SIGNED_DIRECTORY --trust-key VERIFIED_PUBLIC_KEY --expected-fingerprint VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate scheduled --register-scheduler
```

설치기는 `~/Library/LaunchAgents/`에 자신이 소유하는 작업을 등록한다. 실행 코드는 설치 상태 폴더에 보존한 관리 런타임을 사용한다. 등록 작업은 로그인 시와 매시 정각에 갱신 주기를 확인하며, 실제 다운로드 간격은 기본 24시간이다. macOS의 calendar 예약은 절전 중 놓친 실행을 깨어날 때 합쳐 실행한다. 같은 레이블의 기존 작업이나 수정된 예약 파일이 있으면 덮어쓰지 않는다.

설치 결과의 `scheduler`는 실제 launchd 상태를 확인한다. 파일 생성만 된 `registered: false`를 등록 성공으로 보고하지 않는다. 상태를 확인할 수 없거나 실행 작업과 파일의 소유 정보가 다르면 오류·충돌로 표시한다. `launchctl print` 형식이 바뀌어 실행 경로를 확인할 수 없을 때도 해제·교체를 거부한다.

지속 관리 JSON의 `scheduler_register`, `scheduler_status`, `scheduler_unregister` 명령으로 등록·확인·해제를 수행한다. `configure_off`와 `uninstall`도 자신이 소유한 등록 작업을 해제한다. 직접 수정한 작업은 보존하고 충돌을 보고한다. 개인 endpoint의 shell 토큰을 예약 작업에 복사하지 않으며, `token_env`가 설정된 상태의 자동 등록은 거부한다. Linux·Windows 예약 등록은 지원하지 않는다.

`--autoupdate off`는 서명 배포물을 설치하되 자동 갱신을 끈다. 설치한 규약은 네트워크 없이 유지되며, manifest 만료는 이미 설치한 규약을 지우는 조건이 아니다. 원격에서 새로 수락할 때는 만료·서명·순번·버전 검사를 적용한다.

## 관리 코드와 규약 콘텐츠를 분리한다

설치기는 관리 코드의 해시를 이름에 포함한 새 폴더에 관리 도구를 보존한다. 이전 `agent-tool` 폴더는 검증하고 그대로 남긴다. 규약 업데이트가 Python 코드를 바꾸지 않으며 관리 코드 교체는 새 설치 도구를 명시적으로 실행할 때만 진행한다.

설치 후 JSON의 `management_commands`로 상태·제거를 관리한다. 명시적인 갱신 요청은 `runtime_argv.update`로 실행하고, 자동 갱신 해제는 `runtime_argv.configure_off`로 실행한다. 설치용 복제본 경로를 관리 명령에 직접 적어 두지 않는다. 설치 상태의 `verified`, `target_matches`, 복구 필요 여부를 확인하며 파일 검증 성공을 LLM의 모든 규칙 준수와 동일시하지 않는다.

## 실제 예약 실행을 검증했다

[임시 설치 시험](scheduler-registration-verification.json)은 실제 macOS에서 예약 등록과 고정 실행 경로를 확인했다. 갱신 시각 전 실행은 종료 코드 0으로 끝났고, 미공개 endpoint 조회는 종료 코드 3으로 끝나면서 기존 규약을 보존했다. `configure_off` 후 plist와 launchd 작업이 없어졌으며 제거 후 원래 사용자 지침을 복원했다. 시험용 Codex 홈과 별도 상태 폴더만 사용했다.

물리적 절전·복귀나 재로그인을 실행한 시험은 아니다. 로그인 이후의 등록은 LaunchAgents 경로와 macOS 계약에 따른 구현이며, 공개 endpoint에서 새 콘텐츠를 실제 예약 갱신하는 시험은 공개 이후에 남아 있다.
