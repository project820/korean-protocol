# 서명 콘텐츠 발행물을 준비한다

발행 도구는 규약을 검사하고, 외부에서 서명한 결과를 검증해 정적 HTTPS 서버에 올릴 폴더를 만든다. 이 로컬 도구는 서버 업로드·저장소 공개 전환·키 생성을 수행하지 않는다. 프로젝트의 정식 발행은 [GitHub Actions 워크플로](github-actions-pages.md)가 환경 Secret의 발행키로 같은 검사·서명을 수행해 `https://project820.github.io/korean-protocol`에 게시한다. 이 문서의 로컬 절차는 발행 도구의 동작과 수동 발행을 설명한다.

## 발행 입력을 준비한다

검토한 저장소에서 Python 3.9 이상으로 실행한다. OpenSSH의 `ssh-keygen`이 필요하며 새 Python 패키지는 설치하지 않는다. 발행자는 관리하는 Ed25519 공개키와 별도로 확인한 지문을 준비한다. 개인키는 저장소·배포 폴더·로그에 넣지 않는다.

규칙과 두 사전의 콘텐츠 버전이 같아야 한다. `0.2.0-draft`는 숫자 부분이 같은 `0.2.0` 발행 manifest에 사용할 수 있으며 원본의 초안 표시는 그대로 남긴다. 서명은 발행자와 파일 무결성을 확인하며 전문가 승인이나 문장 효과를 인증하지 않는다.

발행 도구는 원본 구조를 검사하고 프로필 세 개와 상세 규약을 임시 폴더에서 다시 생성해 현재 파일과 비교한다. 오래된 생성물이 있으면 원본을 검토하고 `python3 -B -m validation.compile --root . --output .`으로 재생성한 뒤 변경을 검토한다. 도구가 원본을 자동 수정하지 않는다.

## 첫 발행의 서명 입력을 만든다

아래 대문자 값은 발행자가 정할 실제 절대 경로·지문·UTC 시각으로 바꾼다. 시각은 `YYYY-MM-DDTHH:MM:SSZ` 형식이며 발행 시각은 미래일 수 없고 만료 시각은 현재보다 뒤여야 한다. `UNSIGNED_DIR`과 `READY_DIR`은 아직 존재하지 않는 별도 경로를 사용한다.

```sh
python3 -B -m distribution.release prepare --root . --output UNSIGNED_DIR --version 0.2.0 --sequence 1 --issued-at ISSUED_UTC --expires-at EXPIRES_UTC --public-key PUBLISHER_PUBLIC_KEY --fingerprint VERIFIED_FINGERPRINT --first-release
```

첫 발행에만 `--first-release`를 사용한다. 후속 발행에서는 이 옵션 대신 `--previous PREVIOUS_SIGNED_STATIC_DIR`을 지정한다. 이전 발행물의 서명·콘텐츠를 확인하고 버전과 sequence가 모두 증가해야 한다. 이전 폴더의 만료는 과거 이력 확인을 막지 않는다. 로컬에 전달한 이전 폴더를 검사할 뿐 서버의 최신 발행 상태를 자동 조회하지 않으므로, 발행자는 실제 최신 이력을 전달해야 한다.

## 외부에서 서명하고 검증한다

발행자의 키 관리 환경에서 manifest의 정확한 바이트를 서명한다. 다음 OpenSSH 명령은 기존 개인키를 사용하며 manifest 옆에 `.sig` 파일을 만든다. 암호가 설정된 키는 OpenSSH가 직접 처리한다.

```sh
ssh-keygen -Y sign -f PUBLISHER_PRIVATE_KEY -n kproto-release-v1 UNSIGNED_DIR/stable/release.json
python3 -B -m distribution.release seal --prepared UNSIGNED_DIR --signature UNSIGNED_DIR/stable/release.json.sig --output READY_DIR --public-key PUBLISHER_PUBLIC_KEY --fingerprint VERIFIED_FINGERPRINT --first-release
```

후속 발행의 `seal`에도 `--previous PREVIOUS_SIGNED_STATIC_DIR`을 동일하게 사용한다. `seal`은 지정한 공개키로 서명을 확인하고 manifest와 일곱 콘텐츠의 해시·크기·경로를 검사한다. 검증을 통과하기 전에는 업로드용 결과를 만들지 않는다. 출력 경로가 존재하면 덮어쓰지 않는다. 실패한 입력을 수정해 다시 실행할 때도 새 출력 경로를 사용한다.

## 준비된 폴더를 게시한다

완료된 정적 폴더에는 다음 파일만 들어간다.

```text
stable/release.json
stable/release.json.sig
releases/<version>/profiles/coding-agent.md
releases/<version>/profiles/chat.md
releases/<version>/profiles/work-document.md
releases/<version>/specification/rules.json
releases/<version>/lexicon/core.json
releases/<version>/lexicon/domains/software.json
releases/<version>/pack/protocol.md
```

발행자가 관리하는 같은 origin의 HTTPS 주소에 버전별 콘텐츠를 먼저 올리고, stable의 서명과 manifest를 마지막에 게시한다. 두 stable 파일이 교체되는 순간 불일치하면 클라이언트가 해당 갱신을 거부하고 기존 규약을 유지한다. 이전 버전 디렉터리는 보존한다. ZIP 미리보기·실행 코드·개인키·검사 로그를 콘텐츠 endpoint에 섞지 않는다.

게시 후 실제 주소의 서명·TLS·업데이트·오프라인 유지를 별도 설치 상태에서 확인한다. 정식 공개키 지문은 `SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc`이고 공개 endpoint는 `https://project820.github.io/korean-protocol`이다. 다른 키로 만든 발행물은 기존 설치본이 거부하므로 이 endpoint에 게시하지 않는다. 설치·자동 갱신 연결 명령은 [서명 설치 안내](signed-install.md)를 따른다.

## 검증 범위를 구분한다

[발행 도구 시험 기록](publisher-verification.json)에 원본 해시와 검사 범위를 기록했다. 발행 전용 테스트 13개와 전체 테스트 209개가 통과했다. 임시 Ed25519 키로 최초·후속 발행물을 만들고 두 호스트의 격리된 상태에 서명 설치했으며, 변조·다른 키·기존 출력 경로를 거부했다. 독립 검토자도 발행 전용 테스트 13개를 다시 실행했다. 정식 키 관리·공개 HTTPS 게시·실제 예약 갱신 등록은 검증하지 않았다.

위 기록은 첫 공개 발행 이전의 범위다. 2026-10-13 [Actions 실행 38359118074](https://github.com/project820/korean-protocol/actions/runs/38359118074)가 원본 `91526bb`의 `0.2.0` 순번 `1`을 정식 키로 서명해 공개 Pages에 게시했다. [익명 다운로드 확인](public-download-verification.json)은 공개 주소의 9개 파일 서명과 해시를 검증했다. 후속 버전 발행은 아직 실행하지 않았다.
