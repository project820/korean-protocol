```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회의실 예약 취소</title>
  <style>
    body {
      font-family: sans-serif;
      line-height: 1.6;
      max-width: 40rem;
      margin: 2rem auto;
      padding: 0 1rem;
      color: #1a1a1a;
    }
    h1 { font-size: 1.5rem; }
    h2 { font-size: 1.15rem; margin-top: 1.75rem; }
    p { margin: 0.65rem 0; }
  </style>
</head>
<body>
  <h1>회의실 예약 취소</h1>

  <h2>이용 시간 24시간 전까지 취소</h2>
  <p>확정 예약자가 이용 시간 24시간 전까지 예약을 취소하면, 시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보낸다.</p>
  <p>안내를 받은 대기자는 안내를 받은 시점부터 4시간 이내에 응답해야 한다.</p>
  <p>대기자가 그 시간 안에 응답하지 않으면, 안내가 그다음 대기자에게 넘어간다.</p>

  <h2>이용 시간 24시간 이내에 취소</h2>
  <p>확정 예약자가 이용 시간 24시간 이내에 예약을 취소하면, 자동 안내가 가지 않는다.</p>
  <p>이 경우 총무팀이 직접 판단해서 처리한다.</p>

  <h2>남은 대기자가 없는 경우</h2>
  <p>남은 대기자가 없으면, 해당 시간대가 일반 예약으로 다시 열린다.</p>
</body>
</html>
```