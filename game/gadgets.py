"""📱 Cửa hàng điện thoại Mây Mobile: phones and small gadgets, bought outright with xu (story mode).

Feedback F#205 (06/10): "có chỗ mua điện thoại mới, khoe được". The story only had an old phone (Anh Khoa's, see
game/life_content.py GIFTS['phone'], and the snatched phone of game/rui.py); this is where it is upgraded.

* One catalogue (ITEMS), two tabs: 📱 Điện thoại (five tiers, a cheap smartphone to a gold edition) and 🎧 Đồ công
  nghệ (earbuds, a smartwatch, a tablet, a games console, a camera). Fictional brands only. Priced like the garage
  (game/garage.py): the cheapest within two days of pay, the gold phone a rich player's toy.
* Paid in full like a vehicle: the cash in the wallet first, then the bank account (garage._take, wallet rows of the
  existing kind 'life', bank lines 'acc'); never a loan, never below 0, a wallet in debt buys nothing. One of each.
* 🔁 Thu cũ đổi mới (the story hook): the first phone takes the old phone in (unless `trade: false`), TRADE_IN xu
  off, once (`old`).
  A discount, not a payment: no xu is created, and the price paid (`p`) is what selling back uses.
* Selling back: SELL_PCT % of the price paid (rounded down to 5 xu), into the wallet. No daily fee, no upkeep.
* Showing off, cosmetic only (no income, no work bonus): the phone "đang dùng" (`hand`) is on the profile and the
  player's card in Phố nghề (social.snapshot), in the 2.5D avatar's hand when standing still (public/js/v4/look.js
  figure + public/js/isometric/character-art.js), and gives the light perks of its tier and every tier under it
  (PERKS: Chỉ đường remembers recent places, selfie frames, a phone skin on the HUD, a two-shot frame, gold trim).

State `s['journey']['gadgets']` (absent until the first purchase; older builds never read it: journey.validate allows
extra keys), see initial():
    v      VERSION
    own    {item id: {d: life day bought, p: price paid}}
    hand   the phone id "đang dùng", or None (the old phone while `old` is 0)
    old    0: the old phone is still yours, 1: traded in
    stats  {bought, sold}
Ids are stored in saves: never rename or remove one. An id this build does not know (a newer build wrote it) is kept
untouched and simply not shown, so a rollback never loses anything.
Commands (through journey.action, so journey.after and validate_state run): jr_gadget_buy {id, trade?, confirm},
jr_gadget_use {id | None}, jr_gadget_sell {id, confirm}. Deterministic: no draw.
"""
from __future__ import annotations

import re

from . import bank as bk

VERSION = 1
KIND = 'life'                     # journey wallet history kind (an existing one: older builds validate the row)
SELL_PCT = 65                     # selling back: 65 % of the price paid
TRADE_IN = 20                     # 🔁 the old phone, taken in once against the first phone
STATS = ('bought', 'sold')
BLOCK_KEYS = frozenset({'v', 'own', 'hand', 'old', 'stats'})
ITEM_KEYS = frozenset({'d', 'p'})
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
COMMANDS = ('jr_gadget_buy', 'jr_gadget_use', 'jr_gadget_sell')
SHOP = 'Mây Mobile'
WHERE = 'Phố dịch vụ'

GROUPS = (('phone', '📱', 'Điện thoại'), ('gear', '🎧', 'Đồ công nghệ'))
GROUP_IDS = tuple(g[0] for g in GROUPS)

# The light perks a phone in hand gives (its tier's and every tier's under it). The client draws them; the server only
# says which are on (public `perks`). No perk pays xu or speeds up work.
PERKS = (
    ('recent', '🧭', 'Chỉ đường nhớ 3 nơi vừa đi', 'Mở Chỉ đường là thấy ngay chỗ vừa ghé, khỏi gõ tìm.'),
    ('selfie', '📸', 'Khung selfie', 'Chụp selfie nhân vật với khung riêng của máy, lưu ảnh về khoe.'),
    ('skin', '🎨', 'Vỏ máy khoe trên hồ sơ', 'Màu vỏ máy viền quanh huy hiệu điện thoại trên hồ sơ của bạn.'),
    ('duo', '🪞', 'Khung selfie đôi', 'Màn gập đôi: hai dáng trong một tấm, như ảnh photobooth.'),
    ('gold', '✨', 'Viền vàng lấp lánh', 'Vỏ máy và khung selfie viền vàng, lấp lánh như tiệm vàng.'),
)
PERK_IDS = tuple(p[0] for p in PERKS)


