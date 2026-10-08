"""Explicit friend permissions for read-only visits and indefinite cohabitation.

Permissions live in PostgreSQL, never in imported saves. Each permission names
one owner and the exact occupied house. The shared SQL/pure resolver is also
used by the asynchronous live service, including while the owner is offline.
"""
from __future__ import annotations

import copy
import json
import secrets

from . import deco as dc, deco_mate as dm, housing as hs, marriage as mr, reno, social, wardrobe

VISIT_SECONDS = 2 * 3600
LOCK_PAIR_SQL = 'SELECT pg_advisory_xact_lock(hashtextextended(?,0))'


def pair_lock_key(a, b):
    return 'home_guests:' + ':'.join(sorted((a, b)))


def lock_pair(db, a, b):
    # SELECT alone does not start a PgConnection transaction.
    db.begin()
    db.execute(LOCK_PAIR_SQL, (pair_lock_key(a, b),))


class HomeGuestError(mr.MarriageError):
    pass


def need(ok, message, code='home_guest_error', status=400):
    if not ok:
        raise HomeGuestError(message, code, status)


# Exactly (viewer_sid, owner_code), compatible with game.db and live.db.
# PostgreSQL's built-in SHA256 matches social.pid_of, including players who
# have not created a social profile yet.
ACCESS_SQL = """
WITH viewer AS (SELECT ?::text AS sid)
SELECT o.sid AS owner_sid, v.sid AS guest_sid, os.state AS owner_state,
       gs.state AS guest_state, i.id AS invite_id, i.kind AS invite_kind,
       i.status AS invite_status, i.home_id, i.home_kind, i.expires_at,
       c.id AS couple_id, c.status AS couple_status,
       (EXISTS(SELECT 1 FROM friends WHERE sid=o.sid AND friend=v.sid)
        AND EXISTS(SELECT 1 FROM friends WHERE sid=v.sid AND friend=o.sid)) AS friends_ok,
       (EXISTS(SELECT 1 FROM marriage_blocks WHERE
          (sid=o.sid AND target=v.sid) OR (sid=v.sid AND target=o.sid))
        OR EXISTS(SELECT 1 FROM blocks WHERE
          (pid=substring(encode(sha256(convert_to('pid:' || o.sid,'UTF8')),'hex'),1,16)
           AND target=substring(encode(sha256(convert_to('pid:' || v.sid,'UTF8')),'hex'),1,16))
          OR (pid=substring(encode(sha256(convert_to('pid:' || v.sid,'UTF8')),'hex'),1,16)
           AND target=substring(encode(sha256(convert_to('pid:' || o.sid,'UTF8')),'hex'),1,16)))) AS blocked
FROM marriage_people o CROSS JOIN viewer v
JOIN accounts oa ON oa.sid=o.sid
JOIN accounts ga ON ga.sid=v.sid
JOIN sessions os ON os.sid=o.sid
JOIN sessions gs ON gs.sid=v.sid
LEFT JOIN home_guest_invites i ON i.owner=o.sid AND i.guest=v.sid
  AND i.status IN ('pending','accepted')
LEFT JOIN marriage_bonds b ON b.sid=o.sid
LEFT JOIN couples c ON c.id=b.couple AND ((c.a=o.sid AND c.b=v.sid) OR (c.b=o.sid AND c.a=v.sid))
  AND EXISTS(SELECT 1 FROM marriage_bonds reciprocal WHERE reciprocal.sid=v.sid AND reciprocal.couple=c.id)
WHERE o.code=?
"""

# Friend pickers need names/codes, never hundreds of friends' serialized saves.
FRIENDS_SQL = """
WITH viewer AS (SELECT ?::text AS sid, ?::text AS pid)
SELECT p.code,a.display FROM viewer v JOIN friends f ON f.sid=v.sid
JOIN marriage_people p ON p.sid=f.friend JOIN accounts a ON a.sid=f.friend
WHERE EXISTS(SELECT 1 FROM friends r WHERE r.sid=f.friend AND r.friend=v.sid)
AND NOT EXISTS(SELECT 1 FROM marriage_blocks WHERE
    (sid=v.sid AND target=f.friend) OR (sid=f.friend AND target=v.sid))
AND NOT EXISTS(SELECT 1 FROM blocks WHERE
    (pid=v.pid AND target=substring(encode(sha256(convert_to('pid:' || f.friend,'UTF8')),'hex'),1,16))
    OR (target=v.pid AND pid=substring(encode(sha256(convert_to('pid:' || f.friend,'UTF8')),'hex'),1,16)))
ORDER BY a.display,p.code
"""


