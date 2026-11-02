#!/usr/bin/env python3
"""Render one data-only post for a queued city and write its caption.
usage: make_city.py "<City>" reel|carousel YYYY-MM-DD"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import th_media as t

ROOT = Path(__file__).resolve().parent.parent
FOOT = 'Distances are estimates: straight line between stops plus 30% for streets.'
CTA = 'Travelhour puts the places you swipe into walking order and guides you there. Free on the App Store, link in bio.'


def main(city, fmt, date):
    q = json.load(open(ROOT / 'data/route_queue.json'))
    c = next(x for x in q['cities'] if x['city'].lower() == city.lower())
    stops = [dict(name=a, lat=b, lon=d) for a, b, d in c['stops']]
    slug = c['city'].lower().replace(' ', '-')
    out = ROOT / 'posts' / f'{date}-{slug}-{"route-reel" if fmt == "reel" else "order-carousel"}'
    tags = f"#{c['tag']}travel #{c['tag']}itinerary #walkingtour #citybreak #travelplanning"
    with t.Shooter() as sh:
        if fmt == 'reel':
            r = t.route_reel(sh, c['city'], stops, out)
            lines = '\n'.join(f'{i + 1}. {n}' for i, n in enumerate(r['order']))
            cap = (f"{c['city']} on foot: {len(stops)} stops in one line, about {r['km']:.1f} km.\n\n{lines}\n\n"
                   f"📌 Save this for your trip.\n\n{CTA}\n\n{tags}\n\n{FOOT}")
            title = f"{c['city']} on foot: {len(stops)} stops, one line"
        else:
            r = t.order_carousel(sh, c['city'], stops, out)
            lines = '\n'.join(f'{i + 1}. {n}' for i, n in enumerate(r['order']))
            cap = (f"Same {len(stops)} stops in {c['city']}. In a random order you'd walk about {r['rand_km']:.1f} km. "
                   f"In the shortest order, {r['best_km']:.1f} km.\n\n{lines}\n\n"
                   f"📌 Save this order for your trip.\n\n{CTA}\n\n{tags}\n\n{FOOT}")
            title = f"{c['city']}: same {len(stops)} stops, {r['diff']:.0f} km less walking"
    (out / 'caption.txt').write_text(cap, encoding='utf-8')
    (out / 'title.txt').write_text(title, encoding='utf-8')
    (out / 'numbers.json').write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
    print(out, json.dumps(r, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
