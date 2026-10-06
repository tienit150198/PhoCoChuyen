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

1.9.3 (góp ý #200): 45 new pieces (``plus`` in ITEMS: 8 hair styles, 26 clothes and shoes, 11 accessories), sold by
Tiệm Áo Chỉ Mây once it is open (chapter 3). A 1.9.1 worker would refuse their ids in ``s['wardrobe']``, so they
live in their own root key ``s['wardrobe_plus']`` = {v, look: {slot: [id, base]}, owned, wear} (see PLUS_KEY):
``s['wardrobe']`` then holds the slot's default, which is exactly what a 1.9.1 worker or client draws. A 1.9.1
build that changes such a slot makes the entry stale (ignored, dropped on the next load); nothing bought is lost.
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


def _i(iid, slot, name, price=0, need=None, plain=None, plus=False):
    """plain: the name without its colour word ("Áo hoodie" for "Áo hoodie tím"), used once it is recoloured.
    plus: a 1.9.2 piece, saved in s['wardrobe_plus'] (see PLUS_KEY), never in s['wardrobe']."""
    out = dict(id=iid, slot=slot, name=name, price=price, need=need, plain=plain or name)
    if plus:
        out['plus'] = True
    return out


def _n(iid, slot, name, price, plain=None):
    """A 1.9.2 piece (góp ý #200): sold by Tiệm Áo Chỉ Mây once the shop is open (chapter 3 of the story)."""
    return _i(iid, slot, name, price, OPEN_SHOP, plain, plus=True)


OPEN_SHOP = 'open:clothing'


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
    # 1.9.2 (góp ý #200, "chỉ có 18 kiểu tóc"): GenZ street fashion from Tiệm Áo Chỉ Mây. These live in
    # s['wardrobe_plus'] so a 1.9.1 worker (rolling deploy, rollback) never meets an id it does not know.
    _n('toc_song_dai', 'hair', 'Tóc dài uốn sóng', 60),
    _n('toc_bob_mai', 'hair', 'Tóc bob mái ngố', 50),
    _n('toc_duoi_cao', 'hair', 'Tóc đuôi ngựa buộc cao', 45),
    _n('toc_bui_tron', 'hair', 'Tóc hai búi tròn', 55),
    _n('toc_wolf', 'hair', 'Tóc wolf cut', 60),
    _n('toc_undercut', 'hair', 'Tóc undercut', 55),
    _n('toc_mai_bay', 'hair', 'Tóc mái bay', 45),
    _n('toc_tet', 'hair', 'Tóc tết bím', 50),
    _n('ao_croptop', 'top', 'Áo croptop trắng', 70, 'Áo croptop'),
    _n('ao_baby_tee', 'top', 'Áo baby tee hồng', 65, 'Áo baby tee'),
    _n('ao_bomber', 'top', 'Áo khoác bomber xanh rêu', 140, 'Áo khoác bomber'),
    _n('ao_hoodie_os', 'top', 'Hoodie oversize xám', 120, 'Hoodie oversize'),
    _n('ao_so_mi_os', 'top', 'Sơ mi oversize xanh nhạt', 95, 'Sơ mi oversize'),
    _n('ao_khoac_jean', 'top', 'Áo khoác jean', 130),
    _n('vay_hai_day', 'top', 'Váy hai dây lụa đen', 130, 'Váy hai dây'),
    _n('ao_dai_cach_tan', 'top', 'Áo dài cách tân hồng', 150, 'Áo dài cách tân'),
    _n('ao_ba_lo', 'top', 'Áo ba lỗ trắng', 45, 'Áo ba lỗ'),
    _n('dam_suong', 'top', 'Đầm suông xanh lá', 120, 'Đầm suông'),
    _n('vay_maxi_hoa', 'top', 'Váy maxi hoa đào', 160, 'Váy maxi hoa'),
    _n('dam_so_mi', 'top', 'Đầm sơ mi xanh trời', 130, 'Đầm sơ mi'),
    _n('vay_yem_jean', 'top', 'Váy yếm jean', 120),
    _n('dam_hoa_nhi', 'top', 'Đầm babydoll hoa nhí', 140, 'Đầm babydoll hoa nhí'),
    _n('dam_kim_sa', 'top', 'Đầm dạ hội kim sa tím', 180, 'Đầm dạ hội kim sa'),
    _n('quan_ong_rong', 'bottom', 'Quần ống rộng be', 85, 'Quần ống rộng'),
    _n('quan_cargo', 'bottom', 'Quần cargo xanh rêu', 90, 'Quần cargo'),
    _n('vay_tennis', 'bottom', 'Chân váy tennis trắng', 70, 'Chân váy tennis'),
    _n('quan_jogger', 'bottom', 'Quần jogger đen', 70, 'Quần jogger'),
    _n('quan_short_jean', 'bottom', 'Quần short jean', 50),
    _n('chan_vay_jean', 'bottom', 'Chân váy jean', 70),
    _n('vay_xep_ly_dai', 'bottom', 'Chân váy xếp ly dài hồng', 100, 'Chân váy xếp ly dài'),
    _n('sneaker_chunky', 'shoes', 'Sneaker chunky trắng', 95, 'Sneaker chunky'),
    _n('giay_mary_jane', 'shoes', 'Giày Mary Jane đen', 75, 'Giày Mary Jane'),
    _n('boot_co_ngan', 'shoes', 'Bốt cổ ngắn nâu', 90, 'Bốt cổ ngắn'),
    _n('dep_quai_ngang', 'shoes', 'Dép quai ngang', 40),
    _n('kinh_mat_meo', 'acc', 'Kính mát mắt mèo', 60),
    _n('mu_bucket', 'acc', 'Mũ bucket', 55),
    _n('mu_luoi_trai', 'acc', 'Mũ lưỡi trai', 45),
    _n('vong_co', 'acc', 'Vòng cổ mặt trăng', 50, 'Vòng cổ'),
    _n('dong_ho', 'acc', 'Đồng hồ đeo tay', 70),
    _n('kep_toc', 'acc', 'Kẹp tóc càng cua', 30),
    _n('kinh_can', 'acc', 'Kính cận gọng vuông', 40),
    _n('no_lua', 'acc', 'Nơ lụa to hồng', 40, 'Nơ lụa to'),
    _n('khuyen_tron', 'acc', 'Khuyên tai tròn vàng', 45, 'Khuyên tai tròn'),
    _n('khan_bandana', 'acc', 'Khăn bandana đỏ', 35, 'Khăn bandana'),
    _n('balo_mini', 'acc', 'Balo mini vàng', 80, 'Balo mini'),
]
INDEX = {x['id']: x for x in ITEMS}
PLUS = frozenset(x['id'] for x in ITEMS if x.get('plus'))      # 1.9.2 pieces (s['wardrobe_plus'])
BASE_INDEX = {k: v for k, v in INDEX.items() if k not in PLUS}  # what s['wardrobe'] may hold (1.9.1 knows these)
BUYABLE = frozenset(x['id'] for x in ITEMS if x['price'] > 0)
BASE_BUYABLE = BUYABLE - PLUS
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
# Where each piece's colour is kept: 1.3.1's accessories in s['wardrobe_colors'], the other 1.9.1 pieces in
# s['colors']['wear'], the 1.9.2 pieces in s['wardrobe_plus']['wear'] (a 1.9.1 build validates the first two).
BASE_TINTABLE = tuple(i for i in TINTABLE if i not in PLUS)
BASE_CLOTHES = tuple(i for i in CLOTHES if i not in PLUS)
# The colours that sit well with each hair shade ("Hợp với tóc nâu mật ong"), best first.
MATCH = {
    'mau_nau': ('vang', 'dao', 'mint', 'trang'),
    'mau_den': ('do', 'bac', 'trang', 'hong'),
    'mau_mat_ong': ('navy', 'trang', 'nau', 'mint'),
    'mau_hong': ('trang', 'lavender', 'bac', 'mint'),
    'mau_xanh_khoi': ('bac', 'trang', 'navy', 'hong'),
    'mau_bach_kim': ('lavender', 'hong', 'navy', 'den'),
}
PAIRS = frozenset(f'{i}:{c}' for i in BASE_TINTABLE for c in COLOR_INDEX)
BLOCK_KEYS = frozenset({'v', 'look', 'owned'})
# 1.9.2: the new pieces' own root key. look = {slot: [piece id, the id s['wardrobe'] wore in that slot when it was put
# on]} (a 1.9.1 build that changes the slot makes the entry stale: it is then ignored and dropped), owned = the
# pieces bought, wear = {piece id: colour id}. A 1.9.1 build never reads it and keeps it untouched (validate_state
# lists no root keys), while s['wardrobe'] only ever holds ids 1.9.1 knows (the slot's default under a new piece).
PLUS_KEY = 'wardrobe_plus'
PLUS_VERSION = 1
PLUS_BLOCK_KEYS = frozenset({'v', 'look', 'owned', 'wear'})
PLUS_MAX = 200          # ids a block may list (room for pieces of later builds: they are kept, not dropped)

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


