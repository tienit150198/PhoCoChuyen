"""Helpers for the paperwork-desk tests (pharmacy, accounting, customer care)."""
from game import desk, desk_content as dc
from game.content import make_task
from game.engine import validate_state
from tests.helpers import Journey, solve_desk


def find_case(career, variant, pred=None, days=range(1, 60), slots=range(0, 12)):
    """First (day, slot) whose planned case is `variant` (and matches pred(case))."""
    for day in days:
        for slot in slots:
            if dc.plan(career, day, slot) == variant:
                case, _, _ = dc.build(career, variant, day, slot)
                if pred is None or pred(case):
                    return day, slot
    raise LookupError(f'no {career}/{variant} case found')


def desk_journey(career, variant, pred=None, **kw):
    day, slot = find_case(career, variant, pred, **kw)
    j = Journey(career, slot=slot, day=day)
    assert j.task.get('desk') and j.task['variant'] == variant
    return j


def add_task(j, day, slot):
    """Put the case of (day, slot) on the counter of an existing journey."""
    c = j.c
    c['day'] = day
    t = make_task(j.career, day, slot, c['turn'])
    c['tasks'].append(t)
    c['active_task'] = t['id']
    validate_state(j.state)
    return t


def secrets(j, tid=None):
    return desk.secrets(j.get(tid) if tid else j.task)


def best(j):
    return next(v for v, k in secrets(j)['accept'].items() if k == 'best')


def flag_all(j):
    for i in secrets(j)['issues']:
        j.act('desk_flag', task=j.task['id'], field=i['fields'][0], rule=i['rule'])


def review(j, tid):
    return next(p for p in j.c['feed'] if p.get('kind') == 'review' and p.get('source') == tid)


def reports(j, tid):
    return [p for p in j.c['feed'] if p.get('report') and p.get('source') == tid]


def roundtrip(j):
    import json
    validate_state(json.loads(json.dumps(j.state)))


__all__ = ['find_case', 'desk_journey', 'add_task', 'secrets', 'best', 'flag_all', 'solve_desk', 'Journey', 'review', 'reports', 'roundtrip']
