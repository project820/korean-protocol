#!/usr/bin/env python3
"""kp_lint: Korean Protocol 문체 검사기 (파일럿 후보).

사용: kp_lint.py OUTPUT.md [--source SOURCE.txt] [--mode rewrite|compose] [--json]
의미 보존은 검사하지 않는다. 셀 수 있는 문체 규칙만 검사한다.
"""
import argparse, json, re, sys

MAX_WORDS = 12
MAX_PARA = 3
MAX_ITEM = 2
FENCE = chr(96) * 3
NOTICE = re.compile(r'(아닙니다|아니다|아님|아니며|아니므로)[.)”"]*$|뜻하지 않|의미하지 않|대신하지 않|볼 수 없|참고(만|용|로만)|단정할 수 없|확정할 수 없|보장하지 않')
FUSED = re.compile(r'(이며|이고|이지만|으나|지만|으며|,)\s[^.]*?(아니다|아닙니다|볼 수 없다|볼 수 없습니다|뜻하지 않는다|뜻하지 않습니다|대신하지 않는다|대신하지 않습니다)[.]?$|(?<!뿐 )(?<!뿐만 )아니라[ ,]')
DOUBLE = re.compile(r'(않으면|없으면|아니면|없이는|않고는|않는 한)[^.]*?(없다|없습니다|않는다|않습니다|못한다|못합니다|안 된다|안 됩니다)')
PREVIEW = re.compile(r'(다음|아래)과 같(다|습니다)|(아래|부록|뒤)에 (제시|정리|설명)(한다|합니다|했다|했습니다)|살펴보면')
NEGNP = re.compile(r'((?:\S+\s){0,2}\S+?)(?:이|가|은|는|도)?\s(?:아닙니다|아니다|아니라|아니며|아니고|아닌|아님)')
NUM = re.compile(r'\d[\d,]*(?:\.\d+)?')
SENT = re.compile(r'(?<=[.?!])\s+(?=[가-힣A-Z0-9“"‘\'\[(「])')


def sentences(text):
    out = []
    for piece in SENT.split(text.strip()):
        if out and re.search(r'(^|\s)[A-Za-z0-9]{1,4}\.$', out[-1]):
            out[-1] += ' ' + piece
        elif len(piece) > 1:
            out.append(piece)
    return out


def unquoted(s):
    return re.sub(r'[“"「‘\'][^”"」’\']*[”"」’\']', '', s)


def parse(text):
    """본문을 구획(section) 안의 블록으로 나눈다. 블록 종류: para, item, cell, quote."""
    blocks, code, section = [], False, 0
    for no, raw in enumerate(text.split('\n'), 1):
        s = raw.strip()
        if s.startswith(FENCE):
            code = not code
            continue
        if code or not s:
            if not s and blocks:
                blocks[-1]['closed'] = True
            continue
        if s.startswith('#') or re.fullmatch(r'\*\*[^*]+\*\*:?', s):
            section += 1
            continue
        if s.startswith('|'):
            for cell in s.strip('|').split('|'):
                cell = cell.strip()
                if cell and not set(cell) <= set('-: '):
                    blocks.append(dict(kind='cell', line=no, section=section, text=cell, closed=True))
            continue
        quote = s.startswith('>')
        if quote:
            s = s.lstrip('> ').strip()
            if not s:
                continue
        m = re.match(r'([-*•]|\d+[.)])\s+', s)
        if m:
            blocks.append(dict(kind='item', line=no, section=section, text=s[m.end():], closed=False))
        elif quote:
            blocks.append(dict(kind='quote', line=no, section=section, text=s, closed=True))
        elif blocks and blocks[-1]['kind'] in ('para', 'item') and not blocks[-1]['closed']:
            blocks[-1]['text'] += ' ' + s
        else:
            blocks.append(dict(kind='para', line=no, section=section, text=s, closed=False))
    for b in blocks:
        b['sents'] = sentences(b['text']) or [b['text']]
    return blocks


def exempt_length(s):
    return bool(re.search(r'[“"「].+[”"」]', s)) or len(NUM.findall(s)) >= 3 or re.match(r'(근거|출처)\s*[:：]', s) is not None


