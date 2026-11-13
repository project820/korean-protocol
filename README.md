# Korean Protocol

Korean Protocol은 ASD-STE100에서 출발한 독립 규약이다. ASD-STE100 공식 한국어판과 별개다.

**한국어 답변에서 대상·판단·조건·기한을 바로 찾게 한다.**

Korean Protocol(KP)은 Codex·Claude Code에서 **필요할 때 호출하는 한국어 작성 스킬**이다. 원자료의 뜻을 유지하며 배치와 문장을 다듬는다.

| 항목 | 내용 |
| --- | --- |
| 현재 버전 | **v0.11.1** · 호출형 스킬 · 읽는 형태와 L1~L4 출력 형식 |
| 호출 | Codex `$korean-protocol` · Claude Code `/korean-protocol` |
| 적용 범위 | 호출한 대화에만 적용한다. 자동 호출은 꺼져 있다. |
| 설치 범위 | 사용자 범위에 설치하면 같은 계정의 다른 프로젝트에서도 호출한다. |
| 기존 v0.7.0 | 상시 지침이다. 스킬과 함께 켜면 중복 적용되므로 [규약만 OFF로 전환](INSTALL.md#기존-07-상시-지침에서-전환한다)한다. |

[설치](INSTALL.md) · [처음 사용](docs/distribution/quick-start.md) · [v0.7에서 전환](INSTALL.md#기존-07-상시-지침에서-전환한다) · [v0.11.1 변경·검증 상태](docs/distribution/output-formats-candidate-status.md) · [v0.11.0 예문 비교](#문장과-구조를-함께-다듬는다) · [릴리스](https://github.com/project820/korean-protocol/releases)

## v0.11.1은 L1~L4 출력 지침을 정의했다

**v0.11.1 진단은 형식 준수 결과다. 원문·KP·STE 정식 비교는 미완료다.**

**L2~L4를 선택하면 작성 전에 지정한 참조 파일을 읽는다.**
`SKILL.md`의 description과 4A절에 단계별 산출물과 읽을 파일을 명시했다.
참조를 읽을 수 없을 때 지킬 하한도 본문에 뒀다.

| 단계 | 산출물 | 적용 조건 |
| --- | --- | --- |
| L1 | 텍스트 | 기본 문단·목록·절차를 쓴다. |
| L2 | 표·Mermaid 도식 | 비교와 분기·관계를 표현한다. |
| L3 | 단일 `index.html` | 변수 조작·상태 전환이 이해에 필요하거나 사용자가 요청할 때 쓴다. |
| L4 | Manim 코드·내레이션 | 사용자가 영상화·애니메이션 코드를 명시 요청할 때 쓴다. |

L3는 결과 패널을 입력 앞에 둔다. 입력은 원자료의 범주·수치에 맞춘다.
HTML 검사에는 `innerhtml-assignment`·`result-after-input`·`dark-default-theme` 진단을 추가했다.

### 형식 준수 진단을 기록한다

원문은 회의실 예약 취소 안내 1종이다. 모델은 Sonnet 5.5·Sol·Terra·Grok 4.7이다.
추론은 `medium`이다. 기본 실험은 KP·STE 모두 모델마다 2회 반복했다. Sonnet L3는 규칙 보강 뒤 KP만 2회 더 돌렸다.

| 항목 | v0.11.0 | v0.11.1 |
| --- | --- | --- |
| L2 질문에 Mermaid 언급·SKILL.md만 제공 | 0/4 | 8/8 |
| L3 결과 패널이 입력보다 앞·참조 포함 | 미측정 | 10/10 |
| L3 `.panel_layout` 격자·참조 포함 | 미측정 | 10/10 |
| L3 밝은 배경·첫 화면 결과·브라우저 확인 | Grok 어두운 테마 1건 | 16/16 |
| L3 320px 가로 스크롤 | 미측정 | 0/16 |
| Mermaid 11 파서 통과 | 미측정 | 8/8·KP 6, STE 2 |

STE는 기본 실험과 같은 모델·요청·반복으로 L3 8건과 L2 4건을 생성했다.
STE L3는 8건 모두 입력 없는 정적 문서였다.

- **남은 문제:** Sonnet은 `SKILL.md`만 받은 조건에서 원자료에 없는 수치 입력을 4/4회 만들었다.
- **참조 효과:** 규칙 보강 뒤 참조 포함 조건에서는 2/2회 모두 해당 입력이 없었다.
- **적용 한계:** `SKILL.md`만 받은 조건의 격자 CSS 사용은 0/10이었다.
- **진단 범위:** 수치 원문은 시험하지 않았다. 위 결과는 형식 준수 진단이다.
- **L1 회귀:** 파일럿 사례 5개를 4모델로 한 번씩 생성하고 Astra high가 가려서 1회 판정했다. v0.11.1의 의미 통과는 16/20(실패 3, 미해결 1)이고 1,000자당 문체 위반은 2.4다. 같은 검토에서 v0.10.1은 19/20, STE는 14/20이었다. v0.11.0의 이전 검토 값은 17/20, 2.3이다. 같은 STE 출력이 두 검토에서 17/20과 14/20을 받아, 검토 1회의 차이는 3건 안팎으로 흔들린다.
- **L2·L3 의미 보존:** Astra high가 원문과 대조했다. 출력 파일명에 KP·STE가 드러나 있어 가린 검토는 아니다. KP 출력은 16건 중 11건, STE 출력은 8건 중 5건이 보존이다. KP 실패 5건 중 3건은 HTML이 원문에 없는 시간 경계(24시간 정각, 4시간 정각)를 판정한 경우다.
- **판본:** 기본 실험은 중간본 `6ef3520b`로 실행했다. 최종본(`19ae7744`)으로 4모델 확인 프로브 16건을 다시 돌렸다. L2 Mermaid 언급 4/4, L3 결과 먼저·격자 4/4, 검사기 진단 0건이었다.

품질 향상·최종 합격은 이 진단으로 선언하지 않는다.
상세 결과는 [v0.11.1 진단 기록](evaluation/kp-v0111-output-formats-20261113/README.md)에 보존한다.
`SKILL.md`는 `o200k_base` 7,243토큰이다. v0.11.0보다 790토큰·약 12% 늘었다.

## v0.11.0은 읽는 형태를 다듬었다

코어 앞에 0절 「읽는 형태를 맞춘다」를 추가했다. 기존 1~5절과 4A절은 유지했다. 4절에는 요청자 결정 사항을 마지막에 두는 규칙을 추가했다.

- **골격:** 문서 고지는 제목 아래에 한 번 둔다. 핵심 판단은 굵게 쓴다.
- **절차:** 준비·절차·조건별 조치·참고를 나눈다. 단계 첫 줄에는 핵심 행동만 둔다.
- **문장:** 한 문장에 주장 하나를 둔다. 12어절을 넘으면 나누고 중복 설명을 뺀다.
- **의미:** 문장을 나눌 때 수식어와 수량의 대상을 유지한다. 기한 표현은 글자 그대로 둔다.

**사용자가 2026-11-13에 비교 화면을 읽고 후보 5를 채택했다.** 원문·KP·STE 정식 비교는 **미완료**다.

진단용 파일럿은 사례 5개를 모델 4개로 생성했다. 추론은 medium, 반복은 1회였다. v0.10.1과 STE도 같은 조건에서 독립 생성했다.

| 비교군 | 의미 통과 | 1,000자당 문체 위반 |
| --- | --- | --- |
| v0.11.0 후보 5 | 17/20 | 2.3 |
| v0.10.1 | 19/20 | 4.6 |
| STE | 17/20 | 3.7 |

**의미 실패 3건이 남았다.** 시험 결과의 한정 조건을 참고로 옮긴 사례가 1건이다. 원문에 없는 관계·결정을 만든 사례가 2건이다.

- **검토 한계:** 사용자 판독 의견이 후보와 검토 기준 양쪽에 반영됐다. 명료성 판정은 후보에 유리하다.
- **사례 한계:** 0절 예시 일부가 파일럿 사례에서 왔다. 검토 모델은 1개이며 사람의 읽기 시간은 재지 않았다.
- **크기:** `SKILL.md`는 `o200k_base` 6,453토큰이다. v0.10.1의 4,683토큰보다 약 38% 늘었다.

변경 경과는 [변경·검증 상태](docs/distribution/output-formats-candidate-status.md)에 기록한다. 조건별 결과와 한계는 [진단용 파일럿](evaluation/kp-lean-pilot-20261113/README.md)에서 확인한다.

## 문장과 구조를 함께 다듬는다

**아래 표는 v0.11.0 출력이다.** 같은 원문 6개를 Opus 5.5·medium에서 KP v0.11.0과 STE 원칙 적용본으로 한 번씩 생성했다. 출력 12건은 고치지 않았다. 굵게 표시와 줄바꿈만 화면에 맞게 바꿨고, 각 셀에서 출력 원문을 연다.

- **의미 검토:** 12건 모두 보존이다. GPT-6.1 Sol·high가 조건명을 가리고 판정했다.
- **KP 입력:** 태그 `v0.11.0`의 `SKILL.md` 전체다.
- **STE 입력:** [ASD-STE100 공식 설명](https://asd-ste100.org/STE_faq.html)의 공개 원칙을 한국어에 적용한 실험 지침이다. v0.11.0 파일럿과 같은 지침이다.
- **실행 조건·해시:** [v0.11.0 예문 비교 기록](evaluation/readme-model-comparison-20261113/README.md)
- **v0.7.0 출력:** [이전 예문 비교 기록](evaluation/readme-model-comparison-20261015/README.md)에 보존한다.

짧은 예문 6개의 예시다. v0.11.0의 원문·KP·STE 정식 비교는 **미완료**다.

[대상 목록](#1-반납-대상을-먼저-찾는다) · [신청 방식](#2-신청-방식별-조건을-묶는다) · [조건부 처리](#3-조건과-후속-처리를-묶는다) · [기한 예외](#4-기한의-기산점과-예외를-구분한다) · [실패 보고](#5-실행-성공과-의미-오류를-구분한다) · [미확인 상태](#6-표기-없음과-지정-없음을-구분한다)

<table>
<thead>
<tr><th width="33%" scope="col" nowrap>원문 · 사실과 조건의 기준</th><th width="33%" scope="col" nowrap>Korean Protocol 0.11</th><th width="33%" scope="col" nowrap>STE 원칙 적용 · 한국어 참고</th></tr>
</thead>
<tbody>
<tr><th colspan="3" align="left"><a id="1-반납-대상을-먼저-찾는다"></a>1. 반납 대상을 먼저 찾는다</th></tr>
<tr>
<td valign="top">반납 대상은 노트북, 모니터, 출입카드이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다.</td>
<td valign="top">- <strong>반납 대상:</strong><br>  - 노트북<br>  - 모니터<br>  - 출입카드<br>- <strong>접수 담당:</strong> 총무팀<br>- <strong>접수 마감:</strong> 7월 5일 18:00<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/01-kp.txt">모델 출력 원문</a></td>
<td valign="top">반납 대상은 다음과 같다.<br><br>- 노트북<br>- 모니터<br>- 출입카드<br><br>접수 담당은 총무팀이다.<br><br>접수 마감은 7월 5일 18:00이다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/01-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="2-신청-방식별-조건을-묶는다"></a>2. 신청 방식별 조건을 묶는다</th></tr>
<tr>
<td valign="top">교육 신청은 포털 신청과 부서 취합으로 나뉜다. 참석자가 20명 이상인 정기 과정은 본인이 포털에서 직접 신청하며 마감은 마감일 18:00이다. 소규모 실습이나 외부 강사 과정은 부서 담당자가 명단을 취합해 과정 시작 5영업일 전까지 제출한다. 법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.</td>
<td valign="top"><strong>교육 신청 방식 안내</strong><br><br>교육 신청은 포털 신청과 부서 취합으로 나뉜다.<br><br><strong>포털 신청</strong><br><br>- <strong>대상:</strong> 참석자가 20명 이상인 정기 과정<br>- <strong>신청:</strong> 본인이 포털에서 직접 신청한다.<br>- <strong>마감:</strong> 마감일 18:00<br><br><strong>부서 취합</strong><br><br>- <strong>대상:</strong> 소규모 실습이나 외부 강사 과정<br>- <strong>신청:</strong> 부서 담당자가 명단을 취합해 제출한다.<br>- <strong>마감:</strong> 과정 시작 5영업일 전까지<br><br><strong>법정 의무교육</strong><br><br>- <strong>누락 확인:</strong> 법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/02-kp.txt">모델 출력 원문</a></td>
<td valign="top"><strong>교육 신청 방법</strong><br><br>교육 신청 방법은 포털 신청과 부서 취합 두 가지입니다.<br><br>| 과정 | 신청 방법 | 기한 |<br>|---|---|---|<br>| 참석자가 20명 이상인 정기 과정 | 참석자 본인이 포털에서 직접 신청합니다. | 마감일 18:00 |<br>| 소규모 실습 과정, 외부 강사 과정 | 부서 담당자가 명단을 모아 제출합니다. | 과정 시작 5영업일 전 |<br><br><strong>법정 의무교육 누락 확인</strong><br><br>법정 의무교육 대상자가 빠졌는지는 자동으로 확인됩니다. 이 확인은 신청 방법과 관계없이 이루어집니다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/02-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="3-조건과-후속-처리를-묶는다"></a>3. 조건과 후속 처리를 묶는다</th></tr>
<tr>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 자동 안내가 간다. 안내받은 대기자는 안내 수신 후 4시간 안에 응답해야 한다. 이 기한 안에 응답하지 않으면 다음 대기자에게 안내가 간다.</td>
<td valign="top">- <strong>확정자가 이용 24시간 전까지 취소하면</strong> 다음 대기자에게 자동 안내가 간다.<br>- **안내받은 대기자**는 안내 수신 후 4시간 안에 응답해야 한다.<br>- <strong>이 기한 안에 응답하지 않으면</strong> 다음 대기자에게 안내가 간다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/03-kp.txt">모델 출력 원문</a></td>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 안내가 자동으로 간다.<br><br>안내받은 대기자는 안내를 받은 후 4시간 안에 응답해야 한다.<br><br>대기자가 이 4시간 안에 응답하지 않으면 다음 대기자에게 안내가 간다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/03-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="4-기한의-기산점과-예외를-구분한다"></a>4. 기한의 기산점과 예외를 구분한다</th></tr>
<tr>
<td valign="top">승인 담당자는 알림함의 ‘수신 대기’ 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다. 다만 근무시간 밖에 제출된 건은 이 4시간 기한 대신 다음 영업일 12:00까지 수신 확인을 남겨야 한다.</td>
<td valign="top">- <strong>기본 기한:</strong> 승인 담당자는 알림함의 ‘수신 대기’ 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다.<br>- <strong>근무시간 밖에 제출된 건:</strong> 승인 담당자는 이 4시간 기한 대신 다음 영업일 12:00까지 수신 확인을 남겨야 한다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/04-kp.txt">모델 출력 원문</a></td>
<td valign="top"><strong>승인 담당자의 수신 확인 기한</strong><br><br><strong>기본 기한</strong><br>승인 담당자는 알림함의 &#x27;수신 대기&#x27; 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다.<br><br><strong>예외: 근무시간 밖에 제출된 건</strong><br>이 건에는 4시간 기한을 적용하지 않는다. 승인 담당자는 다음 영업일 12:00까지 수신 확인을 남겨야 한다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/04-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="5-실행-성공과-의미-오류를-구분한다"></a>5. 실행 성공과 의미 오류를 구분한다</th></tr>
<tr>
<td valign="top">변환 12건은 모두 정상 실행되었다. 그러나 의미 검토에서 2건의 취소 조건 누락을 찾았다. 담당자는 해당 2건을 보완해야 한다. 재검토 전에는 배포할 수 없다.</td>
<td valign="top">변환 12건은 모두 정상 실행됐다. 그러나 의미 검토에서 2건의 취소 조건 누락을 찾았다.<br><br>- <strong>보완:</strong> 담당자는 해당 2건을 보완해야 한다.<br>- <strong>배포:</strong> 재검토 전에는 배포할 수 없다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/05-kp.txt">모델 출력 원문</a></td>
<td valign="top">변환 12건은 모두 정상 실행되었다.<br>그러나 의미 검토에서 취소 조건 누락 2건이 발견되었다.<br>담당자는 해당 누락 2건을 보완해야 한다.<br>재검토 전에는 배포할 수 없다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/05-ste.txt">모델 출력 원문</a></td>
</tr>
<tr><th colspan="3" align="left"><a id="6-표기-없음과-지정-없음을-구분한다"></a>6. 표기 없음과 지정 없음을 구분한다</th></tr>
<tr>
<td valign="top">자료에는 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.</td>
<td valign="top">- <strong>담당자 표기:</strong> 자료에 없다.<br>- <strong>담당자 지정 여부:</strong> <strong>미확인</strong><br><br><a href="evaluation/readme-model-comparison-20261113/outputs/06-kp.txt">모델 출력 원문</a></td>
<td valign="top">자료에 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.<br><br><a href="evaluation/readme-model-comparison-20261113/outputs/06-ste.txt">모델 출력 원문</a></td>
</tr>
</tbody>
</table>

모바일에서는 표를 좌우로 이동해 세 열을 비교한다. 사례별 판정과 구조 차이는 [비교 기록](evaluation/readme-model-comparison-20261113/README.md)에 있다.

## L1~L4에서 출력 형식을 고른다

KP 코어를 L1 공통 기준으로 사용한다. 사용자가 형식을 지정하면 그 형식을 먼저 따른다.

| 단계 | 사용하는 경우 | 산출물 |
| --- | --- | --- |
| L1 | 기본값이다. | KP 문단·목록·절차 |
| L2 | 구조·흐름을 설명하거나 세 항목 이상을 비교한다. | 표·Mermaid·ASCII 도식 |
| L3 | 변수·상태를 바꿔야 이해되거나 사용자가 요청할 때 사용한다. | 외부 의존성 없는 단일 `index.html` |
| L4 | 사용자가 영상·애니메이션을 명시 요청할 때만 사용한다. | Manim 코드와 장면별 한국어 내레이션 |

[규칙 대응표](docs/spec/output-formats-rule-map.md)는 기존 핵심 규칙 25개의 보존을 설명한다. 비교 도구는 [출력 형식 평가 안내](evaluation/output_formats/README.md)에 있다.

## 설치한다

**설치 기준은 태그 `v0.11.1`이다.** 사용할 호스트에 설치를 요청한다.

두 곳 모두 설치하려면 Codex와 Claude Code를 명시한다.

```text
https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
태그 v0.11.1을 기준으로 Korean Protocol 스킬을 사용자 범위에 설치해줘.
skills/korean-protocol/SKILL.md의 SHA-256을 확인해줘.
기준 해시: 19ae7744da1d469225552b49e4108e52664f4f931c278d9f667c5ae7a4443604
태그가 없거나 해시가 다르면 설치를 멈추고 결과를 알려줘.
다른 프로젝트에서도 호출할 수 있게 하고 자동 호출은 꺼줘.
기존 0.7 상시 설치가 있으면 같은 설치의 관리 명령으로 규약만 OFF로 전환해줘.
높임말·자동 갱신·신뢰 키와 다른 사용자 지침은 보존해줘.
기존 스킬 폴더는 덮어쓰기 전에 차이를 확인하고 설치·발견·호출 결과를 알려줘.
```

설치는 수동이며 자동 갱신기는 없다.
설치 파일은 v0.11.0과 같은 13개다. 바뀐 파일은 5개다.

| 파일 | 역할 |
| --- | --- |
| `SKILL.md` | 코어 지침을 담는다. |
| `references/interactive-html.md` | HTML 작성 지침을 담는다. |
| `references/output-formats.md` | 출력 형식 지침을 담는다. |
| `assets/interactive-explainer.html` | 재사용 HTML 예제를 제공한다. |
| `scripts/check_html.py` | HTML 진단을 수행한다. |

설치 위치와 검증 절차는 [설치 안내](INSTALL.md)에 있다. **0.7 ZIP과 `agent_install.py install`은 이 스킬을 설치하지 않는다.**

## v0.11.1을 호출한다

| 호스트 | 새 대화에 입력한다. |
| --- | --- |
| Codex | `$korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |
| Claude Code | `/korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |

- 원문을 붙이거나 파일을 지정한다.
- 새 글은 `이번 작업의 완료 보고를 작성해줘`처럼 요청한다.
- 높임말이 필요하면 `높임말로 써줘`를 덧붙인다. 지정이 없으면 높임 없이 쓴다.
- Claude Code에서는 `/korean-protocol`을 메시지 맨 앞에 쓴다.

## 적용을 확인하고 끈다

1. **스킬 목록에서 `korean-protocol`을 확인한다.**
   없으면 호스트를 다시 시작한다.
2. **짧은 원문으로 호출하고 출력을 확인한다.**
   원문의 조건과 기한이 남았는지 확인한다. 핵심 판단이 앞에 있는지 확인한다.
3. **적용을 끄려면 새 대화에서 호출하지 않는다.**
   이미 읽힌 규약은 해당 대화에 남는다.

모델이 “적용했다”고 말한 것만으로 확인하지 않는다. 파일·발견·출력 확인 방법은 [호출 확인 안내](docs/distribution/on-demand-skill.md#설치와-호출을-확인한다)에 있다.

## 과거 검증 기록을 확인한다

v0.9.0은 정식 3자 비교를 완료했지만 수락 기준을 통과하지 못했다. 의미 실패 2건과 미해결 2건이 남았다. Opus 두 설정에서는 STE보다 명료성 승수가 적었다.

- **v0.9.0:** 조건별 결과는 [60차 비교 기록](evaluation/clarity-20261016-r60/README.md)에 있다.
- **v0.8.0:** [세션 보고서 비교](evaluation/session-reports-20261015/README.md)를 보존한다.
- **v0.10.0·v0.10.1:** [변경·검증 상태](docs/distribution/output-formats-candidate-status.md)에 정식 비교 미완료와 진단 범위를 기록한다.

## 버전 이력

| 버전 | 형태 | 상태 |
| --- | --- | --- |
| **v0.11.1** | 호출형 스킬 | 현재 권장이다. L1~L4 출력 지침과 참조 읽기 의무를 정의했다. 형식 준수 진단을 기록했으며 정식 3자 비교는 미완료다. |
| v0.11.0 | 호출형 스킬 | 이전 버전이다. 읽는 형태를 다듬었다. 진단용 파일럿을 거쳤으며 정식 3자 비교는 미완료다. |
| v0.10.1 | 호출형 스킬 | 이전 버전이다. 높임말 없는 짧은 문장, 보고용 앞부분과 부록, HTML·영상 표현 기준을 다듬었다. 정식 3자 비교는 완료하지 않았다. |
| v0.10.0 | 호출형 스킬 | 이전 버전. L1~L4 출력 형식을 추가했다. 정식 3자 비교는 완료하지 않았다. |
| v0.9.0 | 호출형 스킬 | 이전 버전. [60차 비교](evaluation/clarity-20261016-r60/README.md) 결과를 따르며 수락 기준은 통과하지 못했다. |
| v0.8.0 | 호출형 스킬 | 이전 버전. [세션 보고서 비교](evaluation/session-reports-20261015/README.md) |
| 중간본 `909dc9d` | 호출형 스킬 | v0.7.0과 v0.8.0 사이의 첫 스킬 검증본이다. 번호를 붙이지 않았다. [평가 기록](evaluation/field-report-20261015/README.md#보완-후보의-검증-범위를-밝힌다) |
| v0.7.0 | 상시 지침·서명 배포 | 기존 사용자 유지용. 원본 `0.7.0-draft`, 서명 콘텐츠 `0.7.0·순번 3`, 엔진 `0.2.0`. [릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0) · [채택 기록](experiments/v7/adoption.md) |

평가 기록의 `r10`·`r11`·`r12`는 실험 회차 번호이며 공개 버전 번호가 아니다. `r10`은 중간본 `909dc9d`, `r12`는 v0.8.0이다. `r11`은 채택하지 않은 실험 후보다. `clarity-20261016-r60`은 v0.9.0의 후보다. `output_formats`의 `run-01`~`run-11`은 v0.10.0 출력 형식 개편의 평가 회차다.

## 문서를 찾는다

| 목적 | 문서 |
| --- | --- |
| 설치·호출·전환 | [설치 안내](INSTALL.md) · [처음 사용](docs/distribution/quick-start.md) · [호출 확인](docs/distribution/on-demand-skill.md) · [호스트 지원](docs/distribution/host-support.md) |
| 평가 기록 | [v0.11.1 형식 준수 진단](evaluation/kp-v0111-output-formats-20261113/README.md) · [v0.11.0 진단용 파일럿](evaluation/kp-lean-pilot-20261113/README.md) · [평가 규칙](evaluation/README.md) · [v0.10.0 출력 형식 평가](evaluation/output_formats/README.md) · [v0.9.0 60차 비교](evaluation/clarity-20261016-r60/README.md) · [v0.8.0 세션 보고서 비교](evaluation/session-reports-20261015/README.md) |
| 규칙과 어휘 | [한국어 세부 규칙](docs/spec/korean-rules.md) · [통제 어휘](docs/spec/lexicon.md) |
| 기존 v0.7.0 관리 | [관리 설정](docs/distribution/application-controls.md) · [배포 계약](docs/distribution/README.md) · [채팅 안내](distribution/CHAT-START.md) |
| 설계와 근거 | [문서 목차](docs/README.md) · [검증 상태](docs/status/requirements.md) · [연구 근거](docs/research-basis.md) |

## 참고

직접 작성한 코드·규약·사전·문서는 [MIT License](LICENSE)로 제공한다. 제3자 자료의 권리는 [NOTICE.md](NOTICE.md)에 구분했다.
