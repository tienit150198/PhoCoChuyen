"""💞 The shared home's furniture: what the spouse has set up in the home both live in (GET /api/deco/mate).

Furniture belongs to each player's own save (game/deco.py), so in a married couple's home each spouse would only see
the pieces they placed themselves. Here a player's room also shows the spouse's pieces, READ-ONLY: computed at view
time from the spouse's save as it is stored (one row read, migrated in memory like marriage._read_state), never
written back, nothing added to either save. The two must live in the SAME home: one owns it (journey.home.own, place
key own:<id>:<kind>) and the other lives there through the marriage ('shared', shared:<couple>:<id>:<kind>) with the
same id and kind, and the couple is still married. The spouse's layout is read with deco.layout(), exactly as their
own room shows it. Their ids get a 'p:' prefix (a piece standing on one of theirs points at it the same way), so
they never mix with the player's own uids. Anything unexpected returns {}: a home never blocks the game.

The page (public/js/v4/reno.js) draws these pieces with the player's own, depth-sorted. They may be used while walking
around the home, but are not draggable, not in the bag, not counted in Ấm cúng and not touched by Cất hết or undo.
Fridge/tub eligibility rechecks the stored relationship and common home; food and clothes stay personal.
The same read also returns the homeowner's wall/floor finishes and structural parts. Finishes are updated
atomically by either resident through game/home_decor.py; their purchased skin licenses remain personal.

🏡 Ở chung (F#307): friends who moved their furniture into the home (game/home_guests.py stay_owner / stay_guests,
deco place 'stay') are residents too. The host and the spouse see their pieces ('g<n>:' ids, each with its owner's
name `n`); a friend living there sees the host's ('p:'), the host spouse's ('s:') and the other friends' pieces, the
host's parts, and the host's finishes with their own walls and floors over them (their own view only). Read-only as
above: each resident moves, sells and paints only through their own save. A friend whose stay has ended gets
{moved: true} once its save has been put back (home_guests.unstay): the page reloads its state.

Load (1000 players, saves up to 10 MB): the other residents' saves are read through residents(): one indexed query
for their sessions.revision, and a save is parsed only when its (sid, revision) is not in a small in-process LRU of
what is drawn from it (digest(): its pieces, finishes, parts and where it lives; bounded by rows and bytes). Nothing
changed: no save is parsed. The page asks again every 30 s while the room is open and visible, after each of its own
deco commands and on the live service's home_changed.
"""
from __future__ import annotations

import json
import threading
from collections import OrderedDict

from . import deco as dc
from . import housing as hs
from . import marriage as mr

PREFIX = 'p:'
CACHE_ROWS = 512
CACHE_BYTES = 8 * 1024 * 1024
_CACHE: OrderedDict = OrderedDict()   # (sid, revision) -> (digest, bytes)
_LOCK = threading.Lock()
_SIZE = [0]
PARSED = [0]                          # saves parsed by residents() (tests, metrics)


def _home(j: dict, couple: int) -> tuple | None:
    """('own'|'shared', home id, kind) of the home a save lives in now (a shared one only through this couple)."""
    h = j.get('home') if isinstance(j.get('home'), dict) else None
    pl = dc.place(j)
    if pl['where'] == 'own':
        return 'own', h['own']['id'], pl['kind']
    if pl['where'] == 'shared' and h['shared'].get('couple') == couple:
        return 'shared', h['shared']['id'], pl['kind']
    return None


def _same(a, b) -> bool:
    return bool(a and b) and {a[0], b[0]} == {'own', 'shared'} and a[1] == b[1] and a[2] == b[2]


def same_home(mine: dict, theirs: dict, couple: int) -> bool:
    """Both journeys live in one home: one owns it, the other lives there as the spouse (same id, same kind)."""
    return _same(_home(mine, couple), _home(theirs, couple))


def _dhome(d: dict, couple: int) -> tuple | None:
    """_home() of a digest."""
    if d.get('own'):
        return tuple(d['own'])
    sh = d.get('shared')
    return ('shared', sh[1], sh[2]) if sh and sh[0] == couple else None


