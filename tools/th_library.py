#!/usr/bin/env python3
"""TravelHour post library: plan -> render -> calendar.

  th_library.py plan               write data/render_plan.json from the verified data
  th_library.py render <i> <n>     render shard i of n into posts/
  th_library.py calendar           write calendar/<YYYY-MM-DD>.json, ready for Metricool

The daily scheduled task only reads calendar/<date>.json and needs no write access here."""
import json, re, sys, tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
RAW = 'https://raw.githubusercontent.com/kutayserin/a/travelhour-social'
TZ = 'Europe/Istanbul'
START = date(2026, 11, 5)
# Every 3 hours. Reel = R (map route), O = order carousel, T = photo tour, S = landmark spotlight reel.
SLOTS = [('01:30', 'S'), ('04:30', 'S'), ('07:30', 'T'), ('10:30', 'S'),
         ('13:30', 'R'), ('16:30', 'O'), ('19:30', 'S'), ('22:30', 'S')]
# Already scheduled by hand in Metricool at 19:30 on these days.
TAKEN = {'2026-11-05T19:30', '2026-11-07T19:30', '2026-11-08T19:30', '2026-11-10T19:30',
         '2026-11-12T19:30', '2026-11-14T19:30', '2026-11-15T19:30'}
# Already covered by the hand-built one-day carousels.
NO_TOUR = {'Istanbul', 'Paris', 'Rome'}
SKIP = set()
AUDIO = ['1304451697253803', '473815599863496', '1369509361952542', '1941675846329817', '957044555314519']
CTAS = [
    'Travelhour turns the landmarks you swipe into one walking day. Free on the App Store, link in bio.',
    'Swipe the places you want and Travelhour puts them in walking order. Free on the App Store, link in bio.',
    'Plan this walk in Travelhour: swipe, sort, go. Free on the App Store, link in bio.',
    'Travelhour guides you between stops on a live map. Free on the App Store, link in bio.',
]
SAVES = ['📌 Save this for your trip.', '📌 Save this and send it to who you\'re going with.',
         '📌 Save this for your next city break.', '📌 Would you go? Save it for later.']


def data():
    lm = json.load(open(ROOT / 'data/landmarks.json'))
    copy = {c['slug']: c for c in json.load(open(ROOT / 'data/spotlights.json'))}
    queue = json.load(open(ROOT / 'data/route_queue.json'))['cities']
    return lm, copy, queue


def tagify(city):
    return city.lower().replace(' ', '')


def credit_short(p):
    a = p['artist'] or 'Unknown'
    a = a.split(' (')[0].strip()
    a = a if len(a) <= 34 else a[:32].rstrip() + '…'
    return f"{a} · {p['license']}"


def credit_line(p):
    return f"{p['artist']} ({p['license']})"


