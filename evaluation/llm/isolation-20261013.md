# 사용자 스킬의 실험 유입을 확인했다

어휘 사용 평가의 최초 STE 1번 묶음이 작업 폴더 밖의 `using-superpowers/SKILL.md`를 읽었다. [원시 실행 기록](lexical-meaning-use-20261013/ste-b1/stdout.jsonl)과 [사건 기록](lexical-meaning-use-20261013/isolation-incident.json)을 보존했다. 사전 계획의 외부 자료 접근 제외 조건에 따라 최초 비교를 최종 점수로 사용하지 않는다.

[공식 스킬 문서](https://developers.openai.com/codex/skills/)는 `$HOME/.agents/skills`를 사용자 스킬 탐색 위치로 설명한다. `CODEX_HOME`을 분리하고 사용자 config와 execpolicy rules를 무시한 것만으로 이 경로가 차단되지 않았다. 읽기 전용 sandbox는 외부 파일의 읽기 차단을 보장하지 않는다.

이전 [압축 문체 비교](controlled-korean-20261013/report.md)와 [새 입력 반복 비교](fresh-controlled-20261013/report.md)의 선택 실행에서는 같은 외부 파일 읽기가 관측되지 않았다. 그러나 사용 가능한 사용자 스킬의 메타데이터를 제거했는지는 당시 검증하지 않았다. 따라서 해당 기록을 사용자 스킬까지 완전히 제거한 기준선으로 해석하지 않는다. 원출력·수치·기존 평정은 변경하지 않는다.

수정은 새 실행기에만 적용하고 이전 실행기·동결 기록을 보존한다. CLI의 실행별 탐색 설정과 임시 app-server의 실제 `skills/list` 결과를 대조한 뒤 같은 입력·정답으로 모든 비교 조건을 다시 실행한다. 프로필·사전·정답을 출력에 맞춰 고치지 않는다. 전역 스킬 파일·설정과 사용자 HOME은 변경하지 않는다.

## 실제 비활성화와 지침 로드를 확인했다

여섯 기능 옵션만 적용한 inventory에는57개가 모두 활성 상태로 남았다. `skills.config`에 관측한 각 경로의 `enabled=false`를 지정한 뒤에는57개 발견·활성0개·오류0개를 확인했다. 다섯 기본 스킬의 경로는 매 실행의 임시 CODEX_HOME에 맞춰 해석한다. [검증 기록](lexical-meaning-use-20261013/skill-isolation-verification.json)을 보존했다.

[실제 모델 진단](lexical-meaning-use-20261013/isolation-model-probe/verification.json)은 프로젝트 AGENTS 표식을 정확히 반환했고, 사용 가능한 스킬 목록은 비어 있었다. 읽기 도구는 호출하지 않았다. CLI의 under-development 옵션 경고는 기록했으며 정상 종료와 구분한다.

수정된 실행기로 여섯 조건을 모두 다시 실행했다. [최종 도구 기록 감사](lexical-meaning-use-20261013/isolated-run-audit.json)에서는 작업 폴더 안의 어휘집 조회만 관측됐다. KP 두 묶음은 관련 사전 내용을 실제로 읽었고, 미적용은 해당 경로가 없는 것을 확인했다. OS 수준의 임의 외부 읽기 차단이나 미래에 추가된 스킬까지 자동 차단하는 보장은 아니다.
