"""Người trong phố: the people around the street trades (fruit stall, rubbish round, drain cleaning)
decide by themselves when the player proposes something: a price, a deposit, a fee, a way to chase
a debt, a word back. Each person has hidden traits rolled from a seed (the task or event id) and
shifted by their persona; every decision is a pure function of those traits and the player's input,
so the same input on the same seed always goes the same way and a save validates as it plays.

    traits(seed, persona)                 -> dict of 0..100 values
    judge_price(tr, fair, price, tries)   -> the answer to a price the player names
    haggle(tr, full, offer, price, tries) -> the answer of a customer who is bargaining down
    chase(tr, owed, tone, asked, tries)   -> what a debtor does when chased
    fee(tr, due, asked, tone, tries)      -> what a household does about the rubbish fee
    word(tr, choice)                      -> how someone takes a word back / a request / a refusal
"""
from __future__ import annotations

import hashlib

KEYS = ('stingy', 'savvy', 'mood', 'honest', 'rude', 'budget', 'proud')
# How each persona leans (added to the rolled value, then clamped 0..100).
LEAN = {'sour': dict(stingy=20, savvy=15, mood=-20, rude=10), 'picky': dict(stingy=15, savvy=25, proud=10),
        'bossy': dict(rude=25, proud=20, savvy=5), 'warm': dict(mood=20, honest=20, rude=-20, stingy=-10),
        'genz': dict(budget=-15, mood=10, savvy=-5), 'quiet': dict(rude=-15, proud=-10, honest=5)}


def roll(*parts) -> int:
    """0..99 from the parts (never random)."""
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16) % 100


def traits(seed: str, persona: str | None = None) -> dict:
    lean = LEAN.get(persona or '', {})
    return {k: max(0, min(100, roll('folk', seed, k) + lean.get(k, 0))) for k in KEYS}


def _clamp(v: float, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, round(v))))


# ---------------------------------------------------------------- a price the player names
def cap_of(tr: dict, fair: int) -> int:
    """The most this person pays for a job worth `fair`: savvy people know the going rate."""
    naive = (100 - tr['savvy']) / 100 * 0.7                  # up to 70% over for someone who has no idea
    rich = tr['budget'] / 100 * 0.25
    return max(1, _clamp(fair * (1.05 + naive + rich - tr['stingy'] / 100 * 0.15), 1, 10 ** 5))


