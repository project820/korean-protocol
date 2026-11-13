```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회의실 예약 취소 안내</title>
  <style>
    body {
      margin: 0;
      color: #202124;
      background: #f5f6f8;
      font-family: system-ui, sans-serif;
      line-height: 1.7;
    }
    main {
      box-sizing: border-box;
      max-width: 760px;
      margin: 40px auto;
      padding: 32px;
      background: #fff;
      border-radius: 12px;
    }
    h1 {
      margin-top: 0;
      font-size: 1.8rem;
    }
    h2 {
      margin-top: 28px;
      font-size: 1.2rem;
    }
    li {
      margin: 8px 0;
    }
    @media (max-width: 600px) {
      main {
        margin: 0;
        padding: 24px;
        border-radius: 0;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>회의실 예약 취소 안내</h1>

    <section aria-labelledby="early-cancellation">
      <h2 id="early-cancellation">이용 시간 24시간 전까지 취소하는 경우</h2>
      <p>예약이 확정된 사람이 이용 시간 24시간 전까지 예약을 취소하면, 시스템이 대기자 명단의 다음 순번에게 자동으로 안내를 보냅니다.</p>
      <ul>
        <li>안내를 받은 대기자는 안내를 받은 시점부터 4시간 이내에 응답하세요.</li>
        <li>4시간 이내에 응답하지 않으면, 시스템이 그다음 대기자에게 안내를 보냅니다.</li>
      </ul>
    </section>

    <section aria-labelledby="late-cancellation">
      <h2 id="late-cancellation">이용 시간 24시간 이내에 취소하는 경우</h2>
      <p>시스템은 자동 안내를 보내지 않습니다.</p>
      <p>총무팀이 직접 판단해서 처리합니다.</p>
    </section>

    <section aria-labelledby="no-waiting">
      <h2 id="no-waiting">남은 대기자가 없는 경우</h2>
      <p>해당 시간대가 일반 예약으로 다시 열립니다.</p>
    </section>
  </main>
</body>
</html>
```