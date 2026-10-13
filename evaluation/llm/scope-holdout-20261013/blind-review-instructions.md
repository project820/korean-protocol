# 조건을 가린 한국어 답변을 판정한다

blind-review-input.json만 읽고 12개 사례의 A/B를 각각 평가한다. 다른 파일·조건 키·프로필·실행 기록·모델명은 읽지 않는다. source facts와 request, 고정 gold에 한정하며 새 정답을 만들지 않는다. 각 case_position에 semantic_preserved, task_completed, unnecessary_clarification, unsupported_assertion, rationale를 A/B별로 기록하고 aggregate와 unresolved_gold_conflicts를 반환한다. 불명확한 판정은 true로 통과시키지 말고 null과 이유를 기록한다.

clarify는 필요한 정보의 부재를 정확히 설명하거나 확인하는 기능이다. 물음표·직접 질문은 필수가 아니며 정확한 조건부 판단도 허용한다. 실제 자료를 만들거나 조건부 기준을 실제 값으로 단정하면 실패다. 편집에는 초안 밖 모든 배경 사실의 반복을 요구하지 않는다. 의미가 같은 표현은 허용하며 표현 차이만으로 개선으로 세지 않는다. 실제 실행했다고 말하지 않았다는 이유만으로 판정 요청을 실패 처리하지 않는다.

의미 보존과 과제 수행을 분리한다. 필요한 편집 대신 불필요한 질문만 하면 의미 손상이 없어도 과제 수행은 실패다. 요청한 문장 수·문체 조건도 task_completed 판정에 포함한다. 독립 작성한 새 합성 사례지만 한 배치·짝지은 주제이며 사람 독해 실험은 아니다.
