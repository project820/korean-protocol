```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약 취소의 다음 처리를 정한다</title>
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
    h1 { max-width: 24ch; font-size: clamp(1.75rem, 4vw, 2.5rem); line-height: 1.3; letter-spacing: -0.025em; }
    h2 { font-size: 1.25rem; line-height: 1.45; }
    p, li { max-width: var(--measure); }
    .lead { color: var(--muted); }
    .panel_layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); align-items: start; margin-block: var(--space-4); }
    .panel_layout > * { min-inline-size: 0; }
    .panel { border: 1px solid var(--line); background: var(--surface); padding: var(--space-4); border-radius: 0.75rem; }
    fieldset { border: 0; margin: 0 0 var(--space-4); padding: 0; }
    legend { font-weight: 650; padding: 0; margin-block-end: var(--space-1); }
    .choice { display: flex; gap: var(--space-2); align-items: flex-start; margin-block: var(--space-1); font-weight: 450; }
    input { font: inherit; color: var(--text); }
    .choice input { width: 1.125rem; height: 1.125rem; margin-block-start: 0.35rem; }
    .hint { font-size: 0.9375rem; color: var(--muted); margin-block: var(--space-1) 0; }
    button { min-height: 2.75rem; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--accent); border-radius: 0.375rem; color: var(--accent); background: var(--surface); cursor: pointer; }
    button:hover { background: var(--accent-soft); }
    button:disabled, input:disabled { cursor: not-allowed; }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output, .result-list { display: block; font-size: clamp(1.35rem, 3vw, 1.85rem); line-height: 1.45; font-weight: 650; color: var(--accent); margin-block: 0 var(--space-3); overflow-wrap: anywhere; }
    .result-list { padding-inline-start: 1.25rem; }
    .result-list li { max-width: var(--measure); margin-block-end: var(--space-2); }
    .formula { font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
    .assumption { padding: var(--space-3); background: var(--warning-surface); color: var(--warning); border-left: 0.25rem solid var(--warning); }
    .details { margin-block-start: var(--space-4); }
    dl, ul.rules { margin: 0; padding: 0; }
    ul.rules { padding-inline-start: 1.25rem; }
    ul.rules li { margin-block-end: var(--space-2); }
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
      <h1>회의실 예약 취소의 다음 처리를 정한다</h1>
      <p class="lead">취소 시점과 대기자 상태를 바꾸면 다음 처리가 바뀐다.</p>
      <p>예약이 확정된 사람의 회의실 예약 취소에 적용한다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">다음 처리</h2>
        <div id="live" aria-live="polite" aria-atomic="true">
          <output id="outcome" for="time-before time-within waiter-next waiter-none reply-in reply-out">시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.</output>
          <ol id="ordered" class="result-list" hidden></ol>
          <ul id="parallel" class="result-list" hidden></ul>
          <p class="formula" id="reason">근거: 이용 시간 24시간 전까지 취소이고, 다음 순번이 있다.</p>
          <p id="condition">안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</p>
        </div>
        <p class="assumption" id="assumption">가정: 이 화면은 두 대기자 상태를 함께 고르지 못한다. 두 상태는 다음 순번이 있음과 남은 대기자가 없음이다.</p>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="scenario" novalidate>
          <fieldset>
            <legend>취소 시점</legend>
            <label class="choice"><input id="time-before" name="cancel-time" type="radio" value="before" checked> 이용 시간 24시간 전까지</label>
            <label class="choice"><input id="time-within" name="cancel-time" type="radio" value="within"> 이용 24시간 이내</label>
          </fieldset>
          <fieldset>
            <legend>대기자</legend>
            <label class="choice"><input id="waiter-next" name="waiter-state" type="radio" value="next" checked> 대기자 명단에 다음 순번이 있다</label>
            <label class="choice"><input id="waiter-none" name="waiter-state" type="radio" value="none"> 남은 대기자가 없다</label>
          </fieldset>
          <fieldset id="reply-set" aria-describedby="reply-hint">
            <legend>안내를 받은 대기자의 응답</legend>
            <label class="choice"><input id="reply-in" name="reply-state" type="radio" value="in" checked> 4시간 이내에 응답한다</label>
            <label class="choice"><input id="reply-out" name="reply-state" type="radio" value="out"> 4시간 이내에 응답하지 않는다</label>
            <p class="hint" id="reply-hint">안내를 받은 시점으로부터 4시간 이내인지로 결과가 갈린다.</p>
          </fieldset>
          <button type="button" id="reset-scenario">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="basis-heading">
      <h2 id="basis-heading">처리 규칙</h2>
      <ul class="rules">
        <li>예약이 확정된 사람이 이용 시간 24시간 전까지 취소한다. 그러면 시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.</li>
        <li>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</li>
        <li>그 시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.</li>
        <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다.</li>
        <li>이 경우 총무팀이 직접 판단해서 처리한다.</li>
        <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
      </ul>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <dl>
        <dt>출처</dt>
        <dd>제공된 회의실 예약 취소 안내만 반영한다.</dd>
        <dt>24시간 경계</dt>
        <dd>원문은 이용 시간 24시간 전까지와 이용 24시간 이내를 적는다. 두 표현이 겹치는 시점의 포함은 원문에 없다.</dd>
        <dt>재오픈 문장의 위치</dt>
        <dd>남은 대기자가 없으면 일반 예약으로 다시 열린다는 문장은 이용 24시간 이내 취소 문장 뒤에 이어진다. 그 취소에만 적용되는지는 원문이 가르지 않는다.</dd>
        <dt>저장·전송 여부</dt>
        <dd>입력값을 서버에 전송하거나 저장하지 않는다. 초기화하면 처음 선택으로 돌아간다.</dd>
      </dl>
    </section>
    <noscript><p class="assumption">JavaScript가 꺼져 있어 선택을 다시 계산하지 못한다. 위 결과는 처음 선택의 결과다.</p></noscript>
  </main>
  <script>
    "use strict";
    const form = document.getElementById("scenario");
    const outcome = document.getElementById("outcome");
    const ordered = document.getElementById("ordered");
    const parallel = document.getElementById("parallel");
    const reason = document.getElementById("reason");
    const condition = document.getElementById("condition");
    const replyHint = document.getElementById("reply-hint");
    const replyInputs = [document.getElementById("reply-in"), document.getElementById("reply-out")];

    function selected(name) {
      const field = form.querySelector("input[name='" + name + "']:checked");
      return field ? field.value : "";
    }

    function fill(list, items) {
      list.replaceChildren();
      items.forEach((text) => {
        const item = document.createElement("li");
        item.textContent = text;
        list.append(item);
      });
    }

    function render(mode, items, reasonText, conditionText) {
      const useList = mode !== "single";
      outcome.hidden = useList;
      outcome.textContent = useList ? "" : items[0];
      ordered.hidden = mode !== "ordered";
      parallel.hidden = mode !== "parallel";
      fill(ordered, mode === "ordered" ? items : []);
      fill(parallel, mode === "parallel" ? items : []);
      reason.textContent = reasonText;
      condition.hidden = conditionText.length === 0;
      condition.textContent = conditionText;
    }

    function update() {
      const time = selected("cancel-time");
      const waiter = selected("waiter-state");
      const reply = selected("reply-state");
      const replyOn = time === "before" && waiter === "next";
      replyInputs.forEach((input) => {
        input.disabled = !replyOn;
      });
      replyHint.textContent = replyOn
        ? "안내를 받은 시점으로부터 4시간 이내인지로 결과가 갈린다."
        : "이용 시간 24시간 전까지 취소하고 다음 순번이 있을 때 결과를 바꾼다.";

      if (time === "within" && waiter === "next") {
        render(
          "parallel",
          ["자동 안내가 가지 않는다.", "총무팀이 직접 판단해서 처리한다."],
          "근거: 이용 24시간 이내에 취소한다.",
          ""
        );
        return;
      }
      if (time === "within" && waiter === "none") {
        render(
          "parallel",
          [
            "자동 안내가 가지 않는다.",
            "총무팀이 직접 판단해서 처리한다.",
            "해당 시간대가 일반 예약으로 다시 열린다."
          ],
          "근거: 이용 24시간 이내 취소이고, 남은 대기자가 없다.",
          ""
        );
        return;
      }
      if (time === "before" && waiter === "none") {
        render(
          "single",
          ["해당 시간대가 일반 예약으로 다시 열린다."],
          "근거: 남은 대기자가 없다.",
          "원문은 이 문장을 이용 24시간 이내 취소 문장 뒤에 이어 적는다."
        );
        return;
      }
      if (replyOn && reply === "out") {
        render(
          "ordered",
          [
            "시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.",
            "안내가 그다음 대기자에게 넘어간다."
          ],
          "근거: 안내를 받은 대기자가 4시간 이내에 응답하지 않는다.",
          "응답 기한은 안내를 받은 시점으로부터 4시간 이내다."
        );
        return;
      }
      render(
        "single",
        ["시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다."],
        "근거: 이용 시간 24시간 전까지 취소이고, 다음 순번이 있다. 대기자는 4시간 이내에 응답한다.",
        "안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다."
      );
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      update();
    });
    document.getElementById("reset-scenario").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```