def _i(iid, group, emoji, name, price, desc, *, tier=0, color='#8a8f98', brand=''):
    """tier: a phone's rank 1–5 (its perks are PERK_IDS[:tier]); 0 for gear. color: the shell, drawn in the hand."""
    return iid, dict(id=iid, group=group, emoji=emoji, name=name, price=price, desc=desc, tier=tier, color=color,
                     brand=brand)


# Cheapest first within each tab. A day's pay is ~50–90 xu (employment) minus 10–20 to live: the cheap phone is two
# days, the mid-range two weeks, the flagship a small car's deposit, the gold one next to a sports car.
ITEMS = dict((
    _i('may_lite', 'phone', '📱', 'Mây Lite 5', 150, 'Máy “quốc dân”: pin trâu, màn to, lướt mạng mượt. Đủ xài, khỏi lo.',
       tier=1, color='#7fb7d9', brand='Mây'),
    _i('sao_mai_s', 'phone', '📱', 'Sao Mai S12', 600, 'Tầm trung đáng tiền: camera chụp đêm khá ổn, sạc nhanh nửa tiếng đầy.',
       tier=2, color='#9d86c9', brand='Sao Mai'),
    _i('may_pro', 'phone', '📱', 'Mây Pro 16', 2400, 'Hàng đầu dòng: khung titan, ba camera, chụp quán phở cũng ra ảnh tạp chí.',
       tier=3, color='#3d4a5c', brand='Mây'),
    _i('sen_gap', 'phone', '📲', 'Sen Gập Fold 3', 6000, 'Gập lại như hộp phấn, mở ra thành máy tính bảng. Cả quán cà phê ngoái nhìn.',
       tier=4, color='#e7a3b8', brand='Sen'),
    _i('kim_long', 'phone', '📱', 'Kim Long Vàng 24K', 24000, 'Phiên bản giới hạn mạ vàng, khắc rồng, hộp gỗ lót nhung. Cầm lên là biết “dân chơi”.',
       tier=5, color='#d4af37', brand='Kim Long'),
    _i('tai_nghe', 'gear', '🎧', 'Tai nghe Sóc Pods', 120, 'Nhét tai là lọt thỏm, chống ồn đủ để không nghe khách than.',
       color='#f3f0e8', brand='Sóc'),
    _i('dong_ho', 'gear', '⌚', 'Đồng hồ Mây Watch', 450, 'Đếm bước, nhắc uống nước, rung nhẹ khi có tin nhắn của crush.',
       color='#2b2b30', brand='Mây'),
    _i('may_tinh_bang', 'gear', '💻', 'Máy tính bảng Mây Tab', 1200, 'Màn 11 inch, xem phim nằm võng hay vẽ thực đơn quán đều được.',
       color='#b8bec6', brand='Mây'),
    _i('may_game', 'gear', '🎮', 'Máy chơi game Rồng Con', 1600, 'Cắm tivi chơi bốn người, gỡ ra mang theo được. Tối thứ bảy cả xóm sang.',
       color='#d9534f', brand='Rồng Con'),
    _i('may_anh', 'gear', '📷', 'Máy ảnh Cò Trắng X', 3200, 'Máy ảnh không gương lật, ống kính chân dung xóa phông mịn như mơ.',
       color='#f3f0e8', brand='Cò Trắng'),
))
ORDER = tuple(ITEMS)
PHONES = tuple(i for i in ORDER if ITEMS[i]['group'] == 'phone')

# Anh Khoa's line when the first phone takes the old one in (game/life_content.py CAST 'anh_khoa').
TRADE_LINE = 'Anh Khoa cười: “Lên đời rồi hả? Máy cũ để anh lau lại, cho bé Tí học online.”'
OLD = dict(emoji='📞', name='Máy cũ', desc='Chiếc máy cũ còn xài tốt. Gọi được, nhắn được, chụp hình hơi mờ.')


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _gr():
    from . import garage
    return garage


def _fmt(n: int) -> str:
    return bk._fmt(n)


def lname(name: str) -> str:
    """A name inside a sentence: a phone is its brand name ("Mây Lite 5"), gear is a noun ("tai nghe Sóc Pods")."""
    return name if any(name == it['name'] and it['group'] == 'phone' for it in ITEMS.values()) else name[:1].lower() + name[1:]