def _state(value):
    if isinstance(value, dict):
        return value
    try:
        data = json.loads(value or '{}')
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def _own(state):
    j = state.get('journey') or {}
    h = j.get('home') or {}
    own = h.get('own')
    if not j.get('story') or not isinstance(own, dict) or own.get('kind') not in hs.HOMES or not own.get('id'):
        return None
    return own


def _invitation_valid(row):
    own = _own(_state(row['owner_state']))
    return bool(own and row['friends_ok'] and not row['blocked']
                and row['home_id'] == own['id'] and row['home_kind'] == own['kind'])


def access_from_row(row, now=None):
    """Pure authorization; returns private room identity or None, never save data."""
    if not row:
        return None
    owner = _state(row['owner_state'])
    own = _own(owner)
    if not own:
        return None
    kind = None
    if row['owner_sid'] == row['guest_sid']:
        kind = 'owner'
    elif row['blocked']:
        return None
    elif row['couple_status'] == 'married' and row['couple_id']:
        guest = _state(row['guest_state'])
        sp = hs._spouse(guest)
        osp = hs._spouse(owner)
        if sp and osp and sp.get('couple') == osp.get('couple') == row['couple_id']:
            if dm.same_home(owner.get('journey') or {}, guest.get('journey') or {}, row['couple_id']):
                kind = 'spouse'
    if kind is None and row['invite_status'] == 'accepted' and _invitation_valid(row):
        now = mr.now() if now is None else now
        if row['invite_kind'] == 'stay' and row['expires_at'] is None:
            kind = 'stay'
        elif row['invite_kind'] == 'visit' and row['expires_at'] is not None and row['expires_at'] > now:
            kind = 'visit'
    if kind is None:
        return None
    return dict(owner_sid=row['owner_sid'], guest_sid=row['guest_sid'], home_id=own['id'], home_kind=own['kind'], kind=kind)


def _person(db, sid):
    row = db.execute('SELECT code FROM marriage_people WHERE sid=?', (sid,)).fetchone()
    return dict(code=row['code'] if row else '', name=mr._display(db, sid))


def _home(own):
    if not own:
        return None
    meta = hs.HOMES[own['kind']]
    return dict(id=own['id'], kind=own['kind'], name=meta['name'], emoji=meta['emoji'])


def _notify(db, *sids):
    for sid in set(sids):
        db.execute('SELECT pg_notify(?,?)', ('mnl_live', json.dumps(dict(t='home_changed', sid=sid))))


def invalidate(db, sid):
    """Persist lost access after owner moves, unfriend/block, or visit timeout.

    Safe after a sessions write in that same transaction. No session locks are
    acquired here; callers doing mutations already hold their session locks.
    """
    rows = mr._rows(db, "SELECT i.*,p.code FROM home_guest_invites i LEFT JOIN marriage_people p ON p.sid=i.owner "
                       "WHERE (i.owner=? OR i.guest=?) AND i.status IN ('pending','accepted') ORDER BY i.id", (sid, sid))
    for invite in rows:
        row = db.execute(ACCESS_SQL, (invite['guest'], invite['code'])).fetchone() if invite['code'] else None
        expired = invite['expires_at'] is not None and invite['expires_at'] <= mr.now()
        if expired or not row or not _invitation_valid(row):
            changed = db.execute("UPDATE home_guest_invites SET status=? WHERE id=? AND status IN ('pending','accepted')",
                                 ('expired' if expired else 'revoked', invite['id'])).rowcount
            if changed:
                _notify(db, invite['owner'], invite['guest'])


def forget(db, sid):
    """Account deletion/save import: imported house ids cannot revive permission."""
    rows = db.execute('DELETE FROM home_guest_invites WHERE owner=? OR guest=? RETURNING owner,guest', (sid, sid)).fetchall()
    if rows:
        _notify(db, *{r[k] for r in rows for k in ('owner', 'guest')})
    from . import home_coop   # 🎨 Cho trang trí: its grants and log
    home_coop.forget(db, sid)


