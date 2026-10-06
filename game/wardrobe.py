"""Tủ đồ: how the player's character looks (hair, clothes, shoes, one accessory).

Save: one root key ``s['wardrobe']`` = {v, look, owned}
* look  = {hair, shade, skin, top, bottom, shoes, acc: item id, uniform: bool}. ``uniform``: in a
  workplace the character wears that place's work layer (apron, white coat, overalls…) over the top,
  as before 0.9.5.
* owned = ids of the items bought (free and unlocked items are never listed).
* Absent in older saves and before the player picks Nam/Nữ: the look is the default of the gender,
  which is exactly how the character was drawn before (``migrate`` adds it once the gender is known).
* Older builds never read the key (engine.validate_state does not list root keys), so a rollback keeps
  loading these saves; ``migrate`` repairs a block written by a newer build (unknown slots or ids fall
  back to the default) instead of refusing the save.

Items: a few free basics for everyone; the rest are bought with the wallet through bank.pay (cash, or
the card when the player prefers it), one wallet row "Mua sắm quần áo · …" (kind 'life'). Having worked
at Tiệm Áo Chỉ Mây (career ``clothing``) gives the staff price (−20 %) and opens the shop's own tee.
Some items are unlocked instead of bought: a maturity level, a title, or being married.

Art lives in public/js/v4/look.js under the same ids (tests/test_wardrobe.py checks the lists match).
Commands (routed by journey.action, so journey.after + validate_state run as for every jr_* command):
``jr_wd_wear`` {look: {slot: id, …, uniform?, tint?}}, ``jr_wd_buy`` {item, wear?, pay?},
``jr_wd_unlock`` {color, pay?}, ``jr_wd_color`` {item, color, buy?, wear?, pay?} and
``jr_wd_deco`` {uid, color, buy?, pay?}.

Bảng màu (1.3.1 began it for the accessories, góp ý #70; now everything): every piece of clothing, every
pair of shoes, every accessory but "Không đeo gì" and every piece of furniture can take a colour from one
palette. Its own colour ("Màu gốc") is always free. A colour is unlocked ONCE (COLOR_PRICE, ánh kim
METAL_PRICE, the Chỉ Mây staff price as for the clothes) and is then free on any item, at home, in a rented
room or the dorm. Hair keeps its own shades (the 'shade' slot). Two root keys:
* ``s['colors']`` (new): the colour wallet {v, have, wear, deco}
    have = ["navy", …]           the unlocked colours
    wear = {clothing id: colour} the colour each top, bottom and pair of shoes is worn in (absent: Màu gốc)
    deco = {furniture uid: colour} the colour of a piece of furniture (journey.reno.items uid; it follows
           the piece into the bag and to the next home, a sold piece's entry is dropped on the next load)
* ``s['wardrobe_colors']`` (1.3.1, kept in its exact shape) = {v, wear, owned}
    wear  = {accessory id: colour}: the accessories' colours still live here
    owned = ["mu_len:navy", …]: 1.3.1 sold a colour per accessory. Every colour unlocked now is mirrored
            here for every accessory, so a 1.3.1/1.3.2 build (rollback) still lets the player wear it.
Migration: each colour a 1.3.1 save owns on any accessory becomes a colour of the wallet (generous on
purpose: 20 xu once bought it for one accessory). Rollback: 1.3.1/1.3.2 never read ``s['colors']`` and keep
it untouched in the save (validate_state lists no root keys); they draw clothes and furniture in Màu gốc and
the accessories in their colours. Back on this build everything is where it was, and a colour such a build
sold for one accessory joins the wallet too.
The look handed to the art (``look_of``, the client's lookOf, the live frames) carries the colours of what
is worn as ``look['tint'] = {item id: colour id}`` (only those that are not Màu gốc, at most four).
"""
from __future__ import annotations

VERSION = 1
KEY = 'wardrobe'
SLOTS = ('hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc')
SLOT_NAMES = dict(hair='Kiểu tóc', shade='Màu tóc', skin='Màu da', top='Áo · đầm', bottom='Quần · váy', shoes='Giày dép', acc='Phụ kiện')
SHOP = 'clothing'                 # Tiệm Áo Chỉ Mây
SHOP_NAME = 'Tiệm Áo Chỉ Mây'
STAFF_OFF = 20                    # % off for someone who has worked there
LABEL = 'Mua sắm quần áo'         # wallet row: "Mua sắm quần áo · Áo len mùa đông"
KIND = 'life'                     # journey.HISTORY_KINDS (an existing kind: older builds still validate the row)


def _i(iid, slot, name, price=0, need=None, plain=None):
    """plain: the name without its colour word ("Áo hoodie" for "Áo hoodie tím"), used once it is recoloured."""
    return dict(id=iid, slot=slot, name=name, price=price, need=need, plain=plain or name)


