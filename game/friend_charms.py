"""🤝 Phụ kiện đôi: pair accessories two friends wear together (góp ý #484 "thêm mấy cái phụ kiện của bạn bè đeo chung
đồ đi … đừng giới hạn số lượng đeo nha"; owner 22/10 "linh kiện thì thêm rồi cho người ta mua").

* Three pairs, sold at 🛍️ Tiệm phụ kiện (public/js/v4/acc-shop.js): 🏎️ Chí cốt (a supercar model on a keyring), 👜 Bạn thân
  (a handbag), 💐 Tri kỉ (an eternal flower pinned on the chest). The names are the player's suggestions (Chí cốt for two
  guys, Bạn thân for two girls, Tri kỉ for everyone else) but nothing is gated by gender: anyone picks any pair.
* One player buys a PAIR (both pieces, one price) → it waits in their gift box → they offer it to a friend (only
  friends, never someone blocked) → the friend accepts (both now own it and wear it, each seeing the other's name) or
  declines (the pair goes back to the box). An unanswered offer goes back to the box after OFFER_DAYS. A pair still in
  the box can be sold back for SELL_PCT % of its price.
* No limit on pairs owned or worn (the player: "đừng giới hạn số lượng đeo"): every pair has its own "Đang đeo" switch on
  each side. Only the box (pairs not given yet) holds at most BOX_MAX, like the ring box.
* The character draws what is worn by KIND, counted: {chi_cot: 2, tri_ki: 1} (public/js/v4/look.js paintPairs: two cars on
  the keyring, one rose). That count, never a partner's name, is all other players see (live/charms.py `pr` on walkers).

* 2.5.4 (owner 22/10 "thêm nhiều món nữa đi, với giá như này rẻ quá, tăng nhẹ tí nữa. rồi tính toán thêm vài món nữa"):
  ten kinds, +50 % on the three first ones (the reasoning: game/friend_charms_content.py). A pair bought before keeps the
  price it was paid (`price`, what a sale from the box gives back 80 % of).
* 💞 Quan hệ (owner 22/10 "set mối quan hệ trong game được, kiểu bạn bè, tri kỉ,... và muốn set thì phải mua mấy cái
  này"): two friends who share a pair (status 'paired') may set ONE relationship label between them (RELS: Bạn thân, Cạ
  cứng, Chí cốt, Tri kỉ, Anh em / Chị em kết nghĩa), each label opened by the kinds listed under it (dearer pairs, closer
  labels). The same offer / accept flow as a pair: charm_bond {id: a pair shared with that friend, label} asks (or accepts
  at once when the friend already asked that very label); the friend answers with charm_bond_answer {id, answer}; either
  side may put it back to 🤝 Bạn bè alone (charm_bond_off). A label shows (the friend list, the pairs in "Đang có", the
  street's player card) only while the two are friends and still share a pair of a kind that opens it: a partner's
  account deleted, an unfriend or a block take it away by itself (unfriend and block also clear the row). A pair once
  given cannot be sold, so a label never outlives its pair otherwise. Table friend_bonds (SCHEMA_VERSION 90), one row per
  two players.

Where things live: the table friend_charms (game/pg_schema.py, SCHEMA_VERSION 86). No save key: money moves through the
journey wallet / bank.pay inside the save's own transaction (marriage._mutate_retry, an effect row with a fixed id, like a
ring), so an old save loads unchanged and a rollback simply never reads the table.
Commands: POST /api/marriage/charm_* (marriage._more_actions), every rule checked here.
"""
from __future__ import annotations

import secrets

from . import marriage as mr
from .friend_charms_content import DEFAULT_REL, INDEX, KINDS, ORDER, REL_INDEX, RELS   # the catalogue (live/charms.py reads it without the engine)

BOX_MAX = 10            # pairs bought and not given yet (box + offered)
OFFER_DAYS = 7          # an offer nobody answered goes back to the box
OFFERS_PER_DAY = 20     # offers a player sends in 24 hours
SELL_PCT = 80           # a pair still in the box sells back for this share of its price
LIST_MAX = 500          # rows read for one view (pairs are not limited: the oldest beyond this are simply not listed)
DAY = mr.DAY
PREFIX = 'charm_'


