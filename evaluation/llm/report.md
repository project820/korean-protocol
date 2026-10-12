# 실제 LLM 초기 snapshot 비교평가 결과

이 결과는 수정 전 규약 snapshot의 초기 평가이며 최종 배포본 검증에 사용할 수 없다. 평가 완료 후 root가 별도 규칙검토에서 SYN008 조건변형 등 P1 결함이 발견됐다고 알렸고 규칙 수정이 시작됐다. 아래 출력과 평정은 실행 당시 고정 snapshot에 대한 실제 관측으로 보존한다. 수정본은 새 profile SHA로 별도 treatment 평가를 해야 한다.

사전 고정한 독립 holdout 24개에서 baseline과 coding-agent 프로필 적용 조건은 모두 의미 보존과 행동 판단을 통과했다. 기존 회귀 사례 2개를 합친 26개에서는 적용 조건이 행동 판단 26/26, baseline이 25/26을 충족했다. baseline의 유일한 차이는 공유된 경고 대상을 불필요하게 다시 적은 s01이며, 뜻의 왜곡이나 원인·절차 창작은 아니었다. 이 결과만으로 프로필의 의미 정확도나 독자 이해도 개선을 주장하지 않는다.

## 실행과 사전 고정

- [사전 계획](plan.md)과 [사례 원자료](holdout.json)는 본 실행 전에 고정했다. 사례 SHA256은 `14848d8a6e1c031d15bfd535af4f4470343269d38b9a6667122c4b6114c9d0d4`이다.
- 실제 `/Users/m5max/.local/bin/codex exec`를 stdin prompt, `--json`, `--ephemeral`, `--sandbox read-only`, `--ignore-user-config`, `--ignore-rules`로 호출했다. 요청 모델은 `gpt-6.1-sol`, effort는 `high`, provider는 `subscription_router`, base_url은 `http://127.0.0.1:10100/v1`이다.
- 임시 프로젝트와 임시 CODEX_HOME을 조건마다 새로 만들었다. 기존 auth.json만 링크했고 전역 설정·사용자 AGENTS·rules·hooks는 로드하지 않았다. prompt와 출력에 인증 내용은 넣지 않았다.
- 적용한 실행 당시72규칙 프로필은 28,667 bytes이며 SHA256은 `00084e5dfbf5b48acb355e0f584b41f68929e8e21cdc7f344fc7cbcbb005e3c5`이다. [고정 파일](runs/paired-20261012/frozen-profile.md), 실제 프로젝트에 넣은 [AGENTS snapshot](runs/paired-20261012/treatment/instructions-snapshot/AGENTS.md), 실행 메타데이터의 digest가 일치한다.
- profile 초안 ready 직후 baseline을 시작했고, 최종규칙 보완 메시지를 받자 supervisor를 일시 정지했다. baseline은 프로필 없이 완료됐고 treatment 시작 전에 최종 프로필을 고정했다. 이 경위를 [고정 입력 메타데이터](runs/paired-20261012/frozen-inputs.json)에 기록했다. baseline의 벽시계시간에는 이 대기가 들어 있으므로 속도를 비교하지 않는다.
- smoke 한 번은 exit 0으로 완료했고 평가에서 제외했다. 별도 fresh-session [자동읽기 probe](runs/autoread-20261012/evidence.json)는 prompt에 없는 로컬 AGENTS nonce를 실제 출력에서 확인했으며 exit 0으로 완료했다. 이 probe도 평가에서 제외했다.
- 본 비교는 조건별 26개를 한 배치로 한 번씩 실행했다. 두 조건 모두 exit 0이고 26개 JSON 응답이 구조 검사를 통과했다. CLI에는 최종 upstream 모델/provider 및 FALLBACK 여부가 반환되지 않았으므로 그 항목은 **미확인**이다. 요청 설정과 실제 실행 증거를 최종 upstream 검증으로 해석하지 않는다.

## 내용 평정

