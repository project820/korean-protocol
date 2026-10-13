# 0.3.0의 공개 발행과 실제 업그레이드를 확인했다

2026-10-13 사용자 승인 후 `468322666bb2c85b2700c50fc701e6d4f82a002f`의 규약을 **0.3.0·순번 2**로 공개했다. [발행 실행 38391389450](https://github.com/project820/korean-protocol/actions/runs/38391389450)은 sign·publish·receipt·archive 작업이 모두 성공했고, [저장한 실행 결과](../../evaluation/release-0.3.0-20261013/public-actions-run.json)는 커밋과 각 작업의 결론을 보존한다. [장기 보관 릴리스](https://github.com/project820/korean-protocol/releases/tag/kproto-history-0.3.0-2)는 초안이 아니며 signed-content ZIP과 서명된 발행 영수증을 포함한다. [보관 조회 기록](../../evaluation/release-0.3.0-20261013/public-history-release.json)은 태그와 첨부물의 해시를 기록한다.

공개 설치 주소는 `https://project820.github.io/korean-protocol`이다. 콘텐츠 원본의 `0.3.0-draft` 표시는 연구·개발 초안의 품질 범위로 유지한다. 오프라인 미리보기 ZIP은 계속 미서명 로컬 설치본이며, `SHA256SUMS`만으로 게시자 인증을 대신하지 않는다.

## 게시자 서명으로 실제 공개 콘텐츠를 확인했다

[공개 업그레이드 기록](../../evaluation/release-0.3.0-20261013/public-upgrade-result.json)은 고정 게시자 공개키 지문 `SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc`으로 공개 0.2.0·순번 1과 0.3.0·순번 2의 SSHSIG를 검증했다. 공개 0.3.0의 manifest SHA-256은 `7290c9ab687e0411d659864e813f03868b5c71d3da916ef2081ef56618154aa8`이며 signature SHA-256은 `3353716bd8f91edc30c9dc7d176c9b48d3c0fee7746b48edc77f570652fd20d5`다. 콘텐츠 7개와 설치 캐시의 바이트가 원본과 일치했고, 캐시의 manifest·signature도 받은 공개 바이트와 일치했다. [독립 공개 검토](../../evaluation/release-0.3.0-20261013/public-independent-review.json)는 저장한 두 manifest의 서명, 콘텐츠와 원본·발행 커밋의 일치, 실행 코드·드라이버 해시를 재확인했다.

## 두 임시 호스트에서 공개 0.2.0을 0.3.0으로 갱신했다

Codex·Claude Code는 각각 11단계를 통과했다. 게시자 서명으로 인증한 0.2.0 설치 상태를 보존한 뒤 현행 runtime·helper로 실제 공개 HTTPS의 0.3.0을 받았다. TEST 키로 다시 서명하지 않았고, 사용자 전역 설정·신뢰 저장소·예약 작업을 변경하거나 모델을 호출하지 않았다.

업그레이드는 규약 OFF·높임말 설정을 보존했고, ON 전환은 현행 프로필 전체를 주입했다. 두 높임말 선택과 사용자 앞·뒤 내용의 보존을 확인했다. 오프라인 갱신은 종료 코드 3을 반환하면서 마지막 검증 프로필·캐시·설정을 보존했고, 시작 wrapper의 호스트 명령은 종료 코드 0을 반환했다. 제거는 사용자 바이트를 정확히 복원했다.

직전·직후 Python crash report의 파일명·stat 비교에서 새 파일이나 변경 파일은 없었다. 보고서 내용을 읽지 않았으며 지연 생성되는 보고서는 이 즉시 비교에서 제외하지 못한다.

## 구버전 실행 코드 이관은 별도 범위로 검증했다

[구버전 코드 이관 기록](../../evaluation/release-0.3.0-20261013/historical-helper-migration.md)은 지정된 Git 커밋 `2067f541d2cc97d94f4a8625de2015d2330aeb1b`의 실제 0.2.0 runtime·helper를 실행해 현행 코드로 이관했고, 두 호스트에서 각각 9단계를 통과했다. 이 시험은 임시 TEST 서명과 생성된 소유 scheduler plist를 사용했다. 실제 등록된 launchd 작업의 이관은 시험하지 않았다.

기존 외부 wrapper는 자동으로 바뀌지 않으므로 사용자가 configure 결과의 `runtime_argv.run` 또는 `runtime_commands.run`으로 직접 교체해야 한다. 콘텐츠 자동 업데이트가 Python 관리 코드까지 자동 교체한다는 주장은 하지 않는다. 실제 모델 실행·재로그인·절전 복귀, 전문가 승인·사람 독해·모델 전체 성능은 이 발행과 설치 검증의 범위에 포함하지 않는다.

[첫 0.2.0 공개 기록](public-download-verification.json)과 [공개 전 TEST 서명 시험](../../evaluation/release-0.3.0-20261013/candidate-upgrade-smoke.json)은 당시의 증거로 보존한다. 이번 공개 발행은 기존 모델 입력·출력·평정·동결 해시와 기능 대응 49/53의 의미를 바꾸지 않는다.
