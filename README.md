# Korean Protocol

**한국어 답변에서 대상·조건·행동·기한을 한눈에 찾게 한다.**

Korean Protocol은 LLM의 한국어 표현을 위한 규약이다. 어휘의 뜻과 결합, 문장 구조, 지시·보고·경고의 작성 기준을 함께 제공한다. 필요한 뜻을 보존하면서 독자가 다시 해석해야 하는 부담을 줄인다.

[설치하기](INSTALL.md) · [규칙 읽기](docs/spec/korean-rules.md) · [구조 예시 보기](#문장과-구조를-함께-다듬는다) · [검증 상태 확인하기](docs/status/requirements.md)

## 사용하는 도구에서 시작한다

| 코딩 에이전트 | 일반 채팅 |
| --- | --- |
| [INSTALL.md](INSTALL.md)를 에이전트에 전달한다. Codex·Claude Code의 로컬 지침과 캐시에 설치한다. | [채팅용 시작 안내](distribution/CHAT-START.md)를 따라 [KOREAN-PROTOCOL.md](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md)를 프로젝트에 올린다. |
| 서명된 콘텐츠를 설치하며 macOS 예약 갱신 또는 Linux 시작 wrapper를 연결한다. | 업로드한 파일을 계속 사용하며 새 버전은 직접 교체한다. |

[0.7.0 다운로드](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)에서 미서명 오프라인 ZIP·채팅용 파일·체크섬을 받는다. 서명 콘텐츠의 자동 갱신과 별도 경로이며 `SHA256SUMS`는 발행자 인증을 대신하지 않는다.

Codex 또는 Claude Code에 다음 문구를 복사한다.

```text
https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
지금 사용하는 코딩 에이전트의 사용자 범위에 서명된 Korean Protocol을 설치해줘.
macOS에서는 예약 자동 갱신을 등록해줘.
설치 버전과 갱신 연결 상태를 확인해줘.
```

기존 설치에서 0.7.0으로 올릴 때는 [최신 관리 도구로 재설치](INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)가 필요하다. 콘텐츠 0.7.0은 관리 엔진 0.2.0 이상을 요구하며 구버전 0.1.0의 자동 갱신은 기존 콘텐츠를 유지한다. 에이전트에는 다음 문구를 복사한다.

```text
최신 https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
기존 Korean Protocol 설치의 관리 도구를 0.2.0 이상으로 갱신해줘.
그 뒤 서명된 0.7.0을 설치해줘.
기존 설치 경로와 규약·높임말·자동 갱신 설정은 보존해줘.
status로 설치 버전과 상태를 확인해줘.
```

저장소와 [서명 배포 manifest](https://project820.github.io/korean-protocol/stable/release.json)는 공개되어 있으며 GitHub 인증 없이 사용할 수 있다. 자동 갱신은 끌 수 있고 [미서명 오프라인 설치](INSTALL.md#오프라인-미서명-설치를-명시적으로-선택한다)도 제공한다.

## 문장과 구조를 함께 다듬는다

같은 개념에는 같은 이름을 쓰고, 행동은 서술어로 직접 나타낸다. 대상과 속성을 나누고 조건이 적용되는 범위를 밝힌다. 가능성·허락·의무와 시작·진행·완료의 차이는 그대로 남긴다.

다음은 구조를 설명하기 위해 만든 예시다.

| 원문 | V7 구조 적용 |
| --- | --- |
| 반납 대상은 노트북과 출입증이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다. | **반납 대상**<br>· 노트북<br>· 출입증<br><br>접수 담당: 총무팀<br>접수 마감: 7월 5일 18:00 |

예시는 새로운 조건이나 반납 절차를 추가하지 않으며 실제 독자 시험의 결과가 아니다. 문장이 이미 짧고 명확하면 그대로 둔다. 원문보다 짧게 만들기 위해 필요한 뜻이나 구분을 없애지 않는다.

## 현재 버전과 검증 범위를 밝힌다

| 항목 | 현재 상태 |
| --- | --- |
| 원본 버전 | **0.7.0-draft**이며 V7 보완본 **r2**의 구조 규칙을 채택했다. |
| 채택 기준 | 사용자가 r2의 가독성을 선택했으며 더 짧게 만든 r3는 채택하지 않았다. |
| 콘텐츠 발행 | **0.7.0·순번 3**을 공개했고 두 호스트의 서명 HTTPS 갱신과 기존 로컬 설치 갱신을 [검증했다](docs/distribution/public-0.7.0-verification.md). |
| 효과 검증 | V7 실험의 의미 변경·미확정 결과가 남아 있으며 실제 독자 시험은 수행하지 않았다. |

[채택 기록](experiments/v7/adoption.md)은 결정과 한계를, [고정 실험 기록](experiments/v7/README.md)은 당시 프로필과 실패 집계를 보존한다. 사용자 선택은 모든 출력의 의미 보존이나 독자 이해 효과를 입증한 결과가 아니다. 0.3.0 당시의 기능 대응 49/53과 모델 평가를 포함한 근거는 [연구·검증 기록](docs/status/research-evidence.md)에 모았다.

## 필요한 문서를 찾는다

| 목적 | 문서 |
| --- | --- |
| 규칙과 예외를 확인한다. | [한국어 세부 규칙](docs/spec/korean-rules.md) · [통제 어휘](docs/spec/lexicon.md) |
| 설치와 적용 설정을 관리한다. | [설치 안내](INSTALL.md) · [규약·높임말 설정](docs/distribution/application-controls.md) · [호스트 지원표](docs/distribution/host-support.md) |
| 설계와 근거를 검토한다. | [문서 목차](docs/README.md) · [검증 상태](docs/status/requirements.md) · [연구 근거](docs/research-basis.md) |

Korean Protocol은 ASD-STE100의 간결한 기술 문체에서 출발한 독립 규약이며 번역본이나 공식 한국어판이 아니다. 영어의 단어 수 제한을 한국어 어절 수로 옮기지 않는다. 직접 작성한 코드·규약·사전·문서는 [MIT License](LICENSE)로 제공하며 제3자 자료의 권리는 [NOTICE.md](NOTICE.md)에 구분했다.
