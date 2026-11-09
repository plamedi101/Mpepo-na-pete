#!/usr/bin/env python3
"""Liste les segments français qui n'ont pas encore de traduction.
Usage : python3 extract.py <racine> <sortie.txt> page1 [page2 …]   (le dictionnaire translations.json est lu s'il existe)"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18nlib import *

root, out, pages = sys.argv[1], sys.argv[2], sys.argv[3:]
memo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations.json')
memo = json.load(open(memo_path, encoding='utf-8')) if os.path.exists(memo_path) else {}

def page_segments(doc):
    segs = []
    for u in find_units(doc):
        segs.append((u.node.s, 'texte', u.key, u.node.tag))
    for i, t in enumerate(doc.toks):
        if t[0] in ('start', 'startend'):
            for s in start_tag_attr_segments(doc.raw(i), t[2]):
                segs.append((i, 'attr', norm(s), t[2]))
    segs.sort(key=lambda x: x[0])
    return segs

seen = set(memo)
lines, order = [], []
n = 0
for p in pages:
    doc = Doc(open(os.path.join(root, p), encoding='utf-8').read())
    lines.append(f'##### {p}')
    for _, kind, key, tag in page_segments(doc):
        if key in seen:
            continue
        seen.add(key)
        n += 1
        order.append(key)
        lines.append(f'{n}. [{tag}{"/attr" if kind=="attr" else ""}] {key}')
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
json.dump(order, open(out + '.order.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(n, 'segments à traduire ->', out)
