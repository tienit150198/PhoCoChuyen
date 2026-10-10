"""👴 Ông Hai's table and the police (game/fair_hai.py; owner 10/10: "nếu chơi thắng ông Hai thì bị bắt và phạt vì tội sử
dụng thiết bị thứ 3, bỏ tù luôn và phạt 30 - 50% tiền; còn ai thắng vẫn thắng bình thường"): every win keeps its prize,
then a 30–50 % fine on the wallet and the bank account (never below zero) and the trại tạm giữ; HAI_DAY games with him a
Vietnam day; Bé Bi and the paid stalls' police are untouched; the save validates."""
from unittest import mock

from game import bank as bk
from game import fair as fh
from game import fair_bm as bm
from game import fair_hai as hai
from game import fair_oaq as oaq
from game.engine import validate_state
from tests.test_fair import greedy_move, weakest
from tests.test_fair_watch import WatchBase

PRIZE = fh.OAQ_PRIZE['kho']


class HaiPolice(WatchBase):
    def win(self, s, lv='kho'):
        """A whole game Ông Hai (or Bé Bi) gives away: the final command's result."""
        with mock.patch.object(oaq, 'ai_move', weakest):
            self.tick(30)
            s, r = self.act(s, 'fair_oaq_start', lv=lv)
            while s['journey']['fair']['oaq']['stage'] == 'play':
                self.tick(3)
                c, d = greedy_move(s['journey']['fair']['oaq']['g'])
                s, r = self.act(s, 'fair_oaq_move', cell=c, dir=d, ply=s['journey']['fair']['oaq']['g']['ply'])
                if 'arrest' in r['fair']:
                    break
        return s, r

    def give_up(self, s):
        self.tick(30)
        s, _ = self.act(s, 'fair_oaq_start', lv='kho')
        self.tick(5)
        s, _ = self.act(s, 'fair_oaq_quit')
        return s

    def test_a_win_keeps_its_prize_then_the_device_fine_and_the_cell(self):
        """Owner 10/10: a win against Ông Hai = a third device: the prize stays, a 30–50 % fine on the wallet and the
        bank account, the trại tạm giữ."""
        s = self.inside(50000)
        with mock.patch.object(bm._rng, 'randint', lambda lo, hi: 40):
            s, r = self.win(s)
        a = r['fair']['arrest']
        self.assertEqual((a['say'], a['seized'], a['jail']), (hai.SAY_DEVICE, 0, bm.JAIL_DAYS))
        self.assertEqual(a['fine'], (50000 + PRIZE) * 40 // 100)
        self.assertEqual(s['journey']['wallet'], 50000 + PRIZE - a['fine'])
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        self.assertIn('thiết bị thứ ba', r['message'])
        validate_state(s)

    def test_the_fine_is_between_30_and_50_percent(self):
        for pct in (hai.FINE_LO, hai.FINE_HI):
            s = self.inside(10000)
            with mock.patch.object(bm._rng, 'randint', lambda lo, hi, pct=pct: pct):
                s, r = self.win(s)
            self.assertEqual(r['fair']['arrest']['fine'], (10000 + PRIZE) * pct // 100)

    def test_the_bank_account_pays_what_the_wallet_cannot_never_below_zero(self):
        s = self.inside(0)
        b = s['journey'].get('bank')
        if not b:
            self.skipTest('no bank on this save')
        b['balance'] = 20000
        with mock.patch.object(bm._rng, 'randint', lambda lo, hi: 50):
            s, r = self.win(s)
        a = r['fair']['arrest']
        self.assertEqual(a['fine'], (PRIZE + 20000) // 2)
        self.assertGreaterEqual(s['journey']['wallet'], 0)
        self.assertGreaterEqual(bk.get(s)['balance'], 0)
        validate_state(s)

    def test_be_bi_and_draws_never_bring_them(self):
        s = self.inside(0)
        for _ in range(4):
            s, r = self.win(s, 'de')
            self.assertNotIn('arrest', r['fair'])
        self.assertNotIn(hai.KEY, s['journey'])

    def test_games_a_day(self):
        s = self.inside(0)
        for _ in range(hai.HAI_DAY):
            self.tick(30)
            s, r = self.act(s, 'fair_oaq_start', lv='kho')
        self.tick(30)
        e = self.refused(s, 'fair_oaq_start', 'fair_oaq_tired', lv='kho')
        self.assertEqual(str(e), hai.TIRED)
        s, r = self.act(s, 'fair_oaq_start', lv='de')   # Bé Bi still plays
        self.tick(24 * 3600)                             # the next Vietnam day
        s, r = self.act(s, 'fair_oaq_start', lv='kho')
        self.assertEqual(s['journey'][hai.KEY]['n'], 1)
        validate_state(s)

    def test_without_the_chợ_đen_police_no_arrest(self):
        s = self.inside(0)
        with mock.patch.dict('os.environ', {'MNL_BM_OFF': '1'}):
            s, r = self.win(s)
            s, r = self.win(s)
        self.assertNotIn('arrest', r['fair'])
        self.assertEqual(s['journey']['wallet'], 2 * PRIZE)
        self.assertEqual(s['journey'][hai.KEY]['w'], [])   # the run is over all the same: never taken later

    def test_the_paid_stalls_police_are_unchanged(self):
        self.assertEqual((fh.WEALTH_RAID_P, fh.WEALTH_THRESHOLD, fh.WEALTH_CHECK_GAP), (.35, 50000, 1800))
        self.assertEqual((fh.AUDIT_PCT, fh.AUDIT_P, fh.AUDIT_GAP, fh.AUDIT_FROM), (10, .225, 7200, 50000))
        self.assertEqual((fh.LOC_MULT, fh.LOC_GAP), (10, 3600))
        s = self.inside(0)
        s, r = self.win(s)
        self.assertNotIn('wealth_raid', r['fair'])
        self.assertNotIn('audit', r['fair'])

    def test_bad_saves_are_refused(self):
        s = self.inside(0)
        s, _ = self.win(s)
        for bad in (dict(d='', n=0, s=0), dict(d='', n=-1, s=0, w=[]), dict(d='', n=0, s=0, w=[[1]]),
                    dict(d='', n=0, s=0, w=[[1, 2]] * (hai.W_MAX + 1)), [], dict(d='x' * 11, n=0, s=0, w=[])):
            t = dict(s, journey=dict(s['journey'], **{hai.KEY: bad}))
            with self.subTest(bad=bad), self.assertRaises(Exception):
                validate_state(t)
