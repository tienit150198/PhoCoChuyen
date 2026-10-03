"""Review aspects: many more angles in reviews (taste, straw, restroom, teacher's patience, office dress...)."""
import copy
import json
import re
import unittest
from unittest import mock

from game import engine, feedback as F, feedback_voices as FV, review_aspects as RA, ai
from game.review_aspects_content import ASPECTS, FAMILY, WRAP, VOICE_WRAP, REGULAR_WRAP, COMBO, STYLE_WRAP, NHO
from game.engine import GameError, validate_state, public_state
from game.content import NPCS
from tests.helpers import Journey

BANNED = ('NPC', 'trong game', 'của game', 'trò chơi', 'mô phỏng', 'giả lập', 'hư cấu', '{', '}')
# The real criterion keys of each career (from their feedback() functions), for stubbed grading.
CRIT = {
    'milk_tea': ('accuracy', 'speed', 'attitude'), 'cafe_bakery': ('accuracy', 'taste', 'presentation'),
    'restaurant': ('broth', 'taste', 'hygiene', 'speed'), 'tra_da': ('tea', 'clean', 'manner', 'spot'),
    'ice_cream': ('order', 'scoop', 'cold', 'clean', 'speed'), 'pho': ('order', 'broth', 'banh', 'clean', 'speed'), 'com': ('order', 'rice', 'taste', 'care', 'speed'), 'nail': ('service', 'finish', 'clean', 'gentle', 'speed'), 'photobooth': ('order', 'shot', 'deco', 'speed'),
    'grocery': ('accuracy', 'price', 'dates', 'speed'), 'clothing': ('accuracy', 'care', 'manner', 'style'), 'pet_shop': ('ask', 'bill'),
    'florist': ('care', 'fresh'), 'mother_baby': ('accuracy', 'presentation', 'speed'), 'pharmacy': ('accuracy', 'care', 'speed'),
    'salon': ('attitude', 'care', 'speed'), 'repair': ('diagnosis', 'honesty', 'speed'), 'pet_care': ('coat', 'gentle', 'calm'),
    'homestay': ('room', 'welcome', 'warmth'), 'tour_guide': ('safety', 'story', 'pace'), 'delivery': ('time', 'condition', 'contact'),
    'farm': ('fresh', 'honest', 'quantity'), 'teacher': ('care', 'feedback', 'order'),
    'customer_care': ('resolution', 'attitude', 'speed'), 'accounting': ('accuracy', 'clarity', 'speed'),
    'corp_accounting': ('accuracy', 'grounds', 'speed', 'independence'), 'tax_payroll': ('accuracy', 'quality', 'speed'),
    'group_accounting': ('accuracy', 'handover', 'speed'),
    'hr_admin': ('accuracy', 'quality', 'care', 'speed'), 'secretary': ('accuracy', 'quality', 'care', 'speed'),
    'it_helpdesk': ('accuracy', 'quality', 'care', 'speed'),
}
NPC = {}
for n in NPCS:
    NPC.setdefault(n['career_id'], []).append(n['id'])


def stub_eval(scores=None):
    def ev(c, t, status):
        keys = CRIT[t['career']]
        h = F._hash('crit', t['id'])
        crit = [dict(key=k, label=k.title(), score=(scores or {}).get(k, (5, 5, 4, 3, 5, 4)[(h >> (3 * i)) % 6]), note='làm đúng lời dặn')
                for i, k in enumerate(keys)]
        low = min(x['score'] for x in crit)
        avg = sum(x['score'] for x in crit) / len(crit)
        return dict(criteria=crit, stars=max(1, min(5, round(min(avg, low + 1.5)))), cap=5)
    return ev


def task(career, i, day=8, **kw):
    npcs = NPC[career]
    t = dict(id=f'{career}-{day:04d}-{i:02d}', career=career, npc=npcs[i % len(npcs)], mistakes=0, patience=80, known=True,
             title='Việc hôm nay')
    t.update(kw)
    return t


def reviews(career, n=300, day=8, gender=None, c=None, scores=None, fresh=True, same_day=False, **kw):
    """n reviews for one workplace; fresh=True gives each its own record (no recent window)."""
    out = []
    shared = c if c is not None else dict(day=day, metrics={})
    with mock.patch.object(F, 'evaluate', stub_eval(scores)):
        for i in range(n):
            d = day if same_day else day + i // 12
            cc = dict(day=d, metrics={}) if fresh else shared
            cc['day'] = d
            t = task(career, i, d, **kw)
            out.append((t, cc, F.make_review({'journey': {'gender': gender}}, cc, t, 'completed')))
    return out


