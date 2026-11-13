```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약 취소 시점에 따라 대기자 안내 방식을 가른다</title>
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
    html { font-family: var(--font-body); color: var(--text); background: var(--canvas); line-height: 1.7; }
    body { margin: 0; font-size: 1rem; }
    main { max-width: var(--page-width); margin-inline: auto; padding: var(--space-5) var(--space-4); }
    h1, h2, p { margin-block: 0 var(--space-3); }
    h1 { max-width: 18em; font-size: clamp(1.75rem, 4vw, 2.5rem); line-height: 1.3; letter-spacing: -0.025em; }
    h2 { font-size: 1.25rem; line-height: 1.45; }
    p { max-width: var(--measure); }
    .lead { color: var(--muted); }
    .panel_layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); align-items: start; margin-block: var(--space-4); }
    .panel_layout > * { min-inline-size: 0; }
    .panel { border: 1px solid var(--line); background: var(--surface); padding: var(--space-4); border-radius: 0.75rem; }
    fieldset { margin: 0 0 var(--space-4); padding: 0; border: 0; min-inline-size: 0; }
    legend { font-weight: 650; margin-block-end: var(--space-2); padding: 0; }
    .choice { display: flex; gap: 0.5rem; align-items: flex-start; margin-block-end: var(--space-2); font-weight: 400; }
    .choice input { width: 1.25rem; height: 1.25rem; margin-block-start: 0.25rem; flex: 0 0 auto; accent-color: var(--accent); }
    .hint { font-size: 0.9375rem; color: var(--muted); margin-block: var(--space-1) 0; }
    button { min-height: 2.75rem; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--accent); border-radius: 0.375rem; color: var(--accent); background: var(--surface); cursor: pointer; }
    button:hover { background: var(--accent-soft); }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output { display: block; font-size: clamp(1.5rem, 3vw, 2rem); line-height: 1.45; font-weight: 750; color: var(--accent); margin-block: var(--space-3); overflow-wrap: anywhere; }
    .formula { font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
    .notice { padding: var(--space-3); background: var(--warning-surface); color: var(--warning); border-left: 0.25rem solid var(--warning); }
    .details { margin-block-start: var(--space-4); }
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
      <h1>회의실 예약 취소 시점에 따라 대기자 안내 방식을 가른다</h1>
      <p class="lead">확정된 회의실 예약의 취소 시점과 대기자 상태를 바꾸면 안내 결과가 바뀐다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">안내 결과</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="result" for="timing-before timing-within wait-yes wait-no no-response" role="none">시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</output>
          <p class="formula" id="basis">예약이 확정된 사람이 이용 시간 24시간 전까지 취소하고 다음 순번 대기자가 있다.</p>
          <p class="notice" id="condition">안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</p>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="selector" novalidate>
          <fieldset>
            <legend>취소 시점</legend>
            <label class="choice" for="timing-before">
              <input id="timing-before" name="timing" type="radio" value="before" checked>
              <span>이용 시간 24시간 전까지</span>
            </label>
            <label class="choice" for="timing-within">
              <input id="timing-within" name="timing" type="radio" value="within">
              <span>이용 24시간 이내</span>
            </label>
          </fieldset>

          <fieldset>
            <legend>남은 대기자</legend>
            <label class="choice" for="wait-yes">
              <input id="wait-yes" name="waiters" type="radio" value="yes" checked>
              <span>대기자 명단의 다음 순번이 있다</span>
            </label>
            <label class="choice" for="wait-no">
              <input id="wait-no" name="waiters" type="radio" value="none">
              <span>남은 대기자가 없다</span>
            </label>
          </fieldset>

          <fieldset>
            <legend>응답</legend>
            <label class="choice" for="no-response">
              <input id="no-response" name="no_response" type="checkbox" aria-describedby="no-response-hint">
              <span>안내를 받은 대기자가 4시간 이내에 응답하지 않는다</span>
            </label>
            <p class="hint" id="no-response-hint">안내를 받은 시점으로부터 4시간 이내를 기준으로 한다.</p>
          </fieldset>

          <button type="button" id="reset-selector">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="basis-heading">
      <h2 id="basis-heading">적용 규칙</h2>
      <p>대상은 확정된 회의실 예약의 취소다.</p>
      <dl>
        <dt>이용 시간 24시간 전까지 취소</dt>
        <dd>예약이 확정된 사람이 취소하면 시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</dd>
        <dt>응답 기한</dt>
        <dd>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</dd>
        <dt>기한 내 미응답</dt>
        <dd>4시간 이내에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.</dd>
        <dt>이용 24시간 이내 취소</dt>
        <dd>자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.</dd>
        <dt>남은 대기자 없음</dt>
        <dd>해당 시간대가 일반 예약으로 다시 열린다.</dd>
      </dl>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <dl>
        <dt>출처</dt>
        <dd>회의실 예약 취소의 안내 방식에 대한 발언이다.</dd>
        <dt>원문이 밝히지 않은 조치</dt>
        <dd>4시간 이내에 응답한 뒤의 조치는 원문에 없다.</dd>
        <dt>저장·전송 여부</dt>
        <dd>입력값을 서버에 전송하거나 저장하지 않는다. 초기화하면 처음 선택한 조건으로 돌아간다.</dd>
      </dl>
    </section>
    <noscript><p class="notice">JavaScript가 꺼져 있어 입력 변경을 반영하지 못한다. 위 결과는 처음 선택한 조건의 결과다.</p></noscript>
  </main>
  <script>
    "use strict";
    const form = document.getElementById("selector");
    const noResponse = document.getElementById("no-response");
    const noResponseHint = document.getElementById("no-response-hint");
    const result = document.getElementById("result");
    const basis = document.getElementById("basis");
    const condition = document.getElementById("condition");

    function selected(name) {
      return form.querySelector('input[name="' + name + '"]:checked').value;
    }

    function showCondition(text) {
      condition.textContent = text;
      condition.hidden = text.length === 0;
    }

    function update() {
      const within = selected("timing") === "within";
      const none = selected("waiters") === "none";
      noResponse.disabled = within || none;
      if (within) {
        noResponseHint.textContent = "이용 24시간 이내 취소에는 자동 안내가 가지 않아 이 조건을 적용하지 않는다.";
      } else if (none) {
        noResponseHint.textContent = "남은 대기자가 없으면 이 조건을 적용하지 않는다.";
      } else {
        noResponseHint.textContent = "안내를 받은 시점으로부터 4시간 이내를 기준으로 한다.";
      }

      if (within && none) {
        result.textContent = "총무팀이 직접 판단해서 처리한다. 해당 시간대는 일반 예약으로 다시 열린다.";
        basis.textContent = "이용 24시간 이내에 취소한다. 남은 대기자가 없다.";
        showCondition("자동 안내가 가지 않는다.");
      } else if (within) {
        result.textContent = "총무팀이 직접 판단해서 처리한다.";
        basis.textContent = "이용 24시간 이내에 취소한다.";
        showCondition("자동 안내가 가지 않는다.");
      } else if (none) {
        result.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = "남은 대기자가 없다.";
        showCondition("");
      } else if (noResponse.checked) {
        result.textContent = "안내가 그다음 대기자에게 넘어간다.";
        basis.textContent = "이용 시간 24시간 전까지 취소한 뒤 안내를 받은 대기자가 4시간 이내에 응답하지 않는다.";
        showCondition("");
      } else {
        result.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.";
        basis.textContent = "예약이 확정된 사람이 이용 시간 24시간 전까지 취소하고 다음 순번 대기자가 있다.";
        showCondition("안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.");
      }
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      update();
    });
    document.getElementById("reset-selector").addEventListener("click", function () {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```