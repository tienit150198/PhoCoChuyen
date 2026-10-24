"""Server-graded step slips shared by 🏍️ Tiệm sửa xe Út Lanh (moto) and 🩺 Phòng khám Thú y Cỏ May (vet).

A job is a list of typed steps the player answers one at a time (the same four kinds as 📻 the radio's slips):
  choice   one option (a diagnosis, the honest answer to an awkward customer)
  order    every option, in the right order (a procedure: changing the oil, an injection)
  multi    the right subset (what to check, what to tell the owner)
  number   an integer read or worked out (a tyre pressure, a weight on the scale, a dose in ml)
Options get neutral letter ids (a, b, c…): an id never says whether it is the answer. A job is a pure function of its
seed (career, day, slot), so the answers stay on the server and validate_task rebuilds them.

The second half runs 🛎️ Phố dịch vụ orders from other players inside the career (svc_work): the same kind of steps,
seeded by the order id; a finished order is kept in the career's data (`svc_ok`), which the service's deliver hook
reads from the provider's committed save before the market pays (game/moto_service.py, game/vet_service.py).
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from . import kit

LETTERS = 'abcdefghij'


def step(job: str, name: str, typ: str, title: str, evidence: str, options=None, unit: str = '') -> dict:
    st = dict(id=f'{job}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if unit:
        st['unit'] = unit
    return st


def lettered(r, rows) -> tuple:
    """Shuffle (key, label) rows and give them neutral ids: (options, {key: letter})."""
    rows = list(rows)
    r.shuffle(rows)
    return [dict(id=LETTERS[i], label=label) for i, (_, label) in enumerate(rows)], {k: LETTERS[i] for i, (k, _) in enumerate(rows)}


def scenario(r, job: str, name: str, title: str, row) -> tuple:
    """A choice step from one (situation, right, wrongs) row: (step, the right letter)."""
    text, right, wrongs = row
    opts, ids = lettered(r, [('right', right)] + [(f'w{i}', w) for i, w in enumerate(wrongs)])
    return step(job, name, 'choice', title, text, opts), ids['right']


def ordered(r, job: str, name: str, title: str, evidence: str, rows) -> tuple:
    """An order step from the right sequence of (key, label) rows: (step, the right letters in order)."""
    opts, ids = lettered(r, rows)
    return step(job, name, 'order', title, evidence, opts), [ids[k] for k, _ in rows]


def picks(r, job: str, name: str, title: str, evidence: str, good, bad) -> tuple:
    """A multi step: the good rows are the answer, the bad ones the traps: (step, sorted right letters)."""
    rows = [(f'g{i}', x) for i, x in enumerate(good)] + [(f'b{i}', x) for i, x in enumerate(bad)]
    opts, ids = lettered(r, rows)
    return step(job, name, 'multi', title, evidence, opts), sorted(ids[f'g{i}'] for i in range(len(good)))


def pairs_to_steps(pairs) -> tuple:
    """[(step, answer)] → (steps, {step id: answer})."""
    steps, key = [], {}
    for st, ans in pairs:
        steps.append(st)
        key[st['id']] = ans
    return steps, key


def value(st: dict, v):
    """The player's answer to `st`, checked for shape only (never for being right)."""
    typ = st['type']
    if typ == 'choice':
        return kit.one_of(v, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(v, 0, 1_000_000)
    ids = [o['id'] for o in st['options']]
    got = kit.id_list(v, ids, len(ids))
    if typ == 'order':
        kit.need(len(got) == len(ids) and len(set(got)) == len(ids), 'Xếp đủ mọi việc theo thứ tự nhé.')
        return list(got)
    kit.need(len(set(got)) == len(got), 'Mỗi dòng chọn một lần thôi.')
    return sorted(got)


def same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def quality(wrong: int, cost: int, floor: int) -> int:
    return max(floor, 100 - cost * wrong)


# ---------------------------------------------------------------- a slip worked step by step (moto, vet)
def work(t: dict, p: dict, quality_of, who: str, lines: int, sev=None, how=None) -> tuple:
    """Grade the payload's answer to the slip's open step: (correct, message, finished). A wrong answer stays open, is
    logged once per step (errors, a review slip of severity sev(step id)) and lowers t['quality'].
    `how(t, step)`: None, or (hint, worked) for a worked-out number: the hint (the way, with the slip's own numbers) on
    the first slip, the whole working down to the answer from kit.REVEAL_AFTER slips on (said by `who`)."""
    from .. import consequences as cq
    steps, key = t['needs']['steps'], t['_key']
    kit.need(t['at'] < len(steps), 'Phiếu này đã xong.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    v = value(st, p.get('value'))
    kit.start_work(t)
    if not same(v, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], sev(st['id']) if sev else 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = quality_of(t['wrong'])
        again = 'Tính lại cho kỹ nhé.' if st['type'] == 'number' else 'Xem lại sổ tay rồi làm lại bước này.'
        hint, worked = (how(t, st) if how else None) or ('', '')
        if worked and kit.tries_on_step(t.get('lines')) + 1 >= kit.REVEAL_AFTER:
            say = f'{who} chỉ: {worked}'
        else:
            say = kit.step_help(t, st, key[st['id']], hint, again, who)
        message = f'Chưa đúng: {st["title"].lower()}. {say}'
        t['lines'] = (t['lines'] + [message[:480]])[-lines:]
        return False, message, False
    t['work'][st['id']] = v
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-lines:]
    if t['at'] < len(steps):
        return True, 'Đúng rồi. Tiếp: ' + steps[t['at']]['title'].lower() + '.', False
    t['stage'] = 'done'
    return True, '', True


def validate_slip(t: dict, original: dict, fixed, quality_of, paid_of, lines: int, what: str) -> None:
    """The shared checks of a step slip: the fixed fields match the regenerated task, the work done is the key's
    answers in order, and the error log, quality and pay agree."""
    for k in fixed:
        kit.need(same(t.get(k), original.get(k)), f'Dữ kiện {what} bị thay đổi: {k}')
    steps, key = t['needs']['steps'], t['_key']
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), f'Tiến trình {what} sai.')
    kit.need(at == 0 or t['known'], f'Chưa nhận {what}.')
    done = t.get('work')
    kit.need(isinstance(done, dict) and set(done) == set(ids[:at]), f'Các bước {what} không liên tục.')
    kit.need(all(same(done[i], key[i]) for i in ids[:at]), f'Kết quả bước {what} sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), f'Nhật ký lỗi {what} sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), f'Nhật ký lỗi {what} sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(t.get('quality') == quality_of(wrong), f'Điểm chất lượng {what} không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (paid_of(t) if at == len(steps) else 0), f'Tiền của {what} không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= lines and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             f'Nhật ký {what} sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), f'{what} chưa xong mà đã hoàn tất.')
    kit.need(at == 0 or t.get('status') != 'new', f'{what} sai trạng thái.')


