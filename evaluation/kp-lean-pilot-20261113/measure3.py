#!/usr/bin/env python3
"""후보 3 측정: 문체 위반, 구조 요소, 사례 탐침, rubric2 가린 검토."""
import json, re, statistics as st, collections, sys
from pathlib import Path
import pilot
ROOT=pilot.ROOT; lint=pilot.kp_lint.lint
ARMS=['kp','ste','v3']
RULES=['긴문장','긴문단','긴항목','가로나열','부정결합','이중부정','말미고지','원문밖부정','예고문장']
def struct(t):
    L=[l for l in t.split('\n') if l.strip()]
    heads=sum(1 for l in L if l.startswith('#'))
    items=[l for l in L if re.match(r'\s*([-*]|\d+[.)])\s',l)]
    boldhead=sum(1 for l in items if re.match(r'\s*([-*]|\d+[.)])\s+\*\*',l))
    title=bool(L) and (L[0].startswith('#') or re.fullmatch(r'\*\*.+\*\*',L[0].strip()) is not None)
    ref=any(re.match(r'(#+\s*)?(\*\*)?참고',l.strip()) for l in L[-6:])
    return dict(heads=heads,items=len(items),boldhead=round(boldhead/max(1,len(items)),2),title=title,ref_bottom=ref)
def probes(c,t):
    p={}
    if c['id']=='P1': p['노란색 언급']=t.count('노란')
    if c['id']=='P5':
        p['빨간 밸브 금지 유지']=bool(re.search(r'빨간[^\n]{0,40}(잠그지|잠그면 안|절대)',t))
        p['빨간 밸브 금지가 파란 밸브 잠금 앞이나 같은 단계']=None
        m1=re.search(r'빨간',t); m2=re.search(r'파란[^\n]{0,30}잠근|파란[^\n]{0,30}잠가',t)
        if m1 and m2: p['빨간 밸브 금지가 파란 밸브 잠금 앞이나 같은 단계']= t.rfind('\n',0,m1.start())<=t.find('\n',m2.start()) and m1.start()<=t.find('\n',m2.start()) if t.find('\n',m2.start())>0 else True
        p['회색 배관 언급']=t.count('회색')
    if c['id'] in ('P2','P3','P4'):
        first=t.strip().split('\n')[:6]; p['첫 6줄 안 고지·미확정']=any(re.search(r'내부 비교|대신하지|수정하지 않|실행하지 않|미확인|확정할 수 없|확정하지',l) for l in first)
    return p
rows={}
for mi,tag in enumerate(pilot.TAG):
    for c in pilot.CASES:
        for a in ARMS:
            f=ROOT/'runs'/f"{c['id']}-{tag}-{a}"/'output.md'
            if not f.exists(): continue
            t=f.read_text(); r=lint(t,c['source'],c['mode'])
            rows[(c['id'],tag,a)]=dict(chars=len(t),viol=sum(r['counts'].get(k,0) for k in RULES),s=struct(t),p=probes(c,t),words=r['stats']['mean_words'])
out=[]; P=lambda *a: out.append(' '.join(str(x) for x in a))
P('## 후보 3 측정 (사례 5 x 모델 4)')
P('| 비교군 | 건수 | 1,000자당 위반 | 모델별 (sol/terra/sonnet/grok) | 문장 평균 어절 | 제목 있음 | 소제목 평균 | 항목 첫머리 굵게 비율 |'); P('|---|---|---|---|---|---|---|---|')
for a in ARMS:
    v=[x for k,x in rows.items() if k[2]==a]
    if not v: continue
    per=[]
    for tag in pilot.TAG:
        w=[x for k,x in rows.items() if k[2]==a and k[1]==tag]; per.append(round(sum(x['viol'] for x in w)/max(1,sum(x['chars'] for x in w))*1000,1))
    P(f"| {a} | {len(v)} | {round(sum(x['viol'] for x in v)/sum(x['chars'] for x in v)*1000,1)} | {' / '.join(map(str,per))} | {round(st.mean(x['words'] for x in v),1)} | {sum(x['s']['title'] for x in v)}/{len(v)} | {round(st.mean(x['s']['heads'] for x in v),1)} | {round(st.mean(x['s']['boldhead'] for x in v),2)} |")
P('\n## 탐침 (sol, terra, sonnet, grok)')
for c in pilot.CASES:
    names=sorted({n for k,x in rows.items() if k[0]==c['id'] for n in x['p']})
    for n in names:
        P(f"- {c['id']} {n}: "+'; '.join(f"{a}=" + ','.join(str(rows[(c['id'],t,a)]['p'].get(n)) if (c['id'],t,a) in rows else '-' for t in pilot.TAG) for a in ARMS))
P('\n## rubric2 가린 검토 (gpt-6-astra high)')
for third in ['v3','candfix','cand']:
    mean=collections.defaultdict(collections.Counter); pair=collections.Counter(); n=0; fails=[]
    for d in sorted(list((ROOT/'reviews').glob(f'*-{third}@r2'))+list((ROOT/'reviews').glob(f'*-{third}@r2.r1'))):
        if not (d/'verdict.json').exists(): continue
        v=json.loads((d/'verdict.json').read_text()); k=json.loads((d/'blind-key.json').read_text()); n+=1
        for L,o in v['outputs'].items():
            arm=k[L]['arm']; mean[arm][o['meaning']]+=1
            if o['meaning']!='pass': fails.append((d.name,arm,o['meaning'],'; '.join(f.get('reason','')[:150] for f in o.get('findings',[])[:2])))
        for pr in v['pairs']:
            l,r=k[pr['left']]['arm'],k[pr['right']]['arm']; w=pr['winner']; key=tuple(sorted([l,r]))
            pair[(key,'tie' if w=='tie' else k[w]['arm'])]+=1
    if not n: continue
    P(f"\n### kp / {third} / ste: 유효 검토 {n}건")
    for arm in ['kp',third,'ste']: P(f"- {arm} 의미: 통과 {mean[arm]['pass']} / 실패 {mean[arm]['fail']} / 미해결 {mean[arm]['unresolved']}")
    for a,b in [(third,'kp'),(third,'ste'),('kp','ste')]:
        key=tuple(sorted([a,b])); P(f"- 명료성 {a} 대 {b}: {a} 승 {pair[(key,a)]} / {b} 승 {pair[(key,b)]} / 무 {pair[(key,'tie')]}")
    for f in fails: P('  - 비통과:',' | '.join(f))
(ROOT/'results-v3.md').write_text('\n'.join(out)+'\n'); print('\n'.join(out))

