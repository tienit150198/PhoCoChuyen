"""🏥 Phòng sinh & nhận nuôi: a new child of a married couple now costs money (owner 21/10: "sinh con ok rồi, và phải
mất tiền ra, đặt tiền tối thiểu và không được ít hơn mức đó. Thay luồng nhận con như hiện tại luôn").

The shared child itself is unchanged (game/family.py: family_children, its care, custody copies, the home room's
👶 in game/cradle.py). This file replaces how a NEW one arrives:

* 🏥 Sinh con: the couple books a phòng sinh, either the NPC ``Nhà hộ sinh Phố Mây`` at a fixed NPC_PRICE (the
  fallback: nobody is ever blocked by the player market), or a birth room a player offers (a homestay owner,
  `careers.homestay.scale.tier` ≥ 1) at the price the provider sets, never below FLOOR. The stay lasts STAY_HOURS
  real hours from check-in; then the baby is born (family_children, origin 'birth', born today).
* 📄 Nhận nuôi: the paperwork at ``Trung tâm bảo trợ Phố Mây``, ADOPT_FEE (the minimum the owner set); the baby comes
  home as soon as both agree. The personal child of journey.household (game/household.py jr_hh_adopt) pays the same
  fee (`take`).
* 🩺 Điều dưỡng (optional): while a booked or ongoing stay asks for one, a player who has started the nurse career
  may join it (first one wins). The baby then starts healthier (NURSE_PERK: no bụng / sạch sẽ / vui vẻ 85 instead of
  65, gắn bó 10): never xu, nothing is printed.

Agreement (one clear rule): one spouse proposes (the place, the price seen, the name, WHO PAYS: "tôi" or "người ấy");
nothing is charged until the other spouse accepts. On acceptance the payer pays the whole price, wallet first then the
bank account, never the credit card, never into debt, never the joint fund (Sổ ví rows of at most ROW_MAX). Either
spouse can check in, cancel a booking before check-in (a full refund to the payer, to where it came from) or
greet the baby when the stay is over. Once checked in there is no cancelling.

Money: the NPC hospital and the adoption fee are pure sinks. A player room's price is held by the booking (escrow:
it left the payer's save, it is in no save) and released when the baby is born: BURN_PCT (5 %, the marketplace's rule)
is burned and the rest is credited to the provider through a pending marriage_effects 'wallet' row (applied by
game/marriage.py settle on the provider's next load, like every cross-save payment of the couple tables; a provider
whose save is gone: the whole price is burned). A cancelled booking refunds in full, nothing burned.

Exactly once: every write locks the birth_stays row (FOR UPDATE) and moves its status forward once; the baby is a
family_children row (PRIMARY KEY couple, INSERT … ON CONFLICT DO NOTHING). Two spouses tapping "Đón bé" together, a
tap racing the sheet's poll (`settle_due`): one birth, one credit; the second sees the baby.

Old flow (documented, never altered): children already born, custody copies and an old free request that was pending
at the deploy keep working exactly as before (family_answer still accepts it free, born after BIRTH_WAIT_DAYS). A
NEW family_child_request (an old client) is refused with a reload hint. A child born here carries an optional
`birth` block {where, nurse, at} in its JSON; 2.4.66 ignores it and keeps it on every write.

Tables (game/pg_schema.py, SCHEMA_VERSION 65): birth_rooms (one per provider save), birth_stays (one row per
booking or adoption: proposed → booked → staying → born, or declined / cancelled / refunded; at most one of
proposed/booked/staying per couple). No save key. 2.4.66 never reads them.

🛎️ Phố dịch vụ (game/service_market.py, SCHEMA 63) LISTS the player birth rooms: `install()` registers
('homestay' | 'hotel', 'phong_sinh') as an own-flow listing (spec `open`): the directory card shows the room, its
price and rating, and opens Nhà & Gia đình › 👶 Đón con chung with that room preselected. The booking, the
agreement, the payment, the escrow (birth_stays) and the payout (`_release`) stay here: the market refuses to order,
negotiate or set up this service itself, so there is one payment path. The provider sets the room (name, price ≥
FLOOR, open) here (family_room_set); the market's ×N settings do not apply. A room is listed under its
birth_rooms.career (only CAREERS may open one today: 'hotel' is registered, its listing stays empty until hotel
players may open rooms).
"""
from __future__ import annotations

import datetime
import json
import re

from . import marriage as mr

FLOOR = 500_000                # a player birth room never costs less (owner 21/10)
ROOM_MAX = 5_000_000           # and never more: 95 % of it fits one Sổ ví row, a booking is not a money pipe
NPC_PRICE = 800_000            # 🏥 Nhà hộ sinh Phố Mây, fixed
ADOPT_FEE = 300_000            # 📄 Trung tâm bảo trợ Phố Mây, the paperwork (the owner's minimum)
STAY_HOURS = 3                 # real hours in the room before the baby is born
BURN_PCT = 5                   # of a player room's price, burned at the birth (the marketplace's rule)
ROOM_CAP = 2                   # stays at once in one player's room (a booked couple waits to check in)
NURSE_ACTIVE_MAX = 3           # stays one nurse helps at once
ROW_MAX = 10_000_000           # one Sổ ví row (journey.validate's bound)
KIND = mr.KIND                 # 'life' in the wallet history
NPC = dict(name='Nhà hộ sinh Phố Mây', emoji='🏥', price=NPC_PRICE, hours=STAY_HOURS,
           desc='Phòng sinh sạch sẽ, bác sĩ trực cả ngày. Giá cố định, luôn còn chỗ.')
