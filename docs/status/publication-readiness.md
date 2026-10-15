# 0.7.0의 공개 발행 상태를 확인한다

서명 콘텐츠 **0.7.0·순번 3**과 사용자 패키지 **v0.7.0**은 공개 발행을 완료했다. 현재 원본의 표기는 `0.7.0-draft`이며 관리 엔진은 `0.2.0`이다. 공개 배포의 성공은 언어 효과의 검증과 구분한다.

| 발행 대상 | 원본과 제공 범위 | 확인 근거 |
| --- | --- | --- |
| 서명 콘텐츠 | `67f537e`의 일곱 콘텐츠 파일과 manifest·서명을 공개 HTTPS로 제공한다. | [발행 실행 38671093558](https://github.com/project820/korean-protocol/actions/runs/38671093558)의 sign·publish·receipt·archive가 성공했고 [서명·갱신 기록](../distribution/public-0.7.0-verification.md)을 남겼다. |
| 사용자 패키지 | `7e01d53`의 설치 도구·안내로 만든 미서명 ZIP·`KOREAN-PROTOCOL.md`·`SHA256SUMS`를 제공한다. | [v0.7.0 다운로드](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)의 세 자산은 익명 다운로드와 해시 일치를 확인했다. |
| 서명 이력 | `kproto-history-*` 릴리스는 기존 서명 콘텐츠와 발행 영수증을 보존한다. | [보관 복구 실행 38676551697](https://github.com/project820/korean-protocol/actions/runs/38676551697)의 receipt·archive가 성공했다. |
| 코드 검사 | `7e01d53`의 Linux·macOS 검사 결과를 출시 기준으로 사용한다. | [CI 실행 38676135546](https://github.com/project820/korean-protocol/actions/runs/38676135546)이 통과했다. |

서명 이력의 읽기 쉬운 제목·본문 이관은 기존 자산의 식별자·크기·해시와 태그를 보존했다. 이 이관과 보관 복구에서 새 콘텐츠를 서명하거나 Pages를 재게시하지 않았다. 자세한 범위는 [공개 파일 점검](../maintenance/repository-inventory.md)을 따른다.

## 후속 문서와 불변 발행물을 구분한다

이 문서는 main의 현행 안내다. 후속 문서 수정은 이미 공개한 `v0.7.0` ZIP과 첨부 파일에 자동 반영되지 않는다. 같은 이름으로 로컬에서 다시 만든 ZIP도 발행 원본이 다르면 기존 공개 자산과 동일하다고 표시하지 않는다. 발행 자산은 해당 릴리스의 체크섬으로 확인한다.

다음 콘텐츠를 발행하려면 원본·버전·호환성·이전 서명 이력을 검증하고 발행 절차를 다시 수행해야 한다. 문서 개정만으로 기존 서명 manifest나 콘텐츠 버전을 바꾸지 않는다. 현재 언어 검증의 남은 항목은 [요구사항과 검증 상태](requirements.md)에서 확인한다.

## 이전 게시 준비 기록을 찾는다

2026-10-13의 비공개 저장소·미게시·시험용 HTTPS 상태는 [개발·발행 연혁](chronology-20261013.md)과 [첫 공개 감사](completion-audit-20261013-public.md)에 보존한다. 당시 파일 수·ZIP 크기·해시·테스트 수는 그 기준본의 결과이며 0.7.0 발행물의 증거로 재사용하지 않는다.