# ---------------------------------------------------------------- what is drawn from a save, cached by revision
def _raw(state: dict) -> list:
    """Every placed piece of a save, ids as saved: [{u, k, r, x, y, f, on, z[, face][, c]}]."""
    from . import wardrobe as wd
    L = dc.layout(state)
    out = []
    for u, q in L['pos'].items():
        if L['kinds'].get(u) not in dc.ITEMS:
            continue
        p = dict(u=u, k=L['kinds'][u], r=q['r'], x=q['x'], y=q['y'], f=q['f'], on=q.get('on', ''), z=q.get('z', 0))
        if q.get('face') == 'back':
            p['face'] = 'back'
        c = wd.deco_color(state, u)
        if c != wd.GOC:
            p['c'] = c
        out.append(p)
    return out


def digest(state: dict) -> dict:
    """What the other residents' views need from one save (no full save is kept)."""
    from . import home_guests as hg, reno
    j = state.get('journey') if isinstance(state, dict) else None
    if not isinstance(j, dict) or not j.get('story'):
        return dict(story=False)
    h = j.get('home') if isinstance(j.get('home'), dict) else None
    pl = dc.place(j)
    own = ('own', h['own']['id'], pl['kind']) if pl['where'] == 'own' else None
    shared = (h['shared'].get('couple'), h['shared']['id'], pl['kind']) if pl['where'] == 'shared' else None
    structure = reno.public(state) if pl['where'] == 'own' else None
    home = hg._own(state)
    return dict(story=True, place=dict(pl), own=own, shared=shared, home=dict(id=home['id'], kind=home['kind']) if home else None,
                stay=dict(dc.stay_of(j) or {}) or None, pieces=_raw(state), skins=dc.layout(state)['skins'],
                parts=structure['parts'] if structure else None)


def _cache_get(key):
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None:
            _CACHE.move_to_end(key)
            return hit[0]
    return None


def _cache_put(key, d: dict) -> None:
    size = len(json.dumps(d, default=str, separators=(',', ':')))
    if size > CACHE_BYTES // 8:
        return
    with _LOCK:
        old = _CACHE.pop(key, None)
        if old:
            _SIZE[0] -= old[1]
        for k in [k for k in _CACHE if k[0] == key[0]]:   # an older revision of the same save is never asked again
            _SIZE[0] -= _CACHE.pop(k)[1]
        _CACHE[key] = (d, size)
        _SIZE[0] += size
        while _CACHE and (len(_CACHE) > CACHE_ROWS or _SIZE[0] > CACHE_BYTES):
            _SIZE[0] -= _CACHE.popitem(last=False)[1][1]


def residents(store, sids) -> dict:
    """{sid: digest or None} for other players' saves: their revisions in one query, a save parsed only when its
    revision is not cached."""
    sids = [s for s in dict.fromkeys(sids) if isinstance(s, str) and s]
    if not sids:
        return {}
    with store.connect() as db:
        revs = {r['sid']: r['revision'] for r in db.execute(
            f"SELECT sid,revision FROM sessions WHERE sid IN ({','.join('?' * len(sids))})", tuple(sids)).fetchall()}
    out = {}
    for sid in sids:
        if sid not in revs:
            out[sid] = None
            continue
        d = _cache_get((sid, revs[sid]))
        if d is None:
            got = mr._read_state(store, sid)
            PARSED[0] += 1
            if not got:
                out[sid] = None
                continue
            d = digest(got[0])
            _cache_put((sid, got[1]), d)
        out[sid] = d
    return out


def resident(store, sid):
    return residents(store, [sid]).get(sid) if sid else None


def pieces_of(d: dict, rooms: set, prefix: str = PREFIX, name: str = '') -> list:
    """A digest's placed pieces as the page draws them: {id, k, r, fx, fy, f, on, z[, face][, c][, n]} (ids prefixed;
    `n`: whose they are, when the home has more than one other resident)."""
    keep = {p['u']: p for p in d.get('pieces') or () if p['r'] in rooms}
    # a small thing whose surface did not make it stays out too
    keep = {u: p for u, p in keep.items() if not p['on'] or p['on'][0] == '#' or p['on'] in keep}
    out = []
    for u, p in keep.items():
        on = p['on']
        x = dict(id=prefix + u, k=p['k'], r=p['r'], fx=p['x'], fy=p['y'], f=p['f'],
                 on=on if not on or on[0] == '#' else prefix + on, z=p['z'])
        if name:
            x['n'] = name
        if p.get('face'):
            x['face'] = p['face']
        if p.get('c'):
            x['c'] = p['c']
        out.append(x)
    return out


