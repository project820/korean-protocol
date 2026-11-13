# KP v0.11.1 개선 근거 (2026-11-13)

## 1. 문제와 프로브 결과
- 사용자 지적: SKILL.md에 L1~L4 정의·가이드가 사실상 보이지 않는다. 다른 세션 에이전트가 L2를 이해하지 못했다. HTML이 마구잡이로 나올 우려.
- 현행 v0.11.0 SKILL.md(24,904바이트, o200k 6,453토큰)에서 L1~L4는 10행 1줄과 4A절 133~135행 3줄뿐이다. "Mermaid", "ASCII", "index.html", "check_html"은 본문에 0회다. L2 참조는 "필요한 부분만 읽는다"로 선택이다. frontmatter description에 L1~L4가 없다.
- 실제 규칙은 references/output-formats.md(12.7KB), interactive-html.md(9.8KB), video-script.md(5.3KB), assets/interactive-explainer.html(9.7KB), scripts/check_html.py에 있다.
- 프로브 A(SKILL.md만 제공, 4모델 Sol/Terra/Sonnet 5.5/Grok 4.7, medium): 4/4가 L2를 "표·도식"으로 답했다. Mermaid·ASCII를 말한 모델 0. L3 규칙은 SKILL.md의 일반 원칙만 나왔고, 참조 전용 규칙(innerHTML 금지, reset 이름 충돌, 첫 화면 결과, check_html.py)을 말한 모델 0. Sonnet만 "참조를 읽지 않았다"고 밝혔다.
- 프로브 B(같은 원문, L3 HTML, SKILL.md만 vs 참조 포함, 1회씩):
  - Sonnet SKILL.md만: 버튼을 눌러야 결과가 나옴, 원문에 없는 "남은 시간(시간)" 입력 가정, innerHTML 4회, check_html form-member-shadow. 참조 포함: 결과 패널 먼저, aria-target-missing 1건.
  - Sol: SKILL.md만은 명사구 제목·1열 라디오, 참조 포함은 '한다' 제목·2열 select.
  - Grok: SKILL.md만은 다크 테마·표 먼저. 참조 포함은 8분 넘게 미응답(미완료).
  - 참조 포함에서도 입력 컨트롤(라디오/select)과 열 배치가 모델마다 달랐다. 화면 골격이 고정돼 있지 않다.
- 원본: output/kp-level-probe-20261113/ (qa-*.md, html-*.html, html-*.png, pair-*.png)

## 2. StyleGallery 근거 (repo HEAD 0bf928f6, material manifest a30cfabe…)
- panel-layout (sg:pattern/path-sha256-9c016fee…): main/utility 패널을 grid auto-fit minmax(min(22rem,100%),1fr)로 리플로한다. DOM 순서·읽기 순서·포커스 순서를 시각 배치와 독립시키지 말 것. 재사용 레이아웃 CSS에 색·그림자·타이포 규칙을 섞지 말 것. 내부 스크롤 컨테이너 없음.
- Form Flow 레시피: 한 열 주 흐름, 라벨·설명·입력·힌트·오류를 DOM에서 인접하게 둔다. fieldset/legend로 묶는다. 상태를 색에만 의존하지 않는다. 문서 스크롤 우선.
- Dashboard 레시피: 패널은 시각 대칭이 아니라 판단 우선순위대로 둔다. 필터·컨트롤은 제어하는 영역 앞에 둔다. 반복 카드는 제목·목록·표 의미를 먼저 준다.
- Typography Roles: 보편 크기 매핑을 만들지 말고 의미 역할(제목·본문·보조)을 유지한다. 기본·확대 글자, 긴 라벨, 폰트 대체를 실제 렌더링으로 확인한다.
- Accessible Motion: 동작 선호·자동 갱신·깜빡임·의미 피드백을 구분한다. 동작 없이도 같은 정보를 준다(reduced-motion).
- 원문 사본: output/kp-v0111-research/sg-*.md

## 3. Mobbin 근거 (web, deep 검색 2회, 12화면 중 관찰)
- Kit "Paid recommendations calculator": 제목 + 한 줄 설명 → 왼쪽 라벨·도움말 있는 입력(초기값 500 채움), 오른쪽 결과 패널(큰 수치, "How do we calculate this?"), 결과 바로 아래 가정·한계 고지. https://mobbin.com/screens/9751f948-1422-48b2-bb69-3b7e783c3f43
- Amplitude 플랜 설정: 왼쪽 큰 값+슬라이더, 오른쪽 Summary(항목별 금액, 소계, 세금, 합계)와 주 행동. https://mobbin.com/screens/ddb6e909-526f-418f-b998-21e2a3dd97f8
- Quicken Retirement Planner: 왼쪽 소제목별 입력 묶음과 Reset, 오른쪽 차트에 기준선 라벨(Retirement Year, Life Expectancy), 차트 아래 한계 고지. https://mobbin.com/screens/83885d0d-82e5-45f1-94b4-17cd3148065e
- v0 credits: 슬라이더마다 값 칸과 소계(= $160), 위에 큰 합계, 아래 조건 문장. https://mobbin.com/screens/36e32f9e-d4c0-48ac-bf01-047e82a2810a
- Leonardo API 가격 계산기: 1·2·3 번호 열로 단계 진행, 마지막 열에 Reset과 합계. https://mobbin.com/screens/2083f41e-c037-41ad-986c-1c11d813c67b
- 반례 Hers TDEE: 입력이 비어 있고 결과가 "— — —"로 비어 있다가 Calculate를 눌러야 나온다. https://mobbin.com/screens/464e2064-0912-49f6-92ac-26580c6bea49
- 관찰 범위: 각 화면 한 장. 사용성 성과는 증명하지 않는다.

## 4. 잠정 융합 결정 (Fable 검토 대상)
- L3 화면 골격을 하나로 고정: 제목('한다' 문장) → 대상·범위 한 줄 → [결과 패널 | 입력 패널] 두 패널(panel-layout 리플로) → 규칙·산출식 → 참고(가정·출처).
- 결과 패널을 DOM과 화면에서 먼저 둔다(KP의 답 우선 원칙, Dashboard의 판단 우선순위). Mobbin 사례 다수는 입력이 왼쪽이다. 이 차이는 KP 원칙을 우선한 적응이다.
- 초기값을 원자료 값으로 채워 첫 화면에 결과를 보인다(Kit 관찰, Hers 반례).
- 가정·한계 고지는 결과 바로 아래(Kit, Quicken).
- 입력은 fieldset/legend로 묶고 라벨·힌트·오류를 인접 배치(Form Flow).
- 컨트롤 어휘: 선택지 2~4개는 라디오, 5개 이상 select, 연속 수치는 숫자 입력(+ 범위가 근거 있으면 슬라이더).

