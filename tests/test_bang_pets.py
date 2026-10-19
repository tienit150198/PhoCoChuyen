"""⚔️ Bang × 🛡️ Bang chiến pet (game/bang_pets.py): the bang tables are the pet war's team kind 'bang': a member's real
bang (never a hidden or disbanded one, never after leaving), any member fields one pet (first come, five a bang), the
🐾 Sân luyện pet level is the training bonus (capped by the war), a war between two real bangs, and the war's ladder
points joining the 👑 Bang mạnh nhất tuần score once the war is over (never sooner)."""
import json
import unittest
from unittest import mock

from game import bang
from game import bang_content as BC
from game import bang_pets
from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from tests.test_lb_titles import at
from tests.test_pet_arena import Store

WED = at(2026, 10, 21, 12)
SAT = at(2026, 10, 24, 21, 0)
END = SAT + PW.GAP + PW.SIZE * PW.DUEL_SECS + 1


class BangPets(Store):
    def setUp(self):
        super().setUp()
        bang_pets.install()               # another test may have unregistered 'bang'
        self.addCleanup(bang_pets.install)
        bang._VIEW.clear()
        self.addCleanup(bang._VIEW.clear)

    def mkbang(self, bid, name, toks, emoji='🐉', hidden=0, status='active'):
        sids = [self.sid(t) for t in toks]

        def run(db):
            db.execute('INSERT INTO bangs(id, name, key, emoji, color, leader, status, hidden, created, created_by) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?)', (bid, name, bid, emoji, 'do', sids[0], status, hidden, WED - 86400, sids[0]))
            for i, s in enumerate(sids):
                db.execute("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in',?,?)",
                           (bid, s, bang.pid_of(s), 'chu' if i == 0 else 'tv', WED - 86400))
        self.store.transaction(run)
        return bid

    def sql(self, q, args=()):
        self.store.transaction(lambda db: db.execute(q, args))

    def team(self, tok):
        with self.store.connect() as db:
            return bang_pets.PROVIDER.team_of(db, self.sid(tok))

    def pick(self, tok):
        return self.op(tok, 'war_pick', pet=px.all_pets(self.store.read(tok)[0])[0]['id'])

    def test_registered_on_import(self):
        self.assertIs(PW.PROVIDERS.get('bang'), bang_pets.PROVIDER)
        self.assertEqual(PW.TRAINING_MAX, BC.PET_WAR_MAX)
        import server  # noqa: F401 - the game server imports the adapter
        self.assertIn('bang', PW.PROVIDERS)

    def test_team_of_respects_membership_hidden_and_disbanded(self):
        a, b, c = (self.arena(('Mít',)) for _ in range(3))
        self.mkbang('b00000000a1', 'Rồng Đỏ', [a, b])
        self.assertEqual(self.team(a), ('b00000000a1', '🐉 Rồng Đỏ'))
        self.assertIsNone(self.team(c), 'not a member')
        with self.store.connect() as db:
            self.assertEqual(PW.team_of(db, self.sid(a)), ('bang', 'b00000000a1', '🐉 Rồng Đỏ', 'Bang'))
            self.assertEqual(bang_pets.PROVIDER.name(db, 'b00000000a1'), '🐉 Rồng Đỏ')
            self.assertTrue(bang_pets.PROVIDER.can_pick(db, 'b00000000a1', self.sid(b)))
            self.assertFalse(bang_pets.PROVIDER.can_pick(db, 'b00000000a1', self.sid(c)))
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(b),))
        self.assertIsNone(self.team(b), 'left the bang')
        self.sql('UPDATE bangs SET hidden=1 WHERE id=?', ('b00000000a1',))
        self.assertIsNone(self.team(a), 'hidden by an operator')
        self.sql("UPDATE bangs SET hidden=0, status='disbanded' WHERE id=?", ('b00000000a1',))
        self.assertIsNone(self.team(a), 'disbanded')

    def test_training_ground_level(self):
        a = self.arena(('Mít',))
        bid = self.mkbang('b00000000b1', 'Hổ Xám', [a])
        with self.store.connect() as db:
            self.assertEqual(PW.training_bonus(db, 'bang', bid), 0)
        self.sql("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'san_pet', 3)", (bid,))
        with self.store.connect() as db:
            self.assertEqual(PW.training_bonus(db, 'bang', bid), 3)
            self.assertEqual(bang_pets.PROVIDER.facility(db, bid, 'kho'), 0, 'only the training ground')
        # a build whose time is up counts before anybody opened the bang's page
        self.sql("UPDATE bang_facilities SET target=4, started=?, ready_at=? WHERE bang=? AND fac='san_pet'", (WED - 10, WED - 1, bid))
        with mock.patch.object(bang, 'now', return_value=WED):
            with self.store.connect() as db:
                self.assertEqual(PW.training_bonus(db, 'bang', bid), 4)
        with mock.patch.object(bang, 'now', return_value=WED - 5):
            with self.store.connect() as db:
                self.assertEqual(PW.training_bonus(db, 'bang', bid), 3, 'still building')
        self.sql("UPDATE bang_facilities SET level=9, target=NULL WHERE bang=? AND fac='san_pet'", (bid,))
        with self.store.connect() as db:
            self.assertEqual(PW.training_bonus(db, 'bang', bid), PW.TRAINING_MAX)
        self.assertIn('+5%', BC.perk('san_pet', 9))
        self.assertIn('+2%', BC.perk('san_pet', 2))

    def test_war_between_two_real_bangs_and_the_weekly_score(self):
        toks = [self.arena(('Mít',), rank=r) for r in (3, 4, 5, 3, 4, 6, 2)]
        red = self.mkbang('b00000000c1', 'Rồng Đỏ', toks[:3])
        blue = self.mkbang('b00000000c2', 'Cá Xanh', toks[3:6], emoji='🐟')
        outsider = toks[6]
        self.sql("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'san_pet', 2)", (blue,))
        with mock.patch.object(A, 'now', return_value=WED):
            for t in toks[:6]:
                self.assertIn('ra trận cho', self.pick(t)['message'])
            with self.assertRaises(A.ArenaError) as cm:
                self.pick(outsider)
            self.assertEqual(cm.exception.code, 'no_team')
            v = self.op(toks[0], 'war')
            self.assertEqual(v['team'], dict(kind='bang', id=red, name='🐉 Rồng Đỏ', label='Bang'))
            self.assertEqual(len(v['picks']), 3)
            self.assertEqual(self.op(toks[3], 'view')['war']['team']['name'], '🐟 Cá Xanh')
            self.assertIsNone(self.op(outsider, 'war')['team'])
        # one of the red fighters leaves before the lock: their pick no longer counts
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(toks[2]),))
        self.assertTrue(PW.run_due(self.store, SAT - 5 * 60))
        with self.store.connect() as db:
            war = dict(db.execute('SELECT * FROM pet_war').fetchone())
            data = json.loads(war['data'])
            teams = {x['id']: x for x in data['teams']}
            self.assertEqual((war['status'], war['n']), ('done', 2))
            self.assertEqual(teams[red]['n'], 2)
            self.assertEqual(teams[blue]['n'], 3)
            self.assertEqual(teams[blue]['tb'], 2)
            self.assertEqual(teams[red]['name'], '🐉 Rồng Đỏ')
            week = war['week']
            # the bang board: nothing from the war until it is over (the results are fixed already)
            self.assertEqual(bang.war_scores(db, week, SAT + 1), {})
            ws = bang.war_scores(db, week, END)
        champ = war['champ_id']
        self.assertIn(champ, (red, blue))
        self.assertEqual(ws[champ], (PW.PTS_WIN + PW.PTS_CHAMP) * BC.PET_WAR_SCORE)
        self.assertNotIn(red if champ == blue else blue, ws, 'the loser of the only match scores nothing')
        with mock.patch.object(bang, 'now', return_value=END):
            with self.store.connect() as db:
                st = {x['bang']: x for x in bang.standings(db, week)}
        # 👑 (owner 21/10): the war is in 🐾 Pets (with the bang's chiến lực), blue's Sân luyện pet 2 in 🏗️ Công trình
        self.assertEqual(st[champ]['war'], ws[champ])
        self.assertEqual(st[champ]['pets'], ws[champ] + st[champ]['power'] // BC.POWER_DIV)
        self.assertEqual(st[blue]['build'], BC.FAC_SCORE * 2)
        self.assertEqual(st[champ]['score'], st[champ]['pets'] + st[champ]['build'] + st[champ]['level'])
        with mock.patch.object(A, 'now', return_value=END):
            v = self.op(toks[3], 'war')
            self.assertEqual(v['phase'], 'done')
            self.assertEqual(v['ladder'][0]['id'], champ)
            self.assertEqual(v['champ'], war['champ_name'])


if __name__ == '__main__':
    unittest.main()
