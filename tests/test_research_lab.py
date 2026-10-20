"""🔬 Đơn nghiên cứu (game/research_lab.py): players order research from a Viện nghiên cứu player through 🛎️ Phố dịch vụ.

Real accounts on one store: the three services at NPC × 3, 95 % to the researcher and 5 % burned; the market's generic
"Xong việc" refused until the three graded research steps are done; the effect lands once in the buyer's save (journey.lab)
and is bounded: +1 unit on at most 3 Vườn mới harvests for 14 days, a recipe's extra pay at most 3 xu a job / 12 jobs / 30
xu for 7 days, a gadget shelf of 12 that pays nothing and cannot be sold; one active effect of a kind, a cooldown, and the
most a service can ever add never exceeds its NPC price. Kill switch MNL_RESEARCH_OFF."""
import copy
import json
import os
from unittest import mock

from game import marriage as mr
from game import research_lab as rl
from game import service_market as sm
from game.careers import kit, farm_plus as fp
from game.employment import hired_record
from game.engine import GameError, new_state, validate_state
from tests.test_quay_hire import Base

DAY = 86400


def answer(order_id, service):
    steps, key, _ = rl.brief(order_id, service)
    return [(st['id'], key[st['id']]) for st in steps]


def wrong(st, right):
    if st['type'] == 'number':
        return right + 1
    if st['type'] == 'choice':
        return next(o['id'] for o in st['options'] if o['id'] != right)
    if st['type'] == 'order':
        return list(reversed(right))
    ids = sorted(o['id'] for o in st['options'])
    return [] if right == ids else ids


class LabBase(Base):
    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        rl.install()

    def researcher(self, name):
        tok = self.user(name)

        def fn(s):
            c = s['careers']['research']
            c['started'] = True
            c['job'] = hired_record('research')
        mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def farmer(self, name, wallet=30000):
        tok = self.user(name, wallet=wallet)
        t = int(kit.now())

        def fn(s):
            c = s['careers']['farm']
            c['started'] = True
            c['ext'][fp.KEY] = fp.initial(t)
        mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def sell(self, tok, service, mult=3):
        return sm.post(self.store, tok, None, 'settings', dict(career='research', service=service, on=True, mode='fixed', mult=mult))

    def order(self, buyer, seller, service, **kw):
        self.rid += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=self.pid(seller), career='research', service=service,
                                                             rid=f'lab-{self.rid:08d}', **kw))['order']

    def total(self, tok):
        from game import bank as bk
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def research(self, tok, oid, service, slips=0, name=''):
        steps, key, _ = rl.brief(oid, service)
        out = None
        for i, st in enumerate(steps):
            if i == 0:
                for _ in range(slips):
                    r = rl.post(self.store, tok, None, 'step', dict(order=oid, step=st['id'], value=wrong(st, key[st['id']])))
                    self.assertFalse(r['correct'])
            payload = dict(order=oid, step=st['id'], value=key[st['id']])
            if i == len(steps) - 1 and name:
                payload['name'] = name
            out = rl.post(self.store, tok, None, 'step', payload)
        return out

    def lab(self, tok):
        return self.state(tok)['journey'].get('lab')

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message