# need: None | 'shop' (sold only at Tiệm Áo Chỉ Mây, to its staff) | 'married' | 'level:N' | 'title:<id>'
ITEMS = [
    # Kiểu tóc
    _i('toc_ngan', 'hair', 'Tóc ngắn gọn gàng'),
    _i('toc_bui', 'hair', 'Tóc búi cài hoa'),
    _i('toc_dai', 'hair', 'Tóc dài thả'),
    _i('toc_bob', 'hair', 'Tóc bob ngang vai', 40),
    _i('toc_duoi_ngua', 'hair', 'Tóc đuôi ngựa', 40),
    _i('toc_xoan', 'hair', 'Tóc xoăn bồng', 60),
    _i('toc_bui_cao', 'hair', 'Tóc búi cao gọn', 50),
    _i('toc_bui_doi', 'hair', 'Tóc búi đôi tinh nghịch', 60),
    _i('toc_bui_thap', 'hair', 'Tóc búi thấp thanh lịch', 45),
    # Màu tóc
    _i('mau_nau', 'shade', 'Nâu hạt dẻ'),
    _i('mau_den', 'shade', 'Đen tuyền'),
    _i('mau_mat_ong', 'shade', 'Nâu mật ong'),
    _i('mau_hong', 'shade', 'Hồng phấn', 50),
    _i('mau_xanh_khoi', 'shade', 'Xanh khói', 50),
    _i('mau_bach_kim', 'shade', 'Bạch kim', 0, 'title:c_salon'),
    # Màu da
    _i('da_sang', 'skin', 'Da sáng'),
    _i('da_hong', 'skin', 'Da hồng hào'),
    _i('da_trung', 'skin', 'Da bánh mật'),
    _i('da_ngam', 'skin', 'Da nâu nắng'),
    # Áo
    _i('ao_quen', 'top', 'Áo quen thuộc'),
    _i('ao_thun_kem', 'top', 'Áo thun kem', plain='Áo thun trơn'),
    _i('ao_thun_xanh', 'top', 'Áo thun xanh lá', plain='Áo thun trơn'),
    _i('ao_so_mi', 'top', 'Sơ mi trắng', 60, plain='Sơ mi'),
    _i('ao_len', 'top', 'Áo len mùa đông', 80),
    _i('ao_hoodie', 'top', 'Áo hoodie tím', 90, plain='Áo hoodie'),
    _i('ao_dai', 'top', 'Áo dài lụa', 160),
    _i('ao_chi_may', 'top', 'Áo thun Chỉ Mây', 45, 'shop'),
    _i('ao_hoa', 'top', 'Sơ mi hoa đi biển', 0, 'level:5'),
    _i('ao_vest', 'top', 'Vest công sở', 0, 'title:st_office'),
    _i('ao_cuoi', 'top', 'Áo dài cưới đỏ', 0, 'married', plain='Áo dài cưới'),
    _i('vest_cuoi', 'top', 'Vest chú rể', 0, 'married'),
    # Full dresses occupy the top slot; the renderer covers the saved bottom without changing it.
    _i('dam_cong_chua', 'top', 'Đầm công chúa tầng mây', 160),
    _i('dam_du_tiec', 'top', 'Đầm dạ tiệc đuôi cá', 180),
    _i('dam_yem', 'top', 'Đầm yếm dạo phố', 120),
    # 1.7.16 (góp ý #191): the new goods of Tiệm Áo Chỉ Mây, for the player too.
    _i('dam_maxi', 'top', 'Đầm maxi vàng nghệ', 150, plain='Đầm maxi'),
    _i('vay_babydoll', 'top', 'Váy babydoll hồng', 110, plain='Váy babydoll'),
    _i('ao_blazer', 'top', 'Áo blazer đen', 120, plain='Áo blazer'),
    _i('ao_cardigan', 'top', 'Áo cardigan kem', 85, plain='Áo cardigan'),
    _i('ao_polo', 'top', 'Áo polo xanh than', 60, plain='Áo polo'),
    # Quần · váy
    _i('quan_kem', 'bottom', 'Quần lửng kem', plain='Quần lửng'),
    _i('quan_xam', 'bottom', 'Quần tây xám', plain='Quần tây'),
    _i('quan_jean', 'bottom', 'Quần jean', 50),
    _i('quan_short', 'bottom', 'Quần short kaki', 40),
    _i('vay_xoe', 'bottom', 'Chân váy xòe', 70),
    _i('vay_dai', 'bottom', 'Váy dài hoa nhí', 100),
    _i('vay_chu_a', 'bottom', 'Chân váy chữ A đen', 70, plain='Chân váy chữ A'),
    # Giày dép
    _i('giay_nau', 'shoes', 'Giày nâu', plain='Giày da'),
    _i('dep_lao', 'shoes', 'Dép lào xanh', plain='Dép lào'),
    _i('giay_trang', 'shoes', 'Giày thể thao trắng', 45, plain='Giày thể thao'),
    _i('giay_do', 'shoes', 'Giày búp bê đỏ', 55, plain='Giày búp bê'),
    _i('bot_den', 'shoes', 'Bốt đen', 85, plain='Bốt'),
    _i('sandal_nau', 'shoes', 'Sandal quai mảnh nâu', 50, plain='Sandal quai mảnh'),
    # Phụ kiện (một món)
    _i('pk_khong', 'acc', 'Không đeo gì'),
    _i('kinh_tron', 'acc', 'Kính gọng tròn', 40),
    _i('kinh_ram', 'acc', 'Kính râm', 0, 'level:3'),
    _i('non_la', 'acc', 'Nón lá', 35),
    _i('mu_len', 'acc', 'Mũ len', 50),
    _i('no_toc', 'acc', 'Nơ cài tóc', 30),
    _i('tui_cheo', 'acc', 'Túi đeo chéo', 60),
    _i('tui_xach', 'acc', 'Túi xách tay', 80),
    _i('bong_tai', 'acc', 'Bông tai ngọc trai', 45),
    _i('khan_lua', 'acc', 'Khăn lụa', 50),
]
INDEX = {x['id']: x for x in ITEMS}
BUYABLE = frozenset(x['id'] for x in ITEMS if x['price'] > 0)
LOOK_KEYS = frozenset(SLOTS) | {'uniform'}
WEAR_KEYS = LOOK_KEYS | {'tint'}  # jr_wd_wear may also switch colours (kept in the colour blocks, not in the look)

