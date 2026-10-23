"""🛃 Hải quan cửa khẩu Bến Mây (owner spec 14/10, I. Bổ sung cập nhật nghề Hải quan). Rules: the game's own
(game/careers/customs_content.py); every place and person is invented.

The player is a public servant of the Chi cục Hải quan cửa khẩu Bến Mây (employment: the entry exam of 8 questions
— the owner's, verbatim — then CV and interview; who may apply: game/gov_rules.py entry_rows). The ladder is the org
'hq' (game/org_content.py): Người tập sự → Kiểm tra viên → Kiểm tra viên chính → Đội trưởng → Chi cục trưởng → Cục
trưởng Cục Hải quan Thành phố → Tổng cục trưởng, with seats for the top posts.

Four kinds of work (spec 1.1.2), each task a list of steps with evidence (`needs.steps`, answers in `_key`):
* 'lane'    kiểm tra, giám sát: the lane the system gave (🟢 / 🟡 / 🔴) → the documents → the goods → the decision;
* 'smuggle' chống buôn lậu: the scan → what it is → the decision (hold, hand over, release);
* 'tax'     thuế xuất nhập khẩu: the rate (C/O) → import duty → VAT (numbers) → collect / exempt / refund;
* 'control' đấu tranh phòng chống tội phạm: the risk profile → a lawful method → the decision.
Evidence steps are answered until right (each first slip a mistake; doing less than the lane asks is a ⚠️ hq_skip).
The decision is final: letting fraud or contraband through is a ⚠️ hq_release; too harsh is a mistake and a real
complaint. Some tasks bring a temptation before the decision (spec 2., 'offer' step): refusing is right (an envelope
refused and reported: Liêm chính +1); going along ends the task at once the way the other side wanted, and the thanh
tra may find it (gov_rules.hq_found, rolled now, applied at the close: kỷ luật or khai trừ).
After the shift (on_close) people may write about it (game/npc_complaints.py): real complaints from the day's slips,
and unreasonable ones (đòi hỏi ngoài dịch vụ, bóc phốt đòi bắt đền, không liên quan) to dismiss or send to CATP.
"""
from __future__ import annotations

from copy import deepcopy
import json

from . import kit
from . import customs_content as CC
from .. import consequences as cq
from .. import npc_complaints as NC

ID = 'customs'
GEN = 1
PEOPLE = CC.PEOPLE
FIXED = ('gen', 'needs', '_key')
PHYSICAL = ('hq_step',)
FREE = ('hq_intro', 'hq_cmp')
NO_TICK = FREE
KINDS = ('lane', 'smuggle', 'tax', 'control')
BONUS = dict(lane=6, smuggle=8, tax=7, control=9)
TEMPT_FROM = 2          # temptations from this career day
TEMPT_P = 0.45
AUDIT_MAX = 12
SLIPS_MAX = 12
LINES_MAX = 24


# ------------------------------------------------------------------------------------- tasks
def _step(sid: str, kind: str, title: str, evidence: str, options=None, final: bool = False) -> dict:
    row = dict(id=sid, kind=kind, title=title, evidence=evidence, final=final)
    if options is not None:
        row['options'] = [dict(id=k, label=v) for k, v in options]
    return row


def _pool(rows, day):
    return [r for r in rows if r[1] <= day]


def _pick(rows, day, slot, salt):
    pool = _pool(rows, day)
    return pool[(day * 7 + slot * 3 + salt) % len(pool)]


def _kind(day: int, slot: int) -> str:
    order = ('lane', 'tax', 'smuggle', 'lane', 'control', 'tax', 'smuggle', 'lane')
    k = order[(slot + day) % len(order)]
    if k == 'control' and day < 2:
        return 'smuggle'
    return k


