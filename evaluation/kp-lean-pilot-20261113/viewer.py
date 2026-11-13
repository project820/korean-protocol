#!/usr/bin/env python3
"""가린 비교 화면을 만든다. 원문과 네 출력을 나란히 보여 주고, 이름은 버튼을 눌러야 보인다."""
import html, json, random, re
from pathlib import Path
import pilot
ROOT=pilot.ROOT
ARMS={'kp':'KP 현행 v0.10.1','ste':'STE 대조군','candfix':'후보 1 + 검사기','v2fix':'후보 2 + 검사기'}
CASE_NAME={'P1':'전원 차단 절차','P2':'공조 견적 보고','P3':'작업 결과 보고','P4':'설비 점검 보고'}
def inline(s):
    s=html.escape(s); s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s); return re.sub(chr(96)+r'(.+?)'+chr(96),r'<code>\1</code>',s)
def render(md):
    out=[]; lines=md.split('\n'); i=0; depth=[]
    def close(to=0):
        while len(depth)>to: out.append('</'+depth.pop()[1]+'>')
    while i<len(lines):
        l=lines[i]; s=l.strip()
        if not s: close(); i+=1; continue
        if s.startswith('|'):
            close(); rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(set(c)<=set('-: ') for c in cells): rows.append(cells)
                i+=1
            out.append('<table>'+''.join('<tr>'+''.join(('<th>' if n==0 else '<td>')+inline(c)+('</th>' if n==0 else '</td>') for c in r)+'</tr>' for n,r in enumerate(rows))+'</table>'); continue
        m=re.match(r'(#{1,4})\s+(.*)',s)
        if m: close(); out.append(f'<h{len(m.group(1))+2}>'+inline(m.group(2))+f'</h{len(m.group(1))+2}>'); i+=1; continue
        m=re.match(r'(\s*)([-*•]|\d+[.)])\s+(.*)',l)
        if m:
            ind=len(m.group(1)); tag='ol' if m.group(2)[0].isdigit() else 'ul'
            while depth and depth[-1][0]>ind: out.append('</'+depth.pop()[1]+'>')
            if not depth or depth[-1][0]<ind: depth.append((ind,tag)); out.append('<'+tag+'>')
            out.append('<li>'+inline(m.group(3))+'</li>'); i+=1; continue
        if depth and l.startswith(' '): out.append('<div class="cont">'+inline(s)+'</div>'); i+=1; continue
        close(); out.append('<p>'+inline(s.lstrip('> '))+'</p>'); i+=1
    close(); return '\n'.join(out)
panels=[]; nav=[]
for c in [x for x in pilot.CASES if x['id'] in CASE_NAME]:
    for tag,model in zip(pilot.TAG,pilot.MODELS):
        pid=f"{c['id']}-{tag}"; arms=list(ARMS); random.Random(pid).shuffle(arms)
        cols=[]
        for label,a in zip('가나다라',arms):
            t=(ROOT/'runs'/f'{pid}-{a}'/'output.md').read_text()
            cols.append(f'<section class="col"><h2>{label} <span class="name" hidden>{ARMS[a]}</span> <small>{len(t):,}자</small></h2>{render(t)}</section>')
        nav.append(f'<option value="{pid}">{CASE_NAME[c["id"]]} · {model.split("/")[-1]}</option>')
        panels.append(f'<article id="{pid}" hidden><details><summary>요청과 원문 ({len(c["source"]):,}자)</summary><p><b>요청:</b> {html.escape(c["task"])}</p><pre>{html.escape(c["source"])}</pre></details><div class="cols">{"".join(cols)}</div></article>')
