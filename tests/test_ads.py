"""📺 Quảng cáo có thưởng (game/ads.py): off without a publisher id, a ticket then a claim at least MIN_WATCH_S later,
7 views a Vietnam day per save (owner 18/10), the places (⏰ Giờ vàng riêng ×1,5 for an hour on shops and counters, 🧩
Ghép ba boosters spent after the day's free ones, 🚔 out of the camp at once, 💸 half of a theft back, 📝 a retake today,
📦 goods now), reset_all keeping the count, the page's meta / CSP, and saves an older build keeps."""
import copy
import os
import unittest
from unittest import mock

from game import ads, jail as jl, tile_match as tm
from game.engine import GameError, apply_action, new_state, validate_state
from game import webassets
from tests.test_bank import story

T0 = 1_792_000_000.0   # 2026-10-15 07:46 VN


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, sec):
        self.t += sec


def act(s, name, **p):
    return apply_action(s, None, name, p)


class AdsBase(unittest.TestCase):
    env = {'ADS_FAKE': '1', 'ADS_REWARDED': '', 'MNL_ADS_OFF': ''}

    def setUp(self):
        e = mock.patch.dict(os.environ, self.env)
        e.start()
        self.addCleanup(e.stop)
        self.clock = Clock()
        for target in (mock.patch.object(ads, '_now', self.clock), mock.patch.object(tm, '_now', self.clock),
                       mock.patch.object(jl, 'now', self.clock)):
            target.start()
            self.addCleanup(target.stop)

    def watch(self, s, place):
        s, r = act(s, 'ad_ticket', place=place)
        self.clock.tick(ads.MIN_WATCH_S)
        return act(s, 'ad_claim', ticket=r['ad']['ticket'])


class OffTest(AdsBase):
    env = {'ADS_FAKE': '', 'ADS_REWARDED': '', 'MNL_ADS_OFF': ''}

    def test_off_without_a_publisher_id(self):
        s = story()
        self.assertFalse(ads.enabled())
        self.assertIsNone(ads.public(s))
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='gold')
        self.assertEqual(e.exception.code, 'ads_off')
        self.assertEqual(ads.head_tags(), [])
        self.assertEqual(ads.content_security_policy("script-src 'self'"), "script-src 'self'")
        self.assertNotIn('ads', s['journey'])

    def test_the_kill_switch(self):
        with mock.patch.dict(os.environ, {'ADS_REWARDED': '1', 'MNL_ADS_OFF': '1'}):
            self.assertFalse(ads.enabled())


class RealTest(AdsBase):
    env = {'ADS_FAKE': '1', 'ADS_REWARDED': '1', 'MNL_ADS_OFF': ''}

    def test_page_meta_csp_and_ads_txt(self):
        self.assertTrue(ads.enabled())
        self.assertFalse(ads.fake())   # a real id wins over the stand-in
        tag, = ads.head_tags()
        self.assertIn('name="mnl-bonus"', tag)
        self.assertIn('ca-pub-9603813200470438', tag)
        base = ("default-src 'self'; script-src 'self' https://www.youtube.com; img-src 'self' data:; "
                "connect-src 'self'; frame-src https://www.youtube.com; object-src 'none'")
        csp = ads.content_security_policy(base)
        self.assertIn('script-src \'self\' https://pagead2.googlesyndication.com', csp)
        self.assertIn('frame-src https://*.googlesyndication.com', csp)
        self.assertIn('https://www.youtube.com', csp)
        self.assertNotIn("'unsafe-eval'", csp)


