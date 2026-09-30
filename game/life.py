"""Chuyện đời thường & tình làng nghĩa xóm: a journey-level layer of everyday life.

Hard days happen often (bị ăn hiếp chỗ làm, phụ huynh làm khó, khách chửi, bị lừa,
thất tình, chuyện xui, bị đặt điều). They cost spirit and sometimes money. Then the
neighbours come round by name: a pot of chè, bia hơi on Anh Khoa, karaoke with the
workmates, and after a scam the whole xóm chips in. You can blow off steam (costs
money or not) and help a neighbour in trouble in return.

* State: `s['journey']['life']` (see initial()). Added by migrate(); validate() and
  public() tolerate its absence.
* Spirit (tinh thần) 0–100, starts at 70. Hard days lower it; days pass and outings
  raise it. Below 35 impulse buys can happen, below 15 a sick day (medicine money).
  Low spirit makes hard days rarer and neighbours more likely: no death spiral.
* Bonds with each neighbour of the journey CAST (0–100); their mean is the street's
  warmth (tình làng nghĩa xóm). Warmer neighbours give more when they chip in.
* A card (`pending`) walks through stages: react → (gop | comfort) → (cope) → done.
  Undecided cards take their default when the next life day closes.
* Money moves only through journey._wallet with the history kind 'life'. Forced losses
  are capped by what the wallet holds and paid choices need the money: life never
  pushes the wallet below zero.
* Deterministic from `journey.seed` and the life day. Story mode only.

Commands (engine routes the `lf_` prefix): lf_choose {id, choice}, lf_cope {choice},
lf_close {id}. Design: docs/superpowers/specs/2026-09-29-life-design.md
"""
from __future__ import annotations

import copy
import random

from .life_content import (ASK, CATS, COMFORT, COPE, COPE_INDEX, FACTS, FRIENDS, GIFTS, GOSSIPS, HARD, IMPULSE,
                           JOYS, SICK, TOKENS, WORK)
from . import archive as ar

VERSION = 1
KIND = 'life'                 # journey wallet history kind
START_SPIRIT = 70
BOND_START = 50
LOG_MAX = 40
RECENT = 10                   # no identical variant within this many life days
COMFORT_RECENT = 5
QUEUE_MAX = 4
SEEN_MAX = 30
FIRST_DAY = 3                 # nothing before the third life day
CALM_UNTIL = 5                # days 3–5: gentler, mild variants only
HARD_P = (.18, .36)           # early, later
RUMOUR_P = .3
RUMOUR_GAP = 5
ASK_P = .13
JOY_P = .16
INVITE_P = .6
IMPULSE_SPIRIT, IMPULSE_P = 35, .35
SICK_SPIRIT, SICK_P = 15, .5
LOW_SPIRIT = 30
HIT_SCALE = 1.6               # authored hits are gentle numbers; a hard day should really sting
COMFORT_SCALE = .7
DOCTOR = 20
HANGOVER = 6
MOODS = ((80, '😄', 'Phơi phới'), (60, '🙂', 'Ổn áp'), (40, '😐', 'Hơi mệt'), (20, '😔', 'Buồn'), (0, '😢', 'Kiệt sức'))
WARMTH_NAMES = ((75, 'Thương nhau như ruột thịt'), (60, 'Tối lửa tắt đèn có nhau'), (45, 'Hàng xóm quen'), (0, 'Còn hơi lạ'))
SAFE = ('no', 'skip', 'none', 'clear', 'rest', 'thanks', 'hand', 'ok')
KINDS = ('hard', 'scam', 'ask', 'joy', 'impulse', 'sick', 'invite', 'cope')
STAGES = ('react', 'gop', 'comfort', 'cope', 'ask', 'joy', 'impulse', 'sick', 'done')
STATS = ('hard', 'warm', 'outings', 'given', 'received', 'spent', 'scams', 'rumours', 'coped')
LOG_KEYS = {'id', 'day', 'kind', 'cat', 'title', 'emoji', 'who', 'text', 'spirit', 'money', 'fact', 'gossip'}
CARD_KEYS = {'id', 'day', 'kind', 'ref', 'cat', 'stage', 'career', 'who', 'loss', 'hit', 'comfort', 'gop', 'fact',
             'gossip', 'trail', 'spirit', 'money', 'src'}

HARD_INDEX = {x['id']: x for x in HARD}
COMFORT_INDEX = {x['id']: x for x in COMFORT}
ASK_INDEX = {x['id']: x for x in ASK}
JOY_INDEX = {x['id']: x for x in JOYS}
IMPULSE_INDEX = {x['id']: x for x in IMPULSE}
SICK_INDEX = {x['id']: x for x in SICK}
EXTERNAL = {'incident': ('📵', 'Bị lừa mất tiền'), 'invest': ('🕳️', 'Dự án “lãi khủng” biến mất')}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _cast() -> dict:
    return _jr().CAST


def _people() -> dict:
    """Everyone a card may name: the journey cast, the gossips, the workmates and friends."""
    out = {k: dict(v) for k, v in _cast().items()}
    out.update({k: dict(v) for k, v in GOSSIPS.items()})
    out['friends'] = dict(FRIENDS)
    out['work'] = dict(name='Đồng nghiệp', emoji='🧑‍🤝‍🧑', role='Chỗ làm')
    return out


def _story(s: dict) -> bool:
    return bool((s.get('journey') or {}).get('story'))


def _gender(s: dict) -> str:
    g = (s.get('journey') or {}).get('gender')
    return g if g in ('male', 'female') else 'none'


def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


def _rng(s: dict, *parts) -> random.Random:
    return random.Random('|'.join(['life', str((s.get('journey') or {}).get('seed', 0))] + [str(p) for p in parts]))


def mood(spirit: int) -> dict:
    low, emoji, label = next(m for m in MOODS if spirit >= m[0])
    return dict(emoji=emoji, label=label)


def warmth(L: dict) -> int:
    b = [int(v) for v in L['bonds'].values()]
    return round(sum(b) / len(b)) if b else BOND_START


def warmth_name(w: int) -> str:
    return next(name for low, name in WARMTH_NAMES if w >= low)


