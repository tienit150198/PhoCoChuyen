"""Người trong phố (0.9.16 street trades 2): the awkward people around the fruit stall, the rubbish
round and the drain calls, and the player's own moves against them. The hidden traits and every
decision are pure functions of the seed and the player's input; the twists validate against the
job; saves from before the twists (no `twist`, no debt book, no trouble) load and play on."""
import copy
import unittest

from tests.helpers import Journey
from tests.test_career_drain import Base as DrainBase
from tests.test_career_fruit import Base as FruitBase
from tests.test_career_garbage import Base as GarbageBase
from game.careers import PLUGINS, kit, till, street_folk as folk
from game.engine import GameError, migrate_state, validate_state

DR, FR, GB = PLUGINS.get('drain'), PLUGINS.get('fruit'), PLUGINS.get('garbage')


def ledger(c, ref):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ref]


def reviews(c, ref):
    return [x for x in c.get('feed', []) if x.get('source') == ref]


class Folk(unittest.TestCase):
    def test_traits_are_pure_and_leaned(self):
        a = folk.traits('drain-0003-02', 'warm')
        self.assertEqual(a, folk.traits('drain-0003-02', 'warm'))
        self.assertTrue(folk.validate_tr(a))
        warm = sum(folk.traits(f's{i}', 'warm')['rude'] for i in range(200))
        bossy = sum(folk.traits(f's{i}', 'bossy')['rude'] for i in range(200))
        self.assertLess(warm, bossy)

    def test_a_price_decision(self):
        tr = dict(stingy=50, savvy=50, mood=50, honest=50, rude=30, budget=50, proud=50)
        self.assertEqual(folk.judge_price(tr, 20, 15)['kind'], 'cheap')
        self.assertEqual(folk.judge_price(tr, 20, 20)['kind'], 'accept')
        self.assertEqual(folk.judge_price(tr, 20, 60)['kind'], 'walk')           # 300%: nobody pays that
        r = folk.judge_price(tr, 20, 30)
        self.assertEqual(r['kind'], 'counter')
        self.assertTrue(20 <= r['counter'] < 30)
        self.assertEqual(folk.judge_price(tr, 20, 30, tries=2)['kind'], 'walk')  # a third try and they leave

    def test_a_haggle_and_a_fee_and_a_chase(self):
        tr = dict(stingy=90, savvy=50, mood=10, honest=20, rude=30, budget=10, proud=80)
        self.assertEqual(folk.haggle(tr, 100, 80, 80)['kind'], 'glad')
        self.assertIn(folk.haggle(tr, 100, 80, 99)['kind'], ('counter', 'walk'))
        self.assertEqual(folk.fee(tr, 8, 8, 'strict', 0)['kind'], 'refuse')        # proud: rules said to their face
        self.assertEqual(folk.chase(tr, 10, 'soft', 10, 0, 1)['kind'], 'deny')      # dishonest: “trả rồi mà?”
        self.assertEqual(folk.chase(tr, 10, 'soft', 10, 1, 5)['kind'], 'gone')      # and then moves away
        self.assertEqual(folk.chase(tr, 10, 'family', 10, 0, 1)['kind'], 'angry')   # proud: never involve the family

    def test_the_debt_book_keeps_every_open_debt(self):
        book = [folk.debt_line(f'd{i}', 0, 'A', 't', 1, 5, 'x') for i in range(folk.DEBT_MAX)]
        book[0]['state'] = 'paid'
        book = folk.trim_debts(book + [folk.debt_line('new', 0, 'B', 't', 2, 5, 'x')])
        self.assertEqual(len(book), folk.DEBT_MAX)
        self.assertEqual(len(folk.open_debts(book)), folk.DEBT_MAX)
        folk.validate_debts(book, 1, kit.need)

    def test_trouble_plan_is_pure(self):
        for day in range(1, 40):
            self.assertEqual(folk.trouble_plan('fruit', day, 45), folk.trouble_plan('fruit', day, 45))
        self.assertEqual(folk.trouble_plan('fruit', 1, 100), [])
        self.assertTrue(any(folk.trouble_plan('garbage', d, 50) for d in range(2, 20)))


