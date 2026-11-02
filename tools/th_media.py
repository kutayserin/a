"""TravelHour social media renderer: brand slides, reels, route maps, audio bed."""
import html, itertools, json, math, os, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE / 'fonts'
LOGO = HERE / 'logo.png'
CREAM, INK, TERRA, OCHRE, MIST, PARCH = '#FAF6EE', '#1A1410', '#7A2F22', '#C97B3F', '#8B7E6E', '#E8E1D3'
FPS = 30
HOOK_DUR, STOP_DUR, END_DUR, XFADE = 2.0, 1.6, 2.6, 0.3
LATIN = ('U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,'
         'U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD')
LATIN_EXT = 'U+0100-0130,U+0132-02BA,U+02BD-02C5,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2C60-2C7F,U+A720-A7FF'


def _face(fam, style, file, rng):
    return (f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:100 900;font-display:block;"
            f"src:url('file://{FONTS / file}') format('woff2');unicode-range:{rng}}}")


FONT_CSS = ''.join([
    _face('Fraunces', 'normal', 'fraunces-latin-full-normal.woff2', LATIN),
    _face('Fraunces', 'normal', 'fraunces-latin-ext-full-normal.woff2', LATIN_EXT),
    _face('Fraunces', 'italic', 'fraunces-latin-full-italic.woff2', LATIN),
    _face('Fraunces', 'italic', 'fraunces-latin-ext-full-italic.woff2', LATIN_EXT),
    _face('Inter', 'normal', 'inter-latin-wght-normal.woff2', LATIN),
    _face('Inter', 'normal', 'inter-latin-ext-wght-normal.woff2', LATIN_EXT),
])


def esc(s):
    return html.escape(s, quote=True)


def page(w, h, body, css, bg='transparent'):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{FONT_CSS}'
            f'*{{box-sizing:border-box}}html,body{{margin:0;width:{w}px;height:{h}px;background:{bg};'
            f'overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}}{css}</style></head>'
            f'<body>{body}</body></html>')


class Shooter:
    """One Chromium instance for every still and frame."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.tmp = tempfile.mkdtemp()
        return self

    def __exit__(self, *a):
        self.browser.close()
        self._pw.stop()

    def open(self, doc, w, h):
        pg = self.browser.new_page(viewport={'width': w, 'height': h})
        path = Path(self.tmp) / f'p{random.randrange(10**9)}.html'
        path.write_text(doc, encoding='utf-8')
        pg.goto(f'file://{path}')
        pg.evaluate('document.fonts.ready')
        pg.wait_for_load_state('networkidle')
        return pg

    def shot(self, doc, out, w, h, transparent=False, quality=92):
        pg = self.open(doc, w, h)
        out = str(out)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if out.endswith('.png'):
            pg.screenshot(path=out, omit_background=transparent)
        else:
            pg.screenshot(path=out, type='jpeg', quality=quality)
        pg.close()


def ff(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + [str(a) for a in args],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {r.stderr[-1500:]}')


# ------------------------------------------------------------------ Audio ---

def ambient_bed(out, seconds):
    """Soft synthesised pad: original, so no licence travels with it."""
    import numpy as np
    sr = 44100
    n = int(sr * seconds)
    t = np.arange(n) / sr
    midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
    chords = [[48, 55, 59, 62, 64], [45, 52, 55, 60, 64], [41, 48, 57, 60, 64], [43, 50, 55, 59, 62]]
    span, fade = 5.0, 1.8
    left, right = np.zeros(n), np.zeros(n)
    for k in range(int(seconds / span) + 2):
        start = k * span - fade / 2
        env = np.clip((t - start) / fade, 0, 1) * np.clip((start + span + fade - t) / fade, 0, 1)
        env = np.sin(env * np.pi / 2) ** 2
        for i, m in enumerate(chords[k % 4]):
            f = midi(m)
            amp = 0.9 / (1 + i * 0.35)
            for d, pan in ((-0.0016, 0.3), (0.0, 0.5), (0.0016, 0.7)):
                ph = 2 * np.pi * f * (1 + d) * t + k + i
                v = amp * env * (np.sin(ph) + 0.12 * np.sin(2 * ph))
                left += v * (1 - pan)
                right += v * pan
    lfo = 0.9 + 0.1 * np.sin(2 * np.pi * 0.11 * t)
    st = np.stack([left, right], axis=1) * lfo[:, None]
    st /= np.abs(st).max()
    st *= 0.32
    edge = np.minimum(np.minimum(t / 0.6, (seconds - t) / 1.2), 1.0).clip(0, 1)
    st *= edge[:, None]
    raw = Path(tempfile.mkdtemp()) / 'bed.f32'
    st.astype('float32').tofile(raw)
    ff(['-f', 'f32le', '-ar', sr, '-ac', 2, '-i', raw, '-c:a', 'aac', '-b:a', '160k', out])


def mux_audio(video, audio, out):
    ff(['-i', video, '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest',
        '-movflags', '+faststart', out])


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


# ------------------------------------------------------------------ Reels ---

REEL_CSS = f"""
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,20,16,.55) 0%,
  rgba(26,20,16,0) 22%,rgba(26,20,16,0) 45%,rgba(26,20,16,.88) 78%,rgba(26,20,16,.92) 100%)}}
