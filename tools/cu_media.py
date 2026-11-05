"""CompassUni social media renderer: brand slides, reels, audio bed."""
import html, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = HERE / 'fonts'
ICON = HERE / 'icon.png'
NAVY, BLUE, ROYAL, SKY, INK, SLATE, MIST, PAPER, LINE = '#172554', '#1E3A8A', '#1D4ED8', '#38BDF8', '#0F172A', '#475569', '#94A3B8', '#F8FAFC', '#E2E8F0'
FPS = 30
XFADE = 0.3
LATIN = ('U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD')
LATIN_EXT = 'U+0100-0130,U+0132-02BA,U+02BD-02C5,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2C60-2C7F,U+A720-A7FF'


def _face(file, rng):
    return (f"@font-face{{font-family:'Inter';font-style:normal;font-weight:100 900;font-display:block;"
            f"src:url('file://{FONTS / file}') format('woff2');unicode-range:{rng}}}")


FONT_CSS = _face('inter-latin-wght-normal.woff2', LATIN) + _face('inter-latin-ext-wght-normal.woff2', LATIN_EXT)
BASE_CSS = f"""
*{{box-sizing:border-box}}html,body{{margin:0;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased;font-family:'Inter';color:#fff}}
em{{font-style:normal;color:{SKY}}}
.brand{{position:absolute;inset:0;background:linear-gradient(160deg,{NAVY} 0%,{BLUE} 55%,{ROYAL} 100%)}}
.orb{{position:absolute;border-radius:50%;background:rgba(255,255,255,.055)}}
.ring{{position:absolute;border-radius:50%;border:3px solid rgba(255,255,255,.07)}}
.chip{{display:inline-block;font:800 30px/1 'Inter';letter-spacing:.13em;padding:18px 26px;border-radius:60px;background:rgba(255,255,255,.12);color:#fff;text-transform:uppercase}}
.chip.sky{{color:#7DD3FC}}.chip.no{{color:#FCA5A5}}.chip.yes{{color:#86EFAC}}
.x{{position:absolute;left:80px;right:110px}}
.big{{font:900 104px/1.07 'Inter';letter-spacing:-.032em;color:#fff}}
.mid2{{font:900 84px/1.1 'Inter';letter-spacing:-.028em;color:#fff}}
.txt{{font:500 50px/1.34 'Inter';letter-spacing:-.006em;color:rgba(255,255,255,.9)}}
.src{{font:600 29px/1.3 'Inter';color:rgba(255,255,255,.62)}}
.foot{{position:absolute;left:70px;right:70px;bottom:46px;display:flex;justify-content:space-between;font:700 26px 'Inter';letter-spacing:.01em}}
.swipe{{position:absolute;right:70px;bottom:112px;font:800 27px 'Inter';letter-spacing:.08em;padding:18px 30px;border-radius:60px;background:#fff;color:{BLUE}}}
.light{{position:absolute;inset:0;background:{PAPER}}}
.eb{{font:800 28px/1.2 'Inter';letter-spacing:.11em;color:{ROYAL};text-transform:uppercase}}
"""


def esc(s):
    return html.escape(s, quote=True)


def page(w, h, body, css='', bg='transparent'):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{FONT_CSS}{BASE_CSS}'
            f'html,body{{width:{w}px;height:{h}px;background:{bg}}}{css}</style></head><body>{body}</body></html>')


def brand_bg(seed=0):
    r = random.Random(seed)
    a, b = r.choice([(-200, -220), (-150, -260), (-260, -160)]), r.choice([(1320, -120), (1200, 720), (1450, 640)])
    return (f'<div class="brand"><div class="orb" style="width:640px;height:640px;top:{a[0]}px;right:{a[1]}px"></div>'
            f'<div class="orb" style="width:340px;height:340px;top:{b[0]}px;left:{b[1]}px"></div>'
            f'<div class="ring" style="width:900px;height:900px;top:{r.choice([420, 520, 600])}px;left:90px"></div></div>')


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

    def shot(self, doc, out, w, h, transparent=False, quality=93):
        pg = self.browser.new_page(viewport={'width': w, 'height': h})
        path = Path(self.tmp) / f'p{random.randrange(10**9)}.html'
        path.write_text(doc, encoding='utf-8')
        pg.goto(f'file://{path}')
        pg.evaluate('document.fonts.ready')
        pg.wait_for_load_state('networkidle')
        out = str(out)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if out.endswith('.png'):
            pg.screenshot(path=out, omit_background=transparent)
        else:
            pg.screenshot(path=out, type='jpeg', quality=quality)
        pg.close()


def ff(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + [str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {r.stderr[-1500:]}')


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


def photo_segment(img, overlay, dur, out, zoom_in=True, fade=False):
    frames = int(round(dur * FPS))
    z = f"1+0.07*on/{frames}" if zoom_in else f"1.07-0.07*on/{frames}"
    crop = "crop=if(gt(iw/ih\\,9/16)\\,ih*9/16\\,iw):if(gt(iw/ih\\,9/16)\\,ih\\,iw*16/9)"
    ov = 'format=rgba' + (',fade=in:st=0.1:d=0.3:alpha=1' if fade else '')
    fc = (f"[0:v]{crop},scale=2160:3840,eq=saturation=1.05:contrast=1.03,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS},"
          f"setsar=1[bg];[1:v]{ov}[ov];[bg][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
    ff(['-i', img, '-loop', 1, '-t', dur, '-i', overlay, '-filter_complex', fc, '-map', '[v]', '-frames:v', frames,
        '-r', FPS, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 18, out])


def still_segment(png, dur, out):
    frames = int(round(dur * FPS))
    z = f"1+0.03*on/{frames}"
    ff(['-loop', 1, '-i', png, '-vf', f"scale=2160:3840,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS},format=yuv420p",
        '-frames:v', frames, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 18, out])


def assemble(segments, durations, out_dir, cover_at=0.9):
    """Crossfade the segments, lay the audio bed under them, write reel.mp4 and cover.jpg."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    inputs, fc, prev, offset = [], [], '0:v', 0.0
    for s in segments:
        inputs += ['-i', s]
    for k in range(1, len(segments)):
        offset += durations[k - 1] - XFADE
        fc.append(f'[{prev}][{k}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[v{k}]')
        prev = f'v{k}'
    fc.append(f'[{prev}]format=yuv420p[o]')
    silent = tmp / 'silent.mp4'
    ff(inputs + ['-filter_complex', ';'.join(fc), '-map', '[o]', '-c:v', 'libx264', '-preset', 'slow', '-crf', 20, '-an', '-movflags', '+faststart', silent])
    total = sum(durations) - XFADE * (len(segments) - 1)
    bed = tmp / 'bed.m4a'
    ambient_bed(bed, total)
    ff(['-i', silent, '-i', bed, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', out / 'reel.mp4'])
    ff(['-ss', cover_at, '-i', out / 'reel.mp4', '-frames:v', 1, '-q:v', 2, out / 'cover.jpg'])
    return total
