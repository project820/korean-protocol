# 과거 평가를 재현한다

규칙과 사전을 정제한 뒤에도 이전 평가의 입력·평정·출처 해시를 보존한다. 이전 평가의 원본 검사는 당시 기준본을 지정해야 통과한다. 기본 명령이 현재 파일과 해시 불일치를 보고하면 과거 평정을 새 원본에 적용하지 않는다.

저장소 루트에서 다음 명령으로 과거 평가의 집계와 출처 무결성을 확인한다.

```sh
python3 evaluation/lexicon-independent/check.py --source-root evaluation/baselines/20261012-before-rule-and-lexicon-refinement
python3 evaluation/korean-independent/verify-review.py --rules-root evaluation/baselines/20261012-before-rule-and-lexicon-refinement
```

두 명령은 통과했으며 각각 최초 어휘 문맥 40개의 19개 직접 연결과 한국어 사례 31개의 30개 검토 통과를 재현했다. 이 검사는 의미 판정을 다시 수행하지 않는다. 최초 어휘 평가의 원래 보고서·평정 파일 10개는 변경하지 않았다.

[임시 설치 시험](local-install-smoke.json)은 SHA256 `6ec821d7aa866f520d7d3e1762b393ba40f0ee7ee8ae69905ab767f053d88c4c`인 이전 프로필의 실제 Codex 로딩을 확인했다. 정제 프로필의 실제 모델 실행은 [별도 보고서](../../evaluation/llm/rule-refinement-20261012/report-ko.md)에 기록했으며, 이전 설치 시험을 정제 프로필의 설치 재시험으로 표시하지 않는다.
