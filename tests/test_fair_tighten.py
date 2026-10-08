"""Owner 07/10 at the fair: lower odds (50%), a long run of one luck stall cools to 40% and recovers only after 3
rounds of another paid luck stall staking >= max(20 xu, 1/4 of the last stake there) or a 10-minute pause (free/skill
stalls and smaller stakes reset nothing; bầu cua exempt: honest dice),
no sure win after losses, and 🍀 Lộc trời cho (×10 the stake of a won round, at
most once an hour for the whole server, replay-safe)."""
import json
import threading
import time
from unittest import mock

from game import fair as fh
from game import fair_scratch as xs
from game.engine import public_state, validate_state
from tests.test_fair import OPEN, Dice as BaseDice, FairBase, StoreBase, story, loto_dice, winning_rs


class Dice(BaseDice):
    def shuffle(self, seq):   # the vé cào's layout: left as drawn
        pass


class Decay(FairBase):
    def xd(self, s, n, draw=.99, stake=10):
        for _ in range(n):
            self.dice(Dice(draws=[.5, draw]))   # no raid, then the luck draw
            s, _ = self.act(s, 'fair_xd', side='chan', stake=stake)
        return s

    def test_a_long_run_cools_step_by_step_to_the_floor_and_stays(self):
        s = self.xd(story(10**6), 40)
        self.assertEqual(s['journey']['fair_run']['n'], 40)
        rates = [fh.run_rate('xd', n) for n in range(1, 201)]
        self.assertEqual(rates[:fh.RUN_FREE], [fh.XD_BASE] * fh.RUN_FREE)
        self.assertAlmostEqual(rates[fh.RUN_FREE], fh.XD_BASE - .015)
        self.assertEqual(rates[25:], [fh.XD_FLOOR] * 175)
        self.assertAlmostEqual(fh.XD_FLOOR * (1 - fh.RAID_PCT / 100), .40, delta=.001)   # 40% won rounds after raids
        self.assertEqual([fh.run_rate('xs', n) for n in (1, 10, 11, 16, 17, 200)], [.50, .50, .485, .41, .40, .40])
        # A draw a little under the floor still wins on round 41, one a little over loses.
        self.dice(Dice(draws=[.5, fh.XD_FLOOR - .001]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertGreater(r['fair']['net'], 0)
        self.dice(Dice(draws=[.5, fh.XD_FLOOR + .001]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertLess(r['fair']['net'], 0)
        validate_state(s)

    def xs(self, s, n, price=20):
        for _ in range(n):
            self.dice(Dice(draws=[.99]))
            s, _ = self.act(s, 'fair_xs', price=price)
        return s

    def xd_p(self, s):
        """The draw xóc đĩa's next round would get (on a copy: nothing counted)."""
        return fh.luck_p(json.loads(json.dumps(s['journey'])), None, 'xd', self.clock.t)

    def test_a_ten_minute_pause_recovers(self):
        s = self.xd(story(10**6), 30)
        self.assertEqual(public_state(s)['fair']['cool']['game'], 'xd')
        self.assertNotIn('pct', public_state(s)['fair']['cool'])   # owner 08/10: no rate reaches the client
        self.clock.t += fh.RUN_GAP - 5
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)                  # 9m55s: still cold
        self.clock.t += 6                                            # a 10-minute pause
        self.assertIsNone(public_state(s)['fair']['cool'])
        self.assertEqual(self.xd_p(s), fh.XD_BASE)
        validate_state(s)

    def test_three_rounds_of_another_paid_stall_recover_one_or_two_do_not(self):
        s = self.xd(story(10**6), 30)
        s = self.xs(s, 2)                                            # two vé cào: not yet
        self.assertEqual(s['journey'][fh.COOL_KEY]['xd']['sw'], 2)
        cold = public_state(s)['fair']['cool']
        self.assertEqual((cold['game'], cold['switch'], cold['min']), ('xd', 1, 20))
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)
        s = self.xd(s, 1)                                            # back to xóc đĩa: the switch starts over
        s = self.xs(s, 2)
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)
        s = self.xs(s, 1)                                            # the third paid round in a row: warm again
        self.assertNotIn('xd', s['journey'][fh.COOL_KEY])
        self.assertEqual(self.xd_p(s), fh.XD_BASE)
        validate_state(s)
        s = self.xd(s, 30)                                           # bầu cua and lô tô count as paid rounds too
        for _ in range(2):
            self.dice(Dice(faces=['bau', 'tom', 'ga']))
            s, _ = self.act(s, 'fair_bc', bets={'cua': 15, 'ga': 5})
        self.dice(Dice(draws=[.99], bits=7))
        s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=2)        # two 10-xu tờ: 20 xu
        self.assertEqual(self.xd_p(s), fh.XD_BASE)
        validate_state(s)

    def test_small_stakes_elsewhere_do_not_count(self):
        s = self.xd(story(10**6), 30)
        s = self.xs(s, 5, price=10)                                  # under 20 xu: nothing
        for _ in range(5):
            self.dice(Dice(faces=['bau', 'tom', 'ga']))
            s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.dice(Dice(draws=[.99], bits=7))
        s, _ = self.act(s, 'fair_loto_buy')                          # the older client's 5-xu tờ
        self.assertEqual(s['journey'][fh.COOL_KEY]['xd']['sw'], 0)
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)
        validate_state(s)

    def test_a_quarter_of_the_last_stake_on_the_cooled_stall(self):
        s = self.xd(story(10**6), 30, stake=1000)
        self.assertEqual(public_state(s)['fair']['cool']['min'], 250)
        s = self.xs(s, 3, price=200)                                 # 200 < 250: nothing
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)
        s = self.xs(s, 2, price=500)
        self.assertEqual(public_state(s)['fair']['cool']['switch'], 1)
        s = self.xd(s, 1, stake=40)                                  # back at 40 xu: the switch starts over, min 20
        self.assertEqual(public_state(s)['fair']['cool']['min'], 20)
        s = self.xs(s, 3, price=20)
        self.assertEqual(self.xd_p(s), fh.XD_BASE)
        validate_state(s)

    def test_free_and_skill_stalls_reset_nothing(self):
        s = self.xd(story(10**6), 30)
        for _ in range(5):
            s, _ = self.act(s, 'fair_ring_start')                     # ném vòng (free)
        s, _ = self.act(s, 'fair_oaq_start', lv='de')               # ô ăn quan
        s, _ = self.act(s, 'fair_oaq_quit')
        s, _ = self.act(s, 'fair_kn_start', stake=2)                # phóng dao
        self.assertNotIn('fair_run', s['journey'])                   # the older run keys still break, as before
        self.assertEqual(s['journey'][fh.COOL_KEY]['xd'], dict(n=30, at=s['journey'][fh.COOL_KEY]['xd']['at'], sw=0, st=10))
        self.assertEqual(public_state(s)['fair']['cool']['game'], 'xd')
        self.assertEqual(self.xd_p(s), fh.XD_FLOOR)
        validate_state(s)

    def test_the_spam_record_is_optional_and_checked(self):
        s = self.xd(story(10**6), 3)
        validate_state(s)
        for bad in ({'oaq': dict(n=1, at=1, sw=0, st=0)}, {'xd': dict(n=1, at=1, sw=0)}, {'xd': dict(n=1, at=1, sw=4, st=0)},
                    {'xd': dict(n=1, at=1, sw=0, st=1001)}, []):
            s2 = json.loads(json.dumps(s))
            s2['journey'][fh.COOL_KEY] = bad
            with self.assertRaises(Exception):
                validate_state(s2)
        s2 = json.loads(json.dumps(s))
        del s2['journey'][fh.COOL_KEY]                                # a save from before 07/10: a fresh run
        validate_state(s2)
        self.assertEqual(fh.luck_p(s2['journey'], None, 'xd', self.clock.t), fh.XD_BASE)

    def test_normal_play_keeps_the_full_rate(self):
        s = story(10**6)
        for _ in range(5):   # a few rounds of each stall, 20 xu or more
            s = self.xd(s, 4, stake=20)
            s = self.xs(s, 4, price=20)
            self.assertIsNone(public_state(s)['fair']['cool'])
        self.assertLessEqual(s['journey']['fair_run2']['n'], fh.RUN_FREE)
        self.assertEqual(set(s['journey'][fh.COOL_KEY]), {'xs'})     # four vé cào warmed xóc đĩa up each time

    def test_the_hint_shows_from_the_first_cooled_round(self):
        s = story(10**6)
        for i in range(fh.RUN_FREE):
            self.assertIsNone(public_state(s)['fair']['cool'], i)
            self.dice(Dice(draws=[.99]))
            s, _ = self.act(s, 'fair_xs', price=2)
        cold = public_state(s)['fair']['cool']
        self.assertEqual((cold['game'], cold['gap'], cold['switch'], cold['min']), ('xs', 10, 3, 20))
        self.assertNotIn('cold', public_state(s)['fair'])   # an older client printed "khoảng N% thắng" from it
        rules = public_state(s)['fair']['rules']
        self.assertEqual((rules['run_switch'], rules['run_switch_min']), (3, 20))
        for key in ('luck_pct', 'cooled_pct', 'floor_pct', 'run_free', 'luck', 'raid_pct'):   # owner 08/10: no rates shown
            self.assertNotIn(key, rules)
        self.assertNotIn('win_pct', rules)   # an older client's line (a sure win after 4 losses) is not shown any more

    def test_bau_cua_is_exempt(self):
        s = story(10**6)
        for _ in range(60):
            self.dice(Dice(faces=['bau', 'tom', 'ga']))
            s, r = self.act(s, 'fair_bc', bets={'cua': 1})
            self.assertEqual(r['fair']['dice'], ['bau', 'tom', 'ga'])   # the dice stay honest: whatever they show
        self.assertEqual(s['journey']['fair_run']['n'], 60)
        self.assertIsNone(public_state(s)['fair']['cool'])
        self.assertEqual(fh.luck_p(s['journey'], None, 'bc', self.clock.t), fh.LUCK_BASE)
        self.assertNotIn('fair_balance', s['journey'])               # no luck draw at bầu cua
        validate_state(s)

    def test_ring_luck_part_cools_too_and_older_locked_rounds_keep_their_rate(self):
        s = story(100)
        for i in range(25):
            s, r = self.act(s, 'fair_ring_start')
        self.assertEqual(s['journey']['fair_chance']['ring']['p'], 400)
        self.dice(Dice(draws=[.399]))
        s, r = self.act(s, 'fair_ring_throw', id=r['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
        self.assertGreater(r['fair']['n'], 0)
        s, r = self.act(s, 'fair_ring_start')
        s['journey']['fair_chance']['ring']['p'] = 665              # a round started on 1.9.9 (its 66.5%)
        self.dice(Dice(draws=[.66]))
        s, r = self.act(s, 'fair_ring_throw', id=r['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
        self.assertGreater(r['fair']['n'], 0)
        validate_state(s)

    def test_no_sure_win_after_four_losses_in_commands(self):
        s = story(10**6)
        for _ in range(8):
            self.dice(Dice(draws=[.99]))
            s, r = self.act(s, 'fair_xs', price=2)
            self.assertEqual(r['fair']['mult'], 0)
        self.assertEqual(s['journey']['fair_balance']['xs'], -4)
        validate_state(s)


class Loc(FairBase):
    def setUp(self):
        super().setUp()
        tok = fh._loc_gate.set(True)   # storage opens it when the hour is free (StoreLoc below)
        self.addCleanup(fh._loc_gate.reset, tok)

    def test_closed_gate_never_grants(self):
        fh._loc_gate.set(False)
        self.dice(Dice(draws=[.5, .1, 0]))
        s, r = self.act(story(1000), 'fair_xd', side='chan', stake=100)
        self.assertNotIn('loc', r['fair'])
        self.assertEqual(s['journey']['wallet'], 1100)

    def test_a_won_xoc_dia_round_pays_ten_times_its_stake(self):
        self.dice(Dice(draws=[.5, .1, fh.LOC_P - .0001]))
        s, r = self.act(story(1000), 'fair_xd', side='chan', stake=100)
        loc = r['fair']['loc']
        self.assertEqual((loc['won'], loc['bonus'], loc['mult']), (1000, 900, 10))
        self.assertEqual(s['journey']['wallet'], 1000 + 1000)
        self.assertTrue(s['journey']['history'][-1]['label'].startswith('🍀 Lộc trời cho ×10'))
        self.assertEqual(s['journey']['history'][-1]['amount'], 900)
        self.assertEqual(fh.money_of(s['journey'])[0], 1000)         # fair profit: the Bảng vàng counts it
        self.assertIn('Lộc trời cho', r['message'])
        self.assertFalse(fh._loc_gate.get())                         # one per command
        validate_state(s)

    def test_the_per_round_chance_and_losses(self):
        self.dice(Dice(draws=[.5, .1, fh.LOC_P]))
        s, r = self.act(story(1000), 'fair_xd', side='chan', stake=100)
        self.assertNotIn('loc', r['fair'])
        self.dice(Dice(draws=[.5, .99, 0]))                         # a lost round: never
        s, r = self.act(s, 'fair_xd', side='chan', stake=100)
        self.assertNotIn('loc', r['fair'])
        self.assertTrue(fh._loc_gate.get())

    def test_bau_cua_win_with_honest_dice(self):
        self.dice(Dice(faces=['cua', 'bau', 'tom'], draws=[0]))
        s, r = self.act(story(1000), 'fair_bc', bets={'cua': 10, 'ga': 5})
        self.assertEqual(r['fair']['dice'], ['cua', 'bau', 'tom'])   # the roll is untouched
        self.assertEqual(r['fair']['net'], 5)
        self.assertEqual(r['fair']['loc']['won'], 150)
        self.assertEqual(s['journey']['wallet'], 1000 + 150)
        self.dice(Dice(faces=['cua', 'cua', 'cua'], draws=[0]))     # a bão already won 10×: nothing to add
        fh._loc_gate.set(True)
        s, r = self.act(story(1000), 'fair_bc', bets={'cua': 10})
        self.assertNotIn('loc', r['fair'])
        self.assertTrue(fh._loc_gate.get())

    def test_scratch_ticket_and_loto_kinh(self):
        with mock.patch.object(xs, 'prize_mult', return_value=2):
            self.dice(Dice(draws=[.1, 0]))
            s, r = self.act(story(1000), 'fair_xs', price=50)
        self.assertEqual(r['fair']['loc']['won'], 500)
        self.assertNotIn('Lộc', r['message'])                       # the ticket is still under its silver
        self.assertEqual(s['journey']['wallet'], 1000 + 500)
        fh._loc_gate.set(True)
        slot = int(self.clock.t // 60) + 1
        self.clock.t = slot * 60 + 1
        self.dice(loto_dice(winning_rs(True, slot), True))
        s, _ = self.act(story(1000), 'fair_loto_buy')
        rv = fh.round_view(s['journey']['fair']['loto'])
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        self.dice(Dice(draws=[0]))
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=max(pos[n] for n in rv['card'][row]) + 1)
        self.assertEqual(r['fair']['loc']['won'], 50)                # ×10 the 5-xu tờ, instead of its 10-xu prize
        self.assertEqual(s['journey']['wallet'], 1000 - 5 + 5 + 50)
        validate_state(s)

    def test_the_police_check_counts_the_bonus_later(self):
        s = story(100000)
        s['journey']['fair'] = f = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition())
        f['stats']['won'] = 60000
        self.dice(Dice(draws=[.5, .1, 0, 0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=100)
        self.assertEqual(r['fair']['loc']['won'], 1000)
        self.assertNotIn('wealth_raid', r['fair'])                    # today's net 1,000: the 1.9.9 raid is not due
        self.assertEqual(r['fair']['audit']['gain'], 61000)
        self.assertEqual(r['fair']['audit']['amount'], 6100)


class StoreLoc(StoreBase):
    def setUp(self):
        super().setUp()
        self.store.transaction(lambda db: db.execute('DELETE FROM mnl_meta WHERE key=?', (fh.LOC_KEY,)))
        fh._loc_seen[0] = 0.0
        self.addCleanup(lambda: fh._loc_seen.__setitem__(0, 0.0))

    def last(self):
        with self.store.connect() as db:
            row = db.execute('SELECT value FROM mnl_meta WHERE key=?', (fh.LOC_KEY,)).fetchone()
        return int(row[0]) if row else None

    def xd_win(self, tok, rid=None):
        self.dice(Dice(draws=[.5, .1, 0, .99]))
        return self.cmd(tok, 'fair_xd', dict(side='chan', stake=100), rid)

    def test_once_an_hour_for_the_whole_server_and_replay_safe(self):
        a, b = self.player('Lan', wallet=1000), self.player('Minh', wallet=1000)
        rev = self.store.read(a)[1]
        args = (a, 'loc-retry-0001', rev, None, 'fair_xd', dict(side='chan', stake=100))
        self.dice(Dice(draws=[.5, .1, 0, .99]))
        first = self.store.command(*args)
        self.assertEqual(first['result']['fair']['loc']['won'], 1000)
        self.assertEqual(self.store.read(a)[0]['journey']['wallet'], 2000)
        self.assertEqual(self.last(), first['result']['fair']['loc']['at'])
        with mock.patch.object(fh, '_loc', side_effect=AssertionError('a replay must not grant again')):
            replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['result'], first['result'])
        self.assertEqual(self.store.read(a)[0]['journey']['wallet'], 2000)
        fh._loc_seen[0] = 0.0                                        # another worker: it reads the row
        r = self.xd_win(b)
        self.assertNotIn('loc', r['result']['fair'])
        self.assertEqual(self.store.read(b)[0]['journey']['wallet'], 1100)
        self.clock.t += fh.LOC_GAP
        r = self.xd_win(b)
        self.assertEqual(r['result']['fair']['loc']['won'], 1000)
        self.assertEqual(self.last(), r['result']['fair']['loc']['at'])

    def test_losing_the_race_computes_the_round_again_without_the_bonus(self):
        tok = self.player('Lan', wallet=1000)
        real = fh.loc_claim
        def rival_first(db, result):
            if (result.get('fair') or {}).get('loc'):   # another worker commits its Lộc just before this one
                self.store.transaction(lambda d: d.execute(
                    'INSERT INTO mnl_meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value',
                    (fh.LOC_KEY, str(int(self.clock.t)))))
            return real(db, result)
        self.dice(Dice(draws=[.5, .1, 0, .99, .1, .1, 0, .99]))   # the second computation wins its round too
        with mock.patch.object(fh, 'loc_claim', side_effect=rival_first):
            r = self.cmd(tok, 'fair_xd', dict(side='chan', stake=100))
        self.assertNotIn('loc', r['result']['fair'])
        self.assertEqual(self.store.read(tok)[0]['journey']['wallet'], 1100)   # one plain won round, once
        self.assertEqual(self.store.read(tok)[0]['journey']['fair']['stats']['xd'], 1)

    def test_concurrent_workers_take_the_hour_once(self):
        """Eight workers claim at the same moment, each in its own transaction: exactly one wins each hour."""
        def race(at, n=8):
            gate, wins = threading.Barrier(n), []
            def worker():
                db = self.store.connect()
                try:
                    db.begin()
                    gate.wait()
                    ok = fh.loc_claim(db, dict(fair=dict(loc=dict(at=at))))
                    time.sleep(.05)
                    db.commit()
                    wins.append(ok)
                finally:
                    db.close()
            threads = [threading.Thread(target=worker) for _ in range(n)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            return sum(wins)
        t0 = int(OPEN)
        self.assertEqual(race(t0), 1)
        self.assertEqual(race(t0 + fh.LOC_GAP // 2), 0)
        self.assertEqual(race(t0 + fh.LOC_GAP), 1)
        self.assertEqual(self.last(), t0 + fh.LOC_GAP)
