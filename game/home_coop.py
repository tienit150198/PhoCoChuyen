"""🎨 Cho trang trí (feedback #257): a friend decorates your home, with your permission, using only your furniture.

* Permission: the owner, living in a home they own (journey.home.own, deco place 'own'), grants one friend (a mutual
  friend, no block either way) "Cho trang trí" for that home: until revoked, or for GRANT_HOURS. One active grant per
  pair (home_deco_grants, a unique partial index). The owner revokes it, the friend may stop; moving, selling the
  home, an import, unfriending or a block end it (checked on every action, ended rows marked lazily by _sweep, and at
  once by command_commit when the owner's home changes).
* What a friend can do: open the owner's home in decorate mode (GET deco/view: the room projection of
  game/home_guests.py plus the owner's bag) and move pieces: place one from the owner's bag, move, flip, turn, reorder,
  put one back in the bag, put back a few spots at once (their own undo). Nothing else: no buying, selling, paints or
  colours. Furniture and money never change hands: the command is deco.apply on the OWNER's save (jr_deco_put /
  jr_deco_pick / jr_deco_layout), the friend's save is never read or written.
* Server-authoritative and concurrency-safe: marriage._mutate computes the change on a fresh copy of the owner's save
  and writes it under its revision guard, in ONE transaction with the permission check (the grant row locked FOR
  UPDATE, the friendship and blocks read again, the home the change was computed on compared with the grant) and the
  log row; a save that moved meanwhile (the owner's own edit) is computed again. The owner's next command then meets
  a newer revision and the page re-sends it against the fresh state (public/js/api.js), so neither side loses a move.
  server.py rate-limits the route.
* Every change is logged (home_deco_log: "Lan đã đặt Ghế mây", with the spots before and after). The owner can undo
  each of the latest UNDO_MAX friend changes (Hoàn tác: jr_deco_layout with the spots before), newest first when the
  same piece was touched again. LOG_KEEP rows a home owner are kept.
* Tables: PostgreSQL (game/pg_schema.py, SCHEMA_VERSION 31). Nothing is added to any save, so older builds (and a
  rollback) simply do not offer it; their deco commands see a save like any other.
"""
from __future__ import annotations

import copy
import json
import secrets

from . import deco as dc, home_guests as hg, marriage as mr, social

GRANT_HOURS = (0, 2, 24, 168)      # 0: until the owner revokes it
LOG_KEEP = 60
LOG_SHOW = 12
UNDO_MAX = 20
LAYOUT_MAX = 40
ACTS = {'put': 'jr_deco_put', 'pick': 'jr_deco_pick', 'layout': 'jr_deco_layout'}
PUT_KEYS = {'uid', 'r', 'x', 'y', 'f', 'on', 'z', 'face'}


class Same(Exception):
    """The change asked for is already there: nothing to write."""


def need(ok, message, code='home_deco_error', status=400):
    hg.need(ok, message, code, status)


def _pids(a, b):
    return social.pid_of(a), social.pid_of(b)


def relation(db, owner, guest) -> tuple[bool, bool]:
    """(mutual friends, blocked either way: the game's and the chat's blocks)."""
    pa, pb = _pids(owner, guest)
    friends = bool(db.execute('SELECT 1 WHERE EXISTS(SELECT 1 FROM friends WHERE sid=? AND friend=?) '
                              'AND EXISTS(SELECT 1 FROM friends WHERE sid=? AND friend=?)', (owner, guest, guest, owner)).fetchone())
    blocked = mr._blocked(db, owner, guest) or bool(db.execute(
        'SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?)', (pa, pb, pb, pa)).fetchone())
    return friends, blocked


def home_of(state) -> dict | None:
    """The home a save lives in when it is one they own (deco place 'own'), else None."""
    own = hg._own(state)
    if not own:
        return None
    pl = dc.place(state['journey'])
    return own if pl['where'] == 'own' and pl['key'].startswith(f"own:{own['id']}:") else None


