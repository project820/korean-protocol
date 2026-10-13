# 규약 적용과 높임말을 전환한다

`protocol`은 규약 적용 여부, `honorifics`는 새 설명·보고 문장의 높임말 여부다. 새 설치의 기본값은 `protocol=on`, `honorifics=off`다. 짧고 명확한 상태 표현과 원문 인용은 높임말 설정 때문에 길게 바꾸지 않는다.

저장소 루트에서 Codex의 사용자 범위 설치를 관리하는 예시는 다음과 같다. Claude Code에는 `--host claude-code`를 사용한다. 별도 홈·상태 폴더에 설치했으면 설치 때의 `--codex-home` 또는 `--claude-home`, `--state-dir`을 같은 값으로 전달한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol off
python3 -B distribution/agent_install.py configure --host codex --protocol on
python3 -B distribution/agent_install.py configure --host codex --honorifics on
python3 -B distribution/agent_install.py configure --host codex --honorifics off
python3 -B distribution/agent_install.py status --host codex
```

설치 결과의 `management_commands`에는 `protocol_on`, `protocol_off`, `honorifics_on`, `honorifics_off`가 포함된다. 이 명령은 설치 폴더에 보존한 관리 코드를 사용하므로 복제본을 옮겨도 실행할 수 있다. 두 설정을 함께 바꾸려면 `configure --protocol on --honorifics off`를 사용한다. 설정 옵션은 `configure`에만 적용한다.

## OFF의 범위를 구분한다

OFF는 호스트 파일에서 활성 규약을 제거하고 소유권 확인용 표지만 남긴다. 설치 상태·신뢰 키·콘텐츠 캐시·높임말 선택은 보존한다. 업데이트·롤백·재설치는 OFF를 유지한다. ON은 캐시의 서명과 해시를 확인한 뒤 지침을 복원한다. 서명된 캐시 자체는 말투 설정으로 바꾸지 않는다.

`installed=true`는 관리되는 설치가 남아 있다는 뜻이다. `enabled=false`, `verified=false`, `content_verified=true`는 검증된 콘텐츠가 있지만 규약 적용은 꺼진 상태다. 설치됨과 적용 중을 같은 뜻으로 보고하지 않는다.

OFF는 자동 갱신 해제와 다르다. 원격 콘텐츠 확인도 멈추려면 반환된 `runtime_commands.configure_off`를 사용한다. `uninstall`은 규약의 관리 블록을 제거하고 소유 예약 작업을 해제한다.

## 세션 전환과 영구 설정을 구분한다

현재 대화에서 `Korean Protocol off/on`, `높임말 off/on`이라고 요청하면 에이전트가 그 이후 답변에 해당 설정을 따른다. 이 문자열을 감지하는 별도 프로그램이나 강제 출력 필터는 없다. 영구 설정을 바꾸려는 요청이면 에이전트가 위 관리 명령을 실행하고 결과를 확인한다.

이미 시작한 세션에서 읽은 지침은 파일을 바꿔도 대화 기록에서 지워지지 않는다. 호스트 파일 전환을 확실히 반영하려면 새 세션을 시작한다. 미적용 비교 시험은 규약을 읽지 않은 새 격리 프로세스로 수행한다.

## 기존 설치의 관리 경로를 이관한다

새 설치기의 `configure`는 소유한 예약 파일과 등록 작업을 현재 관리 런타임으로 이관한 뒤 설정을 바꾼다. 이관 중 쓰기가 실패하면 이전 파일과 설정을 복구한다. 사용자가 예약 파일이나 관리 블록을 수정했으면 덮어쓰지 않는다.

사용자가 직접 만든 외부 wrapper가 구버전 관리 파일을 호출하면 자동 이관되지 않는다. 반환된 새 `runtime_commands`로 그 호출 경로를 교체해야 한다. 오래된 코드는 새 OFF 설정을 알지 못하므로 이전 경로를 계속 실행해서는 안 된다.