def said(made):
    return [a for a in made['feedback'].get('aspects') or [] if a.get('said', True)]


class Catalogue(unittest.TestCase):
    def test_counts_per_family(self):
        counts = RA.catalogue()
        for fam, least in (('food', 25), ('shop', 20), ('service', 25), ('school', 12), ('office', 12)):
            self.assertGreaterEqual(counts[fam], least, fam)

    def test_every_career_has_many_angles(self):
        for career in FAMILY:
            rows = RA.eligible(career, set())
            usable = [a for a in rows if RA.lines(a, 'neg', career, 'p') or RA.lines(a, 'pos', career, 'p')]
            self.assertGreaterEqual(len(usable), 8, career)

    def test_lines_are_clean_clauses(self):
        tokens = {'nv', 'nho', 'owner', 'item'}
        n = 0
        for a in ASPECTS.values():
            self.assertTrue(a['label'])
            groups = []
            for pol in ('neg', 'pos'):
                rows = a[pol]
                groups += list(rows) if isinstance(rows, (list, tuple)) else [x for v in rows.values() for x in v]
            self.assertTrue(groups, a['id'])
            for line in groups + a['sarc']:
                n += 1
                self.assertLessEqual(set(re.findall(r'\{(\w+)\}', line)), tokens, line)
                self.assertFalse(ai.unsafe_review(line), line)
                for bad in BANNED[:-2]:
                    self.assertNotIn(bad, line)
            for line in groups:
                self.assertFalse(line.endswith('.'), line)
                self.assertTrue(line[0].islower() or line[0] == '{', line)
            if not a['claim']:
                self.assertFalse(a['neg'] and not a['sig_neg'], a['id'])   # a claim-less aspect is grounded only
        self.assertGreater(n, 450)

    def test_wrappers_format(self):
        for table in (WRAP, VOICE_WRAP, STYLE_WRAP):
            for rows in table.values():
                for pol in ('neg', 'pos', 'mix'):
                    self.assertTrue(rows[pol])
                    for tpl in rows[pol]:
                        self.assertTrue('{x}' in tpl or '{X}' in tpl, tpl)
        for pol in ('neg', 'pos'):
            for tpl in REGULAR_WRAP[pol]:
                self.assertIn('{x}', tpl)
        for tpl in COMBO['mix']:
            self.assertTrue('{pos}' in tpl and '{neg}' in tpl)
        for persona in F.PERSONAS:
            self.assertIn(persona, WRAP, persona)

    def test_signal_names_are_known(self):
        known = {'messy', 'worn', 'small_place', 'garden', 'dark_porch', 'plant', 'bare', 'sunny', 'rain', 'breeze', 'festival', 'crowded',
                 'calm', 'busy_day', 'cat', 'slow', 'quick', 'slow_crowd', 'fast_crowd', 'regular', 'overtime', 'sealer_dirty', 'seal_good',
                 'grimy_cups', 'no_ice', 'dirty_bowls', 'return_task', 'litter'}
        for a in ASPECTS.values():
            for x in a['sig_neg'] + a['sig_pos'] + a['need']:
                self.assertTrue(x in known or re.fullmatch(r'(slip:[a-z_]+|crit:[a-z_]+:(lo|hi))', x), (a['id'], x))


