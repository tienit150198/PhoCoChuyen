"""⏱️ Tăng ca ×2 and ⚡ thưởng năng suất 30% (game/overtime.py, owner 07/10)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import journey as jr
from game import operations as ops
from game import overtime as ovt
from game import x3_week as x3
from game import engine as E
from game.careers import PLUGINS
from game.content import CAREERS
from game.engine import money, public_state, validate_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parent.parent
BASE_REF = 'rel-1.9.9'   # production when this shipped: a save made here must load there (rollback)


def journey(career):
    j = Journey(career)
    j.state['settings']['securityEvents'] = False
    return j


def job(j, n, pay=40):
    """Book `n` finished jobs the way engine.task_done does ('Hoàn thành: …' rows), each followed by its overtime hook."""
    out = []
    for _ in range(n):
        tid = f'{j.career}-{j.c["day"]:04d}-{len(out) + 90}'
        money(j.state, j.c, pay, 'Hoàn thành: việc thử', tid)
        out.append(ovt.on_job(j.state, j.c, dict(id=tid, career=j.career, title='việc thử'), pay, 'completed', 5))
    return out


def books_ok(tc, s):
    validate_state(json.loads(json.dumps(s)))
    for c in s['careers'].values():
        f = c['ops']['finance']
        tc.assertEqual(c['money'], f['opening_balance'] + sum(x['amount'] for x in f['ledger']))


class Thresholds(unittest.TestCase):
    def test_every_career_has_a_reachable_pair(self):
        for cid in CAREERS:
            c = journey('grocery').state['careers'][cid]
            n, busy = ovt.thresholds(c, cid)
            with self.subTest(career=cid):
                self.assertTrue(1 <= n <= ovt.SLOTS - ovt.OT_MAX, n)
                self.assertTrue(n + ovt.GAP <= busy <= ovt.SLOTS, busy)

    def test_measured_careers_use_the_table(self):
        c = {'day': 3}
        self.assertEqual(ovt.thresholds(c, 'milk_tea'), (7, 12))
        self.assertEqual(ovt.thresholds(c, 'mother_baby'), (3, 6))
        self.assertEqual(ovt.thresholds(c, 'flight_attendant'), (9, 12))
        self.assertLessEqual(set(ovt.NORMAL), set(CAREERS))
        self.assertLessEqual(set(ovt.BUSY), set(ovt.NORMAL))

    def test_a_new_career_gets_a_sensible_pair_on_its_own(self):
        """A career added later (no measured days) gets max(4, its planned jobs) and +3, with no edit here."""
        self.assertEqual(ovt.thresholds({'day': 2}, 'zz_new'), (4, 7))
        planned = mock.Mock(daily_task_count=lambda day: 6)
        with mock.patch.dict(PLUGINS, {'zz_plan': planned}):
            self.assertEqual(ovt.thresholds({'day': 2}, 'zz_plan'), (6, 9))
        broken = mock.Mock(daily_task_count=mock.Mock(side_effect=KeyError))
        with mock.patch.dict(PLUGINS, {'zz_bad': broken}):
            self.assertEqual(ovt.thresholds({'day': 2}, 'zz_bad'), (4, 7))
        self.assertEqual(ovt.thresholds({'day': 1}, 'railway')[0], 4)   # unmeasured: its own plan (4 a day) or 4


class Booking(unittest.TestCase):
    def test_jobs_past_the_normal_day_pay_twice(self):
        j = journey('grocery')   # normal 4, busy 7
        got = job(j, 6, pay=40)
        self.assertEqual(got, [0, 0, 0, 0, 40, 40])
        rows = [r for r in j.c['ops']['finance']['ledger'] if r['category'] == 'overtime']
        self.assertEqual([(r['amount'], r['ref']) for r in rows], [(40, 'ot2-grocery-0001-94'), (40, 'ot2-grocery-0001-95')])
        self.assertTrue(all(r['reason'].startswith('⏱️ Tăng ca ×2') for r in rows))
        self.assertEqual(ovt.today(j.c), dict(jobs=6, pay=240, ot=2, ot_pay=80, prod=0))
        books_ok(self, j.state)

    def test_caps_three_jobs_and_fifty_xu(self):
        j = journey('grocery')
        got = job(j, 10, pay=120)
        self.assertEqual(got, [0] * 4 + [ovt.JOB_CAP] * ovt.OT_MAX + [0] * 3)

    def test_only_a_good_finished_paid_job_earns_overtime(self):
        j = journey('grocery')
        job(j, 4)
        tid = 'grocery-0001-80'
        money(j.state, j.c, 40, 'Hoàn thành: việc thử', tid)
        t = dict(id=tid, career='grocery', title='x')
        self.assertEqual(ovt.on_job(j.state, j.c, t, 40, 'cancelled', 5), 0)
        self.assertEqual(ovt.on_job(j.state, j.c, t, 40, 'referred', 5), 0)
        self.assertEqual(ovt.on_job(j.state, j.c, t, 40, 'completed', 2), 0)      # a 2★ job
        self.assertEqual(ovt.on_job(j.state, j.c, t, 0, 'completed', 5), 0)
        self.assertEqual(ovt.on_job(j.state, j.c, dict(t, player_order={'id': 'o'}), 40, 'completed', 5), 0)
        self.assertEqual(ovt.on_job(j.state, j.c, t, 40, 'completed', 3), 40)
        self.assertEqual(ovt.on_job(j.state, j.c, t, 40, 'completed', 3), 0)      # never twice
        books_ok(self, j.state)

    def test_other_income_never_counts_as_a_job(self):
        """Staff orders, the team's job bonus, tips and the salary are not the player's jobs."""
        j = journey('grocery')
        money(j.state, j.c, 90, 'Thưởng việc của đội — An: 6 việc', 'staff-jobs-1', category='other_income')
        money(j.state, j.c, 30, 'Tiền boa', None, category='tip')
        money(j.state, j.c, 100, 'Lương ngày 1', 'salary-1', category='salary')
        self.assertEqual(ovt.today(j.c)['jobs'], 0)
        self.assertEqual(job(j, 5), [0, 0, 0, 0, 40])

    def test_yesterday_does_not_count(self):
        j = journey('grocery')
        job(j, 6)
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertEqual(ovt.today(j.c), dict(jobs=0, pay=0, ot=0, ot_pay=0, prod=0))
        self.assertEqual(job(j, 5), [0, 0, 0, 0, 40])


class Productivity(unittest.TestCase):
    def close(self, j):
        return j.act('end_day', carry_event=True)['summary']

    def test_the_busy_tier_adds_thirty_percent_at_close(self):
        j = journey('grocery')   # busy 7
        job(j, 7, pay=20)
        s = self.close(j)
        self.assertEqual(s['ot'], dict(jobs=7, normal=4, busy=7, ot=3, ot_pay=60, prod=42, pct=30, total=102))
        rows = [r for r in j.c['ops']['finance']['ledger'] if r['ref'] == 'otp-1']
        self.assertEqual([(r['amount'], r['category']) for r in rows], [(42, 'overtime')])
        self.assertTrue(rows[0]['reason'].startswith('⚡ Thưởng năng suất 30%'))
        self.assertGreaterEqual(s['income'], 140 + 102)
        books_ok(self, j.state)

    def test_capped_and_not_below_the_tier(self):
        j = journey('grocery')
        job(j, 8, pay=100)
        self.assertEqual(self.close(j)['ot']['prod'], ovt.DAY_CAP)
        j = journey('grocery')
        job(j, 6, pay=100)
        s = self.close(j)
        self.assertEqual((s['ot']['prod'], s['ot']['total']), (0, 100))
        j = journey('grocery')
        job(j, 3)
        self.assertNotIn('ot', self.close(j))

    def test_paid_once_even_if_close_runs_again(self):
        j = journey('grocery')
        job(j, 7, pay=20)
        first = ovt.on_close(j.state, j.c, 'grocery')
        again = ovt.on_close(j.state, j.c, 'grocery')
        self.assertEqual(first['prod'], again['prod'])
        self.assertEqual(len([r for r in j.c['ops']['finance']['ledger'] if r['ref'] == 'otp-1']), 1)

    def test_the_view_chip(self):
        j = journey('grocery')
        job(j, 5)
        v = public_state(j.state)['careers']['grocery']['ot']
        self.assertEqual(v, dict(jobs=5, normal=4, busy=7, ot=1, max=3, pay=40, pct=30))
        j.act('end_day', carry_event=True)
        self.assertIsNone(public_state(j.state)['careers']['grocery']['ot'])   # closed: no chip


class Money(unittest.TestCase):
    def setUp(self):
        for target in ('game.workplace_business.refresh', 'game.workplace_business.settle'):
            m = mock.patch(target, return_value=False)
            m.start()
            self.addCleanup(m.stop)

    def test_a_salaried_week_with_overtime_bills_no_tax(self):
        for career in ('nurse', 'hr_admin'):
            if career not in ops.CAREERS:
                continue
            with self.subTest(career=career):
                j = journey(career)
                n, busy = ovt.thresholds(j.c, career)
                for d in range(7):
                    job(j, busy, pay=30)
                    s = j.act('end_day', carry_event=True)['summary']
                    self.assertEqual(s['ot']['ot'], ovt.OT_MAX)
                    if d < 6:
                        j.act('start_day')
                f = j.c['ops']['finance']
                self.assertTrue([r for r in f['ledger'] if r['category'] == 'overtime'])
                self.assertFalse([b for b in f['bills'] if b['kind'] in ('tax', 'rent')])
                self.assertEqual(f['period_revenue'], 0)
                books_ok(self, j.state)

    def test_overtime_is_not_shop_revenue(self):
        j = journey('mother_baby')
        before = j.c['ops']['finance']['period_revenue']
        job(j, 5, pay=30)
        self.assertEqual(j.c['ops']['finance']['period_revenue'] - before, 5 * 30)   # the jobs only, not the 2 OT rows

    def test_no_stacking_with_the_x3_day(self):
        """The 🔥 x3 day's bonus is figured on the day's net without the overtime and productivity rows."""
        j = journey('grocery')
        jr.enable_story(j.state, 4242)
        j.state['journey'].update(gender='female', intro=True)
        job(j, 7, pay=20)   # 140 jobs + 60 OT + 42 productivity
        with mock.patch.object(x3, 'on', lambda c, t=None: c == 'grocery'):
            s = j.act('end_day', carry_event=True)['summary']
        fire = [h['amount'] for h in j.state['journey']['history'] if h['label'].startswith('🔥')]
        self.assertEqual(s['ot']['total'], 102)
        self.assertGreater(s['net'], 102)
        self.assertEqual(fire, [2 * (s['net'] - 102)])

    def test_salary_and_its_multiplier_are_not_doubled(self):
        """A salaried day: overtime comes from the jobs' pay only; the salary row (×3/×5 for accountants) is no job."""
        j = journey('grocery')
        money(j.state, j.c, 300, 'Lương ngày 1 · x3', 'salary-1', category='salary')
        self.assertEqual(sum(job(j, 6, pay=10)), 20)


