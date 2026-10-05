"""Author validation retains its accepted IDs and safe rejection of corrupt saves."""
import copy
import unittest
from game import engine


def populated_career(posts=1):
    s = engine.new_state()
    c = s['careers']['accounting']
    npc = next(reversed(engine.NPC_INDEX))
    post = engine.add_feed(s, c, npc, 'Khách thử nghiệm', 'test')
    post['comments'] = [dict(author='Khách', text='Cảm ơn', day=1, npc=npc)]
    c['feed'] = [dict(copy.deepcopy(post), id=f'post-{i}') for i in range(posts)]
    return c


class AuthorValidation(unittest.TestCase):
    def test_every_known_author_and_player_still_passes(self):
        c = populated_career()
        for npc in ['player', *engine.NPC_INDEX]:
            c['feed'][0]['npc'] = npc
            c['feed'][0]['comments'][0]['npc'] = npc
            engine.validate_career(c, 'accounting')

    def test_corrupt_authors_fail_as_game_errors(self):
        for value in [None, '', 'not-a-npc', [], {}, 7, True]:
            for comment in [False, True]:
                with self.subTest(value=value, comment=comment):
                    c = populated_career()
                    target = c['feed'][0]['comments'][0] if comment else c['feed'][0]
                    target['npc'] = value
                    with self.assertRaises(engine.GameError):
                        engine.validate_career(c, 'accounting')

    def test_validation_does_not_mutate_history(self):
        c = populated_career(1200)
        before = copy.deepcopy(c)
        engine.validate_career(c, 'accounting')
        self.assertEqual(before, c)