class FlowTest(AdsBase):
    def test_ticket_then_claim(self):
        s = story()
        self.assertEqual(ads.public(s)['left'], 7)
        s, r = act(s, 'ad_ticket', place='gold')
        tk = r['ad']['ticket']
        self.clock.tick(ads.MIN_WATCH_S - 1)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_claim', ticket=tk)
        self.assertEqual(e.exception.code, 'ads_fast')
        self.clock.tick(1)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_claim', ticket='0' * 16)
        self.assertEqual(e.exception.code, 'ads_ticket')
        s, r = act(s, 'ad_claim', ticket=tk)
        self.assertEqual(r['ad'], dict(place='gold', n=1, left=6))
        self.assertNotIn('tk', s['journey']['ads'])
        with self.assertRaises(GameError):   # a ticket pays once
            act(s, 'ad_claim', ticket=tk)

    def test_a_ticket_expires(self):
        s = story()
        s, r = act(s, 'ad_ticket', place='gold')
        self.clock.tick(ads.TICKET_TTL_S + 1)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_claim', ticket=r['ad']['ticket'])
        self.assertEqual(e.exception.code, 'ads_ticket')

    def test_bad_payloads(self):
        s = story()
        for p in ({}, {'place': 'fair'}, {'place': 'gold', 'x': 1}, {'place': 1}):
            with self.assertRaises(GameError):
                apply_action(s, None, 'ad_ticket', p)
        with self.assertRaises(GameError):
            apply_action(s, None, 'ad_claim', {'ticket': 5})

    def test_seven_a_day_then_tomorrow(self):
        s = story(wallet=0)
        for i in range(7):
            s, r = self.watch(s, 'gold' if i < 3 else 'tile')
        self.assertEqual(r['ad'], dict(place='tile', n=7, left=0))
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(ads.public(s)['left'], 0)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='tile')
        self.assertEqual(e.exception.code, 'ads_day')
        self.clock.tick(24 * 3600)
        self.assertEqual(ads.public(s)['left'], 7)
        s, r = act(s, 'ad_ticket', place='tile')
        self.assertEqual(s['journey']['ads']['n'], 0)

    def test_the_count_survives_a_reset(self):
        s = story()
        for _ in range(4):
            s, _ = self.watch(s, 'tile')
        s, _ = act(s, 'reset_all', confirm='BAT DAU LAI')
        self.assertEqual(ads.views_today(s), 4)
        self.assertEqual(ads.tile_credits(s), {k: 4 for k in ads.TILE_PACK})

    def test_old_build_keeps_the_block(self):
        s = story()
        s, _ = self.watch(s, 'gold')
        s, _ = act(s, 'ad_ticket', place='tile')
        old = copy.deepcopy(s)
        with mock.patch.object(ads, 'validate', lambda s: None):   # an older build: no ads.validate
            validate_state(old)
        validate_state(s)
        bad = copy.deepcopy(s)
        bad['journey']['ads']['n'] = 8
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        bad['journey']['ads']['zz'] = 1
        with self.assertRaises(GameError):
            validate_state(bad)


