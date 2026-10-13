# 에이전트가 Korean Protocol을 설치한다

이 문서는 사용자가 Korean Protocol 설치를 요청했을 때 적용한다. 저장소를 읽거나 개발하는 것만으로 사용자 환경에 설치하지 않는다. Codex와 Claude Code의 사용자 범위 설치를 지원하며 Python 3.9 이상, OpenSSH `ssh-keygen`, POSIX 환경이 필요하다.

## 설치할 에이전트를 정한다

사용자가 현재 대화 중인 도구가 Codex이면 `codex`, Claude Code이면 `claude-code`를 선택한다. 두 CLI가 설치돼 있다는 이유로 둘 다 변경하지 않는다. 대화 환경에서 대상 도구를 알 수 없을 때만 사용자에게 확인한다.

저장소는 공개되어 있으며 GitHub 인증 없이 내려받을 수 있다. 아래 명령은 저장소 루트에서 실행한다.

```sh
git clone https://github.com/project820/korean-protocol.git
cd korean-protocol
```

## 신뢰 기준을 확인한다

서명 설치는 저장소의 `distribution/trust/publisher.pub`와 다음 지문으로 배포물을 검증한다.

```text
SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc
```

공개키와 지문을 같은 미확인 출처에서 함께 받으면 그 둘만으로 발행자를 독립적으로 인증하지 못한다. 첫 신뢰 경계는 `https://github.com/project820/korean-protocol` 저장소이므로 이 저장소에서 받은 것인지 확인한다. 설치기는 배포 서버가 보낸 키를 신뢰 기준으로 사용하지 않으며, 기존 설치의 신뢰 키를 다른 키로 교체하지 않는다.

## 공개 배포에서 서명 설치한다

공개 배포 주소는 `https://project820.github.io/korean-protocol`이다. Codex 예시이며, Claude Code에서는 모든 명령의 `--host codex`를 `--host claude-code`로 바꾼다. 각 명령은 JSON을 출력한다. 명령이 실패하면 원인과 종료 코드를 보고하고 성공으로 표시하지 않는다.

macOS에서는 예약 자동 갱신을 명시적으로 등록한다.

```sh
python3 -B distribution/agent_install.py plan --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate scheduled --register-scheduler
python3 -B distribution/agent_install.py install --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate scheduled --register-scheduler
python3 -B distribution/agent_install.py status --host codex
```

`plan`은 배포물을 임시 폴더에 내려받아 서명과 콘텐츠를 검증한 뒤 임시 폴더를 지운다. 호스트 지침·설치 상태를 바꾸지 않고 예약 작업도 등록하지 않는다. `install` 결과의 `scheduler`에서 실제 launchd 등록을 확인한다. `registered: false`나 충돌은 등록 성공으로 보고하지 않는다.

Linux에서는 예약 등록을 지원하지 않는다. `--autoupdate interval`을 사용하면 설치 결과의 `runtime_argv.run` 뒤에 `--`와 실제 호스트 명령을 붙여 실행할 때만 갱신을 확인한다. 평소처럼 `codex`나 `claude`를 실행하면 이 경로가 호출되지 않는다. 사용자가 시작 명령 연결을 원하지 않으면 `--autoupdate off`로 설치한다.

```sh
python3 -B distribution/agent_install.py install --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate interval
python3 -B distribution/agent_install.py install --host codex --source https://project820.github.io/korean-protocol --trust-key distribution/trust/publisher.pub --expected-fingerprint SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc --autoupdate off
```

macOS에서도 자동 갱신을 원하지 않으면 `--autoupdate off`를 사용한다. 이 경우 서명된 규약을 설치하고 원격 갱신을 하지 않는다. 잘못된 서명·다른 키·만료된 manifest·유효하지 않은 주소는 설치하지 않는다. 자세한 갱신 동작은 [서명 설치 안내](docs/distribution/signed-install.md)를 따른다.

## 오프라인 미서명 설치를 명시적으로 선택한다

네트워크를 사용할 수 없거나 사용자가 미서명 로컬 설치를 요청하면 서명 옵션 없이 실행한다. 이 경로는 저장소 또는 ZIP의 파일을 그대로 설치하며 자동 갱신은 꺼져 있다.

