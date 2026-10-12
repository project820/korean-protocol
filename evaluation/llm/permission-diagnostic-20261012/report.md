# 허락 조건 진단 보고 — 반복 입력 확률 진단

이 진단은 같은 입력을 두 번 반복한 확률적 재현성 진단이며 새 독립 효능 자료가 아니다. 네 번의 고정 생성 호출은 모두 종료 코드0으로 끝났고, 48개 출력은 모두 구조가 유효하며 prompt/profile hash가 동결 값과 일치한다. v07의 명령형 어미는 반복1에서 baseline과 treatment 모두에, 허락형 어미는 반복2에서 두 조건 모두에 나타났다. 따라서 이 자료로는 v07 어형을 후보 프로필의 효과로 귀속할 수 없다. 과거 정확도는 다시 계산하거나 수정하지 않았다.

## 실행 사실과 모델 경로

네 번의 생성 호출은 `gpt-6.1-sol`(Sol)/reasoning effort `high`를 `subscription_router`(`http://127.0.0.1:10100/v1`)로 요청했고 모두 성공했다([execution-records.json](execution-records.json), [driver-session.json](driver-session.json), [status.json](status.json)). 요청 경로는 실제 upstream 모델이나 서버측 fallback을 증명하지 않으며, 네 metadata 모두 `upstream_provider_observed`와 `fallback_observed`가 `null`이다. 이 보고서는 Sol 하위 agent의 응답 스트림이 네 호출 완료 뒤 끊겨서, OpenCodex를 거쳐 요청된 `claude-opus-5-5`/high가 보고서 작성만 이어받아 썼다. 보고서 작성 모델은 48개 출력을 생성하지 않았고 모델 호출을 다시 실행하지 않았다.

| 반복 | 조건 | 종료 | 소요 | stderr | 응답 수 | 입력/출력 token(반환값) |
|---|---|---:|---:|---:|---:|---|
| 1 | baseline | 0 | 38.4초 | 0바이트 | 12 | 17,735 / 1,127 |
| 1 | treatment | 0 | 29.0초 | 0바이트 | 12 | 24,987 / 791 |
| 2 | baseline | 0 | 30.3초 | 0바이트 | 12 | 17,738 / 879 |
| 2 | treatment | 0 | 32.2초 | 0바이트 | 12 | 24,987 / 866 |

반환된 token 수는 과금 증거가 아니다. 근거 파일은 [sol-repetition-1/baseline/metadata.json](sol-repetition-1/baseline/metadata.json), [sol-repetition-1/treatment/metadata.json](sol-repetition-1/treatment/metadata.json), [sol-repetition-2/baseline/metadata.json](sol-repetition-2/baseline/metadata.json), [sol-repetition-2/treatment/metadata.json](sol-repetition-2/treatment/metadata.json)이다.

## 무결성 점검 결과

