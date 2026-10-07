"""Guards of the classic pharmacy and bookkeeping desks, written once and run in two modes (UI wave 5,
docs/UI_KIT.md "Disabled with a reason").

The engine's commands call them with the default `need` (kit.need: refuse, as before); the public task view
runs them through kit.check and sends the result as `can` (True | {why, fix}), so the page draws the button
dimmed with the refusal's own words before the player taps it. Same messages, same order as the refusals.
Rules read only. `can` is a view field: never saved, never part of task generation.

  ph_ready(t, c)               ph_check / ph_deliver: the tray against the slip (engine.ensure_pharmacy)
  ac_match_rules(t, ds, ts)    ac_match: the picked documents and transactions (engine "ac_match")
  ac_complete_rules(t)         ac_complete: every card settled (engine "ac_complete")
  ph_view(t, c) / ac_view(t)   the `can` view fields
"""
from __future__ import annotations

from .careers import kit

DONE = ('completed', 'referred', 'cancelled')


# ---------------------------------------------------------------- pharmacy
def ph_ready(t: dict, c: dict, need=kit.need) -> None:
    """The tray matches the slip: known, not a referral, the right count, the right code, lots that may go out,
    labels read, the shelf clean, the stock there. (engine.ensure_pharmacy; ph_check adds the three ticks.)"""
    e = kit.eng()
    need(t['known'], 'Phiếu chưa đủ thông tin, cần hỏi lại hoặc chuyển người phụ trách.',
         fix=dict(cmd='ask', payload=dict(task=t['id']), label='💬 Hỏi rõ phiếu'))
    need(not t['needs']['referral'], 'Yêu cầu này cần chuyển người phụ trách, không lấy hộp thay thế.',
         fix=dict(act='referPH', label='Chuyển cô Thu'))
    n = t['needs']
    have = sum(t['basket'].values())
    need(have == n['qty'], 'Số lượng trong khay chưa khớp phiếu.',
         fix=dict(sel='.dw-lots', label='➕ Lấy thêm') if have < n['qty'] else dict(sel='.dw-traylist', label='➖ Bỏ bớt'))
    for lid, qty in t['basket'].items():
        lot = e.LOT_INDEX.get(lid)
        need(lot and lot['product'] == n['product'], 'Mã hộp chưa khớp phiếu.', fix=dict(sel='.dw-traylist', label='➖ Bỏ hộp sai mã'))
        need(lot['status'] == 'available' and lid not in c['held_lots'] and lot['valid_until'] >= c['day'],
             'Lô này không được xuất: tạm giữ hoặc không còn hợp lệ.', fix=dict(sel='.dw-traylist', label='➖ Bỏ hộp'))
        need(lid in t['inspected'], 'Mở nhãn lô đã chọn để đọc trước khi xác nhận.',
             fix=dict(cmd='ph_inspect', payload=dict(task=t['id'], lot=lid), label='👁️ Đọc nhãn ' + lid))
        block = e.ph_shelf_block(c, lid)
        need(not block, block or '')
        need(c['stock'].get(lid, 0) >= qty, 'Số lượng kho của lô không đủ.')


def ph_view(t: dict, c: dict) -> dict | None:
    """can.ph_check for a classic slip still on the counter (the three ticks are the page's own: it adds that
    reason itself, after this one, as the command does)."""
    if t.get('desk') or t.get('status') in DONE:
        return None
    return dict(ph_check=kit.check(ph_ready, t, c))


