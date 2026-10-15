# Korean Protocol 문서를 찾는다

신규 사용자는 [보완 스킬을 설치하고 호출](../INSTALL.md)한다. 기존 0.7 사용자는 [상시 지침을 끈 뒤 전환](../INSTALL.md#기존-07-상시-지침에서-전환한다)한다.

기존 상시 규약 원본은 V7 이전 보완본 r2를 채택한 `0.7.0-draft`이며 서명 콘텐츠는 `0.7.0·순번 3`, 엔진은 `0.2.0`이다. 발행·설치 상태와 기능 대응 설계 49개·검증 0개·부분 4개는 [현재 검증 상태](status/requirements.md)를 따른다.

이 목차는 main의 현행 문서를 안내한다. [v0.7.0 다운로드](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)의 ZIP과 첨부 파일은 설치 도구·안내 원본 `7e01d53`에서 고정했으며 이후 문서 개정이 자동 반영되지 않는다.

## 설치하고 사용한다

| 할 일 | 안내 |
| --- | --- |
| 설치 후 처음 사용한다. | [첫 사용 안내](distribution/quick-start.md)에서 스킬 설치·호출·적용 확인를 확인한다. |
| 문서 구조의 차이를 비교한다. | [원문·KP·STE 참고 예문](../README.md#문장과-구조를-함께-다듬는다) 여섯 사례를 세 열로 읽는다. |
| 코딩 에이전트에 설치한다. | [에이전트 설치 안내](../INSTALL.md)를 따른다. |
| 기존 0.7에서 스킬로 전환한다. | [전환 절차](../INSTALL.md#기존-07-상시-지침에서-전환한다)에서 기존 규약만 OFF로 바꾼다. |
| 사용할 도구를 고른다. | [빠른 시작](distribution/quick-start.md)에서 Codex·Claude Code의 호출문을 확인한다. |
| 일반 채팅에 적용한다. | [채팅용 시작 안내](../distribution/CHAT-START.md)에서 파일과 시작 지침을 확인한다. |
| 스킬 사용과 문체를 선택한다. | [호출·문체 안내](distribution/on-demand-skill.md#적용을-선택하고-문체를-지정한다)를 따른다. 기존 0.7의 [관리 설정](distribution/application-controls.md)은 별도로 유지한다. |
| 호스트와 운영체제의 지원을 확인한다. | [호스트 지원표](distribution/host-support.md)에서 실제 확인 범위를 읽는다. |

## 규칙과 구조를 조회한다

| 확인할 내용 | 기준 문서 |
| --- | --- |
| 규칙의 조건과 예외를 확인한다. | [한국어 세부 규칙](spec/korean-rules.md)과 [통제 어휘](spec/lexicon.md)를 읽는다. |
| 전체 체계를 이해한다. | [규약 목차](spec/toc.md)와 [체계 구조](spec/architecture.md)를 읽는다. |
| 표현을 판단한다. | [표현 운영 지침](spec/control-expression.md)에서 생략·화행·높임의 조건을 확인한다. |
| STE 기능 대응을 검토한다. | [대응 정책](spec/coverage-policy.md)에서 점수의 범위와 검증 조건을 확인한다. |
| 배포 동작을 확인한다. | [배포 계약](distribution/README.md)과 [구현 상태](distribution/implementation-status.md)를 읽는다. |
| 서명 발행물을 준비한다. | [발행 도구 안내](distribution/publisher.md)를 따른다. |

## 결정과 증거를 검토한다

| 검토할 내용 | 기록 |
| --- | --- |
| 현재 버전의 검증 상태를 확인한다. | [요구사항과 검증 상태](status/requirements.md)에서 완료와 미확인을 구분한다. |
| V7 r2의 채택 이유를 확인한다. | [채택 기록](../experiments/v7/adoption.md)과 [고정 실험 기록](../experiments/v7/README.md)을 구분해 읽는다. |
| 기존 연구와 모델 평가를 찾는다. | [연구·검증 근거 모음](status/research-evidence.md)에서 기존 README의 근거와 한계를 찾는다. |
| 규칙의 연구 근거를 확인한다. | [연구 근거와 계획](research-basis.md)과 [선별 문헌 보고서](../research/2026-10-12/research-report.html)를 읽는다. |
| 과거 검사를 재현한다. | [과거 검증 재현 안내](status/historical-verification.md)에서 당시 원본을 지정한다. |
| 과거 점검·평가의 적용 버전을 확인한다. | [상태 기록 목차](status/README.md), [평가 기록 목차](../evaluation/README.md), [실험 목차](../experiments/README.md)에서 현재 안내와 고정 증거를 구분한다. |
| 초기 규약과 개발 순서를 확인한다. | [초기 12개 규칙](protocol-draft.md)과 [2026-10-13까지의 연혁](status/chronology-20261013.md)을 읽는다. |
| 공개 전 보안 점검을 확인한다. | [V7 보안 감사](security/v7-audit.md)에서 검사 범위와 남은 항목을 확인한다. |

날짜가 붙은 평가·배포 기록과 `experiments/v7`의 고정 파일은 당시 상태를 보존한다. 현재 규칙으로 과거 해시·실패 결과를 덮어쓰지 않는다. 문서 배치와 근거는 [문서 설계 기록](maintenance/documentation-design.md)에 남긴다. [공개 파일 점검](maintenance/repository-inventory.md)은 보존할 평가 기록과 로컬에 둘 생성물을 구분한다.
