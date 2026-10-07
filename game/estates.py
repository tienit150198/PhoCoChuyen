"""🏰 Dinh thự: living in a villa bought in Mua sắm, and the rooms of every villa (catalogue: game/estates_content.py).

* A villa is owned in journey.lux.own (bought, sold back at 60 %, billed every tháng by game/lux.py). `journey.lux.live`
  says the player lives there (jr_lux_live); game/deco.py then sets up its rooms: place() gives the key
  'estate:<id>:<day bought>', rooms_of() its rooms. An older build does not know that key, so its deco.validate checks
  those layouts by shape only and its own place (the home in journey.home, or Bà Tám's attic) shows the furniture in
  the bag: never refused, never lost.
* Biệt thự Sông Hồng (game/housing.py) gets the bigger three-floor inside (SONG_HONG_V2) under the place key
  '<its old key>:v2', for the same reason; a layout saved under the old key is read as the same place (deco.upgrade
  renames it, every piece at its exact spot). That holds because rooms_of() builds each room the house already had as
  a strict superset of it (superset()): never fewer columns or rows, and a SONG_HONG_V2 fixture keeps only the cells
  that lie outside the old room or where the old room had the same fixture. As 1.9.11 shipped it (legacy_rooms(), what
  a 1.9.11..1.9.17 build still uses), the kitchen and the second bedroom had a row less and new windows / a longer
  counter over old floor and wall cells: 139 pieces of 16 players went to the bag on 07/10. deco._store writes what
  those builds accept where they read it, the rest in journey.decor_wide (they ignore it: those pieces wait in their bag).
* Living there: the day's "tiền phòng" is the villa's điện nước (`power`), the cozy morning follows a home you own
  (game/reno.py steps), and the infinity pool counts as a pool for game/relax.py. There are no parts to repair: the
  staff the monthly bill pays keep it.
"""
from __future__ import annotations

from . import estates_content as EC

ESTATE = {e['id']: e for e in EC.ESTATES}
V2 = ':v2'
KEY = 'estate'
WROWS = 2
_ROOMS: dict = {}


def _dc():
    from . import deco_content
    return deco_content


def _fx(t, layer, x, y, w=1, h=1, surface=0):
    return dict(t=t, layer=layer, x=x, y=y, w=w, h=h, surface=surface)


def _door(x):
    return [_fx('door', 'wall', x, 0, 1, 2), _fx('door', 'floor', x, 0)]


