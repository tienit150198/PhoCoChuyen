"""Làm sai thì phải chịu: order mistakes that cost you, in proportion.

Every career records what went wrong at the hand-off with `slip(t, code, sev, text)`
(sev 1 = a small slip, 2 = a clear mistake, 3 = a serious one; `safety=True` for
wrong medicine, ignored allergies, alcohol to a minor, unsafe wiring, spoiled
food…). Then, in one place:

* `react()` decides how the customer takes it at the counter, from the persona
  and how bad it is: grumbles and pays, asks for money back, asks for a remake
  (when the career allows one), or leaves without paying. Money only moves
  through engine.money() with a category, and never twice for the same task;
* feedback.evaluate() calls `adjust()` so the review stars drop with severity
  (5 − points, safety → 1★) and mistake_lines weaves the actual mistake into the
  review text;
* repeat or serious mistakes escalate (`_escalate`, once per task): a complaint
  report on the app, the street's trust (c['incidents']['trust']) and, in the
  office jobs, the boss's trust; safety-critical ones also bring an inspection
  the next day through the incidents layer (a chain incident follow-up).

Everything is deterministic from the task id; nothing here is rolled twice.
State: t['slips'] (list) and t['reaction'] (dict|None) on the task, and
c['slipbook'] per workplace (created lazily, optional for old saves).
"""
from __future__ import annotations

import hashlib

MAX_SLIPS = 8
BOOK_LOG = 40
REPORTS_PER_DAY = 2
KINDS = ('accept', 'grumble', 'discount', 'refund', 'walkout', 'remake', 'refuse')
# How much of the price the customer takes back for each reaction.
CUT = dict(accept=0, grumble=0, discount=25, refund=50, walkout=100, refuse=100, remake=0)
# Patient people shrug off a small slip; strict ones do not.
TOLERANCE = dict(warm=1, quiet=1, parent_kind=1, genz=0, parent_worried=0, sour=-1, picky=-1, bossy=-1, parent_strict=-1,
                 knowitall=-1, rude=-1, entitled=-1, drama=-1, troll=0, parent_knowitall=-1, parent_rude=-1)
# Which chain incident a safety-critical mistake brings the next day, per career.
INSPECTION = dict(
    pharmacy='slip_drug_inspect',
    milk_tea='slip_food_inspect', restaurant='slip_food_inspect', cafe_bakery='slip_food_inspect',
    grocery='slip_food_inspect', farm='slip_food_inspect', homestay='slip_food_inspect',
    repair='slip_safety_inspect', salon='slip_safety_inspect', pet_care='slip_safety_inspect',
    delivery='slip_safety_inspect', mother_baby='slip_safety_inspect', florist='slip_safety_inspect',
    tour_guide='slip_safety_inspect', teacher='slip_safety_inspect',
)
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting')


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _eng():
    from . import engine
    return engine


# ---------------------------------------------------------------- recording
def slip(t: dict, code: str, sev: int, text: str, note: str = '', safety: bool = False) -> None:
    """Record one mistake on the task (the same code once). `text` is what the customer
    says about it (goes into the reaction and the review), `note` a short fact."""
    rows = t.setdefault('slips', [])
    if any(r['code'] == code for r in rows) or len(rows) >= MAX_SLIPS:
        return
    rows.append(dict(code=str(code)[:32], sev=max(1, min(3, int(sev))), text=str(text)[:200],
                     note=str(note or '')[:120], safety=bool(safety)))


def downgrade(t: dict, code: str, text: str, note: str = '') -> None:
    """The customer sent it back and got it redone: what is left is one small slip."""
    t['slips'] = []
    slip(t, code, 1, text, note)


def slips(t: dict) -> list:
    return t.get('slips') or []


def points(t: dict) -> int:
    return sum(r['sev'] for r in slips(t))


def safety(t: dict) -> bool:
    return any(r.get('safety') for r in slips(t))


def star_cap(t: dict) -> int:
    """One small slip 4★, a clear mistake 3★, a serious one 2★, five points or safety 1★."""
    if not slips(t):
        return 5
    if safety(t):
        return 1
    pts = points(t)
    return 1 if pts >= 5 else max(2, 5 - pts)


