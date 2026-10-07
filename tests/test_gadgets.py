"""📱 Cửa hàng điện thoại (game/gadgets.py), feedback F#205: the catalogue and its prices, buying outright (wallet,
then the bank account, never below 0, no xu created), the old phone taken in once, the phone in use and its perks,
selling back, the card other players see, net worth, and saves (old ones without the block, blocks a newer build
wrote)."""
import copy
import unittest

from game import gadgets as gd
from game import garage as gr
from game import journey as jr
from game import social, wealth, wealth_pricing
from game.engine import GameError, migrate_state, new_state, public_state, validate_state
from tests.test_bank import B, act, opened, story


def G(s):
    return s['journey']['gadgets']


def buy(s, iid, **kw):
    return act(s, 'jr_gadget_buy', id=iid, confirm=True, **kw)


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def money(s):
    """Every xu the save holds in hand: the wallet and the bank account."""
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


class Catalogue(unittest.TestCase):
    def test_tiers_prices_and_brands(self):
        phones = [gd.ITEMS[i] for i in gd.PHONES]
        self.assertEqual([p['tier'] for p in phones], [1, 2, 3, 4, 5])        # cheap → gold, one each
        self.assertEqual([p['price'] for p in phones], sorted(p['price'] for p in phones))
        self.assertLessEqual(phones[0]['price'] - gd.TRADE_IN, jr.START_WALLET + 2 * 50)   # day-1 reachable (old phone in): ~two days of pay
        self.assertGreaterEqual(phones[-1]['price'], 20000)                    # the gold edition is a rich player's toy
        self.assertLess(phones[-1]['price'], max(v['price'] for v in gr.VEHICLES.values()))
        for gid in gd.GROUP_IDS:
            prices = [it['price'] for it in gd.ITEMS.values() if it['group'] == gid]
            self.assertEqual(prices, sorted(prices), gid)                      # cheapest first within a tab
        gear = [it for it in gd.ITEMS.values() if it['group'] == 'gear']
        self.assertEqual({it['emoji'] for it in gear}, {'🎧', '⌚', '💻', '🎮', '📷'})
        for iid, it in gd.ITEMS.items():
            self.assertRegex(iid, gd.ID_RE.pattern)
            self.assertRegex(it['color'], r'^#[0-9a-f]{6}$')
            self.assertGreater(it['price'], gd.sell_price(it['price']))       # selling back always loses
            self.assertTrue(.6 <= gd.sell_price(it['price']) / it['price'] <= .7, iid)
            self.assertEqual(it['tier'] > 0, it['group'] == 'phone')
            for real in ('iphone', 'samsung', 'galaxy', 'xiaomi', 'oppo', 'vivo', 'apple', 'airpods', 'playstation',
                         'nintendo', 'xbox', 'canon', 'nikon', 'sony', 'huawei', 'nokia', 'ipad'):
                self.assertNotIn(real, (it['name'] + it['desc'] + it['brand']).lower(), iid)   # fictional brands only

    def test_perks_are_light_and_cumulative(self):
        self.assertEqual(gd.perks_of('may_lite'), ['recent'])
        self.assertEqual(gd.perks_of('kim_long'), list(gd.PERK_IDS))
        self.assertEqual(gd.perks_of('tai_nghe'), [])
        self.assertEqual(gd.perks_of(None), [])
        cat = gd.catalogue()
        self.assertEqual([x['id'] for x in cat['items']], list(gd.ORDER))
        self.assertEqual(jr.content()['gadgets'], cat)
        self.assertNotIn('upkeep', str(cat))   # no daily or monthly fee