class Coverage(unittest.TestCase):
    def test_every_career_gets_varied_aspects(self):
        for career in CRIT:
            rows = reviews(career, 240)
            with_aspects = [m for _, _, m in rows if said(m)]
            ids = {a['id'] for m in with_aspects for a in said(m)}
            self.assertGreater(len(with_aspects) / len(rows), 0.2, career)
            self.assertGreaterEqual(len(ids), 6, (career, ids))
            for _, _, m in rows:
                self.assertLessEqual(len(m['text']), 600)
                self.assertFalse(ai.unsafe_review(m['text']), m['text'])
                for bad in BANNED:
                    self.assertNotIn(bad, m['text'], m['text'])

    def test_combined_and_styled_reviews_appear(self):
        rows = reviews('cafe_bakery', 900) + reviews('milk_tea', 900)
        self.assertTrue([m for _, _, m in rows if len(said(m)) == 2])
        mixed = [m for _, _, m in rows if len({a['pos'] for a in said(m)}) == 2]
        self.assertTrue(mixed)
        styled = {m['feedback'].get('style') for _, _, m in rows if said(m)}
        self.assertTrue(styled & set(RA.STYLES_OK), styled)

    def test_quiet_reviewers_use_one_word(self):
        rows = [m for _, _, m in reviews('clothing', 900) if m['feedback']['persona'] == 'quiet' and said(m) and not m['feedback'].get('style')]
        self.assertTrue(rows)
        words = {w for a in ASPECTS.values() for w in a['word'] if w}
        self.assertTrue(any(any(m['text'].endswith(w) for w in words) for m in rows))

    def test_teacher_reviews_speak_as_parents(self):
        seen = 0
        for t, _, m in reviews('teacher', 400, gender='female'):
            if said(m) and F.PERSONAS[m['feedback']['persona']]['group'] == 'parent':
                seen += 1
                self.assertNotIn('cô/thầy', m['text'])
                for a in said(m):
                    parent = {x.replace('cô/thầy', 'cô') for x in RA.lines(ASPECTS[a['id']], 'pos' if a['pos'] else 'neg', 'teacher', 'p', a['tied'])}
                    self.assertIn(a['text'], parent)
        self.assertGreater(seen, 20)


class Grounded(unittest.TestCase):
    def options(self, career, sig):
        g, f, s = RA._options(career, sig, [], 'p')
        return {(x[0], x[1]) for x in g}, {(x[0], x[1]) for x in f}, s

    def test_state_signals(self):
        t = task('tra_da', 1)
        c = dict(day=4, ext=dict(data=dict(glasses=dict(grimy=2, dirty=0, clean=3), ice=dict(portions=0))), metrics={})
        sig = RA.signals({}, c, t, [])
        self.assertIn('grimy_cups', sig)
        self.assertIn('no_ice', sig)
        g, _, _ = self.options('tra_da', sig)
        self.assertIn(('cups', 'neg'), g)
        self.assertIn(('ice', 'neg'), g)
        c = dict(day=4, ext=dict(data=dict(boba=dict(sealer_wear=25, mess=0))), metrics={})
        self.assertIn('sealer_dirty', RA.signals({}, c, task('milk_tea', 1), []))
        c = dict(day=4, ext=dict(data=dict(plan=dict(day=4, rules=dict(dirty=3)))), metrics={})
        sig = RA.signals({}, c, task('restaurant', 1), [])
        self.assertIn('dirty_bowls', sig)
        self.assertIn(('dishes', 'neg'), self.options('restaurant', sig)[0])

    def test_speed_follows_patience_and_regulars(self):
        self.assertIn('slow', RA.signals({}, dict(day=3), task('grocery', 1, patience=40), []))
        self.assertIn('quick', RA.signals({}, dict(day=3), task('grocery', 1, patience=95), []))
        self.assertNotIn('quick', RA.signals({}, dict(day=3), {k: v for k, v in task('grocery', 1).items() if k != 'patience'}, []))
        t = task('grocery', 1)
        self.assertIn('regular', RA.signals({}, dict(day=3, metrics={'served:' + t['npc']: 4}), t, []))
        g, _, _ = self.options('grocery', {'slow'})
        self.assertIn(('speed', 'neg'), g)

    def test_criteria_ground_teacher_and_office(self):
        g, f, _ = self.options('teacher', {'crit:care:lo', 'crit:feedback:hi'})
        self.assertIn(('method', 'neg'), g)
        self.assertIn(('patience', 'neg'), g)
        self.assertIn(('marking', 'pos'), g)
        g, f, _ = self.options('teacher', {'crit:care:hi'})
        self.assertIn(('method', 'pos'), g)
        self.assertNotIn(('method', 'neg'), f)       # grounded praise wins over a seeded complaint
        g, _, _ = self.options('corp_accounting', {'crit:independence:lo', 'crit:speed:hi'})
        self.assertIn(('selfreliant', 'neg'), g)
        self.assertIn(('o_time', 'pos'), g)

    def test_state_bound_complaints_need_their_state(self):
        _, f, _ = self.options('restaurant', set())
        self.assertNotIn(('table', 'neg'), f)
        self.assertNotIn(('flies', 'neg'), f)
        self.assertIn(('restroom', 'neg'), f)       # ambient, answerable
        g, _, _ = self.options('restaurant', {'messy'})
        self.assertIn(('table', 'neg'), g)
        for _, _, m in reviews('restaurant', 600):
            for a in said(m):
                if a['id'] in ('table', 'flies', 'dishes') and not a['pos'] and not a['tied']:
                    self.fail('complaint without state: ' + m['text'])

    def test_slipped_aspects_are_recorded_not_repeated(self):
        slips = [dict(code='seal', sev=2, text='Nắp dán hở, trà rỉ ra túi.', note='', safety=False)]
        _, _, slipped = self.options('milk_tea', {'slip:seal'})
        self.assertIn(('lid', 'slip:seal'), slipped)
        for t, _, m in reviews('milk_tea', 200, slips=slips, mistakes=1):
            for a in m['feedback'].get('aspects') or []:
                if a['id'] == 'lid':
                    self.assertIs(a.get('said'), False)

    def test_signal_specific_lines(self):
        a = ASPECTS['floor']
        self.assertTrue(all('mưa' in x for x in RA.lines(a, 'neg', 'cafe_bakery', None, 'rain')))
        self.assertFalse(any('mưa' in x for x in RA.lines(a, 'neg', 'cafe_bakery', None, 'messy')))

    def test_day_one_is_grounded_only(self):
        rows = reviews('cafe_bakery', 400, day=1, same_day=True)
        self.assertTrue([m for _, _, m in rows if said(m)])
        for _, _, m in rows:
            for a in said(m):
                self.assertTrue(a['tied'], m['text'])
            self.assertIsNone((m['feedback'].get('unfair') or {}).get('aspect'))


