"""🚨 The police's asset check at the fair (owner 07/10: "công an sẽ đòi chứng minh tài sản ở đâu ra và thu 10% lợi
nhuận của cả hội chợ"): fair profit this edition above the threshold, 10% of the profit made since the last check (never
twice on the same xu), wallet first then the bank account, never below zero, replay-safe."""
import json
from unittest import mock

from game import bank as bk
from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import OPEN, Dice, FairBase, StoreBase, story, loto_dice, winning_rs


def rich(profit=60000, wallet=100000):
    """A player who has won `profit` xu at this fair (the Bảng vàng number), `wallet` in the wallet."""
    s = story(wallet)
    s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition())
    f['stats']['won'] = profit
    return s


class WealthRaid(FairBase):
    def test_takes_ten_percent_of_fair_profit_and_records_it(self):
        self.assertEqual((fh.WEALTH_CHECK_GAP, fh.WEALTH_RAID_P), (7200, .45))   # 07/10: once per 2 hours at most
        self.dice(Dice(draws=[fh.WEALTH_RAID_P - 1e-6]))  # a losing bet (honest dice: no luck draw), then a successful check
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        raid = result['fair']['wealth_raid']
        self.assertTrue(raid['audit'])
        self.assertEqual((raid['gain'], raid['amount'], raid['cash'], raid['bank']), (59999, 5999, 5999, 0))
        self.assertEqual(s['journey']['wallet'], 100000 - 1 - 5999)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 1 + 5999)
        self.assertEqual(fh.money_of(s['journey'])[0], 54000)                  # the board's number
        self.assertEqual(s['journey']['fair_audit'], dict(ed=fh.edition(), base=54000))
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('fair', -5999))
        self.assertIn('tài sản', row['label'])
        self.assertIn('nguồn tài sản', raid['say'])
        self.assertEqual(result['fair']['net'], -1)   # the dice outcome itself is unchanged
        validate_state(s)

    def test_never_twice_on_the_same_profit(self):
        self.dice(Dice(draws=[0]))
        s, first = self.act(rich(), 'fair_bc', bets={'cua': 1})
        self.assertEqual(first['fair']['wealth_raid']['amount'], 5999)
        checked = s['journey']['fair']['wealth_check_at']
        self.clock.t += fh.WEALTH_CHECK_GAP
        self.dice(Dice(draws=[0]))
        s, again = self.act(s, 'fair_bc', bets={'cua': 1})   # no new profit since: nothing, not even the cooldown
        self.assertNotIn('wealth_raid', again['fair'])
        self.assertEqual(s['journey']['fair']['wealth_check_at'], checked)
        s['journey']['fair']['stats']['won'] += 20000            # 20,000 xu more won since the check
        self.dice(Dice(draws=[0]))
        s, third = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(third['fair']['wealth_raid']['gain'], 20000 - 2)
        self.assertEqual(third['fair']['wealth_raid']['amount'], (20000 - 2) // 10)
        self.assertEqual(s['journey']['fair_audit']['base'], fh.money_of(s['journey'])[0])
        validate_state(s)

    def test_wallet_first_then_bank_never_below_zero_no_debt(self):
        s = rich(profit=200000, wallet=5000)
        s['journey']['bank'] = dict(bk.initial(s['journey']['seed'], s['journey']['life_day']), balance=8000)
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        raid = result['fair']['wealth_raid']
        self.assertEqual(raid['due'], 199999 // 10)
        self.assertEqual((raid['cash'], raid['bank'], raid['amount']), (4999, 8000, 12999))
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 0)
        self.assertEqual(s['journey']['bank']['log'][-1]['amt'], -8000)
        self.assertNotIn('fair_cash', s['journey'])               # what neither held is let go: no debt
        self.assertFalse(s['journey']['in_debt'])
        self.assertEqual(s['journey']['fair_audit']['base'], 199999 - 12999)
        validate_state(s)
        s2 = rich(wallet=1)                                        # nothing anywhere: the police let it go
        self.dice(Dice(draws=[0]))
        s2, result = self.act(s2, 'fair_bc', bets={'cua': 1})
        self.assertEqual(result['fair']['wealth_raid']['amount'], 0)
        self.assertEqual(s2['journey']['wallet'], 0)
        validate_state(s2)

    def test_boundary_and_no_penalty_for_large_wallet_alone(self):
        for profit in (0, 50000, 50001):   # 50,001 − the lost xu: not above the threshold
            self.dice(Dice(draws=[0]))
            s, result = self.act(rich(profit=profit), 'fair_bc', bets={'cua': 1})
            self.assertNotIn('wealth_raid', result['fair'])
            self.assertNotIn('wealth_check_at', s['journey']['fair'])
        self.dice(Dice(draws=[fh.WEALTH_RAID_P]))
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertIn('wealth_check_at', s['journey']['fair'])
        self.assertNotIn('fair_audit', s['journey'])

    def test_failed_check_also_waits_two_hours_and_survives_reload(self):
        self.dice(Dice(draws=[fh.WEALTH_RAID_P]))
        s, _ = self.act(rich(), 'fair_bc', bets={'cua': 1})
        checked = s['journey']['fair']['wealth_check_at']
        s = json.loads(json.dumps(s))
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.clock.t = checked + fh.WEALTH_CHECK_GAP - 10
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.clock.t = checked + fh.WEALTH_CHECK_GAP
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertIn('wealth_raid', result['fair'])
        validate_state(s)

    def test_skill_free_games_and_reads_do_not_trigger_checks(self):
        for command, payload in [('fair_kn_start', dict(stake=10)), ('fair_ring_start', {}),
                                 ('fair_oaq_start', dict(lv='kho'))]:
            self.dice(Dice(draws=[0]))
            s, result = self.act(rich(), command, **payload)
            self.assertNotIn('wealth_raid', result['fair'])
            self.assertNotIn('wealth_check_at', s['journey']['fair'])

    def test_profit_of_the_whole_fair_counts_across_days(self):
        s = rich()
        self.clock.t += 86400   # a new day: today's net is 0, the fair's profit is not
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(result['fair']['wealth_raid']['amount'], 5999)
        self.assertEqual(s['journey']['fair']['net'], -1 - 5999)
        validate_state(s)

    def test_an_older_edition_s_mark_does_not_count(self):
        s = rich()
        s['journey']['fair_audit'] = dict(ed='fair20250101', base=59999)
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(result['fair']['wealth_raid']['amount'], 5999)

    def test_xd_normal_raid_does_not_double_charge(self):
        self.dice(Dice(draws=[0, 0]))
        s, result = self.act(rich(), 'fair_xd', stake=10, side='chan')
        self.assertTrue(result['fair']['raid'])
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertEqual(s['journey']['wallet'], 100000 - 13)

    def test_saved_fields_validation(self):
        for value in (-1, True, '123', 10**12):
            s = rich()
            s['journey']['fair']['wealth_check_at'] = value
            with self.assertRaises(GameError):
                validate_state(s)
        for bad in ([], dict(ed=fh.edition()), dict(ed=fh.edition(), base='1'), dict(ed=fh.edition(), base=10**11),
                    dict(ed=1, base=0), dict(ed='x' * 13, base=0), dict(ed=fh.edition(), base=0, more=1)):
            s = rich()
            s['journey']['fair_audit'] = bad
            with self.assertRaises(GameError, msg=bad):
                validate_state(s)
        s = rich()
        s['journey']['fair_audit'] = dict(ed=fh.edition(), base=-5)
        validate_state(s)

    def test_loto_claim_is_checked_after_paying_prize(self):
        slot = int(self.clock.t // 60) + 1
        self.clock.t = slot * 60 + 1
        self.dice(loto_dice(winning_rs(True, slot), True))
        s, _ = self.act(rich(), 'fair_loto_buy')
        self.assertNotIn('wealth_check_at', s['journey']['fair'])
        rv = fh.round_view(s['journey']['fair']['loto'])
        positions = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(positions[n] for n in rv['card'][i]))
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_loto_kinh', row=row, at=max(positions[n] for n in rv['card'][row]) + 1)
        self.assertTrue(result['fair']['won'])
        self.assertEqual(result['fair']['wealth_raid']['amount'], (60000 - 5 + result['fair']['prize']) * 10 // 100)


class WealthRaidReplay(StoreBase):
    def test_retry_cannot_charge_wallet_or_redraw_the_check(self):
        from game import marriage as mr
        tok = self.player('Lan', wallet=100000)
        def prepare(s):
            s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition())
            f['stats']['won'] = 60000
        mr._mutate(self.store, {self.store.key(tok): prepare})
        self.dice(Dice(draws=[0]))
        args = (tok, 'wealth-raid-retry-01', self.store.read(tok)[1], None, 'fair_bc', {'bets': {'cua': 1}})
        first = self.store.command(*args)
        saved = self.store.read(tok)[0]['journey']
        self.assertEqual(first['result']['fair']['wealth_raid']['amount'], 5999)
        with mock.patch.object(fh, '_wealth_raid', side_effect=AssertionError('Replay must not check again')):
            replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        after = self.store.read(tok)[0]['journey']
        self.assertEqual(after['wallet'], saved['wallet'])
        self.assertEqual(after['fair_audit'], saved['fair_audit'])
