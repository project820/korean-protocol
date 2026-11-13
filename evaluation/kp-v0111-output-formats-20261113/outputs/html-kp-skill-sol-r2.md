```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회의실 예약 취소 처리 안내</title>
  <style>
    :root {
      color-scheme: light;
      --background: #f4f6fa;
      --surface: #ffffff;
      --text: #192638;
      --muted: #526174;
      --border: #d5ddea;
      --accent: #2456b8;
      --tint: #eef4ff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--background);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.7;
      overflow-wrap: anywhere;
    }

    main {
      width: min(100% - 32px, 820px);
      margin: 48px auto;
    }

    h1 {
      margin: 0 0 12px;
      font-size: clamp(1.55rem, 4vw, 2.15rem);
      line-height: 1.4;
      letter-spacing: -0.04em;
    }

    h2 {
      margin: 0 0 18px;
      font-size: 1.15rem;
    }

    p { margin: 0 0 12px; }
    p:last-child { margin-bottom: 0; }

    .scope {
      margin-bottom: 28px;
      color: var(--muted);
    }

    .panel {
      margin-top: 20px;
      padding: 26px;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: var(--surface);
    }

    .result-panel {
      border-top: 5px solid var(--accent);
    }

    .conditions {
      margin-bottom: 20px;
      padding: 14px 16px;
      border-radius: 10px;
      background: var(--tint);
    }

    .conditions p {
      margin-bottom: 6px;
      font-size: 0.95rem;
    }

    .assumption {
      color: var(--muted);
      font-size: 0.9rem;
    }

    .result-title {
      margin-bottom: 16px;
      font-size: 1.2rem;
      font-weight: 700;
    }

    .steps {
      margin: 0;
      padding-left: 24px;
    }

    .steps li {
      padding-left: 4px;
      margin-bottom: 14px;
    }

    .steps li:last-child { margin-bottom: 0; }
    .steps p { margin: 4px 0 0; }
    .steps strong { display: block; }

    fieldset {
      min-width: 0;
      margin: 0 0 24px;
      padding: 0;
      border: 0;
    }

    legend {
      margin-bottom: 10px;
      padding: 0;
      font-weight: 700;
    }

    .choices {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .choice {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      min-height: 60px;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 10px;
      cursor: pointer;
    }

    .choice:has(input:checked) {
      border-color: var(--accent);
      background: var(--tint);
    }

    input[type="radio"] {
      flex: 0 0 auto;
      width: 18px;
      height: 18px;
      margin: 5px 0 0;
      accent-color: var(--accent);
    }

    input:focus-visible,
    button:focus-visible {
      outline: 3px solid var(--accent);
      outline-offset: 4px;
    }

    button {
      min-height: 44px;
      padding: 10px 18px;
      border: 1px solid var(--border);
      border-radius: 9px;
      background: var(--surface);
      color: var(--text);
      font: inherit;
      cursor: pointer;
    }

    button:hover { background: var(--tint); }

    .reference { color: var(--muted); }

    @media (max-width: 540px) {
      main {
        width: calc(100% - 24px);
        margin: 28px auto;
      }

      .panel { padding: 20px 16px; }
      .choices { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소 처리 경로를 확인한다</h1>
      <p class="scope">대상·범위: 예약이 확정된 이용자의 취소와 대기자 안내</p>
    </header>

    <section class="panel result-panel" aria-labelledby="result-heading">
      <h2 id="result-heading">처리 결과</h2>

      <div class="conditions">
        <p><strong>선택 조건:</strong> <span id="selected-conditions"></span></p>
        <p class="assumption">선택값은 처리 규칙을 확인하기 위한 가정이다.</p>
      </div>

      <div id="result" aria-live="polite" aria-atomic="true">
        <p class="result-title" id="result-title">다음 순번 대기자에게 자동으로 안내한다.</p>
        <ol class="steps" id="result-steps">
          <li>
            <strong>시스템이 다음 순번 대기자에게 안내를 보낸다.</strong>
          </li>
          <li>
            <strong>안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</strong>
          </li>
          <li>
            <strong>4시간 이내에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</strong>
            <p>남은 대기자가 없으면 해당 시간대를 일반 예약으로 다시 연다.</p>
          </li>
        </ol>
      </div>
    </section>

    <section class="panel" aria-labelledby="input-heading">
      <h2 id="input-heading">조건 선택</h2>

      <form id="scenario-form">
        <fieldset>
          <legend>취소 시점</legend>
          <div class="choices">
            <label class="choice" for="timing-advance">
              <input id="timing-advance" type="radio" name="cancellation-timing"
                     value="advance" checked>
              <span>이용 시간 24시간 전까지 취소</span>
            </label>
            <label class="choice" for="timing-late">
              <input id="timing-late" type="radio" name="cancellation-timing"
                     value="late">
              <span>이용 24시간 이내 취소</span>
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>남은 대기자</legend>
          <div class="choices">
            <label class="choice" for="waiting-present">
              <input id="waiting-present" type="radio" name="waiting-status"
                     value="present" checked>
              <span>있음</span>
            </label>
            <label class="choice" for="waiting-empty">
              <input id="waiting-empty" type="radio" name="waiting-status"
                     value="empty">
              <span>없음</span>
            </label>
          </div>
        </fieldset>

        <button id="restore-defaults" type="button">초기화</button>
      </form>
    </section>

    <section class="panel" aria-labelledby="rules-heading">
      <h2 id="rules-heading">적용 기준</h2>
      <p>취소 시점과 남은 대기자 유무를 바꾸면 처리 결과가 바로 바뀐다.</p>
      <p>대기자의 응답 기한은 안내를 받은 시점부터 계산한다.</p>
    </section>

    <section class="panel reference" aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <p>취소 시점의 선택지는 원문의 표현을 유지했다.</p>
      <p>정확히 24시간 전인 경우의 구분 기준은 제공된 원문에서 명확하지 않다.</p>
    </section>

    <noscript>
      <section class="panel">
        <h2>전체 처리 규칙</h2>
        <p>조건별 결과 전환에는 JavaScript가 필요하다.</p>
        <ul>
          <li>이용 시간 24시간 전까지 취소하면 시스템이 다음 순번 대기자에게 안내한다.</li>
          <li>안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</li>
          <li>기한 내 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</li>
          <li>이용 24시간 이내에 취소하면 자동 안내 없이 총무팀이 직접 판단해 처리한다.</li>
          <li>남은 대기자가 없으면 해당 시간대를 일반 예약으로 다시 연다.</li>
        </ul>
      </section>
    </noscript>
  </main>

  <script>
    (() => {
      "use strict";

      const form = document.getElementById("scenario-form");
      const conditions = document.getElementById("selected-conditions");
      const title = document.getElementById("result-title");
      const steps = document.getElementById("result-steps");
      const restoreButton = document.getElementById("restore-defaults");

      function addStep(action, detail) {
        const item = document.createElement("li");
        const heading = document.createElement("strong");
        heading.textContent = action;
        item.appendChild(heading);

        if (detail) {
          const paragraph = document.createElement("p");
          paragraph.textContent = detail;
          item.appendChild(paragraph);
        }

        steps.appendChild(item);
      }

      function updateResult() {
        const timing = form.querySelector(
          'input[name="cancellation-timing"]:checked'
        ).value;
        const waiting = form.querySelector(
          'input[name="waiting-status"]:checked'
        ).value;

        const timingLabel = timing === "advance"
          ? "이용 시간 24시간 전까지 취소"
          : "이용 24시간 이내 취소";
        const waitingLabel = waiting === "present"
          ? "남은 대기자 있음"
          : "남은 대기자 없음";

        conditions.textContent = timingLabel + " / " + waitingLabel;
        steps.replaceChildren();

        if (timing === "late") {
          title.textContent = "총무팀이 직접 판단해 처리한다.";
          addStep("자동 안내를 보내지 않는다.");
          addStep("총무팀이 직접 판단해 처리한다.");

          if (waiting === "empty") {
            addStep("남은 대기자가 없으면 해당 시간대를 일반 예약으로 다시 연다.");
          }
          return;
        }

        if (waiting === "empty") {
          title.textContent = "해당 시간대를 일반 예약으로 다시 연다.";
          addStep("남은 대기자가 없으므로 해당 시간대를 일반 예약으로 다시 연다.");
          return;
        }

        title.textContent = "다음 순번 대기자에게 자동으로 안내한다.";
        addStep("시스템이 다음 순번 대기자에게 안내를 보낸다.");
        addStep("안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.");
        addStep(
          "4시간 이내에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.",
          "남은 대기자가 없으면 해당 시간대를 일반 예약으로 다시 연다."
        );
      }

      form.addEventListener("change", updateResult);
      form.addEventListener("submit", event => event.preventDefault());

      restoreButton.addEventListener("click", () => {
        form.reset();
        updateResult();
      });

      updateResult();
    })();
  </script>
</body>
</html>
```