# ---------------------------------------------------------------- bảng màu
COLOR_KEY = 'wardrobe_colors'          # 1.3.1: the accessories' colours (+ the pairs older builds read)
COLOR_VERSION = 1
COLOR_BLOCK_KEYS = frozenset({'v', 'wear', 'owned'})
PAL_KEY = 'colors'                     # the colour wallet: unlocked colours, clothes' and furniture's colours
PAL_VERSION = 1
PAL_BLOCK_KEYS = frozenset({'v', 'have', 'wear', 'deco'})
GOC = 'goc'                            # "Màu gốc": the item's own colour, free (never stored)
COLOR_PRICE = 40                       # once, for every item (1.3.1: 20 xu per accessory)
METAL_PRICE = 60                       # ánh kim (gold, silver)
UNLOCK_LABEL = 'Mở khóa màu'           # wallet row: "Mở khóa màu · Xanh navy" (kind 'life')


def _c(cid, name, price=COLOR_PRICE):
    return dict(id=cid, name=name, price=price)


# The art (hex) lives in public/js/v4/look.js ACC_COLORS under the same ids; live/street_data.py copies the ids.
COLORS = [
    _c('den', 'Đen tuyền'),
    _c('nau', 'Nâu gỗ'),
    _c('vang', 'Vàng gold', METAL_PRICE),
    _c('bac', 'Bạc ánh kim', METAL_PRICE),
    _c('hong', 'Hồng pastel'),
    _c('do', 'Đỏ son'),
    _c('dao', 'Cam đào'),
    _c('mint', 'Xanh bạc hà'),
    _c('navy', 'Xanh navy'),
    _c('lavender', 'Tím lavender'),
    _c('trang', 'Trắng kem'),
]
COLOR_INDEX = {x['id']: x for x in COLORS}
TINTABLE = tuple(x['id'] for x in ITEMS if x['slot'] == 'acc' and x['id'] != 'pk_khong')   # accessories (1.3.1)
TINT_SLOTS = ('top', 'bottom', 'shoes', 'acc')
CLOTHES = tuple(x['id'] for x in ITEMS if x['slot'] in ('top', 'bottom', 'shoes'))
PAINTABLE = frozenset(TINTABLE + CLOTHES)   # every wardrobe item that takes a colour (hair: its own shades)
# The colours that sit well with each hair shade ("Hợp với tóc nâu mật ong"), best first.
MATCH = {
    'mau_nau': ('vang', 'dao', 'mint', 'trang'),
    'mau_den': ('do', 'bac', 'trang', 'hong'),
    'mau_mat_ong': ('navy', 'trang', 'nau', 'mint'),
    'mau_hong': ('trang', 'lavender', 'bac', 'mint'),
    'mau_xanh_khoi': ('bac', 'trang', 'navy', 'hong'),
    'mau_bach_kim': ('lavender', 'hong', 'navy', 'den'),
}
PAIRS = frozenset(f'{i}:{c}' for i in TINTABLE for c in COLOR_INDEX)
BLOCK_KEYS = frozenset({'v', 'look', 'owned'})

_BASE = dict(shade='mau_nau', skin='da_sang', top='ao_quen', shoes='giay_nau', acc='pk_khong', uniform=True)
DEFAULTS = {
    'male': dict(_BASE, hair='toc_ngan', bottom='quan_xam'),
    'female': dict(_BASE, hair='toc_bui', bottom='quan_kem'),
    None: dict(_BASE, hair='toc_ngan', bottom='quan_kem'),
}


def _core():
    from . import engine
    return engine


