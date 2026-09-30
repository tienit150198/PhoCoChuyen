"""Paperwork desks for the pharmacy counter, the bookkeeping desk and the
support station (Papers, Please-style cases).

The facts of a case come from `desk_content` and are a pure function of
(career, day, slot): documents, checks and stamps are stored on the task so
the client can draw them, while the secret part (which rows break which rule,
which stamp is right, what each stamp leads to) is rebuilt on the server
whenever it is needed and never sent before the stamp is down.

The task only records what the player did: rows flagged, checks run, the first
reply, the till count and the final stamp. Grades, pay, citations and story
flags are all derived from that record, so a save can be re-validated.
"""
from __future__ import annotations

import copy

from . import consequences as cq
from . import desk_content as dc
from . import archive as ar
from . import patience as pt

CAREERS = dc.CAREERS
ACTIONS = ('desk_flag', 'desk_check', 'desk_count', 'desk_reply', 'desk_decide')
BASE_PAY = {'pharmacy': 40, 'accounting': 60, 'customer_care': 55}
SHARE = {'perfect': 100, 'good': 60, 'wrong': 0}
MISTAKES = {'perfect': 0, 'good': 1, 'wrong': 3}
GRADES = tuple(SHARE)
GRADE_LABEL = {'perfect': 'Chuẩn', 'good': 'Đạt', 'wrong': 'Chưa đúng'}
REFERRED = {'refer', 'escalate', 'report'}
DONE = ('completed', 'referred', 'cancelled')
REPLY_PATIENCE = {'best': 10, 'ok': 0, 'bad': -15}
FALSE_FLAG_PATIENCE = 5
BREACH_PATIENCE = 20
MAX_MARKS = 30
STATIC = ('variant', 'desk', 'tier', 'request', 'docs', 'checks', 'verdicts', 'chapter', 'mood', 'replies', 'sla', 'due_turn', 'drawer')
FLAG_IDS = ('nam_label', 'nam_safe', 'nam_risk', 'hoa_honest', 'hoa_hid', 'phuc_calm', 'phuc_fair', 'phuc_favor')
# Story chapters remember the stamp you chose; later chapters read it back.
STORY_FLAGS = {
    ('pharmacy', 1): {'give': 'nam_label', 'refer': 'nam_label'},
    ('pharmacy', 2): {'refer': 'nam_safe', 'refuse': 'nam_safe', 'give': 'nam_risk', 'fix': 'nam_risk'},
    ('pharmacy', 3): {'refer': 'nam_safe', 'refuse': 'nam_safe', 'give': 'nam_risk'},
    ('accounting', 2): {'record': 'hoa_honest', 'report': 'hoa_honest', 'comply': 'hoa_hid'},
    ('customer_care', 1): {'exchange': 'phuc_calm', 'refund': 'phuc_calm'},
    ('customer_care', 3): {'explain': 'phuc_fair', 'deny': 'phuc_fair', 'favor': 'phuc_favor'},
}
CHECK_METRIC = {'pharmacy': 'inspections', 'accounting': 'source_reads', 'customer_care': 'identity_checked'}


def _core():
    from . import engine
    return engine


# ------------------------------------------------------------------ building
def initial(career: str) -> dict:
    return {'desk': fresh()} if career in CAREERS else {}


def fresh() -> dict:
    return dict(v=1, bulletin_day=0, risk=0, viral=0, flags=[], citations=[], inspections=[], history=[], warned=[],
                stats=dict(perfect=0, good=0, wrong=0), today=dict(day=0, citations=0, fines=0))


def data(c: dict) -> dict:
    return c['ext']['data'].setdefault('desk', fresh())


def plan(career: str, day: int, slot: int) -> str | None:
    return dc.plan(career, day, slot) if career in CAREERS else None


def secrets(t: dict) -> dict:
    """The hidden half of a case, rebuilt from its coordinates."""
    slot = int(t['id'].rsplit('-', 1)[1])
    case, _, _ = dc.build(t['career'], t['variant'], t['day'], slot)
    return case


def make_task(career: str, day: int, slot: int, serial: int, base: dict) -> dict | None:
    variant = plan(career, day, slot)
    if not variant:
        return None
    case, _, tier = dc.build(career, variant, day, slot)
    t = dict(base)
    t.update(npc=f'{career}_npc_{case["npc"]:02d}', title=case['title'], opening=case['opening'], variant=variant, desk=True, tier=tier,
             request=case['request'], docs=case['docs'], checks=case.get('checks', []), verdicts=case['verdicts'], chapter=case.get('chapter'))
    if career == 'customer_care':
        order = sorted(range(3), key=lambda i: dc.rng(career, day, slot, 'reply', i).random())
        rows = dc.REPLIES[case['mood']]
        t.update(mood=case['mood'], replies=[dict(id=f'r{k}', text=rows[i][1]) for k, i in enumerate(order)], sla=case['sla'],
                 due_turn=serial + pt.longer(max(5, dc.SLA[case['sla']] - (tier - 1))) if day > 2 else None)  # first two days: learn first, no timer
    if 'notes' in case:
        t['drawer'] = case['notes']
    t.update(found=[], partial=[], marks=[], false_flags=0, verified=[], pending={}, reply=None, thread=[], count=None, miscounts=0,
             verdict=None, grade=None, breached=False, result=None)
    return t