def _plus(s: dict) -> dict | None:
    b = s.get(PLUS_KEY)
    return b if isinstance(b, dict) else None


def _overlay(s: dict, look: dict) -> dict:
    """The 1.9.2 pieces worn over s['wardrobe']'s look (an entry whose base no longer matches is stale)."""
    for slot, pair in _part(_plus(s), 'look', dict).items():
        if (slot in SLOTS and isinstance(pair, list) and len(pair) == 2 and pair[0] in PLUS
                and INDEX[pair[0]]['slot'] == slot and look.get(slot) == pair[1]):
            look[slot] = pair[0]
    return look


def worn(s: dict) -> dict:
    """What the player wears, slot by slot (no colours)."""
    w = s.get(KEY)
    look = dict(w['look']) if isinstance(w, dict) and isinstance(w.get('look'), dict) else default_look(_gender(s))
    return _overlay(s, look)


def look_of(s: dict) -> dict:
    """The look to draw: the saved one, or the gender's default, with the colours of what is worn (``tint``)."""
    look = worn(s)
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
    if iid in PLUS:
        col = _part(_plus(s), 'wear', dict).get(iid) if iid in PAINTABLE else None
    elif iid in TINTABLE:
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
        if isinstance(iid, str) and BASE_INDEX.get(iid, {}).get('slot') == slot:
            out['look'][slot] = iid
    if type(look.get('uniform')) is bool:
        out['look']['uniform'] = look['uniform']
    owned = w.get('owned') if isinstance(w.get('owned'), list) else []
    out['owned'] = [x for i, x in enumerate(owned) if isinstance(x, str) and x in BASE_BUYABLE and x not in owned[:i]]
    return out


