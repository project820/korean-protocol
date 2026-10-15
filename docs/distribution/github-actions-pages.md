# 0.7.0의 서명 콘텐츠와 사용자 패키지를 발행한다

현재 서명 콘텐츠는 0.7.0·순번 3이며 원본은 `67f537e`다. [v0.7.0 사용자 패키지](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)는 별도 원본 `7e01d53`의 ZIP·채팅 파일·체크섬이다. 둘의 콘텐츠 일곱 파일은 같지만 설치 도구·안내 원본과 서명 콘텐츠 원본은 구분한다.

## 발행 경로와 권한을 구분한다

| 경로 | 산출물과 권한 |
| --- | --- |
| `sign` | kproto-release 환경의 `KPROTO_SIGNING_KEY`를 사용해 manifest를 서명한다. Pages 쓰기·OIDC 권한은 주지 않는다. |
| `publish` | 검증한 정적 콘텐츠를 Pages에 게시한다. |
| `receipt`·`archive` | 성공한 공개 게시의 출처를 서명하고 장기 보관 릴리스에 저장한다. |
| `product` | 성공한 보관 뒤 사용자 ZIP·채팅 파일·체크섬을 별도 버전 릴리스로 게시한다. 이 단계는 서명 개인키를 사용하지 않는다. |

공개키와 지문은 `distribution/trust/publisher.pub`·`publisher.json`에 고정한다. 워크플로는 Secret의 키와 공개키가 일치하는지 확인하며 키값을 로그·artifact에 남기지 않는다. 키 교체는 기존 설치의 신뢰 전환이므로 별도 검토 없이 같은 Secret에 덮어쓰지 않는다.

현재 발행 동작의 기준은 [release.yml](../../.github/workflows/release.yml)과 현재 관리 코드다. 과거 실행 수·비공개 상태는 [개정 전 운영 기록](https://github.com/project820/korean-protocol/blob/dacbbc239fc9dbb22f2ddb87119d4ac7161b2e3c/docs/distribution/github-actions-pages.md)에 보존하며 현재 동작으로 옮기지 않는다.

## 다음 콘텐츠 버전을 공개한다

아래 `NEXT_VERSION`은 새 원본의 숫자 버전이며 기존 0.7.0보다 커야 한다. 현재 공개본을 다시 첫 발행으로 초기화하지 않는다.

```sh
gh workflow run release.yml \
  --repo project820/korean-protocol \
  --ref main \
  -f version=NEXT_VERSION \
  -f first_release=false \
  -f publish=true
```

워크플로는 검토된 main과 최신 인증 보관 이력을 사용하며 버전·순번을 증가시킨다. 공개 저장소·Pages 허용 변수·명시적 publish 입력을 확인한다. 최초 게시 전용 `KPROTO_ALLOW_FIRST_PUBLICATION`은 후속 발행에 사용하지 않는다.

공개 게시 요청의 재실행은 차단한다. 실패했으면 현재 Pages·보관 상태를 다시 확인하는 새 workflow_dispatch를 시작한다. `publish=false`의 서명 검증은 공개 게시가 아니며 사용자 릴리스도 만들지 않는다.

## 보관 이력과 본문 안내를 분리한다

`kproto-history-<version>-<sequence>`에는 서명 콘텐츠 ZIP·발행 영수증·서명을 보존한다. 본문은 사람이 읽는 용도·사용법·검증 안내이며 출처 구조는 `archive-provenance.json`에 둔다. 기존 형식의 JSON 본문은 호환 reader로 읽지만 새 기록은 자산과 안내를 분리한다.

후속 발행은 고정 공개키로 이전 영수증을 인증하고 실제 Pages의 stable manifest·서명과 대조한다. 불일치·삭제·연락 불가를 첫 발행으로 간주하지 않고 중단한다. GitHub Releases 보관은 삭제 방지 백업을 보장하지 않는다.

보관이 중단됐으면 실제 공개 게시에 성공한 `RUN_ID`로 복구한다.

```sh
gh workflow run release.yml \
  --repo project820/korean-protocol \
  --ref main \
  -f archive_only=true \
  -f archive_run_id=RUN_ID
```

`archive_only`는 새 콘텐츠 서명·Pages 재게시·사용자 패키지 발행·Latest 변경을 하지 않는다. 출처 기록과 artifact가 사라져 게시 성공을 증명할 수 없으면 중단한다.

## 사용자 패키지를 별도 릴리스로 제공한다

`product`는 main의 공개 발행에서 보관이 성공한 뒤에만 실행한다. 현재 공개 저장소·main 전체 SHA·커밋된 입력과 발행 코드·최신 서명 영수증·실제 Pages·일곱 콘텐츠 해시를 대조한다. 임시 draft의 세 첨부물을 바이트로 확인한 뒤 공개하고 Latest로 지정한다. 충돌·더 새 버전은 덮어쓰지 않는다.

현재 [ZIP](https://github.com/project820/korean-protocol/releases/download/v0.7.0/korean-protocol-0.7.0-draft.zip), [KOREAN-PROTOCOL.md](https://github.com/project820/korean-protocol/releases/download/v0.7.0/KOREAN-PROTOCOL.md), [SHA256SUMS](https://github.com/project820/korean-protocol/releases/download/v0.7.0/SHA256SUMS)는 `7e01d53`의 불변 산출물이다. main 문서 개정만으로 같은 태그의 파일을 교체하지 않는다.

게시 후 익명 다운로드·해시·설치·갱신을 각각 확인한다. [0.7.0 발행 기록](public-0.7.0-verification.md)은 확인된 사실과 남은 한계를 구분한다. manifest 만료 뒤에도 기존 로컬 설치는 유지하지만 신규 원격 수락을 계속 제공하려면 만료 전 후속 콘텐츠 버전을 발행해야 한다.