```sh
python3 -B distribution/agent_install.py plan --host codex
python3 -B distribution/agent_install.py install --host codex
```

ZIP에서는 `distribution/agent_install.py` 대신 루트의 `agent-install.py`를 실행한다. 이 경로를 서명 설치로 보고하지 않는다. 이미 내려받아 `seal`로 검증한 정적 폴더가 있으면 `--signed-directory`로 오프라인 서명 설치를 할 수 있다.

## 설치 위치와 기존 지침을 보존한다

`-B`는 Python 자체의 바이트코드 캐시 생성을 막는다. 기존 사용자 지침은 보존한다. Codex는 사용자 지침의 관리 블록에 설치하고 Claude Code는 사용자 설정 아래 `rules/korean-protocol.md`에 설치한다. 기본 경로는 `CODEX_HOME`과 `CLAUDE_CONFIG_DIR` 설정을 따른다. 경로를 지정하려면 `--codex-home` 또는 `--claude-home`을 사용한다.

별도 상태 위치가 필요하면 각 명령에 같은 `--state-dir`을 전달한다. 두 호스트는 기본 상태 위치를 분리한다.

## 설치 결과를 확인하고 현재 대화에 적용한다

상태 조회에서 설치 대상과 버전을 확인한다. `installed`만 보지 말고 `verified`와 현재 호스트가 선택하는 대상의 일치 여부도 확인한다. 불일치나 복구 필요 상태를 정상 적용으로 보고하지 않는다. 관리 코드와 규약은 상태 폴더에 보존하므로 설치에 사용한 복제본이 없어져도 상태 확인·갱신·제거가 가능하다.

현재 대화에서는 `profiles/coding-agent.md`를 읽고 지침 우선순위 안에서 적용한다. 어휘 판정이 필요하면 `lexicon/core.json`과 `lexicon/domains/software.json`에서 관련 뜻·조건·예외를 읽는다. 새 세션은 설치된 호스트 지침을 읽는다. 파일 설치 성공과 모델의 모든 규칙 준수를 구분하며, 실제 호스트 로딩을 확인하지 않았다면 확인했다고 보고하지 않는다.

사용자에게 설치한 버전, 대상 경로, 서명 여부, 자동 갱신 방식과 연결 상태, 새 세션 시작 안내를 짧게 알린다. 설치 결과의 `management_commands`와 `runtime_argv`에 나온 지속 관리 명령도 남긴다.

## 설치를 관리하거나 제거한다

사용자가 제거를 요청하면 설치 결과에 나온 관리 도구의 `uninstall` 명령을 사용한다. 저장소가 남아 있으면 다음 명령도 사용할 수 있다.

```sh
python3 -B distribution/agent_install.py uninstall --host codex
```

제거는 규약의 관리 블록을 없애고 사용자 지침의 나머지를 보존한다. 설치기가 소유한 예약 작업도 해제한다. 상태·백업·캐시와 관리 도구는 남긴다. 관리 블록이나 예약 파일을 직접 수정해 충돌이 발생하면 덮어쓰지 않고 충돌을 보고한다.

## 라이선스를 함께 보존한다

직접 작성한 코드·규약·사전·문서는 MIT License로 제공한다. 저장소와 ZIP의 `LICENSE`·`NOTICE.md`를 함께 보존한다. 설치 캐시의 `pack/protocol.md`와 지속 관리 Python 파일에도 허가문이 포함되며, 규약 또는 설치 코드를 재배포할 때 해당 고지를 함께 제공한다. 외부 ASD-STE100 원문 등의 권리는 프로젝트의 MIT License로 바뀌지 않는다.

## 규약 적용과 높임말을 바꾼다

새 설치는 규약 적용을 켜고 높임말을 끈다. 설치 뒤 `configure --protocol on|off`와 `configure --honorifics on|off`로 각각 바꾼다. 실제 명령·상태 의미·진행 중인 세션의 제한은 [적용 설정](docs/distribution/application-controls.md)을 따른다. 반환된 지속 관리 명령을 사용하고 실제 사용자 환경과 시험용 홈을 혼동하지 않는다.
