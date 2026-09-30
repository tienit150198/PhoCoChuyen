"""Vợ chồng: what a married couple shares after the wedding.

* 🏦 Quỹ chung (joint fund, table joint_funds + joint_ledger). Each spouse deposits from their
  own wallet ("Gửi vào quỹ chung") and withdraws to it ("Rút từ quỹ chung"). Rule chosen: a
  CAP of WITHDRAW_CAP xu per spouse per rolling 24 hours (withdrawals and bank card spends
  together), AND a notice to the partner on every withdrawal: the cap stops one spouse
  emptying the fund in one night, the notice keeps it open. Deposits are free.
  On divorce the fund is split 50/50 (the odd xu goes to the spouse who did not file):
  contributions are shared money once deposited, like a real joint account, and a
  "by contribution" rule would reward depositing then withdrawing. Open debts between the two
  are first paid from the borrower's half (see below).
* 💸 Giúp đỡ: send money to the spouse's wallet with a preset note, as a gift or as a loan
  ("cho mượn": a debt). "Xin trợ giúp X xu": the spouse accepts (money moves) or declines.
* 🧾 Sổ nợ (IOUs, couple_debts): the lender can "Đòi tiền" with a preset line (polite or
  cheeky); the borrower repays all or part, or "Xin khất". The lender can "Xóa nợ".
  On divorce, open debts are settled from the fund split: the borrower's half pays the lender
  up to what is owed; anything still owed is cleared (status 'cleared', kept in the history).
  A marriage ending should not leave one ex chasing the other forever.
* 💞 Tương tác: once a day per kind, preset lines and emotes, a lunch (5 xu) or a small gift from
  the closeness gift bag. Each day with a moment grows "Điểm hạnh phúc" (a streak bonus up to
  +5/day, at most 6 points from moments per day, capped at 100, never decays). Every
  ANNIV_DAYS life days after the wedding, each spouse gets an anniversary gift of
  5 + happy // 10 xu.

Money always moves through marriage's effect inbox: the payer's save and the DB rows change in
ONE transaction (marriage._mutate, revision guard), the receiver gets an effect with a fixed id
applied once to their save. Each request carries a client rid, so a retried tap never moves money
twice (the effect id / ledger ref are UNIQUE).

For game/bank.py ("Thẻ chung"): joint_account(s) and joint_spend(s, amount, label, ref).
🏠 For game/housing.py: joint_spend(..., kind='home') pays a home's down payment from the fund (not
counted in the daily cap), and on_load brings the spouse into the home through the inbox ('home' effects).
"""
from __future__ import annotations

import datetime
import json
import re

from . import marriage as mr
from .engine import GameError

WITHDRAW_CAP = 300                 # xu per spouse per rolling 24 h (withdraw + card spend)
FUND_MAX = 10 ** 7
SEND_MAX, HELP_MAX = 5000, 2000
SENDS_PER_DAY = 20
HELP_DAYS = 3
CLAIM_HOURS = 12
HAPPY_MAX, HAPPY_DAY_MAX, STREAK_BONUS_MAX = 100, 6, 5
ANNIV_DAYS = 30
LUNCH_COST = 5
HOLD_S = 30                        # a card spend not in the spender's save after this is refunded
HISTORY = 12
VN = datetime.timezone(datetime.timedelta(hours=7))

# Tables: joint_funds, joint_ledger, couple_requests, couple_debts, couple_moments, couple_stats (in marriage.SCHEMA).

NOTES = {
    'none': '', 'ngon': 'Mua gì ngon đi em', 'ngon_anh': 'Mua gì ngon đi anh', 'no': 'Trả nợ giúp anh', 'no_em': 'Trả nợ giúp em',
    'xang': 'Đổ xăng đi làm nha', 'von': 'Thêm chút vốn làm ăn', 'thuong': 'Thương mình nhiều',
}
HELP_NOTES = {
    'none': '', 'nha': 'Tháng này hụt tiền nhà', 'hang': 'Cần vốn nhập hàng', 'an': 'Cho xin tiền ăn trưa', 'gap': 'Việc gấp, về kể sau',
}
CLAIM_LINES = {
    'nhe': ('polite', 'Mình ơi, khoản hôm trước mình xoay được chưa?'),
    'khong_gap': ('polite', 'Không gấp đâu, khi nào tiện thì trả mình nha.'),
    'nho_nhe': ('polite', 'Nhắc nhẹ thôi: sổ nợ nhà mình còn một dòng nè.'),
    'tien_dau': ('cheeky', 'Tiền đâu? Tiền đâu? Tiền đâu? 💸'),
    'kem_om': ('cheeky', 'Nợ ai cũng được, nợ vợ/chồng là phải trả kèm cái ôm nha.'),
    'but_do': ('cheeky', 'Sổ nợ đã ghi, bút đỏ đang chờ ✍️'),
}
LATER_LINES = {
    'cuoi_tuan': 'Cho khất tới cuối tuần nha',
    'luong': 'Đợi lãnh lương rồi trả liền',
    'com': 'Trả bằng một bữa cơm được không?',
}
# kind: (emoji, button, line the partner sees, happiness points)
MOMENTS = {
    'chao': ('☀️', 'Chào buổi sáng', 'Chào buổi sáng! Hôm nay làm tốt nha.', 1),
    'nho': ('💭', 'Nhớ anh/em', 'Nhớ mình quá à.', 1),
    'met': ('😮‍💨', 'Hôm nay mệt quá', 'Hôm nay mệt quá, về ôm cái nha.', 1),
    'om': ('🤗', 'Ôm một cái', 'Ôm một cái cho đỡ mệt.', 1),
    'hon': ('😘', 'Thơm một cái', 'Thơm một cái!', 1),
    'com': ('🍱', 'Mang cơm trưa', 'Mang cơm trưa tới tận nơi, ăn cho no nha.', 2),
    'qua': ('🎁', 'Tặng quà nhỏ', 'Tặng mình {item}.', 2),
}


