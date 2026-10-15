# 현재 구현과 실행법

Python 3.9 표준 라이브러리로 POSIX 설치기와 서명 콘텐츠 updater를 구현했다. 초기 시험 수와 환경은 [2026-10-12 기록](../status/host-environment-20261012.md)에 보존한다. 별도 임시 설치본의 실제 macOS 예약 등록·실행·해제는 [후속 시험](scheduler-registration-verification.json)에서 확인했다.

현재 원본은 V7 r2를 채택한 0.7.0-draft이며 공개 콘텐츠는 0.7.0·순번 3이다. [공개 발행·설치 갱신 기록](public-0.7.0-verification.md)은 정식 게시자 서명·콘텐츠 7개 해시와 두 호스트의 갱신 결과를 확인한다. 이전 시험 결과를 0.7.0의 새 검증 결과로 사용하지 않는다.

콘텐츠 0.7.0은 엔진 0.2.0 이상을 요구한다. 프로필은 30 KiB, 관리 블록은 32 KiB까지 수용하며 Codex 프로젝트의 실제 잔여 예산은 별도로 검사한다. 엔진 0.1.0은 새 콘텐츠를 거부하고 기존 설치본을 유지하므로 [최신 INSTALL.md의 재설치 절차](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)로 관리 도구를 먼저 교체한다.

## 실행 가능한 경로

checkout에서 다음 명령을 실행한다. Python module 경로를 시스템 PATH에 등록하거나 host 바이너리를 대체하지 않는다.

```sh
python3 -m runtime.kproto --help
python3 -m runtime.kproto --state-dir /ABS/STATE install --bundle /ABS/COMPILED_CONTENT --host codex --scope project --project-root /ABS/PROJECT --local-snapshot --version 0.7.0
python3 -m runtime.kproto --state-dir /ABS/STATE status --json
python3 -m runtime.kproto --state-dir /ABS/STATE rollback --version CACHED_VERSION
python3 -m runtime.kproto --state-dir /ABS/STATE uninstall
```

bundle에는 고정 일곱 콘텐츠 파일이 있어야 한다. 개인 snapshot은 `release.json` 없이 설치할 수 있으며 발행자 인증을 표시하지 않는다. `CACHED_VERSION`에는 실제 보존한 이전 버전을 넣는다. 실제 JSON은 schema version `"1.0"`, version 문자열, 비어 있지 않은 rules/entries object 배열을 확인한다. publication validator는 전체 규칙·어휘 schema와 판정 사례를 검사하며 모든 출력의 의미 보존을 증명하지 않는다.

한 상태 루트는 호스트 대상 파일 하나를 관리한다. host adapter는 `codex`, `claude-code`, `gemini-cli`를 지원하며 사용자·프로젝트 scope를 구분한다. Codex 프로젝트 scope는 가까운 Git marker부터 설치 대상 디렉터리까지 선택된 지침의 합계에 32KiB 또는 단순 top-level 설정 상한을 적용하며 global 파일을 차감하지 않는다. 사용자 scope에는 프로젝트 상한을 적용하지 않고 설치기 자체의 최종 파일 4MiB 보호 상한을 사용한다. 절대 host context를 저장하여 매 활성화 때 현재 발견 파일·설정·상위 체인을 다시 계산한다. 향후 더 깊은 작업 디렉터리·다른 project root 발견 규칙·custom fallback 전체 발견은 미지원이다. Cursor adapter, Windows ACL·원자 교체, Linux/Windows scheduler는 설계 상태이다.

[발행물 준비 안내](publisher.md)는 원본 검사·서명 입력 생성·외부 서명·검증된 정적 폴더 생성을 설명한다. 실제 발행키나 서버 연결과는 구분한다.

## 콘텐츠 자동 갱신을 연결하는 조건