def _id_ok(x) -> bool:
    return isinstance(x, str) and 0 < len(x) <= 40


def _repair_plus(b) -> dict:
    """A broken 1.9.2 block: keep every well-formed id (a later build's pieces too: nothing bought is lost)."""
    out = dict(v=PLUS_VERSION, look={}, owned=[], wear={})
    if not isinstance(b, dict):
        return out
    look = b.get('look') if isinstance(b.get('look'), dict) else {}
    out['look'] = {k: list(v) for k, v in look.items()
                   if k in SLOTS and isinstance(v, (list, tuple)) and len(v) == 2 and all(map(_id_ok, v))}
    owned = b.get('owned') if isinstance(b.get('owned'), list) else []
    out['owned'] = [x for i, x in enumerate(owned) if _id_ok(x) and x not in owned[:i]][:PLUS_MAX]
    wear = b.get('wear') if isinstance(b.get('wear'), dict) else {}
    out['wear'] = dict([(k, v) for k, v in wear.items() if _id_ok(k) and v in COLOR_INDEX][:PLUS_MAX])
    return out


def _repair_colors(c) -> dict:
    """A colour block written by a newer build or hand-edited: keep the pairs and colours this build knows."""
    out = dict(v=COLOR_VERSION, wear={}, owned=[])
    if not isinstance(c, dict):
        return out
    owned = c.get('owned') if isinstance(c.get('owned'), list) else []
    out['owned'] = [x for i, x in enumerate(owned) if isinstance(x, str) and x in PAIRS and x not in owned[:i]]
    wear = c.get('wear') if isinstance(c.get('wear'), dict) else {}
    out['wear'] = {k: v for k, v in wear.items() if k in BASE_TINTABLE and isinstance(v, str) and f'{k}:{v}' in out['owned']}
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
    out['wear'] = {k: v for k, v in _part(p, 'wear', dict).items() if k in BASE_CLOTHES and v in out['have']}
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
    want = [f'{i}:{c}' for c in cids if c in COLOR_INDEX for i in BASE_TINTABLE]
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
    else:
        g = _gender(s)
        if g in ('male', 'female'):
            s[KEY] = blank(g)
    if PLUS_KEY in s:
        try:
            validate_plus(s)
        except _core().GameError:
            s[PLUS_KEY] = _repair_plus(s[PLUS_KEY])
        # a slot an older build changed since: the 1.9.2 piece came off there (it stays owned)
        base = s[KEY]['look'] if isinstance(s.get(KEY), dict) else default_look(_gender(s))
        look = s[PLUS_KEY]['look']
        for slot in [k for k, v in look.items() if v[0] in PLUS and base.get(k) != v[1]]:
            look.pop(slot)


