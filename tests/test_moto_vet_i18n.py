"""🏍️ Tiệm sửa xe and 🩺 Thú y Cỏ May ship their English: the first-day guide, the certificate, the story arc, the
specialism pack, the desk surprises and the awkward demands are whole lines in public/i18n/en.json."""
import json
import re
import unittest
from pathlib import Path

from game.careers import PLUGINS

ROOT = Path(__file__).resolve().parents[1]
VI = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', re.I)
NEW = ('moto', 'vet')


def texts(x, out):
    """Every whole Vietnamese line in a content tree; templates ({name}) and ids are left to the patterns."""
    if isinstance(x, str):
        if VI.search(x) and '{' not in x and '|' not in x:
            out.append(' '.join(x.split()))
    elif isinstance(x, dict):
        for v in x.values():
            texts(v, out)
    elif isinstance(x, (list, tuple)):
        for v in x:
            texts(v, out)
    return out


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class English(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pack = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
        cls.strings = pack['strings']

    def has(self, text):
        return bool(self.strings.get(text))   # whole lines, not a generic pattern that leaves Vietnamese behind

    def check(self, cid, what, tree):
        missing = [t for t in texts(tree, []) if not self.has(t)]
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
        from game.careers import moto_content as mc, vet_content as vc
        for cid, content in (('moto', mc), ('vet', vc)):
            self.check(cid, 'desk', content.DESK)
            self.check(cid, 'demands', content.DEMANDS)


if __name__ == '__main__':
    unittest.main()
