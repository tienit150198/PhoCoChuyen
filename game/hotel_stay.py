"""🏨 Phòng cho người chơi: a homestay or hotel player rents rooms to other players (owner 21/10: careers must interact
player to player, "làm hết đi").

The money is Phố dịch vụ's (game/service_market.py, SCHEMA 63): three services per career are registered there,
('homestay' | 'hotel', 'stay_night' | 'stay_hours' | 'stay_couple'), priced from an NPC room rate (BASE) × 3 by default,
×1–×10 or 🤝 thương lượng by the host; the guest's price is held in escrow at the order, the host is paid 95 % (5 %
burned) at check-out, and every cancel, decline or no-show refunds the guest in full (the market's rules). This file
is the stay itself (its own table, hotel_stays, keyed by the market's order id):

  held (the market: the host confirms = take, or declines) → booked (waiting for the guest)
  → arrived (the guest tapped "Tôi tới rồi") → in (the host checked them in: a room, the arrival quirk)
  → out (checked out: the stay's result goes to the market's deliver hook, the order settles at once)
  booked / arrived → gone (cancel by the guest, decline by the host, no-show after ARRIVE_HOURS: refunded in full)

While in, "oái oăm" situations (game/hotel_stay_content.py) come by themselves over the stay, and the guest player
may send up to ASK_MAX requests (late check-out, a free upgrade, a pet…); the host answers each with one choice that
moves the guest's satisfaction (mood, 0–100) and may cost the host a few xu (burned: a key card, a fan; never paid to
anyone). An unanswered one costs mood at check-out. A guest who leaves early is checked out GRACE_MIN later if the
host is away; a stay past its time + GRACE_MIN is checked out by the housekeeping (paid, with a mood penalty).

What the guest gets (REST, real but modest, the game's own bars, at most once per Vietnam day per player:
hotel_rest): tỉnh táo (journey.needs.wake) and no bụng (breakfast) up, tinh thần (journey.life.spirit) +1…+5 by the
stay and its mood. Couples (stay_couple, booked by one spouse/fiancé(e)) stay together: both rest (the partner's
through its own exactly-once step, partner_rest 1 → 2). No new save key: needs and spirit exist in every build since
1.4.1, and only their values move. Nothing is printed: the host's pay is the guest's escrow.

Exactly once: every step locks its hotel_stays row (FOR UPDATE) and checks the stage it starts from; a step that moves
a save (a host's cost, the partner's rest) runs in marriage._mutate with that check inside the same transaction; the
check-out marks the market order delivered in the same transaction (service_market.deliver_in_commit), so the
market's own status guard pays the host once.

🛑 MNL_HOTEL_OFF=1 (1 / true / yes / on): no new booking (the services refuse buyers and providers), the sheet says so; stays already paid
keep their way out (cancel, check-out, the housekeeping) so no money is stuck. No in-memory cache.
Tables (game/pg_schema.py SCHEMA_VERSION 68): hotel_stays, hotel_hosts, hotel_rest.
"""
from __future__ import annotations

import hashlib
import json
import random

from . import hotel_stay_content as hc
from . import marriage as mr
from . import service_market as sm

CAREERS = ('homestay', 'hotel')
SERVICES = {
    'stay_night': dict(kind='night', name='Phòng nghỉ qua đêm', icon='🛏️', unit='đêm', qty_max=3, minutes=180,
                       desc='Một đêm = 3 giờ thật. Ngủ ngon, có bữa sáng: tỉnh táo, no bụng, tinh thần lên.'),
    'stay_hours': dict(kind='hours', name='Nghỉ vài giờ', icon='⏰', unit='lượt', qty_max=1, minutes=60,
                       desc='Chợp mắt 1 giờ thật giữa ngày: tỉnh táo hơn một chút.'),
    'stay_couple': dict(kind='couple', name='Phòng đôi cho cặp đôi', icon='💞', unit='đêm', qty_max=3, minutes=180,
                        desc='Hai bạn ở chung một phòng (vợ chồng hoặc đã đính hôn): cả hai cùng được nghỉ.'),
}
# the NPC room rate of one unit (xu): homestay rooms are 28–48 xu a night (game/careers/homestay.py SPEC), the hotel a bit more
BASE = {'homestay': dict(stay_night=30, stay_hours=12, stay_couple=44), 'hotel': dict(stay_night=40, stay_hours=15, stay_couple=56)}
REST = {'night': dict(wake=45, full=25, spirit=3), 'couple': dict(wake=45, full=25, spirit=4), 'hours': dict(wake=20, full=0, spirit=1)}
MOOD_START, MOOD_GOOD, MOOD_BAD = 70, 80, 40
MISSED_MOOD, AUTO_OUT_MOOD = -8, -5
ARRIVE_HOURS = 12          # a confirmed booking the guest never comes to (or a guest never checked in): refunded
WAIT_MIN = 60              # a guest who arrived and waited this long may cancel (the host is away)
MIN_STAY_MIN = 15          # the earliest a guest may ask to leave
LATE_MIN = 60              # a granted late check-out
GRACE_MIN = 30             # past the end (or a guest's early leave) with no host: checked out by the system
ASK_MAX = 2                # requests a stay's guests may send
EVENTS_MAX = 5
GUEST_OPEN = 1             # open bookings (held or working) a guest may hold at once
WORK_HOURS = 48            # the market's limit for a taken order (longer than any stay: ours always ends first)
STAGES = ('booked', 'arrived', 'in', 'out', 'gone')
LIVE = ('booked', 'arrived', 'in')
HOUR, MIN = 3600, 60


def off() -> bool:
    return sm.env_on('MNL_HOTEL_OFF')


def now() -> float:
    return sm.now()