def command_commit(db, sid, before, after, action):
    """Store hook after save replacement; invalidation belongs to that commit."""
    if action == 'import_save':
        forget(db, sid)
        return
    previous, current = _own(before), _own(after)
    identity = lambda home: (home['id'], home['kind']) if home else None
    if action.startswith('jr_home_') or identity(previous) != identity(current):
        invalidate(db, sid)
        from . import home_coop   # 🎨 Cho trang trí ends with the home it was given for
        home_coop.command_commit(db, sid, before, after, action)


def _actor(store, token):
    sid, display = mr.whoami(store, token)
    need(sid and display, 'Đăng nhập để mời bạn về nhà.', 'login_required', 401)
    mr.ensure_person(store, sid)
    return sid


def _list(db, sid):
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    own = _own(_state(row['state'])) if row else None
    outgoing, incoming, active, homes = [], [], [], []
    for r in mr._rows(db, "SELECT * FROM home_guest_invites WHERE (owner=? OR guest=?) AND status IN ('pending','accepted') ORDER BY created_at,id", (sid, sid)):
        mine = r['owner'] == sid
        other = _person(db, r['guest'] if mine else r['owner'])
        item = dict(id=r['id'], kind=r['kind'], status=r['status'], **other, home=_home(dict(id=r['home_id'], kind=r['home_kind'])),
                    mine=mine, expires_at=r['expires_at'])
        if r['status'] == 'pending':
            (outgoing if mine else incoming).append(item)
        else:
            active.append(item)
            if not mine:
                homes.append(dict(**other, home=item['home'], kind=r['kind']))
    friends = [dict(code=r['code'], name=mr._clean_name(r['display']))
               for r in db.execute(FRIENDS_SQL, (sid, social.pid_of(sid))).fetchall()]
    from . import home_coop   # 🎨 Cho trang trí (an older page ignores the key)
    return dict(own_home=dict(**_person(db, sid), home=_home(own)) if own else None,
                friends=friends, incoming=incoming, outgoing=outgoing, active=active, homes=homes,
                deco=home_coop.listing(db, sid))


def _projection(db, row, access, code):
    # Build on an isolated copy; public() helpers must not observe/mutate owners'
    # live state. Return only explicitly allowed room and furniture fields.
    owner = copy.deepcopy(_state(row['owner_state']))
    public = dc.public(owner)
    need(public, 'Không tìm thấy căn nhà này.', 'not_found', 404)
    deco = {key: public[key] for key in ('place', 'rooms', 'more', 'items')}
    deco['place']['repairs'] = False
    structure = reno.public(owner)
    safe_reno = {key: structure[key] for key in ('home', 'rooms', 'parts')} if structure else None
    mate = {}
    bond = mr._bond(db, row['owner_sid'])
    if bond and bond['status'] == 'married':
        other_sid = mr._other(bond, row['owner_sid'])
        saved = db.execute('SELECT state FROM sessions WHERE sid=?', (other_sid,)).fetchone()
        other = _state(saved['state']) if saved else {}
        if dm.same_home(owner.get('journey') or {}, other.get('journey') or {}, bond['id']):
            layout = dc.layout(owner)
            mate = dict(at=layout['place']['key'], name=mr._display(db, other_sid),
                        items=dm.pieces(other, {r['id'] for r in layout['rooms']}),
                        skins=copy.deepcopy(layout['skins']), parts=safe_reno['parts'] if safe_reno else [], owner=True)
    colors = {p['id']: wardrobe.deco_color(owner, p['id']) for p in deco['items']}
    return dict(owner=_person(db, row['owner_sid']), deco=deco, reno=safe_reno, mate=mate, colors=dict(deco=colors),
                access=dict(code=code, kind=access['kind']), live=dict(code=code))


def get(store, token, state, sub, query):
    from . import home_coop
    if isinstance(sub, str) and sub.startswith('deco/'):   # 🎨 Cho trang trí: deco/view, deco/log
        return home_coop.get(store, token, state, sub[5:], query)
    sid = _actor(store, token)
    from . import friends
    friends.ensure_codes(store, sid)
    store.transaction(lambda db: (invalidate(db, sid), home_coop._sweep(db, sid)))
    with store.connect() as db:
        if sub in ('', None):
            return _list(db, sid)
        need(sub == 'view', 'Không tìm thấy mục này.', 'not_found', 404)
        code = mr.clean_code((query or {}).get('code'))
        row = db.execute(ACCESS_SQL, (sid, code)).fetchone()
        access = access_from_row(row)
        need(access, 'Bạn chưa có quyền ghé căn nhà này hoặc lời mời đã kết thúc.', 'home_access', 403)
        return _projection(db, row, access, code)


