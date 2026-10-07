"""🍚 No bụng · 😴 Tỉnh táo (game/needs.py): the drain over a work day, lunch, the evening (dinner + bedtime) and the
next morning, the free option, money, older saves, validation and double taps."""
import copy
import unittest

from game import dayclock as dc
from game import housing as hs
from game import invest as iv
from game import journey as jr
from game import life as lf
from game import needs as nd
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

CAREER = 'grocery'   # 06:30–21:30, the inventory clock: 20 minutes a ticking action


def story(wallet=100, seed=7, spirit=60):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey'].update(gender='female', intro=True, wallet=wallet)
    iv.migrate(s)
    lf.migrate(s)
    s['journey']['life']['spirit'] = spirit
    validate_state(s)
    return s


def act(s, action, career=CAREER, **p):
    return apply_action(s, career, action, p)


def jr_act(s, action, **p):
    return apply_action(s, None, action, p)


def N(s):
    return s['journey']['needs']


def spirit(s):
    return s['journey']['life']['spirit']


def minute(s, career=CAREER):
    return dc.minute_now(s['careers'][career], career)


def opened(wallet=100, career=CAREER, **kw):
    s = story(wallet, **kw)
    s, _ = act(s, 'select_career', career)
    s, _ = act(s, 'start_day', career)
    return s


def until(s, at, career=CAREER):
    """Tick the shop clock (advance: one ticking action) until it reads `at` or later."""
    notes = []
    for _ in range(80):
        if minute(s, career) >= at:
            break
        s, r = act(s, 'advance', career)
        notes += r.get('effects') or []
    return s, notes


def close(s, career=CAREER):
    s, r = act(s, 'end_day', career, carry_event=True)
    return s, r


