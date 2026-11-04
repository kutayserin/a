#!/usr/bin/env python3
"""website-automation post library: plan -> render -> calendar.

  wa_library.py plan               write data/render_plan.json from data/library_copy.json
  wa_library.py render <i> <n>     render shard i of n into posts/
  wa_library.py calendar           write calendar/<YYYY-MM-DD>.json, ready for Metricool

The daily scheduled task only reads calendar/<date>.json and needs no write access here."""
import json, os, sys, tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wa_media as w
from wa_media import esc, page, browser, end_slide, num_slide, foot

ROOT = w.ROOT
COPY = Path(os.environ.get('WA_COPY', ROOT / 'data/library_copy.json'))
RAW = 'https://raw.githubusercontent.com/kutayserin/a/website-automation-social'
TZ = 'Europe/Istanbul'
START = date(2026, 11, 5)
FIRST_SLOT = '2026-11-05T10:30'  # earlier slots that day are gone by the time the library is live
# Every 3 hours; the kind is the preferred one and any other pool fills in when it runs out.
SLOTS = [('01:30', 'pain'), ('04:30', 'tip'), ('07:30', 'checklist'), ('10:30', 'pain'),
         ('13:30', 'prompt'), ('16:30', 'rewrite'), ('19:30', 'pain'), ('22:30', 'tool')]
# Already scheduled by hand in Metricool at 19:30 on these days.
TAKEN = {'2026-11-06T19:30', '2026-11-09T19:30', '2026-11-11T19:30', '2026-11-13T19:30', '2026-11-16T19:30'}
AUDIO = ['1304451697253803', '473815599863496', '1369509361952542', '1941675846329817', '957044555314519']
REEL_KINDS = {'pain', 'tip', 'prompt', 'tool'}
CTAS = ['Describe your business in plain language and get a free preview in about 30 seconds, no sign-up. Pay only if you publish. Link in bio.',
        'Free preview, no sign-up, about 30 seconds. You only pay if you publish. Link in bio.',
        'Try it with one sentence: free preview, no sign-up, about 30 seconds. Pay only if you publish. Link in bio.']
SAVES = ['📌 Save this for when you update your site.', '📌 Save this for later.', '📌 Send this to someone who runs a small business.']
TOOL_NUM = {'business-name-generator': '10', 'tagline-generator': '10', 'color-palette-generator': '5',
            'logo-generator': '6', 'color-contrast-checker': 'AA', 'faq-generator': '10'}
PART_LABELS = ['Who and where', 'The mood', "What's different", 'What to show']
END_HEAD = 'Your website,<br><em>one prompt away.</em>'
END_SUB = 'Describe your business. See a working site in about 30 seconds.'
DARK = ("html,body{background:radial-gradient(900px 720px at 90% -6%,#124436 0%,rgba(18,68,54,0) 70%),#14181A}"
        ".h1,.h2{color:#F5FAF8}.body{color:#B9C6CE}.eb{color:#43D1A3}em{color:#43D1A3}")
