"""First two weeks of TravelHour posts. Usage: batch1.py [stills|reels|demo|bcn|captions]"""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import th_media as t

UP = Path('/mnt/user-data/uploads/travelhour')
IMG = UP / 'instagram/_work/img'
OUT = Path(__file__).resolve().parent.parent / 'posts'
meta = json.load(open(UP / 'instagram/_work/image_meta.json'))
sel = json.load(open(UP / 'instagram/_work/selection.json'))
FILE = {s[1]: s[2] for c in sel.values() for s in c['stops']}


def photo(name):
    m = meta[FILE[name]]
    return str(IMG / os.path.basename(m.get('local_hi') or m['local']))


def artist(name):
    a = meta[FILE[name]]['artist'] or 'Unknown'
    a = a.replace('This Photo was taken by ', '').split(' (')[0].split('.Please')[0].strip()
    return a if len(a) <= 34 else a[:32].rstrip() + '…'


def credit(name):
    return f"{artist(name)} · {meta[FILE[name]]['license']}"


def credits_block(names):
    lines = [f"{n}: {(meta[FILE[n]]['artist'] or 'Unknown').replace('This Photo was taken by ', '')} ({meta[FILE[n]]['license']})" for n in names]
    return '📷 Photos via Wikimedia Commons, cropped with text added\n' + '\n'.join(lines)


ROME = [('08:00', "St. Peter's Basilica"), ('09:30', "Castel Sant'Angelo"), ('11:00', 'Pantheon'), ('12:30', 'Roman Forum'),
        ('14:00', 'Circus Maximus'), ('14:45', 'Colosseum'), ('16:30', 'Santa Maria Maggiore'), ('17:30', 'Archbasilica of St. John Lateran')]
ROME_XY = {"Archbasilica of St. John Lateran": (41.88590556, 12.50615556), 'Santa Maria Maggiore': (41.8975, 12.49861111),
           'Colosseum': (41.8903, 12.4922), 'Roman Forum': (41.8922, 12.4852), 'Circus Maximus': (41.8858, 12.4856),
           'Pantheon': (41.8986, 12.4768), "Castel Sant'Angelo": (41.9031, 12.4663), "St. Peter's Basilica": (41.90222222, 12.45333333)}
ISTANBUL = [('08:30', 'Sultan Ahmed Mosque', 'Free to enter. Visitors step out during the five daily prayers.'),
            ('09:30', 'Hagia Sophia', 'Built in 537 AD and a working mosque today, so dress modestly.'),
            ('11:00', 'Basilica Cistern', 'Look for the two Medusa heads at the base of the columns.'),
            ('12:00', 'Topkapı Palace', 'Home of the Ottoman sultans for almost four centuries. Closed on Tuesdays.'),
            ('14:30', 'Dolmabahçe Palace', 'Go before mid-afternoon: it shuts at 17:00, and all day on Mondays.'),
            ('16:15', 'Galata Tower', 'Go up for a 360° view across the Bosphorus.'),
            ('17:30', 'Süleymaniye Mosque', 'Built by the architect Sinan, with a view over the Golden Horn.'),
            ('19:00', "Maiden's Tower", 'Walk down to Eminönü and take the ferry to Üsküdar for the best view.')]
PARIS = [('08:00', 'Sacré-Cœur', 'Free to enter. Climb Montmartre early, before the crowds.'),
         ('10:00', 'Louvre Museum', 'Book a timed slot, and skip Tuesdays: it is closed.'),
         ('12:30', 'Notre-Dame', 'Reopened in December 2024. Free to enter, with free slots you can reserve online.'),
         ('13:30', 'Panthéon', "Foucault's pendulum swings under the dome. Voltaire and Marie Curie lie in the crypt."),
         ('16:00', 'Champs-Élysées', 'Start at Place de la Concorde and walk up toward the Arc.'),
         ('17:30', 'Arc de Triomphe', 'Use the underpass, never the roundabout. The rooftop looks straight down the avenue.'),
         ('19:30', 'Eiffel Tower', 'It sparkles on the hour after dark. Watch from Trocadéro.')]