def _place(cid: str | None) -> str:
    from .content import CAREER_META
    return CAREER_META.get(cid, {}).get('place', 'chỗ làm') if cid else 'chỗ làm'


def _who_view(who: str | None, career: str | None = None) -> dict | None:
    if not who:
        return None
    if who == 'work':
        name, emoji = WORK.get(career or '', ('Đồng nghiệp', '🧑‍🤝‍🧑'))
        return dict(id='work', name=name, emoji=emoji, role=_place(career))
    p = _people().get(who)
    return dict(id=who, name=p['name'], emoji=p['emoji'], role=p.get('role', '')) if p else None


def _fill(text, s: dict, card: dict | None = None) -> str:
    g = _gender(s)
    if isinstance(text, dict):
        text = text.get(g) or text['none']
    for k, v in TOKENS.items():
        text = text.replace('{' + k + '}', v[g])
    career = (card or {}).get('career')
    text = text.replace('{place}', _place(career))
    text = text.replace('{mate}', WORK.get(career or '', ('đồng nghiệp', ''))[0])
    gossip = (card or {}).get('gossip')
    text = text.replace('{gossip}', GOSSIPS[gossip]['name'] if gossip in GOSSIPS else 'Người đầu hẻm')
    names = [w for w in (card or {}).get('who', []) if w not in GOSSIPS]
    first = _who_view(names[0], career) if names else None
    text = text.replace('{who_name}', first['name'] if first else 'một người quen')
    return text


# ---------------------------------------------------------------- state
def initial(day: int = 1) -> dict:
    return dict(version=VERSION, day=int(day), spirit=START_SPIRIT, mark=START_SPIRIT,
                bonds={cid: BOND_START for cid in _cast()}, pending=None, seq=0, log=[], recent={}, queue=[],
                seen=[], iv_lost=0, hangover=0, coped=0, outing=None, rumour=0, stats={k: 0 for k in STATS})


def migrate(s: dict) -> dict:
    """Adds `s['journey']['life']` (setdefault only, no retro events). Call after invest.migrate."""
    j = s.get('journey')
    if not isinstance(j, dict):
        return s
    base = initial(int(j.get('life_day', 1)))
    # No retro follow-ups: scams lost before this layer existed are already "seen".
    base['iv_lost'] = int(((j.get('invest') or {}).get('stats') or {}).get('lost', 0))
    base['seen'] = [f'{cid}:{c["incidents"]["last"]["id"]}' for cid, c in (s.get('careers') or {}).items()
                    if isinstance(c, dict) and isinstance(c.get('incidents'), dict) and isinstance(c['incidents'].get('last'), dict)
                    and c['incidents']['last'].get('id')][-SEEN_MAX:]
    L = j.setdefault('life', base)
    if isinstance(L, dict):
        for k, v in base.items():
            L.setdefault(k, copy.deepcopy(v))
        if isinstance(L['bonds'], dict):
            for k in _cast():
                L['bonds'].setdefault(k, BOND_START)
        if isinstance(L['stats'], dict):
            for k in STATS:
                L['stats'].setdefault(k, 0)
    return s


def _state(s: dict) -> dict:
    j = s['journey']
    if 'life' not in j:
        migrate(s)
    return j['life']


def _spirit(L: dict, delta: int) -> int:
    before = L['spirit']
    L['spirit'] = _clamp(before + delta)
    return L['spirit'] - before


def _bond(L: dict, who: str | None, delta: int) -> None:
    if who in L['bonds'] and delta:
        L['bonds'][who] = _clamp(L['bonds'][who] + delta)


def _wallet(s: dict, amount: int, label: str) -> int:
    """Move money through the journey wallet. A loss never takes more than the wallet holds."""
    j = s['journey']
    if amount < 0:
        amount = -min(-amount, max(0, j['wallet']))
    if amount:
        _jr()._wallet(j, amount, KIND, label[:120])
    return amount


def _log(s: dict, L: dict, card: dict, text: str, choice: str | None = None) -> dict:
    row = dict(id=card['id'], day=card['day'], kind=card['kind'], cat=card['cat'], title=_title(s, card)[:80],
               emoji=_emoji(card), who=list(card['who'])[:8], text=text[:160], spirit=card['spirit'],
               money=card['money'], fact=card.get('fact'), gossip=card.get('gossip'))
    L['log'] = ar.last(L['log'] + [row], LOG_MAX, 'life.log', ar.JOURNEY)
    _tell_board(s, row, card, choice)
    return row


def react_choice(s: dict, card: dict) -> str | None:
    """The id of the first (react-stage) choice taken on a hard-day card, from its trail."""
    x = HARD_INDEX.get(card.get('ref')) if card.get('kind') == 'hard' else None
    if not x or not card.get('trail'):
        return None
    return next((c['id'] for c in x['choices'] if _fill(c['text'], s, card) == card['trail'][0]), None)


def _tell_board(s: dict, row: dict, card: dict, choice: str | None) -> None:
    """Nhóm Cư Dân Phố reacts to the row (game/board.on_life_log): scams, heartbreak, rumours,
    neighbours in trouble, joys. Guarded: the board never breaks a life action."""
    try:
        from . import board
    except ImportError:
        return
    fn = getattr(board, 'on_life_log', None)
    if not callable(fn):
        return
    j = s['journey']
    before = copy.deepcopy(j.get('board'))
    try:
        fn(s, dict(row), copy.deepcopy(card), choice, react_choice(s, card))
    except Exception:  # keep the life layer whole; the board simply stays as it was
        if before is not None:
            j['board'] = before


def _new_card(L: dict, day: int, kind: str, ref: str, cat: str, stage: str, career: str | None, **kw) -> dict:
    L['seq'] += 1
    card = dict(id=f'lf-{L["seq"]}', day=int(day), kind=kind, ref=ref, cat=cat, stage=stage, career=career, who=[],
                loss=0, hit=0, comfort=None, gop=None, fact=None, gossip=None, trail=[], spirit=0, money=0, src=None)
    card.update(kw)
    return card


# ---------------------------------------------------------------- content lookups
def _content(card: dict) -> dict:
    k, ref = card['kind'], card['ref']
    return {'hard': HARD_INDEX, 'ask': ASK_INDEX, 'joy': JOY_INDEX, 'impulse': IMPULSE_INDEX,
            'sick': SICK_INDEX}.get(k, {}).get(ref, {})


