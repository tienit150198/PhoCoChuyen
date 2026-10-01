"""💍 Live weddings, the game server's side (design: docs/superpowers/specs/2026-10-01-live-wedding-design.md).

The live party itself runs in the live service (live/wedding.py: the room `wed:<id>`, attendance, the guests' and the
couple's rewards, the reminder, the weekly settle). This module holds what the game server does:

* the tables (SQLite twin of game/pg_schema.py), all new: nothing existing changes;
* booking: a confirmed plan with a real date and time (`plan.at`, 1 hour to 14 days ahead) stores the couple's date
  for good (`wedding_dates`, insert-only) and books the party (`wedding_parties`). The in-game ceremony then
  resolves at that time (`weddings.due_at`) instead of after N life days; older plans keep their life days;
* the couple's date: `wedding_dates`, or for couples married before this feature their done wedding's time, else
  `couples.married_at`, written once as a 'legacy' row the first time it is needed (only adds, never rewrites);
* anniversaries on load (100 days, a year, 500 and 1000 real days since that date): coins, a title and the private
  congratulation card (game/live_effects.py: the system-gift popup), lì xì from the neighbours, a news line. Paid
  once per couple and milestone (idempotent keys); a divorce stops the count;
* the weekly race view ("Khách mời của tuần", Xếp hạng), the couple's party photos (Kỷ niệm) and the upload of one.

Rewards are `live_effects` rows (the live service's grant() rows, or inserted here with the same rules), paid by
game/live_effects.py through the game's own command path.
"""
from __future__ import annotations

import base64
import datetime
import json
import random
import re
import time

# ---- owner-approved numbers (01/10/2026); adjustable ----
BOOK_MIN = 3600                 # a wedding is booked at least 1 hour ahead
BOOK_MAX = 14 * 86400           # and at most 14 days ahead
CONFIRM_MIN = 15 * 60           # the partner confirms while the time is still at least 15 minutes away
OPEN_BEFORE = 10 * 60           # the party room opens 10 minutes before the start
PARTY_SECS = 30 * 60            # and lasts 30 minutes from the start
REMIND_BEFORE = 30 * 60         # friends get a reminder 30 minutes before
VISIBLE = 60                    # avatars shown at once; more guests watch from the "đông quá" view, still counted
GUEST_STEP = 5 * 60             # a guest earns GUEST_XU for every 5 minutes present
GUEST_XU = 15
GUEST_STEPS = 4                 # at most 4 per wedding (60 xu)
GUEST_WEDDINGS_PER_DAY = 2      # rewards from at most 2 weddings a day
GUEST_CLOSE = 2                 # closeness with each spouse, once per wedding
HOST_XU = 30                    # each spouse, for every guest who stayed 5 minutes
HOST_COUNT_MAX = 50
HOST_BONUS = ((10, 100, None), (20, 250, 'w_crowd'))
ANNIVERSARIES = ((100, 200, 'w_100', '100'), (365, 500, 'w_1y', 'một năm'), (500, 800, 'w_500', '500'),
                 (1000, 1500, 'w_1000', '1000'))   # (days, xu for each spouse, title, "tròn … ngày cưới")
ANNIV_NPC = (40, 120)           # lì xì from the neighbours on an anniversary (deterministic per couple and milestone)
RACE = ((1, 300, 'w_vip'), (2, 150, 'w_pro'), (3, 150, 'w_pro'))
PHOTOS_MAX = 3                  # group photos kept per wedding
PHOTO_BYTES = 44 * 1024         # one photo (a canvas snapshot, webp or jpeg; base64 fits the 64 KB POST limit)

TITLE_NAMES = dict(w_crowd='🎉 Đám cưới đông vui', w_100='💞 Trăm ngày bên nhau', w_1y='🎂 Tròn một năm', w_500='💍 Năm trăm ngày thương',
                   w_1000='👑 Nghìn ngày son sắt', w_vip='🥇 Khách quý của phố', w_pro='🎊 Ăn cưới chuyên nghiệp')
VN = datetime.timezone(datetime.timedelta(hours=7))

