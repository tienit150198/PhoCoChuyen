"""Teacher v2 period ("Tiết học"): roll call, plan cards, classroom moments,
helping each kid, exit tickets, kid arcs, gender title and save safety."""
import copy
import itertools
import json
import unittest

from game import classroom as C
from game import teach_lesson as TL
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey

GOOD_ROLL = {'here': 'present', 'sick': 'excused', 'late': 'let_in', 'missing': 'report'}
BEST_CALL = {x['id']: max(x['options'], key=lambda o: (not o['mistake'], sum(o['trust'].values()), o['focus']))['id'] for x in TL.INCIDENTS}


def best_plan(room):
    ok = [p for p in itertools.permutations(room['hand'], 3) if TL.plan_error(p) is None]
    return list(max(ok, key=lambda p: TL._stars(p, room['cond'], TL.need_styles(room))[0]))


def roll_all(j, tid):
    j.act('lesson_roll', task=tid, kid='all')
    for k in j.get(tid)['room']['kids']:
        if k['id'] not in j.get(tid)['room']['roll']:
            j.act('lesson_roll', task=tid, kid=k['id'], choice=GOOD_ROLL[k['status']])


def teach_all(j, tid):
    for ph in range(3):
        room = j.get(tid)['room']
        for ev in room['events']:
            if ev['phase'] == ph:
                j.act('lesson_call', task=tid, event=ev['id'], option=BEST_CALL[ev['id']])
        room = j.get(tid)['room']
        for kid in room['lost']:
            if kid not in room['helped'] and room['flags'].get(kid) != 'miss':
                j.act('lesson_help', task=tid, kid=kid, method=TL.KID[kid]['style'])
        j.act('lesson_next', task=tid)


def mark_all(j, tid):
    for kid, tk in j.get(tid)['room']['tickets'].items():
        j.act('lesson_mark', task=tid, kid=kid, mark=TL.MARK_FOR[tk['kind']])


def mark_all_left(j, tid):
    for kid, tk in j.get(tid)['room']['tickets'].items():
        if kid not in j.get(tid)['room']['marks']:
            j.act('lesson_mark', task=tid, kid=kid, mark=TL.MARK_FOR[tk['kind']])


def play(j, tid=None):
    tid = tid or j.task['id']
    roll_all(j, tid)
    j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
    teach_all(j, tid)
    mark_all(j, tid)
    return j.act('lesson_complete', task=tid, confirm=True)


def pub_task(j, tid):
    return next(t for t in public_state(j.state)['careers']['teacher']['tasks'] if t['id'] == tid)