def need(cond, message: str, code: str = 'hotel_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _load(text, default):
    try:
        v = json.loads(text) if text else default
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def is_stay(career: str, service: str) -> bool:
    return career in CAREERS and service in SERVICES


# ---------------------------------------------------------------- the market's side
def _can_provide(career):
    def why(state):
        if off():
            return 'Sổ phòng đang tạm đóng.'
        c = (state.get('careers') or {}).get(career)
        if not (isinstance(c, dict) and c.get('started')):
            return 'Bạn cần làm nghề này trước đã.'
        if not (state.get('journey') or {}).get('story'):
            return 'Cho thuê phòng dùng ví hành trình.'
        return ''
    return why


def _open_stays(db, buyer: str) -> int:
    marks = ','.join('?' * len(SERVICES))
    return int(db.execute(f"SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND kind='svc' AND career IN (?,?) AND service IN ({marks}) "
                          "AND status IN ('held','working')", (buyer, *CAREERS, *SERVICES)).fetchone()['n'])


def _check(service):
    def why(db, buyer, state):
        if off():
            return 'Sổ phòng đang tạm đóng, chưa nhận đặt phòng mới.'
        if _open_stays(db, buyer) >= GUEST_OPEN:
            return 'Bạn đang có một lượt đặt phòng. Trả phòng hoặc hủy trước rồi đặt tiếp nhé.'
        if service == 'stay_couple':
            c = mr._bond(db, buyer)
            if not c or c.get('status') not in ('engaged', 'married'):
                return 'Phòng đôi dành cho vợ chồng hoặc hai bạn đã đính hôn.'
        return ''
    return why


def _deliver(db, provider, buyer, order):
    """The market's deliver hook: only the check-out here delivers (the generic "Xong việc" is refused, also earlier in
    service_market._done). A plain read, never FOR UPDATE: the market holds svc_orders here, and every stay step locks
    hotel_stays first, then svc_orders (_step, _checkout_db → deliver_in_commit): one lock order, no deadlock."""
    r = db.execute('SELECT stage,result FROM hotel_stays WHERE order_id=?', (order['id'],)).fetchone()
    need(r and r['stage'] == 'out', 'Trả phòng cho khách ở 🏨 Sổ phòng nhé.', 'use_hotel_book', 409)
    return _load(r['result'], {})


def _on_buyer(state, order):
    """At settlement (the market's transaction, once): the guest's rest."""
    rest = ((order.get('result') or {}).get('rest') or {}).get('guest')
    if isinstance(rest, dict):
        apply_rest(state, rest)


def apply_rest(state: dict, rest: dict) -> None:
    """tỉnh táo / no bụng (journey.needs) and tinh thần (journey.life.spirit), clamped; story saves only."""
    from . import needs as nd
    j = state.get('journey')
    if not isinstance(j, dict) or not j.get('story') or type(j.get('life_day')) is not int:
        return
    wake, full, spirit = (max(0, min(100, int(rest.get(k) or 0))) for k in ('wake', 'full', 'spirit'))
    n = nd.ensure(state)
    n['wake'] = nd._clamp(n['wake'] + wake)
    n['full'] = nd._clamp(n['full'] + full)
    nd._spirit(state, min(spirit, 5))


def install() -> None:
    for career in CAREERS:
        for sid, S in SERVICES.items():
            sm.register(career, sid, dict(
                name=S['name'], icon=S['icon'], desc=S['desc'], base=BASE[career][sid], unit=S['unit'], duration=S['minutes'],
                qty_max=S['qty_max'], work_hours=WORK_HOURS, deliver=_deliver, on_buyer=_on_buyer, confirm='auto',
                requires=dict(story=True), check=_check(sid), can_provide=_can_provide(career),
                note_hint='Ví dụ: cho mình phòng yên tĩnh nhé'))


install()


# ---------------------------------------------------------------- draws (deterministic from the order id)
def _rng(oid: str, salt: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f'{oid}:{salt}'.encode()).hexdigest()[:16], 16))


def _pick(oid: str, salt: str, keys) -> str:
    keys = sorted(keys)
    return keys[_rng(oid, salt).randrange(len(keys))]


def _plan(oid: str, service: str, qty: int, temper: str) -> list:
    """The night's situations (ids), drawn once at check-in."""
    kind = SERVICES[service]['kind']
    n = 1 if kind == 'hours' else min(4, 1 + qty)
    n = min(EVENTS_MAX, n + hc.TEMPERS[temper]['extra'])
    pool = sorted(k for k, e in hc.EVENTS.items() if not e.get('couple'))
    r = _rng(oid, 'plan')
    r.shuffle(pool)
    if kind == 'couple':
        couple = sorted(k for k, e in hc.EVENTS.items() if e.get('couple'))
        pool = [couple[r.randrange(len(couple))]] + pool
    return pool[:n]


# ---------------------------------------------------------------- rows
def _row(db, oid: str, lock: bool = False) -> dict | None:
    r = db.execute('SELECT * FROM hotel_stays WHERE order_id=?' + (' FOR UPDATE' if lock else ''), (oid,)).fetchone()
    if not r:
        return None
    r = dict(r)
    r['ev'] = _load(r['ev'], [])
    return r


def _save(db, r: dict, t: float, **cols) -> None:
    r.update(cols)
    ev = r['ev']
    opens = [e for e in ev if e['st'] == 'open' and e['k'] in ('sys', 'ask')]
    waits = [e['at'] for e in ev if e['st'] == 'wait']
    r['open_n'] = len(opens)
    r['next_at'] = min(waits) if waits else None
    db.execute('UPDATE hotel_stays SET stage=?,room=?,arrived_at=?,in_at=?,due_at=?,out_at=?,mood=?,ev=?,asks=?,want_out=?,late=?,open_n=?,'
               'next_at=?,partner_rest=?,result=?,updated_at=? WHERE order_id=?',
               (r['stage'], r['room'], r['arrived_at'], r['in_at'], r['due_at'], r['out_at'], r['mood'], _j(ev), r['asks'], r['want_out'],
                r['late'], r['open_n'], r['next_at'], r['partner_rest'], r['result'], t, r['order_id']))


