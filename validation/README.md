# 데이터 검사와 실행 지침 컴파일

Python 3.9 이상의 표준라이브러리만 사용한다.

```sh
python3 -m validation.check --root . --json
python3 -m validation.check --root . --require-coverage 0.9
python3 -m validation.compile --root . --output .
python3 -m unittest discover -s tests -p test_validation.py
```

검사기는 필수 파일과 필드 타입, 빈 발행 필드, ID 중복, 현행 STE 작성 규칙 53개 ID 집합, 선정 규칙→원본 교차 참조, 규칙·어휘별 연결 사례, 사례 판단 불변조건, 의미 충돌과 대안 참조를 검사한다. 작성 사례 파일의 선택 필드 `origin`은 `author`만 허용하며 독립 검토 증거와 구분한다. 비정상 입력에는 오류 목록과 종료 코드 1을 반환한다. `unmapped`와 `partial`은 설계 공백으로 보고하며 기본 검사에서는 공백 자체를 오류로 처리하지 않는다. `--require-coverage`는 설계 대응 비율의 별도 게이트이며 검증 대응률이나 의미 보존 성능을 측정하지 않는다.

`ste_refs`는 관련 원본 기능 참조이며 `target_rule_ids`는 검토로 선정한 실제 대응 규칙이다. 선정 규칙에 해당 원본 참조가 없으면 오류로 처리한다. 관련 참조가 실제 대응 목록에서 빠지면 검토 공백으로 보고하며 이를 충족 기능 수에 더하지 않는다.

`designed_count`는 한국어 규칙이 연결된 `designed`·`verified` 원본 기능 수를 센다. `verified_count`는 현행 파일 해시와 독립 사례를 가리키는 검토 기록이 통과한 원본 기능 수를 센다. `unconfirmed_count`는 완전한 설계 대응이 없는 기능 수이며 `semantically_unconfirmed_count`는 이 검사기가 LLM 실행·독자 실험의 의미 성능을 판정하지 못한 기능 53개를 표시한다. 별도 실행 평가 결과는 이 수치에 자동으로 합치지 않는다. `semantic_verified`는 항상 false이다. 파일 구조 검사와 검토 기록의 무결성 검사는 검토자의 판단을 반복 실행하지 않으며, 독자의 이해도나 LLM 출력의 의미 보존을 증명하지 않는다.

검토 증거는 crosswalk의 `evidence`에 다음과 같이 연결한다.

```json
{"path":"evaluation/functional-review.json","kind":"functional-review","result":"pass"}
```

증거 파일은 `reviewed_rules_sha256`에 `specification/rules.json`, `reviewed_cases_sha256`에 `examples/rule-cases.json`의 현재 파일 바이트 SHA-256을 기록한다. `reviewed_spec_path`는 `docs/spec/korean-rules.md`로 고정하고 `reviewed_spec_sha256`은 그 문서의 현재 SHA-256을 기록한다. `independent_cases_path`와 `independent_cases_sha256`은 독립 기능 검토 사례 JSON을 가리킨다. 사례 파일은 `schema_version: "1.0"`, `purpose: "functional-design-review"`, `cases`를 가지며 각 사례는 `id`, `ste_ids`, `context`, `input`, `expected_decision`, `acceptable_output`, `rejected_output`, `rationale`, `independent`를 포함한다. `independent: false`인 공통 회귀 사례는 검증 증거로 사용하지 않는다. `keep`은 입력을 보존하고 `clarify`는 허용 출력을 null로 두며 `revise`는 비어 있지 않은 출력을 둔다. 거부 출력은 허용 출력과 달라야 한다. 선택 필드 `expected_measurement`의 공백 토큰 수와 명시한 단위 목록·보존 리터럴도 원문과 대조한다. 이 검사는 한국어의 의미 단위를 독립적으로 판정하지 않는다. 독립 사례 ID는 작성 규칙·어휘 사례 ID와 겹칠 수 없다.

증거의 `reviews` 배열에는 `ste_id`, crosswalk와 동일 순서의 `target_rule_ids`, `verdict: "pass"`, 비어 있지 않은 `rationale`·`reviewer`, 해당 원본 기능에 연결된 독립 `case_ids`를 기록한다. 경로는 프로젝트 내부에 있어야 한다. 해시가 바뀌거나 연결 사례가 없으면 `verified_count`에 포함하지 않는다. 이 증거는 기능 설계 검토 기록이며 실제 LLM 의미 평가 기록과 구분한다.

컴파일러는 검사를 통과한 로컬 발행 데이터에서 `profiles/coding-agent.md`, `profiles/chat.md`, `profiles/work-document.md`, `pack/protocol.md`를 생성한다. 모든 규칙의 요구사항·조건·예외를 ID 순서로 본문에 담으며, 실행 프로필의 `( )`는 적용 조건과 `[ ]`는 예외를 표시한다. 컴파일러는 중요한 의미 보존 원칙을 함께 공급한다. 사전의 모든 의미·활용형·논항틀·조건은 배포 사전 JSON에서 확인하며 선택적 용어 요약은 실행 지침에서 생략한다. 출처 메타데이터와 독립 사례 입력은 자동 로딩 지침에 넣지 않는다. 상세 규약에는 편집자가 발행한 규칙별 바른 수정·잘못된 적용·허용 예문을 담는다. 호스트 자동 로딩은 별도 설치기가 담당한다.

실행 프로필당 기본 UTF-8 예산은 30 KiB(30,720 bytes)다. 엔진 0.2.0의 프로필 상한과 같으며 마커·참조 경로를 포함한 관리 블록에는 별도의 32 KiB(32,768 bytes) 상한을 적용한다. 입력 검사와 모든 프로필의 크기 검사를 먼저 마치므로 예산 초과 시 프로필을 일부 생성하거나 자르지 않는다. `--budget`으로 명시적인 더 작은 예산을 검증할 수 있다. 생성된 파일은 스냅샷이므로 데이터 변경 후 다시 컴파일한다.

설치기는 실제 Codex 프로젝트 지침의 잔여 예산도 검사한다. 내부 상한의 변경은 `project_doc_max_bytes`나 사용자 설정을 바꾸지 않는다. 콘텐츠 0.7.0의 호환 최솟값은 엔진 0.2.0이며 구버전 엔진은 콘텐츠 자동 갱신으로 교체하지 않는다.

현재 0.7.0-draft의 프로필은 선택적 용어 요약을 생략하고 사전 JSON을 별도로 제공한다. 작업보고 지시는 작업 결과 보고에만 적용하며 답에 필수인 정보만 묻도록 안내한다. 짧은 경고에 불필요한 확인 상태나 이유를 붙이지 않도록 명시한다. 72개 규칙의 요구사항·조건·예외와 V7 r2의 정보 배열 기준을 포함하며 원문보다 짧아야 한다는 조건은 두지 않는다.

[이전 후보 검증 보고서](../evaluation/llm/candidate-validation-report.md)는 당시 출력과 허락·지시 구분 문제를 기록한다. 이 결과를 현재 프로필의 의미 보존 검증으로 옮겨 쓰지 않는다.
