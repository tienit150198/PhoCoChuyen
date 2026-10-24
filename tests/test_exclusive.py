"""🌧️ Danh hiệu độc nhất (game/exclusive.py, owner 24/10: "cho mnt2410 cái khung mưa rơi đi, xong rồi cái danh hiệu
Cuồng Vũ Tán Tiên. làm độc nhất nhé"): only the account named in the table holds it (looked up by username, made before
the grant), nothing of it lives in a save, only its holder may wear the frame (jr_frame), the live service sends it
for its holder only and first, and it shows on the boards, Phố nghề, the street's and the town's name tags. Plus the
client's copy of the table (public/js/v4/exclusive.js) and a render smoke test of the frame, chips and bubbles."""
import asyncio
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import accounts, exclusive, social
from game import journey as jr
from game.engine import GameError, apply_action, validate_state
from game import leaderboard as lb
from tests.test_leaderboard import FORMAT, Base, crafted
from tests.test_lb_titles import story_state

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / 'public/js/v4/exclusive.js'
XID = 'ex_cuong_vu'


class Table(unittest.TestCase):
    def test_the_grant(self):
        x = exclusive.EXCLUSIVE[XID]
        self.assertEqual((x['username'], x['name'], x['frame'], x['emoji']), ('mnt2410', 'Cuồng Vũ Tán Tiên', 'Mưa rơi', '🌧️'))
        for xid, x in exclusive.EXCLUSIVE.items():
            self.assertRegex(xid, r'^ex_[a-z0-9_]{1,40}$')
            self.assertRegex(xid, jr.HF_PICK_RE)
            self.assertRegex(x['username'], accounts.USERNAME)
            self.assertRegex(x['before'], r'^\d{4}-\d\d-\d\d$')
        self.assertEqual(len({x['username'] + x['name'] for x in exclusive.EXCLUSIVE.values()}), len(exclusive.EXCLUSIVE))

    def test_from_rows(self):
        ok = dict(sid='s-mua', username='mnt2410', created_at='2026-09-01 10:00:00')
        self.assertEqual(exclusive.from_rows([ok]), {'s-mua': [XID]})
        self.assertEqual(exclusive.from_rows([dict(ok, username='MNT2410')]), {'s-mua': [XID]})
        self.assertEqual(exclusive.from_rows([dict(ok, created_at='2026-10-25 00:00:00')]), {}, 'a username taken again later')
        self.assertEqual(exclusive.from_rows([dict(ok, created_at=None)]), {})
        self.assertEqual(exclusive.from_rows([dict(ok, username='mnt2411')]), {})
        self.assertEqual(exclusive.from_rows([]), {})
        self.assertEqual(exclusive.text_of(['lb_all_1', XID]), '🌧️ Cuồng Vũ Tán Tiên')
        self.assertIsNone(exclusive.text_of(['lb_all_1', 'ex_nope', 'hf_off']))
        self.assertIsNone(exclusive.title('ex_nope'))
        row = exclusive.mark({}, 's-mua', {'s-mua': [XID]})
        self.assertEqual(row['ex'], dict(id=XID, emoji='🌧️', name='Cuồng Vũ Tán Tiên'))
        self.assertEqual(exclusive.mark({}, 's-x', {'s-mua': [XID]}), {})
        self.assertEqual(exclusive.mark({}, None, {'s-mua': [XID]}), {})

    def test_the_client_mirrors_it(self):
        src = JS.read_text(encoding='utf-8')
        block = src[src.index('export const EX={'):src.index('};', src.index('export const EX={'))]
        rows = dict(re.findall(r"(ex_[a-z0-9_]+):\{(.*?)\}", block))
        self.assertEqual(set(rows), set(exclusive.EXCLUSIVE))
        for xid, x in exclusive.EXCLUSIVE.items():
            self.assertIn(f"emoji:'{x['emoji']}'", rows[xid])
            self.assertIn(f"name:'{x['name']}'", rows[xid])
            self.assertIn(f"frame:'{x['frame']}'", rows[xid])


