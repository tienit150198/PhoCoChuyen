"""🏅 Hạng thú cưng, 🧬 ghép ba, 📊 chỉ số, 🧰 linh kiện (owner 19/10: "pet thường tăng 2% lợi nhuận, pet xịn 30% 50%",
"chia theo D B C … tới SSS", "ghép 3 con đi thì hay hơn", "tỷ lệ ra SSS thấp thôi", "chỉ số để cạnh tranh", "linh kiện").
The pet games and tournaments come later (owner: "trò chơi của pets chưa làm").

* Every pet has a rank (RANKS, D…SSS) rolled when it arrives (ODDS_SHELTER / ODDS_SHOP, per 10 000 000: D or C
  only since owner 19/10 "đồ ở shop là chỉ có bậc D và C thôi, pets cũng thế, cao hơn là phải nâng") or given by
  a fusion. Pets older than this module: adopted D, bought C (_record).
* 💰 Only the pet walking with you, not sad, adds PROFIT % of what you earn at work (tile_match.fund_bonus: the day's
  salary, finished jobs, TT99, commissions abroad; never the staff orders nor the quầy chain), at most CAP xu a
  Vietnam day; an SSS with a deep bond (SSS_BOND) more. Its own 'other_income' row (PREFIX), kept out of the 🔥 x3 net.
* 🧬 jr_pet_fuse: any three pets, dogs and cats alike (owner 19/10 "các pet khác nhau cùng cấp vẫn ghép được",
  "mua về được ghép luôn": no waiting days). The odds are never shown (owner "đừng show tỷ lệ ra"). Success
  (FUSE_BP of the lowest rank, +MIX_BP for each rank step another one has above it). Since 19/10 (owner: "chọn 1
  giống chính để nó giữ lại giống đó, còn lại 2 giống kia là nguyên liệu … thất bại thì sẽ biến mất giống thêm vào,
  chỉ áp dụng cho cấp A trở lên") one of the three is the main pet (`main`, else the first): a success raises it one
  rank in place (its breed, coat, name, training and gear stay; its potential takes the better of its own and the
  trio's) and the two others retire to the grandparents' for good (never die, never sold: `ret`). A failure keeps
  all three below LOSE_FROM (S, owner 19/10 "bậc S trở lên mới mất, bậc A chưa mất"); from S up the two others are
  gone (not even at the grandparents'). The fee
  (FUSE_FEE) is spent either way. Three SSS: LEGEND_BP for the main to become 🌟 legendary. Owner 19/10 "con pets nào
  cũng có thể lên cấp sss và huyền thoại hết, khi lên thì được chọn giữ bé hiện tại hoặc đổi giống": `breed` picks what
  the main pet is after a success: its own breed (the default), the breed of one of the two others (with that one's
  coat), or on a legendary fusion its kind's legendary breed; a legendary that keeps its breed is listed in the
  wardrobe block (game/pet_wardrobe.py `lg`, so an older build sees a plain SSS). Three pets of
  a RECIPE with `mix`: HYBRID_BP for a 🧬 hybrid pup (at least its floor rank; the three retire), else the main goes
  up. No daily limit since 19/10 (owner: "ghép mỗi ngày k giới hạn nhé": `day.f` only counts). An SSS gets one
  of the FX coats.
* 📊 Five stats: the rank's RANGE × the pet's potential (pt, 0–100, rolled at birth, a pup inherits its parents'
  mean), the breed's lean (pets_content `st`), training (tn, jr_pet_train) and the gear worn. Power = their sum
  (the 'LC' board, game/pets.py command_commit).
* 🧰 Gear (GSLOTS, ranks like the pets): bought D or C (GSHOP), found on a stroll (D or C) (jr_pet_stroll, May mắn), enhanced
  +1…+10 (GUP_BP; a failure loses nothing but the fee). A rank up (jr_pet_gear_fuse, owner 19/10 "bắt buộc cộng 10 rồi
  mới cho lên bậc, cũng 3 món, bậc S trở đi thì mất đồ nguyên liệu"): the first gear, at +10, plus two more of its slot
  and rank; on success it goes up IN PLACE (worn or not) and back to +0, the two others are used up; a failure from S
  (LOSE_FROM) loses the two others, below S only the fee. Stats only, never money.
* ⚡ Cường hóa nhanh (owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa chứ sao lại cường hóa từng lần", "nó giống
  ghép tự động của áo quần ấy"): one command runs the single one again and again, one charge, one save, a summary {n, ok,
  spent, used, made, stop, left}, within a budget, the money and AUTO_MAX:
  - jr_pet_fuse_auto {budget, top?, scope?, confirm}: jr_pet_fuse's own fusion (_fuse_check / _fuse_roll: the same fee,
    odds, 📺 boost, retiring and losses) of three pets of the lowest rank first (`fuse_sets`, the quick pick's rule: the
    👑 main one the pet walked or the strongest, keeping its breed, never a hybrid; the two others never the pet walked,
    those in the kennel or at the grandparents' before those at home, the weakest first; no 🌟 legendary and no sad pet
    ever used; the result at most `top`, 7 = 🌟), a miss tried again while the pets remain. It stops at a ✨ thần thú
    offer, so the player answers it (jr_pet_morph) before another fusion could replace it.
  - jr_pet_gear_auto {budget, top?, scope?, confirm}: jr_pet_gear_up / jr_pet_gear_fuse's own steps (_gear_up_roll,
    _gear_fuse_roll) by `gear_step`: three of one slot and rank (the lowest rank first, the result at most `top`), the
    main one (worn first, then the highest level) strengthened to +GLV_MAX then ranked up with the two free ones of the
    lowest levels; with no such three, the gear worn by the pets strengthened to +GLV_MAX (highest rank first).
* Pets are bound to the account: nothing here gives, sells or moves a pet to anyone.

State `journey['petx']` (absent until the first pet; older builds keep unknown journey keys, and they never see the
kennel, so a rollback loses nothing): see initial().
    t     {pet id: {r rank, fx coat effect, pt [5], tn [5], g {gear slot: gear id | None}, z fusion time}}
    ken   [pet] in the 🏠 trại nuôi (≤ KENNEL_MAX, records shaped like game/pets.py's)
    ret   [{b, c, n, r, fx}] the last RET_KEEP that retired after a fusion; rn how many in all
    gear  [{id, s slot, m model, r rank, lv level}] (≤ GEAR_MAX); gs the next gear number
    day   {d Vietnam day, f fusions, tr trainings, w strolls, got bonus xu}
"""
from __future__ import annotations

import secrets

from . import pets_content as C

KEY = 'petx'
VERSION = 1
RANKS = ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS')
TOP = len(RANKS) - 1
RANK_NAME = dict(zip(RANKS, ('Thường', 'Khá', 'Tốt', 'Hiếm', 'Quý', 'Siêu quý', 'Thần thoại')))
PROFIT = (2, 3, 5, 8, 12, 20, 30)                                          # % of work earnings
CAP = (20_000, 40_000, 80_000, 150_000, 300_000, 600_000, 1_000_000)      # xu a Vietnam day
SSS_BOND = ((200, 50, 1_500_000), (100, 40, 1_250_000))                   # bond ≥ x: (%, cap)
ODDS = 10_000_000
ODDS_SHELTER = (8_000_000, 2_000_000, 0, 0, 0, 0, 0)   # D or C: higher ranks come from fusions only
ODDS_SHOP = (6_000_000, 4_000_000, 0, 0, 0, 0, 0)
FUSE_BP = (6000, 4500, 3000, 1500, 600, 300)                              # rank r ×3 → r+1, per 10 000
FUSE_FEE = (500, 2_000, 10_000, 50_000, 300_000, 5_000_000, 10_000_000)   # by the lowest rank; [6] = 3 SSS
LEGEND_BP = 500
MIX_BP = 300
HYBRID_BP = 1000
MUTANT_BP = 500
LOSE_FROM = 4                                                              # S: a failure from here loses the two others
KENNEL_MAX = 30
RET_KEEP = 40
FX = (('cau_vong', '🌈', 'Cầu Vồng'), ('ngan_ha', '🌌', 'Ngân Hà'), ('hong_ngoc', '🔥', 'Hồng Ngọc'), ('bang_tinh', '❄️', 'Băng Tinh'))
FX_IDS = tuple(f[0] for f in FX) + ('dot_bien',)
PREFIX = '🐾 Thú cưng hạng'

STATS = (('spd', '⚡', 'Tốc độ'), ('sta', '💪', 'Sức bền'), ('int', '🧠', 'Thông minh'), ('cute', '💖', 'Đáng yêu'), ('luck', '🍀', 'May mắn'))
STAT_IDS = tuple(x[0] for x in STATS)
RANGE = ((10, 30), (20, 40), (30, 55), (45, 70), (60, 85), (75, 95), (90, 110))
LEGEND_RANGE = (110, 130)
TRAIN_MAX = 30
TRAIN_STEP = 2
TRAIN_FEE = (50, 100, 200, 400, 800, 1500, 3000)
TRAIN_DAY = 10

