"""👶 Bé nhà mình (game/cradle.py, feedback #252 / #145): the baby grows through stages, free moments at home
(gắn bó +1, a little tinh thần, once per baby and act per day, never a chore), baby things never on credit, the
shared child's moments through game/family.py, GET /api/family/baby, and "bế bé đi chơi" on the live service
(live/babies.py: `bb` on walk_in / fair_in, the shared child in one pair of arms at a time)."""
import copy
import json
import unittest

from game import cradle as cr
from game import household as hh
from game import journey as jr
from game import marriage as mr
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_bank import B, story, with_card


def act(s, action, **params):
    return apply_action(s, None, action, params)


def with_child(s=None, name='Bông'):
    s = s or story(500)
    s['journey']['life_day'] = max(12, s['journey']['life_day'])
    s, _ = act(s, 'jr_hh_adopt', kind='child', name=name, confirm=True)
    return s


class Grow(unittest.TestCase):
    def test_stages_by_age(self):
        self.assertEqual([cr.grow(d) for d in (0, 6, 7, 20, 21, 400)],
                         ['so_sinh', 'so_sinh', 'biet_bo', 'biet_bo', 'chap_chung', 'chap_chung'])
        self.assertEqual(cr.calendar_age('2026-10-01', '2026-10-08'), 7)
        self.assertEqual(cr.calendar_age('2026-10-09', '2026-10-08'), 0, 'still awaited')
        self.assertEqual(cr.calendar_age(None, '2026-10-08'), 0)

    def test_household_child_is_drawn_by_age(self):
        s = with_child()
        m = hh.public(s)['members'][0]
        self.assertEqual((m['age'], m['grow']), (0, 'so_sinh'))
        s['journey']['life_day'] += 8
        self.assertEqual(hh.public(s)['members'][0]['grow'], 'biet_bo')
        s['journey']['life_day'] += 14
        self.assertEqual(hh.public(s)['members'][0]['grow'], 'chap_chung')
        s, _ = act(s, 'jr_hh_adopt', kind='cat', name='Miu', confirm=True)
        cat = [x for x in hh.public(s)['members'] if x['id'] == 'pet'][0]
        self.assertNotIn('grow', cat, 'pets keep their own shape')


class Moments(unittest.TestCase):
    def test_free_moments_bond_spirit_and_once_a_day(self):
        s = with_child()
        j = s['journey']
        j['life']['spirit'] = 50
        wallet, bond = j['wallet'], j['household']['child']['bond']
        for a in ('bu', 'ru', 'choi'):
            s, r = act(s, 'jr_cradle_do', baby='child', act=a)
            self.assertIn('gắn bó +1', r['message'])
        j = s['journey']
        self.assertEqual(j['wallet'], wallet, 'moments are free')
        self.assertEqual(j['household']['child']['bond'], bond + 3)
        self.assertEqual(j['cradle'], dict(v=1, day=j['life_day'], did=['child:bu', 'child:ru', 'child:choi']))
        self.assertEqual(public_state(s)['journey']['cradle']['spirit_left'], 0)
        self.assertEqual(j['life']['spirit'], 50 + cr.SPIRIT_DAY)
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_cradle_do', baby='child', act='bu')
        self.assertEqual(e.exception.code, 'already_done')
        self.assertEqual(s, before)
        validate_state(s)
        s['journey']['life_day'] += 1                  # a new day: again, nothing missed or decayed
        s, _ = act(s, 'jr_cradle_do', act='ru')
        self.assertEqual(s['journey']['cradle']['did'], ['child:ru'])
        validate_state(s)

    def test_spirit_only_for_the_first_moments_of_a_day(self):
        s = with_child()
        j = s['journey']
        j['cradle'] = dict(v=1, day=j['life_day'], did=['shared:bu', 'shared:ru', 'copy:3:choi'])
        out = cr.moment(s, 'child', 'bu', 'Bông', 'so_sinh')
        self.assertEqual(out['spirit'], 0)
        self.assertNotIn('tinh thần', out['message'])

    def test_refusals(self):
        s = story(500)
        s['journey']['life_day'] = 12
        with self.assertRaises(GameError) as e:
            act(s, 'jr_cradle_do', baby='child', act='bu')
        self.assertEqual(e.exception.code, 'not_found')
        s = with_child()
        for bad in (dict(act='dance'), dict(baby='shared', act='bu'), dict(baby='child', act='bu', extra=1), dict(act=None)):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                act(s, 'jr_cradle_do', **bad)
        self.assertNotIn('cradle', s['journey'])
        free = copy.deepcopy(s)
        free['journey']['story'] = False
        with self.assertRaises(GameError):
            cr.moment(free, 'child', 'bu', 'Bông', 'so_sinh')

    def test_old_saves_and_bad_shapes(self):
        s = with_child()
        self.assertNotIn('cradle', s['journey'])
        validate_state(s)                               # an older save: no block at all
        self.assertEqual(jr.public(s)['cradle']['did'], [])
        s, _ = act(s, 'jr_cradle_do', act='choi')
        j = s['journey']
        for bad in ({}, [], dict(v=1, day=j['life_day'], did=[]) | {'x': 1}, dict(v=2, day=j['life_day'], did=[]),
                    dict(v=1, day=j['life_day'] + 1, did=[]), dict(v=1, day=j['life_day'], did=['child:bu', 'child:bu']),
                    dict(v=1, day=j['life_day'], did=['cat:bu']), dict(v=1, day=j['life_day'], did=['child:dance']),
                    dict(v=1, day=j['life_day'], did=[7]), dict(v=1, day='1', did=[])):
            t = copy.deepcopy(s)
            t['journey']['cradle'] = bad
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(t)

    def test_older_release_keeps_the_save(self):
        """journey.validate allows extra keys: the previous release loads a save with `cradle` unchanged."""
        s = with_child()
        s, _ = act(s, 'jr_cradle_do', act='bu')
        t = copy.deepcopy(s)
        del t['journey']['cradle']
        self.assertLessEqual(set(jr.initial()), set(t['journey']))
        self.assertLessEqual(set(jr.initial()), set(s['journey']))
        self.assertEqual(set(s['journey']) - set(t['journey']), {'cradle'})


