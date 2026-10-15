"""🛃 Hải quan across players (owner spec 14/10, I.1.1.4): a customs officer inspects the warehouse of another player's
shop. Through POST /api/marriage/<op> (game/marriage.py act → _more_actions → ACTIONS here), every rule checked here,
nothing decided by the page.

* hq_shops {}: the shops on the street an officer may inspect now (the social directory's visible players, never
  oneself, a friend or one's spouse), with today's count and the open cases.
* hq_inspect {pid}: 🔎 the inspection. The findings are computed here from the shop's own save, evidence only
  (findings): every career the shop runs, its tax bills still unpaid past their due day (Nợ thuế quá hạn: count,
  total, days late) and its till. Nothing found: the case closes 'clear'. One hq_cases row either way; the owner is
  told (inbox + push).
* hq_propose {case, measure}: what the officer proposes for a case with findings (MEASURES):
  - 'remind' 📨 Nhắc nộp thuế: done at once (an inbox line to the owner), always grounded;
  - 'collect' 💰 Cưỡng chế trích tiền nộp thuế: grounded once the debt is COLLECT_LATE days late;
  - 'seize' 📦 Kê biên hàng tồn: grounded only when the debt is SEIZE_LATE days late and the till cannot pay it.
  A collect / seize waits for approval ('review'): a customs player at a higher post (never the officer, the owner or
  a friend of the owner: hq_reviews / hq_review {case, ok}) or, past REVIEW_S, the Cục's automatic review (NPC): it
  approves what is grounded and rejects the rest. Approved: apply() on the owner's save (collect pays every overdue
  tax bill the till covers, never into debt; seize sells shelf stock at cost into the till first, then the same);
  the debt paid meanwhile: 'void', nothing applied.
* Wrong handling: a proposal without grounds that is rejected counts against the officer (wrong), and one approved by
  a player counts against both the officer and the approver; each is disciplined (gov_rules.WRONG_CASE: giáng 1 bậc +
  giam hàm 15 ngày). WRONG_MAX wrong cases within WRONG_DAYS: khai trừ and the gov_ban instead (serious).
* hq_mine {}: the cases on my shop, with hq_appeal {case} 📣 Khiếu nại within APPEAL_S of an applied measure: the Cục
  reviews it at once; without grounds the measure is reversed (what was taken given back to the till) and the wrong
  counted, else the appeal is dismissed.
* Limits (anti-abuse): an officer on the customs ladder at Kiểm tra viên or above (not Tập sự), the customs shift open,
  not suspended, jailed or on the way out, with an account; at most OFFICER_DAY_MAX inspections a Vietnam day, a shop
  at most once per TARGET_S (all officers), the same officer and shop once per PAIR_S; a shop owner with an account.

Tables hq_cases and hq_roster (game/pg_schema.py SCHEMA_VERSION 48). Nothing here is in the save but the effects
(the till, the bills, the stock, the officer's org record), so older builds load every save.
"""
from __future__ import annotations

import json
import re
import secrets
import time

from . import org_content as OC

CAREER = 'customs'
ORG_ID = 'hq'
POST_ORDER = {p['id']: i for i, p in enumerate(OC.HQ_POSTS)}
INSPECTORS = tuple(p['id'] for p in OC.HQ_POSTS if p['id'] != 'hq_ts')
MEASURES = {'remind': '📨 Nhắc nộp thuế', 'collect': '💰 Cưỡng chế trích tiền nộp thuế', 'seize': '📦 Kê biên hàng tồn'}
COLLECT_LATE = 2
SEIZE_LATE = 5
OFFICER_DAY_MAX = 5
TARGET_S = 24 * 3600
PAIR_S = 72 * 3600
REVIEW_S = 6 * 3600
APPEAL_S = 3 * 86400
WRONG_DAYS = 14
WRONG_MAX = 3
REWARD_ADJ = 1               # +0.1 ★ at the officer's next close for an approved, grounded measure
LIST_MAX = 30
SEEN_S = 14 * 86400
PID_RE = re.compile(r'[0-9a-f]{16}')
ID_RE = re.compile(r'hq[0-9a-f]{16}')
INBOX = 'hq'
COLS = ('id,officer,target,at,day,status,measure,finding,proper,opost,reviewer,review_at,outcome,amount,appeal,appeal_at,'
        'wrong,rwrong')