class GoldTest(AdsBase):
    def test_an_hour_each_stacking_up_to_a_day_of_views(self):
        s = story()
        self.assertEqual(ads.gold_mult(s, T0), 100)
        s, r = self.watch(s, 'gold')
        until = ads.gold_until(s)
        self.assertEqual(until, int(self.clock.t) + ads.GOLD_S)
        self.assertEqual(ads.gold_mult(s, until - 1), 150)
        self.assertEqual(ads.gold_mult(s, until), 100)
        s, _ = self.watch(s, 'gold')
        self.assertEqual(ads.gold_until(s), until + ads.GOLD_S)
        self.assertEqual(ads.scale_take(s, 40, self.clock.t), (140 * 150) // 100 - 100)
        self.assertEqual(ads.scale_take(new_state(), 40, self.clock.t), 40)

    def test_never_more_than_seven_hours_ahead(self):
        s = story()
        s['journey']['ads'] = dict(v=1, d=ads.today(), n=0, g=int(self.clock.t) + ads.GOLD_AHEAD - 10)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='gold')
        self.assertEqual(e.exception.code, 'ads_place')

    def test_staff_orders_and_counters_read_it(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'game'
        self.assertIn('ads.gold_mult(s,at)', (root / 'workplace_business.py').read_text(encoding='utf-8'))
        self.assertIn('ads.scale_take(owner, percent, at / 1000)', (root / 'quay_business.py').read_text(encoding='utf-8'))


class TileTest(AdsBase):
    def test_credits_after_the_days_free_uses_before_xu(self):
        s = story(wallet=10_000)
        s['journey']['tile'] = dict(lv=9, d=tm.today(), n=0, u={}, cur=dict(lv=10, t=int(self.clock.t * 1000), b={}, p={}))
        validate_state(s)
        s, r = self.watch(s, 'tile')
        self.assertEqual(r['ad']['place'], 'tile')
        self.assertEqual(tm.public(s)['free'], {k: tm.FREE[k] + ads.TILE_PACK.get(k, 0) for k in tm.BOOSTS})
        self.clock.tick(600)
        sol = tm.level(10)['solution']
        U = tm.MOVE['undo']
        moves = [sol[0], U] * 5 + sol   # 5 undos: 3 free today, 1 from the ad, 1 paid
        w = s['journey']['wallet']
        s, r = act(s, 'jr_tile_end', n=10, moves=moves, ms=600_000)
        self.assertTrue(r['win'])
        self.assertEqual(r['cost'], tm.PRICE['undo'])
        self.assertEqual(w - s['journey']['wallet'], tm.PRICE['undo'])
        self.assertEqual(s['journey']['tile']['u'], {'undo': 3})
        self.assertEqual(ads.tile_credits(s), {'shuffle': 1, 'push': 1})

    def test_credits_kept_at_most(self):
        s = story()
        s['journey']['ads'] = dict(v=1, d=ads.today(), n=0, tb={k: ads.TILE_KEEP for k in ads.TILE_PACK})
        with self.assertRaises(GameError):
            act(s, 'ad_ticket', place='tile')


class JailTest(AdsBase):
    def setUp(self):
        super().setUp()
        e = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        e.start()
        self.addCleanup(e.stop)

    def test_out_at_once_and_nothing_else_inside(self):
        s = story(50_000)
        jl.arrest(s['journey'], 'bm', 3, self.clock.t)
        validate_state(s)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='gold')
        self.assertEqual(e.exception.code, 'jailed')
        s, r = self.watch(s, 'jail')
        self.assertTrue(r['jail']['free'])
        self.assertFalse(jl.jailed(s))
        self.assertIsNone(jl.public(s))
        self.assertNotIn('jail', s['journey'])
        s, _ = self.watch(s, 'gold')   # free again: everything else is open

    def test_not_jailed(self):
        with self.assertRaises(GameError) as e:
            act(story(), 'ad_ticket', place='jail')
        self.assertEqual(e.exception.code, 'ads_place')


