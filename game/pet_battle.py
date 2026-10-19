"""⚔️ Pet battles (owner 19/10: "thêm thi đua nữa nhé, kết hợp với pet ra tranh đấu với bang nữa"): the engine.

Server-authoritative and deterministic: `battle(a, b, seed)` plays two lineups of fighters (1…5 pets each, a relay:
the front pets fight, a fainted one is replaced by the next, the winner keeps the HP it has left) from a seed and
returns the whole log. The same seed and lineups always give the same log (its own small PRNG, integers only), so a
replay is the same fight and the page only animates what the server decided. Nothing here reads or writes a save:
a battle never touches a pet (no injury, no gear lost, no hunger); the fighters are snapshots (`fighter`).

Fighters come from the pets' real numbers (game/pet_tiers.py): the five stats (⚡ Tốc độ, 💪 Sức bền, 🧠 Thông minh,
💖 Đáng yêu, 🍀 May mắn) already hold the rank's range, the potential, the breed's lean, training and the gear worn.
They become battle numbers (derive):
    HP   = 300 + 1.2·sức bền + 0.4·đáng yêu          ATK = 90 + 0.20·thông minh + 0.12·tốc độ + 0.05·sức bền
    DEF  = 50 + 0.15·sức bền + 0.05·thông minh       SPD = 100 + 0.2·tốc độ (who acts more often)
    a hit = ATK·K/(K+DEF) · ±SPREAD % · element · crit (🍀) · charm (💖 of the one hit) · skill
Base constants damp the stats so a higher rank or better gear wins most fights, never all of them (tests/
test_pet_arena.py Balance simulates thousands of 1-vs-1 fights of random pets: one rank up wins ~74 %, two ranks ~89 %,
a full kit of gear of its rank ~78 %, that kit at +10 against it at +0 ~77 %, +10 training on every stat ~68 %, the
element that beats the other ~62 % (the others ~50 %), dogs against cats 50 %, ~10 actions a 1-vs-1).

🌗 Ngũ hành: each breed has an element from the stat it leans to (pets_content `st`; a few fixed: ELEMENT_OF):
⚡→🔥 Hỏa, 💪→⛰️ Thổ, 🧠→💧 Thủy, 💖→🌿 Mộc, 🍀→🪙 Kim; tương khắc (BEATS) Kim→Mộc→Thổ→Thủy→Hỏa→Kim: ×ADV dealt
to the one it beats, ×DISADV the other way. Each element has one skill, cast when its energy is full (🧠 fills it
faster): ☄️ Cầu lửa (big hit through defence), 🪨 Khiên đá (a shield + a hit), 🌊 Sóng nước (a hit that heals),
🍃 Dây leo (a hit; the target's next blow is weaker), ✨ Móng vàng (a sure critical). Dogs may stand once on 1 HP
(🐶 Trung thành), cats dodge a little more (🐱 Nhanh nhẹn); legendaries and thần thú hit a little harder (🌟 Thần uy).
`ENGINE` names this rule set: a stored match keeps it, a later change of numbers bumps it (an old replay then shows
its stored result only).
"""
from __future__ import annotations

import hashlib

ENGINE = 1
MASK = (1 << 64) - 1

# ---------------------------------------------------------------- numbers (tests/test_pet_arena.py Balance)
HP0, HP_STA, HP_CUTE = 300, 120, 40           # HP = HP0 + (HP_STA·sức bền + HP_CUTE·đáng yêu) / 100
ATK0, ATK_INT, ATK_SPD, ATK_STA = 90, 20, 12, 5    # per 100 of the stat
DEF0, DEF_STA, DEF_INT = 50, 15, 5
SPD0, SPD_SPD, K = 100, 20, 120
SPREAD = 35                        # ± % on each blow
CRIT_BP, CRIT_LUCK, CRIT_MAX, CRIT_X = 1000, 7, 2600, 190         # per 10 000: 10 % + 0.07 % a point of luck; ×1.90
DODGE_BP, DODGE_LUCK, DODGE_SPD, DODGE_MAX = 400, 3, 6, 1800      # 4 % + luck + speed lead
CAT_DODGE = 350                    # 🐱 +3.5 %
CHARM_BP, CHARM_CUTE, CHARM_MAX = 200, 5, 1200                    # 💖 the one hit charms the attacker: half damage
ENERGY0, ENERGY_INT, ENERGY_HIT, ENERGY_FULL = 22, 12, 8, 100     # per action: 22 + thông minh/12; +8 when hit
ADV, DISADV = 107, 95              # % element vs element
LEGEND_X = 106                     # 🌟 Thần uy
DOG_ENDURE = 2500                  # 🐶 once a battle: a blow that would KO leaves 1 HP (per 10 000)
MAX_ACTIONS = 160                  # then the side with more HP left (share of max, the pets to come count full) wins
SKILL_X = dict(hoa=155, tho=110, thuy=125, moc=125, kim=105)      # % of a blow
FIRE_PIERCE = 40                   # ☄️ ignores 40 % of the defence
SHIELD_PCT = 15                    # 🪨 % of max HP
HEAL_PCT = 45                      # 🌊 % of the damage dealt
ROOT_PCT = 45                      # 🍃 the target's next blow −45 %
TICK = 1_000_000                   # time units: a pet acts every TICK // SPD

