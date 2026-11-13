# Korean Protocol v0.11.1의 호스트 지원 범위

호스트 설치·발견·호출 검사는 작성 품질 비교와 구분한다.

- **설치 기준:** 태그 `v0.11.1`을 사용한다.
- **SKILL.md SHA-256:** `19ae7744da1d469225552b49e4108e52664f4f931c278d9f667c5ae7a4443604`이다.

**신규 사용자는 [v0.11.1 스킬](../../INSTALL.md)을 사용자 범위에 수동 설치한다.** 자동 호출은 꺼져 있다. 자동 갱신기는 없다.

## 스킬 설치 위치와 확인 범위를 구분한다

| 호스트 | 사용자 설치 위치와 호출 | 기존 확인 범위 |
| --- | --- | --- |
| Codex | `~/.agents/skills/korean-protocol`에서 `$korean-protocol`로 호출한다. | 중간본 `909dc9d` 설치 때 로컬 macOS의 두 임시 작업 폴더에서 발견·호출을 확인했다. |
| Claude Code | `~/.claude/skills/korean-protocol`에서 `/korean-protocol`로 호출한다. | 중간본 `909dc9d` 설치 때 로컬 macOS에서 슬래시 명령 등록·호출을 확인했다. |
| 다른 기기·원격·클라우드 | 해당 호스트에 별도로 설치한다. | 각 호스트의 설치·발견·호출을 별도로 확인한다. |

Claude Code는 `CLAUDE_CONFIG_DIR`이 있으면 그 아래 `skills/`를 사용한다. 두 호스트는 같은 규약 본문을 사용한다. Claude Code에는 수동 호출용 YAML 설정을 추가한다.

설치 파일은 v0.11.0과 같은 13개다. 바뀐 파일은 5개다.

| 파일 | 역할 |
| --- | --- |
| `SKILL.md` | 코어 지침을 담는다. |
| `references/interactive-html.md` | HTML 작성 지침을 담는다. |
| `references/output-formats.md` | 출력 형식 지침을 담는다. |
| `assets/interactive-explainer.html` | 재사용 HTML 예제를 제공한다. |
| `scripts/check_html.py` | HTML 진단을 수행한다. |

L2~L4를 선택하면 작성 전에 지정한 참조 파일을 읽는다.

| 검사 | v0.11.1에 적용할 범위 |
| --- | --- |
| 파일 검사 | 태그와 `SKILL.md` 해시를 대조한다. |
| 발견·호출 검사 | 위 중간본 기록과 별도로 새 세션에서 확인한다. |
| 품질 비교 | [파일럿 결과와 한계](output-formats-candidate-status.md)를 따른다. 정식 비교는 **미완료**다. |

다른 운영체제에서는 실제 호스트 검증을 수행하지 않았다.

## 기존 0.7 관리 도구의 범위를 확인한다

