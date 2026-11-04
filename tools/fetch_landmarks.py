#!/usr/bin/env python3
"""Fetch facts, coordinates and a freely licensed photo for every landmark in
data/landmark_titles.json. Runs in GitHub Actions, where Wikimedia is reachable.
Writes data/landmarks.json and assets/photos/<slug>.jpg."""
import html, json, math, re, subprocess, sys, tempfile, time, unicodedata, urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'TravelhourSocialBot/1.0 (https://travelhour.app; social media asset builder)'}
OK_LICENSE = re.compile(r'^(cc0|cc[ -]by|fal|free art|public domain|pd\b|attribution)', re.I)
SKIP_FILE = re.compile(r'(map|plan|logo|icon|flag|coat|seal|locator|diagram|symbol|\.svg|\.png|\.gif|\.tif)', re.I)
s = requests.Session()
s.headers.update(UA)


def get(url, **params):
    for attempt in range(6):
        r = s.get(url, params=params or None, timeout=40)
        if r.status_code in (429, 503):
            time.sleep(5 * (attempt + 1))
            continue
        return r
    return r


def slug(text):
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


def hav(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def commons_info(filename):
    r = get('https://commons.wikimedia.org/w/api.php', action='query', format='json', titles=f'File:{filename}',
            prop='imageinfo', iiprop='url|extmetadata|size', iiurlwidth=1920)
    for page in r.json().get('query', {}).get('pages', {}).values():
        if int(page.get('pageid', -1)) < 0 or 'imageinfo' not in page:
            return None
        ii = page['imageinfo'][0]
        meta = ii.get('extmetadata', {})
        lic = meta.get('LicenseShortName', {}).get('value', '')
        artist = html.unescape(re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value', ''))).strip()
        artist = re.sub(r'\s+', ' ', artist)
        if meta.get('Credit', {}).get('value') and not artist:
            artist = html.unescape(re.sub(r'<[^>]+>', '', meta['Credit']['value'])).strip()
        return dict(file=filename, license=lic, artist=artist[:70], width=ii.get('width', 0), height=ii.get('height', 0),
                    thumb=ii.get('thumburl') or ii.get('url'), page=ii.get('descriptionurl', ''))
    return None


def usable(info, min_w=1200):
    return bool(info and OK_LICENSE.match(info['license'] or '') and info['artist'] and info['width'] >= min_w
                and info['width'] >= info['height'] * 0.6)


def pick_photo(title, lead, forced=None):
    if forced:
        info = commons_info(forced)
        if info and OK_LICENSE.match(info['license'] or ''):
            return info
    if lead:
        info = commons_info(lead)
        if usable(info):
            return info
    r = get('https://en.wikipedia.org/w/api.php', action='query', format='json', titles=title, prop='images',
            imlimit=60, redirects=1)
    names = []
    for page in r.json().get('query', {}).get('pages', {}).values():
        names += [i['title'].split(':', 1)[1] for i in page.get('images', [])]
    for n in names:
        if SKIP_FILE.search(n) or not re.search(r'\.jpe?g$', n, re.I):
            continue
        info = commons_info(n)
        if usable(info, 1600):
            return info
        time.sleep(0.2)
    return None


def extra_photos(title, used, limit=4):
    """More freely licensed photos of the same landmark, for quick cuts in the reel."""
    r = get('https://en.wikipedia.org/w/api.php', action='query', format='json', titles=title, prop='images',
            imlimit=80, redirects=1)
    names = []
    for page in r.json().get('query', {}).get('pages', {}).values():
        names += [i['title'].split(':', 1)[1] for i in page.get('images', [])]
    found = []
    for n in names:
        if len(found) >= limit:
            break
        if n == used or SKIP_FILE.search(n) or not re.search(r'\.jpe?g$', n, re.I):
            continue
        info = commons_info(n)
        if usable(info, 1600):
            found.append(info)
        time.sleep(0.15)
    return found


def find_clip(title, city, out_mp4):
    """A short clip from the best freely licensed Commons video of this landmark."""
    q = f'"{title.split(",")[0]}" {city} filetype:video'
    r = get('https://commons.wikimedia.org/w/api.php', action='query', format='json', list='search', srnamespace=6,
            srsearch=q, srlimit=8)
    for hit in r.json().get('query', {}).get('search', []):
        name = hit['title'].split(':', 1)[1]
        v = get('https://commons.wikimedia.org/w/api.php', action='query', format='json', titles=f'File:{name}',
                prop='videoinfo', viprop='url|size|extmetadata|derivatives|mediatype')
        for page in v.json().get('query', {}).get('pages', {}).values():
            if not page.get('videoinfo'):
                continue
            vi = page['videoinfo'][0]
            meta = vi.get('extmetadata', {})
            lic = meta.get('LicenseShortName', {}).get('value', '')
            artist = html.unescape(re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value', ''))).strip()
            dur = float(vi.get('duration') or 0)
            if not OK_LICENSE.match(lic or '') or not artist or vi.get('width', 0) < 1280 or not 8 <= dur <= 900:
                continue
            ders = [d for d in vi.get('derivatives', []) if d.get('type', '').startswith('video/')
                    and 720 <= int(d.get('height') or 0) <= 1080]
            ders.sort(key=lambda d: -int(d.get('height') or 0))
            src = ders[0]['src'] if ders else vi.get('url')
            if int(vi.get('size') or 0) > 900_000_000 and not ders:
                continue
            tmp = Path(tempfile.mkdtemp()) / 'v'
            with get_stream(src) as resp:
                if resp.status_code != 200:
                    continue
                with open(tmp, 'wb') as fh:
                    got = 0
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)
                        got += len(chunk)
                        if got > 400_000_000:
                            break
            start = max(2.0, dur * 0.2)
            vf = 'crop=if(gt(iw/ih\\,9/16)\\,ih*9/16\\,iw):if(gt(iw/ih\\,9/16)\\,ih\\,iw*16/9),scale=1080:1920,fps=30,format=yuv420p'
            cp = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{start:.1f}', '-t', '7', '-i', str(tmp), '-an', '-vf', vf,
                                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', str(out_mp4)], capture_output=True)
            tmp.unlink(missing_ok=True)
            if cp.returncode or not out_mp4.exists() or out_mp4.stat().st_size < 100000:
                out_mp4.unlink(missing_ok=True)
                continue
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '3', '-i', str(out_mp4), '-frames:v', '1', '-q:v', '3',
                            str(out_mp4.with_suffix('.jpg'))], capture_output=True)
            return dict(path=str(out_mp4.relative_to(ROOT)), artist=re.sub(r'\s+', ' ', artist)[:70], license=lic,
                        source=vi.get('descriptionurl', ''), file=name, frame=str(out_mp4.with_suffix('.jpg').relative_to(ROOT)))
    return None


