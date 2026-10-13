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

    def test_critical_actions_and_finance_labels_are_translated(self):
        pack = json.loads((ROOT/'public/i18n/en.json').read_text(encoding='utf-8'))['strings']
        for label in ('Ghi cước vào phiếu', 'Chốt kiểm tranh', 'Đối chiếu và trả đồ', 'Gắn cặp chứng cứ',
                      'Nhập số nguyên từ 0 đến 10000.', 'Quỹ lương', 'Cân kiện và máy in nhãn bưu gửi'):
            self.assertTrue(label in pack, 'Missing translation: ' + label)


if __name__ == '__main__':
    unittest.main()
