import json, time, urllib.request, hashlib, sys, re, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
REPO = Path('/Users/m5max/Documents/ChatGPT/ASD-STE100 Kor')
OUT = REPO/'output/kp-v0111-probe'; OUT.mkdir(exist_ok=True)
SK = REPO/'skills/korean-protocol'
SKILL = (SK/'SKILL.md').read_text()
REFS3 = ''.join('\n\n참조 파일: '+p+'\n'+(SK/p).read_text() for p in ['references/interactive-html.md','assets/interactive-explainer.html'])
REFS2 = '\n\n참조 파일: references/output-formats.md\n'+(SK/'references/output-formats.md').read_text()
STE = (REPO/'evaluation/clarity-20261016-r60/ste.md').read_text()
SRC = (REPO/'output/kp-sns-samples-20261113/source.txt').read_text().strip()
MODELS = {'sol':'gpt-6.1-sol','terra':'gpt-6.1-terra','sonnet':'anthropic/claude-sonnet-5-5','grok':'xai/grok-4.7'}
Q = '이 스킬을 막 불러온 상태다. 사용자가 묻는다: "KP에서 L2가 뭐야? L1~L4를 각각 한 줄로 알려 주고, L3로 HTML을 만들 때 꼭 지킬 규칙을 다섯 개만 말해 줘. 각 규칙이 지침의 어느 부분에 있는지도 밝혀." 지침에 있는 내용만으로 답하라.'
TASK_H = '다음 원문을 작성 지침에 따라 재작성하라. 외부 의존성 없는 단일 index.html 전체를 html 코드 블록 하나로만 출력하라. 설명은 붙이지 마라.\n\n원문\n'+SRC
TASK_L2 = '다음 원문을 작성 지침에 따라 재작성하라. 표와 Mermaid 도식을 쓸 수 있는 마크다운 문서로 출력하라. 설명은 붙이지 마라.\n\n원문\n'+SRC
def call(name, model, prompt):
    if (OUT/(name+'.md')).exists(): return name, 'skip'
    req = {'model':model,'input':[{'role':'user','content':[{'type':'input_text','text':prompt}]}],'reasoning':{'effort':'medium'},'store':False,'stream':True,'tools':[]}
    raw=json.dumps(req,ensure_ascii=False).encode()
    rq = urllib.request.Request('http://127.0.0.1:10100/v1/responses', data=raw, headers={'Content-Type':'application/json','Accept':'text/event-stream'})
    if model.startswith('gpt-'):
        tok = json.loads((Path.home()/'.codex/auth.json').read_text())['tokens']['access_token']
        rq.add_unredirected_header('Authorization','Bearer '+tok)
    t=time.time(); rec={'name':name,'model':model,'request_sha256':hashlib.sha256(raw).hexdigest()}
    try:
        body = urllib.request.urlopen(rq, timeout=420).read().decode()
        ev = [json.loads(l[6:]) for l in body.splitlines() if l.startswith('data: ') and l[6:]!='[DONE]']
        resp = [e['response'] for e in ev if e.get('type') in ('response.completed','response.failed','response.incomplete')][-1]
        outs = resp.get('output') or [e['item'] for e in ev if e.get('type')=='response.output_item.done']
        text = '\n'.join(c['text'] for o in outs if o.get('type')=='message' for c in o.get('content',[]) if c.get('type')=='output_text')
        (OUT/(name+'.md')).write_text(text)
        rec.update(status=resp.get('status'), returned=resp.get('model'), chars=len(text), output_sha256=hashlib.sha256(text.encode()).hexdigest())
    except Exception as e:
        rec.update(status='error', error=repr(e)[:200])
    rec['seconds']=round(time.time()-t); (OUT/(name+'.json')).write_text(json.dumps(rec,ensure_ascii=False))
    return name, rec['status'], rec['seconds']
jobs=[]
for tag,m in MODELS.items():
    jobs.append((f'final-qa-{tag}', m, '작성 지침\n'+SKILL+'\n\n'+Q))
    jobs.append((f'final-l2-kp-skill-{tag}', m, '작성 지침\n'+SKILL+'\n\n작업 요청\nL2로 작성한다. '+TASK_L2))
    jobs.append((f'final-l2-kp-refs-{tag}', m, '작성 지침\n'+SKILL+REFS2+'\n\n작업 요청\nL2로 작성한다. '+TASK_L2))
    jobs.append((f'final-html-kp-refs-{tag}', m, '작성 지침\n'+SKILL+REFS3+'\n\n작업 요청\nL3로 작성한다. '+TASK_H))
(OUT/'plan-final.json').write_text(json.dumps({'skill_sha256':hashlib.sha256(SKILL.encode()).hexdigest(),'ste_sha256':hashlib.sha256(STE.encode()).hexdigest(),'source_sha256':hashlib.sha256(SRC.encode()).hexdigest(),'models':MODELS,'effort':'medium','jobs':[j[0] for j in jobs]},ensure_ascii=False,indent=1))
with ThreadPoolExecutor(14) as p:
    for r in p.map(lambda j: call(*j), jobs): print(r, flush=True)

