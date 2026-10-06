"""💰 Top tài phú (game/wealth.py, game/leaderboard.py `wealth`, game/lb_titles.py): net worth computed from the
save agrees with what "Tiền của bạn" (public/js/v4/wealth.js pockets()) shows for the same save, plus the money the
save holds beyond the sheet (Mây savings, vehicles, Quầy riêng, the fair's Vay nóng) and never Mây Coin, gold or the
Quỹ chung; the board's rows, order and privacy, its weekly titles, and the leaderboard write that sends only the rows
that moved."""
import copy
import datetime as dt
import json
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from unittest import mock

from game import bank as bk
from game import garage as gr
from game import housing as hs
from game import lb_titles as lbt
from game import leaderboard as lb
from game import property_market as pm
from game import quay as qy
from game import wealth as wl
from game.engine import new_state, public_state, validate_state
from tests.test_bank import B, act, opened, story
from tests.test_housing_multi import buy2, tick, to_v1
from tests.test_leaderboard import FORMAT, Base, crafted
from tests import test_quay as tq

ROOT = Path(__file__).resolve().parents[1]
CALM = dt.datetime(2026, 9, 1, 12, tzinfo=pm.VN).timestamp()   # before the property news calendar: every quote neutral

NODE_POCKETS = """
import {pockets} from %s;
let raw='';for await(const c of process.stdin)raw+=c;
const out=JSON.parse(raw).map(([state,current])=>{const P=pockets(state,{joint:null,current});return P.story?[P.net,P.assets,P.debt]:null;});
console.log(JSON.stringify(out));
"""


