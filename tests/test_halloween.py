"""🎃 Lễ hội Ma Phố (game/halloween.py): the Halloween season of 2026. Real accounts on one PostgreSQL store
(TEST_DATABASE_URL): the calendar (nothing before 26/10 00:00 VN, the grace day, the kill switch), the daily check-in, the
pumpkin riddles and the 2.5D walk, the night ×2 and the giant pumpkin, Cho kẹo hay bị ghẹo between players (once a host a
day, the daily caps, the host's tip and its cap, new accounts, one network's clones, blocked players), the candy shop (the
balance, once each, the 🎨 Phong cách items, the pet piece and the capped xu swaps paid into the save exactly once, under
concurrency too), the board and its top 10 granted exactly once after the season, the ticker line, the view, the admin and
an account's deletion."""
import concurrent.futures
import datetime
import os
from unittest.mock import patch

from game import halloween as hw
from game import halloween_content as C
from game import live_effects as lfx
from game import marriage as mr
from game import pet_wardrobe as pw
from game import spend as sp
from game import spend_content as SC
from tests.test_quay_hire import Base

H, M, D = 3600, 60, 86400
DAY1 = hw.START + 10 * H          # Mon 26/10 10:00 (VN)
DAY3 = hw.START + 2 * D + 9 * H   # Wed 28/10 09:00


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class HWBase(Base):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'MNL_HALLOWEEN_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        hw.clear_cache()
        self.addCleanup(hw.clear_cache)
        hw._swept[0] = 0.0
        hw._closed[0] = False
        self.clock = Clock(DAY1)
        p = patch('game.halloween.now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def post(self, tok, op, ip='10.0.0.1', **d):
        return hw.post(self.store, tok, op, d, ip=ip)

    def view(self, tok):
        return hw.view(self.store, tok)

    def candy(self, tok):
        return self.view(tok)['me']['candy']

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def give(self, tok, n):
        sid = self.sid(tok)
        self.store.transaction(lambda db: hw._earn(db, sid, f'test:{sid}:{n}:{self.clock.t}', 'test', n, hw.vn_day(self.clock.t), self.clock.t))

    def fresh(self, name, **kw):
        """An account made just now on the season's clock (accounts.created_at is UTC text)."""
        import time
        tok = self.user(name, **kw)
        at = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.clock.t - 600))
        self.store.transaction(lambda db: db.execute('UPDATE accounts SET created_at=? WHERE sid=?', (at, self.sid(tok))))
        return tok

    def load(self, tok):
        lfx.on_load(self.store, tok, self.state(tok))

    def own(self, tok):
        b = sp.get(self.state(tok))
        return {k: v for k, v in (b or {}).get('own', {}).items() if k in C.STYLE_IDS}

    def right_place(self, i, t=None):
        return hw.spots(hw.vn_day(self.clock.t if t is None else t))[i]['key']