이하 설명은 **기존 0.7 상시 지침·서명 설치기**에만 적용한다. 스킬 전환에는 [0.7 OFF 절차](../../INSTALL.md#기존-07-상시-지침에서-전환한다)를 사용한다. 기존 일반 설치 도구는 Codex·Claude Code를 지원한다. 규약 콘텐츠 0.7.0은 엔진 0.2.0 이상을 요구하며 규칙·사전 데이터 schema는 1.0이다. 설치 파일 검증·호스트 로딩·모델 준수는 각각 확인한다.

## 호스트의 적용 경로를 구분한다

| 호스트 | 설치·적용 경로 | 확인 경계 |
| --- | --- | --- |
| Codex CLI | 사용자 CODEX_HOME의 선택된 AGENTS 파일 또는 프로젝트 AGENTS 파일에 관리 블록을 넣는다. | 실제 선택 파일·override·프로젝트 체인 예산을 확인한다. 과거 로더 결과를 최신 버전 전체 준수로 확대하지 않는다. |
| Claude Code | 사용자 설정의 `rules/korean-protocol.md` 또는 프로젝트 `.claude/rules/korean-protocol.md`에 관리 블록을 넣는다. | 기존 CLAUDE.md·다른 본문은 보존하며 경로 제한 YAML frontmatter가 있으면 설치를 거부한다. |
| Codex desktop·IDE 로컬 작업 | 실제 사용하는 사용자 홈·원격 호스트·프로젝트 위치를 확인해 같은 파일 adapter를 사용한다. | CLI 설치만으로 다른 기기·원격·Cloud에도 적용됐다고 보고하지 않는다. 각 앱 로딩은 별도 확인이다. |
| Codex Cloud | cloud checkout의 프로젝트 지침을 대상으로 한다. | 로컬 사용자 홈이 자동 전달되지 않으며 자동 연결은 제공하지 않는다. |
| Gemini CLI | 저수준 런타임의 사용자·프로젝트 GEMINI.md adapter를 제공한다. | 실제 Gemini 호스트 로딩은 검증하지 않았다. 일반 설치 메뉴의 지원 대상이 아니다. |
| Cursor Agent | 현재 자동 설치 adapter를 제공하지 않는다. | 설계상의 .mdc 경로를 실행 가능한 설치 지원으로 표시하지 않는다. |
| ChatGPT | [채팅 안내](../../distribution/CHAT-START.md)에 따라 프로젝트에 전체 파일과 시작 지침을 저장한다. | 첨부한 복사본은 로컬 updater로 갱신되지 않는다. 계정 UI·실제 응답은 별도 확인이다. |
| Claude·Gemini 일반 채팅과 자체 앱 | 파일 첨부·지침 주입의 실제 지원 범위를 확인해 수동 연결한다. | 계정 설정 자동 변경·공식 동기화·출력 차단 필터는 제공하지 않는다. |

Codex·Claude Code의 에이전트 설치 도구는 사용자 범위만 관리한다. 프로젝트 설치는 [저수준 런타임](implementation-status.md)의 별도 상태 폴더·프로젝트 절대 경로를 사용한다. 기존 홈은 CODEX_HOME·CLAUDE_CONFIG_DIR 또는 명시 옵션으로 정하며 대상이 달라지면 자동 이동하지 않는다.

## 운영체제의 실행 범위를 확인한다

| OS | 현재 경로 | 미확인·미지원 범위 |
| --- | --- | --- |
| macOS | Python 3.9+·POSIX 파일 보호·OpenSSH 검증을 사용한다. 서명 설치는 시작 wrapper·launchd 예약·자동 조회 OFF를 선택한다. | 등록·실행·해제의 기존 증거와 실제 재로그인·물리적 절전 복귀·최신 모델 준수는 구분한다. |
| Linux | POSIX 설치·OpenSSH 검증·시작 wrapper 또는 자동 조회 OFF를 사용한다. | systemd 예약 생성·등록은 제공하지 않는다. CI 자동시험과 실제 사용자의 장기 운영은 구분한다. |
| Windows | 자동 설치를 지원하지 않는다. | ACL·reparse point·원자 교체·Task Scheduler 경로를 현재 지원으로 표시하지 않는다. |

서명 설치에는 OpenSSH가 필요하고 미서명 로컬 snapshot에는 Python·POSIX가 필요하다. 설치기는 Python·암호 패키지를 자동 설치하지 않는다. OS별 실제 CI 실행 결과는 해당 실행으로 확인하며 시험 구성만으로 통과했다고 표시하지 않는다.

## 프로필 예산과 실제 로딩을 구분한다

콘텐츠 파일은 총 7개다. 프로필 3개·규칙 JSON·사전 JSON 2개·규약 본문으로 구성한다. 프로필은 72개 규칙의 요구·조건·예외를 담으며 사전·전체 규약은 검증 캐시의 로컬 경로로 참조한다. 참조만으로 매 응답에서 사전 전체를 읽는다고 가정하지 않는다.

엔진 0.2.0의 프로필 본문 상한은 30 KiB, 관리 블록은 32 KiB, 최종 대상 파일은 4 MiB다. 이를 모델 토큰 수로 표시하지 않는다. 실제 Codex 프로젝트 체인의 잔여 예산도 검사하며 사용자 설정이나 기존 지침을 자동 축소·확대하지 않는다.

Codex 사용자 지침은 프로젝트 체인의 예산 합계에 넣지 않는다. 프로젝트에서는 가까운 Git marker부터 대상 디렉터리까지 선택 파일을 합산한다. top-level 정수 설정만 해석하며 custom fallback·project_root_markers 등 발견 규칙은 자동 추측하지 않는다. 더 깊은 작업 디렉터리·다른 버전·앱별 다중 root는 별도 확인이다.

## 검증된 설치본과 고정 패키지를 사용한다

기존 0.7 관리 도구는 상태 검사를 통과한 대상 관리 본문을 사용한다. 활성 캐시의 `profiles/coding-agent.md`·`lexicon/`도 참조한다. 규약 OFF나 복구 필요 상태를 정상 적용으로 보고하지 않는다. 파일 변경으로 이미 읽은 대화 지침을 지울 수 없으므로 새 세션에서 확인한다.

공개 [v0.7.0 패키지](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)는 `7e01d53`의 고정 산출물이다. 안내도 해당 버전을 기준으로 확인한다. 콘텐츠 자동 갱신은 실행 도구나 웹에 올린 사본을 교체하지 않는다.

[Codex 로더 증거](codex-loader-evidence.json), [Claude 로더 증거](claude-loader-evidence.json), [0.7.0 공개 갱신 기록](public-0.7.0-verification.md)은 각 당시 환경·버전·검사 범위를 기록한다. 과거 72개 규칙 로딩을 모든 모델의 준수나 사람의 이해도 개선으로 확대하지 않는다. 설치는 [INSTALL.md](../../INSTALL.md), 설정은 [적용 설정](application-controls.md), 연구 검증은 [현재 상태](../status/requirements.md)를 따른다.