def _create(db, o: dict, t: float) -> None:
    """A working market order of a stay that has no row yet (the host took it here or in the market's inbox)."""
    partner = ''
    if o['service'] == 'stay_couple':
        c = mr._bond(db, o['buyer'])
        if c and c.get('status') in ('engaged', 'married'):
            other = mr._other(c, o['buyer'])
            partner = other if other != o['provider'] else ''
    oid = o['id']
    wish = _pick(oid, 'wish', hc.WISHES if o['career'] == 'homestay' else [k for k in hc.WISHES if k != 'nostairs'])
    temper = _pick(oid, 'temper', hc.TEMPERS)
    db.execute('INSERT INTO hotel_stays(order_id,host,guest,partner,career,service,qty,stage,wish,temper,booked_at,mood,updated_at) '
               "VALUES(?,?,?,?,?,?,?,'booked',?,?,?,?,?) ON CONFLICT (order_id) DO NOTHING",
               (oid, o['provider'], o['buyer'], partner, o['career'], o['service'], int(o['qty']), wish, temper,
                float(o['updated_at'] or t), MOOD_START, t))


def _ripe(r: dict, t: float) -> bool:
    """Situations whose time came become open (in place). True when something changed."""
    moved = False
    for e in r['ev']:
        if e['st'] == 'wait' and e['at'] <= t:
            e['st'] = 'open'
            moved = True
    return moved


def _mood(r: dict, delta: int) -> int:
    if delta < 0:
        delta = -int(round(-delta * hc.TEMPERS.get(r['temper'], hc.TEMPERS['de_tinh'])['bad']))
    before = int(r['mood'])
    r['mood'] = max(0, min(100, before + delta))
    return r['mood'] - before


def _opt(cat: dict, key: str, pick) -> tuple:
    item = cat.get(key)
    need(item, 'Tình huống này không còn nữa.', 'stale', 409)
    opt = next((o for o in item['opts'] if o[0] == pick), None)
    need(opt, 'Chọn một cách xử lý nhé.', 'bad_pick')
    return item, opt


def _cat(kind: str) -> dict:
    return dict(sys=hc.EVENTS, ask=hc.ASKS, **{'in': hc.CHECKIN, 'out': hc.CHECKOUT})[kind]


def _due(r: dict) -> float:
    return float(r['due_at'] or 0) + int(r['late'] or 0) * MIN


def _stars(mood: int) -> int:
    return 5 if mood >= 85 else 4 if mood >= 70 else 3 if mood >= 50 else 2 if mood >= 30 else 1


def _rest_for(kind: str, mood: int) -> dict:
    x = dict(REST[kind])
    if mood >= MOOD_GOOD:
        x['spirit'] += 1
    elif mood < MOOD_BAD:
        x['spirit'] = 0
        x['wake'] //= 2
    return x


def _rested(db, sid: str, oid: str, t: float) -> bool:
    """One rest a Vietnam day per player: True when this one counts."""
    from .wedding_live import vn_day
    return db.execute('INSERT INTO hotel_rest(sid,day,order_id,at) VALUES(?,?,?,?) ON CONFLICT DO NOTHING', (sid, vn_day(t), oid, t)).rowcount == 1


# ---------------------------------------------------------------- refunds (the market's rules: the whole price back)
def _refund_db(db, r: dict, why: str, t: float) -> bool:
    """Inside a transaction, the row locked: the market order back to its buyer (status-guarded), the stay gone."""
    o = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (r['order_id'],)).fetchone()
    if o and o['status'] == 'working':
        d = sm._data(dict(o))
        d['why'] = why
        sm._set_data(db, o['id'], d)
        if not sm._flip(db, o['id'], 'working', 'refund', t, due_at=t):
            raise sm._Replay()
    _save(db, r, t, stage='gone', out_at=t)
    return True


# ---------------------------------------------------------------- the check-out (exactly once, pays the host)
def _checkout_db(db, r: dict, t: float, pick: str | None, auto: bool) -> tuple:
    """Inside the transaction, the row locked at stage 'in'. Returns (partner, message)."""
    _ripe(r, t)
    for e in r['ev']:
        if e['st'] in ('open', 'wait') and e['k'] in ('sys', 'ask'):
            if e['st'] == 'open':
                e.update(st='miss', d=_mood(r, MISSED_MOOD), reply=hc.MISSED)
            else:
                e['st'] = 'skip'
    key = _pick(r['order_id'], 'out', hc.CHECKOUT)
    if auto or pick is None:
        r['ev'].append(dict(k='out', id=key, at=t, st='miss', d=_mood(r, AUTO_OUT_MOOD), reply=hc.AUTO_OUT, by='sys'))
    else:
        _, o = _opt(hc.CHECKOUT, key, pick)
        r['ev'].append(dict(k='out', id=key, at=t, st='done', pick=pick, d=_mood(r, o[2]), c=o[3], reply=o[5], by='sys'))
    mood = int(r['mood'])
    kind = SERVICES[r['service']]['kind']
    rest = _rest_for(kind, mood)
    got = dict(guest=rest if _rested(db, r['guest'], r['order_id'], t) else None)
    partner_rest = 0
    if r['partner'] and db.execute('SELECT 1 FROM sessions WHERE sid=?', (r['partner'],)).fetchone():
        if _rested(db, r['partner'], r['order_id'], t):
            got['partner'] = rest
            partner_rest = 1
    room = _room(r['career'], r['room'])
    handled = sum(1 for e in r['ev'] if e['k'] in ('sys', 'ask', 'in', 'out') and e['st'] == 'done')
    missed = sum(1 for e in r['ev'] if e['st'] == 'miss')
    brief = f'{room["icon"]} {room["name"]} · 😊 hài lòng {mood}%'
    result = dict(brief=brief, stay=dict(room=room['name'], mood=mood, stars=_stars(mood), nights=int(r['qty']), kind=kind,
                                         handled=handled, missed=missed, auto=bool(auto)), rest=got)
    _save(db, r, t, stage='out', out_at=t, want_out=0, partner_rest=partner_rest, result=_j(result))
    db.execute('INSERT INTO hotel_hosts(sid,stays,mood_sum,handled,missed,updated_at) VALUES(?,1,?,?,?,?) ON CONFLICT (sid) DO UPDATE SET '
               'stays=hotel_hosts.stays+1,mood_sum=hotel_hosts.mood_sum+EXCLUDED.mood_sum,handled=hotel_hosts.handled+EXCLUDED.handled,'
               'missed=hotel_hosts.missed+EXCLUDED.missed,updated_at=EXCLUDED.updated_at', (r['host'], mood, handled, missed, t))
    sm.deliver_in_commit(db, r['host'], r['order_id'])   # the market: working → ready (its deliver hook reads this row)
    line = f'🏨 Trả phòng {room["name"]}: hài lòng {mood}%.' + (' Bạn đã được nghỉ ngơi.' if got['guest'] else ' Hôm nay bạn đã nghỉ một lần rồi.')
    mr._notice(db, r['guest'], line)
    if partner_rest:
        mr._notice(db, r['partner'], line)
    return (r['partner'] if partner_rest else '', f'Đã trả phòng. Khách hài lòng {mood}%.')