def catalog() -> dict:
    """Static list for the client (content.journey.wardrobe.pairs)."""
    return dict(kinds=[dict(k) for k in KINDS], box_max=BOX_MAX, offer_days=OFFER_DAYS, sell_pct=SELL_PCT,
                rels=[dict(r, kinds=list(r['kinds'])) for r in RELS], rel_default=dict(DEFAULT_REL))


# ---------------------------------------------------------------- reading
def _side(r: dict, sid: str) -> str:
    return 'a' if r['a'] == sid else 'b'


def _other(r: dict, sid: str) -> str:
    return r['b'] if r['a'] == sid else r['a']


def _name(db, r: dict, sid: str) -> str:
    """The partner's display name now, else the name kept when the pair was made (an account deleted since)."""
    other = _other(r, sid)
    if other:
        return mr._display(db, other)
    return mr._clean_name(r['b_name'] if r['a'] == sid else r['a_name'])


def worn_db(db, sid: str) -> dict:
    """{kind: count} of the pairs this player wears now (what the character draws; live/charms.py reads the same)."""
    out = {}
    for r in db.execute("SELECT kind FROM friend_charms WHERE status='paired' AND ((a=? AND wear_a=1) OR (b=? AND wear_b=1))",
                        (sid, sid)).fetchall():
        if r['kind'] in INDEX:
            out[r['kind']] = out.get(r['kind'], 0) + 1
    return {k: out[k] for k in ORDER if k in out}


def _expire(db, sid: str) -> None:
    """Offers from or to this player nobody answered for OFFER_DAYS go back to the buyer's box."""
    db.execute("UPDATE friend_charms SET status='box',b='',offered=0 WHERE status='offered' AND offered<? AND (a=? OR b=?)",
               (mr.now() - OFFER_DAYS * DAY, sid, sid))


def _friends(db, sid: str) -> list:
    rows = mr._rows(db, 'SELECT f.friend, p.code FROM friends f JOIN marriage_people p ON p.sid=f.friend WHERE f.sid=? LIMIT 200', (sid,))
    out = [dict(code=r['code'], name=mr._display(db, r['friend'])) for r in rows if r['code']]
    out.sort(key=lambda f: f['name'].lower())
    return out


# ---------------------------------------------------------------- 💞 relationships (friend_bonds, SCHEMA_VERSION 90)
def _key(a: str, b: str) -> tuple:
    return (a, b) if a < b else (b, a)


def shared(db, a: str, b: str) -> set:
    """The kinds of the pairs these two share now (status 'paired', both still there)."""
    if not a or not b or a == b:
        return set()
    return {r['kind'] for r in db.execute("SELECT kind FROM friend_charms WHERE status='paired' AND ((a=? AND b=?) OR (a=? AND b=?))",
                                          (a, b, b, a)).fetchall()}


def opens(kinds) -> list:
    """The labels these kinds open (catalogue order)."""
    have = set(kinds)
    return [r['id'] for r in RELS if have & set(r['kinds'])]


def _friends_now(db, a: str, b: str) -> bool:
    return bool(db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (a, b)).fetchone())


def _bond_row(db, a: str, b: str, lock: bool = False):
    lo, hi = _key(a, b)
    return mr._row(db, 'SELECT * FROM friend_bonds WHERE lo=? AND hi=?' + (' FOR UPDATE' if lock else ''), (lo, hi))


def _valid(label: str, can) -> str:
    return label if label in REL_INDEX and label in can else ''


def rel_between(db, me: str, other: str) -> dict | None:
    """The relationship shown between two players ({id, emoji, name}), None for plain 🤝 Bạn bè (game/friends.py card)."""
    r = _bond_row(db, me, other)
    if not r or not r['label'] or not _friends_now(db, me, other):
        return None
    lab = _valid(r['label'], opens(shared(db, me, other)))
    return {k: REL_INDEX[lab][k] for k in ('id', 'emoji', 'name')} if lab else None