.bars{{position:absolute;top:110px;left:70px;right:70px;display:flex;gap:10px}}
.bar{{flex:1;height:6px;border-radius:3px;background:rgba(250,246,238,.32)}}
.bar.done{{background:{CREAM}}} .bar.now{{background:{OCHRE}}}
.credit{{position:absolute;top:140px;right:70px;font:500 22px 'Inter';color:rgba(250,246,238,.78)}}
.block{{position:absolute;left:80px;right:180px;bottom:480px}}
.eyebrow{{font:700 32px 'Inter';letter-spacing:.2em;color:{OCHRE};text-transform:uppercase}}
.name{{font:600 104px/1.02 'Fraunces';color:{CREAM};margin-top:18px;letter-spacing:-.01em}}
.hookwrap{{position:absolute;left:80px;right:120px;top:560px;text-shadow:0 2px 28px rgba(0,0,0,.35)}}
.hk-eyebrow{{font:700 34px 'Inter';letter-spacing:.24em;color:{CREAM}}}
.hk-city{{font:600 250px/.9 'Fraunces';color:{CREAM};margin-top:26px;letter-spacing:-.02em}}
.hk-sub{{font:italic 500 128px/1 'Fraunces';color:{CREAM};margin-top:6px}}
.hk-meta{{font:600 40px 'Inter';color:{CREAM};margin-top:48px;letter-spacing:.04em}}
.hk-save{{position:absolute;left:80px;bottom:470px;font:700 34px 'Inter';color:{CREAM};
  letter-spacing:.14em;padding:18px 30px;border:3px solid {CREAM};border-radius:60px}}
.hookshade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,20,16,.30) 0%,
  rgba(26,20,16,.66) 26%,rgba(26,20,16,.66) 64%,rgba(26,20,16,.40) 100%)}}
"""

END_PILL = 'Free on the App Store'


def end_card(sh, out, w, h, headline_html, sub, foot='', pill=END_PILL):
    css = f"""
.wrap{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;padding:0 90px}}
.logo{{width:{int(w * .58)}px}}
.rule{{width:90px;height:3px;background:{OCHRE};margin:{int(h * .045)}px 0}}
.hl{{font:600 {int(w * .082)}px/1.08 'Fraunces';color:{INK};letter-spacing:-.01em}}
.hl i{{font-weight:500;color:{TERRA}}}
.sub{{font:500 {int(w * .036)}px/1.45 'Inter';color:{MIST};margin-top:30px;max-width:840px}}
.pill{{margin-top:{int(h * .04)}px;background:{INK};color:{CREAM};font:700 {int(w * .036)}px 'Inter';
  letter-spacing:.04em;padding:26px 54px;border-radius:80px}}
.link{{margin-top:22px;font:600 {int(w * .028)}px 'Inter';color:{MIST};letter-spacing:.04em}}
.foot{{position:absolute;left:60px;right:60px;bottom:{int(h * .06)}px;text-align:center;
  font:500 {int(w * .022)}px/1.4 'Inter';color:{MIST}}}