def js_pockets(states):
    """[(net, assets, debt) | None] from wealth.js pockets() on each save's public view, with the workplace on
    screen the way app.js passes it (career(): current, else focus); the joint fund left out (null)."""
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('node not installed')
    views = []
    for s in states:
        v = public_state(copy.deepcopy(s))
        views.append([v, v.get('current') or v.get('focus') or 'mother_baby'])
    url = json.dumps((ROOT / 'public/js/v4/wealth.js').as_uri())
    out = subprocess.run([node, '--input-type=module', '-e', NODE_POCKETS % url], input=json.dumps(views), cwd=ROOT,
                         capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise AssertionError(out.stderr)
    return [tuple(x) if x else None for x in json.loads(out.stdout)]


def fund(s, cid, money):
    """A started workplace holding `money` (its ledger's opening balance moves with it, as the save checks)."""
    c = s['careers'][cid]
    c['started'] = True
    c['ops']['finance']['opening_balance'] += money - c['money']
    c['money'] = money
    return s


def rich():
    """Wallet, two workplaces (one empty), bank account + demand + a term deposit, a bank loan, a card balance,
    a home bought on a mortgage and a second home, both grown in value."""
    s = opened(wallet=60000, deposit=3000, income_days=14, salary=400)
    B(s)['score'] = 760
    s, _ = act(s, 'jr_bk_save', amount=600, term=0)
    s, _ = act(s, 'jr_bk_save', amount=500, term=30)
    q = bk.quote(300, 'personal', 28)
    s, r = act(s, 'jr_bk_loan_apply', kind='personal', amount=300, term=28, total_interest=q['interest'], confirm=True)
    assert r.get('approved'), r
    s, r = act(s, 'jr_bk_card_apply', confirm=True)
    assert r.get('approved'), r
    bk.pay(s, 150, 'Lò vi sóng', method='card')
    s, _ = buy2(s, 'can_ho_mini', down=hs.down_min(hs.HOMES['can_ho_mini']['price']), months=36)
    s, _ = buy2(s, 'nha_pho')
    tick(s, 20, salary=400)
    fund(s, 'grocery', 840)
    fund(s, 'florist', 0)
    validate_state(s)
    return s


def one_home():
    """One home on a mortgage, 10 days on (to_v1 turns it into the 1.4.5 shape: version 1, no props)."""
    s = opened(wallet=8000, deposit=1000, income_days=14, salary=200)
    B(s)['score'] = 760
    s, _ = buy2(s, 'can_ho_mini', down=hs.down_min(hs.HOMES['can_ho_mini']['price']), months=36)
    tick(s, 10, salary=200)
    return s


def owner_of_everything():
    """1.5–1.7 money through the real commands: a Quầy riêng with staff, a motorbike, the Mây savings book, then a
    fair loan still owed (journey.fair_cash, as fair_borrow leaves it) and some Mây Coin and gold (never counted)."""
    s = tq.opened('sap', wallet=30000)
    fund(s, 'milk_tea', 400)
    s, _ = act(s, 'jr_garage_buy', id='xe_dap', confirm=True)
    s, _ = act(s, 'iv_save', amount=1500)
    j = s['journey']
    j['fair_cash'] = dict(v=1, gift='', loan=dict(ed='20261003', p=100, due=120), debt=0)
    st = tq.ST(s)
    st['due'], st['till'] = 45, 260
    validate_state(s)
    return s


class Formula(unittest.TestCase):
    def setUp(self):
        clock = mock.patch.object(pm, 'now', return_value=CALM)
        clock.start()
        self.addCleanup(clock.stop)

    def test_hand_computed(self):
        s = story(wallet=250)
        fund(s, 'grocery', 900)
        fund(s, 'florist', -40)
        s['careers']['milk_tea']['money'] = 5000          # not started: not yours
        j = s['journey']
        j['life_day'] = 70
        j['bank'] = dict(bk.initial(1, 1), balance=300, demand=200,
                         terms=[dict(id='t1', amount=400, term=30, rate=500, start=60, due=90, renew=False)],
                         loans=[dict(rows=[dict(amount=110, paid=110), dict(amount=110, paid=30)]),     # 80 left
                                dict(rows=[dict(amount=50, paid=50)])],                                 # paid off
                         card=dict(bal=35))
        j['home'] = dict(hs.initial(1), own=dict(id='h1', kind='tap_the', price=1000, day=10, loan=dict(rows=[dict(amount=100, paid=0)] * 3)),
                         props=[dict(id='h2', kind='can_ho_mini', price=4000, day=70, loan=None)])
        own_value = min(1000 * 130 // 100, 1000 + 1000 * hs.GROW_RATE * 60 // (10000 * hs.YEAR_DAYS)) // 10 * 10
        self.assertEqual(own_value, 1030)
        assets = 250 + 900 + 300 + 200 + 400 + own_value + 4000
        debt = 40 + 80 + 35 + 300
        self.assertEqual(wl.sheet(s), (assets - debt, assets, debt))
        self.assertEqual(wl.extras(s), (0, 0))
        self.assertEqual(wl.worth(s), (assets - debt, assets, debt))
        self.assertEqual(wl.score(s), (assets - debt, assets))

    def test_property_market_basis(self):
        """A home's value is today's property quote over the one it was bought at (journey.property_market_basis)."""
        s = fund(story(wallet=0), 'grocery', 0)   # a started workplace: the sheet does not fall back to the one on screen
        j = s['journey']
        j['life_day'] = 10
        j['home'] = dict(hs.initial(1), own=dict(id='h1', kind='can_ho_mini', price=4000, day=10, loan=None),
                         props=[dict(id='h2', kind='can_ho_mini', price=4000, day=10, loan=None)])
        j['property_market_basis'] = {'h2': 8000}
        up = dict(multiplier_bp=12000, rent_bp=10000, news=None)
        r = rich()
        r['journey']['property_market_basis'] = {r['journey']['home']['props'][0]['id']: 8000}
        with mock.patch.object(pm, 'quote', return_value=up):
            self.assertEqual(wl.sheet(s)[1], 4000 * 12000 // 10000 + 4000 * 12000 // 8000)
            self.assertEqual([wl.sheet(r)], js_pockets([r]), 'the sheet reads the same quote and basis')

    def test_wallet_debt_and_no_row(self):
        s = story(wallet=-90)
        fund(s, 'grocery', 50)
        self.assertEqual(wl.worth(s), (-40, 50, 90))
        self.assertIsNone(wl.score(s), '0 or less: no row')
        self.assertNotIn(lb.WEALTH, lb.summary(s))
        s['careers']['grocery']['money'] = 90
        self.assertIsNone(wl.score(s), 'exactly 0: no row')
        s['careers']['grocery']['money'] = 91
        self.assertEqual(lb.summary(s)[lb.WEALTH], (1, 91, 0, 0, 0, 0, 0, 0))

    def test_free_play_and_junk(self):
        s = new_state()
        fund(s, 'grocery', 900)
        self.assertIsNone(wl.worth(s), 'free play has no wallet')
        self.assertIsNone(wl.sheet(s))
        self.assertIsNone(wl.extras(s))
        self.assertNotIn(lb.WEALTH, lb.summary(s))
        for junk in (None, [], {}, {'journey': []}, {'journey': {'story': True, 'wallet': 'x', 'bank': {'terms': 'x', 'loans': [1, None]}}},
                     {'journey': {'story': True, 'garage': {'cars': {'x': None, 'y': {'p': 'z'}}}, 'quay': {'stalls': [None, {'place': 'nowhere'}]},
                                  'invest': {'saving': []}, 'fair_cash': {'loan': 5, 'debt': None}}}):
            w = wl.worth(junk)
            self.assertTrue(w is None or w == (0, 0, 0), junk)

    def test_extras_hand_computed(self):
        """Mây savings, vehicles at buy-back, a Quầy riêng at its sang nhượng price less what it owes, the fair's
        Vay nóng; Mây Coin and gold never."""
        s = fund(story(wallet=1000), 'grocery', 0)
        j = s['journey']
        j['invest'] = dict(saving=dict(balance=700, pending=999), coin=dict(units=10**9))      # pending: milli-xu
        j['garage'] = dict(v=1, cars={'xe_dap': dict(c='do', n='', d=1, p=120), 'xe_may': dict(c='do', n='', d=1, p=3000)})
        j['quay'] = dict(v=1, stalls=[dict(id='q1', place='xe', items=['surge'], till=50, fund=200, due=30,
                                           business=dict(v=1, unpaid_fines=5))])
        j['fair_cash'] = dict(v=1, gift='', loan=dict(ed='20261003', p=100, due=120), debt=40)
        j['vang'] = dict(v=1, phan=500, cost=10**6)
        cars = 120 * 70 // 100 // 10 * 10 + 3000 * 70 // 100 // 10 * 10
        self.assertEqual(cars, 80 + 2100)
        self.assertEqual((gr.sell_price(120), gr.sell_price(3000)), (80, 2100))
        stall = 800 * 50 // 100 + 120 * 30 // 100 + 50 + 200
        self.assertEqual(stall - 30 - 5, qy.sell_back(j['quay']['stalls'][0]), 'the counter is worth its sang nhượng price')
        self.assertEqual(wl.extras(s), (700 + cars + stall, 30 + 5 + 120 + 40))
        self.assertEqual(wl.sheet(s), (1000, 1000, 0), 'the sheet itself never lists them')
        net, assets, debt = wl.worth(s)
        self.assertEqual((assets, debt), (1000 + 700 + cars + stall, 195))
        self.assertEqual(net, assets - debt)

    def test_coin_gold_and_couple_fund_left_out(self):
        s = owner_of_everything()
        base = wl.worth(s)
        j = s['journey']
        j['invest']['coin']['units'] += 10**7
        j['vang'] = dict(v=1, phan=900, cost=500000)
        s['marriage'] = dict(spouse=dict(status='married', name='Gió'))   # the Quỹ chung lives outside the save
        self.assertEqual(wl.worth(s), base)

    def test_real_commands(self):
        """Through the game's own commands: a vehicle loses 30 % of its price the moment it is bought, the Mây
        savings book only moves money between pockets, and selling a Quầy riêng turns it into exactly the cash it
        was counted at."""
        s = owner_of_everything()
        net = wl.worth(s)[0]
        s2, _ = act(s, 'jr_garage_buy', id='xe_dap_dien', confirm=True)
        price = s2['journey']['garage']['cars']['xe_dap_dien']['p']
        self.assertEqual(wl.worth(s2)[0], net - price + gr.sell_price(price))
        s3, _ = act(s, 'iv_save', amount=500)
        self.assertEqual(wl.worth(s3)[0], net)
        st = tq.ST(s)
        s4, _ = act(s, 'jr_quay_sell', stall=st['id'], confirm=True)
        self.assertEqual(s4['journey']['quay']['stalls'], [])
        self.assertEqual(wl.worth(s4)[0], net)
        s5 = copy.deepcopy(s)
        s5['journey']['fair_cash'] = dict(v=1, gift='', loan=None, debt=0)
        self.assertEqual(wl.worth(s5)[0], net + 120, 'the Vay nóng is a debt')

    def test_clamped_to_the_column(self):
        s = story(wallet=10**9)
        j = s['journey']
        j['bank'] = dict(bk.initial(1, 1), balance=10**9, demand=10**9)
        self.assertEqual(wl.score(s), (wl.INT_MAX, wl.INT_MAX))

    def test_reads_only(self):
        for s in (to_v1(one_home()), owner_of_everything()):
            before = json.dumps(s, sort_keys=True)
            wl.worth(s)
            lb.summary(s)
            self.assertEqual(json.dumps(s, sort_keys=True), before, 'nothing upgraded or settled in place')

    def test_cheap(self):
        for state in (owner_of_everything(), rich()):
            t = time.perf_counter()
            for _ in range(200):
                wl.worth(state)
            self.assertLess((time.perf_counter() - t) / 200, .001)


class SameAsTheSheet(unittest.TestCase):
    """The sheet part of the board's number is the sheet's number: Python on the save, wealth.js on its public view;
    the board adds `extras()` on top."""

    def test_python_and_js_agree(self):
        r = rich()
        poor = story(wallet=-40)
        fund(poor, 'grocery', 25)
        fresh = story(wallet=60)                     # nothing started: the sheet counts the workplace on screen
        current = story(wallet=60)
        current['current'] = 'florist'
        current['careers']['florist']['money'] = 410
        mid = opened(wallet=900, deposit=300)
        fund(mid, 'milk_tea', 1234)
        home = one_home()
        everything = owner_of_everything()
        saves = [r, home, to_v1(home), poor, fresh, current, mid, everything, new_state()]
        py = [wl.sheet(s) for s in saves]
        js = js_pockets(saves)
        self.assertEqual(py, js)
        self.assertIsNone(py[-1])
        self.assertGreater(py[0][2], 0, 'the rich fixture has debts of every kind')
        self.assertEqual(py[1], py[2], 'a version 1 home block counts the same')
        self.assertGreater(py[1][2], 0)
        self.assertEqual(py[5][1], 60 + 410)
        for s, sheet in zip(saves[:-1], py):
            ea, ed = wl.extras(s)
            self.assertEqual(wl.worth(s), (sheet[0] + ea - ed, sheet[1] + ea, sheet[2] + ed))
        ea, ed = wl.extras(everything)
        self.assertGreater(ea, 1500, 'the Mây savings, the vehicle and the counter')
        self.assertEqual(ed, 45 + 120, 'what the counter owes and the fair loan')


class WealthBoard(Base):
    def rich_save(self, name, wallet, extra_assets=0):
        s = fund(story(wallet=wallet), 'grocery', extra_assets)   # a fund is never below 0 in a valid save
        s['name'] = name
        return s

    def test_board_order_ties_and_display(self):
        a = self.player(self.rich_save('An', 5000), account='An')
        b = self.player(self.rich_save('Bình', -1000, extra_assets=6000), account='Bình')   # net 5000, more assets
        c = self.player(self.rich_save('Chi', 9000), account='Chi')
        d = self.player(self.rich_save('Dung', 5000), account='Dung')                                 # tie with An, later
        self.player(self.rich_save('Én', -10), account='Én')                                           # in debt: no row
        free = crafted('Phong', grocery=(300, 3, 5))
        self.player(free, account='Phong')                                                            # free play: no row
        v = lb.view(self.store, lb.WEALTH, token=a)
        self.assertEqual([r['name'] for r in v['rows']], ['Chi', 'Bình', 'An', 'Dung'])
        self.assertEqual(v['total'], 4)
        self.assertEqual(v['rows'][0]['xu'], 9000)
        self.assertEqual(v['rows'][0]['score'], 9000)
        self.assertEqual(v['me']['rank'], 3)
        self.assertEqual(v['me']['xu'], 5000)
        self.assertEqual(self.rows(b)[lb.WEALTH]['k1'], 6000)
        self.assertTrue(d)

    def test_guests_opt_in_and_hidden_names(self):
        g = self.player(self.rich_save('Khách Giàu', 99999))
        acc = self.player(self.rich_save('X', 100), account='Tài Khoản')
        self.assertEqual([r['name'] for r in lb.view(self.store, lb.WEALTH)['rows']], ['Tài Khoản'])
        me = lb.view(self.store, lb.WEALTH, token=g)['me']
        self.assertEqual((me['rank'], me['visible']), (1, False), 'a hidden guest still sees where they stand')
        lb.set_visible(self.store, acc, self.store.read(acc)[0], False)
        lb.clear_cache()
        self.assertEqual(lb.view(self.store, lb.WEALTH)['rows'], [])

    def test_rows_follow_money(self):
        tok = self.player(self.rich_save('An', 300), account='An')
        self.assertEqual(self.rows(tok)[lb.WEALTH]['score'], 300)
        st = self.store.read(tok)[0]
        st['journey']['wallet'] = -5
        self.cmd(tok, 'import_save', {'save': {'format': FORMAT, 'state': st}})
        self.assertNotIn(lb.WEALTH, self.rows(tok), 'net worth 0 or less: the row goes')

    def test_vehicle_on_the_board(self):
        tok = self.player(self.rich_save('An', 500), account='An')
        self.cmd(tok, 'jr_garage_buy', {'id': 'xe_dap', 'confirm': True})
        self.assertEqual(self.rows(tok)[lb.WEALTH]['score'], 500 - 120 + gr.sell_price(120))

    def test_parse_query(self):
        self.assertEqual(lb.parse_query({'board': 'wealth'}), ('wealth', lb.LIMIT))
        self.assertIn(lb.WEALTH, lb.BOARDS)
        self.assertEqual(lb.VERSION, 3, 'a new formula: the next start rebuilds every row')

    def test_weekly_titles(self):
        self.assertEqual([lbt.title_of('wealth', r)['text'] for r in (1, 2, 3, 4, 10)],
                         ['💎 Đại gia của phố', '💰 Đại gia mới nổi', '💰 Đại gia mới nổi', '🤑 Hội nhà giàu', '🤑 Hội nhà giàu'])
        self.assertIsNone(lbt.title_of('wealth', 11))
        self.assertIn('wealth', lbt.MAIN)
        toks = [self.player(self.rich_save(f'N{i}', 1000 - i), account=f'Người {i:02d}') for i in range(11)]
        self.assertTrue(lbt.refresh(self.store, time.time()))
        v = lb.view(self.store, lb.WEALTH, token=toks[0])
        self.assertEqual(v['rows'][0]['title'], dict(emoji='💎', name='Đại gia của phố'))
        self.assertEqual([len(t['holders']) for t in v['weekly']['tiers']], [1, 2, 7])
        self.assertIn(dict(emoji='💎', name='Đại gia của phố', board='wealth', label='Top 1'), v['me']['titles'])


class DeltaWrite(Base):
    """lb.write(old=…): the same boards → only the rows that moved; a board gained or lost → the full sync; the
    storage layer passes `old` only when it remembers the rows it wrote itself."""

    def test_only_moved_rows(self):
        with self.store.connect() as db:
            db.execute("INSERT INTO sessions(sid,csrf,state,revision) VALUES('s1','x','{}',1)")
            old = {'grocery': (100, 2, 0, 2, 2, 5, 0, 0), lb.WEALTH: (500, 500, 0, 0, 0, 0, 0, 0), lb.NAME: None}
            lb.write(db, 's1', old, now=1.0)
            new = dict(old, **{lb.WEALTH: (650, 650, 0, 0, 0, 0, 0, 0)})
            seen = []
            real = db.execute

            class Spy:
                def execute(self, sql, args=()):
                    seen.append(sql.split()[0] + (' ' + args[1] if sql.startswith('INSERT INTO leaderboard(') else ''))
                    return real(sql, args)
            lb.write(Spy(), 's1', new, now=2.0, old=old)
            self.assertEqual(seen, ['INSERT wealth'])
            rows = {r['board']: r for r in db.execute("SELECT * FROM leaderboard WHERE sid='s1'")}
            self.assertEqual((rows['wealth']['score'], rows['wealth']['since'], rows['grocery']['since']), (650, 2.0, 1.0))
            gone = {k: v for k, v in new.items() if k != lb.WEALTH}
            lb.write(db, 's1', gone, now=3.0, old=new)
            self.assertEqual(sorted(r['board'] for r in db.execute("SELECT board FROM leaderboard WHERE sid='s1'")), ['grocery'])

    def test_commands_keep_rows_exact(self):
        tok = self.player(fund(story(wallet=300), 'grocery', 200), account='An')
        sid = self.sid(tok)
        self.cmd(tok, 'jr_bk_open')
        for amount in (50, 70):   # money moves between pockets: net worth stays, the rows stay exact
            self.cmd(tok, 'jr_bk_deposit', {'amount': amount})
        self.cmd(tok, 'jr_withdraw', {'career': 'grocery', 'amount': 20})
        state = self.store.read(tok)[0]
        want = {b: v for b, v in lb.summary(state).items() if b != lb.NAME}
        got = {r['board']: tuple(r[f] for f in lb._FIELDS) for r in lb.export_rows(self.store, sid)}
        self.assertEqual(got, want)

    def worker(self):
        """A player with XP at the grocery (rows grocery, all, wealth) whose grocery row the table got wrong."""
        s = fund(story(wallet=3000), 'grocery', 200)
        c = s['careers']['grocery']
        c.update(xp=200, day=3)
        c['metrics']['served'] = 5
        tok = self.player(s, account='An')
        sid = self.sid(tok)
        self.assertEqual(set(self.rows(tok)), {'grocery', 'all', lb.WEALTH})
        self.store.transaction(lambda db: db.execute("UPDATE leaderboard SET score=1 WHERE sid=? AND board='grocery'", (sid,)))
        return tok, sid

    def exact(self, tok, sid):
        state = self.store.read(tok)[0]
        got = {r['board']: tuple(r[f] for f in lb._FIELDS) for r in lb.export_rows(self.store, sid)}
        self.assertEqual(got, {b: v for b, v in lb.summary(state).items() if b != lb.NAME})

    def test_first_command_of_a_process_heals(self):
        """No remembered summary (a new process, or the save moved elsewhere): the full sync, so a row the table got
        wrong is put right by the next command that moves a number."""
        tok, sid = self.worker()
        lb._recent.clear()
        self.cmd(tok, 'jr_garage_buy', {'id': 'xe_dap', 'confirm': True})   # 💰 moves (a vehicle loses 30 %)
        self.exact(tok, sid)

    def test_unchecked_rows_are_not_trusted(self):
        """A first command that moves nothing writes nothing, so what it remembers is not known to be the table's:
        the next command that moves a number still does the full sync."""
        tok, sid = self.worker()
        lb._recent.clear()
        self.cmd(tok, 'settings', {'sound': False})               # nothing on a board moved: no write
        self.assertIsNone(lb.synced(sid, self.store.read(tok)[1]))
        self.assertEqual(self.rows(tok)['grocery']['score'], 1)
        self.cmd(tok, 'jr_garage_buy', {'id': 'xe_dap', 'confirm': True})
        self.exact(tok, sid)
        self.assertIsNotNone(lb.synced(sid, self.store.read(tok)[1]), 'written in full: trusted from now on')
        self.cmd(tok, 'jr_garage_buy', {'id': 'xe_dap_dien', 'confirm': True})   # now the delta write
        self.exact(tok, sid)


class Wired(unittest.TestCase):
    def test_ui(self):
        js = (ROOT / 'public/js/v4/leaderboard.js').read_text(encoding='utf-8')
        self.assertIn("tab('wealth','Tài phú','💰')", js)
        self.assertIn("const OWN=['certs','titles','wealth']", js)
        self.assertIn('Tài sản ròng · chưa tính coin, vàng, Quỹ chung', js)
        self.assertIn('Chưa tính Mây Coin, vàng (giá đổi từng phút) và Quỹ chung.', js)
        self.assertIn("tabs.length>4?'five':'four'", js)
        css = (ROOT / 'public/css/leaderboard.css').read_text(encoding='utf-8')
        self.assertIn('html[data-layout="phone"] .lb-kinds.five>button:nth-child(n+4){grid-column:span 3}', css)
        self.assertIn('html[data-layout="phone"] .lb-kinds.four{grid-template-columns:repeat(2,minmax(0,1fr))', css)

    def test_no_live_price_or_database(self):
        src = (ROOT / 'game/wealth.py').read_text(encoding='utf-8')
        code = src.split('"""', 2)[2]
        for word in ('realtime_market', 'from .invest', 'from .vang', 'execute(', 'connect(', 'import time'):
            self.assertNotIn(word, code, word)


if __name__ == '__main__':
    unittest.main()