SCHEMA = """
CREATE TABLE IF NOT EXISTS wedding_dates (
  couple INTEGER PRIMARY KEY, at REAL NOT NULL, source TEXT NOT NULL, wedding INTEGER, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS wedding_parties (
  wedding INTEGER PRIMARY KEY, couple INTEGER NOT NULL, a TEXT NOT NULL, b TEXT NOT NULL, at REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'booked', reminded REAL, guests INTEGER NOT NULL DEFAULT 0, done_at REAL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS wedding_guests (
  wedding INTEGER NOT NULL, sid TEXT NOT NULL, pid TEXT NOT NULL, ok INTEGER NOT NULL DEFAULT 0, paid INTEGER NOT NULL DEFAULT 0,
  steps INTEGER NOT NULL DEFAULT 0, counted_at REAL NOT NULL, day TEXT NOT NULL, week TEXT NOT NULL,
  PRIMARY KEY (wedding, sid)
);
CREATE TABLE IF NOT EXISTS wedding_photos (
  wedding INTEGER NOT NULL, n INTEGER NOT NULL, sid TEXT NOT NULL, at REAL NOT NULL, image TEXT, PRIMARY KEY (wedding, n)
);
CREATE TABLE IF NOT EXISTS wedding_race (week TEXT PRIMARY KEY, settled REAL NOT NULL, top TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS player_closeness (
  sid TEXT NOT NULL, other TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL, PRIMARY KEY (sid, other)
);
CREATE INDEX IF NOT EXISTS wedding_parties_at ON wedding_parties(status, at);
CREATE INDEX IF NOT EXISTS wedding_guests_week ON wedding_guests(week, ok);
CREATE INDEX IF NOT EXISTS wedding_guests_sid ON wedding_guests(sid, day);
"""


class WeddingError(Exception):
    def __init__(self, message: str, code: str = 'wedding', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'wedding', status: int = 400):
    if not cond:
        raise WeddingError(message, code, status)


def now() -> float:
    return time.time()


# ---------------------------------------------------------------- Vietnam calendar
def vn(t: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(t, VN)


def vn_day(t: float) -> str:
    return vn(t).strftime('%Y-%m-%d')


def vn_week(t: float) -> str:
    """ISO week of the Vietnam date (Monday to Sunday), e.g. '2026-W40'."""
    y, w, _ = vn(t).isocalendar()
    return f'{y}-W{w:02d}'


def week_start(t: float) -> float:
    d = vn(t).replace(hour=0, minute=0, second=0, microsecond=0)
    return (d - datetime.timedelta(days=d.weekday())).timestamp()


def days_between(t0: float, t1: float) -> int:
    """Calendar days in Vietnam from t0's day to t1's day."""
    return (vn(t1).date() - vn(t0).date()).days


def fmt_at(t: float) -> str:
    """'04/10/2026 · 20:30' (Vietnam time)."""
    return vn(t).strftime('%d/%m/%Y · %H:%M')


# ---------------------------------------------------------------- booking (game/marriage.py calls these)
def clean_at(at, t: float | None = None) -> float | None:
    """A plan's real date and time (epoch seconds), 1 hour to 14 days ahead; None when the plan has none
    (a client from before this feature: the wedding keeps its life days)."""
    if at is None:
        return None
    t = now() if t is None else t
    from .marriage import need as mneed
    mneed(type(at) in (int, float) and at == at, 'Giờ cưới không hợp lệ.', 'bad_plan')
    at = float(int(at) // 60 * 60)   # whole minutes
    mneed(at >= t + BOOK_MIN, 'Chọn giờ cưới cách bây giờ ít nhất 1 tiếng nhé.', 'bad_plan')
    mneed(at <= t + BOOK_MAX, 'Chọn ngày cưới trong vòng 14 ngày tới nhé.', 'bad_plan')
    return at


def book(db, couple: dict, wedding_id: int, at: float) -> None:
    """At confirmation: the couple's date for good, and the party."""
    t = now()
    db.execute('INSERT INTO wedding_dates(couple, at, source, wedding, created) VALUES(?, ?, ?, ?, ?) ON CONFLICT(couple) DO NOTHING',
               (couple['id'], at, 'booked', wedding_id, t))
    db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) VALUES(?, ?, ?, ?, ?, 'booked', ?) "
               'ON CONFLICT(wedding) DO NOTHING', (wedding_id, couple['id'], couple['a'], couple['b'], at, t))


def cancel_party(db, couple_id: int) -> None:
    """A divorce or a broken engagement before the day: the party is off."""
    db.execute("UPDATE wedding_parties SET status='cancelled' WHERE couple=? AND status='booked'", (couple_id,))