def _bonds(db, sid: str) -> dict:
    """{other sid: friend_bonds row} of this player."""
    return {(r['hi'] if r['lo'] == sid else r['lo']): r
            for r in mr._rows(db, 'SELECT * FROM friend_bonds WHERE lo=? OR hi=? LIMIT ?', (sid, sid, LIST_MAX))}


def view_db(db, sid: str) -> dict:
    rows = mr._rows(db, "SELECT * FROM friend_charms WHERE (a=? AND status IN ('box','offered','paired')) OR (b=? AND status IN ('offered','paired')) "
                        'ORDER BY at DESC LIMIT ?', (sid, sid, LIST_MAX))
    bonds = _bonds(db, sid)
    friends_set = {r['friend'] for r in mr._rows(db, 'SELECT friend FROM friends WHERE sid=? LIMIT 500', (sid,))}
    kinds_with = {}
    for r in rows:
        if r['status'] == 'paired' and r['a'] and r['b']:
            kinds_with.setdefault(_other(r, sid), set()).add(r['kind'])

    def rel_of(other: str) -> dict:
        """The pair's 💞 part: the label set, the labels the two may set, an open ask."""
        can = opens(kinds_with.get(other, ())) if other in friends_set else []
        b = bonds.get(other)
        out = dict(rel=_valid(b['label'], can) if b else '', can=can)
        if b and b['ask'] and _valid(b['ask'], can):
            out['ask'] = dict(label=b['ask'], mine=b['ask_by'] == sid, id=b['ask_charm'])
        return out
    bond_in = [dict(id=b['ask_charm'], label=b['ask'], name=mr._display(db, other), at=int(b['ask_at']))
               for other, b in bonds.items()
               if b['ask'] and b['ask_by'] != sid and other in friends_set and _valid(b['ask'], opens(kinds_with.get(other, ())))]
    box, sent, incoming, pairs = [], [], [], []
    for r in rows:
        if r['kind'] not in INDEX:
            continue
        base = dict(id=r['id'], kind=r['kind'])
        if r['status'] == 'box':
            box.append(dict(base, price=int(r['price']), sell=int(r['price']) * SELL_PCT // 100))
        elif r['status'] == 'offered':
            (sent if r['a'] == sid else incoming).append(dict(base, name=_name(db, r, sid), at=int(r['offered'])))
        else:
            side = _side(r, sid)
            pairs.append(dict(base, name=_name(db, r, sid), on=bool(r['wear_' + side]), since=int(r['paired'] or r['at']), mine=side == 'a',
                              **rel_of(_other(r, sid))))
    pairs.sort(key=lambda p: (ORDER.index(p['kind']), -p['since']))
    return dict(box=box, sent=sent, incoming=incoming, pairs=pairs, worn=worn_db(db, sid), friends=_friends(db, sid),
                box_max=BOX_MAX, can_buy=len(box) + len(sent) < BOX_MAX, bond_in=bond_in)


def boot(store, token: str | None) -> dict | None:
    """The bootstrap's small part (server.py): what the character wears and how many offers wait. None for a guest."""
    sid, display = mr.whoami(store, token)
    if not sid or not display:
        return None
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM friend_charms WHERE a=? OR b=? LIMIT 1', (sid, sid)).fetchone():
            return dict(worn={}, incoming=0)
        waiting = db.execute("SELECT COUNT(*) FROM friend_charms WHERE b=? AND status='offered' AND offered>=?",
                             (sid, mr.now() - OFFER_DAYS * DAY)).fetchone()[0]
        return dict(worn=worn_db(db, sid), incoming=int(waiting))


def _view(store, sid: str) -> dict:
    with store.connect() as db:
        return view_db(db, sid)


def _live(db, *sids) -> None:
    """The live service reads these players' worn pairs again (live/charms.py); an older one ignores the op."""
    from . import live_chat
    live_chat.notify(db, dict(op='charm', pids=[live_chat.pid_of(s) for s in sids if s]))


def _done(store, sid: str, message: str, out: dict | None = None) -> dict:
    """The answer: the message, this player's view, and the save when money moved (the client adopts it)."""
    res = dict(message=message, changed=bool(out), charms=_view(store, sid))
    st = (out or {}).get('states', {}).get(sid)
    if st:
        res.update(state=mr.public_state(st[0]), revision=st[1])
    return res


# ---------------------------------------------------------------- commands
def _target(db, sid: str, code) -> str:
    """The friend behind a player code; the same words for every reason it cannot be them."""
    p = mr._find(db, mr.clean_code(code))
    mr.need(p and p['sid'] != sid, 'Không tìm thấy người bạn này.', 'not_found', 404)
    other = p['sid']
    mr.need(not mr._blocked(db, sid, other), 'Không tặng được cho người này.', 'blocked', 409)
    mr.need(db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (sid, other)).fetchone(),
            'Chỉ tặng được cho bạn bè. Kết bạn trước nhé (mục 🤝 Bạn bè).', 'not_friends', 409)
    return other


def _offer_db(db, sid: str, display: str, cid: str, other: str, kind: str) -> str:
    t = mr.now()
    mr.need(db.execute('SELECT COUNT(*) FROM friend_charms WHERE a=? AND offered>?', (sid, t - DAY)).fetchone()[0] < OFFERS_PER_DAY,
            f'Mỗi ngày tặng được {OFFERS_PER_DAY} lần. Mai tặng tiếp nhé.', 'rate_limited', 429)
    mr.need(db.execute("UPDATE friend_charms SET status='offered',b=?,offered=? WHERE id=? AND a=? AND status='box'", (other, t, cid, sid)).rowcount == 1,
            'Món này không còn trong hộp quà của bạn.', 'gone', 409)
    k = INDEX[kind]
    mr._notice(db, other, f'{k["emoji"]} {display} tặng bạn một nửa cặp “{k["name"]}” ({k["item"].lower()}). Ghé 🛍️ Tiệm phụ kiện để nhận nhé.')
    return mr._display(db, other)


def _buy(store, sid: str, display: str, d: dict) -> dict:
    """🛍️ One pair, or `qty` pairs of one kind (owner 23/10 "mua thì cho mua nhiều cái 1 lần"; absent: 1, an older
    client): one price of qty × the pair, one effect row (the request id: a retry pays nothing), all in the box or none
    (the box's room, the wallet for the whole). With `code` the first pair goes to that friend, the others wait in the box."""
    kind = d.get('kind')
    mr.need(kind in INDEX, 'Chọn một cặp phụ kiện nhé.', 'bad_kind')
    mr.need(d.get('code') is None or isinstance(d.get('code'), str), 'Mã người chơi không hợp lệ.', 'bad_code')
    qty = d.get('qty', 1)
    mr.need(isinstance(qty, int) and not isinstance(qty, bool) and 1 <= qty <= BOX_MAX, f'Mua từ 1 đến {BOX_MAX} cặp một lần nhé.', 'bad_qty')
    k = INDEX[kind]
    total, times = k['price'] * qty, f' ×{qty}' if qty > 1 else ''
    eid = f'charm:{sid[:16]}:{mr._rid(d)}'
    with store.connect() as db:
        if db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (eid,)).fetchone():
            return _done(store, sid, f'Cặp {k["name"]}{times} này bạn đã mua rồi.')
        n = db.execute("SELECT COUNT(*) FROM friend_charms WHERE a=? AND status IN ('box','offered')", (sid,)).fetchone()[0]
        other = _target(db, sid, d['code']) if d.get('code') else None
    mr.need(n < BOX_MAX, f'Hộp quà đang có {BOX_MAX} cặp chưa tặng. Tặng bớt rồi mua thêm nhé.', 'box_full', 409)
    mr.need(n + qty <= BOX_MAX, f'Hộp quà chỉ còn chỗ cho {BOX_MAX - n} cặp. Mua ít hơn hoặc tặng bớt nhé.', 'box_full', 409)
    cids = ['fc' + secrets.token_hex(6) for _ in range(qty)]
    eff = mr._effect(eid, sid, 'wallet', -total, f'Tiệm phụ kiện: cặp {k["name"]}{times} ({k["item"].lower()})')
    named = []

    def fn(s):
        mr.need(mr._can_spend(s, total, d.get('pay')), f'Ví chưa đủ {total} xu để mua cặp {k["name"]}{times}.', 'not_enough')
        mr._spend(s, eff, d.get('pay'))

    def ops(db):
        for cid in cids:
            db.execute("INSERT INTO friend_charms(id,kind,a,status,price,at) VALUES(?,?,?,'box',?,?)", (cid, kind, sid, k['price'], mr.now()))
        mr._insert_effects(db, [eff], 'applied')
        if other:
            named.append(_offer_db(db, sid, display, cids[0], other, kind))
    try:
        out = mr._mutate_retry(store, {sid: fn}, ops)
    except mr.dbm.IntegrityError:
        return _done(store, sid, f'Cặp {k["name"]}{times} này bạn đã mua rồi.')
    if named:
        rest = f' {qty - 1} cặp còn lại nằm trong hộp quà.' if qty > 1 else ''
        return _done(store, sid, f'Đã mua cặp {k["name"]}{times} ({total} xu) và gửi một chiếc tới {named[0]}. Chờ bạn ấy nhận nhé!{rest}', out)
    return _done(store, sid, f'Đã mua cặp {k["name"]}{times} ({total} xu). {"Các cặp" if qty > 1 else "Cặp"} này nằm trong hộp quà, tặng một chiếc cho bạn bè để cùng đeo nhé.', out)