def pieces(spouse: dict, rooms: set, prefix: str = PREFIX, name: str = '') -> list:
    """pieces_of() straight from a save (home_guests' visit view, use_layout)."""
    return pieces_of(dict(pieces=_raw(spouse)), rooms, prefix, name)


def _with_pieces(L: dict, items: list) -> dict:
    """An ephemeral layout for use eligibility. Ownership, points and saved layouts stay with their player."""
    out = dict(L, pos=dict(L['pos']), kinds=dict(L['kinds']), _use_verified=True)
    for p in items:
        out['kinds'][p['id']] = p['k']
        out['pos'][p['id']] = dc._q(p['r'], p['fx'], p['fy'], p['f'], p.get('on', ''), p.get('z', 0), p.get('face', 'front'))
    return out


def _with_spouse(L: dict, spouse: dict) -> dict:
    return _with_pieces(L, pieces(spouse, {r['id'] for r in L['rooms']}))


def use_layout(state: dict, L: dict | None = None) -> dict:
    """Furniture that may be used in this home, verified against the bound Store's marriage and spouse save.

    No command payload supplies another owner's ids or permissions. The stored marriage link and matching home
    must both still exist; moving apart, divorce, a packed piece or an unavailable save ends access immediately.
    The result exists only for fridge/relax checks and is never passed to deco._store or added to either inventory.
    """
    L = L if L is not None else dc.layout(state)
    if L.get('_use_verified'):
        return L
    own = dict(L, _use_verified=True)
    if L['place']['where'] not in ('own', 'shared') or mr.STORE is None:
        return own
    try:
        from . import couple as cp
        store = mr.STORE
        with store.connect() as db:
            c, sid = cp._sid_of(db, state)
        if not c:
            return own
        got = mr._read_state(store, mr._other(c, sid))   # as before (a command's check, not the page's polling)
        sj = got[0].get('journey') if got else None
        if not isinstance(sj, dict) or not sj.get('story') or not same_home(state['journey'], sj, c['id']):
            return own
        return _with_spouse(L, got[0])
    except Exception:  # noqa: BLE001 - a failed spouse read must never grant access or block the player's own furniture
        return own


def view(store, token: str, state: dict | None) -> dict:
    """GET /api/deco/mate: {at, name, items, skins, parts, owner, use} for a verified common home,
    including when no furniture is placed, else {}. Reads the other residents' saves (residents(): parsed only when
    changed); writes only to put back the viewer's own furniture when their stay in a friend's home has ended
    ({moved: true})."""
    try:
        j = (state or {}).get('journey')
        if isinstance(j, dict) and j.get('story') and dc.place(j)['where'] == 'stay':
            return _stay_view(store, token, state) or {}
        out = _view(store, token, state)
        return _with_guests(store, token, state, out) or {}
    except Exception:  # noqa: BLE001 - a home never blocks the game
        return {}


def _names(names: list) -> str:
    names = [n for n in dict.fromkeys(names) if n]
    return ', '.join(names[:3]) + (f' +{len(names) - 3}' if len(names) > 3 else '')


def _guest_items(store, host: str, home: dict | None, rooms: set, skip=()) -> tuple[list, list]:
    """The pieces of the friends living in `host`'s home (🏡 F#307), and their names."""
    from . import home_guests as hg
    items, names = [], []
    rows = hg.stay_guests(store, host, home, skip)
    if not rows:
        return items, names
    with store.connect() as db:
        named = [mr._clean_name(mr._display(db, sid)) for sid, _ in rows]
    for i, ((_sid, d), name) in enumerate(zip(rows, named)):
        items += pieces_of(d, rooms, f'g{i}:', name)
        names.append(name)
    return items, names


