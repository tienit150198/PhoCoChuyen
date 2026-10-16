"""🏝️ Ra đảo cùng bạn bè: trips to a private island, their seats and their guests (PostgreSQL, never in saves).

The owner of an island (game/island.py, journey.island.own) starts a trip (POST start {island, vehicle}): alone
(vehicle '': the island's own boat, one seat) or in a yacht / plane they own (game/garage.py, game/lux.py) with
island_content.SEATS seats, the owner included. They invite mutual friends nobody blocked (POST invite {trip, codes}:
the game's and the chat's blocks, either way); each invitee gets a live card (pg_notify 'mnl_live' {op:'island'},
live/island.py) and accepts while seats remain (POST answer {trip, answer}). The seats are counted under the trip
row's lock (SELECT … FOR UPDATE), so two friends taking the last seat at once: one is aboard, the other is told the
trip is full. A trip lasts SESSION_MIN minutes (`ends`); the owner ends it sooner (POST end), a guest leaves (POST
leave: the seat is free again), the owner may also take a guest off (POST remove). Selling the island, a reset or an
imported save ends its open trip (command_commit, in the save's own transaction). The live room (live/island.py)
checks the same rows (ACCESS_SQL) on entry and every few seconds; leaving returns the players to town.

Rows: island_trips {id, owner, island, vehicle, kind, seats, status open|ended, created, ends, ended, why},
island_guests {trip, guest, status invited|aboard|declined|left|removed, invited, answered} (game/pg_schema.py 54).
Nothing here moves money: a trip is free (the island's monthly fee pays its crew), and no island earns anything.
"""
from __future__ import annotations

import json
import secrets

from . import island as isl
from . import island_content as C
from . import marriage as mr
from . import social

MINUTES = C.SESSION_MIN
SECONDS = MINUTES * 60
CODES_MAX = 20
ENDS = ('owner', 'time', 'sold', 'gone')


class IslandError(mr.MarriageError):
    pass


def need(ok, message, code='island_error', status=400):
    if not ok:
        raise IslandError(message, code, status)


# The live service's check (live/island.py), compatible with game.db and live.db: one statement sees the trip, this
# player's seat, the friendship with the owner and both kinds of blocks in the same snapshot.
ACCESS_SQL = """
SELECT t.id, t.owner, t.island, t.vehicle, t.kind, t.seats, t.status, t.ends, g.status AS seat,
       (EXISTS(SELECT 1 FROM friends WHERE sid=t.owner AND friend=v.sid)
        AND EXISTS(SELECT 1 FROM friends WHERE sid=v.sid AND friend=t.owner)) AS friends_ok,
       (EXISTS(SELECT 1 FROM marriage_blocks WHERE (sid=t.owner AND target=v.sid) OR (sid=v.sid AND target=t.owner))
        OR EXISTS(SELECT 1 FROM blocks WHERE
          (pid=substring(encode(sha256(convert_to('pid:' || t.owner,'UTF8')),'hex'),1,16)
           AND target=substring(encode(sha256(convert_to('pid:' || v.sid,'UTF8')),'hex'),1,16))
          OR (pid=substring(encode(sha256(convert_to('pid:' || v.sid,'UTF8')),'hex'),1,16)
           AND target=substring(encode(sha256(convert_to('pid:' || t.owner,'UTF8')),'hex'),1,16)))) AS blocked
FROM (SELECT ?::text AS sid) v JOIN island_trips t ON t.id=?
LEFT JOIN island_guests g ON g.trip=t.id AND g.guest=v.sid
"""


def access_for(row, sid: str, now: float) -> str | None:
    """'owner' / 'guest' while the row (ACCESS_SQL for `sid`) lets this player on the island now, else None."""
    if not row or row['status'] != 'open' or float(row['ends']) <= now:
        return None
    if row['owner'] == sid:
        return 'owner'
    return 'guest' if row['seat'] == 'aboard' and row['friends_ok'] and not row['blocked'] else None


