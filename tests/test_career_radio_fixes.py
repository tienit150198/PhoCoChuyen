"""📻 Review fixes of the radio career (game/careers/radio.py): the last-minute trouble is about a news item tonight's
bulletin carries, the misread wish is one in tonight's box, a sponsor is spoken of as who they are (bà Năm is never
"ông"), and the slip's portrait is the person who speaks (client_npc) in both the radio and the research cards."""
import re
import unittest
from pathlib import Path

from game.careers import PLUGINS, kit

R = PLUGINS.get('radio')
if R is not None:
    from game.careers import radio_content as RC
ROOT = Path(__file__).resolve().parents[1]


def builds(job, days=range(1, 50)):
    for day in days:
        for slot in range(6):
            yield R.BUILD[job](kit.rng(R.ID, job, day, slot), day, slot)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Fixes(unittest.TestCase):
    def test_the_last_minute_fix_is_about_tonights_news(self):
        label = {x[0]: x[1] for rows in RC.NEWS.values() for x in rows}
        rows = {x[1]: x[0] for x in RC.BULLETIN_FIX}
        hit = 0
        for b, key, *_ in builds('bulletin'):
            fix = next(st for st in b['steps'] if st['id'] == 'bulletin.fix')
            need = rows[fix['evidence']]
            if need:
                hit += 1
                pick = next(st for st in b['steps'] if st['id'] == 'bulletin.pick')
                self.assertIn(label[need], [o['label'] for o in pick['options']])
        self.assertGreater(hit, 0)
        self.assertTrue(any(x[0] is None for x in RC.BULLETIN_FIX))   # always one that fits any bulletin
        self.assertNotIn('Lê Lai', ' '.join(x[1] for x in RC.BULLETIN_FIX))

    def test_the_misread_wish_is_in_tonights_box(self):
        text = {x[0]: x[1] for x in RC.WISH_OK}
        rows = {x[1]: x[0] for x in RC.WISH_SLIPS}
        self.assertEqual(set(rows.values()), set(text))   # a slip for every wish
        for b, key, *_ in builds('wishes'):
            slip = next(st for st in b['steps'] if st['id'] == 'wishes.slip')
            box = next(st for st in b['steps'] if st['id'] == 'wishes.skip')
            want = text[rows[slip['evidence']]]
            self.assertTrue(any(o['label'].endswith(want) for o in box['options']), (want, slip['evidence']))

    def test_a_sponsor_is_never_called_ong_unless_it_is_ong_luc(self):
        sponsors = {x[1]: x[0] for x in RC.SPONSORS}
        seen = set()
        for b, key, title, opening, npc in builds('spot'):
            sid = sponsors[b['sponsor']]
            seen.add(sid)
            words = ' '.join([st['evidence'] for st in b['steps']] + [o['label'] for st in b['steps'] for o in st.get('options', [])])
            self.assertIsNone(re.search(r'\b[Ôô]ng\b', words), (sid, words))
            if sid != 'lucphat':
                self.assertEqual(npc, RC.MANAGER)
            else:
                self.assertEqual(npc, RC.SPONSOR)
        self.assertIn('banam', seen)

    def test_the_card_shows_who_speaks(self):
        for name in ('radio', 'research'):
            js = (ROOT / f'public/js/careers/{name}.js').read_text(encoding='utf-8')
            self.assertIn('npc:t.client_npc||t.npc', js, name)


if __name__ == '__main__':
    unittest.main()
