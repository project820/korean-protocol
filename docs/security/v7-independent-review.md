# V7 보안·배포 독립 검토

엔진 0.2.0의 상한 조정을 포함한 V7 변경에서 보안 회귀를 확인하지 못했다. 이전 P3 압축 파일 링크 결함은 해결했다. `docs/spec/control-expression.md:5`와 `docs/spec/korean-rules.md:41`은 채택 기록의 저장소 URL을 사용하며 배포 시험도 통과했다. 이 결과는 압축 파일 안에서 찾을 수 없던 상대 경로를 제거했음을 확인하며, 해당 원격 문서의 공개 완료를 입증하지는 않는다.

2026-10-15에 기준 커밋 `52008bdd1eabf0d5e3d359898bedcaebaf057e0a` 이후의 미커밋 변경을 검토했다. 갱신 임시 파일 정리, 런타임 활성화·캐시·신뢰 경로, 관리 도구·실행기 버전, 오프라인 배포 허용 목록, 발행 워크플로, 컴파일러의 배포문·원문 연결, TEST 서명 이관 도구를 확인했다. 운영 코드는 수정하지 않았으며 설치·서명 시험은 임시 환경에서만 실행했다.

## 보안 검토 결과

- `runtime/kproto.py:1248–1272`는 갱신 시도마다 독점 임시 디렉터리를 만든다. 정리 대상은 해당 디렉터리이며 과거 다운로드·서명된 릴리스 캐시·백업은 보존한다. 로컬 Python의 `shutil.rmtree.avoids_symlink_attacks` 값은 `True`였고, 시험에서도 임시 디렉터리 안의 링크가 외부 대상을 삭제하지 않았다.
- 엔진 0.2.0은 검토한 규칙의 뜻을 보존하기 위해 프로필 상한을 28→30 KiB, 관리 블록 상한을 30→32 KiB로 늘렸다. 허용 경로 7개, 파일별·전체 상한, 서명 namespace·principal, 고정 로컬 키, 최대 릴리스 순번 검사, 명시적 캐시 롤백 요건은 유지했다. `host_budget`은 기본값이 32 KiB인 Codex 프로젝트 지침 체인의 설정 상한을 별도로 적용하며, 설치기는 사용자 설정을 늘리지 않는다. 관리 도구의 버전 변경은 서명 설치의 신뢰 판정을 바꾸지 않는다.
- `make_manifest`는 최소 엔진 버전을 0.2.0으로 기록한다. 기준 소스의 실제 엔진 0.1.0은 콘텐츠를 받기 전에 이를 거부하고 설치 대상과 상태를 보존했다. 관리 코드를 갱신하려면 사용자가 현재 저장소의 설치기를 명시적으로 실행해야 하며, 콘텐츠 갱신은 실행 코드를 교체하지 않는다. 규약 적용을 OFF로 설정해도 새 서명 콘텐츠는 갱신하지 않은 엔진 0.1.0과 호환되지 않는다.
- `validation/compile.py:27–40`은 연결된 요구사항·조건·예외 중 하나라도 바뀌면 축약 배포문을 거부한다. 이 검사는 신뢰한 작성 원본과의 일관성을 확인하며, 의미가 같다는 독립 증명은 제공하지 않는다. `distribution/release.py:76–122`는 원본을 확보해 다시 컴파일하고 발행 준비 전에 컴파일 결과의 바이트 일치를 요구한다.
- 발행 워크플로는 기본 버전만 바꿨다. 서명 비밀의 사용 범위, 고정된 액션, 분리된 공개 권한, 발행 이력 검사는 유지했다. 새 오프라인 이관 시험은 임시 TEST 서명자를 사용하며 정식 공개 발행이나 구버전 실행 코드의 이관을 입증하지 않는다고 명시한다.

## 검증 기록

최초 실행은 다음 명령으로 304개 시험을 47.131초 동안 수행했다.

