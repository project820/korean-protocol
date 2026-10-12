# Refined profile actual output review packet

The five actual attempts comprise one Sol capacity failure without semantic output and four Opus/high captures. Every semantic rating remains pending. Original input/profile/plan hashes and amended routing hashes were verified. No overall accuracy is claimed.

## opus-01-edit26-treatment

This is a reused-case criteria-only regression. The historical Sol outputs are not a causal comparison.

### h01

Reviewer input and criteria: {"id": "h01", "set": "holdout", "category": "조건", "context": "세 개의 승인 항목이 모두 참이어야 배포할 수 있다.", "source": "승인 A, B, C를 모두 받은 경우에만 배포하세요.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "A/B/C의 논리곱과 배포조건을 유지한다."}

Actual output: {"id": "h01", "action": "keep", "text": "승인 A, B, C를 모두 받은 경우에만 배포하세요.", "reason": "세 승인이 모두 필요하다는 조건과 '경우에만'의 제한이 명확하다."}

### h02

Reviewer input and criteria: {"id": "h02", "set": "holdout", "category": "예외", "context": "본 규정은 임시 계정에 적용되지 않는다.", "source": "관리자 계정을 제외한 모든 정식 계정은 90일마다 비밀번호를 바꿔야 합니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "관리자 제외, 정식 계정 한정,90일 주기,의무를 유지한다."}

Actual output: {"id": "h02", "action": "keep", "text": "관리자 계정을 제외한 모든 정식 계정은 90일마다 비밀번호를 바꿔야 합니다.", "reason": "적용 대상이 정식 계정이므로 임시 계정 제외와 충돌하지 않는다. 제외 범위와 주기, 의무도 명확하다."}

### h03

Reviewer input and criteria: {"id": "h03", "set": "holdout", "category": "동시조건", "context": "손잡이를 계속 잡아야 문이 열린다.", "source": "손잡이를 당긴 채로 문을 밀어 여세요.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "당김 유지와 밀기를 동시에 하며,연속 단계로 분리하지 않는다."}

Actual output: {"id": "h03", "action": "keep", "text": "손잡이를 당긴 채로 문을 밀어 여세요.", "reason": "'-은 채로'가 손잡이를 계속 당긴 상태에서 문을 밀어야 한다는 동시 조건을 정확히 나타낸다."}

### h04

Reviewer input and criteria: {"id": "h04", "set": "holdout", "category": "순서", "context": "업데이트의 필수 순서는 종료,설치,재시작이다.", "source": "앱을 종료한 뒤 업데이트를 설치하고 앱을 다시 켜세요.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "종료→설치→재시작의 순서를 유지한다."}

Actual output: {"id": "h04", "action": "keep", "text": "앱을 종료한 뒤 업데이트를 설치하고 앱을 다시 켜세요.", "reason": "종료, 설치, 재시작의 필수 순서가 문장 순서와 '-ㄴ 뒤'로 드러난다."}

### h05

Reviewer input and criteria: {"id": "h05", "set": "holdout", "category": "부정범위", "context": "각 로그의 검사 결과는 없다.", "source": "모든 로그가 정상인 것은 아닙니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "일부가 정상이 아님을 뜻하며 모두가 비정상이라고 하지 않는다."}

Actual output: {"id": "h05", "action": "keep", "text": "모든 로그가 정상인 것은 아닙니다.", "reason": "부분 부정의 범위가 명확하다. 각 로그의 검사 결과가 없으므로 어떤 로그가 비정상인지 특정하지 않는 원문을 유지한다."}

### h06

Reviewer input and criteria: {"id": "h06", "set": "holdout", "category": "부정범위확인", "context": "원문 외에 작성자의 의도를 확인할 자료는 없다.", "source": "새 드라이버를 설치하지 않은 장비만 점검하지 마세요.", "allowed_actions": ["clarify"], "required_meaning": "이중 부정과 한정 범위를 확인하며 대상을 임의 확정하지 않는다."}

Actual output: {"id": "h06", "action": "clarify", "text": "새 드라이버를 설치하지 않은 장비는 점검하지 말라는 뜻입니까, 아니면 그 장비만 점검하지 말고 새 드라이버를 설치한 장비도 함께 점검하라는 뜻입니까?", "reason": "'만'과 부정의 범위에 따라 점검 대상이 달라진다. 작성자의 의도를 확인할 자료도 없다."}

### h07

Reviewer input and criteria: {"id": "h07", "set": "holdout", "category": "미확인대상", "context": "정 연구원이 한 연구원에게 견적서를 보냈다. 다음 문장의 담당자는 미확인이다.", "source": "그가 금액을 수정했습니다.", "allowed_actions": ["clarify"], "required_meaning": "누가 수정했는지 물으며 정/한 중 하나를 창작하지 않는다."}

Actual output: {"id": "h07", "action": "clarify", "text": "금액을 수정한 사람은 정 연구원과 한 연구원 중 누구입니까?", "reason": "'그'의 후보가 두 명이고 담당자가 확인되지 않았다."}

### h08

Reviewer input and criteria: {"id": "h08", "set": "holdout", "category": "확인된대상", "context": "정 연구원이 한 연구원에게 견적서를 보냈다. 금액 수정자는 한 연구원이다.", "source": "그가 금액을 수정했습니다.", "allowed_actions": ["rewrite"], "required_meaning": "한 연구원이 금액을 수정했다고 명시한다."}

Actual output: {"id": "h08", "action": "rewrite", "text": "한 연구원이 금액을 수정했습니다.", "reason": "문맥에서 수정자가 한 연구원으로 확인되므로 지시어 대신 이름을 쓴다."}

### h09

Reviewer input and criteria: {"id": "h09", "set": "holdout", "category": "진행", "context": "검토 종료 여부는 확인되지 않았다.", "source": "호환성 검토를 진행했습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "검토를 수행한 사실만 유지하며 검토완료/통과를 확정하지 않는다."}

Actual output: {"id": "h09", "action": "keep", "text": "호환성 검토를 진행했습니다.", "reason": "'진행했다'는 종료 여부를 확정하지 않는다. '검토했습니다'로 줄이면 완료로 읽힐 수 있다."}

### h10

Reviewer input and criteria: {"id": "h10", "set": "holdout", "category": "계획실행구분", "context": "오늘은 복원 계획만 정했고 복원은 아직 실행하지 않았다.", "source": "내일 백업을 복원할 예정입니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "내일이라는 시점,예정 상태를 유지하며 이미 복원했다고 쓰지 않는다."}

Actual output: {"id": "h10", "action": "keep", "text": "내일 백업을 복원할 예정입니다.", "reason": "복원이 아직 실행되지 않은 예정 행동임이 '예정'으로 정확히 드러난다."}

### h11

Reviewer input and criteria: {"id": "h11", "set": "holdout", "category": "허락", "context": "삭제 여부는 담당자의 선택이다.", "source": "검사가 끝난 임시 사본은 지워도 됩니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "검사완료 조건과 삭제 허락을 유지하며 명령/의무로 바꾸지 않는다."}

Actual output: {"id": "h11", "action": "keep", "text": "검사가 끝난 임시 사본은 지워도 됩니다.", "reason": "'-아도 된다'가 담당자의 선택에 맡기는 허락을 정확히 나타낸다."}

### h12

Reviewer input and criteria: {"id": "h12", "set": "holdout", "category": "능력", "context": "USB는 해당 센서의 지원 인터페이스이고 지금 연결되어 있지는 않다.", "source": "이 센서는 USB로 데이터를 전송할 수 있습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "지원 기능을 유지하며 실제 전송완료를 주장하지 않는다."}

Actual output: {"id": "h12", "action": "keep", "text": "이 센서는 USB로 데이터를 전송할 수 있습니다.", "reason": "'수 있다'가 현재 연결 상태가 아닌 지원 기능을 나타낸다."}

### h13

Reviewer input and criteria: {"id": "h13", "set": "holdout", "category": "가능성", "context": "서로 다른 두 버전 간 호환이 보장되지 않는다.", "source": "이 버전에서는 일부 플러그인이 작동하지 않을 수 있습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "일부 플러그인의 실패 가능성을 유지하며 확정 실패/원인/시험상태로 바꾸지 않는다."}

Actual output: {"id": "h13", "action": "keep", "text": "이 버전에서는 일부 플러그인이 작동하지 않을 수 있습니다.", "reason": "호환이 보장되지 않는다는 문맥에 맞게 일부 대상과 가능성을 그대로 유지한다."}

### h14

Reviewer input and criteria: {"id": "h14", "set": "holdout", "category": "의무", "context": "재시도는 선택 행동이 아니며 기존 지시의 필수 단계다.", "source": "연결이 끊기면 인증을 다시 받아야 합니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "연결중단 조건과 재인증 의무를 유지한다."}

Actual output: {"id": "h14", "action": "keep", "text": "연결이 끊기면 인증을 다시 받아야 합니다.", "reason": "조건과 필수 행동이 '-아야 한다'로 정확히 표현되어 있다."}

### h15

Reviewer input and criteria: {"id": "h15", "set": "holdout", "category": "잘못된어휘치환", "context": "도입은 새 도구의 조직 배치를 뜻하고 단순 사용과 다르다.", "source": "팀은 새 분석 도구의 도입을 승인했습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "팀/도입 승인 사실을 유지하며 도구사용/구매 완료로 치환하지 않는다."}

Actual output: {"id": "h15", "action": "keep", "text": "팀은 새 분석 도구의 도입을 승인했습니다.", "reason": "'도입'이 승인 대상인 조직 배치를 뜻하는 명사로 쓰여 단순 사용과 구별된다."}

### h16

Reviewer input and criteria: {"id": "h16", "set": "holdout", "category": "전문어", "context": "보존은 원본 기록을 변경없이 남기는 의무이며 예약 기능과 다르다.", "source": "원본 로그는 보존 기간이 끝날 때까지 보존해야 합니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "원본 로그와 보존기간,보존의무를 유지하며 예약/백업으로 잘못 치환하지 않는다."}

Actual output: {"id": "h16", "action": "keep", "text": "원본 로그는 보존 기간이 끝날 때까지 보존해야 합니다.", "reason": "'보존 기간'은 기간 명칭이고 '보존해야'는 의무다. 정의된 용어를 일관되게 쓰고 있어 바꿀 필요가 없다."}

### h17

Reviewer input and criteria: {"id": "h17", "set": "holdout", "category": "기능명", "context": "화면의 버튼 이름은 동기화이고 업로드 버튼은 다른 기능이다.", "source": "변경 사항을 보내려면 동기화 버튼을 누르세요.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "실제 기능명 동기화를 유지하며 업로드로 바꾸지 않는다."}

Actual output: {"id": "h17", "action": "keep", "text": "변경 사항을 보내려면 동기화 버튼을 누르세요.", "reason": "화면의 실제 버튼 이름을 사용해 업로드 버튼과 혼동되지 않는다."}

### h18

Reviewer input and criteria: {"id": "h18", "set": "holdout", "category": "피동예외", "context": "저장한 사람은 중요하지 않고 설정 저장 상태를 알리는 안내다.", "source": "알림 설정이 저장되었습니다.", "allowed_actions": ["keep"], "required_meaning": "명확한 저장 상태 안내를 유지하며 담당자를 창작하지 않는다."}

Actual output: {"id": "h18", "action": "keep", "text": "알림 설정이 저장되었습니다.", "reason": "행위자보다 저장 상태가 중요한 상태 알림이므로 피동을 유지한다."}

### h19

Reviewer input and criteria: {"id": "h19", "set": "holdout", "category": "상태레이블", "context": "작은 표의 승인상태 셀에 넣는 값이다.", "source": "승인 대기", "allowed_actions": ["keep"], "required_meaning": "셀의 짧은 상태 레이블을 유지하며 설명문/완료상태로 늘리거나 바꾸지 않는다."}

Actual output: {"id": "h19", "action": "keep", "text": "승인 대기", "reason": "표의 승인상태 셀 값으로 짧은 명사구가 적절하다."}

### h20

Reviewer input and criteria: {"id": "h20", "set": "holdout", "category": "정중요청", "context": "상대는 외부 협력사이고 검토를 정중하게 요청해야 한다.", "source": "오늘 보내드린 수정안을 검토해 주시겠습니까?", "allowed_actions": ["keep", "rewrite"], "required_meaning": "오늘 발송된 수정안과 정중한 요청을 유지하며 강한 명령으로 바꾸지 않는다."}

Actual output: {"id": "h20", "action": "keep", "text": "오늘 보내드린 수정안을 검토해 주시겠습니까?", "reason": "외부 협력사에 대한 정중한 요청 의문형이 적절하다."}

### h21

Reviewer input and criteria: {"id": "h21", "set": "holdout", "category": "수량단위", "context": "전체 측정기간은 10분이고 평균응답을 보고한다.", "source": "10분 동안 측정한 평균 응답 시간이 800ms에서 600ms로 줄었습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "10분/평균/800→600ms/감소를 유지하며 최대값이나200퍼센트로 바꾸지 않는다."}

Actual output: {"id": "h21", "action": "keep", "text": "10분 동안 측정한 평균 응답 시간이 800ms에서 600ms로 줄었습니다.", "reason": "측정 기간, 평균값, 기준값, 비교값, 단위가 모두 보존되어 있다."}

### h22

Reviewer input and criteria: {"id": "h22", "set": "holdout", "category": "원인미확인", "context": "관측된 사실은 배포 후 오류율증가이며 인과관계는 아직 확인되지 않았다.", "source": "배포 이후 오류율이 높아졌습니다.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "시간상 이후관계만 유지하며 배포가 원인이라고 확정하지 않는다."}

Actual output: {"id": "h22", "action": "keep", "text": "배포 이후 오류율이 높아졌습니다.", "reason": "시간 순서만 말하고 배포를 원인으로 단정하지 않는다."}

### h23

Reviewer input and criteria: {"id": "h23", "set": "holdout", "category": "재량예외", "context": "복구방법은 담당자가 선택하지만 원본 수정은 금지한다.", "source": "원본을 변경하지 않는 범위에서 담당자가 적절한 복구 방법을 선택하세요.", "allowed_actions": ["keep", "rewrite"], "required_meaning": "담당자 재량과 원본 변경금지를 유지하며 특정 복구절차를 강제하지 않는다."}

Actual output: {"id": "h23", "action": "keep", "text": "원본을 변경하지 않는 범위에서 담당자가 적절한 복구 방법을 선택하세요.", "reason": "복구 방법의 선택은 담당자에게 위임하고 원본 수정 금지라는 제약은 유지한다."}

### h24

Reviewer input and criteria: {"id": "h24", "set": "holdout", "category": "알려진절차", "context": "공유된 장애대응 절차 B-7만 이 문맥에 적용되며 내용은 따로 제공하지 않았다.", "source": "장애가 나면 정해진 절차에 따라 대응하세요.", "allowed_actions": ["rewrite"], "required_meaning": "장애조건과 실제 B-7 절차를 가리키며 재시도/삭제 등의 내용을 창작하지 않는다."}

Actual output: {"id": "h24", "action": "rewrite", "text": "장애가 나면 장애 대응 절차 B-7에 따라 대응하세요.", "reason": "'정해진 절차'를 문맥에서 확인된 절차 이름으로 특정한다."}

### s01

Reviewer input and criteria: {"id": "s01", "set": "regression", "category": "가능성회귀", "context": "경고 대상은 현재 검토 중인 새 로그인 기능이고 양측이 그 대상을 공유한다.", "source": "문제가 있을 수 있습니다.", "allowed_actions": ["keep"], "required_meaning": "가능성 경고를 그대로 유지하며 확인상태 장문으로 바꾸지 않는다."}

Actual output: {"id": "s01", "action": "keep", "text": "문제가 있을 수 있습니다.", "reason": "경고 대상을 양측이 공유하는 짧은 경고이므로 이유나 대상을 덧붙이지 않는다."}

### s02

Reviewer input and criteria: {"id": "s02", "set": "regression", "category": "기준확인회귀", "context": "처리기준,원인,참조절차는 정해지지 않았고 별도의 공유문서도 없다.", "source": "오류를 적절히 처리하세요.", "allowed_actions": ["clarify"], "required_meaning": "필요한 처리기준을 물으며 원인/재시도/삭제/절차를 창작하지 않는다."}

Actual output: {"id": "s02", "action": "clarify", "text": "오류는 어떤 기준이나 절차에 따라 처리해야 합니까, 아니면 처리 방법을 담당자가 정해도 됩니까?", "reason": "처리 기준과 참조 절차가 없다. 방법을 위임했는지도 문맥으로 정할 수 없다."}

## opus-02-validation12-treatment

This is a reused-case criteria-only regression. The historical Sol outputs are not a causal comparison.

### v01

Reviewer input and criteria: {"id": "v01", "set": "validation-holdout", "category": "짧은경고", "facts": ["대화 상대는 지금 검색 색인 업데이트를 검토하고 있다.", "업데이트 도중 검색 결과가 늦게 나타날 가능성이 있다.", "실제 지연이 발생했다는 자료는 없다."], "request": "상대에게 검색 지연 가능성만 짧게 경고하라.", "required_facts": ["업데이트도중검색결과지연가능성"], "forbidden_inferences": ["지연발생확정", "지연원인창작", "없는시험/확인약속"], "speech_purpose": "짧은가능성경고", "concision_criteria": "공유된 검토대상과 발생확인 상태를 필요 없이 반복하지 않고 요청한 경고에 집중한다."}

Actual output: {"id": "v01", "text": "색인 업데이트 중에는 검색 결과가 늦게 나타날 수 있어요."}

### v02

Reviewer input and criteria: {"id": "v02", "set": "validation-holdout", "category": "짧은경고", "facts": ["상대와 함께 대용량 보고서 내보내기 기능을 살펴보고 있다.", "표의 마지막 행이 빠질 위험이 있다.", "누락된 행의 실제 사례나 원인은 제공되지 않았다."], "request": "마지막 행 누락 위험을 한 번 경고하라.", "required_facts": ["마지막행누락위험"], "forbidden_inferences": ["누락확정", "임의원인/누락예시", "없는복구조치명령"], "speech_purpose": "위험경고", "concision_criteria": "상세유형이나 점검결과 설명으로 늘리지 않고 제공된 위험만 알린다."}

Actual output: {"id": "v02", "text": "대용량 보고서를 내보낼 때 표의 마지막 행이 빠질 수 있어요."}

### v03

Reviewer input and criteria: {"id": "v03", "set": "validation-holdout", "category": "미확인필수정보", "facts": ["안내문의 발송인은 김 담당자이다.", "제목은 서버 점검 안내로 정해졌다.", "받는 사람의 이름은 정해지지 않았다."], "request": "수신인의 이름을 넣은 안내문을 지금 작성해 달라는 요청에 답하라.", "required_facts": ["수신인미정", "수신인이름확인필요"], "forbidden_inferences": ["김담당자를수신인으로확정", "임의수신인이름", "실제발송/조회주장"], "speech_purpose": "필수정보확인", "concision_criteria": "필요한 수신인 이름을 질문하거나 확인할 행동을 제시하며 작성불가와 알려진 제목만 반복하지 않는다."}

Actual output: {"id": "v03", "text": "안내문에 넣을 수신인 이름을 알려 주세요."}

### v04

Reviewer input and criteria: {"id": "v04", "set": "validation-holdout", "category": "미확인필수정보", "facts": ["검토자는 박 담당자로 배정됐다.", "보낼 자료는 설계안 3차본이다.", "제출 마감일은 아직 결정되지 않았다."], "request": "마감 날짜까지 포함한 검토 요청을 작성해 달라는 요청에 답하라.", "required_facts": ["마감일미결정", "마감일확인필요"], "forbidden_inferences": ["임의날짜/오늘/내일마감확정", "검토완료주장", "박담당자외담당자창작"], "speech_purpose": "필수정보확인", "concision_criteria": "요청에 필수인 마감일을 확인하며 알려진 사람/자료를 되풀이하는 것만으로 끝내지 않는다."}

Actual output: {"id": "v04", "text": "검토 요청에 넣을 제출 마감일을 알려 주세요."}

### v05

Reviewer input and criteria: {"id": "v05", "set": "validation-holdout", "category": "요청상태우선", "facts": ["색인 규칙은 로컬 파일에 저장됐다.", "검색 서버 적용 작업은 대기열에만 있고 실행되지 않았다.", "대기 시간을 예측할 자료는 없다."], "request": "사용자가 검색 서버에서도 새 규칙을 쓰고 있는지 물었다. 답하라.", "required_facts": ["검색서버아직미적용", "로컬규칙저장", "적용작업대기"], "forbidden_inferences": ["서버새규칙사용중", "임의완료시각", "실행/검증완료주장"], "speech_purpose": "질문상태답변", "concision_criteria": "서버 적용 여부를 먼저 답하고 필요한 로컬/대기 상태를 구분하며 변경위치 보고를 강제하지 않는다."}

Actual output: {"id": "v05", "text": "아니요, 검색 서버에서는 아직 새 규칙을 쓰지 않아요. 새 색인 규칙은 로컬 파일에만 저장됐어요. 검색 서버에 적용하는 작업은 대기열에 있지만 아직 실행되지 않았어요. 언제 실행될지는 예측할 자료가 없어요."}

### v06

Reviewer input and criteria: {"id": "v06", "set": "validation-holdout", "category": "결정상태우선", "facts": ["릴리스 전 검사 6개 중 5개는 통과했다.", "대용량 파일 열기 검사는 실패했으며 릴리스를 막는 필수검사다.", "수정 작업은 아직 시작하지 않았다."], "request": "사용자가 지금 릴리스해도 되는지 물었다. 확인된 근거로 답하라.", "required_facts": ["필수검사실패로현재릴리스불가", "6개중5개통과", "대용량파일열기실패"], "forbidden_inferences": ["전체검사통과", "실패해결/수정완료", "근거없는릴리스허락"], "speech_purpose": "릴리스판단답변", "concision_criteria": "질문의 결정을 바꾸는 실패를 먼저 밝히고 통과5개를 앞세워 핵심제약을 숨기지 않는다."}

Actual output: {"id": "v06", "text": "아니요, 지금은 릴리스하면 안 돼요. 릴리스 전 검사 6개 중 5개는 통과했어요. 하지만 대용량 파일 열기 검사가 실패했고, 이 검사는 실패하면 릴리스를 막는 필수 검사예요. 이 실패를 고치는 작업은 아직 시작하지 않았어요."}

### v07

Reviewer input and criteria: {"id": "v07", "set": "validation-holdout", "category": "정밀조건", "facts": ["스냅샷 생성은 큐 길이가 20개 이하이고 활성 작업이 0개일 때만 허용한다.", "두 조건 중 하나만 만족하면 생성하면 안 된다."], "request": "스냅샷 생성 조건을 담당자에게 알려라.", "required_facts": ["큐길이20이하", "활성작업0", "두조건논리곱/허용"], "forbidden_inferences": ["20미만으로경계변형", "조건논리합", "허용을생성의무로변형"], "speech_purpose": "조건부허락", "concision_criteria": "경계값과 두 조건의 결합을 유지하고 불필요한 새 확인절차를 추가하지 않는다."}

Actual output: {"id": "v07", "text": "스냅샷은 큐 길이가 20개 이하이고 활성 작업이 0개일 때만 생성할 수 있어요. 두 조건을 모두 만족해야 하며, 둘 중 하나만 만족하면 생성하면 안 돼요."}

### v08

Reviewer input and criteria: {"id": "v08", "set": "validation-holdout", "category": "허락과금지", "facts": ["검수한 공개본은 협력사에 전달해도 된다.", "원본 도면은 외부 전달을 금지한다.", "공개본 전달 여부는 담당자가 선택한다."], "request": "자료 전달 기준과 담당자의 선택권을 알려라.", "required_facts": ["검수공개본전달허락", "원본외부전달금지", "담당자선택"], "forbidden_inferences": ["공개본전달의무", "원본전달허용", "검수조건삭제"], "speech_purpose": "허락/금지안내", "concision_criteria": "허락과 금지의 대상을 나누고 담당자가 선택할 여지를 남긴다."}

Actual output: {"id": "v08", "text": "원본 도면은 외부로 전달하면 안 돼요. 검수한 공개본은 협력사에 전달해도 돼요. 공개본을 전달할지는 담당자님이 선택하시면 돼요."}

### v09

Reviewer input and criteria: {"id": "v09", "set": "validation-holdout", "category": "동시성", "facts": ["선택한 타일을 옮기는 동안 Alt 키를 계속 눌러야 정렬 모드가 유지된다.", "타일을 목적 위치에 놓은 다음 Alt 키를 뗀다."], "request": "정렬 모드를 유지한 채 타일을 옮기는 방법을 안내하라.", "required_facts": ["이동중Alt계속누름", "목적위치놓은다음Alt해제"], "forbidden_inferences": ["키누르고즉시해제후이동", "없는추가키/동작", "이동완료이전키해제"], "speech_purpose": "동시조건절차", "concision_criteria": "지속상태와 해제시점을 연결하고 따로 순서를 나눠 동시성을 잃지 않는다."}

Actual output: {"id": "v09", "text": "정렬 모드를 유지한 채 타일을 옮기려면 다음 순서로 하세요.\n1. Alt 키를 누른 채로 선택한 타일을 목적 위치까지 옮기세요. 옮기는 동안 Alt 키를 계속 눌러야 정렬 모드가 유지돼요.\n2. 타일을 목적 위치에 놓은 다음 Alt 키를 떼세요."}

### v10

Reviewer input and criteria: {"id": "v10", "set": "validation-holdout", "category": "근거범위권고", "facts": ["12개 이미지의 미리보기 시험에서 방식 P의 최고 메모리는 1.4GB, 방식 Q는 1.1GB였다.", "처리속도와 다른 이미지의 메모리는 측정하지 않았다.", "사용자는 메모리를 줄이되 처리속도도 유지하고 싶다."], "request": "어느 방식을 검토할지 권고하고 근거 범위를 밝혀라.", "required_facts": ["12이미지시험", "P1.4GB/Q1.1GB", "속도/다른이미지미측정", "메모리와속도기준"], "forbidden_inferences": ["Q가항상빠르고메모리적음", "다른이미지성능보장", "처리속도측정완료"], "speech_purpose": "조건부권고", "concision_criteria": "측정범위의 Q메모리우위와 부족한 속도정보를 나눠 근거범위 안에서 권고한다."}

Actual output: {"id": "v10", "text": "메모리를 줄이려면 방식 Q를 먼저 검토하시길 권해요. 12개 이미지로 미리보기를 시험했을 때 최고 메모리는 Q가 1.1GB로, P의 1.4GB보다 0.3GB 낮았어요. 다만 이 근거는 그 12개 이미지의 최고 메모리에만 해당해요. 처리속도와 다른 이미지의 메모리는 측정하지 않았기 때문에 Q로 처리속도를 유지할 수 있는지는 알 수 없어요. 처리속도도 유지해야 하므로 Q를 정하기 전에 두 방식의 처리속도를 측정해 비교해 보시는 것이 좋아요."}

### v11

Reviewer input and criteria: {"id": "v11", "set": "validation-holdout", "category": "인과미확인", "facts": ["캐시 설정을 바꾼 뒤 재요청 수가 분당 4회에서 9회로 늘었다.", "동시에 접속자 수도 변했다.", "캐시 설정이 증가 원인인지 분석하지 않았다."], "request": "캐시 설정 변경이 재요청 증가를 일으켰는지 묻는 사용자에게 답하라.", "required_facts": ["변경후분당4→9", "원인미분석", "동시접속자수변화"], "forbidden_inferences": ["캐시설정이원인확정", "접속자수가원인확정", "원인분석완료"], "speech_purpose": "인과확인상태설명", "concision_criteria": "관측과 원인분석 상태를 구분하고 어느 원인도 임의로 확정하지 않는다."}

Actual output: {"id": "v11", "text": "캐시 설정 변경 때문에 재요청이 늘었는지는 아직 알 수 없어요. 설정을 바꾼 뒤 재요청 수가 분당 4회에서 9회로 늘어난 것은 맞아요. 하지만 같은 시기에 접속자 수도 바뀌었고, 캐시 설정이 증가 원인인지는 분석하지 않았어요."}

### v12

Reviewer input and criteria: {"id": "v12", "set": "validation-holdout", "category": "참조절차", "facts": ["형식 변환이 실패하면 공유된 대응 규정 R-12를 적용한다.", "이 문맥에 다른 대응 규정은 없다.", "R-12의 구체적인 조치는 여기 제공하지 않았다."], "request": "변환 실패 시 대응 지시를 작성하라.", "required_facts": ["변환실패조건", "공유대응규정R-12참조"], "forbidden_inferences": ["재시도/삭제/재시작조치창작", "임의다른규정", "실패없이무조건절차실행"], "speech_purpose": "공유절차지시", "concision_criteria": "추상적인 대응 말 대신 실제 참조 R-12를 밝히고 미제공 조치 내용을 채우지 않는다."}

Actual output: {"id": "v12", "text": "형식 변환이 실패하면 대응 규정 R-12를 적용하세요."}

## Supplement6 paired targeted diagnostic

The profile was refined after these cases were seen. Both arms requested Opus/high with identical prompts. Original gold is shown only for the reviewer. Adequate candidates expect keep and inconsistent candidates expect rewrite. Equivalent correct wording need not match acceptable_output.

### KI-SUP-ASP-01

Reviewer source/context/gold: {"id": "KI-SUP-ASP-01", "family": "aspect_and_modality", "case_type": "normal", "explicit_context": "가상의 도형 연습이다. 루미는 지금 점 세 개를 그리는 작업을 하고 있다. 작업은 시작되었고 아직 끝나지 않았다. 완성된 점의 수는 정하지 않았다.", "source": "루미는 지금 점 세 개를 그리는 중이다. 아직 그리기를 마치지 않았다.", "candidate": "루미는 지금 점 세 개를 그리고 있다. 아직 그리기를 마치지 않았다.", "expected_decision": "accept", "acceptable_output": "루미는 지금 점 세 개를 그리고 있다. 아직 그리기를 마치지 않았다.", "rejected_output": "루미는 지금 점 세 개를 다 그렸다.", "rationale": "이 맥락에서 그리는 중이다와 그리고 있다는 진행 중인 같은 작업을 나타낸다. 다 그렸다는 완료 주장으로 바뀌어 아직 마치지 않았다는 사실과 충돌한다.", "preserved_facts": ["행위자는 루미다.", "작업 대상은 점 세 개다.", "그리기 작업이 현재 진행 중이다.", "그리기 작업은 아직 끝나지 않았다.", "이미 완성한 점의 수는 제시되지 않았다."], "prohibited_changes": ["진행을 완료로 바꾸지 않는다.", "점의 완성 수나 진행률을 추가하지 않는다.", "그리기의 진행 해석을 모든 고 있다 표현의 유일한 해석으로 일반화하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-ASP-01", "action": "keep", "text": "루미는 지금 점 세 개를 그리고 있다. 아직 그리기를 마치지 않았다.", "reason": "'그리고 있다'는 원문의 '그리는 중이다'와 같이 진행 중인 동작을 나타냅니다. 그리기를 아직 마치지 않았다는 상태도 그대로 유지했습니다."}

Treatment actual output: {"id": "KI-SUP-ASP-01", "action": "keep", "text": "루미는 지금 점 세 개를 그리고 있다. 아직 그리기를 마치지 않았다.", "reason": "'그리다'에 붙은 '-고 있다'는 동작이 진행 중임을 나타낸다. 후보는 '그리는 중이다'의 진행 의미를 유지하고, 미완료 문장도 그대로 둔다."}

### KI-SUP-ASP-02

Reviewer source/context/gold: {"id": "KI-SUP-ASP-02", "family": "aspect_and_modality", "case_type": "failure", "explicit_context": "가상의 인물 관찰 기록이다. 지호는 조금 전에 안경을 썼고 지금도 안경을 착용한 상태다. 관찰 순간에는 안경을 얼굴에 올리는 동작을 하고 있지 않다.", "source": "지호는 지금 안경을 쓰고 있다.", "candidate": "지호는 지금 안경을 쓰는 중이다.", "expected_decision": "reject", "acceptable_output": "지호는 지금 안경을 착용한 상태다.", "rejected_output": "지호는 지금 안경을 쓰는 중이다.", "rationale": "원문의 쓰고 있다는 이 맥락에서 착용 후 유지되는 상태다. 쓰는 중이다는 안경을 쓰는 동작의 진행을 주장하므로 동작이 이미 끝났다는 맥락과 충돌한다.", "preserved_facts": ["관찰 대상은 지호다.", "지호는 현재 안경을 착용하고 있다.", "안경을 쓰는 동작은 관찰 이전에 완료되었다.", "관찰 순간에는 안경을 쓰는 동작이 진행되지 않는다."], "prohibited_changes": ["착용 결과 상태를 착용 동작의 진행으로 바꾸지 않는다.", "안경을 벗었거나 쓰지 않았다고 주장하지 않는다.", "모든 고 있다 표현을 진행으로 일괄 변환하지 않는다.", "안경의 색이나 착용 이유를 추가하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-ASP-02", "action": "rewrite", "text": "지호는 지금 안경을 쓴 상태다.", "reason": "후보의 '쓰는 중이다'는 안경을 얼굴에 올리는 동작이 진행 중이라는 뜻으로 읽힙니다. 문맥상 지호는 이미 안경을 쓴 상태이므로 착용 상태가 분명히 드러나게 고쳤습니다."}

Treatment actual output: {"id": "KI-SUP-ASP-02", "action": "rewrite", "text": "지호는 지금 안경을 쓰고 있다.", "reason": "원문의 '쓰고 있다'는 안경을 착용한 결과 상태가 이어지고 있다는 뜻이다. 후보의 '쓰는 중이다'는 안경을 얼굴에 올리는 동작이 진행 중이라는 뜻이 되어, 지금 그 동작을 하지 않는다는 문맥과 어긋난다."}

### KI-SUP-ASP-03

Reviewer source/context/gold: {"id": "KI-SUP-ASP-03", "family": "aspect_and_modality", "case_type": "keep", "explicit_context": "가상의 그리기 활동 기록이다. 혜윤은 지정된 도형 하나를 모두 그렸고 그리기 작업은 끝났다. 혜윤이 같은 도형을 다시 그리기 시작한 사실은 없다.", "source": "혜윤은 도형을 다 그렸다.", "candidate": "혜윤은 도형을 다 그렸다.", "expected_decision": "keep", "acceptable_output": "혜윤은 도형을 다 그렸다.", "rejected_output": "혜윤은 도형을 그리고 있다.", "rationale": "다 그렸다는 완료를 간결하고 자연스럽게 전달한다. 그리고 있다로 바꾸면 이 맥락에서 완료된 그리기 작업을 진행 중인 작업으로 바꾸게 된다.", "preserved_facts": ["행위자는 혜윤이다.", "그린 대상은 지정된 도형이다.", "도형 그리기가 모두 완료되었다.", "그리기 작업은 진행 중이 아니다."], "prohibited_changes": ["완료를 진행으로 바꾸지 않는다.", "도형을 다시 그리는 새 작업을 추가하지 않는다.", "완성까지 걸린 시간이나 완성 품질을 추가하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-ASP-03", "action": "keep", "text": "혜윤은 도형을 다 그렸다.", "reason": "후보는 원문과 같고, 그리기가 끝났다는 완료 의미를 정확히 전달합니다."}

Treatment actual output: {"id": "KI-SUP-ASP-03", "action": "keep", "text": "혜윤은 도형을 다 그렸다.", "reason": "후보는 원문과 같다. 도형 하나를 모두 그려 작업이 끝났다는 완료 상태를 그대로 전한다."}

### KI-SUP-CAU-01

Reviewer source/context/gold: {"id": "KI-SUP-CAU-01", "family": "passive_and_causative", "case_type": "normal", "explicit_context": "가상의 리본 제작 기록이다. 세나는 이든에게 리본 자르기를 지시했다. 세나는 직접 자르지 않았고 이든이 지시에 따라 리본을 실제로 잘랐다.", "source": "세나는 이든에게 리본을 자르게 했다. 이든이 리본을 잘랐다.", "candidate": "세나의 지시로 이든이 리본을 잘랐다.", "expected_decision": "accept", "acceptable_output": "세나의 지시로 이든이 리본을 잘랐다.", "rejected_output": "이든의 지시로 세나가 리본을 잘랐다.", "rationale": "명시된 지시 맥락에서 사동의 지시자 세나와 실제 행위자 이든을 한 문장으로 유지할 수 있다. 거절 예문은 지시자와 실제 행위자를 뒤집는다.", "preserved_facts": ["세나가 자르기를 지시했다.", "이든이 실제로 리본을 잘랐다.", "세나가 직접 자른 것은 아니다.", "리본 자르기가 실제로 이루어졌다."], "prohibited_changes": ["지시자와 실제 행위자를 바꾸지 않는다.", "실제 자르기를 단순한 예정이나 지시만으로 축소하지 않는다.", "리본 수량이나 자르는 목적을 추가하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-CAU-01", "action": "keep", "text": "세나의 지시로 이든이 리본을 잘랐다.", "reason": "세나가 지시했고 이든이 실제로 잘랐다는 역할과 사동 관계를 그대로 보존했으며 표현도 자연스럽습니다."}

Treatment actual output: {"id": "KI-SUP-CAU-01", "action": "keep", "text": "세나의 지시로 이든이 리본을 잘랐다.", "reason": "세나가 지시했고 이든이 실제로 리본을 잘랐다는 사동주와 행위자, 대상의 관계가 그대로 유지된다. 세나가 직접 자르지 않았다는 사실과도 어긋나지 않는다."}

### KI-SUP-CAU-02

Reviewer source/context/gold: {"id": "KI-SUP-CAU-02", "family": "passive_and_causative", "case_type": "keep", "explicit_context": "가상의 대화 장면이다. 선오가 농담을 했고 그 농담 때문에 다미가 웃었다. 선오는 다미에게 웃으라고 지시하지 않았고 다미는 자연스럽게 웃었다.", "source": "선오가 농담으로 다미를 웃겼다.", "candidate": "선오가 농담으로 다미를 웃겼다.", "expected_decision": "keep", "acceptable_output": "선오가 농담으로 다미를 웃겼다.", "rejected_output": "다미가 선오에게 웃으라고 지시했다.", "rationale": "웃겼다는 원인 제공자 선오와 실제 웃은 사람 다미를 자연스럽게 표현하는 사동이다. 사동을 반드시 지시로 풀면 맥락에 없는 명령을 만들며 거절 예문은 인물의 역할도 바꾼다.", "preserved_facts": ["선오가 농담을 했다.", "농담 때문에 다미가 실제로 웃었다.", "웃은 사람은 다미다.", "다미에게 웃으라는 지시는 없었다."], "prohibited_changes": ["원인 제공자와 실제 웃은 사람을 바꾸지 않는다.", "사동을 명령이나 의무로 일괄 해석하지 않는다.", "농담 내용이나 웃은 시간을 추가하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-CAU-02", "action": "keep", "text": "선오가 농담으로 다미를 웃겼다.", "reason": "후보는 원문과 같습니다. 선오의 농담 때문에 다미가 웃었다는 원인 관계를 나타내며 지시의 의미는 없습니다."}

Treatment actual output: {"id": "KI-SUP-CAU-02", "action": "keep", "text": "선오가 농담으로 다미를 웃겼다.", "reason": "후보는 원문과 같다. 선오의 농담이 원인이 되어 다미가 웃었다는 관계를 전하고, 웃으라는 지시가 있었다는 뜻은 담지 않는다."}

### KI-SUP-PAS-01

Reviewer source/context/gold: {"id": "KI-SUP-PAS-01", "family": "passive_and_causative", "case_type": "failure", "explicit_context": "가상의 연극 동작 기록이다. 예나가 지후를 밀었고 지후가 밀림을 당했다. 지후가 예나를 민 동작은 없었다. 두 사람 외에 다른 행위자는 없다.", "source": "지후가 예나에게 밀렸다.", "candidate": "지후가 예나를 밀었다.", "expected_decision": "reject", "acceptable_output": "예나가 지후를 밀었다.", "rejected_output": "지후가 예나를 밀었다.", "rationale": "피동문의 주어 지후는 밀림을 당한 사람이고 에게가 붙은 예나는 명시된 행위자다. 후보는 피동을 능동으로 바꾸면서 두 역할을 뒤집는다. 허용 예문은 원문에 이미 있는 행위자만 사용한다.", "preserved_facts": ["미는 행위자는 예나다.", "밀림을 당한 사람은 지후다.", "미는 동작은 실제로 이루어졌다.", "지후가 예나를 민 동작은 없다."], "prohibited_changes": ["피동의 대상과 행위자를 바꾸지 않는다.", "명시된 예나 외에 행위자를 만들어 내지 않는다.", "동작의 의도나 힘의 크기를 추가하지 않는다."]}

Baseline actual output: {"id": "KI-SUP-PAS-01", "action": "rewrite", "text": "지후가 예나에게 밀렸다.", "reason": "후보는 지후가 예나를 민 것으로 행위자와 대상을 뒤바꿨습니다. 문맥상 민 사람은 예나이므로 원문의 피동 관계로 되돌렸습니다."}

Treatment actual output: {"id": "KI-SUP-PAS-01", "action": "rewrite", "text": "지후가 예나에게 밀렸다.", "reason": "후보는 지후가 예나를 민 것으로 행위자와 대상을 뒤바꿨다. 문맥에서 민 사람은 예나이고 밀린 사람은 지후이므로, 지후를 주어로 둔 원문의 피동 구조를 유지한다."}

