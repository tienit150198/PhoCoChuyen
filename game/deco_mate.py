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


def pieces(spouse: dict, rooms: set) -> list:
    """The spouse's placed pieces as the page draws them: {id, k, r, fx, fy, f, on, z[, c]} (their ids prefixed)."""
    from . import wardrobe as wd
    L = dc.layout(spouse)
    keep = {u: q for u, q in L['pos'].items() if L['kinds'].get(u) in dc.ITEMS and q['r'] in rooms}
    # a small thing whose surface did not make it stays out too
    keep = {u: q for u, q in keep.items() if not q.get('on') or q['on'][0] == '#' or q['on'] in keep}
    out = []
    for u, q in keep.items():
        on = q.get('on', '')
        p = dict(id=PREFIX + u, k=L['kinds'][u], r=q['r'], fx=q['x'], fy=q['y'], f=q['f'],
                 on=on if not on or on[0] == '#' else PREFIX + on, z=q.get('z', 0))
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
    including when no furniture is placed, else {}. Reads the spouse's save, writes nothing."""
    try:
        return _view(store, token, state) or {}
    except Exception:  # noqa: BLE001 - a home never blocks the game
        return {}


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