def validate(s: dict) -> None:
    """``s['wardrobe']``, ``s['wardrobe_colors']`` and ``s['colors']`` (all absent in older saves). Raises
    GameError like validate_state."""
    validate_colors(s)
    validate_palette(s)
    _validate_look(s)
    validate_plus(s)


def validate_plus(s: dict) -> None:
    """``s['wardrobe_plus']`` (1.9.2, absent before the first new piece). Ids are checked by shape only, so a block a
    later build wrote (pieces this build does not know) still loads; what is drawn is checked in _overlay."""
    e = _core()
    b = s.get(PLUS_KEY)
    if b is None:
        return
    bad = 'Đồ mới trong tủ (bản lưu) không hợp lệ.'
    e.need(isinstance(b, dict) and set(b) == PLUS_BLOCK_KEYS and b['v'] == PLUS_VERSION, bad, 'invalid_save')
    look, owned, wear = b['look'], b['owned'], b['wear']
    e.need(isinstance(look, dict) and all(k in SLOTS and isinstance(v, list) and len(v) == 2 and all(map(_id_ok, v))
                                          for k, v in look.items()), bad, 'invalid_save')
    e.need(isinstance(owned, list) and len(owned) <= PLUS_MAX and len(set(map(str, owned))) == len(owned)
           and all(map(_id_ok, owned)), bad, 'invalid_save')
    e.need(isinstance(wear, dict) and len(wear) <= PLUS_MAX
           and all(_id_ok(k) and isinstance(v, str) and v in COLOR_INDEX for k, v in wear.items()), bad, 'invalid_save')


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
        e.need(isinstance(iid, str) and BASE_INDEX.get(iid, {}).get('slot') == slot, bad, 'invalid_save')
    owned = w['owned']
    e.need(isinstance(owned, list) and len(owned) <= len(BASE_BUYABLE) and len(set(owned)) == len(owned)
           and all(isinstance(x, str) and x in BASE_BUYABLE for x in owned), bad, 'invalid_save')


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
    e.need(isinstance(wear, dict) and all(k in BASE_TINTABLE and isinstance(v, str) and f'{k}:{v}' in owned
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
    e.need(isinstance(wear, dict) and all(k in BASE_CLOTHES and isinstance(v, str) and v in have for k, v in wear.items()),
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


def _plusbox(s: dict) -> dict:
    if not isinstance(s.get(PLUS_KEY), dict):
        s[PLUS_KEY] = dict(v=PLUS_VERSION, look={}, owned=[], wear={})
    return s[PLUS_KEY]


def _set_color(s: dict, iid: str, cid: str) -> None:
    """Wear wardrobe item `iid` in `cid` (an unlocked colour or GOC)."""
    if iid in PLUS:
        if cid != GOC:
            _plusbox(s)['wear'][iid] = cid
        elif _plus(s) is not None:
            s[PLUS_KEY]['wear'].pop(iid, None)
    elif iid in TINTABLE:
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
        if w.get('look') == default_look(old) and not _part(_plus(s), 'look', dict):
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
        if need == OPEN_SHOP and not shop_open(s):
            return f'{it["name"]} bán ở {SHOP_NAME}, tiệm mở cửa từ chương 3 của hành trình.'
        return f'Bạn chưa có {it["name"]}. Mua ở tủ đồ trước nhé.'
    return None


def _box_owned(s: dict) -> list:
    """Every piece bought (1.9.1's block and the 1.9.2 one)."""
    w = s.get(KEY)
    base = w['owned'] if isinstance(w, dict) and isinstance(w.get('owned'), list) else []
    return base + [x for x in _part(_plus(s), 'owned', list) if x in PLUS]


def shop_open(s: dict) -> bool:
    """Tiệm Áo Chỉ Mây sells its 1.9.2 pieces once the shop is open to the player: chapter 3 of the story
    (journey.CH_UNLOCKS), worked there already, or a save outside the story (every workplace open)."""
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    return not j.get('story') or SHOP in (j.get('unlocked') or ()) or staff(s)


def _wear_slot(s: dict, slot: str, iid: str) -> None:
    """Put `iid` on in `slot`. A 1.9.2 piece goes in s['wardrobe_plus'] over the slot's default in s['wardrobe'] (what
    a 1.9.1 build shows); any other piece goes in s['wardrobe'] and takes the 1.9.2 piece off."""
    w = _box(s)
    if iid in PLUS:
        base = default_look(_gender(s))[slot]
        w['look'][slot] = base
        _plusbox(s)['look'][slot] = [iid, base]
    else:
        w['look'][slot] = iid
        if _plus(s) is not None:
            s[PLUS_KEY]['look'].pop(slot, None)


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
        now = _overlay(s, dict(w['look']))
        look = dict(now)
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
        if look == now and not recolour:
            return dict(message='Bạn đang mặc đúng bộ này rồi.')
        for slot in SLOTS:
            if look[slot] != now[slot]:
                _wear_slot(s, slot, look[slot])
        w['look']['uniform'] = look['uniform']
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
        _box(s)
        if worn(s)[slot] != iid:        # its colour is chosen for wearing it: the item must be yours
            why = locked(s, iid)
            need(why is None, why or '')
        cname = _color_name(cid)
        paid = _get_color(s, cid, buy, p.get('pay'))
        if not paid and color_of(s, iid) == cid and (not on or worn(s)[slot] == iid):
            return dict(message=_already(it['name'] if cid == GOC else it['plain'], cid))
        _set_color(s, iid, cid)
        if on and worn(s)[slot] != iid:
            _wear_slot(s, slot, iid)
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
        need(iid not in _box_owned(s), f'Bạn đã có {it["name"]} rồi.')
        if it['need'] == 'shop':
            need(staff(s), f'{it["name"]} chỉ bán cho người làm ở {SHOP_NAME}. Vào làm ở đó một ngày là mua được.')
        if it['need'] == OPEN_SHOP:
            need(shop_open(s), f'{it["name"]} bán ở {SHOP_NAME}, tiệm mở cửa từ chương 3 của hành trình.')
        cost = price(s, iid)
        from . import bank as bk
        paid = bk.pay(s, cost, f'{LABEL} · {it["name"]}', method=p.get('pay', 'auto'), kind=KIND,
                      career=SHOP if staff(s) else None, short=f'Ví chưa đủ {cost} xu để mua {it["name"]}.')
        (_plusbox(s)['owned'] if iid in PLUS else w['owned']).append(iid)
        if p.get('wear', True):
            _wear_slot(s, it['slot'], iid)
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
