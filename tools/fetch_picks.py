#!/usr/bin/env python3
"""Download the picked photos again at a higher resolution, because a reel crops them to 9:16."""
import json, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
s = requests.Session()
s.headers.update({'User-Agent': 'CompassUniSocialBot/1.0 (https://compassuni.com; social media asset builder)'})
pick = json.load(open(ROOT / 'data/visual_pick.json'))
ph = {p['path']: p for u in json.load(open(ROOT / 'data/unis.json')) for p in u['photos']}
for slug, names in pick.items():
    for n in names:
        p = ph[f'assets/photos/{n}.jpg']
        for a in range(5):
            r = s.get('https://commons.wikimedia.org/w/api.php', params=dict(action='query', format='json', titles=f"File:{p['file']}", prop='imageinfo', iiprop='url|size', iiurlwidth=2800), timeout=40)
            if r.status_code == 200:
                break
            time.sleep(5 * (a + 1))
        for pg in r.json().get('query', {}).get('pages', {}).values():
            ii = (pg.get('imageinfo') or [{}])[0]
            url = ii.get('thumburl') or ii.get('url')
            if url:
                img = s.get(url, timeout=90)
                if img.status_code == 200 and len(img.content) > 30000:
                    (ROOT / p['path']).write_bytes(img.content)
                    print(n, len(img.content) // 1024, 'KB', flush=True)
        time.sleep(0.3)
