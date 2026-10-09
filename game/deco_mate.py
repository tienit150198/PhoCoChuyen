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
"""
from __future__ import annotations

from . import deco as dc
from . import housing as hs
from . import marriage as mr

PREFIX = 'p:'


def _home(j: dict, couple: int) -> tuple | None:
    """('own'|'shared', home id, kind) of the home a save lives in now (a shared one only through this couple)."""
    h = j.get('home') if isinstance(j.get('home'), dict) else None
    pl = dc.place(j)
    if pl['where'] == 'own':
        return 'own', h['own']['id'], pl['kind']
    if pl['where'] == 'shared' and h['shared'].get('couple') == couple:
        return 'shared', h['shared']['id'], pl['kind']
    return None


def same_home(mine: dict, theirs: dict, couple: int) -> bool:
    """Both journeys live in one home: one owns it, the other lives there as the spouse (same id, same kind)."""
    a, b = _home(mine, couple), _home(theirs, couple)
    return bool(a and b) and {a[0], b[0]} == {'own', 'shared'} and a[1] == b[1] and a[2] == b[2]


def pieces(spouse: dict, rooms: set, prefix: str = PREFIX, name: str = '') -> list:
    """The spouse's placed pieces as the page draws them: {id, k, r, fx, fy, f, on, z[, c][, n]} (their ids prefixed;
    `n`: whose they are, when the home has more than one other resident)."""
    from . import wardrobe as wd
    L = dc.layout(spouse)
    keep = {u: q for u, q in L['pos'].items() if L['kinds'].get(u) in dc.ITEMS and q['r'] in rooms}
    # a small thing whose surface did not make it stays out too
    keep = {u: q for u, q in keep.items() if not q.get('on') or q['on'][0] == '#' or q['on'] in keep}
    out = []
    for u, q in keep.items():
        on = q.get('on', '')
        p = dict(id=prefix + u, k=L['kinds'][u], r=q['r'], fx=q['x'], fy=q['y'], f=q['f'],
                 on=on if not on or on[0] == '#' else prefix + on, z=q.get('z', 0))
        if name:
            p['n'] = name
        if q.get('face') == 'back':
            p['face'] = 'back'
        c = wd.deco_color(spouse, u)
        if c != wd.GOC:
            p['c'] = c
        out.append(p)
    return out


def _with_spouse(L: dict, spouse: dict) -> dict:
    """An ephemeral layout for use eligibility. Ownership, points and saved layouts stay with their player."""
    out = dict(L, pos=dict(L['pos']), kinds=dict(L['kinds']), _use_verified=True)
    for p in pieces(spouse, {r['id'] for r in L['rooms']}):
        out['kinds'][p['id']] = p['k']
        out['pos'][p['id']] = dc._q(p['r'], p['fx'], p['fy'], p['f'], p.get('on', ''), p.get('z', 0), p.get('face', 'front'))
    return out


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
        got = mr._read_state(store, mr._other(c, sid))
        sj = got[0].get('journey') if got else None
        if not isinstance(sj, dict) or not sj.get('story') or not same_home(state['journey'], sj, c['id']):
            return own
        return _with_spouse(L, got[0])
    except Exception:  # noqa: BLE001 - a failed spouse read must never grant access or block the player's own furniture
        return own


def view(store, token: str, state: dict | None) -> dict:
    """GET /api/deco/mate: {at, name, items, skins, parts, owner, use} for a verified common home,
    including when no furniture is placed, else {}. Reads the other residents' saves; writes only to put back the
    viewer's own furniture when their stay in a friend's home has ended ({moved: true})."""
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


def _guest_items(store, host: str, host_state: dict, rooms: set, skip=()) -> tuple[list, list]:
    """The pieces of the friends living in `host`'s home (🏡 F#307), and their names."""
    from . import home_guests as hg
    items, names = [], []
    with store.connect() as db:
        rows = hg.stay_guests(store, host, host_state, skip)
        named = [(sid, mr._clean_name(mr._display(db, sid))) for sid, _ in rows]
    for i, ((sid, gs), (_, name)) in enumerate(zip(rows, named)):
        items += pieces(gs, rooms, f'g{i}:', name)
        names.append(name)
    return items, names


