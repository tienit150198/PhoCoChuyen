"""Hãng bay Cánh Cò: the small regional airline behind the two air careers
(pilot, flight_attendant). Not a career itself (it is not listed in careers.ORDER).

The player still lives in the phố: before dawn they ride out of the lane to the
city airport, fly short hops to the islands and the delta on a 68-seat turboprop
("tàu Cò Trắng") and are home for bà Tám's dinner. Both careers share the crew,
the routes, the cabin and the working hours kept here, so the captain the pilot
flies with is the same one the cabin crew calls, and the regulars on the
Côn Đảo run are the same people in both jobs.

Everything is fixed content or a pure function of (day, slot): tasks built from it
regenerate exactly (engine.validate_state).
"""
from __future__ import annotations

from . import kit
from .. import inventory as inv

AIRLINE = 'Hãng bay Cánh Cò'
PLANE = 'tàu Cò Trắng'
HOME = 'Thành phố'
ROWS = 17                     # 17 rows of A B | C D: 68 seats
SEATS = 'ABCD'
EXIT_ROWS = (1, 17)           # rows next to the doors: able adults from 15 only
HOURS = (5 * 60 + 30, 19 * 60 + 30)   # crew report at 05:30; the last hop is home by evening
FIRST_DEP, EVERY = 6 * 60 + 10, 95    # the day's first departure and the rhythm of the hops after it

# Destinations from the city. trip = fuel for the hop (kg), alt = the alternate airfield and the fuel to reach it.
ROUTES = [
    dict(id='cd', to='Côn Đảo', emoji='🏝️', minutes=50, trip=650, alt='Cần Thơ', alt_fuel=300, coast=True),
    dict(id='rg', to='Rạch Giá', emoji='🚤', minutes=40, trip=520, alt='Cà Mau', alt_fuel=250, coast=True),
    dict(id='cm', to='Cà Mau', emoji='🦀', minutes=55, trip=700, alt='Rạch Giá', alt_fuel=250, coast=True),
    dict(id='pq', to='Phú Quốc', emoji='🐚', minutes=60, trip=780, alt='Rạch Giá', alt_fuel=250, coast=True),
    dict(id='dl', to='Đà Lạt', emoji='🌲', minutes=50, trip=650, alt='Buôn Ma Thuột', alt_fuel=350, coast=False),
]
HOME_ALT = dict(alt='Cần Thơ', alt_fuel=300)

# Register the crew hours with the shop clock (read at call time, like consequences.INSPECTION).
for _cid in ('pilot', 'flight_attendant'):
    inv.HOURS.setdefault(_cid, HOURS)


def leg(day: int, slot: int) -> dict:
    """The hop flown in this slot: slots 0/1 are out and back on one route, 2/3 on the next…
    Both careers see the same routes on the same day."""
    pair = slot // 2
    r = ROUTES[kit.rng('airline', 'route', day, pair).randrange(len(ROUTES))]
    out = slot % 2 == 0
    code = f'CC {100 + (day * 7 + pair * 2) % 80 * 2 + (0 if out else 1)}'
    at = (FIRST_DEP + slot * EVERY) % (24 * 60)
    when = dict(dep=f'{at // 60:02d}:{at % 60:02d}', gate=1 + kit.rng('airline', 'gate', day, slot).randrange(6))
    if out:
        return dict(code=code, route=r['id'], frm=HOME, to=r['to'], emoji=r['emoji'], minutes=r['minutes'], trip=r['trip'],
                    alt=r['alt'], alt_fuel=r['alt_fuel'], coast=r['coast'], out=True, **when)
    return dict(code=code, route=r['id'], frm=r['to'], to=HOME, emoji='🏙️', minutes=r['minutes'], trip=r['trip'],
                alt=HOME_ALT['alt'], alt_fuel=HOME_ALT['alt_fuel'], coast=r['coast'], out=False, **when)


def seat_side(s: str) -> str:
    """Where a seat is, the way a flight attendant points to it."""
    letter = s[-1]
    return {'A': 'bên trái, sát cửa sổ', 'B': 'bên trái, sát lối đi', 'C': 'bên phải, sát lối đi', 'D': 'bên phải, sát cửa sổ'}.get(letter, '')



# ---------------------------------------------------------------- reviews (feedback.make_review → careers' review_text)
def _band(stars: int) -> int:
    return 5 if stars >= 5 else 4 if stars == 4 else 3 if stars == 3 else 1


def review(t: dict, stars: int, criteria: list, seed: int, voice: dict, lines: dict | None) -> str:
    """A few words after a flight, in the reviewer's own voice: an opener by stars, then one concrete line. `lines`
    maps criterion keys to what a passenger saw (pos, neg); without it (the crew's debrief) the criterion speaks as
    itself. A mistake on the job is named as the job recorded it. Pure: the same review always reads the same."""
    leg = (t.get('needs') or {}).get('leg') or {}
    band = _band(stars)
    rows = voice.get(band) or voice[5]
    head = rows[seed % len(rows)].format(code=leg.get('code', ''), to=leg.get('to', ''))
    slips = sorted(t.get('slips') or [], key=lambda r: -r['sev'])
    if slips:
        body = slips[0]['text']
    else:
        known = [x for x in criteria if lines is None or x['key'] in lines]
        body = ''
        if known:
            x = min(known, key=lambda r: r['score']) if band < 5 else known[(seed // 7) % len(known)]
            if lines is None:
                body = f'{x["label"]}: {x["note"]}.' if x.get('note') else ''
            else:
                body = lines[x['key']][0 if x['score'] >= 5 else 1]
    return f'{head} {body}'.strip()