class DayTests(unittest.TestCase):
    def test_new_save_starts_sensibly(self):
        s = opened()
        n = N(s)
        self.assertEqual((n['full'], n['wake'], n['day']), (nd.START_FULL, nd.START_WAKE, 1))
        self.assertEqual(n['seen'], [CAREER, 1, 6 * 60 + 30])
        v = public_state(s)['needs']
        self.assertTrue(v['enabled'])
        self.assertEqual(v['full']['value'], nd.START_FULL)
        self.assertIsNone(v['lunch'])
        self.assertIsNone(v['evening'])

    def test_drain_follows_the_shop_clock(self):
        s = opened()
        s, _ = until(s, 11 * 60 + 30)          # 5 hours of shop time
        n = N(s)
        self.assertEqual(n['worked'], 300)
        self.assertEqual(n['full'], nd.START_FULL - 5 * nd.FULL_PER_HOUR)
        self.assertEqual(n['wake'], nd.START_WAKE - 5 * nd.WAKE_PER_HOUR)
        # A non-ticking action (talk is free) moves nothing.
        before = copy.deepcopy(n)
        s, _ = act(s, 'task_select', task=s['careers'][CAREER]['tasks'][-1]['id'])
        self.assertEqual(N(s), before)

    def test_lunch_moment_and_choices(self):
        s = opened()
        s, _ = until(s, 11 * 60)
        self.assertIsNone(public_state(s)['needs']['lunch'])
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_lunch', meal='hop')
        self.assertEqual(e.exception.code, 'not_now')
        s, _ = until(s, nd.LUNCH_FROM)
        v = public_state(s)['needs']['lunch']
        self.assertEqual([c['id'] for c in v['choices']], ['hop', 'binh_dan', 'banh_mi', 'nhin'])
        self.assertTrue(all(c['ok'] for c in v['choices']))
        for meal, x in nd.LUNCH.items():
            t, r = jr_act(s, 'jr_needs_lunch', meal=meal)
            n = N(t)
            self.assertEqual(n['lunch'], meal)
            self.assertEqual(n['full'], min(100, N(s)['full'] + x['full']), meal)
            self.assertEqual(n['wake'], min(100, N(s)['wake'] + x['wake']), meal)
            self.assertEqual(t['journey']['wallet'], 100 - x['price'], meal)
            self.assertEqual(spirit(t), spirit(s) + x['spirit'], meal)
            if x['price']:
                row = t['journey']['history'][-1]
                self.assertEqual((row['kind'], row['amount']), ('living', -x['price']))
            self.assertIsNone(public_state(t)['needs']['lunch'])
            self.assertTrue(r['message'])

    def test_lunch_left_alone_is_the_packed_box(self):
        s = opened()
        s, notes = until(s, nd.LUNCH_UNTIL)
        self.assertEqual(N(s)['lunch'], 'hop')
        self.assertTrue(any('🍱' in x for x in notes))
        self.assertEqual(s['journey']['wallet'], 100)

    def test_skipping_lunch_dips_once_with_a_line(self):
        s = opened()
        s, _ = until(s, nd.LUNCH_FROM)
        s, _ = jr_act(s, 'jr_needs_lunch', meal='nhin')
        sp = spirit(s)
        dips = []
        for _ in range(40):
            s, r = act(s, 'advance')
            if r.get('needs_say'):
                dips.append(r)
            if minute(s) >= 21 * 60:
                break
        self.assertEqual(len(dips), 1)                       # once a day, however long it stays low
        self.assertIn('full', N(s)['low'])
        self.assertLess(N(s)['full'], nd.LOW)
        self.assertEqual(spirit(s), sp - 1 - ('wake' in N(s)['low']))
        self.assertTrue(any('🍚' in x for x in dips[0]['effects']))

    def test_well_fed_day_and_evening_to_morning(self):
        s = opened()
        s, _ = until(s, nd.LUNCH_FROM)
        s, _ = jr_act(s, 'jr_needs_lunch', meal='hop')
        s, _ = until(s, 17 * 60)
        sp, last = spirit(s), minute(s)
        s, r = close(s)
        n = N(s)
        self.assertEqual(s['journey']['life_day'], 2)
        self.assertEqual(n['day'], 1)                         # the evening of day 1
        self.assertEqual(n['finish'], last + 20)              # end_day ticks one step
        self.assertTrue(any('ăn đủ bữa' in x for x in r['effects']))
        self.assertGreaterEqual(spirit(s), sp + 1)
        E = public_state(s)['needs']['evening']
        self.assertEqual(E['meals'][0]['id'], 'nha')         # the free dinner first
        self.assertEqual(E['meals'][0]['price'], 0)
        self.assertEqual(E['usual']['meal'], 'nha')
        self.assertEqual(E['usual']['bed'], 23 * 60)
        self.assertIsNone(E['chosen'])
        full = n['full']
        s, r = jr_act(s, 'jr_needs_eve', meal='bua_ngon', bed=22 * 60)
        self.assertEqual(s['journey']['wallet'], 100 + jr.WELCOME_GIFT - jr.LIVING[1] - nd.EVE['bua_ngon']['price'])   # living, the gift, the meal
        self.assertEqual(N(s)['full'], min(100, full + nd.EVE['bua_ngon']['full']))
        self.assertEqual(public_state(s)['needs']['evening']['chosen']['meal'], 'bua_ngon')
        self.assertEqual(N(s)['usual'], dict(meal='bua_ngon', bed=22 * 60))
        sp = spirit(s)
        s, r = act(s, 'start_day')
        n = N(s)
        self.assertEqual(n['day'], 2)
        self.assertEqual(n['wake'], nd.sleep_wake(22 * 60))
        self.assertEqual(n['wake'], 100)
        self.assertEqual(n['full'], min(100, max(0, min(100, full + 55) - nd.NIGHT_FULL) + nd.BREAKFAST))
        self.assertEqual(spirit(s), sp + 1)                   # slept on time
        self.assertTrue(any('☕' in x for x in r['effects']))
        self.assertIsNone(public_state(s)['needs']['evening'])
        self.assertEqual((n['lunch'], n['low'], n['worked'], n['eve']), (None, [], 0, None))

    def test_bedtime_sets_the_morning(self):
        self.assertEqual([nd.sleep_wake(b) for b in nd.BEDS], [100, 91, 82, 73])
        s = opened()
        s, _ = until(s, 18 * 60)
        s, _ = close(s)
        rows = {b['bed']: b for b in public_state(s)['needs']['evening']['meals'][0]['beds']}
        self.assertTrue(all(b['ok'] for b in rows.values()))
        self.assertEqual(rows[24 * 60]['when'], 'tonight')
        sp = spirit(s)
        s, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=25 * 60)
        self.assertEqual(spirit(s), sp + 1)                   # a late film: +1 tonight
        s, _ = act(s, 'start_day')
        self.assertEqual(N(s)['wake'], 73)

    def test_morning_takes_the_usual_free_when_nothing_was_chosen(self):
        s = opened()
        s, _ = until(s, 16 * 60)
        s, _ = close(s)
        N(s)['usual'] = dict(meal='bua_ngon', bed=24 * 60)    # a paid habit is never charged without a tap
        wallet = s['journey']['wallet']
        s, r = act(s, 'start_day')
        self.assertEqual(s['journey']['wallet'], wallet)
        self.assertTrue(any('Tối qua' in x and 'Cơm Bà Tám' in x for x in r['effects']))
        self.assertEqual(N(s)['wake'], nd.sleep_wake(24 * 60))
        self.assertEqual(N(s)['usual'], dict(meal='bua_ngon', bed=24 * 60))   # the habit stays

    def test_late_bedtimes_after_a_late_shift(self):
        s = opened()
        s, _ = until(s, 16 * 60)
        s, _ = close(s)
        N(s)['finish'] = 23 * 60 + 50
        rows = public_state(s)['needs']['evening']['meals'][0]['beds']
        self.assertEqual([b['bed'] for b in rows if b['ok']], [25 * 60])
        self.assertEqual(nd._default(s, N(s)), ('nha', 25 * 60))
        N(s)['finish'] = 25 * 60                               # 01:00, dinner till 01:30
        self.assertEqual([b['bed'] for b in nd.beds(N(s), 30)], [25 * 60 + 30])   # never without a bedtime
        with self.assertRaises(GameError):
            jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)

    def test_evening_shift_had_lunch_at_home(self):
        s = opened(career='delivery')
        self.assertGreaterEqual(dc.hours(s['careers']['delivery'], 'delivery')[0], nd.LATE_START)
        self.assertEqual(N(s)['lunch'], 'nha')
        self.assertIsNone(public_state(s)['needs']['lunch'])


