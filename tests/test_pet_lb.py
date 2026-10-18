"""🐾 Thú cưng on the main Bảng xếp hạng (game/pet_lb.py): each player's best pet by 💪 lực chiến (pet_board 'LC'), the
boards' privacy, the viewer's own place and its weekly titles (game/lb_titles.py)."""
import json

from game import lb_titles as lbt
from game import leaderboard as lb
from game import pet_lb as pl
from tests import test_lb_titles as T
from tests.test_lb_titles import SUN, with_titles


class PetBoard(T.Weekly):   # (the module, not the class: pytest would run Weekly's own tests here again)
    def setUp(self):
        super().setUp()
        pl.clear_cache()
        self.addCleanup(pl.clear_cache)

    def pet(self, token, power, breed='corgi', rank=4, at=1.0, legend=False):
        sid = self.sid(token)
        acc = json.dumps(dict(r=rank, top=rank, x='cau_vong' if rank == 6 else '', lg=legend, a=['no_do', 'bad_id']))

        def w(db):
            db.execute('INSERT INTO pet_board(sid, week, name, breed, coat, acc, pts, at) VALUES(?,?,?,?,?,?,?,?) '
                       'ON CONFLICT (sid, week) DO UPDATE SET pts=EXCLUDED.pts, at=EXCLUDED.at, breed=EXCLUDED.breed, acc=EXCLUDED.acc',
                       (sid, 'LC', f'Bé {power}', breed, 0, acc, power, at))
            db.execute('INSERT INTO pet_board(sid, week, name, breed, coat, acc, pts, at) VALUES(?,?,?,?,?,?,?,?) '
                       'ON CONFLICT (sid, week) DO NOTHING', (sid, '2026-W41', 'Tuần', breed, 0, '[]', 10**6, at))   # the weekly board: not this one
        self.store.transaction(w)
        pl.clear_cache()

    def test_query_and_titles(self):
        self.assertEqual(lb.parse_query({'board': 'pets'}), ('pets', 50))
        self.assertEqual(lbt.title_of('pets', 1)['text'], '🐉 Vua thú cưng của phố')
        self.assertEqual(lbt.title_of('pets', 2)['name'], 'Sen cưng siêu cấp')
        self.assertEqual(lbt.title_of('pets', 10)['name'], 'Hội sen yêu bé')
        self.assertIsNone(lbt.title_of('pets', 11))
        self.assertIn('pets', lbt.MAIN)

    def test_order_pet_privacy_and_me(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        c = self.player(with_titles(1), account='Chi')
        g = self.player(with_titles(1))                      # a guest who never opted in: counted for nobody, never named
        self.pet(a, 300, at=5.0)
        self.pet(b, 900, 'than_tai', 6, legend=True)
        self.pet(c, 300, at=2.0)                             # same power as An, earlier: ahead
        self.pet(g, 5000)
        v = lb.view(self.store, 'pets', 50, a)
        self.assertEqual([(r['name'], r['score'], r['rank'], r['me']) for r in v['rows']],
                         [('Bình', 900, 1, False), ('Chi', 300, 2, False), ('An', 300, 3, True)])
        top = v['rows'][0]
        self.assertEqual((top['pn'], top['b'], top['r'], top['x'], top['lg'], top['kind']), ('Bé 900', 'than_tai', 6, 'cau_vong', True, 'cat'))
        self.assertEqual(top['a'], ['no_do'] if 'no_do' in __import__('game.pets_content', fromlist=['ACC']).ACC else [])
        self.assertNotIn('sid', top)
        self.assertEqual(v['total'], 3)
        self.assertEqual((v['me']['rank'], v['me']['score'], v['me']['b']), (3, 300, 'corgi'))
        lb.set_visible(self.store, b, self.store.read(b)[0], False)
        pl.clear_cache()
        v = lb.view(self.store, 'pets', 50, b)
        self.assertEqual([r['name'] for r in v['rows']], ['Chi', 'An'])
        self.assertEqual(v['me']['rank'], 1)                 # hidden: still told where they would stand
        self.assertFalse(v['me']['visible'])
        d = self.player(with_titles(1), account='Dũng')       # no pet yet
        self.assertIsNone(lb.view(self.store, 'pets', 50, d)['me']['rank'])

    def test_weekly_titles(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        self.pet(a, 100)
        self.pet(b, 200)
        self.assertTrue(lbt.refresh(self.store, SUN))
        self.assertIn(('pets', 1), self.holders()['Bình'])
        self.assertIn(('pets', 2), self.holders()['An'])
        v = lb.view(self.store, 'pets', 50, a)
        self.assertEqual(v['rows'][0]['title'], dict(emoji='🐉', name='Vua thú cưng của phố'))
        self.assertEqual(v['weekly']['tiers'][0]['holders'][0]['name'], 'Bình')