원격 갱신에는 사용자가 별도로 확인한 Ed25519 공개키·지문과 그 키로 서명한 bundle, 동일 origin HTTPS source가 필요하다. 발행키는 [GitHub Actions 환경 Secret](github-actions-pages.md)에 등록했고 공개키는 저장소에 고정했다. 공개 주소 `https://project820.github.io/korean-protocol`에서 0.7.0·순번 3의 서명과 실제 HTTPS 갱신을 검증했다. 서명 bootstrap을 마친 뒤에는 주기적인 수동 update가 필요하지 않으며 규약 사용 자체는 오프라인에서도 가능하다.

```sh
python3 -m runtime.kproto --state-dir /ABS/STATE install --bundle /ABS/SIGNED_BUNDLE --host codex --scope project --project-root /ABS/PROJECT --trust-key /ABS/PUBLISHER.pub --expected-fingerprint SHA256:VERIFIED_FINGERPRINT --source https://publisher.example/kproto --autoupdate interval
python3 -m runtime.kproto --state-dir /ABS/STATE run -- codex
```

위 domain과 fingerprint는 자리표시자이며 실제 배포 정보가 아니다. wrapper는 새 host 시작 시 24시간 갱신 주기를 확인하고 실패하면 설치한 정상 프로필을 유지한다. 사용자는 한 번 host 실행 명령을 wrapper로 연결해야 한다. 기존 `codex` 명령을 직접 실행하면 이 시작 wrapper는 호출되지 않는다. 세션 중에 규약을 매 응답 다운로드하지 않으며 실제 지침 재로드는 호스트의 새 실행 방식에 따른다.

macOS는 wrapper를 사용할 필요가 없는 예약 파일도 생성한다.

```sh
python3 -m runtime.kproto --state-dir /ABS/STATE autoupdate configure --mode scheduled --interval-hours 24 --emit /ABS/kproto-update.plist
python3 -m runtime.kproto --state-dir /ABS/STATE status --json
```

status의 scheduler는 `generated`, `registered=false`를 표시한다. plist에는 절대 Python·runtime·state 경로와 `RunAtLoad`, `StartInterval=86400`이 들어간다. 이 생성 명령은 `launchctl bootstrap`을 실행하지 않는다. 서명 설치기에 `--register-scheduler`를 지정하거나 지속 관리 명령의 `scheduler_register`를 실행하면 OS 등록까지 수행한다. 등록 작업은 매시 정각과 로그인 시에 갱신 시각을 확인한다. 절전 복귀·재로그인·호스트 새 세션의 실제 운영 확인은 별도로 구분한다.

private endpoint는 `--token-env KPROTO_TOKEN`으로 변수 이름만 설정한다. terminal에 설정한 환경 변수가 launchd job에 자동 전달된다고 가정하지 않는다. scheduler 실행 환경의 인증 공급은 사용자가 준비해야 하며 plist에 token 값을 넣지 않는다. 인증이 없으면 원격 갱신은 실패하고 기존 규약을 유지한다.

```sh
python3 -m runtime.kproto --state-dir /ABS/STATE autoupdate configure --mode off
python3 -m runtime.kproto --state-dir /ABS/STATE update --pin CURRENT_VERSION
python3 -m runtime.kproto --state-dir /ABS/STATE update --unpin
```

off는 자신이 등록한 job의 실행 경로·인자와 plist 해시를 확인한 뒤 해제하고, 소유한 예약 파일을 제거한다. 등록 정보가 없거나 사용자가 바꾼 외부 job을 임의로 해제하지 않는다. mode off에서는 원격 조회를 수행하지 않는다. `CURRENT_VERSION`에는 실제 활성 버전을 넣는다. pin은 현재 버전만 지정하며 다른 버전 pin은 cache rollback을 먼저 수행한다.

## 확인한 실패 처리

대상 원문·CRLF·관리 블록 밖 사용자 변경은 보존한다. 관리 블록 안을 사용자가 고치거나 다른 상태 루트가 같은 블록을 소유하면 exit 7로 거부한다. 새 파일·backup·cache·state는 검증한 POSIX 경로에서 descriptor 기반 no-follow 확인과 atomic replace를 사용한다. state와 대상의 flock은 프로세스가 갑자기 종료되어도 커널이 해제하며 다음 recover가 journal을 처리한다.