def _need(cond, message, code='couple_error', status=400):
    mr.need(cond, message, code, status)


def vn_day(t: float | None = None) -> int:
    """Days since 1970 in Vietnam time: 'once a day' resets at local midnight."""
    return int(((mr.now() if t is None else t) + 7 * 3600) // 86400)


def _married(db, sid: str) -> dict:
    c = mr._bond(db, sid)
    _need(c and c['status'] == 'married', 'Chỉ vợ chồng đã cưới mới dùng được mục này.', 'not_married', 409)
    return c


def _names(db, c: dict) -> dict:
    return dict(a=mr._display(db, c['a']), b=mr._display(db, c['b']))


def _amount(d: dict, key: str, top: int) -> int:
    v = d.get(key)
    _need(type(v) is int and 1 <= v <= top, f'Số xu là từ 1 đến {top}.', 'bad_amount')
    return v


def _balance(db, cid: int) -> int:
    r = db.execute('SELECT balance FROM joint_funds WHERE couple=?', (cid,)).fetchone()
    return int(r['balance']) if r else 0


def _used(db, cid: int, sid: str) -> int:
    return int(db.execute("SELECT COALESCE(SUM(amount),0) FROM joint_ledger WHERE couple=? AND sid=? AND kind IN ('withdraw','spend') "
                          "AND status IN ('done','held') AND at>?", (cid, sid, mr.now() - mr.DAY)).fetchone()[0])


def _fund_move(db, cid: int, sid: str, kind: str, amount: int, label: str, ref: str, status: str = 'done') -> int:
    """Change the fund and write its ledger row (UNIQUE ref: a replay raises IntegrityError)."""
    t = mr.now()
    db.execute('INSERT OR IGNORE INTO joint_funds(couple,balance,updated) VALUES(?,0,?)', (cid, t))
    if kind == 'deposit':
        _need(_balance(db, cid) + amount <= FUND_MAX, 'Quỹ chung đã đầy.', 'fund_full', 409)
        db.execute('UPDATE joint_funds SET balance=balance+?,updated=? WHERE couple=?', (amount, t, cid))
    else:
        if kind in ('withdraw', 'spend'):
            left = WITHDRAW_CAP - _used(db, cid, sid)
            _need(amount <= left, f'Mỗi người rút tối đa {WITHDRAW_CAP} xu từ quỹ chung trong 24 giờ. Bạn còn {max(0, left)} xu.', 'fund_cap', 409)
        _need(db.execute('UPDATE joint_funds SET balance=balance-?,updated=? WHERE couple=? AND balance>=?', (amount, t, cid, amount)).rowcount == 1,
              f'Quỹ chung chỉ còn {mr._xu(_balance(db, cid))} xu.', 'fund_low', 409)
    bal = _balance(db, cid)
    db.execute('INSERT INTO joint_ledger(couple,sid,kind,amount,balance,label,ref,status,at) VALUES(?,?,?,?,?,?,?,?,?)',
               (cid, sid, kind, amount, bal, label[:120], ref[:64], status, t))
    return bal


def _moment(db, c: dict, sid: str, kind: str, text: str, key: str) -> None:
    db.execute('INSERT INTO couple_moments(couple,sid,kind,text,key,at) VALUES(?,?,?,?,?,?)', (c['id'], sid, kind, text[:160], key[:80], mr.now()))


def _settle_quietly(store, *sids) -> None:
    for who in sids:
        try:
            mr.settle(store, who)
        except Exception:  # noqa: BLE001 - the effect waits for that save's next load
            pass


def _pay(store, sid: str, eff: dict, ops, check_wallet: int = 0, message: str = '') -> None:
    """The payer's save and the DB rows in one transaction. A replayed rid -> IntegrityError."""
    def fn(s):
        if check_wallet:
            _need(int(s['journey']['wallet']) >= check_wallet, message or f'Ví của bạn chưa đủ {check_wallet} xu.', 'not_enough')
        mr._apply_effect(s, eff)

    def db_ops(db):
        mr._insert_effects(db, [eff], 'applied')
        return ops(db)
    return mr._mutate_retry(store, {sid: fn}, db_ops)['db']


def _done(db, effect_id: str) -> bool:
    return bool(db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (effect_id[:64],)).fetchone())


def _once(fn):
    """A replayed request id (UNIQUE effect id / ledger ref) answers 'done already' instead of failing."""
    from . import db as dbm

    def run(store, sid, display, d):
        try:
            return fn(store, sid, display, d)
        except dbm.IntegrityError:
            return dict(message='Việc này đã làm xong rồi.', changed=False)
    return run


