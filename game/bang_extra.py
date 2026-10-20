"""⚔️ Bang "nhiều hơn" (owner 20/10 "bang hội nữa nhiều hơn"): more for a bang to build and do together. Numbers and
names: game/bang_extra_content.py. Database only (POST /api/bang/<op> through game/bang.py OPS), no save key, no new
table, no schema step:

* 🏯 Kiểu đại sảnh (op hall {style, look, confirm}): the hall on the Đảo bang drawn in another style (the private
  islands' house styles, public/js/house-art.js, big), in one of its three colours. A style needs a Đại sảnh level and
  is bought once from the fund (a pure sink: a bang_fund 'build' row 'h:<bang>:<style>', idempotent); a style bought
  stays bought, switching between owned styles or colours is free but at most once an hour (X.HALL_GAP). Phó bang and
  up. Stored in the hall row's `place` column ('<style>' or '<style>__<n>'), which no build before this one reads:
  rolling back simply shows the old hall again.
* 🎏 Trang trí đảo bang (op decor {id, confirm}): decorations bought once each from the fund, at once (a 'build' row
  'd:<bang>:<id>'), Phó bang and up, standing on fixed spots of the island (public/js/bang-island-layout.js DECOR_AT).
  Stored as bang_facilities rows 'd_<id>' level 1: game/bang.py levels(), the facility list, the ranking
  (`k in C.FACILITIES`) and the island view skip them, in this build and the older ones. Each adds X.DECOR_BONUS % to the
  weekly quests' points (X.DECOR_BONUS_MAX % at most). Nothing else: no income, no ranking points.
* 📋 Nhiệm vụ tuần (op quest {id}): three quests a week for each bang (quests_of: the week and the bang id pick them),
  measured on what the bang's ledgers already hold this Vietnam week (bang_points check-ins and work days, bang_fund
  gifts and builds), targets by the member count. A member who did something for this bang that week claims each done
  quest once (a bang_points 'quest' row 'q:<pid>:<week>:<quest>': idempotent), X.QUEST_WEEK_MAX claims a week every
  bang together. Points are điểm cống hiến (the bang shop); the weekly ranking never counts them (owner 21/10) and
  the members' week column (kinds give/checkin/work/chal) does not either.

There is no way out of the fund here either: no withdraw, transfer or refund (tests/test_bang_extra.py checks the source).
"""
from __future__ import annotations

import hashlib
import math

from . import bang as B
from . import bang_content as C
from . import bang_extra_content as X

need = B.need


# ---------------------------------------------------------------- 🏯 kiểu đại sảnh
def split_hall(place) -> tuple[str, int]:
    """bang_facilities.place of the hall → (style, colour); anything this build does not know → the bang's own hall."""
    s = str(place or '')
    style, _, n = s.partition('__')
    if style not in X.HALL_STYLES:
        return X.HALL_DEFAULT, 0
    look = int(n) if n.isdigit() and 0 < int(n) < X.HALL_LOOKS else 0
    return style, look if style != X.HALL_DEFAULT else 0


def hall_place(style: str, look: int) -> str:
    return f'{style}__{look}' if look and style != X.HALL_DEFAULT else style


def hall_of(db, bid: str) -> tuple[str, int]:
    r = B._row(db, 'SELECT place FROM bang_facilities WHERE bang=? AND fac=?', (bid, C.HALL))
    return split_hall(r['place'] if r else '')


def _owned_styles(db, bid: str) -> set:
    ids = {f'h:{bid}:{s}': s for s in X.HALL_ORDER}
    rows = B._rows(db, "SELECT id FROM bang_fund WHERE bang=? AND kind='build' AND id = ANY(?)", (bid, list(ids)))
    return {X.HALL_DEFAULT} | {ids[r['id']] for r in rows}


def _last_change(db, bid: str) -> float:
    r = B._row(db, "SELECT MAX(at) AS at FROM bang_log WHERE bang=? AND kind='hall'", (bid,))
    return float(r['at']) if r and r['at'] is not None else 0.0


