# TravelHour social media assets

Public media for scheduled TravelHour posts. Metricool pulls files from this branch by URL.
`main` of this repo is unrelated and untouched.

- `posts/<date>-<slug>/`: final media and caption of each post
- `tools/`: slide, reel and route renderer (`make_city.py` builds one post for a queued city)
- `data/route_queue.json`: vetted cities for the map posts
- `batches/`: the hand-built first two weeks