INVITED_SQL = ("SELECT COUNT(*) AS n FROM island_guests g JOIN island_trips t ON t.id=g.trip "
               "WHERE g.guest=? AND g.status='invited' AND t.status='open' AND t.ends>?")


def _notify(db, sid: str, why: str, trip: str = '') -> None:
    db.execute('SELECT pg_notify(?,?)', ('mnl_live', json.dumps(dict(op='island', sid=sid, why=why, trip=trip))))


def _state(value) -> dict:
    if isinstance(value, dict):
        return value
    try:
        data = json.loads(value or '{}')
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def _members(db, trip: str) -> list[str]:
    return [r['guest'] for r in db.execute("SELECT guest FROM island_guests WHERE trip=? AND status IN ('invited','aboard')", (trip,)).fetchall()]


def _end(db, trip: dict, why: str, now: float) -> bool:
    n = db.execute("UPDATE island_trips SET status='ended', ended=?, why=? WHERE id=? AND status='open'", (now, why, trip['id'])).rowcount
    if n:
        for sid in {trip['owner'], *_members(db, trip['id'])}:
            _notify(db, sid, 'ended', trip['id'])
    return bool(n)


def sweep(db, now: float | None = None) -> int:
    """Trips whose hour is over end (why 'time'): one indexed statement; their people are told."""
    now = mr.now() if now is None else now
    rows = db.execute("UPDATE island_trips SET status='ended', ended=?, why='time' WHERE status='open' AND ends<=? "
                      'RETURNING id, owner', (now, now)).fetchall()
    for r in rows:
        for sid in {r['owner'], *_members(db, r['id'])}:
            _notify(db, sid, 'ended', r['id'])
    return len(rows)


# ---------------------------------------------------------------- save hooks (game/storage.py)
HOOK_ACTIONS = ('jr_island_sell', 'reset_all', 'import_save')


def command_commit(db, sid: str, action: str, after) -> None:
    """In the save's transaction: an island the save no longer owns ends its open trip (a sale, a reset, an import)."""
    if action not in HOOK_ACTIONS:
        return
    have = set(isl.owned(after if isinstance(after, dict) else {}))
    now = mr.now()
    for r in mr._rows(db, "SELECT * FROM island_trips WHERE owner=? AND status='open'", (sid,)):
        if r['island'] not in have:
            _end(db, r, 'sold', now)


def forget(db, sid: str) -> None:
    """Account deletion / erase: their open trip ends, their seats go."""
    now = mr.now()
    for r in mr._rows(db, "SELECT * FROM island_trips WHERE owner=? AND status='open'", (sid,)):
        _end(db, r, 'gone', now)
    rows = db.execute("UPDATE island_guests SET status='removed', answered=? WHERE guest=? AND status IN ('invited','aboard') "
                      'RETURNING trip', (now, sid)).fetchall()
    for r in rows:
        t = mr._row(db, 'SELECT owner FROM island_trips WHERE id=?', (r['trip'],))
        if t:
            _notify(db, t['owner'], 'seat', r['trip'])


# ---------------------------------------------------------------- views
def _person(db, sid: str) -> dict:
    row = db.execute('SELECT code FROM marriage_people WHERE sid=?', (sid,)).fetchone()
    return dict(code=row['code'] if row else '', name=mr._display(db, sid), pid=social.pid_of(sid))


def _island(iid: str) -> dict:
    it = isl.ISLAND.get(iid)
    return dict(id=iid, name=it['name'], emoji=it['emoji'], look=it['look']) if it else dict(id=iid, name='Đảo riêng', emoji='🏝️', look='dua')


def _vehicle(vid: str) -> dict:
    if not vid:
        return dict(id='', name=C.ARRIVE['solo'], emoji='🚤')
    from . import garage, lux
    v = garage.VEHICLES.get(vid) or lux.ASSET.get(vid)
    return dict(id=vid, name=v['name'], emoji=v['emoji']) if v else dict(id=vid, name='Phương tiện', emoji='🛥️')


