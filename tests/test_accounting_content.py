"""Curriculum integrity: original material and answers usable by the real checker."""
import importlib
import importlib.util
import unittest

from game import procedures


class AccountingContentTests(unittest.TestCase):
    def content(self):
        self.assertIsNotNone(importlib.util.find_spec('game.accounting_content'),
                             'The two accounting courses have not been implemented')
        return importlib.import_module('game.accounting_content')

    def answer(self, q):
        if q['kind'] == 'entry':
            return [dict(debit=d, credit=c, amount=a) for d, c, a in q['_key']]
        return q['_key']

    def test_full_courses_and_chapter_coverage(self):
        c = self.content()
        self.assertEqual({'basic', 'vn_business'}, {x['id'] for x in c.COURSES})
        for course in c.COURSES:
            lessons = [l for ch in course['chapters'] for l in ch['lessons']]
            self.assertGreaterEqual(len(lessons), 24 if course['id'] == 'basic' else 60)
            self.assertGreaterEqual(len(c.EXAM_BANK[course['id']]), len(lessons))
            self.assertEqual({ch['id'] for ch in course['chapters']},
                             {q['chapter_id'] for q in c.EXAM_BANK[course['id']]})
        self.assertEqual(len(c.LESSONS), sum(len(ch['lessons']) for x in c.COURSES for ch in x['chapters']))

    def test_lessons_teach_and_include_worked_examples_and_sources(self):
        c = self.content()
        self.assertGreaterEqual(len(c.SOURCES), 17)
        self.assertTrue(any('VAS17' in r['locator'] and 'vbpl.vn' in r['url']
                            for r in c.LESSONS['vn_business_deferredtax']['references']))
        # Accounting treatment and tax obligations need different primary sources.
        for lesson_id, source_words in {
            'basic_tax': ('Thuế GTGT', 'Thuế TNDN'),
            'vn_business_vat': ('Thuế GTGT',),
            'vn_business_currenttax': ('Thuế TNDN', '107/2023'),
            'vn_business_deferredtax': ('Thuế TNDN',),
            'vn_business_payroll': ('Thuế TNCN', 'Bảo hiểm xã hội'),
        }.items():
            refs = c.LESSONS[lesson_id]['references']
            for word in source_words:
                self.assertTrue(any(word in r['label'] and 'TT99' not in r['label']
                                    for r in refs), (lesson_id, word))
        for lesson in c.LESSONS.values():
            with self.subTest(lesson=lesson['id']):
                self.assertGreaterEqual(len(lesson['objectives']), 2)
                self.assertGreaterEqual(len(lesson['body']), 2)
                self.assertGreaterEqual(sum(len(p) for p in lesson['body']), 330)
                self.assertGreaterEqual(len(lesson['example']['lines']), 2)
                self.assertTrue(lesson['example']['title'])
                self.assertGreaterEqual(len(lesson['questions']), 3)
                self.assertTrue(lesson['references'])
                for r in lesson['references']:
                    self.assertTrue(r['url'].startswith('https://'))
                    self.assertTrue(r['label'] and r['locator'])

    def test_original_practice_and_exam_ids_and_prompts(self):
        c = self.content()
        practice = [q for l in c.LESSONS.values() for q in l['questions']]
        exams = [q for bank in c.EXAM_BANK.values() for q in bank]
        ids = [q['id'] for q in practice + exams]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse({q['prompt'] for q in practice} & {q['prompt'] for q in exams})
        self.assertEqual(len(exams), len({q['prompt'] for q in exams}))
        self.assertGreaterEqual(len({q['kind'] for q in practice}), 5)
        self.assertEqual(len(c.LESSONS), len({tuple(l['body']) for l in c.LESSONS.values()}))

    def test_every_authored_key_passes_real_shape_and_checker(self):
        c = self.content()
        all_q = [q for l in c.LESSONS.values() for q in l['questions']]
        all_q += [q for bank in c.EXAM_BANK.values() for q in bank]
        for q in all_q:
            with self.subTest(question=q['id']):
                self.assertTrue(q['prompt'] and q['title'] and q['explain'])
                self.assertTrue(procedures.shape_ok(q, self.answer(q)))
                self.assertTrue(procedures.check(q, self.answer(q)))
                if q['kind'] == 'entry':
                    self.assertTrue(all(0 < row[2] < 10**9 for row in q['_key']))

    def test_unsolved_public_projection_hides_answers(self):
        c = self.content()
        for lesson in c.LESSONS.values():
            rows, _ = procedures.public({'proc': lesson['questions'], 'proc_state': procedures.initial_state()})
            self.assertTrue(all('_key' not in q and 'explain' not in q for q in rows))
            self.assertFalse(any('Đáp án:' in q['prompt'] for q in rows))

    def test_tt99_current_account_names_and_statement_scope(self):
        c = self.content()
        chart = dict(c.ACCOUNT_CHART)
        self.assertEqual(chart['112'], 'Tiền gửi không kỳ hạn')
        self.assertEqual(chart['242'], 'Chi phí chờ phân bổ')
        self.assertEqual(chart['215'], 'Tài sản sinh học')
        self.assertEqual(chart['155'], 'Sản phẩm')
        self.assertEqual(chart['332'], 'Phải trả cổ tức, lợi nhuận')
        self.assertNotIn('611', chart)
        self.assertNotIn('441', chart)
        self.assertNotIn('466', chart)
        self.assertNotIn('461', chart)
        self.assertEqual(chart['158'], 'Nguyên liệu, vật tư tại kho bảo thuế')
        self.assertEqual(chart['244'], 'Ký quỹ, ký cược')
        self.assertEqual(chart['337'], 'Thanh toán theo tiến độ hợp đồng xây dựng')
        self.assertEqual(sum(len(code) == 3 for code in chart), 71)
        text = ' '.join(p for l in c.LESSONS.values() for p in l['body'])
        for topic in ('Báo cáo tình hình tài chính', 'Báo cáo kết quả hoạt động kinh doanh',
                      'Báo cáo lưu chuyển tiền tệ', 'Bản thuyết minh', 'thuế thu nhập hoãn lại',
                      'tài sản sinh học', 'chuyển đổi', 'VAS'):
            self.assertIn(topic, text)


if __name__ == '__main__':
    unittest.main()
