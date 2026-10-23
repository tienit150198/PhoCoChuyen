"""🔒 Khóa món (⚒️ Cường hóa v2, owner-approved 23/10 "gọn và dễ dùng như các game khác"): a player locks the pieces they
love so ⚡ Cường hóa nhanh, Ghép tất cả and every fusion never use them up as an ingredient.

* jr_pet_lock {ids: [id…], on: bool}: lock (on) or unlock pieces the player owns, any kind at once: 🪽 wings 'w12',
  🧬 pets 'p3', 👗 pet clothes 'o40', 🧰 pet gear 'g7' (the four kinds' ids never share a first letter). Ids no longer
  owned are dropped from the list on every change (a piece fused away, thrown out, or used by an older build).
* What a lock does (game/wings.py, game/pet_tiers.py, game/pet_wardrobe.py):
  - the ⚡ runs (jr_pet_wing_fuse_auto, jr_pet_fuse_auto, jr_pet_gear_auto, jr_pet_wfuse_auto) never pick a locked piece
    as one of the two others / the three clothes; a locked wing, pet or gear may be the main one (it goes up, never
    away): the main one is the pinned one (`pin`), then the one worn / walked, then a locked one, then the usual pick;
  - the one-shot fusions refuse a locked piece among the ingredients with a clear line (🧬 a hybrid `mix` uses all
    three: none may be locked), jr_pet_wfuse takes three unlocked clothes or refuses;
  - throwing away (jr_pet_wing_drop, jr_pet_gear_drop) refuses a locked piece; jr_pet_wdrop drops an unlocked one.
* `pin` (the ⚡ runs of wings, pets and gear, ⚒️ "Cường hóa tối đa" on one piece): that piece is the main one whenever it
  is in a set and never an ingredient, for this run only (nothing stored).

Save: an OPTIONAL journey key (KEY, {v, ids}), absent while nothing is locked, like game/forge_news.py's `fzn`: older
builds' journey.validate accepts extra journey keys and keeps them untouched (2.5.6 and 2.5.5 load, play and save a save
with locks: tests/test_forge_auto.py Live), they just do not honour them. The client reads journey.forge_locks.
"""
from __future__ import annotations

import re

KEY = 'fzl'
VERSION = 1
COMMAND = 'jr_pet_lock'
MAX = 400                                  # ≥ every piece a save may hold (60 wings, the pets, 150 clothes, 60 gear)
ID_RE = re.compile(r'[wpog][0-9]{1,7}')


def _need(ok, msg, code='invalid_action'):
    from .engine import need
    need(ok, msg, code)


def ids(s: dict) -> frozenset:
    """The ids locked in this save (empty when none or the block is not well formed)."""
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    if not isinstance(b, dict) or not isinstance(b.get('ids'), list):
        return frozenset()
    return frozenset(i for i in b['ids'] if isinstance(i, str))


def locked(s: dict, i) -> bool:
    return isinstance(i, str) and i in ids(s)


def pin_of(p: dict):
    """A ⚡ run's `pin` (one piece's id, or None); its shape checked."""
    v = p.get('pin')
    _need(v is None or (isinstance(v, str) and ID_RE.fullmatch(v) is not None), 'Thông tin không hợp lệ.')
    return v


def owned(s: dict) -> set:
    """Every piece id this save owns now: wings, pets (home, kennel, the grandparents'), clothes, gear."""
    from . import pet_tiers, pet_wardrobe, wings
    out: set = set()
    w = wings.get(s)
    if w:
        out.update(x['id'] for x in w['own'])
    j = s.get('journey') or {}
    if j.get('pets'):
        out.update(p['id'] for p in pet_tiers.all_pets(s))
        x = pet_tiers.get(s)
        if x:
            out.update(g['id'] for g in x['gear'])
        out.update(i['id'] for i in pet_wardrobe.get(s)['it'])   # the stored block, or what the old accessories make
    return out


def refuse(name: str) -> None:
    """The one-shot fusions' line for a locked ingredient."""
    _need(False, f'🔒 {name} đang khóa, không dùng làm nguyên liệu được. Mở khóa rồi hẵng ghép nhé.', 'locked')


def action(s: dict, p: dict) -> dict:
    """jr_pet_lock {ids, on}: see the module's doc."""
    _need(isinstance(p, dict) and set(p) == {'ids', 'on'}, 'Thông tin không hợp lệ.')
    want, on = p['ids'], p['on']
    _need(type(on) is bool and isinstance(want, list) and 1 <= len(want) <= MAX
          and all(isinstance(i, str) and ID_RE.fullmatch(i) for i in want) and len(set(want)) == len(want),
          'Chọn món để khóa nhé.')
    have = owned(s)
    _need(all(i in have for i in want), 'Không thấy món này.', 'not_owned')
    keep = [i for i in (s['journey'].get(KEY) or {}).get('ids', []) if i in have]   # what is gone leaves the list
    if on:
        keep += [i for i in want if i not in keep]
    else:
        keep = [i for i in keep if i not in want]
    _need(len(keep) <= MAX, f'Khóa tối đa {MAX} món.', 'limit')
    if keep:
        s['journey'][KEY] = dict(v=VERSION, ids=keep)
    else:
        s['journey'].pop(KEY, None)   # nothing locked leaves no key
    n = len(want)
    return dict(message=(f'🔒 Đã khóa {n} món.' if on else f'🔓 Đã mở khóa {n} món.') if n > 1
                else ('🔒 Đã khóa.' if on else '🔓 Đã mở khóa.'), locks=list(keep))


def public(s: dict) -> list | None:
    """journey.forge_locks for the client (absent when nothing is locked)."""
    b = (s.get('journey') or {}).get(KEY)
    return list(b['ids']) if isinstance(b, dict) and b.get('ids') else None


def validate(s: dict) -> None:
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    _need(isinstance(b, dict) and set(b) == {'v', 'ids'} and b['v'] == VERSION and isinstance(b['ids'], list)
          and 1 <= len(b['ids']) <= MAX and all(isinstance(i, str) and ID_RE.fullmatch(i) for i in b['ids'])
          and len(set(b['ids'])) == len(b['ids']), 'Dữ liệu khóa món không hợp lệ.', 'invalid_save')
