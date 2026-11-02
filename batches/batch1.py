"""First two weeks of website-automation posts. Usage: batch1.py stills|reels"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import wa_media as w
from wa_media import esc, foot, page, browser, end_slide, num_slide

OUT = w.ROOT / 'posts'
PROMO = Path('/home/claude/website-automation/brand/video/reel-en.mp4')
RAW = 'https://raw.githubusercontent.com/kutayserin/a/website-automation-social/posts'

PARTS = [("Specialty coffee shop in Kadıköy, Istanbul.", 'Who and where', 'Name the business and the city. The copy has something real to work with from the first line.'),
         ("Warm, dark theme.", 'The mood', 'Say the feeling you want. The AI chooses the palette and the fonts from it.'),
         ("We roast on site and regulars come for the filter coffee.", "What's different", 'One true detail gives the headline something to say that no other coffee shop can.'),
         ("Menu, opening hours and an Instagram link.", 'What to show', 'List the sections you want. You can change any of them in the editor afterwards.')]
TOOLS = [('10', 'Business name generator', 'Brand-name ideas based on your industry and style.'),
         ('10', 'Tagline generator', 'Short, specific lines for the top of your site.'),
         ('5', 'Color palette generator', 'Palettes with a role for every color: brand, accent, background, text, muted.'),
         ('6', 'Logo concept generator', 'SVG logo concepts. Download the ones you like.'),
         ('AA', 'WCAG contrast checker', 'An instant AA / AAA verdict for any two colors. No AI needed.'),
         ('10', 'FAQ generator', 'The questions buyers actually ask, with answers.')]
TEMPL = [('serenity-yoga-studio', 'Yoga studio', 'Berlin'), ('wood-fired-pizzeria', 'Neapolitan pizzeria', 'Istanbul'), ('bayside-dental', 'Dental clinic', 'Izmir'),
         ('sage-and-bloom', 'Hair salon', 'Istanbul'), ('petal-and-stem', 'Florist', 'Istanbul'), ('felix-carter-photo', 'Wedding photographer', 'Lisbon'),
         ('ceramics-shop', 'Handmade ceramics', 'Lisbon'), ('leaf-and-spine', 'Independent bookstore', 'Istanbul'), ('lena-kraft-portfolio', 'Product designer', 'Berlin'), ('north-star-strategy', 'GTM consultancy', 'Berlin')]
HAIR = {"hook": "Clients keep asking \"how much is balayage?\" because the prices aren't on the site.",
        "items": [["A service menu with honest prices", "Put a real price next to each service. Clients decide before they message you."],
                  ["A WhatsApp button, not a form", "Your clients already message you there. One tap beats filling in a form."],
                  ["Stylist credits and a gallery", "Name who did each cut. It builds their following and yours."],
                  ["Address, hours and phone up front", "People search for a salon nearby. Make the basics easy to find."]]}
STEPS = [('1', 'Describe your business', 'Plain language is enough. No sign-up, no card.'),
         ('2', 'See a working site', 'About 30 seconds later you have a preview, not a wireframe. You get 3 free previews a day, and each link lasts 24 hours.'),
         ('3', 'Pay only to publish', 'Plans start at $9/mo. Connect your own domain when you go live.'),
         ('4', 'Changed your mind?', '14-day money-back guarantee on your first paid plan. Cancel anytime.')]
FULL = ' '.join(p[0] for p in PARTS)


def prompt_box(hi=None, top=330):
    spans = []
    for i, p in enumerate(PARTS):
        spans.append(f'<b>{esc(p[0])}</b>' if hi == i else esc(p[0]))
    inner = ' '.join(spans) if hi is not None else f'<span class="all">{esc(FULL)}</span>'
    return f'<div class="prompt" style="top:{top}px">{inner}</div>'


def stills(sh):
    d = OUT / '2026-11-06-prompt-carousel'
    n = 7
    body = (f'<div class="pad"><div class="eb">Website prompts</div><div class="h1">"Coffee shop" gets you a site. <em>This gets you yours.</em></div></div>'
            + prompt_box(None, 680) + '<div class="swipe">SWIPE →</div>' + foot(1, n))
    sh.shot(page(1080, 1350, body), d / '01.jpg')
    for i, (txt, label, why) in enumerate(PARTS):
        body = (f'<div class="pad"><div class="eb">Part {i + 1} of 4</div><div class="h2" style="font-size:88px">{esc(label)}</div></div>' + prompt_box(i, 300)
                + f'<div class="pad" style="top:800px"><div class="body" style="margin:0;font-size:50px;line-height:1.36">{esc(why)}</div></div>' + foot(i + 2, n))
        sh.shot(page(1080, 1350, body), d / f'{i + 2:02d}.jpg')
    body = (f'<div class="pad"><div class="eb">Bonus</div><div class="h1">Write it in <em>your language.</em></div>'
            f'<div class="body" style="font-size:42px">The copy follows the language of your prompt. Write in Turkish and your site comes out in Turkish.</div></div>'
            f'<div class="prompt" style="top:800px;color:{w.INK}">Kadıköy\'de nalbur dükkanı. Sade ve güven veren bir tasarım, çalışma saatleri ve WhatsApp butonu.</div>' + foot(6, n))
    sh.shot(page(1080, 1350, body), d / '06.jpg')
    end_slide(sh, d / '07.jpg', 'Try yours in<br><em>about 30 seconds.</em>', 'A single line works too. More detail just gets you closer on the first try.')

    d = OUT / '2026-11-11-free-tools-carousel'
    n = len(TOOLS) + 2
    tiles = ''.join(f'<div class="tile"><b>{num}</b><span>{esc(title.replace(" generator", "").replace("WCAG contrast checker", "Contrast checker"))}</span></div>' for num, title, _ in TOOLS)
    body = (f'<div class="pad"><div class="eb">Free tools</div><div class="h1">6 free tools for your <em>small business.</em></div>'
            f'<div class="body" style="font-size:42px">All free. No sign-up.</div></div><div class="tiles">{tiles}</div>'
            '<div class="swipe">SWIPE →</div>' + foot(1, n))
    sh.shot(page(1080, 1350, body), d / '01.jpg')
    for i, (num, title, desc) in enumerate(TOOLS):
        body = num_slide(f'Tool {i + 1} of {len(TOOLS)}', num, title, desc) + foot(i + 2, n)
        sh.shot(page(1080, 1350, body), d / f'{i + 2:02d}.jpg')
    end_slide(sh, d / f'{n:02d}.jpg', 'Then turn it into<br><em>a real website.</em>', 'website-automation.com/tools. All six are free, no sign-up.')

    ind = next(x for x in json.load(open(w.ROOT / 'data/industry_queue.json'))['industries'] if x['slug'] == 'hair-salons')
    w.industry_carousel(sh, ind, [tuple(i) for i in HAIR['items']], OUT / '2026-11-13-hair-salons-carousel', HAIR['hook'])

    d = OUT / '2026-11-16-pay-to-publish-carousel'
    n = len(STEPS) + 2
    body = (f'<div class="pad"><div class="eb">How it works</div><div class="h1">See your website <em>before you pay.</em></div>'
            f'<div class="body" style="font-size:42px">No template to fill in first, and no card to enter.</div></div>'
            + browser('petal-and-stem', 760, 'your-business.com') + '<div class="swipe" style="z-index:3">SWIPE →</div>')
    sh.shot(page(1080, 1350, body), d / '01.jpg')
    for i, (num, title, desc) in enumerate(STEPS):
        body = num_slide(f'Step {num} of {len(STEPS)}', num, title, desc) + foot(i + 2, n)
        sh.shot(page(1080, 1350, body), d / f'{i + 2:02d}.jpg')
    end_slide(sh, d / f'{n:02d}.jpg', 'Your website,<br><em>one prompt away.</em>', 'Try free, pay when you publish.')


def reels(sh):
    d = OUT / '2026-11-04-promo-reel'
    d.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    dur = float(__import__('subprocess').run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(PROMO)], capture_output=True, text=True).stdout)
    w.ambient_bed(tmp / 'bed.m4a', dur)
    w.ff(['-i', PROMO, '-i', tmp / 'bed.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', d / 'reel.mp4'])
    w.ff(['-ss', 2.0, '-i', d / 'reel.mp4', '-frames:v', 1, '-q:v', 2, d / 'cover.jpg'])
    print('promo', dur)

    tmp = Path(tempfile.mkdtemp())
    css = ".pad{top:230px}"
    stills_ = []
    body = (f'<div class="pad"><div class="eb">website-automation</div><div class="h1" style="font-size:120px;margin-top:44px">Every business needs a <em>different website.</em></div>'
            f'<div class="body" style="font-size:46px">Ten examples from our gallery.</div></div>')
    p = tmp / 'hook.png'
    sh.shot(page(1080, 1920, body, css), p, 1080, 1920)
    stills_.append((p, 2.2))
    for i, (slug, what, city) in enumerate(TEMPL):
        body = (f'<div class="pad"><div class="eb">{i + 1:02d} / {len(TEMPL):02d} · {esc(city)}</div><div class="h1" style="font-size:104px">{esc(what)}</div></div>'
                + browser(slug, 760) + f'<div class="endfoot" style="bottom:420px">Example design from our gallery</div>')
        p = tmp / f't{i}.png'
        sh.shot(page(1080, 1920, body, css), p, 1080, 1920)
        stills_.append((p, 1.5))
    p = tmp / 'end.png'
    end_slide(sh, p, 'Yours starts with<br><em>one sentence.</em>', 'Describe your business. See a working site in about 30 seconds.', 1080, 1920)
    stills_.append((p, 2.8))
    print('templates', w.slideshow_reel(stills_, OUT / '2026-11-09-examples-reel', cover_at=3.0))


if __name__ == '__main__':
    with w.Shooter() as sh:
        for a in sys.argv[1:] or ['stills']:
            {'stills': stills, 'reels': reels}[a](sh)
