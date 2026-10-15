# 비공개 완료 보고서로 규약 입력을 비교한다

[run.py](run.py)는 비공개 원문 하나에 기존 r2 프로필과 새 실험 스킬을 각각 두 번 적용하는 개발용 러너다. 같은 원문·공통 요청·모델 설정을 사용하며, 생성 전 기준과 입력 해시를 고정한다. 이미 검토한 개발 사례를 사용하므로 결과를 보지 않은 홀드아웃 시험이 아니다.

공개 저장소에는 러너와 일반 절차만 둔다. 원문, 주장 목록, 원문별 판정 기준, 토큰 측정 자료, 요청·응답·출력과 평가 기록은 모두 비공개로 보관하며 커밋하거나 공개 예문에 복사하지 않는다. 공개 예문 6개의 과거 r2 결과를 이 실험 스킬의 통과 결과로 사용하지 않는다.

## 원문과 기준을 먼저 준비한다

저장소 루트에서 새 `output/<비공개 이름>` 하위 폴더를 사용하거나, 저장소 밖의 시스템 임시 디렉터리를 사용한다. 러너는 다른 저장소 내부 경로를 거부하고 기존 실험 기록을 덮어쓰지 않는다. `output/`의 Git 제외 여부를 확인하며, 제외 설정은 자료의 외부 공유를 막는 접근 제어가 아니다.

생성 전에 다음 파일을 비공개 실험 폴더에 준비한다.

- `source.md`에는 수정하지 않은 원문을 둔다.
- `claim-ledger.json`에는 원문의 독립 주장, 조건·수치·시간·행위자·의무 강도, 식별자와 출처의 대응을 기록한다.
- `criteria.json`에는 의미 보존과 구조 기준을 고정한다.
- `token-budget.json`에는 전체 스킬 해시, 규약 토큰 계수, 원문 토큰 계수와 실제 최소 요청의 증거를 기록한다.

의미 검사는 원문에서 출력으로, 출력에서 원문으로 양방향 대조한다. 원문에서 확인하지 못한 사실은 확인된 사실로 바꾸지 않는다. 원문 자체의 미검증 주장이나 충돌은 유지하고, 검토자의 감사 주석은 변환 출력과 분리한다.

구조 검사는 완료 결과와 사용에 필요한 운영·노출 조건을 기능·설계 상세보다 앞에 배치했는지 확인한다. 독립적으로 비교할 속성은 별도 항목·행·표의 셀로 찾을 수 있어야 한다. 선행 조건, 실제 순서, 선택적 보조 수단과 사후 조치를 한 필수 절차로 섞지 않는다. 의미 보존만으로 구조 검사를 통과하지 않는다.

## 규약과 공통 요청문의 토큰을 측정한다

**6,000토큰 상한은 후보 스킬 전체와 공통 요청문에 적용한다.** 러너의 `core_prompt()`로 만드는 문자열을 로컬 계수기로 측정하며, 원문은 `source_tokens`에 따로 기록한다. 원문까지 포함한 실제 생성 요청의 `usage.input_tokens`도 보존하지만 이 규약 전용 상한을 전체 요청의 상한으로 바꾸지 않는다.

`probe`는 별도 CLI 하위 명령이 아니다. `probe_request()`로 원문 없는 최소 요청을 만들고 실제 응답을 보관하는 사전 단계다. 전체 스킬의 메타데이터를 포함하며, 짧게 발췌한 규칙으로 계수하지 않는다.

아래 예시는 비공개 파일 이름만 사용한다. 원문·판정 기준은 앞 단계에서 준비하며, 로컬 OpenCodex 경로가 설정된 환경에서 실행한다.

```sh
export KP_STUDY_DIR=output/private-study
export KP_CANDIDATE=skills/korean-protocol/SKILL.md
python3 - <<'PY'
import importlib.util
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location('study', 'evaluation/field-report-20261015/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
study = runner.validate_study_dir(Path(os.environ['KP_STUDY_DIR']))
probe = study / 'token-probe'
probe.mkdir(mode=0o700)
request = runner.probe_request(Path(os.environ['KP_CANDIDATE']).read_bytes(),
                               'anthropic/claude-opus-5-5', 'medium')
runner.write(probe / 'request.json', request)
with (probe / 'response.raw').open('xb') as raw:
    runner.transfer(runner.frozen.old.ENDPOINT, request, raw, {}, 600)
PY
```

이 단계는 실제 모델 요청 한 건을 보낸다. 요청 모델은 **Opus 5.5의 `anthropic/claude-opus-5-5`**, 요청 추론 강도는 **`medium`**으로 기록한다. 반환 모델 식별자가 다르거나 반환 강도가 다른 값이면 거부한다. 응답에 강도 필드가 없으면 `requested_effort: medium`, `returned_effort: null`, `effort_verification: unverified`로 구분하며 실제 medium 수행을 검증했다고 쓰지 않는다. 응답에 표시된 모델명도 상위 제공자의 실제 실행 모델을 독립적으로 증명하지 않는다.

`token-budget.json`은 다음 필드를 사용한다. 계수와 해시는 실제 파일과 실제 응답에서 산출하며 예시 값을 실측값으로 채우지 않는다.