def default_look(gender) -> dict:
    d = DEFAULTS[gender if gender in ('male', 'female') else None]
    return {k: d[k] for k in (*SLOTS, 'uniform')}


def blank(gender) -> dict:
    return dict(v=VERSION, look=default_look(gender), owned=[])


def _gender(s: dict):
    j = s.get('journey')
    return j.get('gender') if isinstance(j, dict) else None


def look_of(s: dict) -> dict:
    """The look to draw: the saved one, or the gender's default, with the colours of what is worn (``tint``)."""
    w = s.get(KEY)
    look = dict(w['look']) if isinstance(w, dict) and isinstance(w.get('look'), dict) else default_look(_gender(s))
    tint = {look[slot]: col for slot in TINT_SLOTS if (col := color_of(s, look.get(slot))) != GOC}
    if tint:
        look['tint'] = tint
    return look


def _legacy(s: dict) -> dict | None:
    c = s.get(COLOR_KEY)
    return c if isinstance(c, dict) else None


def _pal(s: dict) -> dict | None:
    p = s.get(PAL_KEY)
    return p if isinstance(p, dict) else None


def _part(block: dict | None, key: str, kind: type):
    v = block.get(key) if block else None
    return v if isinstance(v, kind) else kind()


def have_colors(s: dict) -> list:
    """The unlocked colours, in palette order: the wallet's, and any a 1.3.1 build sold for an accessory."""
    got = set(_part(_pal(s), 'have', list))
    got.update(x.split(':', 1)[1] for x in _part(_legacy(s), 'owned', list) if isinstance(x, str) and x in PAIRS)
    return [c['id'] for c in COLORS if c['id'] in got]


def has_color(s: dict, cid: str) -> bool:
    return cid == GOC or cid in have_colors(s)


def color_owned(s: dict, iid: str, cid: str) -> bool:
    """1.3.1's name: a colour is no longer bought per item, so this is has_color."""
    return has_color(s, cid)


def color_of(s: dict, iid) -> str:
    """The colour this wardrobe item is worn in (GOC: its own)."""
    if not isinstance(iid, str):
        return GOC
    if iid in TINTABLE:
        col = _part(_legacy(s), 'wear', dict).get(iid)
    elif iid in CLOTHES:
        col = _part(_pal(s), 'wear', dict).get(iid)
    else:
        return GOC
    return col if isinstance(col, str) and col in COLOR_INDEX else GOC


def deco_color(s: dict, uid) -> str:
    col = _part(_pal(s), 'deco', dict).get(uid) if isinstance(uid, str) else None
    return col if isinstance(col, str) and col in COLOR_INDEX else GOC


def item_name(iid: str, cid: str = GOC) -> str:
    """"Áo hoodie tím", or once recoloured "Áo hoodie · Xanh navy" (the colour word of its name would be wrong)."""
    it = INDEX[iid]
    return it['name'] if cid == GOC else f'{it["plain"]} · {COLOR_INDEX[cid]["name"]}'


# ---------------------------------------------------------------- save
def _repair(w, gender) -> dict:
    """A block written by a newer build or a hand-edited backup: keep what this build knows."""
    out = blank(gender)
    if not isinstance(w, dict):
        return out
    look = w.get('look') if isinstance(w.get('look'), dict) else {}
    for slot in SLOTS:
        iid = look.get(slot)
        if isinstance(iid, str) and INDEX.get(iid, {}).get('slot') == slot:
            out['look'][slot] = iid
    if type(look.get('uniform')) is bool:
        out['look']['uniform'] = look['uniform']
    owned = w.get('owned') if isinstance(w.get('owned'), list) else []
    out['owned'] = [x for i, x in enumerate(owned) if isinstance(x, str) and x in BUYABLE and x not in owned[:i]]
    return out


def _repair_colors(c) -> dict:
    """A colour block written by a newer build or hand-edited: keep the pairs and colours this build knows."""
    out = dict(v=COLOR_VERSION, wear={}, owned=[])
    if not isinstance(c, dict):
        return out
    owned = c.get('owned') if isinstance(c.get('owned'), list) else []
    out['owned'] = [x for i, x in enumerate(owned) if isinstance(x, str) and x in PAIRS and x not in owned[:i]]
    wear = c.get('wear') if isinstance(c.get('wear'), dict) else {}
    out['wear'] = {k: v for k, v in wear.items() if k in TINTABLE and isinstance(v, str) and f'{k}:{v}' in out['owned']}
    return out


def _uid_ok(uid) -> bool:
    return isinstance(uid, str) and 1 <= len(uid) <= 12   # journey.reno.items ids (reno.validate)