LABEL_COLLECT = '🛃 Hải quan cưỡng chế nộp thuế quá hạn'
LABEL_SALE = '🛃 Hải quan kê biên, bán hàng tồn nộp thuế'
LABEL_BACK = '🛃 Hải quan hoàn trả sau khiếu nại'


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    from .fair import vn_date
    return vn_date(t)


def _xu(n) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _mr():
    from . import marriage as mr
    return mr


def need(cond, message: str, code: str = 'hq_error', status: int = 409):
    _mr().need(cond, message, code, status)


# ===================================================================================== pure rules (no database)
def officer_of(s: dict):
    """(career, record, org block) of a save on the customs ladder now; (c, None, None) when it is not."""
    c = (s.get('careers') or {}).get(CAREER) if isinstance(s, dict) else None
    if not isinstance(c, dict):
        return None, None, None
    from . import promotion as pm
    rec, x = pm.org_live(s, c, CAREER)
    if not x or x.get('org') != ORG_ID:
        return c, None, None
    return c, rec, x


def _out(s: dict, rec) -> bool:
    from . import promotion as pm
    return pm.banned(s, CAREER) or pm.expel_due(rec)


def officer_block(s: dict, t: float, review: bool = False) -> str | None:
    """Why this save may not inspect (review: approve) now; None: it may."""
    from . import jail
    from . import org as ORG
    if jail.active((s or {}).get('journey'), t):
        return 'Bạn đang ở trại tạm giữ.'
    c, rec, x = officer_of(s)
    if x is None:
        return 'Chỉ công chức Hải quan đang công tác mới kiểm tra kho cửa hàng.'
    if _out(s, rec):
        return 'Bạn đã có quyết định khai trừ, không còn làm nhiệm vụ.'
    if ORG.suspended(x):
        return 'Bạn đang bị tạm đình chỉ công tác.'
    if x['p'] not in INSPECTORS:
        return 'Người tập sự chưa được kiểm tra kho cửa hàng: lên Kiểm tra viên đã nhé.'
    if not review and not c.get('open'):
        return 'Mở ca ở Chi cục Hải quan rồi hẵng đi kiểm tra nhé.'
    return None


def post_of(s: dict) -> str:
    x = officer_of(s)[2]
    return x['p'] if x else ''


def findings(s: dict) -> dict:
    """Evidence read from the shop's save: {items: [{career, name, n, debt, late, till, bills}], debt, late}."""
    from .content import CAREER_META
    from . import operations as ops
    items = []
    for cid, c in (s.get('careers') or {}).items() if isinstance(s, dict) else ():
        if not isinstance(c, dict) or ops.salaried(cid):
            continue
        f = ((c.get('ops') or {}).get('finance') or {}) if isinstance(c.get('ops'), dict) else {}
        due = [b for b in f.get('bills') or () if isinstance(b, dict) and b.get('kind') == 'tax' and b.get('status') == 'unpaid'
               and int(b.get('due') or 0) < int(c.get('day') or 0)]
        if not due:
            continue
        items.append(dict(career=cid, name=CAREER_META.get(cid, {}).get('short', cid), n=len(due),
                          debt=sum(int(b['amount']) for b in due), late=max(int(c['day']) - int(b['due']) for b in due),
                          till=max(0, int(c.get('money') or 0)), bills=sorted(b['id'] for b in due)[:20]))
    return dict(items=items, debt=sum(i['debt'] for i in items), late=max((i['late'] for i in items), default=0))


def grounded(f: dict, measure: str) -> bool:
    """Whether the evidence supports the measure (the Cục's rule, never shown as a verdict before the review)."""
    if not f.get('items'):
        return False
    if measure == 'remind':
        return True
    if measure == 'collect':
        return f['late'] >= COLLECT_LATE
    if measure == 'seize':
        return any(i['late'] >= SEIZE_LATE and i['till'] < i['debt'] for i in f['items'])
    return False


def finding_text(f: dict) -> str:
    if not f.get('items'):
        return '✅ Không phát hiện sai phạm: sổ thuế các cửa hàng không có khoản quá hạn.'
    rows = [f'{i["name"]}: {i["n"]} kỳ thuế quá hạn {i["late"]} ngày, {_xu(i["debt"])} xu (quỹ đang có {_xu(i["till"])} xu)'
            for i in f['items']]
    return '📋 Phát hiện: ' + '; '.join(rows) + '.'


