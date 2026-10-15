# Korean Protocol

**한국어 답변에서 대상·판단·조건·기한을 바로 찾게 한다.**

Korean Protocol(KP)은 **LLM의 한국어 답변 작성 규약**이다. 현재 배포본은 Codex·Claude Code가 읽는 **사용자 지침에 설치**한다. 별도로 호출하는 스킬이나 모델이 아니며 `/kp` 같은 전용 명령도 없다.

[처음 사용하기](docs/distribution/quick-start.md) · [설치하기](INSTALL.md) · [세 열 예문 비교](#문장과-구조를-함께-다듬는다) · [ON/OFF 설정](docs/distribution/application-controls.md)

## 설치 후에는 평소처럼 요청한다

1. **설치한 Codex·Claude Code에서 새 대화를 시작한다.**
2. **평소처럼 작업을 요청한다.** 규약이 ON이면 매번 “KP 적용”을 붙이지 않아도 된다.
3. **답변의 대상·조건·수치·기한을 확인한다.** 설치 확인과 실제 답변의 규칙 준수는 별개다.

새 문서를 요청할 때는 다음처럼 쓴다.

> 이 회의록에서 결정 사항, 담당자, 기한을 정리해줘.

기존 문서를 고치려면 다음처럼 쓴다.

> 아래 보고서를 Korean Protocol 기준으로 정리해줘. 사실·조건·수치·출처는 유지해줘.

설치한 호스트와 적용 범위에서 사용한다. 로컬 Codex에 설치해도 ChatGPT·다른 기기·원격 환경에 자동으로 전달되지는 않는다. ChatGPT에서는 [규약 파일과 프로젝트 지침](distribution/CHAT-START.md)을 설정한 뒤 해당 프로젝트에서 사용한다.

## 적용 여부를 확인한다

설치한 코딩 에이전트에 다음 내용을 요청한다.

```text
설치된 Korean Protocol의 버전, 적용 대상, ON/OFF와 높임말 설정을 확인해줘.
설정은 바꾸지 말고 파일 검증 결과와 현재 대화의 로딩 확인 여부를 구분해 알려줘.
확인할 수 없는 항목은 확인하지 못했다고 표시해줘.
```

확인 결과에서 규약이 ON이고 설치 대상·콘텐츠 검증이 정상인지 확인한다. 이어 아래 예문 하나를 정리하게 해 조건·기한이 유지되는지 살펴본다. “적용 중”이라는 모델의 답변만으로 설치·로딩을 확인하지 않는다. 자세한 [상태 확인 기준](docs/distribution/application-controls.md#상태를-구분한다)을 따른다.

## ON/OFF와 높임말을 바꾼다

아래 문구는 **설정 변경을 에이전트에 맡기는 요청**이다. 설치된 프로그램이 자동 인식하는 단축 명령은 아니다. 원하는 행 하나를 요청한 뒤 **새 대화에서 확인**한다.

| 원하는 설정 | 설치한 코딩 에이전트에 요청한다. |
| --- | --- |
| 규약을 끈다. | “설치된 Korean Protocol을 OFF로 설정하고 상태를 확인해줘. 높임말·자동 갱신 설정은 유지해줘.” |
| 규약을 켠다. | “설치된 Korean Protocol을 ON으로 설정하고 상태를 확인해줘. 높임말·자동 갱신 설정은 유지해줘.” |
| 높임말을 켠다. | “Korean Protocol의 높임말만 ON으로 설정해줘.” |
| 높임말을 끈다. | “Korean Protocol의 높임말만 OFF로 설정해줘.” |

신규 설치는 **규약 ON·높임말 OFF**로 시작하며 기존 설치의 선택은 보존한다. 규약 OFF는 자동 갱신을 끄지 않는다. 이번 답변에만 문체를 달리하려면 “이번 답변만 높임말로 써줘”처럼 요청하며 설치 설정은 바꾸지 않는다. 터미널 명령은 [적용 설정](docs/distribution/application-controls.md), ChatGPT의 전환 방법은 [채팅 안내](distribution/CHAT-START.md)를 따른다.

## 처음 한 번 설치한다

Codex 또는 Claude Code에 다음 내용을 전달한다.

```text
https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
지금 사용하는 코딩 에이전트의 사용자 범위에 서명된 Korean Protocol을 설치해줘.
macOS에서는 예약 자동 갱신을 등록해줘.
설치 버전, 적용 대상, ON/OFF와 갱신 연결 상태를 확인해줘.
```

| 다른 사용 경로 | 시작 방법 |
| --- | --- |
| ChatGPT에서 사용한다. | [KOREAN-PROTOCOL.md](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md)를 받고 [채팅용 시작 안내](distribution/CHAT-START.md)를 따른다. |
| 인터넷 없이 설치한다. | [0.7.0 ZIP](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)을 받아 [오프라인 안내](distribution/START-HERE.md)를 따른다. |
| 기존 설치를 갱신한다. | [관리 도구 갱신 절차](INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)를 따른다. 기존 경로·신뢰·표현·자동 갱신 선택을 유지한다. |

## 문장과 구조를 함께 다듬는다

아래 여섯 사례는 **직접 작성한 설명용 예문**이며 실제 모델 실행 결과나 우열 평가가 아니다. 세 열에서 같은 사실·조건·수치·확실성을 유지한다.

**STE 참고 열**은 [ASD-STE100 공식 설명](https://asd-ste100.org/STE_faq.html)의 짧은 문장·능동 표현·조건 우선 배치를 한국어에 적용한 작성 예다. STE는 영어 규격이므로 이 열을 공식 한국어판이나 영어 어휘·문법 규칙을 충족한 결과로 표시하지 않는다. 각 열의 정보 배치와 한국어 끝맺음을 비교한다.

[대상 목록](#1-반납-대상을-먼저-찾는다) · [신청 방식](#2-신청-방식별-조건을-묶는다) · [조건부 처리](#3-조건과-후속-처리를-묶는다) · [기한 예외](#4-기한의-기산점과-예외를-구분한다) · [실패 보고](#5-실행-성공과-의미-오류를-구분한다) · [미확인 상태](#6-표기-없음과-지정-없음을-구분한다)

<table>
<thead>
<tr><th width="33%" scope="col">원문</th><th width="33%" scope="col">Korean Protocol 0.7</th><th width="33%" scope="col">STE 원칙 적용<br>한국어 참고</th></tr>
</thead>
<tbody>
<tr><th colspan="3" align="left"><a id="1-반납-대상을-먼저-찾는다"></a>1. 반납 대상을 먼저 찾는다</th></tr>
<tr>
<td valign="top">반납 대상은 노트북, 모니터, 출입카드이며 접수 담당은 총무팀이다. 접수 마감은 7월 5일 18:00이다.</td>
<td valign="top"><strong>반납 대상</strong><br>· 노트북<br>· 모니터<br>· 출입카드<br><br>접수 담당: 총무팀<br>접수 마감: <strong>7월 5일 18:00</strong></td>
<td valign="top"><strong>반납 대상</strong><br>· 노트북<br>· 모니터<br>· 출입카드<br><br>접수 담당은 총무팀이다.<br>접수 마감은 <strong>7월 5일 18:00</strong>이다.</td>
</tr>
<tr><th colspan="3" align="left"><a id="2-신청-방식별-조건을-묶는다"></a>2. 신청 방식별 조건을 묶는다</th></tr>
<tr>
<td valign="top">교육 신청은 포털 신청과 부서 취합으로 나뉜다. 참석자가 20명 이상인 정기 과정은 본인이 포털에서 직접 신청하며 마감은 마감일 18:00이다. 소규모 실습이나 외부 강사 과정은 부서 담당자가 명단을 취합해 과정 시작 5영업일 전까지 제출한다. 법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.</td>
<td valign="top"><strong>포털 신청</strong><br>· 대상: 참석자 <strong>20명 이상인 정기 과정</strong><br>· 신청: 본인이 포털에서 직접 신청<br>· 마감: <strong>마감일 18:00</strong><br><br><strong>부서 취합</strong><br>· 대상: 소규모 실습 또는 외부 강사 과정<br>· 제출: 부서 담당자가 명단 취합 후 제출<br>· 기한: <strong>과정 시작 5영업일 전까지</strong><br><br><strong>공통 규칙</strong><br>법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.</td>
<td valign="top"><strong>포털 신청</strong><br>참석자가 <strong>20명 이상인 정기 과정</strong>에 사용한다.<br>본인이 포털에서 직접 신청한다.<br>마감은 <strong>마감일 18:00</strong>이다.<br><br><strong>부서 취합</strong><br>소규모 실습 또는 외부 강사 과정에 사용한다.<br>부서 담당자가 명단을 취합한다.<br>부서 담당자가 <strong>과정 시작 5영업일 전까지</strong> 명단을 제출한다.<br><br><strong>공통 규칙</strong><br>법정 의무교육 대상자의 누락 여부는 신청 방식과 관계없이 자동 확인한다.</td>
</tr>
<tr><th colspan="3" align="left"><a id="3-조건과-후속-처리를-묶는다"></a>3. 조건과 후속 처리를 묶는다</th></tr>
<tr>
<td valign="top">확정자가 이용 24시간 전까지 취소하면 다음 대기자에게 자동 안내가 간다. 안내받은 대기자는 안내 수신 후 4시간 안에 응답해야 한다. 이 기한 안에 응답하지 않으면 다음 대기자에게 안내가 간다.</td>
<td valign="top"><strong>확정자가 이용 24시간 전까지 취소한 경우</strong><br>1. 다음 대기자에게 자동 안내가 간다.<br>2. 안내받은 대기자는 <strong>안내 수신 후 4시간 안에</strong> 응답해야 한다.<br>3. 이 기한 안에 미응답 시 다음 대기자에게 안내가 간다.</td>
<td valign="top"><strong>확정자가 이용 24시간 전까지 취소한 경우</strong><br>1. 다음 대기자에게 안내가 자동으로 간다.<br>2. 안내받은 대기자는 <strong>안내 수신 후 4시간 안에</strong> 응답해야 한다.<br>3. 대기자가 이 기한 안에 응답하지 않으면 다음 대기자에게 안내가 간다.</td>
</tr>
<tr><th colspan="3" align="left"><a id="4-기한의-기산점과-예외를-구분한다"></a>4. 기한의 기산점과 예외를 구분한다</th></tr>
<tr>
<td valign="top">승인 담당자는 알림함의 ‘수신 대기’ 목록을 확인한 뒤 4시간 안에 수신 확인을 남겨야 한다. 다만 근무시간 밖에 제출된 건은 이 4시간 기한 대신 다음 영업일 12:00까지 수신 확인을 남겨야 한다.</td>
<td valign="top"><strong>수신 확인</strong><br>담당: 승인 담당자<br>조치: 수신 확인을 남겨야 한다.<br><br><strong>기본 기한</strong><br>알림함의 ‘수신 대기’ 목록을 <strong>확인한 뒤 4시간 안에</strong><br><br><strong>근무시간 밖 제출 건</strong><br>기본 기한 대신 <strong>다음 영업일 12:00까지</strong></td>
<td valign="top"><strong>수신 확인</strong><br>승인 담당자는 다음 기한까지 수신 확인을 남겨야 한다.<br><br>· 기본 기한: 알림함의 ‘수신 대기’ 목록을 <strong>확인한 뒤 4시간 안에</strong>.<br>· <strong>근무시간 밖에 제출된 건</strong>: 기본 기한 대신 <strong>다음 영업일 12:00까지</strong>.</td>
</tr>
<tr><th colspan="3" align="left"><a id="5-실행-성공과-의미-오류를-구분한다"></a>5. 실행 성공과 의미 오류를 구분한다</th></tr>
<tr>
<td valign="top">변환 12건은 모두 정상 실행되었다. 그러나 의미 검토에서 2건의 취소 조건 누락을 찾았다. 담당자는 해당 2건을 보완해야 한다. 재검토 전에는 배포할 수 없다.</td>
<td valign="top"><strong>의미 오류: 2건의 취소 조건 누락</strong><br><br>· 실행: 변환 <strong>12건 모두 정상 실행</strong><br>· 조치: 담당자는 해당 <strong>2건을 보완해야 한다.</strong><br>· 배포: <strong>재검토 전에는 불가</strong></td>
<td valign="top"><strong>의미 오류</strong><br>의미 검토에서 <strong>2건의 취소 조건 누락</strong>을 찾았다.<br><br>· 변환 <strong>12건은 모두 정상 실행</strong>되었다.<br>· 담당자는 해당 <strong>2건을 보완해야 한다.</strong><br>· <strong>재검토 전에는 배포할 수 없다.</strong></td>
</tr>
<tr><th colspan="3" align="left"><a id="6-표기-없음과-지정-없음을-구분한다"></a>6. 표기 없음과 지정 없음을 구분한다</th></tr>
<tr>
<td valign="top">자료에는 담당자가 표기되어 있지 않다. 담당자가 지정되었는지는 확인하지 못했다.</td>
<td valign="top"><strong>자료에 표기된 담당자 없음.</strong><br>담당자 지정 여부는 미확인.</td>
<td valign="top">자료에 담당자가 표기되어 있지 않다.<br>담당자 지정 여부는 확인하지 못했다.</td>
</tr>
</tbody>
</table>

문장이 이미 짧고 명확하면 그대로 둔다. 길이를 줄이기 위해 필요한 뜻이나 조건을 없애지 않으며, STE 참고 열도 차이를 만들기 위해 불필요하게 늘리지 않는다. 모바일에서는 표를 좌우로 이동해 세 열을 비교한다.

## 현재 버전과 검증 범위를 밝힌다

공개 배포본 `0.7.0`은 원본 `0.7.0-draft`에서 만들었다. `draft`는 연구·개발 품질 범위를 나타내며 저장소 비공개나 릴리스 게시 대기를 뜻하지 않는다.

| 항목 | 현재 상태 |
| --- | --- |
| 원본 버전 | **0.7.0-draft**이며 규칙 72개·규칙 작성자 사례 296개·사전 193뜻을 제공한다. V7 이전 보완본 **r2**의 구조 규칙을 채택했다. |
| 채택 기준 | 사용자가 r2의 가독성을 선택했으며 더 짧게 만든 r3는 채택하지 않았다. |
| 콘텐츠 발행 | **0.7.0·순번 3**을 공개했고 두 호스트의 서명 HTTPS 갱신과 기존 로컬 설치 갱신을 [검증했다](docs/distribution/public-0.7.0-verification.md). |
| 기능 대응 | 현행 대응표는 설계 49개·검증 0개·부분 4개다. 이전 49/53 독립 검토를 현재 검증 점수로 사용하지 않는다. |
| 효과 검증 | V7 실험의 의미 변경·미확정 결과가 남아 있으며 실제 독자 시험은 수행하지 않았다. |

[채택 기록](experiments/v7/adoption.md)은 결정과 한계를, [고정 실험 기록](experiments/v7/README.md)은 당시 프로필과 실패 집계를 보존한다. 사용자 선택은 모든 출력의 의미 보존이나 독자 이해 효과를 입증한 결과가 아니다. 0.3.0 당시의 기능 대응 49/53과 모델 평가를 포함한 근거는 [연구·검증 기록](docs/status/research-evidence.md)에 모았다.

## 필요한 문서를 찾는다

| 목적 | 문서 |
| --- | --- |
| 규칙과 예외를 확인한다. | [한국어 세부 규칙](docs/spec/korean-rules.md) · [통제 어휘](docs/spec/lexicon.md) |
| 설치와 적용 설정을 관리한다. | [설치 안내](INSTALL.md) · [규약·높임말 설정](docs/distribution/application-controls.md) · [호스트 지원표](docs/distribution/host-support.md) |
| 설계와 근거를 검토한다. | [문서 목차](docs/README.md) · [검증 상태](docs/status/requirements.md) · [연구 근거](docs/research-basis.md) |

Korean Protocol은 ASD-STE100의 간결한 기술 문체에서 출발한 독립 규약이며 번역본이나 공식 한국어판이 아니다. 영어의 단어 수 제한을 한국어 어절 수로 옮기지 않는다. 직접 작성한 코드·규약·사전·문서는 [MIT License](LICENSE)로 제공하며 제3자 자료의 권리는 [NOTICE.md](NOTICE.md)에 구분했다.