# 🧬 Giống lai: the three breeds (sorted) -> (the hybrid, its lowest rank). ('cho_ta',)*3 also needs three coats.
RECIPES = {
    ('bac_ha', 'cho_ta', 'phu_quoc'): ('hmong', 2),
    ('cho_ta', 'cho_ta', 'cho_ta'): ('lai_van_ho', 2),
    ('beagle', 'golden', 'poodle'): ('goldendoodle', 2),
    ('husky', 'pom', 'samoyed'): ('pomsky', 2),
    ('akita', 'corgi', 'shiba'): ('corgi_inu', 2),
    ('alaska', 'husky', 'samoyed'): ('soi_tuyet', 3),
    ('alaska', 'becgie', 'husky'): ('soi_xam', 3),
    ('bulldog', 'dalmatian', 'pug'): ('dom_mat_xe', 2),
    ('ald', 'ba_tu', 'xiem'): ('himalaya', 2),
    ('ald', 'ba_tu', 'ragdoll'): ('ragamuffin', 2),
    ('bengal', 'maine_coon', 'meo_muop'): ('toyger', 2),
    ('aln', 'munchkin', 'scottish'): ('scottish_kilt', 2),
    ('abyssinian', 'nga_xanh', 'xiem'): ('ngoc_bich', 3),
    ('tam_the', 'tam_the', 'tam_the'): ('tam_the_duc', 4),
}
LEGEND = dict(dog='linh_khuyen', cat='than_tai')

# 🧰 Linh kiện: (slot, emoji, name, the stat it adds) and three models a slot.
GSLOTS = (('giay', '👟', 'Giày', 'spd'), ('giap', '🎽', 'Áo giáp', 'sta'), ('dau', '🎧', 'Đồ đội đầu', 'int'),
          ('pk', '🎀', 'Phụ kiện', 'cute'), ('bua', '💎', 'Bùa', 'luck'))
GSLOT_IDS = tuple(g[0] for g in GSLOTS)
GMODELS = dict(
    giay=(('👟', 'Giày chạy bộ'), ('🥾', 'Bốt lò xo'), ('🪽', 'Giày gió')),
    giap=(('🦺', 'Áo lưới'), ('🎽', 'Giáp nhẹ'), ('🛡️', 'Giáp vảy rồng')),
    dau=(('🕶️', 'Kính thông minh'), ('🎧', 'Tai nghe học bài'), ('🪖', 'Mũ phi công')),
    pk=(('🎀', 'Nơ pha lê'), ('👑', 'Vương miện nhỏ'), ('🌸', 'Vòng hoa')),
    bua=(('🍀', 'Bùa cỏ bốn lá'), ('🔮', 'Ngọc may mắn'), ('🧧', 'Túi lộc')),
)
# 💎 owner 19/10 "thêm nhiều linh kiện", "đắt vào nhé, giá đồ xịn xịn tí": five premium models a slot (models 3…7),
# GX_MULT times the price, GX_BONUS more to the stat at every level. The save keeps model 0 in `gear` (an older build
# reads a plain one) and the premium model in the wardrobe block (game/pet_wardrobe.py `gm`, {gear id: 0…4}).
GMODELS_X = dict(
    giay=(('🩰', 'Giày ba lê bạc'), ('⛸️', 'Giày trượt tia chớp'), ('👠', 'Giày pha lê'), ('🔥', 'Giày lửa'), ('☁️', 'Giày mây bay')),
    giap=(('🥋', 'Võ phục đai đen'), ('🧥', 'Áo choàng bạc'), ('🛡️', 'Giáp hiệp sĩ'), ('💠', 'Giáp pha lê'), ('🐲', 'Giáp rồng vàng')),
    dau=(('🎓', 'Mũ cử nhân'), ('🤿', 'Kính lặn thông minh'), ('⛑️', 'Mũ cứu hộ'), ('🪖', 'Mũ tướng quân'), ('🧠', 'Vòng trí tuệ')),
    pk=(('💍', 'Nhẫn kim cương'), ('🦋', 'Kẹp bướm ngọc'), ('🌺', 'Hoa tai dâm bụt'), ('🌠', 'Sao băng cài áo'), ('💖', 'Tim pha lê')),
    bua=(('🪙', 'Đồng xu cổ'), ('🐚', 'Vỏ ốc thần'), ('🌙', 'Bùa trăng khuyết'), ('🧿', 'Mắt xanh hộ mệnh'), ('🐉', 'Ngọc rồng')),
)
GX_MULT = (5, 10, 20, 40, 80)
GX_BONUS = (3, 5, 8, 12, 16)
GBASE = (4, 7, 11, 16, 22, 30, 40)            # the stat a gear adds at +0; each level +10 % of it
GSHOP = (300, 1500)                           # D, C in the shop
GUP_BP = (10000, 9000, 8000, 7000, 6000, 5000, 4000, 3500, 3000, 2500)   # +lv → +lv+1
GUP_FEE = (100, 300, 1000, 3000, 10_000, 30_000, 100_000)                # × (lv + 1)
GFUSE_FEE = (50, 200, 1000, 5000, 30_000, 500_000)
GLV_MAX = 10
GEAR_MAX = 60
GEAR_QTY_MAX = 20                             # 🛍️ owner 21/10 "cho chọn số lượng mua": a purchase of one model × rank (and the bag's room)
STROLL_DAY = 3
GEAR_ODDS = (7000, 3000, 0, 0, 0, 0, 0)        # per 10 000, a find on a stroll: D or C
COMMANDS = ('jr_pet_fuse', 'jr_pet_train', 'jr_pet_kennel', 'jr_pet_stroll', 'jr_pet_gear_buy', 'jr_pet_gear_up',
            'jr_pet_gear_fuse', 'jr_pet_gear_wear', 'jr_pet_gear_drop', 'jr_pet_fuse_auto', 'jr_pet_gear_auto')
AUTO_MAX = 50                                  # ⚡ the pet fusions one Cường hóa nhanh makes at most
GEAR_AUTO_MAX = 100                            # ⚡ the gear steps (+1 or a rank up) one makes at most
REC_KEYS = frozenset({'r', 'fx', 'pt', 'tn', 'g', 'z'})
BLOCK_KEYS = frozenset({'v', 't', 'ken', 'ret', 'rn', 'gear', 'gs', 'day'})
DAY_KEYS = ('d', 'f', 'tr', 'w', 'got')


# ---------------------------------------------------------------- helpers
def _pt():
    from . import pets
    return pets


def _need(ok, msg, code='invalid_action'):
    from .engine import need
    need(ok, msg, code)


def _int(v, lo=0, hi=10**12) -> bool:
    return type(v) is int and lo <= v <= hi


def vn_day() -> int:
    from . import wealth_fee
    return wealth_fee.today(_pt().now())


def roll(n: int) -> int:
    return secrets.randbelow(n)


def _pick(table, total) -> int:
    x, acc = roll(total), 0
    for i, w in enumerate(table):
        acc += w
        if x < acc:
            return i
    return 0


def initial() -> dict:
    return dict(v=VERSION, t={}, ken=[], ret=[], rn=0, gear=[], gs=1, day=dict(d=0, f=0, tr=0, w=0, got=0))


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def _today(x: dict) -> dict:
    d = vn_day()
    if x['day']['d'] != d:
        x['day'] = dict(d=d, f=0, tr=0, w=0, got=0)
    return x['day']


def all_pets(s: dict) -> list:
    """Every pet you keep: at home, at the grandparents', in the kennel."""
    b = _pt().get(s)
    x = get(s)
    return (b['list'] + b['farm'] if b else []) + (x['ken'] if x else [])


