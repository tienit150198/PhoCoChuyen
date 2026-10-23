"""🗺️ Tổng quan nhà: the whole house at a glance, for every place a player can live in (story mode).

Owner 23/10: "nhìn được tổng quan cái nhà nữa, mỗi nhà nhìn tổng quan với tương tác ok hơn". The interior view
(public/js/v4/reno.js) shows one room at a time; this is the cutaway above it (public/js/v4/home-overview.js): every
floor, every room, the garden, the pool and the garage, who is home, how many pieces stand in each room and their
Ấm cúng, and a tap on a room hands over to the interior view on that room.

Nothing here is stored. PLANS are built once from the same rooms the interior uses (game/deco.py rooms_of: the home's
rooms, its bathroom and pool kits, a villa's floors from game/estates.py), so a room in the plan is always a room the
interior can open. A home kind without floors of its own (the apartments, the rented rooms, the old houses) gets
DEFAULT_UP: in a nhà phố or a biệt thự the bedrooms, the balcony and the bathroom are upstairs.

public(s, deco_public) adds the per-save part (journey.public 'homelife.ov'): the place's plan kind, each room's
[pieces, Ấm cúng] (room_stats, from what deco.public already computed: no second layout), who is home (you, the
household's child and pet, your pets) and the other homes you own (their plan without furniture: furniture lives where
you live). The spouse and friends staying come from the pages the client already reads (/api/marriage, /api/home-guests).
"""
from __future__ import annotations

from . import deco_content as DC
from . import estates_content as EC
from . import housing as hs

FLOOR_NAMES = {1: 'Tầng trệt', 2: 'Lầu 1', 3: 'Lầu 2', 4: 'Lầu 3'}
GARDEN = ('yard', 'pavilion', 'pool', 'infinity')          # outdoors on the ground floor: the garden
DEFAULT_UP = ('bed', 'bed2', 'balcony', 'bath')            # upstairs in a nhà phố / biệt thự without floors of its own
STOREYS = ('townhouse', 'villa')                           # the housing groups built on more than one floor
PET_EMOJI = {'dog': '🐶', 'cat': '🐱'}
RENT_PLACES = ('attic',) + tuple(DC.RENT_ROOMS)            # Bà Tám's attic and the rented rooms ('tro_moi', 'ky_tuc_xa')
ESTATE = {e['id']: e for e in EC.ESTATES}


def _dc():
    from . import deco
    return deco


def _key(kind: str) -> str | None:
    """A deco place key whose rooms are this kind's (the same ones the interior draws)."""
    if kind == 'attic':
        return 'attic'
    if kind in DC.RENT_ROOMS:
        return f'rent:{kind}:1'
    if kind in ESTATE:
        return f'estate:{kind}:1'
    if kind in hs.HOMES and hs.HOMES[kind]['kind'] == 'own':
        from . import estates
        return estates.v2_key(dict(key=f'own:plan:{kind}', where='own', kind=kind))['key']
    return None


def kinds() -> tuple:
    """Every kind of place with a plan: the attic, the rented rooms, the homes to buy, the villas of Mua sắm."""
    return RENT_PLACES + tuple(hs.OWN) + tuple(ESTATE)


def _meta(kind: str) -> dict:
    if kind == 'attic':
        return dict(name=hs.ATTIC['name'], emoji=hs.ATTIC['emoji'], group='rent')
    if kind in ESTATE:
        e = ESTATE[kind]
        return dict(name=e['name'], emoji=e['emoji'], group='estate')
    h = hs.HOMES[kind]
    return dict(name=h['name'], emoji=h['emoji'], group=h['group'])


def _zone(room: dict, fl: int) -> str:
    if not room.get('out'):
        return 'in'
    return 'garden' if fl == 1 and room['type'] in GARDEN else 'deck'


_PLANS: dict = {}


def plan_of(kind: str) -> dict | None:
    """The cutaway of a kind of place (None: a kind this build does not know). Shared, never changed."""
    if kind in _PLANS:
        return _PLANS[kind]
    key = _key(kind) if isinstance(kind, str) else None
    rooms = _dc().rooms_of(key) if key else None
    if not rooms:
        return None
    meta = _meta(kind)
    floors: dict = {}
    for r in rooms:
        fl = r.get('fl')
        if not fl:
            fl = 2 if meta['group'] in STOREYS and r['type'] in DEFAULT_UP else 1
        floors.setdefault(int(fl), []).append(dict(id=r['id'], type=r['type'], emoji=r['emoji'], name=r['name'],
                                                   cols=r['cols'], frows=r['frows'], zone=_zone(r, int(fl))))
    from . import villa_garage as vg
    out = dict(kind=kind, **meta,
               floors=[dict(fl=n, name='Căn hộ' if meta['group'] == 'apartment' else FLOOR_NAMES.get(n, f'Lầu {n - 1}'),
                            rooms=floors[n]) for n in sorted(floors)],
               garage=vg.spec(kind))
    out['has'] = dict(garden=any(r['zone'] == 'garden' for f in out['floors'] for r in f['rooms']),
                      pool=any(r['type'] in ('pool', 'infinity') for f in out['floors'] for r in f['rooms']),
                      garage=out['garage']['style'] == 'ham', floors=len(out['floors']))
    if len(_PLANS) < 64:
        _PLANS[kind] = out
    return out


