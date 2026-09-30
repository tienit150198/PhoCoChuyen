"""public_state (the projection every response carries): it works on a private save and shares
what it shows unchanged instead of copying it, so the caller's save is never touched; its memos
(review replies, desk bulletins, farm prices, people cards, which careers hire) give the same
bytes as working everything out afresh."""
import copy
import json
import unittest

from game import closeness as qn, desk, employment as emp, engine, feedback_voices as FV
from game.careers import farm
from game.engine import GameError, public_state, tree_copy
from tests.helpers import Journey
from tests.test_feedback_reviews import make_post

CAREERS = ('milk_tea', 'mother_baby', 'pharmacy', 'accounting', 'customer_care', 'teacher', 'tour_guide', 'corp_accounting',
           'tax_payroll', 'group_accounting', 'grocery', 'farm', 'florist', 'restaurant', 'homestay', 'tra_da')


def dump(v):
    return json.dumps(v, ensure_ascii=False, allow_nan=False)


def played(career, steps=5):
    """A save with an open day, some tasks and an open review with stars on the counter."""
    j = Journey(career)
    for _ in range(steps):
        try:
            j.act('advance')
        except GameError:
            break
    make_post(j, 'sour', pid_hint='-view')
    return j.state


def containers(x, out=None):
    """ids of every dict and list in x (views also hold shared content constants: never change them)."""
    out = set() if out is None else out
    if isinstance(x, dict):
        out.add(id(x))
        for v in x.values():
            containers(v, out)
    elif isinstance(x, list):
        out.add(id(x))
        for v in x:
            containers(v, out)
    return out


def forget_memos():
    for memo in (FV._TONES_MEMO, desk._BULLETINS, farm._MARKET, qn._BASES, qn._AT, emp._REQUIRED):
        memo.clear()


class PublicViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = {}
        for cid in CAREERS:
            try:
                cls.states[cid] = played(cid)
            except unittest.SkipTest:
                pass

    def test_the_callers_save_is_never_touched(self):
        for cid, s in self.states.items():
            before = dump(s)
            v = public_state(s)
            self.assertEqual(dump(s), before, cid)
            # the view is the caller's own: no list or dict in it belongs to the caller's save
            self.assertFalse(containers(v) & containers(s), cid)

    def test_a_handed_over_save_gives_the_same_bytes(self):
        for cid, s in self.states.items():
            for focus in (None, 'milk_tea', 'pharmacy', 'tax_payroll', cid):
                self.assertEqual(dump(public_state(s, full=focus)), dump(public_state(tree_copy(s), full=focus, migrated=True)), (cid, focus))

    def test_the_view_does_not_change_the_handed_over_save(self):
        for cid, s in self.states.items():
            mine = tree_copy(s)
            before = dump(mine)
            public_state(mine, migrated=True)
            self.assertEqual(dump(mine), before, cid)

    def test_memos_give_the_bytes_of_fresh_work(self):
        warm = {cid: dump(public_state(s)) for cid, s in self.states.items()}
        again = {cid: dump(public_state(s)) for cid, s in self.states.items()}
        forget_memos()
        cold = {cid: dump(public_state(s)) for cid, s in self.states.items()}
        self.assertEqual(warm, again)
        self.assertEqual(warm, cold)

    def test_review_replies_memo(self):
        j = Journey('milk_tea')
        post = make_post(j, 'sour', pid_hint='memo')
        forget_memos()
        first = FV.tone_choices(post)
        self.assertEqual(first, FV.tone_choices(copy.deepcopy(post)))
        first[0]['text'] = 'changed by a caller'                  # a caller's copy: the memo keeps its own rows
        self.assertNotEqual(FV.tone_choices(post)[0]['text'], 'changed by a caller')
        post['feedback']['rounds'] = 1                              # a new round: other replies
        forget_memos()
        fresh = FV.tone_choices(post)
        self.assertEqual(fresh, FV.tone_choices(post))
        post['feedback']['rounds'] = True                           # not a plain int: no memo row, same text as worked out
        self.assertEqual([r['text'] for r in FV.tone_choices(post)],
                         list(FV._tone_texts(post['id'], True, False, False, 'bạn', 'Thời gian chờ', 'kiên nhẫn còn 45%', 'ly trà sữa',
                                             engine.fbk._hash)))

    def test_farm_market_memo(self):
        for day in (1, 2, 3, 9, 40):
            got = farm.market(day)
            got['ca_chua'] = -1                                     # a caller's copy
            forget_memos()
            self.assertEqual(farm.market(day), farm._market(day))
            self.assertEqual(farm.market(day), farm._market(day))

    def test_memo_is_bounded(self):
        from game.memo import Memo
        m = Memo(entries=3, budget=100)
        for i in range(10):
            m.put(i, str(i), 10)
        self.assertEqual(list(m.rows), [7, 8, 9])                  # rows: the oldest go first
        m.get(7)
        m.put(10, 'x', 10)
        self.assertEqual(list(m.rows), [9, 7, 10])                 # least recently used goes
        m.put('big', 'y', 85)
        self.assertEqual(list(m.rows), [10, 'big'])                 # bytes: evicted down to the budget
        self.assertEqual(m.bytes, 95)
        m.put('huge', 'z', 101)                                     # larger than the whole budget: not kept
        self.assertIsNone(m.get('huge'))
        for memo in (FV._TONES_MEMO, desk._BULLETINS, farm._MARKET):
            self.assertLessEqual(memo.budget, 8 << 20)

    def test_desk_bulletin_memo(self):
        from game import desk_content as dc
        for career in ('pharmacy', 'accounting', 'customer_care'):
            for day in (1, 2, 4, 6, 9, 12):
                forget_memos()
                self.assertEqual(desk._bulletin(career, day), dc.bulletin(career, day))
                self.assertIs(desk._bulletin(career, day), desk._bulletin(career, day))


if __name__ == '__main__':
    unittest.main()
