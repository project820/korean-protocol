import re, json, subprocess, sys
from pathlib import Path
D = Path('/Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/output/kp-v0111-probe/final')
CHK = Path('/Users/m5max/Documents/ChatGPT/ASD-STE100 Kor/skills/korean-protocol/scripts/check_html.py')
F = chr(96)*3
def block(t, lang):
    m = re.findall(re.escape(F)+lang+r'\s*\n(.*?)\n'+re.escape(F), t, re.S)
    return m
rows = {}
for f in sorted(D.glob('html-*.md')):
    t = f.read_text(); m = block(t, 'html'); h = m[0] if m else t
    out = D/(f.stem+'.html'); out.write_text(h)
    j = json.loads(subprocess.run([sys.executable, str(CHK), str(out), '--language', 'ko'], capture_output=True, text=True).stdout or '{}')
    codes = sorted({d['code'] for d in j.get('diagnostics', [])})
    btns = re.findall(r'<button[^>]*>(.*?)</button>', h, re.S)
    calc = [b for b in btns if re.search(r'계산|확인|적용|조회|보기', re.sub('<[^>]+>','',b))] + re.findall(r'type="submit"', h)
    h1 = re.sub('<[^>]+>','', (re.findall(r'<h1[^>]*>(.*?)</h1>', h, re.S) or [''])[0]).strip()
    h2s = [re.sub('<[^>]+>','',x).strip() for x in re.findall(r'<h2[^>]*>(.*?)</h2>', h, re.S)]
    rows[f.stem] = dict(ext=len(re.findall(r'(?:src|href)="https?://', h)), check=j.get('status'), codes=codes,
        result_first='result-after-input' not in codes, calc_btn=len(calc), number_inputs=len(re.findall(r'type="number"', h)),
        radios=len(re.findall(r'type="radio"', h)), selects=len(re.findall(r'<select', h)), panel_layout=('panel_layout' in h),
        h1=h1[:40], h1_handa=bool(re.search(r'다\.?$', h1)), h2_sentence=sum(1 for x in h2s if re.search(r'(한다|된다|있다|없다)\.?$', x)), h2n=len(h2s))
for f in sorted(D.glob('qa-*.md')):
    t = f.read_text()
    rows[f.stem] = dict(mermaid=('Mermaid' in t or 'mermaid' in t), read_files=bool(re.search(r'읽', t)), from_floor=bool(re.search(r'하한', t)),
        innerHTML=('innerHTML' in t), check_html=('check_html' in t))
for f in sorted(D.glob('l2-*.md')):
    t = f.read_text(); ms = block(t, 'mermaid')
    bad = []
    for m in ms:
        for line in m.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith(('subgraph','end','%%','direction')): continue
            for node in re.findall(r'\b([A-Za-z0-9_]+)\s*[\[\{\(]', line):
                if not re.fullmatch(r'[A-Z][A-Z0-9]*', node): bad.append('id:'+node)
            for lab in re.findall(r'[\[\{\(]+([^\]\}\)]*)[\]\}\)]+', line):
                if not (lab.startswith('"') and lab.endswith('"')): bad.append('label:'+lab[:15])
            for el in re.findall(r'\|([^|]*)\|', line):
                if not (el.startswith('"') and el.endswith('"')): bad.append('edge:'+el[:15])
            if re.search(r'\b(style|classDef|linkStyle|click)\b', line): bad.append('style')
    rows[f.stem] = dict(mermaid_blocks=len(ms), table=bool(re.search(r'^\|.*\|\s*$', t, re.M)), syntax_issues=len(bad), sample=bad[:4], chars=len(t))
    (D/(f.stem+'.mmd.json')).write_text(json.dumps(ms, ensure_ascii=False))
(D/'score.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
for k,v in rows.items(): print(k, json.dumps(v, ensure_ascii=False))

