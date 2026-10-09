"""👴 Ông Hai's table and the police (game/fair_hai.py; owner 09/10: "nếu thắng nhiều thì cho công an bắt thu tiền là
được"): two wins in a row, or three within a day, bring the police at once: they take back every win of that run
(wallet first, then the bank account, never below zero, never twice the same win), then the Chợ đen arrest (the fine,
the trại tạm giữ); a lost, drawn or given-up game breaks the run; HAI_DAY games with him a Vietnam day; Bé Bi and the
paid stalls' police are untouched; the save validates."""
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

    def test_one_win_is_paid_and_kept(self):
        s = self.inside(1000)
        s, r = self.win(s)
        self.assertEqual(r['fair']['end']['prize'], PRIZE)
        self.assertNotIn('arrest', r['fair'])
        self.assertEqual(s['journey']['wallet'], 1000 + PRIZE)
        h = s['journey'][hai.KEY]
        self.assertEqual((h['s'], [x for _, x in h['w']], h['n']), (1, [PRIZE], 1))
        validate_state(s)

    def test_two_wins_in_a_row_are_taken_back_with_the_fine_and_the_cell(self):
        s = self.inside(50000)
        s, r = self.win(s)
        s, r = self.win(s)
        a = r['fair']['arrest']
        self.assertEqual((a['seized'], a['stake'], a['say']), (2 * PRIZE, 2 * PRIZE, hai.SAY))
        self.assertEqual(a['fine'], 50000 * bm.FINE_PCT // 100)            # the fine: on the wallet once the wins are gone
        self.assertEqual(s['journey']['wallet'], 50000 - a['fine'])
        self.assertEqual(a['jail'], bm.JAIL_DAYS)
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        self.assertIn('Công an ập vào bàn Ông Hai', r['message'])
        self.assertIn('tịch thu 20.000 xu tiền thắng, nộp phạt 15.000 xu', r['message'])
        self.assertEqual(s['journey'][hai.KEY]['s'], 0)
        self.assertEqual(s['journey'][hai.KEY]['w'], [])
        self.assertEqual(fh.money_of(s['journey'])[0], 2 * PRIZE - 2 * PRIZE - a['fine'])   # the Bảng vàng: nothing won
        labels = [row['label'] for row in s['journey']['history'][-4:]]
        self.assertIn(hai.SEIZE_LABEL, labels)
        validate_state(s)

    def test_a_run_broken_by_a_lost_game_then_the_third_win_in_a_day(self):
        s = self.inside(0)
        s, r = self.win(s)
        s = self.give_up(s)                       # the run is broken
        self.assertEqual(s['journey'][hai.KEY]['s'], 0)
        s, r = self.win(s)
        self.assertNotIn('arrest', r['fair'])     # two wins today, not in a row
        s = self.give_up(s)
        s, r = self.win(s)                        # the third within a day
        a = r['fair']['arrest']
        self.assertEqual(a['seized'], 3 * PRIZE)
        self.assertEqual(a['fine'], 0)            # the wallet held only the wins
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertIn('tịch thu 30.000 xu tiền thắng.', r['message'])
        validate_state(s)

    def test_only_the_wins_of_the_last_day_are_taken(self):
        s = self.inside(0)
        s, r = self.win(s)
        self.tick(hai.WINDOW + 60)                # (the trại tạm giữ is not involved: no arrest yet)
        s, r = self.win(s)                        # still two in a row: the police, but only for this win
        a = r['fair']['arrest']
        self.assertEqual(a['seized'], PRIZE)
        self.assertEqual(s['journey']['wallet'], PRIZE - a['fine'])   # the first win stays (less the fine)
        validate_state(s)

    def test_never_below_zero_wallet_then_bank(self):
        s = self.inside(0)
        s, r = self.win(s)
        s['journey']['wallet'] = 3000             # spent most of it
        s['journey']['bank'] = dict(bk.initial(s['journey']['seed'], s['journey']['life_day']), balance=5000)
        validate_state(s)
        s, r = self.win(s)
        a = r['fair']['arrest']
        self.assertEqual(a['seized'], 3000 + PRIZE + 5000)   # 2 wins due, the wallet and the account hold less
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance'], a['fine']), (0, 0, 0))
        self.assertFalse(s['journey']['in_debt'])
        self.assertEqual(s['journey']['bank']['log'][-1]['amt'], -5000)
        validate_state(s)

    def test_a_wallet_in_debt_stays_where_it_was(self):
        s = self.inside(0)
        s, r = self.win(s)
        s['journey']['wallet'] = -20000
        s['journey']['in_debt'] = True
        validate_state(s)
        s, r = self.win(s)                        # the prize lands in the debt (−10.000): nothing to take
        a = r['fair']['arrest']
        self.assertEqual((a['seized'], a['fine']), (0, 0))
        self.assertEqual(s['journey']['wallet'], -20000 + PRIZE)
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