def initial() -> dict:
    return dict(v=VERSION, own={}, hand=None, old=0, stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    g = j.get('gadgets') if isinstance(j, dict) else None
    return g if isinstance(g, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('gadgets'), dict):
        j['gadgets'] = initial()
    return j['gadgets']


def sell_price(paid: int) -> int:
    return max(0, int(paid) * SELL_PCT // 100 // 5 * 5)


def trade_in(s: dict, iid: str) -> int:
    """The xu off `iid` for the old phone: TRADE_IN on a phone while the old one is still yours, else 0."""
    g = get(s)
    if ITEMS[iid]['group'] != 'phone' or (g and g['old']):
        return 0
    return min(TRADE_IN, ITEMS[iid]['price'] - 10)


def why_not_buy(s: dict, iid: str, trade: bool = True) -> str | None:
    """Why `iid` cannot be bought now (None: it can). Shown on the disabled button."""
    j = s['journey']
    if not j.get('story'):
        return 'Cửa hàng điện thoại chỉ có trong chế độ hành trình.'
    it = ITEMS[iid]
    g = get(s)
    if g and iid in g['own']:
        return f'Bạn đã có {lname(it["name"])} rồi.'
    if j['wallet'] < 0:
        return f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ xong rồi hãy mua nhé.'
    short = it['price'] - (trade_in(s, iid) if trade else 0) - _gr()._have(s)['ready']
    if short > 0:
        return f'Còn thiếu {_fmt(short)} xu.'
    return None


def perks_of(iid: str | None) -> list[str]:
    it = ITEMS.get(iid) if iid else None
    return list(PERK_IDS[:it['tier']]) if it else []


# ---------------------------------------------------------------- save
def _item_ok(iid, x) -> bool:
    return (isinstance(iid, str) and ID_RE.fullmatch(iid) is not None and isinstance(x, dict) and set(x) == ITEM_KEYS
            and type(x['d']) is int and 1 <= x['d'] <= 10**6 and type(x['p']) is int and 1 <= x['p'] <= 10**7)


def validate(s: dict) -> None:
    """``s['journey']['gadgets']`` (absent in older saves). Unknown ids a newer build wrote are allowed by shape.
    Raises GameError like validate_state."""
    e = _core()
    g = get(s)
    j = s.get('journey')
    bad = 'Đồ công nghệ trong bản lưu không hợp lệ.'
    if g is None:
        e.need(not isinstance(j, dict) or j.get('gadgets') is None, bad, 'invalid_save')
        return
    e.need(set(g) == BLOCK_KEYS and g['v'] == VERSION, bad, 'invalid_save')
    own = g['own']
    e.need(isinstance(own, dict) and len(own) <= 64 and all(_item_ok(k, v) for k, v in own.items()), bad, 'invalid_save')
    e.need(g['hand'] is None or g['hand'] in own, bad, 'invalid_save')
    e.need(g['old'] in (0, 1) and type(g['old']) is int, bad, 'invalid_save')
    st = g['stats']
    e.need(isinstance(st, dict) and set(st) <= set(STATS) and all(type(v) is int and 0 <= v <= 10**9 for v in st.values()),
           bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep every item whose record still makes
    sense. Absent stays absent."""
    if not isinstance(j, dict) or 'gadgets' not in j:
        return
    g = j['gadgets']
    if not isinstance(g, dict):
        j['gadgets'] = initial()
        return
    out = initial()
    own = g.get('own') if isinstance(g.get('own'), dict) else {}
    out['own'] = {k: v for k, v in own.items() if _item_ok(k, v)}
    out['hand'] = g.get('hand') if g.get('hand') in out['own'] else None
    out['old'] = 1 if g.get('old') == 1 and type(g.get('old')) is int else 0
    st = g.get('stats') if isinstance(g.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if type(st.get(k)) is int and 0 <= st[k] <= 10**9 else 0 for k in STATS}
    if out != g:
        j['gadgets'] = out


# ---------------------------------------------------------------- commands
def _iid(p: dict) -> str:
    iid = p.get('id')
    _core().need(isinstance(iid, str) and iid in ITEMS, 'Chọn một món trong cửa hàng nhé.')
    return iid


def _mine(s: dict, iid: str) -> dict:
    g = get(s)
    _core().need(g is not None and iid in g['own'], f'Bạn chưa có {lname(ITEMS[iid]["name"])}.', 'not_owned')
    return g


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Cửa hàng điện thoại chỉ có trong chế độ hành trình.')
    day = j['life_day']
    if name == 'jr_gadget_buy':
        need(set(p) <= {'id', 'trade', 'confirm'} and p.get('trade', False) in (True, False), 'Thông tin mua hàng không hợp lệ.')
        iid = _iid(p)
        it = ITEMS[iid]
        g = get(s)
        if g and iid in g['own']:   # a second tap: nothing to pay
            return dict(message=f'Bạn đã có {lname(it["name"])} rồi.', duplicate=True)
        need(p.get('confirm') is True, f'Xác nhận mua {lname(it["name"])}.')
        trade = p.get('trade', True) and trade_in(s, iid) > 0   # the first phone takes the old one in unless told not to
        why = why_not_buy(s, iid, trade)
        need(why is None, why or '', 'not_enough')
        off = trade_in(s, iid) if trade else 0
        price = it['price'] - off
        how = _gr()._take(s, price, f'Mua đồ công nghệ · {it["name"]}')
        g = _ensure(s)
        g['own'][iid] = dict(d=day, p=price)
        g['stats']['bought'] = g['stats'].get('bought', 0) + 1
        tail = ''
        if it['group'] == 'phone':
            cur = ITEMS.get(g['hand']) if g['hand'] else None
            if cur is None or cur['tier'] < it['tier']:
                g['hand'] = iid
                tail = ' Đang dùng máy này.'
            else:
                tail = f' Vẫn dùng {lname(cur["name"])}; đổi máy ở mục “Của bạn”.'
        if off:
            g['old'] = 1
            tail += f' Thu cũ đổi mới: bớt {_fmt(off)} xu. {TRADE_LINE}'
        return dict(message=f'Đã trả {how} cho {lname(it["name"])}.{tail}')
    if name == 'jr_gadget_use':
        need(set(p) <= {'id'}, 'Thông tin không hợp lệ.')
        g = get(s)
        if p.get('id') is None:
            if g:
                g['hand'] = None
            return dict(message='Cất máy vào túi, không khoe trên hồ sơ nữa.')
        iid = _iid(p)
        need(ITEMS[iid]['group'] == 'phone', 'Chỉ chọn được điện thoại để dùng.')
        g = _mine(s, iid)
        g['hand'] = iid
        return dict(message=f'Giờ bạn dùng {lname(ITEMS[iid]["name"])}.')
    if name == 'jr_gadget_sell':
        need(set(p) <= {'id', 'confirm'}, 'Thông tin không hợp lệ.')
        iid = _iid(p)
        g = _mine(s, iid)
        it = ITEMS[iid]
        need(p.get('confirm') is True, f'Xác nhận bán {lname(it["name"])}.')
        back = sell_price(g['own'][iid]['p'])
        g['own'].pop(iid)
        if g['hand'] == iid:   # the best phone left, if any
            left = [x for x in PHONES if x in g['own']]
            g['hand'] = max(left, key=lambda x: ITEMS[x]['tier']) if left else None
        g['stats']['sold'] = g['stats'].get('sold', 0) + 1
        if back:
            _jr()._wallet(j, back, KIND, f'Bán đồ công nghệ · {it["name"]}')
        return dict(message=f'Đã bán {lname(it["name"])}, nhận {_fmt(back)} xu vào ví.')
    raise e.GameError('Thao tác cửa hàng điện thoại không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- views
def hand_view(s: dict) -> dict | None:
    """{id, emoji, name, color, tier} of the phone in use (None: none, the old phone, or one this build does not know)."""
    g = get(s)
    iid = g.get('hand') if g else None
    if iid not in ITEMS or iid not in g['own']:
        return None
    it = ITEMS[iid]
    return dict(id=iid, emoji=it['emoji'], name=it['name'], color=it['color'], tier=it['tier'])


def show_view(s: dict) -> dict | None:
    """What the player's card shows (social.snapshot): the phone in use and up to three gadgets, dearest first."""
    g = get(s)
    if not g:
        return None
    ph = hand_view(s)
    gear = sorted((i for i in g['own'] if i in ITEMS and ITEMS[i]['group'] == 'gear'), key=lambda i: -ITEMS[i]['price'])[:3]
    if not ph and not gear:
        return None
    out = dict(gear=[ITEMS[i]['emoji'] for i in gear])
    if ph:
        out.update(emoji=ph['emoji'], name=ph['name'], color=ph['color'], tier=ph['tier'])
    return out


def public(s: dict) -> dict:
    j = s['journey']
    g = get(s) or initial()
    own = [dict(id=i, day=x['d'], paid=x['p'], sell=sell_price(x['p'])) for i in ORDER if (x := g['own'].get(i))]
    why = {i: w for i in ORDER if i not in g['own'] and (w := why_not_buy(s, i))}
    hand = hand_view(s)
    return dict(story=bool(j.get('story')), have=_gr()._have(s), own=own, hand=hand, perks=perks_of(hand and hand['id']),
                old=g['old'], why=why, stats=dict(g['stats']))


def catalogue() -> dict:
    """Static list for the client (bootstrap content, cached)."""
    return dict(shop=SHOP, where=WHERE, groups=[dict(id=g[0], emoji=g[1], name=g[2]) for g in GROUPS],
                items=[dict(ITEMS[i], perks=perks_of(i)) for i in ORDER],
                perks=[dict(id=p[0], emoji=p[1], name=p[2], desc=p[3]) for p in PERKS],
                sell_pct=SELL_PCT, trade_in=TRADE_IN, old=dict(OLD))