class Calendar(HWBase):
    def test_vietnam_dates(self):
        at = lambda t: datetime.datetime.fromtimestamp(t, hw.VN).strftime('%d/%m %H:%M %a')
        self.assertEqual(at(hw.START), '26/10 00:00 Mon')
        self.assertEqual(at(hw.END), '01/11 00:00 Sun')
        self.assertEqual(at(hw.SHOP_UNTIL), '02/11 00:00 Mon')
        self.assertEqual(at(hw.NIGHT), '31/10 19:00 Sat')
        self.assertEqual(sorted(C.DAYS), [f'2026-10-{d}' for d in range(26, 32)])

    def test_nothing_before_the_start(self):
        tok = self.user('cal_a')
        self.clock.t = hw.START - 1
        self.assertEqual(hw.phase(), 'before')
        self.assertIsNone(hw.hint())
        self.assertIsNone(hw.news_line())
        v = self.view(tok)
        self.assertEqual(v['state'], 'before')
        self.assertNotIn('me', v)
        self.refused('hween_soon', self.post, tok, 'checkin')
        self.refused('hween_over', self.post, tok, 'buy', item='t_hw_san_bi_ngo')
        self.assertEqual(self.post(tok, 'walk', place='bank'), dict(found=False))
        self.clock.t = hw.START
        self.assertEqual(hw.hint()['state'], 'open')
        self.assertEqual(hw.hint()['day'], 1)

    def test_grace_day_then_over(self):
        tok = self.user('cal_b')
        self.give(tok, 100)
        self.clock.t = hw.END + H
        self.assertEqual(hw.hint()['state'], 'grace')
        self.assertIsNone(hw.news_line())
        self.refused('hween_over', self.post, tok, 'checkin')
        self.post(tok, 'buy', item='t_hw_san_bi_ngo')
        self.assertEqual(self.candy(tok), 60)
        self.clock.t = hw.SHOP_UNTIL
        self.assertIsNone(hw.hint())
        self.refused('hween_over', self.post, tok, 'buy', item='f_hw_doi')

    def test_kill_switch(self):
        tok = self.user('cal_c')
        with patch.dict(os.environ, {'MNL_HALLOWEEN_OFF': '1'}):
            self.assertEqual(hw.phase(), 'off')
            self.assertIsNone(hw.hint())
            self.assertIsNone(hw.news_line())
            self.refused('hween_off', self.post, tok, 'checkin')
            self.refused('hween_off', self.post, tok, 'buy', item='t_hw_san_bi_ngo')
            self.clock.t = hw.END + 5 * H
            self.assertEqual(hw.run_housekeeping(self.store), 0)
        self.clock.t = DAY1
        self.post(tok, 'checkin')

    def test_ticker_line_once_a_day_and_at_night(self):
        a = hw.news_line()
        self.assertIn('Phố treo đèn bí ngô', a['text'])
        self.assertEqual(a['key'], 'hween:2026-10-26')
        self.clock.t = hw.NIGHT - 1
        self.assertEqual(hw.news_line()['key'], 'hween:2026-10-31')
        self.clock.t = hw.NIGHT
        self.assertEqual(hw.news_line()['key'], 'hween:2026-10-31:night')
        with patch('game.marriage.now', self.clock):
            news = mr.news(self.store, 0)
        self.assertEqual(news['event']['key'], 'hween:2026-10-31:night')
        self.assertEqual(news['hween']['state'], 'open')


class Candy(HWBase):
    def test_guest_sees_the_season_without_playing(self):
        token, _, _ = self.store.session()
        v = self.view(token)
        self.assertFalse(v['account'])
        self.refused('login_required', self.post, token, 'checkin')

    def test_checkin_once_a_day_with_the_days_bonus(self):
        tok = self.user('ci_a')
        r = self.post(tok, 'checkin')
        self.assertEqual(r['n'], hw.CHECKIN + 5)   # 26/10: khai hội
        self.assertEqual(r['view']['me']['candy'], 15)
        self.refused('done', self.post, tok, 'checkin')
        self.clock.t += D
        self.assertEqual(self.post(tok, 'checkin')['n'], hw.CHECKIN)
        self.assertEqual(self.candy(tok), 25)

    def test_pumpkin_riddles_one_try_each(self):
        tok = self.user('pk_a')
        v = self.view(tok)
        self.assertEqual(len(v['pumpkins']), C.PUMPKINS)
        for p in v['pumpkins']:
            self.assertEqual(len(p['choices']), C.CHOICES)
            self.assertNotIn('key', p)
            self.assertEqual(p['status'], 'open')
        keys = [hw.spots('2026-10-26')[i]['key'] for i in range(C.PUMPKINS)]
        self.assertEqual(len(set(keys)), C.PUMPKINS)
        self.assertNotEqual(keys, [hw.spots('2026-10-27')[i]['key'] for i in range(C.PUMPKINS)], 'another day, other places')
        r = self.post(tok, 'guess', spot=0, place=keys[0])
        self.assertTrue(r['found'])
        self.assertEqual(r['n'], hw.PUMP)
        self.refused('done', self.post, tok, 'guess', spot=0, place=keys[0])
        wrong = next(c for c in hw.spots('2026-10-26')[1]['choices'] if c != keys[1])
        r = self.post(tok, 'guess', spot=1, place=wrong)
        self.assertFalse(r['found'])
        self.assertIn(C.PLACE[keys[1]][1], r['message'])
        self.refused('done', self.post, tok, 'guess', spot=1, place=keys[1])
        bad = next(k for k in C.PLACE if k not in hw.spots('2026-10-26')[2]['choices'])
        self.refused('hween_error', self.post, tok, 'guess', spot=2, place=bad)
        self.refused('hween_error', self.post, tok, 'guess', spot=9, place=keys[0])
        v = self.view(tok)
        self.assertEqual([p['status'] for p in v['pumpkins'][:3]], ['found', 'missed', 'open'])
        self.assertEqual(v['me']['candy'], hw.PUMP)

    def test_walking_to_a_place_finds_its_pumpkin(self):
        tok = self.user('pk_b')
        keys = [s['key'] for s in hw.spots('2026-10-26')]
        other = next(k for k in C.PLACE if k not in keys)
        self.assertEqual(self.post(tok, 'walk', place=other), dict(found=False))
        self.assertEqual(self.post(tok, 'walk', place='nowhere'), dict(found=False))
        r = self.post(tok, 'walk', place=keys[3])
        self.assertTrue(r['found'])
        self.assertEqual(self.post(tok, 'walk', place=keys[3]), dict(found=False), 'once')
        self.refused('done', self.post, tok, 'guess', spot=3, place=keys[3])
        self.clock.t = DAY3 + D   # 29/10: +1 a pumpkin
        k = self.right_place(0)
        self.assertEqual(self.post(tok, 'walk', place=k)['n'], hw.PUMP + 1)

    def test_night_doubles_and_the_giant_pumpkin(self):
        tok = self.user('nt_a')
        self.clock.t = hw.NIGHT - M
        self.refused('not_night', self.post, tok, 'giant')
        self.clock.t = hw.NIGHT + M
        self.assertEqual(self.post(tok, 'checkin')['n'], hw.CHECKIN * 2)
        self.assertEqual(self.post(tok, 'guess', spot=0, place=self.right_place(0))['n'], hw.PUMP * 2)
        self.assertEqual(self.post(tok, 'giant')['n'], hw.GIANT)
        self.refused('done', self.post, tok, 'giant')
        self.assertEqual(self.candy(tok), hw.CHECKIN * 2 + hw.PUMP * 2 + hw.GIANT)


