"""🎣 Câu cá: rods, baits, power casts, a fish bag, 📖 Sổ cá, 🐟 Chợ cá (with haggling), carried fish and trophies.

Owner 24/10 ("chỗ câu cá ấy, tôi muốn phát triển thành bộ sưu tập cá, rồi mua cần câu cá, quăng thì xa ra cá lớn, gần ra
cá nhỏ … cho người ta chọn lực để quăng … cá chia nhiều loại … càng hiếm càng to, mang được trên người … cần có giá tí
để người ta câu cá kiếm tiền"), then: no daily cast limit; the bite wait is random and longer for bigger / rarer fish;
the trader sometimes haggles. Every number lives in game/fishing_content.py.

The server decides everything that matters at the cast (jr_fish_cast): how far the line went (power × rod range × a
random spread: the same rod and power land differently), the zone, whether something bites at all (rỉa mồi), junk or a
fish, its rarity, species, weight and when it bites (a longer wait leans to a heavier fish). The client only plays the
bobber, the nibbles and the reel mini-game; it never learns the fish before the catch. jr_fish_hook must come inside the
bite window (too early: the fish is scared off; too late: it let go), jr_fish_land no sooner than REEL_MIN_SHARE of the
fight; a fish too heavy for the line was fated to snap at the cast. Receipts make a retried landing harmless.

Selling (jr_fish_sell) pays the price of game/fishing_content.price; HAGGLE_CHANCE of the sales the trader offers less
(70–95 %): accept, bargain once (full price, a small bonus, or he refuses those fish for the day) or decline (the offer
stands for the day: no re-rolling by declining). No daily cap anywhere: the round's minimum times are the guard.

Save: journey['fish'] (optional, absent until the first command; older builds ignore it). The three keepsakes of
game/leisure.py (cá rô, cá chép, cá trắm) move into Sổ cá when the block is made (`mig`); leisure keeps its own counts.
PostgreSQL (game/fish_lb.py, in the save's transaction): the boards 🐋 Cá lớn nhất (all time, weekly) and 📖 Bộ sưu tập,
the species records; a 🔴 Cổ đại catch posts a line on the town ticker; a 🏝️ island cast is checked against the trip.
"""
from __future__ import annotations

import math
import re
import secrets
import time

from . import fishing_content as C

VERSION = 1
KEYS = frozenset({'v', 'seq', 'rods', 'rod', 'bait', 'use', 'gio', 'bag', 'dex', 'tot', 'ms', 'carry', 'aq', 'tro', 'act',
                  'rc', 'deal', 'rel', 'mig'})
FISH_KEYS = frozenset({'i', 's', 'g', 'd', 'p', 'k', 'o', 'od'})
ACT_KEYS = frozenset({'id', 'at', 'spot', 'trip', 'rod', 'dist', 'zone', 'kind', 'sp', 'g', 'bite', 'hook', 'reel', 'snap', 'nib'})
TOT_KEYS = ('cast', 'fish', 'junk', 'snap', 'miss', 'sold', 'xu', 'rel')
COMMANDS = ('jr_fish_cast', 'jr_fish_hook', 'jr_fish_land', 'jr_fish_buy', 'jr_fish_equip', 'jr_fish_sell', 'jr_fish_deal',
            'jr_fish_keep', 'jr_fish_release', 'jr_fish_carry', 'jr_fish_mount', 'jr_fish_aqua')
TOKEN = re.compile(r'[0-9a-f]{32}')
TRIP_RE = re.compile(r'[0-9a-f]{16}')
UID_RE = re.compile(r'd[0-9]{1,9}')
MS_RE = re.compile(r'r[0-6]|s_(ho|song|bien|dao)|all')
MAX_RECEIPTS = 12
TROPHY_MAX = 12
SELL_MAX = 200
LIMIT = 10**9
KIND, LABEL = 'life', '🎣 Câu cá'
TROPHY_KIND = 'tranh_ca'   # game/deco_content.py ITEMS: a wall piece drawn from journey.fish.tro


def now() -> float:
    return time.time()


def vn_day(t: float) -> int:
    from .wealth_fee import today
    return today(t)


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


# ---------------------------------------------------------------- the block
def _fresh(j: dict) -> dict:
    d = dict(v=VERSION, seq=0, rods=['tre'], rod='tre', bait={}, use='', gio=0, bag=[], dex={},
             tot={k: 0 for k in TOT_KEYS}, ms=[], carry=0, aq=[], tro={}, act=None, rc=[], deal=None, rel=[0, 0], mig=0)
    _migrate(j, d)
    return d


def _migrate(j: dict, d: dict) -> None:
    """🐟 game/leisure.py's keepsakes (cá rô, cá chép, cá trắm) into Sổ cá, once: their counts, no weight known (0)."""
    if d.get('mig'):
        return
    old = (j.get('leisure') or {}).get('fish') if isinstance(j.get('leisure'), dict) else None
    if isinstance(old, dict):
        for sp in C.LEGACY:
            n = old.get(sp)
            if type(n) is int and n > 0:
                row = d['dex'].setdefault(sp, [0, 0, 0])
                row[0] = min(LIMIT, row[0] + n)
                row[2] |= 1 << C.SPOT_IDS.index('ho')
    d['mig'] = 1


def get(s: dict) -> dict | None:
    d = s['journey'].get('fish')
    return d if isinstance(d, dict) else None


def ensure(s: dict) -> dict:
    j = s['journey']
    d = get(s)
    if d is None:
        d = j['fish'] = _fresh(j)
    return d


def cap(d: dict) -> int:
    return C.BASKETS[min(d['gio'], len(C.BASKETS) - 1)]['cap']


