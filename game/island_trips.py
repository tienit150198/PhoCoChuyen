"""🏝️ Ra đảo cùng bạn bè: trips to a private island, their seats and their guests (PostgreSQL, never in saves).

The owner of an island (game/island.py, journey.island.own) starts a trip (POST start {island, vehicle}): alone
(vehicle '': the island's own boat, one seat) or in a yacht / plane they own (game/garage.py, game/lux.py) with
island_content.SEATS seats, the owner included. They invite mutual friends nobody blocked (POST invite {trip, codes}:
the game's and the chat's blocks, either way); each invitee gets a live card (pg_notify 'mnl_live' {op:'island'},
live/island.py) and accepts while seats remain (POST answer {trip, answer}). The seats are counted under the trip
row's lock (SELECT … FOR UPDATE), so two friends taking the last seat at once: one is aboard, the other is told the
trip is full. Since 19/10 a trip has no time limit (owner: "thời gian lên đảo thoải mái"): it stays open until the
owner ends it (POST end), the island is sold, the save reset or imported (command_commit, in the save's own
transaction) or the account erased; `ends` is still filled, C.UNLIMITED_SECS ahead, so an older build reading it keeps
the trip open (a trip an older build started keeps its hour). A guest leaves (POST leave: the seat is free again), the
owner may also take a guest off (POST remove). The live room (live/island.py) checks the same rows (ACCESS_SQL) on
entry and every few seconds; leaving returns the players to town.

🌍 Đảo mở cửa (19/10): the owner opens the trip to everyone (POST public {trip, open}); GET /api/island?public=1 lists
the open islands (never one whose owner and the viewer block each other either way); a player in story mode, out of
the trại tạm giữ, visits (POST visit {trip}: a row in island_visitors, counted under the trip row's lock: the owner,
the friends aboard and the visitors of the last VISIT_STALE seconds stay under C.PUBLIC_CAP, the live room's own cap
is the same) and leaves (POST leave). Closing it (or the trip ending) sends the visitors home; friends aboard stay.
One visit at a time: visiting another island leaves the first.

Rows: island_trips {id, owner, island, vehicle, kind, seats, status open|ended, created, ends, ended, why},
island_guests {trip, guest, status invited|aboard|declined|left|removed, invited, answered} (game/pg_schema.py 54),
island_public {trip, owner, island, status open|closed, opened, closed}, island_visitors {trip, guest, status
in|left|removed, at} (56). Nothing here moves money: a trip and a visit are free (the island's monthly fee pays its
crew), and no island or building earns anything.
"""
from __future__ import annotations

import json
import secrets

from . import island as isl
from . import island_content as C
from . import marriage as mr
from . import social

MINUTES = C.SESSION_MIN          # older clients' text only: a trip has no time limit since 19/10
SECONDS = C.UNLIMITED_SECS        # how far ahead a new trip's `ends` is written
VISIT_STALE = 6 * 3600            # a visitor row older than this no longer counts toward the cap (a closed browser)
LONG = 365 * 86400                # a trip ending further away than this: shown as unlimited
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
       COALESCE(pb.status, '') AS pub, COALESCE(vi.status, '') AS visit,
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
LEFT JOIN island_public pb ON pb.trip=t.id
LEFT JOIN island_visitors vi ON vi.trip=t.id AND vi.guest=v.sid
"""
# Deploy-order safety (review fix 19/10): a live service started before the game server created island_public /
# island_visitors (SCHEMA_VERSION 56) answers with the friends-only check of 2.4.60 (no public visits yet) instead of
# failing every island entry; live/island.py switches back once the tables exist.
ACCESS_SQL_FRIENDS = (ACCESS_SQL.replace("COALESCE(pb.status, '') AS pub, COALESCE(vi.status, '') AS visit", "'' AS pub, '' AS visit")
                      .replace("LEFT JOIN island_public pb ON pb.trip=t.id\n", "")
                      .replace("LEFT JOIN island_visitors vi ON vi.trip=t.id AND vi.guest=v.sid\n", ""))
assert 'island_public' not in ACCESS_SQL_FRIENDS and 'island_visitors' not in ACCESS_SQL_FRIENDS


def access_for(row, sid: str, now: float) -> str | None:
    """'owner' / 'guest' / 'visitor' while the row (ACCESS_SQL for `sid`) lets this player on the island now, else None."""
    if not row or row['status'] != 'open' or float(row['ends']) <= now:
        return None
    if row['owner'] == sid:
        return 'owner'
    if row['seat'] == 'aboard' and row['friends_ok'] and not row['blocked']:
        return 'guest'
    return 'visitor' if row['pub'] == 'open' and row['visit'] == 'in' and not row['blocked'] else None


def cap_for(row) -> int:
    """How many people the live room holds: the vehicle's seats, C.PUBLIC_CAP while the island is open to everyone."""
    seats = int(row['seats'])
    return max(seats, C.PUBLIC_CAP) if row['pub'] == 'open' else seats


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
    return [r['guest'] for r in db.execute("SELECT guest FROM island_guests WHERE trip=? AND status IN ('invited','aboard') "
                                           "UNION SELECT guest FROM island_visitors WHERE trip=? AND status='in'", (trip, trip)).fetchall()]


