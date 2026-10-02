"""Học kế toán: release safety (older saves, rolling release, payload sizes, hostile payloads, hints)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from game import accounting_company as company
from game import accounting_content as content
from game import accounting_hints as hints
from game import accounting_school as school
from game.engine import GameError, apply_action, migrate_state, needs_migration, new_state, public_state, validate_state

size = lambda x: len(json.dumps(x, ensure_ascii=False).encode())


def rows(q):
    return [(x['debit'], x['credit'], x['amount']) if isinstance(x, dict) else tuple(x) for x in q['_key']]


def answer(q):
    if q['kind'] == 'entry': return [dict(debit=d, credit=c, amount=v) for d, c, v in rows(q)]
    return copy.deepcopy(q['_key'])


class OlderSaves(unittest.TestCase):
    def test_block_is_created_only_on_first_use(self):
        s = new_state()
        self.assertNotIn('accounting_school', s)
        self.assertFalse(needs_migration(migrate_state(s)))
        self.assertNotIn('accounting_school', migrate_state(s))
        validate_state(s)
        v = public_state(s)['accounting_school']
        self.assertEqual(v['salary_multiplier'], 1)
        self.assertLess(size(v), 300)
        s2, r = apply_action(s, None, 'as_view', {})
        self.assertIn('accounting_school', s2)
        self.assertNotIn('accounting_school', s)
        validate_state(s2)
        self.assertIn('accounting_view', r)

    def test_receipt_keeps_no_view_and_replay_still_answers(self):
        from game.storage import Store
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'a.db')
            token, _, _ = store.session()
            out = store.command(token, 'req-as-view-1', 0, None, 'as_view', {'view': {'tab': 'learn', 'course': 'basic'}})
            self.assertIn('accounting_view', out['result'])
            with store.connect() as db:
                text = db.execute('SELECT result FROM receipts').fetchone()['result']
            self.assertNotIn('accounting_view', text)
            again = store.command(token, 'req-as-view-1', 0, None, 'as_view', {'view': {'tab': 'learn', 'course': 'basic'}})
            self.assertTrue(again['replayed'])
            self.assertLess(size(out['state']['accounting_school']), 300)


class HostilePayloads(unittest.TestCase):
    def setUp(self):
        self.s = new_state()
        school.migrate(self.s)

    def test_wrong_types_are_refused_cleanly(self):
        lesson = next(iter(content.LESSONS))
        bad = [('as_open', {'lesson': ['x']}), ('as_open', {'lesson': {'a': 1}}), ('as_exam_start', {'course': ['basic']}),
               ('as_exam_start', {'course': {'basic': 1}}), ('as_answer', {'lesson': lesson, 'question': ['q'], 'answer': 1}),
               ('as_exam_answer', {'question': 'x'}), ('as_exam_cancel', {'confirm': 'yes'}), ('as_company_inspect', {'task': {}}),
               ('as_nope', {}), ('as_view', {'view': {'tab': ['learn'], 'sub': {}, 'course': 5, 'glossary': 'yes'}})]
        for name, p in bad:
            try:
                apply_action(self.s, None, name, p)
            except GameError:
                pass
        school.action(self.s, 'as_open', {'lesson': lesson})
        for value in (None, 5, 'x' * 10_000, [[]], {'a': []}, [{'debit': [], 'credit': {}, 'amount': 1}] * 9):
            q = content.LESSONS[lesson]['questions'][0]
            with self.assertRaises(GameError):
                school.action(self.s, 'as_answer', {'lesson': lesson, 'question': q['id'], 'answer': value})

    def test_view_spec_is_sanitised(self):
        v = school.view(self.s, {'tab': ['x'], 'sub': {'a': 1}, 'course': [], 'glossary': 1})
        self.assertIsNone(v['tab'])
        self.assertNotIn('glossary', v)


class NoAnswersInViews(unittest.TestCase):
    def test_practice_help_never_names_the_answer(self):
        for l in content.LESSONS.values():
            for q in l['questions']:
                v = school._safe_question(q, lesson=l)
                self.assertEqual(len(v['help']), 2)
                text = v['help'][1]  # hint 1 names the lesson (its title may hold a code)
                self.assertIn('ghi', text) if q['kind'] == 'entry' else None
                if q['kind'] == 'entry':
                    for d, c, a in rows(q):
                        self.assertNotIn(d, text)
                        self.assertNotIn(c, text)
                        self.assertNotIn(f'{a:,}'.replace(',', '.'), text)
                if q['kind'] == 'number':
                    self.assertNotIn(str(q['_key']), text)
                self.assertNotIn('_key', repr(v))
        for bank in content.EXAM_BANK.values():
            for q in bank:
                self.assertNotIn('help', school._safe_question(q))

    def test_option_position_does_not_give_the_answer(self):
        firsts = 0; total = 0
        for q in [q for l in content.LESSONS.values() for q in l['questions']] + [q for b in content.EXAM_BANK.values() for q in b]:
            if q['kind'] == 'multi':
                total += 1; firsts += sorted(q['_key']) == [o['id'] for o in q['options'][:len(q['_key'])]]
            if q['kind'] == 'order':
                total += 1; firsts += q['_key'] == [o['id'] for o in q['items']]
            if q['kind'] == 'match':
                total += 1; firsts += all(v == 'r' + k[1:] for k, v in q['_key'].items())
        self.assertLess(firsts, total / 2)

    def test_company_desk_hides_report_answers_and_voucher_codes(self):
        book = company.initial()
        rows = company.tasks(book)
        v = company.public(book)
        self.assertNotIn('reports', v)
        self.assertNotIn('help', v['task'])  # voucher still closed
        for ref in v['task']['references']: self.assertNotIn('TK', ref['locator'])
        for t in rows:
            if t.get('report'): break
            company.inspect(book, t['id']); company.submit(book, t['id'], copy.deepcopy(t['_key']))
        v = company.public(book)
        self.assertEqual(v['task']['report'], 'position')
        self.assertTrue(all(v['statements'][f].get('locked') for f in ('B01', 'B02', 'B03', 'B09')))
        company.inspect(book, 'position')
        self.assertEqual(len(company.public(book)['task']['help']), 2)
        company.submit(book, 'position', copy.deepcopy(rows[book['at']]['_key']))
        v = company.public(book, 'reports')
        self.assertFalse(v['statements']['B01'].get('locked'))
        self.assertTrue(v['statements']['B02'].get('locked'))
        self.assertNotIn('ledger', v)

    def test_wrong_answer_hint_points_at_the_mistake(self):
        q = next(q for l in content.LESSONS.values() for q in l['questions'] if q['kind'] == 'entry' and len(q['_key']) == 1)
        (d, c, a), = rows(q)
        self.assertIn('đảo', hints.wrong(q, [dict(debit=c, credit=d, amount=a)]))
        self.assertIn('số tiền', hints.wrong(q, [dict(debit=d, credit=c, amount=a + 1)]))
        other = next(x for x, _ in content.ACCOUNT_CHART if x not in (d, c))
        self.assertIn('bên Nợ', hints.wrong(q, [dict(debit=other, credit=c, amount=a)]))
        for msg in (hints.wrong(q, [dict(debit=other, credit=c, amount=a)]),):
            self.assertNotIn(d, msg)

    def test_glossary_covers_every_company_account(self):
        codes = {r['code'] for r in hints.glossary()}
        self.assertTrue(set(company.CHART) <= codes)
        self.assertTrue(all(r['nature'] for r in hints.glossary()))


class FullYear(unittest.TestCase):
    def test_full_progress_sizes_and_pay_once_per_month(self):
        from game import journey
        s = new_state(); journey.enable_story(s)
        def act(name, p=None):  # the reducer's own step (apply_action on 1,500 steps would validate whole saves each time)
            out = school.action(s, name, p or {})
            school.validate(s)
            return out
        for cid in school.COURSE_IDS:
            for ch in school.course(cid)['chapters']:
                for l in ch['lessons']:
                    act('as_open', {'lesson': l['id']})
                    for q in l['questions']: act('as_answer', {'lesson': l['id'], 'question': q['id'], 'answer': answer(q)})
            act('as_exam_start', {'course': cid})
            for qid in list(s['accounting_school']['active_exam']['qs']):
                act('as_exam_answer', {'question': qid, 'answer': answer(school.exam_question(cid, qid))})
        act('as_company_join')
        wallet = s['journey']['wallet']; paid = 0
        for period in range(1, 13):
            for t in company.tasks(s['accounting_school']['company']):
                act('as_company_inspect', {'task': t['id']})
                act('as_company_answer', {'task': t['id'], 'answer': answer(t)})
            paid += act('as_company_finish')['salary']
            with self.assertRaises(GameError): act('as_company_finish')
            if period < 12: act('as_company_next')
        with self.assertRaises(GameError): act('as_company_next')
        base = s['careers']['corp_accounting']['job']['salary']
        self.assertEqual(paid, 12 * 3 * base)
        self.assertEqual(s['journey']['wallet'], wallet + paid)
        validate_state(s)
        self.assertLess(size(s['accounting_school']), 45_000)
        self.assertLess(size(public_state(s)['accounting_school']), 300)
        for spec in ({'tab': 'learn', 'course': 'basic'}, {'tab': 'learn', 'course': 'vn_business'}, {'tab': 'exam', 'course': 'vn_business'},
                     {'tab': 'company', 'sub': 'documents'}, {'tab': 'company', 'sub': 'journal'}, {'tab': 'company', 'sub': 'ledger'},
                     {'tab': 'company', 'sub': 'details'}, {'tab': 'company', 'sub': 'reports'}):
            self.assertLess(size(school.view(s, spec)), 60_000, spec)


if __name__ == '__main__':
    unittest.main()
