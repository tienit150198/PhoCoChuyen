"""🎖️ Longer ladders (F#193) and the 🏢 Phòng điều hành (game/promotion.py, game/promotion_office.py).

The rollback test runs the live release's validate_state (MNL_LIVE_TREE, e.g. an archive of 7b3b72c) on saves this
build writes: steps above 4 and the office must stay invisible to it."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from game import promotion as pm
from game import promotion_content as PC
from game import promotion_office as OF
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey
from tests.test_promotion import best, day, story

ROOT = Path(__file__).resolve().parents[1]


def due(j):
    return pm._due(pm.record(j.state, j.career))


def until_due(j, cap=60, office=False):
    for _ in range(cap):
        if office:
            office_day(j)
        else:
            day(j)
        if due(j):
            return
    raise AssertionError('no review came')


def pass_review(j):
    for q in list(due(j)['qs']):
        r = j.act('pm_answer', question=q, option=best(q))
    return j.act('pm_ask', ask='base')


def worker(cid='pilot'):
    j = Journey(cid)
    story(j)
    j.c['metrics']['served'] = 400
    return j


def at(cid, step, open_day=True):
    """A hired worker already at `step` (stored the way this build stores it), the day reopened so the office rolls."""
    j = worker(cid)
    rec = pm.record(j.state, cid, True)
    pm._sync(rec, j.c)
    rec['rank'] = min(step, pm.TOP)
    if step > pm.TOP:
        rec['hi'] = dict(n=step - pm.TOP, due=None, log=[])
    j.act('end_day', carry_event=True)
    if open_day:
        j.act('start_day')
    return j


def office(j):
    return public_state(j.state)['careers'][j.career]['promo']['office']


def office_state(j):
    return pm.record(j.state, j.career)['office']


def plan_well(j):
    """Fill the board the careful way: the hardest slots first, the most skilled person allowed."""
    v = office(j)
    for sl in sorted(v['slots'], key=lambda x: (x['need'] is None, x['i'])):
        if sl['who'] is not None:
            continue
        v = office(j)
        taken = {x['who'] for x in v['slots'] if x['who'] is not None}
        for st in sorted(v['staff'], key=lambda m: -m['sk']):
            if st['i'] in taken or st['off'] or st['rest'] or st['r'] != sl['role']:
                continue
            try:
                j.act('pm_of_plan', slot=sl['i'], mate=st['i'])
                break
            except GameError:
                continue


def answer_inbox_well(j):
    for it in office(j)['inbox']:
        x = OF.INBOX_INDEX[j.career][office_state(j)['inbox'][it['i']]['id']]
        good = next(o['id'] for o in x['options'] if o['good'])
        j.act('pm_of_inbox', item=it['i'], option=good)


def office_day(j):
    if not j.c['open']:
        j.act('start_day')
    if pm._office(j.state, j.c, j.career)[1]:
        plan_well(j)
        answer_inbox_well(j)
    return day(j)


class Ladders(unittest.TestCase):
    def test_tops_by_career(self):
        from game.engine import CAREERS
        for cid in CAREERS:
            t = pm.top(cid)
            self.assertEqual(t, {'pilot': 7, 'teacher': 5}.get(cid, 4), cid)
            if pm.track(cid) == 'emp':
                self.assertGreaterEqual(len(PC.EMP_TITLES.get(cid, PC.EMP_TITLES['repair'])), t, cid)
            self.assertLess(t, len(pm.EMP_STEPS))

    def test_pilot_titles_and_insignia(self):
        j = worker()
        names = [pm.title(j.state, j.c, 'pilot', n) for n in range(8)]
        self.assertEqual(names, ['Cơ phó cấp thấp', 'Cơ phó cao cấp', 'Cơ trưởng', 'Cơ trưởng Huấn luyện', 'Trưởng đội bay',
                                 'Phó Giám đốc Khối khai thác bay', 'Giám đốc Khối khai thác bay', 'Phó Tổng Giám đốc'])
        labels = [PC.insignia_label(x) for x in PC.INSIGNIA['pilot']]
        self.assertEqual(labels[:5], ['1 gạch', '2 gạch', '3 gạch', '4 gạch', '4 gạch · 1 sao'])
        self.assertEqual(len(set(labels)), 8)
        v = pm.public(j.state, j.c, 'pilot')
        self.assertEqual((v['title'], v['top'], v['insignia']['g']), ('Cơ phó cấp thấp', 7, 1))
        self.assertEqual(v['office_title'], 'Phó Giám đốc Khối khai thác bay')
        # The simulator posting keeps its own title at step 0.
        j.c['job']['employer'] = 'pl-sim'
        self.assertNotEqual(pm.title(j.state, j.c, 'pilot', 0), 'Cơ phó cấp thấp')

    def test_teacher_reaches_principal(self):
        j = worker('teacher')
        self.assertEqual(pm.title(j.state, j.c, 'teacher', 5), 'Hiệu trưởng')
        v = pm.public(j.state, j.c, 'teacher')
        self.assertEqual((v['top'], v['badge']), (5, '🍎'))
        self.assertEqual(pm.public(*(lambda x: (x.state, x.c))(worker('delivery')), 'delivery')['top'], 4)

    def test_existing_top_rank_is_kept_and_can_go_on(self):
        """A Trưởng đội bay from before this build: rank 4, no 'hi'. Nothing is rewritten; the next step opens."""
        j = at('pilot', 4)
        rec = pm.record(j.state, 'pilot')
        rec['good'] = rec['worked'] = 30   # good days kept counting at the old top
        self.assertNotIn('hi', rec)
        self.assertEqual(pm.public(j.state, j.c, 'pilot')['next']['title'], 'Phó Giám đốc Khối khai thác bay')
        r = day(j)
        self.assertIn('Phó Giám đốc', r['summary']['promo']['line'])
        rec = pm.record(j.state, 'pilot')
        self.assertEqual((rec['rank'], rec['due'], rec['hi']['due']['to']), (4, None, 5))
        self.assertTrue(all(q.startswith('x') for q in rec['hi']['due']['qs']))   # the board's own questions
        validate_state(j.state)
        r = pass_review(j)
        self.assertTrue(r['celebrate'])
        self.assertIn('Phòng điều hành bay', r['message'])
        rec = pm.record(j.state, 'pilot')
        self.assertEqual((rec['rank'], rec['hi']['n'], pm.rank(j.state, j.c, 'pilot')), (4, 1, 5))
        self.assertEqual(pm.raise_pct(j.state, j.c, 'pilot'), 45)
        self.assertEqual(pm.public(j.state, j.c, 'pilot')['insignia']['s'], 2)
        validate_state(j.state)

    def test_other_careers_still_stop_at_four(self):
        j = at('delivery', 4)
        rec = pm.record(j.state, 'delivery')
        rec['good'] = rec['worked'] = 40
        day(j)
        self.assertIsNone(due(j))
        self.assertIsNone(pm.public(j.state, j.c, 'delivery')['next'])
        self.assertNotIn('office', pm.public(j.state, j.c, 'delivery'))

    def test_pilot_climbs_to_the_cap(self):
        j = at('pilot', 4)
        for step in (5, 6, 7):
            until_due(j, cap=80, office=True)
            pass_review(j)
            self.assertEqual(pm.rank(j.state, j.c, 'pilot'), step)
            validate_state(j.state)
        rec = pm.record(j.state, 'pilot')
        self.assertEqual(rec['rank'], 4)
        self.assertEqual([x['to'] for x in rec['hi']['log']], [5, 6, 7])
        self.assertIsNone(pm.public(j.state, j.c, 'pilot')['next'])
        self.assertEqual(pm.public(j.state, j.c, 'pilot')['title'], 'Phó Tổng Giám đốc')
        top = pm.public(j.state, j.c, 'pilot')['insignia']
        self.assertTrue(top['big'] and top['wing'])   # F#207: one big star on a wing
        self.assertEqual(top['label'], '1 sao lớn · cánh chim vàng')

    def test_office_days_gate_the_director_step(self):
        j = at('pilot', 5)
        rec = pm.record(j.state, 'pilot')
        rec['good'] = rec['worked'] = 40
        nxt = pm.public(j.state, j.c, 'pilot')['next']
        self.assertIn('office', [r['id'] for r in nxt['requirements'] if not r['met']])
        for _ in range(3):
            day(j)   # flying only: the office ran itself (the assistant), no good office day
        self.assertIsNone(due(j))
        self.assertEqual(office_state(j)['kpi']['good'], 0)
        # F#206: the close says the score, part by part, why it did not count, and the progress n/need
        r = day(j)
        lines = r['summary']['promo']['office']['lines']
        self.assertIn('📊 Điểm điều hành', lines[1])
        self.assertIn('chưa tự xếp', lines[1])
        self.assertIn('🏢 Ngày điều hành tốt: 0/5', lines[2])
        req = next(x for x in pm.public(j.state, j.c, 'pilot')['next']['requirements'] if x['id'] == 'office')
        self.assertEqual((req['got'], req['need'], req['label']), (0, 5, '🏢 Ngày điều hành tốt: 0/5'))

    def test_a_planned_good_office_day_is_counted_and_said(self):
        j = at('pilot', 5)
        r = office_day(j)
        o = r['summary']['promo']['office']
        got = office_state(j)['kpi']['good']
        self.assertEqual(got, 1 if o['good'] else 0)
        self.assertIn('✓ tính 1 ngày điều hành tốt' if o['good'] else 'cần từ 60', o['lines'][1])
        self.assertIn(f'🏢 Ngày điều hành tốt: {got}/5', o['lines'][2])
        self.assertIn(f'điểm {o["score"]}', office_state(j)['log'][-1])
        validate_state(j.state)

    def test_quitting_restarts_but_keeps_the_log(self):
        j = at('pilot', 4)
        pm.record(j.state, 'pilot')['hi'] = dict(n=2, due=None, log=[dict(d=3, to=5, pct=45), dict(d=9, to=6, pct=55)])
        j.act('end_day', carry_event=True)
        j.act('job_quit', confirm=True)
        from game.employment import hired_record
        j.c['job'] = hired_record('pilot', None, j.c['day'])
        day(j)
        rec = pm.record(j.state, 'pilot')
        self.assertEqual((pm._rank(rec), rec['hi']['n'], len(rec['hi']['log'])), (0, 0, 2))
        self.assertNotIn('office', rec)
        validate_state(j.state)


class Office(unittest.TestCase):
    def test_not_before_the_executive_step(self):
        j = at('pilot', 4)
        self.assertNotIn('office', public_state(j.state)['careers']['pilot']['promo'])
        with self.assertRaises(GameError):
            j.act('pm_of_plan', slot=0, mate=0)

    def test_board_opens_with_the_day(self):
        j = at('pilot', 5, open_day=False)
        v = public_state(j.state)['careers']['pilot']['promo']['office']
        self.assertTrue(v.get('wait'))
        j.act('start_day')
        v = office(j)
        self.assertTrue(v['live'])
        self.assertEqual((len(v['slots']), len(v['staff']), len(v['inbox']), v['left']), (4, 6, 1, 4))
        self.assertEqual(sum(1 for s in v['slots'] if s['need']), 2)
        self.assertEqual([a['id'] for a in v['acts']], list(OF.BASIC))
        self.assertTrue(all(s['hint'] is None for s in v['staff']))   # traits stay hidden
        self.assertTrue(all('tr' not in m for m in v['staff']))
        self.assertFalse(any(f'"{tr}"' in json.dumps(v) for tr in OF.TRAITS))
        j.act('end_day', carry_event=True)
        with self.assertRaises(GameError) as e:
            j.act('pm_of_plan', slot=0, mate=0)
        self.assertEqual(e.exception.code, 'office_closed')

    def test_plan_rules(self):
        j = at('pilot', 5)
        v = office(j)
        hard = next(s for s in v['slots'] if s['need'])
        easy = next(s for s in v['slots'] if not s['need'])
        rookie = next(m for m in v['staff'] if m['t'] == 'Cơ phó cấp thấp')
        with self.assertRaises(GameError):
            j.act('pm_of_plan', slot=hard['i'], mate=rookie['i'])   # needs a captain
        j.act('pm_of_plan', slot=easy['i'], mate=rookie['i'])
        other = next(s for s in v['slots'] if not s['need'] and s['i'] != easy['i'])
        with self.assertRaises(GameError):
            j.act('pm_of_plan', slot=other['i'], mate=rookie['i'])  # one rotation a day
        j.act('pm_of_plan', slot=easy['i'], mate=None)
        self.assertIsNone(office(j)['slots'][easy['i']]['who'])
        for bad in (dict(slot=99, mate=0), dict(slot='0', mate=0), dict(slot=0, mate=99)):
            with self.assertRaises(GameError):
                j.act('pm_of_plan', **bad)
        # Three days running, then a day of rest by law.
        off = office_state(j)
        off['staff'][rookie['i']]['duty'] = OF.DUTY_MAX
        with self.assertRaises(GameError) as e:
            j.act('pm_of_plan', slot=easy['i'], mate=rookie['i'])
        self.assertIn('nghỉ', str(e.exception))

    def test_office_moves_do_not_tick_the_turn(self):
        j = at('pilot', 5)
        turn = j.c['turn']
        j.act('pm_of_hr', mate=0, act='talk')
        self.assertEqual(j.c['turn'], turn)

    def test_powers_grow_with_the_step(self):
        j = at('pilot', 5)
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=4, act='promote')
        j = at('pilot', 6)
        self.assertEqual([a['id'] for a in office(j)['acts']], list(OF.FULL))
        self.assertEqual(office(j)['left'], 5)
        title = office(j)['staff'][4]['t']
        cost = office(j)['kpi']['cost']
        j.act('pm_of_hr', mate=4, act='promote')
        self.assertNotEqual(office(j)['staff'][4]['t'], title)
        self.assertGreater(office(j)['kpi']['cost'], cost)
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=4, act='raise')   # one decision per person per day
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=0, act='fire')

    def test_decision_budget_per_day(self):
        j = at('pilot', 5)
        for i in range(4):
            j.act('pm_of_hr', mate=i, act='talk')
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=4, act='talk')
        self.assertEqual(office(j)['left'], 0)

    def test_talk_reveals_the_hidden_trait(self):
        j = at('pilot', 5)
        r = j.act('pm_of_hr', mate=2, act='talk')
        tr = office_state(j)['staff'][2]['tr']
        self.assertIn(OF.TRAIT_HINT[tr], r['message'])
        self.assertEqual(office(j)['staff'][2]['hint'], OF.TRAIT_HINT[tr])
        self.assertIsNone(office(j)['staff'][3]['hint'])

    def test_discipline_with_a_reason_fixes_without_one_hurts_the_room(self):
        j = at('pilot', 5)
        off = office_state(j)
        for st in off['staff']:
            st['iss'], st['mood'] = None, 70
        off['staff'][0]['iss'] = 'late'
        room = [st['mood'] for st in off['staff']]
        r = j.act('pm_of_hr', mate=0, act='remind')
        self.assertTrue(r['just'])
        off = office_state(j)
        self.assertIsNone(off['staff'][0]['iss'])
        self.assertEqual(off['staff'][0]['mk'], 1)
        self.assertEqual([st['mood'] for st in off['staff'][1:]], room[1:])
        r = j.act('pm_of_hr', mate=1, act='warn')   # nothing wrong: unfair
        self.assertFalse(r['just'])
        off = office_state(j)
        self.assertTrue(all(st['mood'] < m for st, m in zip(off['staff'][2:], room[2:])))
        validate_state(j.state)

    def test_same_decision_lands_differently_by_trait(self):
        moods = {}
        for tr in ('proud', 'lazy'):
            j = at('pilot', 5)
            off = office_state(j)
            st = off['staff'][0]
            st.update(tr=tr, iss='rude', mk=1, mood=70)
            j.act('pm_of_hr', mate=0, act='warn')
            moods[tr] = office_state(j)['staff'][0]['mood']
        self.assertLess(moods['proud'], moods['lazy'])

    def test_tired_is_not_a_fault(self):
        j = at('pilot', 5)
        st = office_state(j)['staff'][1]
        st.update(iss='tired', mk=0, mood=60)
        r = j.act('pm_of_hr', mate=1, act='remind')
        self.assertFalse(r['just'])
        self.assertEqual(office_state(j)['staff'][1]['iss'], 'tired')

    def test_pushed_too_far_someone_quits(self):
        j = at('pilot', 6)
        off = office_state(j)
        st = off['staff'][5]
        st.update(mood=12, tr='fragile', iss=None, mk=0)
        old = st['n']
        r = j.act('pm_of_hr', mate=5, act='cut' if st['pay'] > 1 else 'review')
        self.assertIn('nộp đơn nghỉ', r['message'])
        new = office_state(j)['staff'][5]
        self.assertNotEqual(new['n'], old)
        self.assertEqual((new['lv'], new['pay']), (0, 1))
        validate_state(j.state)

    def test_suspension_takes_them_off_the_board(self):
        j = at('pilot', 6)
        off = office_state(j)
        st = off['staff'][3]
        st.update(iss='slip', mk=2, mood=80)
        easy = next(s for s in office(j)['slots'] if not s['need'])
        j.act('pm_of_plan', slot=easy['i'], mate=3)
        r = j.act('pm_of_hr', mate=3, act='suspend')
        self.assertTrue(r['just'])
        self.assertIsNone(office(j)['slots'][easy['i']]['who'])
        with self.assertRaises(GameError):
            j.act('pm_of_plan', slot=easy['i'], mate=3)
        day(j)
        j.act('start_day')
        self.assertTrue(office(j)['staff'][3]['off'])   # still home the next day
        day(j)
        j.act('start_day')
        self.assertFalse(office(j)['staff'][3]['off'])

    def test_inbox_and_default(self):
        j = at('pilot', 6)
        v = office(j)
        self.assertEqual(len(v['inbox']), 2)
        self.assertTrue(all('{a}' not in it['text'] for it in v['inbox']))
        it = v['inbox'][0]
        x = OF.INBOX_INDEX['pilot'][office_state(j)['inbox'][it['i']]['id']]
        good = next(o['id'] for o in x['options'] if o['good'])
        j.act('pm_of_inbox', item=it['i'], option=good)
        with self.assertRaises(GameError):
            j.act('pm_of_inbox', item=it['i'], option=good)
        self.assertEqual(len(office(j)['inbox']), 1)
        day(j)   # the other one takes its last option at the close
        self.assertTrue(all(i['pick'] for i in office_state(j)['inbox']))

    def test_giving_in_is_never_rewarded(self):
        for career, rows in OF.INBOX.items():
            for x in rows:
                good = [o for o in x['options'] if o['good']]
                self.assertEqual(len(good), 1, x['id'])
                worst = x['options'][-1]
                self.assertFalse(worst['good'], x['id'])
                g = good[0]['fx']
                for o in x['options']:
                    if o['good']:
                        continue
                    f = o['fx']
                    self.assertTrue(f.get('mood', 0) < g.get('mood', 0) or f.get('compl', 0) > g.get('compl', 0)
                                    or f.get('ontime', 0) < g.get('ontime', 0) or f.get('a', 0) < g.get('a', 0)
                                    or f.get('cost', 0) > g.get('cost', 0), (x['id'], o['id']))

    def test_the_close_pays_only_a_board_the_player_ran(self):
        j = at('pilot', 5)
        money = j.c['money']
        r = day(j)
        o = r['summary']['promo']['office']
        self.assertEqual(o['bonus'], 0)
        self.assertIn('trợ lý xếp tạm', o['lines'][0])
        j.act('start_day')
        plan_well(j)
        answer_inbox_well(j)
        r = day(j)
        o = r['summary']['promo']['office']
        self.assertGreater(o['bonus'], 0)
        self.assertLessEqual(o['bonus'], OF.OFFICE['pilot']['cap'][5])
        ledger = j.c['ops']['finance']['ledger']
        self.assertTrue(any(x['reason'].startswith('🏢 Thưởng điều hành') and x['amount'] == o['bonus'] for x in ledger))
        self.assertGreater(j.c['money'], money)
        validate_state(j.state)

    def test_careful_management_beats_neglect(self):
        def run(careful):
            j = at('pilot', 5)
            for _ in range(8):
                if not j.c['open']:
                    j.act('start_day')
                if careful:
                    plan_well(j)
                    answer_inbox_well(j)
                else:
                    v = office(j)
                    for it in v['inbox']:
                        x = OF.INBOX_INDEX['pilot'][office_state(j)['inbox'][it['i']]['id']]
                        j.act('pm_of_inbox', item=it['i'], option=x['options'][-1]['id'])
                day(j)
            return office_state(j)['kpi']
        good, bad = run(True), run(False)
        self.assertGreater(good['good'], bad['good'])
        self.assertLess(good['compl'], bad['compl'])

    def test_deputy_ceo_runs_every_member_of_staff(self):
        j = at('pilot', 7)
        v = office(j)
        self.assertEqual(len(v['staff']), 12)
        self.assertEqual({m['r'] for m in v['staff']}, {'pl', 'fa', 'op', 'en'})
        self.assertEqual(len(v['slots']), 7)
        fa = next(s for s in v['slots'] if s['role'] == 'fa')
        pilot = next(m for m in v['staff'] if m['r'] == 'pl')
        with self.assertRaises(GameError):
            j.act('pm_of_plan', slot=fa['i'], mate=pilot['i'])
        plan_well(j)
        self.assertTrue(all(s['who'] is not None for s in office(j)['slots']))
        validate_state(j.state)
        self.assertLess(len(json.dumps(public_state(j.state)['careers']['pilot']['promo'], ensure_ascii=False)), 12000)

    def test_principal_office(self):
        j = at('teacher', 5)
        v = office(j)
        self.assertEqual(v['name'], 'Phòng hiệu trưởng')
        self.assertEqual([a['id'] for a in v['acts']], list(OF.FULL))
        self.assertEqual(len(v['inbox']), 2)
        plan_well(j)
        answer_inbox_well(j)
        r = day(j)
        self.assertIn('Phòng hiệu trưởng', r['summary']['promo']['office']['lines'][0])
        validate_state(j.state)


class Saves(unittest.TestCase):
    def test_tampering_is_refused(self):
        j = at('pilot', 7)
        plan_well(j)
        validate_state(j.state)
        for path, value in ((('rank',), 5), (('hi', 'n'), 4), (('hi', 'log'), [dict(d=1, to=3, pct=1)]), (('hi', 'x'), 1),
                            (('office', 'staff', 0, 'lv'), 9), (('office', 'staff', 0, 'tr'), 'saint'), (('office', 'plan', 0), 99),
                            (('office', 'left'), 99), (('office', 'kpi', 'ontime'), 101), (('office', 'inbox', 0, 'id'), 'nope'),
                            (('office', 'staff', 0, 'iss'), 'drunk'), (('office', 'extra'), 1)):
            s = copy.deepcopy(j.state)
            o = s['journey']['promo']['pilot']
            for k in path[:-1]:
                o = o[k]
            o[path[-1]] = value
            with self.assertRaises(GameError, msg=repr(path)):
                validate_state(s)
        s = copy.deepcopy(j.state)   # a step above 4 on a career whose ladder stops there
        rec = pm.new_record()
        rec.update(rank=4, hi=dict(n=1, due=None, log=[]))
        s['journey']['promo']['delivery'] = rec
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)   # two reviews at once
        rec = s['journey']['promo']['pilot']
        rec['hi']['n'] = 2
        rec['hi']['due'] = dict(to=7, day=1, qs=['x1', 'x2'], ans={})
        validate_state(s)
        rec['due'] = dict(to=5, day=1, qs=['a1', 'a2'], ans={})
        with self.assertRaises(GameError):
            validate_state(s)

    def old_tree(self):
        old = os.environ.get('MNL_LIVE_TREE')
        if not old or not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        return old

    def test_saves_cross_the_live_build(self):
        """A rollback: the live build reads a save with steps above 4 and an office, plays a day, and this build
        reads what it wrote: nobody's step went down."""
        old = self.old_tree()
        prog = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state\n'
                's=json.load(sys.stdin)\nvalidate_state(s)\n'
                'cur=s["current"]\npublic_state(s)\n'
                'c=s["careers"][cur]\n'
                'if c["open"]:\n s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
                's,_=apply_action(s,cur,"start_day",{})\npublic_state(s)\n'
                'print(json.dumps(s))')
        saves = []
        j = at('pilot', 6)
        plan_well(j)
        saves.append(copy.deepcopy(j.state))
        rec = pm.record(j.state, 'pilot')
        rec['good'] = rec['worked'] = 60
        rec['office']['kpi']['good'] = 9
        day(j)
        self.assertEqual(due(j)['to'], 7)   # a review above 4 waiting
        saves.append(copy.deepcopy(j.state))
        t = at('teacher', 5)
        saves.append(copy.deepcopy(t.state))
        for s in saves:
            validate_state(s)
            env = dict(os.environ, PYTHONPATH=old)
            out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                                 encoding='utf-8')
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            back = json.loads(out.stdout)
            validate_state(back)
            cur = back['current']
            before = pm._rank(s['journey']['promo'][cur])
            self.assertEqual(pm._rank(back['journey']['promo'][cur]), before)
            back, _ = apply_action(back, cur, 'end_day', {'carry_event': True})
            back, _ = apply_action(back, cur, 'start_day', {})
            validate_state(back)


if __name__ == '__main__':
    unittest.main()
