```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약을 취소하면 처리 방식이 정해진다</title>
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
    html { font-family: var(--font-body); color: var(--text); background: var(--canvas); line-height: 1.7; }
    body { margin: 0; font-size: 1rem; }
    main { max-width: var(--page-width); margin-inline: auto; padding: var(--space-5) var(--space-4); }
    h1, h2, p { margin-block: 0 var(--space-3); }
    h1 { max-width: 28ch; font-size: clamp(1.75rem, 4vw, 2.5rem); line-height: 1.3; letter-spacing: -0.025em; }
    h2 { font-size: 1.25rem; line-height: 1.45; }
    p { max-width: var(--measure); }
    .lead { color: var(--muted); }
    .panel_layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); align-items: start; margin-block: var(--space-4); }
    .panel_layout > * { min-inline-size: 0; }
    .panel { border: 1px solid var(--line); background: var(--surface); padding: var(--space-4); border-radius: 0.75rem; }
    fieldset { border: 0; margin: 0 0 var(--space-4); padding: 0; min-inline-size: 0; }
    legend { font-weight: 650; padding: 0; margin-block-end: var(--space-1); }
    .choice { display: flex; align-items: center; gap: var(--space-2); margin-block-end: var(--space-1); }
    .choice input { width: 1.25rem; height: 1.25rem; margin: 0; }
    .choice label { font-weight: 400; }
    .hint { font-size: 0.9375rem; color: var(--muted); margin-block: var(--space-1) 0; }
    button { min-height: 2.75rem; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--accent); border-radius: 0.375rem; color: var(--accent); background: var(--surface); cursor: pointer; }
    button:hover { background: var(--accent-soft); }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output { display: block; font-size: clamp(1.4rem, 3.5vw, 2rem); line-height: 1.4; font-weight: 750; color: var(--accent); margin-block: var(--space-3); overflow-wrap: anywhere; }
    .notice { padding: var(--space-3); background: var(--warning-surface); color: var(--warning); border-left: 0.25rem solid var(--warning); }
    .details { margin-block-start: var(--space-4); }
    ol, ul { max-width: var(--measure); padding-inline-start: 1.5rem; margin-block: 0 var(--space-3); }
    dl { margin: 0; }
    dt { margin-block-start: var(--space-2); font-weight: 650; }
    dd { margin-inline-start: 0; max-width: var(--measure); }
    [hidden] { display: none; }
    @media (max-width: 42rem) {
      main { padding: var(--space-4) var(--space-3); }
      .panel { padding: var(--space-3); }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소 시점에 따라 처리 방식을 확인한다</h1>
      <p class="lead">예약 확정자의 취소 시점과 대기자 유무를 바꾸면 처리 결과가 바뀐다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">취소 처리 결과</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="outcome" for="timing waiters">시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</output>
          <p id="basis">조건: 이용 시간 24시간 전까지 취소하고 대기자가 있다.</p>
          <div id="conditions"></div>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="cancel-form">
          <fieldset>
            <legend>예약 확정자의 취소 시점</legend>
            <div class="choice">
              <input type="radio" id="timing-before" name="timing" value="before" checked>
              <label for="timing-before">이용 시간 24시간 전까지 취소</label>
            </div>
            <div class="choice">
              <input type="radio" id="timing-within" name="timing" value="within">
              <label for="timing-within">이용 24시간 이내에 취소</label>
            </div>
          </fieldset>
          <fieldset>
            <legend>대기자 상태</legend>
            <div class="choice">
              <input type="radio" id="waiters-yes" name="waiters" value="yes" checked>
              <label for="waiters-yes">대기자가 있음</label>
            </div>
            <div class="choice">
              <input type="radio" id="waiters-no" name="waiters" value="no">
              <label for="waiters-no">남은 대기자가 없음</label>
            </div>
            <p class="hint">이용 24시간 이내 취소에서는 대기자 상태가 처리 결과를 바꾸지 않는다.</p>
          </fieldset>
          <button type="button" id="reset-form">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">규칙</h2>
      <dl>
        <dt>이용 시간 24시간 전까지 취소</dt>
        <dd>시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</dd>
        <dt>안내를 받은 대기자</dt>
        <dd>안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</dd>
        <dt>4시간 이내에 응답하지 않을 때</dt>
        <dd>안내가 그다음 대기자에게 넘어간다.</dd>
        <dt>이용 24시간 이내 취소</dt>
        <dd>자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.</dd>
        <dt>남은 대기자가 없을 때</dt>
        <dd>해당 시간대가 일반 예약으로 다시 열린다.</dd>
      </dl>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <ul>
        <li>원문은 이용 24시간 이내 취소에서 대기자가 없을 때의 처리를 따로 밝히지 않는다.</li>
        <li>입력값을 저장하거나 전송하지 않는다.</li>
      </ul>
    </section>
  </main>
  <script>
    "use strict";
    const form = document.getElementById("cancel-form");
    const outcome = document.getElementById("outcome");
    const basis = document.getElementById("basis");
    const conditions = document.getElementById("conditions");

    function selected(name) {
      return form.querySelector('input[name="' + name + '"]:checked').value;
    }

    function addNotice(text) {
      const p = document.createElement("p");
      p.className = "notice";
      p.textContent = text;
      conditions.appendChild(p);
    }

    function update() {
      const timing = selected("timing");
      const waiters = selected("waiters");
      conditions.textContent = "";
      if (timing === "within") {
        outcome.textContent = "자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.";
        basis.textContent = "조건: 이용 24시간 이내에 취소했다.";
        return;
      }
      if (waiters === "yes") {
        outcome.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.";
        basis.textContent = "조건: 이용 시간 24시간 전까지 취소하고 대기자가 있다.";
        addNotice("안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.");
        addNotice("그 시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.");
      } else {
        outcome.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = "조건: 이용 시간 24시간 전까지 취소하고 남은 대기자가 없다.";
      }
    }

    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => { event.preventDefault(); update(); });
    document.getElementById("reset-form").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```