AGENCY = dict(name='Trung tâm bảo trợ Phố Mây', emoji='📄', fee=ADOPT_FEE,
              desc='Làm giấy tờ nhận nuôi, gặp bé và đón bé về ngay khi cả hai đồng ý.')
CAREERS = ('homestay',)        # who may offer a room here (own table); the marketplace may add 'hotel'
SERVICE = 'phong_sinh'
NURSE = 'nurse'
NURSE_PERK = dict(food=85, clean=85, joy=85, bond=10)
BASE = dict(food=65, clean=65, joy=65, bond=0)
ACTIVE = ('proposed', 'booked', 'staying')
OPS = ('family_birth_book', 'family_birth_answer', 'family_birth_cancel', 'family_birth_checkin',
       'family_birth_done', 'family_birth_rate', 'family_birth_nurse', 'family_room_set')
SOLO = frozenset(('family_birth_nurse', 'family_room_set'))   # a nurse or a provider: no couple needed
COUPLE = frozenset(OPS) - SOLO
VN = datetime.timezone(datetime.timedelta(hours=7))


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _need(ok, message, code='bad_birth', status=400):
    mr.need(ok, message, code, status)


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _today() -> str:
    return datetime.datetime.fromtimestamp(mr.now(), VN).date().isoformat()


# ---------------------------------------------------------------- the marketplace seam
def market():
    """game/service_market.py when it is installed (another branch), else None."""
    try:
        from . import service_market as sm   # noqa: PLC0415
    except ImportError:
        return None
    return sm


def _market_row(r: dict, busy: int = 0) -> dict:
    """A birth room as Phố dịch vụ lists it (service_market own-flow row)."""
    return dict(sid=r['sid'], price=int(r['price']), on=bool(r['open']), stars=int(r['stars']), rated=int(r['rated']), deals=int(r['born']),
                at=float(r['at'] or 0), title=str(r['name'])[:40], data=dict(room=int(r['id'])),
                why='' if r['open'] else 'Phòng sinh đang tạm đóng: mở lại ở Nhà & Gia đình.')


def _providers(career: str):
    def rows(db, limit, offset):
        return [_market_row(r) for r in mr._rows(db, 'SELECT id,sid,name,price,open,stars,rated,born,at FROM birth_rooms WHERE career=? AND open '
                                                     'ORDER BY price,id LIMIT ? OFFSET ?', (career, int(limit), int(offset)))]
    return rows


def _offer(career: str):
    def row(db, sid):
        r = mr._row(db, 'SELECT id,sid,name,price,open,stars,rated,born,at FROM birth_rooms WHERE sid=? AND career=?', (sid, career))
        return _market_row(r) if r else None
    return row


def _can_provide(career: str):
    def why(state):
        return '' if provider_career(state) == career else 'Cần sở hữu homestay (quy mô nghề Homestay từ cấp 1) để mở phòng sinh.'
    return why


def market_spec(career: str) -> dict:
    """('homestay' | 'hotel', 'phong_sinh') for service_market.register: an own-flow listing (keys the registry accepts)."""
    return dict(name='Phòng sinh', icon='🏥', unit='ca sinh', base=NPC_PRICE, floor=FLOOR, max_price=ROOM_MAX, duration=STAY_HOURS * 60,
                desc=f'Phòng cho một ca sinh {STAY_HOURS} giờ của vợ chồng. Giá không dưới {_fmt(FLOOR)} xu.',
                requires=dict(married=True), can_provide=_can_provide(career),
                open=dict(action='marriage', data=dict(tab='family', section='children'), label='👶 Đặt phòng sinh'),
                setup=dict(action='marriage', data=dict(tab='family', section='room'), label='🏡 Phòng sinh của bạn'),
                providers=_providers(career), offer=_offer(career))


def install(strict: bool = False) -> bool:
    """Register the birth rooms in Phố dịch vụ (idempotent; at import and from service_market's seed). A refusal is
    logged, never raised at runtime (the family sheet works without the listing); strict=True (tests) raises it."""
    sm = market()
    if sm is None or not callable(getattr(sm, 'register', None)):
        return False
    try:
        for career in ('homestay', 'hotel'):
            sm.register(career, SERVICE, market_spec(career))
    except Exception:
        if strict:
            raise
        import logging
        logging.getLogger(__name__).exception('🏥 birth rooms: Phố dịch vụ refused the listing')
        return False
    return True


install()


# ---------------------------------------------------------------- money: wallet first, then the account
def have(s: dict) -> int:
    """What a payment here may use: the cash (none while in debt) and the current account. Never the card."""
    from . import bank
    j = s['journey']
    b = bank.get(s)
    return max(0, int(j['wallet'])) + max(0, int(b['balance']) if b else 0)


