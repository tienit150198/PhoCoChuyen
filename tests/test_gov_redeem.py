"""⚖️ Xóa kỷ luật khai trừ (owner 22/10, player feedback #477: "có cách để làm việc tốt rồi làm đc ngành nhà nước lại";
game/promotion.py redeem_close): while journey['gov_ban'] holds, each good day closed in a career outside the state
counts one; REDEEM_DAYS of them lift the ban; every ban lifted before doubles the next one's days. The count lives in
journey['gov_redo'] (an optional key builds before ignore: their validate_ban checks gov_ban's own keys exactly)."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import gov_rules as gr
from game import jail
from game import promotion as pm
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.test_org_police import officer, org
from tests.test_promotion import day, owner

BAN = dict(v=1, t=1000, d=1, c='bribe')


def banned_owner():
    j = owner('pho')
    j.state['journey'][pm.BAN_KEY] = dict(BAN)
    validate_state(j.state)
    return j


def lines(r):
    return (r['summary'].get('promo') or {}).get('org') or []


class Redeem(unittest.TestCase):
    def test_good_days_outside_the_state_lift_the_ban(self):
        j = banned_owner()
        self.assertEqual(pm.redeem_view(j.state), dict(n=0, need=pm.REDEEM_DAYS, left=pm.REDEEM_DAYS))   # a ban from before: from 0
        for i in range(1, pm.REDEEM_DAYS):
            r = day(j)
            self.assertIn(f'{i}/{pm.REDEEM_DAYS}', ' '.join(lines(r)))
        self.assertTrue(pm.banned(j.state, 'police'))
        self.assertEqual(pm.redeem_view(j.state)['left'], 1)
        validate_state(j.state)
        r = day(j)
        self.assertTrue(any('Xóa kỷ luật khai trừ' in t for t in lines(r)))   # the one-time notice
        self.assertFalse(pm.banned(j.state, 'police'))
        self.assertFalse(pm.banned(j.state, 'customs'))
        self.assertIsNone(pm.redeem_view(j.state))
        self.assertEqual(j.state['journey'][pm.REDO_KEY], dict(v=1, n=0, r=1, b=0))
        self.assertTrue(next(x for x in gr.entry_rows(j.state) if x['id'] == 'ban')['met'])
        validate_state(j.state)
        r = day(j)
        self.assertFalse(any('⚖️' in t or '🕊️' in t for t in lines(r)))     # nothing more once lifted

    def test_a_weak_day_does_not_count(self):
        j = banned_owner()
        day(j, done=1)
        self.assertEqual(pm.redeem_view(j.state)['n'], 0)
        day(j)
        self.assertEqual(pm.redeem_view(j.state)['n'], 1)

    def test_jailed_abandoned_or_a_state_career_does_not_count(self):
        j = banned_owner()
        s, c = j.state, j.c
        good = dict(promo=dict(good=True))
        self.assertEqual(pm.redeem_close(s, c, 'police', good), [])
        self.assertEqual(pm.redeem_close(s, c, 'customs', good), [])
        self.assertEqual(pm.redeem_close(s, c, 'pho', dict(good, abandon=dict(n=1))), [])
        self.assertEqual(pm.redeem_close(s, c, 'pho', dict(promo=dict(good=False))), [])
        self.assertEqual(pm.redeem_close(s, c, 'pho', {}), [])
        s['journey']['story'] = True
        with mock.patch.object(jail, 'off', return_value=False):
            jail.arrest(s['journey'], 'bm', 1)
            self.assertTrue(jail.active(s['journey']))
            self.assertEqual(pm.redeem_close(s, c, 'pho', good), [])
        self.assertNotIn(pm.REDO_KEY, s['journey'])
        s['journey'].pop(jail.KEY)
        self.assertTrue(pm.redeem_close(s, c, 'pho', good))
        self.assertEqual(pm.redeem_view(s)['n'], 1)

    def test_no_ban_nothing_written(self):
        j = owner('pho')
        day(j)
        self.assertNotIn(pm.REDO_KEY, j.state['journey'])

    def test_a_ban_after_a_lifted_one_needs_twice_the_days(self):
        j = banned_owner()
        s = j.state
        for _ in range(pm.REDEEM_DAYS):
            pm.redeem_close(s, j.c, 'pho', dict(promo=dict(good=True)))
        self.assertFalse(pm.banned(s, 'police'))
        s['journey'][pm.BAN_KEY] = dict(BAN, t=2000)
        self.assertEqual(pm.redeem_view(s), dict(n=0, need=2 * pm.REDEEM_DAYS, left=2 * pm.REDEEM_DAYS))
        pm.redeem_close(s, j.c, 'pho', dict(promo=dict(good=True)))
        self.assertEqual(pm.redeem_view(s)['n'], 1)
        self.assertEqual(s['journey'][pm.REDO_KEY]['b'], 2000)
        validate_state(s)
        self.assertEqual([pm.redeem_need(r) for r in range(5)], [15, 30, 60, 60, 60])

    def test_a_new_ban_starts_its_count_again(self):
        j = banned_owner()
        s = j.state
        for _ in range(3):
            pm.redeem_close(s, j.c, 'pho', dict(promo=dict(good=True)))
        s['journey'][pm.BAN_KEY] = dict(BAN, t=5000)   # an older build lifted nothing; a new ban was laid
        self.assertEqual(pm.redeem_view(s)['n'], 0)

    def test_the_refusal_and_the_job_screen_say_how_far(self):
        j = banned_owner()
        for _ in range(4):
            day(j)
        s = copy.deepcopy(j.state)
        s['current'] = 'police'
        v = public_state(s)['careers']['police']['job']['gov_ban']
        self.assertEqual((v['n'], v['need'], v['left']), (4, 15, 11))
        self.assertIn('Còn 11 ngày làm việc tốt', v['text'])
        with self.assertRaises(GameError) as e:
            apply_action(s, 'police', 'job_apply', {'posting': 'x'})
        self.assertEqual(e.exception.code, 'gov_banned')
        self.assertIn('Còn 11 ngày làm việc tốt nữa (4/15)', str(e.exception))
        row = next(x for x in gr.entry_rows(s) if x['id'] == 'ban')
        self.assertFalse(row['met'])
        self.assertIn('còn 11 ngày', row['label'])
        self.assertNotIn('gov_ban', public_state(j.state)['careers']['pho'].get('job') or {})

    def test_bad_counts_are_refused(self):
        j = banned_owner()
        for bad in (dict(v=1, n=0, r=0), dict(v=2, n=0, r=0, b=0), dict(v=1, n=16, r=0, b=1000), dict(v=1, n=0, r=0, b=0, x=1),
                    dict(v=1, n=-1, r=0, b=0), [1]):
            s = copy.deepcopy(j.state)
            s['journey'][pm.REDO_KEY] = bad
            with self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['journey'][pm.REDO_KEY] = dict(v=1, n=29, r=1, b=1000)
        validate_state(s)

    def test_an_expulsion_tells_the_way_back(self):
        j = officer('to_truong', 'thuong_uy')
        rec = pm.record(j.state, 'police')
        pm.mark_expel(rec, org(j), j.state, 'bribe')
        r = j.act('end_day', carry_event=True)
        self.assertTrue(pm.banned(j.state, 'police'))
        self.assertTrue(any(f'{pm.REDEEM_DAYS} ngày làm việc tốt ở nghề khác' in t for t in lines(r)))
        self.assertNotIn(pm.REDO_KEY, j.state['journey'])
        validate_state(j.state)


class Rollback(unittest.TestCase):
    """The build before (MNL_LIVE_TREE, 2.5.2.x): a save banned with a count (journey['gov_redo']) and one lifted load
    there, play a day and come back with the count kept."""

    def test_counted_and_lifted_saves_cross_the_build_before(self):
        old = os.environ.get('MNL_LIVE_TREE')
        if not old or not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        a = banned_owner()
        for _ in range(3):
            day(a)
        b = banned_owner()
        for _ in range(pm.REDEEM_DAYS):
            pm.redeem_close(b.state, b.c, 'pho', dict(promo=dict(good=True)))
        for s in (a.state, b.state):
            validate_state(s)
            prog = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state,migrate_state\n'
                    's=migrate_state(json.load(sys.stdin),True)\nvalidate_state(s)\ncur=s["current"]\npublic_state(s)\n'
                    'c=s["careers"][cur]\n'
                    'if c["open"]:\n s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
                    's,_=apply_action(s,cur,"start_day",{})\npublic_state(s)\nprint(json.dumps(s))')
            out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old,
                                 env=dict(os.environ, PYTHONPATH=old, PYTHONUTF8='1'), encoding='utf-8')
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            back = migrate_state(json.loads(out.stdout))
            validate_state(back)
            self.assertEqual(back['journey'][pm.REDO_KEY], s['journey'][pm.REDO_KEY])
            self.assertEqual(pm.banned(back, 'police'), pm.banned(s, 'police'))


if __name__ == '__main__':
    unittest.main()