def _cid(d: dict) -> str:
    cid = d.get('id')
    mr.need(isinstance(cid, str) and 1 <= len(cid) <= 20, 'Chọn một món trong hộp nhé.', 'bad_charm')
    return cid


def _offer(store, sid: str, display: str, d: dict) -> dict:
    cid = _cid(d)

    def run(db):
        _expire(db, sid)
        r = mr._row(db, 'SELECT * FROM friend_charms WHERE id=? AND a=?', (cid, sid))
        mr.need(r and r['status'] in ('box', 'offered'), 'Không tìm thấy món này trong hộp quà.', 'bad_charm', 404)
        mr.need(r['status'] == 'box', 'Món này đang chờ một người bạn trả lời.', 'busy', 409)
        other = _target(db, sid, d.get('code'))
        mr.need(r['kind'] in INDEX, 'Món này chưa dùng được ở phiên bản này.', 'bad_charm')
        return INDEX[r['kind']], _offer_db(db, sid, display, cid, other, r['kind'])
    k, name = store.transaction(run)
    return _done(store, sid, f'Đã gửi một chiếc “{k["name"]}” tới {name}. Bạn ấy nhận là hai bạn cùng đeo.')


def _respond(store, sid: str, display: str, d: dict) -> dict:
    cid, answer = _cid(d), d.get('answer')
    mr.need(answer in ('accept', 'decline'), 'Trả lời không hợp lệ.')

    def run(db):
        _expire(db, sid)
        r = mr._row(db, "SELECT * FROM friend_charms WHERE id=? AND b=? AND status='offered'", (cid, sid))
        mr.need(r and r['kind'] in INDEX, 'Món quà này không còn chờ bạn nữa.', 'gone', 409)
        k = INDEX[r['kind']]
        if answer == 'decline':
            db.execute("UPDATE friend_charms SET status='box',b='',offered=0 WHERE id=? AND status='offered'", (cid,))
            mr._notice(db, r['a'], f'{display} chưa nhận cặp “{k["name"]}” lần này. Món quà vẫn nằm trong hộp của bạn.')
            return k, None
        mr.need(not mr._blocked(db, sid, r['a']), 'Không nhận được món quà này.', 'blocked', 409)
        t, name = mr.now(), mr._display(db, r['a'])
        mr.need(db.execute("UPDATE friend_charms SET status='paired',paired=?,wear_a=1,wear_b=1,a_name=?,b_name=? WHERE id=? AND status='offered'",
                           (t, name, display, cid)).rowcount == 1, 'Món quà này không còn chờ bạn nữa.', 'gone', 409)
        mr._notice(db, r['a'], f'{k["emoji"]} {display} đã nhận cặp “{k["name"]}”. Giờ hai bạn đeo chung rồi!')
        _live(db, sid, r['a'])
        return k, name
    k, name = store.transaction(run)
    if name is None:
        return _done(store, sid, 'Đã từ chối nhẹ nhàng. Món quà trở về hộp của người tặng.')
    return _done(store, sid, f'{k["emoji"]} Bạn và {name} giờ là “{k["name"]}”. Cả hai đang đeo rồi đó!')