def _overdue(c: dict, ids=None) -> list[dict]:
    f = c['ops']['finance']
    return sorted((b for b in f['bills'] if b['kind'] == 'tax' and b['status'] == 'unpaid' and b['due'] < c['day']
                   and (ids is None or b['id'] in ids)), key=lambda b: (b['due'], b['id']))


def _pay(s: dict, c: dict, bills: list[dict]) -> int:
    from . import engine as eng
    paid = 0
    for b in bills:
        if c['money'] < b['amount']:
            continue
        eng.money(s, c, -b['amount'], f'{LABEL_COLLECT} · {b["label"]}'[:300], b['id'], category='tax')
        b['status'] = 'paid'
        b['paid_day'] = c['day']
        paid += b['amount']
    return paid


def _sell(s: dict, c: dict, career: str, need_xu: int) -> int:
    """Kê biên: shelf stock taken at its cost (oldest first) until `need_xu` is covered; the proceeds go into the till."""
    from . import engine as eng
    from . import inventory as inv
    x = (c.get('ext') or {}).get('inv')
    if not x or need_xu <= 0:
        return 0
    cost = {i['id']: int(i.get('cost') or 0) for i in inv.catalogue(career)}
    got = 0
    for lot in sorted((l for l in x['lots'] if l['qty'] > 0 and l['expires'] >= c['day']), key=lambda l: (l['received'], l['id'])):
        unit = max(int(lot.get('unit_cost') or 0), cost.get(lot['item'], 0), 1)
        take = min(lot['qty'], -(-(need_xu - got) // unit))
        lot['qty'] -= take
        got += take * unit
        if got >= need_xu:
            break
    x['lots'] = [l for l in x['lots'] if l['qty'] > 0]
    if got:
        eng.money(s, c, got, LABEL_SALE, None, category='tax')
    return got


def apply(s: dict, measure: str, f: dict) -> dict:
    """An approved collect / seize on the shop's save: {paid, sold, due, lines} (due: the bills of the findings still
    unpaid when it ran; 0 = the owner paid them meanwhile). Only those bills, never into debt."""
    out = dict(paid=0, sold=0, due=0, lines=[])
    for it in f.get('items') or ():
        c = (s.get('careers') or {}).get(it['career'])
        if not isinstance(c, dict):
            continue
        bills = _overdue(c, set(it['bills']))
        if not bills:
            continue
        out['due'] += len(bills)
        if measure == 'seize':
            short = sum(b['amount'] for b in bills) - c['money']
            out['sold'] += _sell(s, c, it['career'], short)
        out['paid'] += _pay(s, c, bills)
    return out


def reverse(s: dict, outcome: dict) -> int:
    """A measure reversed after an appeal: what it took goes back to the first career's till (a ledger line)."""
    from . import engine as eng
    give = int(outcome.get('paid') or 0)
    cid = outcome.get('career')
    c = (s.get('careers') or {}).get(cid) if cid else None
    if give <= 0 or not isinstance(c, dict):
        return 0
    eng.money(s, c, give, LABEL_BACK, None, category='tax')
    return give


def reward(s: dict) -> str:
    c, rec, x = officer_of(s)
    if x is None:
        return ''
    x['adj'] = min(10, x['adj'] + REWARD_ADJ)
    return '⭐ Xử lý đúng, có căn cứ: +0,1★ ngày công tác.'


def wrong(s: dict, key: str, serious: bool) -> str:
    """The officer's (or approver's) save after a case handled without grounds (gov_rules.WRONG_CASE, or khai trừ)."""
    from . import gov_rules as gr
    return gr.hq_wrong(s, key, serious)


# ===================================================================================== the database (thin)
def _read(store, sid: str):
    return _mr()._read_state(store, sid)


def _mutate(store, fns: dict, ops=None):
    return _mr()._mutate_retry(store, fns, ops)


def _lock(db, key: str) -> None:
    db.execute('SELECT pg_advisory_xact_lock(17843, hashtext(?))', (key,))


def _push(store, sid: str, text: str) -> None:
    from . import push
    try:
        store.transaction(lambda db: push.queue(db, sid, INBOX, text[:160], '/'), 250)
    except Exception:  # noqa: BLE001 - best effort
        pass


def _pid(sid: str) -> str:
    from .social import pid_of
    return pid_of(sid)


def _inbox(db, sid: str, text: str) -> None:
    db.execute('INSERT INTO inbox(pid,kind,text,ref,at) VALUES(?,?,?,?,?)', (_pid(sid), INBOX, text[:300], None, now()))


def _sid_of(db, pid) -> str | None:
    if not isinstance(pid, str) or not PID_RE.fullmatch(pid):
        return None
    r = db.execute('SELECT sid FROM profiles WHERE pid=?', (pid,)).fetchone()
    return r['sid'] if r else None


def _account(db, sid: str) -> bool:
    return bool(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone())


def _name(db, sid: str) -> str:
    return _mr()._display(db, sid)


def _close(db, a: str, b: str) -> bool:
    """Friends or spouses: never inspect or review each other."""
    from . import friends as fr
    if fr.are_friends(db, a, b):
        return True
    r = db.execute('SELECT b1.couple FROM marriage_bonds b1 JOIN marriage_bonds b2 ON b1.couple=b2.couple WHERE b1.sid=? AND b2.sid=?',
                   (a, b)).fetchone()
    return bool(r)


def _case(db, case_id) -> dict | None:
    if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
        return None
    r = db.execute(f'SELECT {COLS} FROM hq_cases WHERE id=?', (case_id,)).fetchone()
    return dict(r) if r else None


def _move(db, case_id: str, frm: str, to: str, **kw) -> bool:
    sets = ['status=?'] + [f'{k}=?' for k in kw]
    return db.execute(f'UPDATE hq_cases SET {",".join(sets)} WHERE id=? AND status=?', (to, *kw.values(), case_id, frm)).rowcount == 1


def _wrongs(db, sid: str, t: float) -> int:
    r = db.execute('SELECT COUNT(*) AS n FROM hq_cases WHERE ((officer=? AND wrong=1) OR (reviewer=? AND rwrong=1)) AND at>?',
                   (sid, sid, t - WRONG_DAYS * 86400)).fetchone()
    return int(r['n'])


def checks(db, officer: str, target: str, t: float) -> None:
    """The limits of a new inspection (again inside the transaction that records it, both locked)."""
    day = vn_day(t)
    n = db.execute('SELECT COUNT(*) AS n FROM hq_cases WHERE officer=? AND day=? AND at>?', (officer, day, t - 2 * 86400)).fetchone()['n']
    need(int(n) < OFFICER_DAY_MAX, f'Hôm nay bạn đã kiểm tra đủ {OFFICER_DAY_MAX} cửa hàng. Mai làm tiếp nhé.', 'hq_day_max', 429)
    r = db.execute('SELECT officer,at FROM hq_cases WHERE target=? AND at>? ORDER BY at DESC LIMIT 5', (target, t - PAIR_S)).fetchall()
    need(not any(x['at'] > t - TARGET_S for x in r), 'Cửa hàng này vừa được kiểm tra trong 24 giờ qua.', 'hq_recent', 429)
    need(not any(x['officer'] == officer for x in r), 'Bạn đã kiểm tra cửa hàng này gần đây: để đồng nghiệp khác làm.', 'hq_pair', 429)


def _settle_review(store, row: dict, ok: bool, reviewer: str, t: float, rname: str = '') -> dict:
    """Approve or reject a case in 'review' (a player reviewer or the Cục's NPC review: reviewer '')."""
    f = json.loads(row['finding'])
    proper = bool(row['proper'])
    got: dict = {}
    pair = f'hq:{row["id"]}'
    officer_wrong = (ok and not proper and bool(reviewer)) or (not ok and not proper)
    approver_wrong = ok and not proper and bool(reviewer)
    serious_o = serious_r = False
    with store.connect() as db:
        if officer_wrong:
            serious_o = _wrongs(db, row['officer'], t) + 1 >= WRONG_MAX
        if approver_wrong:
            serious_r = _wrongs(db, reviewer, t) + 1 >= WRONG_MAX
    fns = {}
    if ok:
        def shop(s):
            res = apply(s, row['measure'], f)
            res['career'] = next((i['career'] for i in f['items']), '')
            got['res'] = res
        fns[row['target']] = shop
    if officer_wrong:
        fns[row['officer']] = lambda s: got.__setitem__('o', wrong(s, pair + ':o', serious_o))
    elif ok and proper:
        fns[row['officer']] = lambda s: got.__setitem__('o', reward(s))
    if approver_wrong and reviewer != row['officer']:
        fns[reviewer] = lambda s: got.__setitem__('r', wrong(s, pair + ':r', serious_r))

    def ops(db):
        res = got.get('res') or {}
        paid = int(res.get('paid') or 0)
        status = 'rejected' if not ok else ('done' if res.get('due') else 'void')
        moved = _move(db, row['id'], 'review', status, reviewer=reviewer, review_at=t, amount=paid,
                      outcome=json.dumps(res, ensure_ascii=False, separators=(',', ':'))[:2000] if ok else '',
                      wrong=1 if officer_wrong else 0, rwrong=1 if approver_wrong else 0)
        need(moved, 'Hồ sơ này đã được xử lý rồi.', 'hq_gone')
        who = rname or 'Cục Hải quan Thành phố'
        name = MEASURES[row['measure']]
        if not ok:
            _inbox(db, row['officer'], f'🛃 {who} không duyệt đề xuất {name}: {"chưa đủ căn cứ" if not proper else "chưa cần thiết lúc này"}.')
        elif paid:
            _inbox(db, row['target'], f'🛃 {who} duyệt {name}: đã nộp {_xu(paid)} xu thuế quá hạn'
                   + (f' (bán hàng tồn {_xu(res["sold"])} xu)' if res.get('sold') else '') + '. Bạn có thể khiếu nại trong 3 ngày.')
            _inbox(db, row['officer'], f'🛃 {who} duyệt đề xuất {name}: đã thu {_xu(paid)} xu vào ngân sách.')
        elif status == 'done':
            _inbox(db, row['target'], f'🛃 {who} duyệt {name}: quỹ cửa hàng chưa đủ để trích, khoản thuế quá hạn vẫn còn nợ. Nộp sớm trong Sổ tiệm nhé.')
            _inbox(db, row['officer'], f'🛃 {who} duyệt đề xuất {name}: quỹ cửa hàng chưa đủ để trích, khoản thuế vẫn còn nợ.')
        else:
            _inbox(db, row['officer'], f'🛃 {name}: khoản thuế đã được nộp trước khi duyệt, hồ sơ khép lại.')
        if officer_wrong:
            _inbox(db, row['officer'], '⚖️ Xử lý sai, chèn ép doanh nghiệp: ' + (got.get('o') or 'ghi vào hồ sơ công tác.'))
        if approver_wrong:
            _inbox(db, reviewer, '⚖️ Duyệt đề xuất không có căn cứ: ' + (got.get('r') or 'ghi vào hồ sơ công tác.'))
        return status
    status = _mutate(store, fns, ops)['db'] if fns else store.transaction(ops)
    return dict(status=status, res=got.get('res'), o=got.get('o', ''), r=got.get('r', ''))


def sweep(store, t: float | None = None, limit: int = 5) -> None:
    """The Cục's automatic review of cases waiting past REVIEW_S (called by any hq_* request; a few at a time)."""
    t = now() if t is None else t
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f"SELECT {COLS} FROM hq_cases WHERE status='review' AND at<? ORDER BY at LIMIT ?",
                                            (t - REVIEW_S, limit)).fetchall()]
    for row in rows:
        try:
            _settle_review(store, row, bool(row['proper']), '', t)
        except Exception:  # noqa: BLE001 - another request settled it, or a save moved: the next sweep tries again
            pass