def _tempt(r, kind_tempt, day):
    """The temptation of this task (or None), rolled from the task's own generator."""
    if not kind_tempt or day < TEMPT_FROM or r.random() >= TEMPT_P:
        return None
    t = CC.TEMPT[kind_tempt]
    lo, hi = t['amount']
    amount = (lo + r.randrange(0, hi - lo + 1) // 50 * 50) if hi else 0
    return dict(kind=kind_tempt, code=t['code'], amount=amount, title=t['title'], text=t['text'].format(amount=f'{amount:,}'.replace(',', '.')),
                npc=t['who'])


def _offer_step(tp: dict) -> dict:
    return _step('offer', 'offer', tp['title'], tp['text'], CC.TEMPT[tp['kind']]['options'], final=True)


def _lane(day, slot, r):
    cid, _, lane, title, opening, declared, docs, goods, decision, lines, tk = _pick(CC.LANE_CASES, day, slot, 1)
    em, lname = CC.LANES[lane]
    pax = cid == 'cash_pax'
    steps, key = [], {}
    head = (f'Hành khách tự chọn cửa. {lines[0]}' if pax else f'Tờ khai: {declared}. Hệ thống phân: {em} {lname}.')
    opts = [('green', 'Cửa miễn khai báo (luồng xanh)'), ('red', 'Cửa báo Hải quan (luồng đỏ)'), ('skip', 'Cho đi thẳng ra ngoài')] if pax else list(CC.ROUTE_OPTS)
    r.shuffle(opts)
    steps.append(_step('route', 'route', 'Làm đúng theo luồng', head, opts)); key['route'] = lane
    if docs is not None:
        o = list(CC.DOC_OPTS); r.shuffle(o)
        steps.append(_step('docs', 'docs', 'Kiểm tra chi tiết hồ sơ giấy', ' '.join(x for x in lines if not x.startswith('Đếm thực tế')), o)); key['docs'] = docs
    if goods is not None:
        o = list(CC.GOODS_OPTS); r.shuffle(o)
        ev = ' '.join(x for x in lines if x.startswith(('Đếm thực tế', 'Thực tế', 'Máy soi', 'Ông Kha')))
        if pax:
            ev += f' Định mức không phải khai: {CC.CASH_FREE:,} xu quy đổi.'.replace(',', '.')
        steps.append(_step('goods', 'goods', 'Kiểm tra thực tế', ev or 'Đối chiếu thực tế với tờ khai.', o)); key['goods'] = goods
    tp = _tempt(r, tk, day) if decision != 'clear' or tk == 'collude' else None
    if tp:
        steps.append(_offer_step(tp)); key['offer'] = 'refuse'
    o = list(CC.DECIDE_OPTS)
    steps.append(_step('decide', 'decide', 'Quyết định', 'Căn cứ kết quả kiểm tra ở trên.', o, final=True)); key['decide'] = decision
    return cid, title, opening, dict(variant=cid, lane=lane, declared=declared, pax=pax, steps=steps, tempt=tp), key


def _smuggle(day, slot, r):
    cid, _, title, opening, shadows, sus, ident, ans, decision, tk = _pick(CC.SMUGGLE_CASES, day, slot, 2)
    steps, key = [], {}
    o = [(str(i), f'Khối {i + 1}: {sh}') for i, sh in enumerate(shadows)] + [('none', 'Không có khối nào đáng ngờ')]
    steps.append(_step('scan', 'scan', 'Đọc ảnh soi chiếu', 'Ảnh soi chiếu có ba khối. Khối nào cần mở kiểm tra?', o)); key['scan'] = str(sus) if sus >= 0 else 'none'
    o = list(ident); r.shuffle(o)
    steps.append(_step('identify', 'identify', 'Xác định hàng hóa', 'Mở kiểm tra có biên bản, có người chứng kiến. Đây là gì?', o)); key['identify'] = ans
    tp = _tempt(r, tk, day)
    if tp:
        steps.append(_offer_step(tp)); key['offer'] = 'refuse'
    steps.append(_step('decide', 'decide', 'Quyết định', 'Căn cứ hàng hóa đã xác định.', list(CC.SMUGGLE_DECIDE), final=True)); key['decide'] = decision
    return cid, title, opening, dict(variant=cid, steps=steps, tempt=tp), key


def _tax(day, slot, r):
    cid, _, title, opening, item, value, normal, pref, co, policy, paid, tk = _pick(CC.TAX_CASES, day, slot, 3)
    steps, key = [], {}
    rate = pref if co == 'ok' else normal
    co_line = {'ok': 'C/O ưu đãi: đúng mẫu, còn hạn, đúng lô.', 'bad': 'C/O ưu đãi: hết hạn.', None: 'Không có C/O.'}[co]
    o = sorted({(str(normal), f'Thuế suất thông thường {normal}%'), (str(pref), f'Thuế suất ưu đãi {pref}%'), ('0', 'Thuế suất 0%')})
    head = f'{item}: trị giá tính thuế {value:,} xu. {co_line}'.replace(',', '.')
    steps.append(_step('rate', 'rate', 'Chọn thuế suất nhập khẩu', head, o)); key['rate'] = str(rate)
    if policy == 'refund':
        steps.append(_step('duty', 'duty', 'Số thuế nhập khẩu được hoàn', f'Lô đã nộp thuế nhập khẩu {paid:,} xu khi nhập; nay tái xuất trả người bán.'.replace(',', '.')))
        key['duty'] = paid
    else:
        duty = 0 if policy == 'exempt' else value * rate // 100
        note = f' Quà biếu không quá {CC.GIFT_FREE:,} xu được miễn.'.replace(',', '.') if policy == 'exempt' else ''
        steps.append(_step('duty', 'duty', 'Thuế nhập khẩu phải nộp', f'{head}{note} Ghi số xu phải nộp.'))
        key['duty'] = duty
        vat = 0 if policy == 'exempt' else (value + duty) * CC.VAT // 100
        steps.append(_step('vat', 'vat', 'Thuế GTGT phải nộp', f'(Trị giá + thuế nhập khẩu) × {CC.VAT}%, làm tròn xuống. Ghi số xu phải nộp.'))
        key['vat'] = vat
    tp = _tempt(r, tk, day)
    if tp:
        steps.append(_offer_step(tp)); key['offer'] = 'refuse'
    steps.append(_step('policy', 'policy', 'Quyết định về thuế', 'Thu, miễn hay hoàn đúng diện.', list(CC.POLICY_OPTS), final=True)); key['policy'] = policy
    due = 0 if policy != 'collect' else key['duty'] + key.get('vat', 0)
    return cid, title, opening, dict(variant=cid, item=item, value=value, due=due, steps=steps, tempt=tp), key


def _control(day, slot, r):
    cid, _, title, opening, prof, pans, found, decision, tk = _pick(CC.CONTROL_CASES, day, slot, 4)
    steps, key = [], {}
    o = list(prof); r.shuffle(o)
    steps.append(_step('profile', 'profile', 'Đánh giá dấu hiệu rủi ro', opening, o)); key['profile'] = pans
    o = list(CC.METHOD_OPTS); r.shuffle(o)
    steps.append(_step('method', 'method', 'Biện pháp kiểm soát', 'Chọn biện pháp đúng thẩm quyền.', o)); key['method'] = 'lawful'
    tp = _tempt(r, tk, day)
    if tp:
        steps.append(_offer_step(tp)); key['offer'] = 'refuse'
    steps.append(_step('decide', 'decide', 'Quyết định', found, list(CC.CONTROL_DECIDE), final=True)); key['decide'] = decision
    return cid, title, opening, dict(variant=cid, steps=steps, tempt=tp), key


def make_task(day: int, slot: int, serial: int) -> dict:
    r = kit.rng(ID, day, slot)
    kind = _kind(day, slot)
    cid, title, opening, needs, key = dict(lane=_lane, smuggle=_smuggle, tax=_tax, control=_control)[kind](day, slot, r)
    needs['bonus'] = BONUS[kind]
    npc = {'lane': 1 if not needs.get('pax') else 3, 'smuggle': 3, 'tax': 2, 'control': 4}[kind]
    npc = (npc + (day + slot) % 2 * (kind == 'smuggle')) % len(PEOPLE)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, gen=GEN, kind=kind, needs=needs, _key=key,
                         at=0, work={}, errors=[], lines=[], stage='work', cut=None, outcome='')