class Gender(unittest.TestCase):
    def test_tokens(self):
        g = lambda x: {'journey': {'gender': x}}
        self.assertEqual(RA._tokens(g('female'), 'accounting', 'rude')['nho'], 'con nhỏ')
        self.assertEqual(RA._tokens(g('male'), 'accounting', 'rude')['nho'], 'thằng nhỏ')
        self.assertNotIn('nhỏ', RA._tokens(g(None), 'accounting', 'rude')['nho'])
        self.assertNotIn('nhỏ', RA._tokens(g('female'), 'accounting', 'warm')['nho'])
        self.assertEqual(RA._tokens(g('female'), 'grocery', 'warm')['nv'], 'chị nhân viên')
        self.assertEqual(RA._tokens(g(None), 'grocery', 'warm')['nv'], 'bạn nhân viên')

    def test_office_jabs_follow_gender(self):
        line = next(x for x in ASPECTS['attitude']['neg']['*'] if x.startswith('{nho} khó ưa'))
        p = dict(picks=[dict(id='attitude', pol='neg', tied=None)], voice=None, sig=set())
        for gender, want, other in (('female', 'con nhỏ', 'thằng nhỏ'), ('male', 'thằng nhỏ', 'con nhỏ'), (None, 'bạn đó', 'nhỏ')):
            texts = set()
            for seed in range(200):
                x, rows = RA.render(p, {'journey': {'gender': gender}}, task('accounting', seed), 'rude', 'customer', None, 'hồ sơ', seed)
                texts.add(x.lower())
            joined = ' '.join(texts)
            self.assertIn(want + ' khó ưa', joined)
            self.assertNotIn(other, joined.replace(want, '') if gender else joined)
        self.assertTrue(line)

    def test_neutral_player_is_never_gendered(self):
        for career in ('accounting', 'corp_accounting', 'grocery', 'clothing'):
            for _, _, m in reviews(career, 300, gender=None):
                for a in said(m):
                    for word in ('con nhỏ', 'thằng nhỏ', 'anh nhân viên', 'chị nhân viên'):
                        self.assertNotIn(word, a['text'])