def reply_grades(t: dict) -> dict:
    slot = int(t['id'].rsplit('-', 1)[1])
    order = sorted(range(3), key=lambda i: dc.rng(t['career'], t['day'], slot, 'reply', i).random())
    rows = dc.REPLIES[t['mood']]
    return {f'r{k}': rows[i][0] for k, i in enumerate(order)}


def known_request(t: dict) -> str:
    return t['request']


# ------------------------------------------------------------------ public view
def public_task(t: dict) -> dict:
    v = copy.deepcopy(t)
    b = dc.bulletin(t['career'], t['day'])
    v['rules'] = b['rules']
    v['bulletin'] = b['notices']
    v['stamps'] = b.get('stamps')
    if not t['known']:
        v['docs'] = None
        v['drawer'] = None if 'drawer' in t else None
    else:
        for d in v['docs']:
            for f in d['fields']:
                if f.get('hidden') and f['hidden'] not in t['verified']:
                    f['value'] = None
                    f['locked'] = True
    return v


# ------------------------------------------------------------------ grading
def _issue_of(case: dict, field: str):
    return [i for i in case['issues'] if field in i['fields']]


def blind(t: dict, case: dict, verdict: str) -> bool:
    """A stamp that is only right after a check, taken without that check."""
    req = case.get('requires', {}).get(verdict)
    return bool(req) and req not in t['verified']


def grade_of(t: dict, case: dict, verdict: str) -> str:
    kind = case['accept'].get(verdict)
    if not kind or blind(t, case, verdict):
        return 'wrong'
    missing = [i['id'] for i in case['issues'] if i['id'] not in t['found']]
    needs = [x for x in case.get('needs', []) if x not in t['verified']]
    clean = not missing and not needs and t['false_flags'] == 0
    if t['career'] == 'customer_care':
        clean = clean and not t['breached'] and t['reply'] is not None and reply_grades(t).get(t['reply']) == 'best'
    return 'perfect' if kind == 'best' and clean else 'good'


def pay_for(t: dict, grade: str) -> int:
    base = BASE_PAY[t['career']] + 5 * (t['tier'] - 1)
    return base * SHARE[grade] // 100


# ------------------------------------------------------------------ actions
def _task(c: dict, p: dict) -> dict:
    e = _core()
    t = e.current_task(c, p.get('task'))
    e.need(t.get('desk'), 'Hồ sơ này làm ở bàn cũ, không phải bàn giấy tờ.')
    return t


def _patience(t: dict, delta: int) -> None:
    t['patience'] = max(25, min(100, t.get('patience', 100) + delta))


def _field(t: dict, ref) -> tuple[dict, dict]:
    e = _core()
    e.need(isinstance(ref, str) and ref.count('.') == 1, 'Chọn một dòng trên giấy tờ.')
    did, fid = ref.split('.')
    doc = next((d for d in t['docs'] if d['id'] == did), None)
    row = next((f for f in doc['fields'] if f['id'] == fid), None) if doc else None
    e.need(row, 'Không có dòng này trên giấy tờ.')
    return doc, row


