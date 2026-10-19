"""🏝️ Đảo bang bought and upgraded from the fund (owner 21/10, SCHEMA_VERSION 62): a bang founded now holds no island
until a Phó bang or the Bang chủ buys cấp 1 (1 triệu) from the fund, then upgrades it (cấp 2…5 at the private islands'
prices, 6/12/24/48 h builds). The debit happens once (two officers at once, a repeated request), only from the fund;
upgrades go one level at a time and finish by time; the room's cap grows with the level; the facilities' higher levels
wait for the island (levels already built stay); a bang written without the new columns (before this release, or by
2.4.64 during the rollout) holds cấp 1 for free; what is played on the island (a visit, the pet arena, the Bang chiến
pet) needs it, while joining, the fund, check-in, builds, the shop and the Giờ vàng do not. And the fund has no cap any
more: a single huge gift (wallet then bank, Sổ ví rows of at most 10 M), billions over several gifts, its points capped a
day, the weekly ranking untouched by the island."""
import asyncio
import threading
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import bang_island as BI
from game import bang_island_source as SRC
from game import bang_pets
from game import island_content as IC
from game import marriage as mr
from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from game.engine import GameError, validate_state
from tests.test_bang import Base
from tests.test_bang_island_source import AsyncDb
from tests.test_bank import act
from tests.test_island import rich
from tests.test_lb_titles import at


