"""website-automation social media renderer: slides, slideshow reels, audio bed."""
import html, json, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = HERE / 'fonts'
TEMPLATES = ROOT / 'assets/templates'
LOGO = (HERE / 'logo-horizontal.svg').read_text()
GREEN, TEAL, INK, GREY, MIST, BG, LINE = '#14906A', '#1A9387', '#14181A', '#4A5560', '#8A96A0', '#F5FAF8', '#DCE8E3'
FPS = 30
LATIN = ('U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD')
LATIN_EXT = 'U+0100-0130,U+0132-02BA,U+02BD-02C5,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2C60-2C7F,U+A720-A7FF'


def _face(fam, file, rng):
    return (f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:100 900;font-display:block;"
            f"src:url('file://{FONTS / file}') format('woff2');unicode-range:{rng}}}")


FONT_CSS = ''.join([
    _face('Jakarta', 'plus-jakarta-sans-latin-wght-normal.woff2', LATIN),
    _face('Jakarta', 'plus-jakarta-sans-latin-ext-wght-normal.woff2', LATIN_EXT),
    _face('Inter', 'inter-latin-wght-normal.woff2', LATIN),
    _face('Inter', 'inter-latin-ext-wght-normal.woff2', LATIN_EXT),
])

BASE_CSS = f"""
*{{box-sizing:border-box}}html,body{{margin:0;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased;
  background:radial-gradient(900px 620px at 85% -5%,#D5F2E6 0%,rgba(213,242,230,0) 70%),{BG}}}
em{{font-style:normal;color:{GREEN}}}
.eb{{font:700 26px 'Inter';letter-spacing:.17em;color:{GREEN};text-transform:uppercase}}
.h1{{font:800 96px/1.05 'Jakarta';color:{INK};letter-spacing:-.035em;margin-top:26px}}
.h2{{font:800 70px/1.08 'Jakarta';color:{INK};letter-spacing:-.03em;margin-top:22px}}
.body{{font:500 36px/1.42 'Inter';color:{GREY};margin-top:26px}}
.pad{{position:absolute;left:80px;right:80px;top:96px}}
.foot{{position:absolute;left:80px;right:80px;bottom:46px;display:flex;justify-content:space-between;font:600 23px 'Inter';color:{MIST};letter-spacing:.02em}}
.swipe{{position:absolute;right:80px;bottom:108px;font:700 25px 'Inter';letter-spacing:.1em;color:#fff;background:{INK};padding:15px 28px;border-radius:50px}}
.browser{{position:absolute;left:60px;right:60px;border-radius:24px;overflow:hidden;background:#fff;box-shadow:0 26px 70px rgba(20,24,26,.20)}}
.bar{{height:58px;background:#fff;display:flex;align-items:center;gap:10px;padding:0 22px;border-bottom:1.5px solid {LINE}}}
.dot{{width:15px;height:15px;border-radius:50%;background:{LINE}}}
.url{{margin-left:16px;font:500 21px 'Inter';color:{MIST}}}
.browser img{{display:block;width:100%}}
.num{{font:800 210px/1 'Jakarta';letter-spacing:-.05em;background:linear-gradient(135deg,{GREEN},{TEAL});-webkit-background-clip:text;color:transparent;margin-top:60px}}
.prompt{{position:absolute;left:60px;right:60px;background:#fff;border:3px solid {GREEN};border-radius:26px;padding:40px 44px;font:500 40px/1.5 'Inter';color:#B4BEC5;box-shadow:0 22px 60px rgba(20,144,106,.14)}}
.prompt b{{font-weight:600;color:{INK};background:#CFF1E2;border-radius:10px;padding:3px 10px;-webkit-box-decoration-break:clone;box-decoration-break:clone}}
.prompt .all{{color:{INK}}}
.wrap{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 80px}}
.logo svg{{width:760px;height:auto;display:block}}
.rule{{width:90px;height:5px;border-radius:5px;background:{GREEN};margin:44px 0}}
.pill{{margin-top:44px;background:linear-gradient(135deg,{GREEN},{TEAL});color:#fff;font:700 38px 'Inter';padding:27px 56px;border-radius:80px}}
.link{{margin-top:22px;font:600 30px 'Inter';color:{MIST}}}
.endfoot{{position:absolute;left:60px;right:60px;bottom:70px;text-align:center;font:500 24px/1.4 'Inter';color:{MIST}}}
.mid{{position:absolute;left:80px;right:80px;top:60px;bottom:110px;display:flex;flex-direction:column;justify-content:center}}
.mid .num{{font-size:250px;margin-top:40px}}.mid .h2{{font-size:84px;margin-top:36px}}.mid .body{{font-size:46px;margin-top:30px}}
.tiles{{position:absolute;left:60px;right:60px;top:640px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}}
.tile{{background:#fff;border:2px solid {LINE};border-radius:24px;padding:26px 26px 24px;height:240px}}
.tile b{{display:block;font:800 76px/1 'Jakarta';letter-spacing:-.03em;color:{GREEN}}}
.tile span{{display:block;font:600 27px/1.25 'Inter';color:{INK};margin-top:18px}}
.item{{display:flex;gap:26px;align-items:flex-start;padding:30px 0;border-bottom:2px solid {LINE}}}
.badge{{flex:none;width:68px;height:68px;border-radius:34px;background:linear-gradient(135deg,{GREEN},{TEAL});color:#fff;font:800 32px/68px 'Jakarta';text-align:center}}
.it{{font:700 42px/1.2 'Jakarta';color:{INK};letter-spacing:-.015em}}
.ib{{font:500 30px/1.38 'Inter';color:{GREY};margin-top:8px}}
"""