class NoCredit(unittest.TestCase):
    def broke(self):
        s = with_child(with_card())
        s['journey']['wallet'] = 0
        B(s)['balance'] = 0
        return s

    def test_baby_things_never_go_on_the_card(self):
        s = self.broke()
        before = copy.deepcopy(s)
        for name, p in (('jr_hh_care', dict(member='child', act='milk')),
                        ('jr_hh_care', dict(member='child', act='milk', pay='card')),
                        ('jr_hh_style', dict(member='child', item='yem', confirm=True)),
                        ('jr_hh_style', dict(member='child', item='yem', confirm=True, pay='card'))):
            with self.subTest(name=name, p=p), self.assertRaises(GameError) as e:
                act(s, name, **p)
            self.assertIn(e.exception.code, ('no_credit', 'not_enough'))
        self.assertEqual(s, before, 'nothing charged, no card debt')
        s, _ = act(s, 'jr_hh_care', member='child', act='wash')   # the free care still works
        s['journey']['wallet'] = 50
        s, r = act(s, 'jr_hh_care', member='child', act='milk')   # cash when there is cash
        self.assertEqual(s['journey']['wallet'], 50 - hh.ACTS['milk']['cost'])

    def test_auto_falls_back_to_cash_when_the_preference_is_the_card(self):
        s = with_child(with_card())
        B(s)['pref'] = 'card'
        s['journey']['wallet'] = 100
        s, _ = act(s, 'jr_hh_style', member='child', item='yem', confirm=True)
        self.assertEqual(s['journey']['wallet'], 100 - hh.OUTFITS['yem']['cost'])

    def test_pets_are_unchanged(self):
        s = with_card()
        s['journey']['life_day'] = max(12, s['journey']['life_day'])
        s['journey']['wallet'] = 0
        B(s)['balance'] = 0
        s, _ = act(s, 'jr_hh_adopt', kind='cat', name='Miu', confirm=True, pay='card')
        self.assertEqual(s['journey']['household']['pet']['kind'], 'cat')


try:
    from tests.test_couple import CoupleBase
except Exception:  # noqa: BLE001
    CoupleBase = None


