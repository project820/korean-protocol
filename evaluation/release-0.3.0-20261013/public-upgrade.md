# 실제 공개 0.2.0 → 0.3.0 업그레이드 검증

Codex와 Claude Code의 임시 설치 두 개에서 실제 공개 HTTPS 업그레이드가 통과했다.

1. 게시 전에 공개 0.2.0(sequence 1)의 manifest, SSHSIG 서명, 일곱 개 파일을 고정 공개 키로 인증했다.
2. 현재 runtime/helper로 두 임시 홈에 공개 HTTPS 0.2.0을 설치하고, 규칙 적용 OFF·존댓말 ON을 저장했다.
3. 게시 후 같은 설치의 저장된 update 명령으로 실제 공개 HTTPS 0.3.0(sequence 2)을 받았다.
4. 새 공개 manifest와 서명을 별도로 인증하고, 일곱 개 공개 파일과 캐시 파일이 작업 트리 후보 파일의 정확한 바이트와 일치함을 확인했다.
5. OFF 상태의 설치 파일이 바뀌지 않았고 존댓말 ON도 유지됐음을 확인했다.
6. ON 전환 후 완전한 0.3.0 프로필·캐시 경로·존댓말 overlay가 들어갔음을 확인하고, 두 말투 선택의 왕복을 검증했다.
7. 공개 source URL을 유지한 채 하위 프로세스에만 localhost CONNECT 거부 프록시를 지정했다. 업데이트는 네트워크 오류 코드 3으로 종료했고, 마지막 인증 캐시·프로필·설정은 유지됐다.
8. 오프라인 wrapper의 로컬 호스트 명령이 코드 0으로 종료됐으며, 제거 후 사용자 CRLF 앞뒤 문구가 정확히 보존됐음을 확인했다.
9. 임시 설치 홈을 정리했고, 즉시 확인한 Python crash-report 파일/stat에 새 변화가 없었다.

운영 서명은 임시 키로 다시 서명하지 않았다. 운영 비밀 키, 사용자 전역 설정, 전역 인증서 저장소, 실제 스케줄러에는 접근하거나 변경하지 않았다.

이 검증은 현재 runtime/helper로 설치한 공개 콘텐츠의 실제 업그레이드를 확인했다. 0.2.0 당시 runtime/helper 실행 파일의 이전, 실제 모델 응답, 로그인, sleep/wake, 스케줄러 등록은 별도 검증 범위다. Crash-report 확인은 지연 보고서 생성을 배제하지 않는다.

실행에는 기존 번들 Python을 사용했다.

```sh
/Users/m5max/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B /tmp/kproto-public-upgrade-030.py prepare
/Users/m5max/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B /tmp/kproto-public-upgrade-030.py finish --context /private/var/folders/yy/jvyvnf4x4_1b9pf7p3fq18gr0000gn/T/kproto-public-upgrade-030-4l9d8i2n/context.json
```

검증 당시 드라이버는 `public-upgrade-driver.py`에 보존했다. 이전 0.2.0 공개 기준선과 임시 홈은 게시 전에 준비해야 하므로, 현재 공개 0.3.0 상태에서는 이 prepare 명령이 0.2.0 기준선 요구를 충족하지 않는다.

정확한 runtime/helper·공개 키·콘텐츠·프로필 해시와 각 명령의 종료 코드는 `public-upgrade-baseline.json`과 `public-upgrade-result.json`에 기록했다. 인증에 사용한 두 버전의 공개 manifest와 SSHSIG 서명은 `public-upgrade-0.2.0-release.json[.sig]`와 `public-upgrade-0.3.0-release.json[.sig]`에 보존했다.
