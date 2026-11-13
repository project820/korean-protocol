# v0.11.0 후보 패키지의 검증·설치 절차

이 도구는 서명 없는 로컬 후보 ZIP을 만든다. 원문·KP·STE 정식 비교는 미완료다.

- **기본 버전:** `0.11.0-candidate`를 사용한다.
- **수동 공개 스킬 설치 기준:** 태그 `v0.11.0`을 사용한다. 아래 후보 ZIP 도구는 현재 작업 트리의 바이트를 사용한다.
- **SKILL.md SHA-256:** `c09172014b872636afad1cac194e9c634a99e9fe165711cdd405a5249dd983c6`이다.

**v0.11.0 파일럿은 이 도구의 설치 통과 근거가 아니다.** 설치 계획에는 독립 평가·매체·호스트 근거가 필요하다. 수동 스킬 설치는 [INSTALL.md](../../INSTALL.md)를 따른다.

## 준비

저장소 루트에서 [패키지 도구](../../distribution/skill_package.py)를 실행한다. 아래 `study`는 실제 검증 근거를 둘 예시 경로다.

설치 구성은 이전 v0.10.1과 같은 13개 파일이다. v0.11.0에서는 `SKILL.md`만 바뀌었다. 새 0절과 4절의 추가 문장은 [변경·검증 상태](output-formats-candidate-status.md)에 기록한다.

### 포함 파일을 확인한다

| 원본 경로 | ZIP 안의 `korean-protocol/` 아래 경로 |
| --- | --- |
| `skills/korean-protocol/**` | 접두사를 제거하고 하위 경로를 유지한다. |
| `specification/rules.json` | 같은 경로를 유지한다. |
| `lexicon/core.json` | 같은 경로를 유지한다. |
| `lexicon/domains/software.json` | 같은 경로를 유지한다. |
| `LICENSE`, `NOTICE.md` | 같은 파일명을 유지한다. |

스킬 하위의 새 참고 파일·자산·보조 스크립트도 포함한다. ZIP 파일 권한은 `0644`로 고정한다. Python 보조 스크립트는 `python3`로 실행한다.

빌드·검증은 포함된 스크립트를 실행하지 않는다. 평가 디렉터리·STE 프로필·원시 녹취·비공개 자료는 입력 경로에서 제외한다. 스킬 안의 금지 경로·숨김 경로·심볼릭 링크는 빌드를 중단시킨다.

금지 이름은 `evaluation`, `ste`, `raw`, `private` 등이다. 민감 자료의 내용은 이름만으로 판별할 수 없다. 스킬에 넣는 파일의 범위를 검토한다.

### 고정 값의 뜻을 구분한다

| 기록 | 뜻 |
| --- | --- |
| `source_hashes` | 저장소 상대 경로별 SHA-256을 보존한다. |
| `files` | 설치 상대 경로별 SHA-256을 보존한다. |
| `candidate_id` | 정렬한 `source_hashes`의 직렬화 바이트를 해시한다. |
| `package_sha256` | ZIP 전체 SHA-256을 기록한다. |
| `provenance.base_commit` | 빌드 당시 `HEAD`를 기록한다. |

`candidate_id`의 직렬화는 `json.dumps(mapping, sort_keys=True, separators=(',', ':'))`다. 이 문자열의 UTF-8 바이트를 SHA-256으로 해시한다. 체크섬은 바이트 일치를 확인하며 발행자를 인증하지 않는다.

빌드는 미커밋 변경도 현재 바이트대로 포함한다. 출처는 `working-tree-candidate`이며 `release_tag`는 `null`이다. 같은 파일·기준 커밋·버전으로 빌드하면 ZIP 바이트가 같다.

## 절차

1. **현재 파일로 후보를 만든다.**

   ```sh
   python3 -B distribution/skill_package.py build \
     --output output/kp-v0.11.0/korean-protocol-0.11.0-candidate.zip
   ```

2. **후보 바이트를 검증한다.**

   ```sh
   python3 -B distribution/skill_package.py verify \
     --package output/kp-v0.11.0/korean-protocol-0.11.0-candidate.zip
   ```

3. **평가 근거로 설치 계획을 확인한다.**
   사용자가 요청한 호스트만 `--host`로 지정한다. 아래 예시는 두 호스트를 요청한 경우다.

   ```sh
   python3 -B distribution/skill_package.py plan \
     --package output/kp-v0.11.0/korean-protocol-0.11.0-candidate.zip \
     --evidence output/kp-v0.11.0/study \
     --host codex --host claude-code
   ```

4. **요청받은 설치를 실행한다.**
   실제 평가를 통과한 경우 같은 인자로 실행한다.

   ```sh
   python3 -B distribution/skill_package.py install \
     --package output/kp-v0.11.0/korean-protocol-0.11.0-candidate.zip \
     --evidence output/kp-v0.11.0/study \
     --host codex --host claude-code
   ```

### 평가 근거가 불완전할 때

