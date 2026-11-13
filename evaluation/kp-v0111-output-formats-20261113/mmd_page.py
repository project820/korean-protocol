import json
from pathlib import Path
D = Path('/Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/output/kp-v0111-probe')
cases = {}
for f in sorted(D.glob('l2-*.mmd.json')):
    for i, m in enumerate(json.loads(f.read_text())): cases[f.name.replace('.mmd.json','')+'#'+str(i)] = m
page = '<!doctype html><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script><body><script>const cases=' + json.dumps(cases, ensure_ascii=False).replace('</','<\\/') + ';const out={};mermaid.initialize({startOnLoad:false});(async()=>{for(const [k,v] of Object.entries(cases)){try{await mermaid.parse(v);out[k]="ok"}catch(e){out[k]="ERR "+String(e.message||e).slice(0,60)}}document.body.textContent=JSON.stringify(out)})();</script>'
(D/'mermaid-parse.html').write_text(page); print(len(cases))

