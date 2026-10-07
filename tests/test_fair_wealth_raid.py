"""Large fair winnings: bounded checks, wallet seizure and ledger consistency."""
import json
from unittest import mock

from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import OPEN, Dice, FairBase, StoreBase, story, loto_dice, winning_rs


def rich(net=60000, wallet=100000):
    s = story(wallet)
    s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), net=net)
    return s


class WealthRaid(FairBase):
    def test_seizes_thirty_percent_of_wallet_after_round_and_records_it(self):
        self.assertEqual(fh.WEALTH_RAID_P, .35)   # 07/10: half of 1.9.9's .70 (gap and 30% unchanged)
        self.dice(Dice(draws=[fh.WEALTH_RAID_P - 1e-6]))  # losing bet (honest dice: no luck draw) then successful check
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        raid = result['fair']['wealth_raid']
        self.assertEqual(raid['amount'], 29999)  # 30% of 99,999, whole xu
        self.assertEqual(s['journey']['wallet'], 70000)
        self.assertEqual(s['journey']['fair']['net'], 30000)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 30000)
        row = s['journey']['history'][-1]
        self.assertEqual(row['amount'], -29999)
        self.assertIn('kiểm tra', row['label'])
        self.assertEqual(result['fair']['net'], -1)  # visual dice outcome is unchanged
        validate_state(s)

    def test_boundary_and_no_penalty_for_large_wallet_alone(self):
        for net in (0, 50000, 50001):
            self.dice(Dice(draws=[0]))
            s, result = self.act(rich(net=net), 'fair_bc', bets={'cua': 1})
            self.assertNotIn('wealth_raid', result['fair'])
            self.assertNotIn('wealth_check_at', s['journey']['fair'])
        self.dice(Dice(draws=[fh.WEALTH_RAID_P]))
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertIn('wealth_check_at', s['journey']['fair'])

    def test_failed_check_also_waits_thirty_minutes_and_survives_reload(self):
        self.dice(Dice(draws=[fh.WEALTH_RAID_P]))
        s, _ = self.act(rich(), 'fair_bc', bets={'cua': 1})
        checked = s['journey']['fair']['wealth_check_at']
        s = json.loads(json.dumps(s))
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.clock.t = checked + 1800
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

    def test_new_day_clears_eligibility_and_wallet_never_goes_negative(self):
        s = rich()
        self.clock.t += 86400
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('wealth_raid', result['fair'])
        self.dice(Dice(draws=[0]))
        self.clock.t = OPEN
        s, result = self.act(rich(wallet=1), 'fair_bc', bets={'cua': 1})
        self.assertEqual(s['journey']['wallet'], 0)
        validate_state(s)

    def test_xd_normal_raid_does_not_double_charge(self):
        self.dice(Dice(draws=[0, 0]))
        s, result = self.act(rich(), 'fair_xd', stake=10, side='chan')
        self.assertTrue(result['fair']['raid'])
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertEqual(s['journey']['wallet'], 100000 - 13)

    def test_check_timestamp_validation(self):
        for value in (-1, True, '123', 10**12):
            s = rich()
            s['journey']['fair']['wealth_check_at'] = value
            with self.assertRaises(GameError):
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
        self.assertEqual(result['fair']['wealth_raid']['amount'], (100000 - 5 + result['fair']['prize']) * 30 // 100)


class WealthRaidReplay(StoreBase):
    def test_retry_cannot_charge_wallet_or_redraw_the_check(self):
        from game import marriage as mr
        tok = self.player('Lan', wallet=100000)
        def prepare(s):
            s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), net=60000)
        mr._mutate(self.store, {self.store.key(tok): prepare})
        self.dice(Dice(draws=[0]))
        args = (tok, 'wealth-raid-retry-01', self.store.read(tok)[1], None, 'fair_bc', {'bets': {'cua': 1}})
        first = self.store.command(*args)
        wallet = self.store.read(tok)[0]['journey']['wallet']
        self.assertEqual(first['result']['fair']['wealth_raid']['amount'], 29999)
        with mock.patch.object(fh, '_wealth_raid', side_effect=AssertionError('Replay must not check again')):
            replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        self.assertEqual(self.store.read(tok)[0]['journey']['wallet'], wallet)
