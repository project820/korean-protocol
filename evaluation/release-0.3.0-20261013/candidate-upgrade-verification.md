# 실제 후보 콘텐츠의 로컬 서명 업그레이드가 두 호스트에서 통과했다

[실행 기록](candidate-upgrade-smoke.json)은 현재 런타임·지속 관리 도구를 사용하는 Codex·Claude Code의 임시 사용자 환경에서 공개 0.2.0 콘텐츠를 실제 0.3.0-draft 원본 콘텐츠로 갱신했다. 각 호스트에서 CLI 20단계가 통과했다. 이 결과는 시험 키를 사용하는 로컬 콘텐츠 업그레이드이며, 0.3.0의 게시자 서명·공개 배포 완료를 뜻하지 않는다. 원래 0.2.0 실행 파일에서 새 실행 파일로 이행하는 경로는 이 스크립트로 검증하지 않았다.

스크립트는 `https://project820.github.io/korean-protocol`의 공개 0.2.0 manifest·서명·콘텐츠 7개를 먼저 내려받았다. 고정한 게시자 공개키 지문 `SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc`로 SSHSIG와 파일 해시를 확인했다. 실제 게시자 서명을 유지한 0.2.0을 각 호스트의 별도 임시 환경에 설치하고 원문 복원까지 확인했다. 그 다음 바이트가 같은 0.2.0 콘텐츠와 현행 원본의 0.3.0-draft 콘텐츠를 별도의 임시 TEST 키로 서명해 시험했다.

시험 manifest의 숫자 버전은 0.3.0이고, JSON 원본 세 파일의 버전은 모두 0.3.0-draft다. 후보의 7개 콘텐츠 바이트는 원본과 같으며, 시험을 위한 표식이나 본문 수정을 넣지 않았다. 후보 업그레이드는 기본 인증서 검증을 유지한 TLS와 `localhost:443`만 허용하는 임시 CONNECT 프록시를 통해 manifest·서명·콘텐츠를 합친 9개 파일을 받았다. 임시 CA 경로·프록시는 자식 프로세스 환경에만 적용했다.

두 호스트에서 OFF와 존댓말 ON 설정이 0.2.0→0.3.0 갱신 후에도 유지됐다. OFF 상태의 설치 파일 바이트는 갱신 전후에 같았다. ON으로 바꾸면 후보 프로필 전체와 검증된 후보 캐시 경로가 들어갔고, 존댓말 ON·OFF 오버레이도 각각 확인했다. 사용자 원문의 CRLF 바이트와 설치 후 수동으로 추가한 뒷부분은 설정 변경·업그레이드·제거 후에도 보존됐다.

잘못된 릴리스 서명은 종료 코드 5를 반환하며 설치 파일·캐시·state.json을 보존했다. 명시적 캐시 롤백은 OFF·존댓말·상위 순번을 유지했고, ON에서 공개 0.2.0 본문을 다시 주입했다. 후보 캐시로 돌아오면 이전 후보 ON 바이트와 같았다. 서버를 끈 뒤 갱신은 종료 코드 3을 반환했으며, 검증된 후보 프로필·7개 캐시 파일과 wrapper의 호스트 명령 종료 코드 0을 확인했다.

실행은 이미 제공된 Python 3.12.14·OpenSSL 3.5.8을 사용했다. 시스템 Python 3.9.6으로 실행한 새 오프라인 가드 검사 5개와 기존 smoke 검사 6개가 모두 통과했다. 시스템 Python의 임시 CA 로딩이나 TLS 성공을 이 결과로 주장하지 않는다. 실제 모델 호출·전역 설치·전역 신뢰 저장소 변경·실제 스케줄러 등록·직접 443 포트 바인딩은 수행하지 않았다.

실행 직전과 직후 사용자·시스템 DiagnosticReports 디렉터리의 Python 관련 파일명·mtime·크기를 비교했다. 기존 Python 보고서 19개를 확인했고 새 파일이나 변경 파일은 0개였으며 조회하지 못한 디렉터리는 없었다. 보고서 본문은 읽지 않았다. 이 비교는 즉시 생성된 보고서를 다루며 macOS가 나중에 생성하는 보고서를 제외하지 않는다.

다음 명령으로 실행했고, 기존 증거 파일을 덮어쓰지 않는 새 출력 경로가 필요하다.

```sh
/Users/m5max/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tests/manual_candidate_upgrade_smoke.py --runtime-root . --output evaluation/release-0.3.0-20261013/candidate-upgrade-smoke.json
python3 -B -m unittest discover -s tests -p test_candidate_upgrade_smoke.py
python3 -B -m unittest discover -s tests -p 'test*smoke.py'
```

첫 명령은 pass와 종료 코드 0을 반환했다. 두 번째 명령은 5/5, 세 번째 명령은 11/11을 통과했다. 모든 후보·런타임·관리 도구·기존 HTTPS helper·새 helper 해시는 실행 기록에 남겼고 실행 도중 원본이 바뀌지 않았음을 대조했다. 시험 개인키·TLS 재료·설치 상태는 임시 디렉터리 종료 시 제거됐다.
