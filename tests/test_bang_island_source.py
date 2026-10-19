"""⚔️ Bang → ⚔️ Đảo bang (game/bang_island_source.py): the real bangs behind the island's contract: the facility ids
mapped (each with its own top level, scaled looks), builds and builds finished by time, members (roles mapped), guests
(an open invitation), strangers, a hidden bang (members only), a disbanded one (no island, the room closes), the live
service's access_live, the notices game/bang.py sends, and ⬆️ Nâng cấp running the bang's own build after a confirm."""
import asyncio
import os
import unittest
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import bang_island as BI
from game import bang_island_source as SRC
from game import marriage as mr
from tests.test_bang import Base


class AsyncDb:
    """live.db's shape (await fetchrow(sql, args), ? placeholders) over the test store."""

    def __init__(self, store):
        self.store = store

    async def fetchrow(self, sql, args=()):
        with self.store.connect() as db:
            r = db.execute(sql, args).fetchone()
        return dict(r) if r else None


class Source(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.set_isle(self.bid)            # 🏝️ bought (tests/test_bang_island_buy.py: before that)
        self.p = SRC.PROVIDER
        BI.register(None)
        BI._looked = False
        self.addCleanup(lambda: (BI.register(None), setattr(BI, '_looked', False)))

    def view(self):
        return BI.validate_view(self.p.view(self.store, self.bid))

    def fac(self, isle_id):
        return next(f for f in BI.island_view(self.view(), self.t[0])['facilities'] if f['id'] == isle_id)

    def isle(self, why=None):
        return [e for e in self.sent if e.get('op') == 'bang_island' and (why is None or e.get('why') == why)]

    def test_discovered_and_on(self):
        self.assertIs(BI.provider(), SRC.PROVIDER)
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            self.assertTrue(BI.enabled())

    def test_view_maps_the_facilities(self):
        v = self.view()
        self.assertEqual([f['id'] for f in v['facilities']], list(BI.FACILITY_IDS))
        self.assertEqual(set(SRC.FAC), set(C.FACILITIES), 'every Bang facility has its island slot')
        self.assertEqual(set(SRC.FAC.values()), set(BI.FACILITY_IDS))
        row = self.one('SELECT name, emoji, color FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((v['bang_id'], v['name'], v['emoji'], v['color']), (self.bid, row['name'], row['emoji'], C.COLORS[row['color']][1].lower()))
        f = {x['id']: x for x in v['facilities']}
        self.assertEqual((f['dai_sanh']['level'], f['dai_sanh']['max']), (1, 5))
        self.assertEqual(v['level'], 1)
        self.assertEqual((f['kho_bang']['level'], f['kho_bang']['max']), (0, 10))
        self.set_level(self.bid, 'xuong_may', 4)
        self.set_level(self.bid, 'tuong', 4)
        xm, tb = self.fac('xuong_may'), self.fac('tuong_bang')
        self.assertEqual((xm['level'], xm['max'], xm['band'], xm['next']), (4, 5, 3, 5), 'a 5-level facility: gold at 4')
        self.assertEqual((tb['band'], tb['next']), (2, 5), 'a 10-level facility: stone at 4')
        self.set_level(self.bid, 'xuong_may', 5)
        self.assertIsNone(self.fac('xuong_may')['next'])
        self.assertIn('Cấp 5', self.fac('tuong_bang')['note'])

    def test_a_build_and_its_end_by_time(self):
        self.give(self.a, 10_000_000)
        self.op(self.a, 'build', fac='kho', confirm=True)
        self.assertTrue(self.isle('view'), 'the island repaints when a build starts')
        k = self.fac('kho_bang')
        self.assertEqual((k['state'], k['level'], k['to']), ('building', 0, 1))
        self.assertGreater(k['left'], 0)
        r = self.one("SELECT ready_at FROM bang_facilities WHERE bang=? AND fac='kho'", (self.bid,))
        self.t[0] = float(r['ready_at']) + 1
        k = self.fac('kho_bang')
        self.assertEqual((k['state'], k['level']), ('done', 1), 'done once its time is up, before finish_builds')
        self.sent.clear()
        self.store.transaction(lambda db: bang.finish_builds(db, self.bid, self.t[0]))
        self.assertTrue(self.isle('view'))

    def test_members_guests_strangers_hidden_disbanded(self):
        b, c, d = self.player(name='Minh'), self.player(name='Tú'), self.player(name='Hà')
        self.op(b, 'join', bang=self.bid)
        self.assertEqual(self.p.bang_of(self.store, self.sid(b)), self.bid)
        self.assertEqual(self.p.access(self.store, self.sid(self.a), self.bid), dict(kind='member', role='bang_chu', isle=1, cap=30))
        self.assertEqual(self.p.access(self.store, self.sid(b), self.bid), dict(kind='member', role='thanh_vien', isle=1, cap=30))
        self.assertIsNone(self.p.access(self.store, self.sid(c), self.bid))
        self.assertIsNone(self.p.bang_of(self.store, self.sid(c)))
        self.assertTrue(self.isle('join'))
        # roles
        self.op(self.a, 'role', pid=self.pid(b), role='pho')
        self.assertEqual(self.p.access(self.store, self.sid(b), self.bid)['role'], 'pho_bang')
        self.assertTrue(any(e.get('sid') == self.sid(b) for e in self.isle('role')))
        # a guest: an open invitation
        self.op(self.a, 'invite', code=mr.ensure_person(self.store, self.sid(d))['code'])
        self.assertEqual(self.p.access(self.store, self.sid(d), self.bid), dict(kind='guest', role=None, isle=1, cap=30))
        self.assertTrue(any(e.get('sid') == self.sid(d) for e in self.isle('guest')))
        db = AsyncDb(self.store)
        run = asyncio.run
        self.assertEqual(run(self.p.access_live(db, self.sid(d), self.bid)), dict(kind='guest', role=None, isle=1, cap=30))
        self.assertEqual(run(self.p.access_live(db, self.sid(b), self.bid)), dict(kind='member', role='pho_bang', isle=1, cap=30))
        self.assertIsNone(run(self.p.access_live(db, self.sid(c), self.bid)))
        self.op(d, 'decline', bang=self.bid)
        self.assertIsNone(self.p.access(self.store, self.sid(d), self.bid))
        # leaving and being asked to leave
        self.op(c, 'join', bang=self.bid)
        self.op(c, 'leave', confirm=True)
        self.assertTrue(any(e.get('sid') == self.sid(c) for e in self.isle('left')))
        self.op(c, 'join', bang=self.bid)
        self.op(self.a, 'kick', pid=self.pid(c), confirm=True)
        self.assertTrue(any(e.get('sid') == self.sid(c) for e in self.isle('kicked')))
        self.assertIsNone(self.p.access(self.store, self.sid(c), self.bid))
        # hidden by an operator: members keep their island, guests do not
        self.op(self.a, 'invite', code=mr.ensure_person(self.store, self.sid(d))['code'])
        bang.admin_act(self.store, 'admin', dict(op='hide', id=self.bid))
        self.assertEqual(self.p.access(self.store, self.sid(b), self.bid)['kind'], 'member')
        self.assertIsNone(self.p.access(self.store, self.sid(d), self.bid))
        self.assertIsNotNone(self.p.view(self.store, self.bid))
        bang.admin_act(self.store, 'admin', dict(op='show', id=self.bid))
        # disbanded: no island, the room closes
        self.sent.clear()
        name = self.one('SELECT name FROM bangs WHERE id=?', (self.bid,))['name']
        self.op(self.a, 'disband', confirm=True, name=name)
        self.assertEqual(self.isle('disband'), [dict(op='bang_island', why='disband', bang=self.bid)])
        self.assertIsNone(self.p.view(self.store, self.bid))
        self.assertIsNone(self.p.access(self.store, self.sid(b), self.bid))
        self.assertIsNone(self.p.bang_of(self.store, self.sid(self.a)))

    def test_upgrade_button_runs_the_bang_build_after_a_confirm(self):
        b, c = self.player(name='Minh'), self.player(name='Tú')
        self.op(b, 'join', bang=self.bid)
        self.give(self.a, 10_000_000)
        fund = lambda: self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund']
        ask = self.p.act(self.store, self.sid(self.a), self.bid, 'kho_bang', 'nang_cap', {})
        self.assertIn('2.000.000', ask['confirm']['label'])
        self.assertIn('Kho bang', ask['confirm']['title'])
        self.assertEqual(fund(), 10_000_000, 'asking writes nothing')
        out = self.p.act(self.store, self.sid(self.a), self.bid, 'kho_bang', 'nang_cap', {'confirm': True})
        self.assertIn('Bắt đầu xây', out['message'])
        self.assertEqual(fund(), 8_000_000)
        self.assertEqual(self.fac('kho_bang')['state'], 'building')
        with self.assertRaises(BI.BangIslandError) as cm:     # the bang's own rules: one build at a time here
            self.p.act(self.store, self.sid(self.a), self.bid, 'cong_bang', 'nang_cap', {})
        self.assertEqual(cm.exception.code, 'slots')
        with self.assertRaises(BI.BangIslandError) as cm:     # Thành viên cannot build
            self.p.act(self.store, self.sid(b), self.bid, 'cong_bang', 'nang_cap', {'confirm': True})
        self.assertEqual(cm.exception.code, 'role')
        with self.assertRaises(BI.BangIslandError) as cm:     # not in this bang
            self.p.act(self.store, self.sid(c), self.bid, 'dai_sanh', 'nang_cap', {'confirm': True})
        self.assertEqual(cm.exception.status, 403)
        self.assertIn('Bang', self.p.act(self.store, self.sid(b), self.bid, 'kho_bang', 'gop_quy', {})['message'])

    def test_http_answer_through_the_contract(self):
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            out = BI.get(self.store, self.a, {})
            self.assertEqual(out['bang']['id'], self.bid)
            self.assertEqual(out['me'], dict(kind='member', role='bang_chu', role_name='Bang chủ'))
            self.give(self.a, 10_000_000)
            done = BI.post(self.store, self.a, 'act', dict(bang=self.bid, facility='kho_bang', op='nang_cap'))
            self.assertIn('confirm', done['done'])
            done = BI.post(self.store, self.a, 'act', dict(bang=self.bid, facility='kho_bang', op='nang_cap', data={'confirm': True}))
            kho = next(f for f in done['bang']['facilities'] if f['id'] == 'kho_bang')
            self.assertEqual(kho['state'], 'building')
            stranger = self.player(name='Lạ')
            self.assertIsNone(BI.get(self.store, stranger, {})['bang'])
            with self.assertRaises(BI.BangIslandError) as cm:
                BI.get(self.store, stranger, {'bang': self.bid})
            self.assertEqual(cm.exception.status, 403)


if __name__ == '__main__':
    unittest.main()
