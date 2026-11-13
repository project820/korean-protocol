P2 지적 7건과 P3 지적 2건을 확인했습니다. 핵심 문제는 조건·경고의 배치 충돌, 새 진단의 오탐·미탐, 평가 결과의 버전·반복 조건 표기입니다.

**[P2] 결과 패널의 순서가 경고를 행동보다 뒤에 둡니다.**

- 위치는 [interactive-html.md:46](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/references/interactive-html.md:46>)입니다.
- 근거는 “상태 결과는 '누가 무엇을 한다' 문장 하나로 쓴다”를 2번에, “현재 결과에 걸린 기한·예외·금지를 쓴다”를 4번에 둔 순서입니다.
- 행동을 제시하는 상태 결과에 이 순서를 적용하면 [SKILL.md:125](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/SKILL.md:125>)의 “경고·금지·필수 조건·조건부 허용은 … 관련 행동 앞에 둔다”와 충돌합니다.
- 최소 수정안은 행동형 결과에서 필수 조건·경고를 해당 행동 앞에 배치하도록 예외를 명시하는 것입니다.

**[P2] Mermaid 라벨 규칙이 보호 문자열의 따옴표를 바꾸도록 지시합니다.**

- 위치는 [output-formats.md:109](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/references/output-formats.md:109>)와 [SKILL.md:146](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/SKILL.md:146>)입니다.
- 근거는 “라벨 안의 큰따옴표는 작은따옴표나 낫표로 바꾼다”입니다.
- 원문의 인용·코드·식별자를 라벨에 넣을 때 이 규칙을 적용하면, [SKILL.md:118](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/SKILL.md:118>)의 “공백과 부호까지 그대로 보존한다”를 위반합니다.
- 최소 수정안은 보호 문자열의 표시값을 유지하면서 Mermaid 엔티티로 따옴표를 이스케이프하도록 바꾸는 것입니다.

**[P2] 서로 다른 스킬 해시의 결과를 최종본 진단으로 합산합니다.**

- 위치는 [평가 README.md:5](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/evaluation/kp-v0111-output-formats-20261113/README.md:5>)입니다.
- 근거는 대상 해시를 `729dd2…423bc`로 명시했지만, [plan.json:2](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/evaluation/kp-v0111-output-formats-20261113/plan.json:2>)의 최초 44개 작업은 `6ef352…adc6a`를 사용했다는 기록입니다.
- 최종 해시가 기록된 [plan-sonnet-r34.json:2](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/evaluation/kp-v0111-output-formats-20261113/plan-sonnet-r34.json:2>)에는 Sonnet L3 추가 작업 4개만 있습니다. 따라서 `8/8`, `10/10`, 브라우저 `16/16` 전체를 최종 해시의 측정 결과로 읽게 하는 현재 표기는 부정확합니다.
- 최소 수정안은 보강 전·후 결과를 해시별로 구분하고, 당시 SKILL·참조·요청 원문을 함께 보존하는 것입니다.

**[P2] STE와 KP의 반복 횟수가 같은 것으로 표기됩니다.**

- 위치는 [README.md:51](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/README.md:51>)이며, 변경·검증 상태 문서에도 같은 문장이 있습니다.
- 근거는 “STE도 같은 모델·요청·반복으로 L3 8건과 L2 4건을 생성했다”입니다.
- 실제 파일은 STE L3가 모델별 2회인 8건이고, KP L3는 조건별 10건입니다. [probe_sonnet.py:40](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/evaluation/kp-v0111-output-formats-20261113/probe_sonnet.py:40>)는 KP에만 3·4회차를 추가합니다.
- 최소 수정안은 기본 실험의 모델별 2회와 KP 전용 추가 진단 2회를 구분하고, “같은 반복”의 적용 범위를 기본 실험으로 한정하는 것입니다.

**[P2] 별도 상태 알림이 있으면 결과 순서 위반을 놓칩니다.**

