"""📺 Quảng cáo có thưởng (game/ads.py): off without a publisher id, a ticket then a claim at least MIN_WATCH_S later,
7 views a Vietnam day per save (owner 18/10), the 3rd/7th view's chest, the four places (⏰ Giờ vàng riêng ×1,5 for an
hour on shops and counters, 🧩 Ghép ba boosters spent after the day's free ones, 🚔 5 minutes off a jail day, 💼 the
closed shift's bonus), reset_all keeping the count, the page's meta / CSP / ads.txt, and saves an older build keeps."""
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
    env = {'ADS_FAKE': '1', 'ADS_CLIENT': '', 'MNL_ADS_OFF': ''}

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
    env = {'ADS_FAKE': '', 'ADS_CLIENT': '', 'MNL_ADS_OFF': ''}

    def test_off_without_a_publisher_id(self):
        s = story()
        self.assertFalse(ads.enabled())
        self.assertIsNone(ads.public(s))
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='gold')
        self.assertEqual(e.exception.code, 'ads_off')
        self.assertEqual(ads.head_tags(), [])
        self.assertEqual(ads.content_security_policy("script-src 'self'"), "script-src 'self'")
        self.assertIsNone(ads.ads_txt())
        self.assertEqual(ads.offer_shift(s, 'milk_tea', 1000, 1), 0)
        self.assertNotIn('ads', s['journey'])

    def test_a_malformed_id_is_off(self):
        with mock.patch.dict(os.environ, {'ADS_CLIENT': 'ca-pub-abc'}):
            self.assertFalse(ads.enabled())
        with mock.patch.dict(os.environ, {'ADS_CLIENT': 'ca-pub-1234567890123456', 'MNL_ADS_OFF': '1'}):
            self.assertFalse(ads.enabled())


class RealTest(AdsBase):
    env = {'ADS_FAKE': '1', 'ADS_CLIENT': 'ca-pub-1234567890123456', 'MNL_ADS_OFF': ''}

    def test_page_meta_csp_and_ads_txt(self):
        self.assertTrue(ads.enabled())
        self.assertFalse(ads.fake())   # a real id wins over the stand-in
        tag, = ads.head_tags()
        self.assertIn('name="mnl-bonus"', tag)
        self.assertIn('ca-pub-1234567890123456', tag)
        base = ("default-src 'self'; script-src 'self' https://www.youtube.com; img-src 'self' data:; "
                "connect-src 'self'; frame-src https://www.youtube.com; object-src 'none'")
        csp = ads.content_security_policy(base)
        self.assertIn('script-src \'self\' https://pagead2.googlesyndication.com', csp)
        self.assertIn('frame-src https://*.googlesyndication.com', csp)
        self.assertIn('https://www.youtube.com', csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertEqual(ads.ads_txt(), 'google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n')


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

    def test_seven_a_day_with_two_chests_then_tomorrow(self):
        s = story(wallet=0)
        got = []
        for i in range(7):
            s, r = self.watch(s, 'tile' if i % 2 else 'gold')
            got.append(r.get('chest', 0))
        self.assertEqual(sum(1 for x in got if x), 2)
        lo3, hi3 = ads.CHESTS[3]
        lo7, hi7 = ads.CHESTS[7]
        self.assertTrue(lo3 <= got[2] <= hi3 and lo7 <= got[6] <= hi7)
        self.assertEqual(s['journey']['wallet'], got[2] + got[6])
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

    def test_five_minutes_off_and_nothing_else_inside(self):
        s = story(50_000)
        jl.arrest(s['journey'], 'bm', 3, self.clock.t)
        validate_state(s)
        since = s['journey']['jail']['since']
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='gold')
        self.assertEqual(e.exception.code, 'jailed')
        s, r = self.watch(s, 'jail')
        self.assertEqual(s['journey']['jail']['since'], since - ads.JAIL_S)
        for _ in range(3):
            s, _ = self.watch(s, 'jail')
        # 20 minutes, 4 views: the day may end now, a 5th view is refused
        self.assertLessEqual(jl.public(s)['ready'], self.clock.t)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='jail')
        self.assertEqual(e.exception.code, 'ads_place')
        s, r = act(s, 'jail_end')
        self.assertEqual(s['journey']['jail']['left'], 2)

    def test_not_jailed(self):
        with self.assertRaises(GameError) as e:
            act(story(), 'ad_ticket', place='jail')
        self.assertEqual(e.exception.code, 'ads_place')


class ShiftTest(AdsBase):
    def test_the_last_shift_offer_pays_once(self):
        s = story(wallet=0)
        with self.assertRaises(GameError) as e:
            act(s, 'ad_ticket', place='shift')
        self.assertEqual(e.exception.code, 'ads_place')
        self.assertEqual(ads.offer_shift(s, 'milk_tea', 9000, 3), ads.SHIFT_CAP)
        self.assertEqual(ads.offer_shift(s, 'milk_tea', 900, 4), 450)
        validate_state(s)
        self.assertEqual(ads.public(s)['shift'], 450)
        s, r = self.watch(s, 'shift')
        self.assertEqual(s['journey']['wallet'], 450)
        self.assertEqual(ads.public(s)['shift'], 0)
        with self.assertRaises(GameError):
            act(s, 'ad_ticket', place='shift')
        ads.offer_shift(s, 'milk_tea', 900, 5)
        ads.offer_shift(s, 'milk_tea', -50, 6)   # a losing shift clears the offer
        self.assertNotIn('sh', s['journey']['ads'])


class PageTest(AdsBase):
    def test_the_game_page_carries_the_meta(self):
        src = (webassets.Path(webassets.__file__).read_text(encoding='utf-8'))
        self.assertIn('*ads.head_tags()', src)
        self.assertIn('ads.content_security_policy(', src)


if __name__ == '__main__':
    unittest.main()