def _trip_view(db, t: dict, sid: str) -> dict:
    guests = mr._rows(db, "SELECT guest, status FROM island_guests WHERE trip=? AND status IN ('invited','aboard') "
                          'ORDER BY invited, guest', (t['id'],))
    aboard = sum(1 for g in guests if g['status'] == 'aboard')
    out = dict(id=t['id'], island=_island(t['island']), vehicle=_vehicle(t['vehicle']), kind=t['kind'], seats=int(t['seats']),
               aboard=aboard + 1, ends=float(t['ends']), owner=_person(db, t['owner']), mine=t['owner'] == sid)
    if out['mine']:
        out['guests'] = [dict(**_person(db, g['guest']), status=g['status']) for g in guests]
    return out


def listing(db, sid: str, with_friends: bool = False) -> dict:
    now = mr.now()
    mine = mr._row(db, "SELECT * FROM island_trips WHERE owner=? AND status='open' AND ends>?", (sid, now))
    rows = mr._rows(db, "SELECT t.*, g.status AS seat FROM island_guests g JOIN island_trips t ON t.id=g.trip "
                        "WHERE g.guest=? AND g.status IN ('invited','aboard') AND t.status='open' AND t.ends>? ORDER BY g.invited DESC LIMIT 12",
                    (sid, now))
    invites, aboard = [], []
    for r in rows:
        v = _trip_view(db, r, sid)
        (aboard if r['seat'] == 'aboard' else invites).append(v)
    out = dict(trip=_trip_view(db, mine, sid) if mine else None, invites=invites, aboard=aboard, minutes=MINUTES, now=now)
    if with_friends:   # mutual friends nobody blocked, names and codes only (game/home_guests.py FRIENDS_SQL)
        from .home_guests import FRIENDS_SQL as sql
        out['friends'] = [dict(code=r['code'], name=mr._clean_name(r['display'])) for r in db.execute(sql, (sid, social.pid_of(sid))).fetchall()]
    return out


# ---------------------------------------------------------------- HTTP (server.py: GET /api/island, POST /api/island/<op>)
def _actor(store, token) -> str:
    sid, display = mr.whoami(store, token)
    need(sid and display, 'Đăng nhập để ra đảo cùng bạn bè.', 'login_required', 401)
    mr.ensure_person(store, sid)
    return sid


def get(store, token, query=None) -> dict:
    sid = _actor(store, token)
    store.transaction(lambda db: sweep(db))
    with store.connect() as db:
        return listing(db, sid, with_friends=(query or {}).get('friends') == '1')


def _trip_for_update(db, trip) -> dict:
    need(isinstance(trip, str) and 1 <= len(trip) <= 32, 'Chuyến đi không hợp lệ.')
    t = mr._row(db, 'SELECT * FROM island_trips WHERE id=? FOR UPDATE', (trip,))
    need(t, 'Không tìm thấy chuyến đi này.', 'not_found', 404)
    return t


def _open(t: dict, now: float) -> None:
    need(t['status'] == 'open' and float(t['ends']) > now, 'Chuyến ra đảo này đã kết thúc.', 'ended', 409)


