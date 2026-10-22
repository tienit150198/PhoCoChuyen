"""🪽 Cánh: wings the character wears, bought at 🛍️ Tiệm phụ kiện, raised through the pets' ranks (owner 22/10: "tính xem
thêm cánh cho người dùng nhé, cánh sẽ buff cho người chơi khi đánh pet", "cánh này là làm đẹp cho người dùng nhé, với tăng
tiền kiếm được nữa", "cho nâng nữa, nâng lên như thú đi, D > C > B > A > S > SS > SSS > Huyền thoại", "mua thì mặc định D
hoặc C ngẫu nhiên, xong nâng lên như cơ chế hiện tại nhé", "cho cánh đẹp tí, có cả mode cũ và mode mới đều hiển thị được").

* 🛍️ jr_pet_wing_buy {style, qty?, rid?, confirm}: a style of game/wings_content.py STYLES at its price, each wing rolled D or
  C (ODDS_BUY: D 70 %, C 30 %, like the pets' shop that sells only D and C). `rid` (the client's request id): a retried
  purchase answers the wings it already made and pays nothing (RQ_KEEP ids kept). At most OWN_MAX wings, qty ≤ QTY_MAX.
* 🧬 jr_pet_wing_fuse {wings: [3 ids], main?, confirm}: exactly the pets' fusion (game/pet_tiers.py _fuse): any three wings
  of any styles, the main one (`main`, else the first) keeps its style. The fee FUSE_FEE of the lowest tier is spent either
  way; the chance FUSE_BP of the lowest tier, +MIX_BP for each tier step another one has above it (≤ 90 %), never shown
  (owner 19/10 about pets: "đừng show tỷ lệ ra"). Success: the main wing goes up one tier in place (never below what it
  was) and the two others are used up. Three SSS: LEGEND_BP for 🌟 Huyền thoại. A failure keeps all three below LOSE_FROM
  (S); from S up the two others are gone, the main one stays. The roll is the pets' (secrets), once per command: the save's
  revision makes a retry of a played fusion a conflict, never a second roll.
* 👕 jr_pet_wing_wear {id | null}: one wing worn at a time (or none). 🗑️ jr_pet_wing_drop {id, confirm}: thrown away.
* 💰 The worn wing adds EARN[tier] % of the player's own work earnings (tile_match.fund_bonus: the same base as the pet's
  share, 🧰 the tools' and 💰 Tiền công's: finished jobs, the day's salary, TT99, commissions abroad; never staff orders, the
  quầy, gifts or transfers), at most CAP[tier] xu a Vietnam day, story mode only. Its own 'other_income' row "🪽 Cánh …"
  (PREFIX): kept out of the 🔥 x3 day's base net (tile_match.day_total), and 📈 game/income_boost.py scales that row once
  like every bonus row, so each bonus is computed on the un-boosted figure and nothing compounds. Together with the pet
  (2…30 %, capped a day) and 💰 Tiền công (≤ 50 %), a Huyền thoại adds at most 25 % (SSS 20 %): the bonuses are added, never multiplied.
* ⚔️ The worn wing adds BATTLE[tier] % to the HP and attack of the player's pets in every battle (game/pet_arena.py fighter
  writes `wg` into the snapshot; game/pet_battle.py derive). The jr_pet_* commands refresh the arena / war / challenge
  snapshots (game/pets.py command_commit), so a wing bought or worn counts from the next fight.

Save: journey['wings'] (absent until the first wing; journey.validate allows extra keys and older builds keep an unknown
journey key untouched, so 2.5.3 and older load, play and save a save that owns or wears wings: tests/test_wings.py Rollback)
    {v: 1, own: [{id 'w<n>', k style, r tier 0…7, z when it got that tier}], on: worn id | None, seq: next number,
     day: {d Vietnam day, got bonus xu that day}, rq: {request id: [wing ids]} the last RQ_KEEP purchases}
Seen by others: the worn wing {k, r} in the table wing_worn (SCHEMA_VERSION 90), written with the save (commit), read by the
live service (live/wings.py) as `wg` on walkers, drawn by public/js/v4/look.js paintWings in both display modes.
"""
from __future__ import annotations

import re
import secrets

from .wings_content import BATTLE, CAP, EARN, INDEX, ORDER, SSS, STYLES, TIER_NAME, TIERS, TOP

