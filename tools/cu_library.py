#!/usr/bin/env python3
"""CompassUni post library: plan -> render -> calendar.

  cu_library.py plan               write data/render_plan.json from data/library_copy.json
  cu_library.py render <i> <n>     render shard i of n into posts/
  cu_library.py calendar           write calendar/<YYYY-MM-DD>.json, ready for Metricool

The daily scheduled task only reads calendar/<date>.json and needs no write access here."""
import json, os, re, sys, tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cu_media as m
from cu_media import page, brand_bg, ICON, INK, SLATE, BLUE, ROYAL, SKY, LINE


def esc(s):
    """Keep a price or a year range together: a currency sign or "27" alone on the next line reads as a mistake on a frame."""
    s = re.sub(r'(\d) ([€£$₺])', '\\1\u00a0\\2', m.esc(s))
    return re.sub(r'(\d)-(\d)', '\\1-\u2060\\2', s)


ROOT = m.ROOT
COPY = Path(os.environ.get('CU_COPY', ROOT / 'data/library_copy.json'))
RAW = 'https://raw.githubusercontent.com/kutayserin/a/compassuni-social'
TZ = 'Europe/Istanbul'
START = date(2026, 11, 5)
FIRST_SLOT = '2026-11-05T12:30'  # earlier slots that day are gone by the time the library is live
# Every 2 hours while Turkey is awake: the audience is here, so the night slots of the other brands make no sense.
SLOTS = [('08:30', 'uni'), ('10:30', 'list'), ('12:30', 'uni'), ('14:30', 'myth'),
         ('16:30', 'uni'), ('18:30', 'guide'), ('20:30', 'uni'), ('22:30', 'late')]
AUDIO = ['1304451697253803', '473815599863496', '1369509361952542', '1941675846329817', '957044555314519']
REEL_KINDS = {'uni', 'myth', 'deadline', 'how'}
CTAS = ['Başvuru sürecini birebir danışmanla yürütmek istersen: compassuni.com, link profilde.',
        '5 ülke, 150+ üniversite. Belge hazırlığından başvuru takibine kadar süreci birlikte yürütelim: compassuni.com',
        'Yön senden, yol bizden. Paketler ve süreç: compassuni.com, link profilde.']
SAVES = ['📌 Kaydet, başvuru döneminde lazım olacak.', '📌 Yurt dışı planı yapan birine gönder.', '📌 Kaydet, sonra lazım olur.']
# Dated copy: these name a window that closes in November, so they go out first.
EARLY = ['university-of-pavia', 'uw', 'berkeley']
PART = {'Almanya': 'almanya', 'İtalya': 'italya', 'Hollanda': 'hollanda', 'Birleşik Krallık': 'ingiltere', 'ABD': 'abd'}


def posts():
    return json.load(open(COPY))['posts']


def load(name, default):
    p = ROOT / 'data' / name
    return json.load(open(p)) if p.exists() else default


def unis():
    return {u['slug']: u for u in load('unis.json', [])}


def photos_of(slug, U):
    """Only photos picked by eye: file names on Wikipedia pages cover alumni portraits and other places too."""
    pick = load('visual_pick.json', {}).get(slug, [])
    ph = {p['path']: p for p in U.get(slug, {}).get('photos', [])}
    return [ph[f'assets/photos/{n}.jpg'] for n in pick if f'assets/photos/{n}.jpg' in ph]


ARTIST_FIX = [('File:Heidelberg Universitätsbibliothek', 'Jan Beckendorf'), ('Euku:', 'Euku'), ('Akriesch', 'Akriesch'), ('Uccio ', 'Uccio2'),
              ('The original uploader was Telerg', 'Telerg at French Wikipedia'), ('Photograph by Mike Peel', 'Mike Peel (www.mikepeel.net)')]


def clean_artist(a):
    a = a or 'Bilinmiyor'
    for start, name in ARTIST_FIX:
        if a.startswith(start):
            return name
    a = re.sub(r'\s*\(talk\)|\s*\d\d:\d\d, \d+ \w+ \d{4} \(UTC\)', '', a)
    a = re.sub(r'^user:', '', a, flags=re.I)
    return re.sub(r'\s+-\s+.*$', '', a).strip()