def _with_guests(store, token: str, state: dict, out: dict | None) -> dict | None:
    """The host's view, or the host spouse's: the friends' pieces join the spouse's ({} when nobody else lives there)."""
    from . import home_guests as hg
    j = state['journey'] if isinstance(state, dict) and isinstance(state.get('journey'), dict) else None
    if not j or not j.get('story'):
        return out
    pl = dc.place(j)
    sid = store.key(token)
    if not sid or pl['where'] not in ('own', 'estate', 'shared'):
        return out
    host, home = sid, hg._own(state)
    if pl['where'] == 'shared':   # the spouse owns it: only through the verified common home
        if not out:
            return out
        with store.connect() as db:
            c = mr._bond(db, sid)
        host = mr._other(c, sid) if c else None
        d = resident(store, host)
        if not d:
            return out
        home = d['home']
    rooms = {r['id'] for r in dc.rooms_of(pl['key']) or []}
    items, names = _guest_items(store, host, home, rooms, skip=(sid,))
    if not names:
        return out
    if out:
        return dict(out, items=out['items'] + items, name=_names([out['name']] + names))
    from . import reno
    res = dict(at=pl['key'], name=_names(names), items=items,
               skins={r: {k: v for k, v in x.items() if v in dc.SKINS} for r, x in dc.layout(state)['skins'].items() if r in rooms},
               owner=True, stay=True)
    structure = reno.public(state) if pl['where'] == 'own' else None   # a villa has no parts (home_guests._projection)
    if structure:
        res['parts'] = structure['parts']
    return res


def _stay_view(store, token: str, state: dict) -> dict | None:
    """🏡 A friend living in the host's home: everyone else's pieces, the host's parts and finishes under their own."""
    from . import home_guests as hg
    sid = store.key(token)
    if not sid:
        return None
    j = state['journey']
    found = hg.stay_owner(store, sid, state)
    if not found:
        st = dc.stay_of(j)
        return dict(moved=True) if hg.unstay(store, sid, st['id'] if st else None) else None
    host, hd = found
    here = dc.place(j)['key']
    rooms = {r['id'] for r in dc.rooms_of(here) or []}
    with store.connect() as db:
        host_name = mr._clean_name(mr._display(db, host))
        c = mr._bond(db, host)
    items, names = pieces_of(hd, rooms, PREFIX, host_name), [host_name]
    if c and c['status'] == 'married':   # the host's spouse, when they live there too
        other = mr._other(c, host)
        sd = resident(store, other)
        if sd and sd['story'] and _same(_dhome(hd, c['id']), _dhome(sd, c['id'])):
            with store.connect() as db:
                spouse_name = mr._clean_name(mr._display(db, other))
            items += pieces_of(sd, rooms, 's:', spouse_name)
            names.append(spouse_name)
    more, others = _guest_items(store, host, hd['home'], rooms, skip=(sid,))
    items += more
    names += others
    if len(names) == 1:
        for p in items:
            p.pop('n', None)
    mine = dc.layout(state)['skins']
    theirs = hd['skins']
    skins = {}
    for r in rooms:
        x = {k: v for k, v in {**theirs.get(r, {}), **mine.get(r, {})}.items() if v in dc.SKINS}
        if x:
            skins[r] = x
    out = dict(at=here, name=_names(names), items=items, skins=skins, owner=False, stay=True)
    if hd['parts'] is not None:
        out['parts'] = hd['parts']
    return out


def _view(store, token: str, state: dict | None) -> dict | None:
    j = (state or {}).get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return None
    sp = hs._spouse(state)
    if not sp or type(sp.get('couple')) is not int:
        return None
    sid = store.key(token)
    if not sid:
        return None
    with store.connect() as db:
        c = mr._bond(db, sid)
    if not c or c['status'] != 'married' or c['id'] != sp['couple']:
        return None
    d = resident(store, mr._other(c, sid))
    if not d or not d['story'] or not _same(_home(j, c['id']), _dhome(d, c['id'])):
        return None
    here = dc.place(j)['key']
    rooms = {r['id'] for r in dc.rooms_of(here) or []}
    items = pieces_of(d, rooms)
    from . import fridge, relax, reno
    owner = dc.place(j)['where'] == 'own'
    finishes = dc.layout(state)['skins'] if owner else d['skins']
    skins = {r: {part: skin for part, skin in values.items() if skin in dc.SKINS}
             for r, values in finishes.items() if r in rooms}
    if owner:
        structure = reno.public(state)
        parts = structure['parts'] if structure else []
    else:
        parts = d['parts'] or []
    L = _with_pieces(dc.layout(state), items)
    return dict(at=here, name=mr._clean_name(sp.get('name') or 'Người ấy'), items=items,
                skins=skins, parts=parts, owner=owner,
                use=dict(fridge=fridge.view(state, L), relax=relax.view(state, L)))