def _repair_palette(p) -> dict:
    """A wallet written by a newer build or hand-edited: keep the colours, clothes and pieces this build knows."""
    out = dict(v=PAL_VERSION, have=[], wear={}, deco={})
    if not isinstance(p, dict):
        return out
    have = set(x for x in _part(p, 'have', list) if isinstance(x, str))
    out['have'] = [c['id'] for c in COLORS if c['id'] in have]
    out['wear'] = {k: v for k, v in _part(p, 'wear', dict).items() if k in CLOTHES and v in out['have']}
    deco = [(k, v) for k, v in _part(p, 'deco', dict).items() if _uid_ok(k) and isinstance(v, str) and v in out['have']]
    out['deco'] = dict(deco)
    return out


def _furniture(s: dict) -> set | None:
    """The uids of the furniture the player owns (None: no reno block to compare with)."""
    j = s.get('journey')
    r = j.get('reno') if isinstance(j, dict) else None
    items = r.get('items') if isinstance(r, dict) else None
    if not isinstance(items, list):
        return None
    return {it['id'] for it in items if isinstance(it, dict) and isinstance(it.get('id'), str)}


def _mirror(s: dict, cids) -> None:
    """Every unlocked colour, as 1.3.1 pairs for every accessory: an older build (rollback) still lets the
    player wear it on any accessory."""
    want = [f'{i}:{c}' for c in cids if c in COLOR_INDEX for i in TINTABLE]
    c = _legacy(s)
    owned = c['owned'] if c is not None else []
    missing = [x for x in want if x not in owned]
    if missing:
        _lbox(s)['owned'].extend(missing)


def _sync(s: dict, prune: bool = False) -> None:
    """The wallet holds every colour the player owns (1.3.1's per-accessory colours included), and the 1.3.1
    block mirrors them. prune (on load): furniture sold since (by this build or an older one) loses its colour."""
    legacy = [x.split(':', 1)[1] for x in _part(_legacy(s), 'owned', list) if isinstance(x, str) and x in PAIRS]
    p = _pal(s)
    if legacy and (p is None or not set(legacy) <= set(p['have'])):
        _add_have(s, legacy)
        p = _pal(s)
    if p is None:
        return
    _mirror(s, p['have'])
    if prune and p['deco']:
        mine = _furniture(s) or set()
        gone = [u for u in p['deco'] if u not in mine]
        for u in gone:
            p['deco'].pop(u)


def migrate(s: dict) -> None:
    """Saves from before 0.9.5 get the look they were drawn with; a broken block is repaired.
    The colour blocks are checked the same way (a block a newer build wrote keeps what this build knows), then
    1.3.1's per-accessory colours join the wallet."""
    if COLOR_KEY in s:
        try:
            validate_colors(s)
        except _core().GameError:
            s[COLOR_KEY] = _repair_colors(s[COLOR_KEY])
    if PAL_KEY in s:
        try:
            validate_palette(s)
        except _core().GameError:
            s[PAL_KEY] = _repair_palette(s[PAL_KEY])
    _sync(s, prune=True)
    if KEY in s:
        try:
            _validate_look(s)
        except _core().GameError:
            s[KEY] = _repair(s[KEY], _gender(s))
        return
    g = _gender(s)
    if g in ('male', 'female'):
        s[KEY] = blank(g)


def validate(s: dict) -> None:
    """``s['wardrobe']``, ``s['wardrobe_colors']`` and ``s['colors']`` (all absent in older saves). Raises
    GameError like validate_state."""
    validate_colors(s)
    validate_palette(s)
    _validate_look(s)


def _validate_look(s: dict) -> None:
    e = _core()
    w = s.get(KEY)
    if w is None:
        return
    bad = 'Tủ đồ trong bản lưu không hợp lệ.'
    e.need(isinstance(w, dict) and set(w) == BLOCK_KEYS and w['v'] == VERSION, bad, 'invalid_save')
    look = w['look']
    e.need(isinstance(look, dict) and set(look) == LOOK_KEYS and type(look['uniform']) is bool, bad, 'invalid_save')
    for slot in SLOTS:
        iid = look[slot]
        e.need(isinstance(iid, str) and INDEX.get(iid, {}).get('slot') == slot, bad, 'invalid_save')
    owned = w['owned']
    e.need(isinstance(owned, list) and len(owned) <= len(BUYABLE) and len(set(owned)) == len(owned)
           and all(isinstance(x, str) and x in BUYABLE for x in owned), bad, 'invalid_save')


def validate_colors(s: dict) -> None:
    """``s['wardrobe_colors']`` (1.3.1's shape, unchanged). Raises GameError like validate_state."""
    e = _core()
    c = s.get(COLOR_KEY)
    if c is None:
        return
    bad = 'Màu phụ kiện trong bản lưu không hợp lệ.'
    e.need(isinstance(c, dict) and set(c) == COLOR_BLOCK_KEYS and c['v'] == COLOR_VERSION, bad, 'invalid_save')
    owned = c['owned']
    e.need(isinstance(owned, list) and len(owned) <= len(PAIRS) and len(set(owned)) == len(owned)
           and all(isinstance(x, str) and x in PAIRS for x in owned), bad, 'invalid_save')
    wear = c['wear']
    e.need(isinstance(wear, dict) and all(k in TINTABLE and isinstance(v, str) and f'{k}:{v}' in owned
                                          for k, v in wear.items()), bad, 'invalid_save')


