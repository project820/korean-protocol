# 수정 후 편집·신규 생성 실제평가

신규 한국어 답변 생성에서는 짧은 경고의 과설명과 미확인 승인자를 확인하지 않는 문제가 두 조건에 남았다. 의미 보존은 양쪽12/12를 충족했지만 다섯 평정 차원을 모두 충족한 사례는 양쪽10/12였다. 수정 후 프로필의 편집 과제는 의미·판단26/26을 충족했다. 편집과 신규 생성 결과를 하나의 정확도로 합치거나 모든 문제가 해결됐다고 해석하지 않는다.

## 평가 범위와 실행

기존 [편집26 계획](plan.md)·[고정 사례](holdout.json)는 원문을 keep/rewrite/clarify하는 과제이다. 이번 [신규 생성 계획](generation-plan.md)·[독립12과제](generation-holdout.json)는 사실묶음과 요청에서 자연스러운 한국어 답변을 새로 쓰는 과제이다. 신규 생성의 필수 사실·금지 추론·발화목적·간결성 기준은 실행 전에 고정했고 모델 prompt에는 넣지 않았다. 사례 SHA256은 `b64a53a4728a179aefaf466e9fcef2ce62dde6a9529c77e74f8f159458e577f9`이다.

이번 실행은 수정 후72규칙 profile의 SHA256 `5cd4c4657f33e112b9b1c0b95f29a51b689758ccb91155641a38abe6ba93d44e`를 고정했다. 프로필은 28,665 bytes이며 두 과제의 frozen-profile·실제 AGENTS snapshot·실행 메타데이터 digest가 모두 일치한다. 기존 [초기 snapshot 보고](report.md)는 이전 SHA에 대한 별도 기록으로 남긴다. 이번 관측은 해당 새 SHA에 한정되며 후속 규범 변경을 자동으로 검증하지 않는다.

실제 Codex CLI에서 Sol/high, `subscription_router`, localhost10100, 임시 CODEX_HOME·프로젝트, read-only/ephemeral/ignore-user-config/ignore-rules 조건을 유지했다. 인증은 기존 auth.json 링크를 사용했으며 내용은 출력·복사하지 않았다. 생성 baseline12·편집 treatment26·생성 treatment12를 각각 한 배치로 한 번 실행했고 모두 exit0으로 실제 응답을 저장했다. 기존 편집 baseline26은 원자료를 재사용했으며 최종 treatment prompt와 byte-exact로 같음을 확인했다. 이 재사용에는 실행시점 차이와 baseline 재반복 없음이라는 한계가 있다.

최종 upstream 모델/provider와 FALLBACK 여부는 CLI가 반환하지 않았으므로 미확인이다. 메타데이터의 Sol/라우터 값은 요청 설정이며 최종 upstream 검증으로 표현하지 않는다. JSON envelope 구조검사는 내용점수와 분리했고 golden 문장 exact-match는 사용하지 않았다.

## 신규 생성12 평정

root agent `/root`가 condition-key를 읽지 않은 상태에서 [실제 A/B 출력12개](runs/generation-final-20261012/blind-review.md)를 모두 수동 대조했다. A/B 배치는 이번 packet에서 새로 무작위 배정했다. root가 보고한 검토 모델은 `gpt-6-astra`이며 [평정 원자료](runs/generation-final-20261012/independent-root-ratings.json)를 먼저 저장한 뒤 조건키를 열어 [조건별 집계](runs/generation-final-20261012/summary.json)를 작성했다. 이는 사람 독자 실험이 아닌 별도 agent의 내용검토이다.

| 신규 생성12 관측 | baseline | 프로필 적용 |
|---|---:|---:|
| 의미 보존 만점 사례 | 12/12 | 12/12 |
| 다섯 차원 모두 만점 사례 | 10/12 | 10/12 |
| 의미 보존 점수 | 24/24 | 24/24 |
| 발화목적 점수 | 23/24 | 23/24 |
| 명확성 점수 | 23/24 | 23/24 |
| 자연성 점수 | 24/24 | 24/24 |
| 간결성 점수 | 22/24 | 22/24 |
| 사실·원인·절차 창작 | 0 | 0 |

g07은 이미 공유된 새 로그인 기능에 대해 짧게 가능성을 경고하라는 요청이었다. baseline은 “새 로그인 기능에서 문제가 발생할 가능성이 있습니다” 뒤에 발생 확인 상태·원인·문제 유형을 덧붙였다. 적용 조건도 “문제가 발생할 수 있습니다” 뒤에 “실제 발생 여부는 아직 확인되지 않았습니다”를 붙였다. 둘 다 가능성을 보존했으나 요청에 불필요한 확인 상태를 설명했으므로 간결성1점을 받았다.

g11은 승인자가 기록되지 않은 상황에서 승인자 이름을 밝힌 보고를 요구했다. 두 조건 모두 승인자 미기록을 정확히 말했지만 “결과보고는 작성할 수 없습니다”와 수정안 전달 사실로 끝냈다. 필요한 승인자 확인 질문이나 확인 행동을 제시하지 않아 목적·명확성·간결성에 각1점을 받았다. 의미 왜곡이나 승인자 창작은 발생하지 않았다.

