# 사전 고정 LLM 평가 계획

사례와 평정 기준은 실행 전 고정한다. 새로 구성한 독립 holdout 24개와 기존 규약의 회귀 사례 2개를 구분한다. 두 조건에 동일한 26개 입력을 순서대로 제공하고, 조건별로 새 세션에서 한 배치를 한 번 실행한다. smoke 한 번은 분석에서 제외한다. 이 표본은 사람 독자의 이해도와 효능을 일반화하지 않는다.

baseline은 과제 지시만, treatment는 같은 과제 지시와 coding-agent.md를 로컬 AGENTS.md에 자동 로드한다. 전역 CODEX_HOME의 사용자 AGENTS/config/rules/hooks가 baseline에 섞이지 않도록 임시 CODEX_HOME을 만들고 기존 auth.json만 링크한다. 전역 설정이나 인증 내용은 수정·출력하지 않는다. 명시적 CLI 설정은 model=gpt-6.1-sol, provider=subscription_router, base_url=http://127.0.0.1:10100/v1, reasoning_effort=high, read-only, ephemeral이다. seed/temperature는 CLI에서 통제하지 않는다. 응답 생성에는 도구를 쓰지 않도록 지시한다. 본 실행의 provider 설정은 요청 경로의 증거이며, 최종 upstream/FALLBACK 여부는 CLI가 반환하지 않으면 미확인으로 표기한다.

출력 구조는 id/action/text/reason이다. action은 keep/rewrite/clarify이다. 구조 준수와 의미 정확도는 별도로 집계한다. 정답 문장의 exact match는 사용하지 않는다. 각 사례에서 평정자는 의미 보존, 행동 판단 적합성, 명확성, 자연스러운 한국어를 각각 0~2점으로 평가하고, 원문 밖 사실/원인/절차 창작 여부를 기록한다. 의미 보존 2는 모든 필수 사실·조건·부정 범위·양태·시점·대상·화행이 유지됨, 1은 해석 부담이나 경미한 누락, 0은 사실/행동을 바꾸거나 중요한 정보를 창작함을 뜻한다. 명확성 2는 주어진 문맥에서 대상/관계가 식별됨, 1은 개선 여지가 남음, 0은 판단에 필요한 대상/관계가 흐려짐을 뜻한다. 자연성 2는 통상적인 업무 한국어, 1은 어색하지만 해석 가능, 0은 부자연스러움 때문에 이해가 방해됨을 뜻한다. 판단 적합성 2는 허용 action과 맞음, 1은 불필요한 편집/확인, 0은 의미를 확정할 근거 없이 고침을 뜻한다. 미완료 실행은 점수 0과 구별하여 unscored로 남긴다.

원자료는 stdin prompt, CLI JSONL, stderr, final response, exit code, 실행 시각, 명령 설정, 입력/profile SHA256, parse 상태를 보존한다. 수동 독립 검토 파일은 조건을 A/B로 가려 양쪽 실제 출력과 문맥·필수 의미를 함께 제시한다. 조건별 평정 원자료와 요약은 별도 파일로 저장한다. 구현 테스트는 입력 고정/비공개 oracle 제외/자료 보존/구조 오류와 의미 오류의 구분/CLI 격리를 검증하며 실제 모델 효능을 대체하지 않는다.
