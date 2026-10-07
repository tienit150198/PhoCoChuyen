"""🐾 Nuôi thú cưng (game/pets.py): the breeds and their prices, adopting (free, with an optional donation) and buying
(wallet then bank, never debt, no xu created), the 3-pet cap and the grandparents', the gentle care loop (sad, never
dead), toys, accessories, tricks, the capped tinh thần, saves (old ones without the block, blocks a newer build
wrote), the pet_care hook, and the Bé cưng của tuần rows written with the save."""
import copy
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import journey as jr
from game import pets as pt
from game import pets_content as C
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, opened, story

HEX = re.compile(r'^#[0-9a-f]{6}$')


def P(s):
    return s['journey']['pets']


def money(s):
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def buy(s, breed='corgi', coat=0, nick='Bông'):
    return act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed=breed, coat=coat, nick=nick, confirm=True)


def next_day(s, n=1):
    s['journey']['life_day'] += n
    validate_state(s)


class Catalogue(unittest.TestCase):
    def test_breeds_coats_prices(self):
        self.assertGreaterEqual(len(C.DOGS), 12)
        self.assertGreaterEqual(len(C.CATS), 12)
        prices = [b['price'] for b in C.BREEDS.values()]
        self.assertEqual(min(prices), 300)
        self.assertEqual(max(prices), 30000)
        for bid, b in C.BREEDS.items():
            self.assertRegex(bid, pt.ID_RE.pattern)
            self.assertTrue(b['trait'] and b['line'] and 1 <= len(b['coats']) <= 16, bid)
            for c in b['coats']:
                self.assertTrue(all(HEX.match(c[k]) for k in 'bmle'), (bid, c))
            if b['tier'] == 'ta':
                self.assertLessEqual(b['price'], 400, bid)       # local breeds are cheap
            if b['tier'] == 'hiem':
                self.assertGreaterEqual(b['price'], 9000, bid)
        self.assertTrue(set(C.SHELTER) <= {b for b in C.BREEDS if C.BREEDS[b]['tier'] == 'ta'})
        self.assertEqual(len({a['id'] for a in C.ACCS}), len(C.ACCS))
        self.assertFalse(set(C.ACC) & set(C.TOY))
        self.assertEqual(jr.content()['pets'], pt.catalogue())

    def test_shelter_is_seeded_per_day(self):
        s = story()
        a = pt.shelter_today(s)
        self.assertEqual(a, pt.shelter_today(copy.deepcopy(s)))
        self.assertEqual(len(a), C.SHELTER_SEEN)
        self.assertEqual(len({x['n'] for x in a}), len(a))
        seen = set()
        for d in range(1, 30):
            s['journey']['life_day'] = d
            seen |= {x['b'] for x in pt.shelter_today(s)}
        self.assertTrue(seen & set(C.SHELTER_RARE))               # now and then a purebred waits there too