나머지10과제는 모든 차원2점을 받았다. 관측한 범위에서는 미실행 작업의 완료 보고, 검증범위 확장, 시간관계의 인과 확정, 허락의 명령화, 부분부정/전체부정 혼동, 동시성 누락, 담당자 재량 침해가 발생하지 않았다. 이 관측을 다른 과제나 모델의 성능 보장으로 확대하지 않는다.

## 수정 후 편집26 평정

root는 [수정 후 편집26 실제 출력](runs/edit-final-20261012/blind-review.md)을 모두 읽고 사전0~2 rubric으로 [원평정](runs/edit-final-20261012/independent-root-ratings.json)을 남겼다. root가 이미 같은 baseline을 초기 평가에서 읽었으므로 이번 검토는 완전한 조건 블라인드라고 부르지 않는다. 재사용 원자료의 경로·prompt/response digest·시점차이 한계는 [baseline-reference.json](runs/edit-final-20261012/baseline-reference.json)에 기록했다.

| 편집26 관측 | 재사용 baseline | 수정 후 프로필 적용 |
|---|---:|---:|
| 의미 보존 만점 사례 | 26/26 | 26/26 |
| 의미·판단·명확성·자연성 모두 만점 사례 | 25/26 | 26/26 |
| 의미 보존 점수 | 52/52 | 52/52 |
| 판단 점수 | 51/52 | 52/52 |
| 명확성·자연성 점수 | 각각52/52 | 각각52/52 |
| 사실·원인·절차 창작 | 0 | 0 |

baseline의 s01은 공유된 경고 대상 “새 로그인 기능”을 다시 명시하는 rewrite여서 사전 keep 기준에서 판단1점을 받았다. 뜻의 보존은2점이며 의미왜곡으로 세지 않았다. 수정 후 조건은 s01을 keep했고 s02에서 필요한 처리 목표를 묻는 clarify를 골랐다. 이 결과는 신규 생성 g07/g11의 부족을 해소한 증거가 아니다.

## 반환 usage와 원자료

| 과제·조건 | input_tokens | cached_input_tokens | output_tokens |
|---|---:|---:|---:|
| 편집 재사용 baseline | 18,113 | 4,736 | 2,131 |
| 편집 수정 후 treatment | 25,357 | 0 | 2,361 |
| 생성 baseline | 17,670 | 0 | 796 |
| 생성 treatment | 24,925 | 4,736 | 949 |

입력 토큰 차이는 편집+7,244, 생성+7,255이며 캐시 상태가 다르다. 이 숫자를 비용이나 청구액으로 환산하지 않았다. wall-clock 속도 비교도 하지 않는다.

신규 생성의 [baseline 메타데이터](runs/generation-final-20261012/baseline/metadata.json)·[treatment 메타데이터](runs/generation-final-20261012/treatment/metadata.json)와 편집의 [treatment 메타데이터](runs/edit-final-20261012/treatment/metadata.json)는 같은 디렉터리에 stdin prompt, CLI JSONL, stderr, final response, 구조검사 JSON을 보존한다. [생성 집계](runs/generation-final-20261012/summary.json)와 [편집 집계](runs/edit-final-20261012/summary.json)는 각각의 root 정수점수와 사례별 판정에서 산출했다. 두 점수를 합친 단일 정확도 필드는 null로 남겼다.

별도 hostloader 모델 nonce probe는 root 지시로 취소했고 실행하지 않았다. 대신 [실제 Codex0.162.1 debug prompt-input 증거](../../docs/distribution/codex-loader-evidence.json)는 임시 HOME/Git 프로젝트에서 credential-free fixture의 끝 marker와 stdout digest를 확인한 네트워크·모델 호출 없는 자료이다. 그 loader 자료는 프로필을 prompt에 넣는 범위를 검사하며 모델 준수나 언어효능을 검증하지 않는다.

runner의 신규 생성 mode·oracle 제외·자연어 text envelope·packet별 A/B 무작위화를 TDD로 추가했고 `python3 -m unittest discover -s tests -p test_model_evaluation.py`는8개를 통과했다. raw subprocess 보존과 임시 프로젝트/프로필 snapshot 검증은 기존 테스트에 포함한다. `git diff --check`도 통과했다.

## 해석 한계와 남은 검증

모델1종·고정순서·조건별1batch·반복1·소표본이며 사례별 독립 생성 반복이 아니다. 후속 규칙수정 후 평가라는 선택조건, 편집 baseline 재사용과 검토자 기노출, agent 평정이라는 한계를 남긴다. 신규 생성에서는 짧은 경고의 불필요한 상태설명과 미확인 승인자에 대한 필요한 확인을 개선해야 한다. 다음 검증은 기존 holdout을 학습문장으로 반복 조정한 점수와 구별되는 새 과제·여러 모델/반복·실제 한국어 독자 시험이어야 한다. ASD-STE100 기능대응 충족 여부는 이 LLM 평가의 점수로 대신하지 않는다.
