"""Bỏ dở việc: walking off a workplace mid-work to go and try another one.

The engine calls in at one point, the switch (`select_career`, and any command
aimed at another workplace than the current one):

* `check(s, target, p, internal)` decides whether leaving the current workplace
  now abandons work in progress. In the story it refuses the switch unless the
  payload carries `confirm: true`; with it, the penalty is applied once here.
  With the story off (the free sandbox, tests, MNL_DEV sweeps) it never charges
  anything and only returns a soft warning.
* `public(s)` gives the client a preview of the current workplace (the numbers
  the confirm dialog shows are the numbers the server will apply) and the
  per-workplace "Điểm tin cậy của chủ".
* `on_close(s, c, career, summary)` lists today's abandonments in the day
  summary and lets a clean day win back a little trust.

In progress means the workplace's day is open and either a job was started
(one work step taken), customers are waiting, or a promised order is due. A
closed day, a place you only looked at, or an empty counter costs nothing.

The penalty (deterministic, rolled from ids, applied once per abandonment):

* a fine, scaled to the work abandoned and escalating with repeats the same
  day. An owner pays from the shop fund (refunds to the waiting customers and
  lost goodwill; what the fund lacks comes from the wallet); an employee has it
  docked from the wallet (what the wallet lacks comes from the workplace pay);
* trust drops: the office boss's trust for office jobs, the street's trust for
  places you own, and "Điểm tin cậy của chủ" (kept here) for other employers;
* the started jobs are cancelled with an annoyed review, waiting customers walk
  out, and the boss (or a neighbour) sends one line. The second time in a day
  the boss warns "lần sau cho nghỉ"; nobody is fired here.

State: s['journey']['abandon'] (created lazily; optional in older saves).
"""
from __future__ import annotations

import hashlib

from . import archive as ar
from . import compensation as cf

VERSION = 1
TRUST_START = 70          # "Điểm tin cậy của chủ" of a new employer
TRUST_CLEAN_DAY = 2       # won back by a day closed without walking off
LOG_KEPT = 12
HELD_KEPT = 20            # long commitments already charged for (a guest's room, an order with a deposit)
DONE = ('completed', 'referred', 'cancelled')
STARTED_STATUS = ('in_progress', 'proposed', 'executing', 'awaiting_confirmation', 'handed_over')
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting')

# Fine: per started job a quarter of its value (5..30 xu), 3 xu per waiting customer
# (at most 15), at least 5 xu; times the offence number today (1, 2, 3 at most); at most 120 xu. Then the
# tiền đền factor (game/compensation.py): what is charged and shown is comp(fine), e.g. 4..96 xu at 0.8.
FINE_MIN, FINE_JOB_MIN, FINE_JOB_MAX, FINE_WAIT, FINE_WAIT_MAX, FINE_MAX = 5, 5, 30, 3, 15, 120
# Trust: 2 + 4 per started job + 1 per two waiting customers (at most 10), times the offence number; at most 25.
TRUST_BASE, TRUST_JOB, TRUST_ONE_MAX, TRUST_MAX = 2, 4, 10, 25
VALUE_DEFAULT = 30

WHERE = dict(corp_accounting='bàn', tax_payroll='bàn', group_accounting='bàn', teacher='lớp', tour_guide='đoàn',
             delivery='đơn', accounting='bàn', customer_care='bàn')