def why_not(db, g, owner_state, now=None) -> str | None:
    """None when grant row `g` lets its friend decorate now, else the reason (the same words whatever is hidden)."""
    now = mr.now() if now is None else now
    if not g or g['status'] != 'active':
        return 'Quyền trang trí đã kết thúc.'
    if g['expires_at'] is not None and g['expires_at'] <= now:
        return 'Quyền trang trí đã hết giờ.'
    home = home_of(owner_state) if owner_state is not None else None
    if not home or (home['id'], home['kind']) != (g['home_id'], g['home_kind']):
        return 'Chủ nhà đã dọn đi hoặc đổi nhà, quyền trang trí đã kết thúc.'
    friends, blocked = relation(db, g['owner'], g['guest'])
    if not friends or blocked:
        return 'Quyền trang trí đã kết thúc.'
    return None


def _notify(db, *sids):
    for sid in set(sids):
        db.execute('SELECT pg_notify(?,?)', ('mnl_live', json.dumps(dict(t='home_changed', sid=sid))))


def _end(db, gid, status='ended'):
    return db.execute("UPDATE home_deco_grants SET status=?,ended_at=? WHERE id=? AND status='active'",
                      (status, mr.now(), gid)).rowcount


def _sweep(db, sid):
    """Mark the grants of `sid` (either side) that cannot be used any more. No session locks are taken."""
    now = mr.now()
    for g in mr._rows(db, "SELECT * FROM home_deco_grants WHERE (owner=? OR guest=?) AND status='active'", (sid, sid)):
        row = db.execute('SELECT state FROM sessions WHERE sid=?', (g['owner'],)).fetchone()
        why = why_not(db, g, hg._state(row['state']) if row else None, now)
        if why and _end(db, g['id'], 'expired' if g['expires_at'] is not None and g['expires_at'] <= now else 'ended'):
            _notify(db, g['owner'], g['guest'])


def forget(db, sid):
    """Account deletion / a save import: no grant survives, and the log forgets them both ways."""
    rows = db.execute("DELETE FROM home_deco_grants WHERE owner=? OR guest=? RETURNING owner,guest", (sid, sid)).fetchall()
    db.execute('DELETE FROM home_deco_log WHERE owner=? OR actor=?', (sid, sid))
    if rows:
        _notify(db, *{r[k] for r in rows for k in ('owner', 'guest')})


def command_commit(db, sid, before, after, action):
    """Store hook (called by home_guests.command_commit): the owner's home changed, so their grants end."""
    if action == 'import_save':
        forget(db, sid)
        return
    ident = lambda st: (lambda o: (o['id'], o['kind']) if o else None)(hg._own(st))   # noqa: E731
    if ident(before) != ident(after) or action.startswith('jr_home_'):
        home = home_of(after)
        for g in mr._rows(db, "SELECT * FROM home_deco_grants WHERE owner=? AND status='active'", (sid,)):
            if not home or (home['id'], home['kind']) != (g['home_id'], g['home_kind']):
                if _end(db, g['id']):
                    _notify(db, sid, g['guest'])


# ---------------------------------------------------------------- views
def _when(t):
    return None if t is None else float(t)


def _log_rows(db, owner, home=None, limit=LOG_SHOW):
    sql = 'SELECT * FROM home_deco_log WHERE owner=?' + (' AND home_id=? AND home_kind=?' if home else '') + ' ORDER BY id DESC LIMIT ?'
    args = (owner, home['id'], home['kind'], limit) if home else (owner, limit)
    return mr._rows(db, sql, args)


def _log_view(db, rows, owner_view, newest_ids=None):
    names = {}
    out = []
    for r in rows:
        if r['actor'] not in names:
            names[r['actor']] = mr._display(db, r['actor'])
        v = dict(id=r['id'], name=names[r['actor']], text=r['text'], at=r['at'], undone=r['undone'] is not None)
        if owner_view:
            v['undo'] = r['undone'] is None and (newest_ids is None or r['id'] in newest_ids)
        out.append(v)
    return out


def listing(db, sid) -> dict:
    """The "Cho trang trí" part of GET /api/home-guests (home_guests._list): grants both ways and the latest changes."""
    mine = [dict(id=g['id'], expires_at=_when(g['expires_at']), **hg._person(db, g['guest']),
                 home=hg._home(dict(id=g['home_id'], kind=g['home_kind'])))
            for g in mr._rows(db, "SELECT * FROM home_deco_grants WHERE owner=? AND status='active' ORDER BY created_at,id", (sid,))]
    homes = [dict(id=g['id'], expires_at=_when(g['expires_at']), **hg._person(db, g['owner']),
                  home=hg._home(dict(id=g['home_id'], kind=g['home_kind'])))
             for g in mr._rows(db, "SELECT * FROM home_deco_grants WHERE guest=? AND status='active' ORDER BY created_at,id", (sid,))]
    rows = _log_rows(db, sid)
    return dict(mine=mine, homes=homes, log=_log_view(db, rows, True, _undoable(rows)), hours=list(GRANT_HOURS))