def op_hall(db, sid, data, t):
    bang, me = B._officer(db, sid, C.BUILD_FROM)
    style, look = data.get('style'), data.get('look', 0)
    need(isinstance(style, str) and style in X.HALL_STYLES, 'Chọn một kiểu đại sảnh nhé.')
    need(type(look) is int and 0 <= look < (1 if style == X.HALL_DEFAULT else X.HALL_LOOKS), 'Chọn một màu nhé.')
    bid = bang['id']
    B.finish_builds(db, bid, t)
    name, emoji, hall_need, price = X.HALL_STYLES[style]
    cur = hall_of(db, bid)
    if cur == (style, look):
        return dict(message=f'Đại sảnh đang là {emoji} {name} rồi.', again=True)
    lv = B.levels(db, bid)
    need(lv[C.HALL] >= hall_need, f'{name} cần Đại sảnh cấp {hall_need}.', 'hall')
    owned = style in _owned_styles(db, bid)
    wait = int(_last_change(db, bid) + X.HALL_GAP - t)
    need(wait <= 0, f'Vừa đổi kiểu đại sảnh: {B._wait_text(wait)} nữa mới đổi tiếp được.', 'wait')
    who = B._display(db, sid)
    if not owned:
        fund = int(bang['fund'])
        need(fund >= price, f'Quỹ bang còn thiếu {B.fmt(price - fund)} xu.', 'not_enough')
        need(data.get('confirm') is True, f'Xác nhận dùng {B.fmt(price)} xu quỹ bang mở kiểu {name}.')
        bal = fund - price
        db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, note, at) VALUES(?,?,?,'build',?,?,?,?)",
                   (f'h:{bid}:{style}', bid, sid, -price, bal, f'hall {style}', t))
        db.execute('UPDATE bangs SET fund=?, spent=spent+? WHERE id=?', (bal, price, bid))
    db.execute("INSERT INTO bang_facilities(bang, fac, level, place) VALUES(?, ?, 1, ?) "
               "ON CONFLICT(bang, fac) DO UPDATE SET place=excluded.place", (bid, C.HALL, hall_place(style, look)))
    paid = '' if owned else f' ({B.fmt(price)} xu quỹ)'
    B._log(db, bid, sid, 'hall', f'{who} đổi đại sảnh sang {emoji} {name}{paid}.', t)
    B._bump(db, bid)
    B._isle(db, 'view', bid)
    return dict(message=f'{emoji} Đại sảnh đã khoác diện mạo {name}.' + ('' if owned else f' Trả {B.fmt(price)} xu từ quỹ.'))


# ---------------------------------------------------------------- 🎏 trang trí
def decor_of(db, bid: str) -> list:
    """The decorations standing on this bang's island, in X.DECOR_ORDER."""
    have = {r['fac'][len(X.DECOR_FAC):] for r in B._rows(db, 'SELECT fac FROM bang_facilities WHERE bang=? AND level>=1', (bid,))
            if r['fac'].startswith(X.DECOR_FAC)}
    return [d for d in X.DECOR_ORDER if d in have]


def decor_bonus(n: int) -> int:
    return min(X.DECOR_BONUS_MAX, X.DECOR_BONUS * max(0, n))


def op_decor(db, sid, data, t):
    bang, me = B._officer(db, sid, C.BUILD_FROM)
    did = data.get('id')
    need(isinstance(did, str) and did in X.DECOR, 'Chọn một món trang trí nhé.')
    bid = bang['id']
    name, emoji, price, hall_need, _ = X.DECOR[did]
    if did in decor_of(db, bid):
        return dict(message=f'Bang đã có {emoji} {name} rồi.', again=True)
    need(B.has_island(db, bid), 'Mua 🏝️ Đảo bang trước rồi mới trang trí nhé.', 'island')
    lv = B.levels(db, bid)
    need(lv[C.HALL] >= hall_need, f'{name} cần Đại sảnh cấp {hall_need}.', 'hall')
    fund = int(bang['fund'])
    need(fund >= price, f'Quỹ bang còn thiếu {B.fmt(price - fund)} xu.', 'not_enough')
    need(data.get('confirm') is True, f'Xác nhận dùng {B.fmt(price)} xu quỹ bang mua {name}.')
    bal = fund - price
    db.execute("INSERT INTO bang_fund(id, bang, sid, kind, amount, balance, note, at) VALUES(?,?,?,'build',?,?,?,?)",
               (f'd:{bid}:{did}', bid, sid, -price, bal, f'decor {did}', t))
    db.execute('UPDATE bangs SET fund=?, spent=spent+? WHERE id=?', (bal, price, bid))
    db.execute('INSERT INTO bang_facilities(bang, fac, level, paid) VALUES(?, ?, 1, ?) ON CONFLICT(bang, fac) DO NOTHING',
               (bid, X.DECOR_FAC + did, price))
    B._log(db, bid, sid, 'build', f'{B._display(db, sid)} mua {emoji} {name} cho đảo bang ({B.fmt(price)} xu quỹ).', t)
    B._bump(db, bid)
    B._isle(db, 'view', bid)
    return dict(message=f'{emoji} {name} đã có mặt trên đảo bang: nhiệm vụ tuần +{X.DECOR_BONUS}% điểm.')


