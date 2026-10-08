"""🏠 Nhà của bạn: a better rented room, buying a home and a mortgage at Ngân hàng Phố (story mode).

In-game calendar, shared with the bank's savings (game/bank.py): 1 tháng = MONTH_DAYS = 5 ngày sống,
1 năm = 12 tháng = YEAR_DAYS = 60 ngày sống. Prices are in xu; rates are quoted per year.

Where you live decides the "tiền phòng" part of the daily living cost (journey.living_cost):
* Bà Tám's attic (no `home`, or nothing rented or owned): the chapter's rent, as before;
* a rented room (`rent`): its own daily rent and a refundable deposit (tiền cọc), +comfort tinh thần a day
  (the Ký túc xá's bed has no comfort bonus: its roommates bring small moments instead, see below);
* your own home (`own`): no rent, only điện nước (upkeep), +comfort tinh thần a day;
* your spouse's home (`shared`, delivered through the marriage inbox by game/couple.py): the same,
  while the two of you stay married.

Buying: a down payment of at least DOWN_PCT % of the price plus a BUY_FEE_PCT % fee (công chứng, sang
tên), paid from the joint fund (married couples, optional), then the bank account, then cash. The rest
is a mortgage (vay mua nhà): it needs a bank account, a credit score from HOME_SCORE, steady income and
an installment within DTI_PCT % of a month's income; the yearly rate depends on the score. Installments
are taken every MONTH_DAYS life days from the account (then cash), like the bank's other loans.

Missed payments are gentle: a message the day before when the money is short, then GRACE life days of
grace with a retry every morning (no fee, no score change); only after that a small late fee, a
credit-score drop and one "lần trễ hạn" on the bank record (three of those is nợ xấu, as for other loans).
The comfort bonus pauses while a payment is late. The bank never takes the home: selling it (market value
minus a SELL_FEE_PCT % fee, the mortgage paid off first) is always the player's own choice.

Homes (HOMES, grouped as Phòng thuê / Căn hộ / Nhà phố / Biệt thự by GROUPS): the dearer ones (penthouse,
biệt thự) need a higher credit score for the mortgage (`score`); the installment limit is the same DTI rule.
0.9.13 raised every list price by 20 %. A home bought earlier keeps the price paid, its loan and schedule
(validate accepts OLD_PRICES); its market value still grows from the price paid, so nobody gets a windfall.
Rents did not change (the room's rent is part of the daily living cost, not a house price).

💹 07/10 (game/price_index.py, owner: "tăng giá tất cả mọi thứ"): buying a home costs its list price's index on top, as
its own line, 💹 Thuế trước bạ (`tax()`: +10 %, +20 % from 20 000 xu, +30 % from 60 000 xu of the list price), paid in
cash with the down payment and the fee, never from the joint fund and never lent. The list price itself (own.price, the
fee, the loan) stays: 1.9.9 pins it in validate (prices()), so a home bought under this build still loads there.
prices() already accepts the indexed price, so a later release can fold the tax into the list price. The tax buys no
value: the market value, the sale, the rent a tenant pays and the phí bảo trì still follow the list price, so it is a
pure sink and a home bought before 07/10 and sold after gains nothing. The closed room's daily rent is indexed (the
deposit is pinned in validate and comes back anyway), MOVE_FEE too. The dorm bed stays 7 xu: a new player's first bed,
kept at Bà Tám's attic price in chapter 2 and under half the closed room (7,7 would round to 8, +14 %).

🛏️ Ký túc xá Hẻm 7 (DORM, feedback #59 "ở ghép share tiền phòng"): a bed in a four-bed bunk room, rented and left
like the other room. Rent DORM_RENT a day: one xu more than Bà Tám's attic in chapter 1, the same in chapter 2 and
less from chapter 3 on (the attic follows journey.LIVING at 60 %); a small deposit; no comfort bonus. Its three
roommates (life_content.ROOMMATES) bring the small everyday moments: life cards of kind 'dorm' (game/life.py
_roll_dorm) and a line of the day on the home card (dorm_view: computed, never stored). Nothing new in the save:
`rent.kind` simply holds 'ky_tuc_xa' (an older build rejects that id: see the deploy notes). Moving between two
rented rooms is one command (jr_home_rent while renting the other one: its deposit comes back first).

🏘️ Several homes (VERSION 2, the owner's "cho phép sở hữu nhiều bất động sản"): up to OWNED_MAX homes at once.
`own` is still the one you live in (the comfort bonus, điện nước, reno.py's repairs, deco.py's room, the spouse's
shared home all read it, unchanged); `props` holds the others, each "Đang để trống" or "Cho thuê" (`let`). Each home
keeps its own price, loan, schedule and late fees; every installment is taken the same way.

🧾 Phí bảo trì (owner 03/10, the xu sinks): every home you own from 6 000 xu list price, lived in, empty or let, costs a
share of its price a tháng (game/upkeep.py HOME_BANDS: 0,2 % from 6 000, 0,3 % from 20 000, 0,35 % from 30 000 xu),
billed with the month's other bills; the listing and each home you own show it (`care`, xu a tháng). Until 03/10 an
empty home cost nothing at all; nothing is billed for the days before (upkeep.since).
* Buying another: the same down payment, fee and mortgage rules per home; the bank's 40 % limit counts the
  installments of every home loan already running (offer: `others`), so loans cannot pile up. A second home is
  bought "để trống" unless the player chooses to move in (`move_in`); the joint fund only pays for a home the
  couple moves into (the others belong to the buyer alone). The same listing cannot be bought twice.
* Dọn nhà (jr_home_move): into a home you own that is empty, for MOVE_FEE xu (a truck), shown before confirming.
  The home you leave becomes an empty one; a rented room is given back (deposit returned). reno.py's parts and
  upgrades of the home you leave are kept on it (`keep`) and come back when you return (worn by the days away);
  deco.py's furniture goes to the bag as on every move (never lost; the paints you bought stay yours).
* Cho thuê (jr_home_let): a tenant (TENANTS, picked from the journey seed) moves into an empty home and pays
  rent_of(kind) a month, RENT_BP a year of the list price (5 %: under a term deposit, as real rents are), at the
  home's own month boundary (the days its installments fall due), pro rata for a part month, into the bank
  account (else the wallet). Rent is not income for the bank's limit. Light, capped tenant moments: at most one
  every TENANT_GAP days, one boundary in TENANT_ODDS: the tenant pays LATE_DAYS late (never lost), or a small
  repair (FIX_PCT % of that month's rent) comes out of the rent. Never anything taken from the wallet.
  Taking the home back (jr_home_let on=False) settles the rent to that day.
* Selling (jr_home_sell, `id`): any home; the one you live in sends you back to Bà Tám's attic (move to another
  home first to live there). Paying (jr_home_pay / jr_home_payoff, `id`) works per home. Without `id` (a page
  loaded before 2) every command means the home you live in, as before.
Saves: upgrade() turns a version 1 block into version 2 in place (props [], and `mv`, `let`, `keep` on the home);
nothing else changes (loan, schedule, history, stats). validate() accepts both versions.

State `s['journey']['home']` (absent = never rented or bought: older saves load unchanged), see initial().
Commands arrive as `jr_home_*` through journey.action. Deterministic: the draws (the dorm's line of the day, a
tenant and their moments) are seeded by the journey seed, the home and the life day.
"""
from __future__ import annotations

import copy
import random

from . import archive as ar
from . import bank as bk
from . import bank_content as BK
from . import days as dy
from . import price_index as pi   # 💹 07/10: Thuế trước bạ (tax()), rooms' rent, the moving truck
from . import property_market as pm
from . import upkeep as up   # 🧾 phí bảo trì a tháng

VERSION = 2                       # 2: several homes (props); version 1 blocks are upgraded in place
KIND = 'home'                     # journey wallet history kind (journey.HISTORY_KINDS)
MONTH_DAYS = bk.MONTH_DAYS        # 5 life days
YEAR_DAYS = bk.YEAR_DAYS          # 60 life days

DOWN_PCT = 30                     # trả trước tối thiểu
BUY_FEE_PCT, SELL_FEE_PCT, FEE_MIN = 2, 3, 10
GROW_RATE, GROW_CAP_PCT = 300, 30  # market value: +3 %/năm on the price, at most +30 %
HOME_SCORE = 600
RATES = ((740, 900), (670, 1020), (0, 1140))   # score -> basis points per year (9 / 10,2 / 11,4 %); /12 per month
LOAN_MONTHS = (12, 24, 36)
LOAN_MIN = 100
DTI_PCT = bk.DTI_PCT              # the installment stays within 40 % of a month's income
GRACE = 3                         # life days of grace before a late fee
LATE_PCT, LATE_MIN = 2, 2
PAYOFF_FEE_PCT, PAYOFF_FEE_MIN = 1, 5
LOG_MAX, PAST_MAX = 30, 6
OWNED_MAX = 4                     # homes owned at once, the one you live in included
MOVE_FEE = pi.price(20)           # dọn nhà: a truck for the furniture (base 20 xu, 💹 07/10)
RENT_BP = 1000                    # reference monthly asking rent: list price × 10 % a year / 12
TENANT_GAP = 3 * MONTH_DAYS       # life days between two tenant moments, at least
TENANT_ODDS = 4                   # one month boundary in four (seeded) brings one
LATE_DAYS = 2                     # a tenant who asks pays this many days later
FIX_PCT, FIX_MIN = 20, 3          # a small repair, out of that month's rent
STATS = ('bought', 'sold', 'paid_off', 'ontime', 'late', 'comfort', 'home_days', 'rent_days', 'moves', 'rent_in')
STATS_V1 = STATS[:8]
COMMANDS = ('jr_home_rent', 'jr_home_leave', 'jr_home_buy', 'jr_home_pay', 'jr_home_payoff', 'jr_home_sell',
            'jr_home_move', 'jr_home_let')
OWN_V1 = ('id', 'kind', 'price', 'day', 'down', 'fee', 'joint', 'loan')
OWN_KEYS = OWN_V1 + ('mv', 'let', 'keep')   # mv: moves into it (the spouse's inbox id), let: the tenant, keep: reno parts
LET_KEYS = ('who', 'since', 'rent', 'paid', 'ev', 'owed', 'od')