def _title(s: dict, card: dict) -> str:
    x = _content(card)
    if x.get('title'):
        return _fill(x['title'], s, card)
    if card['kind'] == 'scam':
        return EXTERNAL.get(card['src'], EXTERNAL['incident'])[1]
    if card['kind'] == 'invite':
        k = COMFORT_INDEX.get(card['comfort'])
        who = _who_view(k['who'], card['career']) if k else None
        return f'{who["name"]} rủ đi chơi' if who else 'Hàng xóm rủ đi chơi'
    if card['kind'] == 'cope':
        c = COPE_INDEX.get(card['ref'])
        return c['label'] if c else 'Xả stress'
    return CATS.get(card['cat'], ('', 'Chuyện đời thường'))[1]


def _emoji(card: dict) -> str:
    x = _content(card)
    if x.get('emoji'):
        return x['emoji']
    if card['kind'] == 'scam':
        return EXTERNAL.get(card['src'], EXTERNAL['incident'])[0]
    if card['kind'] == 'cope':
        return COPE_INDEX.get(card['ref'], {}).get('emoji', '🌿')
    return CATS.get(card['cat'], ('🌿', ''))[0]


# ---------------------------------------------------------------- choices per stage
def _opt(cid: str, label: str, spirit: int = 0, money: int = 0, **kw) -> dict:
    return dict(id=cid, label=label, spirit=spirit, money=money, **kw)


def _choices(s: dict, card: dict) -> list[dict]:
    """The choices of the card's current stage (id, label, spirit, money, …)."""
    st = card['stage']
    if st == 'react':
        return [_opt(c['id'], _fill(c['label'], s, card), c['spirit'], c['money'], text=c['text'], bond=c['bond'],
                     who=c.get('who'), default=c['default']) for c in HARD_INDEX[card['ref']]['choices']]
    if st == 'comfort':
        k = COMFORT_INDEX[card['comfort']]
        return [_opt('yes', k['label'], round(k['spirit'] * COMFORT_SCALE), -k['cost'] + k['money'], text=k['text'], bond=k['bond'], who=k['who']),
                _opt('self', 'Thôi, mình tự đi xả stress', 0, 0, text=''),
                _opt('no', 'Cảm ơn, để hôm khác nhé', 3, 0, text='Bạn cảm ơn rối rít. Được hỏi han vậy cũng ấm lòng.', bond=1,
                     who=k['who'])]
    if st == 'gop':
        g = card['gop']
        gift = GIFTS.get(g.get('gift')) if g.get('gift') else None
        take = gift['money'] if gift else g['total']
        return [_opt('take', 'Nhận và cảm ơn cả xóm', gift['spirit'] if gift else 16, take,
                     text=gift['text'] if gift else 'Bạn cầm phong bì, rưng rưng. Tiền thì ít, mà tình thì nhiều.'),
                _opt('thanks', 'Cảm ơn, con tự lo được ạ', 9, 0,
                     text='Mọi người không ép, nhưng dặn: “Cần gì cứ nói nghe.” Bạn thấy mình có chỗ dựa.')]
    if st == 'cope':
        rows = [_opt(x['id'], x['label'], x['spirit'], -x['cost'], emoji=x['emoji'], text=x['text'], risky=bool(x.get('risk')))
                for x in COPE]
        return rows + [_opt('skip', 'Thôi, về ngủ sớm', 2, 0, text='Bạn tắm nước ấm rồi đi ngủ sớm.')]
    if st == 'ask':
        a = ASK_INDEX[card['ref']]
        return [_opt('big', f'Góp {a["big"]} xu', 7, -a['big'], text='Mọi người cảm ơn bạn mãi. Bạn thấy mình là người của hẻm này.', bond=8, who=a['who']),
                _opt('small', f'Góp {a["small"]} xu', 5, -a['small'], text='Ít thôi mà quý. Ai cũng gật đầu cảm ơn.', bond=5, who=a['who']),
                _opt('hand', a['hand'], 4, 0, text='Mồ hôi nhễ nhại, nhưng vui. Được mời ở lại ăn cơm.', bond=4, who=a['who']),
                _opt('none', 'Dạo này mình kẹt quá', -1, 0, text='Không ai trách gì. Bạn hứa lần sau sẽ phụ một tay.')]
    if st == 'joy':
        return [_opt('ok', 'Dễ thương ghê', 0, 0, text='')]
    if st == 'impulse':
        x = IMPULSE_INDEX[card['ref']]
        return [_opt('all', 'Chốt hết cho đỡ buồn', 8, -x['big'], text='Đơn đặt xong, vui được… một lúc.'),
                _opt('one', 'Mua đúng một món thôi', 4, -x['small'], text='Một món nhỏ cho mình. Vậy là đủ.'),
                _opt('clear', 'Xóa giỏ, đi ngủ', 1, 0, text='Khó ghê, nhưng bạn làm được. Sáng mai tự hào ghê.')]
    if st == 'sick':
        return [_opt('rest', 'Uống thuốc, ngủ một giấc', 8, 0, text='Ngủ một mạch tới chiều. Người nhẹ hơn.'),
                _opt('doctor', 'Đi khám cho chắc', 14, -DOCTOR, text='Bác sĩ dặn nghỉ ngơi, ăn uống đủ. Yên tâm hẳn.')]
    return []


def _default(card: dict, choices: list[dict]) -> str:
    st = card['stage']
    if st == 'react':
        return next((c['id'] for c in choices if c.get('default')), next((c['id'] for c in choices if c['money'] >= 0), choices[0]['id']))
    return {'comfort': 'yes', 'gop': 'take', 'cope': 'skip', 'ask': 'hand', 'joy': 'ok', 'impulse': 'one',
            'sick': 'rest'}.get(st, choices[0]['id'] if choices else '')


def _why(s: dict, c: dict) -> str | None:
    w = s['journey']['wallet']
    if c['money'] < 0 and w < -c['money']:
        return f'Ví còn {max(0, w)} xu' if w >= 0 else f'Ví đang nợ {-w} xu'
    return None