class TheftTest(AdsBase):
    def test_half_of_the_latest_loss_back_once(self):
        s = story(wallet=1_000)
        with self.assertRaises(GameError) as e:   # nothing taken yet
            act(s, 'ad_ticket', place='theft')
        self.assertEqual(e.exception.code, 'ads_place')
        ads.note_loss(s, 3_001, 'Bị móc túi')
        validate_state(s)
        self.assertEqual(ads.public(s)['theft']['back'], 1_500)
        s, r = self.watch(s, 'theft')
        self.assertEqual(s['journey']['wallet'], 2_500)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'life')
        self.assertIn('Bị móc túi', s['journey']['history'][-1]['label'])
        self.assertNotIn('ls', s['journey']['ads'])
        self.assertIsNone(ads.public(s)['theft'])
        with self.assertRaises(GameError):   # once
            act(s, 'ad_ticket', place='theft')

    def test_a_day_to_take_it_and_never_while_off(self):
        s = story()
        ads.note_loss(s, 2_000, 'Trộm vào nhà lấy tiền mặt')
        self.clock.tick(ads.LOSS_TTL + 1)
        with self.assertRaises(GameError):
            act(s, 'ad_ticket', place='theft')
        s, _ = act(s, 'reset_all', confirm='BAT DAU LAI')
        self.assertNotIn('ls', s['journey'].get('ads', {}))
        with mock.patch.dict(os.environ, {'MNL_ADS_OFF': '1'}):
            t = story()
            ads.note_loss(t, 2_000, 'x')
            self.assertNotIn('ads', t['journey'])

    def test_the_losses_that_count(self):
        from game import mishap
        s = story(wallet=50_000)
        mishap.apply_fx(s, {'sub': 'police'}, 5_000)   # a fine is not a theft
        self.assertNotIn('ads', s['journey'])
        w = s['journey']['wallet']
        p = {'sub': 'thug'}
        mishap.apply_fx(s, p, 5_000)
        ls = s['journey']['ads']['ls']
        self.assertEqual((ls['amt'], ls['w']), (w - s['journey']['wallet'], mishap.LABELS['thug']))
        self.assertEqual(ls['amt'], p['_taken'])
        validate_state(s)
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'game'
        for name, n in (('rui.py', 2), ('happenings.py', 2), ('life.py', 1)):
            self.assertEqual((root / name).read_text(encoding='utf-8').count('ads.note_loss('), n, name)


class RetakeTest(AdsBase):
    def test_the_interview_again_today(self):
        from tests.test_certificates import interview, story as cstory
        s, _ = interview(cstory())
        job = s['careers']['delivery']['job']
        self.assertEqual(job['status'], 'rejected')
        with self.assertRaises(GameError):
            apply_action(s, 'delivery', 'job_apply', {'posting': 'dl-rider'})
        for p in ({'what': 'job'}, {'what': 'job', 'career': 'nope'}, {'what': 'exam', 'career': 'delivery'}):
            with self.assertRaises(GameError):
                act(s, 'ad_ticket', place='retake', **p)
        s, r = act(s, 'ad_ticket', place='retake', what='job', career='delivery')
        self.assertEqual(s['journey']['ads']['tk']['k'], 'job:delivery')
        validate_state(s)
        self.clock.tick(ads.MIN_WATCH_S)
        s, r = act(s, 'ad_claim', ticket=r['ad']['ticket'])
        self.assertIn('ứng tuyển lại', r['message'])
        s, _ = apply_action(s, 'delivery', 'job_apply', {'posting': 'dl-rider'})
        with self.assertRaises(GameError):   # nothing left to wait for
            act(s, 'ad_ticket', place='retake', what='job', career='delivery')

    def test_the_self_study_exam_now(self):
        from game import certificates as ct
        from tests.test_certificates import GID, next_life_day, sit, story as cstory
        s = cstory(wallet=500)
        s, _ = apply_action(s, None, 'jr_cert_enrol', {'cert': GID, 'mode': 'self'})
        with self.assertRaises(GameError):   # the first life day: nothing earlier to move it to
            act(s, 'ad_ticket', place='retake', what='cert')
        s = cstory(wallet=500)
        s = next_life_day(s)
        s, _ = apply_action(s, None, 'jr_cert_enrol', {'cert': GID, 'mode': 'self'})
        self.assertGreater(s['journey']['study']['ready'], s['journey']['life_day'])
        s, r = act(s, 'ad_ticket', place='retake', what='cert')
        self.clock.tick(ads.MIN_WATCH_S)
        s, r = act(s, 'ad_claim', ticket=r['ad']['ticket'])
        st = s['journey']['study']
        self.assertEqual((st['ready'], st['start']), (s['journey']['life_day'], s['journey']['life_day'] - ct.SELF_DAYS))
        s, r = sit(s, GID, True)
        self.assertTrue(r['cert']['passed'])

    def test_a_review_again_after_the_next_shift(self):
        from game import promotion as pm
        from tests.test_promotion import PC, best, day, employee, until_due
        j = employee()
        until_due(j)
        rec = pm.record(j.state, 'delivery')
        q1, q2 = rec['due']['qs']
        ok = next(o['id'] for o in PC.QUESTION_INDEX[q1]['options'] if o['score'] == 1)
        j.act('pm_answer', question=q1, option=ok)
        j.act('pm_answer', question=q2, option=best(q2))
        self.assertTrue(j.act('pm_ask', ask='high')['later'])
        self.assertEqual(pm.record(j.state, 'delivery')['wait'], pm.RETRY)
        s, r = act(j.state, 'ad_ticket', place='retake', what='promo', career='delivery')
        self.clock.tick(ads.MIN_WATCH_S)
        j.state, r = act(s, 'ad_claim', ticket=r['ad']['ticket'])
        self.assertEqual(pm.record(j.state, 'delivery')['wait'], 0)
        day(j)
        self.assertIsNotNone(pm.record(j.state, 'delivery')['due'])


