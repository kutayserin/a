"""Builds the LinkedIn calendar from the carousel posts of this branch.

One post a day per Page. Each carousel becomes a PDF document post, with a
caption that has a direct link instead of "link in bio".
Usage: python3 tools/li_library.py <travelhour|website|compassuni> <YYYY-MM-DD first day>
Writes linkedin/media/<folder>.pdf, linkedin/<date>.json and linkedin/index.json.
"""
import datetime as dt, glob, io, json, os, re, sys, tempfile
import img2pdf
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

APP = 'https://apps.apple.com/app/travelhour-trip-planner/id6773093615'
WEB = 'https://website-automation.com'
CU = 'https://www.compassuni.com'
BRANDS = {
    'travelhour': dict(branch='travelhour-social', kinds=('tour', 'carousel'), time='12:00', slide='travelhour.app', spacing=1.2, author='Travelhour'),
    'website': dict(branch='website-automation-social', kinds=('checklist', 'rewrite'), time='18:00', slide='website-automation.com', spacing=0, author='website-automation'),
    'compassuni': dict(branch='compassuni-social', kinds=('list', 'guide'), time='09:30', slide=None, spacing=0, author='CompassUni'),
}
# CompassUni: these two carry dates that pass during the run, so they go first.
EARLY = {'compassuni': ['Güz 2027 lisans başvurusunda kritik günler', None, "Eylül 2027'de başlamak için geriye doğru plan"]}


def caption(brand, t):
    if brand == 'travelhour':
        t = t.replace('Free on the App Store, link in bio.', f'Free on the App Store: {APP}')
    elif brand == 'website':
        t = t.replace(' Link in bio.', f'\n{WEB}')
    else:
        t = t.replace('compassuni.com, link profilde.', CU)
        t = re.sub(r'(?<![/.\w])compassuni\.com', CU, t)
    lines = []
    for line in t.split('\n'):
        if line.startswith('#'):
            tags = line.split()
            keep = tags[:3]
            if brand == 'compassuni' and '#compassuni' not in keep:
                keep = tags[:2] + ['#compassuni']
            line = ' '.join(keep)
        lines.append(line)
    t = '\n'.join(lines)
    assert not re.search(r'(?i)link in bio|link profilde', t), t
    assert len(t) <= 3000
    return t


def inter(size):
    src = sorted(glob.glob('tools/fonts/inter-latin-wght-normal.woff2'))[0]
    f = TTFont(src); f.flavor = None
    path = os.path.join(tempfile.gettempdir(), 'inter-li.ttf'); f.save(path)
    font = ImageFont.truetype(path, size)
    font.set_variation_by_axes([600 if a['name'] in (b'Weight', 'Weight') else a['default'] for a in font.get_variation_axes()])
    return font


def bands(im, x0=200, x1=880, y0=500, y1=1300, thr=40):
    px = im.load(); out = []; start = None
    for y in range(y0, y1):
        ref = px[x0 - 40, y]
        hit = any(sum(abs(px[x, y][c] - ref[c]) for c in range(3)) > thr for x in range(x0, x1, 2))
        if hit and start is None: start = y
        if not hit and start is not None:
            out.append((start, y)); start = None
    return out


def patch_last(jpg, text, spacing):
    """Swap the small 'Link in bio' under the button for the site name."""
    im = Image.open(io.BytesIO(jpg)).convert('RGB')
    bs = bands(im)
    def filled(a):   # the button is a solid shape, even along its top edge
        p = im.load()
        y = a + 6
        return sum(sum(abs(p[x, y][c] - p[160, y][c]) for c in range(3)) > 40 for x in range(200, 880)) >= 250
    pill = next(i for i, (a, b) in enumerate(bs) if 50 <= b - a <= 130 and filled(a))
    a, b = bs[pill + 1]
    assert b - a < 45, (bs, pill)
    px = im.load()
    xs = [x for x in range(200, 880) for y in range(a, b) if sum(abs(px[x, y][c] - px[160, y][c]) for c in range(3)) > 40]
    x0, x1 = min(xs), max(xs)
    ink = min((px[x, y] for x in range(x0, x1) for y in range(a, b)), key=sum)
    font = inter(30)
    width = sum(font.getlength(c) + spacing for c in text) - spacing
    d = ImageDraw.Draw(im)
    half = int(max(x1 - x0, width) / 2) + 14
    for y in range(a - 3, b + 3):
        d.line([(540 - half, y), (540 + half, y)], fill=px[540 - half - 6, y])
    x = 540 - width / 2
    y = (a + b) / 2
    for c in text:
        d.text((x, y), c, font=font, fill=ink, anchor='lm')
        x += font.getlength(c) + spacing
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=92, subsampling=0)
    return buf.getvalue()


def rows():
    out = []
    for p in sorted(glob.glob('calendar/2*.json')):
        out += json.load(open(p))
    return sorted(out, key=lambda r: r['date'])


def main(brand, first):
    cfg = BRANDS[brand]
    picked = [r for r in rows() if r['kind'] in cfg['kinds']]
    for i, head in enumerate(EARLY.get(brand, [])):
        if head:
            r = next(x for x in picked if x['info']['text'].startswith(head))
            picked.remove(r); picked.insert(i, r)
    for i in range(1, len(picked)):           # never the same city two days running
        if picked[i].get('city') and picked[i].get('city') == picked[i - 1].get('city'):
            j = next(k for k in range(i + 1, len(picked)) if picked[k].get('city') != picked[i].get('city'))
            picked[i], picked[j] = picked[j], picked[i]
    os.makedirs('linkedin/media', exist_ok=True)
    day = dt.date.fromisoformat(first)
    raw = f"https://raw.githubusercontent.com/kutayserin/a/{cfg['branch']}/linkedin/media"
    for r in picked:
        src = r['info']
        title = src['tiktokData']['title']
        slides = [open(u.split(f"/{cfg['branch']}/")[1], 'rb').read() for u in src['media']]
        if cfg['slide']:
            slides[-1] = patch_last(slides[-1], cfg['slide'], cfg['spacing'])
        pdf = img2pdf.convert(slides, layout_fun=img2pdf.get_layout_fun((540, 675)), title=title, author=cfg['author'])
        open(f"linkedin/media/{r['folder']}.pdf", 'wb').write(pdf)
        stamp = f"{day}T{cfg['time']}:00"
        row = dict(slot=stamp[:16], date=stamp + '+03:00', kind=r['kind'], folder=r['folder'], info=dict(
            autoPublish=True, descendants=[], draft=False, firstCommentText='', hasNotReadNotes=False,
            media=[f"{raw}/{r['folder']}.pdf"], mediaAltText=[], providers=[{'network': 'linkedin'}],
            publicationDate={'dateTime': stamp, 'timezone': 'Europe/Istanbul'}, shortener=False,
            smartLinkData={'ids': []}, text=caption(brand, src['text']),
            linkedinData=dict(documentTitle=title, publishImagesAsPDF=False, previewIncluded=False, type='post')))
        json.dump([row], open(f'linkedin/{day}.json', 'w'), ensure_ascii=False, indent=0)
        day += dt.timedelta(days=1)
    last = day - dt.timedelta(days=1)
    json.dump(dict(first=first, last=str(last), days=len(picked), posts=len(picked), missing=[]), open('linkedin/index.json', 'w'), indent=0)
    print(brand, len(picked), first, str(last))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