class Knock(HWBase):
    def test_treat_or_trick_once_a_host_a_day_and_the_hosts_tip(self):
        a, b = self.user('kn_a'), self.user('kn_b')
        self.post(b, 'checkin')   # b joins the season: a door in a's list
        doors = self.view(a)['knock']['doors']
        door = next(d for d in doors if d['name'] == 'Kn_B')
        r = self.post(a, 'knock', to=door['pid'])
        self.assertIn(r['n'], (hw.TRICK, hw.TREAT))
        self.assertEqual(r['tip'], hw.HOST)
        self.assertEqual(r['trick'], r['n'] == hw.TRICK)
        self.refused('done', self.post, a, 'knock', to='kn_b_test')
        self.assertEqual(self.candy(b), 15 + hw.HOST)
        vb = self.view(b)
        self.assertEqual([v['who']['name'] for v in vb['knock']['visitors']], ['Kn_A'])
        self.assertFalse(vb['knock']['visitors'][0]['back'])
        self.post(b, 'knock', to='kn_a_test')
        self.assertTrue(self.view(b)['knock']['visitors'][0]['back'])
        va = self.view(a)
        self.assertNotIn('Kn_B', [d['name'] for d in va['knock']['doors']], 'knocked today: not offered again')
        self.assertEqual(va['knock']['left'], hw.KNOCKS_DAY - 1)
        self.clock.t += D
        self.post(a, 'knock', to='@kn_b_test')   # another day, the same door again

    def test_treats_and_tricks_both_happen(self):
        a = self.user('kt_a')
        hosts = [self.user(f'kt_h{i}') for i in range(6)]
        with patch('game.halloween.secrets.randbelow', side_effect=[0, 0, 99, 0]):
            r1 = self.post(a, 'knock', to='kt_h0_test')
            r2 = self.post(a, 'knock', to='kt_h1_test')
        self.assertTrue(r1['trick'])
        self.assertEqual(r1['n'], hw.TRICK)
        self.assertFalse(r2['trick'])
        self.assertEqual(r2['n'], hw.TREAT)
        self.clock.t = hw.START + 4 * D + 10 * H   # 30/10 Chợ phù thủy: +1 a treat
        with patch('game.halloween.secrets.randbelow', side_effect=[99, 0]):
            self.assertEqual(self.post(a, 'knock', to='kt_h2_test')['n'], hw.TREAT + 1)
        self.clock.t = DAY3   # 28/10 Ngõ ma lém lỉnh: +1 to the host
        self.assertEqual(self.post(a, 'knock', to='kt_h3_test')['tip'], hw.HOST + 1)

    def test_daily_caps(self):
        a = self.user('kc_a')
        hosts = [self.user(f'kc_h{i}') for i in range(hw.KNOCKS_DAY + 1)]
        for i in range(hw.KNOCKS_DAY):
            self.post(a, 'knock', to=f'kc_h{i}_test')
        self.refused('knock_limit', self.post, a, 'knock', to=f'kc_h{hw.KNOCKS_DAY}_test')
        self.assertTrue(hosts)

    def test_host_tip_cap(self):
        host = self.user('hc_host')
        with patch.object(hw, 'HOSTED_DAY', 2):
            for i in range(3):
                v = self.user(f'hc_v{i}')
                r = self.post(v, 'knock', to='hc_host_test', ip=f'10.1.0.{i}')
                self.assertEqual(r['tip'], hw.HOST if i < 2 else 0)
        vh = self.view(host)
        self.assertEqual(vh['me']['candy'], 2 * hw.HOST)
        self.assertEqual(len(vh['knock']['visitors']), 3, 'the third visitor still shows')

    def test_refusals(self):
        a, b = self.user('kr_a'), self.user('kr_b')
        self.refused('own_door', self.post, a, 'knock', to='kr_a_test')
        self.refused('not_found', self.post, a, 'knock', to='nobody_here')
        new = self.fresh('kr_new')
        self.refused('too_new', self.post, new, 'knock', to='kr_a_test')
        token, _, _ = self.store.session()
        self.refused('login_required', self.post, token, 'knock', to='kr_a_test')
        from game import social
        self.store.transaction(lambda db: db.execute('INSERT INTO blocks(pid, target, at) VALUES(?,?,?)',
                                                     (social.pid_of(self.sid(b)), social.pid_of(self.sid(a)), 1.0)))
        self.refused('not_found', self.post, a, 'knock', to='kr_b_test')
        self.post(b, 'checkin')
        self.assertNotIn('Kr_B', [d['name'] for d in self.view(a)['knock']['doors']])

    def test_one_network_knocks_with_few_accounts(self):
        host = self.user('ip_host')
        vs = [self.user(f'ip_v{i}') for i in range(hw.KNOCK_IPS + 1)]
        for v in vs[:hw.KNOCK_IPS]:
            self.post(v, 'knock', to='ip_host_test', ip='9.9.9.9')
        self.refused('knock_ip', self.post, vs[-1], 'knock', to='ip_host_test', ip='9.9.9.9')
        self.post(vs[-1], 'knock', to='ip_host_test', ip='9.9.9.10')
        self.assertTrue(host)


