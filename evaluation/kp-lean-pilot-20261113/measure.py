#!/usr/bin/env python3
"""파일럿 측정. 검사기 위반 수, 고지 위치, 사례별 탐침, 모델 간 편차, 가린 검토 결과를 집계한다."""
import json, re, statistics as st, sys, collections
from pathlib import Path
import pilot
ROOT=pilot.ROOT; lint=pilot.kp_lint.lint
ARMS=['kp','ste','cand','candfix','v2','v2fix']; RULES=['긴문장','긴문단','긴항목','가로나열','부정결합','이중부정','말미고지','원문밖부정','예고문장']
def body(t): return t
def first_pos(t,pats):
    idx=[m.start() for p in pats for m in [re.search(p,t)] if m]
    return round(min(idx)/max(1,len(t)),2) if idx else None
def probes(c,t):
    p={}
    if c['id']=='P1':
        p['노란색 언급']=t.count('노란'); p['조명 언급']=t.count('조명')
        hand=re.search(r'손',t); lever=re.search(r'레버를[^.\n]*내린|내리세요|내립니다|내리십시오',t)
        p['손 확인이 레버 조작보다 앞']=bool(hand and lever and hand.start()<lever.start())
    if c['id']=='P2':
        p['내부자료 고지 위치']=first_pos(t,[r'내부 비교자료',r'대신하지 않'])
        p['확정견적 고지 위치']=first_pos(t,[r'확정견적'])
    if c['id']=='P3':
        p['미수정 고지 위치']=first_pos(t,[r'수정하지 않',r'수정 안',r'미수정',r'수정은 하지'])
        p['미실행 고지 위치']=first_pos(t,[r'실행하지 않',r'미실행',r'실행은 하지',r'준비만'])
        p['검색 실패 위치']=first_pos(t,[r'실패'])
    if c['id']=='P4':
        p['원인 미확정 고지 위치']=first_pos(t,[r'확정할 수 없',r'원인 규명',r'확정하지'])
    return p
rows={}
for mi,tag in enumerate(pilot.TAG):
    for c in pilot.CASES:
        for a in ARMS:
            f=ROOT/'runs'/f"{c['id']}-{tag}-{a}"/'output.md'
            if not f.exists(): continue
            t=f.read_text(); r=lint(t,c['source'],c['mode'])
            kept,total=map(int,r['stats']['numbers_kept'].split('/'))
            rows[(c['id'],tag,a)]=dict(chars=len(t),ratio=r['stats']['length_ratio'],mean_words=r['stats']['mean_words'],viol=sum(r['counts'].get(k,0) for k in RULES),per1k=round(sum(r['counts'].get(k,0) for k in RULES)/len(t)*1000,1),counts=r['counts'],num_missing=total-kept,probes=probes(c,t))
out=[]
def P(*a): out.append(' '.join(str(x) for x in a))
P('## 1. 비교군별 합계 (4사례 x 4모델 = 16건씩)')
P('| 비교군 | 건수 | 글자 합 | 문장 평균 어절 | '+' | '.join(RULES)+' | 위반 합 | 1,000자당 위반 | 원문 수치 누락 |'); P('|'+'---|'*(len(RULES)+8))
for a in ARMS:
    v=[x for k,x in rows.items() if k[2]==a]
    if not v: continue
    P(f"| {a} | {len(v)} | {sum(x['chars'] for x in v)} | {round(st.mean(x['mean_words'] for x in v),1)} | "+' | '.join(str(sum(x['counts'].get(k,0) for x in v)) for k in RULES)+f" | {sum(x['viol'] for x in v)} | {round(sum(x['viol'] for x in v)/sum(x['chars'] for x in v)*1000,1)} | {sum(x['num_missing'] for x in v)} |")
P('\n## 2. 모델별 1,000자당 위반 수와 모델 간 편차')
P('| 비교군 | '+' | '.join(pilot.TAG)+' | 최대-최소 |'); P('|---|'+'---|'*(len(pilot.TAG)+1))
for a in ARMS:
    vals=[]
    for tag in pilot.TAG:
        v=[x for k,x in rows.items() if k[2]==a and k[1]==tag]
        vals.append(round(sum(x['viol'] for x in v)/max(1,sum(x['chars'] for x in v))*1000,1) if v else None)
    ok=[x for x in vals if x is not None]
    P(f"| {a} | "+' | '.join(str(x) for x in vals)+f" | {round(max(ok)-min(ok),1) if ok else ''} |")
P('\n## 3. 사례별 길이 (원문 대비 배율, 모델 4개 평균과 범위)')
P('| 사례 | 원문 글자 | '+' | '.join(ARMS)+' |'); P('|---|---|'+'---|'*len(ARMS))
for c in pilot.CASES:
    cells=[]
    for a in ARMS:
        v=[x['ratio'] for k,x in rows.items() if k[0]==c['id'] and k[2]==a]
        cells.append(f"{round(st.mean(v),2)} ({min(v)}~{max(v)})" if v else '')
    P(f"| {c['id']} {c['mode']} | {len(c['source'])} | "+' | '.join(cells)+' |')
P('\n## 4. 사례별 탐침 (모델 순서: '+', '.join(pilot.TAG)+')')
for c in pilot.CASES:
    names=list(next(iter([x['probes'] for k,x in rows.items() if k[0]==c['id']]),{}).keys())
    for n in names:
        P(f"- {c['id']} {n}")
        for a in ARMS:
            P(f"  - {a}: "+', '.join(str(rows[(c['id'],t,a)]['probes'].get(n)) if (c['id'],t,a) in rows else '-' for t in pilot.TAG))
P('\n## 5. 가린 검토 (gpt-6-astra high, r60 rubric)')
for third in ['cand','candfix','v2','v2fix']:
    mean=collections.defaultdict(collections.Counter); pair=collections.Counter(); n=0; fails=[]
    for d in sorted(list((ROOT/'reviews').glob(f'*-{third}'))+list((ROOT/'reviews').glob(f'*-{third}.r1'))) if (ROOT/'reviews').exists() else []:
        if not (d/'verdict.json').exists(): continue
        v=json.loads((d/'verdict.json').read_text()); links=json.loads((d/'blind-key.json').read_text()); n+=1
        for label,o in v['outputs'].items():
            arm=links[label]['arm']; mean[arm][o['meaning']]+=1
            if o['meaning']!='pass': fails.append((d.name,arm,o['meaning'],'; '.join(f.get('reason','')[:110] for f in o.get('findings',[])[:2])))
        for p in v['pairs']:
            l,r=links[p['left']]['arm'],links[p['right']]['arm']; w=p['winner']
            if w=='tie': pair[(tuple(sorted([l,r])),'tie')]+=1
            else: pair[(tuple(sorted([l,r])),links[w]['arm'])]+=1
    P(f"\n### kp / {third} / ste 묶음: 유효 검토 {n}건")
    for arm in ['kp',third,'ste']: P(f"- {arm} 의미: 통과 {mean[arm]['pass']} / 실패 {mean[arm]['fail']} / 미해결 {mean[arm]['unresolved']}")
    for a,b in [(third,'kp'),(third,'ste'),('kp','ste')]:
        k=tuple(sorted([a,b])); P(f"- 명료성 {a} 대 {b}: {a} 승 {pair[(k,a)]} / {b} 승 {pair[(k,b)]} / 무 {pair[(k,'tie')]}")
    for f in fails: P('  - 비통과:',' | '.join(f))
(ROOT/'results.md').write_text('\n'.join(out)+'\n'); print('\n'.join(out))