class Rules(unittest.TestCase):
    def test_deterministic(self):
        for career in ('milk_tea', 'teacher', 'tax_payroll'):
            a = reviews(career, 60)
            b = reviews(career, 60)
            self.assertEqual(json.dumps([m for _, _, m in a], sort_keys=True, ensure_ascii=False),
                             json.dumps([m for _, _, m in b], sort_keys=True, ensure_ascii=False))

    def test_no_repeats_within_the_window(self):
        for career in ('cafe_bakery', 'grocery', 'teacher', 'group_accounting'):
            c = dict(day=8, metrics={})
            rows = reviews(career, 240, c=c, fresh=False)
            history = []
            for _, _, m in rows:
                ids = [a['id'] for a in said(m)]
                for x in ids:
                    self.assertNotIn(x, history[-RA.RECENT:], (career, x, history[-RA.RECENT:]))
                history += ids
                self.assertLessEqual(len(c.get(RA.RECENT_KEY) or []), RA.RECENT)
            self.assertTrue(history)

    def test_stars_follow_the_job(self):
        drops = total = 0
        for career in ('cafe_bakery', 'clothing', 'accounting', 'homestay'):
            for t, c, m in reviews(career, 400):
                fb = m['feedback']
                total += 1
                u = fb.get('unfair') or {}
                if u.get('aspect'):
                    drops += 1
                    self.assertEqual(m['stars'], fb['fair'] - 1)
                    self.assertIn(RA.CLUE, fb['clues'])
                    first = said(m)[0]
                    self.assertFalse(first['pos'])
                    self.assertIsNone(first['tied'])
                    self.assertEqual(u['aspect'], first['id'])
                elif said(m) and not (fb.get('twist') or fb.get('gripe') or fb.get('unfair') or fb.get('style')):
                    self.assertGreaterEqual(m['stars'], min(fb['fair'], 4) if fb['persona'] in F.HARSH else fb['fair'], m['text'])
        self.assertGreater(drops, 0)
        self.assertLess(drops / total, 0.08)

    def test_no_complaints_after_flawless_work(self):
        seen = 0
        for career in ('cafe_bakery', 'tra_da', 'clothing', 'teacher', 'accounting', 'homestay'):
            perfect = {k: 5 for k in CRIT[career]}
            for t, c, m in reviews(career, 200, scores=perfect):
                fb = m['feedback']
                self.assertFalse((fb.get('unfair') or {}).get('aspect'), m['text'])
                for a in said(m):
                    seen += 1
                    self.assertTrue(a['pos'] or (a['tied'] and a['tied'] not in RA.AMBIENT), (career, a, m['text']))
        self.assertGreater(seen, 100)
        # One weak criterion is enough for a subjective complaint to be fair game again.
        negs = sum(1 for t, c, m in reviews('cafe_bakery', 200, scores=dict(accuracy=5, taste=5, presentation=3))
                   for a in said(m) if not a['pos'])
        self.assertGreater(negs, 0)

    def test_no_aspects_on_twists_gripes_and_failures(self):
        for t, c, m in reviews('milk_tea', 600, day=15):
            fb = m['feedback']
            if fb.get('twist') or fb.get('gripe'):
                self.assertFalse(said(m))
        with mock.patch.object(F, 'evaluate', stub_eval()):
            for i in range(100):
                m = F.make_review({}, dict(day=9), task('milk_tea', i, 9), 'cancelled')
                self.assertFalse(said(m))


