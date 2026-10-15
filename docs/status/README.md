# 현재 상태와 과거 점검을 구분한다

현재 원본은 V7 r2를 채택한 0.7.0-draft이며 공개 서명 콘텐츠는 0.7.0·순번 3이다. [요구사항과 검증 상태](requirements.md)가 현재 상태의 기준이다. [V7 채택](v7-adoption.md)과 [V7 검증](v7-verification.md)은 결정·코드 시험·단일 모델 출력의 범위를 구분한다.

## 과거 점검은 당시 기준본으로 읽는다

| 기록 | 적용 범위를 구분한다. |
| --- | --- |
| [초기 완료 점검](completion-audit.md)과 [2026-10-13 점검](completion-audit-20261013.md) | 최초 확장과 공개 전의 공백을 보존한다. |
| [사전 진단 후 점검](completion-audit-20261013-post-lexicon.md) | 445110e 이후의 제한된 모델 진단을 다룬다. |
| [편집 범위 점검](completion-audit-20261013-editing-scope.md) | 45f86c6의 편집 범위 보완을 다룬다. |
| [새 과제 평가 점검](completion-audit-20261013-scope-holdout.md) | 9367bde와 미리보기 7의 당시 상태를 다룬다. |
| [실제 서명물 점검](completion-audit-20261013-current-signing.md) | 첫 공개 전의 비공개 서명 시험을 다룬다. |
| [MIT 적용 점검](completion-audit-20261013-mit.md) | 라이선스 선택과 미리보기 8을 다룬다. |
| [첫 공개 점검](completion-audit-20261013-public.md) | 콘텐츠 0.2.0·순번 1의 공개와 설치를 다룬다. |
| [압축 문체 후보 점검](completion-audit-20261013-compact.md) | 콘텐츠 0.3.0·순번 2의 후보·발행을 다룬다. |
| [개발·발행 연혁](chronology-20261013.md)과 [독립 검토 이력](review-log.md) | 당시 발견·수정·미해결 판단을 보존한다. |
| [게시 준비 점검](publication-readiness.md) | V7 발행 결과와 2026-10-13의 과거 준비 기록을 구분한다. |
| [2026-10-12 환경 기록](host-environment-20261012.md) | 당시 호스트 버전·로딩·설치 환경에 한정한다. |

위 과거 문서의 ‘현재’, ‘현행’, ‘아직’은 각 기준본 당시의 상태다. 과거 비공개·게시 대기 표현을 현재 공개 상태로 읽거나 49/53의 옛 기능 검토를 V7의 현재 점수로 사용하지 않는다. 기록의 수치·해시·실패 결과는 보존한다.

[연구·검증 근거 모음](research-evidence.md)은 관련 평가 보고서로 연결한다. [과거 검증 재현 안내](historical-verification.md)는 기준본을 지정하는 명령을 제공한다. 설치·호스트 지원은 [문서 목차](../README.md)에서 찾는다.
