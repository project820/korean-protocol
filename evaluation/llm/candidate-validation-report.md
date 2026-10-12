# 목적 적용 보완 후보의 회귀·신규 검증

후속 교차 검토에서 v07의 감점 근거와 사전 기준 적용에 이견이 확인됐다. 아래 수치는 원래 평정의 기록이며 확정된 의미 오류나 후보 성능 저하의 증거로 단정하지 않는다. [평정 이견 기록](permission-adjudication.md)을 함께 읽어야 한다.

후보 프로필의 새 검증에서는 허용 조건을 실행 지시처럼 표현한 v07이 남았다. 후보는 기존 생성12의 g07 과설명·g11 확인 누락을 개발회귀에서 충족했지만, 그 성공을 새 독립 검증이나 완전 해결로 해석하지 않는다. 새12의 의미 보존 만점은 baseline12/12·후보11/12이고, 다섯 차원 모두 만점은 baseline9/12·후보11/12였다. 의미 보존을 우선하는 목적에서 이 두 집계를 바꾸어 표현하거나 하나의 개선 점수로 합치지 않는다.

## 변경과 사전 고정

이 후보는 coding-agent SCOPES의 작업보고 지시를 작업결과 보고에 조건화하고 기존 EDIT002/DESC005의 필수정보 확인·짧은 경고 목적을 GUARDS에 안내했다. g07/g11의 실제 부족을 관측한 뒤 적용 안내를 조정한 관계를 [실험 계보](runs/validation-candidate-20261012/experiment-lineage.json)에 기록했다. 새 규범이나 정답 문장을 추가한 실험으로 표현하지 않는다.

이전 프로필 SHA는 `5cd4c4657f33e112b9b1c0b95f29a51b689758ccb91155641a38abe6ba93d44e`이고 후보 SHA는 `6ec821d7aa866f520d7d3e1762b393ba40f0ee7ee8ae69905ab767f053d88c4c`이다. 후보는28,665 bytes이며 각 실행의 frozen-profile, 실제 AGENTS snapshot, 메타데이터 digest가 일치한다. 이전 [평가 보고](followup-report.md)의 점수를 새 후보로 이월하지 않았다.

[검증 계획](validation-generation-plan.md)과 [새 validation-holdout12](validation-holdout.json)는 후보 평가 전에 고정했다. 새 사례 SHA는 `7f2aa3ca80ca03293c4aefa48cab0507f2d21ac986b663846582d97c182aaf1f`이다. 새12는 이전 생성12와 같은 사실/요청 문장을 복제하지 않았으며 필요한 정보, 짧은 경고, 요청상태 우선, 정밀조건, 허락/금지, 동시성, 근거범위, 인과 미확인, 참조절차를 새로운 가상 상황으로 구성했다. 부족 유형을 본 뒤 그 유형을 표적 검증한 선택관계는 남아 있으므로 무작위 모집단의 효능 표본으로 해석하지 않는다.

모델에는 facts/request/id만 전달했고 필수 사실·금지 추론·발화목적·간결성 criteria는 prompt에서 제외했다. 자연스러운 한국어 text의 JSON envelope 구조와 내용 평정을 분리했고 golden 문장 exact-match는 쓰지 않았다.

## 실제 실행과 평정

고정한 횟수대로 기존 생성12 후보 개발회귀1회, 기존 편집26 후보 회귀1회, 새12 baseline1회·후보1회만 실행했다. 네 호출 모두 실제 Codex CLI subprocess에서 exit0과 구조 valid를 반환했다. 같은 입력의 반복을 새 독립표본으로 세지 않았고 추가 probe나 재시도는 하지 않았다.

요청 설정은 Sol/high, subscription_router, localhost10100, 임시 CODEX_HOME·프로젝트, read-only/ephemeral/ignore-user-config/ignore-rules였다. auth.json은 기존 안전한 경로를 링크했고 내용을 출력·복사하지 않았다. 요청처리 실패가 없어 caller가 Opus로 모델을 바꾸는 조건은 발생하지 않았다. CLI에는 최종 upstream 모델/provider와 server-side FALLBACK이 반환되지 않았으므로 그 항목은 미확인이다.

root `/root`는 새 [A/B12 packet](runs/validation-candidate-20261012/blind-review.md)을 condition-key 미열람 상태에서 모두 읽고0~2점으로 평정했다. [원평정](runs/validation-candidate-20261012/independent-root-ratings.json)을 먼저 저장하고 key를 열어 [집계](runs/validation-candidate-20261012/summary.json)를 작성했다. root가 보고한 검토 모델은 gpt-6-astra이며 사례 저자/runner 구현자와 별도이지만 후보 문구 통합에도 참여했다. 사람 독자 실험이나 후보 저자와 완전히 독립된 외부 평가라고 표현하지 않는다.

## 새12 검증 결과

| 새 validation12 관측 | baseline | 후보 |
|---|---:|---:|
| 의미 보존 만점 사례 | 12/12 | 11/12 |
| 다섯 차원 모두 만점 사례 | 9/12 | 11/12 |
| 의미 보존 점수 | 24/24 | 23/24 |
| 발화목적 점수 | 24/24 | 23/24 |
| 명확성 점수 | 24/24 | 23/24 |
| 자연성 점수 | 24/24 | 24/24 |
| 간결성 점수 | 21/24 | 24/24 |
| 사실·원인·절차 창작 | 0 | 0 |

