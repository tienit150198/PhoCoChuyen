"""🍱 Căn tin trường and ✏️ Tiệm văn phòng phẩm ship their English: the first-day guide, the certificate, the story arc,
the specialism pack, the desk surprises, the rules, the day's mood, the goods, the people and the intro are whole lines in
public/i18n/en.json. (What the counter says at run time, and the station itself, are checked through the client's i18n
layer in tests/counter-careers-ui.mjs.)"""
import json
import unittest

from game.careers import PLUGINS
from tests.test_moto_vet_i18n import ROOT, texts

NEW = ('canteen', 'stationery')


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

    def test_desk_rules_day_goods_people_and_intro(self):
        for cid in NEW:
            plugin = PLUGINS[cid]
            mod = __import__(f'game.careers.{cid}_content', fromlist=['DESK'])
            self.check(cid, 'desk', mod.DESK)
            self.check(cid, 'rules', mod.RULES)
            self.check(cid, 'day', mod.MODS)
            self.check(cid, 'goods', [[g['name'], g['unit']] for g in mod.GOODS.values()] + [t for _, t in mod.GROUPS])
            self.check(cid, 'people', mod.PEOPLE)
            self.check(cid, 'intro', plugin.content()['intro'])
            self.check(cid, 'meta', plugin.SPEC['meta'])

    def test_registry_lines(self):
        from game import journey, life_content, promotion_content, tip_content, work_gear
        for cid in NEW:
            self.check(cid, 'title', [[t['name'], t['desc']] for t in journey.TITLES if t['id'] == f'c_{cid}'])
            self.check(cid, 'life', life_content.WORK[cid])
            self.check(cid, 'promotion', [promotion_content.OWN_TITLES[cid]])
            self.check(cid, 'tips', [tip_content.CAREER_LINES[cid], [g[1] for g in tip_content.GIFTS[cid]]])
            self.check(cid, 'gear', work_gear.NAMES[cid])


if __name__ == '__main__':
    unittest.main()