def handle(s: dict, c: dict, career: str, action: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(career in CAREERS, 'Bàn giấy tờ không thuộc nghề này.')
    need(c['open'], 'Mở ca trước khi xử lý giấy tờ nhé.')
    t = _task(c, p)
    if action != 'desk_reply':
        need(t['known'], 'Nhận giấy tờ của khách trước đã.')
    if action == 'desk_flag':
        return _flag(s, c, t, p)
    if action == 'desk_check':
        return _check(s, c, t, p)
    if action == 'desk_count':
        return _count(s, c, t, p)
    if action == 'desk_reply':
        return _reply(s, c, t, p)
    if action == 'desk_decide':
        return _decide(s, c, t, p)
    raise e.GameError('Thao tác bàn giấy tờ chưa được hỗ trợ.', 'unknown_action')


def _flag(s, c, t, p):
    e = _core()
    ref = p.get('field')
    doc, row = _field(t, ref)
    e.need(not row.get('hidden') or row['hidden'] in t['verified'], 'Dòng này còn khóa. Kiểm tra trước rồi mới đánh dấu.')
    rule = p.get('rule')
    book = [r['id'] for r in dc.bulletin(t['career'], t['day'])['rules']]
    e.need(rule in book, 'Chọn một quy định trong sổ hôm nay.')
    e.need(not any(m['field'] == ref and m['rule'] == rule for m in t['marks']), 'Bạn đã đánh dấu dòng này với quy định này rồi.')
    e.need(len(t['marks']) < MAX_MARKS, 'Đã đánh dấu quá nhiều. Đóng dấu quyết định thôi nào.')
    case = secrets(t)
    issues = _issue_of(case, ref)
    hit = next((i for i in issues if i['rule'] == rule), None)
    short = dict(dc.RULES[t['career']])[rule][0]
    if hit:
        fresh_hit = hit['id'] not in t['found']
        if fresh_hit:
            t['found'].append(hit['id'])
            e.metric(c, {'pharmacy': 'inspections', 'accounting': 'matched', 'customer_care': 'desk_found'}[t['career']])
            e.metric(c, 'desk_found')
        t['marks'].append(dict(field=ref, rule=rule, result='found'))
        return dict(message=f'✔ {short}: {hit["why"]}', mark='found')
    if issues:
        for i in issues:
            if i['id'] not in t['partial']:
                t['partial'].append(i['id'])
        t['marks'].append(dict(field=ref, rule=rule, result='partial'))
        return dict(message='Dòng này đúng là có vấn đề, nhưng chưa phải quy định đó. Đọc lại sổ quy định nhé.', mark='partial')
    t['false_flags'] += 1
    t['marks'].append(dict(field=ref, rule=rule, result='wrong'))
    _patience(t, -FALSE_FLAG_PATIENCE)
    return dict(message=f'Dòng “{row["label"]}” không trái quy định “{short}”. Khách bắt đầu sốt ruột.', mark='wrong')


def _check(s, c, t, p):
    e = _core()
    cid = p.get('check')
    chk = next((x for x in t['checks'] if x['id'] == cid), None)
    e.need(chk, 'Không có bước kiểm này.')
    e.need(cid != 'count', 'Đếm từng tờ trong két rồi nhập tổng nhé.')
    e.need(cid not in t['verified'], 'Bước này đã có kết quả.')
    e.need(cid not in t['pending'], 'Đang chờ kết quả, làm việc khác một chút nhé.')
    e.metric(c, CHECK_METRIC[t['career']])
    if chk['delay']:
        t['pending'][cid] = c['turn'] + chk['delay']
        return dict(message=f'{chk["label"]}: đã hỏi, có kết quả sau {chk["delay"]} nhịp. Trong lúc chờ, bạn xử lý việc khác được.')
    t['verified'].append(cid)
    return dict(message=f'{chk["label"]}: ' + _revealed(t, cid))


def _revealed(t: dict, cid: str) -> str:
    rows = [f'{f["label"]} — {f["value"]}' for d in t['docs'] for f in d['fields'] if f.get('hidden') == cid]
    return '; '.join(rows) if rows else 'đã xong.'


def _count(s, c, t, p):
    e = _core()
    e.need(t['career'] == 'accounting' and t.get('drawer'), 'Hồ sơ này không có két để đếm.')
    e.need('count' not in t['verified'], 'Két đã đếm khớp rồi.')
    e.need(t['miscounts'] < 6, 'Đếm lệch nhiều lần rồi. Bạn vẫn có thể đóng dấu theo những gì đã thấy.')
    total = e.integer(p.get('total'), 0, 100000)
    case = secrets(t)
    t['count'] = total
    if total == case['cash']:
        t['verified'].append('count')
        e.metric(c, 'source_reads')
        return dict(message=f'Đếm khớp: trong két có {total} xu tiền thật. Giờ so với sổ quỹ nhé.', mark='found')
    t['miscounts'] += 1
    hint = ' Tờ nào không có sợi bạc 🧵 thì để riêng.' if any(r['id'] == 'ac_fake' for r in dc.bulletin('accounting', t['day'])['rules']) else ''
    return dict(message=f'Bạn đếm {total} xu, Lộc đếm lại thấy chưa khớp. Soát lại từng tờ nhé.{hint}', mark='wrong')


def _reply(s, c, t, p):
    e = _core()
    e.need(t['career'] == 'customer_care' and t.get('replies'), 'Hồ sơ này không có tin nhắn để trả lời.')
    e.need(t['reply'] is None, 'Bạn đã trả lời khách rồi. Giờ xử lý cho tới nơi nhé.')
    rid = p.get('reply')
    row = next((r for r in t['replies'] if r['id'] == rid), None)
    e.need(row, 'Chọn một câu trả lời.')
    grade = reply_grades(t)[rid]
    t['reply'] = rid
    _patience(t, REPLY_PATIENCE[grade])
    react = dc.REACT[t['mood']][grade]
    t['thread'] = [dict(who='player', text=row['text']), dict(who='npc', text=react)]
    if not t['known']:
        t['known'] = True
        t['status'] = 'understood'
    late = ' (trễ hạn phản hồi)' if t['breached'] else ''
    return dict(message=f'Khách: “{react}”{late}', mark={'best': 'found', 'ok': 'partial', 'bad': 'wrong'}[grade])


def _decide(s, c, t, p):
    e = _core()
    e.need(p.get('confirm') is True, 'Xác nhận con dấu trước khi đóng hồ sơ.')
    v = p.get('verdict')
    e.need(any(x['id'] == v for x in t['verdicts']), 'Chọn một con dấu có trên bàn.')
    case = secrets(t)
    d = data(c)
    grade = grade_of(t, case, v)
    career = t['career']
    t['verdict'] = v
    t['grade'] = grade
    t['mistakes'] = t['mistakes'] + MISTAKES[grade]
    pay = pay_for(t, grade)
    story = _story_line(t, d, v, case)
    unchecked = blind(t, case, v)
    # A wrong stamp is a mistake the person at the counter will talk about (and a late first reply too).
    slip = dc.slip_for(career, t['variant'], case, v, unchecked)
    if slip:
        cq.slip(t, *slip[:4], safety=slip[4])
    if career == 'customer_care' and t['breached']:
        row = dc.LATE_REPLY_SLIP
        cq.slip(t, *row[:4], safety=row[4])
    says = (case.get('says_blind', {}).get(v) if unchecked else None) or case['says'].get(v) or 'Hồ sơ đã được đóng dấu.'
    found = [i['why'] for i in case['issues'] if i['id'] in t['found']]
    missed = [i['why'] for i in case['issues'] if i['id'] not in t['found']]
    lines = []
    tip = case.get('tip', {}).get(v, 0) + story.get('tip', 0)
    if tip and cq.safety(t):
        lines.append(f'Cô Thu trả lại {tip} xu khách gửi thêm: không nhận tiền cho một lần giao sai.')
        tip = 0
    risk = max(case['risk'].get(v, 0), 2 if unchecked else 0)
    viral = case.get('viral', {}).get(v, 0)
    flag = STORY_FLAGS.get((career, t.get('chapter') or 0), {}).get(v) if t['variant'].endswith('_story') else None
    # stats + story memory
    d['stats'][grade] += 1
    d['history'] = ar.last(d['history'] + [dict(day=c['day'], task=t['id'], variant=t['variant'], grade=grade, verdict=v)], 60, 'desk.history', c)
    if flag and flag not in d['flags']:
        d['flags'] = ar.last(d['flags'] + [flag], 30, 'desk.flags', c)
    if viral:
        d['viral'] = min(9, d['viral'] + viral)
        lines.append(f'Bài chê lan thêm (mức ồn: {d["viral"]}).')
    # quests & achievements
    kind = case['accept'].get(v)
    if career == 'pharmacy' and kind:
        e.metric(c, 'ph_verified')
    if career == 'accounting' and v == 'hold':
        e.metric(c, 'source_requests')
    if career == 'customer_care':
        if kind:
            e.metric(c, 'cs_executed')
        if grade == 'perfect':
            e.metric(c, 'cs_confirmed')
        if v == 'escalate':
            e.metric(c, 'handovers')
    if grade == 'perfect':
        e.metric(c, 'desk_perfect')
    status = 'referred' if v in REFERRED else 'completed'
    narrative = says + (' ' + story['text'] if story.get('text') else '')
    citation = None
    if risk:
        d['risk'] = min(99, d['risk'] + risk)
        if d['today'].get('day') != c['day']:
            d['today'] = dict(day=c['day'], citations=0, fines=0)
        d['today']['citations'] += 1
        rule = next((i['rule'] for i in case['issues']), None)
        if unchecked:
            label = next((x['label'] for x in t['checks'] if x['id'] == case['requires'][v]), 'kiểm tra')
            rule_text = f'Làm trước khi “{label}”'
        else:
            rule_text = dc.RULES[career][rule][0] if rule else 'Quy trình quầy'
        citation = dict(rule=rule_text, fine=0, n=d['today']['citations'])
    result = dict(grade=grade, label=GRADE_LABEL[grade], verdict=v, says=narrative, found=found, missed=missed,
                  false_flags=t['false_flags'], pay=pay, tip=0, fine=0, citation=None, lines=lines,
                  breached=t['breached'] if career == 'customer_care' else None)
    t['result'] = result
    # The grade already set the pay (a wrong stamp earns nothing, a late reply 60%), so the
    # reaction only speaks and escalates here: no second cut on the same mistake.
    reaction = cq.react(s, c, t, 0)
    e.task_done(s, c, t, pay, narrative, status)
    if tip:
        e.money(s, c, tip, 'Khách gửi thêm' if case.get('tip', {}).get(v) else 'Lời cảm ơn của khách quen', t['id'], 'tip')
        result['tip'] = tip
    if story.get('bonus'):
        e.money(s, c, story['bonus'], 'Khách quen giới thiệu bạn bè', t['id'], 'skill_reward')
        result['tip'] += story['bonus']
    if v == 'cover' and case.get('cover'):
        spent = min(case['cover'], c['money'])
        if spent:
            e.money(s, c, -spent, 'Tự bù tiền thiếu trong két', t['id'], 'cash_cover')
            lines.append(f'Bạn bỏ {spent} xu tiền túi vào két.')
    if citation:
        if citation['n'] <= 2:
            lines.append(f'📄 Phiếu nhắc {citation["n"]}/2: {citation["rule"]}. Từ phiếu thứ ba trong ngày sẽ bị trừ xu.')
        else:
            fine = min(20, 5 * risk, c['money'])
            if fine:
                e.money(s, c, -fine, 'Phiếu phạt quầy: ' + citation['rule'], t['id'], 'fine')
                d['today']['fines'] += fine
            citation['fine'] = fine
            lines.append(f'📄 Phiếu phạt: {citation["rule"]} · −{fine} xu.')
        d['citations'] = ar.last(d['citations'] + [dict(day=c['day'], task=t['id'], rule=citation['rule'], fine=citation['fine'])], 40, 'desk.citations', c)
        result['citation'] = citation
        result['fine'] = citation['fine']
    msg = {'perfect': 'Chuẩn từng dòng', 'good': 'Đã xử lý', 'wrong': 'Hồ sơ có sai sót'}[grade]
    total = pay + result['tip'] - result['fine']
    tail = f' {reaction["message"]}' if reaction['message'] else ''
    return dict(message=f'{msg} · {"+" if total >= 0 else "−"}{abs(total)} xu. {says}{tail}', celebrate=grade != 'wrong' and not cq.slips(t),
                desk_result=result)


def _story_line(t: dict, d: dict, v: str, case: dict) -> dict:
    """Consequences of earlier chapters, read back at the stamp."""
    if not t['variant'].endswith('_story') or not case['accept'].get(v):
        return {}
    flags = set(d['flags'])
    ch = t.get('chapter')
    if t['career'] == 'pharmacy' and ch == 4:
        if 'nam_risk' in flags:
            return dict(text='Bác vẫn nhắc lần giao vội hôm trước; cô Thu dặn bạn soát kỹ hơn cho bác.')
        if 'nam_safe' in flags:
            return dict(text='Bác còn gửi kèm túi ổi nhà trồng “cho người chịu chậm lại”.', tip=10)
    if t['career'] == 'accounting' and ch == 3:
        if 'hoa_hid' in flags:
            return dict(text='Cơ quan thuế hỏi thêm ba đơn tiền mặt từng bị bỏ khỏi sổ; cô Hoa phải bổ sung và nộp phạt.')
        if 'hoa_honest' in flags:
            return dict(text='Nhờ sổ ghi đủ từ hôm trước, giải trình khớp ngay. Cô Hoa gửi bạn lời cảm ơn kèm 15 xu.', tip=15)
    if t['career'] == 'accounting' and ch == 4:
        if 'hoa_hid' in flags:
            return dict(text='Ngân hàng hỏi kỹ hơn vì sổ cũ từng thiếu doanh thu, quầy mới mở chậm một tuần.')
        if 'hoa_honest' in flags:
            return dict(text='Khoản vay mở quầy được duyệt nhanh nhờ sổ sạch từ đầu.', bonus=10)
    if t['career'] == 'customer_care' and ch == 4:
        if 'phuc_favor' in flags:
            return dict(text='Phúc lại hỏi xin ưu tiên thêm lần nữa; lần này bạn từ chối khó hơn.')
        if 'phuc_fair' in flags:
            return dict(text='Phúc còn giới thiệu hai người bạn tới đặt hàng ở trạm.', bonus=10)
    return {}


# ------------------------------------------------------------------ day hooks
def tick(s: dict, c: dict, career: str) -> list[str]:
    """Pending checks arrive, support SLAs run out, today's notices show once."""
    e = _core()
    notes = []
    if not c['open'] or career not in CAREERS:
        return notes
    d = data(c)
    for t in c['tasks']:
        if not t.get('desk') or t['status'] in DONE:
            continue
        for cid, ready in list(t['pending'].items()):
            if c['turn'] >= ready:
                t['pending'].pop(cid)
                if cid not in t['verified']:
                    t['verified'].append(cid)
                chk = next((x for x in t['checks'] if x['id'] == cid), dict(label='Kết quả'))
                notes.append(f'{chk["label"]} có kết quả: {t["title"]}')
                e.log(s, c, 'delivery', notes[-1] + ' · ' + _revealed(t, cid), t['npc'], t['id'])
        if (t['career'] == 'customer_care' and t['reply'] is None and not t['breached'] and t['due_turn'] is not None
                and 0 <= t['due_turn'] - c['turn'] <= 3 and t['id'] not in d['warned']):
            d['warned'] = ar.last(d['warned'] + [t['id']], 20, 'desk.warned', c)
            notes.append(f'⏳ {t["title"]}: còn {t["due_turn"] - c["turn"]} nhịp để trả lời câu đầu.')
        if t['career'] == 'customer_care' and t['reply'] is None and not t['breached'] and t['due_turn'] is not None and c['turn'] > t['due_turn']:
            t['breached'] = True
            _patience(t, -BREACH_PATIENCE)
            if t.get('sla') == 'public':
                d['viral'] = min(9, d['viral'] + 1)
            notes.append(f'⏰ Quá hạn phản hồi: {t["title"]}. Khách đợi lâu quá rồi.')
    if d['bulletin_day'] != c['day']:
        d['bulletin_day'] = c['day']
        b = dc.bulletin(career, c['day'])
        fresh_rules = [r['short'] for r in b['rules'] if r['new']]
        if fresh_rules:
            notes.append('📰 Bản tin hôm nay có quy định mới: ' + ', '.join(fresh_rules) + '.')
    return notes


def on_start(s: dict, c: dict, career: str) -> None:
    if career not in CAREERS:
        return
    d = data(c)
    d['today'] = dict(day=c['day'], citations=0, fines=0)
    if career == 'customer_care' and d['viral'] >= 3:
        for t in c['tasks']:
            if t.get('desk') and t['status'] not in DONE and t['day'] == c['day']:
                _patience(t, -10)
        _core().log(s, c, 'fact', 'Bài chê hôm trước vẫn còn lan: khách hôm nay dễ sốt ruột hơn.')
    if d['viral']:
        d['viral'] -= 1


def on_close(s: dict, c: dict, career: str) -> dict | None:
    if career not in CAREERS:
        return None
    e = _core()
    d = data(c)
    day = c['day']
    rows = [h for h in d['history'] if h['day'] == day]
    lines = []
    if rows:
        n = {g: sum(h['grade'] == g for h in rows) for g in GRADES}
        lines.append(f'Hồ sơ giấy tờ: {n["perfect"]} chuẩn · {n["good"]} đạt · {n["wrong"]} chưa đúng.')
    if d['today'].get('day') == day and d['today']['citations']:
        lines.append(f'Phiếu nhắc trong ngày: {d["today"]["citations"]}' + (f' · đã trừ {d["today"]["fines"]} xu.' if d['today']['fines'] else '.'))
    note = None
    if day % dc.INSPECT_EVERY[career] == 0:
        who = {'pharmacy': 'Đoàn kiểm tra', 'accounting': 'Chị Trâm', 'customer_care': 'Chị Mai'}[career]
        risk = d['risk']
        if risk == 0:
            e.money(s, c, 25, f'{who} khen quầy làm đúng quy trình', f'desk-inspect-{day}', 'skill_reward')
            note = f'{who} xem lại cả chặng: không có sai sót nào. Thưởng 25 xu.'
            outcome = 'praise'
        elif risk <= 3:
            note = f'{who} nhắc nhở {risk} điểm rủi ro từ các lần đóng dấu vội. Lần sau soát kỹ hơn nhé.'
            outcome = 'warning'
        else:
            fine = min(60, 10 * (risk - 3), c['money'])
            if fine:
                e.money(s, c, -fine, f'{who} lập biên bản quy trình', f'desk-inspect-{day}', 'fine')
            note = f'{who} lập biên bản: {risk} điểm rủi ro · trừ {fine} xu.'
            outcome = 'fine'
        d['inspections'] = ar.last(d['inspections'] + [dict(day=day, risk=risk, outcome=outcome)], 20, 'desk.inspections', c)
        d['risk'] = 0
    if not lines and not note:
        return None
    return dict(lines=lines, note=note)


def feedback(c: dict, t: dict) -> dict:
    g = t.get('grade') or 'good'
    patience = t.get('patience', 100)
    wait = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    acc = {'perfect': 5, 'good': 4, 'wrong': 2}[g]
    sharp = 5 if t.get('false_flags', 0) == 0 else 4 if t['false_flags'] <= 2 else 3
    career = t['career']
    if career == 'pharmacy':
        rows = [('care', 'An toàn, đúng quy trình', acc, 'soát từng dòng phiếu' if g == 'perfect' else 'còn dòng chưa soát kỹ'),
                ('clarity', 'Giải thích rõ', sharp, 'nói rõ lý do' if sharp >= 5 else 'đánh dấu nhầm vài dòng'),
                ('speed', 'Thời gian chờ', wait, f'kiên nhẫn còn {patience}%')]
    elif career == 'accounting':
        rows = [('accuracy', 'Chính xác', acc, 'mọi dòng khớp chứng từ' if g == 'perfect' else 'còn chỗ chưa khớp'),
                ('evidence', 'Có căn cứ', sharp, 'đánh dấu đúng chỗ' if sharp >= 5 else 'đánh dấu nhầm vài dòng'),
                ('speed', 'Đúng hẹn', wait, f'nhịp chờ còn {patience}%')]
    else:
        tone = {'best': 5, 'ok': 4, 'bad': 2}.get(reply_grades(t).get(t.get('reply')), 3) if t.get('replies') else 4
        rows = [('resolution', 'Giải quyết tới nơi', acc, 'xử lý đúng hồ sơ' if g != 'wrong' else 'hướng xử lý chưa hợp'),
                ('attitude', 'Lời lẽ', tone, 'trả lời đúng mực' if tone >= 4 else 'câu trả lời đầu hơi cụt'),
                ('speed', 'Tốc độ', 2 if t.get('breached') else wait, 'trễ hạn phản hồi' if t.get('breached') else f'kiên nhẫn còn {patience}%')]
    if cq.slips(t):
        stars = cq.star_cap(t)  # a wrong stamp costs stars by how bad it was, even when it pleased at the counter
    else:
        stars = 5 if g == 'perfect' else 4 if g == 'good' else (4 if t.get('verdict') in secrets(t)['pleases'] else 2)
    return dict(criteria=[dict(key=k, label=l, score=sc, note=n) for k, l, sc, n in rows], stars=stars, cap=5)


def assist(s: dict, c: dict, t: dict, role: str) -> str | None:
    """A hired helper runs one quick check or chases a slow one; never stamps."""
    if not t['known']:
        return None
    for chk in t['checks']:
        if chk['id'] in t['verified'] or chk['id'] == 'count':
            continue
        if chk['id'] in t['pending']:
            t['pending'][chk['id']] = c['turn']
            return f'Đã nhắc bên liên quan: {chk["label"]}. Kết quả sắp tới.'
        if not chk['delay']:
            t['verified'].append(chk['id'])
            return f'Đã làm giúp bước “{chk["label"]}”. Quyết định vẫn là của bạn.'
    return None


# ------------------------------------------------------------------ save support
LEGACY_TEXT = {
    'Mình có phiếu mô phỏng này, nhờ bạn lấy đúng mã và số lượng.': 'Mình có phiếu của phòng khám đây, nhờ bạn lấy đúng mã và số lượng.',
    'Mình muốn biết cách xem đơn trong ứng dụng mô phỏng.': 'Mình muốn biết cách xem đơn trong ứng dụng của cửa hàng.',
    'Chính sách mô phỏng': 'Chính sách đổi trả',
    'Có thể mở kiểm tra chặng và hẹn cập nhật trong nhịp game tiếp theo.': 'Có thể mở kiểm tra chặng và hẹn cập nhật ở nhịp tiếp theo.',
    'Có yêu cầu hoàn 120 xu từ quỹ công ty giả lập.': 'Có yêu cầu hoàn 120 xu từ quỹ công ty.',
    'Khách chỉ cần xem trạng thái đơn trong ứng dụng game.': 'Khách chỉ cần xem trạng thái đơn trong ứng dụng của cửa hàng.',
    'P-04 · quá hạn game': 'P-04 · quá hạn',
}


def _swap(obj: dict, keys) -> None:
    for k in keys:
        if isinstance(obj.get(k), str) and obj[k] in LEGACY_TEXT:
            obj[k] = LEGACY_TEXT[obj[k]]


def _refresh_cases(c: dict, cid: str) -> None:
    """A case saved by an older build whose papers no longer match today's content.
    Unfinished ones start again from the current papers; finished ones (already paid,
    already in the ledger) stay as closed records so their slot is never dealt twice.
    Matching cases are left untouched."""
    from .content import make_task as build
    keep, changed = [], False
    for t in c['tasks']:
        if not (isinstance(t, dict) and t.get('desk')):
            keep.append(t)
            continue
        try:
            slot = int(str(t['id']).rsplit('-', 1)[1])
            now = build(cid, t['day'], slot, t['created_turn'])
        except (KeyError, TypeError, ValueError, IndexError):
            keep.append(t)  # malformed: let validation report it
            continue
        if now.get('desk') and all(t.get(k) == now.get(k) for k in STATIC + ('npc', 'title', 'opening')):
            keep.append(t)
            continue
        changed = True
        if t.get('status') in DONE:
            # Already paid and logged: keep the slot taken so the same case is never dealt twice.
            now.update(status='cancelled', completed_turn=t.get('completed_turn', t['created_turn']))
        else:
            now['deferred'] = bool(t.get('deferred'))
        keep.append(now)
    if changed:
        c['tasks'] = keep
        if c.get('active_task') not in {t.get('id') for t in keep if isinstance(t, dict)}:
            c['active_task'] = next((t['id'] for t in keep if isinstance(t, dict) and t.get('status') not in DONE and not t.get('deferred')), None)


def migrate(s: dict) -> None:
    """Older saves: give the desks their memory and refresh wording that changed."""
    careers = s.get('careers')
    if not isinstance(careers, dict):
        return
    for cid in CAREERS:
        c = careers.get(cid)
        if not isinstance(c, dict):
            continue
        ext = c.get('ext')
        if isinstance(ext, dict) and isinstance(ext.get('data'), dict):
            d = ext['data'].setdefault('desk', fresh())
            if isinstance(d, dict):
                d.setdefault('warned', [])
        for t in c.get('tasks') or []:
            if not isinstance(t, dict):
                continue
            _swap(t, ('opening',))
            for ev in t.get('evidence') or []:
                if isinstance(ev, dict):
                    _swap(ev, ('title', 'text'))
        if isinstance(c.get('tasks'), list):
            _refresh_cases(c, cid)
        act = (c.get('life') or {}).get('activity') if isinstance(c.get('life'), dict) else None
        if isinstance(act, dict):
            for card in act.get('cards') or []:
                if isinstance(card, dict):
                    _swap(card, ('label', 'value', 'hint'))
            for card in act.get('right') or []:
                if isinstance(card, dict):
                    _swap(card, ('label', 'hint'))


def validate_data(c: dict) -> None:
    e = _core()
    need = e.need
    d = c['ext']['data'].get('desk')
    need(isinstance(d, dict), 'Thiếu dữ liệu bàn giấy tờ.')
    for k in ('bulletin_day', 'risk', 'viral'):
        e.integer(d.get(k), 0, 10 ** 9)
    need(isinstance(d.get('flags'), list) and len(d['flags']) <= 30 and all(f in FLAG_IDS for f in d['flags']), 'Dấu chuyện không hợp lệ.')
    need(isinstance(d.get('warned'), list) and len(d['warned']) <= 20 and all(isinstance(x, str) and len(x) <= 80 for x in d['warned']), 'Nhắc hạn không hợp lệ.')
    for k, cap in (('citations', 40), ('inspections', 20), ('history', 60)):
        need(isinstance(d.get(k), list) and len(d[k]) <= cap and all(isinstance(x, dict) for x in d[k]), 'Sổ bàn giấy tờ không hợp lệ.')
    for h in d['history']:
        need(h.get('grade') in GRADES, 'Lịch sử hồ sơ không hợp lệ.')
        e.integer(h.get('day'), 1, 10 ** 9)
    for x in d['citations']:
        e.integer(x.get('fine'), 0, 1000)
        e.clean_text(x.get('rule'), 200)
    need(isinstance(d.get('stats'), dict) and set(d['stats']) == set(GRADES), 'Thống kê hồ sơ không hợp lệ.')
    for g in GRADES:
        e.integer(d['stats'][g], 0, 10 ** 9)
    need(isinstance(d.get('today'), dict), 'Thiếu sổ trong ngày.')
    for k in ('day', 'citations', 'fines'):
        e.integer(d['today'].get(k), 0, 10 ** 9)


def validate_task(t: dict, original: dict) -> None:
    e = _core()
    need = e.need
    need(original.get('desk') is True, 'Hồ sơ giấy tờ không khớp lịch ngày.')
    for k in STATIC:
        need(t.get(k) == original.get(k), 'Giấy tờ gốc của hồ sơ đã bị sửa: ' + k)
    case = secrets(t)
    ids = {i['id'] for i in case['issues']}
    need(isinstance(t.get('found'), list) and set(t['found']) <= ids and len(set(t['found'])) == len(t['found']), 'Dấu phát hiện không hợp lệ.')
    need(isinstance(t.get('partial'), list) and set(t['partial']) <= ids, 'Dấu phát hiện không hợp lệ.')
    need(isinstance(t.get('marks'), list) and len(t['marks']) <= MAX_MARKS, 'Quá nhiều dấu trên giấy tờ.')
    for m in t['marks']:
        need(isinstance(m, dict) and m.get('result') in ('found', 'partial', 'wrong'), 'Dấu trên giấy tờ không hợp lệ.')
        e.clean_text(m.get('field'), 80)
        e.clean_text(m.get('rule'), 40)
    need(sum(m['result'] == 'wrong' for m in t['marks']) == e.integer(t.get('false_flags'), 0, MAX_MARKS), 'Số lần đánh dấu nhầm không khớp.')
    # Every find must come from a mark on the paper, and every mark must read the same today.
    hits, near = set(), set()
    for m in t['marks']:
        on_row = _issue_of(case, m['field'])
        hit = next((i for i in on_row if i['rule'] == m['rule']), None)
        need(m['result'] == ('found' if hit else 'partial' if on_row else 'wrong'), 'Dấu trên giấy tờ không khớp hồ sơ.')
        if hit:
            hits.add(hit['id'])
        elif on_row:
            near.update(i['id'] for i in on_row)
    need(set(t['found']) == hits and set(t['partial']) == near, 'Dấu phát hiện không khớp các dòng đã đánh dấu.')
    checks = {x['id'] for x in t['checks']}
    need(isinstance(t.get('verified'), list) and set(t['verified']) <= checks and len(set(t['verified'])) == len(t['verified']), 'Bước kiểm không hợp lệ.')
    need(isinstance(t.get('pending'), dict) and set(t['pending']) <= {x['id'] for x in t['checks'] if x['delay']}, 'Bước chờ không hợp lệ.')
    for v in t['pending'].values():
        e.integer(v, 0, 10 ** 9)
    need(not set(t['pending']) & set(t['verified']), 'Bước kiểm vừa chờ vừa xong.')
    if 'count' in t['verified']:
        need(t.get('count') == case.get('cash'), 'Số đếm két không khớp.')
    need(t.get('count') is None or type(t['count']) is int, 'Số đếm két không hợp lệ.')
    e.integer(t.get('miscounts'), 0, 6)
    need(type(t.get('breached')) is bool, 'Trạng thái hạn phản hồi thiếu.')
    if t['career'] == 'customer_care':
        need(t.get('reply') is None or t['reply'] in {r['id'] for r in t['replies']}, 'Câu trả lời không hợp lệ.')
    else:
        need(t.get('reply') is None, 'Câu trả lời không hợp lệ.')
    need(isinstance(t.get('thread'), list) and len(t['thread']) <= 4, 'Tin nhắn không hợp lệ.')
    for m in t['thread']:
        need(isinstance(m, dict) and m.get('who') in ('player', 'npc'), 'Tin nhắn không hợp lệ.')
        e.clean_text(m.get('text'), 600)
    v = t.get('verdict')
    if v is None:
        need(t['status'] not in ('completed', 'referred') and t.get('grade') is None and t.get('result') is None, 'Hồ sơ đóng mà chưa có con dấu.')
    else:
        need(any(x['id'] == v for x in t['verdicts']), 'Con dấu không hợp lệ.')
        need(t['status'] in DONE, 'Hồ sơ có con dấu mà chưa đóng.')
        need(t.get('grade') == grade_of(t, case, v), 'Kết quả hồ sơ không khớp những gì đã làm.')
        need(isinstance(t.get('result'), dict), 'Thiếu kết quả hồ sơ.')
