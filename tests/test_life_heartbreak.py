"""Heartbreak days never invent a lover (0.9.11): players reported "có bồ mà không biết" after cards like
"Bị chia tay" (three years, over in one text) although the game gives them no love life, and a player engaged
to another player read such a card as that person."""
import unittest

from game import life as lf
from game.content import CAREERS
from game.engine import validate_state
from game.life_content import HARD

from tests.test_life import L, at, play, run, state


def fire(s, hid, d=8):
    at(s, d)
    card = lf._fire_hard(s, L(s), lf.HARD_INDEX[hid], d, 'milk_tea')
    L(s)['pending'] = card
    return card


def engaged(s):
    s['marriage'] = dict(s.get('marriage') or {}, spouse=dict(name='An', status='engaged', since=1, wed=None, date=None))
    return s


class Heartbreak(unittest.TestCase):
    def test_partner_stories_exist_but_are_never_drawn(self):
        self.assertTrue(lf.PARTNER_STORIES <= set(lf.HARD_INDEX))
        s = state()
        for career in list(CAREERS) + [None]:
            for d in (6, 20, 90):
                ids = {x['id'] for x in lf._hard_pool(L(s), d, career)}
                self.assertFalse(ids & lf.PARTNER_STORIES, (career, d))
        left = {x['id'] for x in HARD if x['cat'] == 'that_tinh'} - lf.PARTNER_STORIES
        self.assertTrue(left, 'heartbreak days that need no partner remain')

    def test_long_runs_never_show_a_partner_story(self):
        for seed in (1, 7, 42):
            _, seen = run(seed, n=120)
            refs = {c['ref'] for c in seen if c and c.get('kind') == 'hard'}
            self.assertFalse(refs & lf.PARTNER_STORIES, seed)

    def test_engaged_or_married_players_get_no_heartbreak(self):
        s = engaged(state())
        self.assertTrue(lf._taken(s))
        s['marriage']['spouse']['status'] = 'married'
        self.assertTrue(lf._taken(s))
        for d in (6, 20, 90):
            cats = {x['cat'] for x in lf._hard_pool(L(s), d, 'teacher', taken=True)}
            self.assertNotIn('that_tinh', cats)
        self.assertFalse(lf._taken(state()))

    def test_a_save_holding_an_old_partner_card_still_plays(self):
        s = state()
        fire(s, 'tt_break')
        validate_state(s)
        play(s)
        validate_state(s)
        self.assertEqual(L(s)['log'][-1]['cat'], 'that_tinh')

    def test_breakup_rumour_only_after_being_left(self):
        s = state()
        fire(s, 'tt_blind')
        play(s)
        self.assertNotIn('breakup', lf.facts(s, 'teacher', dict(completed=3), 9))
        s = state()
        fire(s, 'tt_ghost')
        play(s)
        self.assertIn('breakup', lf.facts(s, 'teacher', dict(completed=3), 9))
        engaged(s)
        self.assertNotIn('breakup', lf.facts(s, 'teacher', dict(completed=3), 9))


if __name__ == '__main__':
    unittest.main()
