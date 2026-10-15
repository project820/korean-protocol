# 배포 검증 계획

이 문서는 설치·자동 갱신의 시험 기준을 정의한다. 첫 macOS 검사 78개는 [2026-10-12 환경 기록](../status/host-environment-20261012.md)의 결과다. 이후 공개 HTTPS 갱신과 예약 등록을 포함한 실제 확인 범위는 [현재 검증 상태](../status/requirements.md)와 [호스트 지원표](host-support.md)를 따른다. 아래 기준의 존재를 모든 환경의 시험 완료로 해석하지 않는다.

## 테스트 실행 조건

테스트는 Python 표준 라이브러리 `unittest`와 임시 home/state/project root를 사용한다. 실제 사용자 home, 호스트 설정, Keychain, 저장소 토큰, OS 예약 작업을 바꾸지 않는다. 원격 통신은 localhost 시험 서버 또는 주입 가능한 downloader로 대체하고 TLS·origin 검사는 별도 테스트에서 검증한다. 실제 HTTPS/호스트 시험은 별도로 기록한다.

임시 검증 키를 사용할 때에는 테스트용 SSH keypair임을 기록하고 실제 발행 키를 사용하지 않는다. OpenSSH 검증기가 없으면 암호 시험은 skip 이유를 기록하며 모든 서명 테스트가 통과했다고 표시하지 않는다. mock 검증기로 installer 경로가 통과한 결과는 실제 서명 검증 증거와 구분한다.

## 필수 실패 경로

| 시험 | 기대 결과를 다음처럼 정한다. |
| --- | --- |
| 초기 설치와 재설치 | 같은 bundle을 두 번 설치하면 관리 블록 하나만 남고 두 번째가 bytes를 바꾸지 않는다. |
| 기존 파일 보존 | 원본 bytes·CRLF·권한·블록 외부를 보존하고 backup hash를 확인한다. |
| upgrade·rollback·uninstall | 업그레이드 후 캐시 rollback과 pin이 작동하고 제거 후 사용자 추가 내용을 보존한다. |
| 사용자 관리 블록 수정 | 자동 update/uninstall이 수정 내용을 덮지 않고 exit 7로 끝난다. 현재 자동 diff는 제공하지 않으므로 대상과 보존한 백업·캐시를 별도로 비교한다. |
| 블록 밖 수정 | 블록 밖 변경을 유지하며 현재 파일을 다시 hash 확인한 뒤 관리 블록만 바꾼다. |
| marker/owner 충돌 | 중복·미완료 마커·다른 state root 소유를 발견하면 두 번째 설치를 거부한다. |
| 쓰기 중 동시 수정 | 사전 읽기 이후 대상 bytes를 바꾸면 기존 파일과 수정 파일을 모두 보존하고 교체하지 않는다. |
| 절대경로·탈출 | `/etc/...`, `../...`, `a/../../b`, `C:\...`, UNC, backslash, NUL, `:`, URL-encoded traversal, 대소문자 alias를 manifest 경로로 수락하지 않는다. |
| 링크 우회 | 부모/대상 symlink, hardlink, Windows reparse point/junction, 교체 직전 link 변경을 거부하며 root 밖에 쓰지 않는다. |
| unknown payload | `.py`, `.sh`, hook, executable, 알 수 없는 파일·역할, 같은 경로 중복, 허용 파일 누락을 거부한다. |
| JSON strictness | 중복 키, unknown field, BOM, invalid UTF-8, NaN, 잘못된 semver/time, 지나친 크기를 거부한다. |
| hash/size 불일치 | 실제 bytes와 manifest가 다르면 targets/state를 바꾸지 않는다. |
| 실제 SSHSIG | 신뢰한 테스트 키 서명을 수락하며 bytes 한 글자 변조, 다른 키, 다른 namespace/principal, 손상된 서명을 거부한다. |
| 검증기 부재 | 원격 update는 exit 5로 끝나고 기존 설치 파일을 보존한다. 별도 validation CLI의 데이터 검사와 런타임의 서명 검증을 구분한다. |
| trust bootstrap | manifest의 key id만 바꿔 새로운 공개키를 trust 파일에 등록할 수 없다. |
| 재전송·freeze | 낮은 sequence, 같은 sequence의 다른 hash, expired/future-issued를 거부하고 높은 sequence의 낮은 버전을 자동 적용하지 않는다. |
| compatibility | 지원하지 않는 schema/engine 범위를 exit 6으로 거부한다. host 버전 확인 불가는 검증되지 않은 대상으로 보고하며 자동 적용하지 않는다. |
| 통신 보안 | HTTP, 잘못된 TLS, cross-origin redirect, downgrade, userinfo/query token, 초과응답·timeout을 거부한다. |
| private 인증 | 요청이 Authorization을 한 origin에만 보내며 401/403을 기록하고 token 문자열을 stdout/stderr/state/exception에 남기지 않는다. |
| 절차 중단 | download/verify/prepare/첫 target/state 교체 사이를 각각 중단한 뒤 journal에서 무손실 복구한다. |
| 쓰기 실패 | 디스크 공간 부족, 읽기 전용·닫히지 않은 파일, os.replace/fsync 실패 후 기존 정상본을 유지하거나 정확한 복구 충돌을 보고한다. |
| lock과 동시 실행 | 두 프로세스가 같은 대상에 들어갈 때 한 프로세스만 쓰고 다른 state root 경유도 차단한다. |
| offline·off·pin | 네트워크 완전 차단·mode off·pin에서 규약 읽기와 검사 성공을 확인하고 off/pin의 자동 요청 횟수가 0인지 확인한다. |
| wrapper 실패 격리 | 갱신 실패에도 호스트가 마지막 정상 프로필로 시작하며 host exit code를 전달한다. |
| 예약 작업 | 정확한 사용자 작업 하나만 등록·해제하고 login·24시간·절전 복귀·중복 실행에서 정상본을 보존한다. |
| 프로필 예산 | 30,720-byte 본문/32,768-byte 관리 블록을 검사하고 Codex 프로젝트 체인 상한에서 global을 제외한다. 사용자 scope는 프로젝트 cap을 적용하지 않으며 모든 최종 파일을 설치기 보호 상한 4MiB 이하로 제한한다. |