"""
    body = (f'<div class="wrap"><img class="logo" src="file://{LOGO}"><div class="rule"></div>'
            f'<div class="hl">{headline_html}</div><div class="sub">{esc(sub)}</div>'
            f'<div class="pill">{esc(pill)}</div><div class="link">Link in bio</div></div>'
            f'<div class="foot">{esc(foot)}</div>')
    sh.shot(page(w, h, body, css, bg=CREAM), out, w, h)


def photo_segment(img, overlay, dur, out, zoom_in=True, darken=False):
    frames = int(round(dur * FPS))
    z = f"1+0.08*on/{frames}" if zoom_in else f"1.08-0.08*on/{frames}"
    crop = "crop=if(gt(iw/ih\\,9/16)\\,ih*9/16\\,iw):if(gt(iw/ih\\,9/16)\\,ih\\,iw*16/9)"
    grade = ',eq=saturation=1.06:contrast=1.03' + (':brightness=-0.03' if darken else '')
    fc = (f"[0:v]{crop},scale=2160:3840{grade},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS},"
          f"setsar=1[bg];[1:v]format=rgba,fade=in:st=0.1:d=0.35:alpha=1[ov];"
          f"[bg][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
    ff(['-i', img, '-loop', 1, '-t', dur, '-i', overlay, '-filter_complex', fc,
        '-map', '[v]', '-frames:v', frames, '-r', FPS, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 17, out])


def still_segment(png, dur, out):
    frames = int(round(dur * FPS))
    ff(['-loop', 1, '-t', dur, '-i', png, '-vf', f'scale=1080:1920,fps={FPS},format=yuv420p',
        '-frames:v', frames, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 17, out])


def join(segments, durations, out, xfade=XFADE):
    inputs, fc, prev, offset = [], [], '0:v', 0.0
    for s in segments:
        inputs += ['-i', s]
    for k in range(1, len(segments)):
        offset += durations[k - 1] - xfade
        label = f'v{k}'
        fc.append(f'[{prev}][{k}:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[{label}]')
        prev = label
    fc.append(f'[{prev}]scale=out_range=tv:out_color_matrix=bt709,format=yuv420p[out]')
    ff(inputs + ['-filter_complex', ';'.join(fc), '-map', '[out]',
                 '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                 '-c:v', 'libx264', '-preset', 'slow', '-crf', 20, '-pix_fmt', 'yuv420p', '-an',
                 '-movflags', '+faststart', out])
    return sum(durations) - xfade * (len(segments) - 1)


def photo_reel(sh, title, stops, hook_photo, out_dir, sub='Swipe the landmarks you love. Travelhour turns them into one walking route.',
               foot='Photos: Wikimedia Commons · full credits in caption'):
    """stops: list of dict(time,name,photo,credit)."""
    tmp = Path(tempfile.mkdtemp())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = (f'<div class="hookshade"></div><div class="hookwrap"><div class="hk-eyebrow">A WALKING DAY IN</div>'
            f'<div class="hk-city">{esc(title)}</div><div class="hk-sub">in one day</div>'
            f'<div class="hk-meta">{len(stops)} stops &nbsp;·&nbsp; {stops[0]["time"]} → {stops[-1]["time"]}</div></div>'
            f'<div class="hk-save">SAVE FOR YOUR TRIP</div>')
    sh.shot(page(1080, 1920, body, REEL_CSS), tmp / 'hook.png', 1080, 1920, transparent=True)
    segs, durs = [tmp / 'seg_hook.mp4'], [HOOK_DUR]
    photo_segment(hook_photo, tmp / 'hook.png', HOOK_DUR, segs[0], zoom_in=False, darken=True)
    n = len(stops)
    for i, s in enumerate(stops):
        bars = ''.join(f'<div class="bar {"done" if k < i else "now" if k == i else ""}"></div>' for k in range(n))
        body = (f'<div class="shade"></div><div class="bars">{bars}</div>'
                f'<div class="credit">Photo: {esc(s["credit"])}</div>'
                f'<div class="block"><div class="eyebrow">{i + 1:02d} / {n:02d} &nbsp;·&nbsp; {s["time"]}</div>'
                f'<div class="name">{esc(s["name"])}</div></div>')
        ov = tmp / f'stop{i}.png'
        sh.shot(page(1080, 1920, body, REEL_CSS), ov, 1080, 1920, transparent=True)
        seg = tmp / f'seg{i}.mp4'
        photo_segment(s['photo'], ov, STOP_DUR, seg, zoom_in=i % 2 == 0)
        segs.append(seg)
        durs.append(STOP_DUR)
    end = tmp / 'end.png'
    end_card(sh, end, 1080, 1920, 'Plan a day in <i>any</i> city', sub, foot)
    segs.append(tmp / 'seg_end.mp4')
    durs.append(END_DUR)
    still_segment(end, END_DUR, segs[-1])
    silent = tmp / 'silent.mp4'
    total = join(segs, durs, silent)
    bed = tmp / 'bed.m4a'
    ambient_bed(bed, total)
    mux_audio(silent, bed, out_dir / 'reel.mp4')
    ff(['-ss', 0.9, '-i', out_dir / 'reel.mp4', '-frames:v', 1, '-q:v', 2, out_dir / 'cover.jpg'])
    return total


# -------------------------------------------------------------- Carousels ---

CAR_CSS = f"""
.full{{position:absolute;inset:0;background-size:cover;background-position:center}}
.cshade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(26,20,16,.25) 0%,
  rgba(26,20,16,.05) 35%,rgba(26,20,16,.78) 72%,rgba(26,20,16,.9) 100%)}}