def _undoable(rows):
    """Ids of the rows the owner may undo: the latest UNDO_MAX not undone yet (rows newest first)."""
    return {r['id'] for r in rows if r['undone'] is None}


def _access(db, sid, code, lock=False):
    """(grant, owner row from home_guests.ACCESS_SQL) for the friend `sid` and the owner's code; refused otherwise."""
    row = db.execute(hg.ACCESS_SQL, (sid, code)).fetchone()
    need(row and row['owner_sid'] != sid, 'Không tìm thấy căn nhà này.', 'not_found', 404)
    g = mr._row(db, "SELECT * FROM home_deco_grants WHERE owner=? AND guest=? AND status='active'" + (' FOR UPDATE' if lock else ''),
                (row['owner_sid'], sid))
    why = why_not(db, g, hg._state(row['owner_state']))
    need(not why, why or '', 'home_access', 403)
    return g, row


def _view(db, sid, code):
    g, row = _access(db, sid, code)
    access = dict(owner_sid=row['owner_sid'], guest_sid=sid, home_id=g['home_id'], home_kind=g['home_kind'], kind='deco')
    out = hg._projection(db, row, access, code)
    owner = copy.deepcopy(hg._state(row['owner_state']))
    public = dc.public(owner)
    out['deco']['bag'] = public['bag']
    out['deco']['count'] = public['count']
    from . import wardrobe
    out['colors']['deco'].update({b['id']: wardrobe.deco_color(owner, b['id']) for b in public['bag']})
    out['coop'] = dict(id=g['id'], expires_at=_when(g['expires_at']),
                       log=_log_view(db, _log_rows(db, row['owner_sid'], dict(id=g['home_id'], kind=g['home_kind']), 8), False))
    return out


def get(store, token, state, sub, query):
    sid = hg._actor(store, token)
    store.transaction(lambda db: _sweep(db, sid))
    with store.connect() as db:
        if sub == 'view':
            return _view(db, sid, mr.clean_code((query or {}).get('code')))
        need(sub == 'log', 'Không tìm thấy mục này.', 'not_found', 404)
        return listing(db, sid)


# ---------------------------------------------------------------- changes
def _changed(before: dict, after: dict) -> tuple[dict, dict]:
    uids = {u for u in set(before) | set(after) if before.get(u) != after.get(u)}
    return {u: before.get(u) for u in uids}, {u: after.get(u) for u in uids}


def _text(L0, L1, action, payload, was, now) -> str:
    kinds = L1['kinds']
    if action == 'layout':
        uids = list(was)
        if len(uids) == 1 and kinds.get(uids[0]) in dc.ITEMS:
            return f'đã đặt lại {dc.ITEMS[kinds[uids[0]]]["name"]} như cũ'
        return f'đã đặt lại {len(uids)} món như cũ'
    uid = payload['uid']
    name = dc.ITEMS[kinds[uid]]['name'] if kinds.get(uid) in dc.ITEMS else 'một món'
    a, b = L0['pos'].get(uid), L1['pos'].get(uid)
    if action == 'pick' or b is None:
        return f'đã cất {name} vào túi'
    if a is None:
        room = next((r['name'] for r in L1['rooms'] if r['id'] == b['r']), '')
        return f'đã đặt {name} ở {dc.lname(room)}' if room else f'đã đặt {name}'
    if a['r'] != b['r']:
        room = next((r['name'] for r in L1['rooms'] if r['id'] == b['r']), '')
        return f'đã dời {name} sang {dc.lname(room)}'
    if (a['x'], a['y'], a.get('on', '')) == (b['x'], b['y'], b.get('on', '')):
        if a.get('f', 0) != b.get('f', 0):
            return f'đã lật {name}'
        if a.get('face', 'front') != b.get('face', 'front'):
            return f'đã xoay {name}'
        if a.get('z', 0) != b.get('z', 0):
            return f'đã đổi lớp {name}'
    return f'đã dời {name}'


