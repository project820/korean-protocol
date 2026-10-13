# 현행 발행물의 실제 서명과 HTTPS 확인을 검증했다

GitHub Actions 실행 38353292401은 커밋 a16776de0df8436e0d6fdf38e886dc2b07ab5034에서 실제 GitHub Secret을 사용해 서명했다. sign 작업과 90개 검사가 통과했고 publish·receipt·archive는 건너뛰었다. 저장소 공개나 Pages 설정은 바꾸지 않았다. [실제 실행](https://github.com/project820/korean-protocol/actions/runs/38353292401)과 [설치 검증 기록](current-actions-bootstrap.json)을 함께 확인할 수 있다.

내려받은 artifact 11791059945의 공개키 지문은 `SHA256:O9IrN/e4GB8ayF+UnwseuZNK1jgDyWAiDQcApMC/OAc`다. manifest SHA-256은 `7bf0a7ca0a9143401086ceb7903ec54236d5664000d55f4177e7a3a1937e8d0f`이며, 서명을 검증한 일곱 콘텐츠 파일이 현재 원본과 일치한다. 버전은 0.2.0, 순번은 1이다. 이전 비공개 서명 시험과 같은 첫 발행 순번을 사용하는 검증용 실행이며 이미 공개한 릴리스를 교체한 것이 아니다.

manifest와 서명은 current-actions-artifact에 보존했다. 실제 페이로드는 기록한 원본 커밋에서 manifest의 경로·해시에 맞춰 재구성할 수 있다. 보존은 GitHub 실행 artifact의 만료 뒤에도 서명 증거를 대조하기 위한 것이며, 만료된 manifest를 신규 설치에 수락하도록 허용하는 변경이 아니다.

## 임시 호스트에서 실제 서명을 검증했다

Xcode Python 3.9.6의 비대화형 설치기로 Codex·Claude Code의 별도 임시 환경에 설치했다. 두 호스트 모두 서명 확인, 정확한 프로필 설치, 재설치 후 바이트 유지, 지속 관리 도구의 상태 확인, 기존 사용자 지침 보존, 제거 후 원문 복원이 통과했다. 실제 사용자 전역 설정은 변경하지 않았다.

## 실제 HTTPS와 시험용 업그레이드를 구분했다

[Codex 기록](current-actions-https-codex.json)과 [Claude Code 기록](current-actions-https-claude.json)은 Python 3.11의 기본 인증서 검증과 임시 CA·제한된 loopback CONNECT 프록시를 사용했다. 실제 게시자의 manifest·서명·콘텐츠를 그대로 복사해 제공하며 게시자 개인키를 읽거나 다시 서명하지 않았다. 공급한 artifact 원본은 변경하지 않았다.

각 호스트의 16단계가 통과했다. 수동 갱신과 시작 wrapper가 각각 manifest·서명·일곱 콘텐츠를 합친 9개 파일을 HTTPS로 받아 검증했다. 잘못된 CA 두 경우는 HTTP GET에 도달하지 않았으며, 잘못된 릴리스 서명은 활성 프로필·캐시·설치 상태를 바꾸지 않았다. 서버를 멈춘 뒤 갱신은 네트워크 오류를 반환했고 기존 캐시와 프로필은 그대로 남았다. 자동 갱신을 끈 오프라인 wrapper도 호스트 명령을 실행했다.

실제 발행물 결과는 0.2.0·순번 1의 **같은 버전 확인**이다. 실제 게시자 키로 다음 버전을 발행해 업그레이드한 결과로 확대하지 않는다. 별도 [시험용 키의 회귀 실행](current-fixture-https.json)은 기존 0.2.0→0.2.1·순번 2 업그레이드를 16단계로 확인했다. 서로 다른 두 증거를 합쳐 실제 공개 업그레이드를 완료했다고 표시하지 않는다.

다음 명령은 유효기간 안의 내려받은 정적 배포물을 사용한다. Python 3.11은 이미 설치된 실행기를 사용했고 전역 CA·프록시를 바꾸지 않았다.

```sh
python3.11 tests/manual_https_smoke.py --runtime-root . --via-local-proxy --host codex --signed-static /ABS/SEALED_STATIC --output /ABS/codex-result.json
python3.11 tests/manual_https_smoke.py --runtime-root . --via-local-proxy --host claude-code --signed-static /ABS/SEALED_STATIC --output /ABS/claude-result.json
```

이 실행은 공개 endpoint, 로그인 세션 재시작, 실제 절전 복귀, 모델의 출력 준수를 검증하지 않는다. macOS Python 3.9의 임시 CA 로딩 제한에 관한 기존 기록도 유지한다. Python 3.11의 TLS 성공을 Python 3.9의 동일 임시 CA 시험 성공으로 표시하지 않는다.

## 시험 도구를 검토했다

새 옵션은 공개키 상대경로를 절대경로로 정규화하고 실제 다운로드 순서를 인증된 manifest의 files 배열에서 얻는다. 독립 보안 검토에서 발견한 두 가정 오류를 수정한 뒤 두 실제 발행물 시험과 기존 시험용 업그레이드를 모두 재실행했다. 세 결과는 최종 스크립트·런타임 해시와 일치한다.

새 검사 6개와 발행 도구 검사 13개가 통과했다. 단위 검사는 정적 artifact 로더와 두 회귀를 다루며, HTTPS·wrapper·오프라인 동작은 별도 실제 실행 기록으로 증명한다. 독립 검토자는 코드를 읽고 최종 증거를 대조했으며 네트워크 시험을 별도로 재실행하지 않았다. [검토·시험 요약](current-actions-review.json)에 그 범위를 기록했다.