def view(row: dict, names: dict | None = None, role: str = 'officer') -> dict:
    f = json.loads(row['finding'] or '{}')
    out = dict(id=row['id'], at=int(row['at']), status=row['status'], measure=row['measure'], text=finding_text(f),
               debt=f.get('debt', 0), late=f.get('late', 0), found=bool(f.get('items')))
    if names:
        out['name'] = names.get(row['target' if role != 'target' else 'officer'], '')
    if row['status'] == 'done':
        res = json.loads(row['outcome'] or '{}')
        out['paid'], out['sold'] = int(res.get('paid') or 0), int(res.get('sold') or 0)
    if role == 'target':
        out['appeal'] = int(row['appeal'] or 0)
        out['can_appeal'] = row['status'] == 'done' and not row['appeal'] and now() - float(row['review_at'] or row['at']) < APPEAL_S
    return out


# ===================================================================================== handlers
def _me(store, sid: str):
    loaded = _read(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    return loaded[0]


def op_shops(store, sid: str, display: str, d: dict) -> dict:
    """hq_shops {}: shops on the street an officer may inspect, today's count, my open cases."""
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t)
    need(why is None, why or '', 'hq_off', 403)
    sweep(store, t)
    from .social import pid_of
    with store.connect() as db:
        rows = db.execute('SELECT pid,sid,name,shop FROM profiles WHERE visible=1 AND hidden=0 AND name IS NOT NULL AND seen>? '
                          'ORDER BY seen DESC, pid LIMIT ?', (t - SEEN_S, LIST_MAX * 2)).fetchall()
        day = vn_day(t)
        n = int(db.execute('SELECT COUNT(*) AS n FROM hq_cases WHERE officer=? AND day=? AND at>?', (sid, day, t - 2 * 86400)).fetchone()['n'])
        mine = [dict(r) for r in db.execute(f'SELECT {COLS} FROM hq_cases WHERE officer=? AND at>? ORDER BY at DESC LIMIT 20',
                                            (sid, t - 7 * 86400)).fetchall()]
        names = {r['target']: _name(db, r['target']) for r in mine}
        shops = []
        for r in rows:
            if r['sid'] == sid or _close(db, sid, r['sid']):
                continue
            try:
                shop = json.loads(r['shop'] or '{}')
            except ValueError:
                shop = {}
            careers = [x.get('name') or x.get('id') for x in shop.get('careers') or () if isinstance(x, dict)][:4]
            shops.append(dict(pid=r['pid'], name=r['name'], careers=careers))
            if len(shops) >= LIST_MAX:
                break
    return dict(message='', quiet=True, shops=shops, left=max(0, OFFICER_DAY_MAX - n),
                cases=[view(r, names) for r in mine], measures=MEASURES, me=pid_of(sid))