def date_of(db, couple: dict, write: bool = False) -> float | None:
    """The couple's wedding date and time: booked, or for older couples their wedding's time, else married_at.
    write: store a legacy one the first time (insert-only, inside the caller's transaction)."""
    r = db.execute('SELECT at FROM wedding_dates WHERE couple=?', (couple['id'],)).fetchone()
    if r:
        return float(r['at'])
    if couple.get('status') != 'married':
        return None
    w = db.execute("SELECT id, done_at FROM weddings WHERE couple=? AND status='done' ORDER BY id DESC LIMIT 1", (couple['id'],)).fetchone()
    at = float(w['done_at']) if w and w['done_at'] else (float(couple['married_at']) if couple.get('married_at') else None)
    if at is not None and write:
        db.execute("INSERT INTO wedding_dates(couple, at, source, wedding, created) VALUES(?, ?, 'legacy', ?, ?) ON CONFLICT(couple) DO NOTHING",
                   (couple['id'], at, w['id'] if w else None, now()))
    return at


def label_of(db, couple: dict | None) -> str | None:
    """'💍 Cưới ngày 04/10/2026 · 20:30' for a card, or None."""
    if not couple:
        return None
    at = date_of(db, couple)
    return f'💍 Cưới ngày {fmt_at(at)}' if at else None


# ---------------------------------------------------------------- rewards (the live_effects rows)
def grant(db, sid: str, kind: str, amount: int, key: str, data: dict | None = None) -> bool:
    """One live_effects row (game/live_effects.py pays it), idempotent by key. Same table as live/effects.py grant()."""
    return db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, ?, ?, ?, 'pending', ?) "
                      'ON CONFLICT(id) DO NOTHING', (key, sid, kind, int(amount), json.dumps(data or {}, ensure_ascii=False, separators=(',', ':')),
                                                     now())).rowcount == 1


def anniversaries(store, sid: str) -> bool:
    """On load: a married couple whose date reached 100 days, a year, 500 or 1000 days gets each milestone once:
    for each spouse coins (with the private congratulation card) and a title, the neighbours' lì xì; and a news
    line. True when rows were added (the caller then pays them). One indexed query for everyone else."""
    from . import marriage as mr
    with store.connect() as db:
        c = mr._bond(db, sid)
        if not c or c['status'] != 'married':
            return False
        at = date_of(db, c)
    if at is None:
        return False
    days = days_between(at, now())
    due = [m for m in ANNIVERSARIES if days >= m[0]]
    if not due:
        return False

    def run(db):
        date_of(db, c, write=True)
        names = dict(a=mr._display(db, c['a']), b=mr._display(db, c['b']))
        w = db.execute("SELECT announce_a, announce_b FROM weddings WHERE couple=? AND status='done' ORDER BY id DESC LIMIT 1", (c['id'],)).fetchone()
        added = False
        for d, xu, tid, label in due:
            for side, other in (('a', 'b'), ('b', 'a')):
                base = f'anniv:{c["id"]}:{d}:{side}'
                text = (f'Hôm nay bạn và {names[other]} tròn {label} ngày cưới. Phố gửi hai bạn quà mừng và danh hiệu '
                        f'“{TITLE_NAMES[tid]}”. Chúc hai bạn mãi vui như ngày đầu 💛')
                added |= grant(db, c[side], 'coins', xu, base, dict(src='anniv', popup=dict(title=f'{TITLE_NAMES[tid]}', text=text)))
                added |= grant(db, c[side], 'title', 1, base + ':t', dict(title=tid))
                npc = random.Random(f'{base}:npc').randint(*ANNIV_NPC)
                added |= grant(db, c[side], 'coins', npc, base + ':npc', dict(src='anniv_npc'))
            if not w or (w['announce_a'] and w['announce_b']):
                mr._post_news(db, 'anniversary', f'anniv:{c["id"]}:{d}', f'Hôm nay {names["a"]} và {names["b"]} tròn {label} ngày cưới 🎉', c['a'], c['b'])
        return added
    return bool(store.transaction(run))


def on_load(store, token: str, state: dict | None) -> bool:
    """Bootstrap (before game/live_effects.on_load): the anniversaries of this save's couple."""
    if not state or not (state.get('journey') or {}).get('story'):
        return False
    return anniversaries(store, store.key(token))


# ---------------------------------------------------------------- views
def race(db, week: str, limit: int = 20) -> list:
    """The week's guests: weddings attended ≥ 5 minutes (counted guests only), most first; a tie goes to whoever
    reached that count first."""
    return [dict(r) for r in db.execute('SELECT sid, pid, COUNT(*) AS n, MAX(counted_at) AS last FROM wedding_guests WHERE week=? AND ok=1 '
                                        'GROUP BY sid, pid ORDER BY n DESC, last ASC, sid LIMIT ?', (week, limit))]


