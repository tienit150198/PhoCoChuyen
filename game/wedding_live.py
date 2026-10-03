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

# ---- owner-approved numbers (01/10/2026; the party itself reworked by the owner after the first one); adjustable ----
BOOK_MIN = 3600                 # a wedding plan is booked at least 1 hour ahead
BOOK_MAX = 14 * 86400           # and at most 14 days ahead
CONFIRM_MIN = 15 * 60           # the partner confirms while the time is still at least 15 minutes away
PARTY_BOOK_MIN = 10 * 60        # "Tổ chức tiệc cưới" (any couple with a wedding, free): at least 10 minutes ahead
OPEN_BEFORE = 5 * 60            # the party room opens 5 minutes before the start (guests gather; nothing paid yet)
PARTY_SECS = 10 * 60            # one party, 10 minutes (owner)
MINUTE_SECS = 60                # one paid minute (a dev script shortens it)
PARTY_MINUTES = PARTY_SECS // MINUTE_SECS
MINUTE_XU = 20                  # every minute of the party, everyone present (the couple too) gets 20 xu (owner)
REMIND_BEFORE = 30 * 60         # friends get a reminder 30 minutes before
VISIBLE = 60                    # avatars shown at once; more guests watch from the "đông quá" view, still counted
GUEST_WEDDINGS_PER_DAY = 2      # a guest's minute money from at most 2 weddings a day (anti-farming; still counted)
GUEST_CLOSE = 2                 # closeness with each spouse, once per wedding
GUEST_MIN_MINUTES = 2           # "đi ăn cưới" counts (the couple's 15 xu, Khách mời của tuần) from 2 minutes at the party (owner, 01/10)
HOST_XU = 15                    # each spouse, for every counted guest who came (owner: 15 xu a guest, no cap but the room's)
HOST_COUNT_MAX = 360            # VISIBLE + the watchers (live/wedding.py WATCHERS_MAX)
HOST_BONUS = ((20, 0, 'w_crowd'),)   # (guests, xu, title): the title "Đám cưới đông vui" at 20 guests
ENVELOPES = (10, 20, 50, 100, 200)   # 🧧 a guest's red envelope for the couple (feedback #56), split half and half
# No cap on giving (owner 03/10: "bỏ giới hạn phong bì", "cho gửi thoải mái"): one of ENVELOPES each time, as many
# envelopes as the guest likes while the wallet holds them. A pure transfer: the couple gets exactly what the guest paid,
# and nothing else is paid per envelope.
ENVELOPE_MAX_OLD = 500          # the old per-wedding cap: only printed by older clients ("tối đa … xu mỗi đám"), not enforced
GIFT_XU = 500                   # 🎁 owner 03/10 "với đám cưới thì ad tặng thêm mỗi người 500 xu": once per save, ever (wed_gift)
GIFT_LABEL = '🎁 Quà từ admin: 500 xu đi đám cưới'
GIFT_VERSION = 1                # journey['wed_gift'] {v, got: the life day}
GIFT_DAY = 3                    # a save that has lived this many days at least (not a fresh second account)
WISHES = ('Trăm năm hạnh phúc 💕', 'Bách niên giai lão 🎎', 'Sớm có tin vui nha 👶', 'Đầu bạc răng long 👴👵',
          'Thương nhau dài dài nha 💞', 'Hạnh phúc ngập tràn 🥰')
ANNIVERSARIES = ((100, 200, 'w_100', '100'), (365, 500, 'w_1y', 'một năm'), (500, 800, 'w_500', '500'),
                 (1000, 1500, 'w_1000', '1000'))   # (days, xu for each spouse, title, "tròn … ngày cưới")
