"""🙂 Faces: the small public code of a player's chat avatar (`fc`), as the client builds it
(public/js/v4/face-code.js faceCode) from their save: s['avatar'] (game/avatar.py) and the wardrobe look.

    f1.<skin>.<shape>.<age>.<hair>.<hc>.<expr>.<glasses>.<head>.<hwc>.<beard>.<freckles>.<extra>.<bg>.<shirt>.<g>.<top>.<top colour>.<acc>.<acc colour>
    a1.<the same>   the face that follows the character (never built in the builder: s['avatar'] absent)
    e1.<emoji>      an emoji instead of a face

clean() is the only way a code gets in: every part must be an id of the lists below (copies of game/avatar.py and of
the wardrobe, live/street_data.py; tests/test_avatar.py checks they match). An id this build does not know (a newer
client) takes the part's default; a wrong shape is refused (None). What goes out is rebuilt from the ids, so no text a
client typed ever reaches another player's screen.
"""
from __future__ import annotations

from .street_data import COLOR_IDS, LOOK_IDS, TINTABLE

MAX_LEN = 240
SKINS = ('s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8')
SHAPES = ('tron', 'oval', 'vuong', 'tim')
AGES = ('be', 'teen', 'lon', 'gia')
HAIRS = ('ngan', 'dinh', 'hoi', 'lech', 'dung', 'xoan', 'afro', 'bob', 'dai', 'bui', 'duoi', 'bim', 'mai', 'song', 'tet', 'chom', 'bui_doi', 'bui_thap')
HAIR_COLORS = ('den', 'nau', 'mat_ong', 'vang', 'do', 'hong', 'xanh', 'tim', 'bach_kim', 'xam', 'trang')
EXPRS = ('cuoi', 'toe', 'nhay', 'diu', 'ngac', 'then', 'ngau')
GLASSES = ('0', 'tron', 'vuong', 'ram', 'meo')
HEADS = ('0', 'hijab', 'khan', 'luoi_trai', 'len', 'non_la', 'tai_beo', 'bang_do', 'hoa', 'khan_dong')
PALETTE = ('den', 'nau', 'vang', 'bac', 'hong', 'do', 'dao', 'mint', 'navy', 'lavender', 'trang')
BEARDS = ('0', 'lun', 'ria', 'de', 'quai')
EXTRAS = ('0', 'bong_tai', 'not_ruoi', 'bang_ca', 'tai_nghe')
BGS = ('kem', 'hong', 'dao', 'vang', 'mint', 'xanh', 'lavender', 'xam', 'navy', 'la')
SHIRTS = ('tu',) + PALETTE
EMOJIS = ('🌸', '☕', '🍜', '🎉', '💪', '🌈', '🍀', '⭐', '🧁', '🎁', '🧑‍🍳', '👩‍🏫', '🧑‍💼', '🧑‍🌾', '🐱', '🐶',
          '🐰', '🦊', '🐼', '🐸', '🐧', '🐯', '🐨', '🦁', '🌻', '🌙', '🍉', '🍓', '🧋', '🎨', '🎸', '⚽', '📚', '🌊', '🍵', '🎮')
TINTS = ('0',) + COLOR_IDS

# (allowed ids, default) per position after the tag, in order.
FIELDS = (
    (SKINS, 's2'), (SHAPES, 'tron'), (AGES, 'lon'), (HAIRS, 'ngan'), (HAIR_COLORS, 'nau'), (EXPRS, 'cuoi'),
    (GLASSES, '0'), (HEADS, '0'), (PALETTE, 'do'), (BEARDS, '0'), (('0', '1'), '0'), (EXTRAS, '0'), (BGS, 'kem'),
    (SHIRTS, 'tu'), (('m', 'f', 'n'), 'n'), (LOOK_IDS['top'], 'ao_quen'), (TINTS, '0'), (LOOK_IDS['acc'], 'pk_khong'),
    (TINTS, '0'),
)
ACC, ACC_TINT = 17, 18     # positions in FIELDS: only an accessory that takes a colour keeps one
DEFAULT_AV = '🌸'


def clean(fc, av: str = DEFAULT_AV) -> str | None:
    """The canonical code of `fc`; '' for an automatic face of someone who chose an emoji avatar `av` in their Phố
    nghề profile (that emoji stays); None for nothing or a wrong shape."""
    if not isinstance(fc, str) or not 0 < len(fc) <= MAX_LEN:
        return None
    parts = fc.split('.')
    tag = parts[0]
    if tag == 'e1':
        return f'e1.{parts[1]}' if len(parts) == 2 and parts[1] in EMOJIS else None
    if tag not in ('f1', 'a1') or len(parts) > len(FIELDS) + 4:
        return None
    if tag == 'a1' and av and av != DEFAULT_AV:
        return ''
    out = []
    for i, (ids, default) in enumerate(FIELDS):
        v = parts[i + 1] if i + 1 < len(parts) else default
        out.append(v if v in ids else default)
    if out[ACC_TINT] != '0' and out[ACC] not in TINTABLE:
        out[ACC_TINT] = '0'
    return '.'.join([tag] + out)
