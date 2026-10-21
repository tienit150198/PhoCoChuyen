"""💍 Đời sống vợ chồng (player feedback #442, #444; owner 21/10 "có đi thật luôn nhé, có chụp ảnh này kia luôn, thuê máy
bay du thuyền gì đó"; plan: docs/WEDDING_LIFE_PLAN.md). Three things a couple does together, both partners taking part:

* 🧺 Lễ rước dâu + lễ gia tiên (wl_rite_start / wl_rite_step / wl_rite_cancel, table wl_rites). An engaged couple
  whose plan is confirmed, or a married couple (married before this feature too), once per wedding
  (wedding_live.party_wedding), never while their live party is open. Whoever starts is the side that goes to fetch
  (lead), the other receives (host); the six steps of game/wedding_life_content.py RITE_STEPS alternate between them,
  each a choice of three (1-2 points, nobody fails), the two families as NPCs. Cost: free when the wedding plan has
  the lễ gia tiên (it was paid there), else its price; the mâm quả: the plan's lễ ăn hỏi trays, else 5 / 7 / 9 trays
  at the ăn hỏi prices. The starter pays (wallet, account or card: marriage._spend, never the joint fund) in the same
  transaction as the row. Cancelled (either partner), expired after RITE_DAYS or ended by a divorce: the fee goes back
  to the payer once (marriage_effects id 'wlr:rf:<rite>'). Done: happiness (couple_stats, past its day cap, up to
  HAPPY_MAX), tinh thần for both, a diary line, a photo in the couple album, a ticker line when both allowed news at the
  wedding. The live party's MC tells the guests about it (live/wedding.py reads RITE_SQL).
* ✈️ Đi chơi cùng nhau (wl_trip_propose / wl_trip_answer / wl_trip_cancel / wl_trip_pick, tables wl_trips, wl_photos).
  Married couples. A destination (C.DESTS: in the country, the four of 🌏 Làm việc ở nước ngoài, a private island one
  of them owns) and a ride: a ticket, a rented plane, a rented yacht (sea only), or a plane / yacht one of them owns
  (game/island.py vehicles: the garage's, Mua sắm's and the auction's numbered ones), which costs only the fuel. Who
  pays: the joint fund, half each, or the proposer. The proposer's part is taken at once (the fund through its ledger,
  ref UNIQUE; a wallet through an applied marriage_effects row); the partner's half when they accept, in the same
  transaction that sets the trip 'on' (status guard: one accept wins). Declined, cancelled, expired after TRIP_WAIT_H
  or a divorce before leaving: every part goes back where it came from, once (fixed ids). Once on its way the money
  is spent (a sink). The trip lasts DEST days; each day the partners take turns choosing one of three activities
  (seeded by the trip), a small surprise happens and the game's photo system draws a photo of the two of them
  (game/photo_studio.py render data, no image bytes) into the shared album. DAY_GAP real minutes between two days; a
  trip still on after TRIP_HOURS comes home by itself. Home: happiness, tinh thần, a diary line. One departure a
  Vietnam day per couple, one open trip at a time (partial unique index).
* 🏠 Sống chung (wl_chore_start / wl_chore_join, table wl_chores): việc nhà, đi chợ, nấu cơm, chăm con (with a shared
  child). One partner asks and takes a part, the other joins with another part; once a kind a Vietnam day. Free: the
  happiness of a moment (couple._grow, its day cap), +1 tinh thần each, a diary line; the child a little happier.

Money: never from one player to another; every xu is spent (burned) or given back exactly to whoever paid (a fund
part to the fund). Every request carries a rid: a retried tap pays once. No coins are ever paid out.
Privacy: only the two of them see the album and the trip; a block between them (Hôn nhân or chat) stops new asks.
Tables (game/pg_schema.py SCHEMA_VERSION 83): new ones only, no save key: 2.5.1 never reads them; the refunds a rollback
leaves are marriage_effects 'wallet' rows every build applies.
"""
from __future__ import annotations

import datetime
import json
import random
import secrets
import time

from . import couple as cp
from . import marriage as mr
from . import price_index as pi
from . import wedding_content as W
from . import wedding_life_content as C

RITE_DAYS = 3                   # an unfinished ceremony is called off (and refunded) after this many days
RITE_HAPPY, RITE_SPIRIT = 8, 2
TRIP_WAIT_H = 48                # a proposed trip waits this long for the partner's answer
TRIP_HOURS = 72                 # a trip still on after this comes home by itself
DAY_GAP = 15 * 60               # real seconds between two trip days ("đi thật": a day of the trip is not a tap)
TRIP_HAPPY = dict(vn=6, abroad=10, island=8)
TRIP_SPIRIT = 3
CHORE_POINTS, CHORE_SPIRIT = 2, 1
ALBUM_PAGE = 24
KIND = 'life'                   # wallet history kind (journey.HISTORY_KINDS)
DEST = {d['id']: d for d in C.DESTS}
RIDE = {r[0]: dict(id=r[0], emoji=r[1], name=r[2]) for r in C.RIDES}
STEP = {s['id']: s for s in C.RITE_STEPS}
PAY_BY = ('fund', 'split', 'me')
OPEN = ('proposed', 'on')
VN = datetime.timezone(datetime.timedelta(hours=7))


def need(ok, message, code='wedlife', status=400):
    mr.need(ok, message, code, status)


