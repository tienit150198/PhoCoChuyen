"""📱 KOL, 🎤 ca sĩ phòng trà and 🎬 diễn viên ship their English: the first-day guide, the certificate, the story arc, the
specialism pack, the desk surprises, the awkward demands and the deal/set/scene names are whole lines in
public/i18n/en.json."""
import json
import unittest
from pathlib import Path

from game.careers import PLUGINS
from tests.test_moto_vet_i18n import texts

ROOT = Path(__file__).resolve().parents[1]
NEW = ('kol', 'singer', 'actor')


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class English(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strings = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))['strings']

    def check(self, cid, what, tree):
        missing = [t for t in texts(tree, []) if not self.strings.get(t)]
        self.assertEqual(missing, [], f'{cid} {what}: no English')

    def test_guide_certificate_story_and_specialisms(self):
        from game import career_stories as cs, certificate_content as cc, guide_content as gc
        for cid in NEW:
            self.check(cid, 'guide', gc.CAREERS[cid])
            cert = [g for g in cc.GROUPS if g['id'] == f'{cid}_basics']
            self.assertEqual(len(cert), 1)
            self.check(cid, 'certificate', cert)
            self.check(cid, 'story', cs.ARCS[cid])
            self.check(cid, 'specialisms', json.loads((ROOT / f'game/data/career_specialisms_{cid}.json').read_text(encoding='utf-8')))

    def test_desk_surprises_demands_and_rules(self):
        from game.careers import actor_content as ac, kol_content as kc, singer_content as sc
        for cid, content, jobs in (('kol', kc, kc.DEALS), ('singer', sc, sc.SETS), ('actor', ac, ac.SCENES)):
            self.check(cid, 'desk', content.DESK)
            self.check(cid, 'demands', content.DEMANDS)
            self.check(cid, 'rules', content.RULES)
            self.check(cid, 'people', content.PEOPLE)
            self.check(cid, 'jobs', [j['name'] for j in jobs.values()])


if __name__ == '__main__':
    unittest.main()
