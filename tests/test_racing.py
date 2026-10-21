"""🏁 Đường đua Bến Mây (game/racing.py): tuning your own vehicle at 🔧 Xưởng Tư Pít-tông (jr_tune_buy / jr_tune_fix),
the deterministic race (drag and đèo: the same inputs give the same run, the right choices beat the wrong ones, a stored
run replays exactly), ⏱️ time trials (the fee burned, the daily cap, the week's board and its titles), ⚔️ async duels
(the fixed fee escrowed, the pot minus the burn to the faster, a dead heat and a cancel and an expiry refunded in full,
the money conserved) and their guards (a new account, one network, the same pair, the class and the numbers), and
🔧 a player tuner's work through Phố dịch vụ (game/tuning_service.py)."""
import os
import unittest
from unittest.mock import patch

from game import lb_titles as lbt
from game import marriage as mr
from game import racing as R
from game import service_market as sm
from game import tuning_service as ts
from game.careers import PLUGINS
from game.engine import GameError, validate_state
from tests.test_bank import act
from tests.test_quay_hire import Base

DRAG_OK = dict(launch='manh', shifts=['dung', 'dung', 'dung'])


def stock(vid):
    return R.perf_of(vid, R._blank_car())


def best(track, p):
    if track == 'drag':
        return dict(launch=R.ideal_launch(p), shifts=[R.ideal_shift(p, g) for g in range(3)])
    return dict(brakes=[R.ideal_brake(p, k) for k, _ in R.CORNERS])


class Pure(unittest.TestCase):
    def test_parts_make_a_vehicle_faster_and_every_number_is_in_range(self):
        for vid in R.BASE:
            car = R._blank_car()
            car['m'] = {k: 3 for k in R.MODS}
            p0, p3 = stock(vid), R.perf_of(vid, car)
            self.assertGreater(p3['hp'], p0['hp'])
            self.assertLess(p3['kg'], p0['kg'])
            self.assertGreater(p3['pi'], p0['pi'])
            for track in R.TRACKS:
                self.assertLess(R.run(track, p3, best(track, p3), 's')['ms'], R.run(track, p0, best(track, p0), 's')['ms'], (vid, track))
            self.assertEqual([R.stage_price(vid, 'lop', n) % 10 for n in (1, 2, 3)], [0, 0, 0])
            self.assertTrue(R.stage_price(vid, 'may', 1) < R.stage_price(vid, 'may', 2) < R.stage_price(vid, 'may', 3))
        self.assertEqual([R.stage_price('xe_so', 'may', n) for n in (1, 2, 3)], [40, 90, 160])          # the bike floors
        self.assertEqual([R.stage_price('sieu_xe', 'may', n) for n in (1, 2, 3)], [1440, 3240, 5760])   # 4 / 9 / 16 % of 36 000
        self.assertIsNone(R.base_of('xe_dap'), 'a bicycle never races')

    def test_the_race_is_deterministic_and_the_right_choices_win(self):
        for vid in R.BASE:
            p = stock(vid)
            for track in R.TRACKS:
                good = best(track, p)
                a, b = R.run(track, p, good, 'seed-1'), R.run(track, p, good, 'seed-1')
                self.assertEqual(a, b)
                self.assertLessEqual(abs(a['luck']), R.LUCK_PERMIL)
                if track == 'drag':
                    wrong = dict(good, launch=next(x for x in R.LAUNCH if x != good['launch']))
                else:
                    wrong = dict(brakes=['muon' if x != 'muon' else 'som' for x in good['brakes']])
                # luck is ±0.4 %: a wrong choice costs more than any luck can give back
                self.assertLess(max(R.run(track, p, good, f's{i}')['ms'] for i in range(20)),
                                min(R.run(track, p, wrong, f's{i}')['ms'] for i in range(20)), (vid, track))
                self.assertTrue(all(leg['ok'] for leg in a['legs']))

    def test_wear_and_the_service_price(self):
        car = R._blank_car()
        car['m'] = dict(may=1, gam=0, phanh=2, lop=3)
        car['fx'] = dict(may=2)
        after = R.wear_after(car, slides=2)
        self.assertEqual(after['w'], dict(may=97, gam=100, phanh=94, lop=100 - 10 - 6))
        self.assertEqual(after['fx'], dict(may=1))
        self.assertEqual(R.wear_after(after, 0)['fx'], {}, 'a hand-tune counts down to nothing')
        self.assertEqual(car['w']['lop'], 100, 'a copy')
        self.assertEqual(R.fix_price('xe_so', car), 0)
        worn = R.perf_of('xe_so', after)
        self.assertLess(worn['grip'], R.perf_of('xe_so', dict(car, fx={}))['grip'])
        self.assertGreaterEqual(R.fix_price('xe_so', after), R.FIX_MIN)

    def test_choices_are_checked(self):
        R.check_choices('drag', DRAG_OK)
        R.check_choices('deo', dict(brakes=['vua'] * 5))
        for bad in (None, {}, dict(launch='manh'), dict(launch='x', shifts=['dung'] * 3), dict(DRAG_OK, extra=1),
                    dict(launch='manh', shifts=['dung'] * 2)):
            with self.assertRaises(R.RaceError):
                R.check_choices('drag', bad)
        with self.assertRaises(R.RaceError):
            R.check_choices('deo', dict(brakes=['vua'] * 4))



