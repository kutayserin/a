#!/usr/bin/env python3
"""Longer plain-text source for each landmark, so thin intros still give real details.
Writes data/facts.json: slug -> first part of the English Wikipedia article."""
import json, re, time, unicodedata
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
s = requests.Session()
s.headers['User-Agent'] = 'TravelhourSocialBot/1.0 (https://travelhour.app; social media asset builder)'


def slug(text):
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


out = {}
for item in json.load(open(ROOT / 'data/landmark_titles.json')):
    title = item.get('title') or item['name']
    for attempt in range(5):
        r = s.get('https://en.wikipedia.org/w/api.php', params=dict(action='query', format='json', prop='extracts', explaintext=1,
                  redirects=1, titles=title), timeout=40)
        if r.status_code == 200:
            break
        time.sleep(5 * (attempt + 1))
    pages = r.json().get('query', {}).get('pages', {})
    text = next(iter(pages.values())).get('extract', '') if pages else ''
    text = re.split(r'\n==\s*(See also|References|Notes|External links|Bibliography|Further reading)\s*==', text)[0]
    out[slug(f"{item['city']}-{item['name']}")] = text[:7000]
    print(item['name'], len(text), flush=True)
    time.sleep(0.3)
(ROOT / 'data/facts.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