class MoneyTests(unittest.TestCase):
    def evening(self, wallet):
        s = opened(wallet)
        s, _ = until(s, 15 * 60)
        s, _ = close(s)
        s['journey']['wallet'] = wallet
        return s

    def test_free_option_always_there(self):
        for wallet in (0, -50):
            s = self.evening(wallet)
            rows = {m['id']: m for m in public_state(s)['needs']['evening']['meals']}
            self.assertTrue(rows['nha']['ok'])
            self.assertFalse(rows['an_vat']['ok'])
            self.assertTrue(rows['an_vat']['why'])
            t, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
            self.assertEqual(t['journey']['wallet'], wallet)
        s = opened(0)
        s, _ = until(s, nd.LUNCH_FROM)
        rows = {c['id']: c for c in public_state(s)['needs']['lunch']['choices']}
        self.assertTrue(rows['hop']['ok'] and rows['nhin']['ok'])
        self.assertFalse(rows['binh_dan']['ok'])

    def test_not_enough_money_changes_nothing(self):
        s = self.evening(3)
        before = copy.deepcopy(s['journey'])
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_eve', meal='bua_ngon', bed=23 * 60)
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s['journey'], before)
        s = opened(2)
        s, _ = until(s, nd.LUNCH_FROM)
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_lunch', meal='binh_dan')
        self.assertEqual(e.exception.code, 'not_enough')

    def test_home_decides_the_free_dinner(self):
        s = self.evening(100)
        self.assertEqual(nd.meals(s)[0]['name'], 'Cơm Bà Tám để phần')
        hs.apply(s, 'jr_home_rent', dict(kind='ky_tuc_xa', confirm=True))
        self.assertEqual(nd.meals(s)[0]['name'], 'Mì gói ở phòng')
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None),
                             sticker=True, weddings=1)
        rows = {m['id']: m for m in nd.meals(s)}
        self.assertEqual(rows['vo_chong']['name'], 'Ăn tối cùng Bình')
        self.assertEqual(rows['vo_chong']['price'], 0)
        t, _ = jr_act(s, 'jr_needs_eve', meal='vo_chong', bed=23 * 60)
        self.assertEqual(t['journey']['wallet'], s['journey']['wallet'])
        s['marriage']['spouse']['status'] = 'engaged'
        self.assertNotIn('vo_chong', {m['id'] for m in nd.meals(s)})

    def test_living_cost_unchanged(self):
        """Meals at home stay inside the daily living cost: no second charge for food."""
        s = opened()
        s, _ = until(s, 17 * 60)
        before = s['journey']['wallet']
        s, _ = close(s)
        s, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
        s, _ = act(s, 'start_day')
        cost = jr.living_cost(s['journey'])['total']
        self.assertEqual(s['journey']['wallet'], before - jr.LIVING[1] + jr.WELCOME_GIFT)
        self.assertEqual(cost, jr.LIVING[1])   # 💹 07/10: 10 -> 11 xu