def take(s: dict, amount: int, label: str, need=None) -> dict:
    """Charge `amount` (wallet then account, rows of at most ROW_MAX). Returns {cash, acc, text}; raises through
    `need` (engine.need inside a journey command, the marriage one here) when it is not there."""
    from . import bank, journey as jr
    need = need or (lambda ok, m, code='not_enough': _need(ok, m, code))
    j = s['journey']
    if j['wallet'] < 0:
        need(False, f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ trước nhé.', 'not_enough')
    short = amount - have(s)
    need(short <= 0, f'Còn thiếu {_fmt(max(0, short))} xu (cần {_fmt(amount)} xu tiền mặt hoặc trong tài khoản; '
                     'không trả bằng thẻ tín dụng).', 'not_enough')
    cash = min(max(0, j['wallet']), amount)
    left = cash
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, -part, KIND, label[:120])
        left -= part
    acc = amount - cash
    if acc:
        b = bank.get(s)
        b['balance'] -= acc
        bank._log(b, j['life_day'], 'acc', label[:120], -acc)
        b.pop('ting', None)
    text = (f'{_fmt(cash)} xu tiền mặt và {_fmt(acc)} xu từ tài khoản' if cash and acc else
            f'{_fmt(acc)} xu từ tài khoản' if acc else f'{_fmt(cash)} xu tiền mặt')
    return dict(cash=cash, acc=acc, text=text)


def _give(s: dict, cash: int, acc: int, label: str) -> None:
    """A refund to where the money came from (the account part back to the account; no account any more: cash)."""
    from . import bank, journey as jr
    j = s['journey']
    b = bank.get(s)
    if acc and b is None:
        cash, acc = cash + acc, 0
    left = cash
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, part, KIND, label[:120])
        left -= part
    if acc:
        b['balance'] += acc
        bank._log(b, j['life_day'], 'acc', label[:120], acc)


def _effect_wallet(db, eid: str, sid: str, amount: int, label: str) -> bool:
    """A credit to a save that is not locked here (a provider, a payer after a split): a pending marriage effect,
    applied on that save's next load. Rows of at most ROW_MAX. False when the save is gone (nothing is written)."""
    if amount <= 0 or not db.execute('SELECT 1 FROM sessions WHERE sid=?', (sid,)).fetchone():
        return False
    effects, left, n = [], int(amount), 0
    while left > 0:
        part = min(left, ROW_MAX)
        effects.append(mr._effect(f'{eid}:{n}' if n else eid, sid, 'wallet', part, label))
        left -= part
        n += 1
    fresh = [e for e in effects if not db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (e['id'],)).fetchone()]
    mr._insert_effects(db, fresh, 'pending')
    return True


# ---------------------------------------------------------------- who can do what
def ready(state: dict) -> bool:
    j = (state or {}).get('journey') or {}
    return bool(j.get('story')) and int(j.get('life_day') or 0) >= 10


def provider_career(state: dict) -> str | None:
    """The career through which this save may offer a birth room: a homestay it owns (scale tier ≥ 1)."""
    careers = (state or {}).get('careers') or {}
    for cid in CAREERS:
        c = careers.get(cid)
        tier = ((c or {}).get('scale') or {}).get('tier') if isinstance(c, dict) else None
        if isinstance(c, dict) and c.get('started') is True and type(tier) is int and tier >= 1:
            return cid
    return None


def is_nurse(state: dict) -> bool:
    c = ((state or {}).get('careers') or {}).get(NURSE)
    return isinstance(c, dict) and c.get('started') is True


def _room_name(value) -> str:
    _need(isinstance(value, str) and 2 <= len(value.strip()) <= 30 and not any(ord(ch) < 32 or ch in '<>&"`' for ch in value),
          'Tên phòng cần 2 đến 30 ký tự, không dùng ký tự đặc biệt.')
    from .accounts import offensive_name
    name = ' '.join(value.split())
    _need(not offensive_name(name), 'Chọn một cái tên phòng thân thiện hơn nhé.', 'bad_name')
    return name


def _baby_name(value) -> str:
    from . import household as hh
    from .engine import GameError
    try:
        return hh._name(value)
    except GameError as e:
        raise mr.MarriageError(e.message, e.code, 400) from None


# ---------------------------------------------------------------- the provider side (own table; the seam)
def rooms(db, viewer: set | None = None) -> list:
    """The open player birth rooms as the couple chooses among them: [{id, name, owner, price, stars, rated, born,
    busy, full}], cheapest first. `viewer`: the couple's sids (their own rooms are left out)."""
    rows = mr._rows(db, 'SELECT r.id,r.sid,r.name,r.price,r.stars,r.rated,r.born,a.display FROM birth_rooms r '
                        'LEFT JOIN accounts a ON a.sid=r.sid WHERE r.open ORDER BY r.price,r.id LIMIT 30')
    rows = [r for r in rows if not viewer or r['sid'] not in viewer]
    busy = {}
    if rows:
        marks = ','.join('?' * len(rows))
        for r in db.execute(f"SELECT room,COUNT(*) AS n FROM birth_stays WHERE status='staying' AND room IN ({marks}) GROUP BY room",
                            tuple(int(r['id']) for r in rows)).fetchall():
            busy[int(r['room'])] = int(r['n'])
    return [dict(id=int(r['id']), name=r['name'], owner=mr._clean_name(r['display'] or 'Chủ homestay'), price=int(r['price']),
                 stars=round(int(r['stars']) / int(r['rated']), 1) if int(r['rated']) else None, rated=int(r['rated']),
                 born=int(r['born']), busy=busy.get(int(r['id']), 0), full=busy.get(int(r['id']), 0) >= ROOM_CAP)
            for r in rows[:20]]