NAMES = [('Colosseum', 'Colosseo', 'Say: co-lo-SEH-o', 'Rome'),
         ('Roman Forum', 'Foro Romano', 'Say: FOH-ro ro-MAH-no', 'Rome'),
         ("St. Peter's Basilica", 'Basilica di San Pietro', 'Say: bah-ZEE-lee-kah dee san PYEH-tro', 'Rome'),
         ('Sultan Ahmed Mosque', 'Sultanahmet Camii', 'The Blue Mosque. Say: sul-TAHN-ah-met jah-MEE', 'Istanbul'),
         ('Hagia Sophia', 'Ayasofya', 'Say: ah-yah-SOF-yah', 'Istanbul'),
         ('Basilica Cistern', 'Yerebatan Sarnıcı', 'Say: yeh-reh-bah-TAHN sar-nuh-juh', 'Istanbul'),
         ("Maiden's Tower", 'Kız Kulesi', 'Say: kuhz koo-leh-see', 'Istanbul'),
         ('Eiffel Tower', 'Tour Eiffel', 'Say: toor eh-FEL', 'Paris')]
BCN = [('Park Güell', 41.4136, 2.1528), ('Sagrada Família', 41.4037, 2.1743), ('Casa Milà', 41.3953, 2.1617), ('Casa Batlló', 41.3916, 2.1649),
       ('Palau de la Música', 41.3877, 2.1753), ('Barcelona Cathedral', 41.3839, 2.1764), ('Palau Güell', 41.3788, 2.1744)]
END_SUB = 'Swipe the landmarks you love. Travelhour turns them into one walking route.'
FOOT = 'Photos: Wikimedia Commons · full credits in caption'