def _after_out(store, r: dict, partner: str) -> None:
    sm.settle_quiet(store, r['host'], r['order_id'])   # host paid 95 %, 5 % burned, the guest's rest (on_buyer)
    if partner:
        settle_partner(store, partner)


def settle_partner(store, sid: str | None = None, limit: int = 10) -> int:
    """The partner's rest of a couple's stay, once (partner_rest 1 → 2 in the save's transaction)."""
    sql = 'SELECT order_id,partner,result FROM hotel_stays WHERE partner_rest=1' + (' AND partner=?' if sid else '') + ' LIMIT ?'
    with store.connect() as db:
        rows = [dict(x) for x in db.execute(sql, ((sid,) if sid else ()) + (limit,)).fetchall()]
    n = 0
    for x in rows:
        rest = (_load(x['result'], {}).get('rest') or {}).get('partner')

        def flip(db, oid=x['order_id']):
            if db.execute('UPDATE hotel_stays SET partner_rest=2 WHERE order_id=? AND partner_rest=1', (oid,)).rowcount != 1:
                raise sm._Replay()
        try:
            if isinstance(rest, dict) and mr._read_state(store, x['partner']):
                mr._mutate_retry(store, {x['partner']: lambda s, rest=rest: apply_rest(s, rest)}, flip)
            else:
                store.transaction(flip)
            n += 1
        except sm._Replay:
            pass
    return n


# ---------------------------------------------------------------- timers: rows to create, no-shows, the night, check-outs
def sync(store, sid: str | None = None, limit: int = 20) -> int:
    t = now()
    marks = ','.join('?' * len(SERVICES))
    who = ' AND (o.buyer=? OR o.provider=?)' if sid else ''
    mine = ' AND (h.host=? OR h.guest=? OR h.partner=?)' if sid else ''
    with store.connect() as db:
        new = [dict(x) for x in db.execute(
            f"SELECT o.* FROM svc_orders o LEFT JOIN hotel_stays h ON h.order_id=o.id WHERE h.order_id IS NULL AND o.status='working' "
            f"AND o.kind='svc' AND o.career IN (?,?) AND o.service IN ({marks}){who} ORDER BY o.updated_at LIMIT ?",
            (*CAREERS, *SERVICES, *((sid, sid) if sid else ()), limit)).fetchall()]
        due = [x['order_id'] for x in db.execute(
            "SELECT h.order_id FROM hotel_stays h LEFT JOIN svc_orders o ON o.id=h.order_id WHERE h.stage IN ('booked','arrived','in')" + mine +
            " AND (o.status IS NULL OR o.status<>'working' OR (h.stage='booked' AND h.booked_at<=?) OR (h.stage='arrived' AND h.arrived_at<=?)"
            " OR (h.stage='in' AND (h.due_at+h.late*60<=? OR h.next_at<=?))) ORDER BY h.updated_at LIMIT ?",
            (*((sid, sid, sid) if sid else ()), t - ARRIVE_HOURS * HOUR, t - ARRIVE_HOURS * HOUR, t - GRACE_MIN * MIN, t, limit)).fetchall()]
    if new:
        store.transaction(lambda db: [_create(db, o, t) for o in new])
    n = len(new)
    for oid in due:
        n += _step(store, oid)
    n += settle_partner(store, sid)
    return n


def _step(store, oid: str) -> int:
    t = now()
    out = {}

    def run(db):
        r = _row(db, oid, lock=True)
        if not r or r['stage'] not in LIVE:
            return 0
        o = db.execute('SELECT status FROM svc_orders WHERE id=?', (oid,)).fetchone()
        if not o or o['status'] != 'working':       # refunded or settled meanwhile (the market's own timer, a decline)
            _save(db, r, t, stage='gone', out_at=t)
            return 1
        if r['stage'] == 'booked' and float(r['booked_at']) <= t - ARRIVE_HOURS * HOUR:
            _refund_db(db, r, 'noshow', t)
            mr._notice(db, r['host'], '🏨 Khách không tới nhận phòng: lượt đặt được hủy, khách được hoàn tiền.')
            out['refund'] = True
            return 1
        if r['stage'] == 'arrived' and float(r['arrived_at']) <= t - ARRIVE_HOURS * HOUR:
            _refund_db(db, r, 'late', t)
            mr._notice(db, r['guest'], '🏨 Chủ nhà không nhận phòng cho bạn: đã hoàn đủ tiền phòng.')
            out['refund'] = True
            return 1
        if r['stage'] == 'in' and _due(r) + GRACE_MIN * MIN <= t:
            out['partner'], _ = _checkout_db(db, r, t, None, True)
            out['row'] = r
            return 1
        if r['stage'] == 'in' and _ripe(r, t):
            _save(db, r, t)
            return 1
        return 0
    try:
        n = store.transaction(run)
    except (sm._Replay, sm.ServiceError):
        return 0
    if out.get('row'):
        _after_out(store, out['row'], out.get('partner') or '')
    elif out.get('refund'):
        sm.settle_quiet(store, None, oid)
    return int(n or 0)