def _cancel(store, sid: str, display: str, d: dict) -> dict:
    cid = _cid(d)
    store.transaction(lambda db: mr.need(db.execute("UPDATE friend_charms SET status='box',b='',offered=0 WHERE id=? AND a=? AND status='offered'",
                                                    (cid, sid)).rowcount == 1, 'Món quà này không còn chờ trả lời.', 'gone', 409))
    return _done(store, sid, 'Đã rút lại món quà. Cặp phụ kiện về lại hộp của bạn.')


def _wear(store, sid: str, display: str, d: dict) -> dict:
    on = d.get('on')
    mr.need(type(on) is bool, 'Thao tác không hợp lệ.')
    every = d.get('all', False)
    mr.need(every in (True, False), 'Thao tác không hợp lệ.')

    def run(db):
        if every:   # "Đeo hết" / "Tháo hết": no limit on how many are worn
            n = sum(db.execute(f"UPDATE friend_charms SET wear_{x}=? WHERE {x}=? AND status='paired'", (int(on), sid)).rowcount for x in ('a', 'b'))
            mr.need(n, 'Bạn chưa có phụ kiện đôi nào.', 'none', 404)
        else:
            cid = _cid(d)
            r = mr._row(db, "SELECT * FROM friend_charms WHERE id=? AND status='paired' AND (a=? OR b=?)", (cid, sid, sid))
            mr.need(r, 'Không tìm thấy phụ kiện đôi này.', 'bad_charm', 404)
            db.execute(f'UPDATE friend_charms SET wear_{_side(r, sid)}=? WHERE id=?', (int(on), cid))
        _live(db, sid)
    store.transaction(run)
    if every:
        return _done(store, sid, 'Đã đeo hết phụ kiện đôi.' if on else 'Đã tháo hết phụ kiện đôi, cất vào tủ.')
    return _done(store, sid, 'Đeo vào rồi nè!' if on else 'Đã tháo ra, cất vào tủ.')