사례 저자/runner 구현자와 별도인 root agent가 조건키를 읽기 전에 [A/B 전체 실제 출력](runs/paired-20261012/blind-review.md)을 수동 대조했다. root는 `/root`, 보고한 모델은 `gpt-6-astra`이며 검토 범위는 전체26사례의 의미·판단·명확성·자연성과 창작 여부였다. 이 평정은 사람 독자 실험이 아니다. [독립 평정 원자료](runs/paired-20261012/independent-root-ratings.json)에는 root의 판정과 명시적인 0~2점수를 함께 보존했다. [사례 저자의 별도 평정](runs/paired-20261012/first-reviewer-ratings.json)은 독립평정으로 분류하지 않는다.

| 관측 결과 | baseline | 프로필 적용 |
|---|---:|---:|
| 독립 holdout 의미 보존 | 24/24 | 24/24 |
| 독립 holdout 허용 행동 판단 | 24/24 | 24/24 |
| 전체26 의미 보존 | 26/26 | 26/26 |
| 전체26 허용 행동 판단 | 25/26 | 26/26 |
| 의미 보존 점수 합계 | 52/52 | 52/52 |
| 행동 판단 점수 합계 | 51/52 | 52/52 |
| 명확성 점수 합계 | 52/52 | 52/52 |
| 자연성 점수 합계 | 52/52 | 52/52 |
| 새 사실·원인·절차 창작 | 0 | 0 |
| 실제 CLI 반환 input_tokens | 18,113 | 25,358 |
| 실제 CLI 반환 cached_input_tokens | 4,736 | 0 |
| 실제 CLI 반환 output_tokens | 2,131 | 2,151 |

s01에서 baseline은 “문제가 있을 수 있습니다”를 “새 로그인 기능에 문제가 있을 수 있습니다”로 고쳤다. 경고 대상은 이미 공유됐으므로 사전 keep 기준에서 행동 판단 1점을 받았지만, 가능성은 유지했으므로 의미 점수는 2점이다. 적용 조건은 원문을 keep했다. s02에서는 양쪽이 처리기준을 묻는 clarify를 골랐고 원인이나 처리 절차를 창작하지 않았다. h24의 “장애대응”과 “장애 대응” 띄어쓰기 차이는 B-7 식별이나 뜻을 바꾸지 않으므로 실패로 세지 않았다.

JSON 구조검사와 내용 평정은 별도이다. 문장 exact-match를 의미 정확도로 사용하지 않았다. 반환 input_tokens는 적용 조건에서 7,245개 더 컸지만 캐시 상태도 달랐다. 이 숫자는 청구 금액이나 효율성 입증 자료가 아니다.

## 재현 파일과 한계

각 조건의 `prompt.txt`, `stdout.jsonl`, `stderr.txt`, `final.txt`, `metadata.json`, `parsed.json`은 [baseline](runs/paired-20261012/baseline/metadata.json)과 [treatment](runs/paired-20261012/treatment/metadata.json)에 보존했다. [summary.json](runs/paired-20261012/summary.json)은 독립평정의 사례별 boolean과 정수점수에서 집계한 값이다. [condition-key.json](runs/paired-20261012/condition-key.json)은 독립검토가 끝난 뒤 조건별 집계에 사용했다.

검증 명령 `python3 -m unittest discover -s tests -p test_model_evaluation.py`는 6개 테스트를 통과했다. 테스트는 oracle 비공개, 구조/의미점수 분리, 실제 subprocess 실패 원자료 보존, 프로젝트/사용자설정 격리, 프로필 snapshot 고정을 검증했다. `git diff --check`도 통과했다. 테스트와 probe는 모델 효능 점수를 대신하지 않는다.

조건별 한 번의 고정순서 배치이므로 26사례를 독립 생성 표본 26개로 해석하지 않는다. baseline 과제에도 의미보존과 비창작 지시가 들어 있으며, 독립 holdout에서는 양쪽 모두 만점이었다. 단일 모델·소표본·단일반복의 이 결과는 일반적 효능, 통계적 유의성, 실제 독자 이해도, 현장 성능을 입증하지 않는다. 다음 검증에는 서로 다른 과제·모델에서의 사전 고정 반복, 편집이 필요한 난도가 다양한 사례, 실제 한국어 독자 비교시험이 필요하다. ASD-STE100 기능대응표의 충족 여부는 이 평가의 점수에 포함하지 않았다.