def op_inspect(store, sid: str, display: str, d: dict) -> dict:
    """hq_inspect {pid}: 🔎 inspect a shop's warehouse and tax book."""
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t)
    need(why is None, why or '', 'hq_off', 403)
    sweep(store, t)
    with store.connect() as db:
        need(_account(db, sid), 'Cần tài khoản để ký biên bản kiểm tra.', 'hq_guest', 403)
        target = _sid_of(db, d.get('pid'))
        need(target, 'Không tìm thấy cửa hàng này.', 'not_found', 404)
        need(target != sid, 'Không tự kiểm tra cửa hàng của mình được.', 'self')
        need(_account(db, target), 'Chủ cửa hàng chưa có tài khoản: chưa kiểm tra được.', 'hq_guest')
        need(not _close(db, sid, target), 'Người quen, vợ chồng: phải xin rút, để đồng nghiệp khác kiểm tra.', 'hq_conflict')
        checks(db, sid, target, t)
        name = _name(db, target)
    loaded = _read(store, target)
    need(loaded, 'Không tìm thấy cửa hàng này.', 'not_found', 404)
    f = findings(loaded[0])
    case_id = 'hq' + secrets.token_hex(8)
    row = dict(id=case_id, officer=sid, target=target, at=t, day=vn_day(t), status='found' if f['items'] else 'clear', measure='',
               finding=json.dumps(f, ensure_ascii=False, separators=(',', ':')), proper=0, opost=post_of(me), reviewer='',
               review_at=None, outcome='', amount=0, appeal=0, appeal_at=None, wrong=0, rwrong=0)
    who = (display or 'Công chức Hải quan')[:40]

    def rec(db):
        for k in sorted((f'o:{sid}', f't:{target}')):
            _lock(db, k)
        checks(db, sid, target, t)
        db.execute(f'INSERT INTO hq_cases({COLS}) VALUES({",".join("?" * len(COLS.split(",")))})', tuple(row[k] for k in COLS.split(',')))
        _inbox(db, target, f'🛃 {who} (Hải quan) vừa kiểm tra kho, sổ thuế cửa hàng của bạn. {finding_text(f)}')
    store.transaction(rec)
    _push(store, target, f'🛃 Hải quan vừa kiểm tra kho cửa hàng của bạn.')
    return dict(message=finding_text(f), quiet=True, case=view(row, {target: name}),
                measures=list(MEASURES) if f['items'] else [])


