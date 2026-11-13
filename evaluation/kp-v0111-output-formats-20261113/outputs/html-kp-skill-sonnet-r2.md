```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>회의실 예약 취소 처리 확인</title>
<style>
  body { margin: 0; font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; background: #f5f7fa; color: #1c2430; line-height: 1.6; }
  main { max-width: 860px; margin: 0 auto; padding: 24px 16px; }
  h1 { font-size: 1.5rem; margin: 0 0 8px; }
  h2 { font-size: 1.1rem; margin: 0 0 12px; }
  .scope { margin: 0 0 20px; color: #4a5568; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  section { background: #fff; border: 1px solid #d5dbe3; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
  .field { margin-bottom: 14px; }
  .field > label, fieldset legend { display: block; font-weight: bold; margin-bottom: 4px; }
  fieldset { border: 0; padding: 0; margin: 0 0 14px; }
  fieldset label { display: block; font-weight: normal; }
  input[type="number"], select { width: 100%; padding: 8px; font-size: 1rem; border: 1px solid #aab4c2; border-radius: 4px; box-sizing: border-box; }
  .error { color: #b00020; font-size: 0.9rem; min-height: 1.2em; margin: 4px 0 0; }
  #result { border-left: 6px solid #2b6cb0; }
  #result .verdict { font-weight: bold; font-size: 1.15rem; margin: 0 0 8px; }
  #result ul { margin: 8px 0 0; padding-left: 20px; }
  button { padding: 8px 16px; font-size: 1rem; border: 1px solid #2b6cb0; background: #fff; color: #2b6cb0; border-radius: 4px; cursor: pointer; }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid #f6ad55; outline-offset: 1px; }
  ol, ul.notes { margin: 0; padding-left: 20px; }
  code { background: #edf2f7; padding: 1px 4px; border-radius: 3px; }
  @media (max-width: 320px), (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<main>
  <h1>취소 시점과 대기자 수에 따라 취소 처리 방식을 확인한다.</h1>
  <p class="scope">대상: 확정된 회의실 예약의 취소</p>

  <section id="result" aria-labelledby="rh">
    <h2 id="rh">결과</h2>
    <div id="out" aria-live="polite"></div>
  </section>

  <section aria-labelledby="ih">
    <h2 id="ih">입력</h2>
    <form id="form" onsubmit="return false" novalidate>
      <div class="field">
        <label for="hours">취소 시점 (이용 시작까지 남은 시간, 단위: 시간)</label>
        <input type="number" id="hours" name="hours" min="0" step="any" value="30">
        <p class="error" id="hoursErr"></p>
      </div>
      <div class="field">
        <label for="waiters">대기자 수 (명)</label>
        <input type="number" id="waiters" name="waiters" min="0" step="1" value="2">
        <p class="error" id="waitersErr"></p>
      </div>
      <fieldset>
        <legend>현재 안내받은 대기자의 응답</legend>
        <label><input type="radio" name="resp" value="yes"> 4시간 이내에 응답했다</label>
        <label><input type="radio" name="resp" value="no" checked> 4시간 이내에 응답하지 않았다</label>
      </fieldset>
      <button type="button" id="resetBtn">초기화</button>
    </form>
  </section>

  <section aria-labelledby="rlh">
    <h2 id="rlh">규칙</h2>
    <ol>
      <li>이용 시간 24시간 전까지 취소하면 시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.</li>
      <li>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</li>
      <li>그 시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.</li>
      <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않고 총무팀이 직접 판단해서 처리한다.</li>
      <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
    </ol>
  </section>

  <section aria-labelledby="nh">
    <h2 id="nh">참고</h2>
    <ul class="notes">
      <li>정확히 24시간 남은 취소는 "24시간 전까지"에 해당하는 것으로 계산했다. 이는 가정이다.</li>
      <li>원문은 응답한 대기자의 후속 처리를 밝히지 않는다. 응답한 경우 이 화면은 후속 처리를 표시하지 않는다.</li>
      <li>원문은 이용 24시간 이내 취소 때 남은 대기자가 없는 경우의 처리를 밝히지 않는다.</li>
    </ul>
  </section>
</main>

<script>
(function () {
  var hours = document.getElementById("hours");
  var waiters = document.getElementById("waiters");
  var hoursErr = document.getElementById("hoursErr");
  var waitersErr = document.getElementById("waitersErr");
  var out = document.getElementById("out");
  var radios = document.querySelectorAll('input[name="resp"]');

  function add(parent, tag, text, cls) {
    var el = document.createElement(tag);
    el.textContent = text;
    if (cls) el.className = cls;
    parent.appendChild(el);
    return el;
  }

  function render() {
    var h = hours.value.trim() === "" ? NaN : Number(hours.value);
    var w = waiters.value.trim() === "" ? NaN : Number(waiters.value);
    var ok = true;
    hoursErr.textContent = "";
    waitersErr.textContent = "";
    if (!isFinite(h) || h < 0) { hoursErr.textContent = "0 이상의 숫자를 입력한다."; ok = false; }
    if (!isFinite(w) || w < 0 || Math.floor(w) !== w) { waitersErr.textContent = "0 이상의 정수를 입력한다."; ok = false; }
    out.textContent = "";
    if (!ok) { add(out, "p", "입력 오류를 고칠 때까지 결과를 보류한다."); return; }

    var resp = document.querySelector('input[name="resp"]:checked').value;
    var list = document.createElement("ul");

    if (h >= 24) {
      add(out, "p", "시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.", "verdict");
      if (w === 0) {
        add(list, "li", "남은 대기자가 없으므로 해당 시간대가 일반 예약으로 다시 열린다.");
      } else {
        add(list, "li", "안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.");
        if (resp === "no") {
          if (w > 1) {
            add(list, "li", "응답하지 않으면 안내가 그다음 대기자에게 넘어간다. 남은 대기자는 " + (w - 1) + "명이다.");
          } else {
            add(list, "li", "응답하지 않으면 안내가 그다음 대기자에게 넘어간다. 이 대기자 뒤에 남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.");
          }
        } else {
          add(list, "li", "응답한 경우의 후속 처리는 원문에 없다.");
        }
      }
    } else {
      add(out, "p", "자동 안내가 가지 않고 총무팀이 직접 판단해서 처리한다.", "verdict");
      add(list, "li", "이용 24시간 이내 취소에 해당한다.");
      if (w === 0) add(list, "li", "대기자가 없는 경우의 처리는 원문에 없다.");
    }
    out.appendChild(list);
  }

  hours.addEventListener("input", render);
  waiters.addEventListener("input", render);
  for (var i = 0; i < radios.length; i++) radios[i].addEventListener("change", render);

  document.getElementById("resetBtn").addEventListener("click", function () {
    hours.value = "30";
    waiters.value = "2";
    document.querySelector('input[name="resp"][value="no"]').checked = true;
    render();
  });

  render();
})();
</script>
</body>
</html>
```