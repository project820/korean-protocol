# GitHub Actions에서 서명하고 Pages 배포를 준비한다

발행 개인키는 GitHub의 kproto-release 환경 Secret인 KPROTO_SIGNING_KEY에 보관한다. 환경의 배포 브랜치 정책은 main만 허용한다. 저장소에는 distribution/trust/publisher.pub와 publisher.json의 공개키 지문만 둔다. 로컬 키 생성에 사용한 임시 개인키 사본은 등록 후 제거했다.

현재 저장소는 비공개로 유지한다. KPROTO_PAGES_ENABLED와 KPROTO_ALLOW_FIRST_PUBLICATION 저장소 변수는 모두 false다. 서명 검증용 실행은 비공개 Actions artifact만 만들며 Pages 사이트를 만들거나 게시하지 않는다.

## 서명키의 일치를 확인한다

공개키 지문은 SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc이다. 워크플로는 Secret에서 임시 파일을 만들고 공개키와 대조한 뒤 서명한다. Secret 값은 출력하거나 artifact에 넣지 않는다. 설치자는 검토한 저장소 버전의 공개키와 지문을 신뢰 기준으로 사용한다.

서명키를 바꾸면 기존 설치본의 신뢰 기준도 바뀐다. 키 교체는 별도 전환 작업으로 다루며, 새 키를 만들어 같은 Secret 이름에 조용히 덮어쓰지 않는다.

## 검증 실행과 공개 게시를 구분한다

워크플로는 수동 실행으로 시작한다. 첫 서명 검증에는 first_release를 true로 지정하고 publish는 false로 둔다. 후속 발행은 이전 게시 이력을 인증하며 버전과 순번을 증가시킨다. 모든 실행은 검토된 main 코드를 사용한다.

첫 비공개 검증은 다음 명령으로 실행한다. version은 원본의 숫자 버전과 일치해야 하며 manifest의 유효기간은 발행 시각부터 30일이다.

```sh
gh workflow run release.yml --repo project820/korean-protocol --ref main -f version=0.2.0 -f first_release=true -f publish=false
```

후속 게시는 GitHub Releases에 보관한 최신 발행 이력을 자동으로 선택한다. 이전 artifact를 지정하는 previous_artifact_id는 장기 보관 이전 발행물의 복구에 사용한다. 공개 게시에 실패했으면 실패 job만 재실행하지 않고 새 workflow_dispatch를 시작한다. 게시 요청의 재실행은 차단하며 새 실행에서 현재 공개 상태와 최신 이력을 다시 확인한다. 비공개 서명 검증의 재실행은 허용한다.

공개 게시는 저장소가 공개 상태이고 배포 변수와 명시적인 publish 입력이 모두 허용할 때만 실행한다. 최초 게시는 KPROTO_ALLOW_FIRST_PUBLICATION도 필요하다. 이 조건을 만족하지 않는 게시 요청을 서명 성공이나 공개 성공으로 표시하지 않는다.

정식 공개 전에는 Pages의 Actions 게시 설정, 이전 발행물 보존, 실제 HTTPS 주소와 클라이언트 업데이트를 확인한다. 예정 주소는 https://project820.github.io/korean-protocol 이며, 현재 가동 중인 endpoint로 안내하지 않는다. 사이트 공개와 저장소 공개 시점은 사용자와 정한 개발 완료 시점을 따른다.

## 이전 발행물을 보존한다

후속 정적 배포물은 이전 버전의 콘텐츠와 서명된 manifest를 보존한다. 이전 입력의 출처·서명·버전·순번이 확인되지 않으면 첫 발행으로 초기화하지 않고 중단한다. 장기 이력은 서명된 발행 영수증과 함께 GitHub Releases에 보관한다.

Actions artifact는 90일 보관을 요청한다. [GitHub 보관 정책](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization)은 2026년 10월 1일부터 실행 기록에도 적용되므로, artifact와 실행 기록을 장기 발행 이력으로 의존하지 않는다.

게시가 성공하면 별도 job이 GitHub의 실제 성공 기록과 콘텐츠를 확인하고 발행 영수증에 서명한다. 영수증은 저장소·원본 commit·실행 식별자·서명 시도·게시 시각·버전·순번·manifest 해시·보존 콘텐츠 전체 해시를 묶는다. 서명은 kproto-release 환경 Secret을 사용하며, 이 job에는 저장소 쓰기 권한을 주지 않는다.