def op_propose(store, sid: str, display: str, d: dict) -> dict:
    """hq_propose {case, measure}: the officer's proposal for a case with findings."""
    measure = d.get('measure')
    need(measure in MEASURES, 'Chọn biện pháp xử lý nhé.', 'bad_measure', 400)
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t, review=True)
    need(why is None, why or '', 'hq_off', 403)
    with store.connect() as db:
        row = _case(db, d.get('case'))
    need(row and row['officer'] == sid, 'Không tìm thấy hồ sơ kiểm tra này.', 'not_found', 404)
    need(row['status'] == 'found', 'Hồ sơ này đã xử lý rồi.', 'hq_gone')
    f = json.loads(row['finding'])
    proper = grounded(f, measure)
    if measure == 'remind':
        def ops(db):
            need(_move(db, row['id'], 'found', 'done', measure='remind', proper=1, review_at=t, outcome='{}'), 'Hồ sơ này đã xử lý rồi.', 'hq_gone')
            _inbox(db, row['target'], f'📨 Hải quan nhắc: cửa hàng còn {_xu(f["debt"])} xu thuế quá hạn. Nộp sớm trong Sổ tiệm để tránh cưỡng chế.')
        store.transaction(ops)
        _push(store, row['target'], '📨 Hải quan nhắc nộp thuế quá hạn.')
        return dict(message='📨 Đã gửi giấy nhắc nộp thuế.', quiet=True)

    def ops(db):
        need(_move(db, row['id'], 'found', 'review', measure=measure, proper=1 if proper else 0, opost=post_of(me)),
             'Hồ sơ này đã xử lý rồi.', 'hq_gone')
        _inbox(db, row['target'], f'🛃 Hải quan đề xuất {MEASURES[measure]} với cửa hàng của bạn, chờ cấp trên duyệt.')
    store.transaction(ops)
    _push(store, row['target'], f'🛃 Hải quan đề xuất {MEASURES[measure]}, chờ duyệt.')
    return dict(message=f'Đã trình {MEASURES[measure]}: chờ cấp trên duyệt (quá {REVIEW_S // 3600} giờ, Cục tự xét).', quiet=True)


