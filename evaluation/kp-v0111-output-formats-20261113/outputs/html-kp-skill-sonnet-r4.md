```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>회의실 예약 취소 처리 확인</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --line:#d5d9e0; --text:#1d2430; --muted:#566074; --accent:#1f5fbf; --warn:#9a4a00; }
  * { box-sizing:border-box; }
  body { margin:0; padding:24px 16px; background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,"Malgun Gothic",sans-serif; line-height:1.6; }
  main { max-width:760px; margin:0 auto; }
  h1 { font-size:1.4rem; margin:0 0 4px; }
  h2 { font-size:1.05rem; margin:0 0 10px; }
  .scope { margin:0 0 16px; color:var(--muted); }
  section { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; margin-bottom:14px; }
  fieldset { border:0; padding:0; margin:0 0 12px; }
  legend { font-weight:600; margin-bottom:6px; }
  label { display:block; margin:4px 0; }
  input[type=number] { width:7em; padding:6px; border:1px solid var(--line); border-radius:4px; font-size:1rem; }
  .err { color:#b00020; font-size:.9rem; min-height:1.2em; margin:4px 0 0; }
  .result { border-left:4px solid var(--accent); }
  .result .main { font-size:1.1rem; font-weight:700; margin:0 0 8px; }
  .result ul { margin:6px 0 0; padding-left:20px; }
  .warn { color:var(--warn); }
  button { padding:8px 16px; border:1px solid var(--accent); background:#fff; color:var(--accent); border-radius:6px; font-size:1rem; cursor:pointer; }
  table { width:100%; border-collapse:collapse; }
  th,td { border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
  @media (max-width:320px) { body { padding:12px 8px; } input[type=number] { width:100%; } }
</style>
</head>
<body>
<main>
  <h1>예약 취소 시점과 대기자 상황에 따라 처리 방식을 확인한다.</h1>
  <p class="scope">대상: 회의실 예약 취소 처리. 예약이 확정된 이용자가 취소하는 경우에 해당한다.</p>

  <section class="result" aria-labelledby="rh">
    <h2 id="rh">결과</h2>
    <div id="result" aria-live="polite"></div>
  </section>

  <section aria-labelledby="ih">
    <h2 id="ih">입력</h2>
    <fieldset>
      <legend>취소 시점</legend>
      <label><input type="radio" name="timing" value="before" checked> 이용 시간 24시간 전까지 취소</label>
      <label><input type="radio" name="timing" value="within"> 이용 24시간 이내에 취소</label>
    </fieldset>
    <fieldset>
      <legend>대기자</legend>
      <label><input type="radio" name="waiting" value="yes" checked> 대기자가 있다</label>
      <label><input type="radio" name="waiting" value="no"> 남은 대기자가 없다</label>
    </fieldset>
    <fieldset>
      <legend>안내를 받은 대기자의 응답</legend>
      <label><input type="radio" name="reply" value="in" checked> 4시간 이내에 응답했다</label>
      <label><input type="radio" name="reply" value="out"> 4시간 안에 응답하지 않았다</label>
    </fieldset>
    <div>
      <label for="elapsed">안내 후 경과 시간(시간, 가정)</label>
      <input type="number" id="elapsed" name="elapsed" min="0" step="0.5" value="0">
      <p class="err" id="elapsedErr"></p>
    </div>
    <button type="button" id="resetBtn">초기화</button>
  </section>

  <section aria-labelledby="rlh">
    <h2 id="rlh">규칙·산출식</h2>
    <table>
      <thead><tr><th>조건</th><th>처리</th></tr></thead>
      <tbody>
        <tr><td>이용 시간 24시간 전까지 취소</td><td>시스템이 자동으로 대기자 명단의 다음 순번에게 안내를 보낸다.</td></tr>
        <tr><td>안내받은 대기자가 안내 시점으로부터 4시간 이내에 응답하지 않음</td><td>그다음 대기자에게 안내가 넘어간다.</td></tr>
        <tr><td>이용 24시간 이내에 취소</td><td>자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.</td></tr>
        <tr><td>남은 대기자가 없음</td><td>해당 시간대가 일반 예약으로 다시 열린다.</td></tr>
      </tbody>
    </table>
  </section>

  <section aria-labelledby="nh">
    <h2 id="nh">참고</h2>
    <p>경과 시간 입력은 4시간 기준과 비교하기 위한 가정 값이며 원문에 없는 값이다.</p>
  </section>
</main>

<script>
(function () {
  var resultEl = document.getElementById('result');
  var elapsed = document.getElementById('elapsed');
  var errEl = document.getElementById('elapsedErr');

  function val(name) {
    return document.querySelector('input[name="' + name + '"]:checked').value;
  }
  function add(parent, tag, text, cls) {
    var e = document.createElement(tag);
    e.textContent = text;
    if (cls) { e.className = cls; }
    parent.appendChild(e);
    return e;
  }

  function render() {
    var t = val('timing'), w = val('waiting'), r = val('reply');
    var h = parseFloat(elapsed.value);
    resultEl.textContent = '';
    errEl.textContent = '';
    if (elapsed.value === '' || isNaN(h) || h < 0) {
      errEl.textContent = '0 이상의 숫자를 입력한다.';
      add(resultEl, 'p', '입력 오류로 결과를 보류한다.', 'warn');
      return;
    }
    if (t === 'within') {
      add(resultEl, 'p', '자동 안내가 가지 않는다. 총무팀이 직접 판단해서 처리한다.', 'main');
      if (w === 'no') {
        var ul0 = document.createElement('ul');
        add(ul0, 'li', '남은 대기자가 없는 경우 해당 시간대가 일반 예약으로 다시 열린다는 규칙이 있다. 24시간 이내 취소에 이 규칙이 적용되는지는 제공된 자료에 없다.', 'warn');
        resultEl.appendChild(ul0);
      }
      return;
    }
    if (w === 'no') {
      add(resultEl, 'p', '해당 시간대가 일반 예약으로 다시 열린다.', 'main');
      return;
    }
    var ul = document.createElement('ul');
    if (r === 'in') {
      add(resultEl, 'p', '시스템이 다음 순번 대기자에게 안내를 보냈고 대기자가 4시간 이내에 응답했다.', 'main');
    } else {
      add(resultEl, 'p', '그다음 대기자에게 안내가 넘어간다.', 'main');
    }
    resultEl.appendChild(ul);
    if (r === 'in' && h > 4) {
      add(ul, 'li', '입력한 경과 시간 ' + h + '시간은 4시간을 넘는다. 응답 여부 선택과 맞는지 확인한다.', 'warn');
    }
    if (r === 'out' && h < 4) {
      add(ul, 'li', '입력한 경과 시간 ' + h + '시간은 4시간 미만이다. 응답 기한은 안내 시점으로부터 4시간 이내다.', 'warn');
    }
    add(ul, 'li', '응답 기한: 안내를 받은 시점으로부터 4시간 이내.');
    add(ul, 'li', '남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.');
  }

  var inputs = document.querySelectorAll('input');
  for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener('input', render);
    inputs[i].addEventListener('change', render);
  }
  document.getElementById('resetBtn').addEventListener('click', function () {
    document.querySelector('input[name="timing"][value="before"]').checked = true;
    document.querySelector('input[name="waiting"][value="yes"]').checked = true;
    document.querySelector('input[name="reply"][value="in"]').checked = true;
    elapsed.value = '0';
    render();
  });
  render();
})();
</script>
</body>
</html>
```