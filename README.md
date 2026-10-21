# Korean Protocol

**한국어 답변에서 대상·판단·조건·기한을 바로 찾게 한다.**

Korean Protocol(KP)은 Codex·Claude Code에서 **필요할 때 호출하는 한국어 작성 스킬**이다. 글의 사실·조건·수치·출처는 유지하고 배치와 문장만 바꾼다. 별도 모델이나 출력 필터가 아니다.

| 항목 | 내용 |
| --- | --- |
| 현재 버전 | **v0.10.0** · 호출형 스킬 · KP 코어와 L1~L4 출력 형식 |
| 호출 | Codex `$korean-protocol` · Claude Code `/korean-protocol` |
| 적용 범위 | 호출한 대화에만 적용한다. 자동 호출은 꺼져 있다. |
| 설치 범위 | 사용자 범위에 설치하면 같은 계정의 다른 프로젝트에서도 호출한다. |
| 기존 v0.7.0 | 상시 지침이다. 스킬과 함께 켜면 중복 적용되므로 [규약만 OFF로 전환](INSTALL.md#기존-07-상시-지침에서-전환한다)한다. |

[설치](INSTALL.md) · [처음 사용](docs/distribution/quick-start.md) · [v0.7에서 전환](INSTALL.md#기존-07-상시-지침에서-전환한다) · [v0.10.0 변경·검증 상태](docs/distribution/output-formats-candidate-status.md) · [v0.9.0 검증 기록](evaluation/clarity-20261016-r60/README.md) · [릴리스](https://github.com/project820/korean-protocol/releases)

## KP 코어에 네 단계 출력 형식을 연결했다

v0.10.0은 기존 KP의 한국어 작성·의미 보존 규칙을 **L1 공통 기준**으로 두고, 필요할 때만 출력 형식을 바꾼다. 표의 셀, 도식의 라벨, HTML의 상태 문구, 영상의 내레이션에도 같은 규칙을 적용한다. 사용자가 형식을 지정하면 그 형식을 먼저 따른다.

| 단계 | 사용하는 경우 | 산출물 |
| --- | --- | --- |
| L1 | 기본값이다. | KP 문단·목록·절차 |
| L2 | 아키텍처·프로세스·상태 변화·세 항목 이상 비교가 있을 때 | 표·Mermaid·ASCII 도식 |
| L3 | 변수를 바꿔 보거나 상태를 전환해야 이해될 때, 또는 요청할 때 | 외부 의존성 없는 단일 `index.html` |
| L4 | 영상·애니메이션을 명시 요청할 때만 | Manim 코드와 장면별 한국어 내레이션 |

**v0.10.0의 원문·KP·STE 정식 비교는 완료하지 않았다.** 사용자 지시로 출력 구조를 먼저 배포한다. 중단한 비교에서는 생성 60건 중 59건이 도구 검사를 통과했고 1건은 서버 연결 종료로 완료되지 않았다. 익명 검토 10건에서 v0.10.0 후보의 의미는 9건 통과·1건 미해결, 형식은 10건 모두 통과했다. 미해결은 모호한 전언의 수식 범위를 표의 전달 경로 칸으로 확정한 사례이며, 이를 막는 지침을 보완했다. 보완본은 정식 비교를 거치지 않았다.

STE는 개발·개정의 독립 대조군으로만 사용한다. [개편 규칙 대응표](docs/spec/output-formats-rule-map.md)는 기존 핵심 규칙 25개의 보존을, [변경·검증 상태](docs/distribution/output-formats-candidate-status.md)는 실험 기록과 한계를, [평가 방법](evaluation/output_formats/README.md)은 비교 도구를 설명한다.

## 설치한다

사용할 Codex 또는 Claude Code에 다음을 보낸다. 두 곳 모두 설치하려면 두 호스트를 명시한다.

```text
https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
Korean Protocol v0.10.0 스킬을 지금 사용하는 호스트의 사용자 범위에 설치해줘.
다른 프로젝트에서도 호출할 수 있게 하고 자동 호출은 꺼줘.
기존 0.7 상시 설치가 있으면 같은 설치의 관리 명령으로 규약만 OFF로 전환해줘.
높임말·자동 갱신·신뢰 키와 다른 사용자 지침은 보존해줘.
기존 스킬 폴더는 덮어쓰기 전에 차이를 확인하고 설치·발견·호출 결과를 알려줘.
```

설치 위치·파일 목록·해시 검증·Claude Code 설정은 [설치 안내](INSTALL.md)에 있다. **0.7 ZIP과 `agent_install.py install`은 이 스킬을 설치하지 않는다.**

## 호출한다

| 호스트 | 새 대화에 입력한다. |
| --- | --- |
| Codex | `$korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |
| Claude Code | `/korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |

- 원문을 붙이거나 파일을 지정한다.
- 새 글은 `이번 작업의 완료 보고를 작성해줘`처럼 요청한다.
- 높임말이 필요하면 `높임말로 써줘`를 덧붙인다. 지정이 없으면 높임 없이 쓴다.
- Claude Code에서는 `/korean-protocol`을 메시지 맨 앞에 쓴다.

## 적용을 확인하고 끈다

1. 새 대화의 스킬 목록에서 `korean-protocol`을 확인한다. 없으면 호스트를 다시 시작한다.
2. 짧은 원문으로 호출한다. 대상·조건·기한이 남았는지, 핵심 판단이 첫 문장에 있는지 확인한다.
3. 끌 때는 **새 대화에서 호출하지 않는다.** 이미 읽힌 규약은 그 대화에 남는다. “OFF”라는 말로 지워지지 않는다.

모델이 “적용했다”고 말한 것만으로 확인하지 않는다. 파일·발견·출력 확인 방법은 [호출 확인 안내](docs/distribution/on-demand-skill.md#설치와-호출을-확인한다)에 있다.

## v0.9.0 검증 결과

**v0.9.0은 원문·KP·STE 3자 비교를 완료했으나 수락 기준을 통과하지 못했다.** 사례 12개(재작성 6개·자료 기반 새 글 6개)를 GPT-6.1 Sol과 Claude Opus 5.5의 low·medium 설정에서 조건별 2회 생성했다. 생성 576건과 출력을 가린 모델 검토 192건에 오류는 없었다. STE 열은 [ASD-STE100 공개 원칙의 한국어 실험 적용본](evaluation/clarity-20261016-r60/ste.md)이며 공식 한국어판이 아니다.

| 모델·추론 | 의미 보존 통과/실패/미해결 (v0.9.0 · v0.8.0 · STE) | v0.8.0 대비 명료성 승/패/무 | STE 대비 명료성 승/패/무 |
| --- | --- | --- | --- |
| Sol · low | 23/0/1 · 21/1/2 · 18/3/3 | 16/3/5 | 13/6/5 |
| Sol · medium | 24/0/0 · 21/2/1 · 16/2/6 | 11/9/4 | 9/6/9 |
| Opus · low | 22/2/0 · 19/4/1 · 17/6/1 | 10/1/13 | 5/8/11 |
| Opus · medium | 23/0/1 · 24/0/0 · 19/4/1 | 12/2/10 | 5/7/12 |

수락 기준은 별도 평가 96건 모두의 의미 보존과, 네 설정 각각에서 v0.8.0·STE보다 명료성 승수가 많은 것이다. v0.9.0은 의미 실패 2건·미해결 2건이 남았고 Opus 두 설정에서 STE에 졌다. 사용자 지시로 이 결과를 공개하고 v0.8.0을 대체해 배포한다.

v0.8.0 대비 변경은 다음과 같다.

- 규칙을 작업 범위·근거·의미 보존·표현·최종 대조 순서로 다시 썼다. `SKILL.md`는 `o200k_base` 7,410토큰에서 3,471토큰으로 줄었다.
- 원자료에 없는 사실·주체·원인·기한·승인자를 보태지 않는다. 전언·추정값으로 만든 합계를 확인된 값과 섞지 않는다.
- 실행할 행동이 둘 이상이면 행동마다 줄을 나누고, 순서가 정해진 절차는 한 단계에 행동 하나를 둔다.
- 의미 경계 사례를 [`references/meaning-boundaries.md`](skills/korean-protocol/references/meaning-boundaries.md)로 분리했다. 참고 파일이 없어도 핵심 규칙만으로 작동함을 Codex·Claude Code에서 확인했다.

남은 한계는 다음과 같다.

- 원자료가 정하지 않은 관계(전언의 서면 기재 여부, 승인 주체)를 채우는 오류가 남았다.
- Opus에서는 역할별로 구분하고 단계를 나눈 STE 출력이 더 명료하다는 판정이 많았다.
- 판정은 모델 검토자가 했다. 사람의 읽기 시간은 측정하지 않았다. 확인한 호스트는 로컬 macOS의 Codex·Claude Code다.

원시 출력은 내부 평가 자료로 보존하며 저장소에는 올리지 않았다. 사례별 결과는 [60차 비교 기록](evaluation/clarity-20261016-r60/README.md)에 있다. v0.8.0의 [세션 보고서 비교](evaluation/session-reports-20261015/README.md)는 이전 기준본의 기록이다.

## 버전 이력

| 버전 | 형태 | 상태 |
| --- | --- | --- |
| **v0.10.0** | 호출형 스킬 | 현재 권장. L1~L4 출력 형식을 추가했다. 정식 3자 비교는 완료하지 않았다. |
| v0.9.0 | 호출형 스킬 | 이전 버전. 위 3자 비교 결과를 따르며 수락 기준은 통과하지 못했다. |
| v0.8.0 | 호출형 스킬 | 이전 버전. [세션 보고서 비교](evaluation/session-reports-20261015/README.md) |
| 중간본 `909dc9d` | 호출형 스킬 | v0.7.0과 v0.8.0 사이의 첫 스킬 검증본이다. 번호를 붙이지 않았다. [평가 기록](evaluation/field-report-20261015/README.md#보완-후보의-검증-범위를-밝힌다) |
| v0.7.0 | 상시 지침·서명 배포 | 기존 사용자 유지용. 원본 `0.7.0-draft`, 서명 콘텐츠 `0.7.0·순번 3`, 엔진 `0.2.0`. [릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0) |

평가 기록의 `r10`·`r11`·`r12`는 실험 회차 번호이며 공개 버전 번호가 아니다. `r10`은 중간본 `909dc9d`, `r12`는 v0.8.0이다. `r11`은 채택하지 않은 실험 후보다. `clarity-20261016-r60`은 v0.9.0의 후보다. `output_formats`의 `run-01`~`run-11`은 v0.10.0 출력 형식 개편의 평가 회차다.

<details>
<summary>v0.7.0 상시 지침의 상태를 확인한다.</summary>

공개 배포본 `0.7.0`은 원본 `0.7.0-draft`에서 만들었다. `draft`는 연구·개발 품질 범위를 나타낸다.

| 항목 | 상태 |
| --- | --- |
| 원본 버전 | **0.7.0-draft**. 규칙 72개·규칙 작성자 사례 296개·사전 193뜻. V7 이전 보완본 r2의 구조 규칙을 채택했다. |
| 채택 기준 | 사용자가 r2의 가독성을 선택했다. 더 짧게 만든 r3는 채택하지 않았다. |
| 콘텐츠 발행 | **0.7.0·순번 3**을 공개했다. 두 호스트의 서명 HTTPS 갱신과 기존 로컬 설치 갱신을 [검증했다](docs/distribution/public-0.7.0-verification.md). |
| 기능 대응 | 현행 대응표는 설계 49개·검증 0개·부분 4개다. |
| 효과 검증 | V7 실험의 의미 변경·미확정 결과가 남아 있다. 실제 독자 시험은 수행하지 않았다. |

[채택 기록](experiments/v7/adoption.md)은 결정과 한계를, [고정 실험 기록](experiments/v7/README.md)은 당시 프로필과 실패 집계를 보존한다. 0.3.0 당시의 근거는 [연구·검증 기록](docs/status/research-evidence.md)에 있다.

</details>

## 문장과 구조를 함께 다듬는다

**아래 표는 v0.7.0으로 생성한 과거 출력이며 v0.8.0 이후의 출력이 아니다.** 같은 원문 6개를 Opus 5.5·medium에서 KP 0.7과 STE 원칙 적용본으로 한 번씩 생성했다. 출력 12건은 교정하지 않았다. 굵게 표시와 줄바꿈만 화면에 맞게 표시하며 각 셀에서 출력 원문을 연다.

- 의미 검토: 11건 보존, 1건 보류. STE의 교육 신청 예문은 명단 제출자를 ‘신청자’로 표시했다. 원문이 두 역할의 관계를 정의하지 않아 보류했다.
- KP 입력: 0.7 배포 프로필과 사전 2개 전체. 기존 대화와 설명용 답안은 넣지 않았다.
- STE 열: [ASD-STE100 공식 설명](https://asd-ste100.org/STE_faq.html)의 공개 원칙을 한국어에 적용한 실험이다.
- 입력·출력 해시: [실행 조건·검토 결과](evaluation/readme-model-comparison-20261015/README.md)

[대상 목록](#1-반납-대상을-먼저-찾는다) · [신청 방식](#2-신청-방식별-조건을-묶는다) · [조건부 처리](#3-조건과-후속-처리를-묶는다) · [기한 예외](#4-기한의-기산점과-예외를-구분한다) · [실패 보고](#5-실행-성공과-의미-오류를-구분한다) · [미확인 상태](#6-표기-없음과-지정-없음을-구분한다)

<table>
<thead>
<tr><th width="33%" scope="col" nowrap>원문 · 사실과 조건의 기준</th><th width="33%" scope="col" nowrap>Korean Protocol 0.7</th><th width="33%" scope="col" nowrap>STE 원칙 적용 · 한국어 참고</th></tr>
</thead>
<tbody>
<tr><th colspan="3" align="left"><a id="1-반납-대상을-먼저-찾는다"></a>1. 반납 대상을 먼저 찾는다</th></tr>
<tr>
<td valign="top">반납 대상은 노트북, 모니터, 출입카드이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다.</td>
<td valign="top"><strong>반납 대상</strong><br>- 노트북<br>- 모니터<br>- 출입카드<br><br>접수 기한: 7월 5일 18:00<br>접수 담당: 총무팀<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/01-kp.txt">모델 출력 원문</a></td>
<td valign="top">반납 대상은 다음과 같다.<br><br>- 노트북<br>- 모니터<br>- 출입카드<br><br>접수 담당은 총무팀이다.<br><br>접수 마감은 7월 5일 18:00이다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/01-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="2-신청-방식별-조건을-묶는다"></a>2. 신청 방식별 조건을 묶는다</th></tr>
<tr>
<td valign="top">교육 신청은 포털 신청과 부서 취합으로 나뉜다. 참석자가 20명 이상인 정기 과정은 본인이 포털에서 직접 신청하며 마감은 마감일 18:00이다. 소규모 실습이나 외부 강사 과정은 부서 담당자가 명단을 취합해 과정 시작 5영업일 전까지 제출한다. 법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.</td>
<td valign="top">교육 신청은 포털 신청과 부서 취합으로 나뉜다.<br><br><strong>포털 신청</strong><br><br>- 대상: 참석자가 20명 이상인 정기 과정<br>- 신청 기한: 마감일 18:00<br>- 본인이 포털에서 직접 신청한다.<br><br><strong>부서 취합</strong><br><br>- 대상: 소규모 실습이나 외부 강사 과정<br>- 제출 기한: 과정 시작 5영업일 전까지<br>- 부서 담당자가 명단을 취합해 제출한다.<br><br><strong>두 방식 공통</strong><br><br>- 법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동으로 확인한다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/02-kp.txt">모델 출력 원문</a></td>
<td valign="top"><strong>교육 신청 방식</strong><br><br>교육 신청 방식은 포털 신청과 부서 취합 두 가지입니다.<br><br><strong>포털 신청</strong><br><br>- <strong>대상 과정:</strong> 참석자가 20명 이상인 정기 과정<br>- <strong>신청자:</strong> 참석자 본인<br>- <strong>방법:</strong> 포털에서 직접 신청합니다.<br>- <strong>마감:</strong> 마감일 18:00<br><br><strong>부서 취합</strong><br><br>- <strong>대상 과정:</strong> 소규모 실습 과정 또는 외부 강사 과정<br>- <strong>신청자:</strong> 부서 담당자<br>- <strong>방법:</strong> 참석자 명단을 취합하여 제출합니다.<br>- <strong>기한:</strong> 과정 시작 5영업일 전까지<br><br><strong>법정 의무교육 대상자 확인</strong><br><br>법정 의무교육 대상자의 누락 여부는 자동으로 확인됩니다. 이 확인은 신청 방식과 관계없이 적용됩니다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/02-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="3-조건과-후속-처리를-묶는다"></a>3. 조건과 후속 처리를 묶는다</th></tr>
<tr>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 자동 안내가 간다. 안내받은 대기자는 안내 수신 후 4시간 안에 응답해야 한다. 이 기한 안에 응답하지 않으면 다음 대기자에게 안내가 간다.</td>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 안내가 자동으로 간다.<br><br>응답 기한: 안내 수신 후 4시간 안<br>안내받은 대기자는 이 기한 안에 응답해야 한다.<br><br>기한 안에 응답하지 않으면 다음 대기자에게 안내가 간다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/03-kp.txt">모델 출력 원문</a></td>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 안내가 자동으로 간다.<br><br>안내받은 대기자는 안내를 받은 후 4시간 안에 응답해야 한다.<br><br>대기자가 이 기한 안에 응답하지 않으면 그다음 대기자에게 안내가 간다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/03-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="4-기한의-기산점과-예외를-구분한다"></a>4. 기한의 기산점과 예외를 구분한다</th></tr>
<tr>
<td valign="top">승인 담당자는 알림함의 ‘수신 대기’ 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다. 다만 근무시간 밖에 제출된 건은 이 4시간 기한 대신 다음 영업일 12:00까지 수신 확인을 남겨야 한다.</td>
<td valign="top">승인 담당자는 알림함의 ‘수신 대기’ 목록을 확인하고 아래 기한 안에 수신 확인을 남겨야 한다.<br><br><strong>기본</strong><br>- 수신 확인 기한: ‘수신 대기’ 목록을 확인한 뒤 4시간 안에<br><br><strong>근무시간 밖에 제출된 건</strong><br>- 수신 확인 기한: 다음 영업일 12:00까지<br>- 이 기한은 4시간 기한을 대신한다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/04-kp.txt">모델 출력 원문</a></td>
<td valign="top">승인 담당자는 알림함의 &#x27;수신 대기&#x27; 목록을 확인한 뒤 수신 확인을 남겨야 한다. 수신 확인 기한은 건이 제출된 시각에 따라 다르다.<br><br>- <strong>근무시간 밖에 제출된 건:</strong> 다음 영업일 12:00까지 수신 확인을 남겨야 한다. 4시간 기한은 적용하지 않는다.<br>- <strong>그 밖의 건:</strong> &#x27;수신 대기&#x27; 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/04-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="5-실행-성공과-의미-오류를-구분한다"></a>5. 실행 성공과 의미 오류를 구분한다</th></tr>
<tr>
<td valign="top">변환 12건은 모두 정상 실행되었다. 그러나 의미 검토에서 2건의 취소 조건 누락을 찾았다. 담당자는 해당 2건을 보완해야 한다. 재검토 전에는 배포할 수 없다.</td>
<td valign="top">변환 12건은 모두 정상 실행됐다. 그러나 의미 검토에서 2건의 취소 조건 누락을 찾았다.<br><br>담당자는 해당 2건을 보완해야 한다. 재검토 전에는 배포할 수 없다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/05-kp.txt">모델 출력 원문</a></td>
<td valign="top">변환 12건은 모두 정상 실행되었다.<br><br>그러나 의미 검토에서 취소 조건 누락 2건을 찾았다.<br><br>담당자는 해당 2건을 보완해야 한다.<br><br>재검토 전에는 배포할 수 없다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/05-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="6-표기-없음과-지정-없음을-구분한다"></a>6. 표기 없음과 지정 없음을 구분한다</th></tr>
<tr>
<td valign="top">자료에는 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.</td>
<td valign="top">자료에는 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/06-kp.txt">모델 출력 원문</a></td>
<td valign="top">자료에는 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.<br><br><a href="evaluation/readme-model-comparison-20261015/outputs/06-ste.txt">모델 출력 원문</a></td>
</tr>
</tbody>
</table>

모바일에서는 표를 좌우로 이동해 세 열을 비교한다. 문장·구조의 차이와 의미 판정은 [사례별 검토](evaluation/readme-model-comparison-20261015/README.md)에 있다.

## 문서를 찾는다

| 목적 | 문서 |
| --- | --- |
| 설치·호출·전환 | [설치 안내](INSTALL.md) · [처음 사용](docs/distribution/quick-start.md) · [호출 확인](docs/distribution/on-demand-skill.md) · [호스트 지원](docs/distribution/host-support.md) |
| 평가 기록 | [평가 규칙](evaluation/README.md) · [v0.10.0 출력 형식 평가](evaluation/output_formats/README.md) · [v0.9.0 60차 비교](evaluation/clarity-20261016-r60/README.md) · [v0.8.0 세션 보고서 비교](evaluation/session-reports-20261015/README.md) |
| 규칙과 어휘 | [한국어 세부 규칙](docs/spec/korean-rules.md) · [통제 어휘](docs/spec/lexicon.md) |
| 기존 v0.7.0 관리 | [관리 설정](docs/distribution/application-controls.md) · [배포 계약](docs/distribution/README.md) · [채팅 안내](distribution/CHAT-START.md) |
| 설계와 근거 | [문서 목차](docs/README.md) · [검증 상태](docs/status/requirements.md) · [연구 근거](docs/research-basis.md) |

Korean Protocol은 ASD-STE100의 간결한 기술 문체에서 출발한 독립 규약이며 번역본이나 공식 한국어판이 아니다. 영어의 단어 수 제한을 한국어 어절 수로 옮기지 않는다. 직접 작성한 코드·규약·사전·문서는 [MIT License](LICENSE)로 제공한다. 제3자 자료의 권리는 [NOTICE.md](NOTICE.md)에 구분했다.
