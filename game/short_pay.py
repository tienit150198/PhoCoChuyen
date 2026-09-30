"""Khách đưa thiếu tiền: a customer sometimes hands over less than the bill.

Shared by the cash till (game/careers/till.py: clothing, the pet shop, the trà đá stall). When a
till record is made for a task (`till.new(..., c=c, t=t)`), `roll()` decides once, from the task
id, whether this customer pays short, who they are and by how much. The record keeps it as
rec['sp']; the notes on the counter (rec['tender']) are exactly what was handed over, so a careful
player sees it by reading the notes or by pressing "Đếm lại tiền khách đưa" (`act(..., 'count')`).

Who (hidden until the story shows it):
  honest  two notes stuck together, a miscount;
  elder   an absent-minded older neighbour;
  kid     a child who simply does not have enough;
  cheat   a customer who short-pays on purpose ("đưa lẹ cho rối"), maybe again next time.

The paths (command `<prefix>short` {task, choice}):
  count   count the notes again: reveals the gap (or "đủ rồi");
  ask     remind the customer: honest and elder pay the rest (a small tip or closeness), a kid
          cannot (then owe / less / give), a cheat denies it (then let / police);
  police  call the ward police: time passes and the queue gets impatient; a cheat pays up
          (repeat offenders are noted, the street hears of it), anyone else pays too, but it
          was an overreaction: a "làm quá" slip in the review, closeness and the street's trust drop;
  let     accept the gap knowingly, a small goodwill;
  owe / less / give (kid), let / police (cheat).
Nobody noticed: the sale goes through short, `settle()` names the gap at the till count
("Tối kiểm két thiếu X xu"), an employee's owner trusts them a little less.

Money moves only through engine.money(): what the customer never pays is `loss` (the career takes
it off the pay, like kept excess change), a tip is category 'tip' with t['tip_given'] (tip
contract), a debt paid back later is 'revenue' on the original task. Everything is seeded from the
task id and stored; a choice or a settle never runs twice.

State: rec['sp'] on a till record, c['shortpay'] per workplace (IOUs, repeat offenders, a short
log; created lazily, optional in older saves).
"""
from __future__ import annotations

import hashlib
import os

VERSION = 1
KINDS = ('honest', 'elder', 'kid', 'cheat')
STAGES = ('hidden', 'open', 'kid', 'cheat', 'done')
FIRST = ('ask', 'police', 'let')
FOLLOW = dict(kid=('owe', 'less', 'give'), cheat=('let', 'police'))
CHOICES = ('count',) + FIRST + ('owe', 'less', 'give')
OUTCOMES = (None, 'paid', 'police', 'let', 'owe', 'less', 'give', 'missed')
# What the customer can be short by, per kind (only amounts up to half the bill).
AMOUNTS = dict(honest=(5, 10, 20, 50, 100), elder=(2, 5, 10, 20), kid=(2, 5, 10), cheat=(10, 20, 50, 100))
MIN_PRICE, MAX_PRICE = 6, 2000
RATE = 60          # per mille, from the third day at a workplace
RATE_EARLY = 25    # per mille on day 2; never on day 1 (the guided first day)
CHEATY = ('sour', 'bossy', 'genz', 'rude', 'entitled', 'troll', 'drama')
CHEAT_P, CHEAT_AGAIN_P = 30, 60          # percent, among the customers who could
# People who are never "customers" at the till (the owner, the staff, an inspector…).
NOT_CUSTOMER = ('Chủ tiệm', 'Chủ quán', 'Trông tiệm', 'mẹ chị Vy', 'Tổ kiểm tra', 'Quản lý kênh')
POLICE_TURNS = 1   # the wait for the ward police: one more clock step (20 minutes)
QUEUE_WAIT = 8     # patience the others in the queue lose meanwhile
OWED_MAX, LOG_MAX, CHEATS_MAX = 20, 30, 40
BACK_P = dict(owe=70, give=45)            # a kid pays back tomorrow / a parent comes by to thank
TIP_P = 35                                # honest customer thanks you for the gentle reminder
DELTA = dict(ask_honest=1, ask_elder=2, owe=1, owe_back=2, give=3, give_back=1, let=1,
             police_wrong=-4, police_cheat=-3)