page=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KP 문체 파일럿 가린 비교</title>
<style>
body{{font:15px/1.65 -apple-system,"Apple SD Gothic Neo",sans-serif;margin:0;color:#1b1b1b;background:#f5f5f3}}
header{{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}}
select,button{{font:inherit;padding:6px 10px}}
main{{padding:16px}} details{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 14px;margin-bottom:14px}}
pre{{white-space:pre-wrap;font:13px/1.6 ui-monospace,monospace}}
.cols{{display:grid;grid-template-columns:repeat(4,minmax(300px,1fr));gap:12px;overflow-x:auto}}
.col{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px 16px;min-width:300px}}
.col h2{{font-size:17px;margin:0 0 8px;border-bottom:2px solid #222;padding-bottom:6px}} .col h2 small{{font-weight:400;color:#777;font-size:12px}}
.name{{color:#b3261e;font-size:14px}} h3,h4,h5,h6{{margin:14px 0 6px;font-size:15px}}
table{{border-collapse:collapse;font-size:13px;margin:8px 0}} th,td{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left}} th{{background:#f0f0ee}}
ul,ol{{padding-left:22px;margin:6px 0}} p{{margin:8px 0}} .cont{{margin-left:22px}}
</style>
<header><b>KP 문체 파일럿</b><select id="pick">{"".join(nav)}</select><button id="reveal">이름 보기</button><span>네 칸의 순서는 화면마다 섞여 있다.</span></header>
<main>{"".join(panels)}</main>
<script>
const pick=document.getElementById('pick');
function show(){{document.querySelectorAll('article').forEach(a=>a.hidden=a.id!==pick.value);document.querySelectorAll('.name').forEach(n=>n.hidden=true);}}
pick.onchange=show;document.getElementById('reveal').onclick=()=>document.querySelectorAll('article:not([hidden]) .name').forEach(n=>n.hidden=!n.hidden);show();
</script></html>'''
(ROOT/'viewer.html').write_text(page); print('viewer', len(page))


PAIRS=[('P3','sol','kp','cand','작업 결과 보고: 하지 않은 일을 어디에 두는가'),
       ('P3','sonnet','kp','cand','작업 결과 보고: 다른 모델의 같은 비교'),
       ('P1','terra','kp','cand','전원 차단 절차: 옆 차단기 설명이 있는 쪽과 없는 쪽'),
       ('P2','sonnet','ste','v2fix','공조 견적 보고: 문서 고지의 위치'),
       ('P4','sol','kp','candfix','설비 점검 보고: 문장 길이와 목록')]
NAMES={**ARMS,'cand':'후보 1'}
panels=[]; nav=[]
for n,(cid,tag,a,b,title) in enumerate(PAIRS,1):
    c=[x for x in pilot.CASES if x['id']==cid][0]; arms=[a,b]; random.Random(f'pair{n}').shuffle(arms); cols=[]
    for label,arm in zip('가나',arms):
        t=(ROOT/'runs'/f'{cid}-{tag}-{arm}'/'output.md').read_text()
        cols.append(f'<section class="col"><h2>{label} <span class="name" hidden>{NAMES[arm]}</span> <small>{len(t):,}자</small></h2>{render(t)}</section>')
    nav.append(f'<option value="pair{n}">{n}. {title}</option>')
    panels.append(f'<article id="pair{n}" hidden><details><summary>요청과 원문 ({len(c["source"]):,}자)</summary><p><b>요청:</b> {html.escape(c["task"])}</p><pre>{html.escape(c["source"])}</pre></details><div class="cols">{"".join(cols)}</div></article>')
head,rest=page.split('<header>',1); tail=rest.split('</main>',1)[1]
page2=head.replace('repeat(4,minmax(300px,1fr))','repeat(2,minmax(320px,1fr))')+'<header><b>KP 문체 파일럿: 다섯 쌍 비교</b><select id="pick">'+''.join(nav)+'</select><button id="reveal">이름 보기</button><span>가와 나 중 읽기 편한 쪽을 고른다. 순서는 쌍마다 섞여 있다.</span></header><main>'+''.join(panels)+'</main>'+tail
(ROOT/'viewer-pairs.html').write_text(page2); print('pairs', len(page2))