class Owning(unittest.TestCase):
    def test_shelter_adoption_is_free_and_a_donation_is_optional(self):
        s = story(wallet=100)
        before = money(s)
        a = pt.shelter_today(s)[0]
        s, out = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='Mít', confirm=True)
        self.assertEqual(money(s), before)
        pet = P(s)['list'][0]
        self.assertEqual((pet['b'], pet['c'], pet['n'], pet['s'], pet['p']), (a['b'], a['c'], 'Mít', 'shelter', 0))
        self.assertEqual(P(s)['walk'], pet['id'])
        refused(self, s, 'jr_pet_adopt', 'gone', **{'from': 'shelter'}, i=0, nick='Lu', confirm=True)   # taken today
        s, _ = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=1, nick='Lu', donate=50, confirm=True)
        self.assertEqual(money(s), before - 50)
        self.assertEqual(P(s)['stats']['donated'], 50)
        self.assertEqual(s['journey']['history'][-1]['kind'] if 'history' in s['journey'] else 'life', 'life')
        refused(self, s, 'jr_pet_adopt', 'not_enough', **{'from': 'shelter'}, i=2, nick='Na', donate=500, confirm=True)

    def test_buying_takes_wallet_then_bank_and_never_debt(self):
        s = opened(wallet=5000, deposit=4000)
        s['journey']['wallet'] = 3000
        validate_state(s)
        before = money(s)
        s, out = buy(s, 'corgi', 1, 'Tofu')                          # 6,000: 3,000 cash + 3,000 from the account
        self.assertEqual(money(s), before - 6000)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertIn('từ tài khoản', out['message'])
        self.assertEqual(P(s)['list'][0]['p'], 6000)
        self.assertIn('Còn thiếu', refused(self, s, 'jr_pet_adopt', 'not_enough', **{'from': 'shop'}, breed='phu_quoc', nick='Ki', confirm=True))
        s['journey']['wallet'] = -10
        refused(self, s, 'jr_pet_adopt', 'not_enough', **{'from': 'shop'}, breed='meo_muop', nick='Ki', confirm=True)
        refused(self, s, 'jr_pet_adopt', None, **{'from': 'shop'}, breed='nope', nick='Ki', confirm=True)
        refused(self, s, 'jr_pet_adopt', None, **{'from': 'shop'}, breed='corgi', coat=7, nick='Ki', confirm=True)

    def test_no_command_creates_xu(self):
        s = story(wallet=20000)
        s, _ = buy(s, 'shiba')
        pid = P(s)['list'][0]['id']
        last = money(s)
        steps = [('jr_pet_buy', dict(id='bong', confirm=True)), ('jr_pet_buy', dict(id='no_hong', qty=2, confirm=True)),
                 ('jr_pet_play', dict(pet=pid, toy='bong')), ('jr_pet_wear', dict(pet=pid, slot='head', id='no_hong')),
                 ('jr_pet_bath', dict(pet=pid)), ('jr_pet_show', dict(pet=pid)), ('jr_pet_walk', dict(pet=pid)),
                 ('jr_pet_donate', dict(amount=20, confirm=True)), ('jr_pet_name', dict(pet=pid, nick='Cún')),
                 ('jr_pet_home', dict(pet=pid, confirm=True)), ('jr_pet_back', dict(pet=pid))]
        for name, p in steps:
            s, _ = act(s, name, **p)
            self.assertLessEqual(money(s), last, name)
            last = money(s)
        self.assertEqual(20000 - money(s), P(s)['stats']['xu'])     # every xu spent is counted once
        for day in range(3):
            next_day(s)
            for f in ('tiec', 'pate'):
                try:
                    s, _ = act(s, 'jr_pet_feed', pet=pid, food=f)
                except GameError:
                    pass
            self.assertLessEqual(money(s), last)
            last = money(s)
        self.assertEqual(20000 - money(s), P(s)['stats']['xu'])

    def test_three_pets_then_the_grandparents(self):
        s = story(wallet=5000)
        for n in ('A', 'B', 'C'):
            s, _ = buy(s, 'meo_mun', 0, n)
        self.assertIn('đủ 3 bé', refused(self, s, 'jr_pet_adopt', 'limit', **{'from': 'shop'}, breed='meo_mun', nick='D', confirm=True))
        refused(self, s, 'jr_pet_adopt', 'limit', **{'from': 'shelter'}, i=0, nick='D', confirm=True)
        first = P(s)['list'][0]['id']
        s, _ = act(s, 'jr_pet_home', pet=first, confirm=True)
        self.assertEqual(len(P(s)['list']), 2)
        self.assertEqual([p['id'] for p in P(s)['farm']], [first])
        self.assertNotEqual(P(s)['walk'], first)
        s, _ = buy(s, 'meo_mun', 1, 'D')
        refused(self, s, 'jr_pet_back', 'limit', pet=first)
        s, _ = act(s, 'jr_pet_home', pet=P(s)['list'][0]['id'], confirm=True)
        s, _ = act(s, 'jr_pet_back', pet=first)
        self.assertEqual(len(P(s)['list']), 3)
        self.assertEqual(len(P(s)['farm']), 1)


