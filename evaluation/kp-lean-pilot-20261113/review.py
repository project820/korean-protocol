#!/usr/bin/env python3
"""가린 의미·명료성 검토. r60 plan.json 의 rubric 을 그대로 쓴다. 검토 모델은 gpt-6-astra high."""
import concurrent.futures, hashlib, itertools, json, random, re, sys
from pathlib import Path
import pilot
ROOT=pilot.ROOT; REPO=pilot.REPO
RUBRIC=json.loads((REPO/'evaluation/clarity-20261016-r60/plan.json').read_text())['rubric']
RUBRIC2=(ROOT/'rubric2.txt').read_text()
RUBRIC3=(ROOT/'rubric3.txt').read_text()
RUBRIC4=(ROOT/'rubric4.txt').read_text()
REVIEWER='gpt-6-astra'
pilot.EFFORT='high'
def parse(t):
    t=t.strip(); t=re.sub(r'^```(?:json)?\s*|\s*```$','',t)
    return json.loads(t[t.find('{'):t.rfind('}')+1])
def review(job):
    mi,c,third=job; tagr=third.split('@')[1] if '@' in third else ''; third=third.split('@')[0]
    key=f"{c['id']}-{pilot.TAG[mi]}-{third}"+('@'+tagr if tagr else ''); d=ROOT/'reviews'/key
    if d.exists():
        # 서버 과부하로 출력 없이 실패한 검토만 새 폴더(.r1)에서 한 번 다시 요청한다. 실패 기록은 보존한다.
        rec=json.loads((d/'record.json').read_text()) if (d/'record.json').exists() else {}
        if rec.get('status')!='error' or (ROOT/'reviews'/(key+'.r1')).exists(): return None
        d=ROOT/'reviews'/(key+'.r1')
    arms=['kp',third,'ste']
    for a in arms:
        if not (ROOT/'runs'/f"{c['id']}-{pilot.TAG[mi]}-{a}"/'output.md').exists(): return (key,'missing '+a)
    rnd=random.Random(key); rnd.shuffle(arms)
    outputs={}; links={}
    for label,a in zip('ABC',arms):
        raw=(ROOT/'runs'/f"{c['id']}-{pilot.TAG[mi]}-{a}"/'output.md').read_bytes()
        outputs[label]=raw.decode(); links[label]={'arm':a,'sha256':hashlib.sha256(raw).hexdigest()}
    packet={'task':c['task'],'source':c['source'],'outputs':outputs}
    rec=pilot.call(d,({'r2':RUBRIC2,'r3':RUBRIC3,'r4':RUBRIC4}.get(tagr,RUBRIC))+'\n\n'+json.dumps(packet,ensure_ascii=False),REVIEWER)
    (d/'blind-key.json').write_text(json.dumps(links,ensure_ascii=False,indent=1)); (d/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=1))
    if rec['status']=='completed':
        try:
            v=parse((d/'output.md').read_text()); (d/'verdict.json').write_text(json.dumps(v,ensure_ascii=False,indent=1)); return (key,'ok')
        except Exception as e: return (key,'parse error '+repr(e)[:80])
    return (key,rec['status'])
if __name__=='__main__':
    sel=[a for a in sys.argv[1:] if a.startswith('cases=')]
    cases=[c for c in pilot.CASES if not sel or c['id'] in sel[0][6:].split(',')]
    thirds=[a for a in sys.argv[1:] if not a.startswith('cases=')] or ['cand','candfix']
    jobs=list(itertools.product(range(len(pilot.MODELS)),cases,thirds))
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for r in pool.map(review,jobs):
            if r: print(r,flush=True)

