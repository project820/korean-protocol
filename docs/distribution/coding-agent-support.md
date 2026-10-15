# Codex와 Claude Code에 0.7.0을 설치한다

Codex·Claude Code의 사용자 범위 설치는 [INSTALL.md](../../INSTALL.md)를 따른다. 규약 콘텐츠는 0.7.0·순번 3이며 엔진 0.2.0 이상이 필요하다. 규칙·사전 데이터 schema 1.0은 엔진 번호와 별개다.

## 호스트와 상태를 분리한다

| 대상 | 사용자 지침 위치 |
| --- | --- |
| Codex | 실제 선택된 `CODEX_HOME` 아래 AGENTS 파일의 관리 블록을 사용한다. |
| Claude Code | 실제 선택된 `CLAUDE_CONFIG_DIR` 아래 `rules/korean-protocol.md`의 관리 블록을 사용한다. |

설치 도구의 `--codex-home`·`--claude-home`은 해당 호스트의 명시 경로다. 기본 상태 폴더는 도구별로 분리한다. 같은 상태 루트에 두 호스트를 등록하거나 기존 설치와 다른 홈으로 자동 이동하지 않는다.

기존 사용자 본문과 관리 블록 밖 변경은 보존한다. Claude Code의 `CLAUDE.md`와 다른 규칙 파일은 바꾸지 않으며 전용 파일에 경로 제한 YAML frontmatter가 있으면 설치·갱신을 거부한다. 제거 뒤 원래 없던 전용 파일이 빈 파일로 남을 수 있다.

## 서명 설치와 ZIP 메뉴를 구분한다

[서명 설치](signed-install.md)는 검토한 키·지문으로 HTTPS 콘텐츠를 인증하고 자동 갱신 방식을 선택한다. 기존 설치의 규약·높임말은 보존하지만 서명 재설치에서 `--autoupdate`를 생략하면 OFF로 설정한다.

[공개 v0.7.0 ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip)의 메뉴는 미서명 오프라인 설치다. 아래 명령은 압축 해제 루트에서만 실행한다.

```sh
python3 start.py
python3 start.py --host codex
python3 start.py --host claude-code
```

ZIP은 `7e01d53`의 고정 산출물이며 이후 main의 문서 수정이 포함됐다고 설명하지 않는다. 기존 서명 설치를 메뉴의 로컬 설치로 덮어쓰지 않는다.

## 검증된 설치본을 적용한다

설치 결과의 `status`로 버전·신뢰·캐시·실제 선택 대상·규약·높임말·복구 필요 상태를 확인한다. 현재 대화에는 그 검증된 호스트 관리 본문과 활성 캐시의 프로필·사전을 참조한다. 미검증 checkout의 파일을 현재 설치본으로 바꾸어 적용하지 않는다.

이미 시작한 세션은 이전 지침을 대화 맥락에 보존할 수 있다. 설정을 확실히 반영하려면 새 세션을 시작하며 파일 설치 성공을 모든 출력의 규칙 준수로 보고하지 않는다.

## 실제 로딩과 언어 효과를 구분한다

[Codex 로더 기록](codex-loader-evidence.json)과 [Claude 로더 기록](claude-loader-evidence.json)은 당시 임시 환경의 지침 공급을 확인한다. Claude 시험은 모의 서버가 지침 해시·규칙 수를 남기고 HTTP 400으로 종료하며 실제 모델 추론을 하지 않는다. 당시 호스트 버전·프로필의 증거를 최신 버전 모든 응답의 준수로 확대하지 않는다.

로더 시험을 다시 실행하려면 실제 사용자 설정·인증을 복사하지 않고 임시 환경과 시험용 키를 사용한다.

```sh
python3 -B tests/manual_claude_loader.py --runtime-root . --claude-binary /ABS/claude --output /ABS/claude-loader-evidence.json
```

공개 0.7.0의 두 호스트 HTTPS 갱신은 [발행 기록](public-0.7.0-verification.md), OS·프로젝트 설치의 제한은 [호스트 지원표](host-support.md)를 따른다. 전체 사전 읽기·모델 일반화·독자 이해는 별도 검증이다.