ANNIV_NPC = (40, 120)           # lì xì from the neighbours on an anniversary (deterministic per couple and milestone)
RACE = ((1, 300, 'w_vip'), (2, 150, 'w_pro'), (3, 150, 'w_pro'))
PHOTOS_MAX = 3                  # group photos kept per wedding
PHOTO_BYTES = 44 * 1024         # one photo (a canvas snapshot, webp or jpeg; base64 fits the 64 KB POST limit)
# ---- the party's fun (1.3.0, owner 02/10 after reading the guests' chat at the parties) ----
DISHES = ('Gà luộc', 'Xôi gấc', 'Nem rán', 'Canh măng', 'Bò xào', 'Lẩu thái', 'Tôm hấp', 'Chè đậu')   # the mâm cỗ (drawn by the client)
EAT_SPIRIT, EAT_MAX = 1, 3      # gắp một món: +1 tinh thần, at most 3 times a party (owner)
BEER_SPIRIT, BEER_MAX = -1, 2   # uống bia: −1 tinh thần, at most 2 times a party (owner); nước ngọt: nothing, just fun
TOSS_AT = 525                   # 💐 the MC calls the bouquet toss (party seconds); the couple gets the "Tung hoa" button
TOSS_WAIT = 60                  # ... and if neither presses it, the bouquet is thrown for them
TOSS_XU = 20                    # the guest who catches it (once a party)
# 🎧 the groom picks the music (owner 02/10: "cho chú rể chọn nhạc"; the bride when the groom is not in the room).
# Keys of public/js/v4/wedfeast.js TRACKS (the files public/music/wedding-<key>.mp3); 'auto' is the party's programme.
MUSIC = ('auto', 'house', 'disco', 'edm', 'remix', 'electro', 'latin', 'funk', 'love')
MUSIC_GAP = 20                  # seconds between two changes of one party's music

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


def party_wedding(db, couple: dict | None) -> dict | None:
    """The wedding a couple's live party belongs to: married (their done wedding) or engaged with a confirmed plan."""
    if not couple or couple.get('status') not in ('engaged', 'married'):
        return None
    w = db.execute("SELECT id, status, plan FROM weddings WHERE couple=? AND status IN ('confirmed','done') ORDER BY id DESC LIMIT 1",
                   (couple['id'],)).fetchone()
    if not w or (couple['status'] == 'engaged' and w['status'] != 'confirmed'):
        return None
    return dict(w)


def party_view(db, couple: dict | None, t: float | None = None) -> dict | None:
    """The Hôn nhân sheet's party card: None (no wedding yet) or {state, at, at_label, can_move, invited, guests}.
    state: 'none' (choose a date and time), 'booked', 'live' (the room is open), 'done'."""
    t = now() if t is None else t
    w = party_wedding(db, couple)
    if not w:
        return None
    r = db.execute("SELECT wedding, at, status, guests FROM wedding_parties WHERE couple=? AND status IN ('booked','done') ORDER BY wedding DESC LIMIT 1",
                   (couple['id'],)).fetchone()
    if not r:
        return dict(state='none', min_ahead=PARTY_BOOK_MIN, max_ahead=BOOK_MAX)
    at = float(r['at'])
    planned = 'at' in json.loads(w['plan'] or '{}') and int(r['wedding']) == int(w['id'])   # booked with the plan: its time is the ceremony's
    invited = bool(db.execute('SELECT 1 FROM news WHERE ref=?', (f'wedinv:{r["wedding"]}',)).fetchone())
    state = 'done' if r['status'] == 'done' or t >= at + PARTY_SECS else 'live' if t >= at - OPEN_BEFORE else 'booked'
    return dict(state=state, id=int(r['wedding']), at=int(at), at_label=fmt_at(at), end=int(at + PARTY_SECS),
                can_move=state == 'booked' and not planned and at - t >= PARTY_BOOK_MIN, invited=invited,
                guests=int(r['guests'] or 0), min_ahead=PARTY_BOOK_MIN, max_ahead=BOOK_MAX)


