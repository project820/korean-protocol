```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>회의실 예약 취소에 따른 처리 방식을 확인한다</title>
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
      max-width: 28ch;
      font-size: clamp(1.75rem, 4vw, 2.5rem);
      line-height: 1.3;
      letter-spacing: -0.025em;
    }
    h2 { font-size: 1.25rem; line-height: 1.45; }
    p { max-width: var(--measure); }
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
      border-radius: 0.75rem;
    }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    .details { margin-block-start: var(--space-4); }
    fieldset {
      min-width: 0;
      border: 0;
      padding: 0;
      margin: 0 0 var(--space-4);
    }
    legend { font-weight: 700; margin-block-end: var(--space-2); }
    .choice {
      display: flex;
      align-items: baseline;
      gap: var(--space-2);
      margin-block: var(--space-2);
    }
    input { flex: none; accent-color: var(--accent); }
    label { cursor: pointer; }
    fieldset:disabled label { color: var(--muted); cursor: default; }
    .hint { font-size: 0.9375rem; margin-block: var(--space-1) 0; }
    output {
      display: block;
      margin-block: var(--space-3);
      color: var(--accent);
      font-size: clamp(1.25rem, 3vw, 1.65rem);
      line-height: 1.4;
      font-weight: 750;
    }
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
    ul { padding-inline-start: 1.4rem; }
    li + li { margin-block-start: var(--space-2); }
    @media (max-width: 42rem) {
      main { padding: var(--space-4) var(--space-3); }
      .panel { padding: var(--space-3); }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소에 따른 처리 방식을 확인한다</h1>
      <p class="lead">확정된 예약의 취소 시점과 대기 상황에 따른 안내·처리 방식을 살펴본다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">처리 방식</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="result" for="early late waiting no-waiting pending responded no-response">시스템이 대기자 명단의 다음 순번에게 자동으로 안내한다.</output>
          <p id="basis">취소 시점: 이용 시간 24시간 전까지. 남은 대기자가 있다.</p>
          <p id="condition">안내를 받은 대기자는 안내를 받은 시점부터 4시간 이내에 응답해야 한다.</p>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소와 대기 상황</h2>
        <form id="reservation-form">
          <fieldset>
            <legend>취소 시점</legend>
            <div class="choice">
              <input type="radio" id="early" name="timing" value="early" checked>
              <label for="early">이용 시간 24시간 전까지</label>
            </div>
            <div class="choice">
              <input type="radio" id="late" name="timing" value="late">
              <label for="late">이용 24시간 이내</label>
            </div>
            <p class="hint">취소 시점 범주는 원문 표현을 따른다.</p>
          </fieldset>

          <fieldset>
            <legend>남은 대기자</legend>
            <div class="choice">
              <input type="radio" id="waiting" name="queue" value="waiting" checked>
              <label for="waiting">있음</label>
            </div>
            <div class="choice">
              <input type="radio" id="no-waiting" name="queue" value="none">
              <label for="no-waiting">없음</label>
            </div>
          </fieldset>

          <fieldset id="response-group" aria-describedby="response-hint">
            <legend>안내를 받은 대기자의 응답</legend>
            <div class="choice">
              <input type="radio" id="pending" name="response" value="pending" checked>
              <label for="pending">응답 여부를 정하지 않음</label>
            </div>
            <div class="choice">
              <input type="radio" id="responded" name="response" value="responded">
              <label for="responded">4시간 이내에 응답함</label>
            </div>
            <div class="choice">
              <input type="radio" id="no-response" name="response" value="no-response">
              <label for="no-response">4시간 이내에 응답하지 않음</label>
            </div>
            <p class="hint" id="response-hint">이용 시간 24시간 전까지 취소하고 남은 대기자가 있을 때 적용한다.</p>
          </fieldset>

          <button type="button" id="reset-form">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">처리 규칙</h2>
      <ul>
        <li>확정된 예약을 이용 시간 24시간 전까지 취소하면 시스템이 대기자 명단의 다음 순번에게 자동으로 안내한다.</li>
        <li>안내를 받은 대기자는 안내를 받은 시점부터 4시간 이내에 응답해야 한다.</li>
        <li>그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</li>
        <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다. 총무팀이 직접 판단해 처리한다.</li>
        <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
      </ul>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <p>출처: 제공된 회의실 예약 취소 안내 원문.</p>
      <p>원문의 취소 시점 범주에는 정확히 이용 24시간 전인 경우가 겹친다. 이 화면은 어느 규칙이 우선하는지 정하지 않는다.</p>
      <p>선택한 내용은 저장하거나 전송하지 않는다.</p>
    </section>

    <noscript>
      <p>JavaScript가 꺼져 있어 선택에 따른 결과가 바뀌지 않는다. 처리 규칙은 위에서 확인할 수 있다.</p>
    </noscript>
  </main>

  <script>
    "use strict";

    const form = document.getElementById("reservation-form");
    const responseGroup = document.getElementById("response-group");
    const result = document.getElementById("result");
    const basis = document.getElementById("basis");
    const condition = document.getElementById("condition");

    function update() {
      const timing = form.elements.timing.value;
      const queue = form.elements.queue.value;
      const response = form.elements.response.value;
      const isEarly = timing === "early";
      const hasWaiting = queue === "waiting";

      responseGroup.disabled = !(isEarly && hasWaiting);

      if (!isEarly) {
        result.textContent = "자동 안내가 가지 않으며 총무팀이 직접 판단해 처리한다.";
        basis.textContent = "취소 시점: 이용 24시간 이내.";
        condition.textContent = hasWaiting
          ? "남은 대기자가 있다."
          : "남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.";
        return;
      }

      if (!hasWaiting) {
        result.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = "남은 대기자가 없다.";
        condition.textContent = "취소 시점: 이용 시간 24시간 전까지.";
        return;
      }

      basis.textContent = "취소 시점: 이용 시간 24시간 전까지. 남은 대기자가 있다.";

      if (response === "no-response") {
        result.textContent = "그다음 대기자에게 안내가 넘어간다.";
        condition.textContent = "안내를 받은 대기자가 안내 시점부터 4시간 이내에 응답하지 않은 경우다.";
      } else if (response === "responded") {
        result.textContent = "안내를 받은 대기자가 4시간 이내에 응답했다.";
        condition.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내한 경우다.";
      } else {
        result.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내한다.";
        condition.textContent = "안내를 받은 대기자는 안내를 받은 시점부터 4시간 이내에 응답해야 한다.";
      }
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