STAT_IDS = ('spd', 'sta', 'int', 'cute', 'luck')
ELEMENTS = (('hoa', '🔥', 'Hỏa'), ('tho', '⛰️', 'Thổ'), ('thuy', '💧', 'Thủy'), ('moc', '🌿', 'Mộc'), ('kim', '🪙', 'Kim'))
ELEMENT_IDS = tuple(e[0] for e in ELEMENTS)
LEAN_ELEMENT = dict(zip(STAT_IDS, ('hoa', 'tho', 'thuy', 'moc', 'kim')))
BEATS = dict(kim='moc', moc='tho', tho='thuy', thuy='hoa', hoa='kim')
ELEMENT_OF = dict(linh_khuyen='kim', than_tai='kim', rong_con='hoa', khung_long='hoa', ky_lan='hoa', ky_lan_sung='moc',
                  cho_ta='tho', meo_muop='hoa', tam_the='kim', meo_mun='thuy')
SKILLS = dict(hoa=('☄️', 'Cầu lửa'), tho=('🪨', 'Khiên đá'), thuy=('🌊', 'Sóng nước'), moc=('🍃', 'Dây leo'), kim=('✨', 'Móng vàng'))
PASSIVES = dict(dog=('🐶', 'Trung thành'), cat=('🐱', 'Nhanh nhẹn'), legend=('🌟', 'Thần uy'))


# ---------------------------------------------------------------- the seeded PRNG (splitmix64: integers only)
class Rng:
    def __init__(self, seed: int):
        self.x = int(seed) & MASK

    def next(self) -> int:
        self.x = (self.x + 0x9E3779B97F4A7C15) & MASK
        z = self.x
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, n: int) -> int:
        return self.next() % max(1, int(n))

    def bp(self, p: int) -> bool:
        """True with probability p / 10 000."""
        return self.below(10000) < p

    def shuffle(self, rows: list) -> list:
        out = list(rows)
        for i in range(len(out) - 1, 0, -1):
            j = self.below(i + 1)
            out[i], out[j] = out[j], out[i]
        return out


def seed_of(match_id: str, salt: str = '') -> int:
    """A 64-bit seed from a match id (the replay of a match is its id)."""
    return int.from_bytes(hashlib.sha256(f'pcc-pet-battle|{match_id}|{salt}'.encode()).digest()[:8], 'big')


# ---------------------------------------------------------------- fighters
def element_of(breed: str, lean=None) -> str:
    if breed in ELEMENT_OF:
        return ELEMENT_OF[breed]
    if lean is None:
        from . import pets_content as C
        lean = (C.BREEDS.get(breed) or {}).get('st') or (0,) * 5
    lean = list(lean)[:5] + [0] * max(0, 5 - len(lean))
    best = max(range(5), key=lambda i: (lean[i], -i))
    return LEAN_ELEMENT[STAT_IDS[best]]


