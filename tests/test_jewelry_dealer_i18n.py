"""💍 Tiệm vàng Ngọc Mây and 🚗 Đại lý xe Phố Mây ship their English: the first-day guide, the certificate, the story
arc, the specialism pack, the desk surprises, the awkward demands, the rules and the intro are whole lines in
public/i18n/en.json."""
import json
import unittest

from game.careers import PLUGINS
from tests.test_moto_vet_i18n import ROOT, texts

NEW = ('jewelry', 'car_dealer')


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class English(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pack = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
        cls.strings = pack['strings']

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

    def test_desk_surprises_demands_rules_and_intro(self):
        for cid in NEW:
            content = PLUGINS[cid]
            mod = __import__(f'game.careers.{cid}_content', fromlist=['DESK'])
            self.check(cid, 'desk', mod.DESK)
            self.check(cid, 'demands', mod.DEMANDS)
            self.check(cid, 'rules', mod.RULES)
            self.check(cid, 'intro', content.content()['intro'])
            self.check(cid, 'meta', content.SPEC['meta'])


if __name__ == '__main__':
    unittest.main()
