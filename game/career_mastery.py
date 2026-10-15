"""Prospective career mastery: manual work, judgment reviews and flat daily rewards.

The engine owns completion and payment. This module never changes funds, XP,
contracts, promotion ranks or organization rights. Old saves need no migration.
"""
from __future__ import annotations

import copy
import hashlib
import random

from . import promotion_content as PC

STEPS = (
    dict(clean=40, days=15, level=20, bonus=6, title='Tay nghề đáng tin', badge='🥉'),
    dict(clean=120, days=40, level=45, bonus=12, title='Chuyên gia thực hành', badge='🥈'),
    dict(clean=260, days=75, level=90, bonus=20, title='Bậc thầy nghề nghiệp', badge='🥇'),
)
MAX = 10**6
DAY_MAX = 10000
KEYS = {'v', 'tier', 'start', 'clean', 'completed', 'qualified_days', 'last_closed',
        'today', 'attempts', 'retry_at', 'exam', 'last_result', 'awards', 'paid_days'}
PAPER_KEYS = {'tier', 'attempt', 'day', 'clean', 'qualified_days', 'level', 'questions', 'answers'}


def _need(ok, message='Dữ liệu thành thạo nghề không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _int(value, low=0, high=MAX):
    _need(type(value) is int and low <= value <= high)
    return value


def _initial(day):
    return dict(v=1, tier=0, start=day, clean=0, completed=0, qualified_days=0,
                last_closed=day - 1, today=dict(day=day, jobs=[]), attempts=0,
                retry_at=0, exam=None, last_result=None, awards=[], paid_days=[0, 0, 0])


def _record(c):
    return c.get('mastery') or _initial(c['day'])


def _level(c):
    return 1 + c['xp'] // 90


def _group(career):
    # Public-service mastery must not ask the shared service bank's discount or
    # sales questions. The office bank tests evidence, honesty and teamwork.
    if career in ('police', 'customs', 'nurse', 'library', 'pagoda', 'teacher'):
        return 'office'
    return next((group for group, ids in PC.GROUP.items() if career in ids), 'trade')


def _paper(career, paper):
    """Regenerate the immutable paper; only question IDs and answers are saved."""
    seed = '|'.join(str(x) for x in (career, paper['tier'], paper['attempt'], paper['day']))
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    rows = copy.deepcopy(rng.sample(PC.QUESTIONS[_group(career)], 4))
    for row in rows:
        rng.shuffle(row['options'])
        for i, option in enumerate(row['options']):
            option['id'] = chr(97 + i)
    return rows


def _score(career, paper):
    rows = _paper(career, paper)
    return sum(next(o['score'] for o in row['options'] if o['id'] == answer)
               for row, answer in zip(rows, paper['answers']))


def _requirements(c, record):
    if record['tier'] >= len(STEPS):
        return []
    step = STEPS[record['tier']]
    return [dict(id=key, label=label, got=got, need=need, met=got >= need)
            for key, label, got, need in (
                ('clean', 'Việc tự làm không sai', record['clean'], step['clean']),
                ('days', 'Ngày làm việc đạt chuẩn', record['qualified_days'], step['days']),
                ('level', 'Cấp kinh nghiệm nghề', _level(c), step['level']))]


def completed(c, career, task):
    """Authoritative task_done hook, after served/XP and completed_ids are updated.

    Old-day work, referrals, cancellations and external player orders are not
    generated manual work for this track. Staff and manager jobs never call it.
    """
    if (not c.get('open') or task.get('status') != 'completed' or task.get('career') != career
            or task.get('day') != c['day'] or task.get('player_order')
            or task.get('id') not in c.get('completed_ids', ())
            or not any(t is task for t in c.get('tasks', ()))):
        return False
    record = _record(c)
    if record['last_closed'] >= c['day']:
        return False
    today = record['today'] if record['today']['day'] == c['day'] else dict(day=c['day'], jobs=[])
    if any(j['id'] == task['id'] for j in today['jobs']):
        return False
    _need(len(today['jobs']) < DAY_MAX and record['completed'] < MAX)
    clean = type(task.get('mistakes')) is int and task['mistakes'] == 0
    today['jobs'].append(dict(id=task['id'], clean=clean))
    record['today'] = today
    record['completed'] += 1
    record['clean'] += int(clean)
    c['mastery'] = record
    return True


def close(c, career, allow_reward):
    """Close once before engine increments career day. Caller pays returned bonus."""
    _need(type(allow_reward) is bool)
    record = c.get('mastery')
    empty = dict(bonus=0, qualified=False, clean=0, completed=0)
    if not record or not c.get('open') or record['last_closed'] >= c['day']:
        return empty
    jobs = record['today']['jobs'] if record['today']['day'] == c['day'] else []
    clean = sum(j['clean'] for j in jobs)
    qualified = clean >= 3 and clean * 100 >= len(jobs) * 80
    bonus = STEPS[record['tier'] - 1]['bonus'] if qualified and allow_reward and record['tier'] else 0
    record['qualified_days'] += int(qualified)
    record['last_closed'] = c['day']
    if bonus:
        record['paid_days'][record['tier'] - 1] += 1
    return dict(bonus=bonus, qualified=qualified, clean=clean, completed=len(jobs),
                title=STEPS[record['tier'] - 1]['title'] if record['tier'] else 'Đang rèn nghề')


def action(c, career, name, payload):
    _need(isinstance(payload, dict), 'Thao tác thành thạo nghề không hợp lệ.')
    _need(name in ('mastery_start', 'mastery_answer', 'mastery_finish'), 'Thao tác thành thạo nghề không hợp lệ.')
    _need(set(payload) == ({'option'} if name == 'mastery_answer' else set()), 'Thao tác thành thạo nghề không hợp lệ.')
    record = _record(c)
    if name == 'mastery_start':
        _need(record['exam'] is None, 'Bạn đang có một bài đánh giá chưa hoàn tất.')
        _need(record['tier'] < len(STEPS), 'Bạn đã hoàn thành cả ba bậc thành thạo nghề.')
        _need(record['qualified_days'] >= record['retry_at'], 'Cần thêm ngày làm việc đạt chuẩn trước khi đánh giá lại.')
        _need(all(r['met'] for r in _requirements(c, record)), 'Chưa đủ việc sạch, ngày đạt chuẩn hoặc cấp kinh nghiệm.')
        _need(record['attempts'] < MAX)
        paper = dict(tier=record['tier'] + 1, attempt=record['attempts'] + 1,
                     day=c['day'], clean=record['clean'], qualified_days=record['qualified_days'],
                     level=_level(c), questions=[], answers=[])
        paper['questions'] = [q['id'] for q in _paper(career, paper)]
        record['attempts'] += 1
        record['exam'] = paper
        c['mastery'] = record
        return dict(message='Bắt đầu bốn tình huống đánh giá tay nghề.')
    paper = record['exam']
    _need(paper is not None, 'Chưa có bài đánh giá tay nghề đang mở.')
    if name == 'mastery_answer':
        index = len(paper['answers'])
        _need(index < 4, 'Bạn đã trả lời đủ bốn tình huống.')
        option = payload['option']
        _need(type(option) is str and option in [o['id'] for o in _paper(career, paper)[index]['options']],
              'Lựa chọn đánh giá không hợp lệ.')
        paper['answers'].append(option)
        return dict(message='Đã ghi nhận lựa chọn của bạn.')
    _need(len(paper['answers']) == 4, 'Hãy trả lời đủ bốn tình huống trước khi nộp bài.')
    score = _score(career, paper)
    passed = score >= 7
    result = dict(copy.deepcopy(paper), score=score, passed=passed,
                  finished_day=c['day'], finished_qualified_days=record['qualified_days'])
    if passed:
        record['tier'] += 1
        record['awards'].append(copy.deepcopy(result))
        record['retry_at'] = 0
    else:
        record['retry_at'] = record['qualified_days'] + 3
    record['last_result'] = result
    record['exam'] = None
    return dict(message=('Đạt đánh giá tay nghề. Danh hiệu mới đã được ghi nhận.' if passed else
                         'Chưa đạt 7/8 điểm. Làm thêm ba ngày đạt chuẩn rồi thử lại nhé.'),
                passed=passed, score=score, total=8)


def today_line(c, record):
    """Owner 14/10: today's live line. The career day is booked when the player closes the shift (Khép ca)."""
    if record['last_closed'] >= c['day']:
        return 'Hôm nay đã khép ca, ngày nghề sau tính tiếp'
    jobs = record['today']['jobs'] if record['today']['day'] == c['day'] else []
    clean, total = sum(j['clean'] for j in jobs), len(jobs)
    head = f'Hôm nay: {clean}/{total} việc sạch'
    left = max(0, 3 - clean, 4 * total - 5 * clean)   # clean+k ≥ 3 and clean+k ≥ 80% of total+k
    if left:
        return f'{head} · còn {left} việc sạch nữa là ngày đạt chuẩn'
    return f'{head} · đã đạt, khép ca là tính ✓'


def public(c, career):
    record = _record(c)
    tier = record['tier']
    step = STEPS[tier - 1] if tier else None
    jobs = record['today']['jobs'] if record['today']['day'] == c['day'] else []
    clean = sum(j['clean'] for j in jobs)
    requirements = _requirements(c, record)
    line = today_line(c, record)
    for row in requirements:
        if row['id'] == 'days' and not row['met']:
            row['hint'] = line
    retry = max(0, record['retry_at'] - record['qualified_days'])
    exam = None
    if record['exam']:
        paper = record['exam']
        i = len(paper['answers'])
        q = _paper(career, paper)[i] if i < 4 else None
        exam = dict(index=i, total=4, complete=i == 4,
                    question=(dict(id=q['id'], text=q['text'],
                                   options=[dict(id=o['id'], label=o['label']) for o in q['options']]) if q else None))
    result = record['last_result']
    return dict(tier=tier, title=step['title'] if step else 'Đang rèn nghề', badge=step['badge'] if step else '🌱',
                bonus=step['bonus'] if step else 0, clean=record['clean'], qualified_days=record['qualified_days'],
                today=dict(completed=len(jobs), clean=clean, qualified=clean >= 3 and clean * 100 >= len(jobs) * 80,
                           line=line),
                next=(dict(tier=tier + 1, title=STEPS[tier]['title'], bonus=STEPS[tier]['bonus'],
                           requirements=requirements) if tier < len(STEPS) else None),
                ready=tier < len(STEPS) and all(r['met'] for r in requirements) and not retry and exam is None,
                retry_good_days=retry, exam=exam,
                last_result=(dict(passed=result['passed'], score=result['score'], total=8,
                                  message='Đã đạt đánh giá tay nghề.' if result['passed'] else
                                          'Cần thêm ba ngày đạt chuẩn để đánh giá lại.') if result else None))


def _validate_paper(c, career, record, paper, result=False):
    _need(isinstance(paper, dict) and set(paper) == PAPER_KEYS |
          ({'score', 'passed', 'finished_day', 'finished_qualified_days'} if result else set()))
    tier = _int(paper['tier'], 1, 3)
    _int(paper['attempt'], 1, record['attempts'])
    _int(paper['day'], record['start'], c['day'])
    st = STEPS[tier - 1]
    _int(paper['clean'], st['clean'], record['clean'])
    _int(paper['qualified_days'], st['days'], record['qualified_days'])
    _int(paper['level'], st['level'], _level(c))
    rows = _paper(career, paper)
    _need(paper['questions'] == [r['id'] for r in rows])
    answers = paper['answers']
    _need(isinstance(answers, list) and len(answers) <= 4)
    for row, answer in zip(rows, answers):
        _need(type(answer) is str and answer in [o['id'] for o in row['options']])
    if result:
        _need(len(answers) == 4)
        _int(paper['finished_day'], paper['day'], c['day'])
        _int(paper['finished_qualified_days'], paper['qualified_days'], record['qualified_days'])
        _int(paper['score'], 0, 8)
        _need(paper['score'] == _score(career, paper))
        _need(type(paper['passed']) is bool and paper['passed'] == (paper['score'] >= 7))


def validate(c, career):
    if 'mastery' not in c:
        return
    r = c['mastery']
    _need(isinstance(r, dict) and set(r) == KEYS)
    _int(r['v'], 1, 1)
    _int(r['tier'], 0, 3)
    _int(r['start'], 1, c['day'])
    _int(r['last_closed'], r['start'] - 1, c['day'])
    _int(r['completed'], 0, min(MAX, c.get('metrics', {}).get('served', 0)))
    _int(r['clean'], 0, r['completed'])
    _int(r['qualified_days'], 0, min(r['clean'] // 3, r['last_closed'] - r['start'] + 1))
    _int(r['attempts'], 0, min(MAX, 4 + r['qualified_days'] // 3))
    _int(r['retry_at'], 0, min(MAX, r['qualified_days'] + 3))
    today = r['today']
    _need(isinstance(today, dict) and set(today) == {'day', 'jobs'})
    _int(today['day'], r['start'], c['day'])
    jobs = today['jobs']
    _need(isinstance(jobs, list) and len(jobs) <= min(DAY_MAX, r['completed']))
    ids = []
    for job in jobs:
        _need(isinstance(job, dict) and set(job) == {'id', 'clean'})
        tid = job['id']
        _need(type(tid) is str and len(tid) <= 150 and tid.startswith(f'{career}-{today["day"]:04d}-'))
        _need(type(job['clean']) is bool)
        ids.append(tid)
        task = next((t for t in c.get('tasks', ()) if t.get('id') == tid), None)
        if task:
            _need(task.get('status') == 'completed' and task.get('career') == career
                  and task.get('day') == today['day'] and job['clean'] == (task.get('mistakes') == 0))
    _need(len(ids) == len(set(ids)) and sum(j['clean'] for j in jobs) <= r['clean'])
    _need(sum(not j['clean'] for j in jobs) <= r['completed'] - r['clean'])
    awards = r['awards']
    _need(isinstance(awards, list) and len(awards) == r['tier'])
    previous_attempt = 0
    for i, award in enumerate(awards):
        _validate_paper(c, career, r, award, True)
        _need(award['passed'] and award['tier'] == i + 1 and award['attempt'] > previous_attempt)
        previous_attempt = award['attempt']
    paid = r['paid_days']
    _need(isinstance(paid, list) and len(paid) == 3)
    for i, count in enumerate(paid):
        _int(count, 0, r['qualified_days'] - awards[i]['finished_qualified_days'] if i < len(awards) else 0)
    _need(sum(paid) <= r['qualified_days'])
    last = r['last_result']
    if last is not None:
        _validate_paper(c, career, r, last, True)
        _need(last['tier'] == r['tier'] if last['passed'] else last['tier'] == r['tier'] + 1)
        if last['passed']:
            _need(last == awards[-1] and r['retry_at'] == 0)
        else:
            _need(last['attempt'] > previous_attempt)
            _need(r['retry_at'] == last['finished_qualified_days'] + 3)
    else:
        _need(not awards and r['retry_at'] == 0)
    exam = r['exam']
    if exam is not None:
        _validate_paper(c, career, r, exam)
        _need(exam['tier'] == r['tier'] + 1 and exam['attempt'] == r['attempts']
              and exam['qualified_days'] >= r['retry_at']
              and exam['attempt'] == (last['attempt'] + 1 if last else 1))
    _need(r['attempts'] == (exam['attempt'] if exam else last['attempt'] if last else 0))
