"""⏱️ Interest days on real time (game/interest_clock.py, 09/10): skipping life days fast pays no more interest than
the real hours allow (bank demand pot, term deposits, the invest savings book), honest play pays exactly as before,
tái tục rolls over at most RENEW_MAX, a save of this build loaded by the previous build pays no catch-up, a new
account's transfers are capped per day, and a save that skips many days writes one log line."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import bank as bk
from game import interest_clock as ic
from game import invest as iv
from game import journey as jr
from game.engine import apply_action, new_state, validate_state
from game import bank_xfer as bx
from tests.test_bank_xfer import Base as _XferBase

ROOT = Path(__file__).resolve().parents[1]
OLD = os.environ.get('MNL_PREV_TREE', '')


class Clock:
    """A fake wall clock for interest_clock.now."""

    def __init__(self, t=1_800_000_000):
        self.t = t

    def __call__(self):
        return self.t


def story(wallet=0, seed=777):
    s = new_state()
    jr.enable_story(s, seed)
    j = s['journey']
    j['gender'] = 'female'
    j['wallet'] = wallet
    j['stats']['max_wallet'] = max(wallet, 10**6)
    validate_state(s)
    return s


def act(s, name, **p):
    return apply_action(s, None, name, p)


def rich(demand=10**6, term=10**6, term_days=180, renew=True, book=10**6):
    """A save with a demand pot, one term deposit and an invest savings book."""
    s = story(wallet=demand + term + book + 1000)
    s, _ = act(s, 'jr_bk_open')
    s, _ = act(s, 'jr_bk_deposit', amount=demand + term)
    s, _ = act(s, 'jr_bk_save', amount=demand, term=0)
    s, _ = act(s, 'jr_bk_save', amount=term, term=term_days, renew=renew)
    if book:
        s, _ = act(s, 'iv_save', amount=book)
    return s


def end_days(s, n, clock=None, seconds=0):
    """Close n life days the way the game's after-hooks do (bank, then the invest book), `seconds` apart."""
    for _ in range(n):
        if clock is not None:
            clock.t += seconds
        s['journey']['life_day'] += 1
        bk.on_life_day(s)
        iv.on_life_day(s)
    validate_state(s)
    return s


def money(s):
    b = s['journey']['bank']
    return dict(balance=b['balance'], demand=b['demand'], terms=[t['amount'] for t in b['terms']],
                book=s['journey']['invest']['saving']['balance'], interest=b['stats']['interest_in'],
                earned=s['journey']['invest']['saving']['earned'])


