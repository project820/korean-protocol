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
      overflow-wrap: anywhere;
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
    p, dd { max-width: var(--measure); }
    .lead, .hint { color: var(--muted); }
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
    }
    .result { background: var(--accent-soft); border-color: var(--accent); }
    output {
      display: block;
      margin-block: var(--space-3);
      font-size: clamp(1.35rem, 3vw, 1.8rem);
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
    legend { padding: 0; margin-block-end: var(--space-2); font-weight: 650; }
    .choice {
      display: flex;
      align-items: flex-start;
      gap: var(--space-2);
      padding-block: var(--space-1);
    }
    input[type="radio"] {
      flex: 0 0 auto;
      width: 1.15rem;
      height: 1.15rem;
      margin: 0.3rem 0 0;
      accent-color: var(--accent);
    }
    label { cursor: pointer; }
    fieldset:disabled { color: var(--muted); }
    fieldset:disabled label { cursor: default; }
    .hint { font-size: 0.9375rem; margin-block: var(--space-1) 0; }
    .notice {
      padding: var(--space-3);
      background: var(--warning-surface);
      color: var(--warning);
      border-left: 0.25rem solid var(--warning);
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
    .details { margin-block-start: var(--space-4); }
    dl { margin: 0; }
    dt { margin-block-start: var(--space-3); font-weight: 650; }
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
      <p class="lead">확정된 예약의 취소 시점과 대기 상태를 선택하면 처리 내용을 표시한다.</p>
    </header>

    <div class="panel_layout">
      <section class="panel result" aria-labelledby="result-heading">
        <h2 id="result-heading">처리 내용</h2>
        <div aria-live="polite" aria-atomic="true">
          <output id="handling"
            for="timing-early timing-late stage-cancel stage-expired waiting-yes waiting-no"
            role="none">시스템이 다음 순번 대기자에게 자동으로 안내한다.</output>
          <p id="basis">이용 시간 24시간 전까지 취소했고, 남은 대기자가 있다.</p>
          <p class="notice" id="condition">안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</p>
          <p id="additional" hidden></p>
        </div>
        <p class="hint">가정: 초기 화면은 취소 직후이며, 남은 대기자가 있는 경우다.</p>
      </section>

      <section class="panel" aria-labelledby="inputs-heading">
        <h2 id="inputs-heading">취소·대기 조건</h2>
        <form id="reservation-conditions">
          <fieldset>
            <legend>취소 시점</legend>
            <div class="choice">
              <input id="timing-early" name="timing" type="radio" value="early" checked>
              <label for="timing-early">이용 시간 24시간 전까지</label>
            </div>
            <div class="choice">
              <input id="timing-late" name="timing" type="radio" value="late">
              <label for="timing-late">이용 24시간 이내</label>
            </div>
          </fieldset>

          <fieldset id="stage-group" aria-describedby="stage-hint">
            <legend>자동 안내의 처리 상황</legend>
            <div class="choice">
              <input id="stage-cancel" name="stage" type="radio" value="cancel" checked>
              <label for="stage-cancel">예약 취소 직후</label>
            </div>
            <div class="choice">
              <input id="stage-expired" name="stage" type="radio" value="expired">
              <label for="stage-expired">안내받은 대기자가 4시간 이내 미응답</label>
            </div>
            <p class="hint" id="stage-hint">이용 시간 24시간 전까지 취소한 경우에 적용한다.</p>
          </fieldset>

          <fieldset aria-describedby="waiting-hint">
            <legend>남은 대기자</legend>
            <div class="choice">
              <input id="waiting-yes" name="waiting" type="radio" value="yes" checked>
              <label for="waiting-yes">있음</label>
            </div>
            <div class="choice">
              <input id="waiting-no" name="waiting" type="radio" value="no">
              <label for="waiting-no">없음</label>
            </div>
            <p class="hint" id="waiting-hint">취소 직후에는 다음 순번 대기자의 유무를 선택한다. 미응답 후에는 그다음 대기자의 유무를 선택한다.</p>
          </fieldset>
          <button type="button" id="restore-defaults">초기화</button>
        </form>
      </section>
    </div>

    <section class="panel details" aria-labelledby="rules-heading">
      <h2 id="rules-heading">처리 규칙</h2>
      <dl>
        <dt>이용 시간 24시간 전까지 취소</dt>
        <dd>시스템이 대기자 명단의 다음 순번에게 자동으로 안내한다.</dd>

        <dt>안내받은 대기자의 응답 기한</dt>
        <dd>안내받은 시점부터 4시간 이내에 응답해야 한다.</dd>

        <dt>4시간 이내 미응답</dt>
        <dd>그다음 대기자에게 안내가 넘어간다.</dd>

        <dt>이용 24시간 이내 취소</dt>
        <dd>자동 안내는 발송되지 않는다. 총무팀이 직접 판단해 처리한다.</dd>

        <dt>남은 대기자 없음</dt>
        <dd>해당 시간대가 일반 예약으로 다시 열린다.</dd>
      </dl>
    </section>

    <section class="panel details" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <dl>
        <dt>출처</dt>
        <dd>제공된 회의실 예약 취소 안내 원문을 기준으로 작성했다.</dd>

        <dt>선택 조건과 실제 처리</dt>
        <dd>화면은 선택한 조건에 따른 규칙을 표시한다. 실제 예약 취소나 대기자 안내를 실행하지 않는다.</dd>

        <dt>저장·전송 여부</dt>
        <dd>선택값은 저장하거나 외부로 전송하지 않는다.</dd>

        <dt>확인 범위</dt>
        <dd>코드를 작성했으며, 진단 도구 실행과 브라우저 동작 검사는 수행하지 않았다.</dd>
      </dl>
    </section>

    <noscript>
      <p class="notice">JavaScript가 꺼져 있어 선택 변경을 반영하지 못한다. 처리 내용에는 초기 조건의 결과를 표시한다.</p>
    </noscript>
  </main>

  <script>
    "use strict";

    const form = document.getElementById("reservation-conditions");
    const stageGroup = document.getElementById("stage-group");
    const handling = document.getElementById("handling");
    const basis = document.getElementById("basis");
    const condition = document.getElementById("condition");
    const additional = document.getElementById("additional");

    function selected(name) {
      return form.querySelector('input[name="' + name + '"]:checked').value;
    }

    function update() {
      const late = selected("timing") === "late";
      const expired = selected("stage") === "expired";
      const hasWaiting = selected("waiting") === "yes";

      stageGroup.disabled = late;
      condition.hidden = true;
      condition.textContent = "";
      additional.hidden = true;
      additional.textContent = "";

      if (late) {
        handling.textContent = "총무팀이 직접 판단해 처리한다.";
        basis.textContent = "이용 24시간 이내에 취소한 경우다.";
        condition.textContent = "자동 안내는 발송되지 않는다.";
        condition.hidden = false;

        if (!hasWaiting) {
          additional.textContent = "남은 대기자가 없어 해당 시간대가 일반 예약으로 다시 열린다.";
          additional.hidden = false;
        }
        return;
      }

      if (!hasWaiting) {
        handling.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        basis.textContent = expired
          ? "안내받은 대기자가 4시간 이내에 응답하지 않았고, 남은 대기자가 없다."
          : "예약 취소 후 남은 대기자가 없다.";
        return;
      }

      handling.textContent = expired
        ? "그다음 대기자에게 안내가 넘어간다."
        : "시스템이 다음 순번 대기자에게 자동으로 안내한다.";

      basis.textContent = expired
        ? "안내받은 대기자가 4시간 이내에 응답하지 않았고, 남은 대기자가 있다."
        : "이용 시간 24시간 전까지 취소했고, 남은 대기자가 있다.";

      condition.textContent = "안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.";
      condition.hidden = false;
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => event.preventDefault());

    document.getElementById("restore-defaults").addEventListener("click", () => {
      HTMLFormElement.prototype.reset.call(form);
      update();
    });

    update();
  </script>
</body>
</html>
```