class Saves(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 9

    def post(self, pred, career='milk_tea', **kw):
        with mock.patch.object(F, 'evaluate', stub_eval(kw.pop('scores', None))):
            for i in range(3000):
                t = task(career, i, 9, **kw)
                c = copy.deepcopy(self.j.c)
                made = F.make_review(self.j.state, c, t, 'completed')
                if pred(made):
                    made = F.make_review(self.j.state, self.j.c, t, 'completed')
                    post = engine.add_feed(self.j.state, self.j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
                    F.attach(post, made)
                    return post
        raise AssertionError('no review matched')

    def test_new_fields_validate_and_old_records_load(self):
        post = self.post(lambda m: said(m))
        validate_state(self.j.state)
        self.assertTrue(self.j.c[RA.RECENT_KEY])
        pub = public_state(self.j.state)['careers']['milk_tea']
        view = next(p for p in pub['feed'] if p['id'] == post['id'])
        self.assertNotIn('aspects', view['feedback'])
        # An older save: no recent list, no aspects on the review.
        old = copy.deepcopy(self.j.state)
        c = old['careers']['milk_tea']
        c.pop(RA.RECENT_KEY)
        for p in c['feed']:
            (p.get('feedback') or {}).pop('aspects', None)
        validate_state(old)

    def test_bad_fields_rejected(self):
        post = self.post(lambda m: said(m))
        for bad in ([dict(id='wifi_x', pos=True, tied=None)], [dict(id='wifi', pos='yes', tied=None)],
                    [dict(id='wifi', pos=True, tied=None, extra=1)], [dict(id='wifi', pos=True, tied=None)] * 5):
            s = copy.deepcopy(self.j.state)
            p = next(x for x in s['careers']['milk_tea']['feed'] if x['id'] == post['id'])
            p['feedback']['aspects'] = bad
            with self.assertRaises(GameError):
                validate_state(s)
        for bad in (['wifi'] * 7, ['nope'], 'wifi', [3]):
            s = copy.deepcopy(self.j.state)
            s['careers']['milk_tea'][RA.RECENT_KEY] = bad
            with self.assertRaises(GameError):
                validate_state(s)

    def test_unfair_aspect_can_be_answered_with_facts(self):
        post = self.post(lambda m: (m['feedback'].get('unfair') or {}).get('aspect') and m['feedback']['persona'] not in ('entitled', 'drama'),
                         'milk_tea', patience=80)
        fb = post['feedback']
        self.assertEqual(post['stars'], fb['fair'] - 1)
        d = F.scripted_decision(fb['persona'], fb, post['stars'], 'Dạ camera hôm đó ghi nhận quán dọn mỗi giờ ạ. Cảm ơn góp ý, lần sau quán sẽ chú ý thêm.', 'none')
        self.assertEqual(d['decision'], 'revise_up')
        self.assertEqual(d['stars'], fb['fair'])
        self.assertIn(d['text'], F.TWIST_REPLY['aspect_soft'])
        t = FV.tone_decision(self.j.state, self.j.c, post, 'facts', 'none')
        self.assertEqual(t['decision'], 'revise_up')
        ctx = F.ai_context(self.j.c, post)
        self.assertEqual(ctx['facts']['situation'], RA.SITUATION)
        self.assertTrue(ctx['facts']['aspects'])


class AIPath(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 9

    def aspect_post(self):
        return Saves.post(self, lambda m: said(m) and not m['feedback'].get('style') and not m['feedback'].get('gripe'))

    def test_facts_and_prompt_carry_the_aspects(self):
        post = self.aspect_post()
        seen = {}

        def fake_chat(msgs, **kw):
            seen['msgs'] = msgs
            return 'Cà phê thơm mà ống hút giấy mềm nhũn giữa chừng, hơi tiếc.', None
        with mock.patch.object(ai, 'chat', fake_chat):
            line = ai.review_voice(self.j.c, post)
        self.assertTrue(line)
        facts = json.loads(seen['msgs'][1]['content'])
        self.assertTrue(facts['aspects'])
        want = {ASPECTS[a['id']]['label'] for a in said({'feedback': post['feedback']})}
        self.assertEqual({a['goc'] for a in facts['aspects'] if a.get('chi_tiet')}, want)
        system = seen['msgs'][0]['content']
        self.assertIn('aspects', system)
        self.assertIn('ngoại hình', system)
        self.assertIn('thương hiệu', system)

    def test_unsafe_ai_output_falls_back(self):
        post = self.aspect_post()
        for bad in ('Nhân viên béo ú mà chậm chạp.', 'Thua xa Highlands đầu ngõ.', 'Dân nhà quê pha trà dở.'):
            with mock.patch.object(ai, 'chat', lambda msgs, **kw: (bad, None)):
                self.assertIsNone(ai.review_voice(self.j.c, post), bad)
        with mock.patch.object(ai, 'chat', lambda msgs, **kw: ('Con nhỏ đứng quầy khó ưa, ăn mặc như đi chợ.', None)):
            self.assertTrue(ai.review_voice(self.j.c, post))

    def test_reply_decision_is_filtered_too(self):
        post = self.aspect_post()
        post['feedback']['status'] = 'awaiting'
        post['feedback']['pending'] = dict(decision='keep', stars=post['stars'], text='Ừ.', turn=0)
        reply = json.dumps(dict(decision='keep', stars=post['stars'], text='Bà già đó pha trà dở.'), ensure_ascii=False)
        with mock.patch.object(ai, 'chat', lambda msgs, **kw: (reply, None)):
            self.assertIsNone(ai.feedback_decision(self.j.c, post))


if __name__ == '__main__':
    unittest.main()