def tags(p):
    return ' '.join(f'#{t}' for t in dict.fromkeys([p['tag'], 'yurtdisindaegitim', 'yurtdisindaokumak', 'universite', 'compassuni']))


def source_line(p, sep=', '):
    ds = []
    for s in p.get('sources', []):
        if s['domain'] not in ds:
            ds.append(s['domain'])
    return sep.join(ds)


# ---------------------------------------------------------------- planning ---
def group(p):
    return p.get('country') or p['type']


def plan():
    items = posts()
    kinds = ('uni', 'list', 'myth', 'guide', 'deadline', 'how')
    pools = {k: [i for i, p in enumerate(items) if p['type'] == k] for k in kinds}
    first = [i for s in EARLY for i, p in enumerate(items) if p.get('slug') == s]
    pools['uni'] = first + [i for i in pools['uni'] if i not in first]
    seq = {}
    jobs, recent, d, audio, late = [], [], START, 0, 0
    while any(pools.values()):
        for tm, kind in SLOTS:
            key = f'{d.isoformat()}T{tm}'
            if key < FIRST_SLOT:
                continue
            if kind == 'late':
                kind = 'deadline' if late % 2 == 0 else 'how'
                late += 1
            k = kind if pools[kind] else max(pools, key=lambda q: len(pools[q]))
            if not pools[k]:
                break
            pool = pools[k]
            n = next((a for a, i in enumerate(pool) if group(items[i]) not in recent[-2:]), 0)
            i = pool.pop(n)
            p = items[i]
            recent.append(group(p))
            seq[k] = seq.get(k, 0) + 1
            name = f"{p['slug']}-uni" if k == 'uni' else f'{k}-{seq[k]:02d}'
            job = dict(i=i, kind=k, slot=key, day=d.isoformat(), folder=f'{d.isoformat()}-{name}')
            if k in REEL_KINDS:
                job['audio'] = AUDIO[audio % len(AUDIO)]
                audio += 1
            jobs.append(job)
        d += timedelta(days=1)
    (ROOT / 'data/render_plan.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=0), encoding='utf-8')
    from collections import Counter
    print(len(jobs), 'posts, last slot', jobs[-1]['slot'], Counter(j['kind'] for j in jobs))


# -------------------------------------------------------------- reel frames ---
SHADE = ('<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(15,23,42,.78) 0%,rgba(15,23,42,.52) 40%,'
         'rgba(15,23,42,.34) 62%,rgba(15,23,42,.80) 100%)"></div>')
CHECK = ('<svg width="60" height="60" viewBox="0 0 60 60" style="vertical-align:-14px;margin-right:6px"><circle cx="30" cy="30" r="30" fill="#22C55E"/>'
         '<path d="M17 31l9 9 17-20" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def hook_size(n):
    return 112 if n <= 36 else 100 if n <= 52 else 90


def end_frame(sh, out, h=1920, seed=0, line='Belge hazırlığından başvuru takibine kadar süreci birlikte yürütelim.'):
    top = 'justify-content:center'
    body = (brand_bg(seed) + f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;{top};text-align:center;padding:0 90px">'
            f'<img src="file://{ICON}" style="width:{190 if h > 1400 else 150}px;height:{190 if h > 1400 else 150}px;border-radius:44px">'
            f'<div style="font:900 {88 if h > 1400 else 76}px/1 Inter;letter-spacing:-.03em;margin-top:44px">CompassUni</div>'
            f'<div style="font:800 {60 if h > 1400 else 52}px/1.2 Inter;letter-spacing:-.02em;margin-top:36px">Yön senden, <em>yol bizden.</em></div>'
            f'<div class="txt" style="font-size:{40 if h > 1400 else 36}px;margin-top:30px">{esc(line)}</div>'
            f'<div style="margin-top:54px;font:900 {66 if h > 1400 else 58}px/1 Inter;letter-spacing:-.02em;padding:34px 56px;border-radius:30px;background:rgba(255,255,255,.14);border:2px solid rgba(255,255,255,.22)">compassuni.com</div>'
            f'<div style="margin-top:30px;font:700 36px Inter;color:#7DD3FC">@compassuni.app</div></div>')
    sh.shot(page(1080, h, body), out, 1080, h) if str(out).endswith('.png') else sh.shot(page(1080, h, body), out, 1080, h)


def brand_frame(sh, out, inner, seed):
    sh.shot(page(1080, 1920, brand_bg(seed) + inner), out, 1080, 1920)


def render_uni(sh, job, p, U, out):
    tmp = Path(tempfile.mkdtemp())
    ph = photos_of(p['slug'], U)
    where = f"{p['country']} · {p['city']}"
    hook = p['hook']
    a = (f'<div class="x" style="top:300px"><span class="chip sky">{esc(where)}</span>'
         f'<div style="font:800 46px/1.2 Inter;margin-top:36px;color:#fff">{esc(p["uni_name"])}</div>'
         f'<div class="big" style="font-size:{hook_size(len(hook))}px;margin-top:26px;text-shadow:0 2px 30px rgba(0,0,0,.45)">{esc(hook)}</div></div>')
    cav = f'<div class="txt" style="font-size:37px;margin-top:26px;color:rgba(255,255,255,.76)">{esc(p["caveat"])}</div>' if p.get('caveat') else ''
    b = (f'<div style="position:absolute;left:56px;right:56px;top:470px;background:rgba(15,23,42,.80);border:2px solid rgba(255,255,255,.14);border-radius:34px;padding:56px 56px 50px">'
         f'<div style="font:800 34px/1.2 Inter;color:#7DD3FC">{esc(p["uni_name"])}</div>'
         f'<div class="txt" style="font-size:{54 if len(p["fact"]) <= 110 else 49}px;font-weight:600;color:#fff;margin-top:24px">{esc(p["fact"])}</div>{cav}'
         f'<div class="src" style="margin-top:36px">Kaynak: {esc(source_line(p))} · Kasım 2026</div></div>')
    segs, durs = [], []
    if ph:
        sh.shot(page(1080, 1920, SHADE + a), tmp / 'a.png', 1080, 1920, transparent=True)
        sh.shot(page(1080, 1920, SHADE + b), tmp / 'b.png', 1080, 1920, transparent=True)
        v0 = ROOT / ph[0]['path']
        v1 = ROOT / ph[1 if len(ph) > 1 else 0]['path']
        m.photo_segment(v0, tmp / 'a.png', 3.8, tmp / 'sa.mp4', zoom_in=True, fade=True)
        m.photo_segment(v1, tmp / 'b.png', 6.2, tmp / 'sb.mp4', zoom_in=False)
    else:
        brand_frame(sh, tmp / 'a.png', a, job['i'])
        brand_frame(sh, tmp / 'b.png', b, job['i'] + 1)
        m.still_segment(tmp / 'a.png', 3.8, tmp / 'sa.mp4')
        m.still_segment(tmp / 'b.png', 6.2, tmp / 'sb.mp4')
    end_frame(sh, tmp / 'c.png', seed=job['i'])
    m.still_segment(tmp / 'c.png', 2.4, tmp / 'sc.mp4')
    m.assemble([tmp / 'sa.mp4', tmp / 'sb.mp4', tmp / 'sc.mp4'], [3.8, 6.2, 2.4], out)
    used = ph[:2]
    lines = []
    for v in used:
        ln = f"📷 {clean_artist(v['artist'])} ({v['license']}), Wikimedia Commons, kırpıldı ve metin eklendi"
        if ln not in lines:
            lines.append(ln)
    core = f"{hook}\n\n{p['fact']}" + (f" {p['caveat']}" if p.get('caveat') else '')
    return core, '\n'.join(lines)


def text_reel(sh, job, frames, out):
    """frames: list of (inner html, seconds)."""
    tmp = Path(tempfile.mkdtemp())
    segs, durs = [], []
    for k, (inner, sec) in enumerate(frames):
        brand_frame(sh, tmp / f'f{k}.png', inner, job['i'] + k)
        m.still_segment(tmp / f'f{k}.png', sec, tmp / f's{k}.mp4')
        segs.append(tmp / f's{k}.mp4')
        durs.append(sec)
    end_frame(sh, tmp / 'end.png', seed=job['i'])
    m.still_segment(tmp / 'end.png', 2.4, tmp / 'send.mp4')
    m.assemble(segs + [tmp / 'send.mp4'], durs + [2.4], out)


def center(inner, top=190, bottom=300, right=110):
    return f'<div style="position:absolute;left:80px;right:{right}px;top:{top}px;bottom:{bottom}px;display:flex;flex-direction:column;justify-content:center;align-items:flex-start">{inner}</div>'


def src_el(p):
    return f'<div class="src" style="margin-top:40px">Kaynak: {esc(source_line(p))} · Kasım 2026</div>'


def render_myth(sh, job, p, U, out):
    a = center(f'<span class="chip no">Yanlış bilinen</span>'
               f'<div class="big" style="font-size:{hook_size(len(p["claim"]))}px;margin-top:44px">“{esc(p["claim"])}”</div>')
    b = center(f'<span class="chip yes">Doğrusu</span>'
               f'<div class="mid2" style="font-size:{84 if len(p["truth_title"]) <= 36 else 74}px;margin-top:40px">{esc(p["truth_title"])}</div>'
               f'<div class="txt" style="margin-top:34px">{esc(p["truth"])}</div>{src_el(p)}')
    text_reel(sh, job, [(a, 3.4), (b, 6.4)], out)
    return f"“{p['claim']}”\n\nDoğrusu: {p['truth_title']}. {p['truth']}", ''


def render_deadline(sh, job, p, U, out):
    head = (f'<span class="chip sky">Takvimine yaz · {esc(p.get("country", ""))}</span>'
            f'<div style="font:900 {132 if len(p["date_big"]) <= 12 else 112}px/1.04 Inter;letter-spacing:-.04em;color:{SKY};margin-top:46px">{esc(p["date_big"])}</div>')
    a = center(f'{head}<div class="mid2" style="font-size:76px;margin-top:40px">{esc(p["what"])}</div>')
    b = center(f'{head}<div class="txt" style="margin-top:44px">{esc(p["detail"])}</div>{src_el(p)}')
    text_reel(sh, job, [(a, 3.2), (b, 5.6)], out)
    return f"{p['date_big']} · {p['what']}.\n\n{p['detail']}", ''


def render_how(sh, job, p, U, out):
    frames = [(center(f'<span class="chip sky">CompassUni</span>'
                      f'<div class="big" style="font-size:{hook_size(len(p["hook"]))}px;margin-top:44px">{esc(p["hook"])}</div>'), 3.2)]
    for k, ln in enumerate(p['lines']):
        frames.append((center(f'<div style="font:900 170px/1 Inter;letter-spacing:-.04em;color:{SKY}">{k + 1}</div>'
                              f'<div class="mid2" style="margin-top:34px">{esc(ln["title"])}</div><div class="txt" style="margin-top:30px">{esc(ln["body"])}</div>'), 3.4))
    text_reel(sh, job, frames, out)
    lines = '\n'.join(f"{k + 1}. {ln['title']}: {ln['body']}" for k, ln in enumerate(p['lines']))
    return f"{p['hook']}\n\n{lines}", ''


# ----------------------------------------------------------- carousel slides ---
LIGHT_FOOT = lambda i, n: f'<div class="foot" style="color:#94A3B8"><span>compassuni.com</span><span>{i} / {n}</span></div>'
DARK_FOOT = lambda i, n: f'<div class="foot" style="color:rgba(255,255,255,.6)"><span>compassuni.com</span><span>{i} / {n}</span></div>'


def cover(sh, out, eyebrow, hook, n, seed, preview=''):
    size = 96 if len(hook) <= 44 else 84
    body = (brand_bg(seed) + f'<div class="x" style="top:120px;right:90px"><span class="chip sky" style="font-size:27px">{esc(eyebrow)}</span>'
            f'<div class="big" style="font-size:{size}px;margin-top:44px">{esc(hook)}</div>{preview}</div>'
            f'<div class="swipe">KAYDIR →</div>' + DARK_FOOT(1, n))
    sh.shot(page(1080, 1350, body), out, 1080, 1350)


def note_slide(sh, out, p, i, n):
    body = (f'<div class="light"></div><div class="x" style="top:150px;right:90px;color:{INK}"><div class="eb">Bilmen gereken</div>'
            f'<div style="font:600 54px/1.32 Inter;letter-spacing:-.012em;color:{INK};margin-top:34px">{esc(p["note"])}</div>'
            f'<div class="eb" style="margin-top:70px;color:{SLATE}">Kaynak</div>'
            f'<div style="font:600 36px/1.45 Inter;color:{SLATE};margin-top:20px">{esc(source_line(p, " · "))}</div>'
            f'<div style="font:500 32px/1.4 Inter;color:#64748B;margin-top:30px">Kasım 2026’da resmi sayfalardan kontrol edildi. Başvurmadan önce güncel hâlini teyit et.</div></div>' + LIGHT_FOOT(i, n))
    sh.shot(page(1080, 1350, body), out, 1080, 1350)


def table_slide(sh, out, p, i, n):
    rows = p['rows']
    nums = [r.get('num') for r in rows if r.get('num') is not None]
    top = max(nums) if nums and len(nums) == len(rows) else None
    pad = {4: 46, 5: 34, 6: 23, 7: 14}.get(len(rows), 14)
    fl, fv = {4: (46, 52), 5: (42, 48), 6: (40, 44)}.get(len(rows), (38, 42))
    html_rows = ''
    for r in rows:
        bar = ''
        if top:
            bar = (f'<div style="height:14px;border-radius:8px;background:{LINE};margin-top:14px"><div style="height:14px;border-radius:8px;'
                   f'width:{max(4, r["num"] / top * 100):.1f}%;background:linear-gradient(90deg,{BLUE},{SKY})"></div></div>')
        sub = f'<div style="font:500 28px/1.25 Inter;color:{SLATE};margin-top:6px">{esc(r["sub"])}</div>' if r.get('sub') else ''
        html_rows += (f'<div style="padding:{pad}px 0;border-bottom:2px solid {LINE}"><div style="display:flex;justify-content:space-between;align-items:baseline;gap:24px">'
                      f'<div style="font:800 {fl}px/1.18 Inter;color:{INK};letter-spacing:-.012em">{esc(r["label"])}</div>'
                      f'<div style="font:900 {fv}px/1.1 Inter;color:{ROYAL};white-space:nowrap;letter-spacing:-.02em">{esc(r["value"])}</div></div>{sub}{bar}</div>')
    body = (f'<div class="light"></div><div class="x" style="top:84px;left:70px;right:70px"><div class="eb">{esc(p["eyebrow"])}</div>'
            f'<div style="margin-top:20px">{html_rows}</div></div>' + LIGHT_FOOT(i, n))
    sh.shot(page(1080, 1350, body), out, 1080, 1350)


def render_list(sh, job, p, U, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    n = 4
    prev = ''.join(f'<div style="font:700 36px/1.2 Inter;color:rgba(255,255,255,.72);margin-top:14px">{esc(r["label"])}</div>' for r in p['rows'][:4])
    cover(sh, out / '01.jpg', p['eyebrow'], p['hook'], n, job['i'], f'<div style="margin-top:50px">{prev}</div>')
    table_slide(sh, out / '02.jpg', p, 2, n)
    note_slide(sh, out / '03.jpg', p, 3, n)
    end_frame(sh, out / '04.jpg', 1350, job['i'])
    lines = '\n'.join(f"{r['label']}: {r['value']}" + (f" ({r['sub']})" if r.get('sub') else '') for r in p['rows'])
    return f"{p['hook']}\n\n{lines}\n\n{p['note']}", ''


def render_guide(sh, job, p, U, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    steps = p['steps']
    n = len(steps) + 3
    cover(sh, out / '01.jpg', p['eyebrow'], p['hook'], n, job['i'])
    for k, st in enumerate(steps):
        body = ('<div class="light"></div>' + center(f'<div class="eb">{esc(p["eyebrow"])}</div>'
                f'<div style="font:900 190px/1 Inter;letter-spacing:-.05em;margin-top:40px;background:linear-gradient(135deg,{BLUE},{SKY});-webkit-background-clip:text;color:transparent">{k + 1}</div>'
                f'<div style="font:900 74px/1.1 Inter;letter-spacing:-.028em;color:{INK};margin-top:28px">{esc(st["title"])}</div>'
                f'<div style="font:500 48px/1.36 Inter;color:{SLATE};margin-top:28px">{esc(st["body"])}</div>', top=60, bottom=120, right=90) + LIGHT_FOOT(k + 2, n))
        sh.shot(page(1080, 1350, body), out / f'{k + 2:02d}.jpg', 1080, 1350)
    note_slide(sh, out / f'{n - 1:02d}.jpg', p, n - 1, n)
    end_frame(sh, out / f'{n:02d}.jpg', 1350, job['i'])
    lines = '\n'.join(f"{k + 1}. {st['title']}: {st['body']}" for k, st in enumerate(steps))
    return f"{p['hook']}\n\n{lines}\n\n{p['note']}", ''


RENDER = dict(uni=render_uni, myth=render_myth, deadline=render_deadline, how=render_how, list=render_list, guide=render_guide)


def caption(job, p, core, credits):
    n = job['i']
    src = ''
    if p.get('sources') and job['kind'] != 'how':
        src = f"\n\nKaynak: {source_line(p)} (Kasım 2026’da kontrol edildi). Başvurmadan önce resmi sayfadan teyit et."
    cap = f"{core}{src}\n\n{SAVES[n % len(SAVES)]}\n\n{CTAS[n % len(CTAS)]}\n\n{tags(p)}"
    return cap + (f"\n\n{credits}" if credits else '')


def render(i, n):
    items, U = posts(), unis()
    jobs = json.load(open(ROOT / 'data/render_plan.json'))
    with m.Shooter() as sh:
        for k, job in enumerate(jobs):
            if k % n != i:
                continue
            out = ROOT / 'posts' / job['folder']
            if (out / 'caption.txt').exists():
                continue
            print(k, job['folder'], flush=True)
            p = items[job['i']]
            core, credits = RENDER[job['kind']](sh, job, p, U, out)
            (out / 'caption.txt').write_text(caption(job, p, core, credits), encoding='utf-8')
            (out / 'title.txt').write_text(p['title'], encoding='utf-8')


# ---------------------------------------------------------------- calendar ---
def calendar():
    jobs = json.load(open(ROOT / 'data/render_plan.json'))
    days, missing = {}, []
    for job in jobs:
        d = ROOT / 'posts' / job['folder']
        if not (d / 'caption.txt').exists():
            missing.append(job['folder'])
            continue
        base = f"{RAW}/posts/{job['folder']}"
        text = (d / 'caption.txt').read_text(encoding='utf-8')
        title = (d / 'title.txt').read_text(encoding='utf-8').strip()
        info = dict(autoPublish=True, descendants=[], draft=False, firstCommentText='', hasNotReadNotes=False, mediaAltText=[],
                    providers=[dict(network='instagram'), dict(network='tiktok'), dict(network='facebook')],
                    publicationDate=dict(dateTime=job['slot'] + ':00', timezone=TZ), shortener=False,
                    smartLinkData=dict(ids=[]), text=text)
        tiktok = dict(privacyOption='PUBLIC_TO_EVERYONE', commercialContentOwnBrand=True, title=title[:90])
        if job['kind'] in REEL_KINDS:
            info.update(media=[f'{base}/reel.mp4'], videoThumbnailUrl=f'{base}/cover.jpg',
                        instagramData=dict(type='REEL', showReelOnFeed=True,
                                           audioConfiguration=dict(audioId=job['audio'], videoVolume=0)),
                        facebookData=dict(type='REEL', title=title[:90]), tiktokData=dict(tiktok, autoAddMusic=False))
        else:
            files = sorted(p.name for p in d.glob('*.jpg'))
            info.update(media=[f'{base}/{f}' for f in files], instagramData=dict(type='POST'),
                        facebookData=dict(type='POST'), tiktokData=dict(tiktok, autoAddMusic=True))
        days.setdefault(job['day'], []).append(dict(slot=job['slot'], date=job['slot'] + ':00+03:00', kind=job['kind'],
                                                    folder=job['folder'], info=info))
    out = ROOT / 'calendar'
    out.mkdir(exist_ok=True)
    for f in out.glob('*.json'):
        f.unlink()
    for d, rows in days.items():
        (out / f'{d}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding='utf-8')
    (out / 'index.json').write_text(json.dumps(dict(first=min(days), last=max(days), days=len(days),
                                                     posts=sum(len(v) for v in days.values()), missing=missing), indent=0), encoding='utf-8')
    print(len(days), 'days', sum(len(v) for v in days.values()), 'posts; missing', missing)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'plan':
        plan()
    elif cmd == 'render':
        render(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == 'calendar':
        calendar()
