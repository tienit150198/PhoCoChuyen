"""🧰 Phụ kiện nghề: small paid accessories, one purchase each, for one career (owner 21/10 "thêm phụ kiện vào cho người
ta nhé"). An accessory never does the job: it keeps something from going wrong or shows the player what to check.

* 🧊 Tủ trữ sữa riêng (cafe_bakery, feedback #454 "Xác suất sữa bị hỏng trong ngày khá cao… thêm phụ kiện tủ trữ đồ
  riêng"): fresh milk delivered from now on keeps one more day (2 → 3, game/inventory.py _receive_lot asks the career's
  life_bonus), the fresh milk on the shelf when it is bought too; the "Ca sữa tươi vừa mở có mùi chua" surprise turns up
  far less often (game/careers/cafe_bakery.py sour_keep).
* 📏 Máy kiểm tra độ tuổi (mother_baby, feedback #452 "khách mua mà độ tuổi nó bé hơn cái món quy định thì làm sao để bán
  đc", owner "phụ kiện kiểm tra tuổi … để check"): on an order with a known baby age, every box on the shelf shows ✓ / ✗
  against the baby's age, and when the asked box is not for that age it lists the suitable items in stock within the
  budget (game/giftshop.py age_check). The player still advises (💬 Gợi ý thay), picks, wraps and checks.

Save: the optional c['gadgets'] = {id: {'paid': xu, 'day': game day}}. NOT upgrade ids: 2.4.68 refuses an unknown id in
c['upgrades'] (engine.validate_career "Nâng cấp không hợp lệ"), and keeps a key it does not know (tests/test_career_gadgets.py
runs saves holding both accessories on `git archive` of 2.4.68). Paid from the workplace fund, like 🔧 Thiết bị nghề.
"""
from __future__ import annotations

KEY = 'gadgets'
ACTION = 'gadget_buy'

ITEMS = {
    'milk_fridge': dict(
        id='milk_fridge', career='cafe_bakery', emoji='🧊', name='Tủ trữ sữa riêng', price=220,
        tag='Sữa tươi giữ lâu hơn',
        description='Tủ mát riêng cho sữa tươi, giữ đều 2–4 °C.',
        effects=['🥛 Sữa tươi nhập về để được 3 ngày thay vì 2 (cả sữa đang có trên kệ khi lắp tủ).',
                 '🥛 Chuyện “ca sữa tươi có mùi chua” hiếm hơn nhiều.']),
    'age_checker': dict(
        id='age_checker', career='mother_baby', emoji='📏', name='Máy kiểm tra độ tuổi', price=120,
        tag='Soi nhãn tuổi giúp bạn',
        description='Quét nhãn trên hộp, so với tuổi bé khách nói.',
        effects=['📏 Mỗi món trên kệ hiện ✓ hợp / ✗ chưa hợp tuổi bé.',
                 '💡 Hộp khách hỏi chưa hợp tuổi: gợi ý món hợp tuổi, còn hàng, trong ngân sách. Bạn vẫn tự tư vấn, lấy hàng, gói và kiểm.']),
}


def of(career: str) -> list[dict]:
    return [x for x in ITEMS.values() if x['career'] == career]


def owned(c: dict, gid: str) -> bool:
    r = c.get(KEY) if isinstance(c, dict) else None
    return isinstance(r, dict) and isinstance(r.get(gid), dict)


def buy(s: dict, c: dict, career: str, p: dict) -> dict:
    """gadget_buy {item}: pay from the workplace fund, once."""
    from . import engine as e
    need = e.need
    g = ITEMS.get(p.get('item'))
    need(g is not None and g['career'] == career, 'Phụ kiện này không thuộc nghề đang làm.')
    need(not owned(c, g['id']), f'{g["name"]} đã có ở tiệm rồi.')
    need(c['money'] >= g['price'], f'Quỹ nghề còn thiếu {g["price"] - max(0, c["money"])} xu để mua {g["name"]}.')
    e.money(s, c, -g['price'], 'Mua ' + g['name'], category='upgrade')
    c.setdefault(KEY, {})[g['id']] = dict(paid=g['price'], day=c['day'])
    extra = ''
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    if mod and hasattr(mod, 'on_gadget'):
        extra = mod.on_gadget(s, c, g['id']) or ''
    e.log(s, c, 'upgrade', f'Đã lắp {g["emoji"]} {g["name"]}.')
    return dict(message=f'{g["emoji"]} {g["name"]} đã lắp.' + (' ' + extra if extra else ''), celebrate=True)


def public(c: dict, career: str) -> list[dict] | None:
    """The 🧰 Phụ kiện nghề cards for the Thiết bị sheet (None: this career sells none)."""
    rows = of(career)
    if not rows:
        return None
    return [dict(id=g['id'], emoji=g['emoji'], name=g['name'], price=g['price'], tag=g['tag'], description=g['description'],
                 effects=list(g['effects']), owned=owned(c, g['id']), short=0 if owned(c, g['id']) else max(0, g['price'] - max(0, c['money'])))
            for g in rows]


def validate(c: dict, career: str) -> None:
    from .engine import need, integer
    r = c.get(KEY)
    if r is None:
        return
    ids = {g['id'] for g in of(career)}
    need(isinstance(r, dict) and r and set(r) <= ids, 'Phụ kiện nghề không hợp lệ.')
    for v in r.values():
        need(isinstance(v, dict) and set(v) == {'paid', 'day'}, 'Phụ kiện nghề không hợp lệ.')
        integer(v['paid'], 0, 10**9)
        integer(v['day'], 1, 10**7)
