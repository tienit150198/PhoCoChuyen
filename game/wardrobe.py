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
Commands: ``jr_wd_wear`` {look: {slot: id, …, uniform?}} and ``jr_wd_buy`` {item, wear?, pay?}, routed
by journey.action (so journey.after + validate_state run as for every jr_* command).
"""
from __future__ import annotations

VERSION = 1
KEY = 'wardrobe'
SLOTS = ('hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc')
SLOT_NAMES = dict(hair='Kiểu tóc', shade='Màu tóc', skin='Màu da', top='Áo', bottom='Quần · váy', shoes='Giày dép', acc='Phụ kiện')
SHOP = 'clothing'                 # Tiệm Áo Chỉ Mây
SHOP_NAME = 'Tiệm Áo Chỉ Mây'
STAFF_OFF = 20                    # % off for someone who has worked there
LABEL = 'Mua sắm quần áo'         # wallet row: "Mua sắm quần áo · Áo len mùa đông"
KIND = 'life'                     # journey.HISTORY_KINDS (an existing kind: older builds still validate the row)


def _i(iid, slot, name, price=0, need=None):
    return dict(id=iid, slot=slot, name=name, price=price, need=need)


# need: None | 'shop' (sold only at Tiệm Áo Chỉ Mây, to its staff) | 'married' | 'level:N' | 'title:<id>'
ITEMS = [
    # Kiểu tóc
    _i('toc_ngan', 'hair', 'Tóc ngắn gọn gàng'),
    _i('toc_bui', 'hair', 'Tóc búi cài hoa'),
    _i('toc_dai', 'hair', 'Tóc dài thả'),
    _i('toc_bob', 'hair', 'Tóc bob ngang vai', 40),
    _i('toc_duoi_ngua', 'hair', 'Tóc đuôi ngựa', 40),
    _i('toc_xoan', 'hair', 'Tóc xoăn bồng', 60),
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
    _i('ao_thun_kem', 'top', 'Áo thun kem'),
    _i('ao_thun_xanh', 'top', 'Áo thun xanh lá'),
    _i('ao_so_mi', 'top', 'Sơ mi trắng', 60),
    _i('ao_len', 'top', 'Áo len mùa đông', 80),
    _i('ao_hoodie', 'top', 'Áo hoodie tím', 90),
    _i('ao_dai', 'top', 'Áo dài lụa', 160),
    _i('ao_chi_may', 'top', 'Áo thun Chỉ Mây', 45, 'shop'),
    _i('ao_hoa', 'top', 'Sơ mi hoa đi biển', 0, 'level:5'),
    _i('ao_vest', 'top', 'Vest công sở', 0, 'title:st_office'),
    _i('ao_cuoi', 'top', 'Áo dài cưới đỏ', 0, 'married'),
    _i('vest_cuoi', 'top', 'Vest chú rể', 0, 'married'),
    # Quần · váy
    _i('quan_kem', 'bottom', 'Quần lửng kem'),
    _i('quan_xam', 'bottom', 'Quần tây xám'),
    _i('quan_jean', 'bottom', 'Quần jean', 50),
    _i('quan_short', 'bottom', 'Quần short kaki', 40),
    _i('vay_xoe', 'bottom', 'Chân váy xòe', 70),
    _i('vay_dai', 'bottom', 'Váy dài hoa nhí', 100),
    # Giày dép
    _i('giay_nau', 'shoes', 'Giày nâu'),
    _i('dep_lao', 'shoes', 'Dép lào xanh'),
    _i('giay_trang', 'shoes', 'Giày thể thao trắng', 45),
    _i('giay_do', 'shoes', 'Giày búp bê đỏ', 55),
    _i('bot_den', 'shoes', 'Bốt đen', 85),
    # Phụ kiện (một món)
    _i('pk_khong', 'acc', 'Không đeo gì'),
    _i('kinh_tron', 'acc', 'Kính gọng tròn', 40),
    _i('kinh_ram', 'acc', 'Kính râm', 0, 'level:3'),
    _i('non_la', 'acc', 'Nón lá', 35),
    _i('mu_len', 'acc', 'Mũ len', 50),
    _i('no_toc', 'acc', 'Nơ cài tóc', 30),
    _i('tui_cheo', 'acc', 'Túi đeo chéo', 60),
]
INDEX = {x['id']: x for x in ITEMS}
BUYABLE = frozenset(x['id'] for x in ITEMS if x['price'] > 0)
LOOK_KEYS = frozenset(SLOTS) | {'uniform'}
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
    """The look to draw: the saved one, or the gender's default."""
    w = s.get(KEY)
    return dict(w['look']) if isinstance(w, dict) and isinstance(w.get('look'), dict) else default_look(_gender(s))


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


def migrate(s: dict) -> None:
    """Saves from before 0.9.5 get the look they were drawn with; a broken block is repaired."""
    if KEY in s:
        try:
            validate(s)
        except _core().GameError:
            s[KEY] = _repair(s[KEY], _gender(s))
        return
    g = _gender(s)
    if g in ('male', 'female'):
        s[KEY] = blank(g)


def validate(s: dict) -> None:
    """``s['wardrobe']`` (absent in older saves). Raises GameError like validate_state."""
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


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    if name == 'jr_wd_wear':
        need(set(p) <= {'look'} and isinstance(p.get('look'), dict) and p['look'], 'Bộ đồ không hợp lệ.')
        want = p['look']
        need(set(want) <= LOOK_KEYS, 'Bộ đồ không hợp lệ.')
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
        if look == w['look']:
            return dict(message='Bạn đang mặc đúng bộ này rồi.')
        w['look'] = look
        return dict(message='Đã thay đồ xong. Trông bạn tươi tắn hẳn!')
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
                defaults={k or 'none': v for k, v in DEFAULTS.items()}, staff_off=STAFF_OFF, shop=SHOP, shop_name=SHOP_NAME)
