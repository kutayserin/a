#!/usr/bin/env python3
"""More campus photos from a Commons search, for universities whose Wikipedia page mostly shows people."""
import html, json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
s = requests.Session()
s.headers.update({'User-Agent': 'CompassUniSocialBot/1.0 (https://compassuni.com; social media asset builder)'})
OK = re.compile(r'^(cc0|cc[ -]by|fal|free art|public domain|pd\b|attribution)', re.I)
SKIP = re.compile(r'(logo|seal|crest|emblem|map|plan\b|portrait|ritratto|signature|\.svg|\.png|\.gif|\.tif|\.pdf|\.webm|\.ogv|\.djvu|\.webp)', re.I)
Q = {'sapienza-university-rome': ['Sapienza Università di Roma città universitaria', 'Sapienza University of Rome rectorate'],
     'hpi': ['Hasso-Plattner-Institut Potsdam'], 'bocconi-university': ['Università Bocconi Milano', 'Bocconi University campus'],
     'domus-academy': ['Domus Academy Milano'], 'university-of-verona': ['Università di Verona', 'University of Verona'],
     'luiss': ['LUISS Roma', 'Villa Blanc LUISS'], 'unibz': ['Libera Università di Bolzano', 'Freie Universität Bozen'],
     'university-of-turin': ['Università di Torino Palazzo Nuovo', 'Campus Luigi Einaudi Torino'], 'university-of-genoa': ['Università di Genova via Balbi'],
     'tilburg': ['Tilburg University campus building'], 'rietveld': ['Gerrit Rietveld Academie Amsterdam'],
     'lse': ['London School of Economics building', 'LSE Houghton Street'], 'harvard': ['Harvard Yard', 'Widener Library Harvard'],
     'columbia': ['Low Memorial Library Columbia University', 'Butler Library Columbia'], 'milano-bicocca': ['Università Milano-Bicocca'],
     'eur-rotterdam': ['Erasmus University Rotterdam campus Woudestein'], 'hanze': ['Hanzehogeschool Groningen'],
     'fu-berlin': ['Freie Universität Berlin Henry-Ford-Bau', 'Freie Universität Berlin Philologische Bibliothek'],
     'uni-hamburg': ['Universität Hamburg Hauptgebäude'], 'jacobs-bremen': ['Constructor University Bremen campus']}


def get(url, **p):
    for a in range(6):
        r = s.get(url, params=p or None, timeout=40)
        if r.status_code in (429, 503):
            time.sleep(5 * (a + 1))
            continue
        return r
    return r


def main():
    U = json.load(open(ROOT / 'data/unis.json'))
    by = {u['slug']: u for u in U}
    for slug, queries in Q.items():
        seen, n = set(), 0
        for q in queries:
            r = get('https://commons.wikimedia.org/w/api.php', action='query', format='json', generator='search', gsrsearch=q, gsrnamespace=6, gsrlimit=25,
                    prop='imageinfo', iiprop='url|extmetadata|size', iiurlwidth=1600)
            pages = sorted(r.json().get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 99))
            for pg in pages:
                if n >= 6:
                    break
                name = pg['title'].split(':', 1)[1]
                if name in seen or SKIP.search(name) or not re.search(r'\.jpe?g$', name, re.I) or 'imageinfo' not in pg:
                    continue
                seen.add(name)
                ii = pg['imageinfo'][0]
                meta = ii.get('extmetadata', {})
                lic = meta.get('LicenseShortName', {}).get('value', '')
                artist = html.unescape(re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value', ''))).strip()
                w, h = ii.get('width', 0), ii.get('height', 0)
                if not (OK.match(lic) and artist and w >= 1600 and h >= 900 and 0.6 <= w / max(h, 1) <= 2.0):
                    continue
                img = s.get(ii.get('thumburl') or ii['url'], timeout=60)
                if img.status_code != 200 or len(img.content) < 30000:
                    continue
                n += 1
                path = ROOT / 'assets/photos' / f'{slug}-c{n}.jpg'
                path.write_bytes(img.content)
                by[slug]['photos'].append(dict(file=name, license=lic, artist=re.sub(r'\s+', ' ', artist)[:70], width=w, height=h,
                                               source=ii.get('descriptionurl', ''), path=f'assets/photos/{path.name}'))
                time.sleep(0.2)
        print(slug, n, flush=True)
    (ROOT / 'data/unis.json').write_text(json.dumps(U, ensure_ascii=False, indent=0), encoding='utf-8')


if __name__ == '__main__':
    main()