def adjust(t: dict, criteria: list, cap: int) -> tuple[list, int]:
    """feedback.evaluate hook: the recorded mistakes pull a criterion and the stars down."""
    rows = slips(t)
    if not rows:
        return criteria, cap
    score = star_cap(t)
    worst = max(rows, key=lambda r: r['sev'])
    n = len(rows)
    note = worst['note'] or (f'sai {n} chỗ so với lời dặn' if n > 1 else 'làm sai điều đã dặn')
    out = [dict(x) for x in criteria]
    hit = next((x for x in out if x['key'] in ('accuracy', 'order')), None)
    if hit:
        if hit['score'] > score:
            hit['score'] = score
            hit['note'] = note
    else:
        out.append(dict(key='order', label='Đúng lời dặn', score=score, note=note))
    return out, min(cap, score)


# ---------------------------------------------------------------- the counter
def persona(c: dict, t: dict) -> str:
    from .feedback import persona_for
    return persona_for(t['career'], t['npc'])


def decide(c: dict, t: dict, remake: bool = False) -> str:
    """How this customer takes the mistakes (pure: the same task always decides the same)."""
    rows = slips(t)
    if not rows:
        return 'accept'
    if safety(t):
        return 'refuse'
    pts = points(t)
    if t.get('remade'):
        # They already sent it back once: the old mistake is only the wait now,
        # and only what is wrong with the new one counts in full.
        pts = sum(r['sev'] for r in rows if r['code'] != 'returned')
    level = max(1, pts) - TOLERANCE.get(persona(c, t), 0)
    # Some days people are softer, some days harder: ±1 from the task id.
    roll = _hash('slip-mood', t['id'], len(rows)) % 6
    level += 1 if roll == 0 else -1 if roll == 5 else 0
    if not pts:
        level = min(level, 1)
    elif max(r['sev'] for r in rows if r['code'] != 'returned' or not t.get('remade')) >= 2:
        level = max(level, 1)   # a clear mistake is never shrugged off in silence
    if level >= 4 and pts < 4:
        level = 3
    if level <= 0:
        return 'accept'
    if level == 1:
        return 'grumble'
    if remake and not t.get('remade') and level in (2, 3):
        return 'remake'
    if level == 2:
        return 'discount'
    if level == 3:
        return 'refund'
    return 'walkout'


def _line(kind: str, t: dict, cut: int) -> str:
    from . import mistake_lines as ml
    return ml.reaction_line(kind, t, cut)


def react(s: dict, c: dict, t: dict, price: int, remake: bool = False, prepaid: bool = False,
          who: str = 'Khách') -> dict:
    """Decide the hand-off reaction once and settle the money.

    price    what the customer pays for this job (the reward passed to complete());
    remake   the career can redo the item (the caller then returns it and does NOT complete);
    prepaid  the price was already collected: the refund goes out now with money('refund').
    Returns dict(kind, pay, cut, line, message). `pay` is what the caller should still pass
    to complete() (0 when prepaid). Calling it again for the same task returns the stored
    decision without moving money again."""
    old = t.get('reaction')
    if isinstance(old, dict) and old.get('kind') != 'remake':
        pay = 0 if prepaid else max(0, int(price) - old['cut'])
        return dict(old, pay=pay)
    kind = decide(c, t, remake)
    price = max(0, int(price))
    cut = price * CUT[kind] // 100
    line = _line(kind, t, cut)
    if kind == 'remake':
        t['remade'] = True
        t['reaction'] = dict(kind='remake', cut=0, line=line, day=c['day'])
        return dict(kind=kind, pay=0, cut=0, line=line, message=f'{who}: “{line}”')
    pay = price - cut
    if prepaid:
        take = min(cut, c['money'])
        if take:
            _eng().money(s, c, -take, f'Hoàn tiền cho khách: {t.get("title", "")}'[:120], t['id'], 'refund')
        cut = take
        pay = 0
    t['reaction'] = dict(kind=kind, cut=cut, line=line, day=c['day'])
    notes = _escalate(s, c, t) if slips(t) else []
    msg = f'{who}: “{line}”' if slips(t) else ''
    if cut:
        msg += f' (−{cut} xu)'
    if notes:
        msg += ' ' + ' '.join(notes)
    return dict(kind=kind, pay=pay, cut=cut, line=line, message=msg.strip())


def settle(s: dict, c: dict, t: dict, price: int, **kw) -> tuple[int, str]:
    """Shortcut for careers: (reward to pass to complete, message to show)."""
    r = react(s, c, t, price, **kw)
    return r['pay'], r['message']


# ---------------------------------------------------------------- escalation
def book(c: dict) -> dict:
    b = c.get('slipbook')
    if not isinstance(b, dict):
        b = c['slipbook'] = dict(v=1, day=0, today=0, reports_today=0, total=0, reports=0, log=[])
    if b['day'] != c['day']:
        b.update(day=c['day'], today=0, reports_today=0)
    return b