def stills(sh):
    d = OUT / '2026-11-07-istanbul-carousel'
    n = len(ISTANBUL)
    t.photo_cover(sh, d / '01.jpg', photo('Hagia Sophia'), 'SAVE FOR YOUR TRIP', 'Istanbul', 'in one day', f'{n} stops &nbsp;·&nbsp; 08:30 → 19:00')
    for i, (tm, name, tip) in enumerate(ISTANBUL):
        t.photo_stop(sh, d / f'{i + 2:02d}.jpg', photo(name), credit(name), f'STOP {i + 1:02d} &nbsp;·&nbsp; {tm}', name, tip, i + 1, n)
    t.end_card(sh, d / '10.jpg', 1080, 1350, 'Plan your <i>Istanbul</i> day', END_SUB, FOOT)

    d = OUT / '2026-11-15-paris-carousel'
    n = len(PARIS)
    t.photo_cover(sh, d / '01.jpg', photo('Eiffel Tower'), 'SAVE FOR YOUR TRIP', 'Paris', 'in one day', f'{n} stops &nbsp;·&nbsp; 08:00 → 19:30')
    for i, (tm, name, tip) in enumerate(PARIS):
        t.photo_stop(sh, d / f'{i + 2:02d}.jpg', photo(name), credit(name), f'STOP {i + 1:02d} &nbsp;·&nbsp; {tm}', name, tip, i + 1, n)
    t.end_card(sh, d / '09.jpg', 1080, 1350, 'Plan your <i>Paris</i> day', END_SUB, FOOT)

    d = OUT / '2026-11-12-local-names-carousel'
    n = len(NAMES)
    t.photo_cover(sh, d / '01.jpg', photo('Hagia Sophia'), 'READ THE SIGNS', 'Your guide says Hagia Sophia.', 'The sign says Ayasofya.',
                  '8 famous sights, by their local names', big_css='font-size:112px;line-height:1.02;letter-spacing:-.01em')
    for i, (known, local, say, city) in enumerate(NAMES):
        t.photo_stop(sh, d / f'{i + 2:02d}.jpg', photo(known), credit(known), f'YOUR GUIDE SAYS &nbsp;·&nbsp; {t.esc(known.upper())}', local, say, i + 1, n)
    t.end_card(sh, d / '10.jpg', 1080, 1350, 'Find it by<br><i>the name on the sign</i>',
               'Travelhour shows the name a place is signposted with, in its own language.', FOOT)

    stops = [dict(name=k.replace('Archbasilica of St. John Lateran', 'St. John Lateran'), lat=v[0], lon=v[1]) for k, v in ROME_XY.items()]
    r = t.order_carousel(sh, 'Rome', stops, OUT / '2026-11-08-rome-order-carousel', first="St. Peter's Basilica")
    (OUT / '2026-11-08-rome-order-carousel' / 'numbers.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(r)


def reels(sh):
    st = [dict(time=a, name=b, photo=photo(b), credit=credit(b)) for a, b in ROME]
    print('rome', t.photo_reel(sh, 'Rome', st, photo('Colosseum'), OUT / '2026-11-03-rome-reel', END_SUB, FOOT))
    st = [dict(time=a, name=b, photo=photo(b), credit=credit(b)) for a, b, _ in PARIS]
    print('paris', t.photo_reel(sh, 'Paris', st, photo('Eiffel Tower'), OUT / '2026-11-10-paris-reel', END_SUB, FOOT))


def bcn(sh):
    stops = [dict(name=a, lat=b, lon=c) for a, b, c in BCN]
    r = t.route_reel(sh, 'Barcelona', stops, OUT / '2026-11-14-barcelona-route-reel')
    (OUT / '2026-11-14-barcelona-route-reel' / 'numbers.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(r)


DEMO = [(0.3, 1.7, 1, 'Landed in Rome. <i>Now what?</i>'),
        (2.0, 1.9, 1, 'The places you swiped are already <i>one shortlist.</i>'),
        (4.2, 2.4, 1, "Pick the city you're walking <i>today.</i>"),
        (21.0, 3.6, 1, "One tap and it's <i>a walking route.</i>"),
        (24.6, 3.0, 2, 'Follow it <i>live</i> on a 3D map.'),
        (38.0, 3.0, 1, 'Phone in your pocket? It <i>tells you</i> when you arrive.'),
        (50.2, 2.6, 1, "Then read the story of <i>where you're standing.</i>"),
        (54.6, 2.0, 1, 'Trip complete. <i>Share the day.</i>')]


def demo(sh):
    from PIL import Image, ImageDraw
    src = UP / 'screenrecordappstore/castel.mov'
    d = OUT / '2026-11-05-app-demo-reel'
    d.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    PW, PH, PX, PY = 620, 1348, 230, 400
    S = 4
    mask = Image.new('L', (PW * S, PH * S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PW * S - 1, PH * S - 1), radius=54 * S, fill=255)
    mask = mask.resize((PW, PH), Image.LANCZOS)
    mask.save(tmp / 'mask.png')
    css = f"""
.h{{position:absolute;left:80px;right:80px;top:128px;height:250px;display:flex;align-items:flex-start}}
.t{{font:600 76px/1.06 'Fraunces';color:{t.INK};letter-spacing:-.01em}}
.t i{{font-weight:500;color:{t.TERRA}}}
.ph{{position:absolute;left:{PX}px;top:{PY}px;width:{PW}px;height:{PH}px;border-radius:54px;box-shadow:0 26px 70px rgba(26,20,16,.28)}}
"""
    segs, durs = [], []
    for i, (ss, dur, speed, head) in enumerate(DEMO):
        bg = tmp / f'bg{i}.png'
        sh.shot(t.page(1080, 1920, f'<div class="h"><div class="t">{head}</div></div><div class="ph"></div>', css, bg=t.CREAM), bg, 1080, 1920)
        seg = tmp / f's{i}.mp4'
        fc = (f"[0:v]setpts=PTS/{speed},fps={t.FPS},scale={PW}:{PH}:flags=lanczos,format=rgba[v];"
              f"[2:v]format=gray,scale={PW}:{PH}[m];[v][m]alphamerge[vm];"
              f"[1:v]fps={t.FPS}[b];[b][vm]overlay={PX}:{PY}:shortest=1,format=yuv420p[o]")
        t.ff(['-ss', ss, '-t', dur * speed, '-i', src, '-loop', 1, '-t', dur, '-i', bg, '-loop', 1, '-t', dur, '-i', tmp / 'mask.png',
              '-filter_complex', fc, '-map', '[o]', '-an', '-frames:v', int(round(dur * t.FPS)), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 17, seg])
        segs.append(seg)
        durs.append(dur)
    end = tmp / 'end.png'
    t.end_card(sh, end, 1080, 1920, 'Plan a day in <i>any</i> city', END_SUB, 'Screen recording from the app.')
    t.still_segment(end, t.END_DUR, tmp / 'end.mp4')
    segs.append(tmp / 'end.mp4')
    durs.append(t.END_DUR)
    total = t.join(segs, durs, tmp / 'silent.mp4', xfade=0.2)
    t.ambient_bed(tmp / 'bed.m4a', total)
    t.mux_audio(tmp / 'silent.mp4', tmp / 'bed.m4a', d / 'reel.mp4')
    t.ff(['-ss', 0.8, '-i', d / 'reel.mp4', '-frames:v', 1, '-q:v', 2, d / 'cover.jpg'])
    print('demo', total)


if __name__ == '__main__':
    what = sys.argv[1:] or ['stills']
    with t.Shooter() as sh:
        for w in what:
            {'stills': stills, 'reels': reels, 'demo': demo, 'bcn': bcn}[w](sh)