def room_ids(kind: str) -> list:
    p = plan_of(kind)
    return [r['id'] for f in p['floors'] for r in f['rooms']] if p else []


def catalogue() -> dict:
    """Every plan, once (bootstrap content)."""
    return {k: p for k in kinds() if (p := plan_of(k))}


# ---------------------------------------------------------------- the per-save part
def room_stats(dpub: dict | None) -> dict:
    """{room id: [pieces placed, Ấm cúng]} from deco.public: each kind placed in the room counts its cozy once there,
    and a theme set completed in that room adds its bonus (the home's total counts a kind once for the whole home,
    deco.points: a room's figure is that room's share, for the overview only)."""
    if not isinstance(dpub, dict):
        return {}
    items = DC.ITEMS
    out: dict = {}
    kinds_in: dict = {}
    for it in dpub.get('items') or ():
        rid, k = it.get('r'), it.get('k')
        if not isinstance(rid, str) or k not in items:
            continue
        out.setdefault(rid, [0, 0])[0] += 1
        kinds_in.setdefault(rid, set()).add(k)
    for rid, ks in kinds_in.items():
        out[rid][1] += sum(items[k]['cozy'] for k in ks)
    for st in dpub.get('sets') or ():
        if st.get('done') and isinstance(st.get('room'), str) and st.get('id') in DC.SETS:
            out.setdefault(st['room'], [0, 0])[1] += DC.SETS[st['id']]['bonus']
    return out


def place_kind(dpub: dict | None) -> str | None:
    """The plan kind of the place you live in (deco.public place: 'attic' has no home kind)."""
    pl = dpub.get('place') if isinstance(dpub, dict) else None
    if not isinstance(pl, dict):
        return None
    kind = 'attic' if pl.get('where') == 'attic' else pl.get('kind')
    return kind if plan_of(kind) else None


def who(s: dict) -> list:
    """Who is home in the save itself: you, the household's child and pet (game/household.py), your pets (game/pets.py).
    [{k, n?, e}]: k 'me' | 'child' | 'pet'."""
    j = s['journey']
    out = [dict(k='me', e='🙂')]
    hh = j.get('household') if isinstance(j.get('household'), dict) else {}
    from . import household
    for key in ('child', 'pet'):
        m = hh.get(key)
        if isinstance(m, dict) and isinstance(m.get('name'), str) and m.get('kind') in household.KINDS:
            out.append(dict(k='child' if key == 'child' else 'pet', n=m['name'], e=household.KINDS[m['kind']][0]))
    pets = j.get('pets') if isinstance(j.get('pets'), dict) else {}
    from . import pets_content as PC
    for p in (pets.get('list') or [])[:6]:
        if isinstance(p, dict) and isinstance(p.get('n'), str):
            br = PC.BREEDS.get(p.get('b')) or {}
            out.append(dict(k='pet', n=p['n'], e=PET_EMOJI.get(br.get('kind'), '🐾')))
    return out


def homes(s: dict, here: str | None) -> list:
    """The places to look at: where you live first, then the other homes you own (housing.py props, game/lux.py villas)."""
    j = s['journey']
    out = [dict(kind=here, live=True)] if here else []
    seen = {here}
    h = j.get('home') if isinstance(j.get('home'), dict) else {}
    mine = ([h['own']] if isinstance(h.get('own'), dict) else []) + [x for x in (h.get('props') or []) if isinstance(x, dict)]
    lux = j.get('lux') if isinstance(j.get('lux'), dict) else {}
    kinds_ = [x.get('kind') for x in mine] + [k for k in (lux.get('own') or {}) if k in ESTATE]
    for k in kinds_:
        if k not in seen and plan_of(k):
            seen.add(k)
            out.append(dict(kind=k, live=False))
    return out[:12]


def public(s: dict, dpub: dict | None) -> dict | None:
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    kind = place_kind(dpub)
    pl = (dpub or {}).get('place') or {}
    rooms, hs = room_stats(dpub), homes(s, kind)
    # Small (it rides on every state): no rooms map while nothing is placed, the homes list only with a second home.
    return dict(kind=kind, where=pl.get('where'), **({'rooms': rooms} if rooms else {}), who=who(s), **({'homes': hs} if len(hs) > 1 else {}))