class SafetyTests(unittest.TestCase):
    def test_double_taps(self):
        s = opened()
        s, _ = until(s, nd.LUNCH_FROM)
        s, _ = jr_act(s, 'jr_needs_lunch', meal='binh_dan')
        wallet, n = s['journey']['wallet'], copy.deepcopy(N(s))
        s, r = jr_act(s, 'jr_needs_lunch', meal='binh_dan')     # the same tap again: nothing more
        self.assertEqual((s['journey']['wallet'], N(s)), (wallet, n))
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_lunch', meal='banh_mi')
        self.assertEqual(e.exception.code, 'already_done')
        s, _ = until(s, 17 * 60)
        s, _ = close(s)
        s, _ = jr_act(s, 'jr_needs_eve', meal='an_vat', bed=23 * 60)
        wallet, n, sp = s['journey']['wallet'], copy.deepcopy(N(s)), spirit(s)
        s, r = jr_act(s, 'jr_needs_eve', meal='an_vat', bed=23 * 60)
        self.assertEqual((s['journey']['wallet'], N(s), spirit(s)), (wallet, n, sp))
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_eve', meal='nha', bed=22 * 60)
        self.assertEqual(e.exception.code, 'already_done')

    def test_evening_only_after_closing(self):
        s = opened()
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
        self.assertEqual(e.exception.code, 'not_now')

    def test_junk_payloads(self):
        s = opened()
        s, _ = until(s, 17 * 60)
        s, _ = close(s)
        for p in (dict(meal='nha'), dict(meal='pho', bed=1380), dict(meal='nha', bed='23:00'), dict(meal='nha', bed=1381),
                  dict(meal='nha', bed=True), dict(meal='nha', bed=1380, x=1), dict(meal=['nha'], bed=1380)):
            with self.assertRaises(GameError, msg=p):
                jr_act(s, 'jr_needs_eve', **p)
        for p in (dict(), dict(meal='nha'), dict(meal=None), dict(meal='hop', extra=1)):
            with self.assertRaises(GameError, msg=p):
                jr_act(s, 'jr_needs_lunch', **p)
        with self.assertRaises(GameError):
            jr_act(s, 'jr_needs_other')

    def test_validation_rejects_bad_records(self):
        s = opened()
        validate_state(s)
        bad = [('full', 101), ('full', -1), ('wake', 1.5), ('day', 0), ('day', 99), ('lunch', 'pho'), ('low', ['full', 'full']),
               ('low', ['sleep']), ('seen', ['nowhere', 1, 30]), ('seen', [CAREER, 1]), ('finish', 'x'),
               ('eve', dict(meal='nha', bed=1380)),    # an evening choice while no evening is on
               ('eve', dict(meal='nha')), ('usual', dict(meal='pho', bed=1380)), ('usual', dict(meal='nha', bed=10)),
               ('v', 2), ('worked', -5)]
        for key, value in bad:
            t = copy.deepcopy(s)
            N(t)[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(t)
        t = copy.deepcopy(s)
        N(t)['extra'] = 1
        with self.assertRaises(GameError):
            validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['needs'] = []
        with self.assertRaises(GameError):
            validate_state(t)

    def test_older_save_without_needs(self):
        s = opened()
        old = copy.deepcopy(s)
        old['journey'].pop('needs')
        old.pop('check', None)
        validate_state(old)                                   # absent is fine
        v = public_state(old)['needs']
        self.assertEqual((v['full']['value'], v['wake']['value']), (nd.START_FULL, nd.START_WAKE))
        m = migrate_state(old)
        self.assertNotIn('needs', m['journey'])               # nothing written on load
        t, _ = act(old, 'advance')
        self.assertEqual(N(t)['day'], t['journey']['life_day'])
        self.assertEqual(N(t)['full'], nd.START_FULL)
        # The first command after the update closes the day: the evening is still offered.
        t, _ = close(old)
        self.assertEqual(N(t)['day'], t['journey']['life_day'] - 1)
        self.assertIsNotNone(public_state(t)['needs']['evening'])

    def test_story_off(self):
        s = new_state()
        s, _ = act(s, 'select_career')
        s, _ = act(s, 'start_day')
        for _ in range(20):
            s, _ = act(s, 'advance')
        self.assertNotIn('needs', s['journey'])
        self.assertEqual(public_state(s)['needs'], dict(enabled=False))
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_lunch', meal='hop')
        self.assertEqual(e.exception.code, 'locked')

    def test_many_days_stay_in_range(self):
        """Twenty days of mixed choices: the bars and tinh thần stay in range, the save always validates."""
        s = opened(300)
        meals, beds = ['nha', 'an_vat', 'bua_ngon', 'nha'], [22 * 60, 23 * 60, 24 * 60, 25 * 60]
        lunches = ['hop', 'binh_dan', 'banh_mi', 'nhin', None]
        for d in range(20):
            s, _ = until(s, nd.LUNCH_FROM)
            if lunches[d % 5]:
                s, _ = jr_act(s, 'jr_needs_lunch', meal=lunches[d % 5])
            s, _ = until(s, (16 + d % 5) * 60)
            s, _ = close(s)
            if d % 3:
                s, _ = jr_act(s, 'jr_needs_eve', meal=meals[d % 4], bed=beds[d % 4])
            s, _ = act(s, 'start_day')
            n = N(s)
            self.assertTrue(0 <= n['full'] <= 100 and 0 <= n['wake'] <= 100 and 0 <= spirit(s) <= 100)
            self.assertGreaterEqual(s['journey']['wallet'], 0)
            validate_state(s)


class SnackTests(unittest.TestCase):
    """Ăn thêm: paid, any time in the work day, refused when already full / awake or short of xu."""
    def test_buy_any_time_in_the_day(self):
        s = opened()
        s, _ = until(s, 9 * 60)                            # before lunch, too
        v = public_state(s)['needs']['snack']
        self.assertEqual([c['id'] for c in v], list(nd.SNACK))
        for item, x in nd.SNACK.items():
            n0 = N(s)
            if (x['full'] and n0['full'] >= nd.FULL_CAP) or (not x['full'] and n0['wake'] >= nd.WAKE_CAP):
                continue
            t, r = jr_act(s, 'jr_needs_snack', item=item)
            self.assertEqual(t['journey']['wallet'], 100 - x['price'], item)
            self.assertEqual(N(t)['full'], min(100, n0['full'] + x['full']), item)
            self.assertEqual(N(t)['wake'], min(100, n0['wake'] + x['wake']), item)
            self.assertEqual(spirit(t), spirit(s), item)       # no tinh thần from snacks
            row = t['journey']['history'][-1]
            self.assertEqual((row['kind'], row['amount']), ('living', -x['price']))
            self.assertTrue(r['message'])
        # Lunch is still there after a snack.
        s, _ = jr_act(s, 'jr_needs_snack', item='banh_bao')
        s, _ = until(s, nd.LUNCH_FROM)
        self.assertIsNotNone(public_state(s)['needs']['lunch'])

    def test_again_and_again_until_full(self):
        s = opened(500)
        s, _ = until(s, 15 * 60)
        bought = 0
        for _ in range(10):
            try:
                s, _ = jr_act(s, 'jr_needs_snack', item='xoi')
                bought += 1
            except GameError as e:
                self.assertEqual(e.code, 'too_full')
                break
        self.assertGreaterEqual(bought, 1)
        self.assertGreaterEqual(N(s)['full'], nd.FULL_CAP)
        self.assertEqual(s['journey']['wallet'], 500 - bought * nd.SNACK['xoi']['price'])
        self.assertFalse({c['id']: c for c in public_state(s)['needs']['snack']}['xoi']['ok'])
        validate_state(s)

    def test_coffee_refused_when_awake(self):
        s = opened()
        self.assertGreaterEqual(N(s)['wake'], nd.WAKE_CAP)
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_snack', item='ca_phe')
        self.assertEqual(e.exception.code, 'too_full')

    def test_never_debt_and_not_in_the_evening(self):
        s = opened(2)
        s, _ = until(s, 15 * 60)
        before = copy.deepcopy(s['journey'])
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_snack', item='banh_bao')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s['journey'], before)
        self.assertEqual({c['id']: c['why'] for c in public_state(s)['needs']['snack']}['pho'], 'Chưa đủ xu')
        s['journey']['wallet'] = 100
        s, _ = close(s)
        self.assertIsNone(public_state(s)['needs']['snack'])
        with self.assertRaises(GameError) as e:
            jr_act(s, 'jr_needs_snack', item='banh_bao')
        self.assertEqual(e.exception.code, 'not_now')

    def test_junk(self):
        s = opened()
        s, _ = until(s, 15 * 60)
        for p in (dict(), dict(item='nhin'), dict(item=None), dict(item='xoi', x=1), dict(meal='xoi')):
            with self.assertRaises(GameError, msg=p):
                jr_act(s, 'jr_needs_snack', **p)


if __name__ == '__main__':
    unittest.main()