class Orders(LabBase):
    def test_three_services_at_npc_x3_seed_batch_end_to_end_95_5(self):
        a, b = self.researcher('rl_prov'), self.farmer('rl_buyer')
        cat = {x['service']: x for x in sm.catalog()['services'] if x['career'] == 'research'}
        self.assertEqual(set(cat), {'giong', 'mon', 'may', 'job'})   # + the workplace's own legacy order (workplace_business.ORDERS)
        self.sell(a, 'giong')
        d = sm.get(self.store, b, None, 'dir', dict(career='research', service='giong'))
        self.assertEqual([x['price'] for x in d['items']], [rl.SERVICES['giong']['base'] * 3])
        ta, tb = self.total(a), self.total(b)
        o = self.order(b, a, 'giong', note='Trồng dưa hấu')
        self.assertEqual((o['status'], o['price']), ('held', 120))
        # the market's generic "Xong việc" is refused until the research is done
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        self.refused('lab_not_done', sm.post, self.store, a, None, 'done', dict(order=o['id']))
        view = rl.get_(self.store, a, None, 'orders', {})
        mine = next(x for x in view['orders'] if x['id'] == o['id'])
        self.assertEqual((mine['at'], mine['total'], mine['status']), (0, 3, 'working'))
        self.assertNotIn('_key', json.dumps(mine))
        r = self.research(a, o['id'], 'giong', name='Mây chịu hạn')
        self.assertEqual(r['order']['status'], 'done')
        fee = sm.fee_of(120)
        self.assertEqual((self.total(a) - ta, tb - self.total(b)), (120 - fee, 120))   # 95 % paid, 5 % burned
        lab = self.lab(b)
        self.assertEqual((lab['seed']['n'], lab['seed']['add'], lab['seed']['name']), (rl.SEED_HARVESTS, 1, 'Mây chịu hạn'))
        self.assertLessEqual(lab['seed']['until'] - int(rl.now()), rl.SEED_DAYS * DAY)
        self.assertEqual(lab['orders'], [o['id']])
        validate_state(self.state(b))
        # shown to both on the order
        res = sm.order_of(self.store.connect().__enter__(), o['id'])['result']
        self.assertIn('Mây chịu hạn', res['text'])

    def test_slips_lower_the_quality_and_the_effect_and_a_step_is_server_graded(self):
        a, b = self.researcher('rl_p2'), self.farmer('rl_b2')
        self.sell(a, 'giong')
        o = self.order(b, a, 'giong')
        self.refused('not_working', rl.post, self.store, a, None, 'step', dict(order=o['id'], step='x', value=1))
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        steps, key, _ = rl.brief(o['id'], 'giong')
        self.refused('stale_step', rl.post, self.store, a, None, 'step', dict(order=o['id'], step=steps[1]['id'], value=key[steps[1]['id']]))
        self.research(a, o['id'], 'giong', slips=2)
        self.assertEqual(self.lab(b)['seed']['n'], rl.SEED_LOW)   # quality 80 % < 90: two harvests, not three
        # someone else cannot work on it
        c = self.researcher('rl_p3')
        self.refused('not_found', rl.post, self.store, c, None, 'step', dict(order=o['id'], step=steps[0]['id'], value=key[steps[0]['id']]))

    def test_one_active_effect_of_a_kind_and_a_cooldown(self):
        a, b = self.researcher('rl_p4'), self.farmer('rl_b4')
        self.sell(a, 'giong')
        o = self.order(b, a, 'giong')
        self.refused('requirement', self.order, b, a, 'giong')   # one open order of this kind
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        self.research(a, o['id'], 'giong')
        msg = self.refused('requirement', self.order, b, a, 'giong')   # active batch
        self.assertIn('Vườn mới đang dùng', msg)

        def spent(s):
            s['journey']['lab']['seed'] = None
        mr._mutate(self.store, {self.sid(b): spent})
        msg = self.refused('requirement', self.order, b, a, 'giong')   # used up, but the cooldown runs
        self.assertIn(f'{rl.COOLDOWN_DAYS} ngày', msg)
        with mock.patch.object(sm, 'now', lambda: rl.time.time() + rl.COOLDOWN_DAYS * DAY + 60):
            self.assertEqual(rl._check('giong')(self.store.connect().__enter__(), self.sid(b), self.state(b)), '')

    def test_buyer_needs_the_system_the_effect_lands_in(self):
        a, b = self.researcher('rl_p5'), self.user('rl_b5')
        self.sell(a, 'giong')
        self.sell(a, 'mon')
        self.assertIn('Vườn mới', self.refused('requirement', self.order, b, a, 'giong'))
        self.assertIn('quán', self.refused('requirement', self.order, b, a, 'mon')) 
        # a player who never worked at the institute cannot sell
        c = self.user('rl_c5')
        self.refused('cannot_provide', self.sell, c, 'giong')

    def test_gadget_lands_on_the_shelf_pays_nothing_and_the_shelf_is_bounded(self):
        a, b = self.researcher('rl_p6'), self.farmer('rl_b6')
        self.sell(a, 'may')
        o = self.order(b, a, 'may')
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        before = copy.deepcopy(self.state(b)['journey'].get('gadgets'))
        self.research(a, o['id'], 'may', name='Quạt Mây Mini')
        lab = self.lab(b)
        self.assertEqual(len(lab['gadgets']), 1)
        g = lab['gadgets'][0]
        self.assertEqual(g['name'], 'Quạt Mây Mini')
        self.assertEqual(self.state(b)['journey'].get('gadgets'), before)   # Mây Mobile's own block untouched: nothing to sell back
        self.assertEqual(rl.max_value('may'), 0)

        def full(s):
            s['journey']['lab']['gadgets'] = [dict(g, o=f'x{i}') for i in range(rl.GADGET_MAX)]
            s['journey']['lab']['last'] = {}
        mr._mutate(self.store, {self.sid(b): full})
        self.assertIn('đầy', self.refused('requirement', self.order, b, a, 'may'))

    def test_effect_lands_once_and_a_tampered_result_is_clamped(self):
        s = new_state()
        s['journey']['story'] = True
        order = dict(id='sv_' + 'a' * 24, provider='p', buyer='b', result=dict(n=99, add=50, name='x' * 300, by='Nhà nghiên cứu'))
        rl._on_buyer('giong')(s, order)
        rl._on_buyer('giong')(s, order)   # replayed: once
        lab = s['journey']['lab']
        self.assertEqual((lab['seed']['n'], lab['seed']['add'], len(lab['seed']['name'])), (rl.SEED_HARVESTS, rl.SEED_ADD, 24))
        self.assertEqual(lab['orders'], [order['id']])
        o2 = dict(order, id='sv_' + 'b' * 24, result=dict(n=5000))
        rl._on_buyer('mon')(s, o2)
        r = lab['recipe']
        self.assertEqual((r['n'], r['pct'], r['per'], r['left']), (rl.RECIPE_USES, rl.RECIPE_PCT, rl.RECIPE_PER, rl.RECIPE_CAP))
        validate_state(s)

    def test_the_last_step_sent_twice_at_once_delivers_and_pays_once(self):
        import concurrent.futures
        a, b = self.researcher('rl_p8'), self.farmer('rl_b8')
        self.sell(a, 'may')
        o = self.order(b, a, 'may')
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        steps, key, _ = rl.brief(o['id'], 'may')
        for st in steps[:-1]:
            rl.post(self.store, a, None, 'step', dict(order=o['id'], step=st['id'], value=key[st['id']]))
        last = steps[-1]
        ta, tb = self.total(a), self.total(b)

        def go(_):
            try:
                return rl.post(self.store, a, None, 'step', dict(order=o['id'], step=last['id'], value=key[last['id']]))
            except mr.MarriageError as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            list(pool.map(go, range(4)))
        sm.settle_for(self.store, None, o['id'])
        price = o['price']
        self.assertEqual(self.total(a) - ta, price - sm.fee_of(price))   # paid once
        self.assertEqual(tb, self.total(b))                              # the escrow left at order time, never again
        self.assertEqual(len(self.lab(b)['gadgets']), 1)                 # one gadget
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM svc_orders WHERE id=?', (o['id'],)).fetchone()['status'], 'done')
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM research_jobs WHERE order_id=? AND status='done'", (o['id'],)).fetchone()['n'], 1)

    def test_kill_switch_stops_new_orders_steps_and_pauses_effects(self):
        a, b = self.researcher('rl_p7'), self.farmer('rl_b7')
        self.sell(a, 'giong')
        o = self.order(b, a, 'giong')
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        with mock.patch.dict(os.environ, {'MNL_RESEARCH_OFF': '1'}):
            self.refused('lab_off', rl.post, self.store, a, None, 'step', dict(order=o['id'], step='x', value=1))
            self.refused('unavailable', self.order, b, a, 'giong')   # not listed while the institute is closed
            self.assertEqual(rl._can_provide(self.state(a)), 'Viện nghiên cứu tạm nghỉ nhận đơn.')
        self.research(a, o['id'], 'giong')
        s = self.state(b)
        with mock.patch.dict(os.environ, {'MNL_RESEARCH_OFF': '1'}):
            self.assertEqual(rl.seed_bonus(s, 10, 'ot'), (0, ''))
            self.assertTrue(rl.public(s)['paused'])
        self.assertEqual(s['journey']['lab']['seed']['n'], rl.SEED_HARVESTS)   # paused, not consumed