TRUST = dict(police_wrong=-1, police_cheat=2, police_repeat=1, missed_employee=-2)
DEV_ENV = 'MNL_SHORTPAY'   # MNL_DEV=1 only: "on" forces a short payment, a kind name forces that kind


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _eng():
    from . import engine
    return engine


def _pick(rows, *seed):
    return rows[_hash(*seed) % len(rows)]


def _forced() -> str | None:
    """Dev sweeps only (never in production: MNL_DEV is unset there)."""
    if os.environ.get('MNL_DEV') != '1':
        return None
    v = os.environ.get(DEV_ENV, '')
    return v if v in KINDS or v == 'on' else None


# ---------------------------------------------------------------- the customer
def _npc(t: dict) -> dict:
    from .content import NPC_INDEX
    return NPC_INDEX.get(t.get('npc')) or {}


def _persona(c: dict, t: dict) -> str:
    try:
        from . import consequences as cq
        return cq.persona(c, t)
    except Exception:
        return 'quiet'


def is_kid(t: dict) -> bool:
    from . import closeness as qn
    n = _npc(t)
    name, role = n.get('display_name', ''), n.get('role', '').lower()
    return qn.is_kid(t.get('npc')) or name.startswith(('Bé ', 'Cu ')) or 'lớp ' in role


def is_elder(t: dict) -> bool:
    n = _npc(t)
    name, role = n.get('display_name', ''), n.get('role', '').lower()
    return name.startswith(('Bà ', 'Ông ', 'Cụ ')) or 'lớn tuổi' in role or 'hưu trí' in role


def customer(t: dict) -> bool:
    n = _npc(t)
    return bool(n) and not any(w in n.get('role', '') for w in NOT_CUSTOMER)


def _kind(c: dict, t: dict, forced: str | None) -> str:
    if forced in KINDS:
        return forced
    if is_kid(t):
        return 'kid'
    if is_elder(t):
        return 'elder'
    again = _cheats(c).get(t['npc'], 0) > 0
    if _persona(c, t) in CHEATY and _hash('sp-cheat', t['id']) % 100 < (CHEAT_AGAIN_P if again else CHEAT_P):
        return 'cheat'
    return 'honest'