def validate_palette(s: dict) -> None:
    """``s['colors']``, the colour wallet (absent until the first colour). Furniture uids are checked by shape:
    a piece sold today keeps its entry until the next load (``_sync``), which is harmless."""
    e = _core()
    p = s.get(PAL_KEY)
    if p is None:
        return
    bad = 'Bảng màu trong bản lưu không hợp lệ.'
    e.need(isinstance(p, dict) and set(p) == PAL_BLOCK_KEYS and p['v'] == PAL_VERSION, bad, 'invalid_save')
    have = p['have']
    e.need(isinstance(have, list) and len(have) <= len(COLORS) and len(set(map(str, have))) == len(have)
           and all(isinstance(x, str) and x in COLOR_INDEX for x in have), bad, 'invalid_save')
    wear = p['wear']
    e.need(isinstance(wear, dict) and all(k in CLOTHES and isinstance(v, str) and v in have for k, v in wear.items()),
           bad, 'invalid_save')
    deco = p['deco']
    e.need(isinstance(deco, dict)
           and all(_uid_ok(k) and isinstance(v, str) and v in have for k, v in deco.items()), bad, 'invalid_save')


def _lbox(s: dict) -> dict:
    if not isinstance(s.get(COLOR_KEY), dict):
        s[COLOR_KEY] = dict(v=COLOR_VERSION, wear={}, owned=[])
    return s[COLOR_KEY]


def _pbox(s: dict) -> dict:
    if not isinstance(s.get(PAL_KEY), dict):
        s[PAL_KEY] = dict(v=PAL_VERSION, have=[], wear={}, deco={})
    return s[PAL_KEY]


def _add_have(s: dict, cids) -> None:
    p = _pbox(s)
    got = set(p['have']) | {c for c in cids if c in COLOR_INDEX}
    p['have'] = [c['id'] for c in COLORS if c['id'] in got]


def color_price(s: dict, cid: str) -> int:
    p = COLOR_INDEX[cid]['price']
    return p - p * STAFF_OFF // 100 if staff(s) else p


def _set_color(s: dict, iid: str, cid: str) -> None:
    """Wear wardrobe item `iid` in `cid` (an unlocked colour or GOC)."""
    if iid in TINTABLE:
        if cid != GOC:
            _mirror(s, [cid])
            _lbox(s)['wear'][iid] = cid
        elif _legacy(s) is not None:
            s[COLOR_KEY]['wear'].pop(iid, None)
    elif cid != GOC:
        _pbox(s)['wear'][iid] = cid
    elif _pal(s) is not None:
        s[PAL_KEY]['wear'].pop(iid, None)


def _color_name(cid: str) -> str:
    return 'Màu gốc' if cid == GOC else COLOR_INDEX[cid]['name']


def _unlock(s: dict, cid: str, pay) -> str:
    """Pay for colour `cid` (bank.pay: wallet, else the card; one wallet row) and put it in the wallet.
    The sentence for the message."""
    cost = color_price(s, cid)
    cname = COLOR_INDEX[cid]['name']
    from . import bank as bk
    paid = bk.pay(s, cost, f'{UNLOCK_LABEL} · {cname}', method=pay if isinstance(pay, str) else 'auto', kind=KIND,
                  career=SHOP if staff(s) else None, short=f'Ví chưa đủ {cost} xu để mở khóa màu {cname}.')
    _add_have(s, [cid])
    _mirror(s, [cid])
    how = f'Đã trả {cost} xu' if paid['method'] == 'cash' else paid['text'].rstrip('.')
    off = f' (giá nhân viên {SHOP_NAME})' if cost < COLOR_INDEX[cid]['price'] else ''
    return f'{how}{off} mở khóa màu {cname}.'


def _box(s: dict) -> dict:
    if not isinstance(s.get(KEY), dict):
        s[KEY] = blank(_gender(s))
    return s[KEY]


def on_gender(s: dict, old) -> None:
    """Nam/Nữ changed in the profile: an untouched default look follows the new gender."""
    w = s.get(KEY)
    new = _gender(s)
    if isinstance(w, dict):
        if w.get('look') == default_look(old):
            w['look'] = default_look(new)
    elif new in ('male', 'female'):
        s[KEY] = blank(new)


# ---------------------------------------------------------------- rules
def staff(s: dict) -> bool:
    """Has worked at Tiệm Áo Chỉ Mây: staff price and the shop's own tee."""
    c = (s.get('careers') or {}).get(SHOP)
    return isinstance(c, dict) and bool(c.get('started'))


def price(s: dict, iid: str) -> int:
    p = INDEX[iid]['price']
    return p - p * STAFF_OFF // 100 if p and staff(s) else p


def _married(s: dict) -> bool:
    sp = (s.get('marriage') or {}).get('spouse') if isinstance(s.get('marriage'), dict) else None
    return isinstance(sp, dict) and sp.get('status') == 'married'