실제 subprocess `os._exit(23)`으로 target 쓰기와 state commit 사이를 중단한 뒤 recover가 원래 프로필을 복원했다. 다운로드 중 pin 또는 mode off가 바뀌면 적용을 취소하며 갱신 기록은 최신 config와 병합한다. 악의적인 manifest 경로·payload hash 변경·서명 변조·다른 namespace·schema mismatch를 테스트에서 거부했다. 잘못된 검증본을 정상본으로 교체하지 않는다.

HTTP header/body blocking은 worker process deadline으로 종료하고 private HTTP 예외 본문을 고정 오류로 치환한다. 생성된 worker가 2초 멈추는 실패 경로를 0.1초 deadline으로 중단하여 테스트에서 1초 미만에 끝냈다. 전체 네트워크 deadline은 60초이며 서명·로컬 쓰기는 별도 예산이다. wrapper는 갱신의 filesystem 실패도 격리하되 미완료 journal을 복구하지 못하면 host 시작 전에 오류를 반환한다.

```sh
python3 -m unittest discover -s tests -p test_runtime.py
```

이 문서의 이전 점검에서 이 모듈의 118개 시험이 통과했다. 데이터 fixtures·network 주입과 실제 macOS ssh-keygen을 사용했으며 실제 HTTPS 서버·사용자 host 추론·launchctl 등록 성공을 시험한 것으로 확대하지 않는다.

## 과거 연결 시험과 남은 범위를 구분한다

[후속 HTTPS 시험](https-transport-verification.md)은 Python 3.11과 임시 loopback CONNECT 프록시에서 16단계를 통과했다. 실제 TLS·서명 검증·호스트 시작 자동 갱신·오프라인 유지 경로를 실행했으며 런타임은 변경하지 않았다. 당시 직접 443 바인딩은 EACCES였으며 공개 릴리스 서버와 예약 작업 등록은 시험하지 않았다. 이후 공개 배포·예약 등록은 [0.3.0 공개 검증](public-0.3.0-verification.md)과 [예약 실행 기록](public-scheduler-verification.json)에 남겼다. Python 3.9·LibreSSL의 임시 CA 로딩 실패도 별도 기록에 남겼다.

같은 시험의 독립 로컬 설치 단계에서 관리 블록의 절대 캐시 경로와 활성 캐시가 일치했고 두 사전 파일의 해시가 원본과 같았다. 개별 사전의 절대 파일 경로를 본문에 삽입하거나 모델이 사전을 읽는 것을 관측한 결과는 아니다.

`runtime.kproto`에는 검사기 통합 명령, diff/dry-run, 관리 블록 재소유, host별 상세 status, 자동 trust key rotation이 없다. macOS scheduler registration은 서명 설치·지속 관리 경로와 공개 HTTPS source가 있을 때 지원한다. 검사는 validation CLI를 별도로 사용한다. uninstall은 backup/cache를 유지하고 사용자 내용이 생긴 파일을 지우지 않는다. 처음 없던 빈 파일을 완전히 삭제하는 복원은 아직 구현하지 않았으며 제거 후 빈 파일이 남을 수 있다.

프로젝트 지침 체인의 실제 잔여 예산에 관리 블록을 넣을 수 없으면 프로젝트 설치가 실패한다. 엔진 내부의 프로필 30 KiB·관리 블록 32 KiB 상한은 이 검사를 대신하지 않는다. 같은 global 지침은 프로젝트 예산에 포함하지 않으며 사용자 설치를 프로젝트 상한으로 거부하지 않는다. 설치기는 기존 지침을 삭제하거나 host 상한을 늘리지 않는다. 더 큰 상한을 설정한 프로젝트도 최종 대상이 설치기의 4MiB 파일 보호 상한을 넘으면 거부한다. 3.2MiB 사용자 원문을 설치하고 state commit 전에 중단한 뒤 base64가 커진 journal에서 무손실 복구하는 과거 경계 시험도 통과했다.

Claude Code 어댑터의 사용자·프로젝트 설치와 실제 로더·HTTPS 검증은 [코딩 에이전트 지원 기록](coding-agent-support.md)에 추가했다.