# ---------------------------------------------------------------- 📋 nhiệm vụ tuần
def quests_of(bid: str, week: str) -> list:
    """This week's quests for this bang: X.QUESTS_A_WEEK ids, each measure at most once, the same on every process."""
    def rank(q):
        return hashlib.sha256(f'{week}|{bid}|{q}'.encode()).hexdigest()
    out, seen = [], set()
    for q in sorted(X.QUEST_ORDER, key=rank):
        m = X.QUESTS[q][2]
        if m in seen:
            continue
        out.append(q)
        seen.add(m)
        if len(out) == X.QUESTS_A_WEEK:
            break
    return out


def target(qid: str, members: int) -> int:
    _, _, measure, per, lo, hi, _ = X.QUESTS[qid]
    raw = math.ceil(members * per) if measure != 'give' else members * per
    n = max(lo, min(hi, int(raw)))
    return n // 1000 * 1000 if measure == 'give' else n


def _measures(db, bid: str, t: float) -> dict:
    """This week's totals of the bang (a few indexed reads: bang_points (week, bang), bang_fund (bang, at))."""
    week, start = B.vn_week(t), B.week_start(t)
    pts = {r['kind']: int(r['n']) for r in B._rows(
        db, "SELECT kind, COUNT(*) AS n FROM bang_points WHERE week=? AND bang=? AND kind IN ('checkin','work') GROUP BY kind", (week, bid))}
    act = B._row(db, "SELECT COUNT(DISTINCT sid) AS n FROM bang_points WHERE week=? AND bang=? AND kind IN ('checkin','work')", (week, bid))
    fund = {r['kind']: int(r['s']) for r in B._rows(
        db, "SELECT kind, COALESCE(SUM(ABS(amount)), 0) AS s FROM bang_fund WHERE bang=? AND at>=? AND kind IN ('give','build') GROUP BY kind",
        (bid, start))}
    return dict(checkin=pts.get('checkin', 0), work=pts.get('work', 0), active=int(act['n']) if act else 0,
                give=fund.get('give', 0), build=1 if fund.get('build', 0) > 0 else 0)


def _did_something(db, bid: str, sid: str, week: str) -> bool:
    """Has this member done anything for the bang this week: a check-in, a work day or a gift here."""
    return db.execute("SELECT 1 FROM bang_points WHERE sid=? AND bang=? AND week=? AND kind IN ('checkin','work','give') LIMIT 1",
                      (sid, bid, week)).fetchone() is not None


def _claimed(db, sid: str, week: str) -> tuple[set, int]:
    """(quest ids I claimed in this week, every bang; how many)."""
    rows = B._rows(db, "SELECT id FROM bang_points WHERE sid=? AND week=? AND kind='quest'", (sid, week))
    return {r['id'].rsplit(':', 1)[-1] for r in rows}, len(rows)


