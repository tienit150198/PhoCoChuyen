"""Prospective NPC competition. The engine alone owns money and spirit payments.

Every recorded period contains its ten daily witnesses. Aggregates, peers, cases,
league changes and awards are reproducible when validating a loaded save.
"""
from __future__ import annotations

import copy
import hashlib

from . import promotion as pm
from .career_competition_content import PROFILES

LEAGUES = ('Tập sự thi đua', 'Đồng nghiệp tin cậy', 'Tổ nghề vững vàng', 'Gương sáng nghề nghiệp', 'Dẫn dắt nghề nghiệp')
CAPS = (300, 900, 2000, 5000, 10000)
GOOD = (2, 3, 4, 6)
RANKS = (2, 3, 5, 7)
SPIRIT_CAP = 5
MAX = 10**9
DAY_MAX = 10000
HISTORY_MAX = 24
JUDGMENT = frozenset(('judgment', 'judgement', 'decision', 'reasoning', 'diagnosis', 'resolution', 'ethics', 'triage', 'priority'))
LABELS = dict(quality='Chất lượng thực tế', procedure='Quy trình ít sai sót', judgment='Phán đoán có chứng cứ', teamwork='Phối hợp cùng đồng nghiệp')
WEIGHTS = dict(quality=50, procedure=25, judgment=15, teamwork=10)