def _release(db, stay: dict) -> int:
    """The escrow of a player room once the baby is born: BURN_PCT burned, the rest to the provider. Returns the burn."""
    price = int(stay['price'])
    if stay['provider'] != 'room' or not stay['provider_sid']:
        return price                                  # NPC: all of it is a sink
    burn = -(-price * BURN_PCT // 100)
    paid = _effect_wallet(db, f'birth:{stay["id"]}:p', stay['provider_sid'], price - burn,
                          f'🏥 Phòng sinh: một bé chào đời ({stay["name"]})')
    if paid:
        db.execute('UPDATE birth_rooms SET born=born+1 WHERE id=?', (stay['room'],))
        mr._notice(db, stay['provider_sid'], f'🏥 Một bé đã chào đời ở phòng sinh của bạn. +{_fmt(price - burn)} xu (đã trừ {BURN_PCT}% phí).')
        return burn
    return price


# ---------------------------------------------------------------- the view
def _stay_public(db, r: dict, sid: str, t: float) -> dict:
    data = json.loads(r['data'] or '{}')
    mine = r['from_sid'] == sid
    left = max(0, int((r['ends'] or 0) - t)) if r['status'] == 'staying' else None
    nurse = mr._display(db, r['nurse']) if r['nurse'] else ''
    return dict(id=int(r['id']), kind=r['kind'], status=r['status'], name=r['name'], where=data.get('where', ''),
                emoji=data.get('emoji', '🏥'), price=int(r['price']), payer='me' if r['payer'] == sid else 'partner',
                mine=mine, nurse=nurse, nurse_ok=bool(r['nurse_ok']), starts=r['starts'], ends=r['ends'], left=left,
                due=r['status'] == 'staying' and left == 0, hours=STAY_HOURS,
                paid=data.get('text', ''), can_cancel=(r['status'] == 'proposed' and mine) or r['status'] == 'booked',
                can_answer=r['status'] == 'proposed' and not mine, can_checkin=r['status'] == 'booked')


def public(db, sid: str, c: dict | None, state: dict) -> dict:
    """family.view()['birth']: prices, the rooms, the couple's booking, the last birth to rate, and the provider's and
    the nurse's cards. Read only."""
    t = mr.now()
    out = dict(npc=dict(NPC), agency=dict(AGENCY), floor=FLOOR, max=ROOM_MAX, hours=STAY_HOURS, burn_pct=BURN_PCT,
               nurse_perk=dict(NURSE_PERK), rooms=[], stay=None, rate=None, my_room=None, nurse=None, now=t)
    married = bool(c and c['status'] == 'married')
    if married:
        r = mr._row(db, "SELECT * FROM birth_stays WHERE couple=? AND status IN ('proposed','booked','staying') ORDER BY id DESC LIMIT 1",
                    (c['id'],))
        if r:
            out['stay'] = _stay_public(db, r, sid, t)
        elif not db.execute('SELECT 1 FROM family_children WHERE couple=?', (c['id'],)).fetchone():
            out['rooms'] = rooms(db, {c['a'], c['b']})   # only while they are choosing (the sheet polls every 15 s)
        last = mr._row(db, "SELECT id,name,room,rating,done,data FROM birth_stays WHERE couple=? AND status='born' AND provider='room' "
                           'AND rating IS NULL AND done>? ORDER BY id DESC LIMIT 1', (c['id'], t - 7 * 86400))
        if last:
            out['rate'] = dict(id=int(last['id']), name=last['name'], where=json.loads(last['data'] or '{}').get('where', ''))
    career = provider_career(state)
    mine = mr._row(db, 'SELECT * FROM birth_rooms WHERE sid=?', (sid,))
    if career or mine:
        out['my_room'] = dict(can=bool(career), career=career or (mine or {}).get('career'),
                              room=dict(name=mine['name'], price=int(mine['price']), open=bool(mine['open']),
                                        stars=round(int(mine['stars']) / int(mine['rated']), 1) if int(mine['rated']) else None,
                                        rated=int(mine['rated']), born=int(mine['born'])) if mine else None,
                              staying=int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE room=? AND status='staying'",
                                                     (int(mine['id']),)).fetchone()[0]) if mine else 0,
                              booked=int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE room=? AND status='booked'",
                                                    (int(mine['id']),)).fetchone()[0]) if mine else 0)
    if is_nurse(state):
        own = (c['id'],) if married else (-1,)
        calls = mr._rows(db, "SELECT id,name,status,ends,data,couple FROM birth_stays WHERE status IN ('booked','staying') AND kind='birth' "
                             'AND nurse_ok AND nurse IS NULL AND couple<>? ORDER BY id DESC LIMIT 8', own)
        helping = mr._rows(db, "SELECT id,name,status,ends,data FROM birth_stays WHERE nurse=? AND status IN ('booked','staying') ORDER BY id",
                           (sid,))
        done = int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE nurse=? AND status='born'", (sid,)).fetchone()[0])
        row = lambda x: dict(id=int(x['id']), name=x['name'], status=x['status'], where=json.loads(x['data'] or '{}').get('where', ''),
                             left=max(0, int((x['ends'] or 0) - t)) if x['status'] == 'staying' else None)
        out['nurse'] = dict(calls=[row(x) for x in calls], helping=[row(x) for x in helping], done=done,
                            full=len(helping) >= NURSE_ACTIVE_MAX)
    return out


def alerts(db, sid: str) -> int:
    """A booking waiting for this spouse's answer (the rail's dot)."""
    return int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE to_sid=? AND status='proposed'", (sid,)).fetchone()[0])


