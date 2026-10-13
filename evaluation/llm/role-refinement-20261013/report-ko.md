# 보완한 조사·논항 규칙을 실제 모델로 진단했다

Sol/high에 요청한 미적용·적용 두 실행이 모두 정상 종료됐고, 세 사례씩 총 여섯 출력이 의미와 역할을 보존했다. 별도 검토자는 A/B 조건 키를 읽지 않고 source·explicit_context·candidate와 실제 출력을 대조했다. 두 조건 모두 KI-PAR-01·03의 후보를 유지하고 KI-PAR-02의 뒤집힌 요청자·수신자를 바로잡았다.

실행 전 plan.md, gold.json, public-input.json, prompt-prefix.txt, prompt.txt, frozen-profile.md와 기존 runner.py의 해시를 고정했다. 두 조건의 공개 입력과 순서는 같으며 기대 판정·예문·평가 근거를 모델에게 주지 않았다. 적용 조건에만 28,652바이트 프로필을 임시 프로젝트의 AGENTS.md로 공급했다.

실행은 기존 runner의 read-only·ephemeral Codex CLI와 localhost OpenCodex 경로를 사용했다. 요청 모델은 gpt-6.1-sol이고 effort는 high다. 두 실행의 종료 코드는 0이며 JSON 구조 검사도 통과했다. capacity 실패나 추가 실행은 없었다. CLI 스트림에 FALLBACK 표시는 없지만 실제 상위 공급자를 관측한 것으로 해석하지 않는다.

원출력과 명령·시각·구조 결과는 sol-baseline과 sol-treatment에 보존했다. structural-evidence.json은 고정 입력의 일치와 출력 해시를 기록한다. blind-review-input.json과 blind-ratings.json은 독립 평정의 입력과 여섯 개 판정을 보존하며, 조건 대응은 condition-key.json에 별도로 기록했다.

이는 규칙 보완 때 이미 본 세 사례의 회귀 진단이다. 새로운 독립 표본, 반복 안정성, 일반 효능 또는 사람의 이해도 개선을 입증하지 않는다. 두 조건이 모두 통과했으므로 프로필의 인과적 개선 효과도 주장하지 않는다. 이번 입력은 파일·도구 읽기를 요청하지 않아 전체 사전 사용을 평가하지 않았다.