```sh
python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_release tests.test_actions_release tests.test_history_store tests.test_scheduler tests.test_launcher tests.test_distribution tests.test_candidate_upgrade_smoke tests.test_v7_adoption tests.test_controlled_language
```

303개가 통과했으며 위에서 해결한 압축 파일 링크 검사만 실패했다. ZIP 이름 중복 경고는 잘못된 압축 파일의 거부를 확인하는 시험에서 발생했다.

엔진 변경과 링크 수정 후에는 다음 명령으로 **224개 시험을 모두 통과했다**. 실행 시간은 44.876초였다.

```sh
python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_distribution tests.test_candidate_upgrade_smoke tests.test_v7_adoption tests.test_release
```

경계값 시험은 28 KiB + 1 byte와 정확히 30 KiB인 프로필을 잘림 없이 설치하고, 30 KiB + 1 byte는 거부했다. 상위 지침 때문에 Codex 프로젝트 체인의 잔여 공간이 부족하면 큰 프로필을 거부했다. 거부 후에도 하위·상위 지침 바이트와 `config.toml`은 보존했다.

별도 임시 시험은 기준 커밋 `52008bdd1eabf0d5e3d359898bedcaebaf057e0a`의 런타임 원본을 그대로 불러와 TEST 서명 0.3.0 시험본을 설치했다. 이어 실제 V7 후보 파일 7개의 TEST 서명 manifest를 제공했다. 구버전 런타임은 manifest와 서명만 받은 뒤 `CompatibilityError`를 냈으며, 0.3.0의 설치 대상·상태 파일은 바이트 단위로 유지했다. 이 시험은 현재 런타임의 버전 상수만 바꾸는 방식으로 대체하지 않았다.

`manual_offline_candidate_migration.run_migration(Path.cwd())`도 같은 커밋의 정확한 기준 파일 7개로 통과했다. 임시 Codex·Claude Code 설치는 모두 다음 동작을 확인했다.

- OFF·높임말 설정을 보존했다.
- 캐시의 후보 파일 7개가 원본과 일치했다.
- ON 전환 시 후보 프로필 전체를 적용했다.
- 캐시의 두 버전으로 각각 롤백했다.
- 제거 후 사용자 원문 바이트를 복원하고 임시 자료를 삭제했다.

과거 버전 TLS 이관 도구는 구버전 엔진의 호환성 거부를 기대하도록 병행 수정된 뒤 소스를 검토했다. 이 독립 후속 검토에서는 해당 TLS 도구를 실행하지 않았다.

추가 임시 시험은 다운로드 루트의 심볼릭 링크를 통신 전에 거부하고 설치 대상·상태 바이트와 외부 디렉터리를 보존했다. 연결된 원본 필드 `requirement`·`conditions`·`exceptions`를 각각 바꾸자 축약 배포문 검증이 모두 실패했다. `git diff --check`도 통과했다.

최종 프로필 크기는 coding-agent 30,137 bytes, chat 30,107 bytes, work-document 30,116 bytes였으며 모두 새 상한 30 KiB 이내였다. 검토한 파일의 SHA-256은 다음과 같다.

| 검토 파일 | SHA-256 |
| --- | --- |
| `runtime/kproto.py` | `fc564ee78ee483961d099e4b50453817aa16e2e3b7924244d8230360d74bb055` |
| `validation/compile.py` | `ab378889030dcd007c226ce76ff44a340302d0bd23d472560486a44a261dc7b1` |

## 검토 한계

이 검토에서는 운영 키 서명, 공개 발행, 실제 스케줄러 등록, 실제 모델 호출을 실행하지 않았다. 축약 규칙의 의미 동등성은 별도 언어 검토의 범위다. 강제 종료 후 임시 디렉터리 정리는 이번 수정이 보장하지 않는다.

침해된 로컬 계정이나 신뢰한 발행자는 검토한 신뢰 경계 밖이다. 통합 작업과 작업 트리를 공유했으므로 이후 변경에는 해당 변경의 검증이 필요하다.
