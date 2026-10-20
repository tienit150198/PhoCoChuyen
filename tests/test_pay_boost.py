"""💰 Tiền công +%, 🎉 Tuần lễ tay nghề, 🧰 Bộ đồ nghề / 🤝 Mối khách quen / ⏩ Làm nhanh (game/pay_boost.py)."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import journey as jr
from game import pay_boost as pb
from game import tile_match
from game.engine import GameError, apply_action, dormant_out, make_task, migrate_state, new_state, public_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
LIVE = '83fe229c'   # 2.4.72 (live on 21/10)
WEEK = ('1792602000', '1793206799')   # 22/10/2026 00:00 – 28/10/2026 23:59:59 VN
IN_WEEK = 1792602000 + 3 * 86400 + 5 * 3600


def story(chapter=2):
    s = new_state()
    jr.enable_story(s, 4242)
    j = s['journey']
    j.update(gender='female', intro=True, chapter=chapter, done=list(range(1, chapter)))
    for n in range(1, chapter + 1):
        jr._unlock_chapter(j, n)
    validate_state(s)
    return s


class Run:
    """A story save at one career with one job in hand (the laundry: graded steps with a key)."""

    def __init__(self, career='laundry', slot=0, day=1, s=None):
        self.career = career
        self.state = s or story()
        self.act('select_career')
        self.deal(slot, day)

    def deal(self, slot, day=None):
        c = self.c
        day = day or c['day']
        c.update(day=day, open=True, started=True, turn=c.get('turn', 0) + 1)
        t = make_task(self.career, day, slot, c['turn'])
        c['tasks'] = [x for x in c['tasks'] if x['status'] == 'completed'][-3:] + [t]
        c['active_task'] = t['id']
        validate_state(self.state)
        return t['id']

    @property
    def c(self):
        return self.state['careers'][self.career]

    def get(self, tid):
        return next(t for t in self.c['tasks'] if t['id'] == tid)

    def act(self, action, **p):
        self.state, r = apply_action(self.state, self.career, action, p)
        return r

    def step(self, tid):
        t = self.get(tid)
        if not t['known']:
            return self.act('ask', task=tid)
        st = t['stage']
        p = ({'items': [g['id'] for g in t['needs']['garments']]} if st == 'inspect' else
             {'checks': ['count', 'stains', 'dry', 'finish', 'tag']} if st == 'check' else
             {'tag': t['needs']['tag']} if st == 'deliver' else {'choices': t['_key'][st]})
        return self.act('ld_' + st, task=tid, **p)

    def solve(self, tid):
        r = None
        for _ in range(14):
            if self.get(tid)['status'] == 'completed':
                return r
            r = self.step(tid)
        raise AssertionError('not finished')

    def fund(self, amount):
        from game.engine import money
        money(self.state, self.c, amount - self.c['money'], 'Test fund')

    def rows(self, prefix):
        return [r for r in self.c['ops']['finance']['ledger'] if str(r.get('reason', '')).startswith(prefix)]


ON = {'MNL_PAYBOOST_OFF': '0', 'MNL_PAYWEEK_FROM': '', 'MNL_PAYWEEK_UNTIL': ''}


@mock.patch.dict(os.environ, ON)
class Raise(unittest.TestCase):
    def test_table_targets_low_paid_careers_and_averages_ten_to_fifteen(self):
        from game.content import CAREERS
        vals = [pb.raise_pct(c) for c in CAREERS]
        self.assertTrue(set(vals) <= {pb.LOW, pb.MID, pb.HIGH})
        self.assertTrue(10 <= sum(vals) / len(vals) <= 15, sum(vals) / len(vals))
        self.assertEqual(pb.raise_pct('garbage'), 20)
        self.assertEqual(pb.raise_pct('florist'), 8)
        self.assertEqual(pb.raise_pct('pilot'), 12)
        self.assertTrue(set(pb.RAISE) <= set(CAREERS))

    def test_a_finished_job_gets_its_own_row_and_a_breakdown(self):
        r = Run()
        tid = r.c['active_task']
        res = r.solve(tid)
        base = [x for x in r.c['ops']['finance']['ledger'] if x.get('ref') == tid and str(x['reason']).startswith('Hoàn thành')]
        rows = r.rows(pb.PREFIX)
        self.assertEqual(len(rows), 1)
        self.assertIn('+20%', rows[0]['reason'])
        net = res['payboost']['base']
        self.assertTrue(base and 0 < net <= base[0]['amount'])
        self.assertIn(rows[0]['amount'], (net * 20 // 100, net * 20 // 100 + 1))
        self.assertEqual(res['payboost']['raise'], rows[0]['amount'])
        self.assertEqual(res['payboost']['ref'], tid)
        self.assertIn('xu tiền công thêm', res['message'])
        validate_state(json.loads(json.dumps(r.state)))

    def test_kill_switch_and_classic_mode(self):
        with mock.patch.dict(os.environ, {'MNL_PAYBOOST_OFF': '1'}):
            r = Run()
            res = r.solve(r.c['active_task'])
            self.assertEqual(r.rows(pb.PREFIX), [])
            self.assertNotIn('payboost', res)
        s = new_state()   # outside the story: nothing
        c = s['careers']['milk_tea']
        self.assertEqual(pb.on_earning(s, c, 100, 'x', 'r'), 0)

    def test_staff_orders_get_nothing_salary_does(self):
        r = Run()
        before = r.c['money']
        self.assertEqual(tile_match.fund_bonus(r.state, r.c, 100, 'Đơn riêng', 'o1', direct=True), 0)
        self.assertEqual(r.c['money'], before)
        got = tile_match.fund_bonus(r.state, r.c, 100, 'Lương ngày 3', 'salary-3')
        self.assertEqual(got, 20)
        self.assertEqual(r.c['money'], before + 20)

    def test_row_cap(self):
        r = Run()
        self.assertEqual(pb.on_earning(r.state, r.c, 100000, 'big', 'b1'), pb.ROW_CAP)


@mock.patch.dict(os.environ, ON)
class Event(unittest.TestCase):
    def test_window_from_the_environment_only(self):
        self.assertFalse(pb.event_on(IN_WEEK))
        with mock.patch.dict(os.environ, {'MNL_PAYWEEK_FROM': WEEK[0], 'MNL_PAYWEEK_UNTIL': WEEK[1]}):
            self.assertTrue(pb.event_on(IN_WEEK))
            self.assertFalse(pb.event_on(int(WEEK[0]) - 1))
            self.assertFalse(pb.event_on(int(WEEK[1]) + 1))
            self.assertEqual(pb.news_line(IN_WEEK)['key'], 'payweek:2026-10-25')
            self.assertIn('28/10', pb.news_line(IN_WEEK)['text'])
            with mock.patch.dict(os.environ, {'MNL_PAYBOOST_OFF': '1'}):
                self.assertFalse(pb.event_on(IN_WEEK))
                self.assertIsNone(pb.news_line(IN_WEEK))

    def test_stacking_order_and_caps_with_x3(self):
        s = story()
        with mock.patch.dict(os.environ, {'MNL_PAYWEEK_FROM': WEEK[0], 'MNL_PAYWEEK_UNTIL': WEEK[1]}), \
                mock.patch.object(pb, 'now', return_value=IN_WEEK):
            s['journey'][pb.KEY] = dict(v=1, tool={'garbage': 5, 'florist': 5})
            with mock.patch('game.x3_week.on', return_value=False):
                p = pb.pcts(s, 'garbage')
                self.assertEqual((p['raise_'], p['event'], p['tools'], p['total']), (20, 20, 8, 48))
            with mock.patch('game.x3_week.on', return_value=True):
                p = pb.pcts(s, 'garbage')   # an x3 day: at most ×3.4 in all (3 + 0.40)
                self.assertEqual((p['raise_'], p['event'], p['tools'], p['total']), (20, 20, 0, 40))
                p = pb.pcts(s, 'florist')
                self.assertEqual(p['total'], 36)

    def test_x3_is_paid_on_the_base_net_only(self):
        summary = dict(net=1000, payboost=150, tile=20)
        self.assertEqual(jr._base_net(dict(summary=summary), {}), 830)

    def test_streak_once_a_day_and_growing(self):
        env = {'MNL_PAYWEEK_FROM': WEEK[0], 'MNL_PAYWEEK_UNTIL': WEEK[1]}
        with mock.patch.dict(os.environ, env):
            r = Run()
            for day, (t, paid) in enumerate(((IN_WEEK, 30), (IN_WEEK + 86400, 40), (IN_WEEK + 3 * 86400, 30)), 1):
                with mock.patch.object(pb, 'now', return_value=t):
                    for k in range(pb.STREAK_JOBS + 1):
                        tid = r.deal(k, day=day)
                        res = r.solve(tid)
                        if k == pb.STREAK_JOBS - 1:
                            self.assertEqual(res['payboost']['streak'], paid)
                        else:
                            self.assertNotIn('streak', res.get('payboost', {}))
                    view = pb.public(r.state)
                    self.assertTrue(view['got'])
                    self.assertEqual(view['jobs'], pb.STREAK_JOBS)
            rows = r.rows(pb.STREAK_PREFIX)
            self.assertEqual([x['amount'] for x in rows], [30, 40, 30])   # day 3 skipped a day: the streak starts again
            with mock.patch.object(pb, 'now', return_value=IN_WEEK):
                raised = [x for x in r.rows(pb.PREFIX)]
                self.assertTrue(all('Tuần lễ tay nghề' in x['reason'] and '+40%' in x['reason'] for x in raised))
            validate_state(json.loads(json.dumps(r.state)))
            self.assertEqual(pb.day_total(r.c, r.c['day']), sum(x['amount'] for x in r.c['ops']['finance']['ledger']
                             if x.get('day') == r.c['day'] and str(x['reason']).startswith((pb.PREFIX, pb.STREAK_PREFIX))))


@mock.patch.dict(os.environ, ON)
class Shop(unittest.TestCase):
    def test_tools_in_order_from_the_fund_with_steep_prices(self):
        self.assertEqual(list(pb.TOOL_PCTS[1:]), [2, 3, 5, 6, 8])
        self.assertTrue(all(b > 2 * a for a, b in zip(pb.TOOL_PRICES[1:], pb.TOOL_PRICES[2:])))
        r = Run()
        r.fund(0)
        with self.assertRaises(GameError):
            r.act('payk_buy', item='tool')
        r.fund(sum(pb.TOOL_PRICES) + pb.BOOK_PRICE + pb.FAST_PRICE)
        for n in range(1, 6):
            before = r.c['money']
            r.act('payk_buy', item='tool')
            self.assertEqual(pb.tier(r.state, 'laundry'), n)
            self.assertEqual(before - r.c['money'], pb.TOOL_PRICES[n])
        with self.assertRaises(GameError):
            r.act('payk_buy', item='tool')
        r.act('payk_buy', item='book')
        with self.assertRaises(GameError):
            r.act('payk_buy', item='book')
        r.act('payk_buy', item='fast')
        view = public_state(r.state)['careers']['laundry']['paykit']
        self.assertEqual((view['tier'], view['tool_pct'], view['book'], view['fast']['owned']), (5, 8, True, True))
        self.assertEqual(view['total'], 28)
        validate_state(json.loads(json.dumps(r.state)))
        with self.assertRaises(GameError):   # a career without ⏩
            Run('mother_baby', s=r.state).act('payk_buy', item='fast')

    def test_purchases_stay_within_ten_percent(self):
        self.assertLessEqual(pb.TOOL_PCTS[pb.TOP] + pb.TIP_CHANCE * pb.TIP_PCT / 100, 10)

    def test_tips_about_one_job_in_five(self):
        r = Run()
        r.fund(pb.BOOK_PRICE)
        r.act('payk_buy', item='book')
        tips = 0
        for k in range(60):
            tid = r.deal(k % 12, day=1 + k // 12)
            res = r.solve(tid)
            tips += bool(res['payboost'].get('tip'))
            if res['payboost'].get('tip'):
                self.assertEqual(res['payboost']['tip'], max(1, min(pb.TIP_MAX, res['payboost']['base'] * pb.TIP_PCT // 100)))
        self.assertTrue(4 <= tips <= 22, tips)
        self.assertEqual(len(r.rows(pb.TIP_PREFIX)), tips)

    def test_kill_switch_keeps_what_was_bought(self):
        r = Run()
        r.fund(10**6)
        r.act('payk_buy', item='tool')
        with mock.patch.dict(os.environ, {'MNL_PAYBOOST_OFF': '1'}):
            self.assertEqual(pb.pcts(r.state, 'laundry')['total'], 0)
            r.solve(r.c['active_task'])
            self.assertEqual(r.rows(pb.PREFIX), [])
            self.assertEqual(pb.tier(r.state, 'laundry'), 1)


@mock.patch.dict(os.environ, ON)
class Fast(unittest.TestCase):
    def test_only_after_fifty_right_by_hand_and_never_counts_itself(self):
        r = Run()
        r.fund(pb.FAST_PRICE)
        tid = r.c['active_task']
        r.step(tid)   # ask
        with self.assertRaises(GameError):   # not bought
            r.act('payk_fast', task=tid)
        r.act('payk_buy', item='fast')
        with self.assertRaises(GameError):   # not yet 50 by hand
            r.act('payk_fast', task=tid)
        r.step(tid)   # inspect by hand: 1
        self.assertEqual(pb.count(r.state, 'laundry', 'ld_inspect'), 1)
        r.state['journey'][pb.KEY]['st']['laundry'] = {a: pb.FAST_NEED for a in ('ld_sort', 'ld_treat')}
        validate_state(r.state)
        stage = r.get(tid)['stage']
        self.assertEqual(stage, 'sort')
        view = public_state(r.state)['careers']['laundry']['paykit']['fast']
        self.assertEqual(view['ready']['task'], tid)
        res = r.act('payk_fast', task=tid)
        self.assertTrue(res['fast'])
        self.assertTrue(res['message'].startswith('⏩'))
        self.assertEqual(r.get(tid)['stage'], 'treat')
        self.assertEqual(pb.count(r.state, 'laundry', 'ld_sort'), pb.FAST_NEED)   # a fast step never counts
        r.act('payk_fast', task=tid)
        self.assertEqual(r.get(tid)['stage'], 'wash')
        with self.assertRaises(GameError):   # wash was never done by hand 50 times
            r.act('payk_fast', task=tid)

    def test_a_wrong_answer_does_not_count(self):
        r = Run('laundry', slot=3, day=40)
        tid = r.c['active_task']
        while r.get(tid)['stage'] != 'wash':
            r.step(tid)
        right = r.get(tid)['_key']['wash']
        before = pb.count(r.state, 'laundry', 'ld_wash')
        r.act('ld_wash', task=tid, choices={k: 'boil' for k in right})
        self.assertEqual(pb.count(r.state, 'laundry', 'ld_wash'), before)
        r.step(tid)
        self.assertEqual(pb.count(r.state, 'laundry', 'ld_wash'), before + 1)

    def test_restore_plan_matches_its_steps(self):
        from game.careers import PLUGINS
        t = PLUGINS['restore'].make_task(10, 2, 1)
        t['known'] = True
        for st in ('inspect', 'talk', 'parts', 'clean', 'fix', 'finish', 'check', 'deliver'):
            t['stage'] = st
            action, payload = pb.FAST['restore'](t)
            self.assertEqual(action, 'phc_' + st)
            self.assertTrue(payload)


@mock.patch.dict(os.environ, ON)
class Save(unittest.TestCase):
    def test_validate(self):
        s = story()
        s['journey'][pb.KEY] = dict(v=1, tool={'laundry': 6})
        with self.assertRaises(GameError):
            validate_state(s)
        s['journey'][pb.KEY] = dict(v=1, bogus=1)
        with self.assertRaises(GameError):
            validate_state(s)
        s['journey'][pb.KEY] = dict(v=1, tool={'laundry': 2}, book=['laundry'], fast=['laundry'], st={'laundry': {'ld_sort': 50}},
                                    wk=dict(d='2026-10-25', n=3, got=0, s=1, last='2026-10-24'))
        validate_state(s)

    def test_public_views(self):
        r = Run()
        v = public_state(r.state)
        self.assertIsNone(v['payweek'])
        self.assertEqual(v['careers']['laundry']['paykit']['raise_pct'], 20)
        with mock.patch.dict(os.environ, {'MNL_PAYWEEK_FROM': WEEK[0], 'MNL_PAYWEEK_UNTIL': WEEK[1]}), \
                mock.patch.object(pb, 'now', return_value=IN_WEEK):
            v = public_state(r.state)
            self.assertEqual(v['payweek']['pct'], 20)
            self.assertEqual(v['payweek']['need'], pb.STREAK_JOBS)
            self.assertEqual(v['careers']['laundry']['paykit']['event_pct'], 20)


def old_tree(test, release):
    tmp = tempfile.mkdtemp(prefix='mnl-pay-')
    test.addCleanup(shutil.rmtree, tmp, True)
    try:
        data = subprocess.run(['git', 'archive', release, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                              check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {release}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


LOAD = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
s=migrate_state(json.load(sys.stdin));validate_state(s)
s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
s,_=apply_action(s,'mother_baby','end_day',{'carry_event':True})
validate_state(s)
print(json.dumps(s['journey'].get('paykit'),sort_keys=True))
'''


@mock.patch.dict(os.environ, ON)
class Compat(unittest.TestCase):
    def test_live_release_keeps_the_kit(self):
        r = Run('mother_baby', s=story(1))
        r.fund(10**5)
        r.act('payk_buy', item='tool')
        r.act('payk_buy', item='book')
        r.state['journey'][pb.KEY]['wk'] = dict(d='2026-10-25', n=2, got=0, s=0, last='')
        validate_state(r.state)
        kit = json.dumps(r.state['journey'][pb.KEY], sort_keys=True)
        old = old_tree(self, LIVE)
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', LOAD], input=json.dumps(dormant_out(migrate_state(r.state))), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(out.stdout.strip().splitlines()[-1], kit)


if __name__ == '__main__':
    unittest.main()