class TeacherLessonTests(unittest.TestCase):
    def test_every_roll_is_deterministic_and_has_a_three_star_plan(self):
        for day in range(1, 41):
            for slot in range(6):
                a, b = TL.roll(day, slot), TL.roll(day, slot)
                self.assertEqual(a, b)
                styles = sorted({TL.KID[k]['style'] for k in TL.present_ids(a)})
                self.assertEqual(TL._best(a['hand'], a['cond'], styles), 3, (day, slot))
                self.assertGreaterEqual(len(TL.present_ids(a)), 4)
                self.assertIn(a['slip'], TL.present_ids(a))

    def test_difficulty_grows_with_day(self):
        easy, hard = TL.roll(1, 0), TL.roll(9, 1)
        self.assertEqual((easy['tier'], len(easy['kids']), len(easy['events']), len(easy['hand'])), (1, 5, 1, 5))
        self.assertEqual(hard['tier'], 3)
        self.assertEqual(len(hard['kids']), 7)
        self.assertEqual(len(hard['hand']), 6)
        self.assertGreaterEqual(len(hard['events']), 2)
        self.assertFalse(any(k['status'] == 'missing' for d in (1, 2) for s in range(4) for k in TL.roll(d, s)['kids']))

    def test_full_period_perfect_and_saved(self):
        j = Journey('teacher')
        tid = j.task['id']
        money = j.c['money']
        r = play(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['room']['stars'], 3)
        self.assertGreaterEqual(j.c['money'], money + t['room']['reward'])
        self.assertIn('hiểu bài', r['message'])
        led = [x for x in j.c['ops']['finance']['ledger'] if x['ref'] == tid]
        self.assertTrue(any(x['category'] == 'revenue' and x['amount'] == t['room']['reward'] for x in led))
        self.assertEqual(len(t['attendance']), len(t['students']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_answers_and_future_are_hidden(self):
        j = Journey('teacher', slot=1, day=7)
        tid = j.task['id']
        view = pub_task(j, tid)['room']
        text = json.dumps(view, ensure_ascii=False)
        for secret in ('stuck', 'slip', '"style"', '"focus"', '"mistake"', '"trust"', 'kind'):
            self.assertNotIn(secret, text)
        self.assertEqual(view['events'], [])
        roll_all(j, tid)
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        room = j.get(tid)['room']
        view = pub_task(j, tid)['room']
        self.assertTrue(all(e['phase'] == 0 for e in view['events']))
        self.assertEqual(len(view['events']), sum(e['phase'] == 0 for e in room['events']))
        for ev in view['events']:
            self.assertTrue(all(set(o) == {'id', 'label'} for o in ev['options']))
        self.assertNotIn('answer', pub_task(j, tid)['lesson'])

    def test_invalid_commands_do_not_change_state(self):
        j = Journey('teacher', slot=0, day=4)
        tid = j.task['id']
        j.act('lesson_roll', task=tid, kid='all')
        room = j.get(tid)['room']
        pending = [k for k in room['kids'] if k['id'] not in room['roll']]
        before = copy.deepcopy(j.state)
        bad = [('lesson_plan', dict(steps=best_plan(room))), ('lesson_next', {}), ('lesson_mark', dict(kid='minh', mark='praise')),
               ('lesson_complete', dict(confirm=True)), ('lesson_roll', dict(kid='nobody', choice='present')),
               ('lesson_roll', dict(kid=pending[0]['id'], choice='hack')), ('lesson_help', dict(kid='minh', method='look')),
               ('lesson_attendance', dict(student='minh', present=True))]
        for action, payload in bad:
            with self.assertRaises(GameError, msg=action):
                j.act(action, task=tid, **payload)
            self.assertEqual(j.state, before)
        for k in pending:
            j.act('lesson_roll', task=tid, kid=k['id'], choice=GOOD_ROLL[k['status']])
        room = j.get(tid)['room']
        long_plan = next(p for p in itertools.permutations(room['hand'], 3) if TL._minutes(p) > TL.PLAN_MINUTES) if any(TL._minutes(p) > TL.PLAN_MINUTES for p in itertools.permutations(room['hand'], 3)) else None
        before = copy.deepcopy(j.state)
        for steps in (room['hand'][:2], room['hand'][:4], [room['hand'][0]] * 3, ['breath', 'dance', 'nope'], long_plan):
            if steps is None:
                continue
            with self.assertRaises(GameError):
                j.act('lesson_plan', task=tid, steps=steps)
            self.assertEqual(j.state, before)

    def test_plan_needs_core_and_enough_minutes(self):
        self.assertIn('hoạt động chính', TL.plan_error(['breath', 'riddle', 'board']))
        self.assertIn('ít nhất', TL.plan_error(['breath', 'demo', 'board']))
        self.assertIn('35 phút', TL.plan_error(['poster', 'relay', 'cards']))
        self.assertIn('ít nhất', TL.plan_error(['dance', 'cards', 'ticket']))
        self.assertIsNone(TL.plan_error(['dance', 'poster', 'ticket']))
        stars, parts = TL._stars(['dance', 'poster', 'ticket'], 'sleepy', ['hands', 'short'])
        self.assertEqual(stars, 3)
        stars, parts = TL._stars(['breath', 'story', 'share'], 'sleepy', ['hands'])
        self.assertEqual((stars, parts['open'], parts['reach'], parts['check']), (1, False, False, True))
        self.assertEqual(parts['missing'], ['hands'])

    def test_wrong_choices_are_mistakes_with_clues(self):
        j = Journey('teacher', slot=0, day=3)
        tid = j.task['id']
        room = j.get(tid)['room'] if 'room' in j.task else TL.roll(3, 0)
        sick = next((k for k in TL.roll(3, 0)['kids'] if k['status'] == 'sick'), None)
        j.act('lesson_roll', task=tid, kid='all')
        if sick:
            # A wrong register entry stands (the parents hear about it after the period).
            j.act('lesson_roll', task=tid, kid=sick['id'], choice='present')
            self.assertEqual(j.get(tid)['mistakes'], 1)
            self.assertEqual(j.get(tid)['room']['roll'][sick['id']], 'present')
        for k in j.get(tid)['room']['kids']:
            if k['id'] not in j.get(tid)['room']['roll']:
                j.act('lesson_roll', task=tid, kid=k['id'], choice=GOOD_ROLL[k['status']])
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        room = j.get(tid)['room']
        kid = room['lost'][0]
        wrong = next(m for m in TL.METHOD_IDS if m != TL.KID[kid]['style'])
        n = j.get(tid)['mistakes']
        r = j.act('lesson_help', task=tid, kid=kid, method=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(r['message'], TL.say(j.state, TL.CLUES[kid][1]))
        self.assertEqual(j.get(tid)['mistakes'], n + 1)
        self.assertLess(j.get(tid)['patience'], 100)

    def test_unhelped_kid_and_slip_show_on_tickets(self):
        j = Journey('teacher', slot=2, day=5)
        tid = j.task['id']
        roll_all(j, tid)
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        for _ in range(3):
            room = j.get(tid)['room']
            for ev in room['events']:
                if ev['phase'] == room['phase']:
                    j.act('lesson_call', task=tid, event=ev['id'], option=BEST_CALL[ev['id']])
            j.act('lesson_next', task=tid)
        room = j.get(tid)['room']
        kinds = {k: v['kind'] for k, v in room['tickets'].items()}
        self.assertEqual(kinds[room['slip']], 'slip')
        for kid in room['lost']:
            self.assertIn(kinds[kid], ('wrong', 'copy'))
        wrong_kid = room['slip']
        n = j.get(tid)['mistakes']
        r = j.act('lesson_mark', task=tid, kid=wrong_kid, mark='praise')
        # The mark stands like on a real sheet and does not give the answer away.
        self.assertNotIn('correct', r)
        self.assertEqual(j.get(tid)['room']['marks'][wrong_kid], 'praise')
        self.assertEqual(j.get(tid)['mistakes'], n + 1)
        for kid, tk in j.get(tid)['room']['tickets'].items():
            if kid not in j.get(tid)['room']['marks']:
                j.act('lesson_mark', task=tid, kid=kid, mark=TL.MARK_FOR[tk['kind']])
        got, total = TL.understood(j.get(tid)['room'])
        self.assertLess(got, total)
        self.assertLess(TL.reward_for(j.get(tid), j.get(tid)['room']), 75)

    def test_copying_needs_a_private_talk(self):
        for day in range(1, 30):
            for slot in range(4):
                r = TL.roll(day, slot)
                if any(e['id'] == 'copy' for e in r['events']):
                    j = Journey('teacher', slot=slot, day=day)
                    tid = j.task['id']
                    roll_all(j, tid)
                    j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
                    for _ in range(3):
                        room = j.get(tid)['room']
                        for ev in room['events']:
                            if ev['phase'] == room['phase']:
                                j.act('lesson_call', task=tid, event=ev['id'], option='blind' if ev['id'] == 'copy' else BEST_CALL[ev['id']])
                        j.act('lesson_next', task=tid)
                    self.assertEqual(j.get(tid)['room']['tickets']['vy']['kind'], 'copy')
                    j.act('lesson_mark', task=tid, kid='vy', mark='praise')
                    with self.assertRaises(GameError):
                        j.act('lesson_mark', task=tid, kid='vy', mark='private')
                    mark_all_left(j, tid)
                    j.act('lesson_complete', task=tid, confirm=True)
                    self.assertIn('grade_copy', [x['code'] for x in j.get(tid)['slips']])
                    return
        self.fail('no copy moment rolled')

    def test_tamper_is_rejected(self):
        j = Journey('teacher')
        tid = j.task['id']
        roll_all(j, tid)
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        edits = [lambda r: r.update(hand=['poster', 'relay', 'cards', 'story', 'demo']), lambda r: r.update(stars=3 if r['stars'] != 3 else 2),
                 lambda r: r['helped'].update({r['lost'][0]: 'nope'}), lambda r: r.update(stage='ready'), lambda r: r.update(slip='minh' if r['slip'] != 'minh' else 'an'),
                 lambda r: r['kids'][0].update(status='sick'), lambda r: r.update(reward=999), lambda r: r['notes'].append('fake')]
        for edit in edits:
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['teacher']['tasks'] if x['id'] == tid)
            edit(t['room'])
            with self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['teacher']['ext']['data'].setdefault('class', dict(active=None, done={}, history=[])).setdefault('kids', {})['minh'] = dict(trust=99, beat=0, known=False)
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        next(x for x in s['careers']['teacher']['tasks'] if x['id'] == tid)['plan'] = ['demo', 'practice', 'reflect']
        with self.assertRaises(GameError):
            validate_state(s)

    def test_v1_progress_keeps_v1_rules(self):
        j = Journey('teacher')
        tid = j.task['id']
        self.assertIn('room', pub_task(j, tid))
        t = j.task
        j.act('lesson_plan', task=tid, steps=['demo', 'practice', 'reflect'])
        self.assertNotIn('room', pub_task(j, tid))
        with self.assertRaises(GameError):
            j.act('lesson_roll', task=tid, kid='all')
        for st in t['students']:
            j.act('lesson_attendance', task=tid, student=st['id'], present=st['present'])
        for st in t['students']:
            if st['present']:
                j.act('lesson_teach', task=tid, student=st['id'], method=st['method'])
        for st in t['students']:
            if st['present']:
                ok = st['submission'] == t['lesson']['answer']
                j.act('lesson_grade', task=tid, student=st['id'], correct=ok, feedback='specific' if ok else 'retry')
        j.act('lesson_complete', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(j.state)

    def test_v2_blocks_v1_actions(self):
        j = Journey('teacher')
        tid = j.task['id']
        j.act('lesson_roll', task=tid, kid='all')
        for action, payload in (('lesson_attendance', dict(student='minh', present=True)), ('lesson_teach', dict(student='minh', method='visual')), ('lesson_grade', dict(student='minh', correct=True, feedback='specific'))):
            with self.assertRaises(GameError):
                j.act(action, task=tid, **payload)

    def test_old_save_without_kids_loads(self):
        j = Journey('teacher')
        s = copy.deepcopy(j.state)
        s['careers']['teacher']['ext']['data']['class'] = dict(active=None, done={}, history=[])
        validate_state(s)
        pub = public_state(s)['careers']['teacher']['classroom']
        self.assertEqual(len(pub['notebook']), len(TL.KIDS))
        self.assertTrue(all(k['trust'] == 0 and k['style'] is None for k in pub['notebook']))

    def test_trust_unlocks_story_beats_and_parent_posts(self):
        j = Journey('teacher')
        tid = j.task['id']
        roll_all(j, tid)
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        kid = j.get(tid)['room']['lost'][0]
        TL.kid_row(j.c, kid)['trust'] = 2
        j.act('lesson_help', task=tid, kid=kid, method=TL.KID[kid]['style'])
        row = j.c['ext']['data']['class']['kids'][kid]
        self.assertEqual((row['trust'], row['beat'], row['known']), (3, 1, True))
        self.assertIn(f'{kid}:1', j.get(tid)['room']['arcs'])
        teach_all(j, tid)
        mark_all(j, tid)
        j.act('lesson_complete', task=tid, confirm=True)
        posts = [f for f in j.c['feed'] if f['source'] == f'{tid}:arc:{kid}:1']
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['author'], TL.KID[kid]['guardian'])
        self.assertNotIn('{', posts[0]['text'])
        nb = next(k for k in public_state(j.state)['careers']['teacher']['classroom']['notebook'] if k['id'] == kid)
        self.assertEqual(nb['story'], [TL.ARCS[kid][0][0]])
        self.assertEqual(nb['style'], TL.KID[kid]['style'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_every_moment_has_real_tradeoffs(self):
        self.assertGreaterEqual(len(TL.INCIDENTS), 12)
        for inc in TL.INCIDENTS:
            self.assertEqual(len(inc['options']), 3, inc['id'])
            self.assertTrue(any(not o['mistake'] for o in inc['options']), inc['id'])
            effects = {(o['focus'], tuple(sorted(o['trust'].items())), o['mistake'], tuple(sorted(o['flag'].items()))) for o in inc['options']}
            self.assertEqual(len(effects), 3, inc['id'])
            for o in inc['options']:
                self.assertTrue(o['note'] is None or o['note'] in TL.NOTES)
                self.assertTrue(all(k in TL.KID for k in o['trust']))

    def test_male_teacher_title(self):
        j = Journey('teacher')
        j.state['journey']['gender'] = 'male'
        self.assertEqual(TL.say(j.state, '{Title} và {title}'), 'Thầy và thầy')
        j.state['journey']['gender'] = 'female'
        self.assertEqual(TL.say(j.state, '{Title} và {title}'), 'Cô và cô')
        j.state['journey']['gender'] = None
        self.assertEqual(TL.say(j.state, '{Title}'), 'Cô')
        j.state['journey']['gender'] = 'male'
        # A classroom activity whose feed voice mentions the teacher.
        for a in C.ACTIVITIES:
            day = next((d for d in range(1, C.YEAR + 1) if a['id'] in C.offers(dict(day=d, ext=dict(data={})))
                        and '{' in a['perspectives'][d % len(a['perspectives'])]['text']), None)
            if day:
                break
        j.c['day'] = day
        j.act('cl_start', activity=a['id'])
        for st in a['steps']:
            r = j.act('cl_submit', step=st['id'], answer=copy.deepcopy(st['_key']))
        r = j.act('cl_finish')
        post = j.c['feed'][0]
        self.assertRegex(post['text'], r'[Tt]hầy')
        self.assertNotIn('{', post['text'])
        self.assertNotIn('{title}', json.dumps(r, ensure_ascii=False).lower())
        # Public projection keeps the placeholder; the client fills it in.
        pub = json.dumps(public_state(j.state)['careers']['teacher']['classroom'], ensure_ascii=False)
        self.assertIn('{title}', pub.lower())

    def test_male_title_in_parent_note(self):
        for day in range(1, 30):
            for slot in range(4):
                if any(e['id'] == 'phone' for e in TL.roll(day, slot)['events']):
                    j = Journey('teacher', slot=slot, day=day)
                    j.state['journey']['gender'] = 'male'
                    tid = j.task['id']
                    roll_all(j, tid)
                    j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
                    for _ in range(3):
                        room = j.get(tid)['room']
                        for ev in room['events']:
                            if ev['phase'] == room['phase']:
                                j.act('lesson_call', task=tid, event=ev['id'], option='step_out' if ev['id'] == 'phone' else BEST_CALL[ev['id']])
                        j.act('lesson_next', task=tid)
                    mark_all(j, tid)
                    j.act('lesson_complete', task=tid, confirm=True)
                    post = next(f for f in j.c['feed'] if f['source'] == f'{tid}:khoa_thanks')
                    self.assertIn('thầy', post['text'])
                    self.assertEqual(post['author'], 'Bà nội Khoa')
                    return
        self.fail('no phone moment rolled')


class TeacherConsequenceTests(unittest.TestCase):
    """Wrong register entries and wrong marks stand; parents complain to the school after the period."""

    def period(self, pred=lambda r: True, roll=None, mark=None, start=1, gender=None):
        for day in range(start, 60):
            for slot in range(4):
                if pred(TL.roll(day, slot)):
                    break
            else:
                continue
            break
        j = Journey('teacher', slot=slot, day=day)
        if gender:
            j.state.setdefault('journey', {})['gender'] = gender
        tid = j.task['id']
        if any(k['status'] == 'here' for k in TL.roll(day, slot)['kids']):
            j.act('lesson_roll', task=tid, kid='all')
        for k in j.get(tid)['room']['kids']:
            if k['id'] not in j.get(tid)['room']['roll']:
                j.act('lesson_roll', task=tid, kid=k['id'], choice=(roll or {}).get(k['status'], GOOD_ROLL[k['status']]))
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        teach_all(j, tid)
        for kid, tk in j.get(tid)['room']['tickets'].items():
            j.act('lesson_mark', task=tid, kid=kid, mark=(mark or {}).get(tk['kind'], TL.MARK_FOR[tk['kind']]))
        money = j.c['money']
        r = j.act('lesson_complete', task=tid, confirm=True)
        t = j.get(tid)
        review = next(f for f in j.c['feed'] if f.get('source') == tid and f.get('kind') == 'review')
        return j, t, review, j.c['money'] - money, r

    def test_right_period_full_pay(self):
        j, t, review, delta, r = self.period()
        self.assertFalse(t.get('slips'))
        self.assertGreaterEqual(review['stars'], 4)
        self.assertGreaterEqual(delta, t['room']['reward'])

    def test_praising_a_wrong_sheet_is_reported_by_the_parent(self):
        j, t, review, delta, r = self.period(mark=dict(slip='praise'))
        self.assertEqual([x['code'] for x in t['slips']], ['grade_praise'])
        self.assertLessEqual(review['stars'], 3)
        self.assertIn('sai mà vẫn được khen đúng', review['text'])
        self.assertIn(t['reaction']['kind'], ('grumble', 'discount', 'refund'))
        cut = t['reaction']['cut']
        self.assertEqual(delta, t['room']['reward'] - cut)
        self.assertIn('Phụ huynh', r['message'])
        self.assertNotIn('Mình trả', r['message'])
        from game import consequences as cq
        before = j.c['money']
        self.assertEqual(cq.react(j.state, j.c, t, t['room']['reward'])['cut'], cut)
        self.assertEqual(j.c['money'], before)
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales(self):
        _, small, r1, _, _ = self.period(mark=dict(right='hint'))
        _, big, r2, _, _ = self.period(mark=dict(slip='praise'))
        self.assertEqual([x['sev'] for x in small['slips']], [1])
        self.assertEqual([x['sev'] for x in big['slips']], [2])
        self.assertGreater(r1['stars'], r2['stars'])

    def test_attendance_mistakes_go_through(self):
        j, t, review, delta, r = self.period(lambda r: any(k['status'] == 'sick' for k in r['kids']), roll=dict(sick='present'))
        self.assertEqual([x['code'] for x in t['slips']], ['roll_sick'])
        self.assertIn('ghi có mặt', review['text'])
        self.assertLessEqual(review['stars'], 4)

    def test_missing_child_not_reported_is_a_safety_case(self):
        j, t, review, delta, r = self.period(lambda r: any(k['status'] == 'missing' for k in r['kids']), roll=dict(missing='mark'))
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual((review['stars'], delta), (1, 0))
        self.assertTrue(any(f.get('report') and f.get('source') == t['id'] for f in j.c['feed']))
        self.assertTrue(any(x['src'] == t['id'] and x['script'] == 'slip_safety_inspect' for x in j.c['incidents']['follow']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_two_wrong_helps_for_one_kid_is_a_small_slip(self):
        for gender, title in ((None, 'cô/thầy'), ('male', 'thầy'), ('female', 'cô')):
            text = self.two_wrong_helps(gender)
            self.assertIn(f'bảo {title} phải đổi', text)

    def two_wrong_helps(self, gender):
        j = Journey('teacher', slot=0, day=1)
        if gender:
            j.state.setdefault('journey', {})['gender'] = gender
        tid = j.task['id']
        roll_all(j, tid)
        j.act('lesson_plan', task=tid, steps=best_plan(j.get(tid)['room']))
        kid = j.get(tid)['room']['lost'][0]
        for m in [m for m in TL.METHOD_IDS if m != TL.KID[kid]['style']][:2]:
            j.act('lesson_help', task=tid, kid=kid, method=m)
        self.assertEqual(j.get(tid)['room']['tries'][kid], 2)
        validate_state(json.loads(json.dumps(j.state)))
        self.assertNotIn('tries', json.dumps(pub_task(j, tid)['room']))
        teach_all(j, tid)
        mark_all(j, tid)
        j.act('lesson_complete', task=tid, confirm=True)
        self.assertEqual([(x['code'], x['sev']) for x in j.get(tid)['slips']], [('method', 1)])
        return j.get(tid)['slips'][0]['text']


if __name__ == '__main__':
    unittest.main()
