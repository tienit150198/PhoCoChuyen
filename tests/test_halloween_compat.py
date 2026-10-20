"""🎃 Rollback of Lễ hội Ma Phố (game/halloween.py, SCHEMA_VERSION 80) to 2.4.71 (fe504023, live): its startup on a database
with the season's rows (hw_players, hw_log) runs no DDL and keeps them; a 'hween' live_effects row waiting for a save stays
pending there (a kind 2.4.71 does not pay) and is paid once by this build afterwards; the saves of a player who holds and
wears the season's 🎨 Phong cách title and colour, holds its pet piece and took a xu bag validate, migrate and take a command
on 2.4.71, as the stored text holds them. No save key was added."""
import json

from game import pg_schema
from game import spend as sp
from game import spend_content as SC
from game.engine import validate_state
from tests.helpers import unknown_out
from tests.test_halloween import HWBase
from tests.test_town_fair_compat import SAVES, STARTUP, Rollback as _Old

TABLES = ('hw_players', 'hw_log', 'live_effects')
FX = '''import json,sys
from game.storage import Store
from game import live_effects
store=Store(sys.argv[1])
tok=sys.argv[2]
before=store.read(tok)[1]
live_effects.on_load(store,tok,store.read(tok)[0])
with store.connect() as db:
    st=[r['status'] for r in db.execute("SELECT status FROM live_effects WHERE kind='hween' ORDER BY id").fetchall()]
print(json.dumps([st,store.read(tok)[1]==before]))
store.close_pool()
'''


class Rollback(HWBase):
    old_tree = _Old.old_tree
    run_old = _Old.run_old

    def season(self):
        """Two players: one checked in, knocked, exchanged (title worn, colour, pet piece, a xu bag: all paid); the other
        with an exchange still waiting in live_effects (never loaded)."""
        a, b = self.user('rb_hw_a', wallet=1000), self.user('rb_hw_b')
        self.post(a, 'checkin')
        self.post(b, 'checkin')
        self.post(a, 'knock', to=self.view(a)['knock']['doors'][0]['pid'])
        self.give(a, 500)
        for item in ('t_hw_san_bi_ngo', 'c_hw_bi_ngo', 'pet_vong_keo', 'xu'):
            self.post(a, 'buy', item=item)
        self.load(a)
        self.cmd(a, 'jr_spend_wear', kind='title', id='t_hw_san_bi_ngo')
        self.cmd(a, 'jr_spend_wear', kind='color', id='c_hw_bi_ngo')
        self.give(b, 100)
        self.post(b, 'buy', item='f_hw_doi')   # waiting: b's save has not loaded since
        return a, b

    def test_2_4_71_starts_on_schema_80_without_ddl(self):
        self.season()
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
            idx = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'hw_%'").fetchall())
        self.assertTrue(all(before.values()), before)
        v, n = self.run_old(STARTUP, str(self.store.path), ','.join(TABLES))
        self.assertEqual(int(v), pg_schema.SCHEMA_VERSION, 'the version is never lowered')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 80)
        self.assertEqual(n, before, 'rows kept')
        with self.store.connect() as db:
            idx2 = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'hw_%'").fetchall())
        self.assertEqual(idx2, idx)

    def test_a_pending_exchange_waits_on_2_4_71_and_is_paid_once_here(self):
        a, b = self.season()
        statuses, same = self.run_old(FX, str(self.store.path), b)
        self.assertTrue(same, 'the old build does not touch the save')
        self.assertIn('pending', statuses)
        self.load(b)
        self.assertEqual(self.own(b), {'f_hw_doi': SC.PERMANENT})
        self.load(b)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE sid=? AND kind='hween' AND status='applied'",
                                        (self.sid(b),)).fetchone()['n'], 1)

    def test_saves_of_the_season_load_on_2_4_71(self):
        a, b = self.season()
        saves = [self.state(t) for t in (a, b)]
        for s in saves:
            validate_state(s)
        self.assertEqual(self.own(a), {'t_hw_san_bi_ngo': SC.PERMANENT, 'c_hw_bi_ngo': SC.PERMANENT})
        self.assertEqual(sp.style_now(saves[0])['t'], 't_hw_san_bi_ngo')
        got = self.run_old(SAVES, stdin=json.dumps([unknown_out(x) for x in saves]))
        for (before, after, keys, worn), s in zip(got, saves):
            self.assertEqual(before, after, 'wallet, bank and the style items kept as they are')
            self.assertLessEqual(set(s), set(keys), 'no save key 2.4.71 does not know')
            self.assertNotIn('t', worn, '2.4.71 does not show a title it does not know')
            self.assertNotIn('c', worn, '2.4.71 does not show a colour it does not know')


del _Old   # not collected twice from here