class English(unittest.TestCase):
    """The racing content ships its English (public/i18n/en.json); the page itself: tests/race-track-ui.mjs."""

    def test_the_content_lines_and_the_titles(self):
        import json
        from pathlib import Path
        pack = json.loads((Path(__file__).resolve().parents[1] / 'public/i18n/en.json').read_text(encoding='utf-8'))['strings']
        lines = list(R.NOTES) + [R.OFF_TEXT] + [n for _, n in R.CORNERS] + [t['name'] for t in R.TRACKS.values()] + [t['where'] for t in R.TRACKS.values()]
        lines += [w for d in R.WORDS.values() for w in d.values()] + [n for _, n in R.CLASSES.values()]
        for m in R.MOD_INFO.values():
            lines.append(m['name'])
            for parts in m['stages'].values():
                lines += [x for p in parts for x in (p, p[:1].lower() + p[1:])]
        lines += [n for b in lbt.RACE for _, n in lbt.BOARD_TITLES[b]]
        self.assertEqual([x for x in lines if x != 'Drag 400 m' and not pack.get(x)], [])

class Base2(Base):
    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        R.vn_day  # noqa: B018

    def racer(self, name, vid='xe_so', wallet=200_000, old=True):
        tok = self.user(name, wallet=wallet, old=old)

        def fn(s):
            s2, _ = act(s, 'jr_garage_buy', id=vid, confirm=True)
            s.clear()
            s.update(s2)
        mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def total(self, tok):
        from game import bank as bk
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)

    def post(self, tok, op, ip='10.0.0.1', **d):
        return R.post(self.store, tok, op, d, ip)