class Twists(unittest.TestCase):
    def test_each_career_has_every_twist_and_they_are_pure(self):
        for mod, kinds in ((DR, {'watch', 'extra', 'nocash'}), (FR, {'dear', 'tab', 'dash'}), (GB, {'sharp', 'pile', 'grump'})):
            if mod is None:
                continue
            seen = set()
            for day in range(1, 40):
                for slot in range(0, 10):
                    a, b = mod.make_task(day, slot, 1), mod.make_task(day, slot, 77)
                    ta, tb = mod.twist_of(a), mod.twist_of(b)
                    self.assertEqual(ta, tb)
                    if day == 1:
                        self.assertIsNone(ta, 'no twist on the first day')
                    if ta:
                        seen.add(ta['kind'])
            self.assertEqual(seen, kinds, mod.ID)

    def test_a_forged_twist_is_rejected(self):
        for mod, name in ((DR, 'drain'), (FR, 'fruit'), (GB, 'garbage')):
            if mod is None:
                continue
            day, slot = next((d, s) for d in range(2, 80) for s in range(1, 6) if mod.twist_of(mod.make_task(d, s, 1)))
            j = Journey(name, slot=slot, day=day)
            t = j.c['tasks'][0]
            self.assertEqual(t['twist'], mod.twist_of(t))
            bad = copy.deepcopy(j.state)
            bad['careers'][name]['tasks'][0]['twist'] = dict(t['twist'], n=(t['twist']['n'] + 1) % 4)
            with self.assertRaises(GameError, msg=name):
                validate_state(bad)
            bad = copy.deepcopy(j.state)
            del bad['careers'][name]['tasks'][0]['twist']
            with self.assertRaises(GameError, msg=name):   # state without its twist is a forgery
                validate_state(bad)

    def test_the_hidden_side_stays_hidden(self):
        for mod, name in ((DR, 'drain'), (FR, 'fruit'), (GB, 'garbage')):
            if mod is None:
                continue
            day, slot = next((d, s) for d in range(2, 80) for s in range(1, 6) if mod.twist_of(mod.make_task(d, s, 1)))
            j = Journey(name, slot=slot, day=day)
            v = mod.public_task(j.c['tasks'][0])
            self.assertNotIn('tw', v)
            self.assertFalse(v.get('twist'), name)
            self.assertNotIn('bid', v)
            self.assertNotIn('hg', v)