class Buying(unittest.TestCase):
    def test_buy_with_cash_through_the_wallet_ledger(self):
        s = story(500)
        before = money(s)
        s, r = buy(s, 'may_lite', trade=False)
        j = s['journey']
        self.assertEqual(j['wallet'], 335)                                    # 💹 07/10: 150 -> 165 xu
        self.assertEqual(G(s)['own'], {'may_lite': dict(d=j['life_day'], p=165)})
        self.assertEqual(G(s)['hand'], 'may_lite')                           # the first phone is the one in use
        self.assertEqual(j['history'][-1]['kind'], 'life')                    # an existing kind: older builds validate
        self.assertEqual(j['history'][-1]['amount'], -165)
        self.assertEqual(before - money(s), 165)
        self.assertIn('165 xu tiền mặt', r['message'])
        validate_state(s)

    def test_trade_in_the_old_phone_once(self):
        s = story(500)
        self.assertEqual(public_state(s)['journey']['gadgets']['old'], 0)
        refused(self, s, 'jr_gadget_buy', id='may_lite', confirm=True, trade='yes')
        s, r = buy(s, 'may_lite')                                             # the first phone takes the old one in
        self.assertEqual(s['journey']['wallet'], 500 - 145)
        self.assertEqual(G(s)['own']['may_lite']['p'], 145)                   # what was paid: the base of selling back
        self.assertEqual(G(s)['old'], 1)
        self.assertIn('Anh Khoa', r['message'])
        s['journey']['wallet'] += 600
        s, _ = buy(s, 'sao_mai_s', trade=True)                                # the old phone is gone: full price
        self.assertEqual(s['journey']['wallet'], 295)
        self.assertEqual(G(s)['own']['sao_mai_s']['p'], 660)
        s3, _ = buy(story(500), 'may_lite', trade=False)                      # kept as a keepsake: full price
        self.assertEqual((G(s3)['old'], G(s3)['own']['may_lite']['p']), (0, 165))
        s2 = story(500)
        s2, _ = buy(s2, 'tai_nghe', trade=True)                               # gear never takes the phone in
        self.assertEqual(G(s2)['old'], 0)
        self.assertEqual(G(s2)['own']['tai_nghe']['p'], 130)

    def test_trade_in_makes_a_short_wallet_enough(self):
        s = story(160)
        why = refused(self, s, 'jr_gadget_buy', 'not_enough', id='may_lite', confirm=True, trade=False)
        self.assertIn('Còn thiếu 5 xu', why)
        s, _ = buy(s, 'may_lite')
        self.assertEqual(s['journey']['wallet'], 15)

    def test_not_enough_debt_and_never_the_card(self):
        s = story(100)
        why = refused(self, s, 'jr_gadget_buy', 'not_enough', id='sao_mai_s', confirm=True)
        self.assertIn('Còn thiếu 540 xu', why)                               # the old phone's 20 xu counted
        self.assertEqual(public_state(s)['journey']['gadgets']['why']['sao_mai_s'], 'Còn thiếu 540 xu.')
        why = public_state(s)['journey']['gadgets']['why']
        self.assertEqual((why['may_lite'], why['tai_nghe']), ('Còn thiếu 45 xu.', 'Còn thiếu 30 xu.'))
        self.assertNotIn('may_lite', public_state(story(145))['journey']['gadgets']['why'])   # 165 − 20 for the old phone
        s = story(-5)
        self.assertIn('Ví đang nợ 5 xu', refused(self, s, 'jr_gadget_buy', id='tai_nghe', confirm=True))

    def test_wallet_then_account_never_below_zero(self):
        s = opened(wallet=2640, deposit=2000)          # 640 cash, 2 000 in the account
        s, r = buy(s, 'may_pro', trade=False)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(B(s)['balance'], 0)
        self.assertIn('640 xu tiền mặt và 2.000 xu từ tài khoản', r['message'])
        self.assertEqual(B(s)['log'][-1]['amt'], -2000)
        refused(self, s, 'jr_gadget_buy', 'not_enough', id='tai_nghe', confirm=True)
        validate_state(s)

    def test_confirm_duplicate_and_bad_input(self):
        s = story(500)
        refused(self, s, 'jr_gadget_buy', id='may_lite')                       # no confirm
        refused(self, s, 'jr_gadget_buy', id='dien_thoai_vu_tru', confirm=True)
        refused(self, s, 'jr_gadget_buy', id='may_lite', confirm=True, price=1)
        refused(self, s, 'jr_gadget_frobnicate', id='may_lite')
        s, _ = buy(s, 'may_lite', trade=False)
        s, r = buy(s, 'may_lite')                                              # a second tap pays nothing
        self.assertTrue(r.get('duplicate'))
        self.assertEqual(s['journey']['wallet'], 335)

    def test_free_play_has_no_shop(self):
        s = new_state()
        self.assertFalse(s['journey']['story'])
        refused(self, s, 'jr_gadget_buy', id='may_lite', confirm=True)


