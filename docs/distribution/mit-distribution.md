# 0.7.0 배포물에 MIT 고지를 보존한다

직접 작성한 코드·한국어 규약·사전·용례·문서는 [MIT License](../../LICENSE)로 제공한다. 저작권 표기는 `Copyright (c) 2026 Korean Protocol contributors`다. 제3자 ASD-STE100 원문·논문·표준·인용문의 권리는 [NOTICE.md](../../NOTICE.md)에서 구분한다.

## 배포 위치마다 고지를 함께 둔다

| 배포 위치 | 보존하는 고지 |
| --- | --- |
| 저장소와 오프라인 ZIP | 루트 `LICENSE`와 `NOTICE.md`를 함께 제공한다. |
| 채팅용 `KOREAN-PROTOCOL.md` | 규약 본문과 함께 전체 고지를 담는다. |
| 설치 캐시의 `pack/protocol.md` | 원래 복제본이 없어져도 전체 고지가 남는다. |
| 지속 관리 Python 도구 | 독립 재배포에도 MIT 허가문이 남도록 주석에 포함한다. |

서명 콘텐츠에는 고지가 포함된 상세 규약을 담는다. 컴파일러는 LICENSE·NOTICE를 필수 입력으로 읽고 발행기는 같은 입력을 보호된 경로로 캡처해 재컴파일한다. 누락되거나 생성물이 원본과 다르면 발행 검증을 통과하지 못한다.

## 공개 0.7.0과 현재 원본을 구분한다

[공개 v0.7.0](https://github.com/project820/korean-protocol/releases/tag/v0.7.0)의 ZIP·단독 파일은 `7e01d53`의 고정 산출물이다. 서명 콘텐츠 0.7.0·순번 3은 `67f537e`에서 발행했다. [발행·갱신 기록](public-0.7.0-verification.md)은 두 경로의 출처와 검사 범위를 구분한다.

라이선스는 파일의 사용·재배포 조건이며 발행자 서명이나 전문가 승인·독자 효과의 인증이 아니다. 프로필 상한은 엔진 0.2.0의 30 KiB, 관리 블록 상한은 32 KiB이며 고지를 이유로 규칙·예외를 잘라내지 않는다.

## 변경 후 고지를 검사한다

```sh
python3 -B -m unittest tests.test_distribution tests.test_release tests.test_agent_install
```

이 검사는 패키지·발행 입력·지속 관리 코드의 회귀 확인이며 실제 모델 출력이나 원격 게시의 성공을 대신하지 않는다. 최초 MIT 적용·미리보기 8·비공개 서명 시험은 [개정 전 기록](https://github.com/project820/korean-protocol/blob/dacbbc239fc9dbb22f2ddb87119d4ac7161b2e3c/docs/distribution/mit-distribution.md)에 보존한다. 그 당시의 미공개 상태·28 KiB 한도·시험 300개를 현재 상태로 보고하지 않는다.