BOSS_LINES = {
    1: ['Đi đâu mà bỏ {where} vậy em? Khách chờ rồi bỏ về hết.',
        'Việc đang làm dở mà em đi đâu vậy? Người ta phải xin lỗi khách thay em đó.',
        'Nhận việc rồi thì làm cho xong đã em. Bỏ ngang vậy khách buồn lắm.'],
    2: ['Lần thứ hai trong ngày rồi đó em. Lần sau còn bỏ ngang là cho nghỉ luôn.',
        'Hôm nay em bỏ {where} hai lần rồi. Lần sau còn vậy là cho nghỉ đó nha.'],
    3: ['Nhắc lần cuối: còn bỏ ngang nữa là cho nghỉ thật đó em.',
        'Nói mấy lần rồi. Còn bỏ {where} nữa là cho nghỉ luôn nha em.'],
}
OWNER_LINES = {
    1: ['Quán mở cửa mà không ai đứng {where}, khách chờ rồi về hết đó con.',
        'Đi đâu mà bỏ {where} vậy con? Khách đứng chờ mãi rồi bỏ đi.',
        'Mở cửa rồi bỏ đi đâu mất, khách hỏi cô mà cô không biết trả lời sao.'],
    2: ['Hôm nay bỏ {where} hai lần rồi đó con. Khách quen bắt đầu kháo nhau rồi.',
        'Lại bỏ {where} nữa hả con? Cứ vầy là mất khách quen đó.'],
    3: ['Bỏ {where} hoài vậy thì ai dám ghé nữa con ơi.',
        'Cả xóm thấy quán mở mà không có ai rồi đó con. Coi chừng mất khách luôn.'],
}
REVIEW_LINES = [
    'Đang làm dở cho mình thì bỏ đi đâu mất, chờ mãi không thấy quay lại.',
    'Nhận việc của mình rồi bỏ ngang, mình đành đi chỗ khác.',
    'Làm được nửa chừng rồi biến mất, không ai nói với mình một câu.',
    'Đứng chờ mà người làm cho mình bỏ đi luôn. Không quay lại nữa.',
]
HANDOVER_LINES = [
    'Việc của mình đang làm dở thì bị bỏ ngang, phải chờ người khác làm lại từ đầu.',
    'Đang làm cho mình thì bỏ đi mất, mình phải nhờ người khác. Mất cả buổi.',
]
TRUST_NAMES = dict(office='điểm tin cậy của sếp', employer='điểm tin cậy của chủ', street='điểm uy tín với khu phố')


def _eng():
    from . import engine
    return engine


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _pick(rows: list, *parts) -> str:
    return rows[_hash(*parts) % len(rows)]


def _employed(cid: str) -> bool:
    from . import employment
    return employment.required(cid)


def _place(cid: str) -> str:
    from .content import CAREER_META
    return CAREER_META.get(cid, {}).get('place', cid)


# ---------------------------------------------------------------- state
def _new() -> dict:
    return dict(v=VERSION, places={})


def book(s: dict) -> dict:
    """The abandonment book (created for saves made before it existed)."""
    j = s['journey']
    b = j.get('abandon')
    if not isinstance(b, dict):
        b = j['abandon'] = _new()
    return b


def _place_row(b: dict, cid: str) -> dict:
    row = b['places'].get(cid)
    if not isinstance(row, dict):
        row = b['places'][cid] = dict(trust=TRUST_START, day=0, today=0, total=0, log=[], held=[])
    row.setdefault('held', [])
    return row


# ---------------------------------------------------------------- what is in progress
def started(t: dict) -> bool:
    """At least one work step was taken on this job (or an order was promised)."""
    if t.get('status') in DONE:
        return False
    if t.get('status') in STARTED_STATUS:
        return True
    if isinstance(t.get('basket'), dict) and t['basket']:
        return True
    cup = t.get('cup')
    if isinstance(cup, dict) and (cup.get('items') or cup.get('placed')):
        return True
    if t.get('desk') and (t.get('marks') or t.get('found') or t.get('partial') or t.get('count') is not None or t.get('reply')):
        return True
    ps = t.get('proc_state')
    if isinstance(ps, dict) and ps.get('at', 0):
        return True
    if t.get('career') in ('teacher', 'tour_guide') and (t.get('stage') not in (None, 'plan') or t.get('plan') or t.get('route')):
        return True
    bulk = t.get('bulk')
    if isinstance(bulk, dict) and bulk.get('stage') == 'deliver':  # deposit taken: an order promised for today
        return True
    return False


def _value(t: dict) -> int:
    n = t.get('needs') if isinstance(t.get('needs'), dict) else {}
    for v in (t.get('quoted_price'), n.get('budget'), n.get('value'), t.get('_value'), t.get('budget')):
        if type(v) is int and v > 0:
            return max(10, min(200, v))
    return VALUE_DEFAULT


def kept(c: dict, t: dict) -> bool:
    """A commitment that does not walk out: a guest already in a room, an order with a deposit.
    It still counts as work in progress (charged once), but stays for its own career rules."""
    if t.get('career') == 'homestay' and t.get('room'):
        rooms = (c.get('ext', {}).get('data') or {}).get('rooms') or {}
        if (rooms.get(t['room']) or {}).get('task') == t['id']:
            return True
    bulk = t.get('bulk')
    return isinstance(bulk, dict) and bulk.get('stage') == 'deliver'


def _held(s: dict, cid: str) -> list:
    b = (s.get('journey') or {}).get('abandon')
    row = (b or {}).get('places', {}).get(cid) if isinstance(b, dict) else None
    return row.get('held', []) if isinstance(row, dict) else []