def _sell(store, sid: str, display: str, d: dict) -> dict:
    cid = _cid(d)
    with store.connect() as db:
        r = mr._row(db, 'SELECT * FROM friend_charms WHERE id=? AND a=?', (cid, sid))
    mr.need(r and r['status'] in ('box', 'offered', 'sold'), 'Không tìm thấy món này trong hộp quà.', 'bad_charm', 404)
    if r['status'] == 'sold':
        return _done(store, sid, 'Cặp này đã bán rồi, tiền đã về ví.')
    mr.need(r['status'] == 'box', 'Món này đang chờ một người bạn trả lời. Rút lại rồi hẵng bán nhé.', 'busy', 409)
    amount = int(r['price']) * SELL_PCT // 100
    name = INDEX[r['kind']]['name'] if r['kind'] in INDEX else 'phụ kiện đôi'
    eff = mr._effect('charm-sell:' + cid, sid, 'wallet', amount, f'Bán lại cặp {name} cho Tiệm phụ kiện')

    def ops(db):
        mr.need(db.execute("UPDATE friend_charms SET status='sold' WHERE id=? AND a=? AND status='box'", (cid, sid)).rowcount == 1,
                'Món này vừa thay đổi. Mở lại hộp quà nhé.', 'gone', 409)
        mr._insert_effects(db, [eff], 'applied')
    out = mr._mutate_retry(store, {sid: lambda s: mr._apply_effect(s, eff)}, ops)
    return _done(store, sid, f'Đã bán lại cặp {name}: {amount} xu vào ví ({SELL_PCT}% giá mua).', out)


def _list(store, sid: str, display: str, d: dict) -> dict:
    store.transaction(lambda db: _expire(db, sid))
    return dict(message='', quiet=True, charms=_view(store, sid))


