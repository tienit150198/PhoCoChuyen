"""🛕 Đi chùa (game/chua.py): the quiet acts at chùa Gió Lành for everyone in the story, free, a few a day; the
vegetarian meal on rằm and mùng 1; wishes; older saves, validation and refusals."""
import copy
import unittest

from game import chua as cg
from game import invest as iv
from game import journey as jr
from game import life as lf
from game.engine import GameError, apply_action, new_state, public_state, validate_state


def story(spirit=50, life_day=None):
    s = new_state()
    jr.enable_story(s, 11)
    s['journey'].update(gender='male', intro=True, wallet=40)
    iv.migrate(s)
    lf.migrate(s)
    s['journey']['life']['spirit'] = spirit
    if life_day:
        s['journey']['life_day'] = life_day
    validate_state(s)
    return s


def do(s, **p):
    return apply_action(s, None, 'jr_chua_do', p)


def spirit(s):
    return s['journey']['life']['spirit']


def feast(start=1):
    return next(d for d in range(start, start + 40) if cg.feast_day(d))


class Calendar(unittest.TestCase):
    def test_lunar_days(self):
        self.assertEqual(cg.lunar(1), 11)
        self.assertEqual(cg.lunar(5), 15)
        self.assertEqual(cg.lunar(21), 1)
        self.assertEqual(cg.lunar(35), 15)
        self.assertEqual(cg.lunar_label(5), 'Rằm')
        self.assertEqual(cg.lunar_label(21), 'Mùng 1')
        self.assertEqual([d for d in range(1, 61) if cg.feast_day(d)], [5, 21, 35, 51])


class Visit(unittest.TestCase):
    def test_free_quiet_acts_lift_the_spirit(self):
        s = story(50)
        wallet = s['journey']['wallet']
        s, r = do(s, act='huong')
        self.assertEqual(spirit(s), 52)
        self.assertIn('tinh thần +2', r['message'])
        s, r = do(s, act='ngoi')
        self.assertEqual(spirit(s), 54)
        self.assertGreaterEqual(s['journey']['needs']['wake'], 0)
        s, r = do(s, act='nguyen', wish='pho')
        self.assertEqual(spirit(s), 57)
        self.assertIn('Cho khu phố bình an.', r['message'])
        self.assertEqual(s['journey']['wallet'], wallet, 'never costs xu')
        self.assertEqual(s['journey']['chua'], dict(v=1, day=1, did=['huong', 'ngoi', 'nguyen'], n=3))
        validate_state(s)

    def test_daily_limit_and_once_each(self):
        s = story()
        s, _ = do(s, act='huong')
        with self.assertRaises(GameError) as e:
            do(s, act='huong')
        self.assertEqual(e.exception.code, 'already_done')
        s, _ = do(s, act='chuong')
        s, _ = do(s, act='quet')
        s, _ = do(s, act='ngoi')
        with self.assertRaises(GameError) as e:
            do(s, act='khan', who='ca_nha', what='khoe')
        self.assertEqual(e.exception.code, 'limit')
        view = cg.public(s)
        self.assertEqual(view['left'], 0)
        self.assertTrue(all(not a['ok'] and a['why'] for a in view['acts'] + view['more']))

    def test_a_new_day_opens_the_gate_again(self):
        s = story()
        for a in ('huong', 'chuong', 'quet'):
            s, _ = do(s, act=a)
        s['journey']['life_day'] += 1
        validate_state(s)
        self.assertEqual(cg.public(s)['left'], cg.DAILY)
        s, _ = do(s, act='huong')
        self.assertEqual(s['journey']['chua']['did'], ['huong'])
        self.assertEqual(s['journey']['chua']['n'], 4)

    def test_vegetarian_meal_only_on_full_moon_and_first_day(self):
        s = story(life_day=2)
        with self.assertRaises(GameError) as e:
            do(s, act='com')
        self.assertEqual(e.exception.code, 'not_now')
        self.assertEqual(next(a for a in cg.public(s)['acts'] if a['id'] == 'com')['why'], 'Chỉ rằm và mùng 1')
        s = story(life_day=feast())
        s['journey'].setdefault('needs', None)
        s['journey'].pop('needs')
        s, r = do(s, act='com')
        self.assertIn('no bụng', r['message'])
        self.assertEqual(s['journey']['wallet'], 40)
        validate_state(s)

    def test_spirit_is_capped(self):
        s = story(99)
        s, r = do(s, act='quet')
        self.assertEqual(spirit(s), 100)
        self.assertIn('tinh thần +1', r['message'])

    def test_bad_requests_are_refused(self):
        s = story()
        for p in (dict(act='xin_xam'), dict(act='nguyen'), dict(act='nguyen', wish='giau'), dict(act='huong', wish='nha'),
                  dict(act='huong', money=5)):
            with self.assertRaises(GameError, msg=p):
                do(s, **p)
        self.assertNotIn('chua', s['journey'])

    def test_outside_the_story_it_is_locked(self):
        s = new_state()
        with self.assertRaises(GameError) as e:
            apply_action(s, None, 'jr_chua_do', dict(act='huong'))
        self.assertEqual(e.exception.code, 'locked')
        self.assertEqual(public_state(s)['chua'], dict(enabled=False))


