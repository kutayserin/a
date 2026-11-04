#!/usr/bin/env python3
"""Open the live site like a visitor from Turkey on a phone. Reads only: nothing is typed or submitted."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path('site');OUT.mkdir(exist_ok=True)
PAGES = [('home', 'https://compassuni.com/'), ('packages', 'https://compassuni.com/#packages'), ('how', 'https://compassuni.com/#how'),
         ('checkout', 'https://compassuni.com/odeme.html?paket=premium'), ('app', 'https://compassuni.com/app'),
         ('refund', 'https://compassuni.com/teslimat-iade.html'), ('terms', 'https://compassuni.com/kullanim-sartlari.html'),
         ('privacy', 'https://compassuni.com/gizlilik-kvkk.html'), ('sales', 'https://compassuni.com/mesafeli-satis.html')]
report = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(locale='tr-TR', viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    for name, url in PAGES:
        pg = ctx.new_page()
        errors, failed = [], []
        pg.on('pageerror', lambda e: errors.append(str(e)[:200]))
        pg.on('requestfailed', lambda r: failed.append(r.url[:120]))
        resp = pg.goto(url, wait_until='networkidle', timeout=60000)
        pg.wait_for_timeout(9000 if name == 'app' else 1500)
        pg.screenshot(path=str(OUT / f'{name}.png'))
        report[name] = dict(status=resp.status if resp else None, final=pg.url, title=pg.title(), lang=pg.evaluate('document.documentElement.lang'),
                            text=pg.evaluate('document.body.innerText')[:300], errors=errors[:5], failed=failed[:8])
        pg.close()
    b.close()
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