def _start(db, sid: str, data: dict, now: float) -> None:
    iid, vid = data.get('island'), data.get('vehicle', '')
    need(isinstance(iid, str) and iid in isl.ISLAND, 'Chọn một hòn đảo nhé.')
    need(isinstance(vid, str) and len(vid) <= 24, 'Chọn phương tiện nhé.')
    row = db.execute('SELECT state FROM sessions WHERE sid=? FOR UPDATE', (sid,)).fetchone()
    state = _state(row['state']) if row else {}
    j = state.get('journey') if isinstance(state.get('journey'), dict) else {}
    need(j.get('story'), 'Đảo riêng chỉ có trong hành trình.', 'locked', 403)
    from . import jail
    need(not jail.jailed(state, now), jail.JAILED, 'jailed', 403)
    need(iid in isl.owned(state), 'Bạn chưa có hòn đảo này.', 'not_owned', 403)
    if vid:
        v = next((x for x in isl.vehicles(state) if x['id'] == vid), None)
        need(v, 'Bạn chưa có phương tiện này, hoặc nó không chở khách ra đảo được.', 'not_owned', 403)
        seats, kind = v['seats'], v['arrive']
    else:
        seats, kind = 1, 'solo'
    seats = max(1, min(C.SEATS_MAX, int(seats)))
    got = db.execute('INSERT INTO island_trips(id, owner, island, vehicle, kind, seats, status, created, ends) '
                     "VALUES(?,?,?,?,?,?,'open',?,?) ON CONFLICT DO NOTHING RETURNING id",
                     (secrets.token_hex(8), sid, iid, vid, kind, seats, now, now + SECONDS)).fetchone()
    need(got, 'Bạn đang có một chuyến ra đảo. Kết thúc chuyến đó trước nhé.', 'busy', 409)
    _notify(db, sid, 'start', got['id'])


def _invite(db, sid: str, data: dict, now: float) -> dict:
    t = _trip_for_update(db, data.get('trip'))
    need(t['owner'] == sid, 'Chỉ chủ đảo mới mời được.', 'forbidden', 403)
    _open(t, now)
    need(t['kind'] != 'solo' and t['seats'] > 1, 'Chuyến đi một mình không chở thêm ai. Chọn du thuyền hoặc phi cơ để rủ bạn.', 'solo')
    codes = data.get('codes')
    need(isinstance(codes, list) and 1 <= len(codes) <= CODES_MAX and all(isinstance(c, str) for c in codes), 'Chọn bạn để mời nhé.')
    from . import home_coop
    sent, skipped = [], []
    taken = db.execute("SELECT COUNT(*) AS n FROM island_guests WHERE trip=? AND status IN ('invited','aboard')", (t['id'],)).fetchone()['n']
    for code in dict.fromkeys(codes):
        target = mr._find(db, mr.clean_code(code))
        if not target or target['sid'] == sid:
            skipped.append(code)
            continue
        friends, blocked = home_coop.relation(db, sid, target['sid'])
        if not friends or blocked:
            skipped.append(code)
            continue
        cur = mr._row(db, 'SELECT status FROM island_guests WHERE trip=? AND guest=?', (t['id'], target['sid']))
        if cur and cur['status'] in ('invited', 'aboard'):
            continue
        need(taken < C.INVITE_MAX, f'Một chuyến mời tối đa {C.INVITE_MAX} người.', 'limit')
        db.execute("INSERT INTO island_guests(trip, guest, status, invited) VALUES(?,?,'invited',?) "
                   "ON CONFLICT(trip, guest) DO UPDATE SET status='invited', invited=excluded.invited, answered=NULL",
                   (t['id'], target['sid'], now))
        taken += 1
        sent.append(code)
        _notify(db, target['sid'], 'invite', t['id'])
    need(sent or not skipped, 'Chỉ mời được bạn bè (cả hai đã kết bạn, không ai chặn ai).', 'not_friends')
    return dict(sent=len(sent), skipped=len(skipped))