def op_reviews(store, sid: str, display: str, d: dict) -> dict:
    """hq_reviews {}: proposals waiting for someone at my post or above it."""
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t, review=True)
    need(why is None, why or '', 'hq_off', 403)
    sweep(store, t)
    mine = POST_ORDER.get(post_of(me), -1)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f"SELECT {COLS} FROM hq_cases WHERE status='review' AND at>? ORDER BY at LIMIT 40",
                                            (t - REVIEW_S - 3600, )).fetchall()]
        out = []
        for r in rows:
            if r['officer'] == sid or r['target'] == sid or POST_ORDER.get(r['opost'], 99) >= mine or _close(db, sid, r['target']):
                continue
            v = view(r, {r['target']: _name(db, r['target'])})
            v['by'] = _name(db, r['officer'])
            out.append(v)
    return dict(message='', quiet=True, reviews=out[:20])


def op_review(store, sid: str, display: str, d: dict) -> dict:
    """hq_review {case, ok}: a higher-post officer approves or rejects a proposal."""
    ok = d.get('ok')
    need(type(ok) is bool, 'Chọn duyệt hay không duyệt nhé.', 'bad_ok', 400)
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t, review=True)
    need(why is None, why or '', 'hq_off', 403)
    with store.connect() as db:
        row = _case(db, d.get('case'))
        need(row and row['status'] == 'review', 'Hồ sơ này đã được xử lý rồi.', 'hq_gone')
        need(row['officer'] != sid and row['target'] != sid, 'Không tự duyệt hồ sơ của mình được.', 'self')
        need(POST_ORDER.get(row['opost'], 99) < POST_ORDER.get(post_of(me), -1), 'Chỉ cấp trên của người đề xuất mới được duyệt.', 'hq_rank', 403)
        need(not _close(db, sid, row['target']), 'Người quen, vợ chồng của chủ cửa hàng: phải xin rút.', 'hq_conflict')
    out = _settle_review(store, row, ok, sid, t, (display or 'Cấp trên')[:40])
    msg = {'done': '✅ Đã duyệt: biện pháp được thi hành.', 'void': 'Khoản thuế đã được nộp: hồ sơ khép lại.',
           'rejected': 'Đã không duyệt đề xuất.'}[out['status']]
    if out.get('r'):
        msg += ' ' + out['r']
    return dict(message=msg, quiet=True)


