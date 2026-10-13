"""Reproducible full-shift economy audit (all amounts are fictional game coins).

Run: python -m tests.creative_civic_economy
Writes output/new-careers/economy.json; does not change career implementations.
"""
from __future__ import annotations

import copy
import json
import math
import os
from collections import Counter
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('MNL_CAREERS', 'art_studio,lawyer,laundry,post_office')

from game import employment, operations, workplace_business
from game.engine import new_state, validate_state
from tests.helpers import Journey
from tests.test_career_art_studio import solve as solve_art
from tests.test_career_laundry import solve as solve_laundry
from tests.test_career_lawyer import solve as solve_lawyer
from tests.test_career_post_office import solve as solve_post

CAREERS = ('art_studio', 'lawyer', 'laundry', 'post_office')


class AuditJourney(Journey):
    def __init__(self, career, day, staffed=False):
        self.career = career
        self.state = new_state()
        self.actions = Counter()
        self.c['day'] = day
        self.c['ops']['finance']['period_start'] = day
        if employment.required(career):
            self.c['job'] = employment.hired_record(career, day=day)
        self.act('select_career')
        self.original_fund = self.c['money']
        if staffed:
            self.act('ops_hire', candidate=career + '-staff-1', confirm=True)
        self.recruitment = self.original_fund - self.c['money']
        validate_state(self.state)

    def act(self, action, **payload):
        self.actions[action] += 1
        return super().act(action, **payload)


def liabilities(c):
    f = c['ops']['finance']
    return dict(
        unpaid_bills=sum(b['amount'] for b in f['bills'] if b['status'] == 'unpaid'),
        unbilled_rent=f['period_rent'],
        estimated_unbilled_tax=math.ceil(f['period_revenue'] * operations.RULES['tax_percent'] / 100),
    )