# Tenants (emoji, name inside a sentence). Indexes are stored in saves: append only.
TENANTS = (('👩‍🏫', 'Cô giáo Hà'), ('👨‍👩‍👧', 'Vợ chồng anh Tài'), ('🧑‍🎓', 'Hai bạn sinh viên'), ('👩‍💼', 'Chị Lan'),
           ('👴', 'Ông Sáu'), ('👨‍🍳', 'Anh Phúc đầu bếp'))
REPAIRS = ('vòi nước bị rỉ', 'bóng đèn nhà tắm bị hư', 'ổ khóa cửa bị kẹt', 'máy nước nóng chập chờn', 'cửa sổ bị kẹt bản lề')

ATTIC = dict(emoji='🏚️', name='Căn gác nhà Bà Tám', where='Trên gác nhà Bà Tám, đầu hẻm',
             desc='Phòng nhỏ trên gác, cửa sổ nhìn ra hẻm. Tiền phòng và cơm nước Bà Tám tính theo ngày.')

# How "Nhà của bạn" groups the listings (id, emoji, name, colour of the home's tile in the UI).
GROUPS = (('rent', '🛏️', 'Phòng thuê', '#e0a93b'), ('apartment', '🏢', 'Căn hộ', '#4f9fd1'),
          ('townhouse', '🏠', 'Nhà phố', '#d9734e'), ('villa', '🏰', 'Biệt thự', '#3f9a78'))
GROUP_IDS = tuple(g[0] for g in GROUPS)

# Homes, cheapest first within each group. `price` is the list price in xu (0.9.13: +20 % on the 0.9.5 prices),
# `upkeep` the daily điện nước (apartments add phí quản lý, so they cost more to run than a house of the
# same comfort), `comfort` the tinh thần added each morning. Optional: `perk` (one line the listing shows),
# `score` (the credit score the bank needs to lend on this home, HOME_SCORE when absent).
# Ids are stored in saves: never rename or remove one.
HOMES = {
    'ky_tuc_xa': dict(kind='rent', group='rent', emoji='🛏️', name='Ký túc xá Hẻm 7', where='Hẻm 7 · giường tầng',
                      desc='Phòng máy lạnh bốn giường tầng, giường nào cũng có rèm riêng và tủ khóa. Ở ghép với ba bạn trẻ, chia nhau tiền phòng.',
                      perk='👥 Ở ghép với 3 bạn cùng phòng', rent=7, deposit=20, comfort=0),   # 💹 07/10: stays 7 (below)
    'tro_moi': dict(kind='rent', group='rent', emoji='🛏️', name='Phòng trọ khép kín', where='Hẻm 12, cạnh chợ',
                    desc='Phòng 18 m² có gác lửng, cửa sổ, nhà vệ sinh riêng. Cô Hạnh chủ nhà cho nuôi mèo.',
                    rent=pi.price(14), deposit=60, comfort=1),
    'tap_the': dict(kind='own', group='apartment', emoji='🏢', name='Căn tập thể cũ', where='Khu tập thể đầu phố, tầng 4',
                    desc='35 m², hai phòng nhỏ. Cầu thang hơi dốc nhưng hàng xóm vui tính, chiều nào cũng có người pha trà.',
                    price=1800, upkeep=2, comfort=1),
    'can_ho_studio': dict(kind='own', group='apartment', emoji='🛋️', name='Studio Nắng Mai', where='Tòa Nắng Mai, tầng 9',
                          desc='Căn studio 28 m², bếp mở, cửa kính lớn đón nắng sớm. Nhỏ mà xinh, phí quản lý hơi cao.',
                          price=2400, upkeep=4, comfort=2),
    'can_ho_mini': dict(kind='own', group='apartment', emoji='🏙️', name='Căn hộ mini', where='Đường Hoa Sữa',
                        desc='30 m², có thang máy, ban công nhỏ phơi đồ, bảo vệ giữ xe dưới sảnh.',
                        price=3600, upkeep=3, comfort=2),
    'can_ho_1pn': dict(kind='own', group='apartment', emoji='☁️', name='Căn hộ Mây Xanh', where='Tòa Mây Xanh, tầng 12 · 1 phòng ngủ',
                       desc='Một phòng ngủ riêng, phòng khách nhìn ra hồ, sảnh có quầy trà sữa. Chiều gió lồng lộng.',
                       price=5400, upkeep=5, comfort=3),
    'can_ho_2pn': dict(kind='own', group='apartment', emoji='🪁', name='Căn hộ Cánh Diều', where='Tòa Cánh Diều, tầng 15 · 2 phòng ngủ',
                       desc='Hai phòng ngủ, hai ban công, sân chơi trẻ con dưới sảnh. Đủ chỗ cho cả nhà.',
                       price=10200, upkeep=6, comfort=4),
    'penthouse': dict(kind='own', group='apartment', emoji='🌃', name='Penthouse Mây Xanh', where='Tầng thượng tòa Mây Xanh',
                      desc='Tầng cao nhất, sân thượng riêng trồng rau thơm. Tối ngồi ngắm cả phố lên đèn.',
                      perk='🌿 Sân thượng riêng', price=21600, upkeep=9, comfort=5, score=670),
    'nha_pho': dict(kind='own', group='townhouse', emoji='🏠', name='Nhà phố nhỏ', where='Hẻm xe hơi sau chợ',
                    desc='Một trệt một lầu, ngang 3 mét, phòng khách đủ kê bộ bàn ghế gỗ và một bàn thờ nhỏ.',
                    price=7800, upkeep=4, comfort=3),
    'nha_san': dict(kind='own', group='townhouse', emoji='🏡', name='Nhà có sân', where='Cuối hẻm, gần bờ kênh',
                    desc='Sân trước có cây khế và giàn bông giấy, cổng sắt sơn xanh, chỗ để hai chiếc xe.',
                    price=14400, upkeep=5, comfort=4),
    'biet_thu_vuon': dict(kind='own', group='villa', emoji='🌳', name='Biệt thự Vườn Cau', where='Đường ven kênh, cuối phố',
                          desc='Hai tầng giữa vườn cau và hàng chuối, hồ bơi nhỏ sau nhà. Sáng nghe chim, chiều hái rau, cuối tuần cả xóm sang chơi.',
                          perk='🌳 Vườn rộng, có xích đu', price=36000, upkeep=12, comfort=6, score=700),
    'biet_thu_song': dict(kind='own', group='villa', emoji='🌅', name='Biệt thự Sông Hồng', where='Bờ sông, cuối con đê',
                          desc='Ba tầng nhìn ra sông, hồ bơi nhỏ sau nhà. Hoàng hôn đổ xuống mặt nước mỗi chiều.',
                          perk='🌊 Hồ bơi và bến ngắm sông', price=60000, upkeep=16, comfort=7, score=740),
}
for _H in HOMES.values():   # 💹 07/10: the daily điện nước of a home you own (the list prices stay: see tax())
    if _H.get("upkeep"):
        _H["upkeep"] = pi.price(_H["upkeep"], luxury=False)
OWN = tuple(k for k, v in HOMES.items() if v['kind'] == 'own')
RENT = tuple(k for k, v in HOMES.items() if v['kind'] == 'rent')
DORM = 'ky_tuc_xa'
DORM_RENT = HOMES[DORM]['rent']
# The drawing of the bunk room (house.js): two bunks, the player has the bottom bed by the window.
BEDS = ('left_top', 'left_bottom', 'right_top', 'right_bottom')
YOUR_BED = 'right_bottom'

# List prices before 0.9.13. A home bought then keeps the price paid (own.price, the loan and its schedule),
# and its market value keeps growing from that price (value_of), so the +20 % is no windfall for owners.
OLD_PRICES = {'tap_the': (1500,), 'can_ho_mini': (3000,), 'nha_pho': (6500,), 'nha_san': (12000,)}


def prices(kind: str) -> tuple[int, ...]:
    """Every list price a save may hold for `kind`: today's, then older ones, then the 💹 indexed one (07/10: not
    written yet; accepted so that a later release can fold tax() into the list price and still roll back here)."""
    return (HOMES[kind]['price'],) + OLD_PRICES.get(kind, ()) + (pi.price(HOMES[kind]['price']),)


def tax(kind: str) -> int:
    """💹 Thuế trước bạ (07/10): the price index on the list price, paid in cash on top of the down payment and fee."""
    return pi.extra(HOMES[kind]['price'])


def need_score(kind: str) -> int:
    """The credit score the bank needs to lend on this home."""
    return HOMES[kind].get('score', HOME_SCORE)


def lname(name: str) -> str:
    """A home's name inside a sentence: "Biệt thự Sông Hồng" -> "biệt thự Sông Hồng"."""
    return name[:1].lower() + name[1:]


# What the neighbours say when you move (whole sentences, no names of real people).
MOVE_LINES = {
    'rent': 'Bà Tám dúi cho bịch trái cây: “Ở đâu cũng nhớ về ăn cơm với bà nghe cháu.”',
    'own': 'Bà Tám lau nước mắt: “Có nhà rồi, mừng cho cháu quá. Bữa nào tân gia nhớ gọi bà!”',
    'back': 'Bà Tám mở cửa gác, phủi lại cái chiếu: “Phòng vẫn để đó, về lúc nào cũng được.”',
    'dorm_in': 'Quân, Anh Tuấn và My dọn sẵn giường dưới cạnh cửa sổ, My còn dán tên bạn lên tủ.',
    'dorm_out': 'My dúi cho cái móc khóa, Anh Tuấn hẹn bữa nào ghé ăn mì chung.',
    'move': 'Hàng xóm cũ phụ khiêng cái tủ lên xe, còn dặn: “Cuối tuần nhớ ghé uống trà nghe!”',
}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _rn():
    from . import reno
    return reno


def _es():
    from . import estates
    return estates


def _couple():
    try:
        from . import couple
        return couple
    except ImportError:   # a build without marriage
        return None


_fmt = bk._fmt


def _ceil10(x: int) -> int:
    return -(-int(x) // 10) * 10


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, seq=0, day=int(day), rent=None, own=None, shared=None, past=[], log=[],
                stats={k: 0 for k in STATS}, props=[])


