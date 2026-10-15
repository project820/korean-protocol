# Korean Protocol 0.7.0을 오프라인으로 설치한다

이 패키지는 V7 r2 구조를 채택한 규약 원본 0.7.0-draft와 엔진 0.2.0을 담는다. 서명하지 않은 로컬 설치본이며 콘텐츠는 0.7.0으로 기록한다. SHA256SUMS는 손상 확인용이고 발행자 인증이 아니다.

공개 [v0.7.0 ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip)은 원본 `7e01d53`의 고정 산출물이다. 최신 저장소 문서의 수정이 이 ZIP에도 반영됐다고 설명하지 않는다. [최신 설치 안내](../INSTALL.md)와 서명 HTTPS 설치는 별도로 제공한다.

## 사용할 도구를 고른다

| 대상 | 시작 방법 |
| --- | --- |
| ChatGPT와 일반 채팅 | [채팅 안내](CHAT-START.md)를 따라 `KOREAN-PROTOCOL.md`를 첨부한다. Python 설치를 하지 않는다. |
| Codex와 Claude Code | 아래 메뉴를 사용하거나 에이전트에 이 폴더의 `INSTALL.md`로 설치를 맡긴다. |
| 기존 서명 설치 | 최신 INSTALL.md에서 같은 홈·상태 경로로 서명 재설치한다. 이 미서명 메뉴로 신뢰 방식을 바꾸지 않는다. |

Python 3.9 이상과 POSIX 환경이 필요하다. macOS의 두 도구 설치·상태·제거를 검증했으며 Windows 자동 설치는 지원하지 않는다. Gemini·Cursor의 지원 범위와 실제 로딩 증거는 [호스트 지원표](../docs/distribution/host-support.md)를 따른다.

## ZIP 루트에서 메뉴를 연다

```sh
python3 start.py
```

첫 화면에서 `1`은 Codex, `2`는 Claude Code다. 도구를 고른 뒤 `1`은 설치, `2`는 상태, `3`은 제거, `0`은 종료다. 메뉴가 변경 대상을 보여 주고 확인을 받은 뒤 설치한다.

Claude Code 메뉴를 바로 열려면 `python3 start.py --host claude-code`를 실행한다. 도구별 상태 폴더가 다르므로 선택한 도구의 메뉴에서 관리한다. 메뉴는 미서명 로컬 설치이며 원격 자동 갱신을 켜지 않는다.

## 에이전트가 비대화형으로 설치한다

압축을 푼 루트에서 실행한다. Claude Code에는 `--host claude-code`를 사용한다.

```sh
python3 -B agent-install.py plan --host codex
python3 -B agent-install.py install --host codex
python3 -B agent-install.py status --host codex
```

기존 설치에는 같은 홈과 상태 경로를 지정한다. 메뉴에서 확인한 상태 폴더와 다른 폴더를 임의로 쓰지 않는다. 사용자 지침의 관리 블록 밖 내용과 규약·높임말 설정은 보존하며 충돌을 덮어쓰지 않는다.

프로젝트 한 곳에만 설치하려면 사용자 설치와 다른 상태 폴더와 프로젝트 절대 경로를 사용한다. 아래 경로는 실제 값으로 바꾼다.

```sh
python3 -B runtime/kproto.py --state-dir "/별도/상태/경로" install --bundle "." --host codex --scope project --project-root "/실제/프로젝트/경로" --local-snapshot --version 0.7.0 --autoupdate off
python3 -B runtime/kproto.py --state-dir "/별도/상태/경로" status --json
```

이 저수준 프로젝트 설치는 ZIP과 Python 실행 경로를 고정해 관리한다. 제거도 같은 런타임과 상태 폴더를 사용한다.

```sh
python3 -B runtime/kproto.py --state-dir "/별도/상태/경로" uninstall
```

`agent-install.py`는 사용자 설치 전용이며 위 프로젝트 상태를 조회·제거하지 않는다. 사용자 설치의 에이전트 도구는 관리 코드를 상태 폴더에 따로 보존한다.

## 설치와 설정을 확인한다

상태의 버전은 0.7.0, 신뢰 방식은 `local-snapshot`이어야 한다. 설치 범위에 맞는 명령으로 확인한다.

- 사용자 설치는 `python3 -B agent-install.py status --host codex`를 사용한다. `target_matches`, `content_verified`, `enabled`, `honorifics`, `recovery_required`를 확인한다.
- 프로젝트 설치는 위 저수준 `status --json`을 사용한다. 이 명령은 `version`, `trust`, `target`, `enabled`, `honorifics`, `recovery_required` 등 저장된 상태를 조회한다. 캐시 무결성을 다시 검증하거나 `target_matches`·`content_verified`를 반환하지 않는다.

상태 확인을 이유로 규약·높임말 선택을 바꾸지 않는다. 선택한 도구에서 새 세션을 시작하며 파일 설치를 모델의 모든 규칙 준수로 보고하지 않는다.

규약 OFF와 자동 갱신 OFF는 다르다. 설정을 바꾸기로 선택했을 때만 [적용 설정](../docs/distribution/application-controls.md)의 해당 명령을 실행한다. 서명 설치로 전환할 때만 검토한 키·지문·source를 명시하며 엔진 갱신과 자동 갱신 재설정은 최신 INSTALL.md를 따른다.

## 사용자 설치를 제거하거나 규칙을 읽는다

사용자 설치는 메뉴의 제거 또는 설치 결과의 지속 관리 명령을 사용한다. 프로젝트 설치는 앞의 저수준 제거 명령을 사용한다.

```sh
python3 -B agent-install.py uninstall --host codex
```

소유한 관리 블록만 제거하며 사용자 본문·상태·백업·캐시는 남긴다. 수정한 관리 블록은 충돌로 보고한다.

[규칙](../docs/spec/korean-rules.md), [사전 계약](../docs/spec/lexicon.md), [전체 목차](../docs/spec/toc.md)와 [규약 본문](../pack/protocol.md)을 함께 읽는다. 대상·조건·수량·기한의 관계와 의미를 보존하며 원문보다 짧게 만들 것을 요구하지 않는다. 작성 사례와 파일 검사는 독자 이해도 시험이 아니다. `LICENSE`와 `NOTICE.md`는 재배포할 때 함께 보존한다.
