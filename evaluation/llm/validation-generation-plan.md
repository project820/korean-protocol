# 후보 프로필 개발회귀와 독립 신규 생성 검증 사전 계획

SCOPES의 무조건 작업보고 지시를 작업결과 보고로 조건화하고 기존 EDIT002/DESC005를 GUARDS에서 안내한 후보 profile을 평가한다. 새 규범이나 정답 문장 주입은 이 실험의 변경사항이 아니다. 기존 generation-holdout12의 g07/g11 출력 부족을 관측한 뒤 후보가 마련되었으므로 기존12 재실행은 **개발회귀**로만 기록한다. 이 점수를 독립 holdout 성능이나 일반효능으로 해석하지 않는다.

새 validation-holdout12는 후보 평가 실행 전에 사실묶음·요청·필수 사실·금지 추론·발화목적·간결성 기준을 고정한다. 기존12의 원문이나 출력 문장을 복제하지 않고, 색인·내보내기 경고, 미확인 수신인/검토기한, 서버상태/릴리스 가능성, 정밀조건, 허락/금지, 동시성, 근거범위, 인과 미확인, 공유된 참조절차를 새 사례로 구성한다. 본 사실묶음은 평가용 가상 상황이며 실제 서비스나 작업 상태를 보고하지 않는다.

모델에 주는 입력은 기존 build_generation_prompt와 같은 facts/request/id이고 evaluator의 필수사실·금지추론·criteria는 prompt에서 제외한다. baseline과 candidate에 같은12입력과 순서를 사용한다. 답변은 자연스러운 한국어 text이며 JSON envelope 준수와 내용 평정은 분리한다. golden exact-match는 쓰지 않는다.

기존 생성12 candidate 개발회귀1batch1회, 기존 편집26 candidate 회귀1batch1회, 새12 baseline1batch1회, 새12 candidate1batch1회만 실행한다. GUARDS도 변경되므로 이전 SHA의 편집26 점수를 후보에 이월하지 않는다. 같은 입력의 재실행을 새 독립표본으로 세지 않는다. 추가 probe나 실패 점수에 대한 무한 재시도는 하지 않는다. 후보 profile을 byte snapshot으로 고정하고 SHA256, stdin prompt, CLI JSONL/stderr/final/exit/시각/요청모델설정/usage를 저장한다. 동일 Sol/high/subscription_router/localhost10100/임시 HOME·project/read-only/ephemeral 설정을 유지한다. 최종upstream/FALLBACK은 CLI가 반환하지 않으면 미확인으로 남긴다.

root는 새로운 A/B 무작위 packet의 condition-key를 읽기 전에 전체12사례를 수동 평정한다. 기존12에는 root의 기노출과 profile 후속조정 관계가 있으므로 그 개발회귀를 완전 블라인드나 독립 검증이라고 부르지 않는다. 의미 보존·발화목적·명확성·자연성·간결성에 각각0~2점과 창작 여부를 기록한다. 점수의 정의는 generation-plan.md와 같다. 의미를 그대로 유지해도 확인요청이나 짧은경고 목적을 충족하지 못하면 목적/명확성/간결성에서 감점하고 의미왜곡/창작과 구분한다. 누락/실행실패는 unscored이며0점과 구별한다.

개발회귀·신규독립검증·기존편집평가·정적검증78runtime/43validator·기능대응49판정은 각각의 증거이며 단일 정확도로 합치지 않는다. 모델1종·조건별1batch·반복1·고정순서·소표본·agent 평정·기존실패 뒤 후보조정이라는 제한을 보고한다. 모델/독자 효능·통계유의성·현장효과·비용 개선으로 일반화하거나 반환토큰을 청구금액으로 환산하지 않는다.