def _bond(store, sid: str, display: str, d: dict) -> dict:
    """💞 Ask a friend to set `label` between you (accepted at once when they already asked that very one)."""
    cid, label = _cid(d), d.get('label')
    mr.need(label in REL_INDEX, 'Chọn một mối quan hệ nhé.', 'bad_rel')
    rel = REL_INDEX[label]

    def run(db):
        r = mr._row(db, "SELECT * FROM friend_charms WHERE id=? AND status='paired' AND (a=? OR b=?)", (cid, sid, sid))
        mr.need(r and _other(r, sid), 'Không tìm thấy phụ kiện đôi này.', 'bad_charm', 404)
        other = _other(r, sid)
        mr.need(_friends_now(db, sid, other) and not mr._blocked(db, sid, other), 'Chỉ đặt quan hệ được với bạn bè.', 'not_friends', 409)
        kinds = shared(db, sid, other)
        mr.need(kinds & set(rel['kinds']), f'“{rel["name"]}” cần hai bạn cùng có một cặp: '
                + ', '.join(INDEX[k]['name'] for k in rel['kinds']) + '.', 'need_pair', 409)
        if r['kind'] in rel['kinds']:
            unlock = cid
        else:   # the pair tapped does not open it: another one the two share does
            marks = ','.join('?' * len(rel['kinds']))
            unlock = mr._row(db, f"SELECT id FROM friend_charms WHERE status='paired' AND ((a=? AND b=?) OR (a=? AND b=?)) AND kind IN ({marks}) "
                                 'ORDER BY id LIMIT 1', (sid, other, other, sid, *rel['kinds']))['id']
        lo, hi = _key(sid, other)
        db.execute('INSERT INTO friend_bonds(lo,hi) VALUES(?,?) ON CONFLICT DO NOTHING', (lo, hi))
        b = _bond_row(db, sid, other, lock=True)
        name, t = mr._display(db, other), mr.now()
        if _valid(b['label'], opens(kinds)) == label:
            return 'same', name
        if b['ask'] == label and b['ask_by'] == other:   # they asked for this very label: both agree
            db.execute("UPDATE friend_bonds SET label=?,charm=?,at=?,ask='',ask_by='',ask_charm='',ask_at=0 WHERE lo=? AND hi=?",
                       (label, unlock, t, lo, hi))
            mr._notice(db, other, f'{rel["emoji"]} {display} đã đồng ý: giờ hai bạn là “{rel["name"]}”.')
            return 'set', name
        if (b['ask'], b['ask_by']) != (label, sid):
            mr._notice(db, other, f'{rel["emoji"]} {display} muốn hai bạn thành “{rel["name"]}”. Ghé 🛍️ Tiệm phụ kiện để trả lời nhé.')
        db.execute('UPDATE friend_bonds SET ask=?,ask_by=?,ask_charm=?,ask_at=? WHERE lo=? AND hi=?', (label, sid, unlock, t, lo, hi))
        return 'asked', name
    how, name = store.transaction(run)
    if how == 'same':
        return _done(store, sid, f'Bạn và {name} đã là “{rel["name"]}” rồi.')
    if how == 'set':
        return _done(store, sid, f'{rel["emoji"]} Bạn và {name} giờ là “{rel["name"]}”!')
    return _done(store, sid, f'Đã gửi lời mời “{rel["name"]}” tới {name}. Bạn ấy đồng ý là xong.')