def _level(s: dict) -> int:
    from . import journey as jr
    cs = s['careers']
    places = sum(1 for c in cs.values() if int(c.get('metrics', {}).get('served', 0)) > 0)
    xp = sum(int(c.get('xp', 0)) for c in cs.values()) + jr.BREADTH_XP * places
    return jr.maturity(xp)['level']


def locked(s: dict, iid: str) -> str | None:
    """Why this item cannot be worn now (None: it can). Buying is a separate step."""
    it = INDEX[iid]
    need = it['need'] or ''
    if need.startswith('level:'):
        n = int(need[6:])
        if _level(s) < n:
            return f'{it["name"]} mở khi bạn đạt Trưởng thành cấp {n}.'
    elif need.startswith('title:'):
        from . import journey as jr
        tid = need[6:]
        if tid not in (s['journey'].get('titles') or {}):
            return f'{it["name"]} mở khi bạn có danh hiệu “{jr.TITLE_INDEX[tid]["name"]}”.'
    elif need == 'married' and not _married(s):
        return f'{it["name"]} dành cho người đã về chung một nhà.'
    if it['price'] and iid not in _box_owned(s):
        return f'Bạn chưa có {it["name"]}. Mua ở tủ đồ trước nhé.'
    return None


def _box_owned(s: dict) -> list:
    w = s.get(KEY)
    return w['owned'] if isinstance(w, dict) and isinstance(w.get('owned'), list) else []


def _color_args(p: dict, keys: set) -> tuple[str, bool]:
    need = _core().need
    need(set(p) <= keys, 'Thông tin màu không hợp lệ.')
    cid, buy = p.get('color'), p.get('buy', False)
    need(isinstance(cid, str) and (cid == GOC or cid in COLOR_INDEX), 'Màu này không có trong bảng màu.')
    need(buy in (True, False), 'Thông tin màu không hợp lệ.')
    need(p.get('pay', 'auto') in ('auto', 'cash', 'card', 'account', 'joint'), 'Thông tin màu không hợp lệ.')
    return cid, buy


def _get_color(s: dict, cid: str, buy: bool, pay) -> str:
    """Make sure colour `cid` is the player's: free when unlocked (or Màu gốc), else bought when `buy`.
    Returns the payment sentence ('' when nothing was paid)."""
    if has_color(s, cid):
        return ''
    _core().need(buy, f'Màu {COLOR_INDEX[cid]["name"]} chưa mở khóa ({color_price(s, cid)} xu).')
    return _unlock(s, cid, pay)


