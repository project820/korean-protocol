# 출력 형식 후보를 원문·KP·STE로 검증한다

이 디렉터리는 v0.9.0 이후 출력 형식 후보의 평가 도구와 입력을 보관한다. 스킬 구현·정적 검사·호스트 호출의 성공은 품질 합격을 뜻하지 않는다. 정식 배포 설치기는 독립 비교와 매체·호스트 검증을 모두 통과한 후보만 허용한다.

사용자는 기본 KP와 L1~L4 구조를 로컬에서 먼저 쓰도록 지시했다. 기존 설치 백업·설치 기록·명시 호출을 보존해 두 호스트의 사용자 범위 설치를 갱신했다. 평가 확대와 전송 복구 정책 개발은 중단했다. `run-11`은 r8 후보만 고정했고 정식 계획·모델 생성·검토는 시작하지 않았다. 로컬 사용은 비교 완료나 품질 합격을 뜻하지 않으며 정식 비교는 별도 후속 범위로 남긴다.

## 비교 조건을 고정한다

- 기존 KP v0.9.0, 새 KP 후보, STE 원칙의 한국어 실험 적용본을 동일 원문에서 독립 생성한다. STE는 사용자 스킬의 출력 모드가 아니다.
- Sol과 Opus의 `medium`, `high`, `xhigh`를 각각 2회 실행한다. 개발 12건과 새 평가 12건에 L1~L4를 각각 3건씩 배치한다. 전체 생성은 864건이며 익명 교차 검토는 288건이다.
- 원문·요청·매체 계약·도구 접근·출력 예산은 세 조건에서 같다. 모든 조건의 출력 예산은 64,000토큰이다. 작성 프로필만 다르다. 전체 패키지 파일은 해시로 고정하되, 실제 프롬프트에는 해당 매체의 작성 지침과 필요한 예제만 넣는다.
- 후보 고정 후 새 평가 사례를 독립 작성한다. 후보를 바꾸면 새 평가 사례를 다시 작성한다. 기존 사례·원시 출력·판정은 덮어쓰지 않는다.
- STE 출처·판본·적용 규칙·한국어 적용 방식은 `ste-provenance.json`에 있다. 공식 FAQ를 바탕으로 만든 자체 요약이며 공식 한국어판이나 인증된 규격 준수 결과가 아니다.

## 실행 기록을 분리한다

기본 실행 폴더는 `output/kp-output-formats-20261020/`다. `run-01`은 HTML 기본형의 초기화 오류가 발견된 후보 스냅샷이다. `run-02`는 모델이 만든 HTML에서 초기화 오류와 표시 언어 오류가 발견돼 생성을 중단했으며 비교는 미완료다. `run-03`은 후보만 고정했고 생성하지 않았다. `run-04`는 초기화 호출과 표시 언어 점검을 보완한 별도 후보다. 원시 자료는 공개 패키지에 포함하지 않는다.

`run-05`는 D07의 36개 출력과 익명 검토 12건을 확보했다. 후보의 브라우저 동작은 12개 모두 통과했으나 의미 미해결 1건과 형식 실패 2건이 남았다. `run-06`은 검사 도구를 추가한 스냅샷이며, 도구 자체의 결함을 발견해 모델 출력을 생성하지 않았다. 각 실행의 후보와 원문은 후속 개정으로 덮어쓰지 않는다.

`run-09`는 개발 출력 280건과 익명 검토 60건을 확보한 뒤 중단했다. 검토 59건은 유효했고 D01 검토 1건은 인용 불일치로 무효였다. 유효 검토에서 후보 의미는 59건 통과했고, 형식은 57건 통과·D06 2건 미해결이었다. 최종 검토 기록(로컬 기록 `output/kp-output-formats-20261020/run-09/review-summaries/final-review-status.json`)과 집계(로컬 기록 `output/kp-output-formats-20261020/run-09/summary.json`)는 비교 미완료·품질 미통과를 기록한다.

D06의 분리 방식, D07·D08의 초기 유효 입력·초기화 복원 대상과 D09의 시작 상태·도구 초기화는 [입력 개정 기록](case-revision-notes.md)에 근거와 범위를 남긴다. 브라우저의 전체 초기화·원문 전이 구분과 장식용 상태 표시 인식을 수정하고 회귀 검증했다. `run-10`은 이 변경을 별도로 고정한 뒤 세 비교군의 새 생성·검토를 시작했으며 비교는 아직 미완료다. r7 후보와 미사용 평가 원문은 유지하고, 과거 출력과 판정은 바꾸지 않는다.