`plan`과 `install`은 `evaluation.output_formats.study.validate_installation_evidence`를 호출한다. 평가 디렉터리와 전체 파일 해시를 전달한다. 후보 ID와 ZIP 해시도 전달한다.

검증기가 다시 산출한 두 값이 설치 조건이다.

- **비교 상태:** `comparison_status=complete`여야 한다.
- **품질 게이트:** `quality_gate=pass`여야 한다.

`report.json`의 통과 표시 복사만으로는 설치할 수 없다. 검증기는 입력·프로필·공통 요청·원시 출력·판정의 해시를 대조한다. 원문·KP·STE의 모델·추론 설정별 반복 조건도 대조한다.

후보 전체 파일 해시는 평가 입력과 같아야 한다. `package-binding.json`은 실제 ZIP 해시를 후보에 연결한다. 매체 산출물과 두 호스트의 독립 실행 근거도 확인한다.

대조군 누락·실행 실패·조건 불일치·근거 누락은 설치를 막는다. 평가 도구 부재나 후보 파일 변경도 설치를 막는다. [파일럿 결과와 한계](output-formats-candidate-status.md)는 정식 근거와 구분한다.

### 설치 위치를 바꿀 때

| 호스트 | 기본 설치 위치와 호출 |
| --- | --- |
| Codex | `~/.agents/skills/korean-protocol`에서 `$korean-protocol`로 호출한다. |
| Claude Code | `~/.claude/skills/korean-protocol`에서 `/korean-protocol`로 호출한다. |

`--home`은 격리 확인용 홈을 선택한다. `CLAUDE_CONFIG_DIR`이 있으면 Claude 대상에는 그 설정이 우선한다. `plan`은 대상·백업·임시 설치 파일을 만들지 않는다.

`--evidence`의 상대 경로는 현재 작업 디렉터리 기준으로 정규화한다. 실행 근거는 기록 당시 절대 실행 경로·Python 런타임을 검증한다. 근거를 다른 위치로 옮겨 재사용하는 방식은 지원하지 않는다.

### 기존 설치나 사용자 변경이 있을 때

설치기는 `INSTALLATION.json`의 모든 추적 파일을 실제 바이트와 대조한다. 수정·누락·manifest 부재가 있으면 설치를 중단한다. 추적되지 않은 추가 파일은 보존한다.

추가 파일이 새 패키지 경로와 충돌하면 중단한다. 심볼릭 링크가 있는 설치도 변경하지 않는다. 사전 검사 뒤 생긴 변경도 활성화 전에 확인한다.

### 설치 이동이 실패할 때

두 대상의 사전 검사 뒤 활성 폴더 밖에 준비본·백업을 만든다. 기본 백업은 `~/.local/state/korean-protocol/skill-backups/<transaction>/`이다. `--backup-root`도 활성 대상의 `skills/` 밖으로 지정한다.

대상·백업은 원자적 디렉터리 이동이 가능한 같은 파일시스템에 둔다. 이동이 실패하면 이전 설치를 복원하고 실패를 반환한다.

### 이전 설치로 복원할 때

설치 결과의 `transaction` 경로를 사용한다.

```sh
python3 -B distribution/skill_package.py rollback \
  --transaction /absolute/path/to/skill-backups/TRANSACTION_ID
```

복원은 두 대상과 백업의 파일 해시를 먼저 대조한다. 설치 후 파일을 수정·추가했으면 중단하고 해당 경로를 보고한다. 새 설치였으면 활성 폴더를 백업 트랜잭션 안으로 옮긴다.

기존 설치였으면 이전 폴더를 되돌린다. 동시 설치·프로세스 강제 종료 뒤 자동 복구는 보장하지 않는다.

## 검증

임시 디렉터리의 패키지·설치 동작을 검사한다.

```sh
python3 -m pytest -q tests/test_skill_package.py
```

검사는 ZIP 결정성과 자산 포함을 확인한다. 변조·품질 차단과 사용자 변경 보존도 확인한다. 두 호스트 설치·부분 실패 복구·복원도 임시 디렉터리에서 실행한다.

이 검사는 실제 모델 비교나 사용자 범위 설치를 실행하지 않는다. 설치 성공 뒤에도 새 대화의 발견·호출·출력 품질을 따로 확인한다.

## 참고

- **호스트 설정:** Codex는 원본 `SKILL.md`와 `allow_implicit_invocation: false`를 유지한다. Claude는 `disable-model-invocation: true`와 `user-invocable: true`를 추가한다. 두 호스트의 규약 본문은 같다.
- **설치 기록:** 전체 파일·후보·ZIP·기준 커밋 해시를 보존한다.
- **YAML 검사:** 두 칸 들여쓰기 매핑과 한 줄 값만 해석한다. 실제 `policy.allow_implicit_invocation`은 불리언 `false`여야 한다. `SKILL.md`에는 정확한 이름·비어 있지 않은 문자열 설명이 필요하다.
- **YAML 거부:** 중복 키·별칭·태그·병합·블록 값·모호한 불리언을 거부한다.
- **기존 0.7:** 서명 배포·자동 갱신기는 별도 경로를 사용한다.
