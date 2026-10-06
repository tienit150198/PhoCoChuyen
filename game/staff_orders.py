"""What a shop's staff sell on their own (đơn riêng), from the shop's real catalogue.

Each staffed shop gets a menu built from its own goods, recipes and prices (the
player's Bảng giá included). An order is chosen at completion among the menu
entries that are in stock AND still earn money after the staff wage and
supplies, weighted by how many such orders the shelf can still make, from a
hash of the shop's order count (polling and offline catch-up pick the same).

Rules every entry follows:
* the price is the career's own shelf price for exactly what leaves the stock:
  a whole tub sells as a take-away tub, a pot of rice as seven boxes, never a
  whole tub for the price of one scoop;
* at the worst service (84% of the price, see workplace_business._finish) the
  margin over the catalogue cost still covers the wage and supplies plus 20%;
  a cheap line grows into a sensible basket (six kg of rice, a dozen eggs)
  instead of losing money, and a line that cannot is left out.

Careers without a menu keep their single authored order (workplace_business.ORDERS).
"""
from __future__ import annotations

import math
import zlib

FLOOR = 84        # % of the price at a 1-star service (80 + 1*4)
WEIGHT_CAP = 10   # an item's weight: orders the shelf can still make, capped


def _plugin(career):
    from .careers import PLUGINS
    return PLUGINS.get(career)


def costs(career: str) -> dict:
    """Catalogue (replacement) cost per stock unit."""
    if career == 'mother_baby':
        from .content import PRODUCT_INDEX
        return {k: p['cost'] for k, p in PRODUCT_INDEX.items()}
    if career == 'pharmacy':
        from .content import LOT_INDEX
        return {k: l['cost'] for k, l in LOT_INDEX.items()}
    from . import inventory as inv
    return {x['id']: x['cost'] for x in inv.catalogue(career)}


def known(career: str) -> set:
    """Item ids a staff receipt of this career may list."""
    return set(costs(career))


def _item(career, item_id):
    from . import inventory as inv
    return next(x for x in inv.catalogue(career) if x['id'] == item_id)


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


