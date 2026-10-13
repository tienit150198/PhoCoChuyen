"""Higher shared promotion tiers retain bounded pay and require real work."""
import copy
import json
import unittest

from game import promotion as pm, promotion_content as PC, promotion_office as OF
from game.content import CAREERS
from game.engine import GameError, money, validate_state
from tests.helpers import Journey
from tests.test_promotion import best, day


def at_rank(career, rank):
    j = Journey(career)
    rec = pm.record(j.state, career, True)
    if pm.track(career) == 'emp':
        pm._sync(rec, j.c)
    rec['rank'] = min(rank, pm.TOP)
    if rank > pm.TOP:
        rec['hi'] = dict(n=rank-pm.TOP, due=None, log=[])
    j.c['metrics']['served'] = 400
    return j


class PromotionEndgameTests(unittest.TestCase):
    def test_every_ordinary_career_has_seven_steps_without_changing_police(self):
        for cid in CAREERS:
            self.assertEqual(pm.top(cid), 4 if cid in pm.ORG.OC.CAREER_ORG else 7, cid)
        self.assertEqual(pm.TOP, 4)

    def test_owner_advanced_tiers_have_bounded_benefits(self):
        self.assertGreaterEqual(len(pm.OWN_STEPS), 8)
        for tier, good, served, pct, cap in ((5,24,150,15,42),(6,28,220,18,50),(7,32,300,21,60)):
            self.assertEqual(pm.OWN_STEPS[tier], dict(good=good, served=served, pct=pct, cap=cap))

    def test_nonoffice_employee_can_qualify_at_each_advanced_tier(self):
        for current in (4,5,6):
            j = at_rank('delivery', current)
            rec = pm.record(j.state, j.career)
            rec['good'] = rec['worked'] = pm.EMP_STEPS[current+1]['good']
            self.assertFalse(OF.available(j.career, current))
            self.assertTrue(pm.ready(j.state, j.c, j.career, rec))
            self.assertNotIn('office', [r['id'] for r in pm._gates(j.state, j.c, j.career, rec)])
            self.assertIsNone(pm.office_progress(j.career, rec))
            rec['good'] -= 1
            self.assertFalse(pm.ready(j.state, j.c, j.career, rec))

    def test_existing_offices_still_require_good_office_days(self):
        for cid in ('pilot','teacher'):
            for current, required in ((5,5),(6,8)):
                j = at_rank(cid, current)
                rec = pm.record(j.state, cid)
                rec['good'] = rec['worked'] = 40
                self.assertFalse(pm.ready(j.state, j.c, cid, rec))
                self.assertEqual(pm.office_progress(cid, rec), (0, required))
                rec['office'] = OF.new_office(cid, 42, j.c['day'])
                rec['office']['kpi']['good'] = required
                self.assertTrue(pm.ready(j.state, j.c, cid, rec))

    def test_empty_office_day_cannot_earn_progress_or_bonus(self):
        off = OF.new_office('teacher', 42, 1)
        OF.day_roll('teacher', off, 42, 1, 5)
        for person in off['staff']:
            person.update(sk=100, mood=100, iss=None, lv=3)
        off['budget'] = 10000
        off['plan'] = [0,1,2,3]; off['me'] = True
        for item in off['inbox']:
            item['pick'] = next(o['id'] for o in OF.INBOX_INDEX['teacher'][item['id']]['options'] if o['good'])
        paid = copy.deepcopy(off)
        good = OF.close('teacher', paid, 5, 42, 1, earned=True)
        self.assertGreaterEqual(good['score'], OF.GOOD_SCORE)
        self.assertTrue(good['good'])
        self.assertEqual(paid['kpi']['good'], 1)
        result = OF.close('teacher', off, 5, 42, 1, earned=False)
        self.assertEqual(result['bonus'], 0)
        self.assertFalse(result['good'])
        self.assertEqual(off['kpi']['good'], 0)
        self.assertNotIn('✓ tính 1 ngày điều hành tốt', result['lines'][1])

    def test_advanced_reviews_and_roundtrips_keep_legacy_rank_four(self):
        for cid in ('delivery','pho','teacher'):
            j = at_rank(cid, 4)
            for target in (5,6,7):
                rec = pm.record(j.state, cid)
                steps = pm.EMP_STEPS if pm.track(cid) == 'emp' else pm.OWN_STEPS
                rec['good'] = rec['worked'] = steps[target]['good']-1
                if steps[target].get('office') and OF.available(cid,target-1):
                    rec['office'] = OF.new_office(cid,42,j.c['day'])
                    rec['office']['kpi']['good'] = steps[target]['office']
                day(j)
                due = pm._due(pm.record(j.state, cid))
                self.assertEqual(due['to'], target)
                self.assertEqual(pm.record(j.state, cid)['rank'], 4)
                j.state = json.loads(json.dumps(j.state)); validate_state(j.state)
                for qid in list(due['qs']):
                    j.act('pm_answer', question=qid, option=best(qid))
                if pm.track(cid) == 'emp':
                    j.act('pm_ask', ask='high')
                rec = pm.record(j.state, cid)
                self.assertEqual(pm.rank(j.state, j.c, cid), target)
                self.assertEqual((rec['rank'],rec['good'],rec['worked']), (4,0,0))
                self.assertLessEqual(pm.step_pct(cid,target,rec['extra']),100)
                before = copy.deepcopy(j.state)
                with self.assertRaises(GameError): j.act('pm_answer', question=due['qs'][-1], option=best(due['qs'][-1]))
                self.assertEqual(before,j.state)
                j.state = json.loads(json.dumps(j.state)); validate_state(j.state)
            self.assertIsNone(pm.public(j.state,j.c,cid)['next'])
            self.assertEqual([r['to'] for r in pm.record(j.state,cid)['hi']['log']], [5,6,7])
            if pm.track(cid) == 'emp':
                self.assertEqual(pm.raise_pct(j.state,j.c,cid),100)

    def test_owner_tip_uses_actual_advanced_rank_and_pays_once(self):
        for tier, cap in ((7,60),(6,50),(5,42)):
            j = at_rank('pho',tier)
            money(j.state,j.c,1000,'Test sales',category='revenue')
            result = day(j)
            self.assertEqual(result['summary']['promo']['tip'],cap)
            tips = [r for r in j.c['ops']['finance']['ledger'] if str(r.get('ref','')).startswith('pm-tip-')]
            self.assertEqual([r['amount'] for r in tips],[cap])
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError): j.act('end_day',carry_event=True)
            self.assertEqual(before,j.state)

    def test_old_rank_four_record_loads_without_rewrite(self):
        j = at_rank('delivery',4)
        rec = pm.record(j.state,j.career)
        rec.update(good=17,worked=23,extra=6)
        rec['log'] = [dict(d=1,to=4,pct=61)]
        self.assertNotIn('hi',rec)
        before = copy.deepcopy(rec)
        loaded = json.loads(json.dumps(j.state)); validate_state(loaded)
        self.assertEqual(loaded['journey']['promo'][j.career],before)
        self.assertEqual(pm.public(j.state,j.c,j.career)['next']['need'],24)
        self.assertEqual(pm.record(j.state,j.career),before)

    def test_manager_size_and_pay_caps_are_unchanged_at_new_top(self):
        j = at_rank('delivery',7)
        j.act('end_day',carry_event=True);j.act('start_day',manager=True)
        sh = pm.record(j.state,j.career)['shift']
        self.assertEqual((sh['size'],len(sh['team'])),(8,3))
        self.assertEqual(pm.CAP[4],90)
        self.assertEqual(pm.OWN_CAP[4],135)


if __name__ == '__main__':
    unittest.main()