class Tuning(Base2):
    def test_stages_in_order_paid_and_kept_in_the_save(self):
        tok = self.racer('rc_tune')
        before = self.total(tok)
        out = self.cmd(tok, 'jr_tune_buy', id='xe_so', mod='may')
        s = self.state(tok)
        self.assertEqual(s['journey']['tune']['cars']['xe_so']['m']['may'], 1)
        self.assertEqual(self.total(tok), before - 40)
        self.cmd(tok, 'jr_tune_buy', id='xe_so', mod='may')
        self.cmd(tok, 'jr_tune_buy', id='xe_so', mod='may')
        with self.assertRaises(GameError):
            self.cmd(tok, 'jr_tune_buy', id='xe_so', mod='may')
        with self.assertRaises(GameError):
            self.cmd(tok, 'jr_tune_buy', id='xe_dap', mod='lop')   # not owned / a bicycle
        with self.assertRaises(GameError):
            self.cmd(tok, 'jr_tune_fix', id='xe_so')               # nothing worn yet
        self.assertEqual(self.total(tok), before - 290)
        s = self.state(tok)
        self.assertEqual(s['journey']['tune']['stats'], dict(bought=3, fixed=0, races=0, spent=290))
        validate_state(s)
        self.assertIn('message', out.get('result', out) if isinstance(out, dict) else {})

    def test_a_broken_save_key_is_refused_and_a_sold_vehicle_loses_its_parts(self):
        tok = self.racer('rc_tune2')
        self.cmd(tok, 'jr_tune_buy', id='xe_so', mod='lop')
        s = self.state(tok)
        bad = dict(s)
        bad['journey'] = dict(s['journey'], tune=dict(v=1, cars={'xe_so': dict(m=dict(may=9, gam=0, phanh=0, lop=0))}, stats={}))
        with self.assertRaises(GameError):
            R.validate(bad)
        mr._mutate(self.store, {self.sid(tok): lambda s: s.update(act(s, 'jr_garage_buy', id='xe_ga', confirm=True)[0])})
        mr._mutate(self.store, {self.sid(tok): lambda s: s.update(act(s, 'jr_garage_sell', id='xe_so', confirm=True)[0])})
        self.cmd(tok, 'jr_tune_buy', id='xe_ga', mod='lop')
        self.assertEqual(set(self.state(tok)['journey']['tune']['cars']), {'xe_ga'})


class Trials(Base2):
    def test_a_trial_burns_its_fee_stores_its_inputs_and_replays(self):
        tok = self.racer('rc_trial')
        before = self.total(tok)
        out = self.post(tok, 'trial', track='drag', vid='xe_so', choices=DRAG_OK)
        self.assertEqual(self.total(tok), before - R.TRIAL_FEE['drag'])
        self.assertTrue(out['pb'])
        again = self.post(tok, 'replay', id=out['id'])
        self.assertEqual(again['runs'][0]['run']['ms'], out['run']['ms'])
        self.assertEqual(self.state(tok)['journey']['tune']['stats']['races'], 1)
        home = self.post(tok, 'home')
        self.assertEqual(home['today']['trials'], 1)
        row = home['boards']['race_drag_bike'][0]
        self.assertEqual((row['rank'], row['me'], row['ms']), (1, True, out['run']['ms']))
        self.assertNotIn('sid', row)
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in lbt.standings(db) if r[0] in lbt.RACE], ['race_drag_bike'])
        self.assertEqual(lbt.title_of('race_drag_bike', 1)['text'], '🏁 Vua drag xe máy tuần')
        self.assertIsNone(lbt.title_of('race_drag_bike', 4))

    def test_the_daily_cap_a_guest_and_the_kill_switch(self):
        tok = self.racer('rc_cap')
        with patch.object(R, 'TRIAL_DAY', 2):
            self.post(tok, 'trial', track='deo', vid='xe_so', choices=dict(brakes=['vua'] * 5))
            self.post(tok, 'trial', track='deo', vid='xe_so', choices=dict(brakes=['vua'] * 5))
            before = self.total(tok)
            self.refused('trial_day', self.post, tok, 'trial', track='deo', vid='xe_so', choices=dict(brakes=['vua'] * 5))
            self.assertEqual(self.total(tok), before, 'a refused run costs nothing')
        guest, _, _ = self.store.session()
        self.refused('account_required', self.post, guest, 'home')
        with patch.dict(os.environ, {'MNL_RACE_OFF': '1'}):
            self.refused('race_off', self.post, tok, 'trial', track='drag', vid='xe_so', choices=DRAG_OK)
        self.refused('bad_vehicle', self.post, tok, 'trial', track='drag', vid='o_to_mini', choices=DRAG_OK)