# ---------------------------------------------------------------- bookkeeping
def ac_match_rules(t: dict, ds, ts, need=kit.need, cards: bool = False) -> None:
    """ac_match's refusals in order. cards=True: only the rules about the cards themselves (read, not missing,
    not removed, not in another group, not a copy, the amount as in the original), for one card at a time."""
    docs = {d['id']: d for d in t['docs']}
    if not cards:
        need(isinstance(ds, list) and isinstance(ts, list) and 1 <= len(ds) <= 6 and 1 <= len(ts) <= 6, 'Chọn phiếu và giao dịch để ghép.')
        need(all(isinstance(x, str) for x in ds + ts), 'Mã nhóm chưa hợp lệ.')
        need(len(set(ds)) == len(ds) and len(set(ts)) == len(ts), 'Không lặp thẻ trong cùng nhóm.')
        need(len(ds) == 1 or len(ts) == 1, 'Ghép theo từng quan hệ nhiều-một hoặc một-nhiều, không gộp cả hồ sơ.')
    trans = {x['id']: x for x in t['transactions']}
    need(all(x in docs for x in ds) and all(x in trans for x in ts), 'Mã thẻ không tồn tại.')
    unread = next((x for x in ds if x not in t['inspected'] and not docs[x].get('missing') and x not in t['removed']), None)
    need(all(x in t['inspected'] and x not in t['removed'] and not docs[x].get('missing') for x in ds), 'Đọc đủ bản gốc, không ghép thẻ thiếu hoặc đã loại.',
         fix=dict(cmd='ac_inspect', payload=dict(task=t['id'], doc=unread), label='👁️ Mở gốc ' + unread) if unread else None)
    need(not any(set(ds) & set(g['docs']) or set(ts) & set(g['transactions']) for g in t['groups']), 'Có thẻ đã nằm trong nhóm khác. Tháo nhóm cũ để ghép lại.')
    copy = next((x for x in ds if docs[x].get('duplicate_of')), None)
    need(not copy, 'Có bản sao cùng nguồn trong nhóm; đối chiếu và loại trùng trước nhé.',
         fix=dict(cmd='ac_duplicate', payload=dict(task=t['id'], doc=copy), label='🗂️ Loại trùng ' + copy) if copy and docs[copy]['duplicate_of'] in t['inspected'] else None)
    off = next((x for x in ds if docs[x]['amount'] != docs[x]['original']), None)
    need(not off, 'Số nhập còn khác nguồn. Điều chỉnh có căn cứ trước.',
         fix=dict(cmd='ac_correct', payload=dict(task=t['id'], doc=off), label='✏️ Sửa ' + off + ' theo gốc') if off else None)
    if cards:
        return
    a = sum(docs[x]['amount'] for x in ds)
    b = sum(trans[x]['amount'] for x in ts)
    need(a == b, f'Tổng phiếu {a} xu chưa khớp giao dịch {b} xu. Thử kiểm phần còn thiếu nhé.')
    refs = {docs[x]['ref'] for x in ds}
    txrefs = set(r for x in ts for r in trans[x]['refs'])
    need(refs == txrefs, 'Tổng giống nhau nhưng tham chiếu nguồn chưa khớp. Kiểm mã hóa đơn nhé.')


def ac_complete_rules(t: dict, need=kit.need) -> None:
    """ac_complete's refusals about the board (the explanation it also checks is the page's fixed choice)."""
    valid = [d for d in t['docs'] if d['id'] not in t['removed']]
    linked = {x for g in t['groups'] for x in g['docs']}
    txlinked = {x for g in t['groups'] for x in g['transactions']}
    need(all(d['id'] in linked and not d.get('missing') and not d.get('duplicate_of') for d in valid),
         'Còn chứng từ chưa đối chiếu, thiếu nguồn hoặc chưa loại bản trùng.')
    need(len(txlinked) == len(t['transactions']), 'Còn giao dịch chưa ghép.')


def ac_view(t: dict) -> dict | None:
    """can.ac_match: {doc id: {why, fix}} for the free cards that could not go into any group yet (a card that
    can go is left out); the page adds the rules about the picked set (one-many, the sums, the codes), in the
    command's order. can.ac_complete: True | {why, fix}."""
    if t.get('desk') or t.get('status') in DONE:
        return None
    grouped = {x for g in t['groups'] for x in g['docs']}
    cards = {}
    for d in t['docs']:
        if d['id'] in grouped or d['id'] in t['removed']:
            continue
        r = kit.check(ac_match_rules, t, [d['id']], [], cards=True)
        if r is not True:
            cards[d['id']] = r
    return dict(ac_match=cards, ac_complete=kit.check(ac_complete_rules, t))