def op_mine(store, sid: str, display: str, d: dict) -> dict:
    """hq_mine {}: the cases on my shops (30 days), with the appeal."""
    t = now()
    sweep(store, t)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f'SELECT {COLS} FROM hq_cases WHERE target=? AND at>? ORDER BY at DESC LIMIT 20',
                                            (sid, t - 30 * 86400)).fetchall()]
        names = {r['officer']: _name(db, r['officer']) for r in rows}
    return dict(message='', quiet=True, cases=[view(r, names, 'target') for r in rows])


def op_appeal(store, sid: str, display: str, d: dict) -> dict:
    """hq_appeal {case}: 📣 the owner appeals an applied measure; the Cục decides at once."""
    t = now()
    with store.connect() as db:
        row = _case(db, d.get('case'))
    need(row and row['target'] == sid, 'Không tìm thấy hồ sơ này.', 'not_found', 404)
    need(row['status'] == 'done' and not row['appeal'], 'Hồ sơ này không khiếu nại được nữa.', 'hq_gone')
    need(t - float(row['review_at'] or row['at']) < APPEAL_S, 'Đã quá 3 ngày, hết hạn khiếu nại.', 'hq_late')
    if row['proper']:
        def ops(db):
            need(db.execute('UPDATE hq_cases SET appeal=2,appeal_at=? WHERE id=? AND appeal=0', (t, row['id'])).rowcount == 1,
                 'Hồ sơ này đã được khiếu nại rồi.', 'hq_gone')
            _inbox(db, sid, '📣 Cục Hải quan trả lời khiếu nại: biện pháp có căn cứ (thuế quá hạn), giữ nguyên.')
        store.transaction(ops)
        return dict(message='📣 Cục Hải quan giữ nguyên: biện pháp có căn cứ.', quiet=True)
    res = json.loads(row['outcome'] or '{}')
    got: dict = {}
    pair = f'hq:{row["id"]}'
    fns = {sid: lambda s: got.__setitem__('back', reverse(s, res))}
    with store.connect() as db:
        o_n = _wrongs(db, row['officer'], t)
        r_n = _wrongs(db, row['reviewer'], t) if row['reviewer'] else 0
    if not row['wrong']:
        fns[row['officer']] = lambda s: got.__setitem__('o', wrong(s, pair + ':o', o_n + 1 >= WRONG_MAX))
    if row['reviewer'] and not row['rwrong'] and row['reviewer'] != row['officer']:
        fns[row['reviewer']] = lambda s: got.__setitem__('r', wrong(s, pair + ':r', r_n + 1 >= WRONG_MAX))

    def ops(db):
        need(db.execute("UPDATE hq_cases SET appeal=3,appeal_at=?,status='reversed',wrong=1,rwrong=? WHERE id=? AND appeal=0 AND status='done'",
                        (t, 1 if row['reviewer'] else 0, row['id'])).rowcount == 1, 'Hồ sơ này đã được khiếu nại rồi.', 'hq_gone')
        _inbox(db, row['officer'], '⚖️ Khiếu nại của chủ cửa hàng được chấp nhận: ' + (got.get('o') or 'ghi vào hồ sơ công tác.'))
        if row['reviewer'] and got.get('r'):
            _inbox(db, row['reviewer'], '⚖️ Hồ sơ bạn duyệt bị hủy sau khiếu nại: ' + got['r'])
    _mutate(store, fns, ops)
    return dict(message=f'📣 Khiếu nại được chấp nhận: hoàn trả {_xu(got.get("back") or 0)} xu vào quỹ cửa hàng.', quiet=True)


ACTIONS = dict(hq_shops=op_shops, hq_inspect=op_inspect, hq_propose=op_propose, hq_reviews=op_reviews, hq_review=op_review,
               hq_mine=op_mine, hq_appeal=op_appeal)