def derive(f: dict) -> dict:
    """Battle numbers of a fighter snapshot: {hp, atk, df, sp, crit, dodge, charm, gain} (integers)."""
    st = [max(1, int(v)) for v in (list(f.get('s') or [])[:5] + [1] * 5)[:5]]
    bonus = max(0, min(10, int(f.get('tb') or 0)))     # % (a team's training ground: game/pet_war.py)
    if bonus:
        st = [v + v * bonus // 100 for v in st]
    spd, sta, intl, cute, luck = st
    dodge = DODGE_BP + DODGE_LUCK * luck + (CAT_DODGE if f.get('k') == 'cat' else 0)
    return dict(hp=HP0 + (HP_STA * sta + HP_CUTE * cute) // 100, atk=ATK0 + (ATK_INT * intl + ATK_SPD * spd + ATK_STA * sta) // 100,
                df=DEF0 + (DEF_STA * sta + DEF_INT * intl) // 100, sp=SPD0 + SPD_SPD * spd // 100,
                crit=min(CRIT_MAX, CRIT_BP + CRIT_LUCK * luck), dodge=dodge, spd=spd,
                charm=min(CHARM_MAX, CHARM_BP + CHARM_CUTE * cute), gain=ENERGY0 + intl // 12)


def clean(f) -> dict | None:
    """A fighter snapshot checked (a stored one, an older shape): None when it cannot fight."""
    if not isinstance(f, dict):
        return None
    s = f.get('s')
    if not isinstance(s, list) or len(s) != 5 or not all(type(v) is int and 0 <= v <= 5000 for v in s):
        return None
    out = dict(f)
    out['e'] = f.get('e') if f.get('e') in ELEMENT_IDS else element_of(str(f.get('b') or ''))
    out['k'] = f.get('k') if f.get('k') in ('dog', 'cat') else 'dog'
    out['n'] = str(f.get('n') or 'Bé')[:24]
    return out


# ---------------------------------------------------------------- the battle
class _Pet:
    __slots__ = ('f', 'd', 'hp', 'max', 'en', 'sh', 'root', 'endured', 't', 'i')

    def __init__(self, f: dict, i: int):
        self.f, self.i = f, i
        self.d = derive(f)
        self.hp = self.max = self.d['hp']
        self.en = self.sh = self.root = 0
        self.endured = False
        self.t = 0


def _blow(rng: Rng, att: _Pet, tgt: _Pet, mult: int, pierce: int = 0, sure_crit: bool = False) -> tuple:
    """(damage, crit, charmed) of one blow of `att` on `tgt` (before the shield)."""
    a, d = att.d, tgt.d
    df = d['df'] * (100 - pierce) // 100
    dmg = a['atk'] * K // (K + df)
    dmg = dmg * (100 - SPREAD + rng.below(2 * SPREAD + 1)) // 100
    ea, et = att.f['e'], tgt.f['e']
    if BEATS.get(ea) == et:
        dmg = dmg * ADV // 100
    elif BEATS.get(et) == ea:
        dmg = dmg * DISADV // 100
    if att.f.get('L'):
        dmg = dmg * LEGEND_X // 100
    dmg = dmg * mult // 100
    crit = sure_crit or rng.bp(a['crit'])
    if crit:
        dmg = dmg * CRIT_X // 100
    charmed = rng.bp(d['charm'])
    if charmed:
        dmg = dmg // 2
    if att.root:
        dmg = dmg * (100 - ROOT_PCT) // 100
        att.root = 0
    return max(1, dmg), crit, charmed


def _hurt(rng: Rng, tgt: _Pet, dmg: int, ev: dict) -> None:
    if tgt.sh:
        took = min(tgt.sh, dmg)
        tgt.sh -= took
        dmg -= took
        if took:
            ev['ab'] = took
    if dmg >= tgt.hp and tgt.f.get('k') == 'dog' and not tgt.endured and tgt.hp > 1 and rng.bp(DOG_ENDURE):
        tgt.endured = True
        dmg = tgt.hp - 1
        ev['e'] = 1
    tgt.hp = max(0, tgt.hp - dmg)
    tgt.en = min(ENERGY_FULL, tgt.en + ENERGY_HIT)
    ev['d'] = dmg
    ev['h'] = tgt.hp


def battle(side_a: list, side_b: list, seed: int, max_actions: int = MAX_ACTIONS) -> dict:
    """Play lineup `side_a` against `side_b` (fighter snapshots, front first). Returns
    {w: 0 | 1 | 2 (a, b, draw), ev: [events], left: [pets standing a, b], hp: [[hp of each pet], [..]], max: [[..], [..]],
    sc: [score a, score b] (HP share ×1000, the tie-break), n: actions}.
    Events: {k:'in', s, i} a pet steps in · {k:'hit'|'sk', s (the attacker's side), d damage, h the target's HP after,
    c crit, x charmed (half), ab absorbed by a shield, e endured on 1 HP, n skill element, sh shield got, he heal, hs
    its HP after} · {k:'miss', s} · {k:'ko', s, i} · {k:'end', w}."""
    rng = Rng(seed)
    sides = [[_Pet(f, i) for i, f in enumerate(x for x in (clean(y) for y in side_a) if x)][:5],
             [_Pet(f, i) for i, f in enumerate(x for x in (clean(y) for y in side_b) if x)][:5]]
    ev: list = []
    front = [0, 0]
    now = 0

    def enter(s):
        p = sides[s][front[s]]
        p.t = now + (TICK // p.d['sp']) // 2 + rng.below(TICK // p.d['sp'] // 4 + 1)
        ev.append(dict(k='in', s=s, i=p.i))

    for s in (0, 1):
        if sides[s]:
            enter(s)
    actions = 0
    while all(front[s] < len(sides[s]) for s in (0, 1)) and actions < max_actions:
        pa, pb = sides[0][front[0]], sides[1][front[1]]
        s = 0 if (pa.t, -pa.d['sp']) <= (pb.t, -pb.d['sp']) else 1
        att, tgt = (pa, pb) if s == 0 else (pb, pa)
        now = att.t
        att.t += TICK // att.d['sp']
        actions += 1
        att.en = min(ENERGY_FULL, att.en + att.d['gain'])
        if att.en >= ENERGY_FULL:
            att.en = 0
            el = att.f['e']
            e = dict(k='sk', s=s, n=el)
            if el == 'hoa':
                dmg, crit, ch = _blow(rng, att, tgt, SKILL_X['hoa'], pierce=FIRE_PIERCE)
            elif el == 'kim':
                dmg, crit, ch = _blow(rng, att, tgt, SKILL_X['kim'], sure_crit=True)
            else:
                dmg, crit, ch = _blow(rng, att, tgt, SKILL_X[el])
            if crit:
                e['c'] = 1
            if ch:
                e['x'] = 1
            _hurt(rng, tgt, dmg, e)
            if el == 'tho':
                att.sh += att.max * SHIELD_PCT // 100
                e['sh'] = att.sh
            elif el == 'thuy':
                heal = min(att.max - att.hp, e['d'] * HEAL_PCT // 100)
                att.hp += heal
                e['he'], e['hs'] = heal, att.hp
            elif el == 'moc':
                tgt.root = 1
            ev.append(e)
        else:
            dodge = tgt.d['dodge'] + max(0, tgt.d['spd'] - att.d['spd']) * DODGE_SPD
            if rng.bp(min(DODGE_MAX, dodge)):
                ev.append(dict(k='miss', s=s))
                continue
            dmg, crit, ch = _blow(rng, att, tgt, 100)
            e = dict(k='hit', s=s)
            if crit:
                e['c'] = 1
            if ch:
                e['x'] = 1
            _hurt(rng, tgt, dmg, e)
            ev.append(e)
        if tgt.hp <= 0:
            t = 1 - s
            ev.append(dict(k='ko', s=t, i=tgt.i))
            front[t] += 1
            if front[t] < len(sides[t]):
                enter(t)
    hp = [[p.hp for p in sides[s]] for s in (0, 1)]
    mx = [[p.max for p in sides[s]] for s in (0, 1)]
    left = [sum(1 for p in sides[s] if p.hp > 0) for s in (0, 1)]
    sc = [sum(p.hp * 1000 // p.max for p in sides[s]) for s in (0, 1)]
    if left[0] and not left[1]:
        w = 0
    elif left[1] and not left[0]:
        w = 1
    elif not left[0] and not left[1]:
        w = 2
    else:   # the clock ran out: more HP left (shares) wins
        w = 0 if sc[0] > sc[1] else 1 if sc[1] > sc[0] else 2
    ev.append(dict(k='end', w=w))
    return dict(w=w, ev=ev, left=left, hp=hp, max=mx, sc=sc, n=actions)


def preview(f: dict) -> dict:
    """What the page shows of a fighter: its battle numbers, element, skill and passive."""
    f = clean(f) or {}
    if not f:
        return {}
    d = derive(f)
    el = f['e']
    passive = 'legend' if f.get('L') else f['k']
    return dict(hp=d['hp'], atk=d['atk'], df=d['df'], sp=d['sp'], e=el, sk=list(SKILLS[el]), ps=list(PASSIVES[passive]))


def catalogue() -> dict:
    return dict(engine=ENGINE, elements=[dict(id=a, emoji=b, name=c, beats=BEATS[a], skill=list(SKILLS[a])) for a, b, c in ELEMENTS],
                passives={k: list(v) for k, v in PASSIVES.items()})
