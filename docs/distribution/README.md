# 설치와 배포 계약 v1

이 문서는 Korean Protocol을 한 번 설치한 뒤 로컬에서 계속 사용하는 배포 계약을 정의한다. POSIX 로컬 설치·서명 검증·콘텐츠 updater·시작 wrapper와 macOS launchd 파일 생성은 구현했고, 실제 발행 서비스와 사용자 예약 작업은 연결하지 않았다. [현재 구현과 실행법](implementation-status.md)은 실행 가능한 명령과 남은 설계를 구분한다. 규약은 LLM 응답의 표현을 안내하며 모든 응답의 준수를 보장하지 않는다.

## 적용 범위

규약 파일, 지시 프로필, 통제 어휘 데이터는 네트워크·API·유료 구독 없이 보관하고 읽으며 검사한다. 호스트 LLM 자체의 실행 비용과 네트워크 요구는 해당 호스트가 결정한다. 업데이트 실패나 업데이트 해제는 이미 설치한 규약의 사용을 막지 않는다.

배포물은 UTF-8 Markdown과 JSON만 포함한다. 설치기는 배포물의 스크립트, hooks, 실행 파일, 라이브러리, 셸 명령을 실행하지 않는다. 런타임 코드는 사용자가 별도로 검토하고 교체하며, 콘텐츠 자동 업데이트가 런타임을 갱신하지 않는다. 서명된 콘텐츠에도 임의의 지시가 들어갈 수 있으므로 콘텐츠 릴리스는 발행 전 검토와 의미 보존 회귀 검사를 통과해야 한다.

`profiles`는 모델이 읽는 지침이고 `check`는 정해진 항목을 검사하는 실행 경로이다. 모델의 의미 이해와 검사기의 표면 탐지는 다르다. 검사기가 통과시킨 글도 사실·양태·책임을 바꿀 수 있으며, 프로필을 읽은 모델도 규칙을 어길 수 있다. 응답 공개를 검사 결과로 차단하려면 해당 호스트나 자체 앱이 출력 경로에 검사기를 연결해야 한다.

## 저장 구조

사용자는 설치기의 위치를 정한다. 런타임은 Python 3.9 이상과 표준 라이브러리를 사용하고, 서명 검증 때만 확인된 OpenSSH 검증기를 호출한다. PATH나 셸 초기화 파일을 자동 수정하지 않는다.