def _potential(s: dict, pid: str) -> list:
    """The potential of a pet older than this module: steady (a hash of the save's seed), so a view never re-rolls."""
    import hashlib
    h = hashlib.sha256(f"petx|{s['journey'].get('seed', 0)}|{pid}".encode()).digest()
    return [h[i] * 100 // 255 for i in range(len(STATS))]


def _record(s: dict, p: dict) -> dict:
    """The rank record of pet `p` (made for a pet older than this module: adopted D, bought C)."""
    x = _ensure(s)
    rec = x['t'].get(p['id'])
    if not isinstance(rec, dict):
        rec = x['t'][p['id']] = dict(r=0 if p['s'] == 'shelter' else 1, fx='', pt=_potential(s, p['id']),
                                     tn=[0] * len(STATS), g={k: None for k in GSLOT_IDS}, z=0)
    return rec


def rec_of(s: dict, p: dict) -> dict:
    """Read only: the record, or what _record would make."""
    x = get(s)
    rec = x['t'].get(p['id']) if x else None
    return rec if isinstance(rec, dict) else dict(r=0 if p['s'] == 'shelter' else 1, fx='', pt=_potential(s, p['id']),
                                                  tn=[0] * len(STATS), g={k: None for k in GSLOT_IDS}, z=0)


def on_new(s: dict, p: dict, src: str) -> dict:
    """A pet just adopted or bought: its rank rolled (ODDS_SHELTER / ODDS_SHOP), its potential, an SSS coat."""
    x = _ensure(s)
    r = _pick(ODDS_SHELTER if src == 'shelter' else ODDS_SHOP, ODDS)
    rec = x['t'][p['id']] = dict(r=r, fx=FX[roll(len(FX))][0] if r == TOP else '', pt=[roll(101) for _ in STATS],
                                 tn=[0] * len(STATS), g={k: None for k in GSLOT_IDS}, z=0)
    return rec


def is_legend(p: dict, s=None) -> bool:
    """A 🌟 legendary: its breed, or (since 19/10) a pet that kept its own breed (game/pet_wardrobe.py `lg`)."""
    br = C.BREEDS.get(p['b'])
    if br and br.get('fuse') == 'legend':
        return True
    if not isinstance(s, dict):
        return False
    from . import pet_wardrobe
    x = pet_wardrobe.stored(s)
    return bool(x) and p['id'] in x['lg']


def _gm(s) -> dict:
    """{gear id: premium model 0…4} (game/pet_wardrobe.py), {} without a save."""
    if not isinstance(s, dict):
        return {}
    from . import pet_wardrobe
    x = pet_wardrobe.stored(s)
    return x['gm'] if x else {}


def model_of(g: dict, s=None) -> int:
    """The gear's model, 0…7 (3…7 the premium ones)."""
    x = _gm(s).get(g['id'])
    return 3 + x if type(x) is int and 0 <= x < len(GX_MULT) else g['m']


def model_def(slot: str, m: int) -> tuple:
    return GMODELS[slot][m] if m < 3 else GMODELS_X[slot][m - 3]


def gear_value(g: dict, s=None) -> int:
    base = GBASE[g['r']]
    m = model_of(g, s)
    return base + base * g['lv'] // 10 + (GX_BONUS[m - 3] if m >= 3 else 0)


def stats(s: dict, p: dict, rec: dict | None = None) -> list:
    rec = rec or rec_of(s, p)
    lo, hi = LEGEND_RANGE if is_legend(p, s) else RANGE[rec['r']]
    lean = (C.BREEDS.get(p['b']) or {}).get('st') or (0,) * len(STATS)
    x = get(s)
    bag = {g['id']: g for g in (x['gear'] if x else [])}
    out = []
    for i, sid in enumerate(STAT_IDS):
        v = lo + (hi - lo) * rec['pt'][i] // 100 + lean[i] + rec['tn'][i]
        for slot, gid in rec['g'].items():
            g = bag.get(gid)
            if g and dict((a[0], a[3]) for a in GSLOTS)[slot] == sid:
                v += gear_value(g, s)
        out.append(max(1, v))
    return out


def power(s: dict, p: dict) -> int:
    return sum(stats(s, p))


def bonus_rate(s: dict, p: dict) -> tuple:
    """(percent, daily cap) the pet `p` gives when it walks with you."""
    rec = rec_of(s, p)
    if rec['r'] == TOP:
        for at, pct, cap in SSS_BOND:
            if p['x'] >= at:
                return pct, cap
    return PROFIT[rec['r']], CAP[rec['r']]


# ---------------------------------------------------------------- 💰 the bonus where money is earned
def walker(s: dict):
    """The pet walking with you, when it can bring luck: not sad (a hungry or dirty pet stays home in spirit)."""
    j = s.get('journey')
    pt = _pt()
    b = pt.get(s)
    if not isinstance(j, dict) or not j.get('story') or not b or not b['walk']:
        return None
    p = next((q for q in b['list'] if q['id'] == b['walk']), None)
    if not p or p['b'] not in C.BREEDS:
        return None
    n = pt.needs_at(p, j['life_day']) if p['t'] < j['life_day'] else {k: p[k] for k in pt.NEEDS}
    return p if pt.mood(n) != 'buon' else None


def fund_bonus(s: dict, c: dict, base: int, what: str, ref: str | None) -> int:
    """The walking pet's share of an earning of a workplace fund (game/tile_match.fund_bonus): its own row."""
    if type(base) is not int or base <= 0:
        return 0
    p = walker(s)
    if not p:
        return 0
    pct, cap = bonus_rate(s, p)
    from . import pet_wardrobe
    bp = pct * 100 + pet_wardrobe.bonus_bp(s, p)   # 👗 what it wears adds (the day's cap stays its rank's)
    x = _ensure(s)
    day = _today(x)
    bonus = min(base * bp // 10000, max(0, cap - day['got']))
    if bonus <= 0:
        return 0
    rank = RANKS[rec_of(s, p)['r']]
    from .engine import money
    money(s, c, bonus, f'{PREFIX} {rank} +{bp / 100:g}% · {p["n"]} · {what}'[:120], ref, category='other_income')
    day['got'] += bonus
    return bonus


# ---------------------------------------------------------------- save
def _pet_ok(p) -> bool:
    return _pt()._pet_ok(p)


def validate(s: dict) -> None:
    from .engine import need, integer
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    x = j[KEY]
    bad = 'Dữ liệu hạng thú cưng không hợp lệ.'
    ok = lambda v: need(v, bad, 'invalid_save')
    ok(isinstance(x, dict) and set(x) == BLOCK_KEYS and x['v'] == VERSION)
    ok(isinstance(x['t'], dict) and len(x['t']) <= 64 + KENNEL_MAX)
    for pid, r in x['t'].items():
        ok(isinstance(pid, str) and _pt().PID_RE.fullmatch(pid) is not None and isinstance(r, dict) and set(r) == REC_KEYS)
        ok(_int(r['r'], 0, TOP) and r['fx'] in ('',) + FX_IDS and _int(r['z'], 0, 10**11))
        ok(isinstance(r['pt'], list) and len(r['pt']) == len(STATS) and all(_int(v, 0, 100) for v in r['pt']))
        ok(isinstance(r['tn'], list) and len(r['tn']) == len(STATS) and all(_int(v, 0, TRAIN_MAX) for v in r['tn']))
        ok(isinstance(r['g'], dict) and set(r['g']) == set(GSLOT_IDS) and all(v is None or isinstance(v, str) for v in r['g'].values()))
    ok(isinstance(x['ken'], list) and len(x['ken']) <= KENNEL_MAX and all(_pet_ok(p) for p in x['ken']))
    ids = [p['id'] for p in all_pets(s)]
    ok(len(ids) == len(set(ids)))
    b = _pt().get(s)
    ok(all(int(p['id'][1:]) < (b['seq'] if b else 1) for p in x['ken']))
    ok(isinstance(x['ret'], list) and len(x['ret']) <= RET_KEEP and _int(x['rn'], 0, 10**7))
    for r in x['ret']:
        ok(isinstance(r, dict) and set(r) == {'b', 'c', 'n', 'r', 'fx'} and isinstance(r['b'], str) and _int(r['c'], 0, 15)
           and isinstance(r['n'], str) and len(r['n']) <= C.NAME_MAX and _int(r['r'], 0, TOP) and r['fx'] in ('',) + FX_IDS)
    ok(isinstance(x['gear'], list) and len(x['gear']) <= GEAR_MAX and _int(x['gs'], 1, 10**7))
    gids = set()
    for g in x['gear']:
        ok(isinstance(g, dict) and set(g) == {'id', 's', 'm', 'r', 'lv'} and isinstance(g['id'], str) and g['id'] not in gids
           and g['s'] in GSLOT_IDS and _int(g['m'], 0, len(GMODELS[g['s']]) - 1) and _int(g['r'], 0, TOP) and _int(g['lv'], 0, GLV_MAX))
        gids.add(g['id'])
    worn = [v for r in x['t'].values() for v in r['g'].values() if v]
    ok(len(worn) == len(set(worn)) and all(v in gids for v in worn))
    d = x['day']
    ok(isinstance(d, dict) and set(d) == set(DAY_KEYS) and all(_int(d[k]) for k in DAY_KEYS))
    integer(x['rn'], 0, 10**7)


def upgrade(j: dict) -> None:
    """Drop what no longer points anywhere (a record of a pet an older build let go, gear worn by a record gone)."""
    if not isinstance(j, dict) or not isinstance(j.get(KEY), dict):
        if isinstance(j, dict) and KEY in j:
            j.pop(KEY)
        return
    x = j[KEY]
    if set(x) != BLOCK_KEYS:
        base = initial()
        x = j[KEY] = {k: x.get(k, base[k]) for k in BLOCK_KEYS}
    b = j.get('pets') if isinstance(j.get('pets'), dict) else None
    live = {p['id'] for p in ((b['list'] + b['farm']) if b else []) if isinstance(p, dict)} | {p['id'] for p in x['ken'] if isinstance(p, dict)}
    if isinstance(x['t'], dict):
        for pid in [k for k in x['t'] if k not in live]:
            x['t'].pop(pid)
    gids = {g['id'] for g in x['gear'] if isinstance(g, dict)}
    for r in x['t'].values():
        if isinstance(r, dict) and isinstance(r.get('g'), dict):
            for k, v in r['g'].items():
                if v is not None and v not in gids:
                    r['g'][k] = None


# ---------------------------------------------------------------- finding pets
def _where(s: dict, pid):
    """(the list holding pet `pid`, the pet, 'home' | 'farm' | 'ken') or (None, None, '')."""
    b = _pt().get(s)
    x = get(s)
    for name, rows in (('home', b['list'] if b else []), ('farm', b['farm'] if b else []), ('ken', x['ken'] if x else [])):
        for p in rows:
            if p['id'] == pid:
                return rows, p, name
    return None, None, ''


def place_new(s: dict, p: dict) -> str:
    """Put a new pet at home, else in the kennel, else at the grandparents'. Returns where ('' when full)."""
    pt = _pt()
    b = pt._ensure(s)
    x = _ensure(s)
    if len(b['list']) < C.MAX_PETS:
        b['list'].append(p)
        if b['walk'] is None:
            b['walk'] = p['id']
        return 'home'
    if len(x['ken']) < KENNEL_MAX:
        x['ken'].append(p)
        return 'ken'
    if len(b['farm']) < C.MAX_FARM:
        b['farm'].append(p)
        return 'farm'
    return ''


def has_room(s: dict) -> bool:
    b = _pt().get(s)
    x = get(s)
    return (not b or len(b['list']) < C.MAX_PETS) or not x or len(x['ken']) < KENNEL_MAX


# ---------------------------------------------------------------- commands
def _confirm(p, text):
    _need(p.get('confirm') is True, text)


def _gear(x: dict, gid):
    g = next((g for g in x['gear'] if g['id'] == gid), None) if isinstance(gid, str) else None
    _need(g is not None, 'Không thấy món linh kiện này.', 'not_owned')
    return g


def _wearer(x: dict, gid: str):
    return next((pid for pid, r in x['t'].items() if gid in r['g'].values()), None)


def _new_gear(x: dict, slot: str, rank: int) -> dict:
    g = dict(id=f'g{x["gs"]}', s=slot, m=roll(len(GMODELS[slot])), r=rank, lv=0)
    x['gs'] += 1
    x['gear'].append(g)
    return g


def gear_name(g: dict, s=None) -> str:
    e, n = model_def(g['s'], model_of(g, s))
    return f'{e} {n} {RANKS[g["r"]]}' + (f' +{g["lv"]}' if g['lv'] else '')


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def action(s: dict, name: str, p: dict) -> dict:
    pt = _pt()
    _need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    _need(isinstance(p, dict), 'Thông tin không hợp lệ.')
    j = s['journey']
    day = j['life_day']
    if name == 'jr_pet_fuse':
        return _fuse(s, p)
    if name == 'jr_pet_fuse_auto':
        return _fuse_auto(s, p)
    if name == 'jr_pet_kennel':
        pt._keys(p, {'pet', 'to', 'swap', 'walk'}, {'pet', 'to'})
        _need(p['to'] in ('ken', 'home'), 'Thông tin không hợp lệ.')
        b = pt._ensure(s)
        x = _ensure(s)
        rows, pet, where = _where(s, p['pet'])
        _need(pet is not None, 'Không thấy bé này.', 'not_owned')
        if p['to'] == 'ken':
            _need(where == 'home', 'Chỉ đưa bé đang ở nhà vào trại nuôi nhé.')
            _need(len(x['ken']) < KENNEL_MAX, f'Trại nuôi đã đủ {KENNEL_MAX} bé.', 'limit')
            b['list'].remove(pet)
            pet['t'] = max(pet['t'], day)
            x['ken'].append(pet)
            if b['walk'] == pet['id']:
                b['walk'] = b['list'][0]['id'] if b['list'] else None
            return dict(message=f'🏠 {pet["n"]} vào trại nuôi, có cô chăm mỗi ngày.')
        _need(where == 'ken', 'Bé này không ở trại nuôi.')
        # owner 19/10 "có nhiều hơn mà hiển thị mỗi 3 con": home full, `swap` names the home pet that trades places
        out = None
        if p.get('swap') is not None:
            _need(isinstance(p['swap'], str), 'Thông tin không hợp lệ.')
            out = next((q for q in b['list'] if q['id'] == p['swap']), None)
            _need(out is not None, 'Bé đổi chỗ phải đang ở nhà.', 'not_owned')
        _need(out is not None or len(b['list']) < C.MAX_PETS, f'Nhà đã đủ {C.MAX_PETS} bé rồi.', 'limit')
        _need(p.get('walk') in (None, True, False), 'Thông tin không hợp lệ.')
        x['ken'].remove(pet)
        if out is not None:
            at = b['list'].index(out)
            b['list'][at] = pet
            out['t'] = max(out['t'], day)
            x['ken'].append(out)
            if b['walk'] == out['id']:
                b['walk'] = pet['id']
        else:
            b['list'].append(pet)
        pet['t'] = day
        for k in pt.NEEDS:
            pet[k] = max(pet[k], 80)
        if b['walk'] is None or p.get('walk') is True:
            b['walk'] = pet['id']
        walk = ' Dắt bé đi dạo luôn.' if b['walk'] == pet['id'] else ''
        if out is not None:
            return dict(message=f'🔁 {pet["n"]} về nhà, {out["n"]} vào trại nuôi.{walk}')
        return dict(message=f'🏡 {pet["n"]} về nhà rồi, mừng quýnh.{walk}')
    if name == 'jr_pet_train':
        pt._keys(p, {'pet', 'stat', 'confirm'}, {'pet', 'stat'})
        pet = pt._pet(s, p['pet'])
        _need(p['stat'] in STAT_IDS, 'Chọn chỉ số để luyện nhé.')
        x = _ensure(s)
        rec = _record(s, pet)
        i = STAT_IDS.index(p['stat'])
        _need(rec['tn'][i] < TRAIN_MAX, f'{pet["n"]} đã luyện {STATS[i][2].lower()} tới mức tối đa.', 'full')
        d = _today(x)
        _need(d['tr'] < TRAIN_DAY, f'Hôm nay đã luyện {TRAIN_DAY} buổi rồi. Mai luyện tiếp nhé.', 'limit')
        n = pt.needs_at(pet, day) if pet['t'] < day else {k: pet[k] for k in pt.NEEDS}
        _need(pt.mood(n) != 'buon', f'{pet["n"]} đang buồn, chăm bé trước rồi hẵng luyện.', 'sad')
        fee = TRAIN_FEE[rec['r']]
        how = pt._pay(s, fee, f'Luyện thú cưng · {pet["n"]}')
        rec['tn'][i] = min(TRAIN_MAX, rec['tn'][i] + TRAIN_STEP)
        d['tr'] += 1
        pet['f'] = max(0, pet['f'] - 5)
        return dict(message=f'{STATS[i][1]} {pet["n"]} luyện {STATS[i][2].lower()} xong, +{TRAIN_STEP}. ({how})')
    if name == 'jr_pet_stroll':
        pt._keys(p, set())
        x = _ensure(s)
        pet = walker(s)
        _need(pet is not None, 'Dắt một bé vui vẻ đi dạo đã nhé.', 'no_pet')
        d = _today(x)
        _need(d['w'] < STROLL_DAY, f'Hôm nay đã dạo {STROLL_DAY} vòng rồi.', 'limit')
        _need(len(x['gear']) < GEAR_MAX, f'Túi linh kiện đã đủ {GEAR_MAX} món. Bỏ bớt món cũ nhé.', 'limit')
        d['w'] += 1
        luck = stats(s, pet)[4]
        if roll(10000) >= 3000 + luck * 25:
            return dict(message=f'🦮 {pet["n"]} dạo một vòng, đánh hơi khắp nơi mà chưa thấy gì. Lần sau may hơn!', found=None)
        rank = _pick(GEAR_ODDS, 10000)
        if luck >= 80:
            rank = max(rank, _pick(GEAR_ODDS, 10000))
        g = _new_gear(x, GSLOT_IDS[roll(len(GSLOT_IDS))], rank)
        return dict(message=f'🎁 {pet["n"]} tha về {gear_name(g, s)}!', found=g['id'])
    if name == 'jr_pet_gear_auto':
        return _gear_auto(s, p)
    x = _ensure(s)
    if name == 'jr_pet_gear_buy':
        # 🛍️ owner 21/10 "mua linh kiện cho chọn số lượng": qty (absent: 1, an older client) pieces of one model and rank,
        # each exactly the piece one purchase makes, one charge of qty × the price; none bought if the bag lacks room.
        pt._keys(p, {'slot', 'model', 'rank', 'qty', 'confirm'}, {'slot', 'model', 'rank', 'confirm'})
        _need(p['slot'] in GSLOT_IDS and _int(p['model'], 0, 3 + len(GX_MULT) - 1) and _int(p['rank'], 0, len(GSHOP) - 1),
              'Chọn một món trong tiệm nhé.')
        qty = p.get('qty', 1)
        _need(_int(qty, 1, GEAR_QTY_MAX), f'Mua từ 1 đến {GEAR_QTY_MAX} món một lần nhé.')
        _need(len(x['gear']) < GEAR_MAX, f'Túi linh kiện đã đủ {GEAR_MAX} món.', 'limit')
        room = GEAR_MAX - len(x['gear'])
        _need(qty <= room, f'Túi linh kiện chỉ còn chỗ cho {room} món.', 'limit')
        e, nm = model_def(p['slot'], p['model'])
        price = gear_price(p['model'], p['rank'])
        total = price * qty
        times = f' ×{qty}' if qty > 1 else ''
        _confirm(p, f'Xác nhận mua {nm} hạng {RANKS[p["rank"]]}{times} ({_fmt(total)} xu).')
        how = pt._pay(s, total, f'Linh kiện thú cưng · {nm} {RANKS[p["rank"]]}{times}')
        made = []
        for _ in range(qty):
            g = dict(id=f'g{x["gs"]}', s=p['slot'], m=p['model'] if p['model'] < 3 else 0, r=p['rank'], lv=0)
            x['gs'] += 1
            x['gear'].append(g)
            made.append(g)
            if p['model'] >= 3:
                from . import pet_wardrobe
                pet_wardrobe.set_model(s, g['id'], p['model'] - 3)
        g = made[0]
        out = dict(message=f'🛍️ Đã mua {gear_name(g, s)}{times} ({how}).', gear=g['id'])
        if qty > 1:
            out['gears'] = [q['id'] for q in made]
        return out
    if name == 'jr_pet_gear_up':
        pt._keys(p, {'gear', 'confirm'}, {'gear', 'confirm'})
        g = _gear(x, p['gear'])
        _need(g['lv'] < GLV_MAX, f'{gear_name(g, s)} đã cường hóa tối đa.', 'full')
        fee = GUP_FEE[g['r']] * (g['lv'] + 1)
        _confirm(p, f'Xác nhận cường hóa {gear_name(g, s)} ({_fmt(fee)} xu).')
        how = pt._pay(s, fee, f'Cường hóa linh kiện · {gear_name(g, s)}')
        if _gear_up_roll(g):
            return dict(message=f'✨ Thành công! {gear_name(g, s)}. ({how})', ok=True)
        return dict(message=f'💨 Cường hóa trượt, món đồ vẫn nguyên {gear_name(g, s)}. ({how})', ok=False)
    if name == 'jr_pet_gear_fuse':
        pt._keys(p, {'gears', 'confirm'}, {'gears', 'confirm'})
        ids = p['gears']
        _need(isinstance(ids, list) and len(ids) == 3 and len(set(map(str, ids))) == 3, 'Chọn đúng ba món nhé.')
        gs = [_gear(x, i) for i in ids]
        _need(len({g['s'] for g in gs}) == 1 and len({g['r'] for g in gs}) == 1, 'Ba món phải cùng loại và cùng hạng.')
        main, others = gs[0], gs[1:]
        r = main['r']
        _need(r < TOP, 'Hạng SSS là cao nhất rồi.', 'full')
        # owner 19/10: "bắt buộc cộng 10 rồi mới cho lên bậc": the first one is the one that goes up, at +GLV_MAX
        _need(main['lv'] >= GLV_MAX, f'Cường hóa {gear_name(main, s)} lên +{GLV_MAX} trước rồi mới lên hạng nhé.', 'level')
        _need(not any(_wearer(x, g['id']) for g in others), 'Tháo hai món nguyên liệu khỏi các bé trước khi ghép nhé.', 'worn')
        fee = GFUSE_FEE[r]
        _confirm(p, f'Xác nhận ghép ba {GSLOTS[GSLOT_IDS.index(main["s"])][2].lower()} hạng {RANKS[r]} ({_fmt(fee)} xu).')
        how = pt._pay(s, fee, f'Ghép linh kiện {RANKS[r]}')
        if _gear_fuse_roll(s, x, main, others):
            return dict(message=f'🎉 Lên hạng thành công: {gear_name(main, s)} {RANKS[r + 1]}! Cường hóa lại tới +{GLV_MAX} '
                                f'để lên hạng tiếp. ({how})', ok=True, gear=main['id'])
        if r >= LOSE_FROM:   # owner 19/10: from S up a failure loses the two ingredients (the main one stays)
            return dict(message=f'💨 Ghép trượt: hai món nguyên liệu đã mất, {gear_name(main, s)} vẫn còn. ({how})',
                        ok=False, gear=main['id'], lost=[g['id'] for g in others])
        return dict(message=f'💨 Ghép trượt, ba món vẫn còn nguyên. ({how})', ok=False, gear=main['id'])
    if name == 'jr_pet_gear_wear':
        pt._keys(p, {'pet', 'slot', 'gear'}, {'pet', 'slot'})
        _need(p['slot'] in GSLOT_IDS, 'Thông tin không hợp lệ.')
        rows, pet, where = _where(s, p['pet'])
        _need(pet is not None, 'Không thấy bé này.', 'not_owned')
        rec = _record(s, pet)
        if p.get('gear') is None:
            rec['g'][p['slot']] = None
            return dict(message=f'Đã tháo linh kiện cho {pet["n"]}.')
        g = _gear(x, p['gear'])
        _need(g['s'] == p['slot'], 'Món này không gắn chỗ đó được.')
        who = _wearer(x, g['id'])
        if who and who in x['t']:
            for k, v in x['t'][who]['g'].items():
                if v == g['id']:
                    x['t'][who]['g'][k] = None
        rec['g'][p['slot']] = g['id']
        return dict(message=f'{pet["n"]} gắn {gear_name(g, s)}.')
    if name == 'jr_pet_gear_drop':
        pt._keys(p, {'gear', 'confirm'}, {'gear', 'confirm'})
        g = _gear(x, p['gear'])
        _confirm(p, f'Xác nhận bỏ {gear_name(g, s)}.')
        for r in x['t'].values():
            for k, v in r['g'].items():
                if v == g['id']:
                    r['g'][k] = None
        x['gear'].remove(g)
        from . import pet_wardrobe
        pet_wardrobe.tidy_models(s)
        return dict(message=f'Đã bỏ {gear_name(g, s)}.')
    raise AssertionError(name)


def _gear_up_roll(g: dict) -> bool:
    """✨ One +1 (paid already), jr_pet_gear_up's own: GUP_BP of its level; a miss loses nothing but the fee."""
    if roll(10000) < GUP_BP[g['lv']]:
        g['lv'] += 1
        return True
    return False


def _gear_fuse_roll(s: dict, x: dict, main: dict, others: list) -> bool:
    """📈 One rank up (paid already), jr_pet_gear_fuse's own: FUSE_BP of the rank; a success raises the main one in place
    (worn or not) back to +0 with the best model of the three and uses the two others up; a miss from LOSE_FROM loses the
    two others, below it keeps the three."""
    from . import pet_wardrobe
    r = main['r']
    if roll(10000) < FUSE_BP[r]:
        best = max(model_of(g, s) for g in [main] + others)
        for g in others:
            x['gear'].remove(g)
        main['r'], main['lv'] = r + 1, 0
        if best >= 3:
            main['m'] = 0
            pet_wardrobe.set_model(s, main['id'], best - 3)
        else:
            main['m'] = best
        pet_wardrobe.tidy_models(s)
        return True
    if r >= LOSE_FROM:
        for g in others:
            x['gear'].remove(g)
        pet_wardrobe.tidy_models(s)
    return False


def _auto_args(p: dict, scopes, top_max: int, scope_msg: str) -> tuple:
    """The common fields of a ⚡ Cường hóa nhanh command: (scope, top, budget)."""
    _pt()._keys(p, {'budget', 'top', 'scope', 'confirm'}, {'budget', 'confirm'})
    scope = p.get('scope', 'all')
    _need(scope == 'all' or (isinstance(scope, str) and scope in scopes), scope_msg)
    top = p.get('top', top_max)
    _need(_int(top, 1, top_max), 'Hạng dừng không hợp lệ.')
    budget = p['budget']
    _need(_int(budget, 1, 10**12), 'Nhập số xu tối đa muốn tiêu nhé.')
    return scope, top, budget


AUTO_STOP = {'done': ' Hết bộ ba để ghép.', 'top': ' Đã tới hạng đặt.', 'budget': ' Dừng vì chạm số xu đã đặt.',
             'money': ' Dừng vì hết tiền.', 'cap': ' Đủ lượt tối đa một lần, bấm tiếp nếu muốn.',
             'myth': ' ✨ Có thần thú muốn nhập vào bé: trả lời trước rồi ghép tiếp nhé.'}


# ---------------------------------------------------------------- ⚡ Cường hóa nhanh: pets
def fuse_sets(s: dict, scope: str = 'all', top: int = TOP + 1) -> list:
    """⚡ What Cường hóa nhanh may fuse now: [(rank, [main, a, b] pet ids, how many sets of that rank)], the lowest rank
    first, for every rank with three pets that may join (no 🌟 legendary, no sad pet at home; `scope` 'dog' / 'cat' one
    kind) whose result is at most `top` (TOP + 1: 🌟). The quick pick's rule (v4/pets.js quickLab): the 👑 main one the pet
    walked when it is among them, else the strongest; the two others never the pet walked, those in the kennel or at
    the grandparents' first, then the weakest."""
    pt = _pt()
    b = pt.get(s)
    if not b:
        return []
    walk = b['walk']
    day = s['journey']['life_day']
    groups: dict = {}
    for p in all_pets(s):
        br = C.BREEDS.get(p['b'])
        if not br or is_legend(p, s) or (scope != 'all' and br['kind'] != scope):
            continue
        rows, _, where = _where(s, p['id'])
        if where == 'home':
            n = pt.needs_at(p, day) if p['t'] < day else {k: p[k] for k in pt.NEEDS}
            if pt.mood(n) == 'buon':
                continue
        r = rec_of(s, p)['r']
        if r + 1 > top:
            continue
        groups.setdefault(r, []).append((p, where, power(s, p)))
    out = []
    for r in sorted(groups):
        g = groups[r]
        if len(g) < 3:
            continue
        main = next((q for q in g if q[0]['id'] == walk), None) or max(g, key=lambda q: (q[2], q[0]['id']))
        rest = sorted((q for q in g if q is not main and q[0]['id'] != walk),
                      key=lambda q: (q[1] == 'home', q[2], q[0]['id']))
        if len(rest) < 2:
            continue
        out.append((r, [main[0]['id'], rest[0][0]['id'], rest[1][0]['id']], len(g) // 3))
    return out


def _fuse_auto(s: dict, p: dict) -> dict:
    """⚡ jr_pet_fuse_auto: see the module's doc."""
    pt = _pt()
    scope, top, budget = _auto_args(p, ('dog', 'cat'), TOP + 1, 'Chọn chó, mèo hoặc tất cả nhé.')
    first = fuse_sets(s, scope, top)
    above = top <= TOP and bool(fuse_sets(s, scope))
    _need(bool(first), f'Đã tới hạng {RANKS[top]} rồi: chọn hạng cao hơn nhé.' if above
          else 'Chưa có ba bé cùng hạng (vui vẻ, không phải huyền thoại) để ghép.', 'not_owned')
    fee0 = FUSE_FEE[first[0][0]]
    _need(fee0 <= budget, f'Số xu đặt chưa đủ cho lượt ghép đầu ({_fmt(fee0)} xu).', 'not_enough')
    why = pt._ready_why(s, fee0)
    _need(not why, why, 'not_enough')
    _confirm(p, f'Xác nhận cường hóa nhanh thú cưng, tiêu tối đa {_fmt(budget)} xu.')
    before = {q['id']: (rec_of(s, q)['r'], is_legend(q, s)) for q in all_pets(s)}
    n = won = spent = 0
    stop = 'done'
    myth = None
    while True:
        left = fuse_sets(s, scope, top)
        if not left:
            stop = 'top' if top <= TOP and fuse_sets(s, scope) else 'done'
            break
        if n >= AUTO_MAX:
            stop = 'cap'
            break
        r, ids, _ = left[0]
        fee = FUSE_FEE[r]
        if spent + fee > budget:
            stop = 'budget'
            break
        if pt._ready_why(s, spent + fee):
            stop = 'money'
            break
        c = _fuse_check(s, dict(pets=ids, main=ids[0], confirm=True))
        spent += fee
        n += 1
        out = _fuse_roll(s, c, '')
        if out['fuse']['ok']:
            won += 1
            if out['fuse'].get('myth'):
                myth = out['fuse']['myth']
                stop = 'myth'
                break
    how = pt._pay(s, spent, f'Cường hóa nhanh thú cưng · {n} lượt')
    now = {q['id']: q for q in all_pets(s)}
    made = [dict(id=i, n=q['n'], b=q['b'], r=rec_of(s, q)['r'], legend=is_legend(q, s)) for i, q in now.items()
            if i in before and (rec_of(s, q)['r'], is_legend(q, s)) > before[i]]
    used = len(set(before) - set(now))
    msg = f'⚡ Cường hóa nhanh {n} lượt: {won} thành công, {n - won} trượt.'
    return dict(message=f'{msg}{AUTO_STOP[stop]} ({how})', ok=won > 0,
                auto=dict(n=n, ok=won, spent=spent, stop=stop, used=used, made=made, myth=myth,
                          left=sum(k for _, _, k in fuse_sets(s, scope, top))))


# ---------------------------------------------------------------- ⚡ Cường hóa nhanh: gear
def gear_step(s: dict, x: dict, scope: str = 'all', top: int = TOP) -> tuple | None:
    """⚡ The next step of Cường hóa nhanh linh kiện: ('up', gear) a +1, ('fuse', main, [a, b]) a rank up, or None.
    Three of one slot and rank whose result is at most `top`, the lowest rank first (then the slots' order): the main one
    the gear worn (then the highest level), strengthened to +GLV_MAX then ranked up with the two free ones (not worn) of
    the lowest levels. With none of those: the gear worn below +GLV_MAX, the highest rank first."""
    bag = [g for g in x['gear'] if scope == 'all' or g['s'] == scope]
    worn = {g['id'] for g in bag if _wearer(x, g['id'])}
    groups: dict = {}
    for g in bag:
        if g['r'] < min(top, TOP):
            groups.setdefault((g['r'], GSLOT_IDS.index(g['s'])), []).append(g)
    for key in sorted(groups):
        gs = groups[key]
        main = max(gs, key=lambda g: (g['id'] in worn, g['lv'], -int(g['id'][1:])))
        mates = sorted((g for g in gs if g is not main and g['id'] not in worn), key=lambda g: (g['lv'], int(g['id'][1:])))
        if len(mates) < 2:
            continue
        return ('up', main) if main['lv'] < GLV_MAX else ('fuse', main, mates[:2])
    on = sorted((g for g in bag if g['id'] in worn and g['lv'] < GLV_MAX), key=lambda g: (-g['r'], -g['lv'], int(g['id'][1:])))
    return ('up', on[0]) if on else None


def _step_fee(step: tuple) -> int:
    g = step[1]
    return GUP_FEE[g['r']] * (g['lv'] + 1) if step[0] == 'up' else GFUSE_FEE[g['r']]


def _gear_left(x: dict, scope: str, top: int) -> int:
    """How many rank ups are still possible (three of a slot and rank, two of them free, the result at most `top`)."""
    bag = [g for g in x['gear'] if scope == 'all' or g['s'] == scope]
    n = 0
    for r in range(min(top, TOP)):
        for sl in GSLOT_IDS:
            gs = [g for g in bag if g['s'] == sl and g['r'] == r]
            free = [g for g in gs if not _wearer(x, g['id'])]
            if len(gs) >= 3 and len(free) >= 2:
                n += min(len(gs) // 3, len(free) // 2)
    return n


def _gear_auto(s: dict, p: dict) -> dict:
    """⚡ jr_pet_gear_auto: see the module's doc."""
    pt = _pt()
    scope, top, budget = _auto_args(p, GSLOT_IDS, TOP, 'Chọn một loại linh kiện hoặc tất cả nhé.')
    x = get(s)
    first = gear_step(s, x, scope, top) if x else None
    _need(first is not None, 'Chưa có món nào cường hóa được: cần ba món cùng loại, cùng hạng (hai món chưa gắn) '
          'hoặc một món đang gắn chưa tới +' + str(GLV_MAX) + '.', 'not_owned')
    fee0 = _step_fee(first)
    _need(fee0 <= budget, f'Số xu đặt chưa đủ cho lượt đầu ({_fmt(fee0)} xu).', 'not_enough')
    why = pt._ready_why(s, fee0)
    _need(not why, why, 'not_enough')
    _confirm(p, f'Xác nhận cường hóa nhanh linh kiện, tiêu tối đa {_fmt(budget)} xu.')
    before = {g['id']: (g['r'], g['lv']) for g in x['gear']}
    n = won = ups = spent = 0
    stop = 'done'
    while True:
        step = gear_step(s, x, scope, top)
        if step is None:
            break
        if n >= GEAR_AUTO_MAX:
            stop = 'cap'
            break
        fee = _step_fee(step)
        if spent + fee > budget:
            stop = 'budget'
            break
        if pt._ready_why(s, spent + fee):
            stop = 'money'
            break
        spent += fee
        n += 1
        if step[0] == 'up':
            won += _gear_up_roll(step[1])
        else:
            ups += 1
            won += _gear_fuse_roll(s, x, step[1], step[2])
    how = pt._pay(s, spent, f'Cường hóa nhanh linh kiện · {n} lượt')
    made = [gear_view(x, g, s) for g in x['gear'] if g['id'] in before and (g['r'], g['lv']) > before[g['id']]]
    used = len(set(before) - {g['id'] for g in x['gear']})
    msg = f'⚡ Cường hóa nhanh {n} lượt: {won} thành công, {n - won} trượt.'
    return dict(message=f'{msg}{AUTO_STOP[stop]} ({how})', ok=won > 0,
                auto=dict(n=n, ok=won, spent=spent, stop=stop, used=used, made=made, fuses=ups,
                          left=_gear_left(x, scope, top)))


def chance(ranks: list) -> int:
    """The success chance (per 10 000) of a fusion of pets of these ranks."""
    low = min(ranks)
    if low == TOP:
        return LEGEND_BP
    return min(9000, FUSE_BP[low] + MIX_BP * sum(r - low for r in ranks))


def _ads():
    try:
        from . import ads
    except ImportError:   # a build without rewarded ads
        return None
    return ads


def _ad_boost(s: dict) -> int:
    """📺 What a rewarded ad adds to the next fusion (per 10 000), 0 without one (or without ads)."""
    a = _ads()
    return a.pet_boost(s) if a and hasattr(a, 'pet_boost') else 0


def breed_choices(pets: list, k: int, low: int) -> list:
    """The breeds the main pet (pets[k]) may have after a success: its own, the two others', and on a legendary fusion
    its kind's legendary breed. Never a breed of the other kind for a legendary of its own (a cat stays a cat there)."""
    main = pets[k]
    out = [main['b']] + [q['b'] for i, q in enumerate(pets) if i != k and q['b'] in C.BREEDS]
    if low == TOP:
        out.append(LEGEND[C.BREEDS[main['b']]['kind']])
    seen = []
    for b in out:
        if b not in seen and (b == main['b'] or C.BREEDS[b].get('fuse') != 'legend' or low == TOP):
            seen.append(b)
    return seen


def _fuse(s: dict, p: dict) -> dict:
    c = _fuse_check(s, p)
    _confirm(p, f'Xác nhận ghép ba bé ({_fmt(c["fee"])} xu).')
    how = _pt()._pay(s, c['fee'], f'Ghép thú cưng · {", ".join(q["n"] for q in c["pets"])}'[:120])
    return _fuse_roll(s, c, how)


def _fuse_check(s: dict, p: dict) -> dict:
    """🧬 jr_pet_fuse's checks, before the question: what the fusion is (the pets, the main one, the fee, the odds)."""
    pt = _pt()
    j = s['journey']
    day = j['life_day']
    pt._keys(p, {'pets', 'main', 'mix', 'breed', 'nick', 'confirm'}, {'pets', 'confirm'})
    ids = p['pets']
    _need(isinstance(ids, list) and len(ids) == 3 and all(isinstance(i, str) for i in ids) and len(set(ids)) == 3,
          'Chọn đúng ba bé để ghép nhé.')
    main_id = p.get('main', ids[0])
    _need(main_id in ids, 'Bé chính phải là một trong ba bé.')
    _need(p.get('mix') in (None, True, False), 'Thao tác không hợp lệ.')
    found = [_where(s, i) for i in ids]
    _need(all(f[1] is not None for f in found), 'Không thấy bé này.', 'not_owned')
    pets = [f[1] for f in found]
    _need(all(q['b'] in C.BREEDS for q in pets), 'Có bé thuộc giống chưa ghép được.')
    for q, f in zip(pets, found):
        if f[2] == 'home':
            n = pt.needs_at(q, day) if q['t'] < day else {k: q[k] for k in pt.NEEDS}
            _need(pt.mood(n) != 'buon', f'{q["n"]} đang buồn, chăm bé vui đã rồi hẵng ghép.', 'sad')
    x = _ensure(s)
    recs = [_record(s, q) for q in pets]
    ranks = [6 if is_legend(q, s) else r['r'] for q, r in zip(pets, recs)]
    k = ids.index(main_id)
    main, mrec = pets[k], recs[k]
    low = min(ranks)
    _need(not (low == TOP and is_legend(main, s)), f'{main["n"]} đã là huyền thoại rồi: chọn bé SSS khác làm bé chính nhé.')
    # what the main pet becomes (owner 19/10 "được chọn giữ bé hiện tại hoặc đổi giống")
    kind = C.BREEDS[main['b']]['kind']
    want = p.get('breed', main['b'])
    _need(isinstance(want, str) and want in breed_choices(pets, k, low), 'Chọn giống cho bé chính nhé.')
    d = _today(x)
    fee = FUSE_FEE[low]
    bp = chance(ranks)
    boost = _ad_boost(s)
    if boost:   # 📺 a rewarded ad: +10 points on this fusion at any rank, still a roll (game/ads.py)
        bp = min(_ads().PET_TOP, bp + boost)
    nick = pt._name(p['nick']) if p.get('nick') not in (None, '') else None
    return dict(p=p, found=found, pets=pets, recs=recs, ranks=ranks, k=k, main=main, mrec=mrec, low=low, want=want,
                fee=fee, bp=bp, boost=boost, nick=nick, x=x, d=d)


def _fuse_roll(s: dict, c: dict, how: str) -> dict:
    """🧬 One fusion (paid already), jr_pet_fuse's own: the count, the 📺 boost spent, one roll; a miss keeps the three
    below LOSE_FROM and loses the two others from it; a success a hybrid pup (`mix`) or the main pet up in place."""
    pt = _pt()
    day = s['journey']['life_day']
    p, found, pets, recs, k, main, mrec = c['p'], c['found'], c['pets'], c['recs'], c['k'], c['main'], c['mrec']
    low, want, bp, boost, nick, x, d = c['low'], c['want'], c['bp'], c['boost'], c['nick'], c['x'], c['d']
    main_id = main['id']
    d['f'] = min(10**9, d['f'] + 1)   # counted only (no daily limit since 19/10)
    if boost:
        _ads().spend_pet_boost(s)
    b = pt._ensure(s)
    others = [(f, r) for i, (f, r) in enumerate(zip(found, recs)) if i != k]

    def leave(gone, keep=True):
        """The pets of `gone` leave (their gear back in the bag, no longer walked); kept in `ret` unless lost."""
        for (rows, q, _), r in gone:
            rows.remove(q)
            x['t'].pop(q['id'], None)
            if keep:
                x['ret'].append(dict(b=q['b'], c=q['c'], n=q['n'], r=r['r'], fx=r['fx']))
            if b['walk'] == q['id']:
                b['walk'] = None
        if keep:
            x['ret'] = x['ret'][-RET_KEEP:]
            x['rn'] = min(10**7, x['rn'] + len(gone))
        if b['walk'] is None and b['list']:
            b['walk'] = b['list'][0]['id']
    if roll(10000) >= bp:
        if low >= LOSE_FROM:   # from A up the two others are gone (owner 19/10)
            lost = [f[1] for f, _ in others]
            leave(others, keep=False)
            return dict(message=f'💨 Lần này chưa thành. {main["n"]} vẫn ở bên bạn, {" và ".join(q["n"] for q in lost)} đã mất. ({how})',
                        fuse=dict(ok=False, main=main_id, lost=[q['id'] for q in lost]))
        return dict(message=f'💨 Lần này chưa thành, ba bé vẫn ở bên bạn. ({how})', fuse=dict(ok=False, main=main_id, lost=[]))
    rank = low + 1 if low < TOP else TOP
    breeds = sorted(q['b'] for q in pets)
    pot = [max(0, min(100, sum(r['pt'][i] for r in recs) // 3 - 8 + roll(24))) for i in range(len(STATS))]
    recipe = RECIPES.get(tuple(breeds)) if p.get('mix') is True and low < TOP else None
    if recipe and recipe[0] == 'lai_van_ho' and len({q['c'] for q in pets}) < 3:
        recipe = None
    if recipe and roll(10000) < HYBRID_BP:
        # 🧬 a hybrid pup: the three retire
        bid, floor = recipe
        rank = max(rank, floor)
        coat = roll(len(C.BREEDS[bid]['coats']))
        leave(list(zip(found, recs)))
        name = nick or C.SHELTER_NAMES[roll(len(C.SHELTER_NAMES))]
        pup = pt._new_pet(b, day, bid, coat, name, 'shop', 0)
        x['t'][pup['id']] = dict(r=rank, fx=FX[roll(len(FX))][0] if rank == TOP else '', pt=pot, tn=[0] * len(STATS),
                                 g={k: None for k in GSLOT_IDS}, z=int(pt.now()))
        where = place_new(s, pup)
        if b['walk'] is None and b['list']:
            b['walk'] = b['list'][0]['id']
        place = {'home': 'về nhà', 'ken': 'ở trại nuôi', 'farm': 'ở quê với bà'}.get(where, '')
        return dict(message=f'🧬 Giống lai hiếm! Ra đời bé {C.BREEDS[bid]["name"]} hạng {RANKS[rank]} tên {name}, {place}. '
                            f'Ba bé bố mẹ về quê với bà nghỉ ngơi. ({how})',
                    fuse=dict(ok=True, pet=pup['id'], rank=RANKS[rank], breed=bid, fx=x['t'][pup['id']]['fx']))
    # ⬆️ the main pet goes up in place
    fx = mrec['fx']
    old = C.BREEDS[main['b']]['name']
    if want != main['b']:
        donor = next((q for i, q in enumerate(pets) if i != k and q['b'] == want), None)
        main['b'], main['c'] = want, donor['c'] if donor else 0
    if low == TOP:
        if C.BREEDS[main['b']].get('fuse') == 'legend':
            fx = ''
        else:   # 🌟 a legendary that keeps its breed
            from . import pet_wardrobe
            pet_wardrobe.set_legend(s, main['id'])
    elif rank == TOP and fx not in tuple(f[0] for f in FX):
        fx = FX[roll(len(FX))][0]
    elif len(set(breeds)) == 1 and not fx and roll(10000) < MUTANT_BP:
        fx = 'dot_bien'
    mrec.update(r=rank, fx=fx, pt=[max(a, c) for a, c in zip(mrec['pt'], pot)], z=int(pt.now()))
    leave(others)
    br = C.BREEDS[main['b']]
    head = '🌟 HUYỀN THOẠI! ' if low == TOP else '🎉 '
    gone = ' và '.join(f[1]['n'] for f, _ in others)
    up = f'thành 🌟 huyền thoại' if low == TOP else f'lên hạng {RANKS[rank]}'
    from . import pet_wardrobe
    myth = pet_wardrobe.myth_offer(s, main, rank)   # ✨ owner 19/10: S and up may bring a thần thú
    extra = f' ✨ Một bé {myth["name"]} xuất hiện, muốn nhập vào {main["n"]}!' if myth else ''
    return dict(message=f'{head}{main["n"]} {up}{" (giống " + br["name"] + ")" if br["name"] != old else ""}! '
                        f'{gone} về quê với bà nghỉ ngơi. ({how}){extra}',
                fuse=dict(ok=True, pet=main_id, rank=RANKS[rank], breed=main['b'], fx=fx, up=True, myth=myth))


# ---------------------------------------------------------------- views
def gear_price(model: int, rank: int) -> int:
    return GSHOP[rank] * (GX_MULT[model - 3] if model >= 3 else 1)


def gear_view(x: dict, g: dict, s=None) -> dict:
    m = model_of(g, s)
    e, n = model_def(g['s'], m)
    return dict(id=g['id'], s=g['s'], m=m, r=g['r'], rank=RANKS[g['r']], lv=g['lv'], emoji=e, name=n, vip=m >= 3,
                stat=dict((a[0], a[3]) for a in GSLOTS)[g['s']], value=gear_value(g, s), on=_wearer(x, g['id']),
                up_fee=GUP_FEE[g['r']] * (g['lv'] + 1) if g['lv'] < GLV_MAX else 0)


def pet_extra(s: dict, p: dict) -> dict:
    """What pets.pet_view adds: rank, coat effect, stats, power, gear worn, the bonus it gives on a walk."""
    rec = rec_of(s, p)
    st = stats(s, p, rec)
    pct, cap = bonus_rate(s, p)
    return dict(r=rec['r'], rank=RANKS[rec['r']], fx=rec['fx'], legend=is_legend(p, s), st=st, pw=sum(st), tn=list(rec['tn']),
                g=dict(rec['g']), pct=pct, cap=cap)


def lite(s: dict, p: dict) -> dict:
    rec = rec_of(s, p)
    return dict(id=p['id'], b=p['b'], c=p['c'], n=p['n'], d=p['d'], r=rec['r'], rank=RANKS[rec['r']], fx=rec['fx'],
                legend=is_legend(p, s), pw=power(s, p), pct=bonus_rate(s, p)[0])


def public(s: dict) -> dict:
    x = get(s)
    d = x['day'] if x and x['day']['d'] == vn_day() else dict(f=0, tr=0, w=0, got=0)
    p = walker(s)
    pct, cap = bonus_rate(s, p) if p else (0, 0)
    return dict(ken=[lite(s, q) for q in x['ken']] if x else [], ret=list(x['ret']) if x else [], rn=x['rn'] if x else 0,
                gear=[gear_view(x, g, s) for g in x['gear']] if x else [],
                today=dict(fuse=d['f'], train=d['tr'], stroll=d['w'], got=d['got']), boost=_ad_boost(s) / 100,
                bonus=dict(on=bool(p), pet=p['id'] if p else None, pct=pct, cap=cap, got=d['got']))


def walk_extra(s: dict, p: dict) -> dict:
    """The rank and coat effect the street and the town draw (live clean_pet keeps r and x)."""
    rec = rec_of(s, p)
    out = {}
    if rec['r']:
        out['r'] = rec['r']
    if rec['fx']:
        out['x'] = rec['fx']
    if is_legend(p, s) and (C.BREEDS.get(p['b']) or {}).get('fuse') != 'legend':
        out['lg'] = True   # 🌟 a legendary that kept its breed (live/pet_rank.py: only with one kept)
    return out


def best(s: dict) -> dict | None:
    """The strongest pet (power, then rank) and the highest rank kept: the 'LC' board row (game/pets.py)."""
    rows = [(power(s, p), rec_of(s, p)['r'], p) for p in all_pets(s) if p['b'] in C.BREEDS]
    if not rows:
        return None
    pw, r, p = max(rows, key=lambda t: (t[0], t[1]))
    top = max(t[1] for t in rows)
    return dict(p=p, pw=pw, r=rec_of(s, p)['r'], fx=rec_of(s, p)['fx'], top=top, legend=any(is_legend(t[2], s) for t in rows))


def catalogue() -> dict:
    # owner 19/10 "đừng show tỷ lệ ra": no odds here (adoption, fusion, enhancing): what each rank gives, and the fees
    return dict(
        ranks=[dict(id=i, rank=r, name=RANK_NAME[r], profit=PROFIT[i], cap=CAP[i], range=list(RANGE[i]),
                    fee=FUSE_FEE[i], train=TRAIN_FEE[i]) for i, r in enumerate(RANKS)],
        sss_bond=[dict(at=a, pct=p, cap=c) for a, p, c in SSS_BOND],
        fx=[dict(id=a, emoji=b, name=c) for a, b, c in FX] + [dict(id='dot_bien', emoji='🧪', name='Đột biến')],
        recipes=[dict(of=list(k), to=v[0], floor=RANKS[v[1]], coats=v[0] == 'lai_van_ho') for k, v in RECIPES.items()],
        legend=dict(LEGEND), stats=[dict(id=a, emoji=b, name=c) for a, b, c in STATS],
        gear=dict(slots=[dict(id=a, emoji=b, name=c, stat=d) for a, b, c, d in GSLOTS],
                  models={k: [dict(emoji=e, name=n, mult=1, bonus=0) for e, n in v]
                          + [dict(emoji=e, name=n, mult=GX_MULT[i], bonus=GX_BONUS[i], vip=True) for i, (e, n) in enumerate(GMODELS_X[k])]
                          for k, v in GMODELS.items()},
                  base=list(GBASE), shop=list(GSHOP), up_fee=list(GUP_FEE), fuse_fee=list(GFUSE_FEE), lv_max=GLV_MAX),
        limits=dict(train_day=TRAIN_DAY, train_max=TRAIN_MAX, train_step=TRAIN_STEP, stroll_day=STROLL_DAY,
                    kennel=KENNEL_MAX, gear=GEAR_MAX, lose_from=LOSE_FROM, gear_qty=GEAR_QTY_MAX,
                    auto_max=AUTO_MAX, gear_auto_max=GEAR_AUTO_MAX))