def _rarity(sp: str) -> int:
    return (C.SPECIES.get(sp) or {}).get('r', 0)   # a species of a newer build (rollback): the lowest


def _find(d: dict, uid) -> dict | None:
    return next((f for f in d['bag'] if f['i'] == uid), None)


def legacy_catch(s: dict, sp: str) -> None:
    """game/leisure.py's old fishing round (an older client): the keepsake also counts in Sổ cá when the block exists."""
    d = get(s)
    if d and sp in C.SPECIES:
        row = d['dex'].setdefault(sp, [0, 0, 0])
        row[0] = min(LIMIT, row[0] + 1)
        row[2] |= 1 << C.SPOT_IDS.index('ho')


# ---------------------------------------------------------------- public
def public(s: dict) -> dict | None:
    """journey.fish for the client (None before the first command). The open round's fish is never in it."""
    d = get(s)
    j = s['journey']
    if d is None:
        old = (j.get('leisure') or {}).get('fish') if isinstance(j.get('leisure'), dict) else None
        dex = {sp: [n, 0, 1] for sp, n in (old or {}).items() if sp in C.SPECIES and type(n) is int and n > 0}
        return dict(fresh=True, rod='tre', rods=['tre'], bait={}, use='', gio=0, cap=C.BASKETS[0]['cap'], bag=[], dex=dex,
                    tot={k: 0 for k in TOT_KEYS}, ms=[], carry=0, aq=[], tro={}, deal=None, cond=C.conditions(now())) if dex else None
    day = vn_day(now())
    bag = [dict(i=f['i'], s=f['s'], g=f['g'], p=f['p'], k=f['k'], o=f['o'] if f['od'] == day else 0, pr=C.price(f['s'], f['g']))
           for f in d['bag'] if f['s'] in C.SPECIES]   # pr: what 🐟 Quầy thu mua pays (before haggling)
    deal = None
    if d['deal'] and d['deal']['at'] + C.DEAL_TTL > now():
        deal = _deal_view(d, d['deal']['ids'], day)
    return dict(rod=d['rod'], rods=list(d['rods']), bait=dict(d['bait']), use=d['use'], gio=d['gio'], cap=cap(d), bag=bag,
                dex={k: list(v) for k, v in d['dex'].items()}, tot=dict(d['tot']), ms=list(d['ms']), carry=d['carry'],
                aq=[list(x) for x in d['aq']], tro={k: list(v) for k, v in d['tro'].items()}, deal=deal,
                cond=C.conditions(now()))   # 🌙 / 🌧️ now: the lake's sky and which species can bite


def carried(s: dict) -> dict | None:
    """The fish worn on the walk maps, or None: {sp, r, kg} and what draws it (fam, body, belly, fin, pat), the shape
    live/fish_carry.py rebuilds from the {sp, kg} the client sends it (`fh`)."""
    d = get(s)
    f = _find(d, d['carry']) if d and d['carry'] else None
    if not f or f['s'] not in C.SPECIES:
        return None
    sp = C.SPECIES[f['s']]
    return dict(sp=sp['id'], r=sp['r'], kg=round(f['g'] / 1000, 2), fam=sp['fam'], body=sp['body'], belly=sp['belly'], fin=sp['fin'],
                pat=sp['pat'])


def catalogue() -> dict:
    """api.content.journey.fish: everything the client draws and explains (static)."""
    sp = [dict(id=x['id'], name=x['name'], r=x['r'], fam=x['fam'], spots=list(x['spots']), w=list(x['w']), body=x['body'],
               belly=x['belly'], fin=x['fin'], pat=x['pat'], cond=C.cond_text(x), hint=x['hint']) for x in C.SPECIES.values()]
    return dict(
        rarities=[dict(r) for r in C.RARITIES], spots=[dict(id=k, **v) for k, v in C.SPOTS.items()],
        zones=[dict(id=z['id'], name=z['name'], to=min(z['to'], 999)) for z in C.ZONES],
        rods=[{k: r[k] for k in ('id', 'name', 'emoji', 'price', 'range', 'line', 'luck', 'reel', 'bite', 'ancient', 'color')} for r in C.RODS],
        baits=[{k: b[k] for k in ('id', 'name', 'emoji', 'price', 'n', 'hint')} for b in C.BAITS],
        baskets=[dict(b) for b in C.BASKETS], species=sp, junk=[dict(id=a, emoji=b, name=c) for a, b, c in C.JUNK],
        power_sweet=C.POWER_SWEET, hook_window=C.HOOK_WINDOW, carry_min=C.CARRY_MIN, aquarium=C.AQUARIUM_MAX,
        trophies=TROPHY_MAX, tier_reward=list(C.TIER_REWARD), spot_reward=C.SPOT_REWARD,
        haggle=dict(chance=C.HAGGLE_CHANCE, offer=list(C.HAGGLE_OFFER)),
        titles=[dict(id=t['id'], emoji=t['emoji'], name=t['name'], earn=t['earn']) for t in C.STYLE_TITLES])


def weather(t: float | None = None) -> dict:
    t = now() if t is None else t
    return C.conditions(t)


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Câu cá kiếm tiền chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác câu cá không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict), 'Dữ liệu câu cá không hợp lệ.')
    d = ensure(s)
    t = now()
    fn = globals()['_' + name[len('jr_fish_'):]]
    return fn(s, d, p, t)   # the block itself reaches the client with the state (journey.fish)


