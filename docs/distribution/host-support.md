# 호스트 지원과 적용 범위

현재 원본 0.7.0-draft는 V7 r2를 채택한다. 콘텐츠 0.7.0·순번 3의 [공개 발행·갱신 기록](public-0.7.0-verification.md)은 Codex·Claude Code의 서명 HTTPS 갱신과 기존 로컬 설치 갱신을 구분한다. 새 프로필의 구조 규칙도 기존 호스트 경로와 바이트 예산을 따른다.

아래 호스트 발견·loader 증거는 2026-10-12부터 수행한 당시 환경의 결과다. Codex·Claude Code·Gemini의 POSIX Markdown adapter는 구현했고 임시 파일로 설치를 시험했다. Codex는 [임시 사용자·프로젝트 설치와 실제 loader](../status/local-install-smoke.json)를 확인했다. 별도 [실제 모델 평가](../../evaluation/llm/candidate-validation-report.md)는 시험한 입력과 프로필의 결과이며 모든 호스트의 준수를 입증하지 않는다.

## 지원표

| 호스트 | 지속 지침 위치를 다음처럼 사용한다. | 갱신·적용 범위를 다음처럼 정한다. | 확인 상태를 다음처럼 구분한다. |
| --- | --- | --- | --- |
| Codex CLI | 사용자 `$CODEX_HOME/AGENTS.md` 또는 `~/.codex/AGENTS.md`, 프로젝트 `AGENTS.md`에 관리 블록을 넣는다. | 설치기가 실제 선택되는 파일을 확인한다. 새 실행에서 읽으며 기존 세션 갱신을 보장하지 않는다. | 당시 로컬 0.162.1의 loader에서 임시 사용자·프로젝트 설치의 72개 규칙을 확인했다. 이 수치는 V7 로딩 검증이 아니다. |
| Codex desktop·IDE의 로컬 작업 | 같은 home과 실제 프로젝트 루트를 쓰는 instruction adapter를 설계한다. | 앱의 로컬/원격 실행 위치별 파일 경로를 확인한다. desktop 설치만으로 cloud·다른 기기의 적용을 보장하지 않는다. | OpenAI 문서의 global/project 모델을 확인했다. 각 앱 loader·다중 root 적용은 실측 전이다. |
| Codex Cloud | 해당 cloud checkout의 프로젝트 `AGENTS.md`를 대상으로 한다. | 로컬 사용자 home은 전달되지 않는다. repository 반영이나 cloud setup의 로컬 배포 연결이 필요하다. | 로컬 updater가 cloud 파일을 자동 바꾼다고 표시하지 않는다. cloud setup 자동 연결은 v1 미지원이다. |
| Claude Code | 사용자 `~/.claude/rules/korean-protocol.md`, 프로젝트 `.claude/rules/korean-protocol.md`의 실제 파일을 사용한다. | `paths` frontmatter 없이 시작할 때 읽게 한다. 파일 import·외부 symlink 승인을 요구하는 구조를 피한다. | 사용자·프로젝트 규칙 파일 설치를 구현했다. Claude Code 2.1.296의 로컬 모의 요청에서 72개 규칙 로딩을 확인했으며 모델 준수·OpenCodex 경유 실제 추론은 별도다. |
| Gemini CLI | 사용자 `~/.gemini/GEMINI.md`, 프로젝트 `GEMINI.md`에 관리 블록을 넣는다. | 사용자·workspace·JIT 맥락 계층을 유지한다. 이름이 설정으로 바뀐 환경은 자동 추측하지 않고 명시 대상이 필요하다. | 공식 문서만 확인했다. 로컬 gemini 명령은 발견하지 못했다. |
| Cursor Agent | 설계상 프로젝트 `.cursor/rules/korean-protocol.mdc`에 `alwaysApply: true`와 본문을 둔다. | 현재 설치기의 자동 설치 대상이 아니다. 사용자 전역 Rules는 설정 화면에 프로필을 직접 넣어야 한다. | 공식 문서만 확인했다. Cursor Tab·Inline Edit 전역 적용은 지원하지 않는다. |
| ChatGPT Chat·Work 웹/모바일 | [채팅용 시작 안내](../../distribution/CHAT-START.md)에 따라 프로젝트에 `KOREAN-PROTOCOL.md`를 올리고 시작 지침을 저장한다. | 첨부한 복사본은 로컬 업데이트로 자동 바뀌지 않는다. 짧은 사용자 지침만으로 전체 규약과 사전이 설치됐다고 표시하지 않는다. | 공식 personalization·project 범위를 확인했다. 계정별 저장·첨부 제한과 실제 설정 UI·응답 준수는 시험 전이다. |
| Claude/Gemini 일반 채팅 웹·모바일 | 해당 앱이 제공하는 사용자 지침 UI용 프로필을 내보낸다. | 파일 경로를 제시하는 것만으로 읽기·갱신을 보장하지 않는다. | v1은 앱별 자동 adapter를 지원하지 않는다. 각 제품의 저장 지침 방식 확인이 필요하다. |
| 자체 LLM 앱·로컬 모델 | 앱 소유자가 로컬 profile을 앱의 지침 맥락에 연결한다. | 앱별 자동 연결과 출력 차단 필터는 제공하지 않는다. | provider별 연결과 tokenizer는 앱 소유자가 시험해야 한다. 설치기가 임의의 앱을 가로채지 않는다. |