def _payload(action, data) -> dict:
    if action == 'pick':
        uid = data.get('uid')
        need(isinstance(uid, str) and uid != 'all' and len(uid) <= 40, 'Chọn một món để cất.')
        return dict(uid=uid)
    if action == 'put':
        p = {k: data[k] for k in PUT_KEYS if k in data}
        need(isinstance(p.get('uid'), str) and len(p['uid']) <= 40 and set(data) - {'code', 'action'} <= PUT_KEYS,
             'Chỗ này không đặt đồ được.')
        return p
    ch = data.get('set')
    need(isinstance(ch, dict) and 0 < len(ch) <= LAYOUT_MAX and all(isinstance(u, str) and len(u) <= 40 for u in ch)
         and all(v is None or isinstance(v, dict) for v in ch.values()), 'Không hoàn tác được.')
    return {'set': copy.deepcopy(ch)}


def _act(store, sid, data):
    """A friend's change to the owner's room (see the module notes)."""
    action = data.get('action')
    need(action in ACTS, 'Thao tác trang trí không hợp lệ.')
    code = mr.clean_code(data.get('code'))
    payload = _payload(action, data)
    with store.connect() as db:
        g, row = _access(db, sid, code)
    owner, gid = row['owner_sid'], g['id']
    box = {}

    def fn(state):
        home = home_of(state)
        need(home and (home['id'], home['kind']) == (g['home_id'], g['home_kind']),
             'Chủ nhà đã dọn đi hoặc đổi nhà, quyền trang trí đã kết thúc.', 'home_access', 403)
        L0 = dc.layout(state)
        before = {u: dict(q) for u, q in L0['pos'].items()}
        res = dc.apply(state, ACTS[action], copy.deepcopy(payload))
        L1 = dc.layout(state)
        was, now = _changed(before, {u: dict(q) for u, q in L1['pos'].items()})
        if res.get('duplicate') or not was:
            raise Same(res.get('message') or 'Món này đang ở đây rồi.')
        box.update(res=res, was=was, now=now, home=home, text=_text(L0, L1, action, payload, was, now))

    def ops(db):
        # The save this transaction writes is the one fn changed (revision guard): its home was compared with the grant
        # there. Here the grant itself (locked: a revoke waits for this commit or this waits for the revoke) and the
        # friendship, as they are now.
        gl = mr._row(db, 'SELECT * FROM home_deco_grants WHERE id=? FOR UPDATE', (gid,))
        now = mr.now()
        need(gl and gl['status'] == 'active' and gl['owner'] == owner and gl['guest'] == sid
             and (gl['expires_at'] is None or gl['expires_at'] > now), 'Quyền trang trí đã kết thúc.', 'home_access', 403)
        friends, blocked = relation(db, owner, sid)
        need(friends and not blocked, 'Quyền trang trí đã kết thúc.', 'home_access', 403)
        db.execute('INSERT INTO home_deco_log(owner,actor,home_id,home_kind,text,undo,after,at) VALUES(?,?,?,?,?,?,?,?)',
                   (owner, sid, box['home']['id'], box['home']['kind'], box['text'][:160],
                    json.dumps(box['was'], separators=(',', ':')), json.dumps(box['now'], separators=(',', ':')), now))
        db.execute('DELETE FROM home_deco_log WHERE owner=? AND id NOT IN (SELECT id FROM home_deco_log WHERE owner=? ORDER BY id DESC LIMIT ?)',
                   (owner, owner, LOG_KEEP))
        _notify(db, owner, sid)

    try:
        mr._mutate_retry(store, {owner: fn}, ops)
    except Same as e:
        return dict(message=str(e), duplicate=True)
    return dict(message=box['res'].get('message', ''), duplicate=False)


