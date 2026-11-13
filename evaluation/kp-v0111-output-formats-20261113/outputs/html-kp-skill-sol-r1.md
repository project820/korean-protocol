```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회의실 예약 취소 후 처리 규칙을 확인한다</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6fa;
      --panel: #fff;
      --text: #1e293b;
      --muted: #526176;
      --line: #d5dce6;
      --accent: #2455ad;
      --soft: #edf3ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      line-height: 1.7;
    }
    main {
      width: min(100% - 32px, 780px);
      margin: 40px auto;
    }
    h1 { margin: 0 0 12px; font-size: clamp(1.5rem, 4vw, 2rem); line-height: 1.4; }
    h2 { margin: 0 0 18px; font-size: 1.2rem; }
    p { margin: 10px 0; }
    .scope { margin-bottom: 24px; color: var(--muted); }
    section {
      margin-top: 20px;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel);
    }
    .result { background: var(--soft); border-color: #b8ccef; }
    .status { margin: 0 0 12px; color: var(--accent); font-size: 1.25rem; font-weight: 750; }
    fieldset { margin: 0 0 22px; padding: 0; border: 0; min-width: 0; }
    legend { margin-bottom: 10px; font-weight: 700; }
    .choices { display: grid; gap: 10px; }
    label {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 9px;
      cursor: pointer;
    }
    label:has(input:checked) { background: var(--soft); border-color: var(--accent); }
    input { margin: 7px 0 0; accent-color: var(--accent); flex: 0 0 auto; }
    button {
      padding: 10px 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      font: inherit;
      cursor: pointer;
    }
    button:hover { background: var(--soft); }
    :focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
    .note { font-size: .92rem; color: var(--muted); }
    ul { padding-left: 22px; margin-bottom: 0; }
    li + li { margin-top: 12px; }
    [hidden] { display: none !important; }
    @media (max-width: 420px) {
      main { width: calc(100% - 24px); margin: 24px auto; }
      section { padding: 18px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>회의실 예약 취소 후 처리 규칙을 확인한다</h1>
      <p class="scope">대상·범위: 확정된 회의실 예약의 취소와 대기자 안내</p>
    </header>

    <section class="result" aria-labelledby="result-heading">
      <h2 id="result-heading">처리 결과</h2>
      <div id="result-content" aria-live="polite" aria-atomic="true">
        <p class="status" id="result-status">다음 대기자에게 자동 안내</p>
        <p id="result-main">시스템이 대기자 명단의 다음 순번에게 안내를 보낸다.</p>
        <p id="result-condition">안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</p>
        <p id="result-extra" hidden></p>
      </div>
    </section>

    <section aria-labelledby="input-heading">
      <h2 id="input-heading">상황 선택</h2>
      <p class="note">선택값을 바꾸면 해당 규칙을 바로 표시한다. 실제 예약을 변경하는 기능은 없다.</p>

      <form id="scenario-form">
        <fieldset>
          <legend>확인할 상황</legend>
          <div class="choices">
            <label>
              <input type="radio" name="event-type" value="cancel" checked>
              <span>확정된 예약의 취소</span>
            </label>
            <label>
              <input type="radio" name="event-type" value="timeout">
              <span>안내받은 시점부터 4시간 이내 응답 없음</span>
            </label>
          </div>
        </fieldset>

        <fieldset id="timing-fieldset">
          <legend>취소 시점 — 원문에 제시된 조건</legend>
          <div class="choices">
            <label>
              <input type="radio" name="cancel-timing" value="advance" checked>
              <span>이용 시간 24시간 전까지 취소</span>
            </label>
            <label>
              <input type="radio" name="cancel-timing" value="late">
              <span>이용 24시간 이내 취소</span>
            </label>
          </div>
          <p class="note">
            정확히 24시간 전은 두 표현의 경계가 겹친다.
            원문은 이 경계의 우선 적용 기준을 명시하지 않는다.
            여기서는 선택한 조건의 규칙을 표시한다.
          </p>
        </fieldset>

        <fieldset>
          <legend>남은 대기자 — 다음으로 안내할 대기자 기준</legend>
          <div class="choices">
            <label>
              <input type="radio" name="waiting-state" value="available" checked>
              <span>있음</span>
            </label>
            <label>
              <input type="radio" name="waiting-state" value="empty">
              <span>없음</span>
            </label>
          </div>
        </fieldset>

        <button type="button" id="restore-defaults">초기화</button>
      </form>
    </section>

    <section aria-labelledby="rules-heading">
      <h2 id="rules-heading">처리 규칙</h2>
      <ul>
        <li>
          <strong>이용 시간 24시간 전까지 취소:</strong>
          시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.
        </li>
        <li>
          <strong>안내받은 대기자의 응답:</strong>
          안내받은 시점부터 4시간 이내에 응답해야 한다.
          그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.
        </li>
        <li>
          <strong>이용 24시간 이내 취소:</strong>
          자동 안내를 보내지 않는다.
          총무팀이 직접 판단해서 처리한다.
        </li>
        <li>
          <strong>남은 대기자 없음:</strong>
          해당 시간대가 일반 예약으로 다시 열린다.
        </li>
      </ul>
    </section>

    <section aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <p class="note">출처: 제공된 「회의실 예약 취소」 원문</p>
    </section>
  </main>

  <script>
    "use strict";

    const form = document.getElementById("scenario-form");
    const timingFieldset = document.getElementById("timing-fieldset");
    const status = document.getElementById("result-status");
    const mainText = document.getElementById("result-main");
    const condition = document.getElementById("result-condition");
    const extra = document.getElementById("result-extra");

    function selected(name) {
      return form.querySelector('input[name="' + name + '"]:checked').value;
    }

    function updateResult() {
      const eventType = selected("event-type");
      const timing = selected("cancel-timing");
      const waiting = selected("waiting-state");
      const isCancellation = eventType === "cancel";
      const isManual = isCancellation && timing === "late";
      const isEmpty = waiting === "empty";

      timingFieldset.hidden = !isCancellation;
      timingFieldset.disabled = !isCancellation;

      condition.hidden = true;
      extra.hidden = true;
      condition.textContent = "";
      extra.textContent = "";

      if (isManual) {
        status.textContent = "総務팀 직접 처리".replace("総務", "총무");
        mainText.textContent = "총무팀이 직접 판단해서 처리한다.";
        condition.textContent = "이용 24시간 이내 취소에는 자동 안내를 보내지 않는다.";
        condition.hidden = false;

        if (isEmpty) {
          extra.textContent = "남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.";
          extra.hidden = false;
        }
        return;
      }

      if (isEmpty) {
        status.textContent = "일반 예약으로 재개방";
        mainText.textContent = "남은 대기자가 없으므로 해당 시간대가 일반 예약으로 다시 열린다.";
        return;
      }

      status.textContent = isCancellation
        ? "다음 대기자에게 자동 안내"
        : "그다음 대기자에게 안내";

      mainText.textContent = isCancellation
        ? "시스템이 대기자 명단의 다음 순번에게 안내를 보낸다."
        : "4시간 이내에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.";

      condition.textContent = "안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.";
      condition.hidden = false;
    }

    form.addEventListener("change", updateResult);
    document.getElementById("restore-defaults").addEventListener("click", function () {
      form.reset();
      updateResult();
    });

    updateResult();
  </script>
</body>
</html>
```