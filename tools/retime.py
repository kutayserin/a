#!/usr/bin/env python3
"""Move one day's calendar rows onto the posting times chosen from
Metricool's best-time data. The nightly scheduling runs of TravelHour,
website-automation and CompassUni fetch this file and call it before
creating posts.

    python3 retime.py ROWS.json --slots 10:30,11:30,12:30 [--from 2026-11-12]

ROWS.json is a calendar/<date>.json or linkedin/<date>.json list. Rows are
taken in time order and given the slots in order; rows beyond the last slot
keep their own time. Days before --from keep their times, because they were
already scheduled at the old ones. Only `date`, `slot` and
`info.publicationDate.dateTime` change; the rest of each row is copied as is.
Prints the new list as JSON.
"""
import argparse
import json
import re
import sys


def parse_slots(text):
    slots = [s.strip() for s in text.split(',') if s.strip()]
    for s in slots:
        if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', s):
            sys.exit(f'bad slot: {s}')
    if slots != sorted(slots) or len(set(slots)) != len(slots):
        sys.exit('slots must be distinct and in time order')
    return slots


def retime(rows, slots, start):
    rows = sorted(rows, key=lambda r: r['date'])
    out, seen = [], {}
    for row in rows:
        day = row['date'][:10]
        i = seen.get(day, 0)
        seen[day] = i + 1
        if day < start or i >= len(slots):
            out.append(row)
            continue
        hhmm = slots[i]
        offset = row['date'][19:]  # '+03:00'
        row['date'] = f'{day}T{hhmm}:00{offset}'
        if 'slot' in row:
            row['slot'] = f'{day}T{hhmm}'
        row['info']['publicationDate']['dateTime'] = f'{day}T{hhmm}:00'
        out.append(row)
    return sorted(out, key=lambda r: r['date'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rows')
    ap.add_argument('--slots', required=True)
    ap.add_argument('--from', dest='start', default='0000-00-00')
    a = ap.parse_args()
    with open(a.rows, encoding='utf-8') as f:
        rows = json.load(f)
    json.dump(retime(rows, parse_slots(a.slots), a.start), sys.stdout,
              ensure_ascii=False, indent=1)
    print()


if __name__ == '__main__':
    main()
