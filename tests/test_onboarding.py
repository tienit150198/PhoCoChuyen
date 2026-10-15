"""A brand-new player's first minutes (server side): the welcome tip of the very first customer, the first
level-up with the third customer, Bà Tám's gift at the end of the first day, and "Có gì mới" read at naming.
A save past its first life day (and a sandbox save) sees none of it."""
import copy
import unittest

from game import boba, journey as jr, tips, tip_content as tc, whats_new as wn
from game.engine import apply_action, new_state, public_state, validate_state


def story_save(career='milk_tea', seed=7):
    """Like a new player in production: story on, named, the first workplace picked, day 1 open."""
    s = new_state()
    jr.enable_story(s, seed)
    s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
    s, _ = apply_action(s, career, 'select_career', {})
    s, _ = apply_action(s, career, 'start_day', {})
    return s


def serve_tea(s):
    """Serve the milk-tea customer in hand, perfectly."""
    c = s['careers']['milk_tea']
    tid = c['active_task']
    s, _ = apply_action(s, 'milk_tea', 'ask', {'task': tid})
    t = next(x for x in s['careers']['milk_tea']['tasks'] if x['id'] == tid)
    for action, payload in boba.solution(t):
        s, _ = apply_action(s, 'milk_tea', action, dict(payload, confirm=True) if action == 'tea_serve' else payload)
    t = next(x for x in s['careers']['milk_tea']['tasks'] if x['id'] == tid)
    assert t['status'] == 'completed', t['status']
    return s, t


class WelcomeTip(unittest.TestCase):
    def test_the_first_customer_leaves_a_small_tip_and_a_warm_line(self):
        s = story_save()
        fund = s['careers']['milk_tea']['money']
        s, t = serve_tea(s)
        roll = t['tip_roll']
        self.assertEqual((roll['kind'], roll['why'], roll['to']), ('cash', 'ok', 'till'))
        n = tc.NORMS['milk_tea']
        self.assertTrue(n['lo'] <= roll['amount'] <= n['hi'], roll)
        row = s['careers']['milk_tea']['life']['tip_day'][-1]
        self.assertEqual((row['id'], row['emoji'], row['amount']), (t['id'], '💝', roll['amount']))
        lines = [x.format(self='cô', ac='chị', gv='cô') for x in tc.WELCOME_LINES]
        self.assertIn(row['line'], lines)
        tip_rows = [r for r in s['careers']['milk_tea']['ops']['finance']['ledger'] if r.get('ref') == t['id'] and r.get('category') == 'tip']
        self.assertEqual(sum(r['amount'] for r in tip_rows), roll['amount'])   # through the till's cash book, once
        self.assertGreater(s['careers']['milk_tea']['money'], fund)
        validate_state(copy.deepcopy(s))
        # Deterministic: the same new player serving the same customer gets the same tip and line.
        s2, t2 = serve_tea(story_save())
        self.assertEqual((t2['tip_roll'], s2['careers']['milk_tea']['life']['tip_day'][-1]['line']), (roll, row['line']))

    def test_only_the_very_first_customer(self):
        s = story_save()
        s, _ = serve_tea(s)
        s, t2 = serve_tea(s)
        self.assertNotEqual(t2['tip_roll']['why'], 'first')   # the second job rolls like any other
        self.assertFalse(tips.welcome(s, t2))

    def test_not_outside_the_story_nor_after_the_first_day(self):
        # Sandbox (no story): the first job at a place stays calm, as before.
        s = new_state()
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s, t = serve_tea(s)
        self.assertEqual(t['tip_roll']['why'], 'first')
        # A player on life day 5 trying a new place: no welcome either.
        s = story_save()
        s['journey']['life_day'] = 5
        s, t = serve_tea(s)
        self.assertEqual(t['tip_roll']['why'], 'first')


class FirstLevelUp(unittest.TestCase):
    def test_the_third_cup_is_the_first_level_up(self):
        s = story_save()
        levels = []
        for _ in range(3):
            s, _ = serve_tea(s)
            c = s['careers']['milk_tea']
            levels.append((boba.level(c), 1 + c['xp'] // 90))
        self.assertEqual(levels, [(1, 1), (1, 1), (2, 2)])   # the counter skill and the workplace level together
        self.assertEqual(boba.TIERS[1], 3)


class WelcomeGift(unittest.TestCase):
    def end_day(self, s):
        return apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})

    def test_the_end_of_the_first_day_brings_a_gift_to_the_wallet(self):
        s = story_save()
        s, _ = serve_tea(s)
        before = s['journey']['wallet']
        s, r = self.end_day(s)
        J = s['journey']
        rows = [h for h in J['history'] if h['label'] == jr.WELCOME_LABEL]
        self.assertEqual([(h['day'], h['amount'], h['kind']) for h in rows], [(1, jr.WELCOME_GIFT, 'life')])
        living = r['summary']['journey']['living']
        self.assertEqual(J['wallet'], before - living + jr.WELCOME_GIFT)
        self.assertEqual(r['summary']['journey']['gift'], jr.WELCOME_GIFT)
        self.assertTrue(any('quà chào hàng xóm mới' in e for e in r['effects']))
        validate_state(copy.deepcopy(s))
        # Day 2 ends without one.
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s, r = self.end_day(s)
        self.assertEqual(len([h for h in s['journey']['history'] if h['label'] == jr.WELCOME_LABEL]), 1)
        self.assertNotIn('gift', r['summary']['journey'])

    def test_no_gift_outside_the_story(self):
        s = new_state()
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s, r = self.end_day(s)
        self.assertNotIn('journey', r['summary'])


