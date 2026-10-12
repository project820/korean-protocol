# 독립 어휘 평가의 사전 고정 계획

이 계획과 contexts.json은 사전·예문을 읽기 전에 작성했다. 평가자는 software/work 문맥 40개를 합성했으며 실제 업무 사건이나 자연 코퍼스를 수집하지 않았다. 문맥별 표적 개념 하나를 판정 단위로 사용한다.

고정 분모는 40개이며 software_runtime, work_coordination, data_operations, specification_documentation에 각각 10개를 배정한다. 사전 조회 뒤 문맥·표적 의미·분모를 변경하거나 누락 항목을 제외하지 않는다.

각 문맥에서 표적 개념의 의도한 의미와 사전의 뜻·품사·scope·frame을 비교한다. 같은 표기만 존재하거나 일반적 의미만 부분적으로 겹치면 일치로 집계하지 않는다. 의미와 사용 범위가 함께 맞는 기존 sense ID 하나를 확인하면 matched로 집계한다. 두 개 이상의 기존 ID가 같은 의도 의미를 충족해 구별 근거가 없으면 ambiguous로 집계한다. 기존 ID에 의도 의미가 없거나 scope/frame이 배제하면 unmatched로 집계한다. 단일 후보의 근거가 충분하지 않은 경우에도 ambiguous로 기록하여 분모에 남긴다.

matched 판정과 approved 상태는 별도로 기록한다. proposed 항목을 matched로 판정하더라도 approved coverage에는 넣지 않는다. 사전에 등재된 표적 용어와 프레임 표현의 구별을 유지하며, 규칙상 허용하는 이름·단위·토큰은 허용 경로를 별도로 기록하고 sense ID 일치로 집계하지 않는다.

공개 근거는 schema 및 core/software 사전의 경로·SHA-256, 추출한 후보 ID·의미·상태·scope/frame, 선택 또는 배제 이유를 포함한다. matches.json은 고정 문맥 40개와 1:1로 대응한다. 재현 검사는 문맥 파일 해시, ID 집합, 분모 및 영역별 판정·상태별 수치를 검증한다.

사전 수록률은 이 40개 독립 합성 문맥의 표적 의미에 한정하며 한국어 전체, 실제 현장 효과, 사람 평가, 자연 코퍼스 coverage를 주장하지 않는다. 미지원 개념을 공백으로 보고하며 평가 중 사전을 확장하지 않는다.

contexts.json의 사전 고정 SHA-256은 `25e7242d8a2e43b8afe2f6d2f27821532a119ff3a8af67ef9a7de04539485302`이다. 고정 시각은 2026-10-12T13:23:13Z이다.