KEY = 'wings'
VERSION = 1
BLOCK_KEYS = frozenset({'v', 'own', 'on', 'seq', 'day', 'rq'})
WING_KEYS = frozenset({'id', 'k', 'r', 'z'})
COMMANDS = ('jr_pet_wing_buy', 'jr_pet_wing_wear', 'jr_pet_wing_fuse', 'jr_pet_wing_drop')
ODDS_BUY = (7000, 3000)                                                   # per 10 000: D, C
# tier t ×3 → t+1: game/pet_tiers.py FUSE_BP up to A; from S easier than the pets' 6 / 3 / 5 % and dearer in fees (owner
# 22/10: Huyền thoại "5-10 tỷ là hợp lý", not the pets' ~109 tỷ on average): from the cheapest style S ≈ 1 triệu,
# SS ≈ 25 triệu, SSS ≈ 450 triệu, Huyền thoại ≈ 7 tỷ on average (tests/test_wings.py Tables).
FUSE_BP = (6000, 4500, 3000, 1500, 1000, 1500)
FUSE_FEE = (500, 2_000, 10_000, 50_000, 300_000, 20_000_000, 200_000_000)   # by the lowest tier; [6] = three SSS
LEGEND_BP = 1500
MIX_BP = 300
LOSE_FROM = 4                                                             # S
OWN_MAX = 60
QTY_MAX = 20
RQ_KEEP = 10
PREFIX = '🪽 Cánh'
LABEL = 'Tiệm phụ kiện · Cánh'
ID_RE = re.compile(r'w[0-9]{1,7}')
STYLE_RE = re.compile(r'[a-z_]{1,24}')
RID_RE = re.compile(r'[A-Za-z0-9_.:-]{8,64}')


def _core():
    from . import engine
    return engine


def _need(ok, msg, code='invalid_action'):
    _core().need(ok, msg, code)


def _int(v, lo=0, hi=10**12) -> bool:
    return type(v) is int and lo <= v <= hi


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def vn_day() -> int:
    from . import pet_tiers
    return pet_tiers.vn_day()


