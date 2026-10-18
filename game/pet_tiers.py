"""🏅 Hạng thú cưng, 🧬 ghép ba, 📊 chỉ số, 🧰 linh kiện (owner 19/10: "pet thường tăng 2% lợi nhuận, pet xịn 30% 50%",
"chia theo D B C … tới SSS", "ghép 3 con đi thì hay hơn", "tỷ lệ ra SSS thấp thôi", "chỉ số để cạnh tranh", "linh kiện").
The pet games and tournaments come later (owner: "trò chơi của pets chưa làm").

* Every pet has a rank (RANKS, D…SSS) rolled when it arrives (ODDS_SHELTER / ODDS_SHOP, per 10 000 000) or given by
  a fusion. Pets older than this module: adopted D, bought C (_record).
* 💰 Only the pet walking with you, not sad, adds PROFIT % of what you earn at work (tile_match.fund_bonus: the day's
  salary, finished jobs, TT99, commissions abroad; never the staff orders nor the quầy chain), at most CAP xu a
  Vietnam day; an SSS with a deep bond (SSS_BOND) more. Its own 'other_income' row (PREFIX), kept out of the 🔥 x3 net.
* 🧬 jr_pet_fuse: three pets of one kind (dogs or cats), each at least MIN_AGE life days with you. Success
  (FUSE_BP of the lowest rank, +MIX_BP for each rank step another one has above it): a pup one rank up; the three
  retire to the grandparents' for good (never die, never sold: `ret`). A failure keeps all three; the fee (FUSE_FEE)
  is spent either way. Three SSS: LEGEND_BP for a 🌟 legendary. Three pets of a RECIPE: HYBRID_BP for a 🧬 hybrid
  (at least its floor rank). At most FUSE_DAY a Vietnam day. An SSS gets one of the FX coats.
* 📊 Five stats: the rank's RANGE × the pet's potential (pt, 0–100, rolled at birth, a pup inherits its parents'
  mean), the breed's lean (pets_content `st`), training (tn, jr_pet_train) and the gear worn. Power = their sum
  (the 'LC' board, game/pets.py command_commit).
* 🧰 Gear (GSLOTS, ranks like the pets): bought (GSHOP), found on a stroll (jr_pet_stroll, May mắn), enhanced
  +1…+10 (GUP_BP; a failure loses nothing but the fee), fused three of a slot and rank into one rank up. Stats only,
  never money.
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
ODDS_SHELTER = (7_000_000, 2_200_000, 600_000, 180_000, 18_000, 2_000, 0)
ODDS_SHOP = (5_500_990, 2_800_000, 1_100_000, 450_000, 130_000, 19_000, 10)   # SSS 0,0001 %
FUSE_BP = (6000, 4500, 3000, 1500, 600, 300)                              # rank r ×3 → r+1, per 10 000
FUSE_FEE = (500, 2_000, 10_000, 50_000, 300_000, 5_000_000, 10_000_000)   # by the lowest rank; [6] = 3 SSS
LEGEND_BP = 500
MIX_BP = 300
HYBRID_BP = 1000
MUTANT_BP = 500
FUSE_DAY = 10
MIN_AGE = 3
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
GBASE = (4, 7, 11, 16, 22, 30, 40)            # the stat a gear adds at +0; each level +10 % of it
GSHOP = (300, 1500, 6000)                     # D, C, B in the shop
GUP_BP = (10000, 9000, 8000, 7000, 6000, 5000, 4000, 3500, 3000, 2500)   # +lv → +lv+1
GUP_FEE = (100, 300, 1000, 3000, 10_000, 30_000, 100_000)                # × (lv + 1)
GFUSE_FEE = (50, 200, 1000, 5000, 30_000, 500_000)
GLV_MAX = 10
GEAR_MAX = 60
STROLL_DAY = 3
GEAR_ODDS = (6000, 2800, 900, 250, 45, 5, 0)   # per 10 000, a find on a stroll
COMMANDS = ('jr_pet_fuse', 'jr_pet_train', 'jr_pet_kennel', 'jr_pet_stroll', 'jr_pet_gear_buy', 'jr_pet_gear_up',
            'jr_pet_gear_fuse', 'jr_pet_gear_wear', 'jr_pet_gear_drop')
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


def is_legend(p: dict) -> bool:
    br = C.BREEDS.get(p['b'])
    return bool(br and br.get('fuse') == 'legend')


def gear_value(g: dict) -> int:
    base = GBASE[g['r']]
    return base + base * g['lv'] // 10


def stats(s: dict, p: dict, rec: dict | None = None) -> list:
    rec = rec or rec_of(s, p)
    lo, hi = LEGEND_RANGE if is_legend(p) else RANGE[rec['r']]
    lean = (C.BREEDS.get(p['b']) or {}).get('st') or (0,) * len(STATS)
    x = get(s)
    bag = {g['id']: g for g in (x['gear'] if x else [])}
    out = []
    for i, sid in enumerate(STAT_IDS):
        v = lo + (hi - lo) * rec['pt'][i] // 100 + lean[i] + rec['tn'][i]
        for slot, gid in rec['g'].items():
            g = bag.get(gid)
            if g and dict((a[0], a[3]) for a in GSLOTS)[slot] == sid:
                v += gear_value(g)
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
    x = _ensure(s)
    day = _today(x)
    bonus = min(base * pct // 100, max(0, cap - day['got']))
    if bonus <= 0:
        return 0
    rank = RANKS[rec_of(s, p)['r']]
    from .engine import money
    money(s, c, bonus, f'{PREFIX} {rank} +{pct}% · {p["n"]} · {what}'[:120], ref, category='other_income')
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


def gear_name(g: dict) -> str:
    e, n = GMODELS[g['s']][g['m']]
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
    if name == 'jr_pet_kennel':
        pt._keys(p, {'pet', 'to'}, {'pet', 'to'})
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
        _need(len(b['list']) < C.MAX_PETS, f'Nhà đã đủ {C.MAX_PETS} bé rồi.', 'limit')
        x['ken'].remove(pet)
        pet['t'] = day
        for k in pt.NEEDS:
            pet[k] = max(pet[k], 80)
        b['list'].append(pet)
        if b['walk'] is None:
            b['walk'] = pet['id']
        return dict(message=f'🏡 {pet["n"]} về nhà rồi, mừng quýnh.')
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
        return dict(message=f'🎁 {pet["n"]} tha về {gear_name(g)}!', found=g['id'])
    x = _ensure(s)
    if name == 'jr_pet_gear_buy':
        pt._keys(p, {'slot', 'model', 'rank', 'confirm'}, {'slot', 'model', 'rank', 'confirm'})
        _need(p['slot'] in GSLOT_IDS and _int(p['model'], 0, len(GMODELS.get(p['slot'], ())) - 1) and _int(p['rank'], 0, len(GSHOP) - 1),
              'Chọn một món trong tiệm nhé.')
        _need(len(x['gear']) < GEAR_MAX, f'Túi linh kiện đã đủ {GEAR_MAX} món.', 'limit')
        e, nm = GMODELS[p['slot']][p['model']]
        _confirm(p, f'Xác nhận mua {nm} hạng {RANKS[p["rank"]]}.')
        how = pt._pay(s, GSHOP[p['rank']], f'Linh kiện thú cưng · {nm} {RANKS[p["rank"]]}')
        g = dict(id=f'g{x["gs"]}', s=p['slot'], m=p['model'], r=p['rank'], lv=0)
        x['gs'] += 1
        x['gear'].append(g)
        return dict(message=f'🛍️ Đã mua {gear_name(g)} ({how}).')
    if name == 'jr_pet_gear_up':
        pt._keys(p, {'gear', 'confirm'}, {'gear', 'confirm'})
        g = _gear(x, p['gear'])
        _need(g['lv'] < GLV_MAX, f'{gear_name(g)} đã cường hóa tối đa.', 'full')
        fee = GUP_FEE[g['r']] * (g['lv'] + 1)
        _confirm(p, f'Xác nhận cường hóa {gear_name(g)} ({_fmt(fee)} xu).')
        how = pt._pay(s, fee, f'Cường hóa linh kiện · {gear_name(g)}')
        if roll(10000) < GUP_BP[g['lv']]:
            g['lv'] += 1
            return dict(message=f'✨ Thành công! {gear_name(g)}. ({how})', ok=True)
        return dict(message=f'💨 Cường hóa trượt, món đồ vẫn nguyên {gear_name(g)}. ({how})', ok=False)
    if name == 'jr_pet_gear_fuse':
        pt._keys(p, {'gears', 'confirm'}, {'gears', 'confirm'})
        ids = p['gears']
        _need(isinstance(ids, list) and len(ids) == 3 and len(set(map(str, ids))) == 3, 'Chọn đúng ba món nhé.')
        gs = [_gear(x, i) for i in ids]
        _need(len({g['s'] for g in gs}) == 1 and len({g['r'] for g in gs}) == 1, 'Ba món phải cùng loại và cùng hạng.')
        r = gs[0]['r']
        _need(r < TOP, 'Hạng SSS là cao nhất rồi.', 'full')
        _need(not any(_wearer(x, g['id']) for g in gs), 'Tháo linh kiện khỏi các bé trước khi ghép nhé.', 'worn')
        fee = GFUSE_FEE[r]
        _confirm(p, f'Xác nhận ghép ba {GSLOTS[GSLOT_IDS.index(gs[0]["s"])][2].lower()} hạng {RANKS[r]} ({_fmt(fee)} xu).')
        how = pt._pay(s, fee, f'Ghép linh kiện {RANKS[r]}')
        if roll(10000) < FUSE_BP[r]:
            for g in gs:
                x['gear'].remove(g)
            g = _new_gear(x, gs[0]['s'], r + 1)
            return dict(message=f'🎉 Ghép thành công: {gear_name(g)}! ({how})', ok=True, gear=g['id'])
        return dict(message=f'💨 Ghép trượt, ba món vẫn còn nguyên. ({how})', ok=False)
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
        return dict(message=f'{pet["n"]} gắn {gear_name(g)}.')
    if name == 'jr_pet_gear_drop':
        pt._keys(p, {'gear', 'confirm'}, {'gear', 'confirm'})
        g = _gear(x, p['gear'])
        _confirm(p, f'Xác nhận bỏ {gear_name(g)}.')
        for r in x['t'].values():
            for k, v in r['g'].items():
                if v == g['id']:
                    r['g'][k] = None
        x['gear'].remove(g)
        return dict(message=f'Đã bỏ {gear_name(g)}.')
    raise AssertionError(name)


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


def _fuse(s: dict, p: dict) -> dict:
    pt = _pt()
    j = s['journey']
    day = j['life_day']
    pt._keys(p, {'pets', 'nick', 'confirm'}, {'pets', 'confirm'})
    ids = p['pets']
    _need(isinstance(ids, list) and len(ids) == 3 and all(isinstance(i, str) for i in ids) and len(set(ids)) == 3,
          'Chọn đúng ba bé để ghép nhé.')
    found = [_where(s, i) for i in ids]
    _need(all(f[1] is not None for f in found), 'Không thấy bé này.', 'not_owned')
    pets = [f[1] for f in found]
    _need(all(q['b'] in C.BREEDS for q in pets), 'Có bé thuộc giống chưa ghép được.')
    kinds = {C.BREEDS[q['b']]['kind'] for q in pets}
    _need(len(kinds) == 1, 'Chỉ ghép ba bé cùng loài: chó với chó, mèo với mèo.')
    kind = kinds.pop()
    for q, f in zip(pets, found):
        _need(day - q['d'] >= MIN_AGE, f'{q["n"]} mới về chưa đủ {MIN_AGE} ngày, để bé quen nhà đã nhé.', 'young')
        if f[2] == 'home':
            n = pt.needs_at(q, day) if q['t'] < day else {k: q[k] for k in pt.NEEDS}
            _need(pt.mood(n) != 'buon', f'{q["n"]} đang buồn, chăm bé vui đã rồi hẵng ghép.', 'sad')
    x = _ensure(s)
    recs = [_record(s, q) for q in pets]
    ranks = [6 if is_legend(q) else r['r'] for q, r in zip(pets, recs)]
    d = _today(x)
    _need(d['f'] < FUSE_DAY, f'Hôm nay đã ghép {FUSE_DAY} lần rồi. Mai ghép tiếp nhé.', 'limit')
    low = min(ranks)
    fee = FUSE_FEE[low]
    bp = chance(ranks)
    boost = _ad_boost(s)
    if boost:   # 📺 a rewarded ad: +10 points on this fusion at any rank, still a roll (game/ads.py)
        bp = min(_ads().PET_TOP, bp + boost)
    nick = pt._name(p['nick']) if p.get('nick') not in (None, '') else None
    _confirm(p, f'Xác nhận ghép ba bé ({_fmt(fee)} xu, tỷ lệ thành công {bp / 100:g}%).')
    how = pt._pay(s, fee, f'Ghép thú cưng · {", ".join(q["n"] for q in pets)}'[:120])
    d['f'] += 1
    if boost:
        _ads().spend_pet_boost(s)
    if roll(10000) >= bp:
        return dict(message=f'💨 Lần này chưa thành, ba bé vẫn ở bên bạn. ({how})', fuse=dict(ok=False, chance=bp))
    # the pup
    rank = low + 1 if low < TOP else TOP
    fx = ''
    breeds = sorted(q['b'] for q in pets)
    recipe = RECIPES.get(tuple(breeds))
    if recipe and recipe[0] == 'lai_van_ho' and len({q['c'] for q in pets}) < 3:
        recipe = None
    if low == TOP:
        bid = LEGEND[kind]
        coat = 0
    elif recipe and roll(10000) < HYBRID_BP:
        bid, floor = recipe
        rank = max(rank, floor)
        coat = roll(len(C.BREEDS[bid]['coats']))
    else:
        mom = pets[roll(3)]
        bid, coat = mom['b'], mom['c']
        if len(set(breeds)) == 1 and roll(10000) < MUTANT_BP:
            fx = 'dot_bien'
    if rank == TOP and low < TOP:
        fx = FX[roll(len(FX))][0]
    pot = [max(0, min(100, sum(r['pt'][i] for r in recs) // 3 - 8 + roll(24))) for i in range(len(STATS))]
    # the three retire (their gear back in the bag, no longer walked)
    b = pt._ensure(s)
    for (rows, q, where), r in zip(found, recs):
        rows.remove(q)
        x['t'].pop(q['id'], None)
        x['ret'].append(dict(b=q['b'], c=q['c'], n=q['n'], r=r['r'], fx=r['fx']))
        if b['walk'] == q['id']:
            b['walk'] = None
    x['ret'] = x['ret'][-RET_KEEP:]
    x['rn'] = min(10**7, x['rn'] + 3)
    name = nick or C.SHELTER_NAMES[roll(len(C.SHELTER_NAMES))]
    pup = pt._new_pet(b, day, bid, coat, name, 'shop', 0)
    x['t'][pup['id']] = dict(r=rank, fx=fx, pt=pot, tn=[0] * len(STATS), g={k: None for k in GSLOT_IDS}, z=int(pt.now()))
    where = place_new(s, pup)
    if b['walk'] is None and b['list']:
        b['walk'] = b['list'][0]['id']
    br = C.BREEDS[bid]
    head = '🌟 HUYỀN THOẠI! ' if br['fuse'] == 'legend' else ('🧬 Giống lai hiếm! ' if br['fuse'] == 'hybrid' else '🎉 ')
    place = {'home': 'về nhà', 'ken': 'ở trại nuôi', 'farm': 'ở quê với bà'}.get(where, '')
    return dict(message=f'{head}Ra đời bé {br["name"]} hạng {RANKS[rank]} tên {name}, {place}. Ba bé bố mẹ về quê với bà nghỉ ngơi. ({how})',
                fuse=dict(ok=True, chance=bp, pet=pup['id'], rank=RANKS[rank], breed=bid, fx=fx))


# ---------------------------------------------------------------- views
def gear_view(x: dict, g: dict) -> dict:
    e, n = GMODELS[g['s']][g['m']]
    return dict(id=g['id'], s=g['s'], m=g['m'], r=g['r'], rank=RANKS[g['r']], lv=g['lv'], emoji=e, name=n,
                stat=dict((a[0], a[3]) for a in GSLOTS)[g['s']], value=gear_value(g), on=_wearer(x, g['id']),
                up_fee=GUP_FEE[g['r']] * (g['lv'] + 1) if g['lv'] < GLV_MAX else 0,
                up_bp=GUP_BP[g['lv']] if g['lv'] < GLV_MAX else 0)


def pet_extra(s: dict, p: dict) -> dict:
    """What pets.pet_view adds: rank, coat effect, stats, power, gear worn, the bonus it gives on a walk."""
    rec = rec_of(s, p)
    st = stats(s, p, rec)
    pct, cap = bonus_rate(s, p)
    return dict(r=rec['r'], rank=RANKS[rec['r']], fx=rec['fx'], legend=is_legend(p), st=st, pw=sum(st), tn=list(rec['tn']),
                g=dict(rec['g']), pct=pct, cap=cap)


def lite(s: dict, p: dict) -> dict:
    rec = rec_of(s, p)
    return dict(id=p['id'], b=p['b'], c=p['c'], n=p['n'], d=p['d'], r=rec['r'], rank=RANKS[rec['r']], fx=rec['fx'],
                legend=is_legend(p), pw=power(s, p))


def public(s: dict) -> dict:
    x = get(s)
    d = x['day'] if x and x['day']['d'] == vn_day() else dict(f=0, tr=0, w=0, got=0)
    p = walker(s)
    pct, cap = bonus_rate(s, p) if p else (0, 0)
    return dict(ken=[lite(s, q) for q in x['ken']] if x else [], ret=list(x['ret']) if x else [], rn=x['rn'] if x else 0,
                gear=[gear_view(x, g) for g in x['gear']] if x else [],
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
    return out


def best(s: dict) -> dict | None:
    """The strongest pet (power, then rank) and the highest rank kept: the 'LC' board row (game/pets.py)."""
    rows = [(power(s, p), rec_of(s, p)['r'], p) for p in all_pets(s) if p['b'] in C.BREEDS]
    if not rows:
        return None
    pw, r, p = max(rows, key=lambda t: (t[0], t[1]))
    top = max(t[1] for t in rows)
    return dict(p=p, pw=pw, r=rec_of(s, p)['r'], fx=rec_of(s, p)['fx'], top=top, legend=any(is_legend(t[2]) for t in rows))


def catalogue() -> dict:
    pc = lambda w, n: f'{w * 100 / n:.4f}'.rstrip('0').rstrip('.')
    return dict(
        ranks=[dict(id=i, rank=r, name=RANK_NAME[r], profit=PROFIT[i], cap=CAP[i], range=list(RANGE[i]),
                    shelter=pc(ODDS_SHELTER[i], ODDS), shop=pc(ODDS_SHOP[i], ODDS),
                    fuse=(FUSE_BP[i] / 100 if i < TOP else LEGEND_BP / 100), fee=FUSE_FEE[i], train=TRAIN_FEE[i]) for i, r in enumerate(RANKS)],
        sss_bond=[dict(at=a, pct=p, cap=c) for a, p, c in SSS_BOND],
        fx=[dict(id=a, emoji=b, name=c) for a, b, c in FX] + [dict(id='dot_bien', emoji='🧪', name='Đột biến')],
        recipes=[dict(of=list(k), to=v[0], floor=RANKS[v[1]], coats=v[0] == 'lai_van_ho') for k, v in RECIPES.items()],
        legend=dict(LEGEND), stats=[dict(id=a, emoji=b, name=c) for a, b, c in STATS],
        gear=dict(slots=[dict(id=a, emoji=b, name=c, stat=d) for a, b, c, d in GSLOTS],
                  models={k: [dict(emoji=e, name=n) for e, n in v] for k, v in GMODELS.items()},
                  base=list(GBASE), shop=list(GSHOP), up=list(GUP_BP), up_fee=list(GUP_FEE), fuse_fee=list(GFUSE_FEE), lv_max=GLV_MAX),
        limits=dict(fuse_day=FUSE_DAY, train_day=TRAIN_DAY, train_max=TRAIN_MAX, train_step=TRAIN_STEP, stroll_day=STROLL_DAY,
                    kennel=KENNEL_MAX, gear=GEAR_MAX, min_age=MIN_AGE, mix=MIX_BP / 100, hybrid=HYBRID_BP / 100,
                    legend=LEGEND_BP / 100, mutant=MUTANT_BP / 100))