def _cast(s, d, p, t):
    need = _core().need
    spot = p.get('spot')
    need(set(p) <= {'spot', 'power', 'trip'} and spot in C.SPOTS, 'Chọn một chỗ câu nhé.')
    if C.SPOTS[spot].get('island'):
        need(isinstance(p.get('trip'), str) and TRIP_RE.fullmatch(p['trip']) is not None, 'Bạn không ở trên hòn đảo này.', 'no_island')
    else:
        need('trip' not in p, 'Chỗ câu không hợp lệ.')
    power = p.get('power')
    need(type(power) in (int, float) and math.isfinite(power) and 0 <= power <= 1, 'Lực quăng không hợp lệ.')
    need(len(d['bag']) < cap(d), f'Giỏ đầy rồi ({cap(d)} con)! Bán bớt ở 🐟 Quầy thu mua nhé.', 'bag_full')
    rng = secrets.SystemRandom()
    rod = C.ROD.get(d['rod']) or C.ROD['tre']   # a rod of a newer build (rollback): the bamboo one
    bait = d['use'] if d['use'] in C.BAIT and d['bait'].get(d['use'], 0) > 0 else None
    if bait:
        d['bait'][bait] -= 1
        if d['bait'][bait] <= 0:
            d['bait'].pop(bait)
            d['use'] = ''
    d['tot']['cast'] = min(LIMIT, d['tot']['cast'] + 1)
    d['act'] = None
    dist = min(C.SPOTS[spot]['max'], power * rod['range'] * rng.uniform(*C.SPREAD))
    if power > C.POWER_SWEET and rng.random() < C.TANGLE_CHANCE:
        return dict(message='🪢 Quăng mạnh quá, dây rối mất rồi! Gỡ dây rồi quăng lại nhé.',
                    cast=dict(tangle=True, dist=round(dist, 1)))
    zone = C.zone_of(dist)
    z = C.ZONES[zone]
    cond = C.conditions(t)
    start = t + C.CAST_SECONDS
    act = dict(id=secrets.token_hex(16), at=t, spot=spot, trip=p.get('trip', ''), rod=rod['id'], dist=round(dist, 2),
               zone=zone, kind='none', sp='', g=0, bite=0.0, hook=0.0, reel=0.0, snap=0, nib=[])
    if rng.random() >= rod['bite']:
        act['bite'] = start + rng.uniform(*C.NOBITE_WAIT)          # rỉa mồi: nibbles, then the bait is gone
    elif rng.random() < z['junk']:
        act.update(kind='junk', sp=rng.choice(C.JUNK)[0], bite=start + rng.uniform(*C.JUNK_WAIT), reel=2.0)
    else:
        ws = C.rarity_weights(spot, zone, rod['id'], bait, cond)
        r = rng.choices(range(C.NR), weights=ws)[0]
        sp = rng.choice(C.pool(spot, r, cond))
        f = rng.random() ** z['skew']
        kg = C.weight_of(sp, f)
        act.update(kind='fish', sp=sp['id'], g=C.grams(kg), bite=start + C.wait_of(r, f, rng.random(), bait),
                   reel=round(C.reel_of(r, f, rod['id']), 2), snap=1 if rng.random() < C.snap_chance(kg, rod['id']) else 0)
    k = rng.randint(*C.NIBBLES)
    lo, hi = start + 1.2, act['bite'] - 1.3
    act['nib'] = sorted(round(rng.uniform(lo, hi), 2) for _ in range(k)) if hi > lo else []
    d['act'] = act
    view = dict(id=act['id'], now=t, dist=round(dist, 1), zone=zone, splash=start, nib=list(act['nib']),
                window=C.HOOK_WINDOW, cond=cond)
    if act['kind'] == 'none':
        view['gone'] = act['bite']
    else:
        view['bite'] = act['bite']
    return dict(message='', cast=view, **({'bait_used': bait} if bait else {}))


def _round(d, p, keys):
    need = _core().need
    token = p.get('round')
    need(set(p) == keys and isinstance(token, str) and TOKEN.fullmatch(token) is not None, 'Lượt câu không hợp lệ.', 'bad_round')
    return token


def _close(d, token, res):
    d['rc'] = (d['rc'] + [dict(id=token, res=res)])[-MAX_RECEIPTS:]
    d['act'] = None


def _hook(s, d, p, t):
    need = _core().need
    token = _round(d, p, {'round'})
    a = d['act']
    need(isinstance(a, dict) and a['id'] == token, 'Lượt câu đã đóng. Quăng cần lần nữa nhé.', 'bad_round')
    need(a['hook'] == 0, 'Đã giật cần rồi.', 'bad_round')
    if a['kind'] == 'none':
        _close(d, token, 'none')
        d['tot']['miss'] = min(LIMIT, d['tot']['miss'] + 1)
        return dict(message='🐟 Cá rỉa mất mồi rồi! Quăng lại nhé.', hook=dict(lost='none'))
    if t < a['bite'] - C.HOOK_EARLY:
        _close(d, token, 'early')
        d['tot']['miss'] = min(LIMIT, d['tot']['miss'] + 1)
        return dict(message='😱 Giật sớm quá, cá hoảng sợ bỏ đi mất!', hook=dict(lost='early'))
    if t > a['bite'] + C.HOOK_WINDOW + C.HOOK_LATE:
        _close(d, token, 'late')
        d['tot']['miss'] = min(LIMIT, d['tot']['miss'] + 1)
        return dict(message='💨 Chậm tay rồi, cá nhả mồi mất!', hook=dict(lost='late'))
    a['hook'] = t
    if a['kind'] == 'junk':
        return dict(message='', hook=dict(secs=a['reel'], pull=0.12, dart=0.05, green=0.5, heavy=False, snap_at=None))
    r = _rarity(a['sp'])
    kg = a['g'] / 1000
    fight = C.fight_of(r, kg, a['rod'])
    snap_at = round(a['reel'] * secrets.SystemRandom().uniform(0.35, 0.7), 2) if a['snap'] else None
    return dict(message='', hook=dict(secs=a['reel'], heavy=kg > C.ROD[a['rod']]['line'], snap_at=snap_at, **fight))


