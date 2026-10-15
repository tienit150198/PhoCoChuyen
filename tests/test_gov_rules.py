"""⚖️ Điều lệnh cán bộ (owner spec 14/10, II. Bổ sung cập nhật nghề Công an; game/gov_rules.py, game/org.py discipline and the
hồ sơ công tác): Giám đốc CATP needs at most 6 violations in the whole service; an officer bailing out a friend / spouse /
fiancé(e) is giáng 2 bậc hàm + kỷ luật 15 ngày; an officer found gambling at Chợ đen giáng 1 bậc hàm + kỷ luật 10 ngày."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import gov_rules as gr
from game import org as ORG
from game import org_content as OC
from game import promotion as pm
from game.employment import hired_record
from game.engine import GameError, apply_action, dormant_out, migrate_state, public_state, validate_state
from tests.test_fair import Dice, FairBase, story
from tests.test_jail import StoreBase
from tests.test_org_police import answer_due, gi, officer, org, view
from tests.test_promotion import day

O = OC.ORGS['cand']


def grade(x):
    return O['grades'][x['g']]['id']


def svc(s, career='police'):
    return ORG.svc_count(s, career)


class ServiceRecord(unittest.TestCase):
    def test_every_violation_is_counted_across_the_service(self):
        j = officer('to_truong', 'thuong_uy')
        self.assertEqual(svc(j.state), 0)
        self.assertNotIn(ORG.SVC_KEY, j.state['journey'])
        pm.violation(j.state, j.c, 'police', 'skip_step', 'a')
        self.assertEqual(svc(j.state), 1)
        self.assertEqual(j.state['journey'][ORG.SVC_KEY], dict(v=1, police=1))
        pm.violation(j.state, j.c, 'police', 'skip_step', 'a')          # the same key the same day: nothing new
        self.assertEqual(svc(j.state), 1)
        pm.bribe(j.state, j.c, 'police', 'b')
        self.assertEqual(svc(j.state), 2)
        ORG.own(org(j), j.state, j.c, ORG.ext_of(pm.record(j.state, 'police'), org(j)))   # owning up: the same fault
        self.assertEqual(svc(j.state), 2)
        pm.case_grave(j.state, j.c, 'police', 'kidnap', 15, 'kidnap')
        self.assertEqual(svc(j.state), 3)
        validate_state(j.state)
        self.assertEqual(view(j)['org']['svc'], 3)

    def test_a_record_from_before_starts_from_its_own_log(self):
        j = officer('to_truong', 'thuong_uy')
        x = org(j)
        x['wlog'] = [dict(d=1, k='warn', c='skip_step'), dict(d=2, k='warn', c='unfair'), dict(d=2, k='demote', c='warn4'),
                     dict(d=3, k='bribe', c='bribe'), dict(d=3, k='demote', c='bribe'), dict(d=4, k='own', c='bribe_owned'),
                     dict(d=4, k='warn', c='bribe_owned'), dict(d=5, k='demote', c='kidnap'), dict(d=9, k='expire', c='clean')]
        self.assertEqual(svc(j.state), 4)   # two warnings, an envelope, a grave case
        pm.violation(j.state, j.c, 'police', 'skip_step', 'z')
        self.assertEqual(j.state['journey'][ORG.SVC_KEY]['police'], 5)

    def test_tampered_record_is_refused(self):
        j = officer()
        for bad in (dict(v=2, police=1), dict(v=1, police=-1), dict(v=1, pilot=1), dict(v=1, police='1'), [1]):
            s = copy.deepcopy(j.state)
            s['journey'][ORG.SVC_KEY] = bad
            with self.assertRaises(GameError, msg=str(bad)):
                validate_state(s)


class GiamDoc(unittest.TestCase):
    """Bổ nhiệm Giám đốc CATP: hồ sơ công tác không quá 6 hành vi vi phạm."""

    def setUp(self):
        from game import cand_roster as CR
        self.CR = CR
        CR._cache.update(at=0.0, n={})
        self.addCleanup(CR._cache.update, at=0.0, n={})

    def pgd(self, n):
        j = officer('pgd', 'dai_ta')
        x = org(j)
        x['st'], x['tip'], x['clean'] = [48] * 10, 20, 20
        j.state['journey'][ORG.SVC_KEY] = dict(v=1, police=n)
        return j

    def test_seven_violations_bar_the_appointment(self):
        j = self.pgd(7)
        rows = {r['id']: r for r in view(j)['next']['requirements']}
        self.assertFalse(rows['viol']['met'])
        self.assertIn('không quá 6', rows['viol']['label'])
        for _ in range(ORG.VAC_WAIT + 3):
            day(j)
            self.assertIsNone(org(j)['due'])
        self.assertEqual(org(j)['p'], 'pgd')

    def test_six_violations_still_qualify(self):
        j = self.pgd(6)
        self.assertTrue({r['id']: r for r in view(j)['next']['requirements']}['viol']['met'])
        for _ in range(ORG.VAC_WAIT + 3):
            if org(j)['due']:
                break
            day(j)
        self.assertEqual(org(j)['due']['to'], 'gd')
        answer_due(j)
        self.assertEqual(org(j)['p'], 'gd')
        validate_state(j.state)

    def test_a_violation_after_the_booking_stops_it_at_the_interview(self):
        j = self.pgd(6)
        for _ in range(ORG.VAC_WAIT + 3):
            if org(j)['due']:
                break
            day(j)
        self.assertEqual(org(j)['due']['to'], 'gd')
        j.state['journey'][ORG.SVC_KEY]['police'] = 7
        r = answer_due(j)
        self.assertTrue(r['later'])
        self.assertEqual(org(j)['p'], 'pgd')
        self.assertEqual(org(j)['wait'], ORG.RETRY)

    def test_the_other_posts_do_not_count_violations(self):
        j = officer('truong_phong', 'thuong_ta')
        org(j)['st'] = [48] * 10
        j.state['journey'][ORG.SVC_KEY] = dict(v=1, police=40)
        self.assertNotIn('viol', [r['id'] for r in view(j)['next']['requirements']])

    def test_rules_are_on_the_police_card(self):
        from game.careers import police
        rules = police.content()['rules']
        self.assertEqual([r['id'] for r in rules], ['gd', 'bail_kin', 'gamble', 'svc'])
        self.assertIn('giáng 2 bậc hàm, kỷ luật 15 ngày', rules[1]['text'])
        self.assertIn('giáng 1 bậc hàm, kỷ luật 10 ngày', rules[2]['text'])


def story_officer(wallet=100000, grade_id='thuong_uy', post='to_truong'):
    s = story(wallet)
    s['careers']['police']['job'] = hired_record('police')
    rec, x = pm.org_live(s, s['careers']['police'], 'police', True)
    x['p'], x['g'] = post, gi(grade_id)
    validate_state(s)
    return s


def police_x(s):
    return pm.record(s, 'police')['org']


class Gamble(FairBase):
    def bc(self, s, **extra):
        self.dice(Dice(faces=['cua', 'tom', 'ca']))
        return apply_action(s, None, 'fair_bc', dict(bets={'cua': 2}, **extra))

    def test_a_citizen_plays_as_before(self):
        s, r = self.bc(story(100))
        self.assertNotIn('cop_discipline', r)
        s, r = self.bc(s, cop_ok=True)   # the flag means nothing for a citizen
        validate_state(s)

    def test_an_officer_is_asked_first(self):
        s = story_officer()
        with self.assertRaises(GameError) as e:
            self.bc(s)
        self.assertEqual(e.exception.code, 'cop_gamble')
        self.assertIn('giáng 1 bậc hàm, kỷ luật 10 ngày', e.exception.message)
        self.assertEqual(s['journey']['wallet'], 100000)
        # the free stalls are not gambling
        s2, _ = apply_action(s, None, 'fair_ring_start', {})
        validate_state(s2)

    def test_found_out_giang_1_bac_ky_luat_10_ngay_once_a_working_day(self):
        s = story_officer()
        with mock.patch.object(gr, '_roll', lambda key, p: True):
            s, r = self.bc(s, cop_ok=True)
            self.assertEqual(s['journey']['wallet'], 100000 - 2 + r['fair']['back'])   # the round itself played
            x = police_x(s)
            self.assertEqual(grade(x), 'trung_uy')
            self.assertEqual(pm.record(s, 'police')['cx']['hold'], 10)
            self.assertIn('Kỷ luật 10 ngày', r['message'])
            self.assertEqual(svc(s), 1)
            s, r = self.bc(s, cop_ok=True)                                   # the same working day: once
            self.assertNotIn('cop_discipline', r)
            self.assertEqual(grade(police_x(s)), 'trung_uy')
        validate_state(s)

    def test_not_found_out_nothing_happens(self):
        s = story_officer()
        with mock.patch.object(gr, '_roll', lambda key, p: False):
            s, r = self.bc(s, cop_ok=True)
        self.assertEqual(grade(police_x(s)), 'thuong_uy')
        self.assertEqual(svc(s), 0)

    def test_the_raid_catching_an_officer_is_certain(self):
        s = story_officer()
        r = {'fair': {'arrest': {'fine': 1}}, 'message': ''}
        with mock.patch.object(gr, '_roll', lambda key, p: False):
            gr.gamble_after(s, r, 0)
        self.assertEqual(grade(police_x(s)), 'trung_uy')

    def test_a_part_time_helper_is_no_officer(self):
        s = story(100)
        s['careers']['police']['job'] = hired_record('police', 'cap-td')
        s, r = self.bc(s)
        validate_state(s)


class BailKin(StoreBase):
    def make_officer(self, tok, grade_id='thuong_uy', post='to_truong'):
        def fn(s):
            s['careers']['police']['job'] = hired_record('police')
            rec, x = pm.org_live(s, s['careers']['police'], 'police', True)
            x['p'], x['g'] = post, gi(grade_id)
        self.mr._mutate(self.store, {self.sid(tok): fn})

    def test_an_officer_is_told_the_rule_then_disciplined(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        self.jail(ann)
        self.make_officer(bob)
        out = self.act(bob, 'jail_bail', code=self.code(ann))
        self.assertTrue(out['cop_rule'])
        self.assertIn('giáng 2 bậc hàm, kỷ luật 15 ngày', out['message'])
        self.assertTrue(self.state(ann)['journey']['jail'])                  # nothing done yet
        self.assertEqual(self.state(bob)['journey']['wallet'], 50000)
        out = self.act(bob, 'jail_bail', code=self.code(ann), officer_ok=True)
        self.assertNotIn('jail', self.state(ann)['journey'])
        sb = self.state(bob)
        self.assertEqual(sb['journey']['wallet'], 20000)
        x = pm.record(sb, 'police')['org']
        self.assertEqual(grade(x), 'thieu_uy')                               # Thượng úy → Trung úy → Thiếu úy
        self.assertEqual(pm.record(sb, 'police')['cx']['hold'], 15)
        self.assertEqual(svc(sb), 1)
        self.assertIn('Kỷ luật 15 ngày', out['message'])
        validate_state(sb)

    def test_a_citizen_bails_as_before(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        self.jail(ann)
        out = self.act(bob, 'jail_bail', code=self.code(ann))
        self.assertNotIn('cop_rule', out)
        self.assertNotIn('jail', self.state(ann)['journey'])


class Rollback(unittest.TestCase):
    """A rollback (MNL_LIVE_TREE: the build before, 2.4.24): a save with a hồ sơ công tác count and a kỷ luật (wlog and
    hist rows coded bail_kin / gamble, a held grade) loads there, plays a day, and comes back here."""

    def test_disciplined_saves_cross_the_build_before(self):
        old = os.environ.get('MNL_LIVE_TREE')
        if not old or not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        j = officer('to_truong', 'thuong_uy')
        pm.violation(j.state, j.c, 'police', 'skip_step', 'a')
        self.assertTrue(pm.discipline(j.state, j.c, 'police', 2, 15, 'bail_kin', 'bail-x'))
        self.assertTrue(pm.discipline(j.state, j.c, 'police', 1, 10, 'gamble', 'gamble-x'))
        s = copy.deepcopy(j.state)
        validate_state(s)
        self.assertEqual(s['journey'][ORG.SVC_KEY]['police'], 3)
        prog = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state\n'
                's=json.load(sys.stdin)\nvalidate_state(s)\ncur=s["current"]\npublic_state(s)\n'
                'c=s["careers"][cur]\n'
                'if c["open"]:\n s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
                's,_=apply_action(s,cur,"start_day",{})\npublic_state(s)\nprint(json.dumps(s))')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(dormant_out(s)), capture_output=True, text=True, cwd=old,
                             env=dict(os.environ, PYTHONPATH=old, PYTHONUTF8='1'), encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))   # 💤 customs (never used here) woken again
        validate_state(back)
        self.assertEqual(back['journey'][ORG.SVC_KEY], s['journey'][ORG.SVC_KEY])
        self.assertEqual(grade(back['journey']['promo']['police']['org']), grade(s['journey']['promo']['police']['org']))


if __name__ == '__main__':
    unittest.main()
