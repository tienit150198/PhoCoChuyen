"""📣 Báo cả phố khi lên SS+ (owner 23/10 "cho mọi người thông báo / ẩn thông tin nếu nâng hạng SS trở lên",
game/forge_news.py): a wing, a pet, a pet's clothes or gear reaching rank SS or more through a fusion or a Cường hóa puts
ONE line on the street's ticker (news), once a piece and rank; a ⚡ Cường hóa nhanh run puts one line, its highest rank
("(và 1 đôi SS)" for the rest); below SS nothing; 🕶️ Ẩn tên (settings forgeAnon, an optional journey key) shows
lux.ANON_NAME instead of the account's name, the pets' old line included."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import accounts, lux
from game import forge_news as fz
from game import pet_tiers as px
from game import pet_wardrobe as pw
from game import wings as W
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act
from tests.test_forge_auto import X, Wg, always, gear, pets, wings

REG = dict(username='Bo.Cuong_5', password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Bơ Cường')


def no_myth():
    """No thần thú offer (it would stop a pets' run early)."""
    return mock.patch.object(pw, 'MYTH_BP', {})


class Marks(unittest.TestCase):
    """What the commands mark (result['fz']): the line's piece, the rest counted; nothing below SS."""

    def test_wing_fusion_marks_ss_and_up_only(self):
        s = wings(10**9, ('buom', 3, 3), ('rong', 4, 3))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse', wings=[x['id'] for x in Wg(s)['own'][:3]], confirm=True)
        self.assertTrue(r['fuse']['ok'])
        self.assertNotIn('fz', r, 'A → S: no line')
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse', wings=[x['id'] for x in Wg(s)['own'] if x['k'] == 'rong'], confirm=True)
        self.assertEqual(r['fz'], dict(k='wing', id=r['fuse']['main'], r=5, n=W.INDEX['rong']['name'], lg=False, more=[]))
        self.assertEqual(fz.text('wing', 'Bơ', r['fz']), f'🪽 Bơ vừa cường hóa {W.INDEX["rong"]["name"]} lên hạng SS!')
        with always(W, 9999):
            s2 = wings(10**9, ('buom', 4, 3))
            s2, r = act(s2, 'jr_pet_wing_fuse', wings=[x['id'] for x in Wg(s2)['own']], confirm=True)
        self.assertFalse(r['fuse']['ok'])
        self.assertNotIn('fz', r, 'a miss: no line')

    def test_wing_auto_one_mark_the_highest(self):
        s = wings(10**9, ('buom', 4, 12))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual(r['auto']['n'], 5)
        self.assertEqual((r['fz']['r'], r['fz']['more']), (6, [['SS', 1]]))
        self.assertTrue(fz.text('wing', 'Bơ', r['fz']).endswith('lên hạng SSS (và 1 đôi SS)!'))
        s = wings(10**9, ('buom', 6, 3))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual(r['fz']['r'], 7)
        self.assertEqual(fz.text('wing', 'Bơ', r['fz']), f'🌟 Bơ vừa cường hóa {r["fz"]["n"]} lên HUYỀN THOẠI!')
        s = wings(10**9, ('buom', 0, 9))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertGreater(r['auto']['ok'], 0)
        self.assertNotIn('fz', r, 'D → B: no line')

    def test_pets_clothes_gear(self):
        s, ids = pets(5, 5, 5)
        with always(px, 0), no_myth():
            s, r = act(s, 'jr_pet_fuse', pets=ids, main=ids[0], confirm=True)
        self.assertEqual((r['fz']['k'], r['fz']['id'], r['fz']['r'], r['fz']['lg']), ('pet', ids[0], 6, False))
        self.assertEqual(fz.text('pet', 'Bơ', r['fz']), f'🌈 Bơ vừa ghép ra bé {r["fz"]["n"]} hạng SSS!')
        s, ids = pets(3, 3, 3)
        with always(px, 0), no_myth():
            s, r = act(s, 'jr_pet_fuse', pets=ids, main=ids[0], confirm=True)
        self.assertTrue(r['fuse']['ok'])
        self.assertNotIn('fz', r)
        s, ids = pets(4, 4, 4, 4, 4, 4, 4, 4, 4)
        with always(px, 0), no_myth():
            s, r = act(s, 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['fz']['r'], r['fz']['more']), (6, []), 'three SS made one SSS: the line is the SSS')
        # 👗 clothes: three S pieces → SS
        s, _ = pets(0)
        s, out = act(s, 'jr_pet_wbuy', id='no_hong', qty=3, confirm=True)
        for i in pw.get(s)['it']:
            i['r'] = 4
        with always(px, 0):
            s, r = act(s, 'jr_pet_wfuse', k='no_hong', r=4, confirm=True)
        self.assertEqual((r['fz']['k'], r['fz']['r'], r['fz']['id']), ('ward', 5, r['item']))
        self.assertIn('👗', fz.text('ward', 'Bơ', r['fz']))
        s, _ = pets(0)
        s, out = act(s, 'jr_pet_wbuy', id='no_hong', qty=9, confirm=True)
        for i in pw.get(s)['it']:
            i['r'] = 4
        with always(px, 0):
            s, r = act(s, 'jr_pet_wfuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['fz']['r'], r['fz']['more']), (6, []))
        # 🧰 gear: a +10 S with two S → SS; the auto run marks a rank up, never a +1
        s, _ = gear(('giay', 4, 10, False), ('giay', 4, 0, False), ('giay', 4, 0, False))
        main = X(s)['gear'][0]['id']
        with always(px, 0):
            s, r = act(s, 'jr_pet_gear_fuse', gears=[g['id'] for g in X(s)['gear']], confirm=True)
        self.assertEqual((r['fz']['k'], r['fz']['id'], r['fz']['r']), ('gear', main, 5))
        self.assertIn('🧰', fz.text('gear', 'Bơ', r['fz']))
        s, _ = gear(('giay', 5, 9, True))
        with always(px, 0):
            s, r = act(s, 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual(r['auto']['n'], 1)
        self.assertNotIn('fz', r, 'an SS +9 → +10: no rank, no line')
        s, _ = gear(('giay', 4, 10, True), ('giay', 4, 0, False), ('giay', 4, 0, False))
        with always(px, 0):
            s, r = act(s, 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual(r['fz']['r'], 5)


class Setting(unittest.TestCase):
    def test_forge_anon_setting(self):
        s = wings(10**6)
        self.assertFalse(public_state(s)['settings']['forgeAnon'], 'the default: the name shown')
        s, _ = act(s, 'settings', forgeAnon=True)
        self.assertEqual(s['journey'][fz.KEY], dict(v=1, anon=True))
        self.assertNotIn('forgeAnon', s['settings'], 'the strict settings block of older builds is untouched')
        self.assertTrue(public_state(s)['settings']['forgeAnon'])
        self.assertTrue(fz.hidden(s))
        validate_state(s)
        s, _ = act(s, 'settings', forgeAnon=False)
        self.assertNotIn(fz.KEY, s['journey'])
        self.assertFalse(public_state(s)['settings']['forgeAnon'])
        with self.assertRaises(GameError):
            act(s, 'settings', forgeAnon='yes')
        bad = copy.deepcopy(s)
        bad['journey'][fz.KEY] = dict(v=1, anon='x')
        with self.assertRaises(GameError):
            validate_state(bad)


class Ticker(unittest.TestCase):
    """Through the store: the commit hook posts the line, once a piece and rank, with the name or 🕶️ hidden."""

    def setUp(self):
        from game import marriage as mr
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(prefix='mnl-fzn-', ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        token, _, _ = self.store.session()
        self.store.read(token)
        self.token = accounts.register(self.store, token, REG)['token']
        self.sid = self.store.key(self.token)
        self.mr = mr
        self.n = 0

    def give(self, fn):
        self.mr._mutate(self.store, {self.sid: fn})

    def run_(self, action, **p):
        self.n += 1
        rev = self.store.read(self.token)[1]
        return self.store.command(self.token, f'req-fzn-{self.n:04d}', rev, None, action, p)['result']

    def lines(self):
        with self.store.connect() as db:
            rows = db.execute('SELECT kind, ref, text FROM news WHERE ref LIKE ? ORDER BY id', (f'%:{self.sid[:16]}:%',)).fetchall()
        return [(r['kind'], r['ref'], r['text']) for r in rows]

    def wings_(self, *groups):
        def fn(s):
            s['journey']['wallet'] = 10**9
            s['journey']['stats']['max_wallet'] = 10**9
            w = W._ensure(s)
            for k, r, n in groups:
                for _ in range(n):
                    W._new(w, k, r)
        self.give(fn)

    def test_one_line_a_piece_and_rank_with_the_name(self):
        self.wings_(('buom', 3, 3), ('rong', 4, 6))
        own = Wg(self.store.read(self.token)[0])['own']
        with always(W, 0):
            self.run_('jr_pet_wing_fuse', wings=[x['id'] for x in own[:3]], confirm=True)
        self.assertEqual(self.lines(), [], 'S: no line')
        rong = [x['id'] for x in own if x['k'] == 'rong']
        with always(W, 0):
            r = self.run_('jr_pet_wing_fuse', wings=rong[:3], confirm=True)
        lines = self.lines()
        self.assertEqual(len(lines), 1)
        kind, ref, text = lines[0]
        self.assertEqual((kind, ref), ('forge', f'wingfz:{self.sid[:16]}:{rong[0]}:5'))
        self.assertTrue(text.startswith('🪽 Bơ Cường vừa cường hóa ') and text.endswith(' lên hạng SS!'), text)
        # the same piece and rank again (a replayed mark): nothing more
        with self.store.connect() as db:
            self.assertFalse(fz.post(db, self.sid, self.store.read(self.token)[0], r))
        self.assertEqual(len(self.lines()), 1)
        # a new rank of the same piece: a new line
        def two_more_ss(s):
            for x in Wg(s)['own']:
                if x['id'] in rong[3:5]:
                    x['r'] = 5
        self.give(two_more_ss)
        with always(W, 0):
            self.run_('jr_pet_wing_fuse', wings=[rong[0]] + rong[3:5], confirm=True)
        self.assertEqual([x[1].rsplit(':', 1)[1] for x in self.lines()], ['5', '6'])

    def test_the_auto_run_posts_a_single_line(self):
        self.wings_(('buom', 4, 12))
        with always(W, 0):
            r = self.run_('jr_pet_wing_fuse_auto', budget=10**9, rid='fzn-auto-0001', confirm=True)
        self.assertEqual(r['auto']['n'], 5)
        lines = self.lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0][2].endswith('lên hạng SSS (và 1 đôi SS)!'), lines[0][2])
        # 🧬 pets: nine S → three SS → one SSS: one line
        from tests.test_pet_tiers import get as get_pet

        def fn(s):
            s['journey']['gender'] = s['journey'].get('gender') or 'female'
            for i in range(9):
                s2, _ = get_pet(s, f'Bé {i}', breed='meo_mun', rank=4)
                s.clear()
                s.update(s2)
        self.give(fn)
        with always(px, 0), no_myth():
            r = self.run_('jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual(r['auto']['ok'], 4)
        pet_lines = [x for x in self.lines() if x[0] == 'pets']
        self.assertEqual(len(pet_lines), 1, pet_lines)
        self.assertIn('hạng SSS!', pet_lines[0][2])

    def test_hidden_name(self):
        self.run_('settings', forgeAnon=True)
        self.wings_(('buom', 5, 3))
        with always(W, 0):
            self.run_('jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        (_, _, text), = self.lines()
        self.assertIn(lux.ANON_NAME, text)
        self.assertNotIn('Bơ Cường', text)
        self.run_('settings', forgeAnon=False)
        self.wings_(('rong', 5, 3))
        with always(W, 0):
            self.run_('jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertIn('Bơ Cường', self.lines()[-1][2])

    def test_below_ss_posts_nothing(self):
        self.wings_(('buom', 0, 27))
        with always(W, 0):
            r = self.run_('jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertGreater(r['auto']['ok'], 5)
        self.assertEqual(self.lines(), [])


if __name__ == '__main__':
    unittest.main()