if CoupleBase is not None:
    class SharedBaby(CoupleBase):
        def setUp(self):
            super().setUp()
            for token in (self.a, self.b):
                mr._mutate(self.store, {self.sid(token): lambda s: s['journey'].__setitem__('life_day', 12)})
                self.fund(token, 5000)

        def family(self, token):
            return self.view(token)['family']

        def child(self, origin='adopt'):
            self.act(self.a, 'family_child_request', name='Bông', origin=origin, rid='child-invite-001')
            request = self.family(self.b)['requests'][0]
            self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='child-accept-001')
            return self.family(self.a)['child']

        def test_moment_bonds_the_shared_child_and_is_quiet(self):
            from game import family
            child = self.child()
            self.assertEqual((child['age'], child['grow']), (0, 'so_sinh'))
            wallet = self.wallet(self.a)
            out = family.act(self.store, self.sid(self.a), 'family_child_moment', dict(child='shared', act='bu', rid='moment-bu-0001'))
            self.assertTrue(out['quiet'])
            self.assertTrue(out['changed'])
            self.assertIn('gắn bó +1', out['message'])
            again = family.act(self.store, self.sid(self.a), 'family_child_moment', dict(child='shared', act='bu', rid='moment-bu-0001'))
            self.assertEqual(again, out, 'a retry replays the receipt')
            with self.assertRaises(mr.MarriageError) as e:
                self.act(self.a, 'family_child_moment', child='shared', act='bu', rid='moment-bu-0002')
            self.assertEqual(e.exception.code, 'already_done')
            self.act(self.b, 'family_child_moment', child='shared', act='bu', rid='moment-bu-0003')   # each parent their own
            self.assertEqual(self.family(self.a)['child']['bond'], child['bond'] + 2)
            self.assertEqual(self.wallet(self.a), wallet)
            self.assertEqual(self.state(self.a)['journey']['cradle']['did'], ['shared:bu'])
            self.clock.t += 9 * 86400
            self.assertEqual(self.family(self.a)['child']['grow'], 'biet_bo')

        def test_moment_waits_for_the_birth(self):
            self.child('birth')
            with self.assertRaises(mr.MarriageError) as e:
                self.act(self.a, 'family_child_moment', child='shared', act='ru', rid='moment-early-01')
            self.assertEqual(e.exception.code, 'waiting')
            self.assertNotIn('cradle', self.state(self.a)['journey'])

        def test_baby_endpoint(self):
            from game import family
            self.assertEqual(family.babies(self.store, self.a)['child'], None)
            self.assertEqual(family.babies(self.store, ''), {})
            self.assertEqual(family.babies(self.store, 'no-such-token')['copies'], [])
            self.child()
            out = family.babies(self.store, self.b)
            self.assertEqual(out['child']['name'], 'Bông')
            self.assertEqual(out['child']['grow'], 'so_sinh')
            self.assertEqual(out['copies'], [])
            json.dumps(out)
            self.act(self.a, 'divorce', confirm='LY HON')
            out = family.babies(self.store, self.a)
            self.assertIsNone(out['child'])
            self.assertEqual(out['copies'][0]['name'], 'Bông')
            cid = out['copies'][0]['id']
            self.act(self.a, 'family_child_moment', child=cid, act='choi', rid='copy-moment-001')
            self.assertEqual(self.state(self.a)['journey']['cradle']['did'], [f'{cid}:choi'])

        def test_shared_baby_items_never_on_credit(self):
            self.child()
            with self.assertRaises(mr.MarriageError) as e:
                self.act(self.a, 'family_child_style', child='shared', item='yem', pay='card', rid='style-card-001')
            self.assertEqual(e.exception.code, 'no_credit')


from tests.live_support import HAVE_WS  # noqa: E402

if HAVE_WS:
    from live.babies import clean_baby
    from tests.test_coride import LOOK, Couple

    class Wire(unittest.TestCase):
        def test_clean_baby(self):
            self.assertEqual(clean_baby({'n': 'Bông', 'g': 'biet_bo', 'o': 'yem', 'sh': 1}), {'n': 'Bông', 'g': 'biet_bo', 'o': 'yem', 'sh': 1})
            self.assertEqual(clean_baby({'g': 'so_sinh', 'o': 'gold', 'x': 1}), {'g': 'so_sinh', 'o': 'basic'})
            for odd in (None, 1, 'so_sinh', [], {}, {'g': 'teen'}, {'n': 'Bông'}):
                self.assertIsNone(clean_baby(odd), odd)
            self.assertNotIn('http', json.dumps(clean_baby({'n': 'http://x.vn', 'g': 'so_sinh'})))

    class CarryBaby(Couple):
        BABY = {'n': 'Bông', 'g': 'chap_chung', 'o': 'flower'}

        def goer_of(self, c):
            return self.app.hub.rooms.get(c.room['room']).data['people'][c.pid]

        async def test_seen_on_a_stroll_and_at_the_fair(self):
            (ta, sa), _ = self.pair()
            c = await self.stroll(ta, bb=self.BABY)
            me = [p for p in c.room['people'] if p['pid'] == c.pid][0]
            self.assertEqual(me['bb'], self.BABY)
            self.assertNotIn('bb_taken', c.room)
            g = await self.goer(ta, bb={**self.BABY, 'g': 'so_sinh'})
            self.assertEqual(self.goer_of(g).bb['g'], 'so_sinh')
            self.assertEqual(self.goer_of(g).public()['bb']['g'], 'so_sinh')
            plain = await self.stroll(self.account('Khách Lạ')[0])
            self.assertNotIn('bb', [p for p in plain.room['people'] if p['pid'] == plain.pid][0])

        async def test_shared_child_in_one_pair_of_arms(self):
            (ta, sa), (tb, sb) = self.pair()
            shared = {**self.BABY, 'sh': 1}
            wife = await self.stroll(tb, bb=shared)
            self.assertEqual([p for p in wife.room['people'] if p['pid'] == wife.pid][0]['bb'], shared)
            husband = await self.goer(ta, bb=shared)                     # the fair: she already carries it
            self.assertEqual(husband.room['bb_taken']['by'], self.pid(sb))
            self.assertEqual(husband.room['bb_taken']['name'], 'Lan Anh')
            self.assertIsNone(self.goer_of(husband).bb)
            self.assertNotIn('bb', self.goer_of(husband).public())
            own = await self.stroll(ta, bb=self.BABY)                    # his personal child: never taken
            self.assertEqual([p for p in own.room['people'] if p['pid'] == own.pid][0]['bb'], self.BABY)


if __name__ == '__main__':
    unittest.main()
