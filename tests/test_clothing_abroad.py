"""👗 Tiệm Áo Chỉ Mây ở nước ngoài (feedback #306, game/clothing_abroad.py): the clothes shop in 🌏 Làm việc ở nước
ngoài, the city's sizes and habits on the shop's own tasks, the commission and the way home."""
import copy
import json
import unittest

from game import abroad as ab
from game import clothing_abroad as CA
from game import consequences as cq
from game.careers import kit
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_career_clothing import A, bill_and_pay, roundtrip
from tests.test_promotion import day, story
from tests.helpers import Journey


def jr(j, name, **p):
    j.state, r = apply_action(j.state, None, name, p)
    return r


def shopkeeper(served=CA.SERVED_NEED):
    j = Journey('clothing')
    story(j)
    if 'clothing' not in j.state['journey']['unlocked']:
        j.state['journey']['unlocked'].append('clothing')
    j.c['metrics']['served'] = served
    day(j)
    return j


def away(to='nhat_ban'):
    j = shopkeeper()
    jr(j, 'jr_abroad_work', to=to, career='clothing', confirm=True)
    j.act('start_day')
    return j


def counter(j, kind=None):
    """A dressed counter customer of today (fit or outfit), heard."""
    kinds = (kind,) if kind else CA.ASK_KINDS
    for t in j.c['tasks']:
        if t.get('abroad') and t['kind'] in kinds and t['status'] not in ('completed', 'cancelled'):
            if not t['known']:
                j.act('ask', task=t['id'])
            return j.get(t['id'])
    return None