.cv{{position:absolute;left:80px;right:80px;bottom:120px}}
.cv-eyebrow{{font:700 28px 'Inter';letter-spacing:.24em;color:{OCHRE}}}
.cv-city{{font:600 190px/.92 'Fraunces';color:{CREAM};margin-top:18px;letter-spacing:-.02em}}
.cv-sub{{font:italic 500 96px/1 'Fraunces';color:{CREAM}}}
.cv-meta{{font:600 34px 'Inter';color:{CREAM};margin-top:34px}}
.cv-swipe{{position:absolute;right:80px;top:80px;font:700 26px 'Inter';letter-spacing:.16em;
  color:{CREAM};padding:14px 24px;border:2px solid rgba(250,246,238,.8);border-radius:40px}}
.ph{{position:absolute;left:0;right:0;top:0;height:860px;background-size:cover;background-position:center}}
.ph-credit{{position:absolute;right:28px;top:814px;font:500 19px 'Inter';color:rgba(250,246,238,.92);
  text-shadow:0 1px 6px rgba(0,0,0,.75)}}
.panel{{position:absolute;left:0;right:0;top:860px;bottom:0;background:{CREAM};padding:52px 80px 0}}
.st-eyebrow{{font:700 26px 'Inter';letter-spacing:.2em;color:{TERRA}}}
.st-name{{font:600 76px/1.04 'Fraunces';color:{INK};margin-top:14px;letter-spacing:-.01em}}
.st-tip{{font:500 32px/1.42 'Inter';color:{MIST};margin-top:18px;max-width:920px}}
.st-foot{{position:absolute;left:80px;right:80px;bottom:44px;display:flex;justify-content:space-between;
  font:600 22px 'Inter';color:{MIST};letter-spacing:.06em}}