class Frame(unittest.TestCase):
    """jr_frame: the save may carry the id (the holder's own save validates); the storage hook decides who."""
    def test_the_pure_action_takes_it_and_back(self):
        s = story_state()
        s2, r = apply_action(s, None, 'jr_frame', dict(id=XID))
        self.assertEqual(s2['journey']['hf_pick'], XID)
        validate_state(s2)
        s3, _ = apply_action(s2, None, 'jr_frame', dict(id='auto'))
        self.assertNotIn('hf_pick', s3['journey'])
        for bad in ('ex_', 'ex_Bad', 'EX_CUONG_VU', 'ex_' + 'x' * 41):
            with self.assertRaises(GameError, msg=bad):
                apply_action(s, None, 'jr_frame', dict(id=bad))


class Live(Base):
    """The real store (PostgreSQL): accounts, the command path, the boards, Phố nghề."""
    def mua(self, name='mnt2410', created='2026-09-30 08:00:00', state=None, display='Mưa'):
        """A registered account `name` (made at `created`, UTC), its save imported first; its token."""
        token, _, _ = self.store.session()
        self.cmd(token, 'import_save', {'save': {'format': FORMAT, 'state': state or story_state()}})
        token = accounts.register(self.store, token, dict(username=name, password='mat-khau-dai-1', confirm='mat-khau-dai-1', display=display))['token']
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET created_at=? WHERE username=?', (created, name))
            db.commit()
        exclusive.clear_cache()
        return token

    def setUp(self):
        super().setUp()
        exclusive.clear_cache()

    def tearDown(self):
        exclusive.clear_cache()
        super().tearDown()

    def test_only_her_account_holds_it(self):
        her = self.mua()
        other = self.mua('mnt2410x')
        guest, _, _ = self.store.session()
        self.assertEqual(exclusive.holders(self.store), {self.sid(her): [XID]})
        self.assertEqual([t['id'] for t in exclusive.held(self.store, self.sid(her))], [XID])
        self.assertEqual(exclusive.held(self.store, self.sid(other)), [])
        self.assertEqual(exclusive.held(self.store, self.sid(guest)), [])
        self.assertEqual(exclusive.held(self.store, None), [])

    def test_a_username_taken_again_after_the_grant_gets_nothing(self):
        self.mua(created='2026-10-25 00:00:01')
        self.assertEqual(exclusive.holders(self.store), {})

    def test_jr_frame_her_only(self):
        her, other = self.mua(), self.mua('nguoikhac')
        guest, _, _ = self.store.session()
        self.cmd(guest, 'import_save', {'save': {'format': FORMAT, 'state': story_state()}})
        r = self.cmd(her, 'jr_frame', {'id': XID})
        self.assertIn('Đã đổi khung', r['result']['message'])
        self.assertEqual(self.store.read(her)[0]['journey']['hf_pick'], XID)
        for tok in (other, guest):
            with self.assertRaises(GameError) as e:
                self.cmd(tok, 'jr_frame', {'id': XID})
            self.assertEqual(e.exception.code, 'not_yours')
            self.assertNotIn('hf_pick', self.store.read(tok)[0]['journey'])
        self.cmd(other, 'jr_frame', {'id': 'k_01'})   # every other frame still works for them
        self.cmd(her, 'jr_frame', {'id': 'off'})      # unequipped, then worn again, then automatic
        self.assertEqual(self.store.read(her)[0]['journey']['hf_pick'], 'off')
        self.cmd(her, 'jr_frame', {'id': XID})
        self.cmd(her, 'jr_frame', {'id': 'auto'})
        self.assertNotIn('hf_pick', self.store.read(her)[0]['journey'])
        self.assertNotIn('ex_', json.dumps(self.store.read(her)[0]))   # nothing of it in her save but a choice she made

    def test_the_boards_and_phos_nghe(self):
        her = self.mua(state=crafted('Mưa', grocery=(250, 4, 6)))
        other = self.mua('nguoikhac', state=crafted('Lan', grocery=(150, 3, 4)), display='Lan')
        rows = lb.view(self.store, 'all', token=other)['rows']
        mine = {r['name']: r for r in rows}
        self.assertEqual(mine['Mưa'].get('ex'), dict(id=XID, emoji='🌧️', name='Cuồng Vũ Tán Tiên'))
        self.assertNotIn('ex', mine['Lan'])
        got = social._public_profile(dict(pid='p', sid=self.sid(her), name='Mưa', bio='', avatar='', shop='{}', served=0, seen=0),
                                     ranks={self.sid(her): [dict(exclusive.title(XID), ex=XID)]})
        self.assertEqual(got['rank'], dict(emoji='🌧️', name='Cuồng Vũ Tán Tiên', ex=XID))