def fixtures(rtype: str, c: int) -> list:
    """The built-in fixtures of a villa room of type `rtype`, `c` columns wide (its signature piece among them)."""
    if rtype == 'living':
        return [_fx('window', 'wall', 1, 0, 3, 2), _fx('window', 'wall', c - 5, 0, 2, 2)] + _door(c - 1)
    if rtype in ('bed', 'bed2', 'suite'):
        return _door(0) + [_fx('window', 'wall', c - 4, 0, 3, 2)]
    if rtype == 'kitchen':
        return [_fx('counter', 'floor', 0, 0, c - 2, 1, surface=30), _fx('splash', 'wall', 0, 1, c - 2, 1),
                _fx('window', 'wall', 1, 0, 3, 1)] + _door(c - 1)
    if rtype == 'study':
        return [_fx('bookwall', 'wall', 0, 0, 3, 2), _fx('window', 'wall', 4, 0, 2, 2)] + _door(c - 1)
    if rtype == 'cinema':
        return [_fx('screen', 'wall', 1, 0, c - 4, 2)] + _door(c - 1)
    if rtype == 'cellar':
        return [_fx('racks', 'wall', 0, 0, c - 2, 2)] + _door(c - 1)
    if rtype == 'gym':
        return [_fx('mirror', 'wall', 0, 0, 4, 2), _fx('window', 'wall', 5, 0, 2, 2)] + _door(c - 1)
    if rtype == 'closet':
        return [_fx('rails', 'wall', 0, 0, c - 3, 2)] + _door(c - 1)
    if rtype == 'showroom':
        return [_fx('gate', 'wall', c - 4, 0, 3, 2), _fx('gate', 'floor', c - 4, 0, 3, 1), _fx('car', 'floor', 1, 1, 4, 2)]
    if rtype == 'infinity':
        return [_fx('pool', 'floor', 1, 1, c - 2, 2)]
    if rtype == 'pavilion':
        return [_fx('gazebo', 'floor', c // 2 - 1, 0, 3, 2)]
    return []


def room(rid: str, rtype: str, cols: int, frows: int, fl: int, name: str = '', theme: str = '') -> dict:
    """One villa room in deco_content's room shape, plus its floor `fl` and its default look `skin0`."""
    DC = _dc()
    if rtype in EC.ROOM_TYPES:
        emoji, base, _ = EC.ROOM_TYPES[rtype]
    else:
        emoji, base = DC.ROOM_NAMES[rtype]
    out = rtype in DC.OUT or rtype in EC.OUTDOOR
    skin0 = dict(EC.THEMES.get(theme, {})) if not out else {}
    skin0.update(EC.TYPE_SKIN.get(rtype, {}))
    return dict(id=rid, type=rtype, emoji=emoji, name=name or base, cols=cols, wrows=0 if out else WROWS, frows=frows, out=out,
                fix=fixtures(rtype, cols), tags=(), fl=fl, skin0=skin0)


def _kits(kits) -> list:
    from .deco import kit_room
    return [dict(kit_room(k), fl=fl) for k, fl in kits]


def rooms_of(key: str) -> list | None:
    """The rooms of a villa place key ('estate:<id>:<day>', or a home kind's key ending ':v2'); None: not one of them."""
    if key in _ROOMS:
        return _ROOMS[key]
    bits = key.split(':')
    out = None
    if bits[0] == KEY and len(bits) == 3 and bits[1] in ESTATE:
        e = ESTATE[bits[1]]
        out = [room(*r, theme=e['theme']) for r in e['rooms']] + _kits(e['kits'])
    elif key.endswith(V2) and len(bits) >= 4 and bits[-2] == EC.SONG_HONG:
        from .deco import rooms_of as home_rooms
        old = {r['id']: r for r in home_rooms(key[:-len(V2)]) or ()}
        out = [superset(old[r['id']], r) if r['id'] in old else r for r in legacy_rooms(key)]
    if out is not None and len(_ROOMS) < 64:
        _ROOMS[key] = out
    return out


_LEGACY: dict = {}


def legacy_rooms(key: str) -> list | None:
    """Biệt thự Sông Hồng's three-floor rooms exactly as 1.9.11..1.9.17 build them (their deco.validate checks
    journey.deco / decor / decor_new / decor_more against these); None: any other place."""
    bits = key.split(':')
    if not (key.endswith(V2) and len(bits) >= 4 and bits[-2] == EC.SONG_HONG):
        return None
    if key in _LEGACY:
        return _LEGACY[key]
    out = [room(*r) for r in EC.SONG_HONG_V2['rooms']] + _kits(EC.SONG_HONG_V2['kits'])
    if len(_LEGACY) < 64:
        _LEGACY[key] = out
    return out


def _rows(r: dict, layer: str) -> int:
    return r['wrows'] if layer == 'wall' else r['frows']


def superset(old: dict, new: dict) -> dict:
    """`new` grown so that every spot of `old` stays usable: as many columns and rows as either, and each of new's
    fixtures cut down to the columns that are outside `old` or where `old` had the same fixture (a piece that stood
    there in `old` then still can; a cell only freed is never a problem for a layout made in `new`)."""
    out = dict(new, cols=max(old['cols'], new['cols']), wrows=max(old['wrows'], new['wrows']),
               frows=max(old['frows'], new['frows']))
    def same(layer, t, x, y):
        return any(f['layer'] == layer and f['t'] == t and f['x'] <= x < f['x'] + f['w'] and f['y'] <= y < f['y'] + f['h']
                   for f in old['fix'])
    fix = []
    for f in new['fix']:
        keep = [x for x in range(f['x'], f['x'] + f['w'])
                if all(x >= old['cols'] or y >= _rows(old, f['layer']) or same(f['layer'], f['t'], x, y)
                       for y in range(f['y'], f['y'] + f['h']))]
        run: list = []
        for x in keep + [None]:
            if run and (x is None or x != run[-1] + 1):
                fix.append(dict(f, x=run[0], w=len(run)))
                run = []
            if x is not None:
                run.append(x)
    out['fix'] = fix
    return out


def living_in(j: dict) -> str | None:
    """The villa the player lives in (an id this build knows and they own), else None."""
    b = j.get('lux') if isinstance(j, dict) else None
    if not isinstance(b, dict):
        return None
    eid = b.get('live')
    own = b.get('own') if isinstance(b.get('own'), dict) else {}
    return eid if isinstance(eid, str) and eid in ESTATE and eid in own else None


def place(j: dict) -> dict | None:
    """deco.place for a player living in a villa (None: not)."""
    eid = living_in(j)
    if not eid:
        return None
    return dict(key=f"{KEY}:{eid}:{j['lux']['own'][eid]['d']}", where=KEY, kind=eid)


def v2_key(pl: dict) -> dict:
    """A place in Biệt thự Sông Hồng moves to its three-floor inside."""
    if pl.get('kind') == EC.SONG_HONG and pl.get('where') in ('own', 'shared', 'lease') and not pl['key'].endswith(V2):
        return dict(pl, key=pl['key'] + V2)
    return pl


def name_of(pl: dict) -> tuple[str, str] | None:
    e = ESTATE.get(pl.get('kind')) if pl.get('where') == KEY else None
    return (e['emoji'], e['name']) if e else None


def living(j: dict, out: dict) -> dict:
    """journey.living_cost while living in a villa: its điện nước in place of the rent."""
    eid = living_in(j)
    if not eid:
        return out
    rent = ESTATE[eid]['power']
    return dict(out, total=rent + out['meals'], rent=rent, label='Cơm nước và điện nước dinh thự', where=KEY)


def catalogue() -> dict:
    """For the client: the villas (rooms by type and floor) and the room types' names."""
    return dict(estates=[dict(id=e['id'], theme=e['theme'], emoji=e['emoji'], name=e['name'], where=e['where'], price=e['price'],
                              bp=e['bp'], power=e['power'], staff=e['staff'], floors=max(r[4] for r in e['rooms']),
                              rooms=[dict(t=r[1], fl=r[4]) for r in e['rooms']]) for e in EC.ESTATES],
                types={t: dict(emoji=v[0], name=v[1]) for t, v in EC.ROOM_TYPES.items()})