class RushTest(AdsBase):
    def setUp(self):
        super().setUp()
        import game.careers.kit as kit
        from tests.test_inventory_flow import Clock as KitClock
        old = kit.clock
        kit.clock = KitClock()
        self.addCleanup(setattr, kit, 'clock', old)

    def journey(self, career):
        from tests.helpers import Journey
        from tests.test_promotion import story as pstory
        j = Journey(career)
        pstory(j, 1)
        return j

    def test_stock_orders_at_the_door_now(self):
        from tests.test_inventory_flow import public_inv
        j = self.journey('restaurant')
        with self.assertRaises(GameError):   # nothing on the way
            act(j.state, 'ad_ticket', place='rush', career='restaurant')
        j.act('inv_order', item='noodle', qty=6, supplier='partner', confirm=True)
        j.act('inv_order', item='noodle', qty=2, supplier='partner', confirm=True)
        orders = public_inv(j)['orders']
        self.assertFalse(any(o['ready_now'] for o in orders))
        for p in ({}, {'career': 'nope'}, {'career': 'restaurant', 'what': 'x'}):
            with self.assertRaises(GameError):
                act(j.state, 'ad_ticket', place='rush', **p)
        s, r = act(j.state, 'ad_ticket', place='rush', career='restaurant')
        self.clock.tick(ads.MIN_WATCH_S)
        j.state, r = act(s, 'ad_claim', ticket=r['ad']['ticket'])
        self.assertIn('Hàng đã về', r['message'])
        self.assertTrue(all(o['ready_now'] for o in public_inv(j)['orders'] if o['status'] == 'in_transit'))
        for o in j.c['ext']['inv']['orders']:
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertTrue(all(o['status'] == 'received' for o in j.c['ext']['inv']['orders']))

    def test_stock_desk_parcels_too(self):
        j = self.journey('mother_baby')
        j.act('order_stock', item='cat_bag', qty=2, supplier='express')
        ship = j.c['shipments'][-1]
        with self.assertRaises(GameError):
            j.act('receive_stock', shipment=ship['id'], count=ship['actual'])
        s, r = act(j.state, 'ad_ticket', place='rush', career='mother_baby')
        self.clock.tick(ads.MIN_WATCH_S)
        j.state, r = act(s, 'ad_claim', ticket=r['ad']['ticket'])
        ship = j.c['shipments'][-1]
        if ship['status'] != 'received':   # the stock desk may shelve it itself
            j.act('receive_stock', shipment=ship['id'], count=ship['actual'])
        self.assertEqual(j.c['shipments'][-1]['status'], 'received')


class PageTest(AdsBase):
    def test_the_game_page_carries_the_meta(self):
        src = (webassets.Path(webassets.__file__).read_text(encoding='utf-8'))
        self.assertIn('*ads.head_tags()', src)
        self.assertIn('ads.content_security_policy(', src)


if __name__ == '__main__':
    unittest.main()