class Duels(Base2):
    def setUp(self):
        super().setUp()
        self.a = self.racer('rc_a')
        self.b = self.racer('rc_b')

    def test_the_faster_takes_the_pot_minus_the_burn(self):
        ta, tb = self.total(self.a), self.total(self.b)
        c = self.post(self.a, 'challenge', track='drag', vid='xe_so', fee=20, choices=dict(launch='em', shifts=['tre'] * 3))
        self.assertEqual(self.total(self.a), ta - 20, 'escrowed from the save')
        others = self.post(self.b, 'home')['others']
        self.assertEqual([d['id'] for d in others], [c['id']])
        self.assertIsNone(others[0]['a']['ms'], "the time to beat stays hidden")
        out = self.post(self.b, 'accept', ip='10.0.0.2', id=c['id'], vid='xe_so', choices=DRAG_OK)
        self.assertEqual(out['duel']['status'], 'done')
        self.assertTrue(out['duel']['won'])
        self.assertEqual(self.total(self.b), tb - 20 + 32)
        self.assertEqual(self.total(self.a), ta - 20)
        self.assertEqual((ta - self.total(self.a)) + (tb - self.total(self.b)), 8, 'only the 20 % burn leaves the two saves')
        self.refused('gone', self.post, self.b, 'accept', ip='10.0.0.2', id=c['id'], vid='xe_so', choices=DRAG_OK)
        rp = self.post(self.a, 'replay', id=c['id'])
        self.assertEqual([r['run']['ms'] for r in rp['runs']], [out['duel']['a']['ms'], out['duel']['b']['ms']])

    def test_a_dead_heat_refunds_both(self):
        ta, tb = self.total(self.a), self.total(self.b)
        with patch.object(R, 'run', lambda *a, **k: dict(ms=15000, legs=[], slides=0, luck=0)):
            c = self.post(self.a, 'challenge', track='drag', vid='xe_so', fee=50, choices=DRAG_OK)
            out = self.post(self.b, 'accept', ip='10.0.0.2', id=c['id'], vid='xe_so', choices=DRAG_OK)
        self.assertEqual(out['duel']['status'], 'tie')
        self.assertEqual((self.total(self.a), self.total(self.b)), (ta, tb))

    def test_cancel_and_expiry_refund_the_challenger(self):
        ta = self.total(self.a)
        c = self.post(self.a, 'challenge', track='deo', vid='xe_so', fee=10, choices=dict(brakes=['vua'] * 5))
        self.post(self.a, 'cancel', id=c['id'])
        self.assertEqual(self.total(self.a), ta)
        self.refused('gone', self.post, self.a, 'cancel', id=c['id'])
        c2 = self.post(self.a, 'challenge', track='deo', vid='xe_so', fee=10, choices=dict(brakes=['vua'] * 5))
        self.assertEqual(R.expire(self.store, t=R.now() + 3600), 0, 'not yet')
        self.assertEqual(R.expire(self.store, t=R.now() + R.OPEN_HOURS * 3600 + 60), 1)
        self.assertEqual(R.expire(self.store, t=R.now() + R.OPEN_HOURS * 3600 + 60), 0, 'exactly once')
        self.assertEqual(self.total(self.a), ta)
        self.refused('gone', self.post, self.b, 'accept', ip='10.0.0.2', id=c2['id'], vid='xe_so', choices=dict(brakes=['vua'] * 5))

    def test_the_guards(self):
        c = self.post(self.a, 'challenge', track='drag', vid='xe_so', fee=10, choices=DRAG_OK)
        self.refused('self', self.post, self.a, 'accept', id=c['id'], vid='xe_so', choices=DRAG_OK)
        tb = self.total(self.b)
        self.refused('same_net', self.post, self.b, 'accept', ip='10.0.0.1', id=c['id'], vid='xe_so', choices=DRAG_OK)
        self.assertEqual(self.total(self.b), tb, 'a refusal moves nothing')
        car = self.racer('rc_car', vid='o_to_mini')
        self.refused('bad_vehicle', self.post, car, 'accept', ip='10.0.0.3', id=c['id'], vid='xe_so', choices=DRAG_OK)
        self.refused('class', self.post, car, 'accept', ip='10.0.0.3', id=c['id'], vid='o_to_mini', choices=DRAG_OK)
        fresh = self.racer('rc_new', old=False)
        self.refused('too_new', self.post, fresh, 'challenge', track='drag', vid='xe_so', fee=10, choices=DRAG_OK)
        self.refused('too_new', self.post, fresh, 'accept', ip='10.0.0.4', id=c['id'], vid='xe_so', choices=DRAG_OK)
        self.refused('bad_fee', self.post, self.a, 'challenge', track='drag', vid='xe_so', fee=15, choices=DRAG_OK)
        # a fully tuned bike is out of a stock bike's league (PI_GAP)
        fast = self.racer('rc_fast')
        for mod in R.MODS:
            for _ in range(3):
                self.cmd(fast, 'jr_tune_buy', id='xe_so', mod=mod)
        self.refused('pi_gap', self.post, fast, 'accept', ip='10.0.0.5', id=c['id'], vid='xe_so', choices=DRAG_OK)
        # the same two players: PAIR_DAY duels a day
        with patch.object(R, 'PAIR_DAY', 1):
            self.post(self.b, 'accept', ip='10.0.0.2', id=c['id'], vid='xe_so', choices=DRAG_OK)
            c2 = self.post(self.a, 'challenge', track='drag', vid='xe_so', fee=10, choices=DRAG_OK)
            self.refused('pair_day', self.post, self.b, 'accept', ip='10.0.0.2', id=c2['id'], vid='xe_so', choices=DRAG_OK)
        with patch.object(R, 'OPEN_MAX', 1):
            self.refused('open_max', self.post, self.a, 'challenge', track='drag', vid='xe_so', fee=10, choices=DRAG_OK)