def _with_guests(store, token: str, state: dict, out: dict | None) -> dict | None:
    """The host's view, or the host spouse's: the friends' pieces join the spouse's ({} when nobody else lives there)."""
    j = state['journey'] if isinstance(state, dict) and isinstance(state.get('journey'), dict) else None
    if not j or not j.get('story'):
        return out
    pl = dc.place(j)
    sid = store.key(token)
    if not sid or pl['where'] not in ('own', 'estate', 'shared'):
        return out
    host, host_state = sid, state
    if pl['where'] == 'shared':   # the spouse owns it: only through the verified common home
        if not out:
            return out
        with store.connect() as db:
            c = mr._bond(db, sid)
        host = mr._other(c, sid) if c else None
        got = mr._read_state(store, host) if host else None
        if not got:
            return out
        host_state = got[0]
    rooms = {r['id'] for r in dc.rooms_of(pl['key']) or []}
    items, names = _guest_items(store, host, host_state, rooms, skip=(sid,))
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
    from . import home_guests as hg, reno
    sid = store.key(token)
    if not sid:
        return None
    j = state['journey']
    found = hg.stay_owner(store, sid, state)
    if not found:
        st = dc.stay_of(j)
        return dict(moved=True) if hg.unstay(store, sid, st['id'] if st else None) else None
    host, host_state = found
    here = dc.place(j)['key']
    rooms = {r['id'] for r in dc.rooms_of(here) or []}
    with store.connect() as db:
        host_name = mr._clean_name(mr._display(db, host))
        c = mr._bond(db, host)
    items, names = pieces(host_state, rooms, PREFIX, host_name), [host_name]
    if c and c['status'] == 'married':   # the host's spouse, when they live there too
        got = mr._read_state(store, mr._other(c, host))
        sj = got[0].get('journey') if got else None
        if isinstance(sj, dict) and sj.get('story') and same_home(host_state['journey'], sj, c['id']):
            with store.connect() as db:
                spouse_name = mr._clean_name(mr._display(db, mr._other(c, host)))
            items += pieces(got[0], rooms, 's:', spouse_name)
            names.append(spouse_name)
    more, others = _guest_items(store, host, host_state, rooms, skip=(sid,))
    items += more
    names += others
    if len(names) == 1:
        for p in items:
            p.pop('n', None)
    mine = dc.layout(state)['skins']
    theirs = dc.layout(host_state)['skins']
    skins = {}
    for r in rooms:
        x = {k: v for k, v in {**theirs.get(r, {}), **mine.get(r, {})}.items() if v in dc.SKINS}
        if x:
            skins[r] = x
    out = dict(at=here, name=_names(names), items=items, skins=skins, owner=False, stay=True)
    structure = reno.public(host_state) if dc.place(host_state['journey'])['where'] == 'own' else None
    if structure:
        out['parts'] = structure['parts']
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
    got = mr._read_state(store, mr._other(c, sid))
    if not got:
        return None
    spouse = got[0]
    sj = spouse.get('journey')
    if not isinstance(sj, dict) or not sj.get('story') or not same_home(j, sj, c['id']):
        return None
    here = dc.place(j)['key']
    rooms = {r['id'] for r in dc.rooms_of(here) or []}
    items = pieces(spouse, rooms)
    from . import fridge, relax, reno
    owner = dc.place(j)['where'] == 'own'
    owner_state = state if owner else spouse
    skins = {r: {part: skin for part, skin in values.items() if skin in dc.SKINS}
             for r, values in dc.layout(owner_state)['skins'].items() if r in rooms}
    structure = reno.public(owner_state)
    L = _with_spouse(dc.layout(state), spouse)
    return dict(at=here, name=mr._clean_name(sp.get('name') or 'Người ấy'), items=items,
                skins=skins, parts=structure['parts'] if structure else [], owner=owner,
                use=dict(fridge=fridge.view(state, L), relax=relax.view(state, L)))