_swept = [0.0]


def run_housekeeping(store, every: float = 60.0) -> int:
    """No-shows, the night's situations and overdue check-outs for everyone (both players may be away)."""
    t = now()
    if t - _swept[0] < every:
        return 0
    _swept[0] = t
    return sync(store, None, 50)


def alerts(db, sid: str) -> int:
    """What waits for this host: a guest at the desk, a situation, a check-out (the ticker's svc badge)."""
    t = now()
    return int(db.execute("SELECT COUNT(*) AS n FROM hotel_stays WHERE host=? AND (stage='arrived' OR (stage='in' AND (open_n>0 OR want_out=1 "
                          'OR due_at+late*60<=? OR next_at<=?)))', (sid, t, t)).fetchone()['n'])


def forget(db, sid: str) -> None:
    """Store.delete (the market's forget refunds their open orders): their host record and rest days go; a couple's
    stay loses the partner's rest; live stays settle through the market (the housekeeping marks them gone)."""
    db.execute('DELETE FROM hotel_hosts WHERE sid=?', (sid,))
    db.execute('DELETE FROM hotel_rest WHERE sid=?', (sid,))
    db.execute('UPDATE hotel_stays SET partner_rest=0 WHERE partner=? AND partner_rest=1', (sid,))


# ---------------------------------------------------------------- the view
def _room(career: str, rid: str) -> dict:
    return next((x for x in hc.ROOMS[career] if x['id'] == rid), dict(id='', name='Chưa xếp phòng', icon='🚪', note='', tags=()))


def _opts(cat: dict, key: str) -> list:
    return [dict(id=o[0], label=o[1], cost=o[3], tone='good' if o[2] > 0 else 'bad' if o[2] < 0 else 'mid') for o in cat[key]['opts']]


def _ev_public(e: dict, host: bool) -> dict:
    cat = _cat(e['k']) if e['k'] in ('sys', 'ask', 'in', 'out') else {}
    item = cat.get(e['id']) or {}
    pick = next((o for o in item.get('opts', ()) if o[0] == e.get('pick')), None)
    out = dict(key=f'{e["k"]}:{e["id"]}', k=e['k'], id=e['id'], icon=item.get('icon', '🏨'), st=e['st'], by=e.get('by', 'sys'),
               text=item.get('text', e.get('text', '')), reply=e.get('reply', ''), pick=pick[1] if pick else '', d=e.get('d', 0) if host else None)
    if e['k'] == 'ask':
        out['ask'] = item.get('ask', '')
    if host and e['st'] == 'open' and item:
        out['opts'] = _opts(cat, e['id'])
    return out


def _stay_public(db, r: dict, me: str, t: float, people: dict, busy: set) -> dict:
    host = r['host'] == me
    for s in (r['host'], r['guest'], r['partner']):
        if s and s not in people:
            people[s] = sm._person(db, s)
    S = SERVICES[r['service']]
    room = _room(r['career'], r['room'])
    o = db.execute('SELECT price,status FROM svc_orders WHERE id=?', (r['order_id'],)).fetchone()
    shown = [e for e in r['ev'] if e['st'] != 'wait' and e['st'] != 'skip']
    v = dict(id=r['order_id'], career=r['career'], service=r['service'], kind=S['kind'], name=S['name'], icon=S['icon'], unit=S['unit'],
             qty=int(r['qty']), price=int(o['price']) if o else 0, status=o['status'] if o else '', stage=r['stage'], role='host' if host else 'guest',
             host=people[r['host']], guest=people[r['guest']], partner=people.get(r['partner']) if r['partner'] else None,
             room=dict(id=room['id'], name=room['name'], icon=room['icon']) if r['room'] else None,
             wish=dict(hc.WISHES[r['wish']], id=r['wish']) if r['wish'] in hc.WISHES else None,
             booked_at=r['booked_at'], arrived_at=r['arrived_at'], in_at=r['in_at'], out_at=r['out_at'],
             due=_due(r) if r['stage'] == 'in' else None, left=max(0, int(_due(r) - t)) if r['stage'] == 'in' else None,
             want_out=bool(r['want_out']), late=int(r['late'] or 0), mood=int(r['mood']), events=[_ev_public(e, host) for e in shown],
             result=_load(r['result'], {}) or None, partner_me=bool(r['partner']) and r['partner'] == me, actions=[])
    acts = v['actions']
    if host:
        v['temper'] = dict(hc.TEMPERS[r['temper']], id=r['temper']) if r['temper'] in hc.TEMPERS else None
        if r['stage'] in ('booked', 'arrived'):
            acts.append('decline')
        if r['stage'] == 'arrived':
            acts.append('checkin')
            q = next((e for e in r['ev'] if e['k'] == 'in' and e['st'] == 'open'), None)
            if q:
                v['quirk'] = dict(_ev_public(q, True))
            v['rooms'] = [dict(id=x['id'], name=x['name'], icon=x['icon'], note=x['note'], busy=x['id'] in busy,
                               cost=hc.SUITE_COST if 'suite' in x['tags'] else 0) for x in hc.ROOMS[r['career']]]
        if r['stage'] == 'in' and (r['want_out'] or _due(r) <= t):
            acts.append('checkout')
            key = _pick(r['order_id'], 'out', hc.CHECKOUT)
            v['out_quirk'] = dict(key='out:' + key, icon=hc.CHECKOUT[key]['icon'], text=hc.CHECKOUT[key]['text'], opts=_opts(hc.CHECKOUT, key))
    else:
        if r['stage'] == 'booked':
            acts.append('arrive')
        if r['stage'] in ('booked', 'arrived') and r['guest'] == me:
            acts.append('cancel')
        if r['stage'] == 'in':
            asked = {e['id'] for e in r['ev'] if e['k'] == 'ask'}
            if int(r['asks']) < ASK_MAX:
                acts.append('ask')
                v['asks'] = [dict(id=k, icon=a['icon'], label=a['ask']) for k, a in hc.ASKS.items() if k not in asked]
            if not r['want_out'] and t >= float(r['in_at'] or 0) + MIN_STAY_MIN * MIN:
                acts.append('leave')
        if r['stage'] == 'out' and o and o['status'] == 'done' and r['guest'] == me:
            v['rated'] = bool(db.execute('SELECT 1 FROM svc_reviews WHERE order_id=?', (r['order_id'],)).fetchone())
            if not v['rated']:
                acts.append('rate')
        if r['stage'] == 'arrived':
            v['waited'] = int(t - float(r['arrived_at'] or t))
    return v