class _Menu:
    def __init__(self, c, career, target):
        self.c, self.career, self.target = c, career, target
        self.cost = costs(career)
        self.out = []
        self._avail = {}

    # -- stock and prices
    def avail(self, item):
        if item not in self._avail:
            self._avail[item] = max(0, _available(self.c, self.career, item))
        return self._avail[item]

    def price(self, key, default=None):
        from .careers import kit
        mod = _plugin(self.career)
        if default is None:
            default = (mod.SPEC.get('prices') or {}).get(key) if mod else None
        if default is None:
            default = _item(self.career, key).get('price', 0)
        return max(0, int(kit.price(self.c, key, default)))

    def first(self, *items):
        return next((i for i in items if self.avail(i) > 0), None)

    def _ok(self, revenue, inputs):
        return revenue * FLOOR // 100 - sum(self.cost.get(i, 0) * q for i, q in inputs.items()) >= self.target

    # -- entries
    def fixed(self, label, inputs, revenue):
        """One authored dish/service: every input whole, priced at the shelf."""
        if not inputs or any(i is None for i in inputs):
            return
        n = min(self.avail(i) // q for i, q in inputs.items())
        if n >= 1 and revenue > 0 and self._ok(revenue, inputs):
            self.out.append((label, revenue, dict(inputs), min(WEIGHT_CAP, n)))

    def retail(self, item, revenue_for, label_for, lo=1, cap=12, extra=None):
        """Sell `item` as it sits on the shelf: the smallest basket that still earns."""
        extra = {k: v for k, v in (extra or {}).items()}
        if any(k is None or self.avail(k) < v for k, v in extra.items()):
            return
        have = self.avail(item)
        for q in range(lo, min(cap, have) + 1):
            inputs = {item: q, **extra}
            revenue = revenue_for(q)
            if revenue > 0 and self._ok(revenue, inputs):
                self.out.append((label_for(q), revenue, inputs, max(1, min(WEIGHT_CAP, have // q))))
                return


def _available(c, career, item):
    """Units staff may take now (what the shop's own order checks would accept)."""
    if career in ('mother_baby', 'pharmacy'):
        from .workplace_business import _reserved
        n = c['stock'].get(item, 0) - _reserved(c, item)
        if career == 'pharmacy' and n > 0:
            from .content import LOT_INDEX
            from . import engine
            lot = LOT_INDEX.get(item)
            if (lot is None or lot['status'] != 'available' or lot['valid_until'] < c['day'] or item in c['held_lots']
                    or engine.ph_shelf_block(c, item)):
                return 0
        return n
    if c.get('ext', {}).get('inv') is None:
        return 0
    if career == 'grocery':
        from .careers import grocery
        return grocery._available(c, item)
    from . import inventory as inv
    return inv.count(c, item)


# ---------------------------------------------------------------- menus
def _mother_baby(m):
    from .content import PRODUCTS
    from .careers import mother_baby
    for p in PRODUCTS:
        price = mother_baby._price(m.c, p['id'])
        m.retail(p['id'], lambda q, price=price: price * q,
                 lambda q, p=p: f'Đơn riêng: {p["name"]}' if q == 1 else f'Đơn riêng: {q} × {p["name"]}', cap=3)


def _pharmacy(m):
    from .content import LOT_INDEX
    for lid, lot in LOT_INDEX.items():
        m.retail(lid, lambda q: 18 * q,
                 lambda q, lot=lot: f'Đơn riêng: xuất {"một" if q == 1 else q} hộp {lot["name"]} theo phiếu đã kiểm', cap=3)


def _grocery(m):
    from .careers import grocery
    for it in grocery.ITEMS:
        if it['id'] not in grocery.PRICES:
            continue
        grams = grocery.WEIGHED.get(it['id'], 1000)
        price = grocery._price(m.c, it['id'])
        m.retail(it['id'], lambda q, price=price, grams=grams: price * grams * q // 1000,
                 lambda q, it=it: f'Đơn riêng: {q} {it["unit"]} {_lower(it["name"])}', cap=20)


def _fruit(m):
    from .careers import fruit
    for f in fruit.FRUITS:
        kg = fruit._price_kg(m.c, f['id'])
        m.retail(f['id'], lambda q, kg=kg, g=f['g']: kg * g * q // 1000,
                 lambda q, f=f: f'Đơn riêng: {q} {f["unit"]} {_lower(f["name"])}', cap=6)


def _pet_shop(m):
    from . import inventory as inv
    for it in inv.catalogue('pet_shop'):
        if 'price' not in it:
            continue
        price = m.price(it['id'])
        m.retail(it['id'], lambda q, price=price: price * q,
                 lambda q, it=it: f'Đơn riêng: {q} {it["unit"]} {_lower(it["name"])}', cap=3 if price >= 40 else 6)


def _florist(m):
    from . import inventory as inv
    paper = m.first('paper_kraft', 'paper_white', 'paper_pink', 'paper_black')
    for it in inv.catalogue('florist'):
        if it.get('group') != 'flower':
            continue
        price = m.price(it['id'])
        m.retail(it['id'], lambda q, price=price: price * q,
                 lambda q, it=it: f'Đơn riêng: bó {q} cành {_lower(it["name"])}', lo=3, cap=12, extra={paper: 1})


def _tra_da(m):
    from .careers import tra_da
    m.fixed('Đơn riêng: ấm trà nóng 12 chén cho bàn cờ', {'che': 2}, 12 * m.price('tra_nong'))
    m.fixed('Đơn riêng: bình trà đá 24 cốc cho công trình', {'che': 4, 'da': 3}, 24 * m.price('tra_da'))
    for key in ('huong_duong', 'lac', 'keo_lac', 'banh_quy'):
        it = tra_da.ITEM[key]
        price = m.price(key)
        m.retail(key, lambda q, price=price: price * q,
                 lambda q, it=it: f'Đơn riêng: {q} {it["unit"]} {_lower(it["name"])}', cap=10)


def _ice_cream(m):
    from .careers import ice_cream
    hop = m.price('hop')
    for f in ice_cream.FLAVOURS:
        # A sealed 1.2 kg tub leaves whole, priced by weight as a take-away tub.
        revenue = hop * ice_cream.TUB_G // 100
        if f['id'] == 'bo':
            revenue = revenue * m.price('vien_bo') // max(1, m.price('vien'))
        m.fixed(f'Đơn riêng: hộp kem {f["short"]} mang về 1,2 kg', {f['id']: 1}, revenue)
    que = m.price('que')
    m.retail('que', lambda q: que * q, lambda q: f'Đơn riêng: {q} cây kem que đậu xanh', lo=2, cap=10)


def _com(m):
    from .careers import com
    plates = com.POT_VA // 2   # two ladles a plate
    p = lambda k: m.price(k, com.PRICES[k])
    m.fixed(f'Đơn riêng: {plates} hộp cơm tấm sườn cho văn phòng', {'gao_tam': 1, 'suon': plates, 'hop': plates},
            plates * (p('com_tam') + p('suon') + p('hop')))
    m.fixed(f'Đơn riêng: {plates} hộp cơm tấm trứng ốp', {'gao_tam': 1, 'trung': plates, 'hop': plates},
            plates * (p('com_tam') + p('trung') + p('hop')))
    m.fixed(f'Đơn riêng: {plates} hộp cơm trắng trứng ốp', {'gao': 1, 'trung': plates, 'hop': plates},
            plates * (p('com_trang') + p('trung') + p('hop')))


def _pho(m):
    from .careers import pho
    price = m.price('hop', pho.PRICES['hop'])
    for meat, x in pho.MEATS.items():
        m.fixed(f'Đơn riêng: phở {_lower(x["name"])} mang về', {'banh': 1, meat: 1, 'rau': 1, 'hop': 1}, price)


def _restaurant(m):
    names = dict(kimchi='kim chi', tomyum='tomyum', blackbean='tương đen', cheese='phô mai')
    for broth, name in names.items():
        m.fixed(f'Đơn riêng: mì cay {name} mang về', {'noodle': 1, 'pack_' + broth: 1, 'box': 1}, m.price(broth))


def _cafe_bakery(m):
    bean = m.first('beans_house', 'beans_robusta', 'beans_decaf')
    m.fixed('Đơn riêng: cà phê đen mang về', {bean: 1, 'cup': 1}, m.price('americano'))
    m.fixed('Đơn riêng: latte mang về', {bean: 1, 'milk': 1, 'cup': 1}, m.price('latte'))
    m.fixed('Đơn riêng: bạc xỉu mang về', {bean: 1, 'condensed': 1, 'milk': 1, 'cup': 1}, m.price('bacxiu'))
    m.fixed('Đơn riêng: matcha latte mang về', {'matcha': 1, 'milk': 1, 'cup': 1}, m.price('matcha_latte'))


def _salon(m):
    from . import inventory as inv
    m.fixed('Đơn riêng: gội và cắt tóc đơn giản', {'shampoo': 1, 'towel': 1}, m.price('cut'))
    for it in inv.catalogue('salon'):
        if 'price' in it:
            price = m.price(it['id'], it['price'])
            m.retail(it['id'], lambda q, price=price: price * q,
                     lambda q, it=it: f'Đơn riêng: bán {q} {it["unit"]} {_lower(it["name"])}', cap=2)


def _pet_care(m):
    m.fixed('Đơn riêng: tắm và sấy chó nhỏ', {'sh_normal': 1, 'towel': 1}, m.price('groom_s'))
    m.fixed('Đơn riêng: tắm và sấy cún con', {'sh_puppy': 1, 'towel': 1}, m.price('groom_s'))
    m.fixed('Đơn riêng: tắm chó da nhạy cảm', {'sh_sensitive': 1, 'towel': 1}, m.price('groom_m'))


def _nail(m):
    base = m.price('cat_dua')
    for key, colour in (('son_nude', 'hồng nude'), ('son_do', 'đỏ cherry'), ('son_den', 'đen bóng')):
        m.fixed(f'Đơn riêng: cắt dũa và sơn thường {colour}', {key: 1}, base + m.price('son_thuong'))
        m.fixed(f'Đơn riêng: sơn thường {colour} vẽ đầu móng French', {key: 1}, base + m.price('son_thuong') + m.price('french'))
    for key, colour in (('gel_nude', 'hồng nude'), ('gel_sua', 'trắng sữa'), ('gel_do', 'đỏ cherry')):
        m.fixed(f'Đơn riêng: cắt dũa và sơn gel {colour}', {key: 1}, base + m.price('son_gel'))
        m.fixed(f'Đơn riêng: sơn gel {colour} vẽ đầu móng French', {key: 1}, base + m.price('son_gel') + m.price('french'))


def _giupviec(m):
    room = m.price('room')
    for key, what in (('chai_kinh', 'lau kính hai phòng'), ('chai_da_nang', 'lau dọn hai phòng'),
                      ('chai_dau_mo', 'tẩy dầu mỡ gian bếp và phòng ăn'), ('chai_toilet', 'cọ hai nhà vệ sinh'),
                      ('chai_lau_san', 'lau sàn hai phòng')):
        m.fixed(f'Đơn riêng: {what}', {key: 1}, 2 * room)


def _photobooth(m):
    m.fixed('Đơn riêng: chụp và in một dải ảnh', {'giay_dai': 1}, m.price('strip'))
    m.fixed('Đơn riêng: chụp và in tờ ảnh đôi', {'giay_doi': 1}, m.price('double'))
    m.fixed('Đơn riêng: chụp và in ảnh lớn', {'giay_lon': 1}, m.price('big'))


def _farm(m):
    from . import inventory as inv
    feed = m.first('compost', 'npk')
    for it in inv.catalogue('farm'):
        if it.get('group') == 'seed':
            m.fixed(f'Việc riêng: làm luống, gieo {_lower(it["name"])} cho vườn bên', {it['id']: 1, feed: 1}, 14 + 2 * it['cost'])


def _repair(m):
    from . import inventory as inv
    from .careers import repair
    m.fixed('Việc riêng: bảo dưỡng xích xe', {'oil': 1}, m.price('bike', repair.DEVICES['bike']['labor']))
    for it in inv.catalogue('repair'):
        device = repair.DEVICES.get(it.get('group'))
        if device and 'price' in it:
            labor = m.price(it['group'], device['labor'])
            m.fixed(f'Việc riêng: thay {_lower(it["name"])} ({_lower(device["name"])})', {it['id']: 1},
                    m.price(it['id'], it['price']) + labor)


def _delivery(m):
    m.fixed('Đơn riêng: đóng gói và giao kiện nhỏ', {'bubble': 1, 'tape': 1}, 18)
    m.fixed('Đơn riêng: đóng kiện chống nước và giao', {'rainbag': 1, 'tape': 1}, 18)
    m.fixed('Đơn riêng: đóng kiện hàng lạnh và giao', {'coldpack': 1, 'tape': 1}, 22)
    m.fixed('Đơn riêng: ràng và giao kiện cồng kềnh', {'strap': 1, 'tape': 1}, 22)


def _drain(m):
    m.fixed('Việc riêng: vệ sinh đoạn thoát nước', {'bot': 1, 'gang_tay': 1}, 18)
    m.fixed('Việc riêng: thay ống xi-phông bồn rửa', {'xi_phong': 1, 'gang_tay': 1}, 26)


MENUS = dict(mother_baby=_mother_baby, pharmacy=_pharmacy, grocery=_grocery, fruit=_fruit, pet_shop=_pet_shop,
             florist=_florist, tra_da=_tra_da, ice_cream=_ice_cream, com=_com, pho=_pho, restaurant=_restaurant,
             cafe_bakery=_cafe_bakery, salon=_salon, pet_care=_pet_care, nail=_nail, giupviec=_giupviec,
             photobooth=_photobooth, farm=_farm, repair=_repair, delivery=_delivery, drain=_drain)


def target(cash: int) -> int:
    """Margin an order must keep at the worst service: wage + supplies, plus 20%."""
    return cash + max(1, math.ceil(cash / 5))


def menu(c: dict, career: str, cash: int) -> list:
    m = _Menu(c, career, target(cash))
    MENUS[career](m)
    return m.out


def pick(c: dict, career: str, served: int, cash: int, supplies: int) -> tuple | None:
    """(label, price, supplies, inputs) for the next staff order, or None."""
    rows = menu(c, career, cash)
    if not rows:
        return None
    total = sum(r[3] for r in rows)
    roll = zlib.crc32(f'staff:{career}:{served}'.encode()) % total
    for label, revenue, inputs, weight in rows:
        if roll < weight:
            return (label, revenue, supplies, inputs)
        roll -= weight
    return None  # unreachable


def why(c: dict, career: str, cash: int) -> str:
    """Plain words for a staff team stopped on stock: what is missing, or prices too low to pay the wage."""
    loose = _Menu(c, career, -10**9)
    MENUS[career](loose)
    if loose.out:
        return (f'Còn hàng nhưng giá bán hiện tại không đủ bù lương và vật tư {cash} xu mỗi đơn. '
                'Nhập thêm hàng (đơn lớn hơn sẽ có lãi) hoặc xem lại Bảng giá.')
    dry = _Dry(c, career)
    MENUS[career](dry)
    from .workplace_business import _item_names
    names = _item_names(career)
    gone = [names.get(i, i) for i in dry.used if _available(c, career, i) <= 0]
    if not gone:
        return 'Kệ hết hàng nhân viên bán được. Nhập thêm hàng để đội làm tiếp.'
    more = f' và {len(gone) - 4} món khác' if len(gone) > 4 else ''
    return 'Đội đang chờ hàng: hết ' + ', '.join(gone[:4]) + more + '. Nhập thêm để đội làm tiếp.'


class _Dry(_Menu):
    """Every entry as if the shelf were full: which items the menu draws on."""
    def __init__(self, c, career):
        super().__init__(c, career, -10**9)
        self.used = []

    def avail(self, item):
        if item is not None and item not in self.used:
            self.used.append(item)
        return 10**6