웹/모바일에서도 자동 갱신이 필수라면 공식 쓰기 API 또는 앱이 허용한 동기화 기능이 추가로 필요하다. 그 지원이 확인되지 않은 앱에는 “한 번 설치하면 자동으로 최신화”라는 문구를 쓰지 않는다. 규약의 로컬 사용에는 어떤 LLM 앱도 필요하지 않는다.

## 실제 로드할 프로필과 예산

콘텐츠 pack은 `profiles/coding-agent.md`, `profiles/chat.md`, `profiles/work-document.md`, `specification/rules.json`, `lexicon/core.json`, `lexicon/domains/software.json`, `pack/protocol.md`의 일곱 파일로 고정한다. 설명 문서·원자료·Python 코드·tests는 자동 콘텐츠 갱신 대상에서 제외한다.

프로필은 규칙 requirement와 중요한 조건·예외를 실제 본문에 포함한다. 호스트가 자동 읽는 관리 블록에 프로필 전체를 넣으며 일부 요약만 공급한 것을 전체 규칙 공급으로 확대하지 않는다. 전문 사전·전체 용례는 검증 캐시의 로컬 절대 경로로 참조하며 그 참조 파일을 반드시 읽는다고 가정하지 않는다.

엔진 0.2.0은 각 핵심 프로필의 UTF-8 본문을 30 KiB(30,720 bytes), 마커·경로·호스트 wrapper를 포함한 관리 블록을 32 KiB(32,768 bytes) 이하로 제한한다. 범위가 넘으면 자르지 않고 컴파일·설치를 거부한다. 콘텐츠 0.7.0은 이 엔진 이상을 요구하며 기존 엔진은 [최신 설치 도구로 갱신](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)해야 한다. ChatGPT 설정 UI의 더 작은 제한은 별도 내보내기와 실제 저장 확인이 필요하다.

토큰 수는 모델·tokenizer에 따라 달라진다. 표준 라이브러리 설치기는 tokenizer를 포함하지 않으며 bytes 수를 토큰 수라고 표시하지 않는다. `status`는 정확한 bytes·대상 잔여 예산·`budget_kind`를 기록한다. `codex-project-chain-remaining`은 Codex 프로젝트 지침의 남은 상한이며 `installer-file-safety`는 설치기 자체의 파일 보호 상한이다. 토큰 예산을 요구하는 자체 앱은 자신의 tokenizer로 profile+다른 지침 합계를 계산해야 한다.

Codex의 `project_doc_max_bytes` 기본값은 32 KiB이다. 실제 Codex 0.162.1의 loader에서는 이 상한이 프로젝트 지침 체인에만 적용되며 global 지침은 합산하지 않는다. 설치기는 지정한 디렉터리에서 가장 가까운 `.git` directory/file까지 root→대상 체인의 선택된 파일 bytes를 합산하고, Git marker가 없으면 지정 디렉터리만 계산한다. override가 비어 있지 않으면 같은 위치의 일반 AGENTS 대신 선택한다. 연결용 blank line은 파일 bytes 예산에 추가하지 않는다. [임시 환경 loader 증거](codex-loader-evidence.json)는 cap 256에서 global 400/project 200과 root 128/child 128을 모두 읽었고 root 200/child 200은 child 끝을 잘랐다는 결과를 기록한다.

사용자 scope는 `project_doc_max_bytes`로 거부하지 않는다. 사용자 파일·프로젝트 파일 모두 최종 4 MiB, 관리 추가분 32 KiB라는 설치기 자체 보호 상한을 적용한다. 프로젝트 scope에서는 실제 프로젝트 체인의 잔여 상한도 적용한다. 내부 프로필·관리 블록 상한을 늘려도 Codex의 프로젝트 잔여 예산 검사는 그대로 유지한다. 기존 지침이나 `config.toml`을 줄이거나 바꾸지 않는다.

