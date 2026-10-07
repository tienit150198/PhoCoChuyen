"""🚨 The police's asset check at the fair (owner 07/10: "công an sẽ đòi chứng minh tài sản ở đâu ra và thu 10% lợi
nhuận của cả hội chợ"), a rule of its own next to the 1.9.9 wealth raid (tests/test_fair_wealth_raid.py, unchanged):
fair profit this edition above the threshold, 10% of the profit made since the last check (never twice on the same
xu), wallet first then the bank account, never below zero, at most once per 2 hours (45%), replay-safe. On a round
where both are due, the raid comes first and the check counts the profit left after it."""
import json
from unittest import mock

from game import bank as bk
from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import OPEN, Dice, FairBase, StoreBase, story, loto_dice, winning_rs


def rich(profit=60000, wallet=100000, net=0):
    """A player who has won `profit` xu at this fair (the Bảng vàng number), `wallet` in the wallet, `net` today."""
    s = story(wallet)
    s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), net=net)
    f['stats']['won'] = profit
    return s


class AssetAudit(FairBase):
    def test_the_rules(self):
        self.assertEqual((fh.AUDIT_FROM, fh.AUDIT_GAP, fh.AUDIT_P, fh.AUDIT_PCT), (50000, 7200, .225, 10))   # 07/10: half of 45%
        self.assertEqual((fh.WEALTH_THRESHOLD, fh.WEALTH_CHECK_GAP, fh.WEALTH_RAID_P), (50000, 1800, .35))   # 1.9.9's .70 halved

    def test_takes_ten_percent_of_fair_profit_and_records_it(self):
        self.dice(Dice(draws=[fh.AUDIT_P - 1e-6]))  # a losing bet (honest dice: no luck draw), then a successful check
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        audit = result['fair']['audit']
        self.assertNotIn('wealth_raid', result['fair'])                    # today's net 0: the raid is not due
        self.assertEqual((audit['gain'], audit['amount'], audit['cash'], audit['bank']), (59999, 5999, 5999, 0))
        self.assertFalse(audit['after_raid'])
        self.assertEqual(s['journey']['wallet'], 100000 - 1 - 5999)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 1 + 5999)
        self.assertEqual(fh.money_of(s['journey'])[0], 54000)                  # the board's number
        self.assertEqual(s['journey']['fair_audit'], dict(ed=fh.edition(), base=54000, at=int(self.clock.t)))
        self.assertNotIn('wealth_check_at', s['journey']['fair'])            # the raid's own state is untouched
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('fair', -5999))
        self.assertIn('tài sản', row['label'])
        self.assertIn('nguồn tài sản', audit['say'])
        self.assertIn(audit['message'], result['message'])
        self.assertEqual(result['fair']['net'], -1)   # the dice outcome itself is unchanged
        validate_state(s)

    def test_never_twice_on_the_same_profit(self):
        self.dice(Dice(draws=[0]))
        s, first = self.act(rich(), 'fair_bc', bets={'cua': 1})
        self.assertEqual(first['fair']['audit']['amount'], 5999)
        checked = s['journey']['fair_audit']['at']
        self.clock.t += fh.AUDIT_GAP
        self.dice(Dice(draws=[0]))
        s, again = self.act(s, 'fair_bc', bets={'cua': 1})   # no new profit since: nothing, not even the cooldown
        self.assertNotIn('audit', again['fair'])
        self.assertEqual(s['journey']['fair_audit']['at'], checked)
        s['journey']['fair']['stats']['won'] += 20000            # 20,000 xu more won since the check
        self.dice(Dice(draws=[0]))
        s, third = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(third['fair']['audit']['gain'], 20000 - 2)
        self.assertEqual(third['fair']['audit']['amount'], (20000 - 2) // 10)
        self.assertEqual(s['journey']['fair_audit']['base'], fh.money_of(s['journey'])[0])
        validate_state(s)

    def test_wallet_first_then_bank_never_below_zero_no_debt(self):
        s = rich(profit=200000, wallet=5000)
        s['journey']['bank'] = dict(bk.initial(s['journey']['seed'], s['journey']['life_day']), balance=8000)
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        audit = result['fair']['audit']
        self.assertEqual(audit['due'], 199999 // 10)
        self.assertEqual((audit['cash'], audit['bank'], audit['amount']), (4999, 8000, 12999))
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
        self.assertEqual(result['fair']['audit']['amount'], 0)
        self.assertEqual(s2['journey']['wallet'], 0)
        validate_state(s2)

    def test_boundary_and_a_failed_draw(self):
        for profit in (0, 50000, 50001):   # 50,001 − the lost xu: not above the threshold
            self.dice(Dice(draws=[0]))
            s, result = self.act(rich(profit=profit), 'fair_bc', bets={'cua': 1})
            self.assertNotIn('audit', result['fair'])
            self.assertNotIn('fair_audit', s['journey'])
        self.dice(Dice(draws=[fh.AUDIT_P]))
        s, result = self.act(rich(), 'fair_bc', bets={'cua': 1})
        self.assertNotIn('audit', result['fair'])
        self.assertEqual(s['journey']['fair_audit'], dict(ed=fh.edition(), base=0, at=int(self.clock.t)))
        validate_state(s)

    def test_failed_check_also_waits_two_hours_and_survives_reload(self):
        self.dice(Dice(draws=[fh.AUDIT_P]))
        s, _ = self.act(rich(), 'fair_bc', bets={'cua': 1})
        checked = s['journey']['fair_audit']['at']
        s = json.loads(json.dumps(s))
        self.clock.t = checked + fh.AUDIT_GAP - 10
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('audit', result['fair'])
        self.clock.t = checked + fh.AUDIT_GAP
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertIn('audit', result['fair'])
        validate_state(s)

    def test_skill_free_games_and_reads_do_not_trigger_checks(self):
        for command, payload in [('fair_kn_start', dict(stake=10)), ('fair_ring_start', {}),
                                 ('fair_oaq_start', dict(lv='kho'))]:
            self.dice(Dice(draws=[0]))
            s, result = self.act(rich(), command, **payload)
            self.assertNotIn('audit', result['fair'])
            self.assertNotIn('fair_audit', s['journey'])

    def test_profit_of_the_whole_fair_counts_across_days(self):
        s = rich()
        self.clock.t += 86400   # a new day: today's net is 0, the fair's profit is not
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(result['fair']['audit']['amount'], 5999)
        validate_state(s)

    def test_an_older_edition_s_mark_does_not_count(self):
        s = rich()
        s['journey']['fair_audit'] = dict(ed='fair20250101', base=59999, at=0)
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(result['fair']['audit']['amount'], 5999)

    def test_xd_normal_raid_charges_nothing_more(self):
        self.dice(Dice(draws=[0, 0]))
        s, result = self.act(rich(net=60000), 'fair_xd', stake=10, side='chan')
        self.assertTrue(result['fair']['raid'])
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertNotIn('audit', result['fair'])
        self.assertEqual(s['journey']['wallet'], 100000 - 13)

    def test_saved_fields_validation(self):
        for bad in ([], dict(ed=fh.edition()), dict(ed=fh.edition(), base=0), dict(ed=fh.edition(), base='1', at=0),
                    dict(ed=fh.edition(), base=10**11, at=0), dict(ed=1, base=0, at=0), dict(ed='x' * 13, base=0, at=0),
                    dict(ed=fh.edition(), base=0, at=-1), dict(ed=fh.edition(), base=0, at=0, more=1)):
            s = rich()
            s['journey']['fair_audit'] = bad
            with self.assertRaises(GameError, msg=bad):
                validate_state(s)
        s = rich()
        s['journey']['fair_audit'] = dict(ed=fh.edition(), base=-5, at=0)
        validate_state(s)

    def test_loto_claim_is_checked_after_paying_prize(self):
        slot = int(self.clock.t // 60) + 1
        self.clock.t = slot * 60 + 1
        self.dice(loto_dice(winning_rs(True, slot), True))
        s, _ = self.act(rich(), 'fair_loto_buy')
        self.assertNotIn('fair_audit', s['journey'])
        rv = fh.round_view(s['journey']['fair']['loto'])
        positions = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(positions[n] for n in rv['card'][i]))
        self.dice(Dice(draws=[0]))
        s, result = self.act(s, 'fair_loto_kinh', row=row, at=max(positions[n] for n in rv['card'][row]) + 1)
        self.assertTrue(result['fair']['won'])
        self.assertEqual(result['fair']['audit']['amount'], (60000 - 5 + result['fair']['prize']) * 10 // 100)


class RaidThenAudit(FairBase):
    """Both rules on one round: the 1.9.9 raid (30% of the wallet, today's net) first, then the asset check (10% of the
    fair profit made since its last check, which the raid has already lowered): never the same xu twice."""

    def test_both_on_one_round_raid_first(self):
        s = rich(profit=200000, net=60000)
        self.dice(Dice(draws=[0, 0]))   # the raid's draw, then the check's
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        raid, audit = result['fair']['wealth_raid'], result['fair']['audit']
        self.assertEqual(raid['amount'], 29999)                            # 30% of 99,999, exactly as 1.9.9
        self.assertEqual(raid['wallet'], 70000)
        profit = 200000 - 1 - 29999                                        # what the raid took is out of the profit
        self.assertEqual((audit['gain'], audit['amount'], audit['cash']), (profit, profit // 10, profit // 10))
        self.assertTrue(audit['after_raid'])
        self.assertEqual(audit['wallet'], 70000 - profit // 10)
        self.assertEqual(s['journey']['wallet'], 70000 - profit // 10)
        self.assertEqual(fh.money_of(s['journey'])[0], profit - profit // 10)
        self.assertEqual(s['journey']['fair_audit']['base'], profit - profit // 10)
        self.assertEqual([r['amount'] for r in s['journey']['history'][-2:]], [-29999, -(profit // 10)])
        self.assertLess(result['message'].index(raid['message']), result['message'].index(audit['message']))
        validate_state(s)

    def test_each_keeps_its_own_cooldown(self):
        s = rich(profit=200000, net=60000)
        self.dice(Dice(draws=[0, 0]))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.clock.t += fh.WEALTH_CHECK_GAP                               # 30 minutes: the raid again, not the check
        s['journey']['fair']['net'] = 60000
        s['journey']['fair']['stats']['won'] += 50000
        self.dice(Dice(draws=[0, 0]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertIn('wealth_raid', result['fair'])
        self.assertNotIn('audit', result['fair'])
        validate_state(s)


class AssetAuditReplay(StoreBase):
    def test_retry_cannot_charge_wallet_or_redraw_the_check(self):
        from game import marriage as mr
        tok = self.player('Lan', wallet=100000)
        def prepare(s):
            s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition())
            f['stats']['won'] = 60000
        mr._mutate(self.store, {self.store.key(tok): prepare})
        self.dice(Dice(draws=[0]))
        args = (tok, 'asset-audit-retry-01', self.store.read(tok)[1], None, 'fair_bc', {'bets': {'cua': 1}})
        first = self.store.command(*args)
        saved = self.store.read(tok)[0]['journey']
        self.assertEqual(first['result']['fair']['audit']['amount'], 5999)
        with mock.patch.object(fh, '_asset_audit', side_effect=AssertionError('Replay must not check again')), \
                mock.patch.object(fh, '_wealth_raid', side_effect=AssertionError('Replay must not check again')):
            replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        after = self.store.read(tok)[0]['journey']
        self.assertEqual(after['wallet'], saved['wallet'])
        self.assertEqual(after['fair_audit'], saved['fair_audit'])