def vn_day(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(mr.now() if t is None else t, VN).strftime('%Y-%m-%d')


def _rid(d: dict) -> str:
    return mr._rid(d)[:40]


def _j(raw, default):
    try:
        v = json.loads(raw) if raw else default
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _replayed(store, table: str, ref: str) -> bool:
    """A request id already used (a retried tap): answered as done, nothing paid again."""
    with store.connect() as db:
        return bool(db.execute(f'SELECT 1 FROM {table} WHERE ref=?', (ref,)).fetchone())


def _blocked(db, a: str, b: str) -> bool:
    from . import work_visits as wv
    return wv._blocked(db, a, b)


def _couple(db, sid: str, married: bool = True) -> dict:
    c = mr._bond(db, sid)
    if married:
        need(c and c['status'] == 'married', 'Chỉ vợ chồng đã cưới mới dùng được mục này.', 'not_married', 409)
    else:
        need(c and c['status'] in ('engaged', 'married'), 'Hai bạn cần đính hôn trước đã.', 'not_engaged', 409)
    need(not _blocked(db, c['a'], c['b']), 'Hai bạn đang chặn nhau nên chưa rủ nhau được.', 'blocked', 403)
    return c


def _same(db, c: dict, sid: str) -> None:
    cur = mr._bond(db, sid)
    need(cur and cur['id'] == c['id'] and cur['status'] in ('engaged', 'married'), 'Hai bạn không còn là một đôi.', 'not_married', 409)


def _pay_fn(eid: str, sid: str, amount: int, label: str, how):
    """The payer's save: the amount through the Hôn nhân purchase path (cash, account or card; never the joint fund)."""
    def fn(s):
        need(mr._can_spend(s, amount, how), f'Ví của bạn chưa đủ {mr._xu(amount)} xu.', 'not_enough')
        mr._spend(s, mr._effect(eid, sid, 'wallet', -amount, label), how)
    return fn


def _spirit_fn(n: int, also=None):
    def fn(s):
        if also:
            also(s)
        j = s.get('journey')
        if isinstance(j, dict) and j.get('story'):
            from . import needs as nd
            nd._spirit(s, n)
    return fn


def _jailed(state) -> bool:
    from . import jail
    return bool(state) and jail.jailed(state)


def _happy(db, cid: int, n: int) -> int:
    """Happiness for a ceremony or a trip: past the day cap of the moments, never past HAPPY_MAX."""
    db.execute('INSERT INTO couple_stats(couple) VALUES(?) ON CONFLICT DO NOTHING', (cid,))
    st = mr._row(db, 'SELECT happy FROM couple_stats WHERE couple=? FOR UPDATE', (cid,))
    new = min(cp.HAPPY_MAX, int(st['happy']) + n)
    db.execute('UPDATE couple_stats SET happy=? WHERE couple=?', (new, cid))
    return new - int(st['happy'])


def _settle(store, *sids) -> None:
    cp._settle_quietly(store, *sids)


def _snap(store, sid: str) -> dict:
    """The two of them as the photo system draws them (game/photo_studio.py snapshot_for: looks from both saves)."""
    try:
        from . import photo_studio as ps
        return ps.snapshot_for(store, sid, dict(pkg='doi', mate=True))
    except Exception:  # noqa: BLE001 - a save that cannot be read: the names only, drawn in the default look
        with store.connect() as db:
            c = mr._bond(db, sid)
            other = mr._other(c, sid) if c else ''
            return dict(v=1, pkg='doi', me=dict(n=mr._display(db, sid)[:24], g='none', lk={}),
                        mate=dict(n=mr._display(db, other)[:24] if other else '', g='none', lk={}), isl=False)


def _photo(db, cid: int, src: str, snap: dict, act: dict, head: str, sub: str, frame: str, t: float) -> None:
    data = dict(v=1, pkg='doi', snap=snap, q='good', rt=dict(sang=0, am=1, min=1, vig=1), by='',
                set=dict(bd=act['bd'], light=act['light'], frame=frame, pose=act['pose'], face=act['face'], prop=act['prop']),
                day=datetime.datetime.fromtimestamp(t, VN).strftime('%d.%m.%y'), head=head[:40], sub=sub[:60])
    db.execute('INSERT INTO wl_photos(id, couple, src, data, at) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING',
               ('wl' + secrets.token_hex(8), cid, src[:64], json.dumps(data, ensure_ascii=False, separators=(',', ':')), t))


# ---------------------------------------------------------------- 🧺 lễ rước dâu + lễ gia tiên
def _rite_quote(plan: dict, trays) -> tuple[int, int, int]:
    """(trays, fee, cost of the trays) for a wedding plan and the trays asked for."""
    cer = plan.get('ceremonies') if isinstance(plan.get('ceremonies'), dict) else {}
    fee = 0 if cer.get('gia_tien') else W.CEREMONY_INDEX['gia_tien']['price']
    have = cer.get('an_hoi') if type(cer.get('an_hoi')) is int else 0
    if have:
        return have, fee, 0
    need(trays in C.RITE_TRAYS, 'Chọn số mâm quả nhé.', 'bad_trays')
    return trays, fee, next(x for n, x, _ in W.CEREMONY_INDEX['an_hoi']['options'] if n == trays)


def _grade(score: int) -> str:
    return next(label for cut, label in C.RITE_GRADES if score >= cut)


def _fill(text: str, a: str, b: str) -> str:
    return text.replace('{a}', a).replace('{b}', b)


@cp._once
def rite_start(store, sid, display, d):
    with store.connect() as db:
        c = _couple(db, sid, married=False)
        from . import wedding_live as wl
        w = wl.party_wedding(db, c)
        need(w, 'Hai bạn cần chốt kế hoạch cưới trước đã.', 'no_wedding', 409)
        party = wl.party_view(db, c, mr.now())
        need(not party or party['state'] != 'live', 'Tiệc cưới đang diễn ra. Làm lễ sau tiệc nhé.', 'party_live', 409)
        plan = _j(w['plan'], {})
        lead_name = display
        host_name = mr._display(db, mr._other(c, sid))
    trays, fee, tray_cost = _rite_quote(plan, d.get('trays'))
    cost = fee + tray_cost
    how = d.get('pay')
    rid = _rid(d)
    eid = f'wlr:{c["id"]}:{rid}'
    if _replayed(store, 'wl_rites', eid):
        return dict(message='Việc này đã làm xong rồi.', changed=False)
    snap = _snap(store, sid)
    t = mr.now()

    def ops(db):
        _same(db, c, sid)
        need(not db.execute("SELECT 1 FROM wl_rites WHERE couple=? AND status='on'", (c['id'],)).fetchone(),
             'Lễ của hai bạn đang diễn ra rồi.', 'busy', 409)
        need(not db.execute("SELECT 1 FROM wl_rites WHERE wedding=? AND status='done'", (w['id'],)).fetchone(),
             'Hai bạn đã làm lễ rước dâu rồi.', 'done', 409)
        if cost:
            mr._insert_effects(db, [mr._effect(eid, sid, 'wallet', -cost, 'Lễ rước dâu, lễ gia tiên')], 'applied')
        r = db.execute('INSERT INTO wl_rites(couple, wedding, a, lead, status, step, trays, fee, payer, picks, score, snap, ref, created, updated) '
                       "VALUES(?,?,?,?,'on',0,?,?,?,'[]',0,?,?,?,?) RETURNING id",
                       (c['id'], w['id'], c['a'], sid, trays, cost, sid if cost else '', json.dumps(snap, ensure_ascii=False), eid, t, t)).fetchone()
        mr._notice(db, mr._other(c, sid), f'🧺 {lead_name} chuẩn bị {trays} mâm quả sang rước dâu! Mở Hôn nhân › Lễ rước dâu để cùng làm lễ nha.')
        return r['id']
    if cost:
        mr._mutate_retry(store, {sid: _pay_fn(eid, sid, cost, 'Lễ rước dâu, lễ gia tiên', how)}, ops)
    else:
        store.transaction(ops)
    return dict(message=f'Bắt đầu lễ rước dâu với {trays} mâm quả. Bước đầu là của bạn, sau đó tới lượt {host_name}.', changed=bool(cost))


def _rite_refund(db, r: dict, status: str) -> list:
    """Inside a transaction: the rite ends (status guard) and its fee goes back to the payer once. The sids to settle."""
    if db.execute("UPDATE wl_rites SET status=?, updated=? WHERE id=? AND status='on'", (status, mr.now(), r['id'])).rowcount != 1:
        return []
    if int(r['fee']) > 0 and r['payer']:
        mr._insert_effects(db, [mr._effect(f'wlr:rf:{r["id"]}', r['payer'], 'wallet', int(r['fee']), 'Hoàn tiền lễ rước dâu')])
        return [r['payer']]
    return []


def rite_cancel(store, sid, display, d):
    rid = d.get('rite')
    need(type(rid) is int, 'Lễ không hợp lệ.')

    def run(db):
        c = mr._bond(db, sid)
        need(c, 'Hai bạn không còn là một đôi.', 'not_married', 409)
        r = mr._row(db, "SELECT * FROM wl_rites WHERE id=? AND couple=? AND status='on' FOR UPDATE", (rid, c['id']))
        need(r, 'Lễ này đã khép lại rồi.', 'gone', 409)
        paid = _rite_refund(db, r, 'cancelled')
        mr._notice(db, mr._other(c, sid), f'🧺 {display} đã hoãn lễ rước dâu. Hai bạn làm lại khi nào sẵn sàng nhé.')
        return paid
    paid = store.transaction(run)
    _settle(store, *paid)
    return dict(message='Đã hoãn lễ.' + (' Tiền lễ đã hoàn về ví người trả.' if paid else ''), changed=bool(paid))


def rite_step(store, sid, display, d):
    rid, n, pick = d.get('rite'), d.get('step'), d.get('pick')
    need(type(rid) is int and type(n) is int and isinstance(pick, str), 'Lựa chọn không hợp lệ.')
    with store.connect() as db:
        c = mr._bond(db, sid)
        need(c, 'Hai bạn không còn là một đôi.', 'not_married', 409)
        r = mr._row(db, 'SELECT * FROM wl_rites WHERE id=? AND couple=?', (rid, c['id']))
        need(r, 'Không tìm thấy lễ này.', 'gone', 404)
        picks = _j(r['picks'], [])
        if n < len(picks) and picks[n] == pick:
            return dict(message='Bước này đã xong rồi.', changed=False)
        need(r['status'] == 'on', 'Lễ này đã khép lại rồi.', 'gone', 409)
        need(n == len(picks) and n < len(C.RITE_STEPS), 'Bước này đã qua rồi. Xem lại nhé.', 'stale', 409)
        st = C.RITE_STEPS[n]
        actor = r['lead'] if st['side'] == 'lead' else mr._other(c, r['lead'])
        need(actor == sid, 'Bước này là của người ấy. Chờ một chút nhé.', 'not_your_turn', 409)
        opt = next((o for o in st['options'] if o['id'] == pick), None)
        need(opt, 'Chọn một cách làm nhé.', 'bad_pick')
        lead_name, host_name = mr._display(db, r['lead']), mr._display(db, mr._other(c, r['lead']))
        w = mr._row(db, 'SELECT announce_a, announce_b FROM weddings WHERE id=?', (r['wedding'],))
    last = n + 1 == len(C.RITE_STEPS)
    score = int(r['score']) + int(opt['pts'])
    other = mr._other(c, sid)
    reply = _fill(opt['reply'], lead_name, host_name)

    def ops(db):
        cur = mr._row(db, 'SELECT step, status FROM wl_rites WHERE id=? FOR UPDATE', (rid,))
        need(cur and cur['status'] == 'on' and int(cur['step']) == n, 'Bước này vừa có người chọn. Xem lại nhé.', 'stale', 409)
        t = mr.now()
        db.execute('UPDATE wl_rites SET step=?, picks=?, score=?, status=?, updated=?, done_at=? WHERE id=?',
                   (n + 1, json.dumps(picks + [pick]), score, 'done' if last else 'on', t, t if last else None, rid))
        if not last:
            nxt = C.RITE_STEPS[n + 1]
            mr._notice(db, other, f'{st["emoji"]} {display}: {_fill(opt["text"], lead_name, host_name)} Tới bước “{nxt["title"]}”'
                                  + (' của bạn nha!' if (nxt['side'] == 'lead') == (other == r['lead']) else '.'))
            return 0
        added = _happy(db, c['id'], RITE_HAPPY)
        grade = _grade(score)
        cp._moment(db, c, r['lead'], 'rite', f'🧺 Lễ rước dâu {r["trays"]} mâm quả, lễ gia tiên: {grade}', f'wlr:done:{rid}')
        _photo(db, c['id'], f'r:{rid}', _j(r['snap'], {}), dict(bd='cuoi', light='mem', pose='nam_tay', face='cuoi_hip', prop='hoa'),
               '🕯️ Lễ gia tiên', f'Họ nhà {lead_name} sang rước dâu', 'toan', t)
        if w and w['announce_a'] and w['announce_b']:
            mr._post_news(db, 'rite', f'rite:{rid}', f'🧺 Họ nhà {lead_name} vừa sang rước dâu nhà {host_name}: {r["trays"]} mâm quả, lễ gia tiên trọn vẹn!',
                          c['a'], c['b'])
        mr._notice(db, other, f'🕯️ Lễ rước dâu và lễ gia tiên đã xong: {grade}. Ảnh đã vào album của hai bạn.')
        return added
    if last:
        added = mr._mutate_retry(store, {c['a']: _spirit_fn(RITE_SPIRIT), c['b']: _spirit_fn(RITE_SPIRIT)}, ops)['db']
        return dict(message=f'{reply} Lễ đã xong: {_grade(score)}.' + (f' (+{added} điểm hạnh phúc)' if added else ''), changed=True)
    store.transaction(ops)
    return dict(message=reply, changed=False)


def _rite_view(db, c: dict, sid: str, t: float) -> dict | None:
    from . import wedding_live as wl
    w = wl.party_wedding(db, c)
    if not w:
        return None
    plan = _j(w['plan'], {})
    cer = plan.get('ceremonies') if isinstance(plan.get('ceremonies'), dict) else {}
    have = cer.get('an_hoi') if type(cer.get('an_hoi')) is int else 0
    fee = 0 if cer.get('gia_tien') else W.CEREMONY_INDEX['gia_tien']['price']
    out = dict(state='none', fee=fee, trays_fixed=have or None,
               trays=[dict(n=n, price=0 if have else x) for n, x, _ in W.CEREMONY_INDEX['an_hoi']['options']])
    party = wl.party_view(db, c, t)
    out['party_live'] = bool(party and party['state'] == 'live')
    r = mr._row(db, "SELECT * FROM wl_rites WHERE couple=? AND (status='on' OR (status='done' AND wedding=?)) ORDER BY id DESC LIMIT 1", (c['id'], w['id']))
    if not r:
        return out
    lead = r['lead']
    host = mr._other(c, lead)
    a, b = mr._display(db, lead), mr._display(db, host)
    picks = _j(r['picks'], [])
    steps = []
    for i, s in enumerate(C.RITE_STEPS):
        who = lead if s['side'] == 'lead' else host
        got = next((o for o in s['options'] if i < len(picks) and o['id'] == picks[i]), None)
        steps.append(dict(id=s['id'], emoji=s['emoji'], title=s['title'], who=_fill(s['who'], a, b), line=_fill(s['line'], a, b), mine=who == sid,
                          by=a if s['side'] == 'lead' else b, options=[dict(id=o['id'], text=_fill(o['text'], a, b)) for o in s['options']],
                          picked=dict(id=got['id'], text=_fill(got['text'], a, b), reply=_fill(got['reply'], a, b)) if got else None))
    out.update(state=r['status'], id=r['id'], step=int(r['step']), steps=steps, lead=dict(name=a, me=lead == sid), host=dict(name=b, me=host == sid),
               trays=int(r['trays']), paid=int(r['fee']), score=int(r['score']), grade=_grade(int(r['score'])) if r['status'] == 'done' else None,
               expires=int(r['created'] + RITE_DAYS * mr.DAY), my_turn=r['status'] == 'on' and int(r['step']) < len(steps) and steps[int(r['step'])]['mine'])
    return out


# ---------------------------------------------------------------- ✈️ đi chơi cùng nhau
def _price(dest: dict, ride: str, arrive: str | None = None) -> int:
    if ride == 've':
        return pi.price(dest['base'])
    if ride == 'nha':
        k = 'thue_thuyen' if arrive == 'boat' else 'thue_bay'
        return max(1, pi.price(C.RENT[k].get(dest['kind'], C.RENT['thue_bay'][dest['kind']])) // C.FUEL_DIV)
    return pi.price(C.RENT[ride][dest['kind']])


def _fits(dest: dict, ride: str, arrive: str | None = None) -> str | None:
    """Why this ride cannot go there (None: it can)."""
    if ride == 'thue_thuyen' and (not dest['sea'] or dest['kind'] not in C.RENT['thue_thuyen']):
        return 'Du thuyền chỉ đi được nơi có biển trong nước.'
    if ride == 'nha':
        if arrive == 'boat' and not dest['sea']:
            return 'Du thuyền chỉ đi được nơi có biển.'
        if arrive == 'heli' and dest['kind'] == 'abroad':
            return 'Trực thăng không bay ra nước ngoài được.'
    return None


def _assets(store, c: dict) -> dict:
    """{islands: [{id, name, emoji, owner}], vehicles: [{id, name, emoji, arrive, owner}]} of both saves."""
    from . import island as isl
    out = dict(islands=[], vehicles=[])
    for side in ('a', 'b'):
        got = mr._read_state(store, c[side])
        if not got:
            continue
        s = got[0]
        for iid in isl.owned(s):
            it = isl.ISLAND[iid]
            out['islands'].append(dict(id=iid, name=it['name'], emoji=it['emoji'], owner=side))
        for v in isl.vehicles(s):
            out['vehicles'].append(dict(id=v['id'], name=v['name'], emoji=v['emoji'], arrive=v['arrive'], owner=side))
    return out


def _options(trip_id: int, dest: str, day: int) -> list:
    acts = list(C.ACTIVITIES[dest])
    return random.Random(f'wl|{trip_id}|{day}').sample(acts, 3)


def _event(trip_id: int, day: int, a: str, b: str) -> str:
    return _fill(random.Random(f'wl-ev|{trip_id}|{day}').choice(C.EVENTS), a, b)


def _trip_refund(db, t: dict, status: str) -> list:
    """Inside a transaction: a trip that has not left ends (status guard) and every part goes back where it came from,
    once (the fund through its ledger ref, a wallet through a fixed effect id). The sids to settle."""
    if db.execute('UPDATE wl_trips SET status=?, ended=? WHERE id=? AND status=?', (status, mr.now(), t['id'], 'proposed')).rowcount != 1:
        return []
    paid = []
    if int(t['paid_fund']) > 0:
        c = mr._row(db, 'SELECT * FROM couples WHERE id=? FOR SHARE', (t['couple'],))   # the lock order of couple._lock_fund
        if c and c['status'] == 'married':
            db.execute('INSERT INTO joint_funds(couple,balance,updated) VALUES(?,0,?) ON CONFLICT DO NOTHING', (t['couple'], mr.now()))
            db.execute('SELECT balance FROM joint_funds WHERE couple=? FOR UPDATE', (t['couple'],)).fetchone()
            db.execute('UPDATE joint_funds SET balance=balance+?,updated=? WHERE couple=?', (int(t['paid_fund']), mr.now(), t['couple']))
            bal = cp._balance(db, t['couple'])
            db.execute("INSERT INTO joint_ledger(couple,sid,kind,amount,balance,label,ref,status,at) VALUES(?,?,'refund',?,?,?,?,'done',?)",
                       (t['couple'], t['proposer'], int(t['paid_fund']), bal, 'Hoàn tiền chuyến đi chơi', f'wlt:rf:{t["id"]}', mr.now()))
        else:   # the fund was split meanwhile: whoever proposed gets it back
            mr._insert_effects(db, [mr._effect(f'wlt:rf:{t["id"]}:f', t['proposer'], 'wallet', int(t['paid_fund']), 'Hoàn tiền chuyến đi chơi')])
            paid.append(t['proposer'])
    for side in ('a', 'b'):
        if int(t['paid_' + side]) > 0:
            mr._insert_effects(db, [mr._effect(f'wlt:rf:{t["id"]}:{side}', t[side], 'wallet', int(t['paid_' + side]), 'Hoàn tiền chuyến đi chơi')])
            paid.append(t[side])
    return paid


@cp._once
def trip_propose(store, sid, display, d):
    dest_id, ride, pay_by, vid = d.get('dest'), d.get('ride'), d.get('pay_by'), d.get('vehicle') or ''
    need(dest_id in DEST, 'Chọn nơi muốn đi nhé.', 'bad_dest')
    need(ride in RIDE, 'Chọn cách đi nhé.', 'bad_ride')
    need(pay_by in PAY_BY, 'Chọn ai trả tiền nhé.', 'bad_pay')
    need(isinstance(vid, str) and len(vid) <= 24, 'Chọn phương tiện nhé.', 'bad_ride')
    dest = DEST[dest_id]
    with store.connect() as db:
        c = _couple(db, sid)
        other = mr._other(c, sid)
        name = mr._display(db, other)
    got = mr._read_state(store, sid)
    need(got and (got[0].get('journey') or {}).get('story'), 'Đi chơi chỉ có trong hành trình.', 'locked', 403)
    need(not _jailed(got[0]), 'Đang ở trại tạm giữ, ra rồi hẵng đi chơi nha.', 'jailed', 403)
    assets = _assets(store, c)
    if dest['kind'] == 'island':
        need(assets['islands'], 'Hai bạn chưa có đảo riêng nào.', 'no_island', 409)
    arrive = None
    if ride == 'nha':
        v = next((x for x in assets['vehicles'] if x['id'] == vid), None)
        need(v, 'Hai bạn chưa có máy bay hay du thuyền này.', 'not_owned', 409)
        arrive = v['arrive']
    else:
        vid = ''
    why = _fits(dest, ride, arrive)
    need(not why, why or '', 'bad_ride')
    price = _price(dest, ride, arrive)
    side = mr._side(c, sid)
    mine = price if pay_by == 'me' else (price + 1) // 2 if pay_by == 'split' else 0
    fund = price if pay_by == 'fund' else 0
    rid = _rid(d)
    ref = f'wlt:{c["id"]}:{rid}'
    if _replayed(store, 'wl_trips', ref):
        return dict(message='Việc này đã làm xong rồi.', changed=False)
    t = mr.now()
    label = f'Đi chơi {dest["name"]} ({RIDE[ride]["name"].lower()})'

    def ops(db):
        _same(db, c, sid)
        need(not db.execute("SELECT 1 FROM wl_trips WHERE couple=? AND status IN ('proposed','on')", (c['id'],)).fetchone(),
             'Hai bạn đang có một chuyến đi rồi.', 'busy', 409)
        need(not db.execute("SELECT 1 FROM wl_trips WHERE couple=? AND day=? AND status IN ('on','done')", (c['id'], vn_day(t))).fetchone(),
             'Hôm nay hai bạn vừa đi chơi rồi. Mai đi tiếp nha!', 'today', 409)
        if fund:
            cp._fund_move(db, c['id'], sid, 'spend', fund, label, ref)
            mr._notice(db, other, f'🏦 {display} giữ {mr._xu(fund)} xu từ quỹ chung cho chuyến đi {dest["name"]}.')
        if mine:
            mr._insert_effects(db, [mr._effect(ref, sid, 'wallet', -mine, label)], 'applied')
        r = db.execute('INSERT INTO wl_trips(couple, a, b, proposer, dest, ride, vehicle, pay_by, price, paid_a, paid_b, paid_fund, status, days, picks, '
                       "ref, created, day) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'proposed',?,'[]',?,?,'') RETURNING id",
                       (c['id'], c['a'], c['b'], sid, dest_id, ride, vid, pay_by, price, mine if side == 'a' else 0, mine if side == 'b' else 0,
                        fund, dest['days'], ref, t)).fetchone()
        mr._notice(db, other, f'✈️ {display} rủ bạn đi {dest["name"]} ({RIDE[ride]["name"].lower()}). Mở Hôn nhân › Sống chung để trả lời nha!')
        return r['id']
    if mine:
        mr._mutate_retry(store, {sid: _pay_fn(ref, sid, mine, label, d.get('pay'))}, ops)
    else:
        store.transaction(ops)
    paid = f'Đã giữ {mr._xu(fund or mine)} xu' + (' từ quỹ chung' if fund else '') + '. ' if fund or mine else ''
    return dict(message=f'Đã rủ {name} đi {dest["name"]}. {paid}Người ấy đồng ý là lên đường!', changed=bool(mine))


@cp._once
def trip_answer(store, sid, display, d):
    tid, answer = d.get('trip'), d.get('answer')
    need(type(tid) is int and answer in ('accept', 'decline'), 'Trả lời không hợp lệ.')
    with store.connect() as db:
        c = mr._bond(db, sid)
        need(c and c['status'] == 'married', 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        t = mr._row(db, "SELECT * FROM wl_trips WHERE id=? AND couple=?", (tid, c['id']))
        need(t, 'Không tìm thấy chuyến đi này.', 'gone', 404)
        if answer == 'accept' and t['status'] in ('on', 'done') and t['proposer'] != sid:
            return dict(message='Hai bạn đã lên đường rồi.', changed=False)
        need(t['status'] == 'proposed' and t['proposer'] != sid, 'Lời rủ này không còn chờ bạn trả lời.', 'gone', 409)
        need(t['created'] > mr.now() - TRIP_WAIT_H * 3600, 'Lời rủ này đã hết hạn.', 'expired', 409)
        name = mr._display(db, t['proposer'])
        if answer == 'accept':
            need(not _blocked(db, c['a'], c['b']), 'Hai bạn đang chặn nhau nên chưa đi cùng được.', 'blocked', 403)
    dest = DEST[t['dest']]
    if answer == 'decline':
        def no(db):
            r = mr._row(db, 'SELECT * FROM wl_trips WHERE id=? FOR UPDATE', (tid,))
            need(r['status'] == 'proposed', 'Lời rủ này không còn chờ bạn trả lời.', 'gone', 409)
            paid = _trip_refund(db, r, 'declined')
            mr._notice(db, t['proposer'], f'✈️ {display} chưa đi {dest["name"]} được lần này. Tiền đã giữ được hoàn lại.')
            return paid
        _settle(store, *store.transaction(no))
        return dict(message='Đã trả lời. Hẹn chuyến sau nhé!', changed=False)
    got = mr._read_state(store, sid)
    need(got and (got[0].get('journey') or {}).get('story'), 'Đi chơi chỉ có trong hành trình.', 'locked', 403)
    need(not _jailed(got[0]), 'Đang ở trại tạm giữ, ra rồi hẵng đi chơi nha.', 'jailed', 403)
    side = mr._side(c, sid)
    share = int(t['price']) - int(t['paid_a']) - int(t['paid_b']) - int(t['paid_fund'])
    snap = _snap(store, t['proposer'])
    now = mr.now()
    eid = f'wlt:{tid}:acc:{side}'
    label = f'Đi chơi {dest["name"]} (phần của bạn)'

    def ops(db):
        _same(db, c, sid)
        need(not db.execute("SELECT 1 FROM wl_trips WHERE couple=? AND day=? AND status IN ('on','done')", (c['id'], vn_day(now))).fetchone(),
             'Hôm nay hai bạn vừa đi chơi rồi. Mai đi tiếp nha!', 'today', 409)
        if share > 0:
            mr._insert_effects(db, [mr._effect(eid, sid, 'wallet', -share, label)], 'applied')
        need(db.execute(f"UPDATE wl_trips SET status='on', started=?, last_at=?, day=?, snap=?, paid_{side}=paid_{side}+? "
                        "WHERE id=? AND status='proposed'", (now, now, vn_day(now), json.dumps(snap, ensure_ascii=False), max(0, share), tid)).rowcount == 1,
             'Lời rủ này không còn chờ bạn trả lời.', 'gone', 409)
        cp._moment(db, c, sid, 'trip', f'✈️ Lên đường đi {dest["name"]}! ' + _ride_line(t), f'wlt:go:{tid}')
        mr._notice(db, t['proposer'], f'✈️ {display} đồng ý rồi! Hai bạn lên đường đi {dest["name"]}. Ngày 1 bạn chọn đi đâu nha.')
    if share > 0:
        mr._mutate_retry(store, {sid: _pay_fn(eid, sid, share, label, d.get('pay'))}, ops)
    else:
        store.transaction(ops)
    return dict(message=f'Lên đường đi {dest["name"]} cùng {name}! ' + _ride_line(t), changed=share > 0)


def _ride_line(t: dict) -> str:
    if t['ride'] == 'nha':
        from . import island_content as IC
        arrive = (IC.SEATS.get(t['vehicle']) or ('', 'plane'))[1]
        return C.RIDE_LINES['nha_boat' if arrive == 'boat' else 'nha_plane']
    if t['ride'] == 've' and t['dest'] == 'dao_rieng':
        return C.RIDE_LINES['island']
    return C.RIDE_LINES[t['ride']]


def trip_cancel(store, sid, display, d):
    tid = d.get('trip')
    need(type(tid) is int, 'Chuyến đi không hợp lệ.')

    def run(db):
        c = mr._bond(db, sid)
        need(c, 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        t = mr._row(db, "SELECT * FROM wl_trips WHERE id=? AND couple=? AND proposer=? FOR UPDATE", (tid, c['id'], sid))
        need(t and t['status'] == 'proposed', 'Chuyến này không còn hủy được.', 'gone', 409)
        paid = _trip_refund(db, t, 'cancelled')
        mr._notice(db, mr._other(c, sid), f'✈️ {display} đã hủy lời rủ đi {DEST[t["dest"]]["name"]}.')
        return paid
    paid = store.transaction(run)
    _settle(store, *paid)
    return dict(message='Đã hủy chuyến đi. Tiền đã giữ được hoàn lại đúng nơi đã trả.', changed=bool(paid))


def _day_done(db, c: dict, t: dict, n: int, act: dict, names: dict, at: float) -> None:
    """A trip day: its pick, the photo, the diary line (inside the trip row's lock)."""
    dest = DEST[t['dest']]
    _photo(db, c['id'], f't:{t["id"]}:{n}', _j(t['snap'], {}), act, f'{dest["emoji"]} {dest["name"]} · Ngày {n + 1}',
           act['text'], 'toan' if n % 2 == 0 else 'nua', at)


def trip_pick(store, sid, display, d):
    tid, n, pick = d.get('trip'), d.get('day'), d.get('pick')
    need(type(tid) is int and type(n) is int and isinstance(pick, str), 'Lựa chọn không hợp lệ.')
    with store.connect() as db:
        c = mr._bond(db, sid)
        need(c and c['status'] == 'married', 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        t = mr._row(db, 'SELECT * FROM wl_trips WHERE id=? AND couple=?', (tid, c['id']))
        need(t, 'Không tìm thấy chuyến đi này.', 'gone', 404)
        picks = _j(t['picks'], [])
        if n < len(picks) and picks[n] == pick:
            return dict(message='Ngày này đã chọn rồi.', changed=False)
        need(t['status'] == 'on', 'Chuyến đi này đã kết thúc.', 'gone', 409)
        need(n == len(picks) and n < int(t['days']), 'Ngày này đã qua rồi. Xem lại nhé.', 'stale', 409)
        chooser = t['proposer'] if n % 2 == 0 else mr._other(c, t['proposer'])
        need(chooser == sid, 'Hôm nay tới lượt người ấy chọn. Chờ một chút nhé.', 'not_your_turn', 409)
        opens = float(t['last_at'] or t['started']) + (DAY_GAP if n else 0)
        need(mr.now() >= opens, f'Ngày {n + 1} bắt đầu lúc {datetime.datetime.fromtimestamp(opens, VN).strftime("%H:%M")}. Nghỉ ngơi chút đã!', 'too_soon', 409)
        act = next((x for x in _options(tid, t['dest'], n) if x['id'] == pick), None)
        need(act, 'Chọn một hoạt động nhé.', 'bad_pick')
        names = dict(a=mr._display(db, t['proposer']), b=mr._display(db, mr._other(c, t['proposer'])))
    dest = DEST[t['dest']]
    last = n + 1 == int(t['days'])
    other = mr._other(c, sid)
    event = _event(tid, n, names['a'], names['b'])

    def ops(db):
        cur = mr._row(db, 'SELECT * FROM wl_trips WHERE id=? FOR UPDATE', (tid,))
        need(cur and cur['status'] == 'on' and len(_j(cur['picks'], [])) == n, 'Ngày này vừa có người chọn. Xem lại nhé.', 'stale', 409)
        at = mr.now()
        db.execute('UPDATE wl_trips SET picks=?, last_at=?, status=?, ended=? WHERE id=?',
                   (json.dumps(picks + [pick]), at, 'done' if last else 'on', at if last else None, tid))
        _day_done(db, c, cur, n, act, names, at)
        cp._moment(db, c, sid, 'trip', f'{act["emoji"]} Ngày {n + 1} ở {dest["name"]}: {act["text"]}. {event}', f'wlt:d:{tid}:{n}')
        if not last:
            mr._notice(db, other, f'{act["emoji"]} {display} chọn: {act["text"]}. Ngày {n + 2} tới lượt bạn chọn nha!' if n % 2 == 0
                       else f'{act["emoji"]} {display} chọn: {act["text"]}. Ngày {n + 2} người ấy chọn tiếp.')
            return 0
        added = _happy(db, c['id'], TRIP_HAPPY[dest['kind']])
        cp._moment(db, c, sid, 'trip', f'🏡 Về nhà sau {t["days"]} ngày ở {dest["name"]}. Album có thêm {t["days"]} tấm ảnh đôi.', f'wlt:home:{tid}')
        mr._notice(db, other, f'🏡 Chuyến đi {dest["name"]} đã xong! Xem lại ảnh trong album của hai bạn nha.')
        return added
    if last:
        added = mr._mutate_retry(store, {c['a']: _spirit_fn(TRIP_SPIRIT), c['b']: _spirit_fn(TRIP_SPIRIT)}, ops)['db']
        return dict(message=f'{act["text"]}. {event} Chuyến đi đã xong, về nhà thôi!' + (f' (+{added} điểm hạnh phúc)' if added else ''), changed=True)
    store.transaction(ops)
    return dict(message=f'{act["text"]}. {event}', changed=False)


def _trip_view(db, t: dict, c: dict, sid: str, now: float) -> dict:
    dest = DEST.get(t['dest']) or DEST['da_lat']
    picks = _j(t['picks'], [])
    n = len(picks)
    a, b = mr._display(db, t['proposer']), mr._display(db, mr._other(c, t['proposer']))
    out = dict(id=t['id'], status=t['status'], dest=dict(id=dest['id'], emoji=dest['emoji'], name=dest['name'], kind=dest['kind']),
               ride=dict(RIDE[t['ride']], vehicle=_vehicle_name(t['vehicle'])), pay_by=t['pay_by'], price=int(t['price']),
               mine=t['proposer'] == sid, proposer=a, partner=b, days=int(t['days']), day=n, created=int(t['created']),
               expires=int(t['created'] + TRIP_WAIT_H * 3600), paid_fund=int(t['paid_fund']),
               paid_me=int(t['paid_' + mr._side(c, sid)]), line=_ride_line(t))
    hist = []
    for i, p in enumerate(picks):
        act = next((x for x in C.ACTIVITIES[dest['id']] if x['id'] == p), None)
        if act:
            hist.append(dict(day=i + 1, emoji=act['emoji'], text=act['text'], event=_event(t['id'], i, a, b)))
    out['history'] = hist
    if t['status'] == 'on' and n < int(t['days']):
        chooser = t['proposer'] if n % 2 == 0 else mr._other(c, t['proposer'])
        opens = float(t['last_at'] or t['started']) + (DAY_GAP if n else 0)
        out.update(my_turn=chooser == sid, opens=int(opens), ready=now >= opens, chooser=a if chooser == t['proposer'] else b,
                   options=[dict(id=x['id'], emoji=x['emoji'], text=x['text']) for x in _options(t['id'], dest['id'], n)],
                   home_by=int(float(t['started']) + TRIP_HOURS * 3600))
    out['photos'] = [dict(id=r['id'], **_j(r['data'], {})) for r in
                     mr._rows(db, 'SELECT id, data FROM wl_photos WHERE couple=? AND src LIKE ? ORDER BY at, id', (c['id'], f't:{t["id"]}:%'))]
    return out


def _vehicle_name(vid: str) -> str:
    if not vid:
        return ''
    from . import garage, lux
    v = garage.VEHICLES.get(vid) or lux.ASSET.get(vid)
    return f'{v["emoji"]} {v["name"]}' if v else ''


# ---------------------------------------------------------------- 🏠 sống chung mỗi ngày
def _child(db, cid: int):
    r = db.execute('SELECT state FROM family_children WHERE couple=?', (cid,)).fetchone()
    if not r:
        return None
    data = _j(r['state'], {})
    from . import family
    return data if data.get('born') and family.today() >= data['born'] else None


def chore_start(store, sid, display, d):
    kind, role = d.get('kind'), d.get('role')
    need(kind in C.CHORES, 'Chọn một việc nhé.', 'bad_kind')
    roles = dict(C.CHORES[kind]['roles'])
    need(role in roles, 'Chọn phần việc của bạn nhé.', 'bad_role')
    day = vn_day()

    def run(db):
        c = _couple(db, sid)
        if kind == 'cham_con':
            need(_child(db, c['id']), 'Hai bạn chưa có bé ở nhà để chăm.', 'no_child', 409)
        got = db.execute("INSERT INTO wl_chores(couple, day, kind, starter, role, joiner, role2, status, at) VALUES(?,?,?,?,?,'','','open',?) "
                         'ON CONFLICT DO NOTHING RETURNING couple', (c['id'], day, kind, sid, role, mr.now())).fetchone()
        need(got, 'Hôm nay việc này hai bạn đã rủ nhau rồi.', 'once_a_day', 409)
        x = C.CHORES[kind]
        mr._notice(db, mr._other(c, sid), f'{x["emoji"]} {display}: “{x["ask"]}” ({roles[role].lower()} là phần của {display}). Vào Sống chung để làm cùng nha!')
        return mr._display(db, mr._other(c, sid))
    name = store.transaction(run)
    return dict(message=f'Đã rủ {name}. Người ấy nhận phần còn lại là xong!', changed=False)


def chore_join(store, sid, display, d):
    kind, role = d.get('kind'), d.get('role')
    need(kind in C.CHORES, 'Chọn một việc nhé.', 'bad_kind')
    roles = dict(C.CHORES[kind]['roles'])
    need(role in roles, 'Chọn phần việc của bạn nhé.', 'bad_role')
    day = vn_day()
    with store.connect() as db:
        c = _couple(db, sid)
        r = mr._row(db, 'SELECT * FROM wl_chores WHERE couple=? AND day=? AND kind=?', (c['id'], day, kind))
        need(r and r['status'] == 'open', 'Việc này hôm nay không còn chờ ai nữa.', 'gone', 409)
        need(r['starter'] != sid, 'Chờ người ấy vào làm cùng nhé.', 'not_your_turn', 409)
        need(role != r['role'], 'Phần này người ấy nhận rồi, chọn phần khác nha.', 'bad_role')
        a = mr._display(db, r['starter'])
    x = C.CHORES[kind]
    text = _fill(random.Random(f'wlc|{c["id"]}|{day}|{kind}').choice(C.CHORE_DONE), a, display)
    text = f'{x["emoji"]} ' + text.replace('{ra}', roles[r['role']].lower()).replace('{rb}', roles[role].lower())

    def ops(db):
        need(db.execute("UPDATE wl_chores SET joiner=?, role2=?, status='done', done_at=? WHERE couple=? AND day=? AND kind=? AND status='open'",
                        (sid, role, mr.now(), c['id'], day, kind)).rowcount == 1, 'Việc này hôm nay không còn chờ ai nữa.', 'gone', 409)
        added = cp._grow(db, c['id'], CHORE_POINTS)
        cp._moment(db, c, sid, 'chore', text, f'wlc:{c["id"]}:{day}:{kind}')
        if kind == 'cham_con':
            row = db.execute('SELECT state FROM family_children WHERE couple=? FOR UPDATE', (c['id'],)).fetchone()
            data = _j(row['state'] if row else '', {})
            if data and type(data.get('joy')) is int and type(data.get('bond')) is int:
                data['joy'], data['bond'] = min(100, data['joy'] + 10), min(100, data['bond'] + 2)
                db.execute('UPDATE family_children SET state=?, revision=revision+1 WHERE couple=?',
                           (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')), c['id']))
        mr._notice(db, r['starter'], text)
        return added
    added = mr._mutate_retry(store, {c['a']: _spirit_fn(CHORE_SPIRIT), c['b']: _spirit_fn(CHORE_SPIRIT)}, ops)['db']
    return dict(message=text + (f' (+{added} điểm hạnh phúc)' if added else ''), changed=True)


def _chores_view(db, c: dict, sid: str) -> list:
    day = vn_day()
    rows = {r['kind']: r for r in mr._rows(db, 'SELECT * FROM wl_chores WHERE couple=? AND day=?', (c['id'], day))}
    has_child = bool(_child(db, c['id']))
    out = []
    for kind, x in C.CHORES.items():
        r = rows.get(kind)
        roles = [dict(id=k, text=v) for k, v in x['roles']]
        state = 'none' if not r else r['status']
        item = dict(kind=kind, emoji=x['emoji'], name=x['name'], ask=x['ask'], roles=roles, state=state, locked=kind == 'cham_con' and not has_child)
        if r:
            item.update(mine=r['starter'] == sid, role=r['role'], role2=r['role2'] or None)
        out.append(item)
    return out


# ---------------------------------------------------------------- housekeeping, the end of a marriage, views
def housekeep(store, c: dict | None) -> None:
    """On a view: a ceremony left unfinished RITE_DAYS, a trip unanswered TRIP_WAIT_H (refunded) and a trip still on
    after TRIP_HOURS (it comes home: the remaining days take their first activity). Three indexed reads, nothing else."""
    if not c:
        return
    t = mr.now()
    with store.connect() as db:
        rites = mr._rows(db, "SELECT * FROM wl_rites WHERE couple=? AND status='on' AND created<?", (c['id'], t - RITE_DAYS * mr.DAY))
        waits = mr._rows(db, "SELECT * FROM wl_trips WHERE couple=? AND status='proposed' AND created<?", (c['id'], t - TRIP_WAIT_H * 3600))
        olds = mr._rows(db, "SELECT * FROM wl_trips WHERE couple=? AND status='on' AND started<?", (c['id'], t - TRIP_HOURS * 3600))
    if not (rites or waits or olds):
        return

    def run(db):
        paid = []
        for r in rites:
            paid += _rite_refund(db, r, 'expired')
        for w in waits:
            paid += _trip_refund(db, w, 'expired')
        for o in olds:
            cur = mr._row(db, "SELECT * FROM wl_trips WHERE id=? AND status='on' FOR UPDATE", (o['id'],))
            if not cur:
                continue
            picks = _j(cur['picks'], [])
            names = dict(a=mr._display(db, cur['proposer']), b='')
            for n in range(len(picks), int(cur['days'])):
                act = _options(cur['id'], cur['dest'], n)[0]
                picks.append(act['id'])
                _day_done(db, c, cur, n, act, names, t)
            db.execute("UPDATE wl_trips SET picks=?, status='done', ended=? WHERE id=?", (json.dumps(picks), t, cur['id']))
            if mr._row(db, 'SELECT status FROM couples WHERE id=?', (c['id'],))['status'] == 'married':
                _happy(db, c['id'], TRIP_HAPPY[DEST[cur['dest']]['kind']])
                cp._moment(db, c, cur['proposer'], 'trip', f'🏡 Về nhà sau chuyến đi {DEST[cur["dest"]]["name"]}.', f'wlt:home:{cur["id"]}')
        return paid
    try:
        paid = store.transaction(run)
    except Exception:  # noqa: BLE001 - busy rows: the next view tries again
        return
    _settle(store, *set(paid))


def on_end(db, c: dict, deleted: str | None = None) -> list:
    """couple.on_end, inside the divorce / account-deletion transaction, before the fund is split: an unfinished
    ceremony and a trip that has not left are called off and refunded (a fund part back into the fund, so it is split
    with the rest; a wallet part as an effect, never to a deleted account); a trip on its way simply ends. Returns the
    wallet effects to insert."""
    t = mr.now()
    effects = []
    for r in mr._rows(db, "SELECT * FROM wl_rites WHERE couple=? AND status='on' FOR UPDATE", (c['id'],)):
        db.execute("UPDATE wl_rites SET status='cancelled', updated=? WHERE id=?", (t, r['id']))
        if int(r['fee']) > 0 and r['payer'] and r['payer'] != deleted:
            effects.append(mr._effect(f'wlr:rf:{r["id"]}', r['payer'], 'wallet', int(r['fee']), 'Hoàn tiền lễ rước dâu'))
    for tr in mr._rows(db, "SELECT * FROM wl_trips WHERE couple=? AND status IN ('proposed','on') FOR UPDATE", (c['id'],)):
        if tr['status'] == 'on':
            db.execute("UPDATE wl_trips SET status='ended', ended=? WHERE id=?", (t, tr['id']))
            continue
        db.execute("UPDATE wl_trips SET status='cancelled', ended=? WHERE id=?", (t, tr['id']))
        if int(tr['paid_fund']) > 0:
            db.execute('INSERT INTO joint_funds(couple,balance,updated) VALUES(?,0,?) ON CONFLICT DO NOTHING', (c['id'], t))
            db.execute('UPDATE joint_funds SET balance=balance+?,updated=? WHERE couple=?', (int(tr['paid_fund']), t, c['id']))
            db.execute("INSERT INTO joint_ledger(couple,sid,kind,amount,balance,label,ref,status,at) VALUES(?,?,'refund',?,?,?,?,'done',?)",
                       (c['id'], tr['proposer'], int(tr['paid_fund']), cp._balance(db, c['id']), 'Hoàn tiền chuyến đi chơi', f'wlt:rf:{tr["id"]}', t))
        for side in ('a', 'b'):
            if int(tr['paid_' + side]) > 0 and tr[side] != deleted:
                effects.append(mr._effect(f'wlt:rf:{tr["id"]}:{side}', tr[side], 'wallet', int(tr['paid_' + side]), 'Hoàn tiền chuyến đi chơi'))
    return effects


def catalog() -> dict:
    return dict(dests=[dict(id=d['id'], emoji=d['emoji'], name=d['name'], kind=d['kind'], sea=d['sea'], days=d['days'],
                            prices={r: _price(d, r) for r in ('ve', 'thue_bay', 'thue_thuyen') if not _fits(d, r)},
                            fuel=dict(plane=_price(d, 'nha', 'plane'), boat=_price(d, 'nha', 'boat') if d['sea'] else None))
                       for d in C.DESTS],
                rides=list(RIDE.values()), day_gap=DAY_GAP, wait_h=TRIP_WAIT_H)


def view(store, db, sid: str, c: dict | None) -> dict | None:
    """The Hôn nhân sheet's 💍 Sống chung tab: {rite, trip, last, chores, album, assets, catalog} (None: no couple)."""
    if not c or c['status'] not in ('engaged', 'married'):
        return None
    t = mr.now()
    out = dict(rite=_rite_view(db, c, sid, t), married=c['status'] == 'married')
    if c['status'] != 'married':
        return out
    tr = mr._row(db, "SELECT * FROM wl_trips WHERE couple=? AND status IN ('proposed','on') ORDER BY id DESC LIMIT 1", (c['id'],))
    out['trip'] = _trip_view(db, tr, c, sid, t) if tr else None
    last = None if tr else mr._row(db, "SELECT * FROM wl_trips WHERE couple=? AND status IN ('done','ended') AND ended>? ORDER BY id DESC LIMIT 1",
                                    (c['id'], t - 2 * mr.DAY))
    out['last'] = _trip_view(db, last, c, sid, t) if last else None
    out['today_done'] = bool(mr._row(db, "SELECT 1 AS x FROM wl_trips WHERE couple=? AND day=? AND status IN ('on','done')", (c['id'], vn_day(t))))
    out['chores'] = _chores_view(db, c, sid)
    out['album'] = int(db.execute('SELECT COUNT(*) FROM wl_photos WHERE couple=?', (c['id'],)).fetchone()[0])
    out['fund'] = cp._balance(db, c['id'])
    out['catalog'] = catalog()
    return out


def assets(store, sid, display, d):
    """POST wl_assets: the islands and the planes / yachts the two of them own (the trip planner's choices). Quiet."""
    with store.connect() as db:
        c = _couple(db, sid)
    got = _assets(store, c)
    for x in got['islands'] + got['vehicles']:
        x['mine'] = c[x.pop('owner')] == sid
    return dict(message='', assets=got, quiet=True)


def album(store, sid, display, d):
    """POST wl_album {before?}: the couple's photos, newest first, ALBUM_PAGE at a time. Quiet."""
    before = d.get('before')
    need(before is None or type(before) in (int, float), 'Trang không hợp lệ.')
    with store.connect() as db:
        c = mr._bond(db, sid)
        need(c and c['status'] in ('engaged', 'married'), 'Album chỉ dành cho hai bạn.', 'not_married', 409)
        rows = mr._rows(db, 'SELECT id, data, at FROM wl_photos WHERE couple=? AND at<? ORDER BY at DESC, id DESC LIMIT ?',
                        (c['id'], float(before) if before is not None else 1e12, ALBUM_PAGE + 1))
    more = len(rows) > ALBUM_PAGE
    photos = [dict(id=r['id'], at=float(r['at']), **_j(r['data'], {})) for r in rows[:ALBUM_PAGE]]
    return dict(message='', photos=photos, more=more, quiet=True)


ACTIONS = dict(wl_rite_start=rite_start, wl_rite_step=rite_step, wl_rite_cancel=rite_cancel, wl_trip_propose=trip_propose,
               wl_trip_answer=trip_answer, wl_trip_cancel=trip_cancel, wl_trip_pick=trip_pick, wl_chore_start=chore_start,
               wl_chore_join=chore_join, wl_assets=assets, wl_album=album)


def forget(db, sid: str) -> None:
    """Account deletion: nothing here names one player alone (the rows are the couple's; on_end already closed them)."""
    return None
