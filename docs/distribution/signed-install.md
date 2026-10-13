# 서명 배포물에서 설치한다

이 경로는 발행자가 서명한 정적 배포 폴더와 별도로 확인한 공개키 지문이 있을 때 사용한다. 프로젝트 공개키와 지문은 distribution/trust/에 등록했으며, HTTPS 갱신 주소는 아직 게시하지 않았다. 일반 미리보기 설치는 [INSTALL.md](../../INSTALL.md)를 따르며 자동 갱신을 끈다.

## 설치할 입력을 확인한다

`--signed-directory`는 [발행 도구](https://github.com/project820/korean-protocol/blob/main/docs/distribution/publisher.md)의 `seal` 결과 폴더를 가리킨다. `stable/release.json`, `stable/release.json.sig`와 `releases/<version>/`의 콘텐츠가 필요하다. 개인키는 설치하지 않는다. 공개키와 지문을 같은 미확인 다운로드에서 얻은 것만으로 발행자를 인증했다고 설명하지 않는다.

Codex 예시의 경로·지문·주소는 실제 값으로 바꾼다. Claude Code에서는 `--host claude-code`를 사용한다.

```sh
python3 -B distribution/agent_install.py plan --host codex --signed-directory SIGNED_DIRECTORY --trust-key VERIFIED_PUBLIC_KEY --expected-fingerprint VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate interval
python3 -B distribution/agent_install.py install --host codex --signed-directory SIGNED_DIRECTORY --trust-key VERIFIED_PUBLIC_KEY --expected-fingerprint VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate interval
```

위 주소는 자리표시자다. 원격 자동 갱신을 요청할 때는 실제 같은 origin HTTPS 주소를 지정한다. `plan`과 `install`은 서명·콘텐츠를 로컬에서 확인하며 원격 파일을 내려받지 않는다. 잘못된 서명·다른 키·유효하지 않은 주소는 설치 성공으로 처리하지 않는다. 기존 설치의 신뢰 키를 새 키로 자동 교체하지 않는다.

## 실행 시 갱신과 예약 갱신을 구분한다

`interval`은 지속 관리 런타임의 `run` 경로로 호스트를 시작할 때 갱신 주기를 확인한다. JSON 결과의 `runtime_argv.run` 뒤에 `--`와 실제 호스트 명령을 붙여 실행하며, 평소의 `codex` 또는 `claude` 명령을 그대로 실행하는 것만으로 이 wrapper가 호출된다고 가정하지 않는다. 사용자가 요청한 설치 범위 안에서 에이전트가 시작 명령 연결을 완료했는지 별도로 확인한다.

macOS의 `--autoupdate scheduled`는 지속 관리 경로를 가리키는 launchd 설정 파일을 만든다. 결과의 `registered: false`는 OS 등록 전이라는 뜻이다. plist 생성만으로 예약 실행이 시작됐다고 보고하지 않는다. 실제 등록·실행 이력·재로그인 이후의 갱신 확인은 별도 운영 검증 단계다. Linux·Windows 예약 설치를 지원한다고 표시하지 않는다.

`--autoupdate off`는 서명 배포물을 설치하되 자동 갱신을 끈다. 설치한 규약은 네트워크 없이 유지되며, manifest 만료는 이미 설치한 규약을 지우는 조건이 아니다. 원격에서 새로 수락할 때는 만료·서명·순번·버전 검사를 적용한다.

## 관리 코드와 규약 콘텐츠를 분리한다

설치기는 관리 코드의 해시를 이름에 포함한 새 폴더에 관리 도구를 보존한다. 이전 `agent-tool` 폴더는 검증하고 그대로 남긴다. 규약 업데이트가 Python 코드를 바꾸지 않으며 관리 코드 교체는 새 설치 도구를 명시적으로 실행할 때만 진행한다.

설치 후 JSON의 `management_commands`로 상태·제거를 관리한다. 명시적인 갱신 요청은 `runtime_argv.update`로 실행하고, 자동 갱신 해제는 `runtime_argv.configure_off`로 실행한다. 설치용 복제본 경로를 관리 명령에 직접 적어 두지 않는다. 설치 상태의 `verified`, `target_matches`, 복구 필요 여부를 확인하며 파일 검증 성공을 LLM의 모든 규칙 준수와 동일시하지 않는다.
