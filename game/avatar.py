"""🙂 Ảnh đại diện: the face other players see next to the player's chat messages (and in their friend lists).

Save: one optional root key ``s['avatar']`` = {v, kind, face, emoji}
* kind  'face': a drawn face built from the parts below; 'emoji': one of EMOJIS instead.
* face  {skin, shape, age, hair, hc, expr, glasses, head, hwc, beard, freckles, extra, bg, shirt}: always kept,
        also while an emoji is shown, so switching back finds the face as it was.
* emoji the emoji of kind 'emoji'.
* Absent (older saves, a player who never opened the builder): the client draws a face that follows the character
  (hair, hair colour and skin of the wardrobe look, game/wardrobe.py) — except for someone who picked an emoji in
  their Phố nghề profile before, who keeps it (the live service checks that, live/faces.py).
* Older builds never read the key (validate_state lists no root keys): a rollback keeps loading these saves.
  ``migrate`` repairs a block a newer build wrote (an id this build does not know falls back to its default).

The clothes: with shirt 'tu' ("Mặc đồ trong tủ") the face wears the wardrobe's top and accessory in their colours
(look.tint); with a colour id it wears a plain tee of that colour. The client puts the outfit into the small public
code it sends to the live service (public/js/v4/face-code.js faceCode, checked by live/faces.py clean): only ids of
these lists and of the wardrobe ever travel, never markup or colours as text.

Art and Vietnamese names: public/js/v4/face.js (tests/test_avatar.py checks the id lists of the three places match).
Command (routed by journey.action, so validate_state runs as for every jr_* command):
``jr_avatar`` {kind: 'face'|'emoji', face?: {part: id, …}, emoji?} or {reset: true} (back to "giống nhân vật").
"""
from __future__ import annotations

VERSION = 1
KEY = 'avatar'

# Part ids, in the order the builder shows them; the first is the default unless DEFAULT_FACE says otherwise.
SKINS = ('s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8')
SHAPES = ('tron', 'oval', 'vuong', 'tim')
AGES = ('be', 'teen', 'lon', 'gia')
HAIRS = ('ngan', 'dinh', 'hoi', 'lech', 'dung', 'xoan', 'afro', 'bob', 'dai', 'bui', 'duoi', 'bim', 'mai', 'song', 'tet', 'chom')
HAIR_COLORS = ('den', 'nau', 'mat_ong', 'vang', 'do', 'hong', 'xanh', 'tim', 'bach_kim', 'xam', 'trang')
EXPRS = ('cuoi', 'toe', 'nhay', 'diu', 'ngac', 'then', 'ngau')
GLASSES = ('0', 'tron', 'vuong', 'ram', 'meo')
HEADS = ('0', 'hijab', 'khan', 'luoi_trai', 'len', 'non_la', 'tai_beo', 'bang_do', 'hoa', 'khan_dong')
# Colours of the headwear and of the plain tee: the wardrobe palette (game/wardrobe.py COLORS ids).
PALETTE = ('den', 'nau', 'vang', 'bac', 'hong', 'do', 'dao', 'mint', 'navy', 'lavender', 'trang')
BEARDS = ('0', 'lun', 'ria', 'de', 'quai')
EXTRAS = ('0', 'bong_tai', 'not_ruoi', 'bang_ca', 'tai_nghe')
BGS = ('kem', 'hong', 'dao', 'vang', 'mint', 'xanh', 'lavender', 'xam', 'navy', 'la')
SHIRTS = ('tu',) + PALETTE          # 'tu': the wardrobe's top and accessory
EMOJIS = ('🌸', '☕', '🍜', '🎉', '💪', '🌈', '🍀', '⭐', '🧁', '🎁', '🧑‍🍳', '👩‍🏫', '🧑‍💼', '🧑‍🌾', '🐱', '🐶',
          '🐰', '🦊', '🐼', '🐸', '🐧', '🐯', '🐨', '🦁', '🌻', '🌙', '🍉', '🍓', '🧋', '🎨', '🎸', '⚽', '📚', '🌊', '🍵', '🎮')

PARTS = dict(skin=SKINS, shape=SHAPES, age=AGES, hair=HAIRS, hc=HAIR_COLORS, expr=EXPRS, glasses=GLASSES, head=HEADS,
             hwc=PALETTE, beard=BEARDS, extra=EXTRAS, bg=BGS, shirt=SHIRTS)
DEFAULT_FACE = dict(skin='s2', shape='tron', age='lon', hair='ngan', hc='nau', expr='cuoi', glasses='0', head='0', hwc='do',
                    beard='0', freckles=False, extra='0', bg='kem', shirt='tu')