def judge_price(tr: dict, fair: int, price: int, tries: int = 0) -> dict:
    """kind: 'cheap' (glad), 'accept', 'counter' (with `counter`), 'walk'. `grudge`: they pay now and find out later."""
    fair, price = max(1, int(fair)), max(0, int(price))
    cap = cap_of(tr, fair)
    ratio = price * 100 // fair
    if price * 10 <= fair * 9:
        return dict(kind='cheap', ratio=ratio, grudge=False)
    if price <= cap:
        # Paid without a fuss; someone overcharged by a lot may still hear the real price later.
        return dict(kind='accept', ratio=ratio, grudge=ratio > 130 and tr['savvy'] + tr['honest'] < 120)
    if tries >= 2 or ratio > 250 or (tr['rude'] > 70 and ratio > 160):
        return dict(kind='walk', ratio=ratio, grudge=False)
    counter = _clamp(min(price - 1, max(fair, cap - (tr['stingy'] // 10))), 1, price)
    return dict(kind='counter', ratio=ratio, counter=counter, grudge=False)


def haggle(tr: dict, full: int, offer: int, price: int, tries: int = 0) -> dict:
    """A customer who asked for `offer` answers the price the player names (full = the scale's price).
    kind: 'glad' (at or under their offer), 'accept', 'counter' (a new offer), 'walk'."""
    full, offer, price = max(1, full), max(1, offer), max(0, price)
    if price <= offer:
        return dict(kind='glad')
    # How far above their own offer they go, from stingy (not at all) to easy-going (all the way).
    room = (100 - tr['stingy']) / 100 * 0.8 + tr['mood'] / 100 * 0.3 + tr['budget'] / 100 * 0.2
    cap = offer + _clamp((full - offer) * min(1.1, room), 0, full)
    if price <= cap:
        return dict(kind='accept')
    if tries >= 2 or (tr['proud'] > 75 and price >= full):
        return dict(kind='walk')
    nxt = _clamp(offer + (cap - offer + 1) // 2 + tries, offer, price - 1)
    return dict(kind='counter', counter=nxt)


# ---------------------------------------------------------------- chasing a debt
TONES = ('soft', 'straight', 'family')


def chase(tr: dict, owed: int, tone: str, asked: int, tries: int, days: int) -> dict:
    """A debtor chased for `asked` (≤ owed) after `days`, on the `tries`-th time.
    kind: 'paid' (pays `paid`), 'part' (some), 'later' (promises), 'deny' (says they paid / never owed),
    'angry' (takes offence, a bad word in the street), 'gone' (moved away: never pays)."""
    asked = max(1, min(owed, asked))
    cash = _clamp(owed * (tr['budget'] + 20) / 100, 0, owed)
    if tr['honest'] < 25 and tries >= 1 and days >= 3:
        return dict(kind='gone', paid=0)
    if tone == 'family' and tr['proud'] > 60:
        return dict(kind='angry', paid=min(cash, asked) // 2)
    if tone == 'straight' and tr['proud'] > 70 and tr['honest'] < 60:
        return dict(kind='angry', paid=0)
    if tr['honest'] < 35 and tries == 0:
        return dict(kind='deny', paid=0)
    if days < 1 and tone == 'soft':
        return dict(kind='later', paid=0)
    give = min(cash, asked) if tone != 'soft' or tr['honest'] >= 50 else min(cash, asked) // 2
    if give >= asked:
        return dict(kind='paid', paid=asked)
    if give:
        return dict(kind='part', paid=give)
    return dict(kind='later', paid=0)


# ---------------------------------------------------------------- the rubbish fee
def fee(tr: dict, due: int, asked: int, tone: str, tries: int) -> dict:
    """A household asked for `asked` of a `due` fee. kind: 'paid', 'haggle' (offers `counter`),
    'excuse' (not today), 'refuse' (will not pay at all)."""
    will = _clamp(due * (0.6 + tr['honest'] / 100 * 0.5 + tr['budget'] / 100 * 0.2 - tr['stingy'] / 100 * 0.35), 0, due)
    if asked <= will:
        return dict(kind='paid', paid=asked)
    if tr['stingy'] > 75 and tr['honest'] < 40 and tries >= 1:
        return dict(kind='refuse', paid=0)
    if tone == 'strict' and tr['proud'] > 65:
        return dict(kind='refuse', paid=0)
    if tries >= 2:
        return dict(kind='excuse', paid=0)
    if will * 10 >= due * 6:
        return dict(kind='haggle', paid=0, counter=max(1, will))
    return dict(kind='excuse', paid=0)


# ---------------------------------------------------------------- a word back, a request, a refusal
def word(tr: dict, choice: str) -> str:
    """How someone takes what the player said: 'calm' (backs off), 'sulk' (grumbles but lets it be),
    'blowup' (it gets worse)."""
    heat = tr['rude'] + (100 - tr['mood']) // 2 + (tr['proud'] // 3 if choice in ('answer', 'refuse') else 0)
    if choice == 'away':
        heat -= 20
    if choice == 'answer':
        heat += 10
    return 'calm' if heat < 70 else 'sulk' if heat < 105 else 'blowup'


def validate_tr(v) -> bool:
    return isinstance(v, dict) and set(v) == set(KEYS) and all(type(x) is int and 0 <= x <= 100 for x in v.values())


# ================================================================ a debt book (fruit stall, drain calls)
DEBT_MAX = 16
DEBT_STATES = ('open', 'paid', 'gone', 'forgiven')


def debt_line(did: str, npc: int, who: str, task: str, day: int, owed: int, what: str) -> dict:
    return dict(id=did, npc=npc, who=who[:40], task=task[:60], day=day, owed=owed, paid=0, tries=0, state='open', what=what[:80], last=None, on=0)


def open_debts(book: list) -> list:
    return [x for x in book if x['state'] == 'open']


def trim_debts(book: list) -> list:
    """Every open debt stays (a new one is only written while fewer than DEBT_MAX are open);
    settled lines only while there is room, the newest first."""
    opened = open_debts(book)
    room = max(0, DEBT_MAX - len(opened))
    done = [x for x in book if x['state'] != 'open'][-room:] if room else []
    keep = {x['id'] for x in opened + done}
    return [x for x in book if x['id'] in keep]


def validate_debts(book, npcs: int, need) -> None:
    need(isinstance(book, list) and len(book) <= DEBT_MAX, 'Sổ nợ sai.')
    for x in book:
        need(isinstance(x, dict) and set(x) == {'id', 'npc', 'who', 'task', 'day', 'owed', 'paid', 'tries', 'state', 'what', 'last', 'on'}, 'Dòng sổ nợ sai.')
        need(isinstance(x['id'], str) and len(x['id']) <= 40 and isinstance(x['who'], str) and isinstance(x['task'], str) and isinstance(x['what'], str), 'Dòng sổ nợ sai.')
        need(type(x['npc']) is int and 0 <= x['npc'] < npcs and x['state'] in DEBT_STATES, 'Dòng sổ nợ sai.')
        for k in ('day', 'owed', 'paid', 'tries', 'on'):
            need(type(x[k]) is int and 0 <= x[k] <= 10 ** 7, 'Dòng sổ nợ sai.')
        need(x['paid'] <= x['owed'] and (x['last'] is None or (isinstance(x['last'], str) and len(x['last']) <= 200)), 'Dòng sổ nợ sai.')


CHASE_LINES = {
    'paid': ('{who}: “Rồi rồi, trả nè. Đòi gì đòi dai thế không biết.”', '{who} móc ví đếm đủ: “Xin lỗi nha, quên mất tiêu.”'),
    'part': ('{who}: “Có nhiêu đây thôi, cầm tạm đi, phần còn lại tính sau.”', '{who} dúi mấy tờ: “Đang kẹt, trả dần nha, đừng có hối.”'),
    'later': ('{who}: “Mai, mai chắc chắn luôn, hứa đó.”', '{who}: “Cuối tuần có lương là trả liền, gấp gì.”'),
    'deny': ('{who}: “Ủa trả rồi mà? Nhớ nhầm người rồi đó bà nội.”', '{who}: “Nợ hồi nào? Có giấy tờ gì không mà đòi?”'),
    'angry': ('{who}: “Đòi nợ kiểu xã hội đen vậy hả? Có mấy đồng làm như ghê lắm, vl.”', '{who} gân cổ: “Làm nhục người ta giữa đường, cút đi cho khuất mắt!”'),
    'gone': ('Hàng xóm bảo {who} dọn đi đâu mất rồi, số điện thoại cũng không liên lạc được.', 'Phòng trọ của {who} đã có người khác thuê. Khoản này coi như mất.'),
}
TONE_LABEL = {'soft': 'nhắc nhẹ', 'straight': 'nói thẳng', 'family': 'nhờ người nhà'}


def chase_action(s: dict, c: dict, career: str, book: list, p: dict, persona_of) -> dict:
    """The player's own move: chase one debt (tone, and optionally how much to ask for now) or write it off."""
    from . import kit
    x = next((r for r in book if r['id'] == p.get('debt')), None)
    kit.need(x and x['state'] == 'open', 'Khoản nợ này không còn.')
    who = x['who']
    if p.get('forgive') is True:
        x.update(state='forgiven', last=f'Xóa nợ cho {who}.')
        c['xp'] += 3
        return dict(message=f'🤝 Xóa khoản nợ {x["owed"] - x["paid"]} xu cho {who}. Coi như làm phúc.')
    kit.need(x['on'] != c['day'] or x['tries'] == 0, f'Hôm nay đã đòi {who} rồi. Mai hẵng đòi tiếp.')
    tone = kit.one_of(p.get('tone'), TONES, 'Chọn cách đòi.')
    owed = x['owed'] - x['paid']
    asked = kit.integer(p['amount'], 1, owed) if p.get('amount') is not None else owed
    tr = traits(x['id'], persona_of(x['npc']))
    r = chase(tr, owed, tone, asked, x['tries'], c['day'] - x['day'])
    x['tries'] += 1
    x['on'] = c['day']
    line = CHASE_LINES[r['kind']][roll('chase', x['id'], x['tries']) % 2].format(who=who)
    if r['paid']:
        kit.money(s, c, r['paid'], f'{who} trả nợ'[:120], x['task'], 'debt_paid')
        x['paid'] += r['paid']
    if x['paid'] >= x['owed']:
        x['state'] = 'paid'
    if r['kind'] == 'gone':
        x['state'] = 'gone'
    if r['kind'] == 'angry':
        kit.review(s, c, kit.npc_id(career, x['npc']), 2, 'Có mấy xu mà đòi nợ giữa đường như đòi nợ thuê. Mất hết cả hứng mua bán.', x['id'])
        box = c.get('incidents')
        if isinstance(box, dict) and isinstance(box.get('trust'), int):
            box['trust'] = max(0, box['trust'] - 1)
    x['last'] = line[:200]
    head = {'paid': '💵', 'part': '💵', 'later': '⏳', 'deny': '🙄', 'angry': '😤', 'gone': '👻'}[r['kind']]
    tail = f' (+{r["paid"]} xu)' if r['paid'] else ''
    return dict(message=f'{head} {TONE_LABEL[tone].capitalize()}: {line}{tail}', correct=r['kind'] not in ('angry', 'gone'), celebrate=r['kind'] == 'paid')


def auto_repay(s: dict, c: dict, career: str, book: list, persona_of) -> list:
    """At the start of a day, honest debtors come back and pay by themselves (the rest wait to be chased)."""
    from . import kit
    notes = []
    for x in open_debts(book):
        if x['tries'] or c['day'] <= x['day'] or traits(x['id'], persona_of(x['npc']))['honest'] < 65:
            continue
        owed = x['owed'] - x['paid']
        kit.money(s, c, owed, f'{x["who"]} tự mang tiền nợ tới trả'[:120], x['task'], 'debt_paid')
        x.update(paid=x['owed'], state='paid', last=f'{x["who"]} tự tới trả đủ, còn xin lỗi vì để lâu.')
        notes.append(f'💵 {x["who"]} tự mang {owed} xu tới trả nợ.')
    return notes


def public_debts(book: list) -> list:
    return [dict(x) for x in book]


# ================================================================ trouble: a runtime scene with the player's own move
# A career keeps `trouble_initial()` in its data. An event is planned from the day (like the desk
# surprises) and fired between jobs; it holds its facts (who, how much) and the player answers with
# a choice and, where it fits, an amount. The career resolves it (resolve functions stay in the career).
TROUBLE_LOG = 30


def trouble_initial() -> dict:
    return dict(ev=None, last=None, log=[], day=0, fired=0, seq=0)


def trouble_plan(career: str, day: int, rate: int, first_day: int = 2) -> list:
    """After how many finished jobs today a trouble comes (deterministic from the day)."""
    if day < first_day:
        return []
    out = []
    for n in (1, 3):
        if roll('trouble-plan', career, day, n) < rate:
            out.append(n)
    return out


def trouble_due(tb: dict, career: str, day: int, done: int, rate: int, first_day: int = 2) -> bool:
    if tb['ev'] is not None:
        return False
    if tb['day'] != day:
        tb.update(day=day, fired=0)
    plan = trouble_plan(career, day, rate, first_day)
    return len([p for p in plan if done >= p]) > tb['fired']


def trouble_open(tb: dict, kind: str, day: int, npc: int, facts: dict) -> dict:
    tb['seq'] += 1
    tb['fired'] += 1
    tb['ev'] = dict(id=f'tr-{tb["seq"]}', kind=kind, day=day, npc=npc, step=0, tries=0, facts=dict(facts))
    return tb['ev']


def trouble_close(tb: dict, outcome: str, good, choice: str, title: str, emoji: str) -> None:
    ev = tb['ev']
    tb['last'] = dict(id=ev['id'], kind=ev['kind'], title=title[:80], emoji=emoji, outcome=outcome[:400], good=good, day=ev['day'], choice=choice)
    tb['log'] = (tb['log'] + [dict(id=ev['id'], kind=ev['kind'], day=ev['day'], choice=choice, good=good)])[-TROUBLE_LOG:]
    tb['ev'] = None


def validate_trouble(tb, kinds, need) -> None:
    need(isinstance(tb, dict) and set(trouble_initial()) <= set(tb), 'Chuyện rắc rối sai.')
    for k in ('day', 'fired', 'seq'):
        need(type(tb[k]) is int and 0 <= tb[k] <= 10 ** 9, 'Chuyện rắc rối sai.')
    need(isinstance(tb['log'], list) and len(tb['log']) <= TROUBLE_LOG, 'Chuyện rắc rối sai.')
    for h in tb['log']:
        need(isinstance(h, dict) and h.get('kind') in kinds and h.get('good') in (True, False, None), 'Chuyện rắc rối sai.')
    ev = tb['ev']
    if ev is not None:
        need(isinstance(ev, dict) and ev.get('kind') in kinds and isinstance(ev.get('facts'), dict) and len(ev['facts']) <= 12, 'Chuyện rắc rối sai.')
        for k in ('day', 'npc', 'step', 'tries'):
            need(type(ev.get(k)) is int and 0 <= ev[k] <= 10 ** 7, 'Chuyện rắc rối sai.')
        for v in ev['facts'].values():
            need(isinstance(v, (int, str, bool)) and (not isinstance(v, str) or len(v) <= 200), 'Chuyện rắc rối sai.')
    last = tb['last']
    need(last is None or (isinstance(last, dict) and last.get('kind') in kinds and isinstance(last.get('outcome'), str)), 'Chuyện rắc rối sai.')