- 동결 입력의 SHA256을 다시 계산한 결과 [frozen-cases.json](frozen-cases.json)은 `7f2aa3ca…aaf1f`, [frozen-prompt.txt](frozen-prompt.txt)는 `6f2de705…7e96c`, [frozen-profile.md](frozen-profile.md)는 `6ec821d7…88c4c`, [plan.md](plan.md)는 `7998410d…0d519`로 [frozen-inputs.json](frozen-inputs.json)과 일치한다.
- 네 `prompt.txt`는 모두 `6f2de705…7e96c`이고, 두 treatment의 `instructions-snapshot/AGENTS.md`는 모두 `6ec821d7…88c4c`이다. baseline은 profile이 없으므로 `profile_sha256`이 `null`이다.
- 네 `final.txt`의 SHA256은 execution-records의 `final_sha256`과 일치한다.
- 네 `stdout.jsonl`은 각각 `thread.started`, `turn.started`, `item.completed`(agent_message), `turn.completed` 네 사건으로 구성되며, agent_message 본문은 `final.txt`와 같다.
- 네 `final.txt`는 모두 JSON으로 해석되고, `results` 항목은 v01–v12 순서의 12개이며 키는 `id`, `text`뿐이다. 각 `parsed.json`의 `results`는 `final.txt`와 같고 `structure_valid: true`, `errors: []`이다.
- metadata는 `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, `--sandbox read-only`, 호출별 별도 임시 project 경로를 기록한다.

검토 절차에는 두 가지 한계가 있다. [plan.md](plan.md)는 무작위 A/B 검토 묶음을 정했지만, [sol-repetition-1/condition-key.json](sol-repetition-1/condition-key.json)과 [sol-repetition-2/condition-key.json](sol-repetition-2/condition-key.json)은 둘 다 A=baseline, B=treatment여서 두 반복 사이의 맹검이 약하다. [sol-repetition-1/blind-review.json](sol-repetition-1/blind-review.json)과 [sol-repetition-2/blind-review.json](sol-repetition-2/blind-review.json)의 A/B 본문은 실제 출력과 일치하지만 24개 항목의 점수는 모두 `null`이므로 이 디렉터리에 저장된 점수는 없다.

## v07 독립 기록

사실은 "큐 길이20개 이하 **그리고** 활성 작업0개일 때만 허용"과 "하나만 만족하면 생성 금지"이다. 정확한 출력은 [v07-table.md](v07-table.md)에 있고, 각 `final.txt`에서 다시 확인했다.

| 출력 | 20 포함 경계 | 활성0 논리곱 | 조건 밖 제한 | 명시적 추가 의무 | 명시적 허락 표현 |
|---|---|---|---|---|---|
| 반복1 baseline: "…두 조건을 모두 만족할 때만 스냅샷을 생성하세요. 하나만 만족하면 생성하면 안 됩니다." | 있음("20개 이하") | 있음("두 조건을 모두") | 있음("때만" + 한 조건 금지문) | 없음 | 없음(명령형) |
| 반복1 treatment: "…활성 작업이 0개인 경우에만 스냅샷을 생성하세요. 두 조건 중 하나만 만족하면 생성하면 안 됩니다." | 있음 | 있음("이고") | 있음("경우에만" + 한 조건 금지문) | 없음 | 없음(명령형) |
| 반복2 baseline: "스냅샷은 …0개일 때만 생성할 수 있습니다. 두 조건을 모두 만족해야 합니다." | 있음 | 있음("두 조건을 모두") | 있음("때만"); 한 조건 금지문은 따로 없음 | 없음 | 있음("생성할 수 있습니다") |
| 반복2 treatment: "…0개일 때만 스냅샷을 생성할 수 있습니다. 두 조건 중 하나만 만족하면 생성하면 안 됩니다." | 있음 | 있음("이고") | 있음("때만" + 한 조건 금지문) | 없음 | 있음("생성할 수 있습니다") |

네 출력 모두 20을 포함하는 경계, 활성0과의 논리곱, 조건 밖 제한을 유지하고, "반드시 생성" 같은 무조건 의무를 덧붙이지 않았다. 반복1의 "생성하세요"는 조건 충족 시 생성을 지시하는 것으로도 읽힐 수 있어 허락과 지시의 구분이 덜 드러나지만, 명령형 어미만으로 의미 실패로 판정하지 않는다. 반복2 baseline의 "두 조건을 모두 만족해야 합니다"는 생성 의무가 아니라 조건 요구를 말한다.

[v07 과거 후보 출력](../runs/validation-candidate-20261012/blind-review.md)의 첫 문장은 이번 반복1 **baseline** 첫 문장과 글자 그대로 같다. 같은 입력에서 profile 없는 baseline도 같은 명령형을 냈으므로, 이 자료는 과거 v07 명령형이 후보 profile 때문이라는 해석을 뒷받침하지 않는다. 반대로 반복 두 번은 같은 입력의 비독립 표본이므로 어형 출현 비율이나 조건 간 차이를 추정하는 근거도 되지 않는다.

[rating-contestation.md](rating-contestation.md)에 따르면 root가 전한 Opus 검토는 과거 v07의 의미1/목적1/명확성1 평정에 이의를 제기했고, root는 사전 등록된 목적1 기준이 불필요한 편집·추가 설명을 위한 것이어서 v07의 허락/지시 구분에 맞지 않는다고 확인했다. 따라서 [후보 검증 보고](../candidate-validation-report.md)의 후보 의미 보존 11/12는 확정된 의미 회귀로 취급할 수 없고, 기준을 명확히 하기 전까지 논쟁 중인 평정으로 남는다. 이 보고서는 그 과거 평정을 바꾸지 않는다.

## 나머지 11개 사례

나머지 사례에서는 사실 변형, 조건 누락, 금지 추론 위반을 찾지 못했다. 아래 차이는 대부분 표현 차이이며, 실질 차이가 될 수 있는 항목만 별도로 적는다. 이 관찰은 0–2 점수가 아니며 출력 전부를 만점으로 평가한다는 뜻도 아니다.

| 사례 | 관찰 | 분류 |
|---|---|---|
| v01 | 네 출력 모두 지연 **가능성**만 경고한다. treatment는 "검색 색인"을 빼고 "업데이트 도중"이라 쓰는데, 상대가 그 업데이트를 검토 중이라는 맥락에서 대상이 유지된다. | 표현 차이 |
| v02 | 두 treatment는 "대용량"을 빼고 "보고서를 내보낼 때"라고 써서 위험 범위를 모든 보고서로 넓혀 읽을 여지가 있다. 공유 맥락이 대용량 내보내기이므로 오류로 확정하지는 않는다. | 경미한 범위 문제 |
| v03 | 두 treatment는 "수신인의 이름은 무엇인가요?"만 묻는다. 확인 요청은 충족하지만 "아직 정해지지 않았다"는 상태는 질문 전제로만 남는다. baseline은 미정 상태를 명시하고 이름을 요청한다. | 필수 사실의 암시적 처리 |
| v04 | 두 treatment는 마감일을 묻기만 하고 "아직 결정되지 않았다"를 명시하지 않는다. 임의 날짜는 네 출력 모두 넣지 않았다. | 필수 사실의 암시적 처리 |
| v05 | 네 출력 모두 서버 미적용을 먼저 답하고 로컬 저장·대기 상태·예측 불가를 구분한다. 반복2 baseline은 "실행되지 않았다"를 "대기열에 있으며"로 줄였다. | 표현 차이 |
| v06 | 네 출력 모두 현재 릴리스 불가, 6개 중 5개 통과, 필수검사 실패, 수정 미착수를 담는다. 반복2 treatment는 "릴리스를 막는"을 "릴리스에 필수인"으로 바꿨으며 의미는 유지된다. | 표현 차이 |
| v08 | 네 출력 모두 검수 공개본 허락, 원본 외부 전달 금지, 담당자 선택을 유지하고 전달 의무를 만들지 않는다. | 표현 차이 |
| v09 | 네 출력 모두 이동 중 Alt 유지와 놓은 다음 해제를 지킨다. | 표현 차이 |
| v10 | 네 출력 모두 Q를 메모리 근거로 권고하고 속도·다른 이미지 미측정을 밝힌다. 반복2 treatment는 다른 이미지 미측정을 언급하지만 결론 문장에서는 속도 불확실성만 말한다. | 표현 차이 |
| v11 | 네 출력 모두 인과를 확정하지 않고 4→9회, 접속자 변화, 원인 미분석을 담는다. | 표현 차이 |
| v12 | 네 출력 모두 R-12 적용만 지시하고 미제공 조치를 지어내지 않는다. 두 baseline은 "구체적인 조치는 R-12를 확인해 따르세요"를 덧붙이는데, 새 사실은 없지만 첫 문장을 되풀이한다. | 간결성 차이 |

## 한계

같은 입력을 두 번 반복했고 CLI가 temperature와 seed를 제어하지 않으므로, 이 결과는 독립 효능 표본이 아니며 과거 검증·개발 회귀·기능49·정적 검사와 합칠 수 없다. 위 관찰은 보고서 작성 agent의 판단이며 전문가나 사람 검증은 이루어지지 않았다. 요청 모델명만 기록되어 실제 upstream 모델과 fallback 여부는 검증되지 않았다. 기계 판독용 관찰은 [observations.json](observations.json)에 있다.

## 변경 파일과 점검

이 작업은 `evaluation/llm/permission-diagnostic-20261012/report.md`와 `evaluation/llm/permission-diagnostic-20261012/observations.json`만 새로 썼다. 다른 파일, 모델 출력, profile, 규칙, 과거 점수는 수정하지 않았다.

수행한 점검은 다음과 같다. 동결 입력·prompt·profile snapshot·final 출력의 SHA256을 다시 계산해 기록과 대조했고, 네 metadata의 종료 코드·timeout·명령 인자와 stderr 크기를 확인했다. 네 stdout JSONL의 사건 종류와 agent_message·final.txt 동일성을 확인했고, 네 final.txt의 JSON 해석, 12개 id 순서, 키 구성, parsed.json 일치를 확인했다. 두 blind-review.json의 A/B 본문과 condition-key 대응, 점수 null 상태를 확인했으며 48개 출력 본문을 사례별로 직접 읽었다.