# ------------------------------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, clean=0, duty=0, seized=0, bonus=0, counted=0)


def initial() -> dict:
    return dict(v=1, intro=False, today=_today(0), stats=dict(jobs=0, clean=0, duty=0, seized=0, bonus=0, active_days=0),
                last_active_day=0, audit=[], slips=[], cmp=[], cmp_seq=0)


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
        d['slips'] = []
    return d


def _line(t: dict, text: str) -> None:
    t['lines'] = (t['lines'] + [text[:300]])[-LINES_MAX:]


def _pm():
    from .. import promotion
    return promotion


def _grace(c: dict) -> bool:
    return bool((c.get('job') or {}).get('probation'))


def _warn(s, c, t, code: str) -> str:
    return _pm().violation(s, c, ID, code, f'{t["id"]}:{code}', grace=_grace(c))


# ------------------------------------------------------------------------------------- actions
def handle(s, c, name, p):
    kit.need(name in ('hq_intro', 'hq_step', 'hq_cmp'), 'Thao tác hải quan không hợp lệ.')
    if name == 'hq_intro':
        kit.data(c)['intro'] = True
        return dict(message='Chị Lam Thục đưa sổ tay nghiệp vụ: “Đúng luồng, đủ giấy, không nhận gì của ai.”')
    if name == 'hq_cmp':
        return _complaint(s, c, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc hồ sơ trước khi thao tác.')
    steps = t['needs']['steps']
    kit.need(t['at'] < len(steps), 'Hồ sơ này đã khép.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên hồ sơ nhé.')
    value = p.get('value')
    if 'options' in st:
        kit.one_of(value, [o['id'] for o in st['options']])
    else:
        kit.need(type(value) is int, 'Nhập một số nguyên.')
        kit.integer(value, 0, 10**7)
    kit.start_work(t)
    d = _data(c)
    right = t['_key'][st['id']]
    if st['kind'] == 'offer':
        return _offer(s, c, d, t, st, value)
    if not st['final'] and value != right:
        out = dict(correct=False)
        if st['id'] not in t['errors']:
            t['errors'].append(st['id']); t['mistakes'] += 1
            cq.slip(t, st['id'], 1, CC.REAL_LINES.get(st['kind'], 'Hồ sơ phải làm lại.'))
            d['slips'] = (d['slips'] + [dict(npc=_npc_index(t), k=st['kind'])])[-SLIPS_MAX:]
            if st['id'] == 'route' and _less(t, value):
                w = _warn(s, c, t, 'hq_skip')
                if w:
                    out['rank'] = w
        msg = f'Chưa đúng. {st["evidence"]} Xem lại sổ tay nghiệp vụ rồi thử lại.'
        if out.get('rank'):
            msg += ' ' + out['rank']
        _line(t, msg)
        out['message'] = msg
        return out
    t['work'][st['id']] = value
    t['at'] += 1
    extra = ''
    if st['final'] and value != right:
        extra = _wrong_final(s, c, d, t, st, value, right)
    _line(t, (f'✓ {st["title"]}.' if value == right else f'✗ {st["title"]}.') + (f' {extra}' if extra else ''))
    if t['at'] < len(steps):
        return dict(message='Đã ghi. ' + steps[t['at']]['title'] + (f' {extra}' if extra else ''), correct=True)
    return _finish(s, c, d, t, extra)


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _less(t: dict, value) -> bool:
    """A route that inspects less than the lane asks (or lets everything go)."""
    rank = dict(skip=0, green=1, yellow=2, red=3)
    return rank.get(value, 0) < rank.get(t['_key']['route'], 0)


def _wrong_final(s, c, d, t, st, value, right) -> str:
    """A final decision other than the right one: mistakes, a real complaint, a ⚠️ when fraud or contraband went through."""
    t['errors'].append(st['id']); t['mistakes'] += 2
    cq.slip(t, st['id'], 2, CC.REAL_LINES.get(st['kind'], 'Quyết định sai.'))
    d['slips'] = (d['slips'] + [dict(npc=_npc_index(t), k=st['kind'])])[-SLIPS_MAX:]
    strict = ('hold', 'handover')
    if st['kind'] == 'decide' and right in strict and value not in strict:
        return _warn(s, c, t, 'hq_release') or 'Để lọt hàng vi phạm.'
    if st['kind'] == 'decide' and right == 'handover' and value == 'hold':
        return 'Vụ có dấu hiệu tội phạm phải bàn giao cơ quan điều tra.'
    return 'Quyết định chưa đúng: người dân sẽ phản ánh.'


def _offer(s, c, d, t, st, value) -> dict:
    """The temptation: refuse (right; an envelope reported: Liêm chính +1) or go along (the task ends their way, and
    the thanh tra may find it: rolled now, applied at the close)."""
    tp = t['needs']['tempt']
    t['work']['offer'] = value
    if value == 'refuse':
        t['at'] += 1
        rank = _pm().report_bribe(s, c, ID) if tp['kind'] in ('bribe', 'keep') else ''
        msg = 'Đã từ chối và ghi vào biên bản.' + (f' {rank}' if rank else '')
        _line(t, '✓ ' + msg)
        return dict(message=msg + ' ' + t['needs']['steps'][t['at']]['title'], correct=True)
    from .. import gov_rules as gr
    key = f'{c["day"]}:{t["id"]}'
    found = gr.hq_found(tp['code'], key)
    if tp['amount']:
        from .. import journey as jr
        jr._wallet(s['journey'], tp['amount'], 'life', '💵 Khoản ngoài sổ ở cửa khẩu')
    d['audit'] = (d['audit'] + [dict(code=tp['code'], key=key, found=bool(found), amount=int(tp['amount']), d=c['day'])])[-AUDIT_MAX:]
    t['cut'] = t['at']
    t['at'] = len(t['needs']['steps'])
    t['outcome'] = 'tempt'
    _line(t, 'Đã làm theo lời đề nghị.')
    return _finish(s, c, d, t, '')


def _finish(s, c, d, t, extra: str) -> dict:
    clean = t['mistakes'] == 0 and t['cut'] is None
    bonus = max(3, t['needs']['bonus'] - t['mistakes'])
    duty = t['needs'].get('due', 0) if t['kind'] == 'tax' and t['cut'] is None and t['work'].get('policy') == 'collect' else 0
    seized = int(t['kind'] in ('smuggle', 'control', 'lane') and t['cut'] is None and t['work'].get('decide') in ('hold', 'handover')
                 and t['_key'].get('decide') == t['work'].get('decide'))
    for b in (d['today'], d['stats']):
        b['jobs'] += 1; b['clean'] += int(clean); b['duty'] = min(10**9, b['duty'] + duty); b['seized'] += seized
        b['bonus'] += bonus
    t['stage'] = 'done'
    if not t['outcome']:
        t['outcome'] = 'clean' if clean else 'slip'
    kit.complete(s, c, t, bonus, 'Hồ sơ khép đúng quy trình, có biên bản và chứng từ.' if clean else 'Hồ sơ đã khép.')
    head = 'Đã khép hồ sơ.' if t['cut'] is None else 'Lô hàng đi theo ý người đề nghị.'
    msg = f'{head} Thưởng hiệu suất {bonus} xu.' + (f' Thu ngân sách {duty:,} xu.'.replace(',', '.') if duty else '') + (f' {extra}' if extra else '')
    return dict(message=msg, correct=clean)


# ------------------------------------------------------------------------------------- 📮 complaints
def _complaint(s, c, p) -> dict:
    d = kit.data(c)
    op = p.get('op')
    kit.need(op in NC.OPS, 'Chọn cách xử lý phản ánh.')
    rid = p.get('id')
    row = next((r for r in d['cmp'] if r['id'] == rid and type(rid) is int), None)
    kit.need(row is not None, 'Không tìm thấy phản ánh này.')
    kit.need(row['st'] == 'open', 'Phản ánh này đã xử lý rồi.')
    out = NC.decide(row, op)
    bits = [out['line']]
    if out['viol']:
        w = _pm().violation(s, c, ID, out['viol'], f'cmp-{row["id"]}', grace=_grace(c))
        if w:
            bits.append(w)
    if out['adj']:
        rec, x = _pm().org_live(s, c, ID, True)
        if x:
            x['adj'] = max(-50, min(10, x['adj'] + out['adj']))
            bits.append('+0,1★ ngày công tác.' if out['adj'] > 0 else '−0,1★ ngày công tác.')
    return dict(message=' '.join(bits), correct=out['ok'])


# ------------------------------------------------------------------------------------- the day
def on_start(s, c):
    _data(c)


def on_close(s, c):
    d = _data(c)
    today = d['today']
    lines = [f'🛃 Hải quan: {today["jobs"]} hồ sơ, {today["clean"]} hồ sơ không sai sót, {today["seized"]} vụ tạm giữ đúng.']
    if today['duty']:
        lines.append(f'Thu ngân sách: {today["duty"]:,} xu'.replace(',', '.') + ' (của Nhà nước, không phải của bạn).')
    if today['clean'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1; today['counted'] = 1; d['last_active_day'] = c['day']
    # 🔎 Thanh tra sau thông quan: the acts rolled as found this shift take effect now.
    from .. import gov_rules as gr
    keep = []
    for a in d['audit']:
        if not a['found']:
            keep.append(a)
            continue
        line = gr.hq_apply(s, c, a['code'], a['key'])
        if a['amount']:
            from .. import journey as jr
            j = s['journey']
            back = max(0, min(int(a['amount']), int(j['wallet'])))
            if back:
                jr._wallet(j, -back, 'life', '🔎 Tịch thu khoản nhận sai ở cửa khẩu')
        if line:
            lines.append(line)
    d['audit'] = keep[-AUDIT_MAX:]
    # 📮 What people write about the day (game/npc_complaints.py).
    seen, real = set(), []
    for sl in d['slips']:
        if (sl['npc'], sl['k']) not in seen:
            seen.add((sl['npc'], sl['k']))
            real.append((sl['npc'], CC.REAL_LINES.get(sl['k'], 'Hồ sơ của tôi bị xử lý chưa đúng.')))
    before = NC.open_rows(d['cmp'])
    seed = int((s.get('journey') or {}).get('seed') or 0)
    d['cmp_seq'] = NC.roll(kit.rng(ID, 'cmp', seed, c['day']), d['cmp'], d['cmp_seq'], c['day'], real, CC.FAKE_LINES, len(PEOPLE))
    d['slips'] = []
    new = NC.open_rows(d['cmp']) - before
    if new > 0:
        lines.append(f'📮 {new} phản ánh mới của người dân: xem ở bàn làm việc.')
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Khoản thu cho Nhà nước nộp thẳng ngân sách, không vào quỹ của bạn.')


# ------------------------------------------------------------------------------------- entry (game/employment.py)
def entry_rows(s) -> list[dict]:
    from .. import gov_rules as gr
    return gr.entry_rows(s)


def entry_block(s) -> str | None:
    from .. import gov_rules as gr
    return gr.entry_block(s)


# ------------------------------------------------------------------------------------- views
def known_request(c, t):
    return t['opening'] + ' Đọc hồ sơ → làm từng bước theo sổ tay nghiệp vụ → quyết định có căn cứ.'


def hint(c, t):
    if not t.get('known'):
        return 'Đọc hồ sơ để biết tờ khai, luồng và chứng từ.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Hồ sơ đã khép; nhận hồ sơ tiếp theo.'


def feedback(c, t):
    groups = [('check', 'Kiểm tra đúng luồng, đủ bước', {'route', 'docs', 'goods', 'scan', 'profile', 'method'}),
              ('facts', 'Xác định đúng hàng, đúng số', {'identify', 'rate', 'duty', 'vat'}),
              ('decide', 'Quyết định có căn cứ', {'decide', 'policy'})]
    rows = []
    for k, label, ids in groups:
        n = sum(1 for e in t['errors'] if e in ids)
        rows.append(dict(key=k, label=label, score=max(1, 5 - 2 * n), note='Theo sổ tay nghiệp vụ của Chi cục.'))
    return dict(criteria=rows)


def public_task(t):
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
        return v
    v['needs'].pop('due', None)
    return v


def public_data(c):
    d = kit.data(c)
    st = d['stats']
    ms = [dict(m, achieved=st['clean'] >= m['jobs'] and st['active_days'] >= m['days']) for m in CC.MILESTONES]
    return dict(intro=d['intro'], today={k: v for k, v in d['today'].items() if k != 'counted'}, stats=dict(st),
                progress=dict(milestones=ms, earned=[m['id'] for m in ms if m['achieved']]),
                cmp=NC.public(d['cmp'], PEOPLE), cmp_open=NC.open_rows(d['cmp']), audit=len(d['audit']))


def content():
    from .. import gov_rules as gr
    return dict(notebook=list(CC.NOTEBOOK), lanes={k: dict(emoji=e, name=n) for k, (e, n) in CC.LANES.items()}, vat=CC.VAT,
                rules=gr.content()['customs'], kinds={k: v for k, v in NC.KINDS.items()}, ops=dict(NC.OPS),
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE],
                intro=dict(title='Một ngày ở cửa khẩu Bến Mây', lead=('Mỗi tờ khai là một lô hàng thật của người dân và doanh nghiệp. Đúng luồng, '
                                                                     'đủ giấy, đúng thuế; hàng cấm thì giữ lại. Lương theo hợp đồng, thưởng nhỏ theo chất lượng.'),
                           work=[['🚦', 'Phân luồng, kiểm hồ sơ, kiểm thực tế'], ['🔎', 'Soi chiếu, chống buôn lậu'], ['🧮', 'Tính thuế, miễn, hoàn'],
                                 ['🐕', 'Kiểm soát, phòng chống tội phạm']],
                           meet=[['👩‍✈️', 'Chị Lam Thục, Đội trưởng Đội Thủ tục'], ['🐕', 'Chó nghiệp vụ Mực']],
                           stars=[['✓', 'Đọc kỹ chứng từ, đếm đúng thực tế'], ['✓', 'Không nhận gì của ai']]))


# ------------------------------------------------------------------------------------- validation
def validate_task(t, original):
    for k in FIXED:
        kit.need(json.dumps(t.get(k), sort_keys=True) == json.dumps(original.get(k), sort_keys=True), 'Dữ kiện hồ sơ hải quan bị thay đổi: ' + k)
    steps = t['needs']['steps']
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    cut = t.get('cut')
    kit.need(cut is None or (type(cut) is int and 0 <= cut < len(steps) and steps[cut]['kind'] == 'offer' and at == len(steps)), 'Tiến trình hồ sơ sai.')
    done = ids[:cut + 1] if cut is not None else ids[:at]
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình hồ sơ sai.')
    w = t.get('work')
    kit.need(isinstance(w, dict) and set(w) == set(done), 'Các bước đã ghi không liên tục.')
    for st in steps:
        if st['id'] not in w:
            continue
        v = w[st['id']]
        if st['final']:
            kit.need(v in [o['id'] for o in st['options']], 'Quyết định không hợp lệ.')
        else:
            kit.need(v == t['_key'][st['id']] and type(v) is type(t['_key'][st['id']]), 'Kết quả hồ sơ sai.')
    if cut is not None:
        kit.need(w.get('offer') == 'take', 'Lựa chọn sai.')
    elif 'offer' in w:
        kit.need(w['offer'] == 'refuse', 'Lựa chọn sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) and e in ids for e in errors) and len(errors) == len(set(errors)), 'Nhật ký lỗi sai.')
    kit.need(type(t.get('mistakes')) is int and t['mistakes'] >= len(errors), 'Số lỗi sai.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES_MAX and all(isinstance(x, str) and len(x) <= 300 for x in t['lines']), 'Nhật ký hồ sơ sai.')
    kit.need(t.get('outcome') in ('', 'clean', 'slip', 'tempt') and (t['outcome'] == 'tempt') == (cut is not None), 'Kết quả hồ sơ sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Chưa khép đủ hồ sơ.')


def validate_data(c):
    d = kit.data(c)
    base = initial()
    bad = 'Sổ hải quan sai.'
    kit.need(isinstance(d, dict) and set(d) == set(base) and d['v'] == 1 and type(d['intro']) is bool, bad)
    kit.integer(d['last_active_day'], 0, 10**7)
    for name in ('today', 'stats'):
        kit.need(isinstance(d[name], dict) and set(d[name]) == set(base[name]), bad)
        for v in d[name].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[name]['clean'] <= d[name]['jobs'] and d[name]['seized'] <= d[name]['jobs'], bad)
    kit.integer(d['today']['counted'], 0, 1)
    kit.need(d['stats']['active_days'] <= d['stats']['clean'], bad)
    kit.need(isinstance(d['audit'], list) and len(d['audit']) <= AUDIT_MAX, bad)
    from .. import gov_rules as gr
    for a in d['audit']:
        kit.need(isinstance(a, dict) and set(a) == {'code', 'key', 'found', 'amount', 'd'} and a['code'] in gr.HQ and type(a['found']) is bool, bad)
        kit.need(isinstance(a['key'], str) and 0 < len(a['key']) <= 80, bad)
        kit.integer(a['amount'], 0, 10**6)
        kit.integer(a['d'], 0, 10**9)
    kit.need(isinstance(d['slips'], list) and len(d['slips']) <= SLIPS_MAX, bad)
    for sl in d['slips']:
        kit.need(isinstance(sl, dict) and set(sl) == {'npc', 'k'} and sl['k'] in CC.REAL_LINES, bad)
        kit.integer(sl['npc'], 0, len(PEOPLE) - 1)
    NC.validate(d['cmp'], d['cmp_seq'], len(PEOPLE), kit.need, kit.integer, bad)


SPEC = dict(
    id=ID, prefix='hq_', category='service', people=PEOPLE,
    meta=dict(short='Hải quan', place='Chi cục Hải quan cửa khẩu Bến Mây', tagline='Đúng luồng, đủ giấy, không nhận gì của ai.', icon='shield',
              color='#2f6b4f', light='#e3f1e8', weather='Gió biển thổi qua bãi container', work='Hồ sơ hải quan', station='Quầy thủ tục & bãi kiểm hóa',
              greeting='Tờ khai điện tử lên hệ thống trước, hàng đến sau. Đọc luồng, kiểm đủ bước, quyết định có căn cứ.',
              caption='Giữ cửa khẩu cho hàng ngay, chặn hàng gian', map_label='HẢI QUAN BẾN MÂY'),
    staff=[('Anh Lục Kiên', 'inspect', 'Kiểm hóa mười năm, đếm thùng bằng mắt cũng đúng.', 80, 92),
           ('Chị Đàm Quế', 'desk', 'Đọc tờ khai nhanh, không sót một mã hàng.', 84, 90),
           ('Anh Hà Phong', 'scan', 'Đọc ảnh máy soi container, đánh dấu chỗ cần mở.', 82, 90),
           ('Chị Mạc Lan', 'desk', 'Tra mã hàng nhanh, ghi chú từng dòng tờ khai.', 80, 93)],
    roles={'inspect': 'Kiểm hóa', 'desk': 'Thủ tục', 'scan': 'Soi chiếu'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🛃', 'Một ca ở cửa khẩu', [('Luồng xanh', 'Miễn kiểm, thông quan'), ('Luồng vàng', 'Kiểm hồ sơ giấy'), ('Luồng đỏ', 'Kiểm cả thực tế'),
                                         ('Phong bì', 'Từ chối, lập biên bản')],
              ['Đọc tờ khai, luồng', 'Kiểm hồ sơ, thực tế', 'Tính thuế', 'Quyết định có căn cứ']),
    stories=[('Thùng hàng thừa', ('Container quạt điện có 120 thùng, tờ khai ghi 100.', 'Bạn lập biên bản, chủ hàng phải giải trình.',
                                  'Chị Lam Thục gật đầu: “Đếm đúng là việc nhỏ mà giữ được cả cửa khẩu.”'))],
    review_asides=['Thủ tục rõ ràng, đúng luồng.', 'Tính thuế minh bạch, có giải thích.', 'Không gợi ý gì, rất đàng hoàng.'], situations=[],
    more_line='Hệ thống vừa đẩy thêm một tờ khai.', open_line='Chị Lam Thục đã mở quầy; sổ tay nghiệp vụ đặt cạnh máy soi.',
    guide=('Đọc tờ khai và luồng → luồng xanh miễn kiểm, luồng vàng kiểm hồ sơ giấy, luồng đỏ kiểm cả thực tế → tính thuế: trị giá × thuế suất, '
           'GTGT 10% → hàng cấm, động vật hoang dã: tạm giữ, bàn giao → không nhận gì của ai. Thuế suất, định mức theo sổ tay nghiệp vụ của Chi cục.'),
    employment=dict(postings=[dict(id='hq-ktv', org='Chi cục Hải quan cửa khẩu Bến Mây', kind='public', title='Công chức Hải quan (tập sự)',
                                  salary=(60, 78), probation_days=3, wants=['careful', 'numbers', 'calm'],
                                  perks=['Chị Lam Thục kèm những hồ sơ đầu', 'Ca ngày tại quầy thủ tục và bãi kiểm hóa', 'Lương theo ngạch, bậc'],
                                  culture='Đúng luồng, đủ giấy, ai cũng như ai. Không nhận bất kỳ thứ gì của doanh nghiệp, hành khách.',
                                  questions=['hq_q_envelope', 'hq_q_friend', 'mistake'], reference=True,
                                  stages=['exam', 'cv', 'interview'], boss='chi cục trưởng')],
                    questions={
                        'hq_q_envelope': dict(text='Chủ hàng kẹp phong bì trong bộ hồ sơ “cho nhanh”. Bạn làm gì?', options=[
                            dict(id='decline', label='Trả lại, lập biên bản, hồ sơ xử lý như mọi hồ sơ', score=3, note='Đúng nếp của ngành.'),
                            dict(id='fund', label='Nhận rồi nộp quỹ chung', score=0, note='Quỹ chung hay riêng thì vẫn là nhận.'),
                            dict(id='later', label='Hẹn xong việc rồi tính', score=0, note='Hẹn lại cũng là nhận.')]),
                        'hq_q_friend': dict(text='Bạn thân nhờ “cho lô hàng qua luồng xanh”. Bạn trả lời sao?', options=[
                            dict(id='system', label='Luồng do hệ thống phân, mình kiểm đúng theo luồng', score=3, note='Không ai được chọn luồng.'),
                            dict(id='try', label='Để mình xem có cách không', score=0, note='Một lời hứa là một lần bao che.'),
                            dict(id='skip', label='Cho qua lần này thôi', score=0, note='Bao che là vi phạm.')]),
                    }),
)