def _work(s: dict, cid: str) -> tuple[list, list]:
    """(started jobs, waiting customers) of a workplace whose day is open. Waiting means
    today's customers not served yet; jobs carried from earlier days are commitments, not a queue."""
    c = s['careers'][cid]
    if not c.get('open'):
        return [], []
    held = set(_held(s, cid))
    live = [t for t in c.get('tasks', []) if isinstance(t, dict) and t.get('status') not in DONE and t.get('id') not in held]
    jobs = [t for t in live if started(t)]
    waiting = [t for t in live if not started(t) and t.get('day') == c['day'] and not kept(c, t)]
    return jobs, waiting


def _kind(cid: str, c: dict) -> str:
    if cid in OFFICE and isinstance((c.get('ext', {}).get('data') or {}).get('office'), dict):
        return 'office'
    if _employed(cid):
        return 'employer'
    box = c.get('incidents')
    if isinstance(box, dict) and type(box.get('trust')) is int:
        return 'street'
    return 'employer'


def trust_value(s: dict, cid: str) -> int:
    c = s['careers'][cid]
    kind = _kind(cid, c)
    if kind == 'office':
        return c['ext']['data']['office']['trust']
    if kind == 'street':
        return c['incidents']['trust']
    b = (s.get('journey') or {}).get('abandon')
    row = (b or {}).get('places', {}).get(cid) if isinstance(b, dict) else None
    return row['trust'] if isinstance(row, dict) else TRUST_START