# ---------------------------------------------------------------- the birth itself (exactly once)
def _child(name: str, origin: str, where: str, nurse: str, t: float) -> dict:
    x = NURSE_PERK if nurse else BASE
    return dict(name=name, origin=origin, born=_today(), day='', did=[], care_days=0, bond=x['bond'],
                food=x['food'], clean=x['clean'], joy=x['joy'], outfit='basic', owned=['basic'],
                birth=dict(where=where[:60], nurse=nurse[:24], at=int(t)))


def _finish(db, stay_id: int, t: float) -> str | None:
    """Under the row lock: a stay whose time is up becomes a baby (once). Returns a message, None when not due."""
    r = mr._row(db, 'SELECT * FROM birth_stays WHERE id=? FOR UPDATE', (stay_id,))
    if not r or r['status'] != 'staying' or float(r['ends'] or 0) > t:
        return None
    data = json.loads(r['data'] or '{}')
    c = mr._row(db, 'SELECT * FROM couples WHERE id=?', (r['couple'],))
    nurse = mr._display(db, r['nurse']) if r['nurse'] else ''
    born = c and c['status'] == 'married' and db.execute(
        'INSERT INTO family_children(couple,state) VALUES(?,?) ON CONFLICT DO NOTHING',
        (r['couple'], _json(_child(r['name'], 'birth', data.get('where', NPC['name']), nurse, t)))).rowcount == 1
    if not born:
        # a child came another way meanwhile (an old free request accepted during a rollback), or they parted: refund
        _effect_wallet(db, f'birth:{r["id"]}:r', r['payer'], int(r['price']), f'Hoàn tiền phòng sinh ({r["name"]})')
        db.execute("UPDATE birth_stays SET status='refunded',done=? WHERE id=?", (t, r['id']))
        return 'Gia đình đã có con chung, tiền phòng sinh được hoàn lại.'
    burn = _release(db, r)
    db.execute("UPDATE birth_stays SET status='born',done=?,burn=? WHERE id=?", (t, burn, r['id']))
    for who in (r['from_sid'], r['to_sid']):
        mr._notice(db, who, f'👶 {r["name"]} đã chào đời! Mở Nhà & Gia đình để bế bé nhé.')
    if r['nurse']:
        mr._notice(db, r['nurse'], f'🩺 Ca sinh bạn hỗ trợ đã mẹ tròn con vuông: bé {r["name"]} khỏe mạnh. Cảm ơn bạn!')
    return f'👶 {r["name"]} đã chào đời' + (f', có điều dưỡng {nurse} hỗ trợ: bé khỏe mạnh, vui vẻ.' if nurse else '.')


def settle_due(store, sid: str) -> bool:
    """GET /api/marriage and the home room: a stay of this player's couple whose hours are over becomes the baby
    (cheap: one indexed query when nothing is due). True when a baby was born now."""
    t = mr.now()
    with store.connect() as db:
        r = db.execute("SELECT s.id FROM marriage_bonds b JOIN birth_stays s ON s.couple=b.couple "
                       "WHERE b.sid=? AND s.status='staying' AND s.ends<=? LIMIT 1", (sid, t)).fetchone()
    if not r:
        return False
    return bool(store.transaction(lambda db: _finish(db, int(r['id']), t)))


# ---------------------------------------------------------------- the commands (inside family.act's transaction)
def _stay(db, c, p) -> dict:
    ident = p.get('id')
    _need(type(ident) is int, 'Chọn lượt đặt phòng hợp lệ.')
    r = mr._row(db, 'SELECT * FROM birth_stays WHERE id=? AND couple=? FOR UPDATE', (ident, c['id']))
    _need(r, 'Không tìm thấy lượt đặt phòng này.', 'not_found', 404)
    return r


def _no_child(db, c) -> None:
    _need(not db.execute('SELECT 1 FROM family_children WHERE couple=?', (c['id'],)).fetchone(), 'Hai bạn đã có con chung.', 'already_owned', 409)