def quest_card(db, bid: str, sid: str, t: float, members: int, decor_n: int) -> dict:
    week = B.vn_week(t)
    got = _measures(db, bid, t)
    mine, used = _claimed(db, sid, week)
    did = _did_something(db, bid, sid, week)
    bonus = decor_bonus(decor_n)
    out = []
    for q in quests_of(bid, week):
        emoji, text, measure, *_, pts = X.QUESTS[q]
        n = target(q, members)
        have = min(n, got[measure])
        out.append(dict(id=q, emoji=emoji, text=text.format(n=B.fmt(n)), have=have, need=n, done=have >= n,
                        pts=pts * (100 + bonus) // 100, claimed=q in mine))
    return dict(week=week, ends=B.week_end(week), list=out, bonus=bonus, active=did, used=used, max=X.QUEST_WEEK_MAX)


def op_quest(db, sid, data, t):
    qid = data.get('id')
    need(isinstance(qid, str) and qid in X.QUESTS, 'Chọn một nhiệm vụ nhé.')
    me = B._mine(db, sid)
    need(me is not None, 'Vào một bang để nhận thưởng nhiệm vụ nhé.', 'not_member')
    bang = B._lock(db, me['bang']).get(me['bang'])
    need(bang is not None, 'Vào một bang để nhận thưởng nhiệm vụ nhé.', 'not_member')
    me = B._need_member(db, sid, bang['id'])
    bid, week = bang['id'], B.vn_week(t)
    need(qid in quests_of(bid, week), 'Nhiệm vụ này không có trong tuần này.', 'not_this_week')
    ref = f'q:{me["pid"]}:{week}:{qid}'
    if db.execute('SELECT 1 FROM bang_points WHERE id=?', (ref,)).fetchone():
        return dict(message='Bạn đã nhận thưởng nhiệm vụ này rồi.', again=True)
    n = target(qid, B._count(db, bid))
    need(_measures(db, bid, t)[X.QUESTS[qid][2]] >= n, 'Nhiệm vụ chưa xong: cả bang cố thêm chút nữa nhé!', 'not_done')
    need(_did_something(db, bid, sid, week), 'Góp sức cho bang tuần này (điểm danh, làm việc hoặc góp quỹ) rồi nhận thưởng nhé.', 'idle')
    _, used = _claimed(db, sid, week)
    need(used < X.QUEST_WEEK_MAX, f'Tuần này bạn đã nhận đủ {X.QUEST_WEEK_MAX} phần thưởng nhiệm vụ.', 'week_max')
    pts = X.QUESTS[qid][6] * (100 + decor_bonus(len(decor_of(db, bid)))) // 100
    ok = B._earn(db, bid, sid, ref, 'quest', pts, t)
    need(ok, 'Bạn đã nhận thưởng nhiệm vụ này rồi.', 'done')
    B._bump(db, bid)
    return dict(message=f'📋 Nhiệm vụ xong: +{pts} điểm cống hiến.')


# ---------------------------------------------------------------- the page and the island
def page_part(db, bid: str, sid: str, lv: dict, members: int, t: float) -> dict:
    """What game/bang.py page() adds for a member: the hall's styles, the decorations, this week's quests."""
    style, look = hall_of(db, bid)
    owned = _owned_styles(db, bid)
    decor = decor_of(db, bid)
    last = _last_change(db, bid)
    return dict(
        hall=dict(style=style, look=look, wait=max(0, int(last + X.HALL_GAP - t)),
                  list=[dict(id=s, name=n, emoji=e, hall=h, price=p, owned=s in owned, open=lv[C.HALL] >= h)
                        for s, (n, e, h, p) in X.HALL_STYLES.items()]),
        decor=dict(have=decor, bonus=decor_bonus(len(decor)), max=X.DECOR_BONUS_MAX, per=X.DECOR_BONUS,
                   list=[dict(id=d, name=n, emoji=e, price=p, hall=h, blurb=b, owned=d in decor, open=lv[C.HALL] >= h)
                         for d, (n, e, p, h, b) in X.DECOR.items()]),
        quests=quest_card(db, bid, sid, t, members, len(decor)))


def island_part(db, bid: str) -> dict:
    """What the island view adds (game/bang_island.py validate_view keeps it): the hall's style, the decorations."""
    style, look = hall_of(db, bid)
    return dict(hall=dict(style=style, look=look), decor=decor_of(db, bid))


OPS = dict(hall=op_hall, decor=op_decor, quest=op_quest)
