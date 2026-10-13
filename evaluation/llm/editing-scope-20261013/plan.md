# 편집 범위 변경의 개발 회귀를 실행 전에 고정한다

이 실험은 evaluation/llm/lexicon-usage-20261013의 기존 합성 사례 12개와 실행 전 정답 검토 gold-adjudication.json을 그대로 재사용한다. 이 표본은 독립 검증이나 새로운 홀드아웃이 아니다. 사례를 개발 회귀로 사용하며 사례별 의미 보존과 편집 행동을 별도로 검토한다. 전체 한국어 규약 효능, 독자 이해도, 미관측 어휘 의미 성능으로 확대하지 않는다.

## 비교 입력을 고정한다

OLD는 git 45f86c6의 profiles/coding-agent.md이고 NEW는 편집에 필요한 정보와 실제 실행에 필요한 정보를 구별한 변경을 컴파일한 profiles/coding-agent.md다. 두 조건 모두 동일한 전체 lexicon/core.json 및 lexicon/domains/software.json을 제공한다. 공개 입력, 입력 순서와 프롬프트는 기존 run.py의 public_cases와 build_prompt를 그대로 사용한다. 기존 실험과 실행기는 수정하지 않는다.

원본 cases.json과 gold-adjudication.json을 바이트 그대로 이 디렉터리에 보존한다. 프로필, 두 사전, 사례, 정답, 계획, 기존 실행기 및 공유 실행기의 해시와 정확한 프롬프트 해시를 각 조건의 별도 manifest에 고정한다. root가 PROFILE_READY를 보낸 뒤 NEW 프로필과 사전을 복사하고 기존 실행기 source_contract로 OLD/NEW manifest를 생성한다. 실제 호출 전 prepare-only로 계약과 마운트 해시를 검사한다. 정답·계획·manifest는 모델 임시 작업 폴더에 넣지 않는다.

## 실제 모델 호출을 제한한다

기존 evaluation/llm/lexicon-usage-20261013/run.py로 OLD 다음 NEW를 실행하며 두 호출 모두 --condition treatment를 사용한다. 비어 있는 baseline은 사용하지 않는다. 조건당 한 배치이고 모델은 OpenCodex localhost subscription_router 경로의 gpt-6.1-sol/high다. capacity 오류가 관측되면 실패한 호출과 원시 trace를 보존하고 두 조건을 모두 anthropic/claude-opus-5-5/high로 실행한다. CLI 호출은 최대 네 번이다. 의미 실패, 환경·입력 오류 또는 형식 실패에 대한 재시도는 하지 않는다. fallback 표시가 있는 호출은 유효 비교에서 제외한다.

임시 CODEX_HOME은 기존 auth.json만 심볼릭 링크로 참조하고 사용자·전역 설정을 읽지 않는다. 사용자·전역 설정을 수정하지 않는다. 실제 공급자와 자동 fallback이 CLI에 반환되지 않으면 요청 모델 및 그 관측 한계를 공개한다. read-only sandbox는 쓰기를 제한하지만 cwd만 읽는 보안 경계가 아니다. 원시 trace의 모든 도구 호출을 검토하여 작업 폴더 밖 파일·인터넷·다른 모델·에이전트 사용 여부를 기록한다. 마운트 파일의 실행 전후 해시와 파일 집합이 같은지 기록한다.

## 의미와 행동을 독립 검토자에게 맡긴다

별도 검토자는 공개 사례의 문맥·원문·후보·개념과 기존 gold의 필수 의미·금지 추론·허용 행동을 읽고 A/B의 action·text만 평가한다. packet에는 원본 사례 ID, 조건 이름, 모델 이름, 이유, 사전 ID, trace, reviewer 설명을 넣지 않는다. 조건 대응 키는 별도 private 파일에 둔다. 실행 담당자는 의미 점수를 매기지 않는다.

12개 전체의 의미 보존과 행동 적절성을 검토하며, LX12는 기준 치수 없이도 상대 오차 ±2 mm를 보존하여 rewrite할 수 있어야 한다. 실제 간격 상한 2 mm나 기준 간격 0 mm를 만들어서는 안 된다. 기준 치수는 실제 검사에 필요한 정보이지만 문장을 고치는 데 필수인 정보가 아니므로 질문만 반환하면 불필요한 확인으로 기록한다. LX09는 기존 gold가 keep/rewrite/clarify 모두를 허용하므로 행동 구분력이 낮은 사례로 기록한다. 양쪽이 같은 기준을 만족하면 개선으로 계산하지 않는다.

독립 검토와 원시 trace 경계 검토가 끝나기 전에는 의미 성과를 주장하지 않는다. 실행 구조 성공, 실제 사전 조회, 의미 성공, 행동 성공을 서로 구별한다. 이 평가의 범위에는 보안 구현이 포함되지 않는다.