class Shop(HWBase):
    def test_style_items_once_each_into_the_save(self):
        tok = self.user('sh_a')
        self.give(tok, 300)
        self.refused('not_found', self.post, tok, 'buy', item='nope')
        r = self.post(tok, 'buy', item='t_hw_san_bi_ngo')
        self.assertEqual(r['candy'], 260)
        self.refused('owned', self.post, tok, 'buy', item='t_hw_san_bi_ngo')
        self.load(tok)
        self.assertEqual(self.own(tok), {'t_hw_san_bi_ngo': SC.PERMANENT})
        self.load(tok)   # paid once
        self.cmd(tok, 'jr_spend_wear', kind='title', id='t_hw_san_bi_ngo')
        self.assertEqual(sp.style_now(self.state(tok))['t'], 't_hw_san_bi_ngo')
        self.refused('not_enough', self.post, tok, 'buy', item='t_hw_ba_tuoc')
        self.post(tok, 'buy', item='c_hw_bi_ngo')
        self.load(tok)
        self.cmd(tok, 'jr_spend_wear', kind='color', id='c_hw_bi_ngo')
        self.assertEqual(sp.style_now(self.state(tok))['c'], 'c_hw_bi_ngo')
        with self.store.connect() as db:
            st = [r['status'] for r in db.execute("SELECT status FROM live_effects WHERE kind='hween'").fetchall()]
        self.assertEqual(st, ['applied', 'applied'])
        shop = {x['id']: x for x in self.view(tok)['shop']}
        self.assertTrue(shop['t_hw_san_bi_ngo']['owned'])
        self.assertFalse(shop['f_hw_doi']['owned'])

    def test_style_items_cannot_be_bought_with_xu(self):
        tok = self.user('sh_x', wallet=10**6)
        from game.engine import GameError
        with self.assertRaises(GameError):
            self.cmd(tok, 'jr_spend_style', id='t_hw_ba_tuoc', confirm=True)
        self.assertIn('kẹo', sp.style_why(self.state(tok), 'c_hw_bi_ngo'))

    def test_pet_piece(self):
        tok = self.user('sh_p')
        self.give(tok, 60)
        before = len(pw.get(self.state(tok))['it'])
        self.post(tok, 'buy', item='pet_vong_keo')
        self.load(tok)
        items = pw.get(self.state(tok))['it']
        self.assertEqual(len(items), before + 1)
        self.assertEqual((items[-1]['k'], items[-1]['r']), ('vong_keo', 0))
        from game.engine import validate_state
        validate_state(self.state(tok))

    def test_xu_swaps_capped_and_guarded(self):
        tok = self.user('sw_a', wallet=1000)
        self.give(tok, 500)
        for k in range(hw.SWAP_MAX):
            self.post(tok, 'buy', item='xu')
            self.load(tok)
        self.assertEqual(self.wallet(tok), 1000 + hw.SWAP_MAX * hw.SWAP_COINS)
        self.refused('swap_limit', self.post, tok, 'buy', item='xu')
        self.assertEqual(self.candy(tok), 500 - hw.SWAP_MAX * 50)
        young = self.user('sw_young', life=2)
        self.give(young, 100)
        self.refused('too_new', self.post, young, 'buy', item='xu')
        new = self.fresh('sw_new')
        self.give(new, 100)
        self.refused('too_new', self.post, new, 'buy', item='xu')
        self.assertEqual(self.candy(new), 100, 'nothing taken on a refusal')

    def test_xu_swaps_few_accounts_a_network(self):
        toks = [self.user(f'sw_ip{i}') for i in range(hw.SWAP_IPS + 1)]
        for t in toks:
            self.give(t, 100)
        for t in toks[:hw.SWAP_IPS]:
            self.post(t, 'buy', item='xu', ip='7.7.7.7')
        self.refused('swap_ip', self.post, toks[-1], 'buy', item='xu', ip='7.7.7.7')
        self.post(toks[0], 'buy', item='xu', ip='7.7.7.7')   # an account that swapped already keeps its own cap

    def test_concurrent_buys_spend_once(self):
        tok = self.user('sh_c')
        self.give(tok, 100)

        def go(_):
            try:
                return self.post(tok, 'buy', item='f_hw_doi')['item']
            except mr.MarriageError as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            out = list(ex.map(go, range(6)))
        self.assertEqual(out.count('f_hw_doi'), 1, out)
        self.assertEqual(self.candy(tok), 0)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE kind='hween'").fetchone()['n'], 1)

    def test_concurrent_knocks_keep_the_cap(self):
        a = self.user('kk_a')
        for i in range(8):
            self.user(f'kk_h{i}')

        def go(i):
            try:
                return self.post(a, 'knock', to=f'kk_h{i}_test')['n']
            except mr.MarriageError as e:
                return e.code
        with patch.object(hw, 'KNOCKS_DAY', 3), concurrent.futures.ThreadPoolExecutor(8) as ex:
            out = list(ex.map(go, range(8)))
        self.assertEqual(sum(1 for x in out if isinstance(x, int)), 3, out)


