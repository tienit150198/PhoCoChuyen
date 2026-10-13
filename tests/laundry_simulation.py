"""Repeatable economy audit: two complete engine-driven tickets each day 1..60."""
import json
from tests.helpers import Journey
from tests.test_career_laundry import solve


def run():
    rows = []
    kinds = set()
    for day in range(1, 61):
        for slot in (0, 1):
            j = Journey('laundry', day=day, slot=slot)
            tid = j.task['id']
            start = j.c['turn']
            done = solve(j, tid)
            kinds.add(done['kind'])
            ledger = [r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
            gross = sum(n for n in ledger if n > 0)
            cost = -sum(n for n in ledger if n < 0)
            rows.append(dict(day=day, gross=gross, cost=cost, net=gross-cost, actions=j.c['turn']-start))
            assert done['status'] == 'completed' and done['quality'] == 100
            assert 12 <= gross-cost <= 28
    return dict(jobs=len(rows), variants=len(kinds), days=60,
                ranges={key:[min(r[key] for r in rows),max(r[key] for r in rows)] for key in ('gross','cost','net','actions')},
                totals={key:sum(r[key] for r in rows) for key in ('gross','cost','net','actions')})


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