def _closed(db, trip: str, now: float) -> None:
    """The trip ended: it is no longer open to everyone, its visitors went home."""
    db.execute("UPDATE island_public SET status='closed', closed=? WHERE trip=? AND status='open'", (now, trip))
    db.execute("UPDATE island_visitors SET status='left', at=? WHERE trip=? AND status='in'", (now, trip))


def _end(db, trip: dict, why: str, now: float) -> bool:
    n = db.execute("UPDATE island_trips SET status='ended', ended=?, why=? WHERE id=? AND status='open'", (now, why, trip['id'])).rowcount
    if n:
        for sid in {trip['owner'], *_members(db, trip['id'])}:
            _notify(db, sid, 'ended', trip['id'])
        _closed(db, trip['id'], now)
    return bool(n)


def sweep(db, now: float | None = None) -> int:
    """Trips whose hour is over end (why 'time'): one indexed statement; their people are told."""
    now = mr.now() if now is None else now
    rows = db.execute("UPDATE island_trips SET status='ended', ended=?, why='time' WHERE status='open' AND ends<=? "
                      'RETURNING id, owner', (now, now)).fetchall()
    for r in rows:
        for sid in {r['owner'], *_members(db, r['id'])}:
            _notify(db, sid, 'ended', r['id'])
        _closed(db, r['id'], now)
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
    rows += db.execute("UPDATE island_visitors SET status='removed', at=? WHERE guest=? AND status='in' RETURNING trip", (now, sid)).fetchall()
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


def _visitors(db, trip: str, now: float) -> int:
    """Visitors counted toward the cap: in, and arrived within VISIT_STALE."""
    return db.execute("SELECT COUNT(*) AS n FROM island_visitors WHERE trip=? AND status='in' AND at>?",
                      (trip, now - VISIT_STALE)).fetchone()['n']


def _is_public(db, trip: str) -> bool:
    return bool(db.execute("SELECT 1 FROM island_public WHERE trip=? AND status='open'", (trip,)).fetchone())


def _trip_view(db, t: dict, sid: str, now: float | None = None) -> dict:
    from . import island_build as ib
    now = mr.now() if now is None else now
    guests = mr._rows(db, "SELECT guest, status FROM island_guests WHERE trip=? AND status IN ('invited','aboard') "
                          'ORDER BY invited, guest', (t['id'],))
    aboard = sum(1 for g in guests if g['status'] == 'aboard')
    builds = ib.island_rows(db, t['owner'], t['island'])
    public = _is_public(db, t['id'])
    visitors = _visitors(db, t['id'], now) if public else 0
    out = dict(id=t['id'], island=_island(t['island']), vehicle=_vehicle(t['vehicle']), kind=t['kind'], seats=int(t['seats']),
               aboard=aboard + 1, ends=float(t['ends']), owner=_person(db, t['owner']), mine=t['owner'] == sid,
               unlimited=float(t['ends']) - now > LONG, builds=builds, score=ib.row_score(builds, now),
               public=public, visitors=visitors, cap=C.PUBLIC_CAP if public else int(t['seats']))
    if out['mine']:
        out['guests'] = [dict(**_person(db, g['guest']), status=g['status']) for g in guests]
        if public:
            out['visitor_list'] = [_person(db, r['guest']) for r in db.execute(
                "SELECT guest FROM island_visitors WHERE trip=? AND status='in' ORDER BY at DESC LIMIT 40", (t['id'],)).fetchall()]
    return out