def apply(db, sid: str, c: dict | None, states: dict, op: str, p: dict, rid: str, changed: set) -> str:
    t = mr.now()
    state = states[sid]
    if op == 'family_room_set':
        return _room_set(db, sid, state, p, t)
    if op == 'family_birth_nurse':
        return _nurse(db, sid, c, state, p)
    other = mr._other(c, sid)
    if op == 'family_birth_book':
        return _book(db, sid, other, c, states, p, t)
    r = _stay(db, c, p)
    if op == 'family_birth_answer':
        return _answer(db, sid, c, states, r, p, t, changed)
    if op == 'family_birth_cancel':
        _need(r['status'] in ('proposed', 'booked'), 'Đã nhận phòng thì không hủy được nữa. Bé sắp chào đời rồi!'
              if r['status'] == 'staying' else 'Lượt đặt phòng này đã xong hoặc đã hủy.', 'stale', 409)
        if r['status'] == 'proposed':
            _need(r['from_sid'] == sid, 'Người được mời bấm Từ chối nhé.', 'forbidden', 403)
            db.execute("UPDATE birth_stays SET status='cancelled',done=? WHERE id=?", (t, r['id']))
            mr._notice(db, other, '🏥 Người ấy đã hủy lời mời ' + ('đặt phòng sinh.' if r['kind'] == 'birth' else 'nhận nuôi.'))
            return 'Đã hủy lời mời. Chưa có khoản nào bị trừ.'
        data = json.loads(r['data'] or '{}')
        _give(states[r['payer']], int(data.get('cash', 0)), int(data.get('acc', 0)), f'Hoàn tiền phòng sinh · {data.get("where", "")}')
        changed.add(r['payer'])
        db.execute("UPDATE birth_stays SET status='cancelled',done=? WHERE id=?", (t, r['id']))
        mr._notice(db, other, f'🏥 Đã hủy đặt phòng sinh. {_fmt(r["price"])} xu được hoàn đủ cho người trả.')
        return f'Đã hủy đặt phòng. Hoàn đủ {_fmt(r["price"])} xu cho ' + ('bạn.' if r['payer'] == sid else 'người ấy.')
    if op == 'family_birth_checkin':
        _need(r['status'] == 'booked', 'Lượt này chưa đặt xong hoặc đã nhận phòng rồi.', 'stale', 409)
        _no_child(db, c)
        if r['provider'] == 'room':
            room = mr._row(db, 'SELECT id FROM birth_rooms WHERE id=?', (r['room'],))
            if not room:   # the provider closed their account: never stuck, a full refund
                data = json.loads(r['data'] or '{}')
                _give(states[r['payer']], int(data.get('cash', 0)), int(data.get('acc', 0)), 'Hoàn tiền phòng sinh (phòng đã đóng)')
                changed.add(r['payer'])
                db.execute("UPDATE birth_stays SET status='refunded',done=? WHERE id=?", (t, r['id']))
                return f'Phòng này không còn nữa. Đã hoàn đủ {_fmt(r["price"])} xu; chọn phòng khác hoặc {NPC["name"]} nhé.'
            busy = int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE room=? AND status='staying'", (r['room'],)).fetchone()[0])
            _need(busy < ROOM_CAP, f'Phòng đang có {busy} ca sinh. Chờ một lúc rồi nhận phòng, hoặc hủy để hoàn tiền nhé.', 'room_full', 409)
        db.execute("UPDATE birth_stays SET status='staying',starts=?,ends=? WHERE id=?", (t, t + STAY_HOURS * 3600, r['id']))
        mr._notice(db, other, f'🏥 Hai bạn đã nhận phòng sinh. Bé {r["name"]} chào đời sau {STAY_HOURS} giờ.')
        return f'Đã nhận phòng. {STAY_HOURS} giờ nữa bé {r["name"]} chào đời.'
    if op == 'family_birth_done':
        if r['status'] == 'born':
            return f'👶 {r["name"]} đã chào đời rồi.'
        _need(r['status'] == 'staying', 'Chưa nhận phòng sinh.', 'stale', 409)
        left = int(float(r['ends']) - t)
        _need(left <= 0, f'Còn {left // 3600} giờ {left % 3600 // 60} phút nữa bé mới chào đời.', 'waiting', 409)
        return _finish(db, int(r['id']), t) or 'Bé đã chào đời.'
    # family_birth_rate
    stars = p.get('stars')
    _need(type(stars) is int and 1 <= stars <= 5, 'Chọn từ 1 đến 5 sao.')
    _need(r['status'] == 'born' and r['provider'] == 'room', 'Chỉ chấm phòng sinh của người chơi sau khi bé chào đời.', 'stale', 409)
    _need(r['rating'] is None, 'Hai bạn đã chấm phòng này rồi.', 'already_done', 409)
    db.execute('UPDATE birth_stays SET rating=? WHERE id=?', (stars, r['id']))
    db.execute('UPDATE birth_rooms SET stars=stars+?,rated=rated+1 WHERE id=?', (stars, r['room']))
    return f'Cảm ơn bạn đã chấm {stars} sao.'