Python 3.9 adapter는 단순한 top-level 정수 설정을 읽으며 custom fallback과 project_root_markers 설정은 프로젝트 설치에서 거부한다. 명령행·프로필의 설정 override는 이 adapter가 자동 파악하지 않으므로 별도 확인이 필요하다. 다른 project root 규칙·지정 디렉터리보다 아래의 향후 작업 디렉터리·다른 host 버전·Cloud에서의 발견은 검증하지 않았다. 발견 순서와 설정 설명은 [OpenAI 공식 AGENTS.md 문서](https://learn.chatgpt.com/docs/agent-configuration/agents-md)에 따른다.

## 사용자·프로젝트 우선순위

Codex는 전역 지침을 먼저 읽고 프로젝트 root부터 작업 디렉터리까지 뒤의 지침을 연결한다. `AGENTS.override.md`가 선택되면 같은 위치의 `AGENTS.md`는 적용되지 않으므로 설치기는 선택된 파일을 표시하고 승인을 받은 명시 범위 안에서만 관리한다. 조직·호스트 지침과 사용자 요청은 규약의 문체 선호보다 우선한다.

Claude Code는 user rules보다 project rules를 나중에 읽지만 서로 충돌하는 내용을 기계적으로 override하는 설정으로 취급하지 않는다. 따라서 설치기는 두 내용의 일관성을 유지하며 후순위만으로 충돌 해결을 보장하지 않는다. [Claude Code 공식 memory 문서](https://code.claude.com/docs/en/memory)

Gemini CLI는 global, workspace, 파일 접근 시 JIT 맥락을 연결한다. 설치기는 이 계층을 그대로 사용하며 프로젝트 지침을 삭제하지 않는다. [Gemini CLI 공식 GEMINI.md 문서](https://geminicli.com/docs/cli/gemini-md/)

Cursor는 `.mdc` project rules의 `alwaysApply`로 항상 맥락에 넣을 수 있다. user rules는 Agent Chat에 적용되며 Tab과 Inline Edit에는 적용되지 않는다. 파일 참조는 그 파일을 자동 인라인하지 않는다. [Cursor 공식 Rules 문서](https://cursor.com/docs/rules)

ChatGPT는 사용자 지침과 프로젝트 지침을 저장할 수 있다. 로컬 지침 파일을 모든 ChatGPT 채팅에 연결하는 공개 설정으로 설명하지 않는다. [OpenAI 공식 Personalize 문서](https://learn.chatgpt.com/docs/personalize), [OpenAI 공식 Projects 문서](https://learn.chatgpt.com/docs/projects)

## OS별 설치·검증 상태

| OS | 현재 설치·갱신 경로 | 확인 범위 |
| --- | --- | --- |
| macOS | Python 3.9+와 OpenSSH 검증기를 사용한다. 시작 wrapper, launchd 예약 갱신, 자동 갱신 끄기 중에서 선택한다. | 소유한 launchd 작업의 실제 등록·실행·해제는 [과거 예약 시험](scheduler-registration-verification.json)과 [공개 예약 시험](public-scheduler-verification.json)에서 확인했다. 이 결과는 V7의 모델 준수나 재로그인·절전 복귀를 검증하지 않는다. |
| Linux | Python 3.9+와 OpenSSH 검증기를 사용하며 시작 wrapper 또는 자동 갱신 끄기를 선택한다. | systemd 예약 파일 생성·자동 등록은 제공하지 않는다. 실제 Linux 설치·갱신은 검증하지 않았다. 검증기가 없으면 서명 확인과 원격 갱신은 실패하며 기존 로컬 snapshot은 유지한다. |
| Windows | 현재 자동 설치를 지원하지 않는다. | 설치기의 POSIX 파일 보호 요건을 충족하지 못하면 설치를 거부한다. Windows 파일 교체·ACL·OpenSSH·Task Scheduler 연결은 향후 설계이며 현재 선택할 설치 경로가 아니다. |

OS 표준 Python 설치 자체는 설치기가 처리하지 않는다. 검증기 부재 시 third-party 암호 패키지를 자동 설치하지 않는다. Linux/Windows 성공을 macOS 결과로 대신하지 않는다.

## 과거 로컬 확인 기록을 찾는다

[2026-10-12 환경 기록](../status/host-environment-20261012.md)은 당시 명령·출력·절대 경로와 macOS 테스트의 범위를 보존한다. 이 기록의 호스트 버전과 설치 경로를 현재 사용자 환경으로 간주하지 않는다. [5개 loader matrix](codex-loader-evidence.json)는 임시 환경의 prompt rendering 결과이며 네트워크·모델 호출을 포함하지 않는다.

[HTTPS 실행 검증](https-transport-verification.md)은 Python 3.11의 실제 TLS·서명 확인·시작 wrapper 갱신·오프라인 유지 결과와 환경별 한계를 기록한다. 이후 공개 배포·예약 등록은 [0.3.0 공개 기록](public-0.3.0-verification.md)과 [예약 실행 기록](public-scheduler-verification.json)에 남겼다. 이 과거 증거는 V7의 언어 효과나 새 호스트 버전의 로딩을 검증하지 않는다.