def _land(s, d, p, t):
    need = _core().need
    token = p.get('round')
    need(set(p) == {'round', 'ok'} and isinstance(token, str) and TOKEN.fullmatch(token) is not None and type(p.get('ok')) is bool,
         'Lượt câu không hợp lệ.', 'bad_round')
    old = next((x for x in d['rc'] if x['id'] == token), None)
    if old:
        return dict(message='Lượt này đã lưu rồi.', duplicate=True, land=dict(res=old['res']))
    a = d['act']
    need(isinstance(a, dict) and a['id'] == token and a['hook'] > 0, 'Lượt câu đã đóng. Quăng cần lần nữa nhé.', 'bad_round')
    if p['ok'] and not a['snap']:   # a snap or a lost fish may end the fight early; a landed one takes its reel time
        need(t - a['hook'] + 0.05 >= a['reel'] * C.REEL_MIN_SHARE, 'Cá còn đang giãy, kéo tiếp nào!', 'too_early')
    need(t <= a['at'] + C.ROUND_TTL, 'Lượt câu đã hết giờ. Quăng lại nhé.', 'expired')
    tot = d['tot']
    if a['snap']:
        _close(d, token, 'snap')
        tot['snap'] = min(LIMIT, tot['snap'] + 1)
        heavy = a['kind'] == 'fish' and a['g'] / 1000 > C.ROD[a['rod']]['line']
        return dict(message='💥 Phựt! Đứt dây rồi.' + (' Cá này quá nặng so với cần, nâng cấp cần ở 🎣 Quầy bán cần nhé!' if heavy else ''),
                    land=dict(res='snap', heavy=heavy))
    if not p['ok']:
        _close(d, token, 'miss')
        tot['miss'] = min(LIMIT, tot['miss'] + 1)
        return dict(message='🐟 Cá giãy mạnh quá, thoát mất rồi!', land=dict(res='miss'))
    if a['kind'] == 'junk':
        _close(d, token, 'junk')
        tot['junk'] = min(LIMIT, tot['junk'] + 1)
        junk = next(x for x in C.JUNK if x[0] == a['sp'])
        return dict(message=f'{junk[1]} Kéo lên… {junk[2]}! Thôi coi như dọn sạch hồ.', land=dict(res='junk', junk=junk[0]))
    sp, g, spot = a['sp'], a['g'], a['spot']
    day = vn_day(t)
    d['seq'] += 1
    uid = d['seq']
    d['bag'].append(dict(i=uid, s=sp, g=g, d=day, p=C.SPOT_IDS.index(spot), k=0, o=0, od=0))
    row = d['dex'].get(sp)
    first = row is None or row[0] == 0
    if row is None:
        row = d['dex'][sp] = [0, 0, 0]
    pb = g > row[1]
    row[0] = min(LIMIT, row[0] + 1)
    row[1] = max(row[1], g)
    row[2] |= 1 << C.SPOT_IDS.index(spot)
    tot['fish'] = min(LIMIT, tot['fish'] + 1)
    _close(d, token, 'fish')
    r = _rarity(sp)
    rewards = _milestones(s, d) if first else []
    info = C.SPECIES[sp]
    rar = C.RARITIES[r]
    msg = f'{rar["emoji"]} {info["name"]} {fmt_kg(g)}!' + (' 📖 Loài mới!' if first else ' 🏅 Kỷ lục của bạn!' if pb and row[0] > 1 else '')
    catch = dict(i=uid, s=sp, g=g, r=r, spot=spot, price=C.price(sp, g), new=first, pb=bool(pb and row[0] > 1), at=t)
    out = dict(message=msg, land=dict(res='fish', catch=catch))
    if rewards:
        out['effects'] = rewards
    return out


def fmt_kg(g: int) -> str:
    kg = g / 1000
    if kg >= 1000:
        return f'{kg / 1000:.2f}'.rstrip('0').rstrip('.').replace('.', ',') + ' tấn'
    if kg >= 100:
        return f'{kg:.0f} kg'
    if kg >= 1:
        return f'{kg:.1f}'.rstrip('0').rstrip('.').replace('.', ',') + ' kg'
    return f'{g} g'


def _grant(s: dict, item: str) -> bool:
    from . import spend as sp
    from .spend_content import PERMANENT
    b = sp._ensure(s)
    if item in b['own'] or len(b['own']) >= sp.OWN_MAX:
        return False
    b['own'][item] = PERMANENT
    return True


