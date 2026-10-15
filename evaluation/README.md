# 평가 기록의 버전과 범위를 확인한다

이 디렉터리는 평가 당시 입력·프로필·출력·판정과 해시를 보존한다. 보고서의 ‘현재’, ‘최종’, ‘통과’는 해당 실행의 기준본에 대한 표현이며 최신 규약의 성능을 뜻하지 않는다. 현행 0.7.0의 확인 범위는 [현재 검증 상태](../docs/status/requirements.md)와 [V7 검증 기록](../docs/status/v7-verification.md)을 따른다.

## 평가 목적에 맞는 기록을 읽는다

| 확인할 내용 | 당시 기록 |
| --- | --- |
| STE 작성 기능의 설계 대응을 검토한다. | [기능 검토](functional-review.json)와 [보완 이력](functional-review-revision.md)을 읽는다. |
| 한국어 구문의 독립 사례를 확인한다. | [한국어 독립 사례 보고서](korean-independent/report.md)를 읽는다. |
| 사전의 독립 문맥 연결을 확인한다. | [어휘 독립 평가](lexicon-independent/report.md)와 [보완 후 개발 점검](lexicon-refinement-20261012/report.md)을 구분한다. |
| 실제 모델의 편집·생성 결과를 확인한다. | [정제 규칙 평가](llm/rule-refinement-20261012/report-ko.md), [사전 사용 진단](llm/lexicon-usage-20261013/report-ko.md), [편집 범위 평가](llm/editing-scope-20261013/report-ko.md)를 읽는다. |
| 허락·지시의 평정 이견을 확인한다. | [진단 보고서](llm/permission-diagnostic-20261012/report.md)와 [재판정](llm/permission-adjudication.md)을 읽는다. |
| 압축 문체의 비교와 보완을 확인한다. | [규약·미적용·STE 비교](llm/controlled-korean-20261013/report.md)와 [새 입력 평가](llm/fresh-controlled-20261013/report.md)를 읽는다. |
| 0.3.0의 공개 갱신과 코드 이관을 확인한다. | [공개 업그레이드](release-0.3.0-20261013/public-upgrade.md)와 [구버전 관리 코드 이관](release-0.3.0-20261013/historical-helper-migration.md)을 구분한다. |

더 많은 연구·평가의 연결 경로는 [근거 모음](../docs/status/research-evidence.md)에 있다. V7의 고정 프로필과 실패 집계는 [실험 기록](../experiments/v7/README.md)에서 관리한다.

## 고정 입력과 현재 원본을 구분한다

`baselines/`, `before/`, `final-refresh-before/`, `inputs-snapshot/`, `instructions-snapshot/`와 각 실행의 고정 프로필은 당시 입력이다. 그 안의 설치 안내·지침·버전을 최신 안내로 바꾸지 않는다. `report`, `plan`, `final` 등의 파일명은 실행의 역할을 나타내며 최신 버전 표시가 아니다.

과거 검사를 재현할 때는 [재현 안내](../docs/status/historical-verification.md)에 따라 기준본을 지정한다. 해시 불일치가 나면 입력을 최신 파일로 바꾸어 과거 결과를 통과시키지 않는다. 실제 출력·판정의 보존과 현재 규약의 재검증은 별도 작업이다.

## 0.7 문서 개정에서 평가 원본을 보존한다

이 디렉터리의 보고서·계획·지침·스냅샷은 작성 당시 증거다. [0.3 준비 manifest](release-0.3.0-20261013/before-manifest.json)의 `frozen_model_evaluation_files`는 그중 Markdown 156개의 경로와 해시를 고정한다. 이 목차는 현재 안내로 갱신하지만 평가 원문에는 0.7 지침이나 상태 표시를 삽입하지 않는다. 설치 안내가 필요한 독자는 [INSTALL.md](../INSTALL.md)를 사용한다.