class Care(unittest.TestCase):
    def setUp(self):
        self.s, _ = buy(story(wallet=20000), 'pom', 0, 'Bông')
        self.pid = P(self.s)['list'][0]['id']

    def view(self, s=None):
        s = s or self.s
        return pt.public(s)['pets'][0]

    def test_neglect_makes_sad_never_dead(self):
        s = self.s
        self.assertEqual(self.view()['mood'], 'vui')
        next_day(s, 1)
        self.assertIn(self.view()['mood'], ('on', 'buon'))
        next_day(s, 60)                                            # two months away
        v = self.view()
        self.assertEqual(v['mood'], 'buon')
        self.assertEqual(v['needs'], dict(f=0, j=0, cl=0, h=0))   # floors at 0, the pet is still there
        self.assertEqual(len(P(s)['list']), 1)
        s, out = act(s, 'jr_pet_feed', pet=self.pid, food='com_nha')   # free food always works
        self.assertEqual(P(s)['list'][0]['f'], 30)
        s, _ = act(s, 'jr_pet_vet', pet=self.pid, what='kham', confirm=True)
        self.assertEqual(P(s)['list'][0]['h'], 100)

    def test_full_refusals_and_toys(self):
        s = self.s
        s, _ = act(s, 'jr_pet_buy', id='bong', confirm=True)
        self.assertEqual(P(s)['own']['bong'], 10)
        s, _ = act(s, 'jr_pet_play', pet=self.pid, toy='bong')
        self.assertEqual(P(s)['own']['bong'], 9)
        self.assertIn('chơi mệt', refused(self, s, 'jr_pet_play', 'full', pet=self.pid))
        s, _ = act(s, 'jr_pet_feed', pet=self.pid, food='tiec')
        self.assertIn('no căng', refused(self, s, 'jr_pet_feed', 'full', pet=self.pid, food='hat'))
        refused(self, s, 'jr_pet_play', None, pet=self.pid, toy='can_cau')       # a cat toy, not owned anyway
        s, _ = act(s, 'jr_pet_buy', id='dia_bay', confirm=True)
        refused(self, s, 'jr_pet_buy', 'duplicate', id='dia_bay', confirm=True)   # kept toys: one is enough

    def test_bond_tricks_points_and_one_spirit_a_day(self):
        s = self.s
        s['journey']['life']['spirit'] = 50
        s, out = act(s, 'jr_pet_show', pet=self.pid)
        self.assertEqual(s['journey']['life']['spirit'], 51)
        s, _ = act(s, 'jr_pet_show', pet=self.pid)
        s, _ = act(s, 'jr_pet_bath', pet=self.pid) if P(s)['list'][0]['cl'] < C.FULL else (s, None)
        self.assertEqual(s['journey']['life']['spirit'], 51)      # once a life day
        p = P(s)['list'][0]
        self.assertEqual(p['x'], len(p['done']))                  # one point per kind of care a day
        for d in range(12):
            next_day(s)
            for name, kw in (('jr_pet_feed', dict(food='hat')), ('jr_pet_play', {}), ('jr_pet_show', {})):
                s, _ = act(s, name, pet=self.pid, **kw)
        p = P(s)['list'][0]
        self.assertGreaterEqual(p['x'], 30)
        self.assertEqual(p['tr'][:3], ['ngoi', 'bat_tay', 'nam'])
        self.assertLessEqual(s['journey']['life']['spirit'], 51 + 12)
        s, out = act(s, 'jr_pet_show', pet=self.pid, trick='bat_tay')
        self.assertIn('Bắt tay', out['message'])
        refused(self, s, 'jr_pet_show', None, pet=self.pid, trick='dep')

    def test_accessories_one_pet_per_copy(self):
        s = self.s
        s, _ = buy(s, 'meo_mun', 0, 'Than')
        a, b = (p['id'] for p in P(s)['list'])
        s, _ = act(s, 'jr_pet_buy', id='non_la', confirm=True)
        s, _ = act(s, 'jr_pet_wear', pet=a, slot='head', id='non_la')
        self.assertIn('bé khác', refused(self, s, 'jr_pet_wear', 'not_owned', pet=b, slot='head', id='non_la'))
        refused(self, s, 'jr_pet_wear', None, pet=b, slot='body', id='non_la')
        s, _ = act(s, 'jr_pet_wear', pet=a, slot='head', id=None)
        s, _ = act(s, 'jr_pet_wear', pet=b, slot='head', id='non_la')
        self.assertEqual(pt.walk_ref(s)['n'], 'Bông')
        s, _ = act(s, 'jr_pet_walk', pet=b)
        self.assertEqual(pt.walk_ref(s), dict(b='meo_mun', c=0, n='Than', a=['non_la']))

    def test_names_follow_the_display_name_rules(self):
        refused(self, self.s, 'jr_pet_name', None, pet=self.pid, nick='')
        refused(self, self.s, 'jr_pet_name', None, pet=self.pid, nick='www.lừađảo.com')
        refused(self, self.s, 'jr_pet_name', None, pet=self.pid, nick='Một cái tên rất là dài')

    def test_player_groomer_hook(self):
        s = self.s
        next_day(s, 3)
        self.assertTrue(pt.groom_by_player(s))
        validate_state(s)
        self.assertEqual(P(s)['list'][0]['cl'], 100)
        self.assertFalse(pt.groom_by_player(story()))