def _milestones(s: dict, d: dict) -> list:
    """📖 A rarity tier, a spot or the whole book just completed: its xu (and title) once (journey.fish.ms)."""
    j = s['journey']
    have = {k for k, v in d['dex'].items() if v[0] > 0}
    lines = []
    from .spend_content import STYLE_ITEMS
    for r in range(C.NR):
        key = f'r{r}'
        if key in d['ms'] or not all(x['id'] in have for x in C.by_rarity(r)):
            continue
        d['ms'].append(key)
        xu = C.TIER_REWARD[r]
        _jr()._wallet(j, xu, KIND, f'📖 Sổ cá: đủ cá {C.RARITIES[r]["name"]}')
        lines.append(f'📖 Đủ bộ cá {C.RARITIES[r]["emoji"]} {C.RARITIES[r]["name"]}: +{fmt(xu)} xu')
        tid = C.TIER_TITLE[r]
        if tid and _grant(s, tid):
            lines.append(f'🎖️ Danh hiệu mới: {STYLE_ITEMS[tid]["emoji"]} {STYLE_ITEMS[tid]["name"]}')
    for spot, tid in C.SPOT_TITLE.items():
        key = f's_{spot}'
        if key in d['ms'] or not all(x['id'] in have for x in C.at_spot(spot)):
            continue
        d['ms'].append(key)
        _jr()._wallet(j, C.SPOT_REWARD, KIND, f'📖 Sổ cá: đủ cá {C.SPOTS[spot]["name"]}')
        lines.append(f'{C.SPOTS[spot]["emoji"]} Đủ cá {C.SPOTS[spot]["name"]}: +{fmt(C.SPOT_REWARD)} xu')
        if _grant(s, tid):
            lines.append(f'🎖️ Danh hiệu mới: {STYLE_ITEMS[tid]["emoji"]} {STYLE_ITEMS[tid]["name"]}')
    if 'all' not in d['ms'] and len(have & set(C.SPECIES_IDS)) == len(C.SPECIES_IDS):
        d['ms'].append('all')
        for item in (C.ALL_TITLE, C.ALL_FRAME):
            if _grant(s, item):
                lines.append(f'🎖️ {STYLE_ITEMS[item]["emoji"]} {STYLE_ITEMS[item]["name"]}')
    return lines


# ---------------------------------------------------------------- shop
def _pay(s: dict, amount: int, label: str) -> None:
    from . import auction as auc
    why = auc.ready_why(s, amount)
    _core().need(not why, why or 'Chưa đủ xu.', 'not_enough')
    auc._take(s, amount, label)


def _buy(s, d, p, t):
    need = _core().need
    kind, item = p.get('kind'), p.get('item')
    need(set(p) <= {'kind', 'item', 'n'} and kind in ('rod', 'bait', 'gio') and isinstance(item, str), 'Chọn món cần mua nhé.')
    if kind == 'rod':
        need(set(p) == {'kind', 'item'} and item in C.ROD, 'Cần câu không hợp lệ.')
        need(item not in d['rods'], 'Bạn có cần này rồi.', 'owned')
        rod = C.ROD[item]
        _pay(s, rod['price'], f'🎣 Mua {rod["name"]}')
        d['rods'].append(item)
        d['rods'].sort(key=C.ROD_IDS.index)
        d['rod'] = item
        return dict(message=f'{rod["emoji"]} Đã mua {rod["name"]}! Đã lắp vào tay, ra hồ quăng thử nào.')
    if kind == 'gio':
        idx = next((i for i, b in enumerate(C.BASKETS) if b['id'] == item), None)
        need(set(p) == {'kind', 'item'} and idx is not None, 'Giỏ không hợp lệ.')
        need(idx > d['gio'], 'Bạn có giỏ tốt hơn rồi.', 'owned')
        b = C.BASKETS[idx]
        _pay(s, b['price'], f'🧺 Mua {b["name"]}')
        d['gio'] = idx
        return dict(message=f'{b["emoji"]} Đã đổi sang {b["name"]}: chứa {b["cap"]} con.')
    n = p.get('n', 1)
    need(item in C.BAIT and type(n) is int and 1 <= n <= 10, 'Mồi không hợp lệ.')
    b = C.BAIT[item]
    need(d['bait'].get(item, 0) + b['n'] * n <= C.BAIT_MAX, f'Túi mồi đầy rồi (tối đa {C.BAIT_MAX}).', 'full')
    _pay(s, b['price'] * n, f'{b["emoji"]} Mua {b["name"]}')
    d['bait'][item] = d['bait'].get(item, 0) + b['n'] * n
    if not d['use']:
        d['use'] = item
    return dict(message=f'{b["emoji"]} +{b["n"] * n} {b["name"]}.')


def _equip(s, d, p, t):
    need = _core().need
    need(len(p) == 1 and set(p) <= {'rod', 'bait'}, 'Chọn cần hoặc mồi nhé.')
    if 'rod' in p:
        need(p['rod'] in d['rods'], 'Bạn chưa có cần này.', 'not_owned')
        d['rod'] = p['rod']
        return dict(message=f'{C.ROD[p["rod"]]["emoji"]} Đã cầm {C.ROD[p["rod"]]["name"]}.')
    b = p['bait']
    need(b == '' or (b in C.BAIT and d['bait'].get(b, 0) > 0), 'Bạn chưa có mồi này.', 'not_owned')
    d['use'] = b
    return dict(message=f'{C.BAIT[b]["emoji"]} Dùng {C.BAIT[b]["name"]}.' if b else 'Câu không mồi đặc biệt.')


# ---------------------------------------------------------------- 🐟 Chợ cá
def _ids(d: dict, p: dict, key: str = 'ids') -> list:
    need = _core().need
    ids = p.get(key)
    need(isinstance(ids, list) and 1 <= len(ids) <= SELL_MAX and all(type(i) is int for i in ids) and len(set(ids)) == len(ids),
         'Chọn cá nhé.')
    have = {f['i'] for f in d['bag']}
    need(all(i in have for i in ids), 'Có con cá không còn trong giỏ.', 'gone')
    return ids