def roll(c: dict, t: dict, price: int) -> dict | None:
    """Pure: does this customer pay short, who are they and by how much (None: they pay in full)."""
    from .careers import till
    forced = _forced()
    price = int(price)
    if not isinstance(t, dict) or not t.get('id') or not customer(t) or not MIN_PRICE <= price <= MAX_PRICE:
        return None
    b = c.get('shortpay') if isinstance(c.get('shortpay'), dict) else {}
    prev = next((r for r in reversed(b.get('log') or []) if r.get('task') == t['id']), None)
    if prev:
        # The bill was opened again after the story was settled: it stays settled (nothing re-rolls).
        if prev['short'] > price // 2:
            return None
        got = prev['short'] if prev['outcome'] in ('paid', 'police') else 0
        return dict(v=VERSION, kind=prev['kind'], short=prev['short'], stage='done', outcome=prev['outcome'], path=[], line='',
                    got=got, repeat=False)
    if not forced:
        day = t.get('day') if type(t.get('day')) is int else c.get('day', 1)
        rate = 0 if day <= 1 else RATE_EARLY if day == 2 else RATE
        if _hash('sp-roll', t['id']) % 1000 >= rate:
            return None
    kind = _kind(c, t, forced)
    options = [x for x in AMOUNTS[kind] if x <= price // 2 and len(till.greedy(price - x)) + len(till.greedy(x)) <= 20]
    if not options:
        return None
    short = _pick(options, 'sp-amount', t['id'])
    return dict(v=VERSION, kind=kind, short=short, stage='hidden', outcome=None, path=[], line='', got=0,
                repeat=_cheats(c).get(t['npc'], 0) > 0 and kind == 'cheat')


def tender(price: int, sp: dict) -> list[int]:
    """The notes a short-paying customer hands over: an exact-looking amount, `short` below the bill."""
    from .careers import till
    return till.greedy(price - sp['short']) + (till.greedy(sp['short']) if sp['got'] else [])


def carry(old: dict | None, price: int) -> dict | None:
    """A bill made again for the same price keeps a story already under way (nothing re-rolls)."""
    sp = (old or {}).get('sp') if isinstance(old, dict) else None
    if isinstance(sp, dict) and sp['stage'] != 'hidden' and old.get('price') == price and old.get('outcome') is None:
        return sp
    return None


# ---------------------------------------------------------------- the workplace book
def book(c: dict) -> dict:
    b = c.get('shortpay')
    if not isinstance(b, dict):
        b = c['shortpay'] = dict(v=VERSION, owed=[], cheats={}, log=[])
    return b


def _cheats(c: dict) -> dict:
    b = c.get('shortpay')
    return b['cheats'] if isinstance(b, dict) and isinstance(b.get('cheats'), dict) else {}


def _flag(c: dict, npc: str) -> None:
    ch = book(c)['cheats']
    if npc in ch or len(ch) < CHEATS_MAX:
        ch[npc] = min(99, ch.get(npc, 0) + 1)


def _log(c: dict, t: dict, sp: dict) -> None:
    b = book(c)
    b['log'] = (b['log'] + [dict(task=t['id'], day=c['day'], kind=sp['kind'], outcome=sp['outcome'], short=sp['short'])])[-LOG_MAX:]


# ---------------------------------------------------------------- effects
def _close(s: dict, t: dict, delta: int, text: str) -> None:
    if not delta:
        return
    try:
        from . import closeness as qn
        if isinstance(s.get('journey'), dict):
            qn.change(s, t['npc'], delta, text, 'work')
    except Exception:  # closeness is a flavour: it never blocks the till
        pass


def _street(c: dict, delta: int) -> None:
    box = c.get('incidents')
    if delta and isinstance(box, dict) and type(box.get('trust')) is int:
        box['trust'] = max(0, min(100, box['trust'] + delta))


def _owner(s: dict, c: dict, t: dict, delta: int) -> bool:
    """An employee's owner hears the till came up short: "Điểm tin cậy của chủ" (game/abandon.py)."""
    from . import abandon as ab
    cid = t['career']
    if not ab._employed(cid) or ab._kind(cid, c) != 'employer' or not isinstance(s.get('journey'), dict):
        return False
    row = ab._place_row(ab.book(s), cid)
    row['trust'] = max(0, min(100, row['trust'] + delta))
    return True


def _feed(s: dict, c: dict, t: dict, text: str, kind: str = 'post') -> None:
    """A neighbour (another regular of this place) tells the street."""
    e = _eng()
    career = t['career']
    npcs = [k for k in (f'{career}_npc_{i:02d}' for i in range(1, 9)) if k in e.NPC_INDEX and k != t['npc']]
    if npcs:
        e.add_feed(s, c, _pick(npcs, 'sp-feed', t['id']), text, t['id'], None, kind)


def _pay_rest(rec: dict, sp: dict) -> None:
    from .careers import till
    rec['tender'] = list(rec['tender']) + till.greedy(sp['short'])
    sp['got'] = sp['short']


def _say(sp: dict, step: str, line: str) -> str:
    sp['path'] = (sp['path'] + [step])[-4:]
    sp['line'] = line[:300]
    return line


# ---------------------------------------------------------------- the lines (Vietnamese literals)
ASK = dict(
    honest=('{who} lục ví, đỏ mặt: “Ấy chết, hai tờ dính vào nhau! Xin lỗi nha.” rồi đưa thêm {short} xu.',
            '{who} đếm lại, bật cười: “Trời, đếm hụt thật. Cảm ơn đã nhắc khéo nha.” rồi đưa thêm {short} xu.'),
    elder=('{who} đếm lại từng tờ, cười hiền: “Già rồi mắt kém, may có con nhắc.” rồi đưa thêm {short} xu.',
           '{who} mở khăn tay lấy thêm {short} xu: “Ờ ha, nãy đếm lộn. Con thật thà quá.”'),
    kid=('{who} lục túi mãi, mặt xịu xuống: “Con… con chỉ có nhiêu đó thôi.”',
         '{who} lộn hết túi áo ra, rơm rớm: “Con tưởng đủ rồi…”'),
    cheat=('{who} xua tay: “Đưa đủ rồi mà, đếm kiểu gì vậy?” rồi quay mặt đi.',
           '{who} gắt: “Nãy đưa đủ rồi, giờ đòi nữa là sao?” rồi nhìn ra cửa.'),
)
AGAIN = 'Hình như lần trước {who} cũng đưa thiếu ở quầy này.'
KID = dict(
    owe='Bạn ghi sổ nợ {short} xu: “Mai con mang ra trả nha.” {who} gật đầu lia lịa.',
    less='{who} để lại bớt một món cho vừa tiền. Hóa đơn bớt {short} xu.',
    give='Bạn xua tay: “Thôi, cho con luôn.” {who} cười tít mắt, cảm ơn rối rít.',
)
LET = dict(
    honest='Bạn không nói gì, coi như bớt cho {who} {short} xu.',
    elder='Bạn không nói gì, coi như bớt cho {who} {short} xu. Người già đếm nhầm là chuyện thường.',
    kid='Bạn không nói gì, coi như bớt cho {who} {short} xu.',
    cheat='Bạn thở dài cho qua. {who} đi thẳng ra cửa, không ngoái lại. Mất {short} xu.',
)
WAIT = 'Bạn gọi công an khu vực. Chờ gần hai mươi phút, khách xếp hàng phía sau bắt đầu sốt ruột.'
POLICE = dict(
    cheat='Anh công an khu vực tới, mời {who} đếm lại tiền ngay trên quầy. {who} hết đường chối, trả đủ {short} xu. '
          'Anh dặn: “Lần sau có chuyện cứ báo, tụi anh ở ngay đầu phố.”',
    honest='Anh công an khu vực tới. {who} đếm lại, đỏ mặt: “Tôi nhầm thật mà, đâu cần làm vậy…” rồi trả đủ {short} xu. '
           'Anh công an nói nhỏ: “Chuyện nhỏ vậy, lần sau mình nhắc khách nhẹ nhàng trước nhé.”',
    elder='{who} run run đếm lại trước mặt anh công an, trả đủ {short} xu, mắt đỏ hoe. '
          'Anh công an nói nhỏ: “Người lớn tuổi đếm nhầm thôi, lần sau mình nói chuyện với bà con trước nhé.”',
    kid='{who} òa khóc. Mẹ bé chạy ra trả đủ {short} xu, nhìn quầy không vui. '
        'Anh công an nói nhỏ: “Với trẻ con, mình hỏi han trước đã nhé.”',
)
REPEAT = 'Hóa ra {who} đã đưa thiếu ở quầy này mấy lần. Công an ghi tên vào sổ theo dõi, cô Lụa ghé khen quầy làm đúng.'
NEWS = ('Nghe nói có người đưa thiếu tiền ở {place}, bị công an khu vực mời đếm lại ngay trên quầy. Buôn bán phải vậy!',
        'Hôm nay công an khu vực ghé {place} vì vụ khách cố tình đưa thiếu tiền. Mọi người trả tiền nhớ đếm kỹ nha.')
OVERREACT = dict(
    honest='Tôi đếm nhầm có mấy xu mà gọi cả công an tới, làm quá!',
    elder='Người già đếm nhầm mà gọi công an tới, làm quá.',
    kid='Con nít thiếu mấy đồng mà gọi công an, làm quá!',
)
MISSED = 'Tối kiểm két thiếu {short} xu: {who} đưa thiếu mà lúc nhận không ai đếm lại.'
LESSON = ('Lần sau nhận tiền nhớ đếm lại trước khi cất vào két.',
          'Nhận tiền xong đếm lại một lượt, thiếu thì nhắc khách ngay tại quầy.',
          'Tiền trao tay nên đếm ngay trước mặt khách.')
OWNER = 'Chủ nghe chuyện két thiếu, nhắc nhẹ: lần sau đếm lại giúp.'
KNOWN = dict(let='Két bớt {short} xu cho {who}.', less='Két bớt {short} xu vì {who} để lại một món.',
             give='Cho {who} {short} xu.', owe='Ghi nợ {short} xu cho {who}.')
BACK = dict(owe='{who} chạy ra trả {short} xu còn nợ hôm trước: “Con cảm ơn nha!”',
            give='Mẹ {who} ghé cảm ơn, gửi lại {short} xu: “Cảm ơn đã thương cháu.”')
GONE = 'Sổ nợ còn {short} xu của {who}. Chắc bé quên mất rồi, thôi coi như cho.'


def _fmt(text: str, who: str, sp: dict) -> str:
    return text.format(who=who, short=sp['short'])


# ---------------------------------------------------------------- the player's side
def pending(rec: dict | None) -> bool:
    """A short payment was noticed and still waits for a decision (the hand-over is blocked)."""
    sp = (rec or {}).get('sp')
    return isinstance(sp, dict) and sp['stage'] in ('open', 'kid', 'cheat')


def act(s: dict, c: dict, t: dict, rec: dict | None, choice, who: str = 'Khách') -> dict:
    """`<prefix>short` {task, choice}: count the notes again, or decide what to do about a gap."""
    e = _eng()
    e.need(isinstance(rec, dict), 'Khách chưa đưa tiền mặt.')
    e.need(rec.get('outcome') is None, 'Tiền của khách này đã tính xong.')
    e.need(isinstance(choice, str) and choice in CHOICES, 'Chọn một cách xử lý nhé.')
    sp = rec.get('sp') if isinstance(rec.get('sp'), dict) else None
    paid = sum(rec['tender'])
    if choice == 'count':
        if sp and sp['stage'] == 'done' and not sp['got']:
            return dict(message='🔍 ' + (sp['line'] or f'Đếm lại: {who} đưa {paid} xu, còn thiếu {sp["short"]} xu.'))
        if not sp or sp['stage'] == 'done':
            rec['counted'] = True
            return dict(message=f'🔍 Đếm lại: {who} đưa {paid} xu, hóa đơn {rec["price"]} xu. Đủ rồi.')
        if sp['stage'] == 'hidden':
            sp['stage'] = 'open'
            line = f'Đếm lại: {who} đưa {paid} xu, hóa đơn {rec["price"]} xu, còn thiếu {sp["short"]} xu.'
            if sp['repeat']:
                line += ' ' + _fmt(AGAIN, who, sp)
            _say(sp, 'count', line)
        return dict(message='🔍 ' + sp['line'])
    e.need(sp is not None and sp['stage'] != 'hidden', 'Đếm lại tiền khách đưa trước đã.')
    e.need(sp['stage'] != 'done', 'Chuyện tiền thiếu đã xử lý xong.')
    allowed = FIRST if sp['stage'] == 'open' else FOLLOW[sp['stage']]
    e.need(choice in allowed, 'Cách này không dùng được lúc này.')
    kind = sp['kind']
    if choice == 'ask':
        line = _fmt(_pick(ASK[kind], 'sp-ask', t['id']), who, sp)
        if kind in ('kid', 'cheat'):
            sp['stage'] = kind
            if kind == 'cheat' and sp['repeat']:
                line += ' ' + _fmt(AGAIN, who, sp)
            return dict(message='🙏 ' + _say(sp, 'ask', line))
        _pay_rest(rec, sp)
        _close(s, t, DELTA['ask_' + kind], 'Được nhắc khéo khi đưa thiếu tiền.')
        line += _tip(s, c, t, sp, who)
        return _done(c, t, sp, 'paid', '🙏 ' + _say(sp, 'ask', line))
    if choice == 'police':
        return _police(s, c, t, rec, sp, who)
    if choice == 'let':
        if kind == 'cheat':
            _flag(c, t['npc'])
        else:
            _close(s, t, DELTA['let'], 'Được bớt cho khoản đưa thiếu.')
        return _done(c, t, sp, 'let', '🤐 ' + _say(sp, 'let', _fmt(LET[kind], who, sp)))
    # the kid: owe / less / give
    line = _fmt(KID[choice], who, sp)
    if choice in ('owe', 'give'):
        b = book(c)
        if len(b['owed']) < OWED_MAX:
            back = _hash('sp-back', t['id']) % 100 < BACK_P[choice]
            b['owed'].append(dict(task=t['id'], npc=t['npc'], who=who[:40], amount=sp['short'], day=c['day'], due=c['day'] + 1,
                                  back=back, kind=choice))
    _close(s, t, DELTA.get(choice, 0), 'Được cho nợ khi thiếu tiền.' if choice == 'owe' else 'Được cho thêm khi thiếu tiền.')
    return _done(c, t, sp, choice, {'owe': '📒 ', 'less': '🧺 ', 'give': '🎁 '}[choice] + _say(sp, choice, line))


def _tip(s: dict, c: dict, t: dict, sp: dict, who: str) -> str:
    """An honest customer sometimes thanks you for the gentle reminder (tip contract: once, 'tip')."""
    if sp['kind'] != 'honest' or t.get('tip_given') or _hash('sp-tip', t['id']) % 100 >= TIP_P:
        return ''
    amount = max(2, min(10, sp['short'] // 4))
    _eng().money(s, c, amount, f'Khách cảm ơn vì được nhắc khéo: {t.get("title", "")}'[:120], t['id'], 'tip')
    t['tip_given'] = amount
    return f' {who} dúi thêm {amount} xu: “Người thật thà vậy hiếm lắm.” (+{amount} xu tip)'


def _police(s: dict, c: dict, t: dict, rec: dict, sp: dict, who: str) -> dict:
    from . import consequences as cq
    kind = sp['kind']
    c['turn'] += POLICE_TURNS
    for x in c['tasks']:
        if x is not t and x.get('status') not in ('completed', 'referred', 'cancelled') and type(x.get('patience')) is int:
            x['patience'] = max(25, x['patience'] - QUEUE_WAIT)
    _pay_rest(rec, sp)
    parts = [WAIT, _fmt(POLICE[kind], who, sp)]
    if kind == 'cheat':
        repeat = sp['repeat']
        _flag(c, t['npc'])
        _close(s, t, DELTA['police_cheat'], 'Bị công an mời đếm lại tiền đưa thiếu.')
        _street(c, TRUST['police_cheat'] + (TRUST['police_repeat'] if repeat else 0))
        if repeat:
            parts.append(_fmt(REPEAT, who, sp))
        from .content import CAREER_META
        place = CAREER_META.get(t['career'], {}).get('place', 'quầy')
        _feed(s, c, t, _pick(NEWS, 'sp-news', t['id']).format(place=place))
        _eng().log(s, c, 'police', f'Công an khu vực giúp đòi {sp["short"]} xu khách đưa thiếu.', t['npc'], t['id'])
    else:
        t['mistakes'] += 1
        cq.slip(t, 'police_overreact', 2, OVERREACT[kind], 'gọi công an khi khách chỉ đưa nhầm')
        _close(s, t, DELTA['police_wrong'], 'Bị gọi công an vì đưa nhầm tiền.')
        _street(c, TRUST['police_wrong'])
    return _done(c, t, sp, 'police', '🚓 ' + _say(sp, 'police', ' '.join(parts)))


def _done(c: dict, t: dict, sp: dict, outcome: str, message: str) -> dict:
    sp['stage'] = 'done'
    sp['outcome'] = outcome
    _log(c, t, sp)
    return dict(message=message)


# ---------------------------------------------------------------- the hand-over
def settle(s: dict, c: dict, t: dict, rec: dict, gone: bool, who: str = 'Khách') -> dict:
    """At the hand-over (till.settle): what the gap costs. Returns dict(loss, message)."""
    sp = rec.get('sp') if isinstance(rec, dict) else None
    notes = due(s, c)
    if not isinstance(sp, dict):
        return dict(loss=0, message=' '.join(notes))
    if gone:
        # They put the goods back and leave: nothing was sold, so nothing is short and nobody owes.
        if sp['stage'] != 'done':
            sp.update(stage='done', outcome='let' if sp['stage'] != 'hidden' else 'missed')
        b = c.get('shortpay')
        if isinstance(b, dict):
            b['owed'] = [r for r in b['owed'] if r['task'] != t['id']]
        return dict(loss=0, message=' '.join(notes))
    if sp['stage'] == 'hidden':
        sp.update(stage='done', outcome='missed')
        _log(c, t, sp)
        if sp['kind'] == 'cheat':
            _flag(c, t['npc'])
        line = _fmt(MISSED, who, sp) + ' ' + _pick(LESSON, 'sp-lesson', t['id'])
        if _owner(s, c, t, TRUST['missed_employee']):
            line += ' ' + OWNER
        sp['line'] = line[:300]
        return dict(loss=sp['short'], message=' '.join([line] + notes))
    loss = 0 if sp['got'] else sp['short']
    known = KNOWN.get(sp['outcome'])
    return dict(loss=loss, message=' '.join(([_fmt(known, who, sp)] if loss and known else []) + notes))


def due(s: dict, c: dict) -> list[str]:
    """A later day at the same till: kids who owed come back (or not), a parent comes to say thanks.
    Each IOU is settled once and leaves the book."""
    b = c.get('shortpay')
    if not isinstance(b, dict) or not b.get('owed'):
        return []
    e = _eng()
    out, keep = [], []
    for row in b['owed']:
        if row['due'] > c['day']:
            keep.append(row)
            continue
        fake = dict(id=row['task'], npc=row['npc'], career=None)
        sp = dict(short=row['amount'])
        if row['back']:
            e.money(s, c, row['amount'], f'{row["who"]} trả khoản thiếu hôm trước'[:120], row['task'], 'revenue')
            _close(s, fake, DELTA[row['kind'] + '_back'], 'Quay lại trả tiền còn thiếu.')
            line = _fmt(BACK[row['kind']], row['who'], sp)
            if row['npc'] in e.NPC_INDEX:
                e.add_feed(s, c, row['npc'], line, row['task'], None, 'story')
            out.append('💌 ' + line)
        elif row['kind'] == 'owe':
            out.append('📒 ' + _fmt(GONE, row['who'], sp))
    b['owed'] = keep
    return out


# ---------------------------------------------------------------- the browser
def public(rec: dict | None) -> dict | None:
    """Only what the player has seen: nothing at all while the gap is unnoticed."""
    sp = (rec or {}).get('sp') if isinstance(rec, dict) else None
    if not isinstance(sp, dict) or sp['stage'] == 'hidden':
        return None
    choices = list(FIRST if sp['stage'] == 'open' else FOLLOW.get(sp['stage'], ()))
    shown = sp['stage'] in ('kid', 'cheat') or sp['stage'] == 'done'
    return dict(stage=sp['stage'], short=sp['short'], choices=choices, line=sp['line'], outcome=sp['outcome'],
                kind=sp['kind'] if shown else None, got=sp['got'])


# ---------------------------------------------------------------- saves
def validate_rec(sp, price: int, paid: int) -> None:
    e = _eng()
    if sp is None:
        return
    e.need(isinstance(sp, dict) and sp.get('v') == VERSION and sp.get('kind') in KINDS, 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.integer(sp.get('short'), 1, price // 2 if price >= 2 else 1)
    e.need(sp.get('stage') in STAGES and sp.get('outcome') in OUTCOMES, 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.need((sp['stage'] == 'done') == (sp['outcome'] is not None), 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.need(sp.get('got') in (0, sp['short']), 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.need(type(sp.get('repeat')) is bool, 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.need(paid + (0 if sp['got'] else sp['short']) >= price, 'Tiền khách đưa thiếu sai.', 'invalid_save')
    path = sp.get('path')
    e.need(isinstance(path, list) and len(path) <= 4 and all(x in CHOICES for x in path), 'Tiền khách đưa thiếu sai.', 'invalid_save')
    e.clean_text(sp.get('line'), 300, 0)


def validate_book(c: dict) -> None:
    b = c.get('shortpay')
    if b is None:
        return
    e = _eng()
    e.need(isinstance(b, dict) and b.get('v') == VERSION, 'Sổ tiền khách đưa thiếu sai.', 'invalid_save')
    e.need(isinstance(b.get('owed'), list) and len(b['owed']) <= OWED_MAX, 'Sổ nợ tiền thiếu sai.', 'invalid_save')
    for r in b['owed']:
        e.need(isinstance(r, dict) and r.get('kind') in ('owe', 'give') and type(r.get('back')) is bool, 'Sổ nợ tiền thiếu sai.', 'invalid_save')
        e.clean_text(r.get('task'), 60)
        e.clean_text(r.get('npc'), 60)
        e.clean_text(r.get('who'), 40)
        e.integer(r.get('amount'), 1, 10 ** 4)
        e.integer(r.get('day'), 1, 10 ** 7)
        e.integer(r.get('due'), 1, 10 ** 7)
    ch = b.get('cheats')
    e.need(isinstance(ch, dict) and len(ch) <= CHEATS_MAX, 'Sổ tiền khách đưa thiếu sai.', 'invalid_save')
    for k, v in ch.items():
        e.clean_text(k, 60)
        e.integer(v, 1, 99)
    e.need(isinstance(b.get('log'), list) and len(b['log']) <= LOG_MAX, 'Sổ tiền khách đưa thiếu sai.', 'invalid_save')
    for r in b['log']:
        e.need(isinstance(r, dict) and r.get('kind') in KINDS and r.get('outcome') in OUTCOMES[1:], 'Sổ tiền khách đưa thiếu sai.', 'invalid_save')
        e.clean_text(r.get('task'), 60)
        e.integer(r.get('day'), 1, 10 ** 7)
        e.integer(r.get('short'), 1, 10 ** 4)