class Saves(unittest.TestCase):
    def test_old_saves_and_public(self):
        s = story()
        validate_state(s)
        self.assertNotIn('pets', s['journey'])
        self.assertEqual(public_state(s)['journey']['pets'], dict(story=True, max=3, shelter=pt.public(s)['shelter']))
        s, _ = buy(story(wallet=900), 'cho_ta', 0, 'Vàng')
        m = migrate_state(copy.deepcopy(s))
        validate_state(m)
        self.assertEqual(m['journey']['pets'], P(s))

    def test_bad_blocks_refused_newer_blocks_kept(self):
        s, _ = buy(story(wallet=900), 'cho_ta', 0, 'Vàng')
        for bad in (lambda b: b['list'].append(copy.deepcopy(b['list'][0])), lambda b: b['list'][0].update(f=101),
                    lambda b: b.update(walk='p99'), lambda b: b['list'][0]['w'].update(head='no_hong'),
                    lambda b: b.update(list=[copy.deepcopy(b['list'][0]) for _ in range(4)])):
            x = copy.deepcopy(s)
            bad(P(x))
            with self.assertRaises(GameError):
                validate_state(x)
        newer = copy.deepcopy(s)
        P(newer)['list'][0]['zz'] = 1                                # a field a newer build added
        P(newer)['list'][0]['b'] = 'rong_lua'                        # a breed this build does not know
        P(newer)['own']['vong_moi'] = 1
        P(newer)['list'].extend(copy.deepcopy(P(newer)['list'][0]) | dict(id=f'p{i}') for i in (7, 8, 9))
        P(newer)['zz'] = {}
        m = migrate_state(newer)
        validate_state(m)
        self.assertEqual(len(P(m)['list']), 3)
        self.assertEqual(len(P(m)['farm']), 1)                      # over the cap: to the grandparents', never away
        self.assertEqual(P(m)['list'][0]['b'], 'rong_lua')
        self.assertEqual(P(m)['own']['vong_moi'], 1)
        self.assertFalse(pt.public(m)['pets'][0]['known'])
        self.assertIsNone(pt.walk_ref(m))


class Live(unittest.TestCase):
    """The pet beside a stroller (`pt`, live/street.py clean_pet): optional, outside the look, never refused."""

    def test_breeds_match_the_game(self):
        from live.street_data import PET_ACCS, PET_BREEDS
        self.assertEqual(PET_BREEDS, {b: len(C.BREEDS[b]['coats']) for b in C.ORDER})
        self.assertEqual(PET_ACCS, {a['id'] for a in C.ACCS if a['slot'] != 'bed'})

    def test_clean_pet(self):
        from live.street import Walker, clean_pet
        self.assertEqual(clean_pet(dict(b='corgi', c=1, n='Tofu', a=['no_hong', 'nope', 'o_bong'])),
                         dict(b='corgi', c=1, n='Tofu', a=['no_hong']))
        for bad in (None, 'x', dict(b='rong'), dict(b='pug', c=9), dict(b='pug', c='0'), dict(b='pug', c=0, zz=1)):
            self.assertIsNone(clean_pet(bad))
        self.assertEqual(clean_pet(dict(b='pug', c=0, n='zalo 0912345678'))['n'], 'zalo •••')
        self.assertNotIn('n', clean_pet(dict(b='pug', c=0, n='   ')))

        class Player:
            pid, name = 'a', 'Lan'
        w = Walker(Player(), {}, None, None, (0, 0), 0.0)
        self.assertNotIn('pt', w.public())                       # no pet: the frame is what 1.9.10 sent
        w = Walker(Player(), {}, None, None, (0, 0), 0.0, pt=clean_pet(dict(b='xiem', c=0)))
        self.assertEqual(w.public()['pt'], dict(b='xiem', c=0, a=[]))
        s, _ = buy(story(wallet=900), 'cho_ta', 0, 'Vàng')
        self.assertEqual(clean_pet(pt.walk_ref(s)), pt.walk_ref(s))   # what the client sends passes as it is


class Database(unittest.TestCase):
    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        pt._BOARD.clear()

    def player(self, wallet=50000, name='Lan'):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {self.store.key(token): fn})
        return token

    def cmd(self, token, action, n=[0], **p):
        n[0] += 1
        return self.store.command(token, f'req-{n[0]:08d}', self.store.read(token)[1], None, action, p)

    def test_weekly_board(self):
        a, b = self.player(), self.player(name='Minh')
        T = 1791900000.0
        with mock.patch.object(pt, 'now', return_value=T):
            out = self.cmd(a, 'jr_pet_adopt', **{'from': 'shop'}, breed='samoyed', coat=0, nick='Mây', confirm=True)
            self.assertEqual(out['state']['journey']['wallet'], 50000 - 22000)
            pa = out['state']['journey']['pets']['pets'][0]['id']
            self.cmd(a, 'jr_pet_show', pet=pa)
            self.cmd(b, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='Mít', confirm=True)
            rows = self.store.read(b)[0]['journey']['pets']['list']
            self.cmd(b, 'jr_pet_show', pet=rows[0]['id'])
            self.cmd(b, 'jr_pet_feed', pet=rows[0]['id'], food='hat')
            board = pt.board(self.store, b)
        self.assertEqual(board['week'], pt.week_key(T))
        self.assertEqual([(x['name'], x['pts'], x['me']) for x in board['top']], [('Mít', 2, True), ('Mây', 1, False)])
        self.assertTrue(all('sid' not in x for x in board['top']))
        self.store.delete(a)
        pt._BOARD.clear()
        with mock.patch.object(pt, 'now', return_value=T):
            self.assertEqual([x['name'] for x in pt.board(self.store, None)['top']], ['Mít'])


if __name__ == '__main__':
    unittest.main()