def _need(ok, message='Dữ liệu thi đua nghề không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _int(value, low=0, high=MAX):
    _need(type(value) is int and low <= value <= high)
    return value


def _hash(*values):
    return int(hashlib.sha256('|'.join(map(str, values)).encode()).hexdigest(), 16)


def _initial(day):
    return dict(v=1, start=day, last_closed=day - 1, league=0, good=0,
                days=[], history=[], today=dict(day=day, jobs=[], case=None),
                archive=dict(periods=0, last_day=day - 1, league=0, good=0, completed=0, promotions=[]))


def _number(r):
    return r['archive']['periods'] + len(r['history']) + 1


def _rank_need(career, league):
    return min(RANKS[league], pm.top(career))


def _advance(career, league, good, result):
    good += int(result['good'])
    if league < 4 and good >= GOOD[league] and result['promotion_rank'] >= _rank_need(career, league):
        return league + 1, 0
    return league, good


def _compact(r, career):
    if len(r['history']) <= HISTORY_MAX:
        return
    row = r['history'].pop(0)
    archive = r['archive']
    league, good = _advance(career, archive['league'], archive['good'], row)
    if league > archive['league']:
        archive['promotions'].append(dict(period=row['period'], good=archive['good'] + int(row['good']), rank=row['promotion_rank']))
    archive.update(periods=row['period'], last_day=row['days'][-1]['day'], league=league, good=good,
                   completed=archive['completed'] + sum(d['completed'] for d in row['days']))


def _record(c):
    return c.get('competition') or _initial(c['day'])


def _today(c, r):
    return r['today'] if r['today']['day'] == c['day'] else dict(day=c['day'], jobs=[], case=None)


def _manual(task, career, day):
    return (task.get('career') == career and task.get('day') == day
            and not task.get('player_order') and not task.get('manager')
            and not any(task.get(k) in ('setup', 'brief') for k in ('kind', 'job', 'mode')))


def _accepted(task):
    return bool(task.get('known') or task.get('status') not in ('new', 'completed', 'referred', 'cancelled'))


def _npc(career, period, league, index):
    return [58 + league * 4 + _hash('competition-npc-v1', career, period, league, index, i) % 21 for i in range(3)]


def _scenario(career, day, period):
    return PROFILES[career]['scenarios'][_hash('competition-case-v1', career, day, period) % 3]


def _case_score(career, day, case):
    if not case or case['option'] is None:
        return None
    row = _scenario(career, day, case['period'])
    return next(o['score'] for o in row['options'] if o['id'] == case['option'])


def _components(jobs, failed, teamwork=None, abandoned=False):
    total = len(jobs) + failed
    if not total:
        return dict(quality=None, procedure=None, judgment=None, teamwork=None)
    rows = dict(quality=sum(j['quality'] for j in jobs) // total,
                procedure=sum(j['procedure'] for j in jobs) // total,
                judgment=None, teamwork=teamwork)
    applicable = [j['judgment'] for j in jobs if j['judgment'] is not None]
    if applicable:
        rows['judgment'] = sum(applicable) // (len(applicable) + failed)
    if abandoned:
        rows = {k: 0 if v is not None else None for k, v in rows.items()}
    return rows


def _score(components):
    rows = [(value, WEIGHTS[key]) for key, value in components.items() if value is not None]
    return sum(value * weight for value, weight in rows) // sum(weight for _, weight in rows) if rows else 0


def completed(c, career, task, feedback, income=0):
    """Only authoritative, successful manual completions can create a record."""
    if (career not in PROFILES or not c.get('open') or task.get('status') != 'completed'
            or not _manual(task, career, c['day'])
            or task.get('id') not in c.get('completed_ids', ())
            or not any(t is task for t in c.get('tasks', ()))):
        return False
    r = _record(c)
    if r['last_closed'] >= c['day']:
        return False
    today = _today(c, r)
    if any(j['id'] == task['id'] for j in today['jobs']):
        return False
    _need(isinstance(feedback, dict))
    fair = _int(feedback.get('fair'), 1, 5)
    mistakes = _int(task.get('mistakes'), 0)
    _int(income)
    _need(len(today['jobs']) < DAY_MAX)
    criteria = feedback.get('criteria', [])
    _need(isinstance(criteria, list))
    judgment = [_int(x['score'], 1, 5) * 25 - 25 for x in criteria if x.get('key') in JUDGMENT]
    today['jobs'].append(dict(id=task['id'], quality=(fair - 1) * 25,
                              procedure=max(0, 100 - 25 * mistakes),
                              judgment=sum(judgment) // len(judgment) if judgment else None, income=income))
    r['today'] = today
    c['competition'] = r
    return True


def _period_result(career, number, league, days, authorized, rank, spirit_room=0):
    score = sum(d['score'] for d in days) // 10
    totals = [sum(d['npc'][i] for d in days) for i in range(3)]
    player = sum(d['score'] for d in days)
    place = 1 + sum(n > player for n in totals)
    good = score >= 80 and place <= 2
    income = sum(d['income'] for d in days)
    bonus = min(CAPS[league], income // 10) if good and authorized and career != 'pagoda' else 0
    spirit = min(SPIRIT_CAP, spirit_room) if good and authorized and career == 'pagoda' else 0
    return dict(period=number, league=league, days=copy.deepcopy(days), score=score, rank=place,
                good=good, bonus=bonus, spirit=spirit, authorized=authorized, promotion_rank=rank, spirit_room=spirit_room)


def close(s, c, career, allow_reward=True, abandoned=False):
    """Consume this shift once, returning its flat award for engine settlement."""
    _need(type(allow_reward) is bool and type(abandoned) is bool)
    empty = dict(bonus=0, spirit=0, score=0, period=None)
    if not c.get('open') or career not in PROFILES:
        return empty
    r = c.get('competition')
    if r and r['last_closed'] >= c['day']:
        return empty
    today = _today(c, r or _initial(c['day']))
    ids = {j['id'] for j in today['jobs']}
    failed = sum(1 for t in c.get('tasks', ()) if _manual(t, career, c['day'])
                 and t.get('id') not in ids and t.get('status') not in ('completed', 'referred')
                 and _accepted(t))
    if not today['jobs'] and not failed:
        return empty
    # An accepted but abandoned job is evidence of a worked shift, even if no
    # completion has yet created this prospective record.
    r = r or _initial(c['day'])
    _need(len(r['days']) < 10)
    components = _components(today['jobs'], failed, _case_score(career, c['day'], today['case']), abandoned)
    number = _number(r)
    row = dict(day=c['day'], completed=len(today['jobs']), failed=failed,
               components=components, score=_score(components), abandoned=abandoned,
               income=sum(j['income'] for j in today['jobs']) if allow_reward and not abandoned else 0,
               npc=_npc(career, number, r['league'], len(r['days'])), case=copy.deepcopy(today['case']))
    r['today'] = today
    r['days'].append(row)
    r['last_closed'] = c['day']
    c['competition'] = r
    out = dict(empty, score=row['score'])
    if len(r['days']) == 10:
        current_spirit = (s.get('journey', {}).get('life') or {}).get('spirit')
        spirit_room = min(SPIRIT_CAP, 100 - current_spirit) if career == 'pagoda' and type(current_spirit) is int and 0 <= current_spirit <= 100 else 0
        result = _period_result(career, number, r['league'], r['days'], allow_reward, pm.rank(s, c, career), spirit_room)
        r['history'].append(result)
        r['league'], r['good'] = _advance(career, r['league'], r['good'], result)
        r['days'] = []
        _compact(r, career)
        out.update(bonus=result['bonus'], spirit=result['spirit'], period=_public_result(result))
    return out


def _public_result(row):
    return dict(**{k: row[k] for k in ('period', 'league', 'score', 'rank', 'good', 'bonus', 'spirit')},
                message='Được ghi nhận một kỳ thi đua tốt.' if row['good'] else 'Tiếp tục cải thiện chất lượng và phối hợp trong kỳ sau.')


def action(s, c, career, name, payload):
    _need(name in ('competition_start', 'competition_answer') and isinstance(payload, dict), 'Thao tác thi đua không hợp lệ.')
    _need(set(payload) == ({'option'} if name == 'competition_answer' else set()), 'Thao tác thi đua không hợp lệ.')
    r = c.get('competition')
    _need(r is not None and c.get('open') and r['last_closed'] < c['day'], 'Hãy hoàn thành công việc thực tế trong ca đang mở.')
    today = _today(c, r)
    _need(bool(today['jobs']), 'Hãy hoàn thành công việc thực tế trong ca đang mở.')
    if name == 'competition_start':
        rank = pm.rank(s, c, career)
        _need(rank >= 3 or r['league'] >= 1, 'Cần bậc nghề 3 hoặc liên đoàn thi đua 2 để xử lý tình huống nhóm.')
        _need(today['case'] is None, 'Mỗi ngày chỉ có một tình huống nhóm.')
        number = _number(r)
        row = _scenario(career, c['day'], number)
        today['case'] = dict(id=row['id'], period=number, league=r['league'], rank=rank, option=None)
        return dict(message='Đã mở tình huống phối hợp cùng đồng nghiệp.')
    case = today['case']
    _need(case is not None and case['option'] is None, 'Tình huống chưa mở hoặc đã ghi nhận lựa chọn.')
    row = _scenario(career, c['day'], case['period'])
    option = next((o for o in row['options'] if o['id'] == payload['option']), None)
    _need(option is not None and type(payload['option']) is str, 'Lựa chọn tình huống không hợp lệ.')
    case['option'] = option['id']
    return dict(message=option['feedback'])


def public(s, c, career):
    """Pure view; neither future peer outcomes nor unchosen answer scores leak."""
    r = _record(c)
    profile = PROFILES[career]
    league = r['league']
    today = _today(c, r)
    components = _components(today['jobs'], 0, _case_score(career, c['day'], today['case']))
    number = _number(r)
    standings = [dict(id='player', name='Bạn', strength='Công việc tự hoàn thành',
                      score=sum(d['score'] for d in r['days']), is_player=True)]
    standings += [dict(id=npc['id'], name=npc['name'], strength=npc['strength'],
                       score=sum(d['npc'][i] for d in r['days']), is_player=False)
                  for i, npc in enumerate(profile['rivals'])]
    for row in standings:
        row['rank'] = 1 + sum(other['score'] > row['score'] for other in standings)
    standings.sort(key=lambda x: (-x['score'], x['id']))
    rank = pm.rank(s, c, career)
    unlocked = rank >= 3 or league >= 1
    ready = bool(unlocked and today['jobs'] and today['case'] is None and c.get('open') and r['last_closed'] < c['day'])
    active = result = None
    if today['case']:
        case = today['case']
        raw = _scenario(career, c['day'], case['period'])
        if case['option'] is None and c.get('open') and r['last_closed'] < c['day']:
            active = dict(id=raw['id'], title=raw['title'], text=raw['text'], options=[dict(id=o['id'], label=o['label']) for o in raw['options']])
        elif case['option'] is not None:
            option = next(o for o in raw['options'] if o['id'] == case['option'])
            result = dict(id=raw['id'], title=raw['title'], option=case['option'], score=option['score'], feedback=option['feedback'])
    requirements = [] if league == 4 else [
        dict(id='good', label='Kỳ thi đua tốt ở liên đoàn hiện tại', got=r['good'], need=GOOD[league], met=r['good'] >= GOOD[league]),
        dict(id='rank', label='Bậc nghề hiện tại', got=rank, need=_rank_need(career, league), met=rank >= _rank_need(career, league))]
    return dict(league=league, title=LEAGUES[league], recognizer=profile['recognizer'], focus=profile['focus'],
                period=dict(number=number, worked_days=len(r['days']), total_days=10,
                            score=sum(d['score'] for d in r['days']), eligible_income=sum(d['income'] for d in r['days'])),
                standings=standings,
                today=dict(completed=len(today['jobs']), score=_score(components),
                           components=[dict(id=k, label=LABELS[k], score=v, weight=WEIGHTS[k]) for k, v in components.items() if v is not None],
                           case_completed=bool(today['case'] and today['case']['option'] is not None)),
                next=dict(league=league + 1, title=LEAGUES[league + 1], requirements=requirements) if league < 4 else None,
                reward=dict(cap=CAPS[league], rate=0.1, cash=career != 'pagoda', spirit_cap=SPIRIT_CAP),
                case=dict(unlocked=unlocked, ready=ready, active=active, result=result,
                          reason='Cần bậc nghề 3 hoặc liên đoàn thi đua 2.' if not unlocked else
                          'Cần hoàn thành công việc thực tế trong ca đang mở.' if not today['jobs'] or not c.get('open') or r['last_closed'] >= c['day'] else
                          'Mỗi ngày chỉ có một tình huống nhóm.' if today['case'] else ''),
                last_result=_public_result(r['history'][-1]) if r['history'] else None)


def _validate_case(career, day, period, league, case):
    if case is None:
        return
    _need(isinstance(case, dict) and set(case) == {'id', 'period', 'league', 'rank', 'option'})
    _int(case['period'], period, period)
    _int(case['league'], league, league)
    _int(case['rank'], 0, pm.top(career))
    _need(case['rank'] >= 3 or league >= 1)
    raw = _scenario(career, day, period)
    _need(case['id'] == raw['id'])
    _need(case['option'] is None or type(case['option']) is str and case['option'] in [o['id'] for o in raw['options']])


def _validate_day(c, career, period, league, index, row, previous):
    _need(isinstance(row, dict) and set(row) == {'day', 'completed', 'failed', 'components', 'score', 'abandoned', 'income', 'npc', 'case'})
    _int(row['day'], previous + 1, c['day'])
    _int(row['completed'], 0, DAY_MAX)
    _int(row['failed'], 0, DAY_MAX)
    _need(0 < row['completed'] + row['failed'] <= 2 * DAY_MAX)
    _need(type(row['abandoned']) is bool)
    _int(row['income'], 0, row['completed'] * MAX)
    if row['abandoned'] or not row['completed']:
        _need(row['income'] == 0)
    components = row['components']
    _need(isinstance(components, dict) and set(components) == set(WEIGHTS))
    for key, value in components.items():
        if value is None:
            _need(key in ('judgment', 'teamwork'))
        else:
            _int(value, 0, 100)
            if row['abandoned'] or not row['completed']:
                _need(value == 0)
    _int(row['score'], 0, 100)
    _need(row['score'] == _score(components))
    _need(type(row['npc']) is list and len(row['npc']) == 3)
    for value in row['npc']:
        _int(value, 0, 100)
    _need(row['npc'] == _npc(career, period, league, index))
    _validate_case(career, row['day'], period, league, row['case'])
    if row['case'] is not None:
        _need(row['completed'] > 0)
    team = _case_score(career, row['day'], row['case'])
    _need(components['teamwork'] == (0 if row['abandoned'] and team is not None else team))


def validate(c, career):
    if 'competition' not in c:
        return
    r = c['competition']
    _need(career in PROFILES and isinstance(r, dict) and set(r) == {'v', 'start', 'last_closed', 'league', 'good', 'days', 'history', 'today', 'archive'})
    _int(r['v'], 1, 1)
    _int(r['start'], 1, c['day'])
    _int(r['last_closed'], r['start'] - 1, c['day'])
    _int(r['league'], 0, 4)
    _int(r['good'], 0, MAX)
    _need(isinstance(r['history'], list) and len(r['history']) <= HISTORY_MAX)
    _need(isinstance(r['days'], list) and len(r['days']) < 10)
    archive = r['archive']
    _need(isinstance(archive, dict) and set(archive) == {'periods', 'last_day', 'league', 'good', 'completed', 'promotions'})
    _int(archive['periods'], 0, (c['day'] - r['start'] + 1) // 10)
    _int(archive['last_day'], r['start'] - 1 + archive['periods'] * 10, c['day'])
    _int(archive['league'], 0, 4)
    _int(archive['good'], 0, archive['periods'])
    _int(archive['completed'], 0, archive['periods'] * 10 * DAY_MAX)
    _need(isinstance(archive['promotions'], list) and len(archive['promotions']) == archive['league'])
    promoted_at = good_used = 0
    for tier, promotion in enumerate(archive['promotions']):
        _need(isinstance(promotion, dict) and set(promotion) == {'period', 'good', 'rank'})
        _int(promotion['period'], promoted_at + GOOD[tier], archive['periods'])
        _int(promotion['good'], GOOD[tier], promotion['period'] - promoted_at)
        _int(promotion['rank'], _rank_need(career, tier), pm.top(career))
        promoted_at = promotion['period']
        good_used += promotion['good']
    _need(good_used + archive['good'] <= archive['periods'])
    _need(archive['good'] <= archive['periods'] - promoted_at)
    if not archive['periods']:
        _need(archive == _initial(r['start'])['archive'])
    else:
        _need(len(r['history']) == HISTORY_MAX)
    league, good = archive['league'], archive['good']
    previous = archive['last_day']
    all_days = []
    day_periods = {}
    for number, history in enumerate(r['history'], archive['periods'] + 1):
        _need(isinstance(history, dict) and set(history) == {'period', 'league', 'days', 'score', 'rank', 'good', 'bonus', 'spirit', 'authorized', 'promotion_rank', 'spirit_room'})
        _int(history['period'], number, number)
        _int(history['league'], league, league)
        _need(type(history['authorized']) is bool and type(history['good']) is bool)
        _int(history['promotion_rank'], 0, pm.top(career))
        _int(history['score'], 0, 100)
        _int(history['rank'], 1, 4)
        _int(history['bonus'], 0, CAPS[league])
        _int(history['spirit'], 0, SPIRIT_CAP)
        _int(history['spirit_room'], 0, SPIRIT_CAP if career == 'pagoda' else 0)
        _need(isinstance(history['days'], list) and len(history['days']) == 10)
        for index, row in enumerate(history['days']):
            _validate_day(c, career, number, league, index, row, previous)
            previous = row['day']
            all_days.append(row)
            day_periods[previous] = (number, league)
        expected = _period_result(career, number, league, history['days'], history['authorized'], history['promotion_rank'], history['spirit_room'])
        _need(history == expected)
        league, good = _advance(career, league, good, history)
    _need(r['league'] == league and r['good'] == good)
    number = _number(r)
    for index, row in enumerate(r['days']):
        _validate_day(c, career, number, league, index, row, previous)
        previous = row['day']
        all_days.append(row)
        day_periods[previous] = (number, league)
    _need(r['last_closed'] == previous)
    today = r['today']
    _need(isinstance(today, dict) and set(today) == {'day', 'jobs', 'case'})
    _int(today['day'], r['start'], c['day'])
    _need(isinstance(today['jobs'], list) and len(today['jobs']) <= DAY_MAX)
    ids = set()
    for job in today['jobs']:
        _need(isinstance(job, dict) and set(job) == {'id', 'quality', 'procedure', 'judgment', 'income'})
        tid = job['id']
        _need(type(tid) is str and len(tid) <= 150 and tid.startswith(f'{career}-{today["day"]:04d}-') and tid not in ids)
        ids.add(tid)
        _int(job['quality'], 0, 100)
        _need(job['quality'] % 25 == 0)
        _int(job['procedure'], 0, 100)
        _need(job['procedure'] % 25 == 0)
        if job['judgment'] is not None:
            _int(job['judgment'], 0, 100)
        _int(job['income'])
        task = next((t for t in c.get('tasks', ()) if t.get('id') == tid), None)
        if task:
            _need(_manual(task, career, today['day']) and task.get('status') == 'completed')
            _need(job['procedure'] == max(0, 100 - 25 * task['mistakes']))
    p, tier = day_periods.get(today['day'], (number, league))
    _validate_case(career, today['day'], p, tier, today['case'])
    _need(today['case'] is None or bool(today['jobs']))
    completed_count = archive['completed'] + sum(d['completed'] for d in all_days)
    if today['day'] > r['last_closed']:
        completed_count += len(today['jobs'])
    _need(completed_count <= c.get('metrics', {}).get('served', 0))
    if today['day'] <= r['last_closed']:
        row = next((d for d in all_days if d['day'] == today['day']), None)
        _need(row is not None and row['completed'] == len(today['jobs']) and row['case'] == today['case'])
        _need(row['components'] == _components(today['jobs'], row['failed'], _case_score(career, today['day'], today['case']), row['abandoned']))
        _need(row['income'] in (0, sum(j['income'] for j in today['jobs'])))