def _undo(store, sid, data):
    """The owner puts back the spots a friend's change moved (one log row)."""
    lid = data.get('id')
    need(type(lid) is int and lid > 0, 'Không tìm thấy thay đổi này.', 'not_found', 404)
    with store.connect() as db:
        r = mr._row(db, 'SELECT * FROM home_deco_log WHERE id=? AND owner=?', (lid, sid))
        need(r and r['undone'] is None, 'Thay đổi này đã hoàn tác hoặc không còn nữa.', 'not_found', 404)
        rows = _log_rows(db, sid, None, UNDO_MAX)
    need(lid in _undoable(rows), 'Chỉ hoàn tác được các thay đổi gần đây.', 'too_old')
    was = json.loads(r['undo'])
    newer = [x for x in rows if x['id'] > lid and x['undone'] is None and set(json.loads(x['undo'])) & set(was)]
    need(not newer, 'Món này còn một thay đổi mới hơn. Hoàn tác thay đổi mới hơn trước nhé.', 'newer')
    box = {}

    def fn(state):
        home = home_of(state)
        need(home and (home['id'], home['kind']) == (r['home_id'], r['home_kind']),
             'Thay đổi này thuộc căn nhà bạn đã dọn đi.', 'moved')
        kinds = dc.layout(state)['kinds']
        put = {u: q for u, q in was.items() if u in kinds}
        need(put, 'Món đồ này không còn nữa.', 'gone')
        box['res'] = dc.apply(state, 'jr_deco_layout', {'set': put})

    def ops(db):
        x = mr._row(db, 'SELECT * FROM home_deco_log WHERE id=? FOR UPDATE', (lid,))
        need(x and x['undone'] is None, 'Thay đổi này đã hoàn tác rồi.', 'already', 409)
        db.execute('UPDATE home_deco_log SET undone=? WHERE id=?', (mr.now(), lid))
        _notify(db, sid, x['actor'])

    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(message=box['res'].get('message', 'Đã hoàn tác.'))


def post(store, token, state, sub, data):
    sid = hg._actor(store, token)
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    need(sub in ('grant', 'revoke', 'leave', 'act', 'undo'), 'Không tìm thấy mục này.', 'not_found', 404)
    store.transaction(lambda db: _sweep(db, sid))
    if sub == 'act':
        out = _act(store, sid, data)
        with store.connect() as db:
            out['view'] = _view(db, sid, mr.clean_code(data.get('code')))
        return out
    if sub == 'undo':
        out = _undo(store, sid, data)
        with store.connect() as db:
            out['deco'] = listing(db, sid)
        return out
    if sub == 'grant':
        hours = data.get('hours', 0)
        need(type(hours) is int and hours in GRANT_HOURS, 'Chọn thời gian cho trang trí.')
        with store.connect() as db:
            target = mr._find(db, mr.clean_code(data.get('code')))
        need(target and target['sid'] != sid, 'Không tìm thấy người bạn này.', 'not_found', 404)
        guest = target['sid']

        def grant(db):
            hg.lock_pair(db, sid, guest)
            row = db.execute('SELECT state FROM sessions WHERE sid=? FOR UPDATE', (sid,)).fetchone()   # sessions first, as commands
            home = home_of(hg._state(row['state'])) if row else None
            need(home, 'Bạn cần đang ở căn nhà do mình sở hữu để cho bạn trang trí.', 'not_owner')
            friends, blocked = relation(db, sid, guest)
            need(friends and not blocked, 'Chỉ cho người đang là bạn bè của bạn trang trí.', 'not_friends')
            need(not db.execute("SELECT 1 FROM home_deco_grants WHERE owner=? AND guest=? AND status='active'", (sid, guest)).fetchone(),
                 'Người này đang có quyền trang trí nhà bạn rồi.', 'already', 409)
            now = mr.now()
            db.execute("INSERT INTO home_deco_grants(id,owner,guest,home_id,home_kind,status,created_at,expires_at) VALUES(?,?,?,?,?,'active',?,?)",
                       (secrets.token_hex(16), sid, guest, home['id'], home['kind'], now, now + hours * 3600 if hours else None))
            _notify(db, sid, guest)
        store.transaction(grant)
    else:
        gid = data.get('id')
        need(isinstance(gid, str) and len(gid) <= 64, 'Quyền trang trí không hợp lệ.')

        def end(db):
            g = mr._row(db, 'SELECT * FROM home_deco_grants WHERE id=? FOR UPDATE', (gid,))
            need(g and sid == (g['owner'] if sub == 'revoke' else g['guest']), 'Không tìm thấy quyền trang trí này.', 'not_found', 404)
            need(g['status'] == 'active', 'Quyền trang trí đã kết thúc.', 'not_active', 409)
            _end(db, gid, 'revoked' if sub == 'revoke' else 'left')
            _notify(db, g['owner'], g['guest'])
        store.transaction(end)
    with store.connect() as db:
        return dict(deco=listing(db, sid))