다음 보관 job은 개인키 없이 영수증을 검증한 뒤 kproto-history-<버전>-<순번> GitHub Release에 콘텐츠 ZIP과 영수증·서명을 저장한다. 모든 자산을 올린 다음 draft를 완료 상태로 전환한다. 후속 발행은 고정된 공개키로 이 영수증을 확인하므로 이전 Actions 실행 기록이 만료되어도 이어갈 수 있다. 남아 있는 실행 기록과 영수증이 충돌하면 중단한다. 실제 Pages의 stable manifest·서명도 대조하여, 최신 보관본이 삭제됐거나 다른 버전이 게시되어 있으면 새 발행을 중단한다. Pages가 응답하지 않아 최신 상태를 확인할 수 없어도 중단한다.

보관이 중단되면 새 발행 전에 해당 실행의 보관을 복구한다. 아래 RUN_ID에는 실제 Pages 게시에 성공한 실행 번호를 넣는다. archive_only는 새 콘텐츠 서명과 Pages 재게시를 건너뛴다.

```sh
gh workflow run release.yml --repo project820/korean-protocol --ref main -f archive_only=true -f archive_run_id=RUN_ID
```

완료된 보관본이 있으면 서명을 확인하고 재사용한다. 서명된 영수증을 만들기 전에 원본 실행 기록과 artifact가 모두 사라졌다면 게시 성공을 새로 증명할 수 없으므로 중단한다. 관리자가 Releases 이력까지 삭제하면 자동 복구를 보장하지 않는다. GitHub Releases는 Actions 보관 기간과 독립된 보관 장소이며 삭제 방지 백업을 뜻하지 않는다.

현재 정적 콘텐츠는 최대 32개 버전·64MiB로 제한한다. 한도에 도달하면 과거 버전을 조용히 버리지 않고 발행을 중단한다. 비공개 저장 시험은 kproto-rehearsal-* draft만 만들며 정식 발행 이력으로 인정하지 않는다.

## 실제 비공개 서명 실행을 확인했다

[Actions 실행 38342135371](https://github.com/project820/korean-protocol/actions/runs/38342135371)은 GitHub Secret을 사용한 서명·검증·artifact 업로드에 성공했다. Pages artifact 준비와 publish job은 건너뛰었다. GitHub runner의 관련 테스트 76개와 로컬 전체 테스트 242개가 통과했다.

[검증 기록](github-actions-verification.json)은 실행 commit과 공개키·워크플로 해시를 고정한다. 내려받은 artifact는 manifest·서명·콘텐츠 일곱 개만 포함했고, 실제 발행키의 서명을 Codex·Claude Code의 임시 설치 환경에서 검증해 설치·제거했다. 공개 Pages나 실제 사용자 예약 실행을 검증한 결과는 아니다.

## 장기 보관 경로를 비공개로 시험했다

[장기 보관 검증 기록](github-history-verification.json)은 실제 GitHub draft에 서명된 콘텐츠를 저장한 뒤 내려받아 검증한 결과를 담는다. 콘텐츠 9개 파일이 원본과 같았으며, 같은 보관 요청을 반복해도 기존 자산을 바꾸지 않았다. kproto-rehearsal-0.2.0-1 draft는 정식 발행 이력에서 제외했다.

로컬 전체 시험 256개와 관련 시험 90개가 통과했다. 이 중 새 장기 보관 시험 14개는 기록 만료·서명과 내용 변조·불완전 업로드·재시도·실제 최신 버전과의 불일치를 다룬다. 독립 보안 리뷰 후 실제 GitHub 다운로드에서 발견한 HTTP 415 오류를 수정하고 재시험했다. Actions artifact 요청은 JSON Accept를 사용하고 Release 파일 다운로드는 octet-stream을 사용한다.

[갱신된 Actions 실행 38344642913](https://github.com/project820/korean-protocol/actions/runs/38344642913)에서도 관련 시험 90개와 실제 Secret 서명이 통과했다. 내려받은 artifact의 서명을 다시 검증했으며 publish·receipt·archive job은 모두 건너뛰었다.

이 결과는 실제 공개 Pages 게시, 게시 후 발행 영수증 서명, 운영 예약 갱신 성공을 뜻하지 않는다. 해당 경로의 실제 운영 확인은 저장소 공개 시점에 수행한다.

## GitHub의 공식 계약을 따른다

[GitHub Pages 사용자 지정 워크플로](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)의 게시 job은 Pages 쓰기 권한과 OIDC 권한을 사용한다. 서명 job에는 이 권한을 주지 않는다. [GitHub Actions 보안 지침](https://docs.github.com/en/actions/reference/security/secure-use)은 action을 전체 commit SHA에 고정하도록 권고한다.

[GitHub Pages 생성 안내](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)에 따라 비공개 저장소의 Pages 사이트도 공개될 수 있다. 저장소 비공개 설정만으로 사이트 공개가 차단된다고 가정하지 않는다.