class Scene(unittest.TestCase):
    """1.4.8: the walkable pagoda; khấn put together by the player, the chant kept on the mõ, the abbot's words."""
    def test_khan_is_composed_by_the_player(self):
        s = story(50)
        s, r = do(s, act='khan', who='cha_me', what='khoe')
        self.assertEqual(spirit(s), 53)
        self.assertIn('Con cầu mong cha mẹ được mạnh khỏe.', r['message'])
        self.assertEqual(s['journey']['wallet'], 40)
        self.assertEqual(s['journey']['chua']['did'], ['khan'])
        with self.assertRaises(GameError) as e:
            do(s, act='khan', who='pho', what='binh_an')
        self.assertEqual(e.exception.code, 'already_done')
        validate_state(s)

    def test_khan_refuses_what_does_not_fit(self):
        s = story()
        for p in (dict(act='khan'), dict(act='khan', who='cha_me'), dict(act='khan', what='khoe'),
                  dict(act='khan', who='ong_ba', what='khoe'), dict(act='khan', who='cha_me', what='yen_nghi'),
                  dict(act='khan', who='vua', what='khoe'), dict(act='khan', who='cha_me', what='giau'),
                  dict(act='khan', who='cha_me', what='khoe', wish='nha'), dict(act='nguyen', wish='nha', who='cha_me'),
                  dict(act='huong', who='cha_me'), dict(act='khan', who='cha_me', what='khoe', beat=3)):
            with self.assertRaises(GameError, msg=p):
                do(s, **p)
        self.assertNotIn('chua', s['journey'])
        s, r = do(s, act='khan', who='ong_ba', what='yen_nghi')
        self.assertIn('ông bà đã khuất được yên nghỉ', r['message'])

    def test_every_prayer_reads_well_and_promises_nothing(self):
        for who, (words, whats) in cg.KHAN_WHO.items():
            self.assertTrue(whats and set(whats) <= set(cg.KHAN_WHAT), who)
        text = ' '.join(cg.KHAN_WHAT.values()).lower()
        for bad in ('may mắn', 'giàu', 'tiền', 'trúng', 'đỗ', 'thi'):
            self.assertNotIn(bad, text)

    def test_chant_spirit_follows_the_beats_kept(self):
        for beat, gain in ((0, 1), (3, 1), (4, 2), (8, 3), (cg.BEATS, 4)):
            s = story(50)
            s, r = do(s, act='tung', beat=beat)
            self.assertEqual(spirit(s), 50 + gain, beat)
            self.assertIn(f'tinh thần +{gain}', r['message'])
            self.assertEqual(s['journey']['wallet'], 40)
        s, r = do(story(), act='tung', beat=0)
        self.assertIn('Lần sau mình tụng chậm hơn chút', r['message'])

    def test_chant_refuses_bad_counts(self):
        s = story()
        for p in (dict(act='tung'), dict(act='tung', beat=-1), dict(act='tung', beat=cg.BEATS + 1), dict(act='tung', beat=True),
                  dict(act='tung', beat=2.5), dict(act='tung', beat='12'), dict(act='tung', beat=3, wish='nha')):
            with self.assertRaises(GameError, msg=p):
                do(s, **p)
        self.assertNotIn('chua', s['journey'])

    def test_public_carries_what_the_scene_needs(self):
        v = cg.public(story())
        self.assertEqual(v['chant'], dict(beats=cg.BEATS))
        self.assertEqual({w['id'] for w in v['khan']['who']}, set(cg.KHAN_WHO))
        self.assertEqual({w['id'] for w in v['khan']['what']}, set(cg.KHAN_WHAT))
        self.assertTrue(all(a['ok'] for a in v['more']))
        self.assertEqual(len(v['abbot']), 2)

    def test_the_abbot_speaks_of_the_day(self):
        ram = next(d for d in range(1, 40) if cg.lunar(d) == 15)
        mung1 = next(d for d in range(1, 40) if cg.lunar(d) == 1)
        self.assertEqual(cg.abbot_lines(ram)[0], cg.ABBOT_RAM)
        self.assertEqual(cg.abbot_lines(mung1)[0], cg.ABBOT_MUNG1)
        self.assertGreater(len({tuple(cg.abbot_lines(d)) for d in range(2, 12)}), 3)
        for d in range(1, 40):
            lines = cg.abbot_lines(d)
            self.assertEqual(len(lines), len(set(lines)))


class Saves(unittest.TestCase):
    def test_old_save_without_the_record_loads_and_shows(self):
        s = story()
        self.assertNotIn('chua', s['journey'])
        validate_state(s)
        v = public_state(s)['chua']
        self.assertTrue(v['enabled'])
        self.assertEqual(len(v['acts']) + len(v['more']), len(cg.ACTS))
        self.assertEqual(v['left'], cg.DAILY)

    def test_older_clients_only_see_the_acts_they_can_draw(self):
        # an older client draws every row of `acts` as a plain button (no prayer composer, no mõ)
        v = cg.public(story())
        self.assertEqual([a['id'] for a in v['acts']], ['huong', 'chuong', 'ngoi', 'nguyen', 'quet', 'com'])
        self.assertEqual([a['id'] for a in v['more']], list(cg.SCENE_ACTS))
        s, _ = do(story(), act='huong')
        s['journey']['chua']['did'].append('khan')   # a day with a scene act still loads
        s['journey']['chua']['n'] += 1
        validate_state(s)

    def test_validate_rejects_broken_records(self):
        s, _ = do(story(), act='huong')
        for bad in ('x', dict(v=1, day=1, did=['huong']), dict(v=2, day=1, did=[], n=0), dict(v=1, day=99, did=[], n=0),
                    dict(v=1, day=1, did=['huong', 'huong'], n=2), dict(v=1, day=1, did=['ghost'], n=1),
                    dict(v=1, day=1, did=['huong', 'chuong', 'quet', 'ngoi', 'khan'], n=5), dict(v=1, day=1, did=['huong'], n=0)):
            t = copy.deepcopy(s)
            t['journey']['chua'] = bad
            with self.assertRaises(GameError, msg=bad):
                validate_state(t)


if __name__ == '__main__':
    unittest.main()
