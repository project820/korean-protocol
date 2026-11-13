```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회의실 예약 취소에 따른 처리를 확인한다</title>
  <style>
    :root {
      color-scheme: light;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      color: #172333;
      background: #f4f7fa;
      line-height: 1.6;
    }

    * { box-sizing: border-box; }

    body {
      max-width: 760px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: clamp(1.5rem, 4vw, 2rem);
      line-height: 1.3;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 1.15rem;
    }

    p { margin: 0 0 12px; }

    .scope {
      margin-bottom: 24px;
      color: #526274;
    }

    section {
      margin-top: 16px;
      padding: 20px;
      border: 1px solid #d7e0e9;
      border-radius: 12px;
      background: #fff;
    }

    .result {
      border-left: 5px solid #1766ad;
      background: #f1f7fd;
    }

    .result-main {
      margin-bottom: 8px;
      font-size: 1.15rem;
      font-weight: 700;
    }

    .result p:last-child,
    section p:last-child { margin-bottom: 0; }

    fieldset {
      margin: 0 0 20px;
      padding: 0;
      border: 0;
    }

    fieldset:last-child { margin-bottom: 0; }

    legend {
      margin-bottom: 8px;
      font-weight: 700;
    }

    .option {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 0;
      cursor: pointer;
    }

    input {
      width: 18px;
      height: 18px;
      margin: 4px 0 0;
      accent-color: #1766ad;
    }

    input:focus-visible {
      outline: 3px solid #1766ad;
      outline-offset: 3px;
    }

    ul {
      margin: 0;
      padding-left: 22px;
    }

    li + li { margin-top: 8px; }

    .note {
      color: #526274;
      font-size: 0.95rem;
    }

    @media (max-width: 320px) {
      body { padding: 20px 12px 32px; }
      section { padding: 16px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>회의실 예약 취소에 따른 처리를 확인한다</h1>
    <p class="scope">대상: 확정된 회의실 예약의 취소와 대기자 안내</p>

    <section class="result" aria-labelledby="result-heading">
      <h2 id="result-heading">처리 결과</h2>
      <div id="result" aria-live="polite" aria-atomic="true">
        <p class="result-main" id="result-main"></p>
        <p id="result-detail"></p>
      </div>
    </section>

    <section aria-labelledby="input-heading">
      <h2 id="input-heading">조건 선택</h2>

      <fieldset>
        <legend>취소 시점</legend>
        <label class="option">
          <input type="radio" name="cancellation" value="before" checked>
          <span>이용 시간 24시간 전까지</span>
        </label>
        <label class="option">
          <input type="radio" name="cancellation" value="within">
          <span>이용 24시간 이내</span>
        </label>
      </fieldset>

      <fieldset>
        <legend>대기자 상태</legend>
        <label class="option">
          <input type="radio" name="waiting" value="available" checked>
          <span>다음 순번 대기자 있음</span>
        </label>
        <label class="option">
          <input type="radio" name="waiting" value="no-response">
          <span>안내받은 대기자가 4시간 이내에 응답하지 않음</span>
        </label>
        <label class="option">
          <input type="radio" name="waiting" value="none">
          <span>남은 대기자 없음</span>
        </label>
      </fieldset>
    </section>

    <section aria-labelledby="rules-heading">
      <h2 id="rules-heading">처리 기준</h2>
      <ul>
        <li>확정된 예약을 이용 시간 24시간 전까지 취소하면 시스템이 다음 순번 대기자에게 자동으로 안내한다.</li>
        <li>안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.</li>
        <li>그 시간 안에 응답하지 않으면 그다음 대기자에게 안내가 넘어간다.</li>
        <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않는다. 총무팀이 직접 판단해 처리한다.</li>
        <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
      </ul>
    </section>

    <section aria-labelledby="reference-heading">
      <h2 id="reference-heading">참고</h2>
      <p class="note">취소 시점은 원문의 표현대로 선택한다.</p>
    </section>
  </main>

  <script>
    const mainResult = document.getElementById("result-main");
    const detailResult = document.getElementById("result-detail");

    function updateResult() {
      const cancellation = document.querySelector('input[name="cancellation"]:checked').value;
      const waiting = document.querySelector('input[name="waiting"]:checked').value;

      if (cancellation === "within") {
        mainResult.textContent = "자동 안내가 가지 않는다.";
        detailResult.textContent = waiting === "none"
          ? "총무팀이 직접 판단해 처리한다. 남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다."
          : "총무팀이 직접 판단해 처리한다.";
        return;
      }

      if (waiting === "none") {
        mainResult.textContent = "해당 시간대가 일반 예약으로 다시 열린다.";
        detailResult.textContent = "남은 대기자가 없는 경우에 적용한다.";
      } else if (waiting === "no-response") {
        mainResult.textContent = "그다음 대기자에게 안내가 넘어간다.";
        detailResult.textContent = "안내받은 대기자가 안내받은 시점부터 4시간 이내에 응답하지 않은 경우다. 남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.";
      } else {
        mainResult.textContent = "시스템이 다음 순번 대기자에게 자동으로 안내한다.";
        detailResult.textContent = "안내받은 대기자는 안내받은 시점부터 4시간 이내에 응답해야 한다.";
      }
    }

    document.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.addEventListener("change", updateResult);
    });

    updateResult();
  </script>
</body>
</html>
```