class Board(HWBase):
    def test_board_and_top_titles_granted_once(self):
        toks = [self.user(f'bd_{i}') for i in range(12)]
        for i, t in enumerate(toks):
            self.give(t, 10 + i)
        v = self.view(toks[-1])
        self.assertEqual(v['board'][0]['earned'], 21)
        self.assertTrue(v['board'][0]['me'])
        self.assertEqual(v['me']['rank'], 1)
        self.assertEqual(self.view(toks[0])['me']['rank'], 12)
        self.clock.t = hw.END - 1
        self.assertEqual(hw.run_housekeeping(self.store), 0, 'not before the close')
        self.clock.t = hw.END + 2 * M
        hw._swept[0] = 0.0
        self.assertEqual(hw.run_housekeeping(self.store), hw.TOP)
        hw._swept[0] = 0.0
        hw._closed[0] = False
        self.assertEqual(hw.run_housekeeping(self.store), 0, 'exactly once, even from another process')
        for t in toks:
            self.load(t)
        self.assertEqual(self.own(toks[-1]), {'t_hw_vua_keo': SC.PERMANENT, 'f_hw_bi_ngo_vang': SC.PERMANENT})
        self.assertEqual(self.own(toks[2]), {'t_hw_top_keo': SC.PERMANENT})
        self.assertEqual(self.own(toks[1]), {})
        news = mr.news(self.store, 0)
        self.assertTrue(any('Vua Kẹo' in it['text'] for it in news['items']))
        self.assertGreaterEqual(self.view(toks[-1])['me']['candy'], 21, 'candy stays for the grace day')

    def test_spending_never_lowers_the_board(self):
        a = self.user('bs_a')
        self.give(a, 100)
        self.post(a, 'buy', item='f_hw_doi')
        v = self.view(a)
        self.assertEqual((v['me']['candy'], v['me']['earned']), (0, 100))