def _up(h: dict, day: int = 1) -> None:
    """Version 1 -> 2 in place, lossless: the home you live in gets mv/let/keep, `props` starts empty; every
    other field (the loan, its schedule and fees, the log, the stats) stays as it is. Idempotent."""
    for k, v in initial(day).items():
        if k != 'v':
            h.setdefault(k, copy.deepcopy(v))
    if isinstance(h.get('stats'), dict):
        for k in STATS:
            h['stats'].setdefault(k, 0)
    for x in [h.get('own')] + (h['props'] if isinstance(h.get('props'), list) else []):
        if isinstance(x, dict):
            x.setdefault('mv', 0)
            x.setdefault('let', None)
            x.setdefault('keep', None)
    if h.get('v') == 1:
        h['v'] = VERSION


def get(s: dict) -> dict | None:
    j = s.get('journey')
    h = j.get('home') if isinstance(j, dict) else None
    if not isinstance(h, dict):
        return None
    if h.get('v') == 1 or 'props' not in h:   # a version 1 block that has not been through upgrade() yet
        _up(h, int(j.get('life_day') or 1))
    return h


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('home'), dict):
        j['home'] = initial(j['life_day'])
    return get(s)


def upgrade(j: dict) -> None:
    """On load: version 1 becomes 2 (_up), future fields join here (setdefault only). Absent stays absent."""
    h = j.get('home') if isinstance(j, dict) else None
    if not isinstance(h, dict):
        return
    _up(h, int(j.get('life_day') or 1))


def homes(h: dict | None) -> list[dict]:
    """Every home you own: the one you live in first, then the others."""
    if not h:
        return []
    return ([h['own']] if h['own'] else []) + list(h['props'])


def find(h: dict | None, hid) -> dict | None:
    return next((x for x in homes(h) if x['id'] == hid), None)