# ================================================================ drain
class Drain(DrainBase):
    def pick(self, twist=None, kind='call', where=None):
        for d in range(2, 300):
            for s in range(1, 6):
                t = DR.make_task(d, s, 1)
                tw = DR.twist_of(t)
                if t['kind'] == kind and (tw or {}).get('kind') == twist and (where is None or where(t)):
                    j = self.j = Journey('drain', slot=s, day=d)
                    self.out(j, ('pit_tong', 'lo_xo', 'may_lo_xo', 'may_phun', 'moc'))
                    return j, j.c['tasks'][0]['id']
        self.skipTest('no such job')

    def diagnose(self, j, tid):
        j.act('ask', task=tid)
        for how in ('hoi', 'nhin'):
            j.act('cg_check', task=tid, how=how)
        j.act('cg_diag', task=tid, cause=j.get(tid)['_cause'])

    def fix(self, j, tid):
        cause = DR.CAUSES[j.get(tid)['_cause']]
        if cause.get('part'):
            return j.act('cg_part', task=tid)
        tool = next(x for x in cause['fix'] if x in j.c['ext']['data']['bike'])
        return j.act('cg_work', task=tid, tool=tool)

    def wrap_up(self, j, tid):
        for a in ('cg_test', 'cg_clean', 'cg_advise'):
            j.act(a, task=tid)
        r = self.act_calm(j, 'cg_bill', task=tid)
        t = j.get(tid)
        if t['stage'] == 'pay':
            r = j.act('cg_pay', task=tid, change=till.greedy(till.due(t['cash'])))
        return r

    def fair(self, t):
        return DR.list_price(t['needs']['place'], t['_cause'], t['kind'])

    def test_own_fair_price_is_taken_and_paid(self):
        j, tid = self.pick(where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
        self.diagnose(j, tid)
        t = j.get(tid)
        fair = self.fair(t)
        r = j.act('cg_price', task=tid, price=fair)
        self.assertEqual((j.get(tid)['quote'], j.get(tid)['level']), (fair, 'own'))
        self.fix(j, tid)
        before = j.c['money']
        self.wrap_up(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertGreater(j.c['money'], before)
        self.assertFalse([x for x in j.get(tid).get('slips', []) if x['code'] in ('chop', 'overcharge')], r)

    def test_a_counter_offer_then_a_walkout(self):
        for d in range(2, 300):
            for s in range(1, 6):
                t = DR.make_task(d, s, 1)
                if t['kind'] != 'call' or DR.twist_of(t):
                    continue
                fair = self.fair(t)
                tr = DR._tr(t)
                price = next((p for p in range(fair, fair * 2) if folk.judge_price(tr, fair, p, 0)['kind'] == 'counter'), None)
                if price is None:
                    continue
                j = Journey('drain', slot=s, day=d)
                self.out(j)
                tid = t['id']
                self.diagnose(j, tid)
                j.act('cg_price', task=tid, price=price)
                bid = j.get(tid)['bid']
                self.assertEqual(bid['counter'], folk.judge_price(tr, fair, price, 0)['counter'])
                self.assertIsNone(j.get(tid)['quote'])
                j.act('cg_price', task=tid, price=price)
                j.act('cg_price', task=tid, price=price)       # the third time they are gone
                self.assertEqual(j.get(tid)['status'], 'completed')
                self.assertEqual(ledger(j.c, tid), [])
                return
        self.skipTest('no customer to counter')

    def test_a_rip_off_walks_and_is_noted(self):
        j, tid = self.pick()
        self.diagnose(j, tid)
        fair = self.fair(j.get(tid))
        j.act('cg_price', task=tid, price=fair * 3)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('greedy', {x['code'] for x in t['slips']})

    def test_chop_chop_has_consequences_and_a_comeback(self):
        found = None
        for d in range(2, 400):
            for s in range(1, 6):
                t = DR.make_task(d, s, 1)
                if t['kind'] != 'call' or DR.twist_of(t) or DR.CAUSES[t['_cause']].get('part'):
                    continue
                fair, tr = self.fair(t), DR._tr(t)
                price = fair * 17 // 10 + 1
                if folk.judge_price(tr, fair, price, 0)['kind'] == 'accept':
                    found = (d, s, t['id'], fair, price)
                    break
            if found:
                break
        if not found:
            self.skipTest('nobody pays 170%')
        d, s, tid, fair, price = found
        j = self.j = Journey('drain', slot=s, day=d)
        self.out(j)
        trust = j.c['incidents']['trust']
        self.diagnose(j, tid)
        j.act('cg_price', task=tid, price=price)
        self.fix(j, tid)
        self.wrap_up(j, tid)
        t = j.get(tid)
        self.assertIn('chop', {x['code'] for x in t['slips']})
        self.assertLessEqual(j.c['incidents']['trust'], trust - 3)
        self.assertTrue(reviews(j.c, tid), 'the street hears of it')
        self.assertGreaterEqual(self.d['stats']['chopped'], price - fair)
        cb = self.d['comebacks']
        if not cb:
            return      # this one never found out
        # The next day they come back with a neighbour: refund the difference.
        cb[0]['due'] = j.c['day']
        self.assertTrue(DR._comeback_open(j.state, j.c, self.d))
        validate_state(j.state)
        ev = self.d['trouble']['ev']
        self.assertEqual(ev['kind'], 'comeback')
        with self.assertRaises(GameError):
            j.act('cg_check', task=tid, how='hoi')             # nothing else until they are answered
        money = j.c['money']
        j.act('cg_trouble', choice='refund')
        self.assertEqual(j.c['money'], money - min(money, ev['facts']['extra']))
        self.assertIsNone(self.d['trouble']['ev'])
        self.assertEqual(self.d['comebacks'][0]['state'], 'done')

    def test_the_grumbling_homeowner(self):
        j, tid = self.pick('watch', where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
        self.diagnose(j, tid)
        j.act('cg_quote', task=tid, level='list')
        r = self.fix(j, tid)
        self.assertTrue(r.get('surprise'))
        t = j.get(tid)
        self.assertEqual(t['tw']['state'], 'on')
        self.assertTrue(DR.public_task(t)['twist']['line'])
        with self.assertRaises(GameError):
            self.fix(j, tid)
        tr = DR._tr(t)
        j.act('cg_watch', task=tid, choice='answer')
        how = folk.word(tr, 'answer')
        codes = {x['code'] for x in j.get(tid).get('slips', [])}
        self.assertEqual('argue' in codes, how == 'blowup')
        self.fix(j, tid)
        self.wrap_up(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_refusing_the_job(self):
        j, tid = self.pick('watch', where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
        self.diagnose(j, tid)
        j.act('cg_quote', task=tid, level='list')
        self.fix(j, tid)
        j.act('cg_watch', task=tid, choice='refuse')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(self.d['stats']['walked'], 1)
        self.assertEqual('walked' in {x['code'] for x in t.get('slips', [])}, DR._tr(t)['rude'] < 65)

    def test_tien_tay_extra_job_is_paid_when_agreed(self):
        j, tid = self.pick('extra', where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
        self.diagnose(j, tid)
        j.act('cg_quote', task=tid, level='list')
        self.fix(j, tid)
        for a in ('cg_test', 'cg_clean', 'cg_advise'):
            j.act(a, task=tid)
        r = j.act('cg_bill', task=tid)
        self.assertTrue(r.get('surprise'))
        tr = DR._tr(j.get(tid))
        price = DR.EXTRA_FAIR
        want = folk.judge_price(tr, DR.EXTRA_FAIR, price, 0)
        j.act('cg_extra', task=tid, choice='charge', price=price)
        st = j.get(tid)['tw']
        if want['kind'] == 'counter':
            self.assertEqual(st['counter'], want['counter'])
            j.act('cg_extra', task=tid, choice='charge', price=want['counter'])
            st = j.get(tid)['tw']
        self.assertEqual(st['state'], 'done')
        r = j.act('cg_bill', task=tid)
        t = j.get(tid)
        if t['stage'] == 'pay':
            self.assertEqual(t['cash']['price'], t['quote'] + st['price'])

    def test_no_cash_a_debt_and_chasing_it(self):
        j, tid = self.pick('nocash', where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
        self.diagnose(j, tid)
        j.act('cg_quote', task=tid, level='list')
        self.fix(j, tid)
        for a in ('cg_test', 'cg_clean', 'cg_advise'):
            j.act(a, task=tid)
        r = j.act('cg_bill', task=tid)
        self.assertTrue(r.get('surprise'))
        j.act('cg_nocash', task=tid, choice='trust')
        self.assertEqual(j.get(tid)['status'], 'completed')
        book = self.d['debts']
        if not book:
            return      # the customer was so unhappy they paid nothing and owe nothing
        x = book[0]
        self.assertEqual((x['state'], x['task']), ('open', tid))
        self.assertTrue(DR.public_data(j.c)['debts'])
        money = j.c['money']
        r = j.act('cg_chase', debt=x['id'], tone='soft')
        x = self.d['debts'][0]
        self.assertEqual(x['tries'], 1)
        self.assertEqual(j.c['money'] - money, x['paid'])
        if x['state'] == 'open':
            with self.assertRaises(GameError):
                j.act('cg_chase', debt=x['id'], tone='straight')   # once a day
            j.act('cg_chase', debt=x['id'], forgive=True)
            self.assertEqual(self.d['debts'][0]['state'], 'forgiven')

    def test_chasing_is_deterministic(self):
        outs = []
        for _ in range(2):
            j, tid = self.pick('nocash', where=lambda t: not DR.CAUSES[t['_cause']].get('part'))
            self.diagnose(j, tid)
            j.act('cg_quote', task=tid, level='list')
            self.fix(j, tid)
            for a in ('cg_test', 'cg_clean', 'cg_advise'):
                j.act(a, task=tid)
            j.act('cg_bill', task=tid)
            j.act('cg_nocash', task=tid, choice='deposit', amount=5)
            outs.append((j.c['money'], copy.deepcopy(j.c['ext']['data']['debts'])))
        self.assertEqual(outs[0], outs[1])

    def test_honest_debtors_pay_by_themselves(self):
        j = self.j
        honest = next(f'no-x{i}' for i in range(500) if folk.traits(f'no-x{i}', DR.PEOPLE[0][3])['honest'] >= 65)
        self.d['debts'] = [folk.debt_line(honest, 0, DR.PEOPLE[0][0], 'x', 0, 9, 'Thông bồn cầu')]
        money = j.c['money']
        notes = folk.auto_repay(j.state, j.c, 'drain', self.d['debts'], lambda i: DR.PEOPLE[i][3])
        self.assertEqual(len(notes), 1)
        self.assertEqual(j.c['money'], money + 9)
        self.assertEqual(self.d['debts'][0]['state'], 'paid')
        validate_state(j.state)


# ================================================================ fruit
class Fruit(FruitBase):
    def pick(self, want):
        for d in range(2, 300):
            for s in range(1, 8):
                t = FR.make_task(d, s, 1)
                if t['kind'] == 'buy' and want(t, FR.twist_of(t)):
                    j = Journey('fruit', slot=s, day=d)
                    j.c['ext']['data']['stall']['open'] = True
                    self.stock_up(j)
                    return j, t['id']
        self.skipTest('no such customer')

    def weighed(self, j, tid):
        self.fill(tid, j)
        return j.act('tc_weigh', task=tid)

    def test_name_your_own_price_in_a_haggle(self):
        j, tid = self.pick(lambda t, tw: t.get('_haggle') and not tw)
        self.weighed(j, tid)
        t = j.get(tid)
        self.assertEqual(t['stage'], 'haggle')
        tr, full, offer = FR._tr(t), t['price'], t['offer']
        price = next((p for p in range(offer + 1, full + 1) if folk.haggle(tr, full, offer, p, 0)['kind'] == 'counter'), None)
        if price is not None:
            j.act('tc_offer', task=tid, price=price)
            t = j.get(tid)
            self.assertEqual(t['offer'], folk.haggle(tr, full, offer, price, 0)['counter'])
            self.assertEqual(t['stage'], 'haggle')
        j.act('tc_offer', task=tid, price=j.get(tid)['offer'])
        t = j.get(tid)
        self.assertEqual((t['stage'], t['deal']), ('pay', 'own'))
        self.pay_exact(tid, j)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_ban_dat_a_customer_calls_it_a_rip_off(self):
        j, tid = self.pick(lambda t, tw: not t.get('_haggle') and (tw or {}).get('kind') == 'dear')
        self.weighed(j, tid)
        t = j.get(tid)
        self.assertEqual(t['stage'], 'haggle')
        self.assertEqual(FR._haggle_of(t)['pct'], t['twist']['pct'])
        self.assertLess(t['offer'], t['price'])
        j.act('tc_offer', task=tid, price=t['price'] * 4)       # four times the scale: never taken
        t = j.get(tid)
        self.assertTrue(t['status'] == 'completed' or t['stage'] == 'haggle')   # walked off, or bargains on
        self.assertEqual(ledger(j.c, tid), [])

    def test_ghi_no_a_tab_and_chasing_it(self):
        j, tid = self.pick(lambda t, tw: not t.get('_haggle') and (tw or {}).get('kind') == 'tab')
        self.weighed(j, tid)
        t = j.get(tid)
        self.assertEqual(t['stage'], 'credit')
        self.assertEqual(FR.public_task(t)['twist']['kind'], 'tab')
        j.act('tc_credit', task=tid, choice='tab')
        self.assertEqual(j.get(tid)['status'], 'completed')
        d = j.c['ext']['data']
        if not d['debts']:
            return
        x = d['debts'][0]
        self.assertEqual(x['state'], 'open')
        j.act('tc_chase', debt=x['id'], tone='straight', amount=1)
        x = j.c['ext']['data']['debts'][0]
        self.assertLessEqual(x['paid'], 1)
        self.assertEqual(x['tries'], 1)

    def test_refusing_credit(self):
        j, tid = self.pick(lambda t, tw: not t.get('_haggle') and (tw or {}).get('kind') == 'tab')
        self.weighed(j, tid)
        t = j.get(tid)
        tr = FR._tr(t)
        j.act('tc_credit', task=tid, choice='refuse')
        t = j.get(tid)
        if t['price'] * (tr['budget'] + 20) // 100 >= t['price']:
            self.assertEqual(t['stage'], 'pay')
        else:
            self.assertEqual(t['status'], 'completed')
            self.assertEqual(t['bag'], [])           # the fruit went back in the baskets

    def test_quyt_the_bag_walks_away(self):
        j, tid = self.pick(lambda t, tw: (tw or {}).get('kind') == 'dash' and FR._tr(t)['honest'] < 55)
        self.weighed(j, tid)
        t = j.get(tid)
        if t['stage'] == 'haggle':
            j.act('tc_deal', task=tid, deal=FR._haggle_of(t)['wants'])
        self.assertEqual(j.get(tid)['stage'], 'credit')
        j.act('tc_credit', task=tid, choice='trust')
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(j.c['ext']['data']['stats']['dashed'], 1)

    def open_trouble(self, j, kind):
        d = j.c['ext']['data']
        for day in range(2, 200):
            plan = folk.trouble_plan('fruit', day, 45)
            if not plan:
                continue
            want = 'thief' if folk.roll('tc-trouble', day, 0) < 65 else 'shame'
            if want != kind:
                continue
            j.c['day'], j.c['day_completed'] = day, plan[0]
            d['trouble'] = folk.trouble_initial()
            d['desk']['ev'] = None
            self.assertTrue(FR._trouble_tick(j.state, j.c, d))
            validate_state(j.state)
            return d['trouble']['ev']
        self.skipTest('no such trouble')

    def test_a_shoplifter_and_the_players_demand(self):
        j = Journey('fruit')
        self.setup_stall(j)
        self.stock_up(j)
        ev = self.open_trouble(j, 'thief')
        self.assertIn('value', ev['facts'])
        self.assertTrue(FR.public_data(j.c)['trouble']['ev'])
        with self.assertRaises(GameError):
            j.act('tc_decline', task=self.kind('buy', j)['id']) if any(t['kind'] == 'buy' for t in j.c['tasks']) else j.act('tc_scale_test')
        money = j.c['money']
        j.act('tc_trouble', choice='demand', amount=ev['facts']['value'])
        tb = j.c['ext']['data']['trouble']
        self.assertIsNone(tb['ev'])
        got = j.c['money'] - money
        self.assertIn(got, (0, ev['facts']['value']))
        self.assertEqual(tb['last']['choice'], 'demand')

    def test_a_clip_calling_the_stall_a_rip_off(self):
        j = Journey('fruit')
        self.setup_stall(j)
        ev = self.open_trouble(j, 'shame')
        trust = j.c['incidents']['trust']
        j.act('tc_trouble', choice='argue')
        self.assertEqual(j.c['incidents']['trust'], max(0, trust - 2))
        self.assertIs(j.c['ext']['data']['trouble']['last']['good'], False)
        self.assertTrue(reviews(j.c, ev['id']))


# ================================================================ garbage
class Garbage(GarbageBase):
    def pick(self, kind):
        return self.at(lambda t: (GB.twist_of(t) or {}).get('kind') == kind)

    def test_a_hidden_razor_pricks_through(self):
        j = self.pick('sharp')
        t = j.c['tasks'][0]
        tid, tw = t['id'], t['twist']
        j.c['ext']['data']['gear'] = []            # no gloves tonight
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        stop = next(i for i, st in enumerate(t['needs']['stops']) if any(b['id'] == tw['bag'] for b in st['bags']))
        for _ in range(stop):
            if j.get(tid)['late'] and not j.get(tid)['swept']:
                j.act('rac_sweep', task=tid)
            j.act('rac_next', task=tid)
        if j.get(tid)['late'] and not j.get(tid)['swept']:
            j.act('rac_sweep', task=tid)
        b = next(b for st in t['needs']['stops'] for b in st['bags'] if b['id'] == tw['bag'])
        r = j.act('rac_load', task=tid, bag=b['id'], bin=GB.bag_bin(b))
        self.assertTrue(r.get('surprise'))
        self.assertEqual(j.get(tid)['tw']['state'], 'on')
        with self.assertRaises(GameError):
            j.act('rac_next', task=tid)
        j.act('rac_hurt', task=tid, choice='clean')
        codes = {x['code'] for x in j.get(tid).get('slips', [])}
        self.assertEqual('no_clinic' in codes, tw['item'] == 'kim_tiem')

    def test_looking_first_finds_it(self):
        j = self.pick('sharp')
        t = j.c['tasks'][0]
        tid, tw = t['id'], t['twist']
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        stop = next(i for i, st in enumerate(t['needs']['stops']) if any(b['id'] == tw['bag'] for b in st['bags']))
        for _ in range(stop):
            if j.get(tid)['late'] and not j.get(tid)['swept']:
                j.act('rac_sweep', task=tid)
            j.act('rac_next', task=tid)
        r = j.act('rac_peek', task=tid, bag=tw['bag'])
        self.assertIn('⚠️', r['message'])
        seen = [b for st in GB.public_task(j.get(tid))['needs']['stops'] for b in st['bags'] if b['id'] == tw['bag']][0]
        self.assertIn(tw['item'], seen['items'])       # opened: the razor or needle shows
        j.act('rac_pull', task=tid, bag=tw['bag'], item=tw['item'])
        self.assertEqual(j.get(tid)['tw']['state'], 'safe')
        self.assertIn(tw['item'], j.c['ext']['data']['haz'])

    def test_a_dumped_heap_at_the_end(self):
        j = self.pick('pile')
        tid = j.c['tasks'][0]['id']
        with self.assertRaises(AssertionError):
            self.round_raw(j, tid)
        self.assertEqual(j.get(tid)['tw']['state'], 'on')
        money = j.c['money']
        j.act('rac_pile', task=tid, choice='truck')
        self.assertEqual(j.c['money'], money - min(10, money))
        j.act('rac_finish', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def round_raw(self, j, tid):
        """Every bag the careful way, and then the end of the lane (no answering)."""
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        t = j.get(tid)
        if t['late']:
            j.act('rac_sweep', task=tid)
        for si, st in enumerate(t['needs']['stops']):
            for b in st['bags']:
                if not GB._sorted_ok(b) or GB._hazards(b) or GB._glass(b):
                    j.act('rac_peek', task=tid, bag=b['id'])
                    for i in GB._hazards(b):
                        j.act('rac_pull', task=tid, bag=b['id'], item=i)
                    if GB._glass(b):
                        j.act('rac_wrap', task=tid, bag=b['id'])
                bin_ = GB.bag_bin(b)
                if j.c['ext']['data']['cart'][bin_]['n'] >= GB.CART[bin_]:
                    j.act('rac_dump')
                j.act('rac_load', task=tid, bag=b['id'], bin=bin_)
            if si < len(t['needs']['stops']) - 1:
                j.act('rac_next', task=tid)
        j.act('rac_finish', task=tid)
        assert j.get(tid)['status'] == 'completed'

    def test_the_resident_who_will_not_sort(self):
        j = self.pick('grump')
        t = j.c['tasks'][0]
        tid, stop = t['id'], t['twist']['stop']
        j.act('ask', task=tid)
        r = j.act('rac_go', task=tid)
        for _ in range(stop):
            if j.get(tid)['late'] and not j.get(tid)['swept']:
                j.act('rac_sweep', task=tid)
            r = j.act('rac_next', task=tid)
        self.assertEqual(j.get(tid)['tw']['state'], 'on')
        self.assertTrue(r.get('surprise'))
        j.act('rac_grump', task=tid, choice='refuse')
        bags = [b['id'] for b in t['needs']['stops'][stop]['bags']]
        self.assertEqual(sorted(j.get(tid)['refused']), sorted(bags))
        self.assertTrue(all(x.get('refused') for x in GB.public_task(j.get(tid))['needs']['stops'][stop]['bags']))

    def test_refusing_a_bag_of_your_own_accord(self):
        j = self.at(lambda t: t['kind'] == 'route' and not GB.twist_of(t) and any(not GB._sorted_ok(b) for b in t['needs']['stops'][0]['bags']))
        t = j.c['tasks'][0]
        tid = t['id']
        b = next(b for b in t['needs']['stops'][0]['bags'] if not GB._sorted_ok(b))
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        if j.get(tid)['late']:
            j.act('rac_sweep', task=tid)
        with self.assertRaises(GameError):
            j.act('rac_refuse', task=tid, bag=b['id'])       # look first
        j.act('rac_peek', task=tid, bag=b['id'])
        j.act('rac_refuse', task=tid, bag=b['id'])
        self.assertIn(b['id'], j.get(tid)['refused'])
        for again in (lambda: j.act('rac_refuse', task=tid, bag=b['id']), lambda: j.act('rac_load', task=tid, bag=b['id'], bin=GB.bag_bin(b))):
            with self.assertRaises(GameError):
                again()

    def test_the_fee_book(self):
        j = Journey('garbage', slot=1, day=9)
        self.on_shift(j)
        d = j.c['ext']['data']
        d['fees'] = GB._fee_book(9)
        validate_state(j.state)
        self.assertEqual(len(d['fees']['rows']), GB.FEE_ROWS)
        self.assertNotIn('excuse', {k for r in GB.public_data(j.c)['fees']['rows'] for k, v in r.items() if v is not None})
        results = {}
        for row in list(d['fees']['rows']):
            money = j.c['money']
            r = j.act('rac_fee', row=row['id'], tone='soft', amount=row['due'])
            x = next(y for y in j.c['ext']['data']['fees']['rows'] if y['id'] == row['id'])
            results[x['id']] = (r['message'], x['state'], j.c['money'] - money)
            want = folk.fee(folk.traits(row['id']), row['due'], row['due'], 'soft', 0)
            self.assertEqual(x['paid'], want.get('paid', 0))
            if want['kind'] == 'haggle':
                self.assertEqual(x['counter'], want['counter'])
                j.act('rac_fee', row=row['id'], tone='soft', amount=want['counter'])     # take their offer on the spot
                x = next(y for y in j.c['ext']['data']['fees']['rows'] if y['id'] == row['id'])
                self.assertEqual((x['state'], x['paid']), ('paid', want['counter']))
            elif x['state'] == 'open':
                with self.assertRaises(GameError):
                    j.act('rac_fee', row=row['id'], tone='soft', amount=1)             # once a day at each door
                j.act('rac_fee', row=row['id'], waive=True)
        self.assertTrue(all(x['state'] != 'open' for x in j.c['ext']['data']['fees']['rows']))
        # The same doors, the same answers.
        j2 = Journey('garbage', slot=1, day=9)
        self.on_shift(j2)
        j2.c['ext']['data']['fees'] = GB._fee_book(9)
        for row in j2.c['ext']['data']['fees']['rows']:
            r = j2.act('rac_fee', row=row['id'], tone='soft', amount=row['due'])
            self.assertEqual(r['message'], results[row['id']][0])

    def open_trouble(self, j, kind):
        d = j.c['ext']['data']
        for day in range(2, 200):
            plan = folk.trouble_plan('garbage', day, 50)
            if plan and ('vandal' if folk.roll('rac-trouble', day, 0) < 70 else 'point') == kind:
                j.c['day'], j.c['day_completed'] = day, plan[0]
                d['trouble'] = folk.trouble_initial()
                d['desk']['ev'] = None
                self.assertTrue(GB._trouble_tick(j.state, j.c, d))
                validate_state(j.state)
                return d['trouble']['ev']
        self.skipTest('no such trouble')

    def test_night_vandals(self):
        j = Journey('garbage', slot=1, day=3)
        self.on_shift(j)
        ev = self.open_trouble(j, 'vandal')
        self.assertTrue(GB.public_data(j.c)['trouble']['text'])
        money = j.c['money']
        j.act('rac_trouble', choice='police')
        loss = GB.VANDALS[ev['facts']['v']]['loss']
        self.assertEqual(j.c['money'], money + (loss if GB.VANDALS[ev['facts']['v']]['v'] != 'fire' else 0))
        self.assertIsNone(j.c['ext']['data']['trouble']['ev'])

    def test_an_overflowing_point(self):
        j = Journey('garbage', slot=1, day=3)
        self.on_shift(j)
        ev = self.open_trouble(j, 'point')
        j.act('rac_trouble', choice='leave')
        self.assertIs(j.c['ext']['data']['trouble']['last']['good'], False)
        self.assertTrue(reviews(j.c, ev['id']))


# ================================================================ live saves (0.9.15 shape) carry on
class LiveSaves(unittest.TestCase):
    """A save written by 0.9.15 mid-day: tasks without twists, data without the debt book, the
    trouble, the fee book or the comebacks. It must load, validate, and play on."""

    def old_shape(self, name, day, slot):
        j = Journey(name, slot=slot, day=day)
        c = j.c
        for t in c['tasks']:
            for k in ('twist', 'tw', 'bid', 'hg', 'refused'):
                t.pop(k, None)
        d = c['ext']['data']
        for k in ('debts', 'trouble', 'comebacks', 'fees'):
            d.pop(k, None)
        for k in ('chopped', 'refunds', 'walked', 'freebies', 'stolen', 'dashed', 'caught', 'fees'):
            d['stats'].pop(k, None)
        d['today'].pop('fees', None)
        return j

    def test_old_saves_load_and_play(self):
        for name, mod in (('drain', DR), ('fruit', FR), ('garbage', GB)):
            if mod is None:
                continue
            for day in (2, 5, 11):
                for slot in (1, 2, 3):
                    j = self.old_shape(name, day, slot)
                    tid = j.c['tasks'][0]['id']
                    s = migrate_state(copy.deepcopy(j.state))
                    validate_state(s)
                    self.assertNotIn('twist', s['careers'][name]['tasks'][0], 'an old job never grows a twist')
                    j.state = s
                    j.act('ask', task=tid)
                    d = j.c['ext']['data']
                    self.assertIsInstance(d.get('trouble'), dict)
                    self.assertIsInstance(d.get('debts', d.get('fees')), (list, dict))
