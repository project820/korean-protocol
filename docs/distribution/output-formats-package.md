# 출력 형식 후보 패키지를 검증한 뒤 설치한다

`distribution/skill_package.py`는 호출형 `korean-protocol` 스킬의 로컬 후보 ZIP을 만든다. 기본 버전은 `0.10.0-candidate`다. 후보 파일의 바이트를 고정하며 공개 릴리스나 발행자 서명을 주장하지 않는다. 기존 0.7 ZIP·서명 콘텐츠·자동 갱신기는 이 경로를 사용하지 않는다.

## 현재 파일로 후보를 만든다

저장소 루트에서 다음 명령을 실행한다.

```sh
python3 -B distribution/skill_package.py build \
  --output output/kp-output-formats-20261020/korean-protocol-0.10.0-candidate.zip
python3 -B distribution/skill_package.py verify \
  --package output/kp-output-formats-20261020/korean-protocol-0.10.0-candidate.zip
```

빌드는 커밋하지 않은 변경도 현재 바이트대로 포함한다. `MANIFEST.json`은 기준 `HEAD`를 `provenance.base_commit`에 기록하고 `working-tree-candidate`로 표시한다. 기준 커밋이 후보 파일과 같다고 주장하지 않는다. 동일한 파일·기준 커밋·버전을 다시 빌드하면 ZIP 바이트가 같다.

패키지는 `skills/korean-protocol/`의 전체 파일과 다음 파일을 포함한다.

| 원본 경로가 정해진다. | 설치 경로가 정해진다. |
| --- | --- |
| `skills/korean-protocol/**`를 포함한다. | 접두사를 제거하고 같은 하위 경로를 유지한다. |
| `specification/rules.json`을 포함한다. | 같은 경로를 유지한다. |
| `lexicon/core.json`을 포함한다. | 같은 경로를 유지한다. |
| `lexicon/domains/software.json`을 포함한다. | 같은 경로를 유지한다. |
| `LICENSE`와 `NOTICE.md`를 포함한다. | 같은 파일명을 유지한다. |

새 참고 파일과 HTML·애니메이션 자산도 스킬 하위에 있으면 포함된다. `scripts/check_html.py` 같은 보조 스크립트도 같은 하위 경로와 바이트로 포함된다. ZIP은 파일 권한을 `0644`로 고정하므로 Python 보조 스크립트는 `python3`로 실행한다. 패키지 빌드·검증은 포함된 스크립트를 실행하지 않는다.

평가 디렉터리·STE 프로필·원시 녹취·비공개 자료는 패키지 입력 경로가 아니다. 스킬 아래에서도 `evaluation`, `ste`, `raw`, `private`, 숨김 경로와 심볼릭 링크를 발견하면 빌드가 중단된다. 이름만으로 민감 자료의 내용을 판별할 수 없으므로 스킬 디렉터리에 넣는 파일의 범위는 검토해야 한다.

`source_hashes`는 저장소 상대 경로별 SHA-256을 보존한다. `files`는 설치 상대 경로별 SHA-256을 보존한다. `candidate_id`는 `source_hashes`를 `json.dumps(mapping, sort_keys=True, separators=(',', ':'))`로 직렬화한 UTF-8 바이트의 SHA-256이다. ZIP 전체의 SHA-256은 빌드·검증 명령의 `package_sha256`에 나온다. 체크섬은 바이트의 일치를 확인하며 발행자를 인증하지 않는다.

## 독립 평가가 통과해야 설치할 수 있다

`plan`과 `install`은 `evaluation.output_formats.study.validate_installation_evidence`를 호출한다. 검증기는 평가 디렉터리, 전체 `source_hashes`, `candidate_id`, ZIP 전체 SHA-256을 받는다. `report.json`의 통과 표시만 복사해서는 설치할 수 없다.

설치 도구는 `--evidence`의 상대 경로를 현재 작업 디렉터리 기준의 절대 경로로 정규화한 뒤 검증기에 전달한다. 실행 근거는 기록 당시의 절대 실행 경로와 Python 런타임을 검증하므로 같은 파일을 다른 위치로 옮겨 재사용하는 방식은 지원하지 않는다. 경로 정규화는 실행 근거의 이동을 허용하지 않는다.

검증기는 고정 입력·프로필·공통 요청·원시 출력·판정의 해시와 원문·KP·STE 조건을 다시 대조한다. 모델·추론 설정별 반복 수와 양쪽 출력이 맞아야 한다. 후보 전체 파일의 해시도 평가 입력과 같아야 한다. `package-binding.json`은 실제 ZIP 해시를 후보에 연결한다. 정적·상호작용·애니메이션 산출물의 독립 실행 근거와 Codex·Claude 두 호스트의 근거도 별도로 확인한다.

