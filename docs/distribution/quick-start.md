# Korean Protocol 0.7.0의 사용 경로를 고른다

코딩 에이전트는 서명 설치 또는 오프라인 ZIP을, 일반 채팅은 파일 첨부를 사용한다. 현재 V7 r2는 대상·조건·수량·기한을 구분하며 원문보다 짧게 만들 것을 요구하지 않는다.

| 목적 | 시작 경로 | 유지 방식 |
| --- | --- | --- |
| Codex·Claude Code에 서명 설치한다. | 에이전트에 [INSTALL.md](../../INSTALL.md)를 전달한다. | 예약 갱신·시작 wrapper·자동 조회 OFF 중 선택한다. |
| 기존 설치를 0.7.0으로 갱신한다. | 같은 홈·상태 경로에서 [관리 도구를 재설치](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)한다. | 규약·높임말은 유지한다. 자동 갱신 옵션은 다시 명시한다. |
| 인터넷 없이 로컬 설치한다. | [ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip)을 풀고 `python3 start.py` 또는 [비대화형 안내](../../distribution/START-HERE.md)를 사용한다. | 미서명 `local-snapshot`으로 설치하며 자동 갱신은 끈다. |
| ChatGPT에서 사용한다. | [KOREAN-PROTOCOL.md](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md)를 받고 [채팅 안내](../../distribution/CHAT-START.md)를 따른다. | 프로젝트에 저장한 복사본은 직접 교체한다. |
| 다른 앱에서 사용한다. | 첨부·저장 지침의 실제 지원 범위를 확인한다. | 현재 자동 설치 지원으로 표시하지 않는다. |

## 공개 버전과 원본을 구분한다

서명 콘텐츠는 0.7.0·순번 3이며 관리 엔진 0.2.0 이상을 요구한다. 데이터 schema는 1.0이다. 엔진 0.1.0은 새 콘텐츠를 거부하고 기존 규약을 보존하며 자동 갱신으로 관리 코드를 바꾸지 않는다.

[v0.7.0 릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)의 ZIP·단독 파일·[체크섬](https://github.com/project820/korean-protocol/releases/download/v0.7.0/SHA256SUMS)은 `7e01d53`의 고정 산출물이다. 최신 main의 안내와 혼동하지 않는다. 미서명 파일의 체크섬과 HTTPS 콘텐츠의 게시자 서명은 서로 다른 검사다.

## 적용과 갱신을 확인한다

설치 상태의 버전·신뢰·대상·규약·높임말·자동 갱신 연결을 확인한다. [규약·높임말 설정](application-controls.md)은 콘텐츠와 독립적으로 저장한다. 서명 재설치에서 `--autoupdate`를 생략하면 OFF로 설정하므로 기존 예약 연결을 무조건 보존한다고 보고하지 않는다.

현재 세션에는 검증된 설치 캐시를 참조하며 호스트의 새 세션 로딩과 모델 준수를 구분한다. 지원 환경은 [호스트 지원표](host-support.md), 공개 증거는 [0.7.0 발행 기록](public-0.7.0-verification.md), 언어 효과의 한계는 [현재 검증 상태](../status/requirements.md)를 따른다.