class Caps(LabBase):
    def setUp(self):
        super().setUp()
        self.t0 = 2_000_000_000
        kit.clock = lambda: self.t0
        self.addCleanup(setattr, kit, 'clock', rl.time.time)

    def farm(self, add_lab=None):
        from tests.helpers import Journey
        j = Journey('farm')
        j.act('fa_v_open')
        if add_lab is not None:
            j.state['journey']['lab'] = add_lab
        validate_state(j.state)
        return j

    def seeded(self, n=rl.SEED_HARVESTS, until=None):
        lab = rl.initial()
        lab['seed'] = dict(o='sv_' + 'c' * 24, n=n, add=1, until=until or self.t0 + rl.SEED_DAYS * DAY, by='Thư', name='Mây-12')
        return lab

    def harvest(self, j, i=0):
        j.act('fa_v_plant', plot=i, crop='ot')
        self.t0 += fp.CROP['ot']['mins'] * 60 + 5
        g = j.c['ext'][fp.KEY]
        g['plots'][i]['done'] = [k for k, _ in g['plots'][i]['needs']]
        before = sum(a + b for a, b in g['store'].values())
        r = j.act('fa_v_harvest', plot=i)
        after = sum(a + b for a, b in j.c['ext'][fp.KEY]['store'].values())
        return after - before, r['message']

    def test_seed_batch_adds_one_unit_on_three_harvests_then_nothing(self):
        plain = self.farm()
        base, _ = self.harvest(plain)
        j = self.farm(self.seeded())
        got = []
        for _ in range(5):
            n, msg = self.harvest(j)
            got.append(n - base)
        self.assertEqual(got, [1, 1, 1, 0, 0])
        lab = j.state['journey']['lab']
        self.assertIsNone(lab['seed'])
        self.assertEqual(lab['stats']['seed_units'], rl.SEED_HARVESTS)
        validate_state(j.state)

    def test_seed_batch_expires_and_needs_room(self):
        j = self.farm(self.seeded(until=self.t0 + 60))
        n, _ = self.harvest(j)   # the clock moved past `until` while it grew
        self.assertIsNone(j.state['journey']['lab']['seed'])
        lab = rl.initial()
        lab['seed'] = self.seeded()['seed']
        s = {'journey': {'lab': lab}}
        self.assertEqual(rl.seed_bonus(s, 0, 'ot'), (0, ''))   # no room: nothing used
        self.assertEqual(rl.seed_bonus(s, 9, 'cafe'), (0, ''))   # a crop the batch does not boost (the price bound): nothing used
        self.assertEqual(lab['seed']['n'], rl.SEED_HARVESTS)

    def test_recipe_pays_at_most_three_a_job_twelve_jobs_thirty_xu_in_all(self):
        from tests.helpers import Journey
        j = Journey('pho')
        lab = rl.initial()
        lab['recipe'] = dict(o='sv_' + 'd' * 24, n=rl.RECIPE_USES, pct=rl.RECIPE_PCT, per=rl.RECIPE_PER, left=rl.RECIPE_CAP,
                             until=self.t0 + rl.RECIPE_DAYS * DAY, by='Thư', name='SM-40')
        j.state['journey']['lab'] = lab
        paid = []
        for i in range(20):
            t = dict(id=f'pho-0001-{i:02d}', career='pho')
            paid.append(rl.recipe_bonus(j.state, j.c, t, 500))   # a big job still pays at most RECIPE_PER
        self.assertTrue(all(0 <= x <= rl.RECIPE_PER for x in paid))
        self.assertLessEqual(sum(paid), rl.RECIPE_CAP)
        self.assertLessEqual(sum(1 for x in paid if x), rl.RECIPE_USES)
        self.assertIsNone(j.state['journey']['lab']['recipe'])
        # a small job: at least 1 xu; not a food shop: nothing; expired: nothing
        lab['recipe'] = dict(o='sv_' + 'e' * 24, n=2, pct=10, per=3, left=30, until=self.t0 + 10, by='', name='x')
        self.assertEqual(rl.recipe_bonus(j.state, j.c, dict(id='a', career='lawyer'), 100), 0)
        self.assertEqual(rl.recipe_bonus(j.state, j.c, dict(id='b', career='pho'), 4), 1)
        self.t0 += 20
        self.assertEqual(rl.recipe_bonus(j.state, j.c, dict(id='c', career='pho'), 100), 0)

    def test_recipe_reaches_a_real_finished_job(self):
        from tests.helpers import Journey
        from game import engine
        j = Journey('pho', slot=0, day=2)
        lab = rl.initial()
        lab['recipe'] = dict(o='sv_' + 'f' * 24, n=3, pct=10, per=3, left=30, until=self.t0 + DAY, by='Thư', name='SM-41')
        j.state['journey']['lab'] = lab
        money = j.c['money']
        engine.task_done(j.state, j.c, j.task, 20, 'Xong bát phở.')
        self.assertEqual(j.state['journey']['lab']['recipe']['n'], 2)
        self.assertGreaterEqual(j.c['money'] - money, 20 + 2)

    def test_no_service_can_ever_add_more_than_its_npc_price(self):
        for sid, sp in rl.SERVICES.items():
            self.assertLessEqual(rl.max_value(sid), sp['base'], sid)
            spec = sm.get_spec('research', sid)
            self.assertEqual(spec['base'], sp['base'])
            self.assertLessEqual(spec['work_hours'], 72)
        self.assertEqual(sm.DEFAULT_MULT, 3)   # the buyer pays three times that by default

    def test_the_block_validates_strictly_and_upgrades_leniently(self):
        s = new_state()
        s['journey']['lab'] = rl.initial()
        validate_state(s)
        for bad in (dict(seed=dict(o='x', n=9, add=1, until=1, by='', name='')), dict(recipe=dict(o='x', n=1, pct=50, per=1, left=1, until=1, by='', name='')),
                    dict(gadgets=[dict(o='x', kind='fan', name='a', by='b', at=1, q=1)] * (rl.GADGET_HARD + 1)), dict(extra=1), dict(stats={})):
            t = copy.deepcopy(s)
            t['journey']['lab'].update(bad)
            with self.assertRaises(GameError, msg=str(bad)):
                validate_state(t)
            j = copy.deepcopy(t['journey'])
            rl.upgrade(j)
            t['journey'] = j
            validate_state(t)