사용자가 선택한 새 방식은 `tool-assisted-v1`이다. 기존 KP·후보 KP·STE 모두 같은 고정 검사 도구와 최대 두 번의 자체 수정 기회를 받는다. 최초 생성부터 이 정책을 알린다. 각 호출의 출력 예산은 64,000토큰이며 한 결과물의 최대 호출 예산은 192,000토큰이다. 도구가 실제 문제를 보고한 경우에만 수정을 요청한다. 독립 의미·명료성 검토 결과는 수정 요청에 넣지 않는다.

도구는 모델 출력을 수정하지 않는다. 최초 출력과 각 수정 출력·요청·원시 응답·진단·스크린샷을 별도 보존한다. 필수 진단을 처음 통과한 출력에서 멈춘다. 수정 한도를 소진하면 마지막 출력을 선택하고 남은 문제를 실패·미해결로 유지한다. 전송 오류·도구 실행 실패·누락된 필수 검사는 재시도 없이 미완료로 남긴다. 단회 생성 결과와 도구 보조 결과를 한 비교로 합치지 않는다.

도구 보조 실행의 원시 자료는 `runs/<작업 ID>/attempts/0..2/`에 있다. 각 시도 안의 `diagnostics/`가 해당 출력의 실제 검사 자료를 보관한다. `selection.json`은 선택한 시도와 중단 이유를 연결한다. 비교 화면은 검증된 선택 출력만 표시하므로, 선택 전에 실행이 실패한 경우에는 해당 시도 폴더에서 원시 자료를 확인한다.

## 검토의 인용 정정과 판정 변경을 구분한다

새 [검토 정책](study.py)의 스키마는 `exact-quote-repair/v1`이다. 최초 검토의 JSON·스키마·판단 구조가 유효하고 인용 문자열만 원문·출력과 일치하지 않을 때 해당 문자열만 최대 2회 정정한다. 의미·형식·명료성 판정, 이유, 기존 유효 인용, 필드·목록의 개수와 순서는 잠근다. 유효한 `fail`·`unresolved`는 최종 판정이며 재시도하지 않는다.

최초 검토와 정정 응답·요청·검증 자료는 `reviews/<검토 ID>/attempts/0..2/`에 따로 보존한다. `selection.json`은 첫 유효 검토와 시도별 해시를 연결하고 `review_result`는 정정 자격·잠금·요청·선택을 다시 검증한다. 한 검토의 최대 호출은 최초 1회와 정정 2회이며 각 호출의 출력 예산은 64,000토큰이다. JSON·스키마 오류, 잠금 내용 변경, 전송 오류 또는 정정 한도 소진은 미완료로 남긴다.

이 정책은 새로 고정하는 비교부터 적용하며 `run-09`의 무효 검토나 실패·미해결 판정을 소급 정정하지 않는다. 인용 정정은 생성 모델의 자체 수정과 별개이며 의미 판정을 통과로 바꾸는 절차가 아니다.

## 평가 명령과 고정 조건을 참고한다

아래 명령은 평가 도구의 사용법이며 현재 작업에서 새 비교를 시작하는 지시가 아니다. 패키지의 `source_hashes`를 JSON 파일로 저장해 `--candidate-files`에 전달한다. 아래 경로의 `RUN`은 실행마다 새 디렉터리의 절대 경로로 지정한다. 생성·검토·집계·설치 근거 검증에서 같은 절대 경로와 Python 실행 파일을 사용한다.

현재 도구 실행 기록은 실제 명령의 경로를 정확히 대조하므로 평가 폴더 이동이나 상대 경로 별칭은 지원하지 않는다. 패키지 내부의 파일 목록은 이와 별개로 상대 경로를 사용한다.

