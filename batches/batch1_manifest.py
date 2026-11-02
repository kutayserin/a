"""Writes caption.txt per post and posts.json for the scheduler."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch1 import OUT, RAW, TOOLS, HAIR
TAGS = '#smallbusiness #websitedesign #aiwebsite #smallbusinesstips #websitebuilder'
CTA = 'Free preview, no sign-up, about 30 seconds. You only pay if you publish. Link in bio.'
POSTS = [
 dict(slug='2026-11-04-promo-reel', date='2026-11-04', kind='reel', title='One sentence in. A real website out.', audio='1941675846329817',
      text=f"One sentence in. A real website out.\n\nDescribe your business in plain language and get the copy, the layout and the imagery back as a site you can scroll, edit and publish.\n\n{CTA}\n\n{TAGS}"),
 dict(slug='2026-11-06-prompt-carousel', date='2026-11-06', kind='carousel', count=7, title='How to write a website prompt that works',
      text=f"\"Coffee shop\" gets you a site. A better sentence gets you yours.\n\nFour things to put in a website prompt:\n1. Who and where\n2. The mood\n3. What's different\n4. What to show\n\nAnd write it in your own language: the copy follows it.\n\n📌 Save this for when you write yours.\n\n{CTA}\n\n{TAGS}"),
 dict(slug='2026-11-09-examples-reel', date='2026-11-09', kind='reel', title='Every business needs a different website', audio='957044555314519',
      text=f"A yoga studio and a dental clinic shouldn't share a website.\n\nTen example designs from our gallery, from a pizzeria in Istanbul to a wedding photographer in Lisbon. Which one is closest to your business?\n\nYours starts with one sentence. {CTA}\n\n{TAGS}"),
 dict(slug='2026-11-11-free-tools-carousel', date='2026-11-11', kind='carousel', count=8, title='6 free tools for your small business',
      text="Starting or fixing up a small business? These six are free, no sign-up.\n\n" + '\n'.join(f'{i + 1}. {t[1]}' for i, t in enumerate(TOOLS)) + f"\n\nAll at website-automation.com/tools.\n\n📌 Save this for your next rebrand.\n\nWhen you're ready for the site itself: free preview, about 30 seconds, link in bio.\n\n{TAGS}"),
 dict(slug='2026-11-13-hair-salons-carousel', date='2026-11-13', kind='carousel', count=6, title='What a hair salon website needs',
      text=HAIR['hook'] + "\n\nWhat a hair salon website needs:\n" + '\n'.join(f'{i + 1}. {t[0]}' for i, t in enumerate(HAIR['items'])) + f"\n\n📌 Save this for when you update your site.\n\nDescribe your business in plain language and get a free preview in about 30 seconds, no sign-up. Pay only if you publish. Link in bio.\n\n{TAGS}"),
 dict(slug='2026-11-16-pay-to-publish-carousel', date='2026-11-16', kind='carousel', count=6, title='See your website before you pay',
      text=f"See your website before you pay.\n\n1. Describe your business. No sign-up, no card.\n2. See a working site in about 30 seconds. You get 3 free previews a day.\n3. Pay only to publish. Plans start at $9/mo.\n4. Changed your mind? 14-day money-back guarantee on your first paid plan, and you can cancel anytime.\n\nTry it, link in bio.\n\n{TAGS}"),
]
for p in POSTS:
    (OUT / p['slug'] / 'caption.txt').write_text(p['text'], encoding='utf-8')
    tz = {"dateTime": f"{p['date']}T19:30:00", "timezone": "Europe/Istanbul"}
    reel = p['kind'] == 'reel'
    media = [f"{RAW}/{p['slug']}/reel.mp4"] if reel else [f"{RAW}/{p['slug']}/{i + 1:02d}.jpg" for i in range(p['count'])]
    assert all((OUT / p['slug'] / u.rsplit('/', 1)[1]).exists() for u in media), p['slug']
    info = {"autoPublish": True, "descendants": [], "draft": False, "firstCommentText": "", "hasNotReadNotes": False, "media": media, "mediaAltText": [],
            "providers": [{"network": "instagram"}, {"network": "tiktok"}, {"network": "facebook"}], "publicationDate": tz, "shortener": False, "smartLinkData": {"ids": []}, "text": p['text'],
            "instagramData": {"type": "REEL", "showReelOnFeed": True, "audioConfiguration": {"audioId": p['audio'], "videoVolume": 0}} if reel else {"type": "POST"},
            "facebookData": {"type": "REEL", "title": p['title']} if reel else {"type": "POST"},
            "tiktokData": {"privacyOption": "PUBLIC_TO_EVERYONE", "commercialContentOwnBrand": True, "title": p['title'], "autoAddMusic": not reel}}
    if reel:
        info["videoThumbnailUrl"] = f"{RAW}/{p['slug']}/cover.jpg"
    print('===', p['date'], p['kind'], len(p['text']))
    print(json.dumps(info, ensure_ascii=False))
