#!/usr/bin/env python3
"""Add Pexels footage of each landmark on top of what data/landmarks.json already has."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_landmarks as f

ROOT = f.ROOT
key = os.environ.get('PEXELS_API_KEY')
print('pexels key present:', bool(key), flush=True)
if not key:
    sys.exit(0)
L = json.load(open(ROOT / 'data/landmarks.json'))
clips = ROOT / 'assets/clips'
clips.mkdir(parents=True, exist_ok=True)
total = 0
for x in L:
    try:
        got = f.pexels_clips(x['name'], x['city'], x['slug'] + '-p', clips)
    except Exception as e:
        print('failed', x['name'], e, flush=True)
        got = []
    x['clips'] = got + [c for c in (x.get('clips') or []) if c['license'] != 'Pexels License']
    total += len(got)
    print(x['city'], x['name'], len(got), flush=True)
    time.sleep(1.0)
(ROOT / 'data/landmarks.json').write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
print('pexels clips added', total)