def _book(db, sid, other, c, states, p, t) -> str:
    kind = p.get('kind')
    _need(kind in ('birth', 'adopt'), 'Chọn sinh con hoặc nhận nuôi.')
    _need(all(ready(s) for s in states.values()), 'Cả hai mở hành trình đến ngày sống 10 trước nhé.', 'locked')
    _no_child(db, c)
    _need(not db.execute("SELECT 1 FROM family_requests WHERE couple=? AND kind='child' AND status='pending'", (c['id'],)).fetchone(),
          'Còn một lời mời đón con kiểu cũ đang chờ. Trả lời hoặc hủy nó trước nhé.', 'pending', 409)
    _need(not db.execute("SELECT 1 FROM birth_stays WHERE couple=? AND status IN ('proposed','booked','staying')", (c['id'],)).fetchone(),
          'Hai bạn đang có một lượt đặt phòng hoặc nhận nuôi. Xem ở thẻ phía trên nhé.', 'pending', 409)
    name = _baby_name(p.get('name'))
    payer = p.get('payer', 'me')
    _need(payer in ('me', 'partner'), 'Chọn ai trả tiền.')
    payer_sid = sid if payer == 'me' else other
    price, seen = None, p.get('price')
    room, provider_sid, provider = None, None, 'npc'
    if kind == 'adopt':
        price, where, emoji = ADOPT_FEE, AGENCY['name'], AGENCY['emoji']
        _need(p.get('where', 'agency') == 'agency', 'Nhận nuôi làm giấy tờ ở Trung tâm bảo trợ.')
    elif p.get('where') == 'npc':
        price, where, emoji = NPC_PRICE, NPC['name'], NPC['emoji']
    else:
        ident = p.get('where')
        _need(type(ident) is int, 'Chọn nơi sinh hợp lệ.')
        r = mr._row(db, 'SELECT r.*,a.display FROM birth_rooms r LEFT JOIN accounts a ON a.sid=r.sid WHERE r.id=?', (ident,))
        _need(r and r['open'], 'Phòng này đang đóng. Chọn phòng khác nhé.', 'stale_room', 409)
        _need(r['sid'] not in (sid, other), 'Không đặt phòng sinh của chính gia đình mình.', 'own_room')
        price, provider, room, provider_sid = int(r['price']), 'room', int(r['id']), r['sid']
        where, emoji = f'{r["name"]} ({mr._clean_name(r["display"] or "Chủ homestay")})', '🏡'
        _need(FLOOR <= price <= ROOM_MAX, 'Giá phòng không hợp lệ.', 'stale_room', 409)
    _need(type(seen) is int and seen == price, f'Giá đã đổi thành {_fmt(price)} xu. Xem lại rồi đặt nhé.', 'price_changed', 409)
    if payer_sid == sid:
        _need(have(states[sid]) >= price and states[sid]['journey']['wallet'] >= 0,
              f'Bạn cần {_fmt(price)} xu (tiền mặt + tài khoản). Còn thiếu {_fmt(max(0, price - have(states[sid])))} xu.', 'not_enough')
    nurse_ok = p.get('nurse', True)
    _need(type(nurse_ok) is bool, 'Chọn có mời điều dưỡng hay không.')
    data = dict(where=where, emoji=emoji)
    db.execute('INSERT INTO birth_stays(couple,kind,status,from_sid,to_sid,payer,name,provider,room,provider_sid,price,nurse_ok,data,at) '
               "VALUES(?,?,'proposed',?,?,?,?,?,?,?,?,?,?,?)",
               (c['id'], kind, sid, other, payer_sid, name, provider, room, provider_sid, price, bool(nurse_ok and kind == 'birth'),
                _json(data), t))
    what = f'đặt {where} ({_fmt(price)} xu) để sinh bé {name}' if kind == 'birth' else f'nhận nuôi bé {name} ({_fmt(price)} xu phí giấy tờ)'
    mr._notice(db, other, f'🏥 Người ấy mời bạn {what}. Mở Nhà & Gia đình để đồng ý nhé.')
    return 'Đã gửi lời mời. Chưa trừ tiền: chỉ trừ khi người ấy đồng ý.'


def _answer(db, sid, c, states, r, p, t, changed) -> str:
    _need(r['status'] == 'proposed', 'Lời mời đã được trả lời hoặc hủy.', 'stale', 409)
    _need(r['to_sid'] == sid, 'Chỉ người được mời mới trả lời.', 'forbidden', 403)
    answer = p.get('answer')
    _need(answer in ('accept', 'decline'), 'Chọn đồng ý hoặc từ chối.')
    if answer == 'decline':
        db.execute("UPDATE birth_stays SET status='declined',done=? WHERE id=?", (t, r['id']))
        mr._notice(db, r['from_sid'], '🏥 Người ấy chưa đồng ý lời mời. Không ai bị trừ tiền.')
        return 'Đã từ chối. Không ai bị trừ tiền.'
    _need(all(ready(s) for s in states.values()), 'Cả hai cần hành trình từ ngày sống 10.', 'locked')
    _no_child(db, c)
    data = json.loads(r['data'] or '{}')
    if r['provider'] == 'room':   # the room must still be offered at the price both saw
        room = mr._row(db, 'SELECT open,price FROM birth_rooms WHERE id=?', (r['room'],))
        if not room or not room['open'] or int(room['price']) != int(r['price']):
            db.execute("UPDATE birth_stays SET status='cancelled',done=? WHERE id=?", (t, r['id']))
            mr._notice(db, r['from_sid'], '🏥 Phòng sinh đã đổi giá hoặc đóng, lời mời được hủy. Chưa ai bị trừ tiền.')
            return 'Phòng đã đổi giá hoặc đóng nên lời mời được hủy. Chưa ai bị trừ tiền; đặt lại nhé.'
    payer = states[r['payer']]
    label = (f'🏥 Phòng sinh · {data.get("where", "")}' if r['kind'] == 'birth' else f'📄 Phí nhận nuôi · {AGENCY["name"]}')
    paid = take(payer, int(r['price']), label)
    changed.add(r['payer'])
    data.update(cash=paid['cash'], acc=paid['acc'], text=paid['text'])
    who = 'bạn' if r['payer'] == sid else 'người ấy'
    if r['kind'] == 'adopt':
        _no_child(db, c)
        db.execute('INSERT INTO family_children(couple,state) VALUES(?,?)',
                   (c['id'], _json(_child(r['name'], 'adopt', AGENCY['name'], '', t))))
        db.execute("UPDATE birth_stays SET status='born',data=?,done=?,burn=? WHERE id=?", (_json(data), t, int(r['price']), r['id']))
        mr._notice(db, r['from_sid'], f'📄 Giấy tờ xong! Bé {r["name"]} đã về nhà.')
        return f'📄 Giấy tờ xong! Bé {r["name"]} đã về nhà. {who.capitalize()} trả {paid["text"]}.'
    db.execute("UPDATE birth_stays SET status='booked',data=? WHERE id=?", (_json(data), r['id']))
    mr._notice(db, r['from_sid'], '🏥 Người ấy đã đồng ý! Phòng sinh đã đặt. Bấm Nhận phòng khi hai bạn sẵn sàng.')
    return f'Đã đặt phòng sinh. {who.capitalize()} trả {paid["text"]}. Bấm Nhận phòng khi hai bạn sẵn sàng ({STAY_HOURS} giờ).'


