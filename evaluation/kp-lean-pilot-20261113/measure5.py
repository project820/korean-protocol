#!/usr/bin/env python3
"""후보 4 측정: kp / ste / v3 / v4."""
import json, re, statistics as st, collections
import pilot
ROOT=pilot.ROOT; lint=pilot.kp_lint.lint
ARMS=['kp','ste','v3','v4','v5']
RULES=['긴문장','긴문단','긴항목','가로나열','부정결합','이중부정','말미고지','원문밖부정','예고문장']
NEG=re.compile(r'아니다|아닙니다|아니며|아니고|아니라|않는다|않습니다|않았다|않았습니다|않으며|않고|없다|없습니다|없으며|없고|못했|뜻하지')
def blocks(t):
    out=[];cur=''
    for l in t.split('\n'):
        if re.match(r'\s*([-*]|\d+[.)])\s',l) or not l.strip() or l.startswith('#'):
            if cur: out.append(cur)
            cur=l if l.strip() and not l.startswith('#') else ''
        else: cur+=' '+l
    if cur: out.append(cur)
    return out
def m(t):
    b=blocks(t); L=t.split('\n')
    steps=[i for i,l in enumerate(L) if re.match(r'\d+[.)]\s+\*\*',l)]
    nextline=sum(1 for i in steps if re.fullmatch(r'\d+[.)]\s+\*\*[^*]+\*\*\s*',L[i]) and i+1<len(L) and L[i+1].startswith(' ') and L[i+1].strip())
    return dict(negstack=sum(1 for x in b if len(NEG.findall(x))>=2), neg=len(NEG.findall(t)), steps=len(steps), nextline=nextline,
        boldstatus=len(re.findall(r'\*\*\[확인불가\]\*\*|\*\*(미확인|미실행|미기재)\*\*',t)), status=len(re.findall(r'\[확인불가\]|미확인|미실행',t)))
rows={}
for tag in pilot.TAG:
    for c in pilot.CASES:
        for a in ARMS:
            f=ROOT/'runs'/f"{c['id']}-{tag}-{a}"/'output.md'
            if not f.exists(): continue
            t=f.read_text(); r=lint(t,c['source'],c['mode'])
            rows[(c['id'],tag,a)]=dict(chars=len(t),viol=sum(r['counts'].get(k,0) for k in RULES),**m(t))
out=[];P=lambda *a: out.append(' '.join(str(x) for x in a))
P('| 비교군 | 건수 | 1,000자당 문체 위반 (sol/terra/sonnet/grok) | 부정 2개 이상 쌓인 항목 | 부정 표현 합 | 굵은 단계 중 세부 줄바꿈 | 굵은 상태 표지/상태 표지 |'); P('|---|---|---|---|---|---|---|')
for a in ARMS:
    v=[x for k,x in rows.items() if k[2]==a]
    if not v: continue
    per=[]
    for tag in pilot.TAG:
        w=[x for k,x in rows.items() if k[2]==a and k[1]==tag]; per.append(round(sum(x['viol'] for x in w)/max(1,sum(x['chars'] for x in w))*1000,1))
    P(f"| {a} | {len(v)} | {round(sum(x['viol'] for x in v)/sum(x['chars'] for x in v)*1000,1)} ({' / '.join(map(str,per))}) | {sum(x['negstack'] for x in v)} | {sum(x['neg'] for x in v)} | {sum(x['nextline'] for x in v)}/{sum(x['steps'] for x in v)} | {sum(x['boldstatus'] for x in v)}/{sum(x['status'] for x in v)} |")
for third in ['v5']:
    mean=collections.defaultdict(collections.Counter); pair=collections.Counter(); n=0; fails=[]
    for d in sorted(list((ROOT/'reviews').glob(f'*-{third}@r4'))+list((ROOT/'reviews').glob(f'*-{third}@r4.r1'))):
        if not (d/'verdict.json').exists(): continue
        v=json.loads((d/'verdict.json').read_text()); k=json.loads((d/'blind-key.json').read_text()); n+=1
        for L,o in v['outputs'].items():
            arm=k[L]['arm']; mean[arm][o['meaning']]+=1
            if o['meaning']!='pass': fails.append((d.name,arm,o['meaning'],'; '.join(f.get('reason','')[:160] for f in o.get('findings',[])[:2])))
        for pr in v['pairs']:
            l,r=k[pr['left']]['arm'],k[pr['right']]['arm']; w=pr['winner']; key=tuple(sorted([l,r]))
            pair[(key,'tie' if w=='tie' else k[w]['arm'])]+=1
    P(f"\n가린 검토 rubric4: 유효 {n}건")
    for arm in ['kp',third,'ste']: P(f"- {arm} 의미: 통과 {mean[arm]['pass']} / 실패 {mean[arm]['fail']} / 미해결 {mean[arm]['unresolved']}")
    for a,b in [(third,'kp'),(third,'ste'),('kp','ste')]:
        key=tuple(sorted([a,b])); P(f"- 명료성 {a} 대 {b}: {a} 승 {pair[(key,a)]} / {b} 승 {pair[(key,b)]} / 무 {pair[(key,'tie')]}")
    for f in fails: P('  - 비통과:',' | '.join(f))
(ROOT/'results-v5.md').write_text('\n'.join(out)+'\n'); print('\n'.join(out))