def _escalate(s: dict, c: dict, t: dict) -> list[str]:
    """Once per task: count it, and for repeat or serious mistakes file a complaint
    (app report, trust), plus an inspection tomorrow for safety-critical ones."""
    b = book(c)
    if any(x['task'] == t['id'] for x in b['log']):
        return []
    pts = points(t)
    b['today'] += pts
    b['total'] += 1
    worst = max(slips(t), key=lambda r: r['sev'])
    b['log'] = (b['log'] + [dict(task=t['id'], day=c['day'], code=worst['code'], sev=pts, report=False)])[-BOOK_LOG:]
    repeat = sum(1 for x in b['log'] if x['day'] == c['day']) >= 3 and b['today'] >= 5
    serious = pts >= 3 or safety(t)
    notes = []
    if not (serious or repeat) or b['reports_today'] >= REPORTS_PER_DAY and not safety(t):
        return notes
    e = _eng()
    from . import mistake_lines as ml
    b['reports_today'] += 1
    b['reports'] += 1
    b['log'][-1]['report'] = True
    text = ml.report_text(t, repeat and not serious)
    if t['npc'] in e.NPC_INDEX:
        post = e.add_feed(s, c, t['npc'], text, t['id'], None, 'post')
        post['report'] = True
    e.metric(c, 'complaints')
    e.log(s, c, 'complaint', text, t['npc'], t['id'])
    notes.append('📣 Khách gửi báo cáo lên app.')
    drop = 4 if safety(t) else 2
    box = c.get('incidents')
    if isinstance(box, dict) and isinstance(box.get('trust'), int):
        box['trust'] = max(0, min(100, box['trust'] - drop))
    if t['career'] in OFFICE:
        o = (c.get('ext', {}).get('data') or {}).get('office')
        if isinstance(o, dict) and 'trust' in o:
            from .careers import office
            office.trust(o, -drop)
            office.note(o, c['day'], f'Sếp nhận phản ánh về hồ sơ “{t.get("title", "")}”.'[:160], 'bad')
            notes.append('Sếp đã nhận phản ánh: uy tín với sếp giảm.')
    if safety(t):
        sid = INSPECTION.get(t['career'])
        from . import incidents as incs
        from .incident_content import INDEX
        if isinstance(box, dict) and sid in INDEX and isinstance(box.get('follow'), list):
            before = len(box['follow'])
            incs._schedule(box, (sid, 1), c['day'], t['id'])
            if len(box['follow']) > before:
                notes.append('Chuyện này có thể bị kiểm tra.')
    return notes


# ---------------------------------------------------------------- saves
def validate_task(t: dict) -> None:
    e = _eng()
    rows = t.get('slips')
    if rows is not None:
        e.need(isinstance(rows, list) and len(rows) <= MAX_SLIPS, 'Ghi nhận lỗi của công việc sai.', 'invalid_save')
        for r in rows:
            e.need(isinstance(r, dict) and type(r.get('safety')) is bool, 'Ghi nhận lỗi sai.', 'invalid_save')
            e.clean_text(r.get('code'), 32)
            e.integer(r.get('sev'), 1, 3)
            e.clean_text(r.get('text'), 200, 0)
            e.clean_text(r.get('note'), 120, 0)
    x = t.get('reaction')
    if x is not None:
        e.need(isinstance(x, dict) and x.get('kind') in KINDS, 'Phản ứng của khách sai.', 'invalid_save')
        e.integer(x.get('cut'), 0, 10 ** 6)
        e.integer(x.get('day'), 0, 10 ** 7)
        e.clean_text(x.get('line'), 300, 0)
    if 'remade' in t:
        e.need(type(t['remade']) is bool, 'Ghi nhận làm lại sai.', 'invalid_save')


def validate(c: dict) -> None:
    b = c.get('slipbook')
    if b is None:
        return
    e = _eng()
    e.need(isinstance(b, dict) and b.get('v') == 1, 'Sổ phàn nàn sai.', 'invalid_save')
    for k in ('day', 'today', 'reports_today', 'total', 'reports'):
        e.integer(b.get(k), 0, 10 ** 7)
    e.need(isinstance(b.get('log'), list) and len(b['log']) <= BOOK_LOG, 'Sổ phàn nàn sai.', 'invalid_save')
    for x in b['log']:
        e.need(isinstance(x, dict) and type(x.get('report')) is bool, 'Sổ phàn nàn sai.', 'invalid_save')
        e.clean_text(x.get('task'), 60)
        e.clean_text(x.get('code'), 32)
        e.integer(x.get('day'), 0, 10 ** 7)
        e.integer(x.get('sev'), 0, 100)
