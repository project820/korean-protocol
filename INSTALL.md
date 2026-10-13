# 에이전트가 Korean Protocol을 설치한다

이 문서는 사용자가 Korean Protocol 설치를 요청했을 때 적용한다. 저장소를 읽거나 개발하는 것만으로 사용자 환경에 설치하지 않는다. Codex와 Claude Code의 사용자 범위 설치를 지원하며 Python 3.9 이상과 POSIX 환경이 필요하다.

## 설치할 에이전트를 정한다

사용자가 현재 대화 중인 도구가 Codex이면 `codex`, Claude Code이면 `claude-code`를 선택한다. 두 CLI가 설치돼 있다는 이유로 둘 다 변경하지 않는다. 대화 환경에서 대상 도구를 알 수 없을 때만 사용자에게 확인한다.

저장소에 접근할 수 있으면 로컬로 내려받고 아래 명령을 저장소 루트에서 실행한다. 비공개 개발 기간에는 기존 GitHub 인증을 사용하며 토큰을 명령·로그에 쓰지 않는다. 인증이 없으면 접근 실패를 보고한다. 저장소 공개 전에는 누구나 설치할 수 있다고 안내하지 않는다.

## 설치 위치를 확인하고 설치한다

Codex에서는 다음 명령을 사용한다. Claude Code에서는 모든 명령의 `--host codex`를 `--host claude-code`로 바꾼다.

```sh
python3 -B distribution/agent_install.py plan --host codex
python3 -B distribution/agent_install.py install --host codex
python3 -B distribution/agent_install.py status --host codex
```

ZIP에서는 `distribution/agent_install.py` 대신 루트의 `agent-install.py`를 실행한다. 각 명령은 JSON을 출력한다. `-B`는 Python 자체의 바이트코드 캐시 생성을 막는다. `plan`은 변경할 경로를 확인하며 파일을 만들지 않는다. 사용자의 설치 요청이 있으면 계획을 확인한 뒤 대화형 메뉴 없이 설치한다. 명령이 실패하면 원인과 종료 코드를 보고하고 성공으로 표시하지 않는다.

기존 사용자 지침은 보존한다. Codex는 사용자 지침의 관리 블록에 설치하고 Claude Code는 사용자 설정 아래 `rules/korean-protocol.md`에 설치한다. 기본 경로는 `CODEX_HOME`과 `CLAUDE_CONFIG_DIR` 설정을 따른다. 경로를 지정하려면 `--codex-home` 또는 `--claude-home`을 사용한다. 별도 상태 위치가 필요하면 각 명령에 같은 `--state-dir`을 전달한다. 두 호스트는 기본 상태 위치를 분리한다.

## 설치 결과를 확인하고 현재 대화에 적용한다

설치 후 상태 조회에서 설치 대상과 버전을 확인한다. `installed`만 보지 말고 `verified`와 현재 호스트가 선택하는 대상의 일치 여부도 확인한다. 불일치나 복구 필요 상태를 정상 적용으로 보고하지 않는다. 설치 결과의 `management_commands`에 나온 지속 관리 명령을 사용자에게 남긴다. 관리 코드와 규약은 상태 폴더에 보존하므로 설치에 사용한 임시 복제본이 없어져도 상태 확인과 제거가 가능하다.

현재 대화에서는 `profiles/coding-agent.md`를 읽고 지침 우선순위 안에서 적용한다. 어휘 판정이 필요하면 `lexicon/core.json`과 `lexicon/domains/software.json`에서 관련 뜻·조건·예외를 읽는다. 새 세션은 설치된 호스트 지침을 읽는다. 파일 설치 성공과 모델의 모든 규칙 준수를 구분하며, 실제 호스트 로딩을 확인하지 않았다면 확인했다고 보고하지 않는다.

설치한 버전, 대상 경로, 자동 갱신이 꺼져 있다는 사실, 새 세션 시작 안내를 짧게 알린다. 이 배포는 미서명 로컬 미리보기이며 원격 콘텐츠를 자동 실행하지 않는다. 정식 서명 발행과 공개 HTTPS 갱신 경로는 아직 연결하지 않았다.

## 설치를 관리하거나 제거한다

설치 결과에 제공된 지속 관리 명령으로 상태를 확인한다. 사용자가 제거를 요청하면 같은 관리 도구의 `uninstall` 명령을 사용한다. 저장소가 남아 있으면 다음 명령도 사용할 수 있다.

```sh
python3 -B distribution/agent_install.py uninstall --host codex
```

제거는 규약의 관리 블록을 없애고 사용자 지침의 나머지를 보존한다. 상태·백업·캐시와 관리 도구는 남긴다. 관리 블록을 직접 수정해 충돌이 발생하면 덮어쓰지 않고 충돌을 보고한다.

서명된 정식 배포물을 설치하고 갱신을 연결하는 절차는 [서명 설치 안내](docs/distribution/signed-install.md)를 따른다. 정식 배포 정보가 없는 현재 미리보기에 임의의 키나 주소를 넣지 않는다.