def _answer(db, sid: str, data: dict, now: float) -> dict:
    answer = data.get('answer')
    need(answer in ('accept', 'decline'), 'Chọn lên đường hoặc để lần sau nhé.')
    t = _trip_for_update(db, data.get('trip'))   # the seats are counted under this lock
    g = mr._row(db, 'SELECT * FROM island_guests WHERE trip=? AND guest=?', (t['id'], sid))
    need(g and g['status'] in ('invited', 'left'), 'Lời mời này không còn chờ bạn.', 'not_pending', 409)
    if answer == 'decline':
        db.execute("UPDATE island_guests SET status='declined', answered=? WHERE trip=? AND guest=?", (now, t['id'], sid))
        _notify(db, t['owner'], 'seat', t['id'])
        return dict(declined=True)
    _open(t, now)
    from . import home_coop
    friends, blocked = home_coop.relation(db, t['owner'], sid)
    need(friends and not blocked, 'Lời mời không còn hiệu lực.', 'not_friends', 403)
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    from . import jail
    need(not jail.jailed(_state(row['state']) if row else {}, now), jail.JAILED, 'jailed', 403)
    aboard = db.execute("SELECT COUNT(*) AS n FROM island_guests WHERE trip=? AND status='aboard'", (t['id'],)).fetchone()['n']
    need(aboard + 1 < int(t['seats']), f'Hết chỗ rồi: {_vehicle(t["vehicle"])["name"]} chỉ chở {t["seats"]} người.', 'full', 409)
    # aboard one trip at a time: another seat this player holds is given back
    for r in mr._rows(db, "SELECT g.trip, t.owner FROM island_guests g JOIN island_trips t ON t.id=g.trip "
                          "WHERE g.guest=? AND g.status='aboard' AND g.trip<>?", (sid, t['id'])):
        db.execute("UPDATE island_guests SET status='left', answered=? WHERE trip=? AND guest=?", (now, r['trip'], sid))
        _notify(db, r['owner'], 'seat', r['trip'])
        _notify(db, sid, 'left', r['trip'])
    db.execute("UPDATE island_guests SET status='aboard', answered=? WHERE trip=? AND guest=?", (now, t['id'], sid))
    _notify(db, t['owner'], 'seat', t['id'])
    return dict(aboard=True, trip=t['id'])


def _leave(db, sid: str, data: dict, now: float) -> dict:
    t = _trip_for_update(db, data.get('trip'))
    n = db.execute("UPDATE island_guests SET status='left', answered=? WHERE trip=? AND guest=? AND status='aboard'",
                   (now, t['id'], sid)).rowcount
    need(n, 'Bạn không ở trên chuyến này.', 'not_aboard', 409)
    _notify(db, t['owner'], 'seat', t['id'])
    _notify(db, sid, 'left', t['id'])
    return dict(left=True)


def _remove(db, sid: str, data: dict, now: float) -> dict:
    t = _trip_for_update(db, data.get('trip'))
    need(t['owner'] == sid, 'Chỉ chủ đảo mới làm được.', 'forbidden', 403)
    target = mr._find(db, mr.clean_code(data.get('code')))
    need(target, 'Không tìm thấy người này.', 'not_found', 404)
    n = db.execute("UPDATE island_guests SET status='removed', answered=? WHERE trip=? AND guest=? AND status IN ('invited','aboard')",
                   (now, t['id'], target['sid'])).rowcount
    need(n, 'Người này không có trong chuyến.', 'not_aboard', 409)
    _notify(db, target['sid'], 'removed', t['id'])
    return dict(removed=True)


def _end_op(db, sid: str, data: dict, now: float) -> dict:
    t = _trip_for_update(db, data.get('trip'))
    need(t['owner'] == sid, 'Chỉ chủ đảo mới kết thúc được chuyến.', 'forbidden', 403)
    need(t['status'] == 'open', 'Chuyến này đã kết thúc rồi.', 'ended', 409)
    _end(db, t, 'owner', now)
    return dict(ended=True)


OPS = dict(start=_start, invite=_invite, answer=_answer, leave=_leave, remove=_remove, end=_end_op)


def post(store, token, sub, data) -> dict:
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    need(sub in OPS, 'Không tìm thấy mục này.', 'not_found', 404)

    def run(db):
        now = mr.now()
        sweep(db, now)
        out = OPS[sub](db, sid, data, now) or {}
        return out
    out = store.transaction(run)
    with store.connect() as db:
        listing_ = listing(db, sid, with_friends=sub == 'invite')
    return dict(listing_, done=out if isinstance(out, dict) else {})