@unittest.skipIf('tuning' not in PLUGINS, 'filtered out by MNL_CAREERS')
class PlayerTuner(Base2):
    def setUp(self):
        super().setUp()
        ts.install()

    def provider(self, name):
        tok = self.user(name)

        def fn(s):
            s['journey']['chapter'] = max(int(s['journey'].get('chapter') or 1), 4)
            s['journey']['done'] = sorted(set(s['journey'].get('done') or []) | {1, 2, 3})
        mr._mutate(self.store, {self.sid(tok): fn})
        self.cmd(tok, 'select_career', career='tuning')
        self.cmd(tok, 'start_day', career='tuning')
        for svc in ts.SERVICES:
            sm.post(self.store, tok, None, 'settings', dict(career='tuning', service=svc, on=True, mode='fixed', mult=1))
        return tok

    def order(self, buyer, seller, service):
        from game import social
        self.rid += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=social.pid_of(self.sid(seller)), career='tuning', service=service, qty=1,
                                                               rid=f'rc-order-{self.rid:06d}'))['order']

    def work(self, tok, oid, service):
        self.cmd(tok, 'dx_svc', career='tuning', order=oid, service=service)
        steps, key = PLUGINS['tuning'].svc_job(oid, service)
        for st in steps:
            self.cmd(tok, 'dx_svc', career='tuning', order=oid, service=service, step=st['id'], value=key[st['id']])

    def test_a_hand_tuned_map_lands_on_the_ridden_vehicle_after_the_bench(self):
        tho = self.provider('rc_tho')
        bare = self.user('rc_bare')
        self.refused('requirement', self.order, bare, tho, 'do_dong_co')   # nothing to tune
        khach = self.racer('rc_khach')
        self.refused('requirement', self.order, khach, tho, 'bao_duong_do')   # nothing worn
        o = self.order(khach, tho, 'do_dong_co')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.refused('tuning_bench', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
        with patch.dict(os.environ, {'MNL_TUNING_SVC_OFF': '1'}):
            self.work(tho, o['id'], 'do_dong_co')
            self.refused('tuning_off', sm.post, self.store, tho, None, 'done', dict(order=o['id']))
        done = sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']
        self.assertEqual(done['status'], 'done')
        s = self.state(khach)
        self.assertEqual(s['journey']['tune']['cars']['xe_so']['fx'], dict(may=R.FX_RACES))
        validate_state(s)
        p = R.perf(s, 'xe_so')
        self.assertAlmostEqual(p['hp'], round(9 * 1.03, 1))


if __name__ == '__main__':
    unittest.main()