def enum_items(s):
    chain = max((m.group(0).count('·') + 1 for m in re.finditer(r'[^\s·,]+(?:·[^\s·,]+)+', s)), default=0)
    commas = s.count(', ') + 1 if s.count(', ') >= 2 else 0
    return max(chain, commas)


def stem(w):
    w = re.sub(r'[“”"\'‘’()\[\],.*]', '', w)
    return re.sub(r'(으로|에서|에게|까지|부터|이나|이며|이고|은|는|이|가|을|를|의|도|만|와|과|로|에)$', '', w)


def lint(text, source=None, mode=None):
    blocks = parse(text)
    v = []

    def add(rule, b, s, note=''):
        v.append(dict(rule=rule, line=b['line'], text=s[:90], note=note))

    by_section = {}
    for b in blocks:
        by_section.setdefault(b['section'], []).append(b)
    blocks = [b for b in blocks if b['kind'] != 'quote']
    for b in blocks:
        ss = b['sents']
        for s in ss:
            words = len(s.split())
            if words > MAX_WORDS and not exempt_length(s):
                add('긴문장', b, s, f'{words}어절')
            n = enum_items(s)
            if b['kind'] != 'cell' and len(NUM.findall(s)) < 3 and (n >= 4 or (n == 3 and words > 10)):
                add('가로나열', b, s, f'{enum_items(s)}항목')
            if FUSED.search(s):
                add('부정결합', b, s)
            if DOUBLE.search(s):
                add('이중부정', b, s)
            if PREVIEW.search(unquoted(s)):
                add('예고문장', b, s)
            if source is not None:
                for m in NEGNP.finditer(s):
                    keys = [k for k in (stem(w) for w in m.group(1).split()) if len(k) >= 2]
                    if keys and keys[-1][:2] not in source:
                        add('원문밖부정', b, s, keys[-1])
        if b['kind'] == 'para' and len(ss) > MAX_PARA:
            add('긴문단', b, b['text'], f'{len(ss)}문장')
        if b['kind'] == 'item' and len(ss) > MAX_ITEM:
            add('긴항목', b, b['text'], f'{len(ss)}문장')
        if b['kind'] != 'cell' and len(ss) >= 2 and NOTICE.search(ss[-1].rstrip()):
            add('말미고지', b, ss[-1], '블록 끝')
    for sec in by_section.values():
        body = [b for b in sec if b['kind'] != 'cell']
        for i, b in enumerate(body):
            if len(body) >= 3 and i >= 1 and len(b['sents']) == 1 and NOTICE.search(b['sents'][0].rstrip()) and i == len(body) - 1:
                add('말미고지', b, b['sents'][0], '구획 끝')
    all_s = [s for b in blocks for s in b['sents']]
    stats = dict(chars=len(text), sentences=len(all_s),
                 mean_words=round(sum(len(s.split()) for s in all_s) / max(1, len(all_s)), 1),
                 notices=sum(1 for s in all_s if NOTICE.search(s.rstrip())))
    if source is not None:
        nums = {n for n in NUM.findall(source) if len(n) >= 2}
        missing = sorted(n for n in nums if n not in text)
        stats['length_ratio'] = round(len(text) / max(1, len(source)), 2)
        stats['numbers_kept'] = f'{len(nums) - len(missing)}/{len(nums)}'
        stats['numbers_missing'] = missing[:20]
        if mode == 'rewrite' and len(text) > len(source):
            v.append(dict(rule='길이초과', line=0, text='', note=f"원문의 {stats['length_ratio']}배"))
    counts = {}
    for x in v:
        counts[x['rule']] = counts.get(x['rule'], 0) + 1
    return dict(stats=stats, counts=counts, violations=v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    ap.add_argument('--source')
    ap.add_argument('--mode', choices=['rewrite', 'compose'])
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    text = open(a.output, encoding='utf-8').read()
    source = open(a.source, encoding='utf-8').read() if a.source else None
    r = lint(text, source, a.mode)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print('통계:', json.dumps(r['stats'], ensure_ascii=False))
        print('위반:', json.dumps(r['counts'], ensure_ascii=False) if r['counts'] else '없음')
        for x in r['violations']:
            print(f"  {x['line']:>4}행 [{x['rule']}] {x['note']} | {x['text']}")
    return 1 if r['violations'] else 0


if __name__ == '__main__':
    sys.exit(main())

