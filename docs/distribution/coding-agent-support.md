# 코딩 에이전트부터 지원한다

Codex·Claude Code는 [INSTALL.md](../../INSTALL.md)의 서명 설치를 지원한다. 현재 원본 0.7.0-draft는 V7 r2를 채택했으며 콘텐츠 0.7.0의 실제 공개 발행·갱신 상태는 [현재 검증 상태](../status/requirements.md)를 따른다. 아래의 로더·HTTPS 시험은 당시 호스트와 프로필의 증거이며 V7 출력의 의미 보존을 검증한 결과가 아니다.

사용자가 2026-10-13에 두 도구를 첫 지원 대상으로 선택했다. 오프라인 ZIP에서는 설치 메뉴로 도구를 고르고 설치·상태 확인·제거를 수행한다. 도구마다 상태 폴더를 분리하며 두 도구의 사용자 지침을 같은 파일에 합치지 않는다.

```sh
python3 start.py
python3 start.py --host codex
python3 start.py --host claude-code
```

첫 명령은 도구 선택 화면을 연다. 뒤의 두 명령은 해당 도구의 메뉴를 바로 연다. 설치 후 새 세션을 시작하며, 이미 실행 중인 세션이 즉시 새 지침을 읽는다고 보장하지 않는다.

## Claude Code의 설치 위치를 정한다

사용자 설치는 기본적으로 `~/.claude/rules/korean-protocol.md`를 사용한다. `--claude-home`을 지정하면 그 경로를 우선하며, 지정하지 않으면 `CLAUDE_CONFIG_DIR`을 따른다. 프로젝트 설치는 `<프로젝트>/.claude/rules/korean-protocol.md`를 사용한다. 사용자 설치의 해결된 설정 경로를 저장하므로 갱신·롤백 때 환경 변수가 달라져도 다른 파일로 이동하지 않는다.

기존 `CLAUDE.md`와 다른 규칙 파일은 변경하지 않는다. 전용 파일에 있던 일반 본문과 관리 블록 밖 사용자 내용은 보존한다. 전용 파일에 경로 제한 등의 YAML frontmatter가 있으면 설치·갱신을 거부하며 해당 설정을 지우거나 바꾸지 않는다. 제거는 관리 블록만 없애므로 새로 만들었던 전용 파일이 빈 파일로 남을 수 있다.

[Claude Code 공식 규칙 문서](https://code.claude.com/docs/en/memory)는 사용자·프로젝트 규칙 위치와 경로 제한 없는 규칙의 시작 시 로딩을 설명한다. [설정 문서](https://code.claude.com/docs/en/settings)는 설정 위치를 바꾸는 환경 변수를 설명한다. 두 문서 본문은 2026-10-13에 확인했다. 호스트의 지침 제외 설정과 사용자 요청은 그대로 적용되며, 설치기는 이를 우회하지 않는다.

## 실제 로딩과 갱신 증거를 구분한다

[Claude 로더 검사](claude-loader-evidence.json)는 임시 환경에서 규약을 설치한 뒤 실제 Claude Code 2.1.296이 만든 요청을 로컬 모의 서버로 받는다. 모의 서버는 요청을 기록하는 대신 해시와 규칙 수만 남기고 HTTP 400으로 종료한다. 따라서 CLI의 오류 종료는 의도한 시험 동작이며 실제 모델 추론·응답 준수·사전 전체 읽기의 증거가 아니다.

재현에는 설치된 Claude Code 실행 파일의 절대 경로를 지정한다. 실제 사용자 설정이나 인증키는 복사하지 않으며 임시 HOME과 시험용 키 문자열만 사용한다.

```sh
python3 tests/manual_claude_loader.py --runtime-root . --claude-binary /ABS/claude --output /ABS/claude-loader-evidence.json
```

콘텐츠 서명 확인·로컬 캐시·실패 시 정상본 유지 방식은 공통 런타임을 사용한다. ZIP 메뉴는 미서명 로컬 설치용이며 원격 자동 갱신을 켜지 않는다. 공개 서명 설치와 갱신 연결은 [서명 설치 안내](signed-install.md)를 따른다.

[당시 Claude HTTPS 검사](claude-https-smoke.json)는 서명된 시험 릴리스의 수동·호스트 시작 갱신, 잘못된 CA·서명 거부, 서버 중단 뒤 정상본 유지를 포함한 16단계를 통과했다. 공개 서버나 실제 사용자 예약 등록을 시험한 것은 아니다. 당시 전체 단위·통합 테스트 182개도 통과했다.