class Owning(unittest.TestCase):
    def setUp(self):
        s = story(40000)
        s, _ = buy(s, 'sao_mai_s', trade=False)
        s, _ = buy(s, 'may_lite')                     # a cheaper phone does not take the hand
        s, _ = buy(s, 'dong_ho')
        s, _ = buy(s, 'may_anh')
        self.s = s

    def test_hand_perks_and_views(self):
        s = self.s
        self.assertEqual(G(s)['hand'], 'sao_mai_s')
        pub = public_state(s)['journey']['gadgets']
        self.assertEqual(pub['hand']['id'], 'sao_mai_s')
        self.assertEqual(pub['perks'], ['recent', 'selfie'])
        self.assertEqual([x['id'] for x in pub['own']], ['may_lite', 'sao_mai_s', 'dong_ho', 'may_anh'])
        card = social.snapshot(s)[0]['phone']
        self.assertEqual(card, dict(emoji='📱', name='Sao Mai S12', color=gd.ITEMS['sao_mai_s']['color'], tier=2,
                                    gear=['📷', '⌚']))
        s, _ = act(s, 'jr_gadget_use', id='may_lite')
        self.assertEqual(public_state(s)['journey']['gadgets']['perks'], ['recent'])
        refused(self, s, 'jr_gadget_use', id='may_pro')                      # not yours
        refused(self, s, 'jr_gadget_use', id='dong_ho')                      # a watch is not a phone
        s, _ = act(s, 'jr_gadget_use', id=None)
        self.assertIsNone(G(s)['hand'])
        self.assertEqual(social.snapshot(s)[0]['phone'], dict(gear=['📷', '⌚']))
        validate_state(s)

    def test_buying_a_better_phone_takes_the_hand(self):
        s, _ = buy(self.s, 'kim_long')
        self.assertEqual(G(s)['own']['kim_long']['p'], 28800)                 # the old phone went with the first one
        self.assertEqual(G(s)['hand'], 'kim_long')
        self.assertEqual(public_state(s)['journey']['gadgets']['perks'], list(gd.PERK_IDS))

    def test_sell_back_pays_65_percent_into_the_wallet(self):
        s = self.s
        w = s['journey']['wallet']
        s, r = act(s, 'jr_gadget_sell', id='sao_mai_s', confirm=True)
        self.assertEqual(s['journey']['wallet'], w + 425)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'life')
        self.assertEqual(G(s)['hand'], 'may_lite')                           # the best phone left
        self.assertIn('425 xu', r['message'])
        refused(self, s, 'jr_gadget_sell', id='sao_mai_s', confirm=True)      # gone
        refused(self, s, 'jr_gadget_sell', id='may_lite')                     # no confirm
        s, _ = act(s, 'jr_gadget_sell', id='may_lite', confirm=True)
        self.assertIsNone(G(s)['hand'])
        self.assertEqual(G(s)['stats'], dict(bought=4, sold=2))
        validate_state(s)

    def test_no_round_trip_makes_money(self):
        s = story(40000)
        start = money(s)
        for iid in gd.ORDER:
            s, _ = buy(s, iid, trade=True)
            s, _ = act(s, 'jr_gadget_sell', id=iid, confirm=True)
            self.assertLess(money(s), start)
        self.assertEqual(G(s)['own'], {})

    def test_net_worth_counts_gadgets_at_the_buy_back_price(self):
        s = story(1000)
        net0, assets0, _ = wealth.worth(s)
        s, _ = buy(s, 'sao_mai_s', trade=False)
        net1, assets1, _ = wealth.worth(s)
        self.assertEqual(net0 - net1, 660 - gd.sell_price(660))
        self.assertEqual(wealth_pricing.total(s), 340 + gd.sell_price(660))


class Saves(unittest.TestCase):
    def test_old_saves_have_no_block_and_stay_so(self):
        s = story(500)
        self.assertNotIn('gadgets', s['journey'])
        s2 = migrate_state(copy.deepcopy(s))
        self.assertNotIn('gadgets', s2['journey'])
        validate_state(s2)
        self.assertIsNone(public_state(s2)['journey']['gadgets']['hand'])

    def test_bad_blocks_are_refused(self):
        s, _ = buy(story(500), 'may_lite')
        for bad in ({'own': {'may_lite': {'d': 1}}}, {'hand': 'sao_mai_s'}, {'old': True}, {'old': 2},
                    {'stats': {'x': 1}}, {'extra': 1}, {'v': 2}):
            t = copy.deepcopy(s)
            G(t).update(bad)
            with self.assertRaises(GameError, msg=bad):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['gadgets'] = []
        with self.assertRaises(GameError):
            validate_state(t)

    def test_a_newer_builds_block_is_kept_by_upgrade(self):
        s, _ = buy(story(500), 'may_lite')
        t = copy.deepcopy(s)
        G(t)['own']['dien_thoai_2027'] = dict(d=3, p=999)   # an id this build does not know: kept, not shown
        G(t)['extra'] = {'z': 1}                            # a field a newer build added: dropped by upgrade
        t = migrate_state(t)
        validate_state(t)
        self.assertIn('dien_thoai_2027', G(t)['own'])
        self.assertNotIn('extra', G(t))
        self.assertEqual([x['id'] for x in public_state(t)['journey']['gadgets']['own']], ['may_lite'])


if __name__ == '__main__':
    unittest.main()