# ---------------------------------------------------------------- planning a card's next stage
def _pick_comfort(s: dict, L: dict, cats: tuple, day: int, career: str | None, rng: random.Random,
                  advice: bool = False) -> str | None:
    pool = [k for k in COMFORT if set(k['cats']) & set(cats)]
    if advice:
        pool = [k for k in pool if k['advice']] or pool
    fresh = [k for k in pool if day - L['recent'].get(k['id'], -99) >= COMFORT_RECENT]
    pool = fresh or pool
    if not pool:
        return None
    weights = [1 + L['bonds'].get(k['who'], BOND_START) / 50 for k in pool]
    pick = rng.random() * sum(weights)
    for k, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            return k['id']
    return pool[-1]['id']


def _plan_gop(s: dict, L: dict, card: dict, rng: random.Random) -> dict:
    """Cả xóm góp tiền: part of the loss back, bigger when the street is warm. Or a gift."""
    loss = card['loss']
    if card['ref'] == 'xu_phone':
        return dict(rows=[], total=0, gift='phone')
    if loss < 12 or rng.random() < .25:
        gift = rng.choice(['rice', 'flowers', 'food'])
        return dict(rows=[], total=0, gift=gift)
    w = warmth(L)
    ratio = max(.4, min(.9, .5 + .4 * (w - 40) / 40))
    target = max(10, round(loss * ratio))
    ids = sorted(L['bonds'], key=lambda k: (-L['bonds'][k], k))
    people = [k for k in ids if k != 'be_ti'][:6]
    rng.shuffle(people)
    people = people[:rng.choice((3, 4, 5))]
    weights = [L['bonds'][k] + rng.randint(10, 40) for k in people]
    total_w = sum(weights)
    rows, given = [], 0
    for i, (k, wt) in enumerate(zip(people, weights)):
        amt = target - given if i == len(people) - 1 else max(2, target * wt // total_w)
        amt = max(1, amt)
        rows.append(dict(who=k, amount=int(amt)))
        given += amt
    rows.sort(key=lambda r: -r['amount'])
    return dict(rows=rows, total=sum(r['amount'] for r in rows), gift=None)


def _after_react(s: dict, L: dict, card: dict) -> None:
    """Who comes round after a hard day: the xóm chips in (scams, big losses) or someone comforts you."""
    rng = _rng(s, 'follow', card['id'], card['day'])
    cat = card['cat']
    p_gop = .85 if cat == 'lua' else .45 if cat == 'xui' and card['loss'] >= 20 else 0
    if card['ref'] == 'xu_phone':
        p_gop = .6
    if rng.random() < p_gop:
        card['gop'] = _plan_gop(s, L, card, rng)
        card['stage'] = 'gop'
        return
    p = 1.0 if cat in ('that_tinh', 'dat_dieu') else .95 if L['spirit'] < 45 else .75
    if rng.random() < p:
        kid = _pick_comfort(s, L, (cat,), card['day'], card['career'], rng, advice=cat == 'dat_dieu')
        if kid:
            card['comfort'] = kid
            card['stage'] = 'comfort'
            return
    card['stage'] = 'done'


# ---------------------------------------------------------------- applying a choice
def _apply(s: dict, L: dict, card: dict, cid: str, auto: bool = False) -> list[str]:
    e = _core()
    choices = _choices(s, card)
    c = next((x for x in choices if x['id'] == cid), None)
    e.need(c, 'Lựa chọn này không có trong chuyện.')
    if not auto:
        why = _why(s, c)
        e.need(not why, f'Chưa đủ tiền: {why}.' if why else '', 'not_enough')
    elif _why(s, c):
        free = [x for x in choices if x['money'] >= 0]
        c = next((x for x in free if x['id'] in SAFE), free[0])
        cid = c['id']
    st = card['stage']
    title = _title(s, card)
    lines = []
    spirit = c['spirit']
    money = c['money']
    text = _fill(c.get('text') or '', s, card)
    # Coping has its own little twist (online orders) and hangovers.
    if st == 'cope' and cid != 'skip':
        x = COPE_INDEX[cid]
        if x.get('risk') and _rng(s, 'risk', card['id'], cid).random() < x['risk']['p']:
            spirit, text = x['risk']['spirit'], x['risk']['text']
        if x.get('hangover'):
            L['hangover'] = s['journey']['life_day'] + 1
        L['coped'] = s['journey']['life_day']
        L['stats']['coped'] += 1
    if money:
        gift = GIFTS.get((card['gop'] or {}).get('gift') or '')
        label = {'react': title, 'comfort': 'Đi chơi cùng hàng xóm',
                 'gop': f'Quà của xóm: {gift["name"]}' if gift else 'Cả xóm góp tiền giúp bạn',
                 'cope': f'Xả stress: {COPE_INDEX[cid]["label"] if cid in COPE_INDEX else ""}',
                 'ask': f'Góp giúp: {title}', 'impulse': f'Buồn quá tiêu tiền: {title}',
                 'sick': 'Đi khám bệnh'}.get(st, title)
        money = _wallet(s, money, label)
        card['money'] += money
        if money < 0:
            L['stats']['spent'] += -money
        if st == 'gop':
            L['stats']['received'] += money
        if st == 'ask':
            L['stats']['given'] += -money
    card['spirit'] += _spirit(L, spirit)
    who = c.get('who')
    if who == 'work' or who == 'friends':
        pass
    elif who:
        _bond(L, who, c.get('bond', 0))
    elif c.get('bond') and st == 'react':
        _bond(L, next((w for w in card['who'] if w in L['bonds']), None), c['bond'])
    if who and who not in card['who']:
        card['who'].append(who)
    if text:
        lines.append(text)
    # Advance.
    if st == 'react':
        card['trail'].append(text)
        _after_react(s, L, card)
    elif st == 'gop':
        g = card['gop']
        for r in g['rows']:
            _bond(L, r['who'], 3 if cid == 'thanks' else 2)
            if r['who'] not in card['who']:
                card['who'].append(r['who'])
        gift = GIFTS.get(g.get('gift')) if g.get('gift') else None
        if gift:
            _bond(L, gift['who'], 4)
            if gift['who'] not in card['who']:
                card['who'].append(gift['who'])
        card['trail'].append(text)
        L['stats']['warm'] += 1
        card['stage'] = 'done'
    elif st == 'comfort':
        k = COMFORT_INDEX[card['comfort']]
        if cid == 'self':
            card['stage'] = 'cope'
        else:
            card['trail'].append(text)
            if cid == 'yes':
                L['stats']['warm'] += 1
                L['stats']['outings'] += 1
                L['outing'] = dict(day=int(s['journey']['life_day']), who=k['who'])
            card['stage'] = 'done'
    elif st == 'sick':
        card['trail'].append(text)
        rng = _rng(s, 'sick-care', card['id'])
        kid = _pick_comfort(s, L, ('om',), card['day'], card['career'], rng)
        card['comfort'] = kid
        card['stage'] = 'comfort' if kid else 'done'
    else:
        card['trail'].append(text)
        card['stage'] = 'done'
    card['trail'] = ar.last([t for t in card['trail'] if t], 6, 'life.trail', ar.JOURNEY)
    if card['stage'] == 'done':
        _finish(s, L, card, cid)
    return lines


def _finish(s: dict, L: dict, card: dict, choice: str | None = None) -> None:
    if card['comfort']:
        L['recent'][card['comfort']] = card['day']
    first = (_content(card).get('lines') or [''])[0]
    _log(s, L, card, ' '.join(card['trail'][-2:]) or _fill(first, s, card) or _title(s, card), choice)


def _auto(s: dict, L: dict, card: dict) -> None:
    """A card left undecided when the next day closes takes its defaults, stage by stage."""
    for _ in range(6):
        if card['stage'] == 'done':
            return
        choices = _choices(s, card)
        if not choices:
            card['stage'] = 'done'
            _finish(s, L, card)
            return
        _apply(s, L, card, _default(card, choices), auto=True)


# ---------------------------------------------------------------- firing cards
def _fire_hard(s: dict, L: dict, x: dict, day: int, career: str | None, gossip: str | None = None) -> dict:
    card = _new_card(L, day, 'hard', x['id'], x['cat'], 'react', career, fact=x.get('fact'), gossip=gossip)
    if x['cat'] == 'dat_dieu' and x.get('fact') == 'seen' and L.get('outing'):
        card['who'].append(L['outing']['who'])
    card['hit'] = _spirit(L, round(x['hit'] * HIT_SCALE))
    card['spirit'] = card['hit']
    if x['loss']:
        card['loss'] = -_wallet(s, -x['loss'], _fill(x['title'], s, card))
        card['money'] = -card['loss']
    L['recent'][x['id']] = day
    L['stats']['hard'] += 1
    if x['cat'] == 'lua':
        L['stats']['scams'] += 1
    if x['cat'] == 'dat_dieu':
        L['stats']['rumours'] += 1
        L['rumour'] = day
    return card


def _fire_external(s: dict, L: dict, q: dict, day: int, career: str | None) -> dict:
    """A scam lost in an incident or Mây Coin: the neighbours hear and chip in."""
    card = _new_card(L, day, 'scam', q['src'], 'lua', 'gop', career, src=q['src'], loss=int(q['loss']))
    card['trail'].append(q['text'][:160])
    rng = _rng(s, 'scam-gop', card['id'], day)
    card['gop'] = _plan_gop(s, L, card, rng)
    card['spirit'] = _spirit(L, -8)
    card['hit'] = card['spirit']
    L['stats']['scams'] += 1
    return card


def _pick(rng: random.Random, pool: list, weights: list) -> dict | None:
    if not pool:
        return None
    pick = rng.random() * sum(weights)
    for x, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            return x
    return pool[-1]


# Heartbreaks that assume the player has a lover ("Ba năm, kết thúc trong một tin nhắn"). The game gives the
# player no love life of its own, so a single player met a partner they never had, and a player engaged or
# married to another player read it as that person. Still defined (a save may hold such a card), never drawn.
PARTNER_STORIES = frozenset({'tt_break', 'tt_far', 'tt_third', 'tt_birthday'})
# Heartbreaks after which "bị bỏ" (the breakup rumour) is true: being ghosted, and the old partner stories.
DUMPED = frozenset(HARD_INDEX[k]['title'] for k in ('tt_ghost', 'tt_break', 'tt_far', 'tt_third'))


def _taken(s: dict) -> bool:
    """Engaged or married to another player (game/marriage.py): no heartbreak cards at all."""
    sp = (s.get('marriage') or {}).get('spouse') if isinstance(s.get('marriage'), dict) else None
    return isinstance(sp, dict) and sp.get('status') in ('engaged', 'married')


def _hard_pool(L: dict, day: int, career: str | None, facts: set | None = None, taken: bool = False) -> list:
    rows = []
    for x in HARD:
        if x['careers'] and career not in x['careers']:
            continue
        if x['id'] in PARTNER_STORIES or (taken and x['cat'] == 'that_tinh'):
            continue
        if day <= CALM_UNTIL and not x['mild']:
            continue
        if day - L['recent'].get(x['id'], -99) < RECENT:
            continue
        if facts is None:
            if x['cat'] == 'dat_dieu':
                continue
        elif x['cat'] != 'dat_dieu' or x['fact'] not in facts:
            continue
        rows.append(x)
    return rows


def _weight(x: dict) -> float:
    if not x['careers']:
        return 1.0
    return 2.5 if len(x['careers']) <= 3 else 1.6


def _roll(s: dict, L: dict, day: int, career: str | None, facts: set) -> dict | None:
    """The new life day's card (or None). Pure function of the seed, the day and the life state."""
    if L['queue']:
        q = L['queue'].pop(0)
        return _fire_external(s, L, q, day, career)
    if day < FIRST_DAY:
        return None
    r = _rng(s, 'day', day)
    rolls = [r.random() for _ in range(8)]
    early = day <= CALM_UNTIL
    sp = L['spirit']
    if sp < SICK_SPIRIT and rolls[0] < SICK_P:
        x = r.choice([k for k in SICK if day - L['recent'].get(k['id'], -99) >= 3] or SICK)
        card = _new_card(L, day, 'sick', x['id'], 'om', 'sick', career)
        card['loss'] = -_wallet(s, -x['cost'], f'Tiền thuốc: {x["title"]}')
        card['money'] = -card['loss']
        L['recent'][x['id']] = day
        return card
    if sp < IMPULSE_SPIRIT and rolls[1] < IMPULSE_P and not early:
        pool = [k for k in IMPULSE if day - L['recent'].get(k['id'], -99) >= RECENT] or IMPULSE
        x = r.choice(pool)
        L['recent'][x['id']] = day
        return _new_card(L, day, 'impulse', x['id'], 'buon', 'impulse', career)
    if facts and not early and day - L['rumour'] >= RUMOUR_GAP and rolls[2] < RUMOUR_P:
        pool = _hard_pool(L, day, career, facts, _taken(s))
        x = _pick(r, pool, [1.0] * len(pool))
        if x:
            return _fire_hard(s, L, x, day, career, gossip=r.choice(sorted(GOSSIPS)))
    p = HARD_P[0] if early else HARD_P[1]
    if sp < LOW_SPIRIT:
        p *= .5
    if rolls[3] < p:
        pool = _hard_pool(L, day, career, taken=_taken(s))
        x = _pick(r, pool, [_weight(k) for k in pool])
        if x:
            return _fire_hard(s, L, x, day, career)
    if sp < 40 and rolls[4] < INVITE_P:
        kid = _pick_comfort(s, L, ('ru',), day, career, r)
        if kid:
            card = _new_card(L, day, 'invite', kid, 'ru', 'comfort', career, comfort=kid)
            card['who'].append(COMFORT_INDEX[kid]['who'])
            return card
    if not early and rolls[5] < ASK_P:
        pool = [a for a in ASK if day - L['recent'].get(a['id'], -99) >= RECENT * 2]
        if pool:
            a = r.choice(pool)
            L['recent'][a['id']] = day
            card = _new_card(L, day, 'ask', a['id'], 'xom', 'ask', career)
            card['who'].append(a['who'])
            return card
    if rolls[6] < JOY_P:
        pool = [a for a in JOYS if day - L['recent'].get(a['id'], -99) >= RECENT]
        if pool:
            a = r.choice(pool)
            L['recent'][a['id']] = day
            card = _new_card(L, day, 'joy', a['id'], 'vui', 'joy', career)
            if a['who']:
                card['who'].append(a['who'])
            card['spirit'] = _spirit(L, a['spirit'])
            return card
    return None


# ---------------------------------------------------------------- facts for rumours (read from the real save)
def facts(s: dict, career: str | None, summary: dict | None, day: int) -> set:
    """What the street could have noticed about you lately (only true things)."""
    j = s['journey']
    L = _state(s)
    out = set()
    rows = j.get('days', [])
    if isinstance(summary, dict) and int(summary.get('completed') or 0) >= 5:
        out.add('late')
    last = rows[-3:]
    if len(last) == 3 and len({r['c'] for r in last}) == 3 and last[-1]['d'] - last[0]['d'] == 2:
        out.add('late')
    hist = [h for h in j.get('history', []) if h.get('day', 0) >= day - 3]
    spent = -sum(h['amount'] for h in hist if h['amount'] < 0 and h['kind'] in (KIND, 'invest'))
    if spent >= 60:
        out.add('spend')
    if sum(h['amount'] for h in hist if h['amount'] > 0 and h['kind'] == 'draw') >= 150:
        out.add('draw')
    o = L.get('outing')
    if o and o.get('who') == 'anh_khoa' and _gender(s) != 'male' and day - o.get('day', -99) <= 3:
        out.add('seen')
    if not _taken(s) and any(r['cat'] == 'that_tinh' and r['title'] in DUMPED and day - r['day'] <= 10 for r in L['log']):
        out.add('breakup')
    c = (s.get('careers') or {}).get(career or '')
    if isinstance(c, dict):
        ledger = ((c.get('ops') or {}).get('finance') or {}).get('ledger') or []
        closed = int(c.get('day', 1)) - 1
        if any(r.get('day') == closed and (r.get('category') == 'stock' or str(r.get('reason', '')).startswith('Nhập '))
               for r in ledger[-80:]):
            out.add('stock')
    return out & set(FACTS)


# ---------------------------------------------------------------- scams elsewhere → the xóm hears
def _queue(L: dict, src: str, key: str, loss: int, text: str) -> None:
    if key in L['seen'] or loss <= 0:
        return
    L['seen'] = ar.last(L['seen'] + [key], SEEN_MAX, 'life.seen', ar.JOURNEY)
    if len(L['queue']) < QUEUE_MAX:
        L['queue'].append(dict(src=src, key=key[:60], loss=int(min(loss, 10**6)), text=text[:160]))


def _watch_scams(s: dict, L: dict, career: str | None) -> None:
    # An incident whose money went to a scammer (ledger category scam_loss).
    for cid, c in (s.get('careers') or {}).items():
        box = c.get('incidents') if isinstance(c, dict) else None
        last = (box or {}).get('last')
        if not last or last.get('practice'):
            continue
        lost = -sum(int(x.get('amount', 0)) for x in last.get('lines', []) if x.get('cat') == 'scam_loss' and x.get('amount', 0) < 0)
        if lost > 0:
            from .incident_content import INDEX
            title = INDEX.get(last.get('script'), {}).get('title', 'Bị lừa')
            _queue(L, 'incident', f'{cid}:{last["id"]}', lost, f'{title}: mất {lost} xu.')
    # Mây Coin: a "lãi khủng" project vanished with the stake.
    iv = s['journey'].get('invest')
    if isinstance(iv, dict):
        lost = int((iv.get('stats') or {}).get('lost', 0))
        if lost > L['iv_lost']:
            gone = lost - L['iv_lost']
            L['iv_lost'] = lost
            _queue(L, 'invest', f'invest:{lost}', gone, f'Dự án “lãi khủng” biến mất cùng {gone} xu của bạn.')
        elif lost < L['iv_lost']:
            L['iv_lost'] = lost


# ---------------------------------------------------------------- the day turns
def _daily(s: dict, L: dict, nd: int, mode: str | None, completed: int) -> list[str]:
    notes = []
    sp = L['spirit']
    gain = 4 if sp < 40 else 2 if sp < 55 else 1 if sp < 70 else 0
    if mode == 'calm':
        gain += 2       # a slow day is a rest day
    elif mode == 'festival':
        gain += 1
    if completed >= 3:
        gain += 1       # a good day's work
    _spirit(L, gain)
    if L['hangover'] and L['hangover'] <= nd:
        _spirit(L, -HANGOVER)
        L['hangover'] = 0
        notes.append('🥴 Dậy đầu đau như búa bổ. Tối qua uống hơi nhiều.')
    return notes


def on_life_day(s: dict, result: dict | None = None, career: str | None = None) -> None:
    """Catch up to `journey.life_day`: recover, settle yesterday's card, roll today's. Idempotent."""
    j = s.get('journey')
    if not isinstance(j, dict):
        return
    L = _state(s)
    target = int(j['life_day'])
    if not j.get('story'):
        L['day'] = max(L['day'], target)
        return
    if L['day'] >= target:
        return
    summary = (result or {}).get('summary') if isinstance(result, dict) else None
    completed = int((summary or {}).get('completed') or 0) if isinstance(summary, dict) else 0
    rows = j.get('days') or []
    mode = rows[-1]['m'] if rows else None
    career = career or (rows[-1]['c'] if rows else s.get('current'))
    before = L['mark']
    L['day'] = max(L['day'], target - 60)
    notes = []
    while L['day'] < target:
        nd = L['day'] + 1
        last = nd == target
        notes += _daily(s, L, nd, mode if last else None, completed if last else 0)
        card = L['pending']
        if card and card['stage'] != 'done':
            _auto(s, L, card)
        L['pending'] = None
        if last:
            _watch_scams(s, L, career)
            L['pending'] = _roll(s, L, nd, career, facts(s, career, summary, nd))
        L['day'] = nd
    L['mark'] = L['spirit']
    if isinstance(summary, dict):
        card = L['pending']
        summary['life'] = dict(spirit=L['spirit'], delta=L['spirit'] - before, warmth=warmth(L), notes=notes,
                               pending=dict(emoji=_emoji(card), title=_title(s, card), cat_label=CATS[card['cat']][1])
                               if card else None, **mood(L['spirit']))


def after(s: dict, career: str | None, action: str, result: dict) -> None:
    """Engine hook after every successful career action (after journey.after and invest.on_life_day)."""
    j = s.get('journey')
    if not isinstance(j, dict):
        return
    L = _state(s)
    if j.get('story') and action in ('inc_choose', 'end_day'):
        _watch_scams(s, L, career)
    on_life_day(s, result, career if action == 'end_day' else None)


# ---------------------------------------------------------------- commands
def apply(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(j.get('story'), 'Chuyện đời thường chỉ có trong hành trình.', 'locked')
    L = _state(s)
    card = L['pending']
    result = dict(message='', effects=[])
    if name == 'lf_choose':
        need(set(p) == {'id', 'choice'} and isinstance(p['id'], str) and isinstance(p['choice'], str), 'Chọn một cách nhé.')
        need(card and card['id'] == p['id'] and card['stage'] != 'done', 'Chuyện này đã qua rồi.', 'already_decided')
        lines = _apply(s, L, card, p['choice'])
        result['message'] = lines[0] if lines else ''
    elif name == 'lf_cope':
        need(set(p) == {'choice'} and p['choice'] in COPE_INDEX, 'Chọn một cách xả stress nhé.')
        need(L['coped'] != j['life_day'], 'Hôm nay xả rồi. Mai nhé!', 'already_done')
        need(not card or card['stage'] == 'done', 'Đang có một chuyện chờ bạn. Xem nó trước nhé.', 'busy')
        c = _new_card(L, j['life_day'], 'cope', p['choice'], 'xa', 'cope', s.get('current'))
        need(not _why(s, next(x for x in _choices(s, c) if x['id'] == p['choice'])), 'Ví không đủ cho cuộc vui này.', 'not_enough')
        lines = _apply(s, L, c, p['choice'])
        L['pending'] = None
        result['message'] = lines[0] if lines else ''
    elif name == 'lf_close':
        need(set(p) == {'id'} and isinstance(p['id'], str), 'Dữ liệu thao tác không hợp lệ.')
        need(card and card['id'] == p['id'], 'Chuyện này đã cất rồi.', 'already_decided')
        need(card['stage'] in ('done', 'joy'), 'Chọn một cách trước đã nhé.')
        if card['stage'] == 'joy':
            _apply(s, L, card, 'ok')
        L['pending'] = None
    return result


def action(s: dict, name: str, p: dict) -> tuple[dict, dict]:
    """Engine entry point (like invest.action): apply, run journey hooks, validate."""
    e = _core()
    result = apply(s, name, p or {})
    _jr().after(s, None, name, p or {}, result)
    validate(s)
    e.validate_state(s)
    return s, result


COMMANDS = ('lf_choose', 'lf_cope', 'lf_close')


# ---------------------------------------------------------------- views
def _choice_view(s: dict, c: dict) -> dict:
    why = _why(s, c)
    return dict(id=c['id'], label=c['label'], spirit=c['spirit'], money=c['money'], emoji=c.get('emoji'),
                risky=bool(c.get('risky')), ok=not why, why=why)


def _card_view(s: dict, L: dict, card: dict) -> dict:
    x = _content(card)
    cat_emoji, cat_label = CATS.get(card['cat'], ('🌿', 'Chuyện đời thường'))
    v = dict(id=card['id'], day=card['day'], kind=card['kind'], cat=card['cat'], cat_emoji=cat_emoji, cat_label=cat_label,
             emoji=_emoji(card), title=_title(s, card), stage=card['stage'], loss=card['loss'], hit=card['hit'],
             spirit=card['spirit'], money=card['money'], trail=list(card['trail']), lines=[], speaker=None, gop=None,
             choices=[], fact=card['fact'], gossip=_who_view(card['gossip']) if card['gossip'] else None,
             who=[w for w in (_who_view(k, card['career']) for k in card['who']) if w])
    if card['kind'] == 'scam':
        v['lines'] = list(card['trail'][:1])
    elif x.get('lines'):
        v['lines'] = [_fill(t, s, card) for t in x['lines']]
    if card['kind'] == 'ask':
        v['speaker'] = _who_view(x['who'])
    if card['kind'] == 'joy' and x.get('who'):
        v['speaker'] = _who_view(x['who'])
    if card['stage'] == 'comfort' and card['comfort']:
        k = COMFORT_INDEX[card['comfort']]
        v['speaker'] = _who_view(k['who'], card['career'])
        v['say'] = [_fill(t, s, card) for t in k['lines']]
    if card['gop']:
        g = card['gop']
        gift = GIFTS.get(g.get('gift')) if g.get('gift') else None
        v['gop'] = dict(rows=[dict(amount=r['amount'], **_who_view(r['who'])) for r in g['rows']], total=g['total'],
                        gift=dict(emoji=gift['emoji'], name=gift['name'], text=gift['text'], money=gift['money'],
                                  **{'from': _who_view(gift['who'])}) if gift else None)
    if card['stage'] != 'done':
        v['choices'] = [_choice_view(s, c) for c in _choices(s, card)]
    return v


def public(s: dict) -> dict:
    j = s.get('journey') or {}
    L = j.get('life') or initial(int(j.get('life_day', 1)))
    w = warmth(L)
    people = _cast()
    bonds = sorted(({'id': k, 'name': people[k]['name'], 'emoji': people[k]['emoji'], 'role': people[k]['role'],
                     'bond': int(v)} for k, v in L['bonds'].items() if k in people), key=lambda r: (-r['bond'], r['name']))
    card = L['pending'] if j.get('story') else None
    cope_used = L['coped'] == j.get('life_day')
    probe = dict(stage='cope')
    cope = [_choice_view(s, c) for c in _choices(s, probe) if c['id'] != 'skip'] if j.get('story') else []
    if cope_used:
        for c in cope:
            c.update(ok=False, why=None)      # the sheet says it once: "hôm nay xả rồi"
    return dict(enabled=bool(j.get('story')), spirit=L['spirit'], mood=mood(L['spirit']), warmth=w, warmth_name=warmth_name(w),
                bonds=bonds, pending=_card_view(s, L, card) if card else None,
                log=[dict(r, who=[x for x in (_who_view(k) for k in r['who']) if x]) for r in reversed(L['log'][-20:])],
                stats=dict(L['stats']), cope=cope, cope_used=cope_used, wallet=j.get('wallet', 0),
                hangover=bool(L['hangover']), low=L['spirit'] < IMPULSE_SPIRIT)


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or 'life' not in j:
        return
    L = j['life']
    bad = 'Dữ liệu chuyện đời thường không hợp lệ.'
    need(isinstance(L, dict) and set(L) == set(initial()), bad, 'invalid_save')
    need(L['version'] == VERSION, bad, 'invalid_save')
    integer(L['day'], 1, 10**6)
    need(L['day'] <= j['life_day'], bad, 'invalid_save')
    integer(L['spirit'], 0, 100)
    integer(L['mark'], 0, 100)
    integer(L['seq'], 0, 10**9)
    integer(L['iv_lost'], 0, 10**9)
    integer(L['hangover'], 0, 10**6)
    integer(L['coped'], 0, 10**6)
    integer(L['rumour'], 0, 10**6)
    need(isinstance(L['bonds'], dict) and set(L['bonds']) == set(_cast()), bad)
    for v in L['bonds'].values():
        integer(v, 0, 100)
    need(isinstance(L['recent'], dict) and len(L['recent']) <= 400, bad)
    for k, v in L['recent'].items():
        txt(k, 40)
        integer(v, 0, 10**6)
    need(isinstance(L['seen'], list) and len(L['seen']) <= SEEN_MAX and all(isinstance(x, str) and len(x) <= 80 for x in L['seen']), bad)
    need(isinstance(L['queue'], list) and len(L['queue']) <= QUEUE_MAX, bad)
    for q in L['queue']:
        need(isinstance(q, dict) and set(q) == {'src', 'key', 'loss', 'text'} and q['src'] in EXTERNAL, bad)
        integer(q['loss'], 1, 10**6)
        txt(q['text'], 160)
    o = L['outing']
    need(o is None or (isinstance(o, dict) and set(o) == {'day', 'who'} and o['who'] in _people()), bad)
    if o:
        integer(o['day'], 1, 10**6)
    st = L['stats']
    need(isinstance(st, dict) and set(st) == set(STATS), bad)
    for v in st.values():
        integer(v, 0, 10**9)
    need(isinstance(L['log'], list) and len(L['log']) <= LOG_MAX, bad)
    people = _people()
    for r in L['log']:
        need(isinstance(r, dict) and set(r) == LOG_KEYS and r['kind'] in KINDS and r['cat'] in CATS, bad)
        integer(r['day'], 1, 10**6)
        integer(r['spirit'], -200, 200)
        integer(r['money'], -10**6, 10**6)
        txt(r['title'], 80)
        txt(r['text'], 160)
        need(isinstance(r['who'], list) and all(w in people for w in r['who']), bad)
        need(r['fact'] in (None,) + FACTS and (r['gossip'] is None or r['gossip'] in GOSSIPS), bad)
    card = L['pending']
    if card is not None:
        need(isinstance(card, dict) and set(card) == CARD_KEYS, bad)
        need(card['kind'] in KINDS and card['stage'] in STAGES and card['cat'] in CATS, bad)
        integer(card['day'], 1, 10**6)
        need(card['day'] <= j['life_day'], bad)
        need(card['kind'] != 'hard' or card['ref'] in HARD_INDEX, bad)
        need(card['kind'] != 'ask' or card['ref'] in ASK_INDEX, bad)
        need(card['stage'] != 'comfort' or card['comfort'] in COMFORT_INDEX, bad)
        need(card['stage'] != 'gop' or isinstance(card['gop'], dict), bad)
        need(isinstance(card['who'], list) and all(w in people for w in card['who']), bad)
        need(isinstance(card['trail'], list) and len(card['trail']) <= 6, bad)
        for k in ('loss', 'hit', 'spirit', 'money'):
            integer(card[k], -10**6, 10**6)