검증기가 `comparison_status=complete`, `quality_gate=pass`를 다시 산출한 경우에만 설치 계획이 나온다. 대조군 누락·실행 실패·조건 불일치·파일 변경·독립 근거 누락은 설치를 막는다. 평가 도구가 없을 때도 설치를 막는다. 평가 기록은 후보 ZIP에 포함하지 않고 저장소의 평가 도구로 확인한다.

## 두 호스트의 계획을 먼저 확인한다

사용자가 요청한 호스트만 `--host`로 지정한다. 다음 명령은 두 호스트를 요청한 경우의 계획 조회다. 평가 디렉터리에는 실제 검증 근거가 있어야 한다.

```sh
python3 -B distribution/skill_package.py plan \
  --package output/kp-output-formats-20261020/korean-protocol-0.10.0-candidate.zip \
  --evidence output/kp-output-formats-20261020/study \
  --host codex --host claude-code
```

Codex 기본 대상은 `~/.agents/skills/korean-protocol`이다. Claude Code 기본 대상은 `~/.claude/skills/korean-protocol`이며 `CLAUDE_CONFIG_DIR`이 있으면 그 아래 `skills/korean-protocol`을 쓴다. `--home`은 격리된 확인용 홈을 선택한다. 이 옵션을 쓰더라도 명시된 `CLAUDE_CONFIG_DIR`이 Claude 대상에 우선한다. `plan`은 대상·백업·임시 설치 파일을 만들지 않는다.

기존 설치가 있으면 `INSTALLATION.json`의 **모든 추적 파일**을 실제 바이트와 대조한다. 수정·누락된 파일이나 manifest 없는 폴더가 있으면 덮어쓰지 않고 중단한다. 추적되지 않은 추가 파일은 보존한다. 추가 파일이 새 패키지 경로와 충돌하면 중단한다. 심볼릭 링크가 있는 설치도 변경하지 않는다.

## 통과한 계획의 설치와 복원을 실행한다

사용자가 설치를 요청했고 실제 평가가 통과했으면 같은 인자로 `install`을 실행한다.

```sh
python3 -B distribution/skill_package.py install \
  --package output/kp-output-formats-20261020/korean-protocol-0.10.0-candidate.zip \
  --evidence output/kp-output-formats-20261020/study \
  --host codex --host claude-code
```

설치기는 두 대상의 사전 검사를 모두 마친 뒤 활성 스킬 폴더 밖에 준비본과 백업을 만든다. 기본 백업 경로는 `~/.local/state/korean-protocol/skill-backups/<transaction>/`이다. `--backup-root`로 지정할 때도 활성 대상의 `skills/` 아래를 사용하지 않는다. 대상과 백업은 원자적 디렉터리 이동이 가능한 같은 파일시스템에 둔다. 이동이 실패하면 이전 설치를 복원하고 실패를 반환한다.

Codex는 원본 `SKILL.md` 바이트와 `allow_implicit_invocation: false`를 유지한다. Claude Code는 YAML 앞부분에 `disable-model-invocation: true`와 `user-invocable: true`만 추가한다. 두 호스트의 규약 본문은 같다. 설치 기록은 전체 파일 해시·후보·ZIP·기준 커밋을 보존한다. 설치 성공은 새 대화의 발견·로딩·출력 품질을 대신 입증하지 않는다.

패키지 검증은 YAML을 두 칸 들여쓰기의 매핑과 한 줄 값으로 제한해 파싱한다. 실제 `policy.allow_implicit_invocation` 값이 불리언 `false`여야 하며 다른 항목의 같은 이름은 대신하지 못한다. 중복 키·별칭·태그·병합·블록 값·모호한 불리언 표기는 거부한다. `SKILL.md`에는 정확한 이름과 비어 있지 않은 문자열 설명이 있어야 한다.

설치 결과의 `transaction` 경로로 이전 설치를 복원한다.

```sh
python3 -B distribution/skill_package.py rollback \
  --transaction /absolute/path/to/skill-backups/TRANSACTION_ID
```

복원은 두 대상과 백업의 파일 해시를 먼저 대조한다. 설치 후 사용자가 파일을 바꾸거나 추가했으면 복원을 중단하고 해당 경로를 보고한다. 새 설치였으면 활성 폴더를 백업 트랜잭션 안으로 옮긴다. 기존 설치였으면 이전 폴더를 되돌린다. 이 도구는 동시에 실행한 설치나 프로세스 강제 종료 뒤의 자동 복구를 보장하지 않는다.

## 임시 디렉터리에서 설치 동작을 검증한다

```sh
python3 -B -m unittest discover -s tests -p test_skill_package.py -v
```

검사는 임시 디렉터리에서 결정적 ZIP, 자산 포함, 변조 거부, 품질 차단, 두 호스트 설치, 사용자 변경 보존, 부분 실패 복구와 복원을 실행한다. 이 검사는 실제 모델 비교나 사용자 범위 설치를 실행하지 않는다.
