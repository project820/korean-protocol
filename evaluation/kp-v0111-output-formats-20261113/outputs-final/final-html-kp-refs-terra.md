```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>회의실 예약 취소에 따른 안내와 처리를 확인한다</title>
  <style>
    :root {
      color-scheme: light;
      --font-body: system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      --text: #17252d;
      --muted: #4a5d66;
      --surface: #fff;
      --canvas: #f3f6f6;
      --line: #b8c7cb;
      --accent: #075d60;
      --accent-soft: #e6f3ef;
      --focus: #005fcc;
      --space-1: .375rem;
      --space-2: .75rem;
      --space-3: 1rem;
      --space-4: 1.5rem;
      --space-5: 2.5rem;
      --page-width: 72rem;
    }
    * { box-sizing: border-box; }
    html {
      font-family: var(--font-body);
      color: var(--text);
      background: var(--canvas);
      line-height: 1.7;
    }
    body { margin: 0; }
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
    }
    h2 { font-size: 1.25rem; }
    .lead, .hint { color: var(--muted); }
    .panel_layout {
      display: grid;
      gap: var(--space-4);
      grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr));
      align-items: start;
    }
    .panel_layout > * { min-inline-size: 0; }
    .panel {
      border: 1px solid var(--line);
      background: var(--surface);
      padding: var(--space-4);
      border-radius: .75rem;
    }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output {
      display: block;
      font-size: 1.3rem;
      font-weight: 750;
      line-height: 1.5;
      color: var(--accent);
      margin-block: var(--space-3);
    }
    fieldset {
      border: 0;
      padding: 0;
      margin: 0 0 var(--space-4);
      min-inline-size: 0;
    }
    legend { font-weight: 700; margin-bottom: var(--space-2); }
    .choice { display: flex; align-items: baseline; gap: var(--space-2); margin-block: var(--space-1); }
    input { flex: 0 0 auto; }
    label { cursor: pointer; }
    .hint { font-size: .9375rem; margin-block: var(--space-1); }
    button {
      min-height: 2.75rem;
      padding: var(--space-2) var(--space-3);
      font: inherit;
      border: 1px solid var(--accent);
      border-radius: .375rem;
      color: var(--accent);
      background: var(--surface);
      cursor: pointer;
    }
    button:hover { background: var(--accent-soft); }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .details { margin-block-start: var(--space-4); }
    li { margin-block: var(--space-2); }
    [hidden] { display: none; }
    @media (max-width: 42rem) {
      main { padding: var(--space-4) var(--space-3); }
      .panel { padding: var(--space-3); }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소에 따른 안내와 처리를 확인한다</h1>
      <p class="lead">확정된 예약의 취소 시점과 대기자 상태에 따른 처리를 살펴본다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">처리 결과</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="result" for="cancel-before cancel-within wait-present wait-none response-waiting response-late">시스템이 대기자 명단의 다음 순번에게 안내를 보낸다.</output>
          <p id="basis">조건: 이용 시간 24시간 전까지 취소하고 남은 대기자가 있다.</p>
          <p id="condition">안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</p>
        </div>
      </section>

      <section class="panel" aria-labelledby="input-heading">
        <h2 id="input-heading">취소와 대기자 상태</h2>
        <form id="reservation-form">
          <fieldset>
            <legend>취소 시점</legend>
            <div class="choice">
              <input type="radio" id="cancel-before" name="cancel-time" value="before" checked>
              <label for="cancel-before">이용 시간 24시간 전까지</label>
            </div>
            <div class="choice">
              <input type="radio" id="cancel-within" name="cancel-time" value="within">
              <label for="cancel-within">이용 24시간 이내</label>
            </div>
          </fieldset>

          <fieldset>
            <legend>남은 대기자</legend>
            <div class="choice">
              <input type="radio" id="wait-present" name="waiters" value="present" checked>
              <label for="wait-present">있음</label>
            </div>
            <div class="choice">
              <input type="radio" id="wait-none" name="waiters" value="none">
              <label for="wait-none">없음</label>
            </div>
          </fieldset>

          <fieldset id="response-fieldset" aria-describedby="response-hint">
            <legend>안내받은 대기자의 응답 상태</legend>
            <div class="choice">
              <input type="radio" id="response-waiting" name="response" value="waiting" checked>
              <label for="response-waiting">안내 후 응답 기한 적용</label>
            </div>
            <div class="choice">
              <input type="radio" id="response-late" name="response" value="late">
              <label for="response-late">4시간 이내에 응답하지 않음</label>
            </div>
            <p class="hint" id="response-hint">이용 시간 24시간 전까지 취소하고 남은 대기자가 있을 때 선택한다.</p>
          </fieldset>

          <button type="button" id="reset-form">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">안내와 처리 기준</h2>
      <ul>
        <li>확정된 예약을 이용 시간 24시간 전까지 취소하면 시스템이 대기자 명단의 다음 순번에게 자동으로 안내한다.</li>
        <li>안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</li>
        <li>그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</li>
        <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.</li>
        <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
      </ul>
    </section>

    <noscript>
      <p>JavaScript가 꺼져 있어 선택에 따른 결과를 바꾸지 못한다. 위 결과는 초기 선택에 따른 안내다.</p>
    </noscript>
  </main>

  <script>
    "use strict";

    const form = document.getElementById("reservation-form");
    const result = document.getElementById("result");
    const basis = document.getElementById("basis");
    const condition = document.getElementById("condition");
    const responseFieldset = document.getElementById("response-fieldset");

    function update() {
      const cancelTime = form.elements["cancel-time"].value;
      const waiters = form.elements["waiters"].value;
      const response = form.elements["response"].value;

      responseFieldset.disabled = cancelTime !== "before" || waiters !== "present";

      if (cancelTime === "within") {
        result.textContent = "자동 안내가 가지 않으며 총무팀이 직접 판단해서 처리한다.";
        basis.textContent = "조건: 이용 24시간 이내에 취소했다.";
        condition.textContent = waiters === "none"
          ? "남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다."
          : "";
      } else if (waiters === "none") {
        result.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = "조건: 남은 대기자가 없다.";
        condition.textContent = "";
      } else if (response === "late") {
        result.textContent = "그다음 대기자에게 안내가 넘어간다.";
        basis.textContent = "조건: 안내받은 대기자가 4시간 이내에 응답하지 않았다.";
        condition.textContent = "남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.";
      } else {
        result.textContent = "시스템이 대기자 명단의 다음 순번에게 안내를 보낸다.";
        basis.textContent = "조건: 이용 시간 24시간 전까지 취소하고 남은 대기자가 있다.";
        condition.textContent = "안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.";
      }
      condition.hidden = condition.textContent === "";
    }

    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => event.preventDefault());
    document.getElementById("reset-form").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```