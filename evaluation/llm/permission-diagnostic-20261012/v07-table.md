# Exact v07 outputs — reused-input diagnostic

Read each response in context; grammar alone does not determine its semantic rating.

Facts: 스냅샷 생성은 큐 길이가 20개 이하이고 활성 작업이 0개일 때만 허용한다. / 두 조건 중 하나만 만족하면 생성하면 안 된다.

Request: 스냅샷 생성 조건을 담당자에게 알려라.

| Repetition | Requested model | Condition | Exit | Exact text |
|---|---|---|---:|---|
| 1 | gpt-6.1-sol | baseline | 0 | 큐 길이가 20개 이하이고 활성 작업이 0개인 두 조건을 모두 만족할 때만 스냅샷을 생성하세요. 하나만 만족하면 생성하면 안 됩니다. |
| 1 | gpt-6.1-sol | treatment | 0 | 큐 길이가 20개 이하이고 활성 작업이 0개인 경우에만 스냅샷을 생성하세요. 두 조건 중 하나만 만족하면 생성하면 안 됩니다. |
| 2 | gpt-6.1-sol | baseline | 0 | 스냅샷은 큐 길이가 20개 이하이고 활성 작업이 0개일 때만 생성할 수 있습니다. 두 조건을 모두 만족해야 합니다. |
| 2 | gpt-6.1-sol | treatment | 0 | 큐 길이가 20개 이하이고 활성 작업이 0개일 때만 스냅샷을 생성할 수 있습니다. 두 조건 중 하나만 만족하면 생성하면 안 됩니다. |
