"""New career copy and guidance must ship in the English runtime pack."""
import json
import unittest
from pathlib import Path

from game import guide_content as guides

ROOT = Path(__file__).resolve().parents[1]


class CreativeCivicEnglish(unittest.TestCase):
    def test_all_new_guides_have_english_copy(self):
        pack = json.loads((ROOT/'public/i18n/en.json').read_text(encoding='utf-8'))['strings']
        for cid in ('art_studio', 'lawyer', 'laundry', 'post_office'):
            guide = guides.CAREERS[cid]
            texts = [guide['name'], guide['place'], guide['intro']]
            texts += [s for key in ('steps', 'stars', 'prep', 'surprises') for s in guide[key]]
            texts += [j[k] for j in guide['jobs'] for k in ('name', 'how')]
            texts += [j[k] for j in guide['mistakes'] for k in ('bad', 'result')]
            for text in texts:
                with self.subTest(career=cid, text=text):
                    self.assertTrue(pack.get(text), 'New guide line needs an English translation')

    def test_endgame_titles_and_mastery_actions_have_english(self):
        from game import promotion_content as pc, career_mastery as cm
        pack = json.loads((ROOT/'public/i18n/en.json').read_text(encoding='utf-8'))['strings']
        labels = [t for table in (pc._EMP_HIGH, pc._OWN_HIGH) for titles in table.values() for t in titles]
        labels += [r['title'] for r in cm.STEPS]
        labels += ['Tay nghề lâu năm', 'Thưởng ngày tay nghề', 'Bắt đầu xét tay nghề · 4 câu', 'Nộp bài xét tay nghề']
        for label in labels:
            self.assertTrue(pack.get(label), 'Missing translation: ' + label)

    def test_critical_actions_and_finance_labels_are_translated(self):
        pack = json.loads((ROOT/'public/i18n/en.json').read_text(encoding='utf-8'))['strings']
        for label in ('Ghi cước vào phiếu', 'Chốt kiểm tranh', 'Đối chiếu và trả đồ', 'Gắn cặp chứng cứ',
                      'Nhập số nguyên từ 0 đến 10000.', 'Quỹ lương', 'Cân kiện và máy in nhãn bưu gửi'):
            self.assertTrue(label in pack, 'Missing translation: ' + label)


if __name__ == '__main__':
    unittest.main()
