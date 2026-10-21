"""🔧 Xưởng độ xe ships its English: the first-day guide, the certificate, the story arc, the specialism pack, the
desk surprises, the awkward demands, the notebook rules and every fixed line of the content are whole lines in
public/i18n/en.json; the ticket templates (names, numbers, plates) are patterns, checked in tests/tuning-ui.mjs."""
import json
import re
import unittest
from pathlib import Path

from game.careers import PLUGINS

ROOT = Path(__file__).resolve().parents[1]
VI = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', re.I)


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


@unittest.skipIf('tuning' not in PLUGINS, 'filtered out by MNL_CAREERS')
class English(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pack = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
        cls.strings = pack['strings']
        cls.patterns = [p[0] for p in pack['patterns']]

    def has(self, text):
        return bool(self.strings.get(text))

    def check(self, what, tree):
        missing = [t for t in texts(tree, []) if not self.has(t)]
        self.assertEqual(missing, [], f'tuning {what}: no English')

    def test_guide_certificate_story_and_specialisms(self):
        from game import career_stories as cs, certificate_content as cc, guide_content as gc
        self.check('guide', gc.CAREERS['tuning'])
        cert = [g for g in cc.GROUPS if g['id'] == 'tuning_basics']
        self.assertEqual(len(cert), 1)
        self.check('certificate', cert)
        self.check('story', cs.ARCS['tuning'])
        self.check('specialisms', json.loads((ROOT / 'game/data/career_specialisms_tuning.json').read_text(encoding='utf-8')))

    def test_desk_demands_rules_and_every_fixed_line(self):
        from game.careers import tuning as T, tuning_content as TC
        self.check('desk', TC.DESK)
        self.check('demands', TC.DEMANDS)
        self.check('rules', TC.RULES)
        self.check('content', {k: v for k, v in vars(TC).items() if k.isupper()})
        self.check('content card', T.content())

    def test_the_ticket_templates_have_patterns(self):
        """The generated lines (who brings which vehicle, the build sheet, the readings, the spec card) are patterns."""
        plain = {p.replace('(.+?)', '$').replace('\\', '') for p in self.patterns}
        for vi in ('$1 đưa chiếc $2 màu $3 vào xưởng: “$4”', 'Bảng độ đã chốt: $1; $2; $3; $4; $5; $6. Tổng tiền phụ tùng bao nhiêu xu?',
                   '$1 mã lực (trước độ $2)', 'đã độ: $1, $2, $3, $4, $5, $6', 'Giao xe đúng phiếu $1. Thu $2 xu: phụ tùng $3 xu, công $4 xu.',
                   'Mục tiêu: $1. Khách để $2 xu cho phụ tùng. Thứ tự ưu tiên của xưởng: $3. Món nào còn vừa tiền thì lấy, không vừa thì bỏ qua xét món sau. Chọn đủ các món sẽ lắp.'):
            self.assertIn(re.sub(r'\$\d', '$', vi), plain, vi)


if __name__ == '__main__':
    unittest.main()
