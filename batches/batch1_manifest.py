"""Writes caption.txt per post and posts.json, the list the scheduler reads."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch1 import ROME, ISTANBUL, PARIS, NAMES, credits_block, OUT

RAW = 'https://raw.githubusercontent.com/kutayserin/a/travelhour-social/posts'
CTA = 'Want this as a map with walking directions? Travelhour turns the landmarks you swipe into one walking day. Free on the App Store, link in bio.'
sched = lambda rows: '\n'.join(f'{a}  {b}' for a, b, *_ in rows)

rome_num = json.load(open(OUT / '2026-11-08-rome-order-carousel/numbers.json'))
bcn_num = json.load(open(OUT / '2026-11-14-barcelona-route-reel/numbers.json'))

POSTS = [
 dict(slug='2026-11-03-rome-reel', date='2026-11-03', kind='reel', title='Rome in one day: 8 stops, one route',
      text=f"""Rome in one day 🇮🇹 8 stops, one walking route.

{sched(ROME)}

Before you go: St. Peter's is often closed on Wednesday mornings, and Castel Sant'Angelo on Mondays. Book the Colosseum ahead. In winter, last entry is 15:30.

📌 Save this for your trip and send it to who you're going with.

{CTA}

#romeitinerary #onedayinrome #rometravel #romeguide #italytravel

{credits_block([b for _, b in ROME])}"""),
 dict(slug='2026-11-05-app-demo-reel', date='2026-11-05', kind='reel', title='Landed in Rome. Now what?',
      text="""Landed somewhere new and thinking "so what do I actually do here?"

Swipe right on the places you want to see. Travelhour puts them in walking order, guides you on a live 3D map, and alerts you when you arrive, even with your phone in your pocket.

Browsing, planning and setting off are free, with guided walking as far as your second stop. Pro covers the whole walk. Free on the App Store, link in bio.

#travelapp #tripplanner #citybreak #walkingtour #travelplanning

Photo in the app: Castel Sant'Angelo by Livioandronico2013 (CC BY-SA 4.0). Map © Mapbox © OpenStreetMap."""),
 dict(slug='2026-11-07-istanbul-carousel', date='2026-11-07', kind='carousel', count=10, title='Istanbul in one day: 8 stops with a tip each',
      text=f"""Istanbul in one day 🇹🇷 8 stops from Sultanahmet to the Bosphorus. Swipe for a tip at every stop →

{sched(ISTANBUL)}

Not all on foot: take the T1 tram to Kabataş for Dolmabahçe, and the ferry to Üsküdar for the Maiden's Tower.

📌 Save this for your trip. Which stop would you start with?

{CTA}

#istanbulitinerary #istanbultravel #istanbulguide #visitistanbul #turkeytravel

{credits_block([b for _, b, _ in ISTANBUL])}"""),
 dict(slug='2026-11-08-rome-order-carousel', date='2026-11-08', kind='carousel', count=5, title='Rome: same 8 stops, 9 km less walking',
      text=f"""Same 8 stops in Rome. In a random order you'd walk about {rome_num['rand_km']:.1f} km. In the shortest order, {rome_num['best_km']:.1f} km.

{chr(10).join(f'{i + 1}. {n}' for i, n in enumerate(rome_num['order']))}

📌 Save this order for your trip.

Travelhour tests a route from every stop, straightens the crossings, then guides you with live directions. Free on the App Store, link in bio.

#romeitinerary #rometravel #walkingtour #citybreak #travelplanning

Distances are estimates: straight line between stops plus 30% for streets. Random order is the average of every possible order."""),
 dict(slug='2026-11-10-paris-reel', date='2026-11-10', kind='reel', title='Paris in one day: 7 stops, one route',
      text=f"""Paris in one day 🇫🇷 7 stops, from Sacré-Cœur in the morning to the Eiffel Tower in the evening.

{sched(PARIS)}

Before you go: the Louvre is closed on Tuesdays, so book a timed slot for another day.

📌 Save this for your trip and tag who you'd take.

{CTA}

#parisitinerary #onedayinparis #paristravel #parisguide #francetravel

{credits_block([b for _, b, _ in PARIS])}"""),
 dict(slug='2026-11-12-local-names-carousel', date='2026-11-12', kind='carousel', count=10, title="The name on the sign isn't the one in your guide",
      text=f"""Your guide says Hagia Sophia. The sign says Ayasofya. 8 famous sights, by the names you'll actually see on the street →

{chr(10).join(f'{a} = {b}' for a, b, *_ in NAMES)}

📌 Save this before your trip.

Travelhour shows the name a place is signposted with, in its own language. Free on the App Store, link in bio.

#traveltips #rometravel #istanbultravel #paristravel #citybreak

{credits_block([a for a, *_ in NAMES])}"""),
 dict(slug='2026-11-14-barcelona-route-reel', date='2026-11-14', kind='reel', title='Barcelona on foot: 7 stops, one line',
      text=f"""Barcelona on foot: 7 stops in one line, about {bcn_num['km']:.1f} km.

{chr(10).join(f'{i + 1}. {n}' for i, n in enumerate(bcn_num['order']))}

📌 Save this for your trip.

Travelhour puts the places you swipe into walking order and guides you there. Free on the App Store, link in bio.

#barcelonatravel #barcelonaitinerary #walkingtour #citybreak #travelplanning

Distances are estimates: straight line between stops plus 30% for streets."""),
 dict(slug='2026-11-15-paris-carousel', date='2026-11-15', kind='carousel', count=9, title='Paris in one day: 7 stops with a tip each',
      text=f"""Paris in one day 🇫🇷 7 stops, one tip for each. Swipe →

{sched(PARIS)}

📌 Save this for your trip. Which stop would you skip?

{CTA}

#parisitinerary #paristravel #parisguide #traveltips #francetravel

{credits_block([b for _, b, _ in PARIS])}"""),
]

out = []
for p in POSTS:
    (OUT / p['slug'] / 'caption.txt').write_text(p['text'], encoding='utf-8')
    if p['kind'] == 'reel':
        p['media'] = [f"{RAW}/{p['slug']}/reel.mp4"]
        p['cover'] = f"{RAW}/{p['slug']}/cover.jpg"
    else:
        p['media'] = [f"{RAW}/{p['slug']}/{i + 1:02d}.jpg" for i in range(p['count'])]
    assert len(p['text']) <= 2200, (p['slug'], len(p['text']))
    print(p['slug'], len(p['text']), len(p['media']))
    out.append(p)
(Path(__file__).resolve().parent / 'posts.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