def get_stream(url):
    return s.get(url, stream=True, timeout=120)


def main():
    titles = json.load(open(ROOT / 'data/landmark_titles.json'))
    queue = {c['city']: {a: (b, d) for a, b, d in c['stops']}
             for c in json.load(open(ROOT / 'data/route_queue.json'))['cities']}
    out, problems = [], []
    photos = ROOT / 'assets/photos'
    photos.mkdir(parents=True, exist_ok=True)
    for item in titles:
        city, name, title = item['city'], item['name'], item.get('title') or item['name']
        r = get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'), safe=''))
        if r.status_code != 200:
            problems.append(f'{city}/{name}: summary {r.status_code}')
            continue
        d = r.json()
        lead = None
        if d.get('originalimage'):
            lead = urllib.parse.unquote(d['originalimage']['source'].rsplit('/', 1)[-1])
        co = d.get('coordinates') or {}
        lat, lon = co.get('lat'), co.get('lon')
        known = queue.get(city, {}).get(name)
        dist = None
        if known and lat is not None:
            dist = round(hav(known, (lat, lon)), 2)
            if dist > 1.5:
                problems.append(f'{city}/{name}: wiki coordinate {dist} km from the deck')
        info = pick_photo(d.get('title', title), lead, item.get('photo'))
        rec = dict(city=city, name=name, title=d.get('title', title), url=d.get('content_urls', {}).get('desktop', {}).get('page', ''),
                   description=d.get('description', ''), extract=d.get('extract', ''), lat=lat, lon=lon, deck=known,
                   deck_km=dist, slug=slug(f'{city}-{name}'))
        if info:
            path = photos / f"{rec['slug']}.jpg"
            if not path.exists() or path.stat().st_size < 10000 or item.get('photo'):
                img = get(info['thumb'])
                if img.status_code != 200 or not img.headers.get('content-type', '').startswith('image'):
                    problems.append(f'{city}/{name}: image download {img.status_code}')
                    info = None
                else:
                    path.write_bytes(img.content)
            if info:
                rec['photo'] = dict(path=f"assets/photos/{rec['slug']}.jpg", artist=info['artist'], license=info['license'],
                                    source=info['page'], file=info['file'], width=info['width'], height=info['height'])
        if 'photo' not in rec:
            problems.append(f'{city}/{name}: no usable photo')
        rec['more_photos'] = []
        for j, more in enumerate(extra_photos(rec['title'], rec.get('photo', {}).get('file'))):
            path = photos / f"{rec['slug']}-{j + 2}.jpg"
            img = get(more['thumb'])
            if img.status_code == 200 and img.headers.get('content-type', '').startswith('image'):
                path.write_bytes(img.content)
                rec['more_photos'].append(dict(path=f"assets/photos/{path.name}", artist=more['artist'], license=more['license'],
                                               source=more['page'], file=more['file'], width=more['width'], height=more['height']))
        clips = ROOT / 'assets/clips'
        clips.mkdir(parents=True, exist_ok=True)
        try:
            rec['clip'] = find_clip(rec['title'], city, clips / f"{rec['slug']}.mp4")
        except Exception as e:  # a clip is a bonus, never a reason to stop
            problems.append(f'{city}/{name}: clip failed {e}')
            rec['clip'] = None
        out.append(rec)
        print(city, name, '->', rec['title'], '|', rec.get('photo', {}).get('license'), '|', dist, '| photos', 1 + len(rec['more_photos']), '| clip', bool(rec['clip']), flush=True)
        time.sleep(0.4)
    (ROOT / 'data/landmarks.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    (ROOT / 'data/landmarks_problems.txt').write_text('\n'.join(problems) + '\n', encoding='utf-8')
    print(len(out), 'landmarks,', len(problems), 'problems')
    print('\n'.join(problems))


if __name__ == '__main__':
    sys.exit(main())