"""


def photo_cover(sh, out, photo, eyebrow, big, sub, meta, big_css=''):
    body = (f'<div class="full" style="background-image:url(\'file://{photo}\')"></div>'
            f'<div class="cshade"></div><div class="cv-swipe">SWIPE →</div>'
            f'<div class="cv"><div class="cv-eyebrow">{esc(eyebrow)}</div>'
            f'<div class="cv-city" style="{big_css}">{big}</div><div class="cv-sub">{sub}</div>'
            f'<div class="cv-meta">{meta}</div></div>')
    sh.shot(page(1080, 1350, body, CAR_CSS, bg=INK), out, 1080, 1350)


def photo_stop(sh, out, photo, credit, eyebrow, name, tip, idx, total, pos='center'):
    body = (f'<div class="ph" style="background-image:url(\'file://{photo}\');background-position:{pos}"></div>'
            f'<div class="ph-credit">Photo: {esc(credit)}</div>'
            f'<div class="panel"><div class="st-eyebrow">{eyebrow}</div>'
            f'<div class="st-name">{esc(name)}</div><div class="st-tip">{esc(tip)}</div>'
            f'<div class="st-foot"><span>TRAVELHOUR.APP</span><span>{idx:02d} / {total:02d}</span></div></div>')
    sh.shot(page(1080, 1350, body, CAR_CSS, bg=CREAM), out, 1080, 1350)


# ----------------------------------------------------------------- Routes ---

STREET_FACTOR = 1.3  # lib/services/walking_routes.dart
WALK_KMH = 4.5


def hav(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def path_len(order, d):
    return sum(d[order[i]][order[i + 1]] for i in range(len(order) - 1))


def plan_route(pts):
    """Port of RoutePlanner.order (lib/services/route_planner.dart):
    nearest-neighbour from every start, 2-opt each, keep the shortest open path."""
    n = len(pts)
    d = [[hav(pts[i], pts[j]) for j in range(n)] for i in range(n)]
    best, best_len = None, float('inf')
    for s in range(n):
        route, left = [s], set(range(n)) - {s}
        while left:
            nxt = min(left, key=lambda j: d[route[-1]][j])
            route.append(nxt)
            left.remove(nxt)
        improved = True
        while improved:
            improved = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                    if path_len(cand, d) + 1e-9 < path_len(route, d):
                        route, improved = cand, True
        ln = path_len(route, d)
        if ln < best_len:
            best, best_len = route, ln
    return best, best_len, d


def random_baseline(d):
    """Mean over every visiting order, plus a real order whose length sits nearest that mean."""
    n = len(d)
    orders = list(itertools.permutations(range(n)))
    lens = [path_len(o, d) for o in orders]
    mean = sum(lens) / len(lens)
    rng = random.Random(7)
    near = sorted(range(len(orders)), key=lambda i: abs(lens[i] - mean))[:200]
    pick = orders[rng.choice(near)]
    return mean, list(pick), path_len(pick, d)


def project(pts, x0, y0, w, h, pad=70):
    lat0 = sum(p[0] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    xs = [p[1] * k for p in pts]
    ys = [-p[0] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sc = min((w - 2 * pad) / max(maxx - minx, 1e-6), (h - 2 * pad) / max(maxy - miny, 1e-6))
    ox = x0 + (w - (maxx - minx) * sc) / 2
    oy = y0 + (h - (maxy - miny) * sc) / 2
    px_per_km = sc / 111.195
    return [(ox + (x - minx) * sc, oy + (y - miny) * sc) for x, y in zip(xs, ys)], px_per_km


def map_svg(pts, order, w, h, line, dot, text, grid, width=7, num_size=30, r=30):
    """Static numbered route map, north up."""
    xy, ppk = project(pts, 0, 0, w, h)
    g = ''.join(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{grid}" stroke-width="1.5"/>' for x in range(0, w + 1, 90))
    g += ''.join(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{grid}" stroke-width="1.5"/>' for y in range(0, h + 1, 90))
    poly = ' '.join(f'{xy[i][0]:.1f},{xy[i][1]:.1f}' for i in order)
    marks = ''
    for rank, i in enumerate(order):
        x, y = xy[i]
        marks += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{dot}"/>'
                  f'<text x="{x:.1f}" y="{y + num_size * .35:.1f}" text-anchor="middle" font-family="Inter" '
                  f'font-weight="700" font-size="{num_size}" fill="{text}">{rank + 1}</text>')
    km = 1 if ppk > 90 else 2 if ppk > 45 else 5
    bar = ppk * km
    scale = (f'<line x1="24" y1="{h - 26}" x2="{24 + bar:.1f}" y2="{h - 26}" stroke="{MIST}" stroke-width="4"/>'
             f'<text x="24" y="{h - 40}" font-family="Inter" font-weight="600" font-size="22" fill="{MIST}">{km} km</text>')
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{g}'
            f'<polyline points="{poly}" fill="none" stroke="{line}" stroke-width="{width}" stroke-linejoin="round" '
            f'stroke-linecap="round"/>{marks}{scale}</svg>')


ORDER_CSS = f"""
.pad{{position:absolute;inset:0;padding:84px 80px}}
.eb{{font:700 26px 'Inter';letter-spacing:.2em;color:{TERRA}}}
.h1{{font:600 104px/1.0 'Fraunces';color:{INK};letter-spacing:-.02em;margin-top:22px}}
.h1 i{{font-weight:500;color:{TERRA}}}
.h2{{font:600 66px/1.05 'Fraunces';color:{INK};letter-spacing:-.01em;margin-top:18px}}
.h2 i{{font-weight:500;color:{TERRA}}}
.km{{font:600 150px/1 'Fraunces';letter-spacing:-.02em;margin-top:10px}}
.note{{font:500 30px/1.4 'Inter';color:{MIST};margin-top:14px}}
.mapbox{{position:absolute;left:60px;right:60px;border:2px solid {PARCH};border-radius:26px;background:#FFFDF8;overflow:hidden}}
.foot{{position:absolute;left:80px;right:80px;bottom:44px;display:flex;justify-content:space-between;font:600 22px 'Inter';color:{MIST};letter-spacing:.06em}}
.swipe{{position:absolute;right:80px;top:78px;font:700 24px 'Inter';letter-spacing:.14em;color:{INK};padding:12px 22px;border:2px solid {INK};border-radius:40px}}
.twin{{position:absolute;left:60px;right:60px;top:560px;display:flex;gap:24px}}
.tw{{flex:1}}
.tw .mapbox{{position:relative;left:0;right:0}}
.tl{{font:700 24px 'Inter';letter-spacing:.14em;margin-bottom:14px}}
.tk{{font:600 76px/1 'Fraunces';margin-top:18px;letter-spacing:-.01em}}
.row{{display:flex;align-items:center;gap:26px;padding:27px 0;border-bottom:2px solid {PARCH}}}
.nm{{width:60px;height:60px;border-radius:30px;background:{TERRA};color:{CREAM};font:700 28px/60px 'Inter';text-align:center;flex:none}}
.rn{{font:600 42px/1.1 'Fraunces';color:{INK};flex:1}}
.rk{{font:600 27px 'Inter';color:{MIST};white-space:nowrap}}
"""


def order_carousel(sh, city, stops, out_dir, first=None):
    """stops: list of dict(name,lat,lon). Writes 01..05.jpg and returns the numbers used in the caption.
    first: name of the stop to start from when the route's far end is that stop."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pts = [(s['lat'], s['lon']) for s in stops]
    order, straight, d = plan_route(pts)
    if first and stops[order[-1]]['name'] == first:
        order.reverse()
    mean, rand_order, _ = random_baseline(d)
    best_km = straight * STREET_FACTOR
    rand_km = mean * STREET_FACTOR
    diff = rand_km - best_km
    n = len(stops)
    foot = '<div class="foot"><span>TRAVELHOUR.APP</span><span>{}</span></div>'
    bad = lambda w, h, **k: map_svg(pts, rand_order, w, h, OCHRE, OCHRE, CREAM, '#F4EEE1', **k)
    good = lambda w, h, **k: map_svg(pts, order, w, h, TERRA, TERRA, CREAM, '#F4EEE1', **k)
    body = (f'<div class="pad"><div class="eb">THE ORDER MATTERS · {esc(city.upper())}</div>'
            f'<div class="h1" style="margin-top:60px">Same {n} stops.<br><i>{diff:.0f} km</i> less walking.</div></div>'
            f'<div class="swipe" style="top:auto;bottom:104px">SWIPE →</div>'
            f'<div class="twin"><div class="tw"><div class="tl" style="color:{OCHRE}">RANDOM ORDER</div>'
            f'<div class="mapbox">{bad(468, 430, width=5, num_size=20, r=19)}</div>'
            f'<div class="tk" style="color:{OCHRE}">{rand_km:.1f} km</div></div>'
            f'<div class="tw"><div class="tl" style="color:{TERRA}">SHORTEST ORDER</div>'
            f'<div class="mapbox">{good(468, 430, width=5, num_size=20, r=19)}</div>'
            f'<div class="tk" style="color:{TERRA}">{best_km:.1f} km</div></div></div>'
            + foot.format(f'01 / 05'))
    sh.shot(page(1080, 1350, body, ORDER_CSS, bg=CREAM), out / '01.jpg', 1080, 1350)
    body = (f'<div class="pad"><div class="eb">IN A RANDOM ORDER</div><div class="h2">{n} famous stops, no plan</div>'
            f'<div class="km" style="color:{OCHRE}">{rand_km:.1f} km</div></div>'
            f'<div class="mapbox" style="top:420px;height:790px">{bad(956, 790)}</div>'
            f'<div class="foot" style="font-weight:500;letter-spacing:0"><span>Average of every possible order. This map is one of them.</span><span style="font-weight:600;letter-spacing:.06em">02 / 05</span></div>')
    sh.shot(page(1080, 1350, body, ORDER_CSS, bg=CREAM), out / '02.jpg', 1080, 1350)
    body = (f'<div class="pad"><div class="eb">THE SAME STOPS, SORTED</div><div class="h2">One line across {esc(city)}</div>'
            f'<div class="km" style="color:{TERRA}">{best_km:.1f} km</div></div>'
            f'<div class="mapbox" style="top:420px;height:790px">{good(956, 790)}</div>'
            + foot.format('03 / 05'))
    sh.shot(page(1080, 1350, body, ORDER_CSS, bg=CREAM), out / '03.jpg', 1080, 1350)
    rows = ''
    for rank, i in enumerate(order):
        leg = '' if rank == 0 else f'{d[order[rank - 1]][i] * STREET_FACTOR:.1f} km'
        rows += (f'<div class="row"><div class="nm">{rank + 1}</div><div class="rn">{esc(stops[i]["name"])}</div>'
                 f'<div class="rk">{leg}</div></div>')
    body = (f'<div class="pad"><div class="eb">SAVE THIS ORDER</div><div class="h2" style="margin-bottom:26px">{esc(city)}, stop by stop</div>{rows}</div>'
            + foot.format('04 / 05'))
    sh.shot(page(1080, 1350, body, ORDER_CSS, bg=CREAM), out / '04.jpg', 1080, 1350)
    end_card(sh, out / '05.jpg', 1080, 1350, 'Swipe what you want to see. <i>We sort the walk.</i>',
             'Travelhour tests a route from every stop, straightens the crossings, then guides you with live directions.',
             f'Distances are estimates: straight line between stops plus 30% for streets, as in the app.')
    return dict(order=[stops[i]['name'] for i in order], best_km=best_km, rand_km=rand_km, diff=diff,
                walk_h=best_km / WALK_KMH)


REEL_MAP_JS = """
const S = %s;
function setT(t){
  const prog = document.getElementById('prog');
  const legs = S.legs, xy = S.xy, ord = S.order;
  let done = 0, active = -1, frac = 0;
  for (let i=0;i<legs.length;i++){
    const a = S.start + i*S.step, b = a + S.draw;
    if (t>=b) done = i+1;
    else if (t>=a){ active=i; frac=(t-a)/S.draw; frac=frac*frac*(3-2*frac); break; }
    else break;
  }
  let pts = xy[ord[0]].join(',');
  for (let i=0;i<done;i++) pts += ' '+xy[ord[i+1]].join(',');
  if (active>=0){
    const p=xy[ord[active]], q=xy[ord[active+1]];
    pts += ' '+(p[0]+(q[0]-p[0])*frac)+','+(p[1]+(q[1]-p[1])*frac);
  }
  prog.setAttribute('points', t>=S.start ? pts : '');
  const reached = t<S.start ? -1 : done + ((active>=0 && frac>0.98)?1:0);
  ord.forEach((k,r)=>{
    const c=document.getElementById('c'+r), n=document.getElementById('n'+r);
    const on = r<=reached;
    const appear = Math.min(1,Math.max(0,(t-0.25-r*0.09)/0.3));
    c.setAttribute('fill', on? S.ochre : S.dim);
    c.setAttribute('opacity', appear); n.setAttribute('opacity', appear);
    n.setAttribute('fill', on? S.ink : S.cream);
    c.setAttribute('r', r===reached ? 37 : 30);
  });
  const hook = document.getElementById('hook');
  hook.style.opacity = t<S.start-0.15 ? 1 : Math.max(0,1-(t-(S.start-0.15))/0.25);
  const panel=document.getElementById('panel');
  const finished = t >= S.start + legs.length*S.step + 0.15;
  panel.style.opacity = (t>=S.start && !finished) ? Math.min(1,(t-S.start)/0.2) : 0;
  const idx = Math.max(0,Math.min(ord.length-1,reached));
  document.getElementById('pe').textContent = String(idx+1).padStart(2,'0')+' / '+String(ord.length).padStart(2,'0');
  document.getElementById('pn').textContent = S.names[idx];
  document.getElementById('pk').textContent = idx===0 ? 'Start here' : S.cum[idx].toFixed(1)+' km walked';
  const sum=document.getElementById('sum');
  sum.style.opacity = finished ? Math.min(1,(t-(S.start+legs.length*S.step+0.15))/0.3) : 0;
}
"""


def route_reel(sh, city, stops, out_dir, sub='Swipe the places you want. Travelhour sorts them into one walk.', first=None):
    """Animated map reel: needs no photographs, so it works for any city."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    pts = [(s['lat'], s['lon']) for s in stops]
    order, straight, d = plan_route(pts)
    if first and stops[order[-1]]['name'] == first:
        order.reverse()
    km = straight * STREET_FACTOR
    W, H = 1080, 1920
    MY, MH = 210, 900
    xy, ppk = project(pts, 40, MY, W - 80, MH, pad=80)
    cum, tot = [0.0], 0.0
    for r in range(1, len(order)):
        tot += d[order[r - 1]][order[r]] * STREET_FACTOR
        cum.append(tot)
    n = len(stops)
    start, step, draw = 2.3, 1.45, 0.85
    st = dict(xy=[[round(a, 1), round(b, 1)] for a, b in xy], order=order, legs=[0] * (n - 1), start=start, step=step, draw=draw,
              names=[stops[i]['name'] for i in order], cum=cum, ochre=OCHRE, dim='#4A3D32', ink=INK, cream=CREAM)
    grid = ''.join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#2A221B" stroke-width="1.5"/>' for x in range(0, W + 1, 90))
    grid += ''.join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#2A221B" stroke-width="1.5"/>' for y in range(30, H + 1, 90))
    marks = ''.join(
        f'<circle id="c{r}" cx="{xy[i][0]:.1f}" cy="{xy[i][1]:.1f}" r="30"/>'
        f'<text id="n{r}" x="{xy[i][0]:.1f}" y="{xy[i][1] + 11:.1f}" text-anchor="middle" font-family="Inter" font-weight="700" font-size="31">{r + 1}</text>'
        for r, i in enumerate(order))
    bar_km = 1 if ppk > 90 else 2 if ppk > 45 else 5
    bar = (f'<line x1="70" y1="{MY + MH + 6}" x2="{70 + ppk * bar_km:.1f}" y2="{MY + MH + 6}" stroke="{MIST}" stroke-width="4"/>'
           f'<text x="70" y="{MY + MH - 10}" font-family="Inter" font-weight="600" font-size="24" fill="{MIST}">{bar_km} km</text>')
    css = f"""
#hook{{position:absolute;left:80px;right:80px;top:1150px}}
.he{{font:700 34px 'Inter';letter-spacing:.2em;color:{OCHRE}}}
.hc{{font:600 {170 if len(city) > 8 else 210}px/.94 'Fraunces';color:{CREAM};letter-spacing:-.02em;margin-top:18px}}
.hs{{font:italic 500 80px/1.02 'Fraunces';color:{CREAM};margin-top:6px}}
.hm{{font:600 36px 'Inter';color:{CREAM};margin-top:22px;letter-spacing:.03em}}
#panel,#sum{{position:absolute;left:80px;right:120px;top:1160px;opacity:0}}
.pe{{font:700 32px 'Inter';letter-spacing:.2em;color:{OCHRE}}}
.pn{{font:600 84px/1.04 'Fraunces';color:{CREAM};margin-top:14px;letter-spacing:-.01em}}
.pk{{font:600 36px 'Inter';color:#B9AD9C;margin-top:18px}}
.sb{{font:600 88px/1.04 'Fraunces';color:{CREAM};letter-spacing:-.01em}}
.sb i{{font-weight:500;color:{OCHRE}}}
"""
    body = (f'<svg style="position:absolute;inset:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{grid}{bar}'
            f'<polyline id="prog" fill="none" stroke="{OCHRE}" stroke-width="11" stroke-linejoin="round" stroke-linecap="round"/>{marks}</svg>'
            f'<div id="hook"><div class="he">THE SHORTEST WALK</div><div class="hc">{esc(city)}</div>'
            f'<div class="hs">{n} stops, one line</div><div class="hm">{km:.1f} km on foot · save for your trip</div></div>'
            f'<div id="panel"><div class="pe" id="pe"></div><div class="pn" id="pn"></div><div class="pk" id="pk"></div></div>'
            f'<div id="sum"><div class="sb">{n} stops. <i>{km:.1f} km.</i><br>About {km / WALK_KMH:.1f} hours on foot.</div></div>'
            f'<script>{REEL_MAP_JS % json.dumps(st)}</script>')
    pg = sh.open(page(W, H, body, css, bg=INK), W, H)
    map_dur = start + (n - 1) * step + 1.9
    frames = int(map_dur * FPS)
    silent_map = tmp / 'map.mp4'
    proc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS),
                             '-c:v', 'mjpeg', '-i', '-', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast',
                             '-crf', '17', str(silent_map)], stdin=subprocess.PIPE)
    for f in range(frames):
        pg.evaluate(f'setT({f / FPS})')
        proc.stdin.write(pg.screenshot(type='jpeg', quality=95))
    proc.stdin.close()
    proc.wait()
    pg.close()
    end = tmp / 'end.png'
    end_card(sh, end, W, H, 'Plan a day in <i>any</i> city', sub,
             'Distances are estimates: straight line between stops plus 30% for streets, as in the app.')
    still_segment(end, END_DUR, tmp / 'end.mp4')
    total = join([silent_map, tmp / 'end.mp4'], [frames / FPS, END_DUR], tmp / 'silent.mp4')
    bed = tmp / 'bed.m4a'
    ambient_bed(bed, total)
    mux_audio(tmp / 'silent.mp4', bed, out / 'reel.mp4')
    ff(['-ss', 1.2, '-i', out / 'reel.mp4', '-frames:v', 1, '-q:v', 2, out / 'cover.jpg'])
    return dict(order=st['names'], km=km, walk_h=km / WALK_KMH, seconds=total)
