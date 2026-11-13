```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약 취소 조건에 따른 처리를 확인한다</title>
  <style>
    :root {
      color-scheme: light;
      --font-body: system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      --text: #17252d;
      --muted: #4a5d66;
      --surface: #ffffff;
      --canvas: #f3f6f6;
      --line: #b8c7cb;
      --accent: #075d60;
      --accent-soft: #e6f3ef;
      --warning: #714a00;
      --warning-surface: #fff4d6;
      --error: #a32020;
      --focus: #005fcc;
      --space-1: 0.375rem;
      --space-2: 0.75rem;
      --space-3: 1rem;
      --space-4: 1.5rem;
      --space-5: 2.5rem;
      --measure: 64ch;
      --page-width: 72rem;
    }
    * { box-sizing: border-box; }
    html {
      font-family: var(--font-body);
      color: var(--text);
      background: var(--canvas);
      line-height: 1.7;
    }
    body { margin: 0; font-size: 1rem; }
    main {
      max-width: var(--page-width);
      margin-inline: auto;
      padding: var(--space-5) var(--space-4);
    }
    h1, h2, p { margin-block: 0 var(--space-3); }
    h1 {
      max-width: 26ch;
      font-size: clamp(1.75rem, 4vw, 2.5rem);
      line-height: 1.3;
      letter-spacing: -0.025em;
    }
    h2 { font-size: 1.25rem; line-height: 1.45; }
    p, li, dd { max-width: var(--measure); }
    .lead, .hint { color: var(--muted); }
    .hint { font-size: 0.9375rem; }
    .panel_layout {
      display: grid;
      gap: var(--space-4);
      grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr));
      align-items: start;
      margin-block: var(--space-4);
    }
    .panel_layout > * { min-inline-size: 0; }
    .panel {
      border: 1px solid var(--line);
      background: var(--surface);
      padding: var(--space-4);
      border-radius: 0.75rem;
      overflow-wrap: anywhere;
    }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output {
      display: block;
      margin-block: var(--space-3);
      font-size: clamp(1.25rem, 3vw, 1.65rem);
      line-height: 1.5;
      font-weight: 750;
      color: var(--accent);
    }
    fieldset {
      min-inline-size: 0;
      margin: 0 0 var(--space-4);
      padding: 0;
      border: 0;
    }
    legend {
      padding: 0;
      margin-block-end: var(--space-2);
      font-weight: 650;
    }
    .choice {
      display: flex;
      align-items: flex-start;
      gap: var(--space-2);
      margin-block-end: var(--space-2);
    }
    input[type="radio"] {
      flex: 0 0 auto;
      width: 1.25rem;
      height: 1.25rem;
      margin: 0.25rem 0 0;
      accent-color: var(--accent);
    }
    label { cursor: pointer; }
    button {
      min-height: 2.75rem;
      padding: var(--space-2) var(--space-3);
      font: inherit;
      border: 1px solid var(--accent);
      border-radius: 0.375rem;
      color: var(--accent);
      background: var(--surface);
      cursor: pointer;
    }
    button:hover { background: var(--accent-soft); }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .notice {
      padding: var(--space-3);
      background: var(--warning-surface);
      color: var(--warning);
      border-left: 0.25rem solid var(--warning);
    }
    .details { margin-block-start: var(--space-4); }
    dl { margin: 0; }
    dt { margin-block-start: var(--space-3); font-weight: 650; }
    dt:first-child { margin-block-start: 0; }
    dd { margin-inline-start: 0; }
    [hidden] { display: none; }
    @media (max-width: 42rem) {
      main { padding: var(--space-4) var(--space-3); }
      .panel { padding: var(--space-3); }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소 조건에 따른 처리를 확인한다</h1>
      <p class="lead">확정된 예약의 취소 시점과 남은 대기자 유무에 따른 처리를 확인한다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">취소 후 처리</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="result" for="cancel-early cancel-late waiting-yes waiting-no">시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</output>
          <p class="hint" id="basis">선택 조건: 이용 시간 24시간 전까지 취소하며, 남은 대기자가 있다.</p>
          <div id="response-conditions">
            <p><strong>안내를 받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</strong></p>
            <p>그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</p>
          </div>
          <div class="notice" id="manual-conditions" hidden>
            <p>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다.</p>
            <p>총무팀이 직접 판단해서 처리한다.</p>
          </div>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="conditions-form">
          <fieldset aria-describedby="timing-hint">
            <legend>취소 시점</legend>
            <div class="choice">
              <input id="cancel-early" name="cancel-timing" type="radio" value="early" checked>
              <label for="cancel-early">이용 시간 24시간 전까지 취소</label>
            </div>
            <div class="choice">
              <input id="cancel-late" name="cancel-timing" type="radio" value="late">
              <label for="cancel-late">이용 24시간 이내에 취소</label>
            </div>
            <p class="hint" id="timing-hint">원문의 시간 구분을 그대로 선택지로 사용한다.</p>
          </fieldset>

          <fieldset>
            <legend>남은 대기자</legend>
            <div class="choice">
              <input id="waiting-yes" name="waiting-status" type="radio" value="yes" checked>
              <label for="waiting-yes">남은 대기자가 있다</label>
            </div>
            <div class="choice">
              <input id="waiting-no" name="waiting-status" type="radio" value="no">
              <label for="waiting-no">남은 대기자가 없다</label>
            </div>
          </fieldset>

          <button type="button" id="restore-conditions">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">처리 규칙</h2>
      <dl>
        <dt>이용 시간 24시간 전까지 취소</dt>
        <dd>시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</dd>

        <dt>안내를 받은 대기자의 응답</dt>
        <dd>안내를 받은 시점부터 4시간 이내에 응답해야 한다.</dd>
        <dd>그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</dd>

        <dt>이용 24시간 이내에 취소</dt>
        <dd>자동 안내가 가지 않는다.</dd>
        <dd>총무팀이 직접 판단해서 처리한다.</dd>

        <dt>남은 대기자가 없는 경우</dt>
        <dd>해당 시간대가 일반 예약으로 다시 열린다.</dd>
      </dl>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <dl>
        <dt>출처와 초기 선택</dt>
        <dd>제공된 회의실 예약 취소 안내 원문을 기준으로 작성했다.</dd>
        <dd>초기 화면은 원문에 먼저 나온 자동 안내 조건을 표시한다.</dd>

        <dt>24시간 경계</dt>
        <dd>원문은 ‘24시간 전까지’와 ‘24시간 이내’를 함께 사용한다.</dd>
        <dd>제공된 원문만으로는 정확히 24시간 전의 적용 구분을 확정할 수 없다.</dd>

        <dt>화면의 기능</dt>
        <dd>선택 조건에 따른 안내만 표시한다.</dd>
        <dd>실제 예약 취소나 대기자 안내를 실행하지 않는다.</dd>

        <dt>저장·전송 여부</dt>
        <dd>선택값을 저장하거나 외부로 전송하지 않는다.</dd>
        <dd>초기화하면 처음 선택한 조건으로 돌아간다.</dd>
      </dl>
    </section>

    <noscript>
      <p class="notice">JavaScript가 꺼져 있어 선택 변경을 반영하지 못한다. 처리 규칙에서 조건별 내용을 확인한다.</p>
    </noscript>
  </main>

  <script>
    "use strict";

    const form = document.getElementById("conditions-form");
    const result = document.getElementById("result");
    const basis = document.getElementById("basis");
    const responseConditions = document.getElementById("response-conditions");
    const manualConditions = document.getElementById("manual-conditions");

    function update() {
      const late = document.getElementById("cancel-late").checked;
      const hasWaiting = document.getElementById("waiting-yes").checked;

      const timingText = late
        ? "이용 24시간 이내에 취소하며"
        : "이용 시간 24시간 전까지 취소하며";
      const waitingText = hasWaiting
        ? "남은 대기자가 있다."
        : "남은 대기자가 없다.";

      basis.textContent = "선택 조건: " + timingText + ", " + waitingText;
      responseConditions.hidden = late || !hasWaiting;
      manualConditions.hidden = !late;

      if (!hasWaiting) {
        result.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
      } else if (late) {
        result.textContent = "총무팀이 직접 판단해서 처리한다.";
        manualConditions.hidden = true;
        responseConditions.hidden = true;
      } else {
        result.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.";
      }

      if (late && hasWaiting) {
        manualConditions.hidden = false;
        manualConditions.lastElementChild.hidden = true;
      } else {
        manualConditions.lastElementChild.hidden = false;
      }
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => event.preventDefault());

    document.getElementById("restore-conditions").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });

    update();
  </script>
</body>
</html>
```