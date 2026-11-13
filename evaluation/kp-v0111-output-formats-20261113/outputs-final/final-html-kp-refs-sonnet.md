```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="data:,">
  <title>회의실 예약 취소 후 처리 경로를 확인한다</title>
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
    p { max-width: var(--measure); }
    .lead { color: var(--muted); }
    .panel_layout { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr)); align-items: start; margin-block: var(--space-4); }
    .panel_layout > * { min-inline-size: 0; }
    .panel { border: 1px solid var(--line); background: var(--surface); padding: var(--space-4); border-radius: 0.75rem; }
    fieldset { border: 0; margin: 0 0 var(--space-4); padding: 0; min-inline-size: 0; }
    legend { font-weight: 650; padding: 0; margin-block-end: var(--space-1); }
    label { display: block; font-weight: 650; margin-block-end: var(--space-1); }
    .choice { display: flex; gap: var(--space-2); align-items: flex-start; font-weight: 400; margin-block-end: var(--space-1); }
    .choice input { margin-block-start: 0.45rem; flex: none; }
    .hint { font-size: 0.9375rem; color: var(--muted); margin-block: var(--space-1) 0; }
    button { min-height: 2.75rem; padding: var(--space-2) var(--space-3); font: inherit; border: 1px solid var(--accent); border-radius: 0.375rem; color: var(--accent); background: var(--surface); cursor: pointer; }
    button:hover { background: var(--accent-soft); }
    :focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output { display: block; font-size: clamp(1.375rem, 3.5vw, 1.875rem); line-height: 1.4; font-weight: 750; color: var(--accent); margin-block: var(--space-3); overflow-wrap: anywhere; }
    .notice { padding: var(--space-3); background: var(--warning-surface); color: var(--warning); border-left: 0.25rem solid var(--warning); }
    .details { margin-block-start: var(--space-4); }
    ol, ul { margin-block: 0 var(--space-3); padding-inline-start: 1.5rem; max-width: var(--measure); }
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
      <h1>회의실 예약 취소 후 처리 경로를 확인한다</h1>
      <p class="lead">취소 시점과 대기자 유무를 바꾸면 처리 경로를 다시 보인다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">취소 후 처리 경로</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="outcome" for="timing waiting"></output>
          <p id="basis"></p>
          <ol id="steps"></ol>
          <p class="notice" id="condition"></p>
        </div>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소 조건</h2>
        <form id="calculator" novalidate>
          <fieldset id="timing">
            <legend>취소 시점</legend>
            <label class="choice"><input type="radio" name="timing" value="before" checked><span>이용 시간 24시간 전까지 취소</span></label>
            <label class="choice"><input type="radio" name="timing" value="within"><span>이용 24시간 이내에 취소</span></label>
            <p class="hint">예약이 확정된 사람이 취소하는 경우다.</p>
          </fieldset>
          <fieldset id="waiting">
            <legend>대기자 명단</legend>
            <label class="choice"><input type="radio" name="waiting" value="yes" checked><span>대기자가 있다</span></label>
            <label class="choice"><input type="radio" name="waiting" value="no"><span>남은 대기자가 없다</span></label>
            <p class="hint">남은 대기자가 없을 때의 경로를 보려면 두 번째 항목을 고른다.</p>
          </fieldset>
          <button type="button" id="reset-calculator">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">규칙</h2>
      <dl>
        <dt>이용 시간 24시간 전까지 취소</dt>
        <dd>시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.</dd>
        <dt>대기자의 응답</dt>
        <dd>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다. 그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</dd>
        <dt>이용 24시간 이내 취소</dt>
        <dd>자동 안내를 보내지 않는다. 총무팀이 직접 판단해서 처리한다.</dd>
        <dt>남은 대기자가 없을 때</dt>
        <dd>해당 시간대가 일반 예약으로 다시 열린다.</dd>
      </dl>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <p class="hint">출처는 회의실 예약 취소 안내 원문이다. 원문은 이용 24시간 이내 취소에서 남은 대기자가 없을 때의 경로를 따로 밝히지 않았다. 입력값을 저장하거나 전송하지 않는다.</p>
    </section>
    <noscript><p class="notice">JavaScript가 꺼져 있어 선택에 따른 결과를 갱신하지 못한다. 아래 규칙 구획에서 경로를 확인한다.</p></noscript>
  </main>
  <script>
    "use strict";
    var form = document.getElementById("calculator");
    var outcome = document.getElementById("outcome");
    var basis = document.getElementById("basis");
    var steps = document.getElementById("steps");
    var condition = document.getElementById("condition");

    function selected(name) {
      return form.querySelector('input[name="' + name + '"]:checked').value;
    }

    function setSteps(list) {
      steps.textContent = "";
      list.forEach(function (text) {
        var li = document.createElement("li");
        li.textContent = text;
        steps.appendChild(li);
      });
    }

    function update() {
      var timing = selected("timing");
      var waiting = selected("waiting");
      if (timing === "before" && waiting === "yes") {
        outcome.textContent = "시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.";
        basis.textContent = "근거: 이용 시간 24시간 전까지 취소했고 대기자가 있다.";
        setSteps([
          "시스템이 다음 순번 대기자에게 안내를 보낸다.",
          "대기자가 안내를 받은 시점으로부터 4시간 이내에 응답한다.",
          "4시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다."
        ]);
        condition.textContent = "조건: 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.";
      } else if (timing === "before") {
        outcome.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = "근거: 이용 시간 24시간 전까지 취소했고 남은 대기자가 없다.";
        setSteps(["해당 시간대가 일반 예약으로 다시 열린다."]);
        condition.textContent = "조건: 남은 대기자가 없는 경우에 적용한다.";
      } else {
        outcome.textContent = "총무팀이 직접 판단해서 처리한다.";
        basis.textContent = "근거: 이용 24시간 이내에 취소했다.";
        setSteps(["자동 안내를 보내지 않는다.", "총무팀이 직접 판단해서 처리한다."]);
        condition.textContent = waiting === "no"
          ? "조건: 이 선택에서 남은 대기자가 없을 때의 경로는 제공된 자료에 없다."
          : "조건: 자동 안내는 이용 24시간 이내 취소에 적용하지 않는다.";
      }
    }

    form.addEventListener("change", update);
    form.addEventListener("submit", function (event) { event.preventDefault(); update(); });
    document.getElementById("reset-calculator").addEventListener("click", function () {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });
    update();
  </script>
</body>
</html>
```