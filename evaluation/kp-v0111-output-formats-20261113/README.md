# v0.11.1 L1~L4 출력 지침의 형식 준수를 진단했다

이 기록은 진단용이다. 원문·KP·STE 정식 비교는 미완료다.

- **대상:** `skills/korean-protocol` v0.11.1. 최종 `SKILL.md` SHA-256은 `19ae7744da1d469225552b49e4108e52664f4f931c278d9f667c5ae7a4443604`이다.
- **일시:** 2026-11-13
- **모델:** gpt-6.1-sol, gpt-6.1-terra, anthropic/claude-sonnet-5-5, xai/grok-4.7. 추론 강도 medium.

## 실행한 판본

| 실행 | `SKILL.md` SHA-256 | 건수 |
|---|---|---|
| 기본 실험(`probe.py`)과 L1 회귀 | `6ef3520b…adc6a` ([사본](profiles/SKILL-6ef3520b.md)) | 44건, 20건 |
| Sonnet L3 추가(`probe_sonnet.py`) | `729dd2cc…423bc` | 4건 |
| 최종본 확인(`probe_final.py`) | `19ae7744…43604` | 16건 |

- **6ef3520b와 최종본의 차이:** L3 하한 5번에 "원자료에 없는 수치 변수는 만들지 않는다"를 더했다. L2 하한의 Mermaid 문장을 나누고 라벨 안 큰따옴표를 `#quot;`로 쓰게 했다.
- **참조 문서의 차이:** 기본 실험 뒤 `interactive-html.md`에 수치 입력 금지 행, 행동형 결과의 조건 선행, 배치 예외 문장 분리를 더했다. `output-formats.md`는 `#quot;` 규칙과 예시 화살표 라벨 따옴표를 고쳤다. 기본 실험 당시의 참조 문서 사본은 따로 보존하지 않았다.

## 결과

| 항목 | v0.11.0 | v0.11.1 |
|---|---|---|
| L2 질문에 Mermaid 언급 (SKILL.md만) | 0/4 | 8/8 |
| L3 결과 패널이 입력보다 앞 (참조 포함) | 미측정 | 10/10 |
| L3 `.panel_layout` 격자 (참조 포함) | 미측정 | 10/10 |
| L3 `innerHTML`·외부 자원·계산 버튼 (KP 20건) | Sonnet `innerHTML` 4회·계산 버튼 | 0 |
| L3 밝은 배경·첫 화면 결과 (KP, 브라우저 16건) | Grok 어두운 테마 1건 | 16/16 |
| L3 320px 가로 스크롤 (KP 16건) | 미측정 | 0/16 |
| L2 Mermaid 블록 (참조 포함 / SKILL.md만) | 미측정 | 4/4 / 2/4 |
| L2 Mermaid 작성 규칙 위반 (KP 6블록 / STE 2블록) | 미측정 | 0 / 21 |
| Mermaid 11 파서 통과 | 미측정 | 8/8 |

아래 v0.11.1 값은 기본 실험(6ef3520b)이다. v0.11.0 값은 [이전 프로브](../../README.md#v0111은-l1l4-출력-지침을-정의했다)의 1회 실행 값이다.

- **L2·L3 의미 보존:** Astra high가 원문과 대조했다. KP 16건 중 11건, STE 8건 중 5건이 보존이다. 출력 파일명에 KP·STE가 드러나 있어 가린 검토는 아니다. 판정은 [meaning-review-l2l3.json](meaning-review-l2l3.json)에 있다.
- **KP 의미 실패 5건:** HTML이 원문에 없는 시간 경계를 판정한 경우가 3건이다. "자동으로"를 뺀 경우가 2건이다.
- **남은 문제:** Sonnet은 SKILL.md만 받은 조건에서 원자료에 없는 수치 입력을 4/4회 만들었다. 규칙 보강 뒤 참조 포함 조건에서는 2/2회 0개였다.
- **L1 회귀:** 파일럿 사례 5개 × 4모델, Astra high 가린 검토 1회다. v0.11.1의 의미 통과는 16/20(실패 3, 미해결 1)이다. 같은 검토에서 v0.10.1은 19/20, STE는 14/20이다. 집계는 [l1-regression-results.md](l1-regression-results.md)에 있다.

## 최종본 확인

최종본(19ae7744)과 해당 참조로 4모델을 한 번씩 돌렸다. 출력은 [outputs-final](outputs-final)에 있다.

| 항목 | 결과 |
|---|---|
| L2 질문에 Mermaid 언급 | 4/4 |
| L2 Mermaid 블록 (참조 포함 / SKILL.md만) | 4/4 / 3/4 |
| L2 Mermaid 작성 규칙 위반 | 0 |
| L3 결과 먼저·격자·계산 버튼 0·숫자 입력 0 (참조 포함) | 4/4 |
| L3 검사기 진단 (참조 포함) | 0건 |

최종본 출력의 브라우저 확인과 의미 검토는 하지 않았다.

## 조건

- **원문:** 회의실 예약 취소 안내 1종(`plan.json`의 `source_sha256`)이다. 수치 원문은 시험하지 않았다.
- **조건 4개:** SKILL.md만, SKILL.md와 해당 참조, STE 지침(`evaluation/clarity-20261016-r60/ste.md`), 질의응답(SKILL.md만).
- **반복:** 기본 실험은 KP·STE 모두 모델마다 2회다. L2는 1회다. Sonnet L3는 규칙 보강 뒤 KP만 2회를 더 돌렸다(`probe_sonnet.py`).
- **채점:** `score.py`(정적), 내장 브라우저(`browser.json`), Mermaid 11 파서(`mermaid-parse.html`).
- **L1 회귀:** `evaluation/kp-lean-pilot-20261113/`의 생성기와 rubric4로 실행했다. P2 원문은 비공개라 회귀 출력은 올리지 않았다.

## 설계 근거

- [evidence.md](design/evidence.md): 첫 프로브 결과, StyleGallery·Mobbin 근거, 잠정 결정
- [fable-review.md](design/fable-review.md): claude-fable-5-2 high의 설계 검토 원문
- [astra-review.md](design/astra-review.md): gpt-6-astra high의 구현 검토 원문. P2 7건, P3 2건을 반영했다.
- 스킬에 반영한 근거 목록은 `skills/korean-protocol/references/interactive-html.md`의 마지막 절에 있다.

## 파일

- **출력:** `outputs/`. 모델 원시 출력과 호출 기록(`*.json`)이다. HTML은 마크다운 출력에서 코드 블록만 뽑았다.
- **화면:** `screens/grid-refs.png`, `grid-skill.png`, `grid-refs-320.png`
- **해시:** `hashes.txt`

## 한계

- 원문 1종, 반복 2회, 검토 모델 1개다.
- STE L3는 8건 모두 입력 없는 정적 문서였다. 같은 형식 요구에서 STE와 KP의 상호작용 품질은 비교하지 않았다.
- 낭독기 동작과 200% 확대는 확인하지 않았다.