class RealDay(unittest.TestCase):
    def test_a_played_mother_and_baby_day(self):
        j = journey('mother_baby')   # normal 3, busy 6
        for _ in range(6):
            left = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
            if not left:
                j.act('more_work')
                left = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
            j.solve(left[0]['id'])
        d = ovt.today(j.c)
        self.assertEqual((d['jobs'], d['ot']), (6, 3))
        jobs = [r['amount'] for r in j.c['ops']['finance']['ledger'] if r['reason'].startswith('Hoàn thành:')]
        self.assertEqual(d['ot_pay'], sum(min(ovt.JOB_CAP, x) for x in jobs[3:6]))
        s = j.act('end_day', carry_event=True)['summary']
        self.assertEqual(s['ot']['prod'], min(ovt.DAY_CAP, sum(jobs) * 30 // 100))
        books_ok(self, j.state)


class Rollback(unittest.TestCase):
    """A save with overtime rows loads in 1.9.9 (its own process), and comes back unchanged."""

    @classmethod
    def setUpClass(cls):
        old = os.environ.get('MNL_OLD_TREE')
        if old:
            cls.tree = old
            return
        if not shutil.which('git') or not (ROOT / '.git').exists():
            raise unittest.SkipTest('needs a git checkout or MNL_OLD_TREE')
        if subprocess.run(['git', 'cat-file', '-e', BASE_REF + '^{commit}'], cwd=ROOT, capture_output=True).returncode:
            raise unittest.SkipTest(f'{BASE_REF} is not in this clone')
        cls._tmp = tempfile.TemporaryDirectory(prefix='ot-base-')
        archive = subprocess.run(['git', 'archive', BASE_REF, 'game', 'reference', 'i18n'], cwd=ROOT, capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', cls._tmp.name], input=archive, check=True)
        cls.tree = cls._tmp.name

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, '_tmp', None):
            cls._tmp.cleanup()

    def test_old_release_reads_the_save(self):
        j = journey('mother_baby')
        job(j, 7, pay=30)
        j.act('end_day', carry_event=True)
        played = json.dumps(j.state, ensure_ascii=False)
        prog = ('import json,sys\nfrom game.engine import migrate_state,validate_state\n'
                's=migrate_state(json.loads(sys.stdin.read()))\nvalidate_state(s)\nprint(json.dumps(s,ensure_ascii=False))')
        env = dict(os.environ, PYTHONPATH=self.tree)
        out = subprocess.run([sys.executable, '-c', prog], input=played, capture_output=True, text=True, encoding='utf-8',
                             cwd=self.tree, env=env, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = json.loads(out.stdout)
        self.assertEqual(back['careers']['mother_baby']['ops']['finance']['ledger'], j.c['ops']['finance']['ledger'])
        self.assertEqual(back['careers']['mother_baby']['money'], j.c['money'])
        validate_state(E.migrate_state(back))


if __name__ == '__main__':
    unittest.main()
