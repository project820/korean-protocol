```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약 취소 조건에 따라 대기자 안내 처리를 가른다</title>
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
    p, li { max-width: var(--measure); }
    .lead { color: var(--muted); }
    .panel_layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); align-items: start; margin-block: var(--space-4); }
    .panel_layout > * { min-inline-size: 0; }
    .panel { border: 1px solid var(--line); background: var(--surface); padding: var(--space-4); border-radius: 0.75rem; }
    fieldset { border: 0; padding: 0; margin: 0 0 var(--space-4); min-inline-size: 0; }
    legend { font-weight: 650; padding: 0; margin-block-end: var(--space-2); }
    .choice { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); margin-block-end: var(--space-2); }
    .choice label { font-weight: 400; margin: 0; }
    .choice:has(input:disabled) label { color: var(--muted); }
    input { display: block; padding: var(--space-2); border: 1px solid var(--muted); border-radius: 0.375rem; font: inherit; color: var(--text); background: var(--surface); }
    input[type="radio"] { width: 1.25rem; height: 1.25rem; padding: 0; accent-color: var(--accent); }
    input[aria-invalid="true"] { outline: 2px solid var(--error); }
    .hint { font-size: 0.9375rem; color: var(--muted); margin-block: var(--space-1) 0; }
    .error { color: var(--error); margin-block: var(--space-1) 0; font-weight: 600; }
    button { min-height: 2.75rem; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--accent); border-radius: 0.375rem; color: var(--accent); background: var(--surface); cursor: pointer; }
    button:hover { background: var(--accent-soft); }
    button:disabled { cursor: not-allowed; }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output { display: block; font-size: 1.125rem; line-height: 1.6; font-weight: 650; color: var(--text); margin-block: var(--space-2); overflow-wrap: anywhere; }
    output ol { margin: 0; padding-inline-start: 1.25rem; }
    output li + li { margin-block-start: var(--space-2); }
    .formula { overflow-wrap: anywhere; }
    ul { margin-block: 0; padding-inline-start: 1.25rem; }
    li + li { margin-block-start: var(--space-2); }
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
      <h1>회의실 예약 취소 조건에 따라 대기자 안내 처리를 가른다</h1>
      <p class="lead">예약이 확정된 사람의 취소 조건을 바꾸면 안내 처리를 다시 보여 준다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">안내 처리</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="outcome" for="timing-before timing-within waiter-next waiter-none response-in response-out" role="none">
            <ol>
              <li>시스템이 대기자 명단의 다음 순번에게 안내를 자동으로 보낸다.</li>
              <li>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답한다.</li>
            </ol>
          </output>
          <p class="formula" id="basis">취소 시점은 이용 시간 24시간 전까지다. 다음 순번 대기자가 있다. 그 대기자는 4시간 이내에 응답한다.</p>
          <p id="condition">응답 기한은 안내를 받은 시점으로부터 4시간이다.</p>
          <p class="error" id="result-error" hidden>입력 오류가 있어 결과 계산을 보류한다. 표시한 입력 조건을 확인해야 한다.</p>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="cancellation" novalidate>
          <fieldset aria-describedby="timing-hint timing-error">
            <legend>취소 시점</legend>
            <div class="choice">
              <label for="timing-before">이용 시간 24시간 전까지</label>
              <input id="timing-before" name="timing" type="radio" value="before" checked>
            </div>
            <div class="choice">
              <label for="timing-within">이용 24시간 이내</label>
              <input id="timing-within" name="timing" type="radio" value="within">
            </div>
            <p class="hint" id="timing-hint">기준은 이용 시간이다.</p>
            <p class="error" id="timing-error" hidden>취소 시점을 골라야 한다.</p>
          </fieldset>

          <fieldset aria-describedby="waiter-hint waiter-error">
            <legend>대기자</legend>
            <div class="choice">
              <label for="waiter-next">다음 순번 대기자가 있다</label>
              <input id="waiter-next" name="waiter" type="radio" value="next" checked>
            </div>
            <div class="choice">
              <label for="waiter-none">남은 대기자가 없다</label>
              <input id="waiter-none" name="waiter" type="radio" value="none">
            </div>
            <p class="hint" id="waiter-hint">남은 대기자가 없으면 해당 시간대는 일반 예약으로 다시 열린다.</p>
            <p class="error" id="waiter-error" hidden>대기자 조건을 골라야 한다.</p>
          </fieldset>

          <fieldset id="response-set" aria-describedby="response-hint response-error">
            <legend>안내를 받은 대기자의 응답</legend>
            <div class="choice">
              <label for="response-in">4시간 이내에 응답한다</label>
              <input id="response-in" name="response" type="radio" value="in" checked>
            </div>
            <div class="choice">
              <label for="response-out">4시간 이내에 응답하지 않는다</label>
              <input id="response-out" name="response" type="radio" value="out">
            </div>
            <p class="hint" id="response-hint">기한은 안내를 받은 시점으로부터 4시간이다.</p>
            <p class="error" id="response-error" hidden>응답 여부를 골라야 한다.</p>
          </fieldset>

          <button type="button" id="reset-cancellation">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="basis-heading">
      <h2 id="basis-heading">적용 규칙</h2>
      <ul>
        <li>예약이 확정된 사람이 이용 시간 24시간 전까지 취소한다. 이때 시스템이 대기자 명단의 다음 순번에게 안내를 자동으로 보낸다.</li>
        <li>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</li>
        <li>그 시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.</li>
        <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다.</li>
        <li>이용 24시간 이내에 취소하면 총무팀이 직접 판단해서 처리한다.</li>
        <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
      </ul>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <dl>
        <dt>출처</dt>
        <dd>제공된 회의실 예약 취소 안내 원문이다.</dd>
        <dt>반영 범위</dt>
        <dd>화면은 원문에 적힌 안내 조건의 결과만 보여 준다.</dd>
        <dt>저장·전송</dt>
        <dd>입력값을 서버에 전송하거나 저장하지 않는다. 초기화하면 처음 선택한 조건으로 돌아간다.</dd>
      </dl>
    </section>
    <noscript><p>JavaScript가 꺼져 있어 조건 변경을 반영하지 못한다. 위 결과는 처음 선택한 조건의 결과다.</p></noscript>
  </main>
  <script>
    "use strict";
    const form = document.getElementById("cancellation");
    const outcome = document.getElementById("outcome");
    const basis = document.getElementById("basis");
    const condition = document.getElementById("condition");
    const resultError = document.getElementById("result-error");
    const responseHint = document.getElementById("response-hint");
    const responseInputs = Array.from(document.querySelectorAll('input[name="response"]'));

    function selected(name) {
      return document.querySelector('input[name="' + name + '"]:checked');
    }

    function markGroup(name, accepted) {
      const error = document.getElementById(name + "-error");
      error.hidden = accepted;
      document.querySelectorAll('input[name="' + name + '"]').forEach((input) => {
        input.setAttribute("aria-invalid", String(!accepted));
      });
    }

    function showText(node, text) {
      if (!text) {
        node.hidden = true;
        node.textContent = "";
        return;
      }
      node.hidden = false;
      node.textContent = text;
    }

    function showSteps(steps) {
      outcome.replaceChildren();
      if (steps.length < 2) {
        outcome.textContent = steps[0] || "";
        return;
      }
      const list = document.createElement("ol");
      steps.forEach((step) => {
        const item = document.createElement("li");
        item.textContent = step;
        list.appendChild(item);
      });
      outcome.appendChild(list);
    }

    function update() {
      const timing = selected("timing");
      const waiter = selected("waiter");
      const response = selected("response");
      const timingOk = Boolean(timing);
      const waiterOk = Boolean(waiter);
      const useResponse = timingOk && waiterOk && timing.value === "before" && waiter.value === "next";
      responseInputs.forEach((input) => {
        input.disabled = !useResponse;
      });
      if (timing && timing.value === "within") {
        responseHint.textContent = "이용 24시간 이내 취소에는 자동 안내가 가지 않는다. 이 항목을 쓰지 않는다.";
      } else if (waiter && waiter.value === "none") {
        responseHint.textContent = "남은 대기자가 없는 조건에는 이 항목을 쓰지 않는다.";
      } else {
        responseHint.textContent = "기한은 안내를 받은 시점으로부터 4시간이다.";
      }
      const responseOk = !useResponse || Boolean(response);
      markGroup("timing", timingOk);
      markGroup("waiter", waiterOk);
      markGroup("response", responseOk);
      const valid = timingOk && waiterOk && responseOk;
      resultError.hidden = valid;
      if (!valid) {
        outcome.replaceChildren();
        outcome.textContent = "계산을 보류한다";
        showText(basis, "입력 오류를 수정하면 결과를 다시 보여 준다.");
        showText(condition, "");
        return;
      }

      const before = timing.value === "before";
      const within = timing.value === "within";
      const hasNext = waiter.value === "next";
      const noneLeft = waiter.value === "none";
      const responded = response && response.value === "in";
      let steps = [];
      let basisText = "";
      let conditionText = "";

      if (within && hasNext) {
        steps = [
          "자동 안내가 가지 않는다.",
          "총무팀이 직접 판단해서 처리한다."
        ];
        basisText = "취소 시점은 이용 24시간 이내다.";
      } else if (within && noneLeft) {
        steps = [
          "자동 안내가 가지 않는다.",
          "총무팀이 직접 판단해서 처리한다.",
          "해당 시간대가 일반 예약으로 다시 열린다."
        ];
        basisText = "취소 시점은 이용 24시간 이내다. 남은 대기자가 없다.";
        conditionText = "자동 안내가 가지 않는 조건과 총무팀 처리의 조건은 이용 24시간 이내 취소다. 시간대가 일반 예약으로 다시 열리는 조건은 남은 대기자가 없는 경우다.";
      } else if (before && noneLeft) {
        steps = ["해당 시간대가 일반 예약으로 다시 열린다."];
        basisText = "취소 시점은 이용 시간 24시간 전까지다. 남은 대기자가 없다.";
        conditionText = "시간대가 일반 예약으로 다시 열리는 조건은 남은 대기자가 없는 경우다.";
      } else if (before && hasNext && responded) {
        steps = [
          "시스템이 대기자 명단의 다음 순번에게 안내를 자동으로 보낸다.",
          "안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답한다."
        ];
        basisText = "취소 시점은 이용 시간 24시간 전까지다. 다음 순번 대기자가 있다. 그 대기자는 4시간 이내에 응답한다.";
        conditionText = "응답 기한은 안내를 받은 시점으로부터 4시간이다.";
      } else if (before && hasNext && !responded) {
        steps = [
          "시스템이 대기자 명단의 다음 순번에게 안내를 자동으로 보낸다.",
          "안내가 그다음 대기자에게 넘어간다."
        ];
        basisText = "취소 시점은 이용 시간 24시간 전까지다. 다음 순번 대기자가 있다. 그 대기자는 4시간 이내에 응답하지 않는다.";
        conditionText = "응답 기한은 안내를 받은 시점으로부터 4시간이다.";
      }

      showSteps(steps);
      showText(basis, basisText);
      showText(condition, conditionText);
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      update();
    });
    document.getElementById("reset-cancellation").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```