FACE_KEYS = frozenset(DEFAULT_FACE)
BLOCK_KEYS = frozenset(('v', 'kind', 'face', 'emoji'))
KINDS = ('face', 'emoji')


def _core():
    from . import engine
    return engine


def blank() -> dict:
    return dict(v=VERSION, kind='face', face=dict(DEFAULT_FACE), emoji=EMOJIS[0])


def combinations() -> int:
    """How many different faces the builder can make (every part, the headwear colour counted only for headwear
    that shows one: not for none or the nón lá), not counting the wardrobe's own tops and accessories."""
    n = 2   # freckles
    for k, ids in PARTS.items():
        if k not in ('head', 'hwc'):
            n *= len(ids)
    coloured = len([h for h in HEADS if h not in ('0', 'non_la')])
    return n * (len(HEADS) - coloured + coloured * len(PALETTE))


def _face_ok(f) -> bool:
    return (isinstance(f, dict) and set(f) == FACE_KEYS and type(f['freckles']) is bool
            and all(isinstance(f[k], str) and f[k] in ids for k, ids in PARTS.items()))


def validate(s: dict) -> None:
    """``s['avatar']`` (absent in older saves). Raises GameError like validate_state."""
    a = s.get(KEY)
    if a is None:
        return
    _core().need(isinstance(a, dict) and set(a) == BLOCK_KEYS and a['v'] == VERSION and a['kind'] in KINDS
                 and _face_ok(a['face']) and isinstance(a['emoji'], str) and a['emoji'] in EMOJIS,
                 'Ảnh đại diện trong bản lưu không hợp lệ.', 'invalid_save')


def _repair(a) -> dict | None:
    """What this build keeps of a block it cannot read as is (a newer build's ids): known parts, else defaults."""
    if not isinstance(a, dict):
        return None
    out = blank()
    if a.get('kind') in KINDS:
        out['kind'] = a['kind']
    if isinstance(a.get('emoji'), str) and a['emoji'] in EMOJIS:
        out['emoji'] = a['emoji']
    f = a.get('face') if isinstance(a.get('face'), dict) else {}
    for k, ids in PARTS.items():
        if isinstance(f.get(k), str) and f[k] in ids:
            out['face'][k] = f[k]
    if type(f.get('freckles')) is bool:
        out['face']['freckles'] = f['freckles']
    return out


def migrate(s: dict) -> None:
    """Nothing to add to older saves (absent = follows the character); a broken block is repaired."""
    if KEY not in s:
        return
    try:
        validate(s)
    except _core().GameError:
        fixed = _repair(s[KEY])
        if fixed is None:
            s.pop(KEY, None)
        else:
            s[KEY] = fixed


def clean_face(f) -> dict:
    """A face from a command: only known parts with known ids (a missing part takes its default). Raises GameError."""
    e = _core()
    e.need(isinstance(f, dict) and set(f) <= FACE_KEYS, 'Ảnh đại diện không hợp lệ.')
    out = dict(DEFAULT_FACE)
    for k, v in f.items():
        if k == 'freckles':
            e.need(type(v) is bool, 'Ảnh đại diện không hợp lệ.')
        else:
            e.need(isinstance(v, str) and v in PARTS[k], 'Ảnh đại diện không hợp lệ.')
        out[k] = v
    return out


def action(s: dict, name: str, p: dict) -> dict:
    """``jr_avatar``: save the face (or the emoji), or go back to the face that follows the character."""
    e = _core()
    e.need(name == 'jr_avatar' and isinstance(p, dict), 'Thao tác không hợp lệ.', 'unknown_action')
    if p.get('reset') is True:
        e.need(set(p) == {'reset'}, 'Ảnh đại diện không hợp lệ.')
        s.pop(KEY, None)
        return dict(message='Ảnh đại diện giờ giống nhân vật của bạn.')
    e.need(set(p) <= {'kind', 'face', 'emoji'} and p.get('kind') in KINDS, 'Ảnh đại diện không hợp lệ.')
    cur = s.get(KEY) or blank()
    out = dict(v=VERSION, kind=p['kind'], face=dict(cur['face']), emoji=cur['emoji'])
    if 'face' in p:
        out['face'] = clean_face(p['face'])
    if 'emoji' in p:
        e.need(isinstance(p['emoji'], str) and p['emoji'] in EMOJIS, 'Biểu tượng này chưa có.')
        out['emoji'] = p['emoji']
    s[KEY] = out
    return dict(message='Đã lưu ảnh đại diện.')
