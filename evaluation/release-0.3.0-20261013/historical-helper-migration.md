# 실제 구버전 코드에서 현행 관리 코드로 이관하는 경로를 확인했다

Codex·Claude Code에서 지정된 로컬 Git 커밋 `2067f541d2cc97d94f4a8625de2015d2330aeb1b`의 0.2.0 관리 코드를 실제로 실행하고 현행 관리 코드로 이관했다. 두 호스트 모두 CLI 9단계를 통과했다. [실행 기록](historical-helper-migration.json)은 Git 커밋·tree·추출 파일 해시, CLI 명령과 종료 코드를 보존한다. 해당 커밋의 공개 이력은 작업 지시의 정보이며, 이 로컬 시험이 외부 공개 상태를 증명하지는 않는다.

구버전 커밋의 콘텐츠 7개는 게시자 서명으로 인증한 [공개 0.2.0 기록](candidate-upgrade-smoke.json)의 파일 해시와 모두 일치했다. Git 객체의 정확한 바이트를 임시 디렉터리로 추출하고 실제 구버전 설치기로 영구 관리 폴더에 설치했다. 콘텐츠에는 임시 TEST 키의 서명을 사용했다. 구버전 실행 파일을 현행 코드의 mock으로 바꾸지 않았다.

현행 `distribution/agent_install.py configure --protocol off --honorifics on`은 별도의 현행 관리 폴더를 만들고, 생성된 소유 scheduler plist의 runtime 경로를 갱신했다. plist의 나머지 필드·인수, source·scheduled mode와 구버전 관리 폴더의 전체 바이트는 보존했다. 이 명령은 기존에 저장한 wrapper argv와 다른 새 관리·wrapper argv를 반환했다. 실제 launchctl 등록이나 사용자 전역 환경 변경은 수행하지 않았다.

기존에 저장한 구버전 wrapper argv를 직접 실행하는 진단에서는 구버전 runtime이 OFF를 무시하고 후보 본문을 주입하며 높임말 오버레이도 넣지 않는 동작을 재현했다. 상태의 설정 필드는 OFF·honorifics ON으로 남았다. 이 경로는 [기존 설정 문서](../../docs/distribution/application-controls.md)에 명시된 미지원 외부 wrapper이며 자동 이관 성공으로 보고하지 않는다. 사용자는 구버전 wrapper 호출을 현행 configure 결과의 `runtime_argv.run` 또는 `runtime_commands.run`으로 명시적으로 교체해야 한다.

현행 영구 helper로 OFF를 재적용하면 진단 전의 OFF 바이트로 복구됐다. 현행 runtime의 후보 콘텐츠 갱신은 OFF·높임말 설정을 유지했고, 새 wrapper의 호스트 명령은 종료 코드 0을 반환했다. ON은 후보 프로필 전체와 선택한 높임말 오버레이를 넣었다. 제거 후에도 사용자 CRLF 원문과 수동으로 추가한 뒷부분의 바이트를 보존했다.

다음 명령은 이미 제공된 Python 3.12.14와 임시 TLS CA·제한된 localhost CONNECT 프록시를 사용해 종료 코드 0과 pass를 반환했다.

```sh
/Users/m5max/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tests/manual_historical_helper_migration.py --runtime-root . --output evaluation/release-0.3.0-20261013/historical-helper-migration.json
```

이 증거는 생성된 소유 예약 파일의 이관을 다룬다. 실제 등록된 launchd 작업의 이관, 게시자 서명을 사용하는 공개 0.3.0 갱신, 모델 실행·로그인·절전 복귀는 검증하지 않았다. 직전·직후 Python crash report 파일명·stat 비교에서 기존 19개와 새 파일·변경 파일 0개를 확인했으며, 지연 생성되는 보고서는 제외하지 못한다. 콘텐츠 업데이트만으로 Python 관리 코드가 자동 교체된다는 주장은 하지 않는다.