def _room_set(db, sid, state, p, t) -> str:
    career = provider_career(state)
    _need(career, 'Cần sở hữu homestay (mở quy mô nghề Homestay từ cấp 1) để cho đặt phòng sinh.', 'not_provider', 403)
    name = _room_name(p.get('name'))
    price = p.get('price')
    _need(type(price) is int and price >= FLOOR, f'Giá phòng sinh tối thiểu {_fmt(FLOOR)} xu, không đặt thấp hơn.', 'below_floor')
    _need(price <= ROOM_MAX, f'Giá phòng sinh tối đa {_fmt(ROOM_MAX)} xu.', 'above_max')
    is_open = p.get('open', True)
    _need(type(is_open) is bool, 'Chọn mở hoặc đóng phòng.')
    db.execute('INSERT INTO birth_rooms(sid,career,name,price,open,at) VALUES(?,?,?,?,?,?) '
               'ON CONFLICT (sid) DO UPDATE SET career=EXCLUDED.career,name=EXCLUDED.name,price=EXCLUDED.price,open=EXCLUDED.open,at=EXCLUDED.at',
               (sid, career, name, price, is_open, t))
    return (f'Phòng sinh “{name}” đang nhận khách: {_fmt(price)} xu một ca, bạn nhận {100 - BURN_PCT}% khi bé chào đời.'
            if is_open else f'Đã tạm đóng phòng sinh “{name}”. Ca đã đặt vẫn giữ nguyên.')


def _nurse(db, sid, c, state, p) -> str:
    _need(is_nurse(state), 'Cần bắt đầu nghề Điều dưỡng để hỗ trợ ca sinh.', 'not_nurse', 403)
    ident = p.get('id')
    _need(type(ident) is int, 'Chọn ca sinh hợp lệ.')
    r = mr._row(db, 'SELECT * FROM birth_stays WHERE id=? FOR UPDATE', (ident,))
    _need(r and r['kind'] == 'birth' and r['status'] in ('booked', 'staying') and r['nurse_ok'], 'Ca sinh này không còn cần điều dưỡng.', 'stale', 409)
    _need(sid not in (r['from_sid'], r['to_sid']), 'Không tự hỗ trợ ca sinh của gia đình mình.', 'own_stay')
    _need(not r['nurse'], 'Đã có điều dưỡng khác nhận ca này rồi.', 'taken', 409)
    n = int(db.execute("SELECT COUNT(*) FROM birth_stays WHERE nurse=? AND status IN ('booked','staying')", (sid,)).fetchone()[0])
    _need(n < NURSE_ACTIVE_MAX, f'Bạn đang hỗ trợ {n} ca rồi. Xong bớt rồi nhận thêm nhé.', 'busy', 409)
    db.execute('UPDATE birth_stays SET nurse=? WHERE id=?', (sid, r['id']))
    me = mr._display(db, sid)
    for who in (r['from_sid'], r['to_sid']):
        mr._notice(db, who, f'🩺 Điều dưỡng {me} sẽ hỗ trợ ca sinh của bé {r["name"]}: bé chào đời khỏe mạnh hơn.')
    return f'Bạn đã nhận hỗ trợ ca sinh của bé {r["name"]}. Bé sẽ khỏe mạnh hơn nhờ bạn.'


# ---------------------------------------------------------------- the relationship ends, an account goes
def end(db, c: dict, deleted: str | None = None) -> None:
    """Inside the relationship-end transaction (game/family.py end): an open booking closes; money already paid goes
    back to the payer (a pending effect: their save is not locked here), unless the payer is the account being deleted."""
    t = mr.now()
    for r in mr._rows(db, "SELECT * FROM birth_stays WHERE couple=? AND status IN ('proposed','booked','staying') FOR UPDATE", (c['id'],)):
        if r['status'] == 'proposed':
            db.execute("UPDATE birth_stays SET status='cancelled',done=? WHERE id=?", (t, r['id']))
            continue
        if r['payer'] != deleted:
            _effect_wallet(db, f'birth:{r["id"]}:r', r['payer'], int(r['price']), f'Hoàn tiền phòng sinh ({r["name"]})')
        db.execute("UPDATE birth_stays SET status='refunded',done=? WHERE id=?", (t, r['id']))


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM birth_rooms WHERE sid=?', (sid,))
    db.execute("UPDATE birth_stays SET nurse=NULL WHERE nurse=? AND status IN ('booked','staying')", (sid,))
    db.execute("DELETE FROM birth_stays WHERE (from_sid=? OR to_sid=?) AND status NOT IN ('proposed','booked','staying')", (sid, sid))


def valid_birth(v) -> dict | None:
    """The optional `birth` block of a child as the sheet shows it (anything odd: None)."""
    if not isinstance(v, dict):
        return None
    where, nurse, at = v.get('where'), v.get('nurse'), v.get('at')
    if not isinstance(where, str) or not isinstance(nurse, str) or type(at) is not int:
        return None
    return dict(where=re.sub(r'[<>]', '', where)[:60], nurse=re.sub(r'[<>]', '', nurse)[:24], at=at)
