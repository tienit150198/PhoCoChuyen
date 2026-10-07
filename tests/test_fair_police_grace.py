"""🚓 A quiet start at the fair (B6, owner 07/10): chat said "vừa vào bị tóm", "tay đầu tiên bị tóm luôn". Time away
counted towards both police cooldowns, so the first paid round after a break rolled the 30% raid and the 10% asset
check at once. Now neither runs in a fair session's first GRACE_S seconds or first GRACE_ROUNDS paid rounds, whichever
ends LATER; a session starts after SESSION_GAP away. Odds and gaps stay as 1.9.12; the xóc đĩa's own per-round raid
(dẹp chiếu) is not touched."""
import json
from unittest import mock

from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import OPEN, Dice, FairBase, story


def rich(profit=200000, wallet=100000, net=60000):
    """Both checks due: today's net above the raid's threshold, fair profit above the asset check's."""
    s = story(wallet)
    s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), net=net)
    f['stats']['won'] = profit
    return s


class QuietStart(FairBase):
    def setUp(self):
        super().setUp()
        for name, value in (('GRACE_S', 600), ('GRACE_ROUNDS', 20)):   # FairBase turns them off for the other tests
            p = mock.patch.object(fh, name, value)
            p.start()
            self.addCleanup(p.stop)

    def bc(self, s, draws=(0, 0)):
        self.dice(Dice(draws=list(draws)))
        return self.act(s, 'fair_bc', bets={'cua': 1})

    def test_the_rules(self):
        self.assertEqual((fh.SESSION_GAP, fh.GRACE_S, fh.GRACE_ROUNDS), (1800, 600, 20))
        # 1.9.12's odds and gaps, unchanged.
        self.assertEqual((fh.WEALTH_RAID_P, fh.WEALTH_CHECK_GAP, fh.AUDIT_P, fh.AUDIT_GAP, fh.RAID_PCT), (.35, 1800, .225, 7200, .88))

    def test_the_first_round_back_is_never_checked(self):
        s, result = self.bc(rich())
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertNotIn('audit', result['fair'])
        j = s['journey']
        self.assertEqual(j['wallet'], 100000 - 1)                     # only the lost bet
        self.assertNotIn('wealth_check_at', j['fair'])                # no cooldown spent either
        self.assertNotIn(fh.AUDIT_KEY, j)
        self.assertEqual(j[fh.SESS_KEY], dict(at=int(self.clock.t), n=1, ls=int(self.clock.t)))
        validate_state(s)

    def test_twenty_rounds_and_ten_minutes_whichever_later(self):
        s = rich()
        for _ in range(fh.GRACE_ROUNDS + 5):                          # 25 quick rounds, well inside 10 minutes
            s, result = self.bc(s)
            self.assertNotIn('wealth_raid', result['fair'])
            self.assertNotIn('audit', result['fair'])
        start = s['journey'][fh.SESS_KEY]['at']
        self.assertLess(self.clock.t - start, fh.GRACE_S)
        self.clock.t = start + fh.GRACE_S                             # 10 minutes in, round 26: both checks again
        s, result = self.bc(s)
        self.assertIn('wealth_raid', result['fair'])
        self.assertIn('audit', result['fair'])
        validate_state(s)
        # The other way round: past 10 minutes after 2 rounds, still quiet until round 21.
        s = rich()
        s, _ = self.bc(s)
        self.clock.t += fh.GRACE_S + 60
        for n in range(2, fh.GRACE_ROUNDS + 1):
            s, result = self.bc(s)
            self.assertNotIn('wealth_raid', result['fair'], n)
            self.clock.t += 20                                        # a slow player: one round every ~20 s
        self.assertEqual(s['journey'][fh.SESS_KEY]['n'], fh.GRACE_ROUNDS)
        s, result = self.bc(s)
        self.assertIn('wealth_raid', result['fair'])

    def test_a_short_pause_keeps_the_session_a_long_one_starts_a_new_one(self):
        s = rich()
        t = int(self.clock.t)
        s['journey'][fh.SESS_KEY] = dict(at=t - 3600, n=60, ls=t - fh.SESSION_GAP + 30)   # back after 29.5 minutes
        s, result = self.bc(s)
        self.assertIn('wealth_raid', result['fair'])                  # same session: the checks run as in 1.9.12
        self.assertIn('audit', result['fair'])
        self.assertEqual(s['journey'][fh.SESS_KEY]['n'], 61)
        s = rich()
        s['journey'][fh.SESS_KEY] = dict(at=t - 3600, n=60, ls=t - fh.SESSION_GAP)          # back after 30 minutes
        s, result = self.bc(s)
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertNotIn('audit', result['fair'])
        self.assertEqual(s['journey'][fh.SESS_KEY]['n'], 1)

    def test_free_and_skill_stalls_do_not_count(self):
        s = rich()
        s, _ = self.act(s, 'fair_ring_start')
        self.assertNotIn(fh.SESS_KEY, s['journey'])

    def test_the_back_corner_raid_is_per_round_as_before(self):
        s = rich()
        self.dice(Dice(draws=[0]))                                    # the dẹp chiếu draw, on the session's first round
        s, result = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertTrue(result['fair']['raid'])
        self.assertNotIn('wealth_raid', result['fair'])
        self.assertEqual(s['journey'][fh.SESS_KEY]['n'], 1)          # it still counts as a paid round
        validate_state(s)

    def test_the_session_key_is_checked(self):
        s, _ = self.bc(rich())
        validate_state(json.loads(json.dumps(s)))
        for bad in ({'at': 1, 'n': 1}, {'at': 1, 'n': -1, 'ls': 1}, {'at': 'x', 'n': 1, 'ls': 1}, [1, 2, 3],
                    {'at': 1, 'n': 1, 'ls': 1, 'x': 0}):
            t = json.loads(json.dumps(s))
            t['journey'][fh.SESS_KEY] = bad
            with self.assertRaises(GameError):
                validate_state(t)
        old = json.loads(json.dumps(s))
        del old['journey'][fh.SESS_KEY]                                 # a save from before: fine, the next round starts one
        validate_state(old)