CHECK = ('<svg width="118" height="118" viewBox="0 0 118 118"><circle cx="59" cy="59" r="59" fill="#14906A"/>'
         '<path d="M33 61l18 18 35-40" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def posts():
    return json.load(open(COPY))['posts']


def industries():
    return {x['slug']: x for x in json.load(open(ROOT / 'data/industry_queue.json'))['industries']}


def a_an(s):
    return ('an ' if s[0].lower() in 'aeiou' else 'a ') + s


def tags(p):
    return f"#{p['tag']} #smallbusiness #websitedesign #smallbusinesstips #websitebuilder"


# ---------------------------------------------------------------- planning ---
def group(p):
    return p.get('slug') or p['type']


def plan():
    items = posts()
    pools = {k: [i for i, p in enumerate(items) if p['type'] == k] for k in ('pain', 'tip', 'checklist', 'prompt', 'rewrite', 'tool')}
    by = {}
    for i in pools['pain']:
        by.setdefault(items[i]['slug'], []).append(i)
    pools['pain'] = []
    while any(by.values()):  # one pain per industry in turn
        for s in by:
            if by[s]:
                pools['pain'].append(by[s].pop(0))
    seq = {}
    jobs, recent, d, audio = [], [], START, 0
    while any(pools.values()):
        for tm, kind in SLOTS:
            key = f'{d.isoformat()}T{tm}'
            if key in TAKEN or key < FIRST_SLOT:
                continue
            k = kind if pools[kind] else max(pools, key=lambda q: len(pools[q]))
            if not pools[k]:
                break
            pool = pools[k]
            n = next((m for m, i in enumerate(pool) if group(items[i]) not in recent[-5:]), 0)
            i = pool.pop(n)
            p = items[i]
            recent.append(group(p))
            seq[k] = seq.get(k, 0) + 1
            if k == 'pain' or k in ('checklist', 'prompt'):
                name = f"{p['slug']}-{k}" + (f'-{seq[k]:02d}' if k == 'pain' else '')
            elif k == 'tool':
                name = p['url_path'].rsplit('/', 1)[1] + '-tool'
            else:
                name = f'{k}-{seq[k]:02d}'
            job = dict(i=i, kind=k, slot=key, day=d.isoformat(), folder=f'{d.isoformat()}-{name}')
            if k in REEL_KINDS:
                job['audio'] = AUDIO[audio % len(AUDIO)]
                audio += 1
            jobs.append(job)
        d += timedelta(days=1)
    (ROOT / 'data/render_plan.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=0), encoding='utf-8')
    from collections import Counter
    print(len(jobs), 'posts, last slot', jobs[-1]['slot'], Counter(j['kind'] for j in jobs))


# ------------------------------------------------------------------ slides ---
def statement(sh, out, eyebrow, line, tpl=None, dark=False):
    """The opening frame of a reel: one line, big, on the brand background."""
    css = (DARK if dark else '') + '.pad{top:230px}'
    n = len(line)
    if tpl:
        size = 92 if n <= 60 else 80
        body = f'<div class="pad"><div class="eb">{esc(eyebrow)}</div><div class="h1" style="font-size:{size}px">{esc(line)}</div></div>' + browser(tpl, 1010)
    else:
        size = 118 if n <= 44 else 104 if n <= 60 else 92
        body = (f'<div class="mid" style="bottom:240px"><div class="eb">{esc(eyebrow)}</div>'
                f'<div class="h1" style="font-size:{size}px;margin-top:36px">{esc(line)}</div></div>')
    sh.shot(page(1080, 1920, body, css), out, 1080, 1920)


def fix_frame(sh, out, eyebrow, title, text, dark=False):
    body = (f'<div class="mid" style="bottom:240px">{CHECK}<div class="eb" style="margin-top:44px">{esc(eyebrow)}</div>'
            f'<div class="h2" style="font-size:88px">{esc(title)}</div><div class="body" style="font-size:48px">{esc(text)}</div></div>')
    sh.shot(page(1080, 1920, body, DARK if dark else ''), out, 1080, 1920)


def render_text_reel(sh, job, p, ind, out, eyebrow, line, fix_eb, title, text, dark=False, tpl=None):
    tmp = Path(tempfile.mkdtemp())
    statement(sh, tmp / 'a.png', eyebrow, line, tpl, dark)
    fix_frame(sh, tmp / 'b.png', fix_eb, title, text, dark)
    end_slide(sh, tmp / 'c.png', END_HEAD, END_SUB, 1080, 1920)
    w.slideshow_reel([(tmp / 'a.png', 3.6), (tmp / 'b.png', 4.4), (tmp / 'c.png', 2.6)], out)


def render_pain(sh, job, p, ind, out):
    i = ind[p['slug']]
    render_text_reel(sh, job, p, ind, out, f"For {i['plural']}", p['hook'], 'The fix', p['fix_title'], p['fix_body'], tpl=i.get('template'))
    return (f"{p['hook']}\n\nThe fix: {p['fix_title']}. {p['fix_body']}")


def render_tip(sh, job, p, ind, out):
    render_text_reel(sh, job, p, ind, out, 'Website tip', p['hook'], 'Do this', p['tip_title'], p['tip_body'], dark=True)
    return f"{p['hook']}\n\n{p['tip_title']}. {p['tip_body']}"


def render_tool(sh, job, p, ind, out):
    tmp = Path(tempfile.mkdtemp())
    statement(sh, tmp / 'a.png', 'Free tool, no sign-up', p['hook'], dark=True)
    key = p['url_path'].rsplit('/', 1)[1]
    body = num_slide('website-automation.com/tools', TOOL_NUM[key], p['tool'], p['body'])
    sh.shot(page(1080, 1920, body), tmp / 'b.png', 1080, 1920)
    end_slide(sh, tmp / 'c.png', 'Then turn it into<br><em>a real website.</em>', 'website-automation.com/tools. All six are free, no sign-up.', 1080, 1920)
    w.slideshow_reel([(tmp / 'a.png', 3.4), (tmp / 'b.png', 4.4), (tmp / 'c.png', 2.6)], out)
    return f"{p['hook']}\n\n{p['tool']}: {p['body']}\n\nFree, no sign-up: website-automation.com{p['url_path']}"


def render_prompt(sh, job, p, ind, out):
    i = ind[p['slug']]
    parts = [p['who'], p['mood'], p['different'], p['show']]
    tmp = Path(tempfile.mkdtemp())
    full = ' '.join(parts)
    size = 52 if len(full) <= 170 else 46

    def box(hi):
        inner = ' '.join(f'<b>{esc(x)}</b>' if k == hi else esc(x) for k, x in enumerate(parts)) if hi is not None else f'<span class="all">{esc(full)}</span>'
        return f'<div class="prompt" style="top:760px;font-size:{size}px">{inner}</div>'
    css = '.pad{top:230px}'
    head = (f'<div class="pad"><div class="eb">For {esc(i["plural"])}</div><div class="h1" style="font-size:96px">A website prompt <em>you can copy.</em></div>'
            f'<div class="body" style="font-size:42px">Change the details to yours.</div></div>')
    sh.shot(page(1080, 1920, head + box(None), css), tmp / 'p0.png', 1080, 1920)
    stills = [(tmp / 'p0.png', 4.0)]
    for k, label in enumerate(PART_LABELS):
        f = (f'<div class="pad"><div class="eb">Part {k + 1} of 4</div><div class="h1" style="font-size:104px">{esc(label)}</div></div>' + box(k))
        sh.shot(page(1080, 1920, f, css), tmp / f'p{k + 1}.png', 1080, 1920)
        stills.append((tmp / f'p{k + 1}.png', 2.3))
    end_slide(sh, tmp / 'end.png', 'Try yours in<br><em>about 30 seconds.</em>', 'A single line works too. More detail just gets you closer on the first try.', 1080, 1920)
    stills.append((tmp / 'end.png', 2.6))
    w.slideshow_reel(stills, out)
    return (f"A website prompt for {a_an(i['singular'])}. Copy it and change the details:\n\n\"{full}\"\n\n"
            f"Who and where, the mood, what's different, what to show. Write it in your own language: the copy follows it.")


def render_checklist(sh, job, p, ind, out):
    i = ind[p['slug']]
    items = [tuple(x) for x in p['items']]
    n = len(items) + 2
    tpl = i.get('template')
    head = f"{len(items)} things your {esc(i['singular'])} <em>website needs</em>"
    preview = ''
    if not tpl:  # no gallery screenshot for this trade: the list itself fills the cover
        preview = ''.join(f'<div class="item" style="padding:20px 0"><div class="badge" style="width:58px;height:58px;font-size:28px;line-height:58px">{k + 1}</div>'
                          f'<div class="it" style="font-size:36px;padding-top:8px">{esc(t)}</div></div>' for k, (t, _) in enumerate(items))
        preview = f'<div class="pad" style="top:{620 if len(i["singular"]) <= 14 else 700}px;bottom:auto">{preview}</div>'
    size = (84 if len(i['singular']) <= 14 else 74) if tpl else (88 if len(i['singular']) <= 14 else 80)
    body = (f'<div class="pad"><div class="eb">For {esc(i["plural"])}</div><div class="h1" style="font-size:{size}px">{head}</div>'
            f'<div class="body" style="font-size:33px">{esc(p["hook"])}</div></div>'
            + (browser(tpl, 770) if tpl else preview + foot(1, n)) + '<div class="swipe" style="z-index:3">SWIPE →</div>')
    Path(out).mkdir(parents=True, exist_ok=True)
    sh.shot(page(1080, 1350, body), out / '01.jpg')
    for k, (t, a) in enumerate(items):
        sh.shot(page(1080, 1350, num_slide(i['plural'], k + 1, t, a) + foot(k + 2, n)), out / f'{k + 2:02d}.jpg')
    end_slide(sh, out / f'{n:02d}.jpg', END_HEAD, END_SUB)
    lines = '\n'.join(f'{k + 1}. {t}' for k, (t, _) in enumerate(items))
    return f"{p['hook']}\n\nWhat {a_an(i['singular'])} website needs:\n{lines}"


REWRITE_CSS = (".card{position:absolute;left:60px;right:60px;border-radius:26px;padding:34px 44px 40px}"
               ".lab{font:700 25px 'Inter';letter-spacing:.16em;text-transform:uppercase}"
               ".was{top:300px;background:#EDF2F0;color:#7C8890}.was p{margin:18px 0 0;font:500 50px/1.3 'Inter';text-decoration:line-through;text-decoration-thickness:3px}"
               ".now{top:610px;background:#fff;border:3px solid #14906A;box-shadow:0 22px 60px rgba(20,144,106,.14)}.now .lab{color:#14906A}"
               ".now p{margin:18px 0 0;font:800 66px/1.18 'Jakarta';color:#14181A;letter-spacing:-.02em}")


def render_rewrite(sh, job, p, ind, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    body = (f'<div class="pad"><div class="eb">Example rewrite</div><div class="h1" style="font-size:{84 if len(p["business"]) <= 23 else 66}px">{esc(p["business"])}</div></div>'
            f'<div class="card was"><div class="lab">Before</div><p>{esc(p["before"])}</p></div>'
            f'<div class="card now"><div class="lab">After</div><p>{esc(p["after"])}</p></div>'
            '<div class="swipe">SWIPE →</div>' + foot(1, 3))
    sh.shot(page(1080, 1350, body, REWRITE_CSS), out / '01.jpg')
    body = (f'<div class="mid">{CHECK}<div class="eb" style="margin-top:44px">Why it works</div>'
            f'<div class="h2" style="font-size:76px">{esc(p["why"])}</div></div>' + foot(2, 3))
    sh.shot(page(1080, 1350, body), out / '02.jpg')
    end_slide(sh, out / '03.jpg', END_HEAD, END_SUB)
    return f"Before: \"{p['before']}\"\nAfter: \"{p['after']}\"\n\n{p['why']}\n\nExample for {a_an(p['business'][0].lower() + p['business'][1:])}. Which line does your site sound like?"


RENDER = dict(pain=render_pain, tip=render_tip, tool=render_tool, prompt=render_prompt, checklist=render_checklist, rewrite=render_rewrite)


def caption(job, p, core):
    n = job['i']
    if job['kind'] == 'tool':
        tail = "When you're ready for the site itself: free preview, about 30 seconds, link in bio."
    else:
        tail = CTAS[n % len(CTAS)]
    return f"{core}\n\n{SAVES[n % len(SAVES)]}\n\n{tail}\n\n{tags(p)}"


def render(i, n):
    items, ind = posts(), industries()
    jobs = json.load(open(ROOT / 'data/render_plan.json'))
    with w.Shooter() as sh:
        for k, job in enumerate(jobs):
            if k % n != i:
                continue
            out = ROOT / 'posts' / job['folder']
            if (out / 'caption.txt').exists():
                continue
            print(k, job['folder'], flush=True)
            p = items[job['i']]
            core = RENDER[job['kind']](sh, job, p, ind, out)
            (out / 'caption.txt').write_text(caption(job, p, core), encoding='utf-8')
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