```sh
python3 -m evaluation.output_formats.study freeze --run-dir RUN --candidate-only --candidate . --candidate-files SOURCE_HASHES.json
# 위 고정 시점 뒤에 독립 평가 사례를 작성하고 dataset.json을 만든다.
python3 -m evaluation.output_formats.study freeze --run-dir RUN --baseline BASELINE_SKILL --ste evaluation/output_formats/ste.md --ste-provenance evaluation/output_formats/ste-provenance.json --dataset evaluation/output_formats/dataset.json --method tool-assisted-v1 --html-checker skills/korean-protocol/scripts/check_html.py --browser-checker evaluation/output_formats/browser_check.mjs --oracle SOURCE_BOUND_ORACLES.json
python3 -m evaluation.output_formats.study preflight --run-dir RUN --timeout 900
python3 -m evaluation.output_formats.study generate --run-dir RUN --split development --workers 6 --timeout 900
python3 -m evaluation.output_formats.study review --run-dir RUN --split development --workers 6 --timeout 900
python3 -m evaluation.output_formats.study generate --run-dir RUN --split evaluation --workers 6 --timeout 900
python3 -m evaluation.output_formats.study review --run-dir RUN --split evaluation --workers 6 --timeout 900
python3 -m evaluation.output_formats.study aggregate --run-dir RUN
python3 -m evaluation.output_formats.study viewer --run-dir RUN
```

명령은 기존 요청을 자동 재시도하거나 다른 모델·추론 설정으로 대체하지 않는다. 실패한 요청에도 원시 응답과 오류 기록을 남긴다. 서버가 실제 추론 설정을 응답에 돌려주지 않으면 확인 상태를 `unknown`으로 기록한다. 요청 설정과 서버 응답 설정의 불일치는 실패다.

브라우저 검사는 이미 설치한 Node·Playwright·Chrome을 사용한다. `KP_PLAYWRIGHT_MODULE_ROOT`에는 사용할 `node_modules` 경로를 지정한다. 평가 도구가 의존성을 자동 설치하지 않는다. 원문에서 독립 작성한 오라클은 데이터셋과 각 L3 원문의 해시를 포함한다. 산출식·입력 범위·초기값·상태 전이는 원자료에만 근거한다. 모델이 만든 결과나 검토자의 선호로 정답을 정하지 않는다.

L1·L2의 도구 검사는 적용 가능한 정적 확인에 한정한다. L3에는 HTML 정적 진단과 여섯 브라우저 동작 검사를 적용한다. L4에는 Python 구문과 Manim 구조의 정적 검사를 적용한다. 이 단계는 의미 보존이나 실제 영상 렌더링을 인증하지 않는다. 후보의 최종 진단에 오류나 검토 요구가 남으면 설치를 차단한다.

## 수락 기준을 구분한다

- 모든 생성과 유효 검토가 있어야 비교가 완료된다. 미완료·입력 불일치·원시 자료 변조는 설치를 차단한다.
- 모든 후보 출력의 의미와 요청 형식이 통과해야 한다. 각 모델·추론 조건에서 기존 KP와 STE 각각에 대한 명료성 승수가 패수보다 많아야 한다. 의미·형식 미해결은 합격이 아니다.
- 비교 화면은 원문·후보 KP·STE의 세 칼럼을 제공하며 기존 KP를 선택해 볼 수 있다. 원시 출력은 수정하지 않는다.
- HTML은 모든 비교군에 동일한 정적·브라우저 검사를 적용한다. 후보의 오프라인 실행·초기값·변경·오류·초기화·좁은 화면·키보드 동작이 실패하면 설치를 차단한다.
- Manim은 코드 구문과 장면별 내레이션 대응을 확인한다. 실제 영상 렌더링과 음성 합성은 별도로 확인하며, 코드 생성만으로 완료를 선언하지 않는다.
- 두 호스트의 실제 읽기·출력 이벤트를 고정 후보에 연결한다. 임의의 `pass` 표시나 해시만 있는 빈 증거 파일로 통과시킬 수 없다.

고정 매체 비교는 자동 형식 선택의 적절성을 입증하지 않는다. 자동 선택은 별도 사례로 확인하며, 이 결과를 같은 매체의 STE 대비 명료성 판정에 섞지 않는다. 모델 검토 결과는 실제 사람의 읽기 시간 측정이 아니다.

## 관련 검사를 실행한다

```sh
python3 -B -m unittest discover -s tests -p 'test_output_formats*.py'
python3 -B -m unittest discover -s tests -p 'test_skill_package.py'
python3 -B -m validation.check --root . --json
```

새 설치 패키지와 품질 게이트 연결은 [패키지 안내](../../docs/distribution/output-formats-package.md)를 따른다. 기존 v0.7 서명 배포·자동 갱신기는 변경하지 않는다.