def _pending(db, o: dict, me: str, people: dict) -> dict:
    other = o['buyer'] if o['provider'] == me else o['provider']
    if other not in people:
        people[other] = sm._person(db, other)
    S = SERVICES[o['service']]
    return dict(id=o['id'], career=o['career'], service=o['service'], kind=S['kind'], name=S['name'], icon=S['icon'], unit=S['unit'],
                qty=int(o['qty']), price=int(o['price']), note=sm._data(o).get('note', ''), who=people[other], created_at=o['created_at'],
                role='host' if o['provider'] == me else 'guest', actions=['confirm', 'decline'] if o['provider'] == me else ['cancel'])


def host_card(db, sid: str) -> dict:
    h = db.execute('SELECT * FROM hotel_hosts WHERE sid=?', (sid,)).fetchone()
    if not h or not int(h['stays']):
        return dict(stays=0, mood=None, handled=0, missed=0)
    return dict(stays=int(h['stays']), mood=round(int(h['mood_sum']) / int(h['stays'])), handled=int(h['handled']), missed=int(h['missed']))


def view(store, sid: str, state: dict | None = None) -> dict:
    sync(store, sid)
    t = now()
    marks = ','.join('?' * len(SERVICES))
    people = {}
    with store.connect() as db:
        rows = [_row(db, x['order_id']) for x in db.execute(
            'SELECT order_id FROM hotel_stays WHERE (host=? OR guest=? OR partner=?) AND (stage IN (?,?,?) OR updated_at>?) '
            'ORDER BY updated_at DESC LIMIT 40', (sid, sid, sid, *LIVE, t - 3 * 86400)).fetchall()]
        held = [dict(x) for x in db.execute(
            f"SELECT * FROM svc_orders WHERE (provider=? OR buyer=?) AND kind='svc' AND status='held' AND career IN (?,?) AND service IN ({marks}) "
            'ORDER BY created_at LIMIT 30', (sid, sid, *CAREERS, *SERVICES)).fetchall()]
        busy = {(r['career'], r['room']) for r in db.execute("SELECT career,room FROM hotel_stays WHERE host=? AND stage='in'", (sid,)).fetchall()}
        stays = []
        for r in rows:
            if r:
                stays.append(_stay_public(db, r, sid, t, people, {room for c, room in busy if c == r['career']}))
        pending = [_pending(db, o, sid, people) for o in held]
        selling = [dict(career=x['career'], service=x['service']) for x in db.execute(
            f"SELECT career,service FROM svc_settings WHERE provider=? AND on_=1 AND career IN (?,?) AND service IN ({marks})",
            (sid, *CAREERS, *SERVICES)).fetchall()]
        card = host_card(db, sid)
    if state is None:
        loaded = mr._read_state(store, sid)
        state = loaded[0] if loaded else {}
    careers = [c for c in CAREERS if isinstance((state.get('careers') or {}).get(c), dict) and state['careers'][c].get('started')]
    host = [x for x in stays if x['role'] == 'host']
    guest = [x for x in stays if x['role'] == 'guest']
    return dict(off=off(), now=t, careers=careers, selling=selling, card=card,
                host=dict(pending=[p for p in pending if p['role'] == 'host'], stays=host),
                guest=dict(pending=[p for p in pending if p['role'] == 'guest'], stays=guest),
                rules=dict(arrive_hours=ARRIVE_HOURS, wait_min=WAIT_MIN, min_stay_min=MIN_STAY_MIN, late_min=LATE_MIN, grace_min=GRACE_MIN,
                           ask_max=ASK_MAX, fee_pct=sm.FEE_PCT, default_mult=sm.DEFAULT_MULT, rest=REST, mood_good=MOOD_GOOD,
                           services={k: dict(name=v['name'], icon=v['icon'], minutes=v['minutes'], unit=v['unit']) for k, v in SERVICES.items()},
                           base=BASE))


# ---------------------------------------------------------------- actions
def _oid(data) -> str:
    oid = data.get('order')
    need(isinstance(oid, str) and sm.ID_RX.fullmatch(oid) and oid.startswith('sv_'), 'Không tìm thấy lượt đặt phòng.', 'not_found', 404)
    return oid


def _with_cost(store, payer: str, cost: int, label: str, run) -> None:
    """`run(db)` in one transaction; with a cost, the payer's save pays it (burned) in that same transaction."""
    if cost > 0:
        mr._mutate_retry(store, {payer: lambda s: sm.debit(s, cost, label)}, run)
    else:
        store.transaction(run)


def _market_order(db, oid: str, sid: str) -> dict:
    """The market order of a stay this player is part of: its buyer, its host, or the couple's partner."""
    o = db.execute('SELECT * FROM svc_orders WHERE id=?', (oid,)).fetchone()
    mine = o and (sid in (o['buyer'], o['provider']) or
                  db.execute("SELECT 1 FROM hotel_stays WHERE order_id=? AND partner=? AND partner<>''", (oid, sid)).fetchone())
    need(mine and is_stay(o['career'], o['service']), 'Không tìm thấy lượt đặt phòng.', 'not_found', 404)
    return dict(o)