def book_party(db, couple: dict, sid: str, at, t: float | None = None) -> dict:
    """"Tổ chức tiệc cưới": any couple with a wedding picks (or moves) the date and time of their one live party, free.
    The time also becomes their wedding date (cards, anniversaries) unless a booked plan already set it. Inside the
    caller's transaction."""
    t = now() if t is None else t
    from .marriage import need as mneed
    w = party_wedding(db, couple)
    mneed(w, 'Hai bạn cần chốt kế hoạch cưới trước đã.', 'no_wedding', 409)
    mneed(type(at) in (int, float) and at == at, 'Giờ tổ chức không hợp lệ.', 'bad_plan')
    at = float(int(at) // 60 * 60)
    mneed(at >= t + PARTY_BOOK_MIN, f'Chọn giờ cách bây giờ ít nhất {PARTY_BOOK_MIN // 60} phút để mọi người kịp tới nhé.', 'bad_plan')
    mneed(at <= t + BOOK_MAX, 'Chọn ngày trong vòng 14 ngày tới nhé.', 'bad_plan')
    cur = db.execute("SELECT wedding, at, status FROM wedding_parties WHERE couple=? AND status IN ('booked','done') ORDER BY wedding DESC LIMIT 1",
                     (couple['id'],)).fetchone()
    if cur:
        mneed(cur['status'] == 'booked' and float(cur['at']) + PARTY_SECS > t, 'Tiệc cưới của hai bạn đã tổ chức rồi.', 'done', 409)
        v = party_view(db, couple, t)
        mneed(v and v['can_move'], 'Tiệc sắp bắt đầu rồi, không đổi giờ được nữa.', 'too_late', 409)
        db.execute("UPDATE wedding_parties SET at=?, reminded=NULL WHERE wedding=? AND status='booked'", (at, cur['wedding']))
        wid = int(cur['wedding'])
    else:
        db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) VALUES(?, ?, ?, ?, ?, 'booked', ?) "
                   "ON CONFLICT(wedding) DO UPDATE SET at=excluded.at, status='booked', reminded=NULL WHERE wedding_parties.status='cancelled'",
                   (w['id'], couple['id'], couple['a'], couple['b'], at, t))
        wid = int(w['id'])
    d = db.execute('SELECT source FROM wedding_dates WHERE couple=?', (couple['id'],)).fetchone()
    if not d:
        db.execute("INSERT INTO wedding_dates(couple, at, source, wedding, created) VALUES(?, ?, 'party', ?, ?) ON CONFLICT(couple) DO NOTHING",
                   (couple['id'], at, wid, t))
    elif d['source'] in ('legacy', 'party'):
        db.execute("UPDATE wedding_dates SET at=?, source='party', wedding=? WHERE couple=? AND source IN ('legacy','party')", (at, wid, couple['id']))
    return dict(id=wid, at=at)


def invite(db, couple: dict, names: dict, t: float | None = None) -> int:
    """"Mời khách" (free, once per party): the couple's friends get an inbox line and a web push, and the whole phố a
    news line. Returns how many friends were told; 0 when already invited."""
    t = now() if t is None else t
    from . import marriage as mr
    from . import push
    v = party_view(db, couple, t)
    mr.need(v and v['state'] in ('booked', 'live'), 'Chọn ngày giờ tổ chức tiệc trước đã.', 'no_party', 409)
    when = fmt_at(v['at'])
    if not mr._post_news(db, 'invite', f'wedinv:{v["id"]}', f'💌 {names["a"]} & {names["b"]} mời cả phố dự tiệc cưới lúc {when}! Vào Khu phố › Lịch cưới nha.',
                         couple['a'], couple['b']):
        return 0
    rows = db.execute('SELECT DISTINCT friend FROM friends WHERE sid IN (?, ?) AND friend NOT IN (?, ?) LIMIT 400',
                      (couple['a'], couple['b'], couple['a'], couple['b'])).fetchall()
    text = f'💌 {names["a"]} và {names["b"]} mời bạn dự tiệc cưới lúc {when}. Mở Khu phố › Lịch cưới để vào dự nhé!'
    for r in rows:
        mr.ensure_person_db(db, r['friend'])
        mr._notice(db, r['friend'], text)
        push.queue(db, r['friend'], 'wedding', f'{names["a"]} và {names["b"]} mời bạn dự tiệc cưới lúc {when[-5:]} ngày {when[:5]} 💍')
    return len(rows)


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


