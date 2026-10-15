# 2026-10-12 로컬 환경 확인 기록

> **과거 기록을 보존한다.** 아래 버전·검증 수치·미완료 항목은 작성 당시의 상태다. 현행 0.7의 사용법은 [설치 안내](../../INSTALL.md), 확인 범위는 [현재 상태](requirements.md)를 따른다. 과거 결과를 0.7의 재검증으로 계산하지 않는다.

이 문서는 호스트 지원표에 있던 당시 환경·시험 기록을 정리한다. 개인 홈 경로는 일반화했으며 정확한 원본은 [당시 저장소 기록](https://github.com/project820/korean-protocol/blob/52008bdd1eabf0d5e3d359898bedcaebaf057e0a/docs/distribution/host-support.md)에 보존한다. 버전과 시험 결과는 2026-10-12의 값이며 현재 설치 안내나 V7 검증 결과가 아니다. 현재 지원 범위는 [호스트 지원표](../distribution/host-support.md)를 따른다.

## 당시 macOS 시험 범위를 보존한다

Darwin 27.0.0/Python 3.9.6에서 실제 SSHSIG·임시 installer/updater·launchd 생성/해제·실프로세스 중단 복구를 포함한 78 테스트를 통과했다. 당시 이 시험은 실제 host 추론과 launchctl 등록을 검증하지 않았다. 이후 소유 작업의 등록·실행·해제 결과는 별도 [예약 시험](../distribution/scheduler-registration-verification.json)과 [공개 예약 시험](../distribution/public-scheduler-verification.json)에 남겼다.

## 당시 조회 결과를 구분한다

다음 표기는 당시 조회 결과에서 개인 홈 경로만 일반화한 것이다. 그대로 실행한 원문은 위 커밋의 기록을 따른다.

```text
~/.local/bin/codex --version
  exit=0; codex-cli 0.162.1
/usr/bin/python3 --version
  exit=0; Python 3.9.6
/usr/bin/ssh-keygen -Y verify
  exit=1; Too few arguments for verify: missing namespace
```

마지막 명령은 verify 옵션의 존재만 확인하며 별도의 runtime tests에서 실제 서명을 검증했다. `~/.codex/AGENTS.md`가 일반 파일이고 `.codex/AGENTS.override.md`가 없다는 사실을 확인했다. 기존 AGENTS.md 본문과 사용자 설정을 수정하지 않았다. `gemini`와 `cursor` 명령은 PATH에서 찾지 못했으며 이 결과를 GUI 앱 부재로 확대하지 않는다. 추가로 `codex debug prompt-input -c project_doc_max_bytes=256 probe`를 임시 CODEX_HOME/Git project에서 실행하여 [5개 loader matrix](../distribution/codex-loader-evidence.json)를 기록했으며 네트워크·모델 호출 없이 prompt rendering만 확인했다.