# One indexed read of the open islands a viewer may visit: never one whose owner and the viewer block each other.
OPEN_SQL = """
SELECT t.*, pb.opened FROM island_public pb JOIN island_trips t ON t.id=pb.trip
WHERE pb.status='open' AND t.status='open' AND t.ends>? AND t.owner<>?
  AND NOT EXISTS(SELECT 1 FROM marriage_blocks WHERE (sid=t.owner AND target=?) OR (sid=? AND target=t.owner))
  AND NOT EXISTS(SELECT 1 FROM blocks WHERE
    (pid=substring(encode(sha256(convert_to('pid:' || t.owner,'UTF8')),'hex'),1,16) AND target=?)
    OR (pid=? AND target=substring(encode(sha256(convert_to('pid:' || t.owner,'UTF8')),'hex'),1,16)))
ORDER BY pb.opened DESC LIMIT ?
"""
OPEN_MAX = 30


def open_list(db, sid: str, now: float) -> list:
    """🌍 The islands open to everyone right now, the most beautiful and the fullest first."""
    pid = social.pid_of(sid)
    out = []
    for r in mr._rows(db, OPEN_SQL, (now, sid, sid, sid, pid, pid, OPEN_MAX)):
        v = _trip_view(db, r, sid, now)
        v['people'] = v['aboard'] + v['visitors']
        out.append(v)
    out.sort(key=lambda v: (-v['score'], -v['people'], v['id']))
    return out