def post(store, token, state, sub, data):
    if isinstance(sub, str) and sub.startswith('deco/'):   # 🎨 Cho trang trí: grant, revoke, leave, act, undo
        from . import home_coop
        return home_coop.post(store, token, state, sub[5:], data)
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Yêu cầu không hợp lệ.')
    need(sub in ('invite', 'answer', 'revoke', 'leave'), 'Không tìm thấy mục này.', 'not_found', 404)
    store.transaction(lambda db: invalidate(db, sid))
    with store.connect() as db:
        if sub == 'invite':
            kind = data.get('kind')
            need(kind in ('visit', 'stay'), 'Chọn ghé thăm hoặc ở cùng.')
            target = mr._find(db, mr.clean_code(data.get('code')))
            need(target and target['sid'] != sid, 'Không tìm thấy người bạn này.', 'not_found', 404)
            owner, guest = sid, target['sid']
        else:
            ident = data.get('id')
            need(isinstance(ident, str) and len(ident) <= 64, 'Lời mời không hợp lệ.')
            saved = mr._row(db, 'SELECT * FROM home_guest_invites WHERE id=?', (ident,))
            need(saved and sid in (saved['owner'], saved['guest']), 'Không tìm thấy lời mời.', 'not_found', 404)
            owner, guest = saved['owner'], saved['guest']
    def run(db):
        lock_pair(db, owner, guest)
        # All writers lock sessions first and in lexical order, then invitation.
        states = {member: db.execute('SELECT state FROM sessions WHERE sid=? FOR UPDATE', (member,)).fetchone()
                  for member in sorted({owner, guest})}
        need(all(states.values()), 'Không tìm thấy người chơi.', 'not_found', 404)
        invalidate(db, owner)
        owner_code = _person(db, owner)['code']
        relation = db.execute(ACCESS_SQL, (guest, owner_code)).fetchone()
        if sub == 'invite':
            own = _own(_state(states[owner]['state']))
            need(own, 'Bạn cần đang ở căn nhà do mình sở hữu để mời bạn.', 'not_owner')
            need(relation and relation['friends_ok'] and not relation['blocked'], 'Chỉ mời người đang là bạn bè của bạn.', 'not_friends')
            need(not relation['invite_id'], 'Bạn đã có lời mời hoặc quyền ở cùng với người này.', 'already', 409)
            db.execute("INSERT INTO home_guest_invites(id,owner,guest,home_id,home_kind,kind,status,created_at) VALUES(?,?,?,?,?,?,'pending',?)",
                       (secrets.token_hex(16), owner, guest, own['id'], own['kind'], kind, mr.now()))
        else:
            r = mr._row(db, 'SELECT * FROM home_guest_invites WHERE id=? FOR UPDATE', (ident,))
            need(r, 'Không tìm thấy lời mời.', 'not_found', 404)
            if sub == 'answer':
                need(sid == guest and r['status'] == 'pending', 'Lời mời không còn chờ bạn trả lời.', 'not_pending', 409)
                answer = data.get('answer')
                need(answer in ('accept', 'decline'), 'Chọn nhận hoặc từ chối lời mời.')
                need(relation and _invitation_valid(relation), 'Lời mời không còn hiệu lực.', 'home_access', 403)
                status = 'accepted' if answer == 'accept' else 'declined'
                expires = mr.now() + VISIT_SECONDS if status == 'accepted' and r['kind'] == 'visit' else None
                db.execute('UPDATE home_guest_invites SET status=?,expires_at=? WHERE id=?', (status, expires, ident))
            else:
                need(sid == (owner if sub == 'revoke' else guest), 'Bạn không thể đổi lời mời này.', 'forbidden', 403)
                need(r['status'] in (('pending', 'accepted') if sub == 'revoke' else ('accepted',)), 'Lời mời đã kết thúc.', 'not_active', 409)
                db.execute('UPDATE home_guest_invites SET status=? WHERE id=?', ('revoked' if sub == 'revoke' else 'left', ident))
        _notify(db, owner, guest)
        return _list(db, sid)
    return store.transaction(run)