# ---------------------------------------------------------------- 🛎️ Phố dịch vụ orders worked in a career (moto, vet)
SVC_OPEN = 6       # player jobs open at once
SVC_KEEP = 20      # finished player jobs remembered for the market's deliver hook
ORDER_RX = re.compile(r'sv_[0-9a-f]{24}')


def svc_grade(wrong: int) -> int:
    """⭐ of a player job: 3, one less per wrong step, at least 1."""
    return max(1, 3 - wrong)


def svc_work(d: dict, p: dict, services, job_of, done_message: str) -> dict:
    """One step of a 🛎️ order from another player (no money, no xp here: the market pays at delivery, and an order id
    is only checked against the market there). The finished order goes into d['svc_ok']."""
    kit.need(set(p) <= {'order', 'service', 'step', 'value', 'drop', 'confirm'}, 'Thông tin phiếu không hợp lệ.')
    order = p.get('order')
    kit.need(isinstance(order, str) and ORDER_RX.fullmatch(order), 'Mã đơn không hợp lệ.')
    if p.get('drop') is True:   # the buyer cancelled or was refunded: an untouched job leaves the book and frees its slot
        job = next((x for x in d['svc'] if x['o'] == order), None)
        kit.need(job is not None, 'Không có đơn này trong sổ.')
        # a started job stays (dropping it and taking it again would wipe its mistakes): finishing it frees the slot too
        kit.need(job['at'] == 0 and job['wrong'] == 0, 'Đơn này đã làm dở. Làm nốt các bước là đơn rời sổ.')
        d['svc'] = [x for x in d['svc'] if x['o'] != order]
        return dict(message='Đã bỏ đơn khỏi sổ.')
    service = kit.one_of(p.get('service'), services, 'Dịch vụ không hợp lệ.')
    if any(x['o'] == order for x in d['svc_ok']):
        return dict(message='Đơn này đã làm xong. Bấm Giao ở 🛎️ Phố dịch vụ nhé.', svc_ready=order)
    job = next((x for x in d['svc'] if x['o'] == order), None)
    if job is None:
        kit.need(len(d['svc']) < SVC_OPEN, f'Đang có {SVC_OPEN} đơn của người chơi chờ làm. Làm xong bớt rồi nhận thêm nhé.')
        job = dict(o=order, s=service, at=0, wrong=0)
        d['svc'].append(job)
        if 'step' not in p:
            return dict(message='Đã nhận đơn vào sổ. Làm từng bước trên phiếu nhé.')
    kit.need(job['s'] == service, 'Phiếu này là dịch vụ khác.')
    if 'step' not in p:   # opened again: nothing changes
        return dict(message='Đơn này đã ở trong sổ. Làm tiếp bước đang mở nhé.')
    steps, key = job_of(order, service)
    st = steps[job['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    v = value(st, p.get('value'))
    if not same(v, key[st['id']]):
        job['wrong'] = min(job['wrong'] + 1, 99)
        return dict(message=f'Chưa đúng: {st["title"].lower()}. Xem lại sổ tay rồi làm lại bước này.', correct=False)
    job['at'] += 1
    if job['at'] < len(steps):
        return dict(message='Đúng rồi. Tiếp: ' + steps[job['at']]['title'].lower() + '.', correct=True)
    d['svc'] = [x for x in d['svc'] if x['o'] != order]
    d['svc_ok'] = (d['svc_ok'] + [dict(o=order, s=service, q=svc_grade(job['wrong']))])[-SVC_KEEP:]
    d['stats']['svc'] += 1
    return dict(message=done_message, correct=True, celebrate=job['wrong'] == 0, svc_ready=order)


def svc_public(d: dict, job_of) -> tuple:
    """(the open jobs as the client sees them, the finished order ids)."""
    jobs = []
    for x in d['svc']:
        steps, _ = job_of(x['o'], x['s'])
        jobs.append(dict(order=x['o'], service=x['s'], at=x['at'], total=len(steps), wrong=x['wrong'],
                         step=deepcopy(steps[x['at']]) if x['at'] < len(steps) else None))
    return jobs, [x['o'] for x in d['svc_ok']]


def svc_validate(d: dict, services, job_of) -> None:
    kit.need(isinstance(d['svc'], list) and len(d['svc']) <= SVC_OPEN, 'Phiếu của người chơi sai.')
    seen = set()
    for x in d['svc']:
        kit.need(isinstance(x, dict) and set(x) == {'o', 's', 'at', 'wrong'} and isinstance(x['o'], str) and ORDER_RX.fullmatch(x['o'])
                 and x['s'] in services and x['o'] not in seen, 'Phiếu của người chơi sai.')
        seen.add(x['o'])
        kit.integer(x['at'], 0, len(job_of(x['o'], x['s'])[0]) - 1)
        kit.integer(x['wrong'], 0, 99)
    kit.need(isinstance(d['svc_ok'], list) and len(d['svc_ok']) <= SVC_KEEP, 'Sổ đơn người chơi đã xong sai.')
    for x in d['svc_ok']:
        kit.need(isinstance(x, dict) and set(x) == {'o', 's', 'q'} and isinstance(x['o'], str) and ORDER_RX.fullmatch(x['o'])
                 and x['s'] in services and type(x['q']) is int and x['q'] in (1, 2, 3) and x['o'] not in seen,
                 'Sổ đơn người chơi đã xong sai.')
        seen.add(x['o'])   # an order is open or finished, once
