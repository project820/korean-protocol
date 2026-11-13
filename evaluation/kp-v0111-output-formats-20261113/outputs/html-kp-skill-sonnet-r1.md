```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>회의실 예약 취소 처리 확인</title>
<style>
  body { font-family: sans-serif; background: #f7f8fa; color: #1c2330; margin: 0; padding: 16px; line-height: 1.6; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  h2 { font-size: 1.05rem; margin: 0 0 8px; }
  .scope { margin: 0 0 16px; color: #4a5568; }
  section { background: #fff; border: 1px solid #d5dae1; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; }
  .field { margin-bottom: 12px; }
  .field > label, .field > .legend { display: block; font-weight: bold; margin-bottom: 4px; }
  .opt { display: block; font-weight: normal; margin: 2px 0; }
  input[type="number"] { width: 8em; padding: 6px; font-size: 1rem; }
  .error { color: #b42318; font-size: 0.9rem; margin: 4px 0 0; min-height: 1em; }
  #result { border-color: #2b6cb0; }
  #verdict { font-weight: bold; margin: 0 0 8px; }
  ul { margin: 6px 0; padding-left: 20px; }
  button { padding: 8px 14px; font-size: 1rem; }
  @media (max-width: 320px) { body { padding: 8px; } section { padding: 10px; } }
</style>
</head>
<body>
<main>
  <h1>예약 취소 시점에 따라 처리 방식을 확인한다.</h1>
  <p class="scope">대상: 확정된 회의실 예약의 취소</p>

  <section id="result" aria-labelledby="rh">
    <h2 id="rh">결과</h2>
    <div aria-live="polite">
      <p id="verdict"></p>
      <ul id="details"></ul>
    </div>
  </section>

  <section aria-labelledby="ih">
    <h2 id="ih">입력</h2>
    <div class="field">
      <label for="hours">이용 시작까지 남은 시간(시간 단위)</label>
      <input type="number" id="hours" name="hours" min="0" step="any" value="30">
      <p class="error" id="hoursError"></p>
    </div>
    <div class="field">
      <span class="legend" id="wlabel">남은 대기자</span>
      <div role="radiogroup" aria-labelledby="wlabel">
        <label class="opt"><input type="radio" name="waiter" value="yes" checked> 있다</label>
        <label class="opt"><input type="radio" name="waiter" value="no"> 없다</label>
      </div>
    </div>
    <button type="button" id="resetBtn">초기화</button>
  </section>

  <section aria-labelledby="rlh">
    <h2 id="rlh">규칙·산출식</h2>
    <ul>
      <li>취소 시점이 이용 24시간 전까지이면 시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</li>
      <li>안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.</li>
      <li>그 시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.</li>
      <li>이용 24시간 이내에 취소하면 자동 안내가 가지 않고 총무팀이 직접 판단해 처리한다.</li>
      <li>남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.</li>
    </ul>
  </section>

  <section aria-labelledby="nh">
    <h2 id="nh">참고</h2>
    <p>원문은 정확히 24시간인 시점이 어느 쪽인지 밝히지 않는다. 이 화면은 24시간을 "24시간 전까지"로 처리한다. (가정)</p>
    <p>원문은 이용 24시간 이내 취소 때 대기자 유무에 따른 처리를 밝히지 않는다.</p>
  </section>
</main>

<script>
(function () {
  var hoursEl = document.getElementById('hours');
  var errEl = document.getElementById('hoursError');
  var verdict = document.getElementById('verdict');
  var details = document.getElementById('details');
  var INITIAL = '30';

  function add(text) {
    var li = document.createElement('li');
    li.textContent = text;
    details.appendChild(li);
  }

  function render() {
    details.textContent = '';
    var raw = hoursEl.value.trim();
    var h = Number(raw);
    if (raw === '' || isNaN(h) || h < 0) {
      errEl.textContent = '0 이상의 숫자를 입력한다.';
      verdict.textContent = '입력을 바로잡을 때까지 결과를 보류한다.';
      return;
    }
    errEl.textContent = '';
    var waiter = document.querySelector('input[name="waiter"]:checked').value;

    if (h >= 24) {
      verdict.textContent = '시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.';
      if (waiter === 'yes') {
        add('안내를 받은 대기자는 안내를 받은 시점으로부터 4시간 이내에 응답해야 한다.');
        add('4시간 안에 응답하지 않으면 안내가 그다음 대기자에게 넘어간다.');
        add('남은 대기자가 없어지면 해당 시간대가 일반 예약으로 다시 열린다.');
      } else {
        add('남은 대기자가 없으므로 해당 시간대가 일반 예약으로 다시 열린다.');
      }
    } else {
      verdict.textContent = '자동 안내가 가지 않고 총무팀이 직접 판단해 처리한다.';
      add('이용 24시간 이내 취소이다.');
      if (waiter === 'no') {
        add('남은 대기자가 없으면 해당 시간대가 일반 예약으로 다시 열린다.');
      }
    }
  }

  hoursEl.addEventListener('input', render);
  var radios = document.querySelectorAll('input[name="waiter"]');
  for (var i = 0; i < radios.length; i++) radios[i].addEventListener('change', render);
  document.getElementById('resetBtn').addEventListener('click', function () {
    hoursEl.value = INITIAL;
    document.querySelector('input[name="waiter"][value="yes"]').checked = true;
    render();
  });
  render();
})();
</script>
</body>
</html>
```