| 대상 | 기본 경로를 다음처럼 정한다. |
| --- | --- |
| macOS 사용자 데이터 | `~/Library/Application Support/KoreanProtocol/`에 저장한다. |
| Linux 사용자 데이터 | `${XDG_DATA_HOME:-~/.local/share}/korean-protocol/`에 저장한다. |
| Windows 사용자 데이터 | `%LOCALAPPDATA%\KoreanProtocol\`에 저장한다. |
| 프로젝트 상태 | `--state-dir /ABS/PROJECT/.korean-protocol`을 명시해야 그 경로에 저장한다. `--scope project`만 지정하면 사용자 기본 상태 경로를 사용한다. |
| 사용자 지정 상태 | `--state-dir ABSOLUTE_PATH`가 기본 데이터 경로를 대체한다. |

현재 상태 디렉터리는 `config.json`, `state.json`, `trust/allowed_signers`, `trust/public_key`, `releases/<version>-<manifest-sha256>/`, `downloads/<id>/`, `backups/<id>/original`, `journal.json`, `write.lock`을 갖는다. `state.json`은 마지막으로 commit한 활성 릴리스·cache id·대상·관리 블록 hash·profile/managed bytes·host context·pin·최고 수락 sequence를 기록한다. 마지막 정상본은 commit한 state의 cache id로 표현하며 별도 last-good pointer는 없다. 공개키와 콘텐츠 캐시는 자격 증명을 포함하지 않는다. JSON은 중복 키와 비정상 수치, BOM, 잘못된 UTF-8·과도한 parser 중첩을 거부한다.

POSIX 상태·trust 디렉터리는 사용자 소유의 `0700`, trust/config/state는 `0600`으로 만들고 그룹·다른 사용자 쓰기 권한을 거부한다. 기존 대상 파일은 최대 4MiB로 보호하며 이는 Codex 모델/프로젝트 상한이 아니라 설치기의 파일 읽기·복구 상한이다. journal은 원문 base64 팽창과 상태 metadata를 고려한 별도 제한으로 읽어 이 경계의 복구를 지원한다. Windows는 사용자 ACL과 reparse point 상태를 확인할 구현이 필요하다. 그 검사를 구현하지 않은 플랫폼에는 안전한 원격 갱신 지원을 표시하지 않는다. 캐시는 사용자 신뢰 경계 안에 있으며 매 활성화 때 manifest·콘텐츠 hash를 다시 확인한다.

사용자 설치와 프로젝트 설치는 서로 다른 상태 루트를 갖는다. 같은 호스트의 동일 파일에 두 설치가 각각 블록을 추가하지 못한다. 상태에 소유자가 있는 대상은 그 상태 루트를 명시해서만 갱신한다. 상태가 사라진 대상은 자동으로 재소유하지 않고 복구용 차이를 제공한다.

## 설치 대상과 기존 지침

[호스트 지원표](host-support.md)는 실제 호스트 발견 방식과 적용 공백을 정의한다. 설치기는 원격 manifest가 지정한 경로에 쓰지 않는다. 사용자가 고른 `--host`, `--scope`, `--project-root`, `--codex-home`과 설치기 내부 adapter가 대상 경로를 결정한다. 프로젝트 루트와 상태 루트는 절대 경로로 정규화한다. 환경 변수는 경로 값으로만 사용하고 셸 구문으로 해석하지 않는다.

파일을 공유하는 Codex/Gemini adapter는 다음 관리 블록을 삽입한다. 본문에는 호스트가 읽을 실행 프로필의 규칙 requirement와 중요한 조건·예외를 넣으며, 외부 URL 다운로드나 도구 실행을 지시하지 않는다. Markdown 파일 참조만으로 반드시 읽힌다고 간주하지 않는다.

```markdown
<!-- korean-protocol:begin id=kproto -->
Korean Protocol <version>의 한국어 표현 지침을 적용한다.
<검증된 짧은 프로필 본문을 넣는다.>
<!-- korean-protocol:end id=kproto -->
```

관리 블록 외부의 bytes와 줄바꿈은 그대로 보존한다. 현재 backup은 원본 bytes를 저장하고 journal은 원본 bytes·새 전체 hash·이전/후보 state를 기록한다. 기존 대상의 권한은 atomic 교체 시 유지하며 최초 존재 여부는 state에 기록한다. 별도 원본 권한·backup hash metadata는 장래 보강 대상이다. 사전 읽기 bytes와 교체 직전 bytes가 다르면 쓰기를 중단한다. 관리 블록이 둘 이상이거나 마커가 손상되면 재삽입하지 않는다. 같은 버전·같은 hash의 중복 설치는 성공으로 끝나고 변경하지 않는다.

관리 블록의 hash가 설치기 기록과 다르면 사용자가 수정한 것으로 처리한다. 현재 구현은 대상 파일과 활성 상태를 유지하고 exit 7로 끝난다. 후보 cache와 backup을 비교하여 사용자가 충돌을 정리해야 한다. 장래 `install --adopt-managed-edit`와 diff 출력은 검토한 블록만 재소유하도록 설계하되 현재 CLI에는 제공하지 않는다. CLI는 전체 파일을 덮어쓰는 `--force`를 제공하지 않는다.

Claude/ Cursor의 전용 규칙 파일을 사용할 때에는 파일 전체를 관리한다. 기존 같은 이름의 파일이 있으면 다른 이름을 임의 생성하지 않고 충돌을 보고한다. 외부 링크 승인을 피하려고 호스트 파일을 로컬 실제 파일로 렌더링한다. 설치기와 업데이트기는 symlink, junction/reparse point, hardlink 대상에 쓰지 않는다.

호스트가 읽는 우선순위를 설치기가 바꾸지 않는다. 프로필은 표현 범위에만 적용하며 사용자 요청, 호스트 상위 지침, 프로젝트의 사실·용어·승인 정책과 충돌하면 그 지침을 유지한다. 전역 규약과 프로젝트 규약이 모두 있으면 프로젝트가 버전을 pin할 수 있으나 실제 모델 지침 우선순위는 호스트를 따른다.

## 첫 설치의 신뢰

첫 설치는 사용자가 검토한 로컬 checkout 또는 내려받아 확인한 배포물을 입력으로 받는다. 원격 코드를 즉시 실행하는 인터넷 설치 명령을 제공하지 않는다. `install --bundle LOCAL_DIR --trust-key LOCAL_PUBLIC_KEY --expected-fingerprint SHA256:...`는 공개키 지문이 일치하고 서명이 유효한 배포물만 수락한다. 같은 서버에서 받은 공개키와 hash만 비교하면 그 서버의 변조를 검출하지 못하므로 발행자 인증으로 설명하지 않는다.

발행 공개키는 사용자가 별도로 확인한 채널, 검토한 저장소 commit 또는 조직 관리 정책으로 전달한다. v1에서는 공개키를 remote 콘텐츠로 자동 교체하지 않는다. 키 교체·폐기는 별도 검토와 로컬 trust 설정 교체가 필요하다. 이 제한 때문에 키가 바뀌면 자동 업데이트가 멈출 수 있으며 기존 규약은 계속 작동한다. 재시도만으로 키 변경을 승인하지 않는다.

서명이 없는 개인 checkout은 `install --bundle LOCAL_DIR --local-snapshot --version 0.2.0`으로 설치한다. 이 입력은 release manifest 없이 고정 일곱 콘텐츠 파일을 검증하고 자체 hash metadata를 생성한다. 이 옵션은 로컬 파일을 사용자가 선택했다는 뜻이며 발행자 인증을 뜻하지 않는다. 상태에 `trust=local-snapshot`을 기록하고 원격 자동 업데이트를 거부한다. 서명 없는 원격 다운로드를 checksum만 확인하여 자동 적용하는 모드는 제공하지 않는다.

## manifest와 서명

[release.schema.json](../../schemas/release.schema.json)은 릴리스의 구조를 정의한다. 파일 이름은 설치기에도 고정 allowlist로 들어가야 하며 schema만으로 보안을 검증했다고 주장하지 않는다.

릴리스는 버전, stable channel, 단조 증가하는 sequence, 발행·만료 시점, schema 및 engine 호환 범위, 콘텐츠 경로·역할·크기·SHA-256을 담는다. SHA-256은 bytes 손상 검출에 사용한다. 발행자 인증은 이미 신뢰한 공개키의 서명 검증으로 판단한다.

manifest의 rules/lexicon 호환 번호 `1`은 실제 데이터의 `schema_version: "1.0"`을 뜻한다. 런타임은 실제 JSON도 top-level object인지, 해당 schema version과 version 문자열을 갖는지, rules/entries가 비어 있지 않은 object 배열인지 확인한다. 이는 최소 형식 호환 검사이며 개별 규칙·어휘의 의미와 전체 publication schema 검증을 대신하지 않는다.

`release.json.sig`는 `release.json`의 **원본 UTF-8 bytes 전체**를 OpenSSH SSHSIG로 서명한다. JSON을 재직렬화하거나 줄바꿈을 바꾼 결과에 대해 서명을 검증하지 않는다. 서명은 manifest 내부에 넣지 않는다. namespace는 `kproto-release-v1`, principal은 `kproto-release`이며 key id는 SHA-256 공개키 지문이다. manifest의 key id를 trust anchor로 채택하지 않는다.

v1의 trust anchor는 `ssh-ed25519` 공개키 하나로 제한한다. installer는 public key를 strict parse하고 실제 지문을 계산하여 expected fingerprint와 일치시킨 뒤 principal·namespace가 고정된 allowed_signers를 직접 생성한다. 내려받은 allowed_signers, wildcard principal, 임의 options, certificate trust를 자동 수락하지 않는다. manifest의 호환 범위는 `min <= running < max_exclusive`로 비교하며 최소값이 최대값 이상인 범위를 거부한다. JSON Schema의 `format` 구현 여부에 기대지 않고 실제 달력 날짜·시각과 `issued_at < expires_at`를 검사한다.

확인된 절대 경로의 `ssh-keygen`을 `subprocess.run([...], input=manifest_bytes, shell=False, timeout=10)`으로 호출한다. 명령은 `-Y verify -f LOCAL_ALLOWED_SIGNERS -I kproto-release -n kproto-release-v1 -s LOCAL_SIGNATURE`를 사용한다. 서명기 출력은 진단에 노출하거나 파일에 보관하지 않으며 자격 증명 환경 변수도 전달하지 않는다. `check-novalidate`는 발행자 인증 경로에 사용하지 않는다. OpenSSH는 authorized signer 검증을 `-Y verify`로 제공한다. [OpenSSH 공식 매뉴얼](https://man.openbsd.org/ssh-keygen)

Python 표준 라이브러리는 여기서 필요한 SSHSIG 검증 API를 제공하지 않는다. 직접 암호 알고리즘을 새로 구현하거나 private `ssl` API를 사용하지 않는다. 검증기를 찾지 못하거나 capability 검사에 실패하면 원격 업데이트는 exit 5로 거부한다. 사용자는 오프라인 로컬 snapshot을 계속 쓸 수 있다. macOS·Linux·Windows의 검증기 제공 여부와 실측 범위는 [호스트 지원표](host-support.md)에 기록한다.

## 원격 조회와 인증

v1은 사용자 지정 HTTPS 정적 릴리스 저장소를 지원하도록 설계한다. 발행자는 `stable/release.json`, `stable/release.json.sig`, `releases/<version>/<allowlisted-content-file>`을 제공한다. content 파일 URL은 설치기가 source origin과 버전·고정 경로로 조립하며 manifest에서 URL을 받지 않는다. 서명한 manifest를 마지막에 게시해 부분 업로드의 수락을 막는다. 부분 업로드가 발생하면 설치기는 기존 정상본을 유지한다.

클라이언트는 TLS 검증을 유지하고 HTTP, URL userinfo, query credentials, 교차 origin redirect, HTTPS→HTTP redirect를 거부한다. 자동 redirect는 끈다. 각 HTTP 객체는 blocking TLS·header·body를 별도 POSIX worker에서 처리하고 부모가 15초 또는 남은 deadline에 worker를 종료한다. update 시작부터 모든 네트워크 조회의 총 deadline은 60초이며 서명 검증·filesystem 쓰기 시간은 별도이다. manifest는 64 KiB, 서명은 16 KiB, 각 콘텐츠는 1 MiB, 전체는 4 MiB로 제한한다. 실제 bytes 길이가 명시 크기와 다르면 거부한다. archive를 풀지 않고 고정 파일만 내려받는다.

private 저장소는 정적 콘텐츠를 제공하는 **동일 origin HTTPS endpoint + 선택한 환경 변수의 Bearer 토큰**으로 지원한다. `--token-env KPROTO_TOKEN`은 변수 이름만 설정에 저장한다. 토큰 값, Authorization header, 전체 환경, private 응답 본문은 로그·상태·예외에 기록하지 않는다. 토큰은 업데이트 실행 시에만 읽고 외부 검증기에는 전달하지 않는다.

v1은 GitHub private Releases의 API 조회·asset redirect를 자동 처리하지 않는다. GitHub의 API·asset 호스트를 사용할 adapter는 별도 구현·허용 origin·redirect 인증 전달 테스트가 필요하다. 그 전에는 사용자가 private repo에서 가져온 로컬 bundle을 설치하거나 조직이 동일 origin 배포 endpoint를 운영한다. Git credential helper를 호출하거나 저장소 토큰을 자동 탐색하지 않는다.

## 자동 업데이트

설치기는 기본적으로 `stable` 콘텐츠를 사용한다. `install --autoupdate interval`은 호스트를 새로 시작하는 `kproto run -- <host>` wrapper에서 24시간이 지난 경우 갱신을 시도한다. 사용자는 wrapper를 호스트의 실행 명령으로 한 번 지정한다. host 바이너리를 가로채거나 같은 이름으로 바꾸지 않는다. wrapper는 실패를 기록하고 마지막 정상본으로 호스트를 시작한다. 세션 중 매 응답을 다운로드하지 않는다.

자동 조회 실패는 1시간 후부터 재시도하며 연속 실패는 2·4·8·24시간까지 간격을 늘린다. 성공하면 24시간 주기로 돌아간다. 수동 `update`는 이 대기 시간을 무시한다. 상태에는 시도 시각과 성공 시각을 따로 기록하며 시스템 시각이 뒤로 움직이면 자동 조회를 한 번만 시도하고 다음 시각을 다시 계산한다. 한 번의 host 시작이 여러 네트워크 재시도를 수행하지 않는다.

wrapper를 쓰지 않는 macOS 사용자는 OS 예약 작업을 한 번 연결한다. 현재 `autoupdate configure --mode scheduled --interval-hours 24 --emit PATH`는 고정 절대 경로의 Python·CLI·state를 갖는 launchd plist를 생성하며 `registered=false`, `status=generated`로 기록한다. 생성만으로 예약 작업이 등록되지는 않는다. 사용자가 생성한 파일을 검토하여 `launchctl bootstrap`으로 연결해야 하며 이 작업에서는 실제 등록하지 않았다. 시스템이 job을 시작하면 `RunAtLoad`와 24시간 `StartInterval`로 `update --scheduled`를 실행한다. Linux systemd와 Windows Task Scheduler 출력·등록은 미구현이며 wrapper 방식을 제공한다. `--register`는 현재 CLI에 없다.

`autoupdate configure --mode off`는 네트워크 조회를 해제한다. 현재 구현은 hash가 일치하는 자기 생성 plist를 제거하고 `disabled`로 기록하며 설치한 규약과 캐시를 유지한다. 사용자가 외부에서 등록한 job 자체는 자동 bootout하지 않지만 남은 job의 scheduled 호출은 off 설정을 읽고 네트워크를 사용하지 않는다. 실제 job 제거는 사용자의 `launchctl bootout`이 필요하다. 명시적인 `update` 명령은 mode off에서도 네트워크 작업임을 사용자가 지시한 것으로 처리한다. pin이 있으면 원격 조회 및 적용을 하지 않는다. 현재 만료된 릴리스도 로컬 사용과 검사에서는 계속 허용한다. 만료는 새로운 원격 릴리스의 수락 조건이며 오프라인 사용 기한이 아니다.

최초 원격 수락 때에도 미래 발행 시각, 잘못된 시간 형식, 지난 만료를 거부한다. 최고 수락 sequence보다 낮은 릴리스는 원격 업데이트에서 거부한다. 같은 sequence의 다른 manifest hash도 거부한다. 같은 sequence·hash면 변경 없이 성공한다. sequence가 같거나 높아도 현재 버전보다 낮은 콘텐츠는 자동 적용하지 않는다. 해시가 일치하는 캐시의 과거 릴리스를 사용자가 `rollback`하면 sequence 최고값은 유지하고 그 버전으로 pin한다. 이는 rollback 직후 자동 업데이트가 사용자의 선택을 취소하지 않도록 한다.

TLS와 서명은 최신 릴리스가 존재한다는 사실을 보장하지 않는다. 서명한 manifest의 만료와 sequence로 재전송 범위를 제한하되 만료 전 최신본 숨김은 검출하지 못한다. 상태는 마지막 성공 조회 시각과 업데이트 실패를 표시하며 오래된 캐시를 최신본으로 표시하지 않는다. 시스템 시각 오류가 수락을 막으면 규약은 유지하고 시간을 확인하도록 보고한다.

## 원자성·동시 실행·복구

모든 쓰기 명령은 상태 루트와 대상 파일의 POSIX `flock`을 nonblocking으로 잡는다. 다른 프로세스가 lock을 보유하면 exit 7로 중단한다. 커널은 프로세스가 종료되면 lock을 해제하므로 PID 재사용을 근거로 stale lock을 회수하지 않는다. lock 파일은 남겨 동일 inode를 사용하며, 제거하지 않아 lock inode가 둘로 나뉘는 경쟁을 피한다.

POSIX 구현은 가능하면 디렉터리 descriptor와 `O_NOFOLLOW`를 사용하고 열린 파일의 owner/link count/inode를 재확인한다. 문자열의 `resolve()`와 쓰기 전 `is_symlink()`만으로 동시 symlink 교체를 막았다고 주장하지 않는다. 대상/부모의 identity가 바뀌면 쓰기를 중단한다. 네트워크 filesystem과 여러 사용자가 함께 쓸 수 있는 trust/대상 경로는 v1 원자 쓰기 지원에서 제외한다.

현재 처리는 다운로드·검증·cache 준비 이후 단일 `journal.json`에 원본/후보 state와 target 원본/후보 hash를 적는다. target 교체와 state commit 후 journal을 제거하며 전체 phase별 journal은 아직 구현하지 않았다. 각 파일은 같은 filesystem의 새 파일에 쓰고 `flush`, `fsync`, `os.replace`를 사용하며 POSIX 부모 디렉터리를 fsync한다. Windows atomic 구현은 미지원이다. 전원 단절 내구성은 filesystem과 OS 검증 범위를 따르므로 rename 성공만으로 보장하지 않는다.

여러 호스트 파일과 state 파일을 하나의 원자 연산으로 교체할 수는 없다. 기본 install은 호스트 하나만 등록한다. 여러 설치 대상 업데이트는 호스트가 시작되기 전 같은 lock 안에서 수행하고, 모든 대상 성공 후 state를 commit한다. 중간 실패 시 journal의 원본 hash와 현재 관리 hash가 일치하는 파일만 복원한다. 다른 프로세스나 사용자가 바꾼 파일은 복원하지 않고 충돌을 보고한다. 이미 실행 중인 호스트가 순간적인 서로 다른 버전을 읽는 경우를 막는다고 주장하지 않는다.

다음 쓰기 명령은 미완료 journal을 먼저 확인한다. state가 후보로 commit되지 않았고 target bytes가 후보이면 원본으로 복원한다. state와 target 모두 commit한 후보와 일치하면 journal 정리만 수행한다. target이 예상 원본/후보 모두와 다르면 쓰기를 중단하며 자동 diff는 제공하지 않는다. 읽기 전용 `status`는 미완료를 보고하며 파일을 복원하지 않는다. wrapper도 복구가 필요한 journal은 host를 시작하기 전에 처리하며 복구 충돌을 무시하지 않는다.

## CLI 계약

아래 표는 전체 인터페이스 계약이며 현재 지원 여부는 [구현 상태](implementation-status.md)에 따른다. `kproto`는 문서상 명칭이며 현재 실행 명령은 checkout에서 `python3 -m runtime.kproto`이다. 로컬 bundle·경로·source·trust key 값은 사용자가 정하며 예시를 실행한 것으로 표시하지 않는다.

| 명령 | 동작을 다음처럼 정한다. |
| --- | --- |
| `kproto install --bundle LOCAL_DIR --host codex --scope project --project-root ABS_PATH --local-snapshot` | 로컬 규약을 확인하고 프로젝트 파일에 관리 블록을 설치한다. |
| `kproto install --bundle LOCAL_DIR --host codex --scope user --trust-key PUBLIC_KEY --expected-fingerprint SHA256:... --autoupdate interval --source HTTPS_URL` | 신뢰한 서명 bundle을 설치하고 시작 wrapper의 주기 업데이트를 허용한다. |
| `kproto status --json` | 설치 버전·hash·trust·대상·충돌·pin·마지막 조회·오프라인 가용 상태를 로컬에서만 읽는다. |
| `kproto check INPUT --format json` | 활성 규약으로 로컬 검사한다. 모델 API를 호출하지 않는다. 의미 판정 미지원은 결과에 남긴다. |
| `kproto update` / `kproto update --scheduled` | 신뢰·호환·hash·경로를 검증한 stable 콘텐츠를 적용한다. scheduled 실패는 작업 결과에 남긴다. |
| `kproto update --pin 0.1.0` / `kproto update --unpin` | pin을 로컬 설정에 기록하거나 해제한다. pin과 자동 원격 하향 적용을 섞지 않는다. |
| `kproto rollback --version 0.1.0` | 검증 캐시의 과거 버전을 복원하고 pin한다. 캐시가 없으면 exit 4로 끝난다. |
| `kproto uninstall --host codex --scope user` | 검증된 관리 블록/전용 파일과 자기 예약 연결만 제거하며 다른 bytes를 유지한다. |
| `kproto autoupdate configure --mode interval\|scheduled\|off` | 자동 갱신 모드를 저장하고 지정한 자기 작업만 생성·해제한다. |
| `kproto run -- codex` | 갱신 주기가 왔으면 시도한 뒤 정상 로컬 규약으로 호스트를 시작한다. |

현재 `status --json`은 자격 증명 없는 결과를 stdout에 쓰고 진단은 stderr에 쓴다. `--dry-run`, 자동 diff, `status --host`, 검사 CLI 통합은 장래 인터페이스이며 현재 runtime parser에는 없다. 검사는 별도 validation CLI를 사용한다. source origin과 환경 변수 이름만 설정에 저장하고 secret 값·query credentials를 출력하지 않는다. 런타임 검사 JSON의 상세 계약은 검사 lane이 정의하며 설치기는 그 결과를 과장하지 않는다.

| Exit | CLI는 이 결과를 반환한다. |
| --- | --- |
| `0` | 작업을 마쳤거나 같은 내용이어서 변경할 것이 없다. |
| `1` | 로컬 검사에서 설정한 차단 등급 항목을 찾았다. |
| `2` | 인자·config·schema·UTF-8·경로 입력이 유효하지 않다. |
| `3` | 네트워크·시간 제한·private endpoint 인증에 실패했고 정상본을 유지했다. |
| `4` | 설치본·요청한 캐시·선택한 프로필을 찾지 못했다. |
| `5` | 신뢰 앵커·서명·hash·sequence·만료 검증에 실패했거나 검증기가 없다. |
| `6` | engine/schema/host 호환 범위를 충족하지 않는다. |
| `7` | 사용자 수정·중복 소유·lock·재개 충돌 때문에 쓰기를 중단했다. |
| `8` | filesystem 쓰기·원자 교체·복구를 완료하지 못했다. |

`run`은 호스트를 시작하면 호스트 exit code를 반환하고, 갱신 실패 코드는 상태와 stderr에 남긴다. 정상 로컬 규약이 없으면 호스트를 시작하기 전에 exit 4로 끝난다. `update --scheduled`는 위 실패 코드를 그대로 반환하여 OS 작업 이력이 실패를 기록하게 한다.

## 제거와 복구

제거는 기록한 hash와 일치하는 관리 내용만 제거한다. 설치 때 없던 파일도 사용자 내용이 생겼으면 보존한다. 현재 구현은 파일에서 관리 블록을 제거하며 최초 추가한 separator는 원본 prefix hash가 일치할 때만 제거한다. 관리 블록 자체가 바뀌었으면 오류를 반환하고 exit 7로 끝나며 원문·cache·backup을 보존한다. 자동 diff와 backup 경로 안내는 아직 제공하지 않는다.

uninstall은 상태·원본 backup·검증 캐시를 남겨 복구할 수 있게 한다. 별도의 명시적 purge가 있어야 자기 데이터도 지우며 v1 최초 구현 범위에는 purge를 넣지 않는다. 제거한 상태에서 같은 bundle을 다시 설치해 복원할 수 있다. updater는 자기 백업을 자동 삭제하지 않는다.

## 구현 순서

1. 로컬 bundle 검증·고정 allowlist·호스트 하나의 프로젝트 관리 블록·중복 설치·status·uninstall을 구현한다.
2. 충돌 감지·backup·lock·journal·중단 복구·rollback을 구현하고 실패 주입 시험을 통과시킨다.
3. SSHSIG 검증·HTTPS 동일 origin·size/timeout·sequence/expiry·private token 비노출을 구현한다.
4. wrapper 주기 갱신을 구현하고 갱신 실패 후 기존 프로필 유지와 host 실행을 시험한다.
5. 각 OS 예약 작업과 추가 호스트 adapter를 별도 검증하여 지원표의 상태를 갱신한다.

설계의 모든 항목이 첫 구현에 포함되었다고 주장하지 않는다. [검증 계획](verification.md)과 [구현 상태](implementation-status.md)는 실제 시험 증거와 남은 공백을 정한다.

[HTTPS 실행 검증](https-transport-verification.md)은 Python 3.11의 실제 TLS·서명 확인·시작 wrapper 갱신·오프라인 유지 결과와 환경별 한계를 기록한다. 공개 배포와 예약 실행 등록은 별도 단계로 남아 있다.

## 발행용 콘텐츠를 준비한다

[발행 도구 안내](publisher.md)는 원본 구조·생성물 일치 검사, 외부 서명 입력 생성, 서명 검증을 거친 정적 배포 폴더 생성을 다룬다. 준비 명령과 실제 서버 게시·공개키 신뢰 설정을 구분한다.