@unittest.skipIf(A is None, 'clothing filtered out')
class Contract(unittest.TestCase):
    def test_the_shop_is_offered_once_enough_customers_are_served(self):
        j = shopkeeper(served=3)
        v = public_state(j.state)['journey']['abroad']
        self.assertEqual(v['shop']['career'], 'clothing')
        self.assertIn('12', v['shop']['why'])
        with self.assertRaises(GameError):
            jr(j, 'jr_abroad_work', to='han_quoc', career='clothing', confirm=True)
        j.c['metrics']['served'] = CA.SERVED_NEED
        self.assertIsNone(public_state(j.state)['journey']['abroad']['shop']['why'])
        self.assertEqual(set(ab.catalogue()['shop']), set(CA.SHOPS))
        w0 = j.state['journey']['wallet']
        r = jr(j, 'jr_abroad_work', to='han_quoc', career='clothing', confirm=True)
        self.assertIn('Seoul', r['message'])
        self.assertEqual(j.state['journey']['wallet'], w0)   # Chị Vy pays the ticket
        w = j.state['journey']['abroad']['work']
        self.assertEqual((w['career'], w['emp'], w['hd'], w['fee'], w['need']), ('clothing', None, 0, 0, CA.SHOPS['han_quoc']['days']))
        self.assertTrue(public_state(j.state)['journey']['abroad']['work']['shop'])
        validate_state(j.state)

    def test_other_workplaces_stay_shut_and_the_last_day_brings_you_home(self):
        j = away('han_quoc')
        with self.assertRaises(GameError):
            ab.gate_start(j.state, 'pho')
        sh = CA.SHOPS['han_quoc']
        lines = []
        for n in range(sh['days']):
            fund = j.c['money']
            A._data(j.c)['day_sales'] = 1000 if n == 0 else 0
            r = day(j)
            lines += r['summary']['career']['lines']
            if n == 0:
                self.assertEqual(j.c['money'] - fund, 1000 * sh['pct'] // 100)
        self.assertTrue(any('Hoa hồng' in x for x in lines))
        self.assertTrue(any(x.startswith('🇰🇷 Ngày 1/') for x in lines))
        self.assertTrue(any('Hết hợp đồng' in x for x in lines))
        b = j.state['journey']['abroad']
        self.assertIsNone(b['work'])
        self.assertEqual(b['done']['han_quoc'], 1)
        validate_state(j.state)

    def test_a_day_without_a_customer_does_not_count(self):
        j = away()
        j.act('end_day', carry_event=True)
        self.assertEqual(j.state['journey']['abroad']['work']['n'], 0)

    def test_coming_home_early(self):
        j = away()
        j.act('end_day', carry_event=True)
        r = jr(j, 'jr_abroad_home', confirm=True)
        self.assertIn('về nước sớm', r['message'])
        self.assertIsNone(ab.contract(j.state))


@unittest.skipIf(A is None, 'clothing filtered out')
class Customers(unittest.TestCase):
    def setUp(self):
        self.chance = CA.ASK_CHANCE
        CA.ASK_CHANCE = 1.0

    def tearDown(self):
        CA.ASK_CHANCE = self.chance

    def test_tasks_are_dressed_and_generation_is_untouched(self):
        j = away('phap')
        dressed = [t for t in j.c['tasks'] if t.get('abroad')]
        self.assertTrue(dressed)
        for t in j.c['tasks']:
            original = A.make_task(t['day'], int(t['id'].rsplit('-', 1)[1]), t['created_turn'])
            self.assertEqual(t['needs'], original['needs'])
            self.assertNotIn('wish', t) if t.get('abroad') else None
            if t['kind'] in CA.KINDS:
                self.assertEqual(t['abroad']['to'], 'phap')
        v = public_state(j.state)['careers']['clothing']
        pv = next(x for x in v['tasks'] if x.get('abroad'))
        self.assertIn(pv['abroad']['who'], CA.SHOPS['phap']['names'])
        self.assertTrue(pv['opening'].startswith('Bonjour'))
        self.assertEqual(pv['abroad']['chart'], [])   # the chart comes with the order, once heard
        t = counter(j, 'fit')
        pv = A.public_task(t)
        self.assertEqual([r['label'] for r in pv['abroad']['chart']][:1], ['👚 Nữ' if A._npc_index(t) not in CA.MALE else '👔 Nam'])
        roundtrip(j)

    def test_local_sizes_never_name_the_label_unless_it_is_the_label(self):
        rng = kit.rng('t')
        self.assertEqual(CA.local_size('han_quoc', 'tee', 'M', 1, rng)[1], '66')
        self.assertEqual(CA.local_size('han_quoc', 'tee', 'M', 2, rng)[1], '95')
        self.assertEqual(CA.local_size('nhat_ban', 'shirt', 'L', 2, rng)[1], 'LL')
        self.assertEqual(CA.local_size('nhat_ban', 'kids', '5T', 1, rng)[1], 'bé cao 110 cm')
        self.assertIn('tuổi Hàn', CA.local_size('han_quoc', 'kids', '5T', 1, rng)[0])
        self.assertEqual(CA.local_size('phap', 'sneaker', '38', 1, rng)[2], '38')
        self.assertIsNone(CA.local_size('uc', 'jeans', '30', 1, rng)[2])
        self.assertEqual(CA.local_size('uc', 'jeans', '30', 1, rng)[1], 'quần AU 12')
        for to in CA.SHOPS:
            for item in A.ITEM:
                for size in A.SIZES[item]:
                    said, ask, told = CA.local_size(to, item, size, 1, kit.rng(to, item, size))
                    self.assertTrue(said and ask)
                    self.assertIn(told, (None, size))
            for row in CA.chart(to):
                self.assertTrue(row['cells'])

    def test_fit_in_osaka_local_sizes_habit_and_bill(self):
        j = away('nhat_ban')
        t = counter(j, 'fit')
        self.assertIsNotNone(t)
        tid = t['id']
        q = CA.ask_of(t)
        self.assertIsNotNone(q)
        pv = A.public_task(t)
        for ln, raw in zip(pv['needs']['lines'], t['needs']['lines']):
            self.assertNotIn('_size', ln)
            if raw['item'] in ('tee', 'shirt') and raw['_size'] != 'F':
                self.assertNotIn(f'size {raw["_size"]}', ln['say'])
        self.assertEqual(pv['abroad']['ask']['id'], q['id'])
        self.assertNotIn('grade', json.dumps(pv['abroad']['ask']))   # the grades stay on the server
        self.assertIn(q['say'], A.known_request(j.c, t))
        for ln in A._wanted_lines(t):
            j.act('ao_pick', task=tid, item=ln['item'], size=ln['_size'], colour=ln['colour'])
        with self.assertRaises(GameError):   # the habit is answered before the bill
            j.act('ao_bill', task=tid)
        good = next(o for o in q['opts'] if o['grade'] == 'good')
        r = j.act('ao_local', task=tid, answer=good['id'])
        self.assertEqual(r['local'], 'good')
        with self.assertRaises(GameError):
            j.act('ao_local', task=tid, answer=good['id'])
        bill_and_pay(j, tid)
        done = j.get(tid)
        self.assertEqual(done['status'], 'completed')
        self.assertNotIn('local_miss', [x['code'] for x in cq.slips(done)])
        self.assertEqual(next(x for x in A.feedback(j.c, done)['criteria'] if x['key'] == 'local')['score'], 5)
        roundtrip(j)

    def test_a_bad_answer_is_a_slip_and_mood_depends_on_the_hidden_temper(self):
        j = away('uc')
        t = counter(j)
        q = CA.ask_of(t)
        bad = next(o for o in q['opts'] if o['grade'] == 'bad')
        j.act('ao_local', task=t['id'], answer=bad['id'])
        t = j.get(t['id'])
        self.assertEqual(t['abroad']['ok'], 'bad')
        self.assertIn('local_miss', [x['code'] for x in cq.slips(t)])
        self.assertGreaterEqual(t['mistakes'], 1)
        seen = set()
        for i in range(40):
            tt = dict(id=f'clothing-{100 + i:04d}-01', kind='fit', stage='pick', patience=90, mistakes=0, abroad=dict(to='uc', ask='change', ans=None, ok=None))
            seen.add(CA.answer(j.state, j.c, tt, dict(answer='no'))['local'])
        self.assertEqual(seen, {'ok', 'bad'})

    def test_validation_refuses_a_forged_answer(self):
        j = away('han_quoc')
        t = counter(j)
        roundtrip(j)
        for bad in (dict(t['abroad'], to='mars'), dict(t['abroad'], ans='zzz', ok='good'), dict(t['abroad'], ok='good'),
                    dict(t['abroad'], extra=1)):
            s = copy.deepcopy(j.state)
            next(x for x in s['careers']['clothing']['tasks'] if x['id'] == t['id'])['abroad'] = bad
            with self.assertRaises(GameError):
                validate_state(s)

    def test_waiting_customers_follow_the_shop_and_home_tasks_are_plain(self):
        j = shopkeeper()
        j.act('start_day')
        self.assertFalse(any(t.get('abroad') for t in j.c['tasks']))
        A.on_task(j.state, j.c, dict(j.c['tasks'][0]))
        j.act('end_day', carry_event=True)
        jr(j, 'jr_abroad_work', to='nhat_ban', career='clothing', confirm=True)
        j.act('start_day')
        waiting = [t for t in j.c['tasks'] if not t['known'] and t['status'] == 'new' and t['kind'] in CA.KINDS and 'wish' not in t]
        self.assertTrue(all(t.get('abroad') for t in waiting))
        j.act('end_day', carry_event=True)
        jr(j, 'jr_abroad_home', confirm=True)
        j.state['journey']['life_day'] += ab.REST
        j.act('start_day')
        self.assertFalse(any(t.get('abroad') for t in j.c['tasks'] if not t['known'] and t['status'] == 'new'))

    def test_names_in_messages_are_the_citys(self):
        j = away('phap')
        t = counter(j)
        names = CA.SHOPS['phap']['names']
        self.assertIn(A._who(t), names)
        self.assertNotIn(A.PEOPLE[A._npc_index(t)][0], A._who(t))

    def test_online_order_keeps_its_lines_and_ships_to_the_city(self):
        j = away('uc')
        t = next((x for x in j.c['tasks'] if x['kind'] == 'online'), None)
        if t is None:   # none walked in today: any online order, dressed for Melbourne
            t = next(A.make_task(d, s, 1) for d in range(2, 40) for s in range(12) if A.make_task(d, s, 1)['kind'] == 'online')
            CA.dress(j.state, t, 'uc')
        line = A.known_request(j.c, t)
        self.assertTrue(line.startswith('Đơn: '))
        self.assertIn('Melbourne', line)
        v = A.public_task(dict(t, known=True))
        self.assertIn(v['needs']['address'], CA.SHOPS['uc']['address'])


@unittest.skipIf(A is None, 'clothing filtered out')
class Rollback(unittest.TestCase):
    def test_an_older_build_ends_the_contract_without_money(self):
        """1.9.37's abroad: a contract without a hired job behind it ends (sync), and fee 0 means no refund owed."""
        j = away('han_quoc')
        b = j.state['journey']['abroad']
        w = b['work']
        c = j.state['careers'][w['career']]
        job = c['job']
        self.assertNotEqual(job.get('status'), 'hired')   # what the old _valid() checks: it finds nothing
        self.assertEqual(w['fee'], 0)


if __name__ == '__main__':
    unittest.main()
