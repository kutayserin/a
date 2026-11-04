#!/usr/bin/env python3
"""Fetch freely licensed campus photos for data/universities.json from Wikipedia and Commons.
Runs in GitHub Actions, where Wikimedia is reachable. Writes data/unis.json and assets/photos/."""
import html, json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'CompassUniSocialBot/1.0 (https://compassuni.com; social media asset builder)'}
OK_LICENSE = re.compile(r'^(cc0|cc[ -]by|fal|free art|public domain|pd\b|attribution)', re.I)
SKIP = re.compile(r'(map|plan\b|logo|icon|flag|coat|seal|crest|emblem|wappen|locator|diagram|symbol|signature|portrait|nobel|president|'
                  r'chancellor|professor|rector|bust|medal|team|football|basketball|mascot|graph|chart|\.svg|\.png|\.gif|\.tif)', re.I)
s = requests.Session()
s.headers.update(UA)
W = 'https://en.wikipedia.org/w/api.php'


def get(url, **params):
    for attempt in range(6):
        r = s.get(url, params=params or None, timeout=40)
        if r.status_code in (429, 503):
            time.sleep(5 * (attempt + 1))
            continue
        return r
    return r


def info(filename):
    r = get('https://commons.wikimedia.org/w/api.php', action='query', format='json', titles=f'File:{filename}',
            prop='imageinfo', iiprop='url|extmetadata|size', iiurlwidth=1600)
    for page in r.json().get('query', {}).get('pages', {}).values():
        if int(page.get('pageid', -1)) < 0 or 'imageinfo' not in page:
            return None
        ii = page['imageinfo'][0]
        meta = ii.get('extmetadata', {})
        lic = meta.get('LicenseShortName', {}).get('value', '')
        artist = html.unescape(re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value', ''))).strip()
        artist = re.sub(r'\s+', ' ', artist) or html.unescape(re.sub(r'<[^>]+>', '', meta.get('Credit', {}).get('value', ''))).strip()
        return dict(file=filename, license=lic, artist=artist[:70], width=ii.get('width', 0), height=ii.get('height', 0),
                    thumb=ii.get('thumburl') or ii.get('url'), source=ii.get('descriptionurl', ''))
    return None


def usable(i):
    return bool(i and OK_LICENSE.match(i['license'] or '') and i['artist'] and i['width'] >= 1400 and i['width'] >= i['height'] * 0.6)


def names(title):
    r = get(W, action='query', format='json', titles=title, prop='images|pageimages', piprop='name', imlimit=80, redirects=1)
    out, lead = [], None
    for page in r.json().get('query', {}).get('pages', {}).values():
        if int(page.get('pageid', -1)) < 0:
            return None, []
        lead = page.get('pageimage')
        out += [i['title'].split(':', 1)[1] for i in page.get('images', [])]
    return lead, out


def main():
    out = []
    (ROOT / 'assets/photos').mkdir(parents=True, exist_ok=True)
    for u in json.load(open(ROOT / 'data/universities.json')):
        lead, files = names(u['name'])
        if lead is None and not files:
            r = get(W, action='query', format='json', list='search', srsearch=f"{u['name']} university {u['city']}", srlimit=1)
            hits = r.json().get('query', {}).get('search', [])
            if hits:
                u['title'] = hits[0]['title']
                lead, files = names(hits[0]['title'])
        order = ([lead.replace('_', ' ')] if lead else []) + [f for f in files if f.replace('_', ' ') != (lead or '').replace('_', ' ')]
        photos = []
        for f in order:
            if len(photos) >= 6:
                break
            if SKIP.search(f) or not re.search(r'\.jpe?g$', f, re.I):
                continue
            i = info(f)
            time.sleep(0.15)
            if not usable(i):
                continue
            path = ROOT / 'assets/photos' / f"{u['slug']}-{len(photos) + 1}.jpg"
            img = s.get(i['thumb'], timeout=60)
            if img.status_code != 200 or len(img.content) < 30000:
                continue
            path.write_bytes(img.content)
            i.pop('thumb')
            i['path'] = f'assets/photos/{path.name}'
            photos.append(i)
        u['photos'] = photos
        out.append(u)
        print(u['slug'], len(photos), flush=True)
        (ROOT / 'data/unis.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print('done', sum(len(u['photos']) for u in out), 'photos', sum(1 for u in out if not u['photos']), 'without')


if __name__ == '__main__':
    main()