class Numbers(Base):
    def test_ladder_follows_the_private_islands(self):
        self.assertEqual(C.ISLE_PRICES, (1_000_000, 30_000_000, 60_000_000, 120_000_000, 200_000_000))
        self.assertEqual(C.ISLE_PRICES[1:], tuple(i['price'] for i in IC.ISLANDS), 'read from game/island_content.py, no multiplier')
        self.assertEqual([C.isle_cost(n)[1] // 3600 for n in range(1, 6)], [0, 6, 12, 24, 48])
        self.assertEqual([C.isle_cap(n) for n in range(0, 6)], [0, 30, 40, 50, 60, 80])
        self.assertLessEqual(max(C.ISLE_CAP), BI.CAP_MAX)
        self.assertEqual(C.ISLE_MAX, BI.ISLE_MAX)
        self.assertEqual([C.isle_needed('kho', n) for n in range(1, 11)], [0, 0, 0, 0, 2, 2, 3, 3, 4, 5])
        self.assertEqual([C.isle_needed(C.HALL, n) for n in range(1, 6)], [0, 0, 2, 3, 5], 'a 5-level facility counts double')
        self.assertEqual(len(C.ISLE_ZONES), C.ISLE_MAX)


class Buying(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.b, self.c = self.player(name='Minh'), self.player(name='Tú')
        for t in (self.b, self.c):
            self.op(t, 'join', bang=self.bid)
        self.op(self.a, 'role', pid=self.pid(self.b), role='pho')
        self.op(self.a, 'role', pid=self.pid(self.c), role='lao')

    def row(self):
        return self.one('SELECT * FROM bangs WHERE id=?', (self.bid,))

    def ledger(self):
        return self.rows("SELECT id, kind, amount, balance FROM bang_fund WHERE bang=? AND id LIKE 'i:%' ORDER BY at, id", (self.bid,))

    def has(self):
        with self.store.connect() as db:
            return bang.has_island(db, self.bid)

    def test_a_new_bang_has_none_and_officers_buy_it_once_from_the_fund(self):
        r = self.row()
        self.assertEqual((r['isle'], r['isle_how']), (0, ''))
        self.assertFalse(self.has())
        self.assertEqual(bang.page(self.store, self.sid(self.a))['isle']['level'], 0)
        self.refused_op(self.b, 'isle', 'not_enough', to=1, confirm=True)             # an empty fund
        self.give(self.a, 3_000_000)
        before = (self.wallet(self.a), self.wallet(self.b))
        self.refused_op(self.c, 'isle', 'role', to=1, confirm=True)                   # Trưởng lão: no
        self.refused_op(self.b, 'isle', None, to=1)                                   # needs the confirmation
        self.refused_op(self.b, 'isle', None, to=0, confirm=True)
        self.refused_op(self.b, 'isle', None, to='1', confirm=True)
        self.refused_op(self.b, 'isle', 'order', to=2, confirm=True)                  # one level at a time
        out = self.op(self.b, 'isle', to=1, confirm=True)['done']                     # a Phó bang buys it
        self.assertIn('đã có đảo', out['message'])
        r = self.row()
        self.assertEqual((r['isle'], r['isle_to'], r['isle_how'], r['isle_paid'], r['fund'], r['spent']), (1, None, 'buy', 1_000_000, 2_000_000, 1_000_000))
        self.assertEqual(self.ledger(), [dict(id=f'i:{self.bid}:1', kind='build', amount=-1_000_000, balance=2_000_000)])
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), before, 'never from a wallet')
        self.assertTrue(self.has())
        again = self.op(self.a, 'isle', to=1, confirm=True)['done']                   # the same request again: nothing paid
        self.assertTrue(again.get('again'))
        self.assertEqual((self.row()['fund'], len(self.ledger())), (2_000_000, 1))
        self.assertTrue(any(e.get('op') == 'bang_island' and e.get('why') == 'view' for e in self.sent))
        self.assertTrue(self.rows("SELECT 1 FROM bang_log WHERE bang=? AND text LIKE '%mua Đảo bang%'", (self.bid,)))

    def test_two_officers_buy_at_once_one_debit(self):
        self.give(self.a, 5_000_000)
        got, errs = [], []

        def go(tok):
            try:
                got.append(self.op(tok, 'isle', to=1, confirm=True)['done'])
            except bang.BangError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=(t,)) for t in (self.a, self.b)]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual((len(got), errs), (2, []))
        self.assertEqual(sorted(bool(x.get('again')) for x in got), [False, True], 'the second one waited and saw the purchase')
        self.assertEqual((self.row()['fund'], self.row()['isle_paid'], len(self.ledger())), (4_000_000, 1_000_000, 1))

    def test_upgrades_one_level_at_a_time_real_time_builds_and_two_officers_at_once(self):
        self.set_fund(self.bid, 1_000_000_000)
        self.op(self.a, 'isle', to=1, confirm=True)
        got, errs = [], []

        def go(tok):
            try:
                got.append(self.op(tok, 'isle', to=2, confirm=True)['done'])
            except bang.BangError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=(t,)) for t in (self.a, self.b)]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual(errs, [])
        self.assertEqual(sorted(bool(x.get('again')) for x in got), [False, True])
        r = self.row()
        self.assertEqual((r['isle'], r['isle_to'], r['isle_ready'] - self.t[0]), (1, 2, 6 * 3600))
        self.assertEqual(r['fund'], 1_000_000_000 - 1_000_000 - 30_000_000, 'one debit for two officers')
        self.refused_op(self.a, 'isle', 'building', to=3, confirm=True)
        card = bang.page(self.store, self.sid(self.a))['isle']
        self.assertEqual((card['level'], card['to'], card['cap']), (1, 2, 30))
        self.assertTrue(self.has(), 'still played on while it grows')
        # time passes: done by time before anything writes it, then written by the next page read
        self.t[0] += 6 * 3600 + 1
        with self.store.connect() as db:
            self.assertTrue(bang.builds_due(db, self.bid, self.t[0]))
        self.assertEqual(bang.island_of(self.row(), self.t[0])['level'], 2)
        self.sent.clear()
        page = bang.page(self.store, self.sid(self.a))
        self.assertEqual((page['isle']['level'], page['isle']['cap'], page['isle']['next'], page['isle']['cost']), (2, 40, 3, 60_000_000))
        self.assertEqual((self.row()['isle'], self.row()['isle_to']), (2, None))
        self.assertTrue(any(e.get('why') == 'view' for e in self.sent), 'the island repaints at its new level')
        self.assertTrue(self.rows("SELECT 1 FROM bang_log WHERE bang=? AND text LIKE '%lên cấp 2%'", (self.bid,)))
        for n, hours in ((3, 12), (4, 24), (5, 48)):
            self.op(self.b, 'isle', to=n, confirm=True)
            self.assertEqual(self.row()['isle_ready'] - self.t[0], hours * 3600)
            self.t[0] += hours * 3600 + 1
            self.store.transaction(lambda db: bang.finish_builds(db, self.bid, self.t[0]))
            self.assertEqual(self.row()['isle'], n)
        self.assertTrue(self.op(self.a, 'isle', to=5, confirm=True)['done']['again'])
        self.assertNotIn('next', bang.page(self.store, self.sid(self.a))['isle'])
        self.assertEqual([x['amount'] for x in self.ledger()], [-p for p in C.ISLE_PRICES])
        self.assertEqual(self.row()['isle_paid'], sum(C.ISLE_PRICES))

    def test_facility_levels_wait_for_the_island_and_nothing_built_is_lowered(self):
        self.set_fund(self.bid, 500_000_000)
        self.set_level(self.bid, C.HALL, 5)
        self.set_level(self.bid, 'kho', 4)
        self.refused_op(self.a, 'build', 'island', fac='kho', confirm=True)   # level 5 needs cấp 2 (no island at all here)
        fac = {f['id']: f for f in bang.page(self.store, self.sid(self.a))['facilities']}
        self.assertEqual((fac['kho']['next'], fac['kho']['isle']), (5, 2))
        self.op(self.a, 'build', fac='cong', confirm=True)                     # Cổng 1: no island needed
        self.set_isle(self.bid, 2)
        self.op(self.a, 'build', fac='kho', confirm=True)
        self.set_level(self.bid, 'tuong', 8)                                  # built before 21/10 on an island of cấp 1
        self.set_isle(self.bid, 1)
        page = bang.page(self.store, self.sid(self.a))
        self.assertEqual({f['id']: f['level'] for f in page['facilities']}['tuong'], 8, 'kept')
        self.refused_op(self.a, 'build', 'island', fac='tuong', confirm=True)  # level 9 needs cấp 4

    def test_the_old_bangs_hold_cap_1_for_free(self):
        """The migration: a bangs row written without the new columns (every bang before 21/10, and one a 2.4.64 process
        founds during the rollout) reads isle 1, 'grant'."""
        def run(db):
            db.execute("INSERT INTO bangs(id, name, key, emoji, color, leader, created, created_by) VALUES('b0000000old', 'Cũ', 'cu', '🐉', 'do', 's', 1, 's')")
        self.store.transaction(run)
        r = self.one("SELECT isle, isle_to, isle_how, isle_paid FROM bangs WHERE id='b0000000old'")
        self.assertEqual(r, dict(isle=1, isle_to=None, isle_how='grant', isle_paid=0))
        with self.store.connect() as db:
            self.assertTrue(bang.has_island(db, 'b0000000old'))
            db.execute("UPDATE bangs SET status='disbanded' WHERE id='b0000000old'")
            self.assertFalse(bang.has_island(db, 'b0000000old'), 'a disbanded bang has none')
            self.assertFalse(bang.has_island(db, 'b00000nope0'))

    def test_without_an_island_the_rest_of_the_bang_works(self):
        d = self.player(name='Hà')
        self.op(d, 'join', bang=self.bid)
        self.give(d, 1_000_000)
        self.op(d, 'checkin')
        self.set_fund(self.bid, 50_000_000)
        self.op(self.a, 'build', fac='den_vang', confirm=True)
        self.finish(self.bid, 'den_vang')
        self.op(self.a, 'gh_set', start=int((self.t[0] + 2 * 3600) // 300 * 300))
        self.set_points(d, 1000)
        self.op(d, 'buy', item='huy', rid='rid-0000001')
        self.assertFalse(self.has())

    def test_the_island_level_is_part_of_cap_bang(self):
        """Owner 21/10: the week's score is pets, công trình and cấp bang only; the island's level joins ⭐ Cấp bang
        (the Đại sảnh's level + the island's, × LEVEL_SCORE) and nothing else."""
        from game import bang_content as BC
        self.give(self.a, 5_000_000)
        week = bang.vn_week(self.t[0])
        with self.store.connect() as db:
            before = next(x for x in bang.standings(db, week) if x['bang'] == self.bid)
        self.assertEqual(before['island'], 0)
        self.op(self.a, 'isle', to=1, confirm=True)
        with self.store.connect() as db:
            after = next(x for x in bang.standings(db, week) if x['bang'] == self.bid)
            self.assertEqual(dict(bang.scores(db, week))[self.bid], after['score'])
        self.assertEqual((after['island'], after['level'] - before['level']), (1, BC.LEVEL_SCORE))
        self.assertEqual((after['pets'], after['build']), (before['pets'], before['build']), 'only ⭐ Cấp bang moves')
        self.assertEqual(after['score'] - before['score'], BC.LEVEL_SCORE * (100 + after['tuong']) // 100)


class Island(Base):
    """The provider, the HTTP answer and the live room before and after the purchase."""

    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.m, self.g = self.player(name='Minh'), self.player(name='Hà')
        self.op(self.m, 'join', bang=self.bid)
        self.op(self.a, 'invite', code=mr.ensure_person(self.store, self.sid(self.g))['code'])
        BI.register(None)
        BI._looked = False
        self.addCleanup(lambda: (BI.register(None), setattr(BI, '_looked', False)))
        self.p = SRC.PROVIDER

    def test_before_the_purchase_an_offer_nobody_on_it(self):
        self.assertEqual(self.p.access(self.store, self.sid(self.m), self.bid), dict(kind='member', role='thanh_vien', isle=0, cap=0))
        self.assertIsNone(self.p.access(self.store, self.sid(self.g), self.bid), 'a guest of a bang with no island: nobody')
        self.assertIsNone(self.p.view(self.store, self.bid))
        out = BI.get(self.store, self.m)
        self.assertIsNone(out['bang'])
        self.assertEqual((out['offer']['cost'], out['offer']['officer'], out['offer']['cap'], out['me']['kind']), (1_000_000, False, 30, 'member'))
        self.assertTrue(BI.get(self.store, self.a)['offer']['officer'])
        with self.assertRaises(BI.BangIslandError) as cm:
            BI.get(self.store, self.g, {'bang': self.bid})
        self.assertEqual(cm.exception.code, 'not_member')
        with self.assertRaises(BI.BangIslandError) as cm:
            BI.post(self.store, self.a, 'act', dict(bang=self.bid, facility='kho_bang', op='nang_cap'))
        self.assertEqual(cm.exception.code, 'no_island')
        run = asyncio.run
        self.assertEqual(run(self.p.access_live(AsyncDb(self.store), self.sid(self.m), self.bid))['isle'], 0)

    def test_after_the_purchase_the_island_its_level_and_its_cap(self):
        clock = patch.object(BI.time, 'time', lambda: self.t[0])
        clock.start()
        self.addCleanup(clock.stop)
        self.give(self.a, 40_000_000)
        self.op(self.a, 'isle', to=1, confirm=True)
        self.assertEqual(self.p.access(self.store, self.sid(self.g), self.bid), dict(kind='guest', role=None, isle=1, cap=30))
        out = BI.get(self.store, self.m)
        self.assertEqual((out['cap'], out['bang']['isle']['level'], out['bang']['isle']['state'], out['bang']['isle']['max']), (30, 1, 'done', 5))
        self.op(self.a, 'isle', to=2, confirm=True)
        isle = BI.get(self.store, self.m)['bang']['isle']
        self.assertEqual((isle['level'], isle['state'], isle['to'], isle['left']), (1, 'building', 2, 6 * 3600))
        self.t[0] += 6 * 3600 + 1
        out = BI.get(self.store, self.m)
        self.assertEqual((out['cap'], out['bang']['isle']['level'], out['bang']['isle']['state']), (40, 2, 'done'))
        self.assertEqual(self.p.access(self.store, self.sid(self.m), self.bid)['cap'], 40)

    def test_the_contract_checks_the_isle_view(self):
        v = BI.stub_view('b1')
        self.assertEqual(BI.isle_of(BI.validate_view(v))['cap'], BI.CAP, 'without isle: level 1, the default cap')
        for bad in (dict(level=0), dict(level=6), dict(level=2, max=1), dict(level=1, state='building'), dict(level=5, state='building', ready_at=10),
                    dict(level=1, cap=0), dict(level=1, cap=BI.CAP_MAX + 1), 'x'):
            with self.assertRaises(BI.ContractError, msg=bad):
                BI.validate_view(dict(v, isle=bad))
        ok = BI.validate_view(dict(v, isle=dict(level=3, max=5, state='building', ready_at=2e9, cap=50)))
        self.assertEqual(ok['isle'], dict(level=3, max=5, state='building', ready_at=2e9, cap=50))


class Arena(Base):
    """What is played on the island needs it: the pet arena (view, lineup, thử thách) and the Bang chiến pet."""

    def setUp(self):
        super().setUp()
        bang_pets.install()
        self.addCleanup(bang_pets.install)
        s = rich(50_000_000)
        for i, nick in enumerate(('Mít', 'Na')):
            s, _ = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed=('corgi', 'meo_mun')[i], coat=0, nick=nick, confirm=True)
        validate_state(s)
        self.a = self.player(name='Lan')
        mr._mutate(self.store, {self.sid(self.a): lambda x: (x.clear(), x.update(s), x.__setitem__('name', 'Lan'))})
        self.bid = self.found(self.a)
        self.m = self.player(name='Minh')
        mr._mutate(self.store, {self.sid(self.m): lambda x: (x.clear(), x.update(s), x.__setitem__('name', 'Minh'))})
        self.op(self.m, 'join', bang=self.bid)

    def arena(self, tok, op, **data):
        st = self.store.read(tok)[0]
        with patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            return A.act(self.store, tok, op, data, st, '1.1.1.1')

    def refused(self, tok, op, want, **data):
        with self.assertRaises(A.ArenaError) as cm:
            self.arena(tok, op, **data)
        self.assertEqual(cm.exception.code, want, str(cm.exception))
        return str(cm.exception)

    def pets(self, tok):
        return [p['id'] for p in A.candidates(self.store.read(tok)[0])]

    def test_locked_until_the_island_is_bought_then_open(self):
        v = self.arena(self.m, 'view')
        self.assertEqual((v['locked'], v['island']), ('island', dict(officer=False, cost=1_000_000)))
        self.assertEqual(self.arena(self.a, 'view')['island']['officer'], True)
        self.assertIn('Đảo bang', self.refused(self.m, 'lineup', 'no_island', pets=self.pets(self.m)[:1]))
        self.refused(self.m, 'npc', 'no_island', stage=0)
        self.refused(self.m, 'war_pick', 'no_island', pet=px.all_pets(self.store.read(self.m)[0])[0]['id'])
        with self.store.connect() as db:
            self.assertFalse(bang_pets.PROVIDER.can_pick(db, self.bid, self.sid(self.m)), 'the war provider refuses too')
            self.assertIsNotNone(bang_pets.PROVIDER.team_of(db, self.sid(self.m)), 'their page still names their bang')
        self.give(self.a, 1_000_000)
        self.op(self.a, 'isle', to=1, confirm=True)
        self.assertNotIn('locked', self.arena(self.m, 'view'))
        self.arena(self.m, 'lineup', pets=self.pets(self.m)[:1])
        self.arena(self.m, 'npc', stage=0)
        self.arena(self.m, 'war_pick', pet=px.all_pets(self.store.read(self.m)[0])[0]['id'])
        with self.store.connect() as db:
            self.assertTrue(bang_pets.PROVIDER.can_pick(db, self.bid, self.sid(self.m)))
        self.assertEqual(len(self.rows('SELECT 1 FROM pet_war_picks WHERE team_id=?', (self.bid,))), 1)

    def test_a_granted_bang_plays_at_once(self):
        self.set_isle(self.bid, 1)
        self.store.transaction(lambda db: db.execute("UPDATE bangs SET isle_how='grant' WHERE id=?", (self.bid,)))
        self.assertNotIn('locked', self.arena(self.m, 'view'))
        self.arena(self.m, 'lineup', pets=self.pets(self.m)[:1])


class BigGifts(Base):
    """21/10: no cap on the fund nor on one gift (only what the player has), Sổ ví rows of ≤ 10 M, points capped a day."""

    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan', wallet=900_000_000)
        self.bid = self.found(self.a)

    def bank(self, tok, amount):
        self.cmd(tok, 'jr_bk_open')
        mr._mutate(self.store, {self.sid(tok): lambda s: s['journey']['bank'].__setitem__('balance', amount)})   # deposits are ≤ 10 M each

    def test_one_huge_gift_from_wallet_then_bank(self):
        self.bank(self.a, 300_000_000)                       # 895 M cash, 300 M in the bank
        s = self.store.read(self.a)[0]
        cash = s['journey']['wallet']
        self.give(self.a, 1_000_000_000)                     # one gift of 1 tỷ: all the cash, then the bank
        s = self.store.read(self.a)[0]
        validate_state(s)
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 300_000_000 - (1_000_000_000 - cash)))
        rows = [h['amount'] for h in s['journey']['history'] if h['label'] == '⚔️ Góp quỹ bang']
        self.assertTrue(rows and all(-10_000_000 <= x < 0 for x in rows), 'Sổ ví rows of at most 10 M')
        self.assertEqual(self.one('SELECT fund, given FROM bangs WHERE id=?', (self.bid,)), dict(fund=1_000_000_000, given=1_000_000_000))
        self.assertEqual(self.mine(self.a)['points'], C.GIVE_PTS_DAY, 'the points of one day at most')
        self.assertEqual(s['journey']['bang']['last']['a'], 1_000_000_000)
        self.refused_cmd(self.a, 'jr_bang_give', 'not_enough', bang=self.bid, amount=300_000_000, confirm=True)   # more than is left

    def test_billions_over_several_gifts_no_cap(self):
        others = [self.player(name=f'P{i}', wallet=900_000_000) for i in range(2)]
        for t in others:
            self.op(t, 'join', bang=self.bid)
        for t in [self.a] + others:
            self.give(t, 500_000_000)
            self.give(t, 200_000_000)
        r = self.one('SELECT fund, given FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['fund'], r['given']), (2_100_000_000, 2_100_000_000))
        self.assertGreater(r['fund'], C.KHO_CAP[-1], 'beyond the old top cap (1 tỷ)')
        bal = [x['balance'] for x in self.rows("SELECT balance FROM bang_fund WHERE bang=? AND kind='give' ORDER BY balance", (self.bid,))]
        self.assertEqual(bal[-1], 2_100_000_000)
        self.t[0] += 86400                                   # a new day: points again (still capped)
        self.give(self.a, 100_000_000)
        self.assertEqual(self.mine(self.a)['earned'], 2 * C.GIVE_PTS_DAY)
        with self.store.connect() as db:
            sc = dict(bang.scores(db, bang.vn_week(self.t[0])))
        self.assertLess(sc[self.bid], 10**9, 'the weekly score stays a sane number')
        for t in [self.a] + others:
            validate_state(self.store.read(t)[0])