def roll(n: int) -> int:
    return secrets.randbelow(n)


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    w = j.get(KEY) if isinstance(j, dict) else None
    return w if isinstance(w, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = dict(v=VERSION, own=[], on=None, seq=1, day=dict(d=0, got=0), rq={})
    return j[KEY]


def worn(s: dict) -> dict | None:
    """The wing worn now ({id, k, r, z}), or None."""
    w = get(s)
    if not w or not w.get('on'):
        return None
    return next((x for x in w['own'] if x['id'] == w['on']), None)


def tier_label(r: int) -> str:
    return 'Huyền thoại' if r == TOP else TIERS[r]


def name(x: dict) -> str:
    st = INDEX.get(x['k'])
    return f'{st["name"] if st else "Cánh"} {tier_label(x["r"])}'


def battle_pct(s: dict) -> int:
    """⚔️ The pet-battle bonus % of the worn wing (0 without one, or outside story mode)."""
    j = s.get('journey') if isinstance(s, dict) else None
    x = worn(s) if isinstance(j, dict) and j.get('story') else None
    return BATTLE[x['r']] if x else 0


def ref(s: dict) -> dict | None:
    """{k, r} of the worn wing: what the character draws and other players see (wing_worn, live/wings.py)."""
    x = worn(s)
    return dict(k=x['k'], r=x['r']) if x else None


# ---------------------------------------------------------------- 💰 the bonus where money is earned
def fund_bonus(s: dict, c: dict, base: int, what: str, ref_: str | None) -> int:
    """The worn wing's share of an earning of a workplace fund (game/tile_match.fund_bonus, your own work): its own row."""
    if type(base) is not int or base <= 0:
        return 0
    j = s.get('journey')
    x = worn(s) if isinstance(j, dict) and j.get('story') else None
    if not x:
        return 0
    w = get(s)
    d = vn_day()
    if w['day']['d'] != d:
        w['day'] = dict(d=d, got=0)
    pct, cap = EARN[x['r']], CAP[x['r']]
    bonus = min(base * pct // 100, max(0, cap - w['day']['got']))
    if bonus <= 0:
        return 0
    _core().money(s, c, bonus, f'{PREFIX} {tier_label(x["r"])} +{pct}% · {what}'[:120], ref_, category='other_income')
    w['day']['got'] += bonus
    return bonus


# ---------------------------------------------------------------- commands
def _keys(p, allowed, required=frozenset()):
    _need(isinstance(p, dict) and set(p) <= allowed and required <= set(p), 'Thông tin không hợp lệ.')


def _wing(w: dict, wid) -> dict:
    x = next((x for x in w['own'] if x['id'] == wid), None) if isinstance(wid, str) else None
    _need(x is not None, 'Không thấy đôi cánh này.', 'not_owned')
    return x


def _new(w: dict, k: str, r: int) -> dict:
    from . import pets
    x = dict(id=f'w{w["seq"]}', k=k, r=r, z=int(pets.now()))
    w['seq'] += 1
    w['own'].append(x)
    return x


def chance(tiers: list) -> int:
    """The success chance (per 10 000) of a fusion of wings of these tiers (game/pet_tiers.py chance)."""
    low = min(tiers)
    if low == SSS:
        return LEGEND_BP
    return min(9000, FUSE_BP[low] + MIX_BP * sum(t - low for t in tiers))


def action(s: dict, name_: str, p: dict) -> dict:
    from . import pets as pt
    _need(name_ in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    if name_ == 'jr_pet_wing_buy':
        _keys(p, {'style', 'qty', 'rid', 'confirm'}, {'style', 'confirm'})
        st = INDEX.get(p['style']) if isinstance(p['style'], str) else None
        _need(st is not None, 'Chọn một kiểu cánh trong tiệm nhé.')
        qty = p.get('qty', 1)
        _need(_int(qty, 1, QTY_MAX), f'Mua từ 1 đến {QTY_MAX} đôi một lần nhé.')
        rid = p.get('rid')
        _need(rid is None or (isinstance(rid, str) and RID_RE.fullmatch(rid) is not None), 'Thông tin không hợp lệ.')
        w = get(s)
        if rid and w and rid in w['rq']:   # a retried purchase: the wings it made, nothing paid again
            made = [x for x in w['own'] if x['id'] in w['rq'][rid]]
            return dict(message=f'Đã mua rồi: {", ".join(name(x) for x in made) or st["name"]}.', wings=[dict(x) for x in made], duplicate=True)
        times = f' ×{qty}' if qty > 1 else ''
        _need(p['confirm'] is True, f'Xác nhận mua {st["name"]}{times} ({_fmt(st["price"] * qty)} xu).')
        w = _ensure(s)
        room = OWN_MAX - len(w['own'])
        _need(room > 0, f'Tủ cánh đã đủ {OWN_MAX} đôi. Ghép hoặc bỏ bớt nhé.', 'limit')
        _need(qty <= room, f'Tủ cánh chỉ còn chỗ cho {room} đôi. Ghép hoặc bỏ bớt nhé.', 'limit')
        how = pt._pay(s, st['price'] * qty, f'{LABEL} · {st["name"]}{times}')
        made = [_new(w, st['id'], 0 if roll(10000) < ODDS_BUY[0] else 1) for _ in range(qty)]
        if rid:
            w['rq'][rid] = [x['id'] for x in made]
            while len(w['rq']) > RQ_KEEP:
                w['rq'].pop(next(iter(w['rq'])))
        first = not w['on']
        if first:   # the first wing goes on at once
            w['on'] = made[0]['id']
        tiers = ', '.join(f'{n} hạng {tier_label(r)}' for r, n in ((r, sum(1 for x in made if x['r'] == r)) for r in (1, 0)) if n)
        on = ' Đeo luôn rồi nè!' if first else ''
        return dict(message=f'🪽 Đã mua {st["name"]}{times}: {tiers} ({how}).{on}', wings=[dict(x) for x in made])
    w = _ensure(s)
    if name_ == 'jr_pet_wing_wear':
        _keys(p, {'id'}, {'id'})
        if p['id'] is None:
            w['on'] = None
            return dict(message='Đã cất cánh vào tủ.')
        x = _wing(w, p['id'])
        w['on'] = x['id']
        return dict(message=f'🪽 Đã đeo {name(x)}.')
    if name_ == 'jr_pet_wing_drop':
        _keys(p, {'id', 'confirm'}, {'id', 'confirm'})
        x = _wing(w, p['id'])
        _need(p['confirm'] is True, f'Xác nhận bỏ {name(x)}.')
        w['own'].remove(x)
        if w['on'] == x['id']:
            w['on'] = None
        return dict(message=f'Đã bỏ {name(x)}.')
    # 🧬 jr_pet_wing_fuse
    _keys(p, {'wings', 'main', 'confirm'}, {'wings', 'confirm'})
    ids = p['wings']
    _need(isinstance(ids, list) and len(ids) == 3 and all(isinstance(i, str) for i in ids) and len(set(ids)) == 3,
          'Chọn đúng ba đôi cánh để ghép nhé.')
    main_id = p.get('main', ids[0])
    _need(main_id in ids, 'Đôi cánh chính phải là một trong ba đôi.')
    xs = [_wing(w, i) for i in ids]
    main = xs[ids.index(main_id)]
    others = [x for x in xs if x is not main]
    tiers = [x['r'] for x in xs]
    low = min(tiers)
    _need(low < TOP, 'Huyền thoại là hạng cao nhất rồi.', 'full')
    _need(main['r'] < TOP, f'{name(main)} đã là huyền thoại rồi: chọn đôi khác làm cánh chính nhé.', 'full')
    fee = FUSE_FEE[low]
    _need(p['confirm'] is True, f'Xác nhận ghép ba đôi cánh ({_fmt(fee)} xu).')
    how = pt._pay(s, fee, f'Ghép cánh · {", ".join(name(x) for x in xs)}'[:120])
    if roll(10000) >= chance(tiers):
        if low >= LOSE_FROM:   # from S up the two others are gone (the pets' rule)
            for x in others:
                w['own'].remove(x)
                if w['on'] == x['id']:
                    w['on'] = main['id']
            return dict(message=f'💨 Lần này chưa thành. {name(main)} vẫn còn, hai đôi kia đã mất. ({how})',
                        fuse=dict(ok=False, main=main['id'], lost=[x['id'] for x in others]))
        return dict(message=f'💨 Lần này chưa thành, ba đôi cánh vẫn còn nguyên. ({how})', fuse=dict(ok=False, main=main['id'], lost=[]))
    main['r'] = max(main['r'], low + 1)
    from . import pets
    main['z'] = int(pets.now())
    for x in others:
        w['own'].remove(x)
        if w['on'] == x['id']:
            w['on'] = main['id']
    head = '🌟 HUYỀN THOẠI! ' if main['r'] == TOP else '🎉 '
    return dict(message=f'{head}{INDEX.get(main["k"], {}).get("name", "Đôi cánh")} lên hạng {tier_label(main["r"])}! ({how})',
                fuse=dict(ok=True, main=main['id'], tier=main['r']))


# ---------------------------------------------------------------- views
def public(s: dict) -> dict | None:
    w = get(s)
    if not w:
        return None
    x = worn(s)
    d = vn_day()
    return dict(own=[dict(x) for x in w['own']], on=w['on'], got=w['day']['got'] if w['day']['d'] == d else 0,
                cap=CAP[x['r']] if x else 0)


def catalogue() -> dict:
    """Static lists for the client (content.journey.wardrobe.wings)."""
    return dict(styles=[dict(x) for x in STYLES], tiers=list(TIERS), tier_names=list(TIER_NAME), earn=list(EARN), cap=list(CAP),
                battle=list(BATTLE), fee=list(FUSE_FEE), own_max=OWN_MAX, qty_max=QTY_MAX, lose_from=LOSE_FROM)


# ---------------------------------------------------------------- save
def validate(s: dict) -> None:
    w = get(s)
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or KEY not in j:
        return
    bad = 'Dữ liệu cánh không hợp lệ.'
    ok = lambda v: _need(v, bad, 'invalid_save')   # noqa: E731
    ok(isinstance(w, dict) and set(w) == BLOCK_KEYS and w['v'] == VERSION)
    ok(isinstance(w['own'], list) and len(w['own']) <= OWN_MAX)
    ok(_int(w['seq'], 1, 10**7))
    seen = set()
    for x in w['own']:
        ok(isinstance(x, dict) and set(x) == WING_KEYS and isinstance(x['id'], str) and ID_RE.fullmatch(x['id']) is not None)
        ok(isinstance(x['k'], str) and STYLE_RE.fullmatch(x['k']) is not None and _int(x['r'], 0, TOP) and _int(x['z'], 0, 10**11))
        ok(x['id'] not in seen and int(x['id'][1:]) < w['seq'])
        seen.add(x['id'])
    ok(w['on'] is None or w['on'] in seen)
    ok(isinstance(w['day'], dict) and set(w['day']) == {'d', 'got'} and _int(w['day']['d'], 0, 10**7) and _int(w['day']['got'], 0, 10**9))
    ok(isinstance(w['rq'], dict) and len(w['rq']) <= RQ_KEEP)
    for k, v in w['rq'].items():
        ok(isinstance(k, str) and RID_RE.fullmatch(k) is not None and isinstance(v, list) and len(v) <= QTY_MAX
           and all(isinstance(i, str) and ID_RE.fullmatch(i) for i in v))


# ---------------------------------------------------------------- the table others read (SCHEMA_VERSION 90)
def commit(db, sid: str, after: dict) -> None:
    """A jr_pet_wing_* command, in the save's transaction (game/pets.py command_commit): the worn wing in wing_worn (what
    the street and the 2.5D map draw on this player, live/wings.py), the live service told when it changed."""
    r = ref(after)
    row = db.execute('SELECT k, r FROM wing_worn WHERE sid=?', (sid,)).fetchone()
    if (dict(k=row['k'], r=int(row['r'])) if row else None) == r:
        return
    from . import live_chat, pets
    if r:
        db.execute('INSERT INTO wing_worn(sid, pid, k, r, at) VALUES(?,?,?,?,?) ON CONFLICT (sid) DO UPDATE SET k=EXCLUDED.k, '
                   'r=EXCLUDED.r, at=EXCLUDED.at', (sid, live_chat.pid_of(sid), r['k'], r['r'], pets.now()))
    else:
        db.execute('DELETE FROM wing_worn WHERE sid=?', (sid,))
    live_chat.notify(db, dict(op='wing', pids=[live_chat.pid_of(sid)]))


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM wing_worn WHERE sid=?', (sid,))


__all__ = ['ORDER', 'STYLES']