v07은 큐 길이20개 이하와 활성작업0개가 모두 참일 때 스냅샷 생성을 **허용하는 조건 안내**였다. 후보는 “큐 길이가 20개 이하이고 활성 작업이 0개인 두 조건을 모두 만족할 때만 스냅샷을 생성하세요”라고 답했다. 조건과 경계값은 남았지만 지시형으로 써 허락/지시와 재량이 덜 명확하므로 의미·목적·명확성에 각1점을 받았다. “때만”은 조건을 제한하므로 조건충족 시 반드시 생성하는 의무까지 확정했다고 주장하지 않으며0점의 명백한 사실변형으로 세지 않았다.

baseline의 v03/v04/v12는 필요한 확인질문·지시 외에 이미 주어진 제목/담당/자료와 작성 계획, 공유절차 참조를 반복하여 간결성1점씩을 받았다. 다른 차원은2점이며 의미왜곡이나 창작은 아니었다. v01/v02의 한문장 경고에서 대상 이름을 짧게 밝힌 것은 새 답변 작성의 허용범위로 보았다. 이는 이미 명확한 원문을 유지해야 하는 편집 s01과 다른 과제이다.

## 개발회귀 결과

기존 생성12의 [이전 프로필 적용 대 후보 packet](runs/candidate-generation-regression-20261012/blind-review.md)과 [원평정](runs/candidate-generation-regression-20261012/independent-root-ratings.json)은 개발회귀이다. 이전 적용은 모든 차원 만점10/12였고 후보는12/12였다. 후보에서 g07의 짧은 경고 과설명과 g11의 필요한 승인자 확인 누락을 해당 입력에서 충족했다. g06은3단계로 나눴지만 버튼 유지조건과 해제시점을 명시해 동시성 손실로 판정하지 않았다.

기존 편집26의 [회귀 packet](runs/candidate-edit-regression-20261012/blind-review.md)과 [원평정](runs/candidate-edit-regression-20261012/independent-root-ratings.json)은 이전 적용·후보 모두 모든 차원26/26을 충족했다.24개 action/text는 같았고 h06/s02의 다른 질문도 필요한 정보를 적절히 확인했다. GUARDS 변경 후 실제로 다시 실행한 결과이며 이전 점수를 그대로 이월한 값이 아니다.

두 회귀에는 root의 기존 입력/출력 기노출과 후보 후속조정 관계가 있다. 이전 프로필 적용 출력은 미적용 baseline이 아니며 condition-key와 development-reference.json에도 그렇게 명명했다. [생성회귀 집계](runs/candidate-generation-regression-20261012/summary.json)·[편집회귀 집계](runs/candidate-edit-regression-20261012/summary.json)·새 validation12 집계는 별도로 보존하고 결합 정확도는 null로 남겼다.

## 원자료·usage·제한

각 실행에는 prompt.txt, stdout.jsonl, stderr.txt, final.txt, metadata.json, parsed.json을 보존했다. [개발 생성 메타데이터](runs/candidate-generation-regression-20261012/treatment/metadata.json), [개발 편집 메타데이터](runs/candidate-edit-regression-20261012/treatment/metadata.json), [새 baseline 메타데이터](runs/validation-candidate-20261012/baseline/metadata.json), [새 후보 메타데이터](runs/validation-candidate-20261012/treatment/metadata.json)는 실제 명령·시각·exit·요청모델·prompt/profile digest를 담는다. 실험 계보는 네 실제 실행, tool item 유형, 반환 usage, 재시도0·probe0·caller 모델변경 없음과 server fallback 미확인을 구분한다.

| 이번 네 호출 | input_tokens | cached_input_tokens | output_tokens |
|---|---:|---:|---:|
| 기존 생성12 후보 회귀 | 24,929 | 0 | 1,032 |
| 기존 편집26 후보 회귀 | 25,365 | 0 | 2,390 |
| 새12 baseline | 17,729 | 0 | 881 |
| 새12 후보 | 24,983 | 0 | 1,169 |

새12의 후보 입력은 baseline보다7,254토큰 많았으며 이 숫자를 비용이나 청구금액으로 환산하지 않았다. 문자열 줄 중복0, 각 case ID의 유일성, oracle 필드가 실제 prompt에 없음, 양쪽 새 prompt의 byte-exact 동일성, 네 exit0/구조valid, 후보 snapshot digest 일치를 검사했다. 이 단계는 새 실험 자료를 작성했으며 runner 소스는 바꾸지 않았다. 기존 runner8개 테스트의 통과 기록은 앞선 보고에 남기고 이 단계의 모델효능 증거와 섞지 않는다.

정적78runtime/43validator 테스트와 독립 기능대응49판정은 언어 출력 성능과 별개이다. 한 모델·고정순서·조건별1batch·반복1·소표본·agent 평정이므로 모델/독자 일반효능, 통계유의성, 현장 성능을 입증하지 않는다. 후보가 이전 두 부족을 해당 개발입력에서 충족해도 새 v07의 허락/지시 구분은 남은 검증 항목이다. 추가 실행은 하지 않았으며 이 보고는 고정된 관측과 한계를 보존한다.
