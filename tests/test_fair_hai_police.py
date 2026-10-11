"""👴 Ông Hai's table and the police (game/fair_hai.py; owner 11/10: "ô ăn quan nếu thắng trên 50 ván thì bị bắt vì sử
dụng thiết bị hỗ trợ, và phạt 50% ví (tổng tiền, có trừ cả ví ngân hàng)"): every win keeps its prize and is counted; the
51st brings a 50 % fine on the wallet and the bank (never below zero) and the trại tạm giữ; no games-a-day limit; Bé Bi
and the paid stalls' police are untouched; the save validates."""
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

    def test_a_win_keeps_its_prize_and_is_counted(self):
        """Owner 11/10: a win is no longer fined by itself; it is counted (journey[hai.WINS_KEY])."""
        s = self.inside(50000)
        s, r = self.win(s)
        self.assertNotIn('arrest', r['fair'])
        self.assertEqual(s['journey']['wallet'], 50000 + PRIZE)
        self.assertEqual(s['journey'][hai.WINS_KEY], {'n': 1})
        self.assertNotIn('jail', s['journey'])
        validate_state(s)

    def test_the_51st_win_brings_the_device_fine_and_the_cell(self):
        """Owner 11/10: past hai.DEVICE_WINS wins, "thiết bị hỗ trợ": the prize stays, 50% of the wallet and the bank,
        the trại tạm giữ; then the count starts again."""
        self.assertEqual((hai.DEVICE_WINS, hai.DEVICE_PCT), (50, 50))
        s = self.inside(50000)
        s['journey'][hai.WINS_KEY] = {'n': hai.DEVICE_WINS - 1}
        validate_state(s)
        s, r = self.win(s)   # the 50th: still free
        self.assertNotIn('arrest', r['fair'])
        self.assertEqual(s['journey'][hai.WINS_KEY], {'n': hai.DEVICE_WINS})
        s, r = self.win(s)   # the 51st
        a = r['fair']['arrest']
        total = 50000 + 2 * PRIZE
        self.assertEqual((a['game'], a['say'], a['seized'], a['jail']), ('oaq', hai.SAY_DEVICE, 0, bm.JAIL_DAYS))
        self.assertEqual(a['fine'], total * 50 // 100)
        self.assertEqual(s['journey']['wallet'], total - a['fine'])
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        self.assertEqual(s['journey'][hai.WINS_KEY], {'n': 0})
        self.assertIn('thiết bị hỗ trợ', r['message'])
        self.assertNotIn('thiết bị thứ ba', r['message'])
        last = s['journey']['history'][-1]
        self.assertEqual((last['amount'], last['label']), (-a['fine'], hai.FINE_LABEL))
        validate_state(s)

    def test_the_device_fine_takes_the_bank_too(self):
        """Half of wallet + bank: the wallet first, then the bank account (no loss_limits ceiling)."""
        s = self.inside(0)
        j = s['journey']
        j['bank'] = bk.initial(j['seed'], j['life_day'])
        j['bank']['balance'] = 100000
        j[hai.WINS_KEY] = {'n': hai.DEVICE_WINS}
        validate_state(s)
        s, r = self.win(s)
        fine = (PRIZE + 100000) // 2
        self.assertEqual(r['fair']['arrest']['fine'], fine)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(bk.get(s)['balance'], 100000 - (fine - PRIZE))
        self.assertEqual(s['journey']['fair']['stats']['lost'], fine)
        validate_state(s)

    def test_be_bi_and_draws_never_bring_them(self):
        s = self.inside(0)
        for _ in range(4):
            s, r = self.win(s, 'de')
            self.assertNotIn('arrest', r['fair'])
        self.assertNotIn(hai.KEY, s['journey'])

    def test_no_games_a_day_limit(self):
        """Owner 11/10 "không giới hạn số ván": past the former HAI_DAY games a day he still plays."""
        s = self.inside(0)
        for _ in range(hai.HAI_DAY + 5):
            self.tick(30)
            s, r = self.act(s, 'fair_oaq_start', lv='kho')
        self.assertEqual(s['journey'][hai.KEY]['n'], hai.HAI_DAY + 5)   # still counted (legacy counter)
        self.assertTrue(hai.can_start(s['journey'], fh.vn_date(self.t)))
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
        self.assertEqual(s['journey'][hai.WINS_KEY], {'n': 1})
        for bad in ({'n': -1}, {'n': hai.DEVICE_WINS + 1}, {'n': '1'}, {'n': 1, 'd': ''}, {}, [], 1):
            t = dict(s, journey=dict(s['journey'], **{hai.WINS_KEY: bad}))
            with self.subTest(bad=bad), self.assertRaises(Exception):
                validate_state(t)
