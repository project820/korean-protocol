# 공개 문맥과 정답 기준을 사용해 A/B를 독립 평가한다

blind-review-input.json의 배열 순서를 그대로 유지한다. 각 조건의 의미 보존, 허용 편집 행동 선택, 불필요한 확인 질문, 불필요한 재작성을 개별 판정한다. 표현 차이만으로 오류나 개선을 계산하지 않는다. 새 의미 기준을 추가하거나 기존 정답을 수정하지 않는다. 근거는 해당 문맥·원문·후보와 출력의 구체 표현에 연결한다. 결과는 case_position(1~12), A/B의 semantic_preserved, action_correct, unnecessary_clarification, unnecessary_rewrite 및 짧은 근거를 반환한다. private-condition-key.json, 모델·trace·실행 메타데이터는 읽지 않는다. 이 자료는 기존 합성 12개를 재사용한 개발 회귀이다.
