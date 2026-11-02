#!/usr/bin/env python3
"""Render one post for a queued industry and write its caption.
usage: make_industry.py <slug> carousel|reel YYYY-MM-DD <copy.json>
copy.json: {"hook": "...", "items": [["Title", "One line of advice"], ...3 or 4 items]}"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wa_media as w


def main(slug, fmt, date, copy_path):
    q = json.load(open(w.ROOT / 'data/industry_queue.json'))
    ind = next(x for x in q['industries'] if x['slug'] == slug)
    c = json.load(open(copy_path))
    items = [tuple(i) for i in c['items']]
    out = w.ROOT / 'posts' / f'{date}-{slug}-{fmt}'
    with w.Shooter() as sh:
        if fmt == 'carousel':
            n = w.industry_carousel(sh, ind, items, out, c['hook'])
            print('slides', n)
        else:
            print('seconds', w.industry_reel(sh, ind, items, out, c['hook']))
    lines = '\n'.join(f'{i + 1}. {t}' for i, (t, _) in enumerate(items))
    cap = f"{c['hook']}\n\nWhat a {ind['singular']} website needs:\n{lines}\n\n📌 Save this for when you update your site.\n\n{w.CTA}\n\n{w.TAGS}"
    (out / 'caption.txt').write_text(cap, encoding='utf-8')
    (out / 'title.txt').write_text(f"What a {ind['singular']} website needs", encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main(*sys.argv[1:5])
