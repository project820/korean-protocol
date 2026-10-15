# 0.7.0 설치·갱신을 검증한다

현재 checkout의 코드·패키지·임시 설치를 각각 검사한다. 규약 0.7.0, 엔진 0.2.0, schema 1.0을 구분하며 이전 실행의 테스트 수를 현재 결과로 보고하지 않는다.

## 현재 원본의 검사를 실행한다

```sh
python3 -B -m validation.check --root . --json
python3 -B -m unittest tests.test_runtime tests.test_agent_install tests.test_scheduler tests.test_distribution tests.test_release tests.test_actions_release tests.test_history_store tests.test_product_release
```

전체 검사가 필요하면 `python3 -B -m unittest discover -s tests -p 'test_*.py'`를 실행한다. CI는 Ubuntu 24.04·macOS 15의 Python 3.11에서 같은 데이터 검사와 전체 테스트를 실행하도록 구성했다. 실제 실행의 성공 여부는 해당 CI 결과로 확인하며 구성만으로 통과했다고 보고하지 않는다.

## 임시 환경에서 실패 경로를 확인한다

실제 사용자 홈·지침·Keychain·예약 작업을 바꾸지 않는다. 임시 홈·상태·프로젝트·시험용 키를 사용하며 실제 공개 다운로드에는 사용자 자격 정보를 보내지 않는다.

| 경계 | 필요한 확인 |
| --- | --- |
| 설치와 재설치 | 중복 관리 블록을 만들지 않고 사용자 본문·규약·높임말을 보존한다. |
| 자동 갱신 재설정 | 서명 재설치의 명시 옵션을 적용하며 생략하면 OFF가 되는 동작을 확인한다. |
| 경로와 소유권 | 다른 홈·상태·symlink·hardlink·미완료 marker·관리 블록 수정을 거부한다. |
| 서명과 콘텐츠 | 실제 시험 키의 양성·변조·다른 키·namespace·경로·크기·해시 오류를 검사한다. |
| 시간·순번·호환 | 만료·미래 발행·낮은 순번·같은 순번 다른 hash·구버전 엔진 수락을 거부한다. |
| 통신 | TLS·동일 origin·redirect·시간·크기 제한과 인증값 비노출을 검사한다. |
| 중단과 경쟁 | 대상 교체·상태 commit 사이 중단과 pin·OFF 변경에서 복구·사용자 본문을 보존한다. |
| 예산 | 프로필 30,720바이트·관리 블록 32,768바이트와 실제 Codex 프로젝트 잔여 예산을 별도로 검사한다. |
| 설정과 제거 | OFF·ON·높임말·롤백·pin·제거 뒤의 캐시·대상·본문을 대조한다. |
| 예약 | 생성과 실제 등록을 구분하고 소유 작업만 등록·확인·해제한다. |

자동 diff·런타임 `check` 명령은 제공하지 않는다. 콘텐츠 검사와 상태 명령을 실제 지원하는 CLI로 실행하며 미구현 설계를 검증한 것으로 기록하지 않는다.

## 공개 0.7.0과 로컬 빌드를 분리한다

[공개 manifest](https://project820.github.io/korean-protocol/stable/release.json)는 게시자 서명을 먼저 검증한 뒤 일곱 콘텐츠의 해시·크기를 대조한다. 서명 콘텐츠의 원본은 `67f537e`다.

[v0.7.0 사용자 패키지](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)는 `7e01d53`의 고정 ZIP·채팅 파일·체크섬이다. 익명으로 받은 세 파일과 기록된 해시를 대조하며 현재 main으로 새로 만든 ZIP이 공개 파일과 같다고 가정하지 않는다. ZIP 내부 파일 체크섬과 외부 ZIP·채팅 파일 체크섬의 범위도 구분한다.

로컬 패키지에서는 포함 파일·CRC·체크섬·Markdown 상대경로·앵커·생성물 일치를 확인한다. 원래 복제본을 옮긴 뒤 지속 관리 도구로 상태·제거가 되는지도 임시 환경에서 확인한다.

## 호스트 로딩과 언어 효과를 따로 판정한다

Codex·Claude Code는 임시 설정으로 새 세션의 지침 발견을 확인한다. 설치 파일과 캐시의 검증만으로 모델이 모든 규칙·사전을 읽었다고 표시하지 않는다. ChatGPT는 첨부 파일과 프로젝트 지침의 적용 범위를 확인하며 로컬 updater가 업로드한 복사본을 바꾼다고 설명하지 않는다.

실제 OS·호스트·모델·프로필·원본 SHA·명령·종료 코드와 미확인 범위를 기록한다. 공개 0.7.0의 기존 증거는 [발행 기록](public-0.7.0-verification.md), 언어 효과는 [V7 검증 기록](../status/v7-verification.md)을 따른다. 실제 독자 시험·다른 모델 일반화·macOS 물리적 절전 복귀는 별도 검증이다.
