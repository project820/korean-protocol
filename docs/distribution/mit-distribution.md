# 직접 작성한 코드와 한국어 규약을 MIT로 제공한다

2026-10-13 소유자의 선택에 따라 직접 작성한 코드·규약·사전·용례·문서에 루트 [LICENSE](../../LICENSE)의 MIT License를 적용했다. 저작권 표기는 `Copyright (c) 2026 Korean Protocol contributors`다. [NOTICE.md](../../NOTICE.md)는 외부 ASD-STE100 원문·논문·표준·인용문 등 제3자 자료의 권리를 구분하며, 프로젝트가 ASD의 공식 번역판이나 인증 규격이라는 의미로 표시하지 않는다.

ZIP에는 LICENSE와 NOTICE.md를 넣었다. 단독 배포하는 KOREAN-PROTOCOL.md와 설치 캐시의 pack/protocol.md에도 전체 고지를 넣었다. 원래 복제본이 없어져도 남는 두 Python 관리 파일은 MIT 전문을 주석으로 포함한다. 관리 코드의 AST와 기존 세 프로필은 변경 전과 같으며, CONTENT_PATHS·TOOL_FILES·서명 manifest 계약·프로필 크기 제한을 바꾸지 않았다.

컴파일러는 LICENSE와 NOTICE.md를 필수 입력으로 읽고 상세 규약 뒤에 덧붙인다. 서명 발행 도구는 두 파일을 보호된 읽기 경로로 캡처한 뒤 해당 스냅샷으로 컴파일해 원본 변경에 따른 혼합을 막는다. 고지가 빠지거나 상세 규약에 최신 고지가 반영되지 않으면 발행 검증을 통과하지 못한다. 기존 프로필에 라이선스를 억지로 넣어 28KiB 제한을 넘기거나 규칙을 삭제하지 않았다.

## 패키지와 설치 결과를 대조했다

[미리보기 8](https://github.com/project820/korean-protocol/releases/tag/untagged-7cf837d2c3ac9241b318)은 e5d0c5d의 비공개 GitHub 초안이다. ZIP은 32개 파일, 393,478바이트이며 SHA-256은 `cec56ce395e8d270a185e60a2322c055619be3ca0c7a691dcd8bc662f89447b2`다. GitHub에서 다시 내려받은 ZIP·단독 규약·체크섬 세 파일이 로컬 원본과 일치한다.

[실제 패키지 시험](mit-package-verification.json)은 ZIP 체크섬, 단독 문서의 중복 없는 고지, Codex·Claude Code의 정확한 프로필 설치, 캐시·지속 관리 코드의 전체 허가문, 기존 사용자 내용 보존을 확인했다. 원본 패키지 폴더를 이동한 뒤에도 상태 확인과 제거가 통과했다. 사용자 전역 설정은 변경하지 않았다.

최종 자동 시험 300개가 통과했다. 처음 추가한 검사에서 예전 고정 관리 폴더를 가정해 실패했으며, 설치기가 반환하는 실제 관리 경로를 사용하도록 검사만 수정한 뒤 전체를 다시 실행했다. 독립 Astra/high 검토자는 빌드·서명 입력 캡처·관리 코드 고지를 대조했고 남은 결함을 발견하지 않았다.

## 실제 서명물에도 고지가 포함됐다

[GitHub Actions 38357637401](https://github.com/project820/korean-protocol/actions/runs/38357637401)은 e5d0c5d에서 실제 GitHub Secret으로 서명했고 95개 검사를 통과했다. publish·receipt·archive는 건너뛰었다. artifact 11793470869의 서명된 상세 규약에 두 고지가 정확히 한 번씩 있으며 모든 콘텐츠가 현재 원본과 같다.

[서명물 설치 기록](mit-actions-verification.json)은 두 임시 호스트의 서명 검증, 고지 포함 캐시, 제거 후 원문 복원을 확인한다. manifest와 서명은 mit-actions-artifact에 보존했다. 이 발행물은 비공개 시험용 0.2.0·순번 1이며 공개된 이전 버전을 업그레이드한 증거는 아니다. ZIP 자체는 미서명 오프라인 미리보기이고 자동 갱신은 기본으로 꺼져 있다.

라이선스 선택은 완료됐다. 저장소 공개·Pages 활성화·첫 정식 게시와 그 뒤의 공개 endpoint 검증은 아직 수행하지 않았다.
