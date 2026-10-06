"""Unpleasant, careless and fake reviews: rates, determinism, report outcomes,
rude-reply backfire, clamps and old saves."""
import copy
import json
import unittest

from game import engine, feedback as F
from game.engine import GameError, validate_state, public_state
from tests.helpers import Journey


def fake_task(i, career='milk_tea', npc='milk_tea_npc_01', mistakes=0, patience=100):
    return dict(id=f'task-{career}-{i}', career=career, npc=npc, mistakes=mistakes, patience=patience, known=True, title='Ly trà sữa')


def kind_of(made):
    fb = made['feedback']
    return (fb.get('twist') or {}).get('kind') or ('mood' if fb['persona'] in F.HARSH else 'unfair' if fb['unfair'] else 'plain')


def find(kind, day=15, career='milk_tea', npc='milk_tea_npc_01', mistakes=0, patience=100):
    for i in range(20000):
        t = fake_task(i, career, npc, mistakes, patience)
        made = F.make_review({}, dict(day=day), t, 'completed')
        if kind_of(made) == kind:
            return t
    raise AssertionError('no task rolls ' + kind)


class Classifier(unittest.TestCase):
    def test_everyday_words_are_not_insults(self):
        for text in ('Cảm ơn người đã góp ý, xin lỗi ạ', 'Em sẽ bù cho chị một ly', 'Chúc anh ngủ ngon', 'Bạn diễn hay quá', 'Nguyên liệu tươi'):
            self.assertFalse(F.classify(text)['rude'], text)

    def test_rude_replies_are_caught(self):
        for text in ('Không thích thì đi chỗ khác.', 'Đồ ngu.', 'Khách gì mà mất dạy', 'Phụ huynh không hài lòng thì chuyển lớp khác đi.'):
            self.assertTrue(F.classify(text)['rude'], text)


class Rolls(unittest.TestCase):
    def roll(self, day, n=3000, career='milk_tea', npc='milk_tea_npc_01'):
        return [kind_of(F.make_review({}, dict(day=day), fake_task(f'{day}-{i}', career, npc), 'completed')) for i in range(n)]

    def test_rates_grow_with_days(self):
        early = self.roll(2)
        self.assertFalse([k for k in early if k not in ('plain', 'unfair')])
        late = self.roll(15)
        twists = sum(k not in ('plain', 'unfair', 'mood') for k in late) / len(late)
        moods = sum(k == 'mood' for k in late) / len(late)
        self.assertGreater(twists, 0.10)
        self.assertLess(twists, 0.22)
        self.assertGreater(moods, 0.06)
        mid = self.roll(4)
        self.assertLess(sum(k not in ('plain', 'unfair', 'mood') for k in mid) / len(mid), twists)

    def test_every_kind_appears_for_customers_and_parents(self):
        late = set(self.roll(15, 4000))
        for k in ('offtopic', 'no_visit', 'wrong_shop', 'competitor', 'flip_low', 'bocphot', 'demand', 'mood'):
            self.assertIn(k, late)
        parents = set(self.roll(15, 3000, 'teacher', 'teacher_npc_01'))
        for k in ('offtopic_p', 'wrong_class', 'flip_low', 'rumor', 'mood'):
            self.assertIn(k, parents)

    def test_deterministic_and_stranger_authors(self):
        t = find('wrong_shop')
        a = F.make_review({}, dict(day=15), t, 'completed')
        b = F.make_review({}, dict(day=15), copy.deepcopy(t), 'completed')
        self.assertEqual(json.dumps(a, sort_keys=True, ensure_ascii=False), json.dumps(b, sort_keys=True, ensure_ascii=False))
        # Chat C#23729: a stranger from the same trade signs it (not the customer served), so it reads as this shop's.
        self.assertTrue(a['npc'] and a['npc'].startswith('milk_tea_npc_') and a['npc'] != t['npc'])
        self.assertNotIn('Trà sữa', a['text'])        # never the player's own trade
        self.assertFalse(a['aside'])

    def test_careless_stars_leave_the_facts(self):
        t = find('flip_low')
        made = F.make_review({}, dict(day=15), t, 'completed')
        self.assertEqual(made['stars'], 1)
        self.assertEqual(made['feedback']['fair'], 5)
        self.assertEqual(made['feedback']['clues'], ['Lời khen mà chấm 1★'])
        t = find('flip_high', mistakes=5, patience=40)
        made = F.make_review({}, dict(day=15), t, 'completed')
        self.assertEqual(made['stars'], 5)
        self.assertLessEqual(made['feedback']['fair'], 3)

    def test_failed_jobs_get_no_twist(self):
        for i in range(400):
            made = F.make_review({}, dict(day=20), fake_task(i), 'cancelled')
            self.assertIsNone(made['feedback'].get('twist'))