| 필드 | 기록할 값 |
| --- | --- |
| `profile_sha256` | 후보 스킬 전체 바이트의 SHA-256을 기록한다. |
| `ceiling` | 규약 예산 `6000`을 기록한다. |
| `counters` | 계수기 이름별 `core_prompt()` 토큰 수를 기록하며 모두 상한을 지켜야 한다. |
| `source_tokens` | 계수기 이름별 원문 토큰 수를 별도로 기록한다. |
| `model_probe.profile_sha256` | 같은 후보 스킬 해시를 기록한다. |
| `model_probe.model_requested`, `effort` | 각각 요청 모델과 요청 강도를 기록한다. |
| `model_probe.request_file`, `response_file` | 실험 폴더 안의 실제 최소 요청·원시 응답 상대 경로를 기록한다. |
| `model_probe.request_sha256`, `response_sha256` | 해당 두 파일의 해시를 기록한다. |

러너는 최소 요청 바이트를 다시 구성해 대조하고 실제 응답의 `usage.input_tokens`가 6,000 이내인지 검사한다. 이 검사는 규약 예산을 확인하며 원문 토큰을 숨기지 않는다.

## 입력을 고정하고 한 번 실행한다

```sh
python3 evaluation/field-report-20261015/run.py prepare \
  --study-dir "$KP_STUDY_DIR" --candidate "$KP_CANDIDATE" \
  --model anthropic/claude-opus-5-5 --effort medium
python3 evaluation/field-report-20261015/run.py run \
  --study-dir "$KP_STUDY_DIR"
```

`prepare`는 원문·기준·주장 목록·토큰 증거·두 규약과 러너 해시를 고정하고 요청 네 건을 만든다. 이 명령은 생성 요청을 보내지 않으며, 사전 최소 요청 증거가 이미 있어야 한다. `baseline`은 고정된 r2 프로필이고 `candidate`는 전달한 전체 스킬이다.

`run`은 각 조건 두 번씩 총 네 건을 보내며 최대 동시 요청은 두 건이다. 각 요청에는 원문 하나와 규약 하나 및 같은 공통 요청만 넣으며, 판정 기준·주장 목록·이전 답안·대화 이력은 넣지 않는다. 도구를 제공하지 않고 `store: false`로 요청하지만, 이 설정을 전체 중계 경로의 무보관 증명으로 사용하지 않는다.

요청별 전송 제한은 총 600초이며 자동 재시도는 하지 않는다. 실패·중단·식별자 불일치의 원시 응답과 가능한 종료 텍스트도 남긴다. 실패 기록을 성공 출력으로 교체하거나 같은 폴더에서 다시 생성하지 않는다. 새 실행은 별도 폴더와 실행 기록으로 구분한다.

## 원시 출력을 바꾸지 않고 검증한다

```sh
python3 evaluation/field-report-20261015/run.py verify \
  --study-dir "$KP_STUDY_DIR"
```

`verify`는 네트워크 없이 고정 입력·요청·응답·출력·사용량의 해시와 대응을 확인한다. 완료 응답의 `output_text`는 앞뒤 공백·줄바꿈까지 그대로 보관한다. 의미 오류가 있어도 교정·재정렬·요약하지 않으며, 후속 수정본은 원시 출력과 별개로 기록한다. 러너를 바꾼 뒤 과거 기록을 검증할 때의 `--archived-runner`는 보관한 러너 바이트의 해시 대조 전용이며 과거 코드를 실행하거나 새 요청을 보내지 않는다.

전송·해시 검증 통과와 의미·구조 통과는 별개다. 검토자는 주장별 출력 위치, 추가·누락·변경된 의미, 구조 조건별 판정과 근거를 따로 기록한다. 문자 수는 raw·가시 문자·공백·Markdown 및 링크 차이를 구분하며, 규약 토큰 예산이나 의미 보존 판정을 대신하지 않는다.

이 비교는 **규약 텍스트를 직접 넣은 실험**이다. 설치된 스킬의 발견·실제 로딩, 전역 설치, 정식 0.7의 변경, 사용자 독해 시간 또는 새 후보의 최종 통과를 증명하지 않는다. 수동 설치와 호출은 [실험 스킬 안내](../../docs/distribution/on-demand-skill.md)를 따른다.

## 현재 후보의 판정을 구분한다

현재 스킬 전체와 공통 호출문은 Opus 경로의 원문 없는 최소 요청에서 **5,951토큰**으로 계측했다. 같은 텍스트의 `o200k_base`는 3,432토큰, `cl100k_base`는 5,255토큰이다. 이 수치는 호스트의 다른 지침·이력·원문을 포함한 전체 컨텍스트 상한이 아니다. 후보 해시는 아래와 같다.

```text
825272c90a0e102602163d15cdae5e1b2d128d3abd7ceae3c13a222e52e6f28f
```

기존 짧은 원문 6개는 최종 후보의 의미·구조 검토에서 모두 통과했다. 그러나 긴 실전 보고서의 두 반복 출력은 모두 전체 기준을 통과하지 못했다. 구조 검사는 각각 12/13이었으며, 운영 종료 조건의 앞쪽 배치와 일반 주장·특정 기능 설명의 범위 보존에 문제가 남았다.

이 후보는 반복 관찰한 개발 사례로 보완했다. 새로운 문서에 대한 일반화, 독자의 재독 감소, 설치된 스킬의 실제 로딩은 검증하지 않았다. 코드 테스트와 CI 통과는 생성된 보고서의 의미·구조 합격을 뜻하지 않는다. 민감한 원문과 미가공 출력, 상세 판정은 비공개 로컬 기록으로 보존하며 공개 저장소에 넣지 않는다.

스킬화는 필요한 작업에서 규약을 읽게 하는 적용 방식이다. 실제 출력의 준수를 보장하는 장치로 간주하지 않으며, 정식 0.7의 상시 지침·서명 배포본을 이 후보로 바꾸지 않는다.
