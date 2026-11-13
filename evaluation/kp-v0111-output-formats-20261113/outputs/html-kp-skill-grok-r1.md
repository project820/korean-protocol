```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>회의실 예약 취소의 처리를 확인한다</title>
<style>
  :root {
    color-scheme: light;
    --bg: #f6f5f2;
    --ink: #1c1c1c;
    --muted: #3f3f3f;
    --line: #ddd8cf;
    --panel: #ffffff;
    --accent: #1e2a32;
    --focus: #1e4d8c;
    --error: #8d1d1d;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
    font-size: 16px;
    line-height: 1.55;
  }

  main {
    max-width: 40rem;
    margin: 0 auto;
    padding: 24px 16px 48px;
  }

  h1 {
    margin: 0;
    font-size: 1.35rem;
    line-height: 1.4;
    font-weight: 700;
  }

  h2 {
    margin: 0 0 12px;
    font-size: 1rem;
    font-weight: 700;
  }

  .scope {
    margin: 8px 0 0;
    color: var(--muted);
  }

  section { margin-top: 28px; }

  #result-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px;
  }

  .result-line { margin: 0 0 8px; }
  .result-line:last-child { margin-bottom: 0; }

  .field-status {
    margin: 0 0 6px;
    font-size: 0.92rem;
  }

  fieldset {
    margin: 0 0 12px;
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
  }

  fieldset:disabled { opacity: 0.55; }

  legend {
    padding: 0 4px;
    font-weight: 700;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
  }

  input[type="radio"] {
    width: 1.1rem;
    height: 1.1rem;
    margin: 0;
  }

  button {
    margin-top: 4px;
    padding: 8px 14px;
    border: 0;
    border-radius: 6px;
    background: var(--accent);
    color: #fff;
    font: inherit;
    cursor: pointer;
  }

  button:focus-visible,
  input:focus-visible {
    outline: 2px solid var(--focus);
    outline-offset: 2px;
  }

  .error {
    margin: 0 0 12px;
    color: var(--error);
  }

  .error:empty { display: none; }

  ul {
    margin: 0;
    padding-left: 1.2rem;
  }

  li { margin: 0 0 10px; }

  .note { margin: 0 0 8px; }
  .note:last-child { margin-bottom: 0; }

  @media (max-width: 320px) {
    main { padding: 12px 10px 32px; }
    h1 { font-size: 1.15rem; }
  }
</style>
</head>
<body>
<main>
  <h1>회의실 예약 취소의 처리를 확인한다</h1>
  <p class="scope">범위는 확정 예약의 취소와 대기자 안내다.</p>

  <section id="result-panel">
    <h2>결과</h2>
    <div id="result-body" aria-live="polite"></div>
  </section>

  <section>
    <h2>입력</h2>
    <form id="rule-form">
      <fieldset aria-describedby="cancel-error">
        <legend>취소 시점</legend>
        <label for="cancel-before">
          <input id="cancel-before" type="radio" name="cancel-time" value="before" checked>
          이용 24시간 전까지
        </label>
        <label for="cancel-within">
          <input id="cancel-within" type="radio" name="cancel-time" value="within">
          이용 24시간 이내
        </label>
      </fieldset>
      <p id="cancel-error" class="error"></p>

      <fieldset aria-describedby="wait-error">
        <legend>대기자</legend>
        <label for="wait-next">
          <input id="wait-next" type="radio" name="waitlist" value="next" checked>
          다음 순번이 있다
        </label>
        <label for="wait-none">
          <input id="wait-none" type="radio" name="waitlist" value="none">
          남은 대기자가 없다
        </label>
      </fieldset>
      <p id="wait-error" class="error"></p>

      <p class="field-status"><strong>입력 상태:</strong> <span id="reply-status">적용</span></p>
      <fieldset id="reply-set" aria-describedby="reply-error">
        <legend>안내 후 응답</legend>
        <label for="reply-in-time">
          <input id="reply-in-time" type="radio" name="reply" value="in-time" checked>
          4시간 이내 응답
        </label>
        <label for="reply-late">
          <input id="reply-late" type="radio" name="reply" value="late">
          4시간 이내 미응답
        </label>
      </fieldset>
      <p id="reply-error" class="error"></p>

      <button type="button" id="restore-initial" name="restore-initial">초기값</button>
    </form>
  </section>

  <section>
    <h2>규칙</h2>
    <ul>
      <li><strong>24시간 전 취소:</strong> 확정 예약자가 이용 24시간 전까지 취소하면 시스템이 다음 순번에게 안내를 보낸다.</li>
      <li><strong>응답 기한:</strong> 안내를 받은 대기자는 안내 시점부터 4시간 이내에 응답해야 한다.</li>
      <li><strong>미응답:</strong> 그 시간 안에 응답이 없으면 안내가 그다음 대기자에게 넘어간다.</li>
      <li><strong>24시간 이내 취소:</strong> 자동 안내를 보내지 않는다.</li>
      <li><strong>총무팀 처리:</strong> 이용 24시간 이내 취소는 총무팀이 직접 판단해서 처리한다.</li>
      <li><strong>대기자 없음:</strong> 남은 대기자가 없으면 해당 시간대는 일반 예약으로 다시 열린다.</li>
    </ul>
  </section>

  <section>
    <h2>참고</h2>
    <p class="note">24시간 기준점은 이용 시각이다.</p>
    <p class="note">4시간 기준점은 안내를 받은 시각이다.</p>
  </section>
</main>
<script>
(function () {
  var form = document.getElementById("rule-form");
  var resultBody = document.getElementById("result-body");
  var replySet = document.getElementById("reply-set");
  var replyStatus = document.getElementById("reply-status");
  var initial = {
    "cancel-time": "before",
    "waitlist": "next",
    "reply": "in-time"
  };

  function selected(name) {
    var node = form.querySelector('input[name="' + name + '"]:checked');
    return node ? node.value : "";
  }

  function setError(id, text) {
    document.getElementById(id).textContent = text;
  }

  function addLine(label, text) {
    var p = document.createElement("p");
    var strong = document.createElement("strong");
    p.className = "result-line";
    strong.textContent = label;
    p.appendChild(strong);
    p.appendChild(document.createTextNode(" " + text));
    resultBody.appendChild(p);
  }

  function clearResult() {
    while (resultBody.firstChild) {
      resultBody.removeChild(resultBody.firstChild);
    }
  }

  function render() {
    var cancel = selected("cancel-time");
    var wait = selected("waitlist");
    var reply = selected("reply");
    var replyApplies = cancel === "before" && wait === "next";
    var valid = true;

    replySet.disabled = !replyApplies;
    replyStatus.textContent = replyApplies ? "적용" : "미적용";

    if (!cancel) {
      setError("cancel-error", "취소 시점을 고르지 않았다.");
      valid = false;
    } else {
      setError("cancel-error", "");
    }

    if (!wait) {
      setError("wait-error", "대기자를 고르지 않았다.");
      valid = false;
    } else {
      setError("wait-error", "");
    }

    if (replyApplies && !reply) {
      setError("reply-error", "응답 여부를 고르지 않았다.");
      valid = false;
    } else {
      setError("reply-error", "");
    }

    clearResult();
    if (!valid) {
      return;
    }

    if (cancel === "within") {
      addLine("조건:", "취소 시점은 이용 24시간 이내다.");
      addLine("처리:", "자동 안내를 보내지 않는다.");
      addLine("처리:", "총무팀이 직접 판단해서 처리한다.");
      if (wait === "none") {
        addLine("조건:", "남은 대기자가 없다.");
        addLine("처리:", "해당 시간대는 일반 예약으로 다시 열린다.");
      }
      return;
    }

    if (wait === "none") {
      addLine("조건:", "남은 대기자가 없다.");
      addLine("처리:", "해당 시간대는 일반 예약으로 다시 열린다.");
      return;
    }

    addLine("조건:", "이용 24시간 전까지 취소다.");
    addLine("조건:", "대기자 명단에 다음 순번이 있다.");
    addLine("처리:", "시스템이 대기자 명단의 다음 순번에게 안내를 보낸다.");
    addLine("조건:", "응답 기한은 안내를 받은 시점부터 4시간이다.");

    if (reply === "in-time") {
      addLine("상태:", "4시간 이내 응답이다.");
      return;
    }

    addLine("조건:", "4시간 이내에 응답이 없다.");
    addLine("처리:", "안내가 그다음 대기자에게 넘어간다.");
  }

  form.addEventListener("change", render);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
  });

  document.getElementById("restore-initial").addEventListener("click", function () {
    var names = Object.keys(initial);
    var i;
    for (i = 0; i < names.length; i += 1) {
      var input = form.querySelector(
        'input[name="' + names[i] + '"][value="' + initial[names[i]] + '"]'
      );
      if (input) {
        input.checked = true;
      }
    }
    render();
  });

  render();
})();
</script>
</body>
</html>
```