class MidGameSave(unittest.TestCase):
    def test_a_player_on_day_five_sees_nothing_new(self):
        s = story_save()
        s['journey']['intro'] = True
        s['journey']['life_day'] = 5
        s['settings']['whatsNewSeen'] = '0.9.0'
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertEqual(s['settings']['whatsNewSeen'], '0.9.0')          # the notes still pop up for them
        s, t = serve_tea(s)
        self.assertEqual(t['tip_roll']['why'], 'first')                    # no welcome tip
        before = len(s['journey']['history'])
        s, r = apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})
        self.assertFalse(any(h['label'] == jr.WELCOME_LABEL for h in s['journey']['history'][before:]))
        self.assertNotIn('gift', r['summary']['journey'])


class NotesAtNaming(unittest.TestCase):
    def test_a_new_player_has_read_the_notes(self):
        self.assertEqual(story_save()['settings']['whatsNewSeen'], wn.LATEST)

    def test_a_new_save_is_marked_for_the_first_time_hints(self):
        s = story_save()
        self.assertEqual(s['settings']['notesSeen'].split(','), [jr.ONBOARD_MARK])
        # Idempotent, and it keeps what was there (an announcement already seen).
        s = new_state()
        jr.enable_story(s, 2)
        s, _ = apply_action(s, None, 'settings', {'notesSeen': 'guide-v1'})
        for g in ('female', 'male'):
            s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': g})
        self.assertEqual(s['settings']['notesSeen'], 'guide-v1,' + jr.ONBOARD_MARK)
        validate_state(copy.deepcopy(s))

    def test_older_saves_are_never_marked(self):
        s = new_state()   # sandbox
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertEqual(s['settings']['notesSeen'], '')
        s = story_save()
        s['settings']['notesSeen'] = 'guide-v1'
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan Anh', 'gender': 'female'})   # past the intro
        self.assertEqual(s['settings']['notesSeen'], 'guide-v1')


class InterfaceQuestionAtNaming(unittest.TestCase):
    """"Quay về giao diện cũ?" is for returning players: a new neighbour never saw the old interface."""
    def test_a_new_neighbour_is_not_asked(self):
        s = story_save()
        self.assertEqual(s['journey']['interface'], dict(interfacePromptSeen=True))
        self.assertIs(public_state(s)['settings']['interfacePromptSeen'], True)
        self.assertIs(public_state(s)['settings']['newInterface'], True)
        validate_state(copy.deepcopy(s))

    def test_a_choice_already_made_is_kept(self):
        s = new_state()
        jr.enable_story(s, 3)
        s['journey']['interface'] = dict(newInterface=False, interfacePromptSeen=False)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertEqual(s['journey']['interface'], dict(newInterface=False, interfacePromptSeen=False))

    def test_not_for_a_save_past_the_intro_nor_the_sandbox(self):
        s = new_state()
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertNotIn('interface', s['journey'])
        s = new_state()
        jr.enable_story(s, 3)
        s['journey'].update(intro=True, life_day=5)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertNotIn('interface', s['journey'])


class CalmFirstDays(unittest.TestCase):
    """Feedback 16/10 ("giai đoạn đầu khó chơi"): life days 2..EASY_DAYS of a new neighbour are calm days."""
    def close(self, s):
        return apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})[0]

    def test_days_two_and_three_are_calm_then_luck_rolls_again(self):
        s = story_save()
        s, _ = serve_tea(s)
        modes = []
        for _ in range(jr.EASY_DAYS):
            s = self.close(s)
            modes.append(s['careers']['milk_tea']['life']['mode'])
            s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        self.assertEqual(modes[:jr.EASY_DAYS - 1], ['calm'] * (jr.EASY_DAYS - 1))
        # Rolled at the close of life day EASY_DAYS: the usual luck of the day, the same as any later player's.
        day = s['careers']['milk_tea']['day']
        self.assertEqual(modes[-1], jr.roll_mode(dict(s, journey=dict(s['journey'], life_day=jr.EASY_DAYS)), 'milk_tea', day))
        self.assertEqual(s['journey']['life_day'], jr.EASY_DAYS + 1)
        validate_state(copy.deepcopy(s))

    def test_later_players_and_the_sandbox_keep_their_luck(self):
        s = story_save()
        rolls = {jr.roll_mode(dict(s, journey=dict(s['journey'], life_day=d)), 'milk_tea', 9) for d in (jr.EASY_DAYS, 40)}
        self.assertEqual(len(rolls), 1)          # past the first days the life day plays no part
        sandbox = new_state()
        self.assertEqual(jr.roll_mode(sandbox, 'milk_tea', 9), jr.roll_mode(dict(sandbox, journey=dict(sandbox['journey'], life_day=40)), 'milk_tea', 9))


if __name__ == '__main__':
    unittest.main()
