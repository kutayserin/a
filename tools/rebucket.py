#!/usr/bin/env python3
"""Re-bucket calendar rows from START onwards into PER_DAY posts a day at SLOTS.
Usage: python3 rebucket.py REPO_DIR START SLOTS [--write]
Prints the plan; with --write rewrites calendar/<date>.json and index.json."""
import json, os, re, sys, datetime as dt
repo, start, slots = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
write = '--write' in sys.argv
cal = os.path.join(repo, 'calendar')
files = sorted(f for f in os.listdir(cal) if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', f))
rows = []
for f in files:
    if f[:10] >= start:
        rows += json.load(open(os.path.join(cal, f), encoding='utf-8'))
rows.sort(key=lambda r: r['date'])
old_dates = {id(r): r['date'] for r in rows}
day = dt.date.fromisoformat(start)
plan = {}
for i, r in enumerate(rows):
    d = (day + dt.timedelta(days=i // len(slots))).isoformat()
    hhmm = slots[i % len(slots)]
    off = r['date'][19:]
    r['date'] = f'{d}T{hhmm}:00{off}'
    if 'slot' in r: r['slot'] = f'{d}T{hhmm}'
    r['info']['publicationDate']['dateTime'] = f'{d}T{hhmm}:00'
    plan.setdefault(d, []).append(r)
print('rows', len(rows), 'days', len(plan), 'from', min(plan), 'to', max(plan))
# time-sensitive check: dates mentioned in text that fall between old and new publish date
MONTHS = {m: i for i, m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'], 1)}
pat = re.compile(r'\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December)(?: (\d{4}))?', re.I)
for d, rs in plan.items():
    for r in rs:
        text = r['info'].get('text', '')
        for m in pat.finditer(text):
            y = int(m.group(3) or 2026); mo = MONTHS[m.group(2).lower()]
            try: when = dt.date(y, mo, int(m.group(1)))
            except ValueError: continue
            new = dt.date.fromisoformat(d)
            if dt.date(2026, 11, 9) <= when < new + dt.timedelta(days=3):
                print('  CHECK', d, r.get('folder'), '| mentions', when, '|', text.split('\n')[0][:80])
if write:
    for f in files:
        if f[:10] >= start:
            os.remove(os.path.join(cal, f))
    for d, rs in plan.items():
        with open(os.path.join(cal, f'{d}.json'), 'w', encoding='utf-8') as fh:
            json.dump(rs, fh, ensure_ascii=False, indent=1); fh.write('\n')
    idx_p = os.path.join(cal, 'index.json')
    idx = json.load(open(idx_p, encoding='utf-8'))
    all_files = sorted(f for f in os.listdir(cal) if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', f))
    idx['last'] = all_files[-1][:10]
    idx['days'] = len(all_files)
    idx['posts'] = sum(len(json.load(open(os.path.join(cal, f), encoding='utf-8'))) for f in all_files)
    json.dump(idx, open(idx_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0); open(idx_p, 'a').write('\n')
    print('written; index', idx)