class AdminAndPrivacy(HWBase):
    def test_admin_view_and_forget(self):
        a, b = self.user('ad_a'), self.user('ad_b')
        self.give(a, 80)
        self.post(a, 'buy', item='xu', ip='5.5.5.5')
        self.post(b, 'knock', to='ad_a_test')
        out = hw.admin_view(self.store)
        self.assertEqual(out['totals']['swaps'], 1)
        self.assertEqual(out['totals']['xu'], hw.SWAP_COINS)
        self.assertEqual(out['swaps'][0]['username'], 'ad_a_test')
        self.assertNotIn('5.5.5.5', str(out))
        self.assertEqual(out['top'][0]['username'], 'ad_a_test')
        hw.forget(self.store, a)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM hw_players WHERE sid=?', (self.sid(a),)).fetchone())
            self.assertIsNone(db.execute('SELECT 1 FROM hw_log WHERE sid=?', (self.sid(a),)).fetchone())

    def test_catalogue_in_step(self):
        for i in C.STYLE_IDS:
            self.assertIn(i, SC.STYLE_ITEMS)
            self.assertEqual(SC.STYLE_ITEMS[i]['price'], 0)
            self.assertIn('kẹo' if not i.startswith(('t_hw_vua', 't_hw_top', 'f_hw_bi_ngo_vang')) else 'Bảng kẹo', SC.STYLE_ITEMS[i]['earn'])
        for it in C.SHOP:
            if it['kind'] == 'style':
                self.assertIn(str(it['cost']), SC.STYLE_ITEMS[it['id']]['earn'])
        from game import pet_wardrobe_content as W
        for p in C.PET_PIECES:
            self.assertEqual(W.ITEM[p]['set'], 'halloween')
        self.assertEqual({k for k, _, _ in C.PLACES} - set(hw.C.PLACE), set())
        import json
        from pathlib import Path
        layout = json.loads((Path(__file__).resolve().parents[1] / 'game' / 'town_layout.json').read_text(encoding='utf-8'))
        amenities = {a['id'] for a in layout['amenities']}
        self.assertEqual({k for k, _, _ in C.PLACES} - amenities, set(), 'every hiding place is a signpost of the 2.5D town')

    def test_apply_refuses_foreign_payloads(self):
        tok = self.user('ap_a')
        sid = self.sid(tok)
        for i, data in enumerate((dict(items=['t_dai_gia']), dict(pet='canh_doi'), dict(coins=10**6), dict())):
            self.store.transaction(lambda db, i=i, data=data: db.execute(
                "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?)",
                (f'hween:bad:{i}', sid, 'hween', data.get('coins') or 1, __import__('json').dumps(data), 1.0)))
        w = self.wallet(tok)
        self.load(tok)
        with self.store.connect() as db:
            self.assertEqual({r['status'] for r in db.execute("SELECT status FROM live_effects WHERE kind='hween'").fetchall()}, {'pending'})
        self.assertEqual(self.wallet(tok), w)