- 위치는 [check_html.py:254](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/scripts/check_html.py:254>)입니다.
- 근거는 첫 번째 `output` 또는 `aria-live` 속성이 있는 요소를 무조건 `first_result`로 선택하는 코드입니다.
- `<div aria-live="polite">저장 상태</div><input aria-label="입력"><output>결과</output>`를 검사하면 실제 결과가 입력 뒤에 있는데도 `no_findings`를 반환합니다. 앞선 요소가 `aria-live="off"`, 숨긴 `output`, `template` 안의 `output`인 경우도 같은 미탐을 재현했습니다.
- 최소 수정안은 실제 결과 영역을 식별하고, 비활성·숨김·템플릿 요소와 별도 상태 알림을 구분하는 회귀 사례를 추가하는 것입니다.

**[P2] HTML 변경 진단이 JavaScript 구문을 잘못 분류합니다.**

- 위치는 [check_html.py:324](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/scripts/check_html.py:324>)입니다.
- 근거는 문자열·주석을 지운 코드에 점 표기 정규식만 적용하는 방식입니다.
- `const pattern = /node.innerHTML = value/;`는 실행되는 대입이 아닌데 `innerhtml-assignment` 오류를 반환합니다. 반대로 `node["innerHTML"] = source;`와 템플릿 보간식 안의 `node.innerHTML = source`는 `no_findings`를 반환합니다.
- 최소 수정안은 정규식 리터럴·템플릿 보간식·정적 대괄호 속성을 구분하고, 세 사례를 회귀 테스트에 추가하는 것입니다.

**[P2] 어두운 테마 진단이 CSS 문자열을 선언으로 오인합니다.**

- 위치는 [check_html.py:308](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/scripts/check_html.py:308>)입니다.
- 근거는 주석만 제거한 CSS 전체에서 `color-scheme: … dark`를 검색하는 코드입니다.
- `p::before { content: "color-scheme: dark"; }`는 테마를 설정하지 않지만 `dark-default-theme` 오류를 반환합니다. 반대로 `<meta name="color-scheme" content="dark">`는 검사에서 누락됩니다.
- 최소 수정안은 CSS 문자열과 실제 선언을 구분하고, 메타 태그의 지원 여부를 명시한 회귀 테스트를 추가하는 것입니다.

**[P3] Mermaid 예제가 새 작성 규칙을 위반합니다.**

- 위치는 [output-formats.md:108](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/references/output-formats.md:108>)입니다.
- 근거는 “모든 라벨을 큰따옴표로 감싼다”와 같은 파일 [79행](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/references/output-formats.md:79>)의 `A -->|적합하다| B`입니다. 부적합 분기의 라벨도 따옴표가 없습니다.
- 최소 수정안은 예제의 두 화살표 라벨을 `|"적합하다"|`, `|"부적합하다"|`로 맞추는 것입니다.

**[P3] 새 스킬 문안이 자체 12어절 상한을 위반합니다.**

- 위치는 [SKILL.md:146](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/SKILL.md:146>)입니다.
- 근거는 “노드 ID는 영문 대문자와 숫자로 쓰고, 라벨은 `A["가동한다"]`처럼 큰따옴표로 감싸고, 라벨 안의 인용은 작은따옴표로 쓴다.”입니다.
- 이 문장은 공백 기준 15어절이며, [73행](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/SKILL.md:73>)의 “12어절을 넘으면 나누거나 목록으로 바꾼다”를 위반합니다. [interactive-html.md:96](</Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/references/interactive-html.md:96>)의 배치 예외 문장도 18어절입니다.
- 최소 수정안은 ID·라벨·인용 규칙을 각각 한 문장으로 나누고, 배치 예외 문장도 조건과 행동을 나누는 것입니다.

`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p test_skill_html_check.py`는 36개 테스트를 통과했습니다. 평가 폴더의 해시 141개와 원시 출력 해시는 모두 일치했습니다. 현재 `SKILL.md`의 SHA-256과 `o200k_base` 7,236토큰도 사실 자료와 일치했습니다.

파일은 수정하지 않았으며, `evaluation/README.md` 변경은 검토하지 않았습니다. 내장 브라우저가 `Browser is not available: iab`를 반환하여 예제의 실제 화면·키보드·낭독기 동작은 확인하지 못했습니다.