# ---------------------------------------------------------------- 🧧 the guests' red envelopes
def envelope(store, sid: str, display: str, d: dict) -> dict:
    """POST /api/marriage/envelope {wedding, amount, wish, rid}: a guest at an open party (recorded, with an account,
    not the couple) gives a red envelope of one of ENVELOPES from the wallet, as many times as they like (no cap); each
    spouse gets half as a live_effects row. The sender's debit is a marriage_effects row `wenv:<wedding>:<rid>` (the live
    service reads it back to tell the room; the couple's end card sums their `wedenv:` rows)."""
    from . import marriage as mr
    from . import db as dbm
    wid, amount, wish = d.get('wedding'), d.get('amount'), d.get('wish', 0)
    mr.need(type(wid) is int and wid >= 1, 'Đám cưới không hợp lệ.', 'bad_envelope')
    mr.need(type(amount) is int and amount in ENVELOPES, 'Chọn số tiền trong phong bì nhé.', 'bad_envelope')
    mr.need(type(wish) is int and 0 <= wish < len(WISHES), 'Chọn một lời chúc nhé.', 'bad_envelope')
    rid = mr._rid(d)[:24]
    eid = f'wenv:{wid}:{rid}'

    def check(db, t):
        p = db.execute('SELECT a, b, at, status FROM wedding_parties WHERE wedding=?', (wid,)).fetchone()
        mr.need(p and p['status'] == 'booked' and p['at'] - OPEN_BEFORE <= t < p['at'] + PARTY_SECS,
                'Tiệc cưới này không mở nữa.', 'not_open', 409)
        mr.need(sid not in (p['a'], p['b']), 'Phong bì là của khách mừng hai bạn đó 😄', 'own_wedding', 409)
        g = db.execute('SELECT ok FROM wedding_guests WHERE wedding=? AND sid=?', (wid, sid)).fetchone()
        mr.need(g and int(g['ok']), 'Vào dự tiệc rồi mới gửi phong bì được nhé.', 'not_guest', 409)
        return p
    with store.connect() as db:
        if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone():
            return dict(message='Phong bì này đã gửi rồi.', changed=False, quiet=True, rid=rid)
        p = check(db, now())
        names = dict(a=mr._display(db, p['a']), b=mr._display(db, p['b']))
    # BANK.PAY: a gift from the wallet, cash (like the spouse transfer)
    out = mr._effect(eid, sid, 'wallet', -amount, f'🧧 Phong bì mừng cưới {names["a"]} & {names["b"]}', dict(wedding=wid, wish=wish))

    def fn(s):
        # A resend of this very envelope (its answer was lost; the client sends the same rid again) that started before
        # the first one landed: nothing to pay twice and no "not enough" either, the row's insert below says "already sent".
        if out['id'] in mr._box(s)['applied']:
            return
        mr.need(int(s['journey']['wallet']) >= amount, f'Ví của bạn chưa đủ {amount} xu.', 'not_enough')
        mr._apply_effect(s, out)

    def ops(db):
        p = check(db, now())
        mr._insert_effects(db, [out], 'applied')
        for side in ('a', 'b'):
            grant(db, p[side], 'coins', amount // 2, f'wedenv:{wid}:{side}:{rid}', dict(src='env'))
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:   # the same rid twice (a double tap); anything else is an error the client shows
        with store.connect() as db:
            mr.need(db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone(), 'Chưa gửi được, thử lại nhé.', 'busy', 409)
        return dict(message='Phong bì này đã gửi rồi.', changed=False, quiet=True, rid=rid)
    return dict(message=f'Đã gửi phong bì {amount} xu mừng {names["a"]} & {names["b"]} 🧧', changed=True, quiet=True, rid=rid)


# ---------------------------------------------------------------- 🎁 the admin's gift for the weddings
def wed_gift(store, sid: str, display: str, d: dict) -> dict:
    """POST /api/marriage/wed_gift {}: GIFT_XU into the wallet, once per save ever, while a party is open (the newer
    client asks when the player walks into one and the save has not had it: journey.public wed_gift False; None while
    the save is younger than GIFT_DAY life days, against fresh second accounts made for the gift). Kept in
    journey['wed_gift'] {v, got} (optional, beside the other blocks: older servers accept a journey with more blocks);
    the wallet row is kind 'life' (every build knows it). An older server answers not_found: the client stays quiet."""
    from . import marriage as mr
    mr.need(not d, 'Dữ liệu không hợp lệ.', 'bad_gift')
    t = now()
    with store.connect() as db:
        on = db.execute("SELECT 1 FROM wedding_parties WHERE status='booked' AND at<=? AND at>? LIMIT 1",
                        (t + OPEN_BEFORE, t - PARTY_SECS)).fetchone()
    mr.need(on, 'Quà này dành cho lúc đi dự tiệc cưới nhé.', 'no_party', 409)

    def fn(s):
        from . import journey as jr
        j = s['journey']
        mr.need(j.get('story'), 'Quà vào ví chỉ có trong hành trình.', 'not_story')
        mr.need('wed_gift' not in j, 'Bạn đã nhận quà đi đám cưới rồi nha.', 'wed_gift_done', 409)
        mr.need(j['life_day'] >= GIFT_DAY, f'Sống ở phố đủ {GIFT_DAY} ngày rồi nhận quà nhé.', 'wed_gift_early', 409)
        j['wed_gift'] = dict(v=GIFT_VERSION, got=j['life_day'])
        jr._wallet(j, GIFT_XU, 'life', GIFT_LABEL)
    mr._mutate_retry(store, {sid: fn})
    return dict(message=f'{GIFT_LABEL} đã vào ví!', changed=True, quiet=True, gift=GIFT_XU)


def gift_public(j: dict):
    """journey.public wed_gift: True (had it), False (may ask for it at a party), None (not yet: a young save)."""
    return True if 'wed_gift' in j else (False if j['life_day'] >= GIFT_DAY else None)


def gift_validate(j: dict) -> None:
    """journey['wed_gift'] (optional): {v, got: the life day} once the gift is paid."""
    if 'wed_gift' not in j:
        return
    from .engine import need, integer
    g = j['wed_gift']
    need(isinstance(g, dict) and set(g) == {'v', 'got'} and g['v'] == GIFT_VERSION, 'Dữ liệu quà đám cưới không hợp lệ.', 'invalid_save')
    integer(g['got'], 1, 10**6)


def envelopes_of(db, couple_sid: str, wid: int, side: str) -> int:
    """The envelopes one spouse got at one party (their halves)."""
    return int(db.execute('SELECT COALESCE(SUM(amount), 0) FROM live_effects WHERE sid=? AND id LIKE ?',
                          (couple_sid, f'wedenv:{wid}:{side}:%')).fetchone()[0] or 0)


# ---------------------------------------------------------------- views
def race(db, week: str, limit: int = 20) -> list:
    """The week's guests: weddings attended for at least a minute of the party (counted guests only), most first;
    a tie goes to whoever reached that count first."""
    return [dict(r) for r in db.execute('SELECT sid, pid, COUNT(*) AS n, MAX(counted_at) AS last FROM wedding_guests WHERE week=? AND ok=1 AND steps>=? '
                                        'GROUP BY sid, pid ORDER BY n DESC, last ASC, sid LIMIT ?', (week, GUEST_MIN_MINUTES, limit))]


def race_view(store, sid: str | None) -> dict:
    """GET /api/wedding/race: "Khách mời của tuần" now, my place, and last week's winners."""
    t = now()
    week, last_week = vn_week(t), vn_week(week_start(t) - 3600)
    with store.connect() as db:
        rows = race(db, week)
        mine = None
        if sid and not any(r['sid'] == sid for r in rows):
            r = db.execute('SELECT COUNT(*) AS n FROM wedding_guests WHERE week=? AND ok=1 AND steps>=? AND sid=?', (week, GUEST_MIN_MINUTES, sid)).fetchone()
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


