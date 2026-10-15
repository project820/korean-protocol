# 0.7.0의 규약 적용과 높임말을 전환한다

`protocol`은 규약 적용 여부, `honorifics`는 새 설명·보고의 높임말 여부다. 신규 설치는 ON·OFF로 시작하며 기존 설치의 두 선택은 갱신·재설치·롤백에서 보존한다. 자동 갱신 방식은 별도 설정이다.

## 같은 설치의 지속 관리 명령을 사용한다

설치 결과의 `management_commands`에는 `protocol_on`·`protocol_off`·`honorifics_on`·`honorifics_off`·`status`가 있다. 반환된 경로는 원래 복제본을 옮겨도 사용한다.

검토한 checkout에서 관리할 때는 다음 명령도 사용할 수 있다. Claude Code에는 `--host claude-code`를 쓰고 기존의 별도 홈·상태 경로를 모두 전달한다.

아래 변경 중 원하는 하나만 선택한다. 규약을 끄려면 다음 명령을 사용한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol off
```

규약과 높임말을 모두 켜려면 다음 명령을 사용한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --protocol on --honorifics on
```

규약 선택은 유지하고 높임말만 끄려면 다음 명령을 사용한다.

```sh
python3 -B distribution/agent_install.py configure --host codex --honorifics off
```

선택한 변경 뒤 상태를 확인한다.

```sh
python3 -B distribution/agent_install.py status --host codex
```

`configure`에만 적용 옵션을 전달한다. 현재 선택 대상이 설치 당시 대상과 다르거나 관리 본문이 수정됐으면 덮어쓰지 않는다. 기존 설치에는 새 홈이나 상태 폴더를 임의로 만들지 않는다.

## 상태를 구분한다

| 상태 | 의미 |
| --- | --- |
| `installed=true` | 관리되는 설치가 남아 있다. 규약 ON을 뜻하지 않는다. |
| `enabled=false` | 활성 프로필 대신 소유권 표지만 호스트 파일에 둔다. |
| `content_verified=true` | 활성 캐시의 콘텐츠 무결성 검사가 통과했다. 게시자 인증 여부는 `trust`도 확인한다. |
| `verified=false`와 규약 OFF | 콘텐츠를 검증했어도 현재 적용은 꺼져 있을 수 있다. |
| `target_matches=false` 또는 `recovery_required=true` | 정상 적용으로 보고하지 않고 경로·복구 문제를 해결한다. |

ON은 캐시를 다시 검증해 지침을 복원한다. 서명된 콘텐츠의 바이트는 높임말 전환으로 바꾸지 않으며 설치기는 호스트 본문에 설정을 반영한다. 짧은 상태형·인용·기존 제품 문체를 높임말 선택만으로 불필요하게 늘리지 않는다.

## 규약 OFF와 자동 갱신 OFF를 구분한다

규약 OFF는 신뢰 키·콘텐츠 캐시·높임말·자동 갱신 선택을 보존한다. 자동 조회도 멈추려면 반환된 `runtime_commands.configure_off`를 실행한다. 자동 갱신 OFF에서도 사용자가 명시한 수동 `update`는 원격 작업이다.

서명 `install`의 `--autoupdate`는 기본값이 OFF다. 재설치로 기존 예약·시작 갱신을 유지하려면 같은 방식을 명시하고 연결을 재확인한다. 규약·높임말이 보존됐다는 사실만으로 자동 갱신도 유지됐다고 보고하지 않는다. 실행 방식과 1~168시간 간격은 [서명 설치 안내](signed-install.md)를 따른다.

## 현재 대화와 영구 설정을 구분한다

현재 채팅에서 규약·높임말 전환을 요청하면 에이전트가 이후 표현에 적용한다. 이 문자열을 감지하는 별도 프로그램이나 출력 차단 필터는 없다. 영구 설치 설정을 바꾸라는 요청이면 관리 명령을 실행해 상태를 확인한다.

현재 대화에 설치본을 적용할 때는 `status`가 검증한 관리 본문과 활성 캐시만 참조한다. 미검증 checkout을 대신 읽거나 규약 OFF를 임의로 켜지 않는다. 이미 읽은 지침은 파일 변경으로 대화 기록에서 지워지지 않으므로 새 세션에서 확인한다.

## 관리 엔진과 호출 경로를 이관한다

규약 0.7.0은 엔진 0.2.0 이상이 필요하다. [관리 도구 재설치](../../INSTALL.md#기존-설치의-관리-도구를-먼저-갱신한다)는 콘텐츠 자동 갱신과 별도다. 새 도구는 소유한 예약 파일·작업의 관리 경로를 확인하며 충돌·실패 시 이전 사용자 내용을 보존한다.

직접 만든 외부 wrapper는 자동 이관하지 않는다. 반환된 새 `runtime_argv.run` 또는 `runtime_commands.run`으로 호출 경로를 교체한다. 제거는 요청한 관리 블록과 소유 예약 작업만 해제하며 상태·백업·캐시를 남긴다.