# ---------------------------------------------------------------- planning ---
def plan():
    lm, copy, queue = data()
    lm = [x for x in lm if x['slug'] in copy and x.get('photo') and x['slug'] not in SKIP]
    by_city = {}
    for x in lm:
        by_city.setdefault(x['city'], []).append(x)
    spot = []
    pools = {c: list(v) for c, v in by_city.items()}
    while any(pools.values()):  # one landmark per city in turn, so a city never repeats soon
        for c in sorted(pools, key=lambda k: -len(pools[k])):
            if pools[c]:
                spot.append(pools[c].pop(0))
    route = [c['city'] for c in queue]
    order = route[len(route) // 2:] + route[:len(route) // 2]  # map order differs from route reels
    tour = [c for c in sorted(by_city, key=lambda c: route.index(c) if c in route else 99)
            if c not in NO_TOUR and len([x for x in by_city[c] if x.get('lat')]) >= 5]
    pools = dict(R=list(route), O=list(order), T=list(tour))
    jobs, recent, d, audio = [], [], START, 0
    while spot or pools['R'] or pools['O'] or pools['T']:
        for tm, kind in SLOTS:
            key = f'{d.isoformat()}T{tm}'
            if key in TAKEN:
                continue
            k = kind if pools.get(kind) else 'S'
            if k == 'S' and not spot:
                k = next((q for q in 'ROT' if pools[q]), None)
                if not k:
                    break
            if k == 'S':
                i = next((n for n, x in enumerate(spot) if x['city'] not in recent[-4:]), 0)
                x = spot.pop(i)
                city, job = x['city'], dict(kind='spotlight', slug=x['slug'])
            else:
                city = pools[k].pop(0)
                job = dict(kind=dict(R='reel', O='carousel', T='tour')[k], city=city)
            recent.append(city)
            job.update(slot=key, day=d.isoformat(), city=city)
            if job['kind'] in ('spotlight', 'reel'):
                job['audio'] = AUDIO[audio % len(AUDIO)]
                audio += 1
            jobs.append(job)
        d += timedelta(days=1)
    (ROOT / 'data/render_plan.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=0), encoding='utf-8')
    print(len(jobs), 'posts, last slot', jobs[-1]['slot'])
    from collections import Counter
    print(Counter(j['kind'] for j in jobs))


# --------------------------------------------------------------- rendering ---
SPOT_CSS = """
.top{position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,20,16,.62) 0%,rgba(26,20,16,.30) 34%,
  rgba(26,20,16,.30) 58%,rgba(26,20,16,.72) 100%)}
.hook{position:absolute;left:80px;right:110px;top:470px;color:#FAF6EE;font:600 HOOKSIZEpx/1.06 'Fraunces';
  letter-spacing:-.012em;text-shadow:0 2px 30px rgba(0,0,0,.45)}
.where{position:absolute;left:80px;top:380px;font:700 32px 'Inter';letter-spacing:.2em;color:#FAF6EE;
  text-transform:uppercase;text-shadow:0 1px 16px rgba(0,0,0,.6)}
.fshade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,20,16,.40) 0%,rgba(26,20,16,0) 20%,
  rgba(26,20,16,0) 34%,rgba(26,20,16,.86) 58%,rgba(26,20,16,.93) 100%)}
.fact{position:absolute;left:80px;right:130px;bottom:470px;color:#FAF6EE}
.fname{font:600 FNAMEpx/1.03 'Fraunces';letter-spacing:-.01em}
.ftext{font:500 44px/1.36 'Inter';margin-top:26px;color:#FAF6EE}
.fcity{font:700 28px 'Inter';letter-spacing:.2em;color:#E0A458;margin-bottom:16px;text-transform:uppercase}
.fcredit{position:absolute;right:60px;top:130px;font:500 22px 'Inter';color:rgba(250,246,238,.82);
  text-shadow:0 1px 6px rgba(0,0,0,.7)}
"""


def still_cut(t, img, overlay, dur, out, zoom_in=True, darken=False, fade=False):
    frames = int(round(dur * t.FPS))
    z = f"1+0.07*on/{frames}" if zoom_in else f"1.07-0.07*on/{frames}"
    crop = "crop=if(gt(iw/ih\\,9/16)\\,ih*9/16\\,iw):if(gt(iw/ih\\,9/16)\\,ih\\,iw*16/9)"
    grade = ',eq=saturation=1.06:contrast=1.03' + (':brightness=-0.03' if darken else '')
    ov = 'format=rgba' + (',fade=in:st=0.1:d=0.3:alpha=1' if fade else '')
    fc = (f"[0:v]{crop},scale=2160:3840{grade},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={t.FPS},"
          f"setsar=1[bg];[1:v]{ov}[ov];[bg][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
    t.ff(['-i', img, '-loop', 1, '-t', dur, '-i', overlay, '-filter_complex', fc, '-map', '[v]', '-frames:v', frames,
          '-r', t.FPS, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 18, out])


def clip_cut(t, clip, overlay, dur, out, start=0.0, darken=False, fade=False):
    frames = int(round(dur * t.FPS))
    ov = 'format=rgba' + (',fade=in:st=0.1:d=0.3:alpha=1' if fade else '')
    grade = 'eq=saturation=1.05:contrast=1.02' + (':brightness=-0.04' if darken else '')
    fc = (f"[0:v]setsar=1,{grade}[bg];[1:v]{ov}[ov];[bg][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
    t.ff(['-stream_loop', -1, '-ss', start, '-i', clip, '-loop', 1, '-t', dur, '-i', overlay, '-filter_complex', fc, '-map', '[v]',
          '-frames:v', frames, '-r', t.FPS, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 18, out])


def visuals_of(x):
    """Clips first because moving footage holds attention, then photos; rejected ones are skipped."""
    rej = set(json.load(open(ROOT / 'data/visual_rejects.json'))) if (ROOT / 'data/visual_rejects.json').exists() else set()
    clips = [c for c in (x.get('clips') or []) if c['path'] not in rej]
    photos = [p for p in [x.get('photo')] + (x.get('more_photos') or []) if p and p['path'] not in rej]
    return clips, photos


def render_spotlight(sh, job, x, c, out):
    import th_media as t
    tmp = Path(tempfile.mkdtemp())
    clips, photos = visuals_of(x)
    hook = c['hook']
    css = SPOT_CSS.replace('HOOKSIZE', '112' if len(hook) <= 34 else '96' if len(hook) <= 52 else '84') \
                  .replace('FNAME', '92' if len(x['name']) <= 18 else '74')
    a = f'<div class="top"></div><div class="where">{t.esc(x["city"])}</div><div class="hook">{t.esc(hook)}</div>'
    sh.shot(t.page(1080, 1920, a, css), tmp / 'a.png', 1080, 1920, transparent=True)
    b = ('<div class="fshade"></div><div class="fcredit">Credits in caption</div>'
         f'<div class="fact"><div class="fcity">{t.esc(x["city"])}</div><div class="fname">{t.esc(x["name"])}</div>'
         f'<div class="ftext">{t.esc(c["fact"])}</div></div>')
    sh.shot(t.page(1080, 1920, b, css), tmp / 'b.png', 1080, 1920, transparent=True)
    end = tmp / 'end.png'
    t.end_card(sh, end, 1080, 1920, f'Plan your <i>{t.esc(x["city"])}</i> walk',
               'Swipe the landmarks you love. Travelhour turns them into one walking route.', '')
    # Hook on the strongest visual, then quick cuts under the fact. 6 s is enough to read it.
    visuals = [('clip', v) for v in clips] + [('photo', v) for v in photos]
    segs, durs, used = [], [], []
    v0 = visuals[0]
    segs.append(tmp / 'hook.mp4'); durs.append(2.8); used.append(v0[1])
    if v0[0] == 'clip':
        clip_cut(t, str(ROOT / v0[1]['path']), tmp / 'a.png', 2.8, segs[0], darken=True, fade=True)
    else:
        still_cut(t, str(ROOT / v0[1]['path']), tmp / 'a.png', 2.8, segs[0], zoom_in=False, darken=True, fade=True)
    rest = visuals[1:4] or [v0]
    each = round(6.3 / len(rest) + 0.3 * (len(rest) - 1) / len(rest), 2)
    for i, (kind, v) in enumerate(rest):
        seg = tmp / f'cut{i}.mp4'
        if kind == 'clip':
            clip_cut(t, str(ROOT / v['path']), tmp / 'b.png', each, seg, start=3.0 if v is v0[1] else 0.0)
        else:
            still_cut(t, str(ROOT / v['path']), tmp / 'b.png', each, seg, zoom_in=i % 2 == 0)
        segs.append(seg); durs.append(each)
        if v not in used:
            used.append(v)
    segs.append(tmp / 'end.mp4'); durs.append(2.2)
    t.still_segment(end, 2.2, segs[-1])
    silent = tmp / 'silent.mp4'
    total = t.join(segs, durs, silent, xfade=0.3)
    bed = tmp / 'bed.m4a'
    t.ambient_bed(bed, total)
    out.mkdir(parents=True, exist_ok=True)
    t.mux_audio(silent, bed, out / 'reel.mp4')
    t.ff(['-ss', 0.9, '-i', out / 'reel.mp4', '-frames:v', 1, '-q:v', 2, out / 'cover.jpg'])
    n = sum(ord(ch) for ch in x['slug'])
    cr = []
    for v in used:
        if v['license'] == 'Pexels License':
            cr.append(f"🎥 Video: {v['artist']} via Pexels")
        else:
            cr.append(f"📷 {credit_line(v)} via Wikimedia Commons, cropped with text added")
    cap = (f"{hook}\n\n{c['fact']}\n\n📍 {x['name']}, {x['city']}\n{SAVES[n % len(SAVES)]}\n\n{CTAS[n % len(CTAS)]}\n\n"
           f"#{tagify(x['city'])}travel #{tagify(x['city'])} #{c['tag']} #traveltips #citybreak\n\n" + '\n'.join(cr))
    (out / 'caption.txt').write_text(cap, encoding='utf-8')
    (out / 'title.txt').write_text(c.get('title') or hook, encoding='utf-8')


def render_tour(sh, job, stops, copy, out):
    """stops: landmarks of one city, in walking order; cover plus one slide per stop."""
    import th_media as t
    city = job['city']
    coords = [tuple(s.get('deck') or (s['lat'], s['lon'])) for s in stops]
    idx, _, _ = t.plan_route(coords)
    route = [stops[i] for i in idx][:8]
    n = len(route)
    legs = [t.hav(tuple(a.get('deck') or (a['lat'], a['lon'])), tuple(b.get('deck') or (b['lat'], b['lon']))) * t.STREET_FACTOR
            for a, b in zip(route, route[1:])]
    total_km = sum(legs)
    out.mkdir(parents=True, exist_ok=True)
    cover = route[0] if route[0]['photo']['width'] >= route[0]['photo']['height'] * .6 else route[1]
    t.photo_cover(sh, out / '01.jpg', str(ROOT / cover['photo']['path']), 'A WALK THROUGH', t.esc(city),
                  'on foot', f'{n} stops &nbsp;·&nbsp; about {total_km:.1f} km')
    for i, s in enumerate(route):
        walk = f'{legs[i] / t.WALK_KMH * 60:.0f} MIN WALK TO NEXT' if i < n - 1 else 'LAST STOP'
        t.photo_stop(sh, out / f'{i + 2:02d}.jpg', str(ROOT / s['photo']['path']), credit_short(s['photo']),
                     f'STOP {i + 1:02d} &nbsp;·&nbsp; {walk}', s['name'], copy[s['slug']]['fact'], i + 1, n)
    t.end_card(sh, out / f'{n + 2:02d}.jpg', 1080, 1350, f'Plan your <i>{t.esc(city)}</i> walk',
               'Swipe the landmarks you love. Travelhour turns them into one walking route.',
               'Photos: Wikimedia Commons · full credits in caption')
    lines = '\n'.join(f'{i + 1}. {s["name"]}' for i, s in enumerate(route))
    creds = '\n'.join(f'{s["name"]}: {credit_line(s["photo"])}' for s in route)
    tag = tagify(city)
    cap = (f"{city} on foot: {n} stops, about {total_km:.1f} km. Swipe for what to look for at each one →\n\n{lines}\n\n"
           f"📌 Save this for your trip. Which stop would you start with?\n\n{CTAS[len(city) % len(CTAS)]}\n\n"
           f"#{tag}travel #{tag}itinerary #walkingtour #citybreak #traveltips\n\n"
           f"Distances are estimates: straight line between stops plus 30% for streets.\n\n"
           f"📷 Photos via Wikimedia Commons, cropped with text added\n{creds}")
    (out / 'caption.txt').write_text(cap, encoding='utf-8')
    (out / 'title.txt').write_text(f'{city} on foot: {n} stops, what to look for', encoding='utf-8')


def folder(job):
    if job['kind'] == 'spotlight':
        return f"{job['day']}-{job['slug']}-spotlight"
    slug = job['city'].lower().replace(' ', '-')
    return f"{job['day']}-{slug}-" + dict(reel='route-reel', carousel='order-carousel', tour='walk-carousel')[job['kind']]


def render(i, n):
    import th_media as t
    import make_city
    lm, copy, _ = data()
    by_slug = {x['slug']: x for x in lm}
    jobs = json.load(open(ROOT / 'data/render_plan.json'))
    with t.Shooter() as sh:
        for k, job in enumerate(jobs):
            if k % n != i:
                continue
            out = ROOT / 'posts' / folder(job)
            if (out / 'caption.txt').exists():
                continue
            print(k, folder(job), flush=True)
            if job['kind'] == 'spotlight':
                render_spotlight(sh, job, by_slug[job['slug']], copy[job['slug']], out)
            elif job['kind'] == 'tour':
                stops = [x for x in lm if x['city'] == job['city'] and x['slug'] in copy and x.get('photo')
                         and (x.get('deck') or x.get('lat'))]
                render_tour(sh, job, stops, copy, out)
    for k, job in enumerate(jobs):  # make_city opens its own browser
        if k % n == i and job['kind'] in ('reel', 'carousel') and not (ROOT / 'posts' / folder(job) / 'caption.txt').exists():
            print(k, folder(job), flush=True)
            make_city.main(job['city'], job['kind'], job['day'])


# ---------------------------------------------------------------- calendar ---
def calendar():
    jobs = json.load(open(ROOT / 'data/render_plan.json'))
    days, missing = {}, []
    for job in jobs:
        d = ROOT / 'posts' / folder(job)
        if not (d / 'caption.txt').exists():
            missing.append(folder(job))
            continue
        base = f"{RAW}/posts/{folder(job)}"
        text = (d / 'caption.txt').read_text(encoding='utf-8')
        title = (d / 'title.txt').read_text(encoding='utf-8').strip()
        info = dict(autoPublish=True, descendants=[], draft=False, firstCommentText='', hasNotReadNotes=False, mediaAltText=[],
                    providers=[dict(network='instagram'), dict(network='tiktok'), dict(network='facebook')],
                    publicationDate=dict(dateTime=job['slot'] + ':00', timezone=TZ), shortener=False,
                    smartLinkData=dict(ids=[]), text=text)
        tiktok = dict(privacyOption='PUBLIC_TO_EVERYONE', commercialContentOwnBrand=True, title=title[:90])
        if job['kind'] in ('spotlight', 'reel'):
            info.update(media=[f'{base}/reel.mp4'], videoThumbnailUrl=f'{base}/cover.jpg',
                        instagramData=dict(type='REEL', showReelOnFeed=True,
                                           audioConfiguration=dict(audioId=job['audio'], videoVolume=0)),
                        facebookData=dict(type='REEL', title=title[:90]),
                        tiktokData=dict(tiktok, autoAddMusic=False))
        else:
            files = sorted(p.name for p in d.glob('*.jpg'))
            info.update(media=[f'{base}/{f}' for f in files], instagramData=dict(type='POST'),
                        facebookData=dict(type='POST'), tiktokData=dict(tiktok, autoAddMusic=True))
        days.setdefault(job['day'], []).append(dict(slot=job['slot'], date=job['slot'] + ':00+03:00', kind=job['kind'],
                                                    city=job['city'], folder=folder(job), info=info))
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