def _already(name: str, cid: str) -> str:
    return f'{name} đang ở màu gốc rồi.' if cid == GOC else f'{name} đang mang màu {COLOR_INDEX[cid]["name"]} rồi.'


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    if name == 'jr_wd_wear':
        need(set(p) <= {'look'} and isinstance(p.get('look'), dict) and p['look'], 'Bộ đồ không hợp lệ.')
        want = dict(p['look'])
        need(set(want) <= WEAR_KEYS, 'Bộ đồ không hợp lệ.')
        tint = want.pop('tint', None)
        if tint is not None:   # colours already unlocked: switching is free
            need(isinstance(tint, dict) and 0 < len(tint) <= len(PAINTABLE), 'Màu không hợp lệ.')
            for iid, cid in tint.items():
                need(iid in PAINTABLE and isinstance(cid, str) and (cid == GOC or cid in COLOR_INDEX), 'Màu không hợp lệ.')
                need(has_color(s, cid), f'Màu {_color_name(cid)} chưa mở khóa. Mở ở Bảng màu của bạn nhé.')
        w = _box(s)
        look = dict(w['look'])
        for slot, iid in want.items():
            if slot == 'uniform':
                need(type(iid) is bool, 'Bộ đồ không hợp lệ.')
                look['uniform'] = iid
                continue
            need(isinstance(iid, str) and INDEX.get(iid, {}).get('slot') == slot, 'Món đồ này không có trong tủ.')
            if iid != look[slot]:          # what you already wear stays on (a wedding outfit after a divorce…)
                why = locked(s, iid)
                need(why is None, why or '')
            look[slot] = iid
        recolour = {k: v for k, v in (tint or {}).items() if color_of(s, k) != v}
        if look == w['look'] and not recolour:
            return dict(message='Bạn đang mặc đúng bộ này rồi.')
        w['look'] = look
        for iid, cid in recolour.items():
            _set_color(s, iid, cid)
        return dict(message='Đã thay đồ xong. Trông bạn tươi tắn hẳn!')
    if name == 'jr_wd_unlock':
        cid, _buy = _color_args(p, {'color', 'pay'})
        need(cid != GOC, 'Màu gốc lúc nào cũng miễn phí.')
        cname = COLOR_INDEX[cid]['name']
        if has_color(s, cid):        # a second tap: nothing to pay
            return dict(message=f'Màu {cname} đã có trong bảng màu của bạn rồi.', duplicate=True)
        msg = _unlock(s, cid, p.get('pay'))
        return dict(message=f'{msg} Từ giờ màu này dùng được cho mọi món đồ.')
    if name == 'jr_wd_color':
        cid, buy = _color_args(p, {'item', 'color', 'buy', 'wear', 'pay'})
        iid = p.get('item')
        need(isinstance(iid, str) and iid in PAINTABLE, 'Món này không đổi màu được.')
        on = p.get('wear', True)
        need(on in (True, False), 'Thông tin màu không hợp lệ.')
        it, slot = INDEX[iid], INDEX[iid]['slot']
        w = _box(s)
        if w['look'][slot] != iid:        # its colour is chosen for wearing it: the item must be yours
            why = locked(s, iid)
            need(why is None, why or '')
        cname = _color_name(cid)
        paid = _get_color(s, cid, buy, p.get('pay'))
        if not paid and color_of(s, iid) == cid and (not on or w['look'][slot] == iid):
            return dict(message=_already(it['name'] if cid == GOC else it['plain'], cid))
        _set_color(s, iid, cid)
        if on:
            w['look'][slot] = iid
        msg = f'{it["name"]} trở lại màu gốc.' if cid == GOC else f'{it["plain"]} giờ mang màu {cname}.'
        done = (' Đeo luôn rồi nè!' if slot == 'acc' else ' Mặc luôn rồi nè!') if on else ''
        return dict(message=f'{paid} {msg}{done}'.strip())
    if name == 'jr_wd_deco':
        cid, buy = _color_args(p, {'uid', 'color', 'buy', 'pay'})
        uid = p.get('uid')
        need(_uid_ok(uid) and uid in (_furniture(s) or set()), 'Không tìm thấy món đồ này.')
        from . import deco as dc
        r = s['journey']['reno']
        k = next(it['k'] for it in r['items'] if it.get('id') == uid)
        need(k in dc.ITEMS, 'Món đồ này chưa dùng được ở phiên bản này.')
        nm = dc.ITEMS[k]['name']
        cname = _color_name(cid)
        paid = _get_color(s, cid, buy, p.get('pay'))
        if not paid and deco_color(s, uid) == cid:
            return dict(message=_already(nm, cid), duplicate=True)
        if cid == GOC:
            if _pal(s) is not None:
                s[PAL_KEY]['deco'].pop(uid, None)
            return dict(message=f'{nm} trở lại màu gốc.')
        deco = _pbox(s)['deco']
        mine = _furniture(s) or set()
        for u in [u for u in deco if u not in mine]:
            deco.pop(u)
        deco[uid] = cid
        return dict(message=f'{paid} {nm} giờ mang màu {cname}.'.strip())
    if name == 'jr_wd_buy':
        need(set(p) <= {'item', 'wear', 'pay'}, 'Thông tin mua hàng không hợp lệ.')
        iid = p.get('item')
        need(isinstance(iid, str) and iid in BUYABLE, 'Món này không bán.')
        it = INDEX[iid]
        need(p.get('wear', True) in (True, False), 'Thông tin mua hàng không hợp lệ.')
        w = _box(s)
        need(iid not in w['owned'], f'Bạn đã có {it["name"]} rồi.')
        if it['need'] == 'shop':
            need(staff(s), f'{it["name"]} chỉ bán cho người làm ở {SHOP_NAME}. Vào làm ở đó một ngày là mua được.')
        cost = price(s, iid)
        from . import bank as bk
        paid = bk.pay(s, cost, f'{LABEL} · {it["name"]}', method=p.get('pay', 'auto'), kind=KIND,
                      career=SHOP if staff(s) else None, short=f'Ví chưa đủ {cost} xu để mua {it["name"]}.')
        w['owned'].append(iid)
        if p.get('wear', True):
            w['look'][it['slot']] = iid
        how = f'Đã trả {cost} xu' if paid['method'] == 'cash' else paid['text'].rstrip('.')
        off = f' (giá nhân viên {SHOP_NAME})' if cost < it['price'] else ''
        return dict(message=f'{how}{off} cho {it["name"]}.' + (' Mặc luôn rồi nè!' if p.get('wear', True) else ' Đã cất vào tủ.'))
    raise e.GameError('Thao tác tủ đồ không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- client
def content() -> dict:
    """Static list for the client (bootstrap content, cached): names, prices and unlocks by id."""
    return dict(slots=[dict(id=k, name=SLOT_NAMES[k]) for k in SLOTS], items=[dict(x) for x in ITEMS],
                defaults={k or 'none': v for k, v in DEFAULTS.items()}, staff_off=STAFF_OFF, shop=SHOP, shop_name=SHOP_NAME,
                colors=[dict(x) for x in COLORS], tintable=list(TINTABLE), clothes=list(CLOTHES),
                match={k: list(v) for k, v in MATCH.items()})
