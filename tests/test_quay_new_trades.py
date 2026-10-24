"""#501 + #507 (players 24/10): 💄 Mỹ phẩm, 🎀 Phụ kiện dễ thương and 🍢 Cá viên chiên at the counter (game/quay.py TRADES).
Each is opened by the jobs of a nearby career (Làm móng, Văn phòng phẩm, Trà đá vỉa hè): that career's 10 jobs open
it, its staff stand there, the wallet rows and a hired shift name that career (journey.validate checks them)."""
import unittest

from game import quay as qy
from game import quay_economy as qe
from game import quay_self as qs
from game import shop_events
from game.engine import GameError, public_state, validate_state
from tests.test_quay import ST, act, days, owner, refused

NEW = {'cosmetics': 'nail', 'cute_acc': 'stationery', 'ca_vien': 'tra_da'}


class Catalogue(unittest.TestCase):
    def test_new_trades_like_the_others(self):
        from game.content import CAREERS
        for trade, career in NEW.items():
            T = qy.TRADES[trade]
            self.assertEqual(qy.career_of(trade), career)
            self.assertIn(career, CAREERS)
            self.assertEqual(len(qs.MENUS[trade]), 12)
            self.assertEqual(sum(r[3] for r in qs.MENUS[trade][:3]), 3 * T['price'])
            self.assertEqual(len({r[0] for r in qs.MENUS[trade]}), 12)
            self.assertIn(trade, qs.TOOL)
            self.assertIn(trade, qs.TOOL_DEFAULT)
            for place in qy.PLACE_IDS:
                self.assertIn(trade, qe.SUPPLIES[place])
            for k in ('nang', 'mua', 'fest', 'cogs', 'mult'):
                self.assertTrue(30 <= T[k] <= 160, (trade, k))
        # cá viên is food and spoils (the hygiene check, dine-and-dash); cosmetics and accessories keep
        self.assertGreater(qy.TRADES['ca_vien']['spoil'], 0)
        self.assertEqual((qy.TRADES['cosmetics']['spoil'], qy.TRADES['cute_acc']['spoil']), (0, 0))
        self.assertIn('ca_vien', qe.FOOD)
        self.assertIn('ca_vien', shop_events.FOOD)
        self.assertFalse({'cosmetics', 'cute_acc'} & (qe.FOOD | shop_events.FOOD))
        for trade in qy.TRADE_IDS:   # every older trade is its own career
            if trade not in NEW:
                self.assertEqual(qy.career_of(trade), trade)
        cat = qy.catalogue()['trades']
        self.assertEqual(cat['cosmetics'], dict(emoji='💄', name='Mỹ phẩm', career='nail', career_name='Làm móng'))
        self.assertEqual(cat['milk_tea']['career'], 'milk_tea')

    def test_margins_sit_with_the_other_trades(self):
        """The new trades earn like the old ones: a staffed day's value and the share of revenue kept."""
        old = [qy.shift_value(p, t) for p in qy.PLACE_IDS for t in qy.TRADE_IDS if t not in NEW and t != 'grocery']
        for trade in NEW:
            for place in qy.PLACE_IDS:
                v = qy.shift_value(place, trade)
                peers = [qy.shift_value(place, t) for t in qy.TRADE_IDS if t not in NEW and t != 'grocery']
                self.assertTrue(min(peers) * .9 <= v <= max(peers) * 1.1, (trade, place, v, peers))
        self.assertTrue(old)


class Opening(unittest.TestCase):
    def test_opened_by_the_nearby_career(self):
        s = owner(trade='nail')
        self.assertEqual(qy.known_trades(s), ['cosmetics'])
        why = refused(self, s, 'jr_quay_open', 'locked', trade='cute_acc', place='xe', confirm=True)
        self.assertEqual(why, 'Cần làm 10 việc ở nghề Văn phòng phẩm (bạn đã làm 0/10). Vào nghề Văn phòng phẩm làm thêm để mở.')
        s, r = act(s, 'jr_quay_open', trade='cosmetics', place='xe', name='Son Xinh', confirm=True)
        self.assertIn('Son Xinh', r['message'])
        st = ST(s)
        self.assertEqual(st['trade'], 'cosmetics')
        self.assertEqual(s['journey']['history'][-1]['career'], 'nail')   # the wallet row names a real career
        validate_state(s)
        cands = qy.candidates(s, st)
        self.assertTrue(cands)                                              # the nail salon's people stand at it
        s, _ = act(s, 'jr_quay_hire', stall=st['id'], cand=cands[0]['id'], wage=cands[0]['ask'])
        days(s, 4)
        v = public_state(s)['journey']['quay']
        self.assertEqual(v['can'], ['cosmetics'])
        self.assertEqual(v['stalls'][0]['trade'], 'cosmetics')

    def test_every_new_trade_opens_runs_and_validates(self):
        for trade, career in NEW.items():
            with self.subTest(trade=trade):
                s = owner(wallet=30000, trade=career)
                self.assertIn(trade, qy.known_trades(s))
                s, _ = act(s, 'jr_quay_open', trade=trade, place='sap', confirm=True)
                st = ST(s)
                self.assertTrue(st['name'].startswith(qy.TRADES[trade]['name'][:10]))
                self.assertEqual(st['menu']['on'], [d[0] for d in qs.MENUS[trade]])
                for c in qy.candidates(s, st)[:2]:
                    s, _ = act(s, 'jr_quay_hire', stall=st['id'], cand=c['id'], wage=c['ask'])
                s, _ = act(s, 'jr_quay_start', stall=st['id'])   # the owner at the counter: a customer of this trade
                c = qs.customer(s, ST(s), ST(s)['run'], 0)
                self.assertTrue(set(c['items']) <= set(qs.DISH[trade]))
                days(s, 3)
                validate_state(s)

    def test_a_hired_shift_is_a_day_of_the_career(self):
        s = owner(trade='tra_da')
        q = qy.ensure(s)
        q['shift'] = dict(id='qj-0123abcd', career='tra_da', day=1, base=0, wage=20, value=60, who='Chủ', name='Cá viên Mây', until=10**10)
        validate_state(s)
        q['shift']['career'] = 'ca_vien'   # a trade id is not a career: never stored there
        with self.assertRaises(GameError):
            validate_state(s)


if __name__ == '__main__':
    unittest.main()