def post(store, token, state, op: str, data: dict, ip: str = '') -> dict:
    sid = sm._actor(store, token)
    need(isinstance(data, dict), 'Dữ liệu không hợp lệ.')
    sm._touch(store, sid, ip)
    oid = _oid(data)
    t = now()
    with store.connect() as db:
        o = _market_order(db, oid, sid)
    host = o['provider'] == sid
    if op in ('confirm', 'decline', 'cancel') and o['status'] == 'held':
        need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')
        need((op == 'cancel') != host, 'Thao tác không hợp lệ.', 'forbidden', 403)
        if op == 'confirm':
            need(not off(), 'Sổ phòng đang tạm đóng, chưa nhận khách mới.', 'off', 503)
        out = sm.post(store, token, state, 'take' if op == 'confirm' else op, dict(order=oid), ip)
        if op == 'confirm':
            sync(store, sid)
            store.transaction(lambda db: mr._notice(db, o['buyer'], '🏨 Chủ nhà đã xác nhận phòng của bạn. Tới nơi thì bấm “🧳 Tôi tới rồi” nhé.'))
        msg = dict(confirm='Đã xác nhận đặt phòng. Khách tới thì nhận phòng cho khách nhé.', decline='Đã từ chối. Tiền đã hoàn về ví khách.',
                   cancel='Đã hủy. Tiền đã hoàn về ví của bạn.')[op]
        return dict(changed=bool(out.get('changed')), message=msg, view=view(store, sid, state))
    sync(store, sid)
    fn = dict(decline=_decline, cancel=_cancel, arrive=_arrive, checkin=_checkin, handle=_handle, ask=_ask, leave=_leave, checkout=_checkout).get(op)
    need(fn, 'Thao tác không hợp lệ.', 'unknown_action')
    msg = fn(store, sid, oid, data, t)
    return dict(changed=True, message=msg, view=view(store, sid, state))


def _locked(db, oid: str, sid: str, role: str, stages) -> dict:
    r = _row(db, oid, lock=True)
    need(r, 'Lượt đặt phòng này chưa sẵn sàng. Tải lại nhé.', 'not_found', 404)
    if role == 'host':
        need(r['host'] == sid, 'Chỉ chủ nhà làm được việc này.', 'forbidden', 403)
    elif role == 'buyer':
        need(r['guest'] == sid, 'Chỉ người đặt phòng làm được việc này.', 'forbidden', 403)
    else:
        need(sid in (r['guest'], r['partner']), 'Chỉ khách của phòng làm được việc này.', 'forbidden', 403)
    need(r['stage'] in stages, 'Lượt này đã sang bước khác. Tải lại nhé.', 'stale', 409)
    return r


