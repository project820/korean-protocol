# Korean Protocol 오프라인 설치 초안

이 패키지는 0.2 연구·개발 초안이다. 한국어 규칙 72개, 사전 뜻 193개와 규칙·어휘 작성 사례를 포함한다. 규약은 LLM의 표현을 안내하며 모든 출력의 의미 보존이나 독자 이해도를 보장하지 않는다. ASD-STE100의 공식 한국어판이 아니다.

이 패키지는 서명하지 않은 로컬 설치용 미리보기다. `SHA256SUMS`는 파일 손상 확인용이며 발행자 인증이 아니다. 공개 발행키와 갱신 서버가 연결되지 않아 이 미리보기로 원격 자동 갱신을 켤 수 없다. 서명된 정식 배포물을 별도로 신뢰하고 설치한 뒤에 자동 갱신을 연결한다.

## 사용할 도구를 고른다

ChatGPT 등 일반 채팅에서 사용할 때는 [채팅용 시작 안내](CHAT-START.md)를 따른다. 프로젝트에 올릴 `KOREAN-PROTOCOL.md` 하나에 전체 규약과 사전을 묶었다.

Codex·Claude Code 사용자라면 압축을 푼 폴더에서 다음 명령으로 설치 메뉴를 연다. 메뉴가 대상 파일을 보여 준 뒤 설치·제거 여부를 확인하며, 상태 조회만으로 설치하지 않는다.

```sh
python3 start.py
```

첫 화면에서 `1`은 Codex, `2`는 Claude Code를 선택한다. 도구 선택 뒤에는 `1`로 설치, `2`로 상태 확인, `3`으로 제거, `0`으로 종료한다. 설치 후 선택한 도구에서 새 세션을 시작한다. 프로젝트 한 곳에만 적용하거나 경로를 직접 지정하려면 아래의 상세 설치법을 사용한다.

## 설치 환경과 파일을 준비한다

Python 3.9 이상과 POSIX 환경이 필요하다. 실제 설치 검증은 macOS의 Codex 파일 지침 방식에서 수행했다. Claude Code는 별도 규칙 파일을 설치하며 기존 CLAUDE.md를 바꾸지 않는다. Windows와 Cursor의 자동 설치는 지원한다고 표시하지 않는다. Gemini CLI용 파일 adapter는 있지만 실제 Gemini 호스트 로딩은 검증하지 않았다.

ZIP을 사용자가 관리할 고정 경로에 풀고 아래 두 변수를 실제 경로로 바꾼다. 압축을 푼 폴더의 `runtime/kproto.py`를 읽고 실행할 코드를 확인한다. 예시의 상태 경로는 호스트 대상 하나만 관리하며 다른 대상 설치에는 별도 상태 경로를 사용한다.

```sh
KPROTO_DIR="/실제/경로/korean-protocol-0.2.0-draft"
KPROTO_STATE="/실제/설치/상태/경로"
```

메뉴로 이미 설치했다면 메뉴에 표시된 상태 폴더를 `KPROTO_STATE`에 그대로 넣는다. macOS와 Linux의 기본 상태 경로가 다르므로 임의의 다른 경로로 바꾸지 않는다. 메뉴로 설치한 규약은 같은 메뉴의 `3`으로 제거하는 것이 가장 간단하다.

Claude Code 메뉴를 바로 열려면 `python3 start.py --host claude-code`를 실행한다. 두 도구는 서로 다른 상태 폴더를 쓰므로 각 도구의 메뉴에서 설치와 제거를 관리한다.

아래 상세 명령은 Codex 사용자 지침에 규약을 추가한다. 기본 `CODEX_HOME`은 기존 환경 설정을 따르며, 프로젝트 설치를 원하면 아래의 별도 명령을 사용한다. 기존 사용자 지침의 관리 블록 밖 내용을 보존하며 충돌이 있으면 설치를 거부한다.

```sh
python3 "$KPROTO_DIR/runtime/kproto.py" --state-dir "$KPROTO_STATE" install --bundle "$KPROTO_DIR" --host codex --scope user --local-snapshot --version 0.2.0 --autoupdate off
python3 "$KPROTO_DIR/runtime/kproto.py" --state-dir "$KPROTO_STATE" status --json
```

상태에 `installed: true`와 `trust: local-snapshot`이 표시되는지 확인하고 새 Codex 세션을 시작한다. 이는 로컬 설치 상태이며 모델이 모든 규칙을 따랐다는 검증 결과가 아니다. 호스트의 기존 지침·프로젝트 지침과 사용자 요청도 함께 적용된다.

프로젝트 하나에 설치하려면 별도 상태 경로와 프로젝트 절대 경로를 지정한다. 사용자 설치 예시와 같은 상태 경로를 공유하지 않는다.

```sh
python3 "$KPROTO_DIR/runtime/kproto.py" --state-dir "/별도/상태/경로" install --bundle "$KPROTO_DIR" --host codex --scope project --project-root "/실제/프로젝트/경로" --local-snapshot --version 0.2.0 --autoupdate off
```

설치한 규약과 사전은 로컬에 복사돼 서버나 정기 갱신 없이 유지된다. 호스트가 내용을 읽는 방식과 새 세션 시작 조건은 호스트에 따라 다르다. 향후 상태 확인·제거에 사용할 런타임 폴더와 Python은 고정 경로에 보관한다. 런타임 코드는 콘텐츠 자동 갱신으로 교체하지 않는다.

## 설치를 제거한다

```sh
python3 "$KPROTO_DIR/runtime/kproto.py" --state-dir "$KPROTO_STATE" uninstall
```

제거는 소유한 관리 블록을 없애고 블록 밖 사용자 내용을 보존한다. 상태·백업·캐시는 남긴다. 관리 블록 안을 직접 수정했으면 충돌로 거부할 수 있으므로 변경 내용을 먼저 확인한다.

## 규약과 검증 범위를 읽는다

- [전체 목차](docs/spec/toc.md)는 규약의 각 부를 정의한다.
- [한국어 규칙](docs/spec/korean-rules.md)은 조건·예외·용례를 제공한다.
- [사전 구조](docs/spec/lexicon.md)는 뜻·문맥·결합에 따른 어휘 사용을 정의한다.
- [전체 규약 본문](pack/protocol.md)과 `lexicon/`은 설치할 콘텐츠다.
- `examples/`는 작성자가 만든 판정 사례이며 독립적인 효능 시험이 아니다.

기능 대응 검토의 49/53개는 전체 완성도·사전 충족률·LLM 정답률을 뜻하지 않는다. 독자 실험과 한국어학·군사 전문가의 실제 자문은 수행하지 않았다. 연구·평가 실행 기록과 개발용 검사기는 이 설치 패키지에 포함하지 않았다. 전체 근거는 [프로젝트 저장소](https://github.com/project820/korean-protocol)에서 관리하며 현재 저장소 접근 권한이 필요하다.
