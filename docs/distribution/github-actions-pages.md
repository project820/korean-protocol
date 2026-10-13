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

후속 게시는 first_release 대신 최신 성공 게시의 previous_artifact_id를 전달한다. 공개 게시에 실패했으면 실패 job만 재실행하지 않고 새 workflow_dispatch를 시작한다. 게시 요청의 재실행은 차단하며 새 실행에서 현재 공개 상태와 최신 이력을 다시 확인한다. 비공개 서명 검증의 재실행은 허용한다.

공개 게시는 저장소가 공개 상태이고 배포 변수와 명시적인 publish 입력이 모두 허용할 때만 실행한다. 최초 게시는 KPROTO_ALLOW_FIRST_PUBLICATION도 필요하다. 이 조건을 만족하지 않는 게시 요청을 서명 성공이나 공개 성공으로 표시하지 않는다.

정식 공개 전에는 Pages의 Actions 게시 설정, 이전 발행물 보존, 실제 HTTPS 주소와 클라이언트 업데이트를 확인한다. 예정 주소는 https://project820.github.io/korean-protocol 이며, 현재 가동 중인 endpoint로 안내하지 않는다. 사이트 공개와 저장소 공개 시점은 사용자와 정한 개발 완료 시점을 따른다.

## 이전 발행물을 보존한다

후속 정적 배포물은 이전 버전의 콘텐츠와 서명된 manifest를 보존한다. 이전 입력의 출처·서명·버전·순번이 확인되지 않으면 첫 발행으로 초기화하지 않고 중단한다. Actions artifact의 보존 기간은 무기한이 아니므로, artifact가 사라졌을 때의 장기 보존·복구 경로를 공개 전에 검증해야 한다.

현재 구현은 artifact 보존을 90일로 요청하며 최대 32개 콘텐츠 버전을 처리한다. 이전 artifact가 만료되거나 없어지면 후속 발행을 거부한다. 장기 보존 경로를 연결하기 전에는 운영 배포 준비가 모두 끝났다고 표시하지 않는다.

## 실제 비공개 서명 실행을 확인했다

[Actions 실행 38342135371](https://github.com/project820/korean-protocol/actions/runs/38342135371)은 GitHub Secret을 사용한 서명·검증·artifact 업로드에 성공했다. Pages artifact 준비와 publish job은 건너뛰었다. GitHub runner의 관련 테스트 76개와 로컬 전체 테스트 242개가 통과했다.

[검증 기록](github-actions-verification.json)은 실행 commit과 공개키·워크플로 해시를 고정한다. 내려받은 artifact는 manifest·서명·콘텐츠 일곱 개만 포함했고, 실제 발행키의 서명을 Codex·Claude Code의 임시 설치 환경에서 검증해 설치·제거했다. 공개 Pages나 실제 사용자 예약 실행을 검증한 결과는 아니다.

## GitHub의 공식 계약을 따른다

[GitHub Pages 사용자 지정 워크플로](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)의 게시 job은 Pages 쓰기 권한과 OIDC 권한을 사용한다. 서명 job에는 이 권한을 주지 않는다. [GitHub Actions 보안 지침](https://docs.github.com/en/actions/reference/security/secure-use)은 action을 전체 commit SHA에 고정하도록 권고한다.

[GitHub Pages 생성 안내](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)에 따라 비공개 저장소의 Pages 사이트도 공개될 수 있다. 저장소 비공개 설정만으로 사이트 공개가 차단된다고 가정하지 않는다.