def _bond_answer(store, sid: str, display: str, d: dict) -> dict:
    cid, answer = _cid(d), d.get('answer')
    mr.need(answer in ('accept', 'decline'), 'Trả lời không hợp lệ.')

    def run(db):
        b = mr._row(db, "SELECT * FROM friend_bonds WHERE ask_charm=? AND ask<>'' AND ask_by<>? AND (lo=? OR hi=?) FOR UPDATE",
                    (cid, sid, sid, sid))
        mr.need(b, 'Lời mời này không còn chờ bạn nữa.', 'gone', 409)
        other, rel = b['ask_by'], REL_INDEX.get(b['ask'])
        if answer == 'decline' or not rel:
            db.execute("UPDATE friend_bonds SET ask='',ask_by='',ask_charm='',ask_at=0 WHERE lo=? AND hi=?", (b['lo'], b['hi']))
            if rel:
                mr._notice(db, other, f'{display} chưa nhận lời “{rel["name"]}” lần này. Hai bạn vẫn là bạn bè nhé.')
            return None, mr._display(db, other)
        mr.need(_friends_now(db, sid, other) and not mr._blocked(db, sid, other), 'Chỉ đặt quan hệ được với bạn bè.', 'not_friends', 409)
        mr.need(rel['id'] in opens(shared(db, sid, other)), f'Hai bạn không còn cặp phụ kiện nào mở “{rel["name"]}”.', 'need_pair', 409)
        db.execute("UPDATE friend_bonds SET label=ask,charm=ask_charm,at=?,ask='',ask_by='',ask_charm='',ask_at=0 WHERE lo=? AND hi=?",
                   (mr.now(), b['lo'], b['hi']))
        mr._notice(db, other, f'{rel["emoji"]} {display} đã đồng ý: giờ hai bạn là “{rel["name"]}”.')
        return rel, mr._display(db, other)
    rel, name = store.transaction(run)
    if rel is None:
        return _done(store, sid, 'Đã từ chối nhẹ nhàng. Hai bạn vẫn là bạn bè.')
    return _done(store, sid, f'{rel["emoji"]} Bạn và {name} giờ là “{rel["name"]}”!')


def _bond_off(store, sid: str, display: str, d: dict) -> dict:
    """Back to 🤝 Bạn bè (either side alone), this player's own open ask withdrawn too."""
    cid = _cid(d)

    def run(db):
        r = mr._row(db, "SELECT * FROM friend_charms WHERE id=? AND (a=? OR b=?) AND status='paired'", (cid, sid, sid))
        mr.need(r and _other(r, sid), 'Không tìm thấy phụ kiện đôi này.', 'bad_charm', 404)
        other = _other(r, sid)
        b = _bond_row(db, sid, other, lock=True)
        mr.need(b and (b['label'] or (b['ask'] and b['ask_by'] == sid)), 'Hai bạn đang là bạn bè rồi.', 'none', 409)
        lo, hi = _key(sid, other)
        if b['label']:
            db.execute("UPDATE friend_bonds SET label='',charm='',at=? WHERE lo=? AND hi=?", (mr.now(), lo, hi))
            rel = REL_INDEX.get(b['label'])
            if rel:
                mr._notice(db, other, f'{display} đã đổi quan hệ “{rel["name"]}” về bạn bè.')
        if b['ask'] and b['ask_by'] == sid:
            db.execute("UPDATE friend_bonds SET ask='',ask_by='',ask_charm='',ask_at=0 WHERE lo=? AND hi=?", (lo, hi))
        return mr._display(db, other)
    name = store.transaction(run)
    return _done(store, sid, f'Bạn và {name} giờ là {DEFAULT_REL["emoji"]} {DEFAULT_REL["name"]}.')


def clear_bond(db, a: str, b: str) -> None:
    """An unfriend or a block (game/friends.py): the label and any ask between the two go."""
    lo, hi = _key(a, b)
    db.execute('DELETE FROM friend_bonds WHERE lo=? AND hi=?', (lo, hi))


def forget(db, sid: str) -> None:
    """An account deleted (marriage.forget): its box goes; an offer it received goes back to the buyer's box; a pair it
    shared stays with the friend under the name kept when the pair was made, worn on nobody's side but theirs."""
    db.execute("DELETE FROM friend_charms WHERE a=? AND status IN ('box','offered','sold')", (sid,))
    db.execute('DELETE FROM friend_bonds WHERE lo=? OR hi=?', (sid, sid))   # 💞 their relationships
    db.execute("UPDATE friend_charms SET status='box',b='',offered=0 WHERE b=? AND status='offered'", (sid,))
    db.execute("UPDATE friend_charms SET a='',wear_a=0 WHERE a=? AND status='paired'", (sid,))
    db.execute("UPDATE friend_charms SET b='',wear_b=0 WHERE b=? AND status='paired'", (sid,))


ACTIONS = dict(charm_view=_list, charm_buy=_buy, charm_offer=_offer, charm_respond=_respond, charm_cancel=_cancel,
               charm_wear=_wear, charm_sell=_sell, charm_bond=_bond, charm_bond_answer=_bond_answer, charm_bond_off=_bond_off)