def race_view(store, sid: str | None) -> dict:
    """GET /api/wedding/race: "Khách mời của tuần" now, my place, and last week's winners."""
    t = now()
    week, last_week = vn_week(t), vn_week(week_start(t) - 3600)
    with store.connect() as db:
        rows = race(db, week)
        mine = None
        if sid and not any(r['sid'] == sid for r in rows):
            r = db.execute('SELECT COUNT(*) AS n FROM wedding_guests WHERE week=? AND ok=1 AND sid=?', (week, sid)).fetchone()
            mine = int(r['n']) if r else 0
        top = [dict(rank=i + 1, name=_public_name(db, r['sid'], sid), n=int(r['n']), me=r['sid'] == sid) for i, r in enumerate(rows)]
        prev = db.execute('SELECT top FROM wedding_race WHERE week=?', (last_week,)).fetchone()
        winners = []
        for w in json.loads(prev['top']) if prev else []:
            winners.append(dict(rank=w['rank'], name=_public_name(db, w['sid'], sid), n=w['n'], title=TITLE_NAMES.get(w['title'], ''), me=w['sid'] == sid))
    ends = week_start(t) + 7 * 86400
    return dict(week=week, top=top, mine=mine, ends=ends, last=dict(week=last_week, winners=winners),
                prizes=[dict(rank=r, xu=x, title=TITLE_NAMES[tid]) for r, x, tid in RACE])


def _public_name(db, sid: str, viewer: str | None) -> str:
    """The name Xếp hạng would show (game/leaderboard.py privacy: accounts by default, guests once they opt in)."""
    from . import leaderboard as lb
    p = lb._privacy(db, sid)
    return p['name'] if p['name'] and (p['visible'] or sid == viewer) else 'Một người chơi'


def photos(store, sid: str) -> list:
    """GET /api/wedding/photos: the group photos of my weddings (Kỷ niệm), newest first."""
    with store.connect() as db:
        rows = db.execute('SELECT p.wedding, p.n, p.at, p.image, w.at AS wed_at, w.a, w.b FROM wedding_photos p JOIN wedding_parties w ON w.wedding=p.wedding '
                          'WHERE (w.a=? OR w.b=?) AND p.image IS NOT NULL ORDER BY p.at DESC LIMIT 12', (sid, sid)).fetchall()
    return [dict(wedding=int(r['wedding']), n=int(r['n']), at=float(r['at']), image=r['image'], date=fmt_at(float(r['wed_at']))) for r in rows]


_IMAGE = re.compile(r'data:image/(webp|jpeg);base64,([A-Za-z0-9+/=]+)')


def save_photo(store, sid: str, d: dict) -> dict:
    """POST /api/wedding/photo {wedding, n, image}: the snapshot of a group photo the live service reserved for this
    player (wedding_photos row without an image). Once; at most PHOTO_BYTES; webp or jpeg only."""
    wid, n, image = d.get('wedding'), d.get('n'), d.get('image')
    need(type(wid) is int and type(n) is int and 1 <= n <= PHOTOS_MAX, 'Ảnh không hợp lệ.')
    m = _IMAGE.fullmatch(image) if isinstance(image, str) and len(image) <= PHOTO_BYTES * 4 // 3 + 40 else None
    need(m, 'Ảnh không hợp lệ.')
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except ValueError:
        raw = b''
    need(0 < len(raw) <= PHOTO_BYTES and (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' or raw[:3] == b'\xff\xd8\xff'), 'Ảnh không hợp lệ.')
    t = now()
    ok = store.transaction(lambda db: db.execute('UPDATE wedding_photos SET image=? WHERE wedding=? AND n=? AND sid=? AND image IS NULL AND at>?',
                                                 (image, wid, n, sid, t - 600)).rowcount)
    need(ok == 1, 'Ảnh này đã lưu hoặc hết hạn.', 'gone', 409)
    return dict(ok=True)


def close_points(db, sid: str, other: str) -> int:
    try:
        r = db.execute('SELECT points FROM player_closeness WHERE sid=? AND other=?', (sid, other)).fetchone()
    except Exception:  # noqa: BLE001 - a database from before these tables
        return 0
    return int(r['points']) if r else 0


def forget(store, token: str) -> None:
    """Account deletion ("XOA"): this save's attendance, closeness and the photos it took go with it."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM wedding_guests WHERE sid=?', (sid,))
        db.execute('DELETE FROM player_closeness WHERE sid=? OR other=?', (sid, sid))
        db.execute('DELETE FROM wedding_photos WHERE sid=?', (sid,))
    store.transaction(run)