def assess(s: dict, cid: str) -> dict | None:
    """What leaving `cid` right now would cost (None: nothing in progress).
    The confirm dialog shows exactly these numbers; check() applies them."""
    if cid not in s.get('careers', {}):
        return None
    c = s['careers'][cid]
    jobs, waiting = _work(s, cid)
    if not jobs and not waiting:
        return None
    b = (s.get('journey') or {}).get('abandon')
    row = (b or {}).get('places', {}).get(cid) if isinstance(b, dict) else None
    today = row['today'] if isinstance(row, dict) and row.get('day') == c['day'] else 0
    n = min(3, today + 1)
    job_fine = sum(max(FINE_JOB_MIN, min(FINE_JOB_MAX, _value(t) // 4)) for t in jobs)
    fine = cf.comp(min(FINE_MAX, max(FINE_MIN, job_fine + min(FINE_WAIT_MAX, FINE_WAIT * len(waiting))) * n))
    trust = min(TRUST_MAX, min(TRUST_ONE_MAX, TRUST_BASE + TRUST_JOB * len(jobs) + len(waiting) // 2) * n)
    kind = _kind(cid, c)
    story = bool((s.get('journey') or {}).get('story'))
    return dict(career=cid, place=_place(cid), task=(jobs[0]['title'] if jobs else waiting[0]['title'])[:120],
                started=len(jobs), waiting=len(waiting), leaving=len(waiting) + sum(1 for t in jobs if not kept(c, t)),
                fine=fine if story else 0, trust=trust if story else 0,
                trust_kind=kind, trust_name=TRUST_NAMES[kind], trust_now=trust_value(s, cid),
                pocket='wallet' if _employed(cid) else 'fund', offence=n, warn=n >= 2, soft=not story)


def _what(x: dict) -> str:
    return f'Đang làm dở: {x["task"]}.' if x['started'] else f'{x["place"]} đang mở, {x["waiting"]} khách đang chờ.'


def message(x: dict) -> str:
    """The confirm line, in one place for the server refusal and the client dialog."""
    return f'{_what(x)} Bỏ đi bây giờ: phạt {x["fine"]} xu, mất {x["trust"]} {x["trust_name"]}, khách đang chờ sẽ bỏ về.'


# ---------------------------------------------------------------- the switch
def check(s: dict, target: str, p: dict, internal: bool = False) -> dict | None:
    """Engine hook, before s['current'] moves to `target`. Returns what happened
    (for result['abandon']) or None. Raises when confirmation is still needed."""
    e = _eng()
    cur = s.get('current')
    if internal or not cur or cur == target or cur not in s.get('careers', {}):
        return None
    x = assess(s, cur)
    if not x:
        return None
    if x['soft']:
        # Free sandbox (no story): nothing is charged; the work simply waits.
        return dict(soft=True, career=cur, place=x['place'], task=x['task'],
                    text=f'Việc ở {x["place"]} vẫn đang dở: {x["task"]}. Quay lại làm nốt nhé.')
    e.need(p.get('confirm') is True, message(x) + ' Chọn “Vẫn đi” nếu bạn chắc chắn.', 'abandon_confirm')
    return _apply(s, cur, x)


def _apply(s: dict, cid: str, x: dict) -> dict:
    e = _eng()
    c = s['careers'][cid]
    b = book(s)
    row = _place_row(b, cid)
    if row['day'] != c['day']:
        row['day'], row['today'] = c['day'], 0
    row['today'] += 1
    row['total'] += 1
    n = x['offence']
    ref = f'abandon-{c["day"]}-{row["today"]}'
    # Money: an owner refunds the waiting customers from the fund; an employee's pay is docked.
    fund = wallet = 0
    fine = x['fine']
    j = s['journey']
    if x['pocket'] == 'fund':
        fund = min(fine, c['money'])
        wallet = min(fine - fund, max(0, j['wallet']))
    else:
        wallet = min(fine, max(0, j['wallet']))
        fund = min(fine - wallet, c['money'])
    if fund:
        e.money(s, c, -fund, 'Bỏ dở việc' + (' · hoàn tiền khách chờ' if x['pocket'] == 'fund' else ' · trừ lương'), ref, 'abandon_fine')
    if wallet:
        from . import journey as jr
        jr._wallet(j, -wallet, 'incident', f'Bỏ dở việc · trừ lương · {x["place"]}'[:120], cid)
    paid = fund + wallet
    # Trust.
    before = trust_value(s, cid)
    kind = x['trust_kind']
    if kind == 'office':
        from .careers import office
        o = c['ext']['data']['office']
        office.trust(o, -x['trust'])
        office.note(o, c['day'], f'Bỏ dở việc giữa chừng (lần {row["today"]} hôm nay).', 'bad')
    elif kind == 'street':
        c['incidents']['trust'] = max(0, c['incidents']['trust'] - x['trust'])
    else:
        row['trust'] = max(0, row['trust'] - x['trust'])
    after = trust_value(s, cid)
    # The jobs: started ones are cancelled with an annoyed review, waiting customers walk out.
    jobs, waiting = _work(s, cid)
    employee = _employed(cid)
    from .feedback import persona_for
    from . import feedback_voices as fv
    gone = 0
    for t in jobs:
        if kept(c, t):
            row['held'] = (row['held'] + [t['id']])[-HELD_KEPT:]
            continue
        _cancel(s, c, t)
        gone += 1
        persona = persona_for(cid, t['npc'])
        stars = 1 if persona in fv.HARSHP or _hash('abandon-star', t['id']) % 3 == 0 else 2
        opener = ((fv.MORE_VOICE.get(persona) or {}).get('open') or {}).get(stars) or ['']
        body = _pick(HANDOVER_LINES if employee else REVIEW_LINES, 'abandon-review', t['id'])
        text = (_pick(opener, 'abandon-open', t['id']) + ' ' + body).strip()
        e.add_feed(s, c, t['npc'], text, t['id'], stars, 'review')
        e.metric(c, 'reviews_' + str(stars))
        e.log(s, c, 'walkout', f'Bỏ dở “{t["title"]}”: khách không chờ nữa.'[:300], t['npc'], t['id'])
    for t in waiting:
        _cancel(s, c, t)
    if waiting:
        e.log(s, c, 'walkout', f'{len(waiting)} khách đang chờ đã bỏ về.' if not employee else f'{len(waiting)} việc đang chờ được giao lại cho người khác.')
    e.metric(c, 'abandoned')
    e.next_active(c)
    # One line from the boss (or a neighbour for a place you own).
    who, line = _speaker(cid, c, n, ref)
    e.log(s, c, 'abandon', f'{who} nhắn: “{line}”'[:400])
    rec = dict(day=c['day'], fine=paid, trust=before - after, walked=len(waiting), jobs=gone, warn=n >= 2)
    row['log'] = ar.last(row['log'] + [rec], LOG_KEPT, 'abandon.log', cid)
    return dict(career=cid, place=x['place'], task=x['task'], fine=paid, fund=fund, wallet=wallet, pocket=x['pocket'],
                trust=before - after, trust_after=after, trust_name=x['trust_name'], trust_kind=kind,
                walked=len(waiting), jobs=gone, offence=n, warn=n >= 2, who=who, line=line,
                label='Bỏ dở việc', text=f'{who}: “{line}”')


def _cancel(s: dict, c: dict, t: dict) -> None:
    from .careers import PLUGINS
    mod = PLUGINS.get(t['career'])
    if mod and hasattr(mod, 'on_abandon'):
        mod.on_abandon(s, c, t)  # a career may tidy its own job state first
    run = t.get('run')
    if t['career'] == 'delivery' and isinstance(run, dict):
        run.update(outcome='failed', kept=[], missed=[])  # the parcel goes back to the depot
    t['status'] = 'cancelled'
    t['completed_turn'] = c['turn']
    t['deferred'] = False
    _eng().mark_done(c, t['id'])


def _speaker(cid: str, c: dict, n: int, ref: str) -> tuple[str, str]:
    where = WHERE.get(cid, 'quầy')
    if _employed(cid):
        from . import employment as emp
        job = c.get('job') or {}
        rows = emp.postings(cid)
        post = next((r for r in rows if r['id'] == job.get('employer')), rows[0] if rows else {})
        who = 'Trưởng phòng' if cid in OFFICE else emp._cap(emp._boss(cid, post)) if post else 'Chủ'
        lines = BOSS_LINES
    else:
        who, lines = 'Cô Sáu hàng xóm', OWNER_LINES
    return who, _pick(lines[min(3, n)], 'abandon-line', cid, ref).format(where=where)


# ---------------------------------------------------------------- day end
def on_close(s: dict, c: dict, career: str, day: int) -> dict | None:
    """Engine hook at end_day: today's abandonments for the summary; a clean day wins back trust."""
    b = (s.get('journey') or {}).get('abandon')
    row = (b or {}).get('places', {}).get(career) if isinstance(b, dict) else None
    if not isinstance(row, dict):
        return None
    today = [r for r in row['log'] if r['day'] == day]
    if not today:
        if _kind(career, c) == 'employer' and row['trust'] < 100:
            row['trust'] = min(100, row['trust'] + TRUST_CLEAN_DAY)
        return None
    return dict(count=len(today), fine=sum(r['fine'] for r in today), trust=sum(r['trust'] for r in today),
                walked=sum(r['walked'] for r in today), jobs=sum(r['jobs'] for r in today),
                warn=any(r['warn'] for r in today), trust_name=TRUST_NAMES[_kind(career, c)], trust_now=trust_value(s, career),
                pocket='wallet' if _employed(career) else 'fund')


# ---------------------------------------------------------------- client view
def public(s: dict) -> dict:
    cur = s.get('current')
    x = assess(s, cur) if cur else None
    if x:
        x = dict(x, text=message(x), what=_what(x))
    trust = {}
    for cid, c in s.get('careers', {}).items():
        if c.get('started') and _kind(cid, c) == 'employer':
            trust[cid] = trust_value(s, cid)
    return dict(preview=x, trust=trust)


# ---------------------------------------------------------------- saves
def validate(s: dict) -> None:
    e = _eng()
    need, integer = e.need, e.integer
    b = (s.get('journey') or {}).get('abandon')
    if b is None:
        return
    need(isinstance(b, dict) and b.get('v') == VERSION and set(b) == {'v', 'places'}, 'Sổ bỏ dở việc sai.', 'invalid_save')
    need(isinstance(b['places'], dict) and set(b['places']) <= set(s['careers']), 'Sổ bỏ dở việc sai nơi làm.', 'invalid_save')
    for row in b['places'].values():
        need(isinstance(row, dict) and set(row) == {'trust', 'day', 'today', 'total', 'log', 'held'}, 'Sổ bỏ dở việc sai.', 'invalid_save')
        need(isinstance(row['held'], list) and len(row['held']) <= HELD_KEPT and all(isinstance(x, str) and 0 < len(x) <= 60 for x in row['held']),
             'Sổ bỏ dở việc sai.', 'invalid_save')
        integer(row['trust'], 0, 100)
        integer(row['day'], 0, 10 ** 7)
        integer(row['today'], 0, 10 ** 6)
        integer(row['total'], 0, 10 ** 9)
        need(row['today'] <= row['total'], 'Sổ bỏ dở việc sai.', 'invalid_save')
        need(isinstance(row['log'], list) and len(row['log']) <= LOG_KEPT, 'Sổ bỏ dở việc sai.', 'invalid_save')
        for r in row['log']:
            need(isinstance(r, dict) and set(r) == {'day', 'fine', 'trust', 'walked', 'jobs', 'warn'} and type(r['warn']) is bool,
                 'Dòng bỏ dở việc sai.', 'invalid_save')
            integer(r['day'], 1, 10 ** 7)
            integer(r['fine'], 0, FINE_MAX)
            integer(r['trust'], 0, 100)
            integer(r['walked'], 0, 100)
            integer(r['jobs'], 0, 100)
