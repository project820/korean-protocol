# 0.7.0 배포의 구현 상태와 실행 범위를 확인한다

규약 콘텐츠 0.7.0·순번 3, 관리 엔진 0.2.0, 규칙·사전 schema 1.0을 제공한다. V7 r2 구조를 채택했으며 [공개 발행·갱신 기록](public-0.7.0-verification.md)은 게시자 서명과 두 호스트의 실제 HTTPS 갱신을 구분한다.

## 구현한 경로를 사용한다

| 기능 | 현재 동작 |
| --- | --- |
| 사용자 설치 | `agent_install.py`가 Codex·Claude Code의 계획·설치·상태·설정·제거를 제공한다. |
| 저수준 설치 | `runtime.kproto`가 Codex·Claude Code·Gemini 파일 adapter와 사용자·프로젝트 범위를 제공한다. Gemini 실제 호스트 로딩은 별도다. |
| 콘텐츠 인증 | 고정 키·SSHSIG·일곱 파일 해시·크기·경로·시간·순번·호환 범위를 검증한다. |
| 지속 관리 | 관리 코드를 상태 폴더에 보존하며 관리 블록 밖 사용자 내용을 유지한다. |
| 갱신 | 수동·시작 wrapper·macOS 예약 실행을 제공한다. 실패하면 기존 정상본을 보존한다. |
| 복구 | 잠금·저널·원자 교체·캐시 롤백과 버전 pin을 제공한다. |
| 공개 패키지 | v0.7.0의 ZIP·채팅 파일·체크섬을 별도 사용자 릴리스로 제공한다. |

서명 콘텐츠의 원본은 `67f537e`, 공개 사용자 패키지 원본은 `7e01d53`다. 같은 0.7.0이어도 최신 main의 문서·도구 변경이 고정 패키지에 들어 있다고 설명하지 않는다. 코드의 최신 상태는 현재 checkout, 공개 파일의 바이트는 [해당 릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)를 기준으로 확인한다.

## 설치와 관리를 실행한다

일반 설치는 [INSTALL.md](../../INSTALL.md)를 따른다. 저수준 CLI는 저장소 루트에서 다음 형식으로 사용하며 대문자 경로·버전을 실제 값으로 바꾼다.

```sh
python3 -B -m runtime.kproto --help
python3 -B -m runtime.kproto --state-dir /ABS/STATE install --bundle /ABS/CONTENT --host codex --scope project --project-root /ABS/PROJECT --local-snapshot --version 0.7.0 --autoupdate off
python3 -B -m runtime.kproto --state-dir /ABS/STATE status --json
python3 -B -m runtime.kproto --state-dir /ABS/STATE rollback --version CACHED_VERSION
python3 -B -m runtime.kproto --state-dir /ABS/STATE uninstall
```

한 상태 루트는 대상 파일 하나만 관리한다. 프로젝트 설치에는 별도 상태 폴더와 실제 프로젝트 절대 경로를 사용한다. 기존 사용자 설치와 같은 상태 경로를 공유하지 않는다.

지속 관리 도구를 설치했다면 반환된 명령을 우선 사용한다. 기존 홈·상태·신뢰·규약·높임말을 보존하며 서명 재설치의 자동 갱신 옵션은 다시 명시한다. 생략하면 OFF로 설정한다.

## 엔진과 호스트 예산을 검사한다

엔진 0.2.0은 프로필 30 KiB·관리 블록 32 KiB·최종 대상 파일 4 MiB의 내부 상한을 사용한다. 실제 Codex 프로젝트 체인의 잔여 예산은 별도로 검사하며 global 지침을 프로젝트 예산에서 빼지 않는다. 사용자 설치는 프로젝트 상한으로 거부하지 않는다.

엔진 0.1.0은 0.7.0 콘텐츠를 거부한다. 관리 엔진은 사용자가 검토한 설치 도구를 명시적으로 실행해 갱신하며 콘텐츠 updater가 실행 코드를 교체하지 않는다. 기존 지침이나 Codex 설정의 상한을 자동 변경하지 않는다.

## 자동 갱신과 수동 갱신을 구분한다

기본 성공 간격은 24시간이며 관리 런타임에서 1~168시간을 선택한다. `interval`은 반환된 wrapper로 호스트를 시작해야 실행 기회를 얻는다. macOS `scheduled`는 파일 생성과 OS 등록을 구분하며 실제 등록 작업은 로그인 시·매시 정각에 기한을 확인한다.

자동 갱신 OFF는 소유 예약 연결을 해제한다. 사용자의 명시적 `update`는 OFF에서도 조회하지만 pin은 조회·적용을 막는다. `rollback`은 검증된 캐시를 활성화하고 선택 버전을 pin한다. 상세 명령은 [서명 설치](signed-install.md), 표현 설정은 [적용 설정](application-controls.md)을 따른다.

## 구현하지 않았거나 별도 확인이 필요한 경로를 남긴다

Windows의 ACL·원자 교체·예약 등록, Linux systemd 예약 등록, Cursor 자동 설치, 웹 채팅 자동 동기화는 제공하지 않는다. Linux 시작 wrapper의 운영 검증과 macOS 재로그인·물리적 절전 복귀·모델 전체 준수는 [호스트 지원표](host-support.md)의 확인 범위를 따른다.

자동 diff·관리 블록 재소유·신뢰 키 자동 교체·런타임 응답 검사·출력 차단은 없다. `status --host`는 에이전트 설치 도구 옵션이며 저수준 런타임 옵션이 아니다. 제거 후 상태·백업·캐시와 새로 만들었던 빈 파일은 남을 수 있다.

```sh
python3 -B -m validation.check --root . --json
python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_scheduler tests.test_distribution
```

위 검사는 현재 checkout을 대상으로 실행해 결과를 확인한다. 과거 78개·118개 시험 수나 이전 프로필의 로더 결과를 현재 검사 결과로 보고하지 않는다. 정적 구조 검사는 실제 의미 보존이나 독자 이해를 입증하지 않는다.