class LiveService(unittest.TestCase):
    def test_first_in_tt_for_her_only(self):
        from live import honours

        class DB:
            async def fetch(self, sql, args=()):
                if 'FROM accounts' in sql:
                    self.args = args
                    return [dict(sid='sid-a', username='mnt2410', created_at='2026-09-01 00:00:00')]
                if 'lb_weekly' in sql:
                    return [dict(sid='sid-a', board='all', rank=1), dict(sid='sid-b', board='wealth', rank=2)]
                if 'FROM profiles' in sql:
                    return [dict(pid=p, sid='sid-' + p, ti=None, hf=DB.hf.get(p)) for p in args]
                return []
            hf = {}

        app = type('App', (), dict(db=DB(), by_name={}, hub=None))()
        h = honours.of_app(app)
        got = asyncio.run(h.of(['a', 'b']))
        self.assertEqual(got['a'], [XID, 'lb_all_1'])
        self.assertEqual(got['b'], ['lb_wealth_2'])
        self.assertIn('mnt2410', app.db.args)
        DB.hf = {'a': 'off', 'b': XID}   # her frame put away; somebody else's edited save asks for hers
        honours.on_notify(app, {'op': 'honours', 'pid': 'a'})
        honours.on_notify(app, {'op': 'honours', 'pid': 'b'})
        got = asyncio.run(h.of(['a', 'b']))
        self.assertEqual(got['a'], ['hf_off', XID, 'lb_all_1'])
        self.assertEqual(got['b'], ['lb_wealth_2'], 'never sent for anybody else')

    def test_street_name_tag_leads_with_it(self):
        from live.street import StreetFeature
        f = StreetFeature.__new__(StreetFeature)
        f.app = type('App', (), dict(by_name={}))()
        f.lb = {'sid-a': '👑 Trùm cuối của phố'}
        p = type('P', (), dict(pid='a', sid='sid-a'))()
        self.assertEqual(f.title_of(p, None, None, None, [XID, 'lb_all_1']), '🌧️ Cuồng Vũ Tán Tiên')
        self.assertEqual(f.title_of(p, None, None, None, ['lb_all_1']), '👑 Trùm cuối của phố')

    def test_town_walker_carries_tt(self):
        from live.town import Walker
        pl = type('P', (), dict(pid='a', name='Mưa', fc=''))()
        w = Walker(pl, {}, 'female', (1.0, 2.0), 'down')
        self.assertNotIn('tt', w.public())
        w.tt = [XID]
        self.assertEqual(w.public()['tt'], [XID])


@unittest.skipUnless(shutil.which('node'), 'node')
class Client(unittest.TestCase):
    def test_render_smoke(self):
        out = subprocess.run(['node', str(ROOT / 'tests/exclusive_client.mjs')], capture_output=True, text=True, encoding='utf-8',
                             timeout=120, cwd=ROOT)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('exclusive client ok', out.stdout)


if __name__ == '__main__':
    unittest.main()