class Actions(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 15

    def post(self, kind, **kw):
        t = find(kind, **kw)
        made = F.make_review(self.j.state, self.j.c, t, 'completed')
        post = engine.add_feed(self.j.state, self.j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(post, made)
        validate_state(self.j.state)
        return post

    def get(self, pid):
        return next(p for p in self.j.c['feed'] if p['id'] == pid)

    def rating(self):
        return public_state(self.j.state)['careers']['milk_tea']['rating']

    def test_report_removes_known_fake(self):
        good = self.post('plain')
        fake = self.post('competitor')
        self.assertLess(self.rating(), 5)
        r = self.j.act('fb_report', post=fake['id'])
        self.assertEqual(r['report'], 'accepted')
        p = self.get(fake['id'])
        self.assertIsNone(p['stars'])
        self.assertEqual(p['feedback']['removed_stars'], 1)
        self.assertEqual(self.rating(), self.get(good['id'])['stars'])
        with self.assertRaises(GameError):
            self.j.act('fb_report', post=fake['id'])
        with self.assertRaises(GameError):
            self.j.act('fb_reply', post=fake['id'], text='Cảm ơn bạn đã góp ý ạ.', offer='none')
        pub = next(x for x in public_state(self.j.state)['careers']['milk_tea']['feed'] if x['id'] == fake['id'])
        self.assertTrue(pub['feedback']['removed'])
        self.assertEqual(pub['feedback']['kind_label'], 'Tài khoản cài cắm')
        validate_state(self.j.state)

    def test_wrong_report_costs_no_star(self):
        # Góp ý #196: a report the platform does not accept keeps the stars and adds no review.
        for i in range(2000):                   # a bad-day reviewer with no off-topic gripe: a real experience
            t = fake_task(f'real-{i}')
            made = F.make_review(self.j.state, self.j.c, t, 'completed')
            if kind_of(made) == 'mood' and not made['feedback'].get('gripe'):
                break
        real = engine.add_feed(self.j.state, self.j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(real, made)
        self.assertFalse(F.removable(real))
        before = real['stars']
        n = len(self.j.c['feed'])
        r = self.j.act('fb_report', post=real['id'])
        self.assertEqual(r['report'], 'rejected')
        self.assertIn('Sao giữ nguyên', r['message'])
        p = self.get(real['id'])
        self.assertEqual(p['stars'], before)
        self.assertEqual(len(self.j.c['feed']), n)
        self.assertEqual(p['feedback']['thread'][-1]['role'], 'customer')
        self.assertEqual(p['feedback']['thread'][-1]['decision'], 'keep')
        self.assertEqual(p['feedback']['status'], 'closed')
        validate_state(self.j.state)

    def test_offtopic_one_star_is_removed_without_a_pile_on(self):
        troll = self.post('offtopic')
        self.assertEqual(troll['stars'], 1)
        n = len(self.j.c['feed'])
        r = self.j.act('fb_report', post=troll['id'])
        self.assertEqual(r['report'], 'accepted')
        self.assertEqual(len(self.j.c['feed']), n)
        p = self.get(troll['id'])
        self.assertIsNone(p['stars'])
        self.assertEqual(p['feedback']['removed_stars'], 1)   # kept, marked, out of the average
        validate_state(self.j.state)

    def test_report_limit_per_day(self):
        a, b, c, d = self.post('wrong_shop'), self.post('no_visit'), self.post('competitor'), self.post('offtopic')
        for x in (a, b, c):
            self.j.act('fb_report', post=x['id'])
        with self.assertRaises(GameError):
            self.j.act('fb_report', post=d['id'])
        self.assertEqual(self.get(d['id'])['stars'], d['stars'])

    def test_public_hides_the_twist(self):
        p = self.post('competitor')
        pub = next(x for x in public_state(self.j.state)['careers']['milk_tea']['feed'] if x['id'] == p['id'])
        self.assertNotIn('twist', pub['feedback'])
        self.assertNotIn('fair', pub['feedback'])
        self.assertNotIn('kind_label', pub['feedback'])
        self.assertTrue(pub['feedback']['can_report'])
        self.assertIn('Tài khoản mới, đây là đánh giá đầu tiên', pub['feedback']['clues'])

    def test_rude_reply_backfires_once(self):
        p = self.post('plain')
        n = len(self.j.c['feed'])
        r = self.j.act('fb_reply', post=p['id'], text='Không thích thì đi chỗ khác, tiệm không tiếp loại khách như bạn.', offer='none')
        added = len(self.j.c['feed']) - n
        self.assertTrue(1 <= added <= 3)
        self.assertEqual(r['viral'], added)
        self.assertTrue(all(x['stars'] == 1 and x['feedback']['twist']['kind'] == 'pile_on' for x in self.j.c['feed'][:added]))
        self.j.act('advance')
        self.j.act('advance')
        p = self.get(p['id'])
        self.assertEqual([x for x in p['feedback']['thread'] if x['role'] == 'customer'][-1]['decision'], 'revise_down')
        validate_state(self.j.state)
        if p['feedback']['status'] == 'open':
            self.j.act('fb_reply', post=p['id'], text='Đồ ngu.', offer='none')
            self.assertEqual(len(self.j.c['feed']) - n, added)

    def test_flip_low_polite_reply_restores_the_truth(self):
        p = self.post('flip_low')
        self.j.act('fb_reply', post=p['id'], text='Cảm ơn bạn đã khen tiệm! Hình như bạn chấm nhầm sao, bạn xem lại giúp tiệm nhé.', offer='none')
        self.j.act('advance')
        self.j.act('advance')
        p = self.get(p['id'])
        self.assertEqual(p['stars'], p['feedback']['fair'])

    def test_fakes_do_not_move_on_replies(self):
        p = self.post('competitor')
        cash = self.j.state['money'] if 'money' in self.j.state else None
        # Chat C#15809: bù xu on a review it can never change is refused with a warning, and no xu leaves the wallet.
        with self.assertRaises(GameError) as e:
            self.j.act('fb_reply', post=p['id'], text='Xin lỗi anh, tiệm sẽ cải thiện. Theo hóa đơn thì hôm đó...', offer='refund')
        self.assertIn('Chưa trừ xu nào', str(e.exception))
        if cash is not None:
            self.assertEqual(self.j.state['money'], cash)
        pub = next(x for x in public_state(self.j.state)['careers']['milk_tea']['feed'] if x['id'] == p['id'])
        self.assertIn('Bù xu không đổi được', pub['feedback']['offer_note'])
        self.j.act('fb_reply', post=p['id'], text='Xin lỗi anh, tiệm sẽ cải thiện. Theo hóa đơn thì hôm đó...', offer='none')
        self.j.act('advance')
        self.j.act('advance')
        self.assertEqual(self.get(p['id'])['stars'], 1)

    def test_bocphot_wants_money_and_ignoring_spreads(self):
        p = self.post('bocphot')
        self.j.act('fb_reply', post=p['id'], text='Tiệm thành thật xin lỗi, xin hoàn tiền cho bạn ạ.', offer='refund')
        self.j.act('advance')
        self.j.act('advance')
        self.assertEqual(self.get(p['id'])['stars'], self.get(p['id'])['feedback']['fair'])
        q = self.post('bocphot')
        n = len(self.j.c['feed'])
        r = self.j.act('fb_ignore', post=q['id'])
        self.assertEqual(len(self.j.c['feed']), n + 2)
        self.assertEqual(r['viral'], 2)
        validate_state(self.j.state)

    def test_ignore_plain_is_harmless(self):
        p = self.post('offtopic')
        n = len(self.j.c['feed'])
        self.j.act('fb_ignore', post=p['id'])
        self.assertEqual(len(self.j.c['feed']), n)
        self.assertEqual(self.get(p['id'])['feedback']['status'], 'closed')

    def test_ai_proposal_is_clamped_for_fakes(self):
        p = self.post('wrong_shop')
        self.j.act('fb_reply', post=p['id'], text='Dạ bạn nhầm quán rồi ạ.', offer='none')
        state, _ = engine.apply_action(self.j.state, 'milk_tea', 'fb_resolve', dict(post=p['id'], decision='revise_up', stars=5, text='Ừ nhầm.', mode='ai'), internal=True)
        self.j.state = state
        post = self.get(p['id'])
        self.assertLessEqual(post['stars'], post['feedback']['stars_original'] + 1)


class Parents(unittest.TestCase):
    def setUp(self):
        self.j = Journey('teacher')
        self.j.c['day'] = 15
        self.j.state['journey']['gender'] = 'female'

    def post(self, kind):
        t = find(kind, career='teacher', npc='teacher_npc_01')
        made = F.make_review(self.j.state, self.j.c, t, 'completed')
        post = engine.add_feed(self.j.state, self.j.c, made.get('npc', t['npc']), made['text'], t['id'], made['stars'], 'review')
        F.attach(post, made)
        return post

    def test_wrong_class_is_removed_and_rude_reply_spreads_in_the_group(self):
        p = self.post('wrong_class')
        self.assertEqual(self.j.act('fb_report', post=p['id'])['report'], 'accepted')
        q = self.post('rumor')
        n = len(self.j.c['feed'])
        self.j.act('fb_reply', post=q['id'], text='Phụ huynh không hài lòng thì chuyển lớp khác đi.', offer='none')
        self.assertGreater(len(self.j.c['feed']), n)
        self.assertNotIn('cô/thầy', json.dumps(self.j.c['feed'][:len(self.j.c['feed']) - n], ensure_ascii=False))
        validate_state(self.j.state)

    def test_rumor_settles_with_facts(self):
        p = self.post('rumor')
        self.j.act('fb_reply', post=p['id'], text='Dạ, theo sổ lớp và phiếu cuối tiết hôm nay, các con đều hoàn thành bài ạ.', offer='none')
        self.j.act('advance')
        self.j.act('advance')
        p = next(x for x in self.j.c['feed'] if x['id'] == p['id'])
        self.assertEqual(p['stars'], p['feedback']['fair'])


class OldSaves(unittest.TestCase):
    def test_old_record_loads_and_projects(self):
        j = Journey('milk_tea')
        post = engine.add_feed(j.state, j.c, 'milk_tea_npc_01', 'Ngon.', 'task-old', 4, 'review')
        post['feedback'] = dict(persona='sour', criteria=[dict(key='speed', label='Thời gian chờ', score=4, note='ok')], cap=5, fair=4,
                                stars_original=4, unfair=None, thread=[], status='open', rounds=0, pending=None, voice='scripted', task='task-old', title='x', value=0)
        validate_state(j.state)
        pub = next(x for x in public_state(j.state)['careers']['milk_tea']['feed'] if x['id'] == post['id'])
        self.assertEqual(pub['feedback']['clues'], [])
        self.assertTrue(pub['feedback']['can_report'])
        r = j.act('fb_report', post=post['id'])
        self.assertEqual(r['report'], 'rejected')
        validate_state(j.state)

    def test_bad_new_fields_rejected(self):
        j = Journey('milk_tea')
        j.c['day'] = 15
        t = find('competitor')
        made = F.make_review(j.state, j.c, t, 'completed')
        post = engine.add_feed(j.state, j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(post, made)
        post['feedback']['twist']['kind'] = 'hack'
        with self.assertRaises(GameError):
            validate_state(j.state)


# ---------------------------------------------------------------- wave 2b
from game import feedback_voices as FV  # noqa: E402

BANNED = ('NPC', 'trong game', 'của game', 'trò chơi', 'mô phỏng', 'giả lập', 'hư cấu', '{', '}')


def make_post(j, persona, stars=3, score=3, unfair=None, twist=None, style=None, pid_hint=''):
    crit = [dict(key='speed', label='Thời gian chờ', score=score, note='kiên nhẫn còn 45%' if score <= 3 else 'khách chờ vừa đủ'),
            dict(key='accuracy', label='Đúng vị đã gọi', score=5, note='đúng trà, topping, đường đá')]
    post = engine.add_feed(j.state, j.c, j.career + '_npc_01', 'Chờ hơi lâu.' + pid_hint, 'task-x' + pid_hint, stars, 'review')
    post['feedback'] = dict(persona=persona, criteria=crit, cap=5, fair=min(5, max(stars, score)), stars_original=stars, unfair=unfair,
                            thread=[], status='open', rounds=0, pending=None, voice='scripted', task='task-x' + pid_hint, title='Ly trà sữa',
                            value=0, item='ly trà sữa')
    if twist:
        post['feedback']['twist'] = dict(kind=twist, reportable=False)
    if style:
        post['feedback']['style'] = style
    return post


def expected(code):
    return {'W': {'revise_up'}, 'U': {'revise_up'}, 'L': {'revise_up'}, 'F': {'revise_up'}, 'K': {'keep'}, 'S': {'keep'},
            'A': {'argue'}, 'J': {'argue'}, 'D': {'revise_down'}, 'R': {'revise_up', 'revise_down'}}[code]


class ToneTable(unittest.TestCase):
    """Every persona × tone gives the table's outcome, within the star bounds."""

    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 8

    def run_cell(self, persona, tone, offer='none', **kw):
        post = make_post(self.j, persona, pid_hint=f'{persona}-{tone}-{offer}-{len(self.j.c["feed"])}', **kw)
        if offer != 'none':
            post['feedback']['thread'].append(dict(role='owner', text='x', day=8, offer=offer))
        d = FV.tone_decision(self.j.state, self.j.c, post, tone, offer)
        code, _ = FV.outcome_code(post['feedback'], persona, tone, post['stars'], offer, F._hash('tone', post['id'], 0, tone))
        return post, d, code

    def test_every_cell_matches_the_table(self):
        for persona in F.PERSONAS:
            for tone in FV.TONE_ORDER:
                for scenario in ('fault', 'unfair', 'happy'):
                    kw = dict(fault=dict(stars=3, score=3), happy=dict(stars=4, score=5),
                              unfair=dict(stars=3, score=5, unfair=dict(key='speed', label='Thời gian chờ', claim='đợi lâu muốn xỉu', truth='khách chờ vừa đủ')))[scenario]
                    post, d, code = self.run_cell(persona, tone, **kw)
                    low, high = F._bounds(post['feedback'], post['stars'])
                    self.assertTrue(low <= d['stars'] <= high, (persona, tone, scenario, d))
                    allowed = expected(code) if code != '$' else {'keep'}
                    if d['stars'] >= high and code in 'WULF':
                        allowed = allowed | {'keep'}
                    self.assertIn(d['decision'], allowed, (persona, tone, scenario, code, d))
                    self.assertTrue(d['text'].strip())
                    for bad in BANNED:
                        self.assertNotIn(bad, d['text'], (persona, tone, d['text']))
                    if tone == 'harsh':
                        self.assertEqual(d['decision'], 'revise_down')

    def test_table_shape(self):
        self.assertEqual(set(FV.TABLE), set(F.PERSONAS))
        for persona, row in FV.TABLE.items():
            self.assertEqual(len(row), len(FV.TONE_ORDER), persona)
            self.assertTrue(set(row) <= set('WULFKSAJDR$'), persona)
            self.assertEqual(row[FV.TONE_ORDER.index('harsh')], 'D')
            self.assertEqual(row[FV.TONE_ORDER.index('sassy')], 'R')

    def test_spot_outcomes(self):
        self.assertEqual(self.run_cell('warm', 'warm')[1]['decision'], 'revise_up')
        self.assertEqual(self.run_cell('rude', 'warm')[1]['decision'], 'keep')
        self.assertEqual(self.run_cell('entitled', 'sorry')[1]['decision'], 'keep')             # words alone
        self.assertEqual(self.run_cell('entitled', 'sorry', offer='gift')[1]['decision'], 'revise_up')
        self.assertEqual(self.run_cell('picky', 'facts')[1]['decision'], 'argue')             # the records show a real fault
        self.assertEqual(self.run_cell('knowitall', 'facts')[1]['decision'], 'revise_down')
        self.assertEqual(self.run_cell('picky', 'facts', stars=3, score=5)[1]['decision'], 'revise_up')  # facts back the shop
        _, d, _ = self.run_cell('sour', 'facts', stars=3, score=5, unfair=dict(key='speed', label='Thời gian chờ', claim='đợi lâu', truth='khách chờ vừa đủ'))
        self.assertEqual((d['decision'], d['stars']), ('revise_up', 5))
        _, d, _ = self.run_cell('genz', 'genz')
        self.assertEqual(d['decision'], 'revise_up')
        self.assertTrue(d.get('fans'))
        self.assertEqual(self.run_cell('parent_worried', 'silent')[1]['decision'], 'argue')
        # A happy review has nothing to move up: thanks, same stars.
        _, d, _ = self.run_cell('warm', 'warm', stars=5, score=5)
        self.assertEqual((d['decision'], d['stars']), ('keep', 5))

    def test_kinds_override_the_table(self):
        _, d, _ = self.run_cell('warm', 'funny', stars=1, score=5, twist='flip_low')
        self.assertEqual(d['decision'], 'revise_up')
        _, d, _ = self.run_cell('troll', 'sorry', stars=1, score=5, twist='competitor')
        self.assertEqual(d['decision'], 'keep')
        _, d, _ = self.run_cell('drama', 'warm', stars=1, score=3, twist='bocphot')
        self.assertEqual(d['decision'], 'keep')
        _, d, _ = self.run_cell('drama', 'sorry', offer='refund', stars=1, score=3, twist='bocphot')
        self.assertEqual(d['decision'], 'revise_up')
        _, d, _ = self.run_cell('genz', 'warm', stars=5, score=3, style='handsome')
        self.assertEqual(d['decision'], 'keep')

    def test_deterministic(self):
        post = make_post(self.j, 'sour', pid_hint='det')
        one = FV.tone_decision(self.j.state, self.j.c, post, 'sassy', 'none')
        two = FV.tone_decision(self.j.state, self.j.c, copy.deepcopy(post), 'sassy', 'none')
        self.assertEqual(one, two)
        self.assertEqual(FV.tone_choices(post), FV.tone_choices(copy.deepcopy(post)))

    def test_sass_is_a_gamble_for_both_sides(self):
        seen = set()
        for i in range(60):
            post = make_post(self.j, 'sour', pid_hint=f'sass{i}')
            seen.add(FV.tone_decision(self.j.state, self.j.c, post, 'sassy', 'none').get('sass'))
        self.assertEqual(seen, {'won', 'lost'})


class ToneFlow(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 8

    def get(self, pid):
        return next(p for p in self.j.c['feed'] if p['id'] == pid)

    def reply(self, post, tone, offer='none'):
        pub = next(x for x in public_state(self.j.state)['careers']['milk_tea']['feed'] if x['id'] == post['id'])
        text = next(t['text'] for t in pub['feedback']['tones'] if t['id'] == tone)
        r = self.j.act('fb_reply', post=post['id'], text=text, offer=offer, tone=tone)
        self.j.act('advance')
        self.j.act('advance')
        return r

    def test_public_tones_and_hidden_fields(self):
        post = make_post(self.j, 'warm', style='short')
        pub = next(x for x in public_state(self.j.state)['careers']['milk_tea']['feed'] if x['id'] == post['id'])
        f = pub['feedback']
        self.assertEqual([t['id'] for t in f['tones']], list(FV.TONE_ORDER))
        self.assertNotIn('style', f)
        self.assertNotIn('pending', f)
        for t in f['tones']:
            for bad in BANNED:
                self.assertNotIn(bad, t['text'])
        self.assertTrue(F.classify(next(t['text'] for t in f['tones'] if t['id'] == 'harsh'))['rude'])
        self.assertFalse(F.classify(next(t['text'] for t in f['tones'] if t['id'] == 'sassy'))['rude'])

    def test_compensation_costs_money_through_the_ledger(self):
        post = make_post(self.j, 'warm')
        before = self.j.c['money']
        n = len(self.j.c['ops']['finance']['ledger'])
        self.reply(post, 'sorry', 'drink')
        self.assertEqual(self.j.c['money'], before - F.OFFERS['drink'])
        rows = self.j.c['ops']['finance']['ledger'][n:]
        self.assertTrue(any(r['amount'] == -F.OFFERS['drink'] and r['category'] == 'compensation' for r in rows))
        self.assertEqual(self.get(post['id'])['feedback']['thread'][0]['tone'], 'sorry')
        validate_state(self.j.state)

    def test_invalid_tone_changes_nothing(self):
        post = make_post(self.j, 'warm')
        before = self.j.c['money']
        with self.assertRaises(GameError):
            self.j.act('fb_reply', post=post['id'], text='Cảm ơn bạn nhiều ạ.', offer='gift', tone='hack')
        self.assertEqual(self.j.c['money'], before)
        self.assertEqual(self.get(post['id'])['feedback']['thread'], [])

    def test_rude_words_override_a_gentle_label(self):
        post = make_post(self.j, 'warm')
        n = len(self.j.c['feed'])
        self.j.act('fb_reply', post=post['id'], text='Không thích thì đi chỗ khác.', offer='none', tone='warm')
        self.assertEqual(self.get(post['id'])['feedback']['thread'][0]['tone'], 'harsh')
        self.assertGreater(len(self.j.c['feed']), n)

    def test_fans_come_and_are_capped(self):
        made = 0
        for i in range(8):
            post = make_post(self.j, 'genz', pid_hint=f'fan{i}')
            self.reply(post, 'genz')
            made = sum(1 for p in self.j.c['feed'] if ((p.get('feedback') or {}).get('twist') or {}).get('kind') == 'fan')
        self.assertGreaterEqual(made, 1)
        self.assertLessEqual(made, FV.FANS_PER_DAY)
        fan = next(p for p in self.j.c['feed'] if ((p.get('feedback') or {}).get('twist') or {}).get('kind') == 'fan')
        self.assertGreaterEqual(fan['stars'], 4)
        validate_state(self.j.state)

    def test_lost_sass_spreads_once(self):
        for i in range(60):
            post = make_post(self.j, 'knowitall', pid_hint=f'lost{i}')
            if FV.tone_decision(self.j.state, self.j.c, post, 'sassy', 'none').get('sass') == 'lost':
                break
        n = len(self.j.c['feed'])
        self.reply(post, 'sassy')
        p = self.get(post['id'])
        self.assertTrue(p['feedback']['viral'])
        new = self.j.c['feed'][:len(self.j.c['feed']) - n]
        self.assertTrue(new and all(x['stars'] == 1 for x in new))
        self.assertIn('Kéo tới từ câu cà khịa của bạn', new[0]['feedback']['clues'])
        validate_state(self.j.state)

    def test_third_parties_rate_and_caps(self):
        with_guest = total = 0
        for day in range(2, 14):
            self.j.c['day'] = day
            for i in range(10):
                post = make_post(self.j, 'sour', pid_hint=f'g{day}-{i}')
                self.reply(post, 'warm')
                total += 1
                rows = [x for x in self.get(post['id'])['feedback']['thread'] if x['role'] == 'guest']
                self.assertLessEqual(len(rows), FV.GUESTS_PER_POST)
                with_guest += bool(rows)
                if rows:
                    self.assertEqual(self.get(post['id'])['feedback']['thread'][-1]['role'], 'customer')
            day_guests = sum(1 for p in self.j.c['feed'] for x in p['feedback']['thread'] if x['role'] == 'guest' and x['day'] == day)
            self.assertLessEqual(day_guests, FV.GUESTS_PER_DAY)
        self.assertTrue(0.15 <= with_guest / total <= 0.45, with_guest / total)
        validate_state(self.j.state)

    def test_no_bystanders_on_day_one(self):
        self.j.c['day'] = 1
        for i in range(12):
            post = make_post(self.j, 'warm', pid_hint=f'd1-{i}')
            self.reply(post, 'warm')
            self.assertFalse([x for x in self.get(post['id'])['feedback']['thread'] if x['role'] == 'guest'])

    def test_bad_guest_row_rejected(self):
        post = make_post(self.j, 'warm')
        post['feedback']['thread'].append(dict(role='guest', name='A', emoji='🙂', side='boss', text='hi', day=1))
        with self.assertRaises(GameError):
            validate_state(self.j.state)


class Voices(unittest.TestCase):
    def reviews(self, career, npc, n, day=8, gender=None, extra=None, **kw):
        s = dict(journey=dict(gender=gender))
        out = []
        for i in range(n):
            t = fake_task(f'v{day}-{i}', career, npc, **kw)
            t.update(extra or {})
            c = dict(day=day, metrics={f'served:{npc}': i % 6}, life=dict(mode=('calm', 'normal', 'festival')[i % 3]))
            out.append(F.make_review(s, c, t, 'completed'))
        return out

    def test_styles_appear_and_texts_are_clean(self):
        rows = self.reviews('milk_tea', 'milk_tea_npc_01', 900) + self.reviews('milk_tea', 'milk_tea_npc_02', 900, mistakes=3, patience=45)
        styles = {r['feedback'].get('style') for r in rows}
        for s in ('short', 'emoji', 'teencode', 'rant', 'lifestory', 'regular', 'handsome', 'sarcastic'):
            self.assertIn(s, styles)
        parents = {r['feedback'].get('style') for r in self.reviews('teacher', 'teacher_npc_01', 900, extra=dict(feedback=True))}
        for s in ('p_short', 'p_story', 'p_long', 'p_emoji'):
            self.assertIn(s, parents)
        for r in rows:
            for bad in BANNED:
                self.assertNotIn(bad, r['text'], r['text'])
            self.assertLessEqual(len(r['text']), 600)
            if r['feedback'].get('style') in ('short', 'emoji', 'lifestory', 'handsome'):
                self.assertFalse(r['aside'])

    def test_owner_is_never_assumed_female(self):
        for gender, word, other in ((None, 'chủ quán', None), ('male', 'anh chủ', 'chị chủ'), ('female', 'chị chủ', 'anh chủ')):
            texts = [r['text'] for r in self.reviews('milk_tea', 'milk_tea_npc_03', 1500, gender=gender) if r['feedback'].get('style') == 'handsome']
            self.assertTrue(texts)
            for t in texts:
                self.assertIn(word, t.lower())
                if other:
                    self.assertNotIn(other, t)

    def test_item_and_day_aware(self):
        rows = self.reviews('milk_tea', 'milk_tea_npc_01', 300)
        self.assertTrue(any('ly trà sữa' in r['text'].lower() or '“ly trà sữa”' in r['text'].lower() for r in rows))
        early = self.reviews('milk_tea', 'milk_tea_npc_01', 300, day=2)
        self.assertTrue(any('mới mở' in r['text'] or 'khai trương' in r['text'] for r in early))

    def test_day_one_is_plain_and_styles_start_on_day_two(self):
        rows = self.reviews('milk_tea', 'milk_tea_npc_01', 400, day=1)
        self.assertFalse([r for r in rows if r['feedback'].get('twist') or r['feedback'].get('style')])
        rows = self.reviews('milk_tea', 'milk_tea_npc_01', 400, day=2)
        self.assertFalse([r for r in rows if r['feedback'].get('twist')])
        self.assertTrue([r for r in rows if r['feedback'].get('style')])

    def test_every_voice_list_formats(self):
        for persona, v in F.VOICE.items():
            for key, rows in v.items():
                lines = [x for star in rows.values() for x in star] if key == 'open' else rows
                self.assertTrue(lines, (persona, key))
                for line in lines:
                    text = FV.fill(line, note='n', good='g', bad='b', owner='o', item='i')
                    self.assertNotIn('{', text, (persona, key, line))
        for key in ('moved', 'laugh', 'jab', 'seen', 'fans', 'item_pos', 'item_neg', 'accept', 'keep', 'argue', 'down'):
            for persona in F.PERSONAS:
                self.assertIn(key, F.VOICE[persona], (persona, key))
        # Plenty of openers per persona.
        for persona, v in F.VOICE.items():
            self.assertGreaterEqual(sum(len(x) for x in v['open'].values()), 10, persona)


class OldSavesWave2b(unittest.TestCase):
    def test_old_thread_and_record_without_new_fields(self):
        j = Journey('milk_tea')
        j.c['day'] = 6
        post = engine.add_feed(j.state, j.c, 'milk_tea_npc_01', 'Chậm.', 'task-old2', 3, 'review')
        post['feedback'] = dict(persona='picky', criteria=[dict(key='speed', label='Thời gian chờ', score=3, note='chờ lâu')], cap=5, fair=3,
                                stars_original=3, unfair=None, thread=[], status='open', rounds=0, pending=None, voice='scripted', task='task-old2', title='x', value=0)
        validate_state(j.state)
        pub = next(x for x in public_state(j.state)['careers']['milk_tea']['feed'] if x['id'] == post['id'])
        self.assertEqual(len(pub['feedback']['tones']), len(FV.TONE_ORDER))
        j.act('fb_reply', post=post['id'], text='Dạ bên mình làm theo quy trình ạ.', offer='none', tone='process')
        j.act('advance')
        j.act('advance')
        validate_state(j.state)
        # A plain reply without a tone keeps the old scripted path.
        post2 = engine.add_feed(j.state, j.c, 'milk_tea_npc_01', 'Chậm.', 'task-old3', 3, 'review')
        post2['feedback'] = copy.deepcopy(post['feedback'])
        post2['feedback'].update(thread=[], status='open', rounds=0, pending=None, task='task-old3')
        j.act('fb_reply', post=post2['id'], text='Xin lỗi bạn, lần sau bên mình sẽ sửa quy trình ạ.', offer='none')
        post2 = next(p for p in j.c['feed'] if p['id'] == post2['id'])
        self.assertNotIn('tone', post2['feedback']['thread'][0])
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
