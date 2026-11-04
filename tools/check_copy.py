#!/usr/bin/env python3
"""Mechanical checks on data/spotlights.json against data/landmarks.json."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
L = {x['slug']: x for x in json.load(open(ROOT / 'data/landmarks.json'))}
C = json.load(open(ROOT / 'data/spotlights.json'))
F = json.load(open(ROOT / 'data/facts.json')) if (ROOT / 'data/facts.json').exists() else {}
bad, seen = [], {}
for c in C:
    s = c.get('slug')
    if s not in L:
        bad.append(f'{s}: unknown slug'); continue
    if s in seen:
        bad.append(f'{s}: duplicate')
    seen[s] = 1
    x = L[s]
    src = (x['extract'] + ' ' + F.get(s, '') + ' ' + x['description'] + ' ' + x['name'] + ' ' + x['city'] + ' ' + x['title']).lower()
    for k, lim in dict(hook=60, fact=120, title=70).items():
        v = c.get(k, '')
        if not v:
            bad.append(f'{s}: empty {k}')
        if len(v) > lim:
            bad.append(f'{s}: {k} is {len(v)} chars, limit {lim}')
        if '—' in v or '–' in v:
            bad.append(f'{s}: dash in {k}')
    for k in ('hook', 'fact', 'title'):
        for num in re.findall(r'\d[\d,.]*\d|\d', c.get(k, '')):
            n = num.replace(',', '')
            if n not in src.replace(',', ''):
                bad.append(f'{s}: {k} has number {num} not in the extract')
    if not re.fullmatch(r'[a-z0-9]+', c.get('tag', '')):
        bad.append(f'{s}: bad tag {c.get("tag")}')
missing = [k for k in L if k not in seen]
if missing:
    bad.append(f'missing {len(missing)}: {missing[:20]}')
hooks = [c.get('hook', '').split()[0].lower() for c in C if c.get('hook')]
top = max(set(hooks), key=hooks.count) if hooks else ''
print(f'{len(C)} entries, {len(bad)} problems; most common first word: {top} x{hooks.count(top)}')
print('\n'.join(bad))
sys.exit(1 if bad else 0)