def rent_of(kind: str) -> int:
    """A month's rent from a tenant: RENT_BP a year of today's list price."""
    return -(-HOMES[kind]['price'] * RENT_BP * pm.quote(kind)['rent_bp'] // (10000 * 12 * 10000))


def active_lease(j: dict) -> dict | None:
    lease = j.get('rental')
    return lease if isinstance(lease, dict) and j.get('life_day', 0) < lease.get('end_day', 0) else None


def demand(ask: int, reference: int) -> int:
    """Daily percent chance; decreases to zero at three times reference rent."""
    return max(0, min(90, (300 * reference - 100 * ask) // (4 * max(1, reference))))


def _tick_ad(s: dict, h: dict, x: dict, day: int, notes: list) -> None:
    j = s['journey']
    ad = j.get('rental_ads', {}).get(x['id'])
    if not ad or not ad.get('active') or x['let'] or day <= ad['checked']:
        return
    ad['checked'] = day
    rng = random.Random(f"rental-demand|{j.get('seed', 0)}|{x['id']}|{day}")
    if rng.randrange(100) >= demand(ad['rent'], rent_of(x['kind'])):
        return
    who = rng.randrange(len(TENANTS))
    x['let'] = dict(who=who, since=day, rent=ad['rent'], paid=day, ev=day, owed=0, od=0)
    ad['active'] = False
    label = f"{TENANTS[who][1]} thuê {HOMES[x['kind']]['name']}, {_fmt(ad['rent'])} xu/tháng."
    _log(h, day, label)
    notes.append(label)


def tenant(L: dict) -> tuple[str, str]:
    return TENANTS[L['who']] if 0 <= L['who'] < len(TENANTS) else ('🙂', 'Người thuê')


def _log(h: dict, day: int, text: str, amt: int = 0) -> None:
    h['log'] = ar.last(h['log'] + [dict(day=int(day), text=text[:140], amt=int(amt))], LOG_MAX, 'home.log', ar.JOURNEY)


def _seq(h: dict) -> str:
    h['seq'] += 1
    return f'h{h["seq"]}'


def down_min(price: int) -> int:
    return _ceil10(price * DOWN_PCT / 100)


def buy_fee(price: int) -> int:
    return max(FEE_MIN, -(-price * BUY_FEE_PCT // 100))


def sell_fee(value: int) -> int:
    return max(FEE_MIN, -(-value * SELL_FEE_PCT // 100))


def value_of(own: dict, day: int, basis: int = 10000) -> int:
    """Market value today: the price plus GROW_RATE per year held, capped, rounded down to 10 xu."""
    price = own['price']
    held = max(0, day - own['day'])
    grown = price + price * GROW_RATE * held // (10000 * YEAR_DAYS)
    base = min(price * (100 + GROW_CAP_PCT) // 100, grown)
    return base * pm.quote(own['kind'])['multiplier_bp'] // basis // 10 * 10


def rate_for(score: int) -> int:
    return next(rate for low, rate in RATES if score >= low)


def attic_rent(j: dict) -> int:
    return _jr().LIVING.get(j['chapter'], _jr().LIVING[_jr().LAST]) * 6 // 10


def _spouse(s: dict) -> dict | None:
    m = s.get('marriage')
    sp = m.get('spouse') if isinstance(m, dict) else None
    return sp if isinstance(sp, dict) and sp.get('status') == 'married' else None


def _shared_ok(s: dict, sh: dict | None) -> bool:
    """The spouse's home counts while the two are still married to each other."""
    if not sh:
        return False
    sp = _spouse(s)
    if not sp:
        return False
    return type(sp.get('couple')) is not int or sp['couple'] == sh['couple']


def where(h: dict | None) -> tuple[str, str | None]:
    """('own'|'shared'|'rent'|'attic', home kind)."""
    if not h:
        return 'attic', None
    if h['own']:
        return 'own', h['own']['kind']
    if h['shared']:
        return 'shared', h['shared']['kind']
    if h['rent']:
        return 'rent', h['rent']['kind']
    return 'attic', None


def living(j: dict, total: int) -> dict:
    """journey.living_cost: the day's total split into rent (or điện nước at home) and meals."""
    rent = total * 6 // 10
    meals = total - rent
    place, kind = where(j.get('home') if isinstance(j.get('home'), dict) else None)
    lease = active_lease(j)
    if lease:
        place, kind = 'lease', lease['kind']
    if place in ('own', 'shared', 'lease'):
        rent, label = HOMES[kind]['upkeep'], 'Cơm nước và điện nước nhà mình'
    elif place == 'rent':
        rent, label = HOMES[kind]['rent'], 'Tiền giường ký túc xá và cơm nước' if kind == DORM else 'Tiền phòng trọ và cơm nước'
    else:
        label = 'Tiền phòng và cơm nước'
    return dict(total=rent + meals, rent=rent, meals=meals, label=label, where=place)


def _spirit(s: dict, n: int) -> int:
    L = s['journey'].get('life')
    if not isinstance(L, dict) or type(L.get('spirit')) is not int:
        return 0
    before = L['spirit']
    L['spirit'] = max(0, min(100, before + n))
    return L['spirit'] - before


# ---------------------------------------------------------------- mortgage maths (mirrored in public/js/v4/house.js)
def month_bp(rate: int) -> int:
    return rate // 12


def schedule(principal: int, rate: int, months: int, start: int) -> list[dict]:
    bp = month_bp(rate)
    pay = bk.installment(principal, bp, months)
    rows, rest = [], principal
    for k in range(1, months + 1):
        i = bk._interest(rest, bp)
        part = rest if k == months else max(0, min(rest, pay - i))
        rows.append(dict(k=k, due=start + MONTH_DAYS * k, principal=part, interest=i, amount=part + i, paid=0, fee=0, late=False))
        rest -= part
    return rows


def quote(principal: int, rate: int, months: int, start: int = 0) -> dict:
    rows = schedule(principal, rate, months, start)
    return dict(rows=rows, installment=rows[0]['amount'], interest=sum(r['interest'] for r in rows),
                total=sum(r['amount'] for r in rows))


def offer(s: dict, score: int = HOME_SCORE) -> dict:
    """The bank's answer before amounts: ok, why, text, the rate for this score, the monthly room.
    `score`: the credit score the home needs (need_score(kind)); the listing asks with HOME_SCORE."""
    b = bk.get(s)
    if b is None:
        return dict(ok=False, why='no_account', text='Mở tài khoản Ngân hàng Phố trước rồi mới vay mua nhà được.',
                    rate=RATES[-1][1], room=0, score=None)
    why, text = bk._screen(s, b, score)
    inc = bk.income(s)
    others = home_due(get(s))
    room = max(0, inc['avg'] * MONTH_DAYS * DTI_PCT // 100 - bk._weekly_due(b) * MONTH_DAYS // 7 - others)
    return dict(ok=why is None, why=why, text=text, rate=rate_for(b['score']), room=room, score=b['score'], others=others)


def home_due(h: dict | None) -> int:
    """What the home loans already running take in a month (each one's largest installment still to pay):
    the bank's 40 % limit counts them all before lending on another home."""
    return sum(max((r['amount'] - r['paid'] for r in x['loan']['rows'] if r['paid'] < r['amount']), default=0)
               for x in homes(h) if x['loan'])


def _payoff(ln: dict, day: int, fee: bool = True) -> dict:
    """Early settlement: overdue rows in full, the rest of the principal, interest for the days used, a small fee."""
    overdue = sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount'])
    future = [r for r in ln['rows'] if r['due'] > day and r['paid'] < r['amount']]
    principal = sum(r['principal'] for r in future)
    used = 0
    if future:
        start = future[0]['due'] - MONTH_DAYS
        used = -(-principal * month_bp(ln['rate']) * max(0, day - start) // (10000 * MONTH_DAYS))
    charge = max(PAYOFF_FEE_MIN, -(-principal * PAYOFF_FEE_PCT // 100)) if principal and fee else 0
    return dict(overdue=overdue, principal=principal, interest=used, fee=charge, total=overdue + principal + used + charge,
                saved=sum(r['interest'] for r in future) - used)


def _late(ln: dict | None) -> bool:
    return bool(ln) and any(r['late'] and r['paid'] < r['amount'] for r in ln['rows'])


# ---------------------------------------------------------------- the daily tick
def _what(h: dict, x: dict) -> str:
    """The loan in the bank's words: the home you live in keeps "vay mua nhà"; another home is named."""
    return 'vay mua nhà' if x is h['own'] else f'vay mua {lname(HOMES[x["kind"]]["name"])}'


def _close_loan(s: dict, h: dict, x: dict, day: int, why: str) -> None:
    x['loan'] = None
    s['journey']['stats']['home_paid'] = s['journey']['stats'].get('home_paid', 0) + 1
    h['stats']['paid_off'] += 1
    b = bk.get(s)
    if b is not None and why:
        bk._score(b, day, why)


def _tick_loan(s: dict, h: dict, x: dict, n: int, notes: list) -> None:
    b = bk.get(s)
    ln = x['loan']
    if b is None or ln is None:
        return
    name = HOMES[x['kind']]['name']
    what = _what(h, x)
    What = what[:1].upper() + what[1:]
    tag = '' if x is h['own'] else f' · {name}'
    total = len(ln['rows'])
    j = s['journey']
    for r in ln['rows']:
        if r['paid'] >= r['amount']:
            continue
        left = r['amount'] - r['paid']
        if r['due'] == n + 1 and b['balance'] + max(0, j['wallet']) < left:
            notes.append('🏠 ' + bk._inbox(b, n, 'sms', f'{BK.BANK_NAME}: Ngày mai (Ngày {r["due"]}) đến hạn trả góp nhà kỳ {r["k"]}/{total}{tag}, '
                                                        f'{_fmt(left)} xu. Tài khoản và ví hiện chưa đủ, quý khách nhớ nộp thêm nhé.'))
        if r['due'] > n:
            continue
        if bk._debit(s, b, left, f'Trả góp nhà kỳ {r["k"]}/{total} · {name}', n):
            r['paid'] = r['amount']
            bk._log(b, n, 'loan', f'Kỳ {r["k"]}/{total} · {What}', -left)
            if not r['late']:
                bk._score(b, n, 'home_ok')
                h['stats']['ontime'] += 1
                bk._inbox(b, n, 'sms', BK.INSTALLMENT_SMS.format(bank=BK.BANK_NAME, amount=_fmt(left), k=r['k'], n=total, what=what))
            else:
                notes.append(f'🏠 Đã trích {_fmt(left)} xu trả kỳ {r["k"]} khoản {what} đang trễ.')
            continue
        late_for = n - r['due']
        if late_for == 0:
            notes.append('🏠 ' + bk._inbox(b, n, 'sms', f'{BK.BANK_NAME}: Kỳ trả góp nhà {r["k"]}/{total}{tag} ({_fmt(left)} xu) chưa trích được vì '
                                                        f'tài khoản và ví chưa đủ. Quý khách có {GRACE} ngày ân hạn, ngân hàng thử lại mỗi sáng, chưa tính phí.'))
        elif late_for == GRACE and not r['late']:
            fee = max(LATE_MIN, -(-r['amount'] * LATE_PCT // 100))
            r.update(late=True, fee=r['fee'] + fee, amount=r['amount'] + fee)
            b['stats']['fees'] += fee
            b['stats']['late'] += 1
            b['misses'] += 1
            h['stats']['late'] += 1
            bk._score(b, n, 'home_late')
            bk._log(b, n, 'loan', f'Phạt trễ hạn kỳ {r["k"]} · {What}', -fee)
            notes.append('⚠️ ' + bk._inbox(b, n, 'sms', BK.REMIND_SMS[1].format(bank=BK.BANK_NAME, what=f'trả góp nhà kỳ {r["k"]}{tag}',
                                                                              amount=_fmt(r['amount'] - r['paid']))))
        elif r['late'] and late_for > GRACE and (late_for - GRACE) % MONTH_DAYS == 0:
            notes.append('📞 ' + bk._call(s, b, n, what, r['amount'] - r['paid'], late_for))
    if all(r['paid'] >= r['amount'] for r in ln['rows']):
        _close_loan(s, h, x, n, 'home_done')
        _log(h, n, f'Trả xong khoản vay mua {lname(name)}.')
        notes.append(f'🎉 Bạn đã trả xong khoản vay mua nhà. {name} giờ hoàn toàn là của bạn!')


def _rent_due(L: dict, n: int) -> int:
    """The rent for the days since the last payment (one month at most)."""
    return L['rent'] * min(MONTH_DAYS, max(0, n - L['paid'])) // MONTH_DAYS


def _settle(s: dict, h: dict, x: dict, day: int) -> int:
    """The tenant leaves: the rent up to `day` and anything they asked to pay later, into the account (else the wallet)."""
    L = x['let']
    got = _rent_due(L, day) + L['owed']
    x['let'] = None
    if got:
        _receive(s, got, f'Tiền thuê {lname(HOMES[x["kind"]]["name"])}', day)
        h['stats']['rent_in'] += got
    return got


def _tick_let(s: dict, h: dict, x: dict, n: int, notes: list) -> None:
    """A tenant's morning: the rent at the home's month boundary (the days its installments fall due), now and
    then one light moment (TENANT_GAP, TENANT_ODDS). Never takes anything from the player."""
    L = x['let']
    name = lname(HOMES[x['kind']]['name'])
    who = tenant(L)[1]
    if L['owed'] and n >= L['od']:
        got = L['owed']
        L.update(owed=0, od=0)
        _receive(s, got, f'Tiền thuê {name}', n)
        h['stats']['rent_in'] += got
        notes.append(f'🏠 {who} gửi đủ {_fmt(got)} xu tiền nhà {name} còn khất.')
    if (n - x['day']) % MONTH_DAYS or n <= L['paid']:
        return
    amount = _rent_due(L, n)
    L['paid'] = n
    if amount == L['rent'] and n - L['ev'] >= TENANT_GAP:
        rng = random.Random(f'tenant|{s["journey"].get("seed", 0)}|{x["id"]}|{n}')
        roll = rng.randrange(TENANT_ODDS * 2)
        if roll == 0:
            L.update(owed=L['owed'] + amount, od=n + LATE_DAYS, ev=n)
            _log(h, n, f'{who} xin khất tiền thuê {name} {LATE_DAYS} ngày.')
            notes.append(f'🏠 {who} xin khất tiền nhà {name} {LATE_DAYS} ngày, hứa gửi đủ {_fmt(amount)} xu.')
            return
        if roll == 1:
            cost = max(FIX_MIN, amount * FIX_PCT // 100)
            amount = max(0, amount - cost)
            L['ev'] = n
            what = rng.choice(REPAIRS)
            _log(h, n, f'Sửa {what} ở {name}: {_fmt(cost)} xu, trừ vào tiền thuê.')
            notes.append(f'🔧 {who} báo {what} ở {name}: thợ sửa hết {_fmt(cost)} xu, trừ vào tiền thuê tháng này.')
    if amount:
        _receive(s, amount, f'Tiền thuê {name}', n)
        h['stats']['rent_in'] += amount
        notes.append(f'🏠 Nhận {_fmt(amount)} xu tiền thuê {name}.')


def _tick(s: dict, h: dict, n: int, notes: list) -> None:
    """Morning of life day `n`: the tenants' rent first (it may pay an installment), then every home loan."""
    for x in h['props']:
        _tick_ad(s, h, x, n, notes)
        if x['let']:
            _tick_let(s, h, x, n, notes)
    for x in homes(h):
        if x['loan']:
            _tick_loan(s, h, x, n, notes)
    place, kind = where(h)
    lease = s['journey'].get('rental')
    if lease and lease['start_day'] <= n < lease['end_day']:
        place, kind = 'lease', lease['kind']
    if place == 'attic':
        return
    h['stats']['rent_days' if place in ('rent', 'lease') else 'home_days'] += 1
    if not _late(h['own']['loan'] if h['own'] else None):
        h['stats']['comfort'] += _spirit(s, HOMES[kind]['comfort'])


def _check_shared(s: dict, h: dict, notes: list) -> None:
    sh = h['shared']
    if sh and not _shared_ok(s, sh):
        h['shared'] = None
        _log(h, s['journey']['life_day'], f'Dọn khỏi {lname(HOMES[sh["kind"]]["name"])} của {sh["name"]}.')
        if not h['own'] and not h['rent']:
            notes.append('🏚️ ' + MOVE_LINES['back'])


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the home up to `journey.life_day` (idempotent): installments, comfort, the spouse's home."""
    j = s.get('journey')
    h = get(s)
    if not h or not j.get('story'):
        return []
    notes: list[str] = []
    _check_shared(s, h, notes)
    target = int(j['life_day'])
    h['day'] = max(h['day'], target - 400)
    while h['day'] < target:
        h['day'] += 1
        _tick(s, h, h['day'], notes)
    if j.get('rental') and not active_lease(j):
        j.pop('rental', None)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- the spouse's home (game/couple.py, game/marriage.py)
def partner_effects(state: dict, couple_id: int, side: str, other_sid: str, effect) -> list:
    """End accepted sharing when a home is sold. Moving in requires family consent."""
    h = get(state)
    if not h or not (state.get('journey') or {}).get('story'):
        return []
    out = []
    for p in h['past']:
        out.append(effect(f'homeoff:{couple_id}:{side}:{p["id"]}', other_sid, 'home', 0, 'Căn nhà chung đã bán',
                          dict(set='out', couple=couple_id, id=p['id'])))
    return out


def apply_effect(s: dict, data: dict) -> None:
    """A 'home' effect from the marriage inbox, applied to the spouse's save (never raises)."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story') or not isinstance(data, dict):
        return
    what, couple, hid = data.get('set'), data.get('couple'), data.get('id')
    if type(couple) is not int or not isinstance(hid, str) or not 1 <= len(hid) <= 16:
        return
    if what == 'in' and data.get('kind') in OWN:
        h = _ensure(s)
        name = str(data.get('name') or 'Người ấy')[:24] or 'Người ấy'
        h['shared'] = dict(couple=couple, id=hid, kind=data['kind'], name=name, since=int(j['life_day']))
        _log(h, j['life_day'], f'Về ở chung {lname(HOMES[data["kind"]]["name"])} của {name}.')
        if h['rent']:   # moving in with the spouse ends a rented room, the deposit comes back
            _leave_rent(s, h, j['life_day'])
    elif what == 'out':
        h = get(s)
        if h and h['shared'] and h['shared']['id'] == hid and h['shared']['couple'] == couple:
            sh = h['shared']
            h['shared'] = None
            _log(h, j['life_day'], f'{sh["name"]} đã bán {lname(HOMES[sh["kind"]]["name"])}.')


def accept_shared(s: dict, data: dict) -> None:
    """Explicit consent, inside the family transaction. Personal homes remain owned.

    Moving in is free; a personal home becomes empty with its renovation retained.
    A rented room ends and returns its deposit once. Furniture remains personal.
    """
    _core().need(not active_lease(s['journey']), 'Trả nhà đang thuê của người chơi trước khi dọn về nhà chung.', 'active_lease')
    h = _ensure(s)
    if h['own']:
        _move_out(s, h, s['journey']['life_day'])
    apply_effect(s, dict(data, set='in'))
    _es().move_out(s['journey'])   # 🏰 out of the villa too


def leave_shared(s: dict) -> None:
    h = get(s)
    if h and h['shared']:
        sh = h['shared']
        h['shared'] = None
        _log(h, s['journey']['life_day'], f'Dọn khỏi {lname(HOMES[sh["kind"]]["name"])} của {sh["name"]}.')


# ---------------------------------------------------------------- commands
def _have(s: dict) -> dict:
    j = s['journey']
    b = bk.get(s)
    return dict(wallet=max(0, j['wallet']), balance=b['balance'] if b else 0)


def _take(s: dict, amount: int, label: str, day: int) -> None:
    """Take `amount` from the bank account first, then cash. The caller checked it is there."""
    b = bk.get(s)
    from_acc = min(b['balance'], amount) if b else 0
    if from_acc:
        b['balance'] -= from_acc
        bk._log(b, day, 'acc', label, -from_acc)
    if amount > from_acc:
        _jr()._wallet(s['journey'], -(amount - from_acc), KIND, label)


def _receive(s: dict, amount: int, label: str, day: int) -> str:
    """Money back to the player: into the bank account when there is one, else the wallet."""
    b = bk.get(s)
    if b is not None:
        b['balance'] += amount
        bk._log(b, day, 'acc', label, amount)
        return 'tài khoản ngân hàng'
    _jr()._wallet(s['journey'], amount, KIND, label)
    return 'ví'


def _leave_rent(s: dict, h: dict, day: int) -> int:
    r = h['rent']
    h['rent'] = None
    what = 'giường' if r['kind'] == DORM else 'phòng'
    _jr()._wallet(s['journey'], r['deposit'], KIND, f'Nhận lại tiền cọc {lname(HOMES[r["kind"]]["name"])}')
    _log(h, day, f'Trả {what} {lname(HOMES[r["kind"]]["name"])}, nhận lại {_fmt(r["deposit"])} xu tiền cọc.', r['deposit'])
    return r['deposit']


def _int(p: dict, key: str, low: int, high: int, msg: str) -> int:
    v = p.get(key)
    _core().need(type(v) is int and low <= v <= high, msg)
    return v


def _pick(h: dict | None, p: dict) -> dict | None:
    """The home a command is about: `id`, or (a page loaded before several homes) the one you live in."""
    hid = p.get('id')
    if hid is None:
        return h['own'] if h else None
    return find(h, hid) if isinstance(hid, str) else None


def _move_out(s: dict, h: dict, day: int) -> None:
    """The home you live in becomes one of the others, empty; reno.py's parts and upgrades stay with it."""
    own = h['own']
    own['keep'] = _rn().leave_home(s, own, day)
    h['own'] = None
    h['props'].append(own)


def _move_in(s: dict, h: dict, x: dict, day: int) -> None:
    h['props'] = [o for o in h['props'] if o is not x]
    keep, x['keep'] = x['keep'], None
    x['mv'] += 1
    h['own'] = x
    if x['id'] in s['journey'].get('rental_ads', {}):
        s['journey']['rental_ads'][x['id']]['active'] = False
    _rn().enter_home(s, x, keep, day)


def next_rent_day(x: dict, day: int) -> int:
    """The next month boundary of a home (its installments' days): when the tenant pays."""
    return day + MONTH_DAYS - (day - x['day']) % MONTH_DAYS


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_home_*` commands. Everything is checked before anything changes (a declined mortgage is a
    normal result: the bank's inquiry stays on the record, like bank.py's declines)."""
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác nhà ở không hợp lệ.', 'unknown_action')
    need(j['story'], 'Thuê và mua nhà chỉ có trong chế độ hành trình.', 'story_only')
    day = j['life_day']
    h = get(s)
    own = h['own'] if h else None
    rent = h['rent'] if h else None
    need(not active_lease(j) or name in ('jr_home_pay', 'jr_home_payoff', 'jr_home_let', 'jr_home_sell'),
         'Trả nhà đang thuê của người chơi trước khi đổi chỗ ở nhé.', 'active_lease')
    if name == 'jr_home_rent':
        kind = p.get('kind')
        need(kind in RENT, 'Chọn phòng muốn thuê nhé.')
        need(not own, 'Bạn đã có nhà riêng rồi.')
        need(not rent or rent['kind'] != kind, 'Bạn đang ở đây rồi.')
        need(p.get('confirm') is True, 'Xác nhận thuê phòng.')
        H = HOMES[kind]
        have = _have(s)
        back = rent['deposit'] if rent else 0          # moving from the other rented room: its deposit comes back first
        need(have['wallet'] + have['balance'] + back >= H['deposit'],
             f'Tiền cọc {_fmt(H["deposit"])} xu: bạn còn thiếu {_fmt(H["deposit"] - have["wallet"] - have["balance"] - back)} xu.', 'not_enough')
        h = _ensure(s)
        if rent:
            _leave_rent(s, h, day)
        _take(s, H['deposit'], f'Đặt cọc {lname(H["name"])}', day)
        h['rent'] = dict(kind=kind, since=day, deposit=H['deposit'])
        _es().move_out(j)   # 🏰 out of the villa too (game/estates.py move_out)
        _log(h, day, f'Thuê {lname(H["name"])}, đặt cọc {_fmt(H["deposit"])} xu.', -H['deposit'])
        bed = kind == DORM
        msg = (f'Đã thuê {lname(H["name"])}: tiền {"giường" if bed else "phòng"} {_fmt(H["rent"])} xu/ngày, '
               f'cọc {_fmt(H["deposit"])} xu (trả lại khi dọn đi).')
        line = MOVE_LINES['dorm_in' if bed else 'rent']
        if back:
            msg += f' Đã trả {"giường " if rent["kind"] == DORM else ""}{lname(HOMES[rent["kind"]]["name"])}, nhận lại {_fmt(back)} xu tiền cọc.'
            line = MOVE_LINES['dorm_in' if bed else 'dorm_out' if rent['kind'] == DORM else 'rent']
        return dict(message=f'{msg} {line}')
    if name == 'jr_home_leave':
        need(rent, 'Bạn không thuê phòng nào.')
        need(p.get('confirm') is True, 'Xác nhận trả phòng.')
        bed = rent['kind'] == DORM
        back = _leave_rent(s, h, day)
        return dict(message=f'Đã trả {"giường" if bed else "phòng"}, nhận lại {_fmt(back)} xu tiền cọc vào ví. '
                            + (MOVE_LINES['dorm_out'] + ' ' if bed else '') + MOVE_LINES['back'])
    if name == 'jr_home_buy':
        kind = p.get('kind')
        need(kind in OWN, 'Chọn căn nhà muốn mua nhé.')
        H = HOMES[kind]
        need(not any(x['kind'] == kind for x in homes(h)), f'{H["name"]} đã là nhà của bạn rồi.', 'owned')
        need(len(homes(h)) < OWNED_MAX, f'Bạn đang có {OWNED_MAX} căn nhà. Bán bớt một căn rồi hãy mua thêm nhé.', 'too_many')
        # A page loaded before several homes never sends it. Living in a home already (yours, or the spouse's: feedback
        # #137 "đang ở biệt thự, mua căn hộ xong ở luôn căn hộ") the new one stays empty unless the player says so.
        move_in = p.get('move_in', own is None and not _shared_ok(s, h['shared'] if h else None) and not _es().living_in(j))
        need(type(move_in) is bool, 'Chọn dọn về ở hay để trống nhé.')
        price, fee, duty = H['price'], buy_fee(H['price']), tax(kind)
        down = _int(p, 'down', down_min(price), price, f'Trả trước từ {_fmt(down_min(price))} xu ({DOWN_PCT}% giá nhà) tới {_fmt(price)} xu.')
        loan = price - down
        need(loan == 0 or loan >= LOAN_MIN, f'Vay ít nhất {_fmt(LOAN_MIN)} xu, hoặc trả đủ luôn nhé.')
        pay = down + fee + duty
        joint = p.get('joint', 0)
        need(type(joint) is int and 0 <= joint <= pay, 'Số xu lấy từ quỹ chung không hợp lệ.')
        need(joint <= down + fee, f'Quỹ chung góp tới {_fmt(down + fee)} xu (trả trước và phí); thuế trước bạ trả từ ví hoặc tài khoản nhé.', 'no_joint')
        need(not joint or move_in, 'Quỹ chung chỉ góp mua căn nhà cả hai cùng về ở.', 'no_joint')
        need(p.get('confirm') is True, 'Xác nhận ký hợp đồng mua nhà.')
        have = _have(s)
        short = pay - joint - have['balance'] - have['wallet']
        need(short <= 0, f'Trả trước, phí và thuế cần {_fmt(pay)} xu: bạn còn thiếu {_fmt(short)} xu.', 'not_enough')
        if joint:
            acc = bk.joint(s)
            need(acc is not None, 'Bạn chưa có quỹ chung vợ chồng.', 'no_joint')
            need(acc['balance'] >= joint, f'Quỹ chung chỉ còn {_fmt(acc["balance"])} xu.', 'not_enough')
        b = bk.get(s)
        months, q, rate = 0, None, 0
        if loan:
            months = p.get('months')
            need(months in LOAN_MONTHS, 'Chọn thời hạn vay nhé.')
            o = offer(s, need_score(kind))
            need(o['why'] != 'no_account', o['text'], 'no_account')
            rate = o['rate']
            q = quote(loan, rate, months, day)
            need(p.get('total_interest') == q['interest'], 'Điều khoản vay vừa thay đổi. Xem lại lịch trả góp rồi ký nhé.', 'stale_quote')
            if o['why'] != 'many':
                b['inq'] = (b['inq'] + [day])[-bk.INQ_MAX:]
                bk._score(b, day, 'inquiry')
            if not o['ok']:
                return dict(message=f'Hồ sơ vay mua nhà chưa được duyệt. {o["text"]}', approved=False)
            if q['installment'] > o['room']:
                others = f', đã trừ {_fmt(o["others"])} xu trả góp các căn đang vay' if o['others'] else ''
                return dict(message=f'Hồ sơ vay mua nhà chưa được duyệt: mỗi kỳ {_fmt(q["installment"])} xu vượt {DTI_PCT}% thu nhập một tháng '
                                    f'({_fmt(o["room"])} xu{others}). Trả trước nhiều hơn hoặc vay dài hơn nhé.', approved=False, why='dti')
        h = _ensure(s)
        if joint:   # its own database transaction, idempotent by ref (a retried command never pays twice)
            sp = _spouse(s) or {}
            _couple().joint_spend(s, joint, f'Mua {lname(H["name"])}', f'home{sp.get("side", "x")}{day}n{h["seq"] + 1}', kind='home')
        hid = _seq(h)
        _take(s, pay - duty - joint, f'Trả trước mua {lname(H["name"])}', day)
        if duty:
            _take(s, duty, f'💹 Thuế trước bạ · {lname(H["name"])}', day)
        ln = None
        if loan:
            ln = dict(principal=loan, rate=rate, months=months, start=day, rows=q['rows'])
            bk._log(b, day, 'loan', f'Giải ngân vay mua nhà: {_fmt(loan)} xu trả thẳng cho bên bán', 0)
            bk._inbox(b, day, 'sms', f'{BK.BANK_NAME}: Khoản vay mua nhà {_fmt(loan)} xu đã giải ngân cho bên bán. Trả góp {months} kỳ, mỗi kỳ '
                                     f'{_fmt(q["installment"])} xu, cứ {MONTH_DAYS} ngày một kỳ, kỳ đầu Ngày {q["rows"][0]["due"]}.')
        x = dict(id=hid, kind=kind, price=price, day=day, down=down, fee=fee, joint=joint, loan=ln, mv=0, let=None, keep=None)
        j.setdefault('property_market_basis', {})[hid] = pm.quote(kind)['multiplier_bp']
        left, back = h['own'], 0
        if move_in:
            if left:
                _move_out(s, h, day)
            back = _leave_rent(s, h, day) if h['rent'] else 0
            h['own'] = x
            _es().move_out(j)   # 🏰 out of the villa too
        else:
            h['props'].append(x)
        h['stats']['bought'] += 1
        j['stats']['homes_bought'] = j['stats'].get('homes_bought', 0) + 1
        _log(h, day, f'Mua {lname(H["name"])} giá {_fmt(price)} xu' + (f', vay {_fmt(loan)} xu' if loan else ', trả đủ một lần') + '.', -pay)
        msg = f'Chúc mừng! {H["name"]} ở {H["where"]} giờ là nhà của bạn. Đã trả {_fmt(pay)} xu (gồm {_fmt(fee)} xu phí công chứng, sang tên'
        msg += f', {_fmt(duty)} xu thuế trước bạ)' if duty else ')'
        msg += f', trong đó {_fmt(joint)} xu từ quỹ chung.' if joint else '.'
        if loan:
            msg += f' Khoản vay {_fmt(loan)} xu trả {months} kỳ, mỗi kỳ khoảng {_fmt(q["installment"])} xu, kỳ đầu {dy.on_day(s, q["rows"][0]["due"])}.'
        if back:
            msg += f' Đã trả phòng trọ, nhận lại {_fmt(back)} xu tiền cọc.'
        if not move_in:
            return dict(message=f'{msg} Căn này đang để trống: dọn về ở hoặc cho thuê lúc nào cũng được.', approved=True, home=kind, id=hid)
        if left:
            msg += f' {HOMES[left["kind"]]["name"]} giờ để trống.'
        return dict(message=f'{msg} {MOVE_LINES["own"] if not left else MOVE_LINES["move"]}', approved=True, home=kind, id=hid)
    if name == 'jr_home_move' and p.get('to') == 'shared':
        # 💞 back to the spouse's home (feedback #137): the home you live in becomes an empty one, as on any move.
        sh = h['shared'] if h else None
        need(_shared_ok(s, sh), 'Bạn không có nhà chung với người ấy để về.', 'no_shared')
        need(own is not None, 'Bạn đang ở nhà chung rồi.', 'here')
        need(p.get('confirm') is True, 'Xác nhận dọn nhà.')
        have = _have(s)
        short = MOVE_FEE - have['wallet'] - have['balance']
        hn = lname(HOMES[sh['kind']]['name'])
        need(short <= 0, f'Thuê xe dọn nhà {_fmt(MOVE_FEE)} xu: bạn còn thiếu {_fmt(short)} xu.', 'not_enough')
        _take(s, MOVE_FEE, f'Thuê xe dọn về {hn}', day)
        _move_out(s, h, day)
        _es().move_out(j)   # 🏰 out of the villa too
        h['stats']['moves'] += 1
        _log(h, day, f'Dọn về ở chung {hn} của {sh["name"]}.', -MOVE_FEE)
        return dict(message=f'Đã dọn về ở chung {hn} của {sh["name"]}, xe chở đồ {_fmt(MOVE_FEE)} xu. '
                            f'{HOMES[own["kind"]]["name"]} giờ để trống. {MOVE_LINES["move"]}')
    if name == 'jr_home_move':
        x = find(h, p.get('id')) if h and isinstance(p.get('id'), str) else None
        need(x is not None, 'Chọn căn nhà muốn dọn về nhé.')
        H = HOMES[x['kind']]
        need(x is not own, 'Bạn đang ở đây rồi.', 'here')
        need(not x['let'], f'{H["name"]} đang cho thuê: báo khách trả nhà trước rồi mới dọn về được nhé.', 'let')
        need(p.get('confirm') is True, 'Xác nhận dọn nhà.')
        have = _have(s)
        back = rent['deposit'] if rent else 0
        short = MOVE_FEE - have['wallet'] - have['balance'] - back
        need(short <= 0, f'Thuê xe dọn nhà {_fmt(MOVE_FEE)} xu: bạn còn thiếu {_fmt(short)} xu.', 'not_enough')
        if rent:
            _leave_rent(s, h, day)
        _take(s, MOVE_FEE, f'Thuê xe dọn về {lname(H["name"])}', day)
        if own:
            _move_out(s, h, day)
        _move_in(s, h, x, day)
        _es().move_out(j)   # 🏰 out of the villa too
        h['stats']['moves'] += 1
        _log(h, day, f'Dọn về {lname(H["name"])}.', -MOVE_FEE)
        msg = f'Đã dọn về {lname(H["name"])}, xe chở đồ {_fmt(MOVE_FEE)} xu.'
        if own:
            msg += f' {HOMES[own["kind"]]["name"]} giờ để trống.'
        if back:
            msg += f' Đã trả phòng, nhận lại {_fmt(back)} xu tiền cọc.'
        return dict(message=f'{msg} {MOVE_LINES["move"]}')
    if name == 'jr_home_let':
        x = find(h, p.get('id')) if h and isinstance(p.get('id'), str) else None
        need(x is not None, 'Chọn căn nhà nhé.')
        H = HOMES[x['kind']]
        on = p.get('on')
        need(type(on) is bool, 'Chọn cho thuê hay lấy lại nhà nhé.')
        need(p.get('confirm') is True, 'Xác nhận nhé.')
        hn = lname(H['name'])
        if on:
            need(x is not own, 'Bạn đang ở căn này: dọn sang căn khác rồi mới cho thuê được nhé.', 'here')
            need(not x['let'], f'{H["name"]} đang có người thuê rồi.', 'let')
            need(not x.get('joint'), 'Nhà mua bằng quỹ chung cần giữ quyền của cả hai, chưa thể cho thuê.', 'joint_home')
            ask = p.get('rent', rent_of(x['kind']))
            need(type(ask) is int and 1 <= ask <= bk.AMOUNT_MAX, 'Giá thuê phải là số xu nguyên dương.', 'bad_rent')
            ads = j.setdefault('rental_ads', {})
            old = ads.get(x['id'], {})
            ads[x['id']] = dict(rent=ask, since=day, checked=max(day, old.get('checked', day)), active=True)
            _log(h, day, f'Đăng cho thuê {hn}, {_fmt(ask)} xu/tháng; đang tìm khách.')
            return dict(message=f'Đã đăng {hn}: {_fmt(ask)} xu mỗi {MONTH_DAYS} ngày sống. Khách sẽ cân nhắc từ ngày sống tiếp theo.')
        ad = j.get('rental_ads', {}).get(x['id'])
        if ad and ad.get('active') and not x['let']:
            ad['active'] = False
            return dict(message='Đã gỡ tin cho NPC thuê nhà.')
        need(x['let'], f'{H["name"]} đang để trống.', 'empty')
        tname = tenant(x['let'])[1]
        got = _settle(s, h, x, day)
        _log(h, day, f'{tname} trả nhà {hn}.', got)
        return dict(message=f'{tname} đã trả nhà {hn}' + (f', gửi nốt {_fmt(got)} xu tiền thuê' if got else '') + '. Căn nhà đang để trống.')
    if name in ('jr_home_pay', 'jr_home_payoff'):
        x = _pick(h, p)
        need(x and x['loan'], 'Bạn không có khoản vay mua nhà nào.')
        ln = x['loan']
        what = _what(h, x)
        What = what[:1].upper() + what[1:]
        tag = '' if x is own else f' · {HOMES[x["kind"]]["name"]}'
        b = bk.get(s)
        have = _have(s)
        if name == 'jr_home_pay':
            rows = [r for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']]
            if not rows:
                rows = [next(r for r in ln['rows'] if r['paid'] < r['amount'])]
            amount = sum(r['amount'] - r['paid'] for r in rows)
            need(have['balance'] + have['wallet'] >= amount, f'Cần {_fmt(amount)} xu: tài khoản và ví còn thiếu '
                                                              f'{_fmt(amount - have["balance"] - have["wallet"])} xu.', 'not_enough')
            _take(s, amount, f'Trả góp nhà kỳ {", ".join(str(r["k"]) for r in rows)}{tag}', day)
            for r in rows:
                r['paid'] = r['amount']
            bk._log(b, day, 'loan', f'Trả kỳ {", ".join(str(r["k"]) for r in rows)} · {What}', -amount)
            msg = f'Đã trả {_fmt(amount)} xu cho khoản {what}.'
            if all(r['paid'] >= r['amount'] for r in ln['rows']):
                _close_loan(s, h, x, day, 'home_done')
                _log(h, day, f'Trả xong khoản {what}.')
                msg += ' Khoản vay đã trả xong, căn nhà hoàn toàn là của bạn!'
            return dict(message=msg)
        need(p.get('confirm') is True, 'Xác nhận tất toán khoản vay mua nhà.')
        off = _payoff(ln, day)
        need(have['balance'] + have['wallet'] >= off['total'], f'Tất toán cần {_fmt(off["total"])} xu: tài khoản và ví còn thiếu '
                                                                f'{_fmt(off["total"] - have["balance"] - have["wallet"])} xu.', 'not_enough')
        _take(s, off['total'], f'Tất toán sớm {what}', day)
        b['stats']['fees'] += off['fee']
        bk._log(b, day, 'loan', f'Tất toán sớm {what} · phí {_fmt(off["fee"])} xu', -off['total'])
        _close_loan(s, h, x, day, 'home_done')
        _log(h, day, f'Tất toán sớm khoản {what}: {_fmt(off["total"])} xu.', -off['total'])
        return dict(message=f'Đã tất toán {_fmt(off["total"])} xu (phí trả trước hạn {_fmt(off["fee"])} xu), bớt được '
                            f'{_fmt(max(0, off["saved"]))} xu tiền lãi. Căn nhà giờ không còn nợ!')
    # jr_home_sell
    x = _pick(h, p)
    need(x, 'Bạn chưa có nhà để bán.')
    need(p.get('confirm') is True, 'Xác nhận bán nhà.')
    value = value_of(x, day, s['journey'].get('property_market_basis', {}).get(x['id'], 10000))
    need(p.get('value') == value, 'Giá thị trường vừa thay đổi. Xem lại rồi bán nhé.', 'stale_quote')
    fee = sell_fee(value)
    off = _payoff(x['loan'], day, fee=False) if x['loan'] else None
    got = value - fee - (off['total'] if off else 0)
    need(got >= 0, 'Tiền bán nhà chưa đủ trả hết khoản vay. Nộp thêm tiền trả bớt nợ rồi hãy bán nhé.', 'underwater')
    H = HOMES[x['kind']]
    live = x is own
    b = bk.get(s)
    left = ''
    if x['let']:
        tname = tenant(x['let'])[1]
        rent_back = _settle(s, h, x, day)
        left = f' {tname} dọn đi' + (f', gửi nốt {_fmt(rent_back)} xu tiền thuê.' if rent_back else '.')
    if off:
        bk._log(b, day, 'loan', f'Bán nhà, trả hết {_what(h, x)}: {_fmt(off["total"])} xu', -off['total'])
        _close_loan(s, h, x, day, '')
    to = _receive(s, got, f'Tiền bán {lname(H["name"])}', day) if got else 'ví'
    h['past'] = ar.last(h['past'] + [dict(id=x['id'], kind=x['kind'], bought=x['day'], sold=day, price=x['price'], got=got)], PAST_MAX, 'home.past', ar.JOURNEY)
    if live:
        h['own'] = None
    else:
        h['props'] = [o for o in h['props'] if o is not x]
    j.get('rental_ads', {}).pop(x['id'], None)
    j.get('property_market_basis', {}).pop(x['id'], None)
    h['stats']['sold'] += 1
    _log(h, day, f'Bán {lname(H["name"])} được {_fmt(value)} xu, phí {_fmt(fee)} xu' + (f', trả nợ vay {_fmt(off["total"])} xu' if off else '') + '.', got)
    msg = f'Đã bán {lname(H["name"])} giá {_fmt(value)} xu (phí môi giới, thuế {_fmt(fee)} xu)'
    msg += f', trả hết nợ vay {_fmt(off["total"])} xu' if off else ''
    msg += f'. {_fmt(got)} xu đã về {to}.' + left
    return dict(message=msg + (' ' + MOVE_LINES['back'] if live and where(h)[0] == 'attic' else ''))


def action(s: dict, name: str, p: dict) -> dict:
    """Entry from journey.action (which runs journey.after and validate_state)."""
    return apply(s, name, p or {})


# ---------------------------------------------------------------- views
def rules() -> dict:
    return dict(month_days=MONTH_DAYS, year_days=YEAR_DAYS, down_pct=DOWN_PCT, buy_fee_pct=BUY_FEE_PCT, sell_fee_pct=SELL_FEE_PCT,
                fee_min=FEE_MIN, grow_rate=GROW_RATE, grow_cap_pct=GROW_CAP_PCT, home_score=HOME_SCORE,
                rates=[dict(min=low, rate=rate) for low, rate in RATES], months=list(LOAN_MONTHS), loan_min=LOAN_MIN, dti_pct=DTI_PCT,
                grace=GRACE, late_pct=LATE_PCT, late_min=LATE_MIN, payoff_fee_pct=PAYOFF_FEE_PCT, payoff_fee_min=PAYOFF_FEE_MIN,
                owned_max=OWNED_MAX, move_fee=MOVE_FEE, rent_bp=RENT_BP, late_days=LATE_DAYS, fix_pct=FIX_PCT)


def catalogue() -> dict:
    """The homes on the market, static (journey.content()['homes'], sent once at bootstrap): public()'s
    market rows carry only what changes (how much is still missing), the browser joins the two by id."""
    homes = []
    for k, H in HOMES.items():
        row = dict(id=k, kind=H['kind'], group=H['group'], emoji=H['emoji'], name=H['name'], where=H['where'], desc=H['desc'],
                   comfort=H['comfort'], perk=H.get('perk'))
        if H['kind'] == 'rent':
            row.update(rent=H['rent'], deposit=H['deposit'])
        else:
            p, fee = H['price'], buy_fee(H['price']) + tax(k)   # fee: what is paid on top of the down payment (💹 tax in)
            row.update(price=p, upkeep=H['upkeep'], down_min=down_min(p), fee=fee, tax=tax(k), need=down_min(p) + fee,
                       cash_all=p + fee, score=need_score(k), let_rent=rent_of(k), care=up.home_month(k, p))
        homes.append(row)
    return dict(groups=[dict(id=g, emoji=e, name=n, color=c) for g, e, n, c in GROUPS], homes=homes)


def _market(ready: int, back: int = 0) -> list[dict]:
    """Per home: what is still missing for the deposit (rent), the down payment and fee, or the whole price.
    `back`: the deposit of the room rented now, which comes back when moving to the other one."""
    out = []
    for k, H in HOMES.items():
        if H['kind'] == 'rent':
            out.append(dict(id=k, missing=max(0, H['deposit'] - ready - back)))
        else:
            p, fee = H['price'], buy_fee(H['price']) + tax(k)
            out.append(dict(id=k, missing=max(0, down_min(p) + fee - ready), missing_all=max(0, p + fee - ready)))
    return out


def _place_view(s: dict, h: dict | None) -> dict:
    j = s['journey']
    place, kind = where(h)
    if active_lease(j):
        place, kind = 'lease', j['rental']['kind']
    cost = living(j, _jr().LIVING.get(j['chapter'], _jr().LIVING[_jr().LAST]))
    eid = _es().living_in(j)
    if eid:   # 🏰 living in a villa bought in Mua sắm (game/estates.py): where you are, where "Vào nhà" goes
        E = _es().ESTATE[eid]
        return dict(emoji=E['emoji'], name=E['name'], where=E['where'], desc='', where_id='estate', kind=eid, group='villa',
                    comfort=0, perk=None, cost=_es().living(j, cost))
    if place == 'attic':
        return dict(ATTIC, where_id='attic', kind=None, group=None, comfort=0, perk=None, cost=cost)
    H = HOMES[kind]
    out = dict(emoji=H['emoji'], name=H['name'], where=H['where'], desc=H['desc'], where_id=place, kind=kind, group=H['group'],
               comfort=H['comfort'], perk=H.get('perk'), cost=cost)
    if place == 'shared':
        out['with'] = h['shared']['name']
    if place == 'rent' and kind == DORM:
        out['dorm'] = dorm_view(s)
    return out


def dorm_view(s: dict) -> dict:
    """The bunk room on the home card: the roommates on their beds and one roommate's line of the day
    (from the journey seed and the life day: the same all day, another one tomorrow). Computed, never stored."""
    from .life_content import DORM_LINES, ROOMMATES
    j = s['journey']
    rng = random.Random(f'dorm-line|{j.get("seed", 0)}|{int(j["life_day"])}')
    who = rng.choice(sorted(ROOMMATES))
    mates = [dict(id=k, name=m['name'], emoji=m['emoji'], role=m['role'], bed=m['bed'], gender=m['gender'], look=dict(m['look']))
             for k, m in ROOMMATES.items()]
    return dict(mates=mates, you=YOUR_BED, line=dict(who=who, name=ROOMMATES[who]['name'], text=rng.choice(DORM_LINES[who])))


def _home_view(s: dict, h: dict, x: dict, day: int, ready: int) -> dict:
    """One home you own as the page shows it (`own` keeps 0.9's fields; the others add their tenant and what can be done)."""
    H = HOMES[x['kind']]
    value = value_of(x, day, s['journey'].get('property_market_basis', {}).get(x['id'], 10000))
    fee = sell_fee(value)
    ln = x['loan']
    loan = None
    off_sale = _payoff(ln, day, fee=False) if ln else None
    if ln:
        nxt = next((r for r in ln['rows'] if r['paid'] < r['amount']), None)
        loan = dict(ln, rate_text=bk.year_text(ln['rate']), left=sum(r['amount'] - r['paid'] for r in ln['rows']),
                    principal_left=sum(r['principal'] for r in ln['rows'] if r['paid'] < r['amount']), next=nxt,
                    overdue=sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']),
                    late=_late(ln), payoff=_payoff(ln, day), paid_rows=sum(1 for r in ln['rows'] if r['paid'] >= r['amount']))
    get_ = value - fee - (off_sale['total'] if off_sale else 0)
    out = {k: v for k, v in x.items() if k != 'keep'}
    out.update(emoji=H['emoji'], group=H['group'], perk=H.get('perk'), list_price=H['price'], name=H['name'], where=H['where'],
               desc=H['desc'], upkeep=H['upkeep'], comfort=H['comfort'], value=value, loan=loan, live=x is h['own'],
               let_rent=rent_of(x['kind']), care=up.home_month(x['kind'], x['price']),
               sell=dict(value=value, fee=fee, payoff=off_sale['total'] if off_sale else 0, get=get_, ok=get_ >= 0,
                         why='' if get_ >= 0 else 'Tiền bán chưa đủ trả hết nợ vay'))
    ad = s['journey'].get('rental_ads', {}).get(x['id'])
    out['rental_ad'] = dict(ad, demand_pct=demand(ad['rent'], rent_of(x['kind'])), market_rent=rent_of(x['kind']), listed_day=ad['since']) if ad and ad.get('active') else None
    out['market_news'] = pm.quote(x['kind'])['news']
    L = x['let']
    if L:
        emoji, who = tenant(L)
        nd = next_rent_day(x, day)
        out['let'] = dict(L, emoji=emoji, name=who, next=nd, next_amount=_rent_due(L, nd))
    if x is not h['own']:
        back = h['rent']['deposit'] if h['rent'] else 0
        out['move'] = dict(ok=not L and ready + back >= MOVE_FEE, fee=MOVE_FEE,
                           why='Đang cho thuê: lấy lại nhà trước' if L else '' if ready + back >= MOVE_FEE
                           else f'Thiếu {_fmt(MOVE_FEE - ready - back)} xu thuê xe')
    return out


def public(s: dict) -> dict:
    j = s['journey']
    h = get(s)
    b = bk.get(s)
    day = j['life_day']
    have = _have(s)
    ready = have['wallet'] + have['balance']
    attic = attic_rent(j)
    market = _market(ready, h['rent']['deposit'] if h and h['rent'] else 0)
    o = offer(s)
    o['rate_text'] = bk.year_text(o['rate'])
    own = _home_view(s, h, h['own'], day, ready) if h and h['own'] else None
    props = [_home_view(s, h, x, day, ready) for x in h['props']] if h else []
    count = len(homes(h))
    rent = None
    if h and h['rent']:
        H = HOMES[h['rent']['kind']]
        rent = dict(h['rent'], emoji=H['emoji'], name=H['name'], where=H['where'], rent_day=H['rent'], comfort=H['comfort'])
    shared = None
    if h and h['shared']:
        H = HOMES[h['shared']['kind']]
        shared = dict(h['shared'], emoji=H['emoji'], home=H['name'], where=H['where'], upkeep=H['upkeep'], comfort=H['comfort'])
    sp = _spouse(s)
    full = count >= OWNED_MAX
    bills = up.public(s) if j.get('story') and count else None
    out = dict(story=bool(j.get('story')), life_day=day, have=dict(have, ready=ready, bank=b is not None, debt=max(0, -j['wallet']),
                savings=bk._savings_total(b) if b else 0), place=_place_view(s, h), attic_rent=attic, market=market, offer=o,
                own=own, rent=rent, shared=shared, married=bool(sp), spouse=(sp or {}).get('name'),
                log=list(reversed(h['log'])) if h else [], stats=dict(h['stats']) if h else {k: 0 for k in STATS}, rules=rules(),
                tenancy=dict(active_lease(j)) if active_lease(j) else None,
                market_news=[dict(kind=k, **pm.quote(k)) for k in OWN if pm.quote(k)['news']],
                props=props, count=count, owned=[x['kind'] for x in homes(h)],
                can_buy=dict(ok=not full, why=f'Đã có {OWNED_MAX} căn nhà: bán bớt một căn rồi hãy mua thêm' if full else ''))
    if bills and (bills['home'] or bills['due']['home']):   # 🧾 this tháng's phí bảo trì (absent: none; an older server)
        out['care'] = dict(month=bills['home'], next=bills['next'], due=bills['due']['home'])
    return out


# ---------------------------------------------------------------- validation
def _valid_home(s: dict, x, v: int, live: bool) -> None:
    """One home you own (version 1: the 0.9 fields only; version 2 adds mv, let, keep)."""
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s['journey']
    bad = 'Dữ liệu nhà ở không hợp lệ.'
    need(isinstance(x, dict) and set(x) == set(OWN_V1 if v == 1 else OWN_KEYS) and x['kind'] in OWN
         and x['price'] in prices(x['kind']) and x['fee'] == buy_fee(x['price']), bad)
    txt(x['id'], 16)
    integer(x['day'], 1, 10**6)
    integer(x['down'], down_min(x['price']), x['price'])
    integer(x['joint'], 0, x['down'] + x['fee'])
    ln = x['loan']
    if ln is not None:
        need(bk.get(s) is not None, bad)
        need(isinstance(ln, dict) and set(ln) == {'principal', 'rate', 'months', 'start', 'rows'} and ln['months'] in LOAN_MONTHS
             and ln['rate'] in [rate for _, rate in RATES] and ln['principal'] == x['price'] - x['down'] and ln['start'] == x['day'], bad)
        rows = ln['rows']
        need(isinstance(rows, list) and len(rows) == ln['months'], bad)
        for i, row in enumerate(rows):
            need(isinstance(row, dict) and set(row) == {'k', 'due', 'principal', 'interest', 'amount', 'paid', 'fee', 'late'}
                 and row['k'] == i + 1 and row['due'] == ln['start'] + MONTH_DAYS * (i + 1) and type(row['late']) is bool, bad)
            for k in ('principal', 'interest', 'amount', 'paid', 'fee'):
                integer(row[k], 0, bk.AMOUNT_MAX * 2)
            need(row['amount'] == row['principal'] + row['interest'] + row['fee'] and row['paid'] <= row['amount'], bad)
        need(sum(row['principal'] for row in rows) == ln['principal'], bad)
    if v == 1:
        return
    integer(x['mv'], 0, 10**6)
    L = x['let']
    need(L is None or not live, bad)                 # the home you live in is never let
    if L is not None:
        need(isinstance(L, dict) and set(L) == set(LET_KEYS), bad)
        integer(L['who'], 0, 99)
        integer(L['rent'], 1, bk.AMOUNT_MAX)
        for k in ('since', 'paid', 'ev'):
            integer(L[k], 1, 10**6)
        need(x['day'] <= L['since'] <= L['paid'] <= j['life_day'] and L['ev'] <= j['life_day'], bad)
        integer(L['owed'], 0, L['rent'] * 2)
        integer(L['od'], 0, 10**6)
    K = x['keep']
    need(K is None or not live, bad)                 # reno.py's block holds the parts of the home you live in
    if K is not None:
        parts = _rn().PART_IDS
        need(isinstance(K, dict) and set(K) == {'day', 'parts'} and isinstance(K['parts'], dict) and set(K['parts']) == set(parts), bad)
        integer(K['day'], 1, 10**6)
        need(K['day'] <= j['life_day'], bad)
        for p in K['parts'].values():
            need(isinstance(p, dict) and set(p) == {'c', 'lv'}, bad)
            integer(p['c'], 0, 100)
            integer(p['lv'], 0, _rn().LV_MAX)


def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or j.get('home') is None:
        return
    h = j['home']
    bad = 'Dữ liệu nhà ở không hợp lệ.'
    need(isinstance(h, dict) and h.get('v') in (1, VERSION), bad, 'invalid_save')
    v = h['v']
    keys = set(initial()) - {'props'} if v == 1 else set(initial())     # version 1: a save not upgraded yet (still accepted)
    need(set(h) == keys, bad, 'invalid_save')
    integer(h['seq'], 0, 10**6)
    integer(h['day'], 1, 10**6)
    need(h['day'] <= j['life_day'], bad)
    need(isinstance(h['stats'], dict) and set(h['stats']) == set(STATS_V1 if v == 1 else STATS), bad)
    for n in h['stats'].values():
        integer(n, 0, 10**9)
    r = h['rent']
    if r is not None:
        need(isinstance(r, dict) and set(r) == {'kind', 'since', 'deposit'} and r['kind'] in RENT and r['deposit'] == HOMES[r['kind']]['deposit'], bad)
        integer(r['since'], 1, 10**6)
    x = h['own']
    need(not (x and r), bad)
    if x is not None:
        _valid_home(s, x, v, True)
    owned = [x] if x is not None else []
    if v != 1:
        need(isinstance(h['props'], list) and len(h['props']) + len(owned) <= OWNED_MAX, bad)
        for o in h['props']:
            _valid_home(s, o, v, False)
        owned += h['props']
        need(len({o['id'] for o in owned}) == len(owned) and len({o['kind'] for o in owned}) == len(owned), bad)
    sh = h['shared']
    if sh is not None:
        need(isinstance(sh, dict) and set(sh) == {'couple', 'id', 'kind', 'name', 'since'} and sh['kind'] in OWN, bad)
        integer(sh['couple'], 1, 10**12)
        txt(sh['id'], 16)
        txt(sh['name'], 24)
        integer(sh['since'], 1, 10**6)
    need(isinstance(h['past'], list) and len(h['past']) <= PAST_MAX, bad)
    for p in h['past']:
        need(isinstance(p, dict) and set(p) == {'id', 'kind', 'bought', 'sold', 'price', 'got'} and p['kind'] in OWN, bad)
        txt(p['id'], 16)
        for k in ('bought', 'sold'):
            integer(p[k], 1, 10**6)
        integer(p['price'], 1, bk.AMOUNT_MAX)
        integer(p['got'], 0, bk.AMOUNT_MAX * 2)
    need(isinstance(h['log'], list) and len(h['log']) <= LOG_MAX, bad)
    for row in h['log']:
        need(isinstance(row, dict) and set(row) == {'day', 'text', 'amt'}, bad)
        integer(row['day'], 1, 10**6)
        txt(row['text'], 140)
        integer(row['amt'], -bk.AMOUNT_MAX * 2, bk.AMOUNT_MAX * 2)