def _deal_view(d: dict, ids: list, day: int) -> dict:
    fish = [f for f in d['bag'] if f['i'] in ids and f['s'] in C.SPECIES]
    full = sum(C.price(f['s'], f['g']) for f in fish)
    offer = sum(C.price(f['s'], f['g']) * (f['o'] if f['od'] == day and f['o'] > 0 else 100) // 100 for f in fish)
    return dict(ids=[f['i'] for f in fish], full=full, offer=offer, pct=round(100 * offer / full) if full else 100)


def _sold(s: dict, d: dict, ids: list, total: int, line: str) -> None:
    j = s['journey']
    d['bag'] = [f for f in d['bag'] if f['i'] not in ids]
    if d['carry'] in ids:
        d['carry'] = 0
    d['deal'] = None
    d['tot']['sold'] = min(LIMIT, d['tot']['sold'] + len(ids))
    d['tot']['xu'] = min(LIMIT, d['tot']['xu'] + total)
    left = total
    while left > 0:   # one history row stays under journey.ROW_MAX
        part = min(left, 10**7)
        _jr()._wallet(j, part, KIND, line)
        left -= part


def _sell(s, d, p, t):
    need = _core().need
    need(set(p) == {'ids'}, 'Chọn cá để bán nhé.')
    ids = _ids(d, p)
    day = vn_day(t)
    fish = [f for f in d['bag'] if f['i'] in ids and f['s'] in C.SPECIES]
    refused = [f for f in fish if f['od'] == day and f['o'] < 0]
    fish = [f for f in fish if f not in refused]
    need(fish, 'Lái cá không mua mấy con này hôm nay nữa. Mai quay lại nhé!', 'refused')
    ids = [f['i'] for f in fish]
    rng = secrets.SystemRandom()
    haggle = any(f['od'] == day and f['o'] > 0 for f in fish)
    if rng.random() < C.HAGGLE_CHANCE:
        pct = rng.randint(*C.HAGGLE_OFFER)
        for f in fish:
            if not (f['od'] == day and f['o'] > 0):
                f['o'], f['od'] = pct, day
        haggle = True
    note = f' ({len(refused)} con lái không mua hôm nay)' if refused else ''
    if haggle:
        d['deal'] = dict(ids=ids, at=t)
        v = _deal_view(d, ids, day)
        return dict(message=f'🤔 Lái cá trả giá: {fmt(v["offer"])} xu thay vì {fmt(v["full"])} xu.{note}', deal=v)
    total = sum(C.price(f['s'], f['g']) for f in fish)
    _sold(s, d, ids, total, f'🐟 Bán {len(ids)} con cá')
    return dict(message=f'💰 Bán {len(ids)} con: +{fmt(total)} xu.{note}', sold=dict(n=len(ids), xu=total))


def _deal(s, d, p, t):
    need = _core().need
    pick = p.get('pick')
    need(set(p) == {'pick'} and pick in ('accept', 'bargain', 'decline'), 'Chọn bán, trả giá hoặc thôi nhé.')
    deal = d['deal']
    need(isinstance(deal, dict) and deal['at'] + C.DEAL_TTL > t, 'Lái cá đi mất rồi. Bán lại nhé.', 'no_deal')
    day = vn_day(t)
    have = {f['i'] for f in d['bag'] if f['s'] in C.SPECIES}
    ids = [i for i in deal['ids'] if i in have]
    need(ids, 'Cá không còn trong giỏ.', 'gone')
    fish = [f for f in d['bag'] if f['i'] in ids]
    if pick == 'decline':
        d['deal'] = None
        return dict(message='🙅 Thôi không bán. Cá vẫn trong giỏ (lái vẫn trả giá đó hôm nay).')
    if pick == 'accept':
        v = _deal_view(d, ids, day)
        _sold(s, d, ids, v['offer'], f'🐟 Bán {len(ids)} con cá (bị trả giá)')
        return dict(message=f'🤝 Chốt! +{fmt(v["offer"])} xu.', sold=dict(n=len(ids), xu=v['offer']))
    haggled = [f for f in fish if f['od'] == day and f['o'] > 0]
    roll, acc = secrets.SystemRandom().random(), 0.0
    pct = 0
    for share, value in C.BARGAIN:
        acc += share
        if roll < acc:
            pct = value
            break
    if pct == 0:
        for f in haggled:
            f['o'] = -1
        d['deal'] = None
        return dict(message='😤 Lái cá phẩy tay: “Thôi không mua nữa!” Cá vẫn trong giỏ, mai bán tiếp nhé.', bargain='refused')
    total = sum(C.price(f['s'], f['g']) * pct // 100 for f in fish)
    _sold(s, d, ids, total, f'🐟 Bán {len(ids)} con cá (trả giá thành công)')
    msg = (f'🎉 Trả giá khéo quá! Lái mua giá cao hơn: +{fmt(total)} xu.' if pct > 100 else
           f'😎 Trả giá thành công: đủ giá +{fmt(total)} xu.')
    return dict(message=msg, sold=dict(n=len(ids), xu=total), bargain='won')


# ---------------------------------------------------------------- the bag
def _keep(s, d, p, t):
    need = _core().need
    need(set(p) == {'id', 'on'} and type(p.get('on')) is bool, 'Chọn cá nhé.')
    f = _find(d, p.get('id'))
    need(f is not None, 'Cá không còn trong giỏ.', 'gone')
    f['k'] = 1 if p['on'] else 0
    return dict(message='⭐ Đã giữ con này (không bán nhầm).' if p['on'] else 'Đã bỏ giữ.')


def _release(s, d, p, t):
    need = _core().need
    need(set(p) == {'ids'}, 'Chọn cá để thả nhé.')
    ids = _ids(d, p)
    d['bag'] = [f for f in d['bag'] if f['i'] not in ids]
    if d['carry'] in ids:
        d['carry'] = 0
    if d['deal'] and set(d['deal']['ids']) & set(ids):
        d['deal'] = None
    day = vn_day(t)
    if d['rel'][0] != day:
        d['rel'] = [day, 0]
    from . import needs as nd
    n = max(0, min(len(ids), C.RELEASE_SPIRIT - d['rel'][1]))
    d['rel'][1] += n
    got = nd._spirit(s, n) if n else 0
    d['tot']['rel'] = min(LIMIT, d['tot']['rel'] + len(ids))
    return dict(message=f'🌊 Thả {len(ids)} con về nước. Lòng nhẹ tênh!', effects=[f'😊 Tinh thần +{got}'] if got else [])


def _carry(s, d, p, t):
    need = _core().need
    need(set(p) == {'id'} and type(p.get('id')) is int, 'Chọn cá nhé.')
    if p['id'] == 0:
        d['carry'] = 0
        return dict(message='Đã cất cá vào giỏ.')
    f = _find(d, p['id'])
    need(f is not None, 'Cá không còn trong giỏ.', 'gone')
    need(f['s'] in C.SPECIES and _rarity(f['s']) >= C.CARRY_MIN, f'Chỉ cá {C.RARITIES[C.CARRY_MIN]["emoji"]} {C.RARITIES[C.CARRY_MIN]["name"]} trở lên mới mang trên người được.', 'too_small')
    d['carry'] = f['i']
    return dict(message=f'💪 Vác {C.SPECIES[f["s"]]["name"]} {fmt_kg(f["g"])} đi dạo phố!')


def _mount(s, d, p, t):
    """🖼️ Tranh cá: the fish leaves the bag for a wall piece in the furniture bag (game/deco.py places it)."""
    need = _core().need
    need(set(p) == {'id'}, 'Chọn cá nhé.')
    f = _find(d, p.get('id'))
    need(f is not None, 'Cá không còn trong giỏ.', 'gone')
    from . import reno as rn
    blk = rn.ensure_block(s)
    have = {x.get('id') for x in blk['items']}
    d['tro'] = {u: v for u, v in d['tro'].items() if u in have}
    need(len(d['tro']) < TROPHY_MAX, f'Nhà đã có {TROPHY_MAX} tranh cá rồi.', 'full')
    uid = rn.new_uid(blk)
    blk['items'].append(dict(id=uid, k=TROPHY_KIND, r=None, x=None))
    d['tro'][uid] = [f['s'], f['g']]
    d['bag'] = [x for x in d['bag'] if x is not f]
    if d['carry'] == f['i']:
        d['carry'] = 0
    if d['deal'] and f['i'] in d['deal']['ids']:
        d['deal'] = None
    return dict(message='🖼️ Tranh cá đã vào túi đồ trang trí. Mở Trang trí nhà để treo lên tường nhé!')


def _aqua(s, d, p, t):
    """🐠 Bể cá: a fish swims in the home aquarium (deco 'be_ca' draws journey.fish.aq), or comes back to the bag."""
    need = _core().need
    need(len(p) == 1 and set(p) <= {'id', 'out'}, 'Chọn cá nhé.')
    if 'out' in p:
        k = p['out']
        need(type(k) is int and 0 <= k < len(d['aq']), 'Cá không còn trong bể.', 'gone')
        need(len(d['bag']) < cap(d), 'Giỏ đầy rồi.', 'bag_full')
        sp, g = d['aq'].pop(k)
        d['seq'] += 1
        d['bag'].append(dict(i=d['seq'], s=sp, g=g, d=vn_day(t), p=0, k=1, o=0, od=0))
        return dict(message='🧺 Đã vớt cá về giỏ.')
    f = _find(d, p.get('id'))
    need(f is not None, 'Cá không còn trong giỏ.', 'gone')
    need(len(d['aq']) < C.AQUARIUM_MAX, f'Bể cá đã đủ {C.AQUARIUM_MAX} con.', 'full')
    d['aq'].append([f['s'], f['g']])
    d['bag'] = [x for x in d['bag'] if x is not f]
    if d['carry'] == f['i']:
        d['carry'] = 0
    if d['deal'] and f['i'] in d['deal']['ids']:
        d['deal'] = None
    return dict(message=f'🐠 {C.SPECIES[f["s"]]["name"]} đã vào bể cá trong nhà.')


# ---------------------------------------------------------------- PostgreSQL (game/storage.py, in the save's transaction)
def command_commit(db, sid: str, action: str, after, result=None) -> None:
    """A 🏝️ island cast must come from a player on that trip now (else the whole command rolls back); a catch updates
    the boards and records (game/fish_lb.py), a 🔴 Cổ đại one the town ticker."""
    if not action.startswith('jr_fish_') or not isinstance(after, dict) or not isinstance(after.get('journey'), dict):
        return
    d = get(after)
    if d is None:
        return
    need = _core().need
    if action == 'jr_fish_cast':
        a = d['act']
        if a and C.SPOTS[a['spot']].get('island'):
            from . import island_trips as it
            row = db.execute(it.ACCESS_SQL, (sid, a['trip'])).fetchone()
            need(it.access_for(row, sid, now()), 'Bạn không ở trên hòn đảo này.', 'no_island')
        return
    land = (result or {}).get('land') if isinstance(result, dict) else None
    if action != 'jr_fish_land' or not isinstance(land, dict) or land.get('res') != 'fish' or result.get('duplicate'):
        return
    from . import fish_lb
    fish_lb.on_catch(db, sid, after, land['catch'], result)


# ---------------------------------------------------------------- saves
SP_RE = re.compile(r'[a-z][a-z0-9_]{0,31}')
BAG_MAX = 1000


def _int(v, lo, hi) -> bool:
    return type(v) is int and lo <= v <= hi


def _num(v, lo, hi) -> bool:
    return type(v) in (int, float) and math.isfinite(v) and lo <= v <= hi


def _sp(v) -> bool:
    return isinstance(v, str) and SP_RE.fullmatch(v) is not None


def _fish_ok(f) -> bool:
    return (isinstance(f, dict) and FISH_KEYS <= set(f) and _int(f['i'], 1, LIMIT) and _sp(f['s']) and _int(f['g'], 1, 10**8)
            and _int(f['d'], 0, 10**7) and _int(f['p'], 0, 15) and f['k'] in (0, 1) and type(f['k']) is int
            and _int(f['o'], -1, 200) and _int(f['od'], 0, 10**7))


def _act_ok(a) -> bool:
    if a is None:
        return True
    return (isinstance(a, dict) and ACT_KEYS <= set(a) and isinstance(a['id'], str) and TOKEN.fullmatch(a['id']) is not None
            and _num(a['at'], 0, 1e11) and a['spot'] in C.SPOTS and isinstance(a['trip'], str)
            and (a['trip'] == '' or TRIP_RE.fullmatch(a['trip']) is not None) and _sp(a['rod']) and _num(a['dist'], 0, 10**4)
            and _int(a['zone'], 0, len(C.ZONES) - 1) and a['kind'] in ('none', 'junk', 'fish') and isinstance(a['sp'], str)
            and _int(a['g'], 0, 10**8) and all(_num(a[k], 0, 1e11) for k in ('bite', 'hook')) and _num(a['reel'], 0, 600)
            and a['snap'] in (0, 1) and isinstance(a['nib'], list) and len(a['nib']) <= 8 and all(_num(x, 0, 1e11) for x in a['nib']))


def _ok(d) -> bool:
    """The block as this build reads it. Lenient where a newer build may add (keys, species, rods, baits, baskets): a
    rollback never breaks a save that holds them."""
    if not (isinstance(d, dict) and KEYS <= set(d) and d['v'] == VERSION and _int(d['seq'], 0, LIMIT)):
        return False
    bag = d['bag']
    if not (isinstance(bag, list) and len(bag) <= BAG_MAX and all(_fish_ok(f) for f in bag)):
        return False
    uids = [f['i'] for f in bag]
    if len(set(uids)) != len(uids) or any(u > d['seq'] for u in uids):
        return False
    rods = d['rods']
    if not (isinstance(rods, list) and 1 <= len(rods) <= 32 and 'tre' in rods and len(set(rods)) == len(rods)
            and all(_sp(r) for r in rods) and d['rod'] in rods):
        return False
    b = d['bait']
    if not (isinstance(b, dict) and len(b) <= 32 and all(_sp(k) and _int(v, 1, C.BAIT_MAX) for k, v in b.items())
            and isinstance(d['use'], str) and (d['use'] == '' or d['use'] in b) and _int(d['gio'], 0, 15)):
        return False
    dex = d['dex']
    if not (isinstance(dex, dict) and len(dex) <= 2000 and all(
            _sp(k) and isinstance(v, list) and len(v) == 3 and _int(v[0], 0, LIMIT) and _int(v[1], 0, 10**8) and _int(v[2], 0, 2**16)
            for k, v in dex.items())):
        return False
    tot = d['tot']
    if not (isinstance(tot, dict) and set(TOT_KEYS) <= set(tot) and all(_int(v, 0, LIMIT) for v in tot.values())):
        return False
    ms = d['ms']
    if not (isinstance(ms, list) and len(ms) <= 64 and len(set(ms)) == len(ms) and all(isinstance(x, str) and len(x) <= 24 for x in ms)):
        return False
    if not (_int(d['carry'], 0, LIMIT) and (d['carry'] == 0 or d['carry'] in uids)):
        return False
    aq = d['aq']
    if not (isinstance(aq, list) and len(aq) <= C.AQUARIUM_MAX and all(
            isinstance(x, list) and len(x) == 2 and _sp(x[0]) and _int(x[1], 1, 10**8) for x in aq)):
        return False
    tro = d['tro']
    if not (isinstance(tro, dict) and len(tro) <= TROPHY_MAX and all(
            isinstance(u, str) and UID_RE.fullmatch(u) and isinstance(v, list) and len(v) == 2 and _sp(v[0]) and _int(v[1], 1, 10**8)
            for u, v in tro.items())):
        return False
    if not _act_ok(d['act']):
        return False
    rc = d['rc']
    if not (isinstance(rc, list) and len(rc) <= MAX_RECEIPTS and all(
            isinstance(x, dict) and set(x) == {'id', 'res'} and isinstance(x['id'], str) and TOKEN.fullmatch(x['id'])
            and isinstance(x['res'], str) and len(x['res']) <= 12 for x in rc)):
        return False
    deal = d['deal']
    if deal is not None and not (isinstance(deal, dict) and set(deal) == {'ids', 'at'} and isinstance(deal['ids'], list)
                                 and 1 <= len(deal['ids']) <= SELL_MAX and all(_int(i, 1, LIMIT) for i in deal['ids'])
                                 and _num(deal['at'], 0, 1e11)):
        return False
    rel = d['rel']
    return (isinstance(rel, list) and len(rel) == 2 and _int(rel[0], 0, 10**7) and _int(rel[1], 0, 100) and d['mig'] in (0, 1)
            and type(d['mig']) is int)


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'fish' not in j:
        return
    _core().need(_ok(j['fish']), 'Dữ liệu câu cá không hợp lệ.', 'invalid_save')


def upgrade(j: dict) -> None:
    """Heal what a save can lose without losing a fish, a rod or a coin: an open round or an offer that no longer
    parses is dropped (a round lives minutes); the rest stays for validate()."""
    d = j.get('fish') if isinstance(j, dict) else None
    if not isinstance(d, dict):
        return
    if 'act' in d and not _act_ok(d['act']):
        d['act'] = None
    if 'deal' in d and d['deal'] is not None and not (isinstance(d['deal'], dict) and set(d['deal']) == {'ids', 'at'}):
        d['deal'] = None