def shift(j, staff_orders=0):
    day = j.c['day']
    mode = j.c['life']['mode']
    before_fund = j.c['money']
    before_wallet = j.state['journey'].get('wallet')
    before_actions = j.actions.copy()
    before_liabilities = liabilities(j.c)
    before_ledger = len(j.c['ops']['finance']['ledger'])
    before_staff_orders = j.c['ops'].get('business', {}).get('served', 0)
    j.act('start_day')
    ids = [t['id'] for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
    for tid in ids:
        j.act('task_select', task=tid)
        if j.career == 'laundry':
            solve_laundry(j, tid)
        else:
            {'art_studio': solve_art, 'lawyer': solve_lawyer, 'post_office': solve_post}[j.career](j)
    completed = [copy.deepcopy(j.get(tid)) for tid in ids]
    assert all(t['status'] == 'completed' for t in completed)
    employer_postage = sum(t['needs'].get('postage', 0) for t in completed)
    elapsed = 0
    if staff_orders:
        start = j.c['ops']['business']['anchor']
        for _ in range(staff_orders):
            due = min(p['at'] for p in j.c['ops']['business']['pending'].values())
            workplace_business.settle(j.state, due)
        elapsed = due - start
    j.act('end_day', carry_event=True)
    summary = copy.deepcopy(j.c['shift_summary'])
    fund_after_close = j.c['money']
    accrued = liabilities(j.c)
    # Utility and earned wages are invoices, not immediate ledger debits. Pay them
    # through the engine so the cash reconciliation includes actual settlement.
    if accrued['unpaid_bills']:
        j.act('ops_pay_all', confirm=True)
    ledger = copy.deepcopy(j.c['ops']['finance']['ledger'][before_ledger:])
    by_category = Counter()
    for entry in ledger:
        by_category[entry['category']] += entry['amount']
    income = sum(max(0, r['amount']) for r in ledger)
    expense = -sum(min(0, r['amount']) for r in ledger)
    net = income - expense
    assert net == j.c['money'] - before_fund, (j.career, day, ledger)
    remaining = liabilities(j.c)
    accrual_net = net - sum(remaining.values()) + sum(before_liabilities.values())
    salary = sum(r['amount'] for r in ledger if r['category'] == 'salary')
    bonuses = sum(r['amount'] for r in ledger if r['amount'] > 0 and r.get('ref') in ids)
    if employment.required(j.career):
        assert salary == j.c['job']['salary'], (j.career, day, salary)
        assert sum(r['category'] == 'salary' for r in ledger) == 1
        assert remaining['unbilled_rent'] == 0
        assert remaining['estimated_unbilled_tax'] == 0
    assert not remaining['unpaid_bills'], (j.career, day, remaining)
    assert accrual_net > 0, (j.career, day, accrual_net)
    validate_state(j.state)
    print(j.career, day, 'staff', len(j.c['ops']['staff']), 'jobs', len(ids),
          'gross', income, 'paid', expense, 'cash-net', net, 'accrual-net', accrual_net, flush=True)
    return dict(
        career=j.career, day=day, story=j.state['journey'].get('story', False),
        mode=mode, scheduled_jobs=len(ids), completed_jobs=len(completed),
        actions=dict(j.actions - before_actions), staff=len(j.c['ops']['staff']),
        contract_salary=j.c['job']['salary'], salary=salary,
        ledger_revenue=sum(r['amount'] for r in ledger if r['category'] == 'revenue' and r['amount'] > 0),
        customer_gross=(0 if employment.required(j.career) else
                        sum(r['amount'] for r in ledger if r['category'] == 'revenue' and r['amount'] > 0)),
        task_bonus=bonuses if employment.required(j.career) else 0,
        staff_orders_completed=j.c['ops'].get('business', {}).get('served', 0) - before_staff_orders,
        staff_seconds_since_anchor=elapsed,
        quoted_staff_wage=sum(e['wage'] for e in j.c['ops']['staff']),
        conservative_net_after_quoted_wage=accrual_net - sum(e['wage'] for e in j.c['ops']['staff']),
        staff_order_supported=j.career in workplace_business.ORDERS,
        employer_postage=employer_postage, total_income=income, paid_costs=expense,
        ledger_net=net, accrual_adjusted_net=accrual_net, by_category=dict(by_category),
        initial_career_fund=before_fund, after_close_career_fund=fund_after_close,
        final_career_fund=j.c['money'], initial_journey_wallet=before_wallet,
        final_journey_wallet=j.state['journey'].get('wallet'),
        liabilities_before=before_liabilities, liabilities_at_close=accrued,
        liabilities_after_payment=remaining, shift_summary=summary, ledger=ledger,
    )


def audit():
    standalone = [shift(AuditJourney(cid, day)) for cid in CAREERS for day in (1, 10, 40)]
    staffed = [shift(AuditJourney(cid, day, staffed=True), staff_orders=4)
               for cid in CAREERS for day in (1, 10, 40)]
    periods = []
    for cid in ('art_studio', 'laundry'):
        j = AuditJourney(cid, 1, staffed=True)
        rows = [shift(j, staff_orders=4) for _ in range(operations.RULES['period_days'])]
        net = j.c['money'] - j.original_fund
        assert net == sum(r['ledger_net'] for r in rows) - j.recruitment
        assert not sum(liabilities(j.c).values())
        assert any(r['by_category'].get('rent', 0) < 0 for r in rows)
        assert all(r['by_category'].get('wage', 0) < 0 for r in rows)
        assert net > 0
        periods.append(dict(career=cid, days=len(rows), recruitment_cost=j.recruitment,
                            initial_career_fund=j.original_fund, final_career_fund=j.c['money'],
                            net_after_recruitment_and_all_bills=net, shifts=rows))
    return dict(
        assumptions=[
            'Non-story new-state fixtures; no journey-wallet withdrawals or owner draws.',
            'Independent days 1, 10 and 40 isolate content tiers, not accumulated upgrades or promotions.',
            'Complete every engine-scheduled job perfectly; no optional extra customers, grants or purchases.',
            'Employed fixtures use the upper advertised signed-contract salary, off probation; one salary per worked shift.',
            'Bill settlement uses ops_pay_all after end_day. Accrual net also reserves unbilled rent and rounded game tax.',
            'Staffed rows hire the first candidate; shift figures exclude one-time recruitment. Seven-day totals include it.',
            'Consecutive periods use the actual rolled daily mode and include incidental engine costs and income.',
            'Staffed rows settle exactly four independent staff orders at their server-clock due times, using workplace_business.settle as the server does; wages are paid per order. No fabricated attendance.',
            'Conservative staff sensitivity subtracts the quoted daily wage even when no actual staff payroll was earned; this is not a ledger debit.',
        ], rules=dict(operations.RULES), standalone=standalone, staffed=staffed, full_periods=periods,
        staff_integration=dict(unsupported=[cid for cid in CAREERS if cid not in workplace_business.ORDERS],
                               explanation='Each new career has a service-order definition; timed wages and materials are debited before revenue and the existing profit bonus. No separate daily payroll invoice.'),
    )


if __name__ == '__main__':
    with patch.object(workplace_business.time, 'time', return_value=2000000000):
        report = audit()
    path = Path(__file__).resolve().parents[1] / 'output/new-careers/economy.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for r in report['standalone'] + report['staffed']:
        print(r['career'], r['day'], 'staff', r['staff'], 'jobs', r['scheduled_jobs'],
              'income', r['total_income'], 'paid', r['paid_costs'], 'cash-net', r['ledger_net'],
              'accrual-net', r['accrual_adjusted_net'])
    for r in report['full_periods']:
        print(r['career'], 'seven-day net incl recruitment:', r['net_after_recruitment_and_all_bills'])
    print(path)
