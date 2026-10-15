# Korean Protocol

**한국어 답변에서 대상·판단·조건·기한을 바로 찾게 한다.**

Korean Protocol(KP)은 **필요한 작업에서 호출하는 한국어 작성 스킬**이다. 별도 모델이나 출력 후 필터가 아니며, 사용자가 선택한 글을 의미·조건을 유지하면서 정리한다. Codex·Claude Code의 **사용자 범위에 설치하면 다른 프로젝트에서도 호출**할 수 있다.

현재 권장 경로는 검증한 보완 스킬이다. 기존 **0.7.0 상시 지침·서명 배포본과는 별개**이며, 새 정식 버전 번호를 발행한 것은 아니다. 0.7 사용자는 [전환 절차](INSTALL.md#기존-07-상시-지침에서-전환한다)에 따라 상시 적용을 끈 뒤 스킬을 사용한다.

[설치하기](INSTALL.md) · [처음 사용하기](docs/distribution/quick-start.md) · [0.7에서 전환하기](INSTALL.md#기존-07-상시-지침에서-전환한다) · [검증 범위](evaluation/field-report-20261015/README.md#보완-후보의-검증-범위를-밝힌다)

## 처음 한 번 설치한다

사용할 Codex 또는 Claude Code에 다음을 복사한다. 두 곳 모두 설치하려면 두 호스트를 명시한다.

```text
https://github.com/project820/korean-protocol 의 INSTALL.md를 읽어줘.
검증한 Korean Protocol 보완 스킬을 지금 사용하는 호스트의 사용자 범위에 설치해줘.
다른 프로젝트에서도 호출할 수 있게 하고 자동 호출은 꺼줘.
기존 0.7 상시 설치가 있으면 같은 설치의 관리 명령으로 규약만 OFF로 전환해줘.
높임말·자동 갱신·신뢰 키와 다른 사용자 지침은 보존해줘.
기존 스킬 폴더는 덮어쓰기 전에 차이를 확인하고 설치·발견·호출 결과를 알려줘.
```

설치 위치·고정 커밋·파일 복사와 Claude Code용 설정은 [설치 안내](INSTALL.md)에 있다. **0.7 ZIP과 `agent_install.py install`은 새 스킬을 설치하지 않는다.**

## 새 대화에서 스킬을 호출한다

| 호스트 | 입력할 요청 |
| --- | --- |
| Codex | `$korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |
| Claude Code | `/korean-protocol 이 보고서를 정리해줘. 사실·조건·수치·출처는 유지해줘.` |

보고서 원문을 함께 붙이거나 파일을 지정한다. 새 글도 `이번 작업의 완료 보고를 작성해줘`처럼 요청할 수 있다. Claude Code에서는 `/korean-protocol`을 메시지 맨 앞에 쓴다.

자동 호출은 꺼 둔다. 사용하지 않을 때는 **새 대화에서 스킬을 호출하지 않는다.** 이미 읽힌 규약은 대화에 남으므로 “OFF”라는 말로 컨텍스트가 지워지는 것은 아니다. 높임말을 원하면 호출할 때 “높임말로 써줘”를 덧붙인다. 기존 0.7의 ON/OFF·높임말 관리 명령은 이 스킬의 설정이 아니다.

## 설치와 실제 출력을 확인한다

1. 새 대화의 스킬 목록에서 `korean-protocol`을 확인한다. 보이지 않으면 호스트를 다시 시작한다.
2. 위 호출문과 함께 짧은 원문을 정리하게 한다.
3. 원문의 대상·조건·기한이 남았는지, 필요한 목록과 판단이 앞에 나오는지 확인한다.

설치 파일, 호스트의 발견·로딩, 출력 품질은 별도 검사다. 모델이 “적용했다”고 말한 것만으로 세 검사를 통과했다고 판단하지 않는다. 구체적인 [확인 예문과 읽기 확인](docs/distribution/on-demand-skill.md#설치와-호출을-확인한다)을 제공한다.

검증한 스킬은 실전 보고서 2회·기존 예문 6건·추가 사례 8건의 의미·구조 검사를 통과했다. 임시 Codex의 전체 파일 읽기와 별도 출력도 확인했다. 개발 회귀 사례의 결과이며 모든 문서의 준수나 독해 속도 개선을 보장하지 않는다. 전체 규약과 공통 요청문은 **10,842토큰**으로 측정했으며, 호스트 지침·원문·대화 이력은 별도로 더해진다. [실행 조건과 한계](evaluation/field-report-20261015/README.md#보완-후보의-검증-범위를-밝힌다)를 공개한다.

스킬은 검증한 커밋에 고정해 수동으로 설치하며 자동 갱신하지 않는다. ChatGPT에는 로컬 스킬이 전달되지 않는다. ChatGPT에서 기존 0.7 파일을 사용하려면 [채팅 안내](distribution/CHAT-START.md)를 따른다.

## 문장과 구조를 함께 다듬는다

**아래 세 열은 기존 0.7과 STE 참고 방식의 과거 실행 결과다. 현재 보완 스킬의 출력으로 바꿔 표시하지 않는다.**

아래는 **기존 원문 6개를 Opus 5.5·medium에서 실제 변환한 결과**다. KP 0.7과 STE 원칙 적용본을 각각 한 번씩 생성했으며, **출력 12건을 추가로 교정하지 않았다.** 굵게 표시와 줄바꿈만 화면에 맞게 표시하며 각 셀에서 출력 원문을 열 수 있다.

**의미 검토는 11건 보존·1건 보류로 판정했다.** STE의 교육 신청 예문은 명단 제출자를 ‘신청자’로 표시했다. 원문에 두 역할의 관계가 정의되지 않아 이 표현은 보류했다.

KP에는 **0.7 배포 프로필과 사전 2개 전체**를 제공했다. 각 요청에는 해당 원문과 해당 조건의 지침만 넣었으며 기존 대화·설명용 답안은 넣지 않았다. [실행 조건·검토 결과](evaluation/readme-model-comparison-20261015/README.md)에서 입력과 출력 해시를 확인할 수 있다.

**STE 열**은 [ASD-STE100 공식 설명](https://asd-ste100.org/STE_faq.html)의 공개 원칙을 한국어에 적용한 실험이다. 영어 규격 전체의 준수 결과나 공식 한국어판은 아니다.

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

**이 표는 모범 답안이 아니라 실제 출력이다.** 문장·구조의 차이와 의미 보존 판정은 [사례별 검토](evaluation/readme-model-comparison-20261015/README.md)에서 구분한다. 모바일에서는 표를 좌우로 이동해 세 열을 비교한다.

## 현재 버전과 검증 범위를 밝힌다

현재 스킬은 커밋 `909dc9d`의 보완본을 사용한다. 아래 버전 표는 기존 상시 지침·서명 배포본의 이력이며 스킬 버전 표가 아니다.

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
| 설치와 적용 설정을 관리한다. | [스킬 설치·0.7 전환](INSTALL.md) · [기존 0.7 설정](docs/distribution/application-controls.md) · [호스트 지원표](docs/distribution/host-support.md) |
| 설계와 근거를 검토한다. | [문서 목차](docs/README.md) · [검증 상태](docs/status/requirements.md) · [연구 근거](docs/research-basis.md) |

Korean Protocol은 ASD-STE100의 간결한 기술 문체에서 출발한 독립 규약이며 번역본이나 공식 한국어판이 아니다. 영어의 단어 수 제한을 한국어 어절 수로 옮기지 않는다. 직접 작성한 코드·규약·사전·문서는 [MIT License](LICENSE)로 제공하며 제3자 자료의 권리는 [NOTICE.md](NOTICE.md)에 구분했다.