def _decline(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')

    def run(db):
        r = _locked(db, oid, sid, 'host', ('booked', 'arrived'))
        _refund_db(db, r, 'decline', t)
        mr._notice(db, r['guest'], '🏨 Chủ nhà đã hủy phòng của bạn. Đã hoàn đủ tiền phòng.')
    store.transaction(run)
    sm.settle_quiet(store, sid, oid)
    return 'Đã hủy lượt đặt. Tiền đã hoàn đủ cho khách.'


def _cancel(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')

    def run(db):
        r = _locked(db, oid, sid, 'buyer', ('booked', 'arrived'))
        _refund_db(db, r, 'cancel', t)
        mr._notice(db, r['host'], '🏨 Khách đã hủy đặt phòng (được hoàn tiền theo luật Phố dịch vụ).')
    store.transaction(run)
    sm.settle_quiet(store, sid, oid)
    return 'Đã hủy. Tiền phòng đã hoàn đủ về ví của bạn.'


def _arrive(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')

    def run(db):
        r = _locked(db, oid, sid, 'guest', ('booked',))
        key = _pick(oid, 'in', hc.CHECKIN)
        r['ev'].append(dict(k='in', id=key, at=t, st='open', by='sys'))
        _save(db, r, t, stage='arrived', arrived_at=t)
        mr._notice(db, r['host'], f'🧳 {mr._display(db, sid)} đã tới quầy, chờ bạn nhận phòng.')
    store.transaction(run)
    return 'Bạn đã tới quầy. Chờ chủ nhà nhận phòng cho bạn nhé.'


def _checkin(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order', 'room', 'pick'}, 'Thông tin không hợp lệ.')
    with store.connect() as db:
        r0 = _row(db, oid)
    need(r0 and r0['host'] == sid, 'Không tìm thấy lượt đặt phòng.', 'not_found', 404)
    room = next((x for x in hc.ROOMS[r0['career']] if x['id'] == data.get('room')), None)
    need(room, 'Chọn một phòng cho khách nhé.', 'bad_room')
    q = next((e for e in r0['ev'] if e['k'] == 'in'), None)
    need(q, 'Khách chưa tới quầy.', 'stale', 409)
    _, opt = _opt(hc.CHECKIN, q['id'], data.get('pick'))
    cost = opt[3] + (hc.SUITE_COST if 'suite' in room['tags'] else 0)
    out = {}

    def run(db):
        r = _locked(db, oid, sid, 'host', ('arrived',))
        need(not db.execute("SELECT 1 FROM hotel_stays WHERE host=? AND career=? AND room=? AND stage='in'", (sid, r['career'], room['id'])).fetchone(),
             f'{room["name"]} đang có khách. Chọn phòng khác nhé.', 'room_busy', 409)
        e = next(x for x in r['ev'] if x['k'] == 'in')
        need(e['st'] == 'open', 'Đã nhận phòng rồi.', 'stale', 409)
        e.update(st='done', pick=opt[0], d=_mood(r, opt[2]), c=opt[3], reply=opt[5])
        wish = hc.WISHES.get(r['wish'])
        fit, line = 0, ''
        if SERVICES[r['service']]['kind'] == 'couple' and 'double' not in room['tags']:
            fit, line = -12, 'Phòng đôi mà xếp hai giường đơn, hai bạn phải nằm hai đầu phòng.'
        elif wish and (wish['tag'] in room['tags'] if not wish['tag'].startswith('-') else wish['tag'][1:] not in room['tags']):
            fit, line = 6, 'Phòng đúng ý bạn dặn.'
        elif wish:
            fit, line = -6, 'Phòng không giống điều bạn đã dặn.'
        if 'suite' in room['tags']:
            fit, line = fit + 4, (line + ' Lại còn là suite xịn!').strip()
        r['ev'].append(dict(k='room', id=room['id'], at=t, st='done', d=_mood(r, fit), reply=f'{room["icon"]} {room["name"]}. {line}'.strip(), by='sys'))
        minutes = SERVICES[r['service']]['minutes'] * int(r['qty'])
        plan = _plan(oid, r['service'], int(r['qty']), r['temper'])
        for i, key in enumerate(plan):
            r['ev'].append(dict(k='sys', id=key, at=t + minutes * MIN * 0.85 * (i + 1) / (len(plan) + 1), st='wait', by='sys'))
        _save(db, r, t, stage='in', room=room['id'], in_at=t, due_at=t + minutes * MIN)
        mr._notice(db, r['guest'], f'🔑 Đã nhận {room["name"]}. Chúc bạn nghỉ ngơi thật ngon!')
        if r['partner']:
            mr._notice(db, r['partner'], f'🔑 Hai bạn đã nhận {room["name"]}. Chúc nghỉ ngơi thật ngon!')
        out['room'] = room['name']
    _with_cost(store, sid, cost, f'🏨 Chi phí phòng khách · {room["name"]}', run)
    return f'Đã nhận phòng cho khách: {out.get("room", room["name"])}.' + (f' Chi {cost} xu.' if cost else '')


def _handle(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order', 'ev', 'pick'}, 'Thông tin không hợp lệ.')
    key = data.get('ev')
    need(isinstance(key, str) and ':' in key, 'Chọn tình huống cần xử lý.')
    kind, ident = key.split(':', 1)
    need(kind in ('sys', 'ask'), 'Chọn tình huống cần xử lý.')
    _, opt = _opt(_cat(kind), ident, data.get('pick'))
    out = {}

    def run(db):
        r = _locked(db, oid, sid, 'host', ('in',))
        _ripe(r, t)
        e = next((x for x in r['ev'] if x['k'] == kind and x['id'] == ident), None)
        need(e and e['st'] == 'open', 'Tình huống này đã xử lý rồi.', 'stale', 409)
        e.update(st='done', pick=opt[0], d=_mood(r, opt[2]), c=opt[3], reply=opt[5])
        if opt[4] == 'late' and not r['late']:
            r['late'] = LATE_MIN
        if opt[4] == 'upgrade':
            r['ev'].append(dict(k='room', id=r['room'], at=t, st='done', d=0, reply='⬆️ Phòng đã được nâng hạng.', by='sys'))
        _save(db, r, t)
        mr._notice(db, r['guest'] if e.get('by') != 'partner' or not r['partner'] else r['partner'], f'🏨 {opt[5]}')
        out['d'] = e['d']
    _with_cost(store, sid, opt[3], '🏨 Chi phí phục vụ khách', run)
    d = out.get('d', 0)
    return f'Đã xử lý. Hài lòng {"+" if d >= 0 else ""}{d}.' + (f' Chi {opt[3]} xu.' if opt[3] else '')


def _ask(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order', 'ask'}, 'Thông tin không hợp lệ.')
    ident = data.get('ask')
    need(ident in hc.ASKS, 'Chọn một yêu cầu nhé.', 'bad_ask')

    def run(db):
        r = _locked(db, oid, sid, 'guest', ('in',))
        need(int(r['asks']) < ASK_MAX, f'Mỗi lượt ở chỉ nhờ được {ASK_MAX} việc thôi.', 'ask_max', 409)
        need(not any(e['k'] == 'ask' and e['id'] == ident for e in r['ev']), 'Bạn đã nhờ việc này rồi.', 'already_done', 409)
        r['ev'].append(dict(k='ask', id=ident, at=t, st='open', by='guest' if sid == r['guest'] else 'partner'))
        _save(db, r, t, asks=int(r['asks']) + 1)
        mr._notice(db, r['host'], f'🛎️ Khách phòng {_room(r["career"], r["room"])["name"]}: {hc.ASKS[ident]["ask"]}.')
    store.transaction(run)
    return 'Đã nhắn chủ nhà. Chờ trả lời nhé.'


def _leave(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')

    def run(db):
        r = _locked(db, oid, sid, 'guest', ('in',))
        need(t >= float(r['in_at'] or 0) + MIN_STAY_MIN * MIN, f'Ở ít nhất {MIN_STAY_MIN} phút rồi hẵng trả phòng nhé.', 'too_soon', 409)
        if r['want_out']:
            return
        _save(db, r, t, want_out=1, due_at=min(float(r['due_at'] or t), t), late=0)
        mr._notice(db, r['host'], f'🧳 Khách phòng {_room(r["career"], r["room"])["name"]} muốn trả phòng.')
    store.transaction(run)
    return f'Đã báo chủ nhà. Chủ nhà làm thủ tục trả phòng (hoặc tự trả sau {GRACE_MIN} phút).'


def _checkout(store, sid, oid, data, t) -> str:
    need(set(data) <= {'order', 'pick'}, 'Thông tin không hợp lệ.')
    with store.connect() as db:
        r0 = _row(db, oid)
    need(r0 and r0['host'] == sid, 'Không tìm thấy lượt đặt phòng.', 'not_found', 404)
    key = _pick(oid, 'out', hc.CHECKOUT)
    _, opt = _opt(hc.CHECKOUT, key, data.get('pick'))
    out = {}

    def run(db):
        r = _locked(db, oid, sid, 'host', ('in',))
        need(r['want_out'] or _due(r) <= t, 'Khách chưa tới giờ trả phòng.', 'too_soon', 409)
        out['partner'], out['msg'] = _checkout_db(db, r, t, data.get('pick'), False)
        out['row'] = r
    _with_cost(store, sid, opt[3], '🏨 Chi phí trả phòng', run)
    _after_out(store, out['row'], out.get('partner') or '')
    return out['msg']


# ---------------------------------------------------------------- http
def get(store, token, state, sub: str, query: dict) -> dict:
    sid = sm._actor(store, token)
    need(sub in ('', 'view'), 'Không có mục này.', 'not_found', 404)
    return view(store, sid, state)