# ---------------------------------------------------------------- 🏦 quỹ chung
@_once
def deposit(store, sid, display, d):
    amount = _amount(d, 'amount', SEND_MAX)
    with store.connect() as db:
        c = _married(db, sid)
    eid = f'fund:{c["id"]}:{mr._rid(d)}'
    # BANK.PAY: wallet -> joint fund stays cash: a credit card here would be a cash advance (bank app: Ứng tiền mặt)
    eff = mr._effect(eid, sid, 'wallet', -amount, 'Gửi vào quỹ chung')

    def ops(db):
        _need(mr._bond(db, sid) and mr._bond(db, sid)['id'] == c['id'], 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        bal = _fund_move(db, c['id'], sid, 'deposit', amount, 'Gửi vào quỹ chung', eid)
        mr._notice(db, mr._other(c, sid), f'🏦 {display} vừa gửi {mr._xu(amount)} xu vào quỹ chung. Quỹ giờ có {mr._xu(bal)} xu.')
        return bal
    bal = _pay(store, sid, eff, ops, amount, f'Ví của bạn chưa đủ {amount} xu.')
    return dict(message=f'Đã gửi {mr._xu(amount)} xu vào quỹ chung. Quỹ giờ có {mr._xu(bal)} xu.', changed=True)


@_once
def withdraw(store, sid, display, d):
    amount = _amount(d, 'amount', WITHDRAW_CAP)
    with store.connect() as db:
        c = _married(db, sid)
    eid = f'fundw:{c["id"]}:{mr._rid(d)}'
    eff = mr._effect(eid, sid, 'wallet', amount, 'Rút từ quỹ chung')

    def ops(db):
        _need(mr._bond(db, sid) and mr._bond(db, sid)['id'] == c['id'], 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        bal = _fund_move(db, c['id'], sid, 'withdraw', amount, 'Rút từ quỹ chung', eid)
        mr._notice(db, mr._other(c, sid), f'🏦 {display} vừa rút {mr._xu(amount)} xu từ quỹ chung. Quỹ còn {mr._xu(bal)} xu.')
        return bal
    bal = _pay(store, sid, eff, ops)
    return dict(message=f'Đã rút {mr._xu(amount)} xu về ví. Quỹ chung còn {mr._xu(bal)} xu.', changed=True)


# ---------------------------------------------------------------- 💸 gửi tiền, xin trợ giúp, sổ nợ
def _transfer(store, c: dict, sid: str, display: str, amount: int, note: str, loan: bool, key: str, extra=None) -> None:
    """Money from sid's wallet to the spouse's wallet; a loan also opens a debt."""
    other = mr._other(c, sid)
    with store.connect() as db:
        name = mr._display(db, other)
    # BANK.PAY: spouse transfer stays cash (a transfer, not a purchase)
    out = mr._effect(f'send:{key}', sid, 'wallet', -amount, (f'Cho {name} mượn' if loan else f'Gửi {name}') + (f': {note}' if note else ''))
    inn = mr._effect(f'recv:{key}', other, 'wallet', amount, (f'Mượn của {display}' if loan else f'{display} gửi') + (f': {note}' if note else ''))

    def ops(db):
        cur = mr._bond(db, sid)
        _need(cur and cur['id'] == c['id'] and cur['status'] == 'married', 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        _need(db.execute("SELECT COUNT(*) FROM couple_moments WHERE couple=? AND sid=? AND kind='send' AND at>?",
                         (c['id'], sid, mr.now() - mr.DAY)).fetchone()[0] < SENDS_PER_DAY,
              f'Mỗi ngày gửi tiền được {SENDS_PER_DAY} lần thôi.', 'rate_limited', 429)
        mr._insert_effects(db, [inn])
        t = mr.now()
        if loan:
            db.execute("INSERT INTO couple_debts(couple,lender,borrower,amount,repaid,status,note,ref,at,updated) VALUES(?,?,?,?,0,'open',?,?,?,?)",
                       (c['id'], sid, other, amount, note, f'debt:{key}', t, t))
        _moment(db, c, sid, 'send', f'{"💸 Cho mượn" if loan else "💸 Gửi"} {amount} xu' + (f': {note}' if note else ''), f'send:{key}')
        mr._notice(db, other, f'💸 {display} vừa {"cho bạn mượn" if loan else "gửi bạn"} {amount} xu' + (f': "{note}"' if note else '.'))
        if extra:
            extra(db)
    _pay(store, sid, out, ops, amount, f'Ví của bạn chưa đủ {amount} xu.')
    _settle_quietly(store, other)


@_once
def send(store, sid, display, d):
    amount = _amount(d, 'amount', SEND_MAX)
    note = d.get('note', 'none')
    _need(note in NOTES, 'Chọn một lời nhắn soạn sẵn nhé.', 'bad_note')
    loan = d.get('loan', False)
    _need(type(loan) is bool, 'Lựa chọn không hợp lệ.')
    with store.connect() as db:
        c = _married(db, sid)
        name = mr._display(db, mr._other(c, sid))
    _transfer(store, c, sid, display, amount, NOTES[note], loan, f'{c["id"]}:{mr._rid(d)}')
    return dict(message=f'Đã {"cho " + name + " mượn" if loan else "gửi " + name} {amount} xu.' + (' Khoản này đã vào sổ nợ.' if loan else ''), changed=True)


def help_ask(store, sid, display, d):
    amount = _amount(d, 'amount', HELP_MAX)
    note = d.get('note', 'none')
    _need(note in HELP_NOTES, 'Chọn một lời nhắn soạn sẵn nhé.', 'bad_note')
    loan = d.get('loan', False)
    _need(type(loan) is bool, 'Lựa chọn không hợp lệ.')

    def run(db):
        c = _married(db, sid)
        _expire(db, c['id'])
        _need(not db.execute("SELECT 1 FROM couple_requests WHERE couple=? AND from_sid=? AND kind='help' AND status='pending'", (c['id'], sid)).fetchone(),
              'Bạn đang có một lời nhờ chờ trả lời rồi.', 'already', 409)
        other = mr._other(c, sid)
        db.execute("INSERT INTO couple_requests(couple,from_sid,to_sid,kind,amount,note,loan,status,at) VALUES(?,?,?,'help',?,?,?,'pending',?)",
                   (c['id'], sid, other, amount, HELP_NOTES[note], int(loan), mr.now()))
        mr._notice(db, other, f'🙏 {display} {"hỏi mượn" if loan else "xin trợ giúp"} {amount} xu' + (f': "{HELP_NOTES[note]}"' if note != 'none' else '.'))
        return mr._display(db, other)
    name = store.transaction(run)
    return dict(message=f'Đã nhờ {name}. Chờ trả lời nhé.', changed=False)


def _expire(db, cid: int) -> None:
    db.execute("UPDATE couple_requests SET status='expired',decided=? WHERE couple=? AND kind='help' AND status='pending' AND at<?",
               (mr.now(), cid, mr.now() - HELP_DAYS * mr.DAY))


@_once
def help_answer(store, sid, display, d):
    rid, answer = d.get('id'), d.get('answer')
    _need(type(rid) is int and answer in ('accept', 'decline'), 'Trả lời không hợp lệ.')
    with store.connect() as db:
        c = _married(db, sid)
        if answer == 'accept' and _done(db, f'send:{c["id"]}:help{rid}'):
            return dict(message='Việc này đã làm xong rồi.', changed=False)
        r = mr._row(db, "SELECT * FROM couple_requests WHERE id=? AND couple=? AND to_sid=? AND kind='help' AND status='pending' AND at>?",
                    (rid, c['id'], sid, mr.now() - HELP_DAYS * mr.DAY))
        _need(r, 'Lời nhờ này không còn chờ trả lời.', 'gone', 409)
        name = mr._display(db, r['from_sid'])
    if answer == 'decline':
        def run(db):
            _need(db.execute("UPDATE couple_requests SET status='declined',decided=? WHERE id=? AND status='pending'", (mr.now(), rid)).rowcount == 1,
                  'Lời nhờ này không còn chờ trả lời.', 'gone', 409)
            mr._notice(db, r['from_sid'], f'{display} chưa giúp được lần này.')
        store.transaction(run)
        return dict(message='Đã trả lời. Lần sau giúp nhau nhé.', changed=False)

    def close(db):
        _need(db.execute("UPDATE couple_requests SET status='accepted',decided=? WHERE id=? AND status='pending'", (mr.now(), rid)).rowcount == 1,
              'Lời nhờ này không còn chờ trả lời.', 'gone', 409)
    _transfer(store, c, sid, display, r['amount'], r['note'], bool(r['loan']), f'{c["id"]}:help{rid}', close)
    return dict(message=f'Đã giúp {name} {r["amount"]} xu.' + (' Khoản này đã vào sổ nợ.' if r['loan'] else ''), changed=True)


def help_cancel(store, sid, display, d):
    rid = d.get('id')
    _need(type(rid) is int, 'Lời nhờ không hợp lệ.')
    store.transaction(lambda db: _need(db.execute("UPDATE couple_requests SET status='cancelled',decided=? WHERE id=? AND from_sid=? AND status='pending'",
                                                  (mr.now(), rid, sid)).rowcount == 1, 'Lời nhờ này không còn chờ trả lời.', 'gone', 409))
    return dict(message='Đã rút lại lời nhờ.', changed=False)


def _debt(db, did, sid: str, role: str) -> dict:
    _need(type(did) is int, 'Khoản nợ không hợp lệ.')
    r = mr._row(db, f"SELECT * FROM couple_debts WHERE id=? AND {role}=? AND status='open'", (did, sid))
    _need(r, 'Khoản nợ này đã khép lại.', 'gone', 409)
    return r


def claim(store, sid, display, d):
    line = d.get('line')
    _need(line in CLAIM_LINES, 'Chọn một câu đòi nợ soạn sẵn nhé.', 'bad_note')

    def run(db):
        r = _debt(db, d.get('debt'), sid, 'lender')
        _need(not db.execute("SELECT 1 FROM couple_requests WHERE debt=? AND kind='claim' AND at>?", (r['id'], mr.now() - CLAIM_HOURS * 3600)).fetchone(),
              f'Vừa nhắc rồi. {CLAIM_HOURS} giờ sau hẵng nhắc lại cho đỡ căng nha.', 'rate_limited', 429)
        db.execute("UPDATE couple_requests SET status='cancelled',decided=? WHERE debt=? AND kind='claim' AND status IN ('pending','later')", (mr.now(), r['id']))
        left = r['amount'] - r['repaid']
        db.execute("INSERT INTO couple_requests(couple,from_sid,to_sid,kind,amount,note,debt,status,at) VALUES(?,?,?,'claim',?,?,?,'pending',?)",
                   (r['couple'], sid, r['borrower'], left, CLAIM_LINES[line][1], r['id'], mr.now()))
        mr._notice(db, r['borrower'], f'🧾 {display}: "{CLAIM_LINES[line][1]}" (còn nợ {left} xu)')
        return mr._display(db, r['borrower'])
    name = store.transaction(run)
    return dict(message=f'Đã nhắc {name}.', changed=False)


def later(store, sid, display, d):
    line = d.get('line')
    _need(line in LATER_LINES, 'Chọn một câu soạn sẵn nhé.', 'bad_note')

    def run(db):
        r = _debt(db, d.get('debt'), sid, 'borrower')
        _need(db.execute("UPDATE couple_requests SET status='later',decided=?,note=? WHERE debt=? AND kind='claim' AND status='pending'",
                         (mr.now(), LATER_LINES[line], r['id'])).rowcount >= 1, 'Chưa ai đòi khoản này.', 'gone', 409)
        mr._notice(db, r['lender'], f'🙏 {display} xin khất: "{LATER_LINES[line]}"')
    store.transaction(run)
    return dict(message='Đã xin khất.', changed=False)


@_once
def repay(store, sid, display, d):
    with store.connect() as db:
        if type(d.get('debt')) is int and isinstance(d.get('rid'), str) and _done(db, f'repay:{d["debt"]}:{mr._rid(d)}'):
            return dict(message='Việc này đã làm xong rồi.', changed=False)
        r = _debt(db, d.get('debt'), sid, 'borrower')
        name = mr._display(db, r['lender'])
    left = r['amount'] - r['repaid']
    amount = _amount(d, 'amount', left)
    key = f'{r["id"]}:{mr._rid(d)}'
    # BANK.PAY: debt repayment stays cash (never repay a debt with the credit card)
    out = mr._effect(f'repay:{key}', sid, 'wallet', -amount, f'Trả nợ {name}')
    inn = mr._effect(f'repaid:{key}', r['lender'], 'wallet', amount, f'{display} trả nợ')

    def ops(db):
        t = mr.now()
        _need(db.execute("UPDATE couple_debts SET repaid=repaid+?,updated=?,status=CASE WHEN amount-repaid-?<=0 THEN 'paid' ELSE 'open' END "
                         "WHERE id=? AND status='open' AND amount-repaid>=?", (amount, t, amount, r['id'], amount)).rowcount == 1,
              'Khoản nợ vừa thay đổi. Xem lại nhé.', 'gone', 409)
        full = amount == left
        open_claims = "('pending','later')" if full else "('pending')"
        db.execute(f"UPDATE couple_requests SET status=?,decided=? WHERE debt=? AND kind='claim' AND status IN {open_claims}",
                   ('accepted' if full else 'later', t, r['id']))
        mr._insert_effects(db, [inn])
        mr._notice(db, r['lender'], f'🧾 {display} vừa trả {amount} xu' + (' — hết nợ rồi!' if full else f', còn {left - amount} xu.'))
        _moment(db, dict(id=r['couple']), sid, 'repay', f'🧾 Trả nợ {amount} xu', f'repay:{key}')
    _pay(store, sid, out, ops, amount, f'Ví của bạn chưa đủ {amount} xu.')
    _settle_quietly(store, r['lender'])
    return dict(message=f'Đã trả {name} {amount} xu.' + (' Hết nợ!' if amount == left else f' Còn {left - amount} xu.'), changed=True)


def forgive(store, sid, display, d):
    def run(db):
        r = _debt(db, d.get('debt'), sid, 'lender')
        db.execute("UPDATE couple_debts SET status='forgiven',updated=? WHERE id=?", (mr.now(), r['id']))
        db.execute("UPDATE couple_requests SET status='cancelled',decided=? WHERE debt=? AND status IN ('pending','later')", (mr.now(), r['id']))
        mr._notice(db, r['borrower'], f'💝 {display} đã xóa khoản nợ {r["amount"] - r["repaid"]} xu cho bạn.')
        return mr._display(db, r['borrower'])
    name = store.transaction(run)
    return dict(message=f'Đã xóa nợ cho {name}.', changed=False)


# ---------------------------------------------------------------- 💞 tương tác, điểm hạnh phúc
def _grow(db, cid: int, points: int) -> int:
    """Happiness for one moment today; returns the points added."""
    day = vn_day()
    st = mr._row(db, 'SELECT * FROM couple_stats WHERE couple=?', (cid,))
    if not st:
        db.execute('INSERT INTO couple_stats(couple) VALUES(?)', (cid,))
        st = dict(happy=0, streak=0, best=0, last_day=0, today=0)
    if st['last_day'] == day:
        add = max(0, min(points, HAPPY_DAY_MAX - st['today']))
        streak, today = st['streak'], st['today'] + add
    else:
        streak = st['streak'] + 1 if st['last_day'] == day - 1 else 1
        add = min(points, HAPPY_DAY_MAX)
        today = add
        add += min(streak, STREAK_BONUS_MAX) - 1          # the first day of a streak has no bonus
    happy = min(HAPPY_MAX, st['happy'] + add)
    db.execute('UPDATE couple_stats SET happy=?,streak=?,best=?,last_day=?,today=? WHERE couple=?',
               (happy, streak, max(st['best'], streak), day, today, cid))
    return happy - st['happy']


def _bag(s: dict):
    st = (s.get('journey') or {}).get('closeness')
    return st.get('bag') if isinstance(st, dict) and isinstance(st.get('bag'), dict) else None


def _received():
    try:
        from .closeness_content import RECEIVED
        from .closeness import BAG_MAX
        return RECEIVED, BAG_MAX
    except Exception:  # noqa: BLE001
        return {}, 9


def interact(store, sid, display, d):
    kind = d.get('kind')
    _need(kind in MOMENTS, 'Chọn một điều muốn gửi nhé.', 'bad_kind')
    emoji, _, line, points = MOMENTS[kind]
    day = vn_day()
    with store.connect() as db:
        c = _married(db, sid)
        other = mr._other(c, sid)
        name = mr._display(db, other)
    key = f'm:{c["id"]}:{sid[:12]}:{kind}:{day}'
    received, _ = _received()
    item = d.get('item') if kind == 'qua' else None
    if kind == 'qua':
        _need(item in received, 'Chọn một món trong túi quà nhé.', 'bad_item')
        line = line.format(item=received[item]['name'].lower())
    text = f'{emoji} {line}'

    def ops(db):
        cur = mr._bond(db, sid)
        _need(cur and cur['id'] == c['id'] and cur['status'] == 'married', 'Hai bạn không còn là vợ chồng.', 'not_married', 409)
        _need(not db.execute('SELECT 1 FROM couple_moments WHERE key=?', (key,)).fetchone(), 'Hôm nay bạn gửi điều này rồi. Mai gửi tiếp nhé!', 'once_a_day', 409)
        _moment(db, c, sid, kind, text, key)
        added = _grow(db, c['id'], points)
        if kind == 'qua':
            mr._insert_effects(db, [mr._effect(f'bag:{key}', other, 'bag', data=dict(item=item))])
        mr._notice(db, other, f'💞 {display}: {text}')
        return added
    if kind in ('com', 'qua'):
        def fn(s):
            if kind == 'com':
                _need(mr._can_spend(s, LUNCH_COST, d.get('pay')), f'Cần {LUNCH_COST} xu trong ví để mua cơm trưa.', 'not_enough')
                # BANK.PAY: lunch for the spouse: cash or the credit card (marriage._spend)
                mr._spend(s, mr._effect(f'lunch:{key}', sid, 'wallet', -LUNCH_COST, f'Mang cơm trưa cho {name}'), d.get('pay'))
            else:
                bag = _bag(s)
                _need(bag and bag.get(item, 0) >= 1, 'Món này không còn trong túi quà của bạn.', 'bad_item')
                bag[item] -= 1
                if not bag[item]:
                    del bag[item]
        added = mr._mutate_retry(store, {sid: fn}, ops)['db']
        if kind == 'qua':
            _settle_quietly(store, other)
        changed = True
    else:
        added = store.transaction(ops)
        changed = False
    return dict(message=f'Đã gửi tới {name}: {text}' + (f' (+{added} điểm hạnh phúc)' if added else ''), changed=changed)


def moments_seen(store, sid, display, d):
    def run(db):
        c = mr._bond(db, sid)
        if c:
            db.execute('UPDATE couple_moments SET seen=1 WHERE couple=? AND sid<>? AND seen=0', (c['id'], sid))
    store.transaction(run)
    return dict(message='', changed=False)


ACTIONS = dict(fund_deposit=deposit, fund_withdraw=withdraw, send=send, help_ask=help_ask, help_answer=help_answer, help_cancel=help_cancel,
               claim=claim, later=later, repay=repay, forgive=forgive, interact=interact, moments_seen=moments_seen)


# ---------------------------------------------------------------- the end of a marriage
def on_end(db, c: dict, filer: str | None, deleted: str | None = None) -> list:
    """Inside the divorce / account-deletion transaction: split the fund, settle debts, close
    requests. Returns the wallet effects to insert (applied through the inbox)."""
    t = mr.now()
    cid = c['id']
    bal = _balance(db, cid)
    if deleted:  # the one who stays keeps the whole fund; debts between them are cleared
        stay = mr._other(c, deleted)
        share = {stay: bal, deleted: 0}
    else:
        half = bal // 2
        stay = mr._other(c, filer) if filer in (c['a'], c['b']) else c['b']
        share = {c['a']: half, c['b']: half}
        share[stay] += bal - 2 * half
    for r in mr._rows(db, "SELECT * FROM couple_debts WHERE couple=? AND status='open'", (cid,)):
        owed = r['amount'] - r['repaid']
        pay = 0 if deleted else min(owed, share.get(r['borrower'], 0))
        share[r['borrower']] = share.get(r['borrower'], 0) - pay
        share[r['lender']] = share.get(r['lender'], 0) + pay
        db.execute('UPDATE couple_debts SET repaid=repaid+?,status=?,updated=? WHERE id=?', (pay, 'settled' if pay == owed else 'cleared', t, r['id']))
    db.execute("UPDATE couple_requests SET status='cancelled',decided=? WHERE couple=? AND status IN ('pending','later')", (t, cid))
    effects = []
    if bal:
        db.execute('UPDATE joint_funds SET balance=0,updated=? WHERE couple=?', (t, cid))
        db.execute("INSERT OR IGNORE INTO joint_ledger(couple,sid,kind,amount,balance,label,ref,status,at) VALUES(?,?,'split',?,0,?,?,'done',?)",
                   (cid, filer, bal, 'Chia quỹ chung khi chia tay', f'split:{cid}', t))
    for who, amount in share.items():
        if amount and who != deleted:
            effects.append(mr._effect(f'split:{cid}:{mr._side(c, who)}', who, 'wallet', amount,
                                      'Phần quỹ chung khi chia tay' + (' (đã trừ/cộng nợ)' if not deleted else '')))
    return effects


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM couple_moments WHERE sid=?', (sid,))
    db.execute("UPDATE couple_requests SET status='cancelled' WHERE (from_sid=? OR to_sid=?) AND status IN ('pending','later')", (sid, sid))


# ---------------------------------------------------------------- loading a save: anniversaries, card holds, old saves
def on_load(store, sid: str, state: dict | None, c: dict | None) -> None:
    """Called by marriage._on_load_sid before the inbox is applied."""
    if not state:
        return
    _reconcile(store, sid, state)
    if not c or c['status'] != 'married':
        return
    m = state.get('marriage') if isinstance(state.get('marriage'), dict) else {}
    sp = m.get('spouse') if isinstance(m.get('spouse'), dict) else None
    side = mr._side(c, sid)
    effects = []
    if sp and sp.get('couple') != c['id']:  # saves married before the couple id was kept
        effects.append(mr._effect(f'link:{c["id"]}:{side}', sid, 'status', data=dict(set='link', couple=c['id'], side=side)))
    if sp and sp.get('status') == 'married' and sp.get('wed'):
        k = (mr._life_day(state) - int(sp['wed'])) // ANNIV_DAYS
        if k >= 1:
            with store.connect() as db:
                st = mr._row(db, 'SELECT happy FROM couple_stats WHERE couple=?', (c['id'],))
            gift = 5 + int((st or {}).get('happy') or 0) // 10
            effects.append(mr._effect(f'anniv:{c["id"]}:{side}:{k}', sid, 'wallet', gift, f'Quà kỷ niệm {k * ANNIV_DAYS} ngày về chung một nhà'))
    effects += _home_effects(store, state, c, sid, side)   # 🏠 the spouse moves into this save's home
    if not effects:
        return

    def run(db):
        added = 0
        for e in effects:
            if not db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (e['id'],)).fetchone():
                mr._insert_effects(db, [e])
                added += 1
                if e['id'].startswith('anniv:'):
                    mr._notice(db, sid, f'🎂 {e["label"]}! Nhận {e["amount"]} xu quà kỷ niệm.')
                    _moment(db, c, sid, 'anniv', f'🎂 {e["label"]}', e['id'])
                elif e['id'].startswith('home:'):
                    mr._notice(db, e['sid'], f'🏠 {e["label"]}.')
        return added
    store.transaction(run, 500)


def _home_effects(store, state: dict, c: dict, sid: str, side: str) -> list:
    """🏠 game/housing.py: 'home' effects for the spouse that are not in the inbox yet (read-only check, so a
    plain load writes nothing)."""
    try:
        from . import housing
        want = housing.partner_effects(state, c['id'], side, mr._other(c, sid), mr._effect)
    except Exception:  # noqa: BLE001 - a home never blocks loading the game
        return []
    if not want:
        return []
    with store.connect() as db:
        return [e for e in want if not db.execute('SELECT 1 FROM marriage_effects WHERE id=?', (e['id'],)).fetchone()]


def _reconcile(store, sid: str, state: dict) -> None:
    """Card spends ("held") the bank's save write never confirmed: refund after HOLD_S."""
    with store.connect() as db:
        held = mr._rows(db, "SELECT * FROM joint_ledger WHERE sid=? AND status='held' AND at<?", (sid, mr.now() - HOLD_S))
    if not held:
        return
    applied = set(((state.get('marriage') or {}).get('applied')) or [])

    def run(db):
        for r in held:
            if r['ref'] in applied:
                db.execute("UPDATE joint_ledger SET status='done' WHERE id=? AND status='held'", (r['id'],))
                continue
            if db.execute("UPDATE joint_ledger SET status='void' WHERE id=? AND status='held'", (r['id'],)).rowcount != 1:
                continue
            c = mr._row(db, 'SELECT * FROM couples WHERE id=?', (r['couple'],))
            if c and c['status'] == 'married':
                db.execute('UPDATE joint_funds SET balance=balance+?,updated=? WHERE couple=?', (r['amount'], mr.now(), r['couple']))
            else:  # the fund was split meanwhile: the spender gets it back
                mr._insert_effects(db, [mr._effect(f'jvoid:{r["id"]}', sid, 'wallet', r['amount'], 'Hoàn tiền thẻ chung')])
    store.transaction(run, 500)


# ---------------------------------------------------------------- for game/bank.py ("Thẻ chung")
def _sid_of(db, s: dict):
    m = s.get('marriage') if isinstance(s, dict) else None
    sp = m.get('spouse') if isinstance(m, dict) else None
    if not isinstance(sp, dict) or sp.get('status') != 'married' or type(sp.get('couple')) is not int or sp.get('side') not in ('a', 'b'):
        return None, None
    c = mr._row(db, 'SELECT * FROM couples WHERE id=?', (sp['couple'],))
    if not c or c['status'] != 'married':
        return None, None
    sid = c[sp['side']]
    b = db.execute('SELECT couple FROM marriage_bonds WHERE sid=?', (sid,)).fetchone()
    return (c, sid) if b and b['couple'] == c['id'] else (None, None)


def _history(db, cid: int, limit: int = HISTORY) -> list:
    names = {}
    out = []
    for r in mr._rows(db, "SELECT * FROM joint_ledger WHERE couple=? AND status<>'void' ORDER BY id DESC LIMIT ?", (cid, limit)):
        if r['sid'] and r['sid'] not in names:
            names[r['sid']] = mr._display(db, r['sid'])
        out.append(dict(who=names.get(r['sid'], ''), kind=r['kind'], amount=r['amount'], balance=r['balance'], label=r['label'], at=int(r['at']),
                        held=r['status'] == 'held'))
    return out


def joint_account(s: dict) -> dict | None:
    """{id, balance, members, history, daily_left} of this save's joint fund, or None (not
    married, an old save before its first load, or marriage not bound to a Store)."""
    store = mr.STORE
    if store is None:
        return None
    with store.connect() as db:
        c, sid = _sid_of(db, s)
        if not c:
            return None
        return dict(id=c['id'], balance=_balance(db, c['id']), members=[dict(name=mr._display(db, c[x]), me=c[x] == sid) for x in ('a', 'b')],
                    history=_history(db, c['id']), daily_left=max(0, WITHDRAW_CAP - _used(db, c['id'], sid)))


def joint_spend(s: dict, amount: int, label: str, ref: str, kind: str = 'spend') -> dict:
    """Charge the joint fund for a card payment made while computing save `s`.

    Idempotent by `ref` (the same ref never charges twice; retries of the same command are
    fine). The fund is debited at once in its own transaction ("held") and `s` records it
    (s['marriage']['applied']); when the command's save write never lands, the next load of
    that save refunds the hold after HOLD_S seconds. Counts toward the WITHDRAW_CAP daily
    limit. Raises GameError when not allowed. Returns {balance, daily_left}.
    Do not call it while holding the store's write lock (e.g. inside Store._command_locked):
    it raises GameError('busy') instead of waiting on itself.
    kind='home' (🏠 game/housing.py): a home's down payment, outside the daily cap."""
    store = mr.STORE
    if kind not in ('spend', 'home'):
        raise GameError('Loại giao dịch không hợp lệ.', 'bad_kind')
    if type(amount) is not int or not 1 <= amount <= FUND_MAX:
        raise GameError('Số tiền không hợp lệ.', 'bad_amount')
    if not isinstance(ref, str) or not re.fullmatch(r'[A-Za-z0-9:_\-]{1,40}', ref):
        raise GameError('Mã giao dịch không hợp lệ.', 'bad_ref')
    if store is None:
        raise GameError('Quỹ chung chưa sẵn sàng.', 'no_joint')
    owned = getattr(store._wlock, '_is_owned', None)
    if store._depth and callable(owned) and owned():
        raise GameError('Quỹ chung đang bận. Thử lại sau một chút nhé.', 'busy')
    with store.connect() as db:
        c, sid = _sid_of(db, s)
    if not c:
        raise GameError('Bạn chưa có quỹ chung.', 'no_joint')
    key = f'jspend:{c["id"]}:{ref}'
    box = mr._box(s)

    def run(db):
        r = mr._row(db, 'SELECT status FROM joint_ledger WHERE ref=?', (key,))
        if r:
            if r['status'] == 'void':
                raise GameError('Giao dịch này đã hết hạn. Thử lại nhé.', 'expired')
        else:
            try:
                _fund_move(db, c['id'], sid, kind, amount, str(label or 'Thẻ chung')[:120], key, 'held')
            except mr.MarriageError as e:
                raise GameError(e.message, e.code) from None
            mr._notice(db, mr._other(c, sid), f'{"🏠" if kind == "home" else "💳"} {mr._display(db, sid)} vừa chi {amount} xu từ quỹ chung: {str(label or "Thẻ chung")[:60]}')
        return dict(balance=_balance(db, c['id']), daily_left=max(0, WITHDRAW_CAP - _used(db, c['id'], sid)))
    if key in box['applied']:
        with store.connect() as db:
            r = mr._row(db, 'SELECT status FROM joint_ledger WHERE ref=?', (key,))
            if r and r['status'] == 'void':
                raise GameError('Giao dịch này đã hết hạn. Thử lại nhé.', 'expired')
            return dict(balance=_balance(db, c['id']), daily_left=max(0, WITHDRAW_CAP - _used(db, c['id'], sid)))
    out = store.transaction(run)
    box['applied'] = (box['applied'] + [key])[-mr.APPLIED_KEPT:]
    return out


# ---------------------------------------------------------------- views
def debts_view(db, sid: str) -> list:
    out = []
    for r in mr._rows(db, 'SELECT * FROM couple_debts WHERE lender=? OR borrower=? ORDER BY id DESC LIMIT 20', (sid, sid)):
        mine = r['lender'] == sid
        claim_row = mr._row(db, "SELECT note,status,at FROM couple_requests WHERE debt=? AND kind='claim' ORDER BY id DESC LIMIT 1", (r['id'],))
        out.append(dict(id=r['id'], lender=mine, who=mr._display(db, r['borrower'] if mine else r['lender']), amount=r['amount'], repaid=r['repaid'],
                        left=r['amount'] - r['repaid'], status=r['status'], note=r['note'], at=int(r['at']),
                        claim=dict(text=claim_row['note'], status=claim_row['status'], at=int(claim_row['at'])) if claim_row else None,
                        can_claim=mine and r['status'] == 'open' and not (claim_row and claim_row['at'] > mr.now() - CLAIM_HOURS * 3600)))
    return out


def view(db, sid: str, c: dict | None) -> dict:
    out = dict(debts=debts_view(db, sid), notes=NOTES, help_notes=HELP_NOTES,
               claim_lines={k: dict(tone=v[0], text=v[1]) for k, v in CLAIM_LINES.items()}, later_lines=LATER_LINES,
               moments_kinds={k: dict(emoji=v[0], label=v[1], points=v[3]) for k, v in MOMENTS.items()},
               gifts={k: dict(name=v['name'], emoji=v['emoji']) for k, v in _received()[0].items()},
               limits=dict(withdraw_cap=WITHDRAW_CAP, send_max=SEND_MAX, help_max=HELP_MAX, lunch=LUNCH_COST, anniv_days=ANNIV_DAYS))
    if not c or c['status'] != 'married':
        return out
    cid = c['id']
    st = mr._row(db, 'SELECT * FROM couple_stats WHERE couple=?', (cid,)) or dict(happy=0, streak=0, best=0, last_day=0, today=0)
    day = vn_day()
    streak = st['streak'] if st['last_day'] >= day - 1 else 0
    done = {r['kind'] for r in mr._rows(db, 'SELECT kind FROM couple_moments WHERE couple=? AND sid=? AND key LIKE ?',
                                         (cid, sid, f'm:{cid}:%:{day}'))}
    moments = [dict(mine=r['sid'] == sid, text=r['text'], kind=r['kind'], at=int(r['at']), new=r['sid'] != sid and not r['seen'])
               for r in mr._rows(db, 'SELECT * FROM couple_moments WHERE couple=? ORDER BY id DESC LIMIT 15', (cid,))]
    reqs = []
    for r in mr._rows(db, "SELECT * FROM couple_requests WHERE couple=? AND kind='help' AND status='pending' AND at>? ORDER BY id DESC",
                      (cid, mr.now() - HELP_DAYS * mr.DAY)):
        reqs.append(dict(id=r['id'], mine=r['from_sid'] == sid, amount=r['amount'], note=r['note'], loan=bool(r['loan']), at=int(r['at']),
                         expires=int(r['at'] + HELP_DAYS * mr.DAY)))
    out.update(fund=dict(balance=_balance(db, cid), daily_left=max(0, WITHDRAW_CAP - _used(db, cid, sid)), history=_history(db, cid)),
               happy=dict(points=st['happy'], streak=streak, best=st['best'], today=st['today'] if st['last_day'] == day else 0, max=HAPPY_MAX),
               done_today=sorted(done), moments=moments, requests=reqs)
    return out


def alerts(db, sid: str, cid: int | None) -> int:
    n = db.execute("SELECT COUNT(*) FROM couple_requests WHERE to_sid=? AND status='pending' AND (kind='claim' OR at>?)",
                   (sid, mr.now() - HELP_DAYS * mr.DAY)).fetchone()[0]
    if cid:
        n += db.execute('SELECT COUNT(*) FROM couple_moments WHERE couple=? AND sid<>? AND seen=0', (cid, sid)).fetchone()[0]
    return int(n)