## 호스트 확인

Codex는 임시 `CODEX_HOME`과 프로젝트에 설치한 뒤 새 실행의 instruction 발견 결과를 확인한다. 상위·프로젝트·하위 override와 이미 큰 AGENTS 파일을 각각 시험한다. 모델이 지침을 요약했다고 해서 모든 응답의 준수로 판단하지 않는다.

Claude Code는 filesystem rule 위치와 `/memory` 또는 공식 audit 기능으로 발견을 확인하며 OpenCodex를 통한 실행 경로를 사용한다. Gemini는 공식 memory 확인 기능을 사용한다. Cursor는 실제 Agent 세션의 rule 상태와 프로필 본문을 확인하며 Tab/Inline Edit로 결과를 확대하지 않는다. 모든 실제 모델 실행은 사용자의 기존 계정·실행 권한 범위에서 별도로 수행한다.

ChatGPT는 프로젝트에 첨부한 `KOREAN-PROTOCOL.md`와 시작 지침을 새 채팅에서 확인한다. 로컬 pack update 후 웹의 첨부 파일과 지침이 자동 갱신되지 않는 한계를 결과에 남긴다. 앱별 설정 글자 제한과 계정 rollout 차이를 검증 없이 단정하지 않는다.

## 완료 조건

배포 구현은 오프라인 설치·상태·검사·충돌·복구·제거 시험과 실제 macOS SSHSIG 양성/음성 시험이 통과해야 로컬 최소 지원으로 표시한다. 원격 updater는 network/credential/replay 검사까지 통과해야 지원으로 표시한다. scheduler는 OS별 실행 증거가 있어야 해당 OS의 자동 예약 지원으로 표시한다. 실제 발행 저장소·공개키·release가 정해지지 않은 상태에서는 배포 완료 또는 자동 최신 규약 수신 완료로 표시하지 않는다.