class Allowance(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        p = patch.object(ic, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def test_two_thousand_days_at_once_pay_at_most_the_allowance(self):
        s = rich()
        end_days(s, 2000, self.clock, seconds=5)   # 5 s a day: 2000 days in under 3 hours
        m = money(s)
        paid_days = ic.CAP + (2000 * 5) // ic.RATE_SECONDS
        c = s['journey'][ic.KEY]
        self.assertGreaterEqual(sum(b - a + 1 for a, b in c['x']), ic.KEEP_DAYS - 2)   # the last 400 days kept: all but ~1 forfeited
        # Demand pot: 0,05 %/day on at most paid_days days (compounded daily at most).
        self.assertLessEqual(m['demand'], int(10**6 * (1 + bk.DEMAND_BP / 10000) ** paid_days) + 1)
        # Term deposit: principal never grows (interest goes to the account), interest on paid days only.
        self.assertEqual(m['terms'], [10**6])
        self.assertLessEqual(m['balance'], bk.term_interest(10**6, bk.TERM_RATE[180], paid_days))
        # Invest savings book: 0,1-0,3 %/day on paid days only.
        self.assertLessEqual(m['earned'], iv.accrual(10**6 + m['earned']) * paid_days // 1000 + 1)
        # About 170 paid days on 3M xu (~0,5M); without the allowance the same 2000 days paid millions
        # (the 3-year sổ alone renewed 11 times at +26,4 %, compounding: ~12M).
        self.assertLess(m['interest'] + m['earned'], 600_000)

    def test_honest_play_pays_exactly_as_before(self):
        a, b = rich(renew=False), rich(renew=False)
        end_days(a, 400, self.clock, seconds=2880)   # 30 life days per real day
        plenty = Clock();
        with patch.object(ic, 'now', plenty):
            end_days(b, 400, plenty, seconds=10**6)   # always a full bucket
        self.assertEqual(money(a), money(b))
        self.assertEqual(a['journey'][ic.KEY]['x'], [])
        # And it is what the old rules pay: the 180-day sổ matured once (no renewal) with its full interest.
        self.assertEqual(a['journey']['bank']['balance'], 10**6 + bk.term_interest(10**6, bk.TERM_RATE[180], 180))

    def test_a_week_away_then_a_long_evening(self):
        s = rich()
        self.clock.t += 7 * 86400
        end_days(s, 160, self.clock, seconds=60)   # 160 days in under 3 hours after a week away: all paid
        self.assertEqual(s['journey'][ic.KEY]['x'], [])

    def test_forfeited_days_leave_the_term_interest(self):
        s = story(wallet=2 * 10**6)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=10**6)
        s, _ = act(s, 'jr_bk_save', amount=10**6, term=60)
        s['journey'][ic.KEY]['t'] = 10   # 10 interest days left, the clock stands still
        end_days(s, 60, self.clock)
        b = s['journey']['bank']
        self.assertEqual(b['balance'], 10**6 + bk.term_interest(10**6, bk.TERM_RATE[60], 10))
        # Early close also counts only the paid days held.
        s, _ = act(s, 'jr_bk_save', amount=10**6, term=180)
        end_days(s, 20, self.clock)
        tid = s['journey']['bank']['terms'][0]['id']
        before = s['journey']['bank']['balance']
        s, _ = act(s, 'jr_bk_unsave', id=tid, confirm=True)
        self.assertEqual(s['journey']['bank']['balance'] - before, 10**6)   # 0 paid days held: no interest

    def test_renewal_rolls_over_at_most_ten_million(self):
        s = rich(demand=1000, term=10**6, term_days=7, book=0)
        b = s['journey']['bank']
        b['terms'][0]['amount'] = 35 * 10**6   # a sổ compounded by an older build
        b['balance'] = 0
        end_days(s, 7, self.clock, seconds=3600)
        t = b['terms'][0]
        gain = bk.term_interest(35 * 10**6, bk.TERM_RATE[7], 7)
        self.assertEqual(t['amount'], bk.RENEW_MAX)
        self.assertEqual(b['balance'], 25 * 10**6 + gain)
        self.assertTrue(any('về tài khoản' in m['text'] for m in b['inbox']))
        # The next renewal keeps the principal; the interest goes to the account again.
        end_days(s, 7, self.clock, seconds=3600)
        self.assertEqual(t['amount'], bk.RENEW_MAX)
        self.assertEqual(b['balance'], 25 * 10**6 + gain + bk.term_interest(bk.RENEW_MAX, bk.TERM_RATE[7], 7))

    def test_small_renewal_sends_interest_to_the_account(self):
        s = rich(demand=1000, term=10**6, term_days=7, book=0)
        b = s['journey']['bank']
        bal = b['balance']
        end_days(s, 7, self.clock, seconds=3600)
        self.assertEqual(b['terms'][0]['amount'], 10**6)
        self.assertEqual(b['balance'] - bal, bk.term_interest(10**6, bk.TERM_RATE[7], 7))

    def test_bucket_refills_with_real_hours_and_stops_at_the_cap(self):
        s = story()
        end_days(s, 1, self.clock)
        c = s['journey'][ic.KEY]
        c['t'] = 0
        self.clock.t += 5 * 3600 + 10
        end_days(s, 1, self.clock)
        self.assertEqual(c['t'], 4)
        self.clock.t += 400 * 3600
        end_days(s, 1, self.clock)
        self.assertEqual(c['t'], ic.CAP - 1)
        self.assertEqual(c['at'], self.clock.t)   # no banking beyond the cap

    def test_no_key_is_a_full_bucket_and_validates(self):
        s = story()
        self.assertNotIn(ic.KEY, s['journey'])
        validate_state(s)
        end_days(s, 3, self.clock)   # the first day creates the block (full), the next two take a token each
        self.assertEqual(s['journey'][ic.KEY]['t'], ic.CAP - 2)
        s['journey'][ic.KEY]['t'] = ic.CAP + 1
        with self.assertRaises(Exception):
            validate_state(s)

    def test_day_skip_alert_is_one_log_line(self):
        s = story()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            end_days(s, ic.ALERT_DAYS + 40, self.clock, seconds=5)
        lines = [x for x in err.getvalue().splitlines() if x.startswith('[day-skip]')]
        self.assertEqual(len(lines), 1, err.getvalue())
        self.clock.t += 86400
        with contextlib.redirect_stderr(io.StringIO()) as err2:
            end_days(s, 10, self.clock, seconds=5)
        self.assertNotIn('[day-skip]', err2.getvalue())

    def test_end_day_through_the_engine(self):
        s = rich()
        s['journey'][ic.KEY]['t'] = 0
        before = money(s)
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_bk_read')   # any command runs the after-hooks
        self.assertEqual(money(s)['demand'], before['demand'])
        self.assertEqual(s['journey'][ic.KEY]['x'][-1][1], s['journey']['life_day'])


OLD_PROBE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from game import bank as bk, invest as iv
from game.engine import migrate_state, validate_state
s = json.load(open(sys.argv[2]))
s = migrate_state(s, owned=True)
validate_state(s)
b = s['journey']['bank']
def snap():
    return [b['balance'], b['demand'], [t['amount'] for t in b['terms']], s['journey']['invest']['saving']['balance'],
            s['journey']['invest']['saving']['pending'], b['pend']]
a = snap()
bk.on_life_day(s); iv.on_life_day(s)
same = snap()
s['journey']['life_day'] += 1
bk.on_life_day(s); iv.on_life_day(s)
validate_state(s)
print(json.dumps(dict(before=a, same=same, next=snap())))
'''


@unittest.skipUnless(OLD and Path(OLD, 'game', 'bank.py').exists(), 'set MNL_PREV_TREE to an archive of the live release')
class Rollback(unittest.TestCase):
    def test_previous_build_pays_no_catch_up(self):
        clock = Clock()
        with patch.object(ic, 'now', clock):
            s = rich()
            end_days(s, 1500, clock, seconds=5)
        self.assertTrue(s['journey'][ic.KEY]['x'])
        d = s['journey']['bank']['demand']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'save.json')
            path.write_text(json.dumps(s), encoding='utf-8')
            out = subprocess.run([sys.executable, '-I', '-c', OLD_PROBE, OLD, str(path)], capture_output=True, text=True,
                                 cwd=tmp, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        r = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(r['before'], r['same'])   # loading and ticking the same day: nothing paid
        # One more day pays one day: the demand pot moves by at most one day's interest, the terms do not jump.
        self.assertLessEqual(r['next'][1] - r['before'][1], d * bk.DEMAND_BP // 10000 + 1)
        self.assertEqual(r['next'][2], r['before'][2])
        self.assertEqual(r['next'][0], r['before'][0])


class TransferCap(_XferBase):
    def young(self, name, days=3, **k):
        tok = self.user(name, **k)
        when = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days * 86400))
        self.store.transaction(lambda db: db.execute('UPDATE accounts SET created_at=? WHERE sid=?', (when, self.sid(tok))))
        return tok

    def test_new_account_sends_at_most_the_day_cap(self):
        alt = self.young('alt', bank=900_000, wallet=0)
        boss = self.user('boss')
        self.friends(alt, boss)
        v = bx.get(self.store, alt, self.state(alt))
        self.assertFalse(v['rules']['unlimited'])
        self.assertEqual((v['rules']['send_day'], v['today']['left']), (bx.NEW_DAY_MAX, bx.NEW_DAY_MAX))
        self.assertIn('500.000', v['rules']['cap_text'])
        self.send(alt, boss, 300_000)
        e = self.refused('day_cap', self.send, alt, boss, 300_000)
        self.assertIn('200.000', e.message)
        self.assertIn('Tài khoản mới', e.message)
        self.send(alt, boss, 200_000)
        e = self.refused('day_cap', self.send, alt, boss, 10)
        self.assertIn('đủ rồi', e.message)
        self.assertEqual(self.balance(alt), 400_000)
        self.assertEqual(bx.get(self.store, alt, self.state(alt))['today']['left'], 0)

    def test_week_old_account_is_unlimited(self):
        old = self.young('old', days=8, bank=900_000, wallet=0)
        boss = self.user('boss')
        self.friends(old, boss)
        self.send(old, boss, 800_000)
        self.assertTrue(bx.get(self.store, old, self.state(old))['rules']['unlimited'])


if __name__ == '__main__':
    unittest.main()