def listing(db, sid: str, with_friends: bool = False, with_public: bool = False) -> dict:
    now = mr.now()
    mine = mr._row(db, "SELECT * FROM island_trips WHERE owner=? AND status='open' AND ends>?", (sid, now))
    rows = mr._rows(db, "SELECT t.*, g.status AS seat FROM island_guests g JOIN island_trips t ON t.id=g.trip "
                        "WHERE g.guest=? AND g.status IN ('invited','aboard') AND t.status='open' AND t.ends>? ORDER BY g.invited DESC LIMIT 12",
                    (sid, now))
    invites, aboard = [], []
    for r in rows:
        v = _trip_view(db, r, sid, now)
        (aboard if r['seat'] == 'aboard' else invites).append(v)
    visiting = [dict(_trip_view(db, r, sid, now), visit=True) for r in mr._rows(
        db, "SELECT t.* FROM island_visitors v JOIN island_trips t ON t.id=v.trip JOIN island_public pb ON pb.trip=t.id "
            "WHERE v.guest=? AND v.status='in' AND pb.status='open' AND t.status='open' AND t.ends>? ORDER BY v.at DESC LIMIT 3", (sid, now))]
    out = dict(trip=_trip_view(db, mine, sid, now) if mine else None, invites=invites, aboard=aboard, visiting=visiting,
               minutes=MINUTES, unlimited=True, now=now)
    if with_public:
        out['open'] = open_list(db, sid, now)
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
        return listing(db, sid, with_friends=(query or {}).get('friends') == '1', with_public=(query or {}).get('public') == '1')


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
    n += db.execute("UPDATE island_visitors SET status='left', at=? WHERE trip=? AND guest=? AND status='in'", (now, t['id'], sid)).rowcount
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
    n += db.execute("UPDATE island_visitors SET status='removed', at=? WHERE trip=? AND guest=? AND status='in'",
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


def _public(db, sid: str, data: dict, now: float) -> dict:
    """🌍 The owner opens the island to everyone, or closes it (its visitors go home; friends aboard stay)."""
    on = data.get('open')
    need(type(on) is bool, 'Chọn mở hay đóng cửa đảo nhé.')
    t = _trip_for_update(db, data.get('trip'))
    need(t['owner'] == sid, 'Chỉ chủ đảo mới mở cửa được.', 'forbidden', 403)
    _open(t, now)
    if on:
        db.execute("INSERT INTO island_public(trip, owner, island, status, opened) VALUES(?,?,?,'open',?) "
                   "ON CONFLICT(trip) DO UPDATE SET status='open', opened=excluded.opened, closed=NULL", (t['id'], sid, t['island'], now))
    else:
        db.execute("UPDATE island_public SET status='closed', closed=? WHERE trip=? AND status='open'", (now, t['id']))
        for r in db.execute("UPDATE island_visitors SET status='removed', at=? WHERE trip=? AND status='in' RETURNING guest",
                            (now, t['id'])).fetchall():
            _notify(db, r['guest'], 'removed', t['id'])
    _notify(db, sid, 'seat', t['id'])
    return dict(public=on)


def _visit(db, sid: str, data: dict, now: float) -> dict:
    """🌍 Visiting an island open to everyone: one visit at a time, under the cap, nobody blocked, story mode, not jailed."""
    t = _trip_for_update(db, data.get('trip'))   # the cap is counted under this lock
    _open(t, now)
    if t['owner'] == sid:
        return dict(visit=False, trip=t['id'])
    need(_is_public(db, t['id']), 'Đảo này không còn mở cửa cho mọi người.', 'closed', 409)
    from . import home_coop
    _, blocked = home_coop.relation(db, t['owner'], sid)
    need(not blocked, 'Bạn không ghé đảo này được.', 'blocked', 403)
    if not data.get('_checked'):   # post() checked the save before taking the trip's lock (never parsed under it)
        _visit_check(db, sid, now)
    seat = mr._row(db, 'SELECT status FROM island_guests WHERE trip=? AND guest=?', (t['id'], sid))
    if seat and seat['status'] == 'aboard':   # a friend already aboard: the seat is theirs
        return dict(visit=False, trip=t['id'])
    cur = mr._row(db, 'SELECT status, at FROM island_visitors WHERE trip=? AND guest=?', (t['id'], sid))
    counted = cur and cur['status'] == 'in' and float(cur['at']) > now - VISIT_STALE
    aboard = db.execute("SELECT COUNT(*) AS n FROM island_guests WHERE trip=? AND status='aboard'", (t['id'],)).fetchone()['n']
    if not counted:
        need(1 + aboard + _visitors(db, t['id'], now) < C.PUBLIC_CAP, f'Đảo đông quá rồi ({C.PUBLIC_CAP} người). Ghé lại sau nhé.', 'full', 409)
    # one visit at a time: another island this player is visiting is left
    for r in mr._rows(db, "SELECT v.trip, t.owner FROM island_visitors v JOIN island_trips t ON t.id=v.trip "
                          "WHERE v.guest=? AND v.status='in' AND v.trip<>?", (sid, t['id'])):
        db.execute("UPDATE island_visitors SET status='left', at=? WHERE trip=? AND guest=?", (now, r['trip'], sid))
        _notify(db, r['owner'], 'seat', r['trip'])
        _notify(db, sid, 'left', r['trip'])
    db.execute("INSERT INTO island_visitors(trip, guest, status, at) VALUES(?,?,'in',?) "
               "ON CONFLICT(trip, guest) DO UPDATE SET status='in', at=excluded.at", (t['id'], sid, now))
    _notify(db, t['owner'], 'seat', t['id'])
    return dict(visit=True, trip=t['id'])


def _visit_check(db, sid: str, now: float) -> None:
    """A visitor is in story mode and not in the trại tạm giữ: their save, parsed once (outside any trip lock: post)."""
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    state = _state(row['state']) if row else {}
    j = state.get('journey') if isinstance(state.get('journey'), dict) else {}
    need(j.get('story'), 'Ghé đảo chỉ có trong hành trình.', 'locked', 403)
    from . import jail
    need(not jail.jailed(state, now), jail.JAILED, 'jailed', 403)


OPS = dict(start=_start, invite=_invite, answer=_answer, leave=_leave, remove=_remove, end=_end_op, public=_public, visit=_visit)


def post(store, token, sub, data) -> dict:
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    need(sub in OPS, 'Không tìm thấy mục này.', 'not_found', 404)
    data = {k: v for k, v in data.items() if k != '_checked'}
    if sub == 'visit':   # 🌍 the visitor's save is read and parsed here, before the trip row's lock (review fix 19/10)
        with store.connect() as db:
            _visit_check(db, sid, mr.now())
        data['_checked'] = True

    def run(db):
        now = mr.now()
        sweep(db, now)
        out = OPS[sub](db, sid, data, now) or {}
        return out
    out = store.transaction(run)
    with store.connect() as db:
        listing_ = listing(db, sid, with_friends=sub == 'invite', with_public=sub in ('visit', 'public', 'leave'))
    return dict(listing_, done=out if isinstance(out, dict) else {})
