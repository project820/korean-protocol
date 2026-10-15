# 공개 0.7.0 패키지를 내려받거나 로컬에서 만든다

[v0.7.0 릴리스](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)는 V7 r2의 오프라인 설치 ZIP과 채팅 파일을 제공한다. 서명 콘텐츠를 보관하는 `kproto-history-*` 릴리스와 구분한다.

## 공개 산출물을 선택한다

| 파일 | 용도 |
| --- | --- |
| [korean-protocol-0.7.0-draft.zip](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip) | 설치 도구·규칙·사전·안내를 함께 내려받아 로컬 설치한다. |
| [KOREAN-PROTOCOL.md](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md) | 일반 채팅에 규약 본문과 사전 데이터를 첨부한다. |
| [SHA256SUMS](https://github.com/project820/korean-protocol/releases/download/v0.7.0/SHA256SUMS) | 위 두 공개 파일의 손상을 확인한다. 발행자 인증은 제공하지 않는다. |

공개 패키지 원본은 `7e01d537d5e2364a5a5730e7e4d2e9aff9d5f911`이다. 서명된 일곱 콘텐츠의 원본 `67f537e`와 구분하며 두 산출물의 콘텐츠는 같다. ZIP은 규약 원본 0.7.0-draft·설치 콘텐츠 0.7.0·엔진 0.2.0을 담는다.

공개 파일은 고정 산출물이다. 이후 main의 문서나 빌드 도구가 바뀌어도 같은 v0.7.0 첨부물이 자동 교체되지 않는다. 공개 파일의 근거는 [0.7.0 발행·갱신 기록](public-0.7.0-verification.md)을 따른다.

## 압축을 풀고 사용한다

ZIP 루트의 `START-HERE.md`와 `INSTALL.md`를 읽는다. [오프라인 안내](../../distribution/START-HERE.md)는 `python3 start.py` 메뉴와 `agent-install.py` 비대화형 명령을 구분한다. [채팅 안내](../../distribution/CHAT-START.md)는 프로젝트 첨부 경로를 설명한다.

ZIP의 기본 설치는 미서명 `local-snapshot`이며 자동 갱신은 OFF다. 서명 설치가 필요하면 검토한 공개키·지문·HTTPS source를 명시한다. 기존 서명 설치를 ZIP의 로컬 모드로 덮어쓰지 않는다.

기존 설치를 관리하려면 같은 홈·상태 경로와 반환된 지속 관리 명령을 사용한다. 서명 재설치에서 자동 갱신 옵션을 생략하면 OFF로 설정되며 규약·높임말 설정과 별개다.

## 현재 checkout의 별도 패키지를 만든다

출력 부모 폴더를 먼저 준비하고 존재하지 않는 출력 파일을 지정한다.

```sh
python3 -B -m distribution.build --root . --output /ABS/korean-protocol-0.7.0-draft.zip
python3 -B -m unittest tests.test_distribution
```

이 명령은 현재 checkout으로 새 로컬 ZIP을 만들며 공개 v0.7.0의 바이트를 재현한다고 보장하지 않는다. 파일명에 같은 버전이 있어도 문서·설치 도구가 바뀌면 ZIP 해시는 다르다. 공개 산출물을 조용히 덮어쓰는 용도로 사용하지 않는다.

빌더는 고정 허용 목록만 담고 symlink·누락 파일·기존 출력 덮어쓰기를 거부한다. 저장소 전부·평가 로그·발행 개인키·자격 정보를 묶지 않는다. Markdown은 ZIP 안으로 옮긴 경로에 맞춰 상대 링크를 바꾸며 포함하지 않은 근거는 저장소 문서로 연결한다.

ZIP 내부 `SHA256SUMS`는 내부 파일을, 공개 릴리스의 별도 `SHA256SUMS`는 ZIP과 채팅 파일을 검사한다. 두 범위 모두 해시이며 서명이 아니다.

## 이전 미리보기 근거를 찾는다

0.2.0 미리보기 1~8의 크기·해시·당시 시험 수는 [개정 전 패키지 기록](https://github.com/project820/korean-protocol/blob/dacbbc239fc9dbb22f2ddb87119d4ac7161b2e3c/docs/distribution/preview-package.md)에 보존한다. 그 수치를 현재 ZIP이나 엔진의 검증 결과로 옮기지 않는다. 현재 설치·발행·언어 효과의 범위는 [현재 검증 상태](../status/requirements.md)를 따른다.