def esc(s):
    return html.escape(s, quote=True)


def page(w, h, body, css=''):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{FONT_CSS}{BASE_CSS}'
            f'html,body{{width:{w}px;height:{h}px}}{css}</style></head><body>{body}</body></html>')


class Shooter:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.tmp = tempfile.mkdtemp()
        return self

    def __exit__(self, *a):
        self.browser.close()
        self._pw.stop()

    def shot(self, doc, out, w=1080, h=1350, quality=93):
        pg = self.browser.new_page(viewport={'width': w, 'height': h})
        path = Path(self.tmp) / f'p{random.randrange(10**9)}.html'
        path.write_text(doc, encoding='utf-8')
        pg.goto(f'file://{path}')
        pg.evaluate('document.fonts.ready')
        pg.wait_for_load_state('networkidle')
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if str(out).endswith('.png'):
            pg.screenshot(path=str(out))
        else:
            pg.screenshot(path=str(out), type='jpeg', quality=quality)
        pg.close()


def ff(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + [str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {r.stderr[-1500:]}')


def foot(i, n):
    return f'<div class="foot"><span>website-automation.com</span><span>{i:02d} / {n:02d}</span></div>'


def browser(slug, top, url=None, extra=''):
    url = url or 'your-business.com'
    return (f'<div class="browser" style="top:{top}px;{extra}"><div class="bar"><span class="dot"></span><span class="dot"></span>'
            f'<span class="dot"></span><span class="url">{esc(url)}</span></div><img src="file://{TEMPLATES / (slug + ".jpg")}"></div>')


def num_slide(eb, num, title, desc):
    return (f'<div class="mid"><div class="eb">{esc(eb)}</div><div class="num">{esc(str(num))}</div>'
            f'<div class="h2">{esc(title)}</div><div class="body">{esc(desc)}</div></div>')


def end_slide(sh, out, headline, sub, w=1080, h=1350, pill='Free preview, no sign-up', endfoot=''):
    body = (f'<div class="wrap"><div class="logo">{LOGO}</div><div class="rule"></div><div class="h2" style="margin-top:0">{headline}</div>'
            f'<div class="body">{esc(sub)}</div><div class="pill">{esc(pill)}</div><div class="link">Link in bio</div></div>'
            f'<div class="endfoot">{esc(endfoot)}</div>')
    sh.shot(page(w, h, body), out, w, h)


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


def slideshow_reel(stills, out_dir, cover_at=0.8, xfade=0.3):
    """stills: list of (path, seconds). Slow push on each frame, crossfaded, with the audio bed."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    segs, durs = [], []
    for i, (png, dur) in enumerate(stills):
        frames = int(round(dur * FPS))
        z = f"1+0.035*on/{frames}"
        seg = tmp / f's{i}.mp4'
        ff(['-loop', 1, '-i', png, '-vf', f"scale=2160:3840,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS},format=yuv420p",
            '-frames:v', frames, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 18, seg])
        segs.append(seg)
        durs.append(dur)
    inputs, fc, prev, offset = [], [], '0:v', 0.0
    for s in segs:
        inputs += ['-i', s]
    for k in range(1, len(segs)):
        offset += durs[k - 1] - xfade
        fc.append(f'[{prev}][{k}:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[v{k}]')
        prev = f'v{k}'
    fc.append(f'[{prev}]format=yuv420p[o]')
    silent = tmp / 'silent.mp4'
    ff(inputs + ['-filter_complex', ';'.join(fc), '-map', '[o]', '-c:v', 'libx264', '-preset', 'slow', '-crf', 20, '-an', '-movflags', '+faststart', silent])
    total = sum(durs) - xfade * (len(segs) - 1)
    bed = tmp / 'bed.m4a'
    ambient_bed(bed, total)
    ff(['-i', silent, '-i', bed, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', out / 'reel.mp4'])
    ff(['-ss', cover_at, '-i', out / 'reel.mp4', '-frames:v', 1, '-q:v', 2, out / 'cover.jpg'])
    return total


# -------------------------------------------------------------- Industries ---

CTA = ('Describe your business in plain language and get a free preview in about 30 seconds, no sign-up. Pay only if you publish. Link in bio.')
TAGS = '#smallbusiness #websitedesign #aiwebsite #smallbusinesstips #websitebuilder'


def industry_carousel(sh, ind, items, out_dir, hook, headline=None):
    """ind: queue entry. items: list of (title, advice). Writes numbered JPGs."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = len(items) + 2
    headline = headline or f"{len(items)} things your {esc(ind['singular'])} <em>website needs</em>"
    tpl = ind.get('template')
    body = (f'<div class="pad"><div class="eb">For {esc(ind["plural"])}</div><div class="h1" style="font-size:{84 if tpl else 104}px">{headline}</div>'
            f'<div class="body" style="font-size:33px">{esc(hook)}</div></div>'
            + (browser(tpl, 700) if tpl else foot(1, n)) + '<div class="swipe" style="z-index:3">SWIPE →</div>')
    sh.shot(page(1080, 1350, body), out / '01.jpg')
    for i, (t, a) in enumerate(items):
        body = num_slide(ind['plural'], i + 1, t, a) + foot(i + 2, n)
        sh.shot(page(1080, 1350, body), out / f'{i + 2:02d}.jpg')
    end_slide(sh, out / f'{n:02d}.jpg', 'Your website,<br><em>one prompt away.</em>', 'Describe your business. See a working site in about 30 seconds.')
    return n


def industry_reel(sh, ind, items, out_dir, hook):
    tmp = Path(tempfile.mkdtemp())
    tpl = ind.get('template')
    css = ".pad{top:230px}.h1{font-size:92px}"
    stills = []
    body = f'<div class="pad"><div class="eb">For {esc(ind["plural"])}</div><div class="h1">{esc(hook)}</div></div>'
    if tpl:
        body += browser(tpl, 1010)
    p = tmp / 'hook.png'
    sh.shot(page(1080, 1920, body, css), p, 1080, 1920)
    stills.append((p, 3.2))
    for i, (t, a) in enumerate(items):
        body = num_slide(f'What the site needs · {i + 1} of {len(items)}', i + 1, t, a)
        p = tmp / f'i{i}.png'
        sh.shot(page(1080, 1920, body, css), p, 1080, 1920)
        stills.append((p, 3.0))
    p = tmp / 'end.png'
    end_slide(sh, p, 'Your website,<br><em>one prompt away.</em>', 'Describe your business. See a working site in about 30 seconds.', 1080, 1920)
    stills.append((p, 2.8))
    return slideshow_reel(stills, out_dir)
