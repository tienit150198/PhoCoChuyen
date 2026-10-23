"""✈️ Du lịch trải nghiệm (game/travel.py, feedback #464): the catalogue (every place has its own spots and souvenirs,
fares sit in the economy), the booking price rules (flying today costs most, booking early is the good price, business
class), validation (no past day, no farther than the airline sells, money, one ticket at a time, the visa of game/lux.py),
cancel and missed-flight refunds (never more than paid), the trip's steps (board, meal, land, spots, souvenirs, home),
the collection (stamps, postcards, souvenirs, log), the life-day morning, the lux trip it counts as, and saves."""
import copy
import unittest

from game import lux
from game import travel as tv
from game import travel_content as C
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act, story


def TV(s):
    return s['journey']['travel']


def money(s):
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def today(s):
    return s['journey']['life_day']


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def next_day(s, n=1):
    for _ in range(n):
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_seen', ids=['x'])   # any command: journey.after runs every morning's catch-up
    return s


def book(s, to='da_lat', cls='eco', ahead=0):
    return act(s, 'jr_trip_book', to=to, cls=cls, day=today(s) + ahead, confirm=True)


def give_visa(s, country, days=30):
    b = lux._ensure(s)
    b['visa'][country] = today(s) + days - 1
    validate_state(s)
    return s


class Catalogue(unittest.TestCase):
    def test_places_have_their_own_identity(self):
        kinds = {d['kind'] for d in C.DESTS}
        self.assertEqual(kinds, {'vn', 'intl'})
        self.assertGreaterEqual(sum(d['kind'] == 'vn' for d in C.DESTS), 5)
        self.assertGreaterEqual(sum(d['kind'] == 'intl' for d in C.DESTS), 6)
        for name in ('Đà Lạt', 'Hội An', 'Phú Quốc', 'Hạ Long', 'Sa Pa', 'Hàn Quốc', 'Nhật Bản', 'Thái Lan', 'Pháp', 'Úc', 'Trung Quốc'):
            self.assertIn(name, [d['name'] for d in C.DESTS])
        for d in C.DESTS:
            self.assertTrue(3 <= len(d['spots']) <= 6, d['id'])
            self.assertEqual(len(d['souv']), 3, d['id'])
            self.assertTrue(d['greet'] and d['tag'] and d['skyline'] and d['airport'], d['id'])
            for k in ('sky', 'land', 'accent'):
                self.assertRegex(d[k], r'^#[0-9a-f]{6}$')
            self.assertGreaterEqual(len({sp['kind'] for sp in d['spots']}), 3, d['id'])   # a photo, a dish, a game or a rest
            self.assertTrue(all(sp['kind'] in C.KINDS and sp['line'] and 0 <= sp['fee'] <= 200 and 1 <= sp['sp'] <= 6 for sp in d['spots']))
            self.assertEqual([g['price'] for g in d['souv']], sorted(g['price'] for g in d['souv']))
            if d['visa']:
                self.assertIn(d['visa'], lux.COUNTRY)   # the consulate's paperwork lives in game/lux.py
        self.assertFalse(next(d for d in C.DESTS if d['id'] == 'thai_lan')['visa'])   # miễn visa

    def test_ids_unique_and_shaped(self):
        ids = [d['id'] for d in C.DESTS] + [sp['id'] for d in C.DESTS for sp in d['spots']] + [g['id'] for d in C.DESTS for g in d['souv']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(tv.ID_RE.fullmatch(i) for i in ids))
        meals = [m['id'] for m in C.MEALS['food'] + C.MEALS['drink']]
        self.assertEqual(len(meals), len(set(meals)))

    def test_fares_follow_the_rules(self):
        for d in C.DESTS:
            f = [tv.fare(d['id'], 'eco', a) for a in range(C.MAX_AHEAD + 1)]
            self.assertEqual(f, sorted(f, reverse=True), d['id'])            # never dearer for booking earlier
            self.assertEqual(len(set(f[C.GOOD_AHEAD:])), 1)                  # 4+ days ahead: the good price
            self.assertAlmostEqual(f[0] / f[C.GOOD_AHEAD], 2, delta=0.05)   # flying today: about twice
            biz = tv.fare(d['id'], 'biz', C.GOOD_AHEAD)
            self.assertAlmostEqual(biz / f[C.GOOD_AHEAD], 3, delta=0.05)
            self.assertTrue(all(x % 10 == 0 for x in f))
        vn = [tv.fare(d['id'], 'eco', C.GOOD_AHEAD) for d in C.DESTS if d['kind'] == 'vn']
        intl = [tv.fare(d['id'], 'eco', C.GOOD_AHEAD) for d in C.DESTS if d['kind'] == 'intl']
        self.assertTrue(all(200 <= x <= 450 for x in vn))      # about a good day's pay (median ≈ 262 xu a life day)
        self.assertTrue(all(1000 <= x <= 7000 for x in intl))
        self.assertLess(max(vn), min(intl))

    def test_catalogue_for_the_client(self):
        k = tv.catalogue()
        self.assertEqual(len(k['dests']), len(C.DESTS))
        d = k['dests'][0]
        self.assertEqual(d['fares']['eco'], [tv.fare(d['id'], 'eco', a) for a in range(C.MAX_AHEAD + 1)])
        self.assertEqual(set(d['fares']), {'eco', 'biz'})
        self.assertTrue(all(sp['fee'] >= 0 for sp in d['spots']))
        from game import journey
        self.assertEqual(journey.content()['travel']['dests'][0]['id'], C.DESTS[0]['id'])


class Booking(unittest.TestCase):
    def test_book_today_costs_most_and_early_is_cheaper(self):
        s = story(5000)
        s1, r = book(copy.deepcopy(s), ahead=0)
        s2, _ = book(copy.deepcopy(s), ahead=C.GOOD_AHEAD)
        self.assertEqual(money(s) - money(s1), tv.fare('da_lat', 'eco', 0))
        self.assertEqual(money(s) - money(s2), tv.fare('da_lat', 'eco', C.GOOD_AHEAD))
        self.assertGreater(money(s2), money(s1))
        self.assertEqual(TV(s2)['book'], dict(to='da_lat', cls='eco', day=today(s) + C.GOOD_AHEAD, at=today(s),
                                              paid=tv.fare('da_lat', 'eco', C.GOOD_AHEAD)))
        self.assertIn('giá tốt', act(copy.deepcopy(s), 'jr_trip_book', to='da_lat', cls='eco', day=today(s) + 5, confirm=True)[1]['message'])
        s3, _ = book(copy.deepcopy(s), cls='biz', ahead=C.GOOD_AHEAD)
        self.assertEqual(money(s) - money(s3), tv.fare('da_lat', 'biz', C.GOOD_AHEAD))

    def test_wallet_then_bank(self):
        s = story(100)
        s, _ = act(s, 'jr_bk_open')
        s['journey']['bank']['balance'] = 1000
        validate_state(s)
        before = money(s)
        s, r = book(s, ahead=C.GOOD_AHEAD)
        self.assertEqual(before - money(s), tv.fare('da_lat', 'eco', C.GOOD_AHEAD))
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertIn('tài khoản', r['message'])

    def test_validation(self):
        s = story(5000)
        s['journey']['life_day'] = 10
        s = next_day(s, 0)
        refused(self, s, 'jr_trip_book', 'past', to='da_lat', cls='eco', day=9, confirm=True)
        refused(self, s, 'jr_trip_book', 'too_far', to='da_lat', cls='eco', day=10 + C.MAX_AHEAD + 1, confirm=True)
        refused(self, s, 'jr_trip_book', to='atlantis', cls='eco', day=10, confirm=True)
        refused(self, s, 'jr_trip_book', to='da_lat', cls='first', day=10, confirm=True)
        refused(self, s, 'jr_trip_book', to='da_lat', cls='eco', day='10', confirm=True)
        refused(self, s, 'jr_trip_book', to='da_lat', cls='eco', day=10)                       # no confirm
        refused(self, s, 'jr_trip_book', to='da_lat', cls='eco', day=10, confirm=True, extra=1)
        poor = story(50)
        refused(self, poor, 'jr_trip_book', 'not_enough', to='da_lat', cls='eco', day=today(poor), confirm=True)
        debt = story(5000)
        debt['journey']['wallet'] = -10
        refused(self, debt, 'jr_trip_book', 'not_enough', to='da_lat', cls='eco', day=today(debt), confirm=True)
        s, _ = book(s, ahead=2)
        msg = refused(self, s, 'jr_trip_book', 'already_done', to='hoi_an', cls='eco', day=12, confirm=True)   # one ticket at a time
        self.assertIn('Hủy vé đó trước', msg)

    def test_visa_is_the_consulates(self):
        s = story(50000)
        msg = refused(self, s, 'jr_trip_book', 'no_visa', to='han_quoc', cls='eco', day=today(s) + 4, confirm=True)
        self.assertIn('visa Hàn Quốc', msg)
        s, _ = book(copy.deepcopy(s), to='thai_lan')                       # Thái Lan: no visa
        s = give_visa(story(50000), 'han_quoc', days=3)                   # valid today .. today + 2
        refused(self, s, 'jr_trip_book', 'no_visa', to='han_quoc', cls='eco', day=today(s) + 3, confirm=True)
        s, _ = book(s, to='han_quoc', ahead=2)
        self.assertEqual(public_state(s)['journey']['travel']['visa'], {'han_quoc': today(s) + 2})
        s = give_visa(story(50000), 'chau_au')
        s, _ = book(s, to='phap', ahead=1)                                  # Pháp: the Schengen visa of Châu Âu
        s = give_visa(story(50000), 'uc')
        s, _ = book(s, to='uc', ahead=1)                                    # 🇦🇺 joined game/lux.py for this

    def test_cancel_refunds(self):
        s = story(5000)
        s, _ = book(s, ahead=3)
        paid = TV(s)['book']['paid']
        refused(self, s, 'jr_trip_cancel', confirm=False)
        before = s['journey']['wallet']
        s1, r = act(copy.deepcopy(s), 'jr_trip_cancel', confirm=True)
        self.assertEqual(s1['journey']['wallet'] - before, paid * C.REFUND_EARLY // 100)
        self.assertIsNone(TV(s1)['book'])
        self.assertEqual(public_state(s)['journey']['travel']['book']['back'], paid * C.REFUND_EARLY // 100)
        s2 = next_day(s, 3)                                                  # the flight's day: half
        before = s2['journey']['wallet']
        s2, _ = act(s2, 'jr_trip_cancel', confirm=True)
        self.assertEqual(s2['journey']['wallet'] - before, paid * C.REFUND_LATE // 100)
        refused(self, s2, 'jr_trip_cancel', 'not_found', confirm=True)
        self.assertLessEqual(TV(s2)['stats']['back'], paid)

    def test_missed_flight_refunds_half_by_itself(self):
        s = story(5000)
        s, _ = book(s, ahead=1)
        paid = TV(s)['book']['paid']
        s = next_day(s)
        self.assertEqual(public_state(s)['journey']['travel']['book']['left'], 0)
        before = s['journey']['wallet']
        s['journey']['life_day'] += 1
        s, r = act(s, 'jr_seen', ids=['x'])
        self.assertIsNone(TV(s)['book'])
        self.assertEqual(s['journey']['wallet'] - before, paid * C.REFUND_LATE // 100)
        self.assertTrue(any('lỡ chuyến' in e for e in r['effects']))
        s = next_day(s)
        self.assertEqual(s['journey']['wallet'] - before, paid * C.REFUND_LATE // 100)   # once


class Trip(unittest.TestCase):
    def test_the_whole_journey(self):
        s = story(5000)
        start = money(s)
        s, _ = book(s, ahead=2)
        refused(self, s, 'jr_trip_board', 'not_yet')
        refused(self, s, 'jr_trip_meal', 'locked', food='com_ga', drink='tra_nong')
        s = next_day(s, 2)
        s, r = act(s, 'jr_trip_board')
        self.assertIsNone(TV(s)['book'])
        self.assertEqual(TV(s)['trip']['ph'], 'fly')
        refused(self, s, 'jr_trip_book', 'already_done', to='hoi_an', cls='eco', day=today(s) + 4, confirm=True)
        refused(self, s, 'jr_trip_spot', 'locked', id='dl_ho')
        refused(self, s, 'jr_trip_meal', 'locked', food='bo_bit_tet', drink='vang_do')       # business-class menu
        s, r = act(s, 'jr_trip_meal', food='com_ga', drink='tra_nong')
        self.assertTrue(r['effects'][0].startswith('💁'))
        refused(self, s, 'jr_trip_meal', 'already_done', food='mi_bo', drink='nuoc_cam')
        s, r = act(s, 'jr_trip_land')
        self.assertEqual(r['travel'], dict(stamp='da_lat', first=True))
        self.assertEqual(TV(s)['trip']['ph'], 'here')
        self.assertEqual(TV(s)['stamps'], {'da_lat': 1})
        self.assertIn('Đà Lạt', r['effects'][0])
        refused(self, s, 'jr_trip_spot', id='ha_cau')                                       # another place's spot
        refused(self, s, 'jr_trip_buy', 'locked', id='ha_gom')
        spent = 0
        for sp in tv.DEST['da_lat']['spots']:
            w = money(s)
            s, r = act(s, 'jr_trip_spot', id=sp['id'])
            self.assertEqual(w - money(s), sp['fee'])
            spent += sp['fee']
            self.assertEqual(r['travel'], dict(card=sp['id'], new=True))
            self.assertEqual(r['effects'], [sp['line']])
        refused(self, s, 'jr_trip_spot', 'already_done', id='dl_ho')
        g = tv.DEST['da_lat']['souv'][0]
        s, _ = act(s, 'jr_trip_buy', id=g['id'])
        s, _ = act(s, 'jr_trip_buy', id=g['id'])
        spent += 2 * g['price']
        self.assertEqual(TV(s)['souv'], {g['id']: 2})
        self.assertEqual(TV(s)['trip']['xu'], spent)
        s, r = act(s, 'jr_trip_home')
        self.assertEqual(TV(s)['trip']['ph'], 'back')
        refused(self, s, 'jr_trip_buy', 'locked', id=g['id'])
        s, _ = act(s, 'jr_trip_meal', food='banh_mi', drink='ca_phe')                         # the way home: a meal again
        s, r = act(s, 'jr_trip_land')
        x = r['travel']['summary']
        self.assertEqual((x['to'], x['n'], x['xu'], x['cards'], x['of']), ('da_lat', 5, spent, 5, 5))
        self.assertGreater(x['sp'], 10)
        self.assertIsNone(TV(s)['trip'])
        self.assertEqual(len(TV(s)['log']), 1)
        self.assertEqual(TV(s)['stats']['trips'], 1)
        self.assertEqual(start - money(s), tv.fare('da_lat', 'eco', 2) + spent)   # every xu accounted for
        refused(self, s, 'jr_trip_land', 'locked')
        # a second trip: the same postcards are not counted twice, the stamp is
        s, _ = book(s)
        s, _ = act(s, 'jr_trip_board')
        s, r = act(s, 'jr_trip_land')
        self.assertFalse(r['travel']['first'])
        s, r = act(s, 'jr_trip_spot', id='dl_ho')
        self.assertFalse(r['travel']['new'])
        self.assertEqual(TV(s)['cards'].count('dl_ho'), 1)
        self.assertEqual(TV(s)['stamps'], {'da_lat': 2})

    def test_business_class_and_needs(self):
        s = story(5000)
        s['journey'].setdefault('needs', None)
        from game import needs
        needs.ensure(s)
        s['journey']['needs']['full'], s['journey']['needs']['wake'] = 30, 30
        s, _ = book(s, cls='biz')
        s, _ = act(s, 'jr_trip_board')
        s, _ = act(s, 'jr_trip_meal', food='bo_bit_tet', drink='vang_do')
        self.assertEqual(s['journey']['needs']['full'], 30 + C.MEAL_FULL)
        s, _ = act(s, 'jr_trip_land')
        self.assertEqual(s['journey']['needs']['wake'], 30 + C.BIZ_WAKE)
        s, _ = act(s, 'jr_trip_spot', id='dl_cho')   # a dish
        self.assertEqual(s['journey']['needs']['full'], 30 + C.MEAL_FULL + C.FOOD_FULL)
        s, _ = act(s, 'jr_trip_spot', id='dl_doi')   # a rest
        self.assertEqual(s['journey']['needs']['wake'], 30 + C.BIZ_WAKE + C.REST_WAKE)

    def test_spot_money_and_spirit_caps(self):
        s = story(5000)
        s, _ = book(s, to='phu_quoc')
        s, _ = act(s, 'jr_trip_board')
        s, _ = act(s, 'jr_trip_land')
        s['journey']['wallet'] = 10
        refused(self, s, 'jr_trip_spot', 'not_enough', id='pq_lan')        # 77 xu
        s, _ = act(s, 'jr_trip_spot', id='pq_sao')                          # free
        s['journey']['life']['spirit'] = 100
        s, r = act(s, 'jr_trip_spot', id='pq_dinh')
        self.assertEqual(s['journey']['life']['spirit'], 100)
        self.assertNotIn('Tinh thần', r['message'])

    def test_a_trip_left_open_flies_home(self):
        s = story(5000)
        s, _ = book(s)
        s, _ = act(s, 'jr_trip_board')
        s, _ = act(s, 'jr_trip_land')
        s = next_day(s, C.STAY_DAYS)
        self.assertIsNotNone(TV(s)['trip'])
        s['journey']['life_day'] += 1
        s, r = act(s, 'jr_seen', ids=['x'])
        self.assertIsNone(TV(s)['trip'])
        self.assertEqual(len(TV(s)['log']), 1)
        self.assertTrue(any('bay về nhà' in e for e in r['effects']))

    def test_abroad_counts_as_a_lux_trip(self):
        s = give_visa(story(50000), 'han_quoc')
        s, _ = book(s, to='han_quoc')
        s, _ = act(s, 'jr_trip_board')
        s, r = act(s, 'jr_trip_land')
        b = lux.get(s)
        self.assertEqual(b['trips'], {'han_quoc': 1})
        self.assertIn('in_han_quoc', b['today'])                            # the lux souvenir shop of that country opens
        self.assertEqual(b['album'][-1]['k'], 'trip')
        s, _ = act(s, 'jr_lux_souv', id='mat_na_hahoe')
        # Thái Lan has no lux country: nothing written there
        s2 = story(50000)
        s2, _ = book(s2, to='thai_lan')
        s2, _ = act(s2, 'jr_trip_board')
        s2, _ = act(s2, 'jr_trip_land')
        self.assertIsNone(lux.get(s2))

    def test_three_countries_earn_the_lux_title(self):
        s = story(500000)
        for c, to in (('han_quoc', 'han_quoc'), ('nhat_ban', 'nhat_ban'), ('trung_quoc', 'trung_quoc')):
            s = give_visa(s, c)
            s, _ = book(s, to=to)
            s, _ = act(s, 'jr_trip_board')
            s, r = act(s, 'jr_trip_land')
            s, _ = act(s, 'jr_trip_home')
            s, _ = act(s, 'jr_trip_land')
        self.assertIn('t_xe_dich', lux.earned(s))


class Saves(unittest.TestCase):
    def test_absent_block_and_public(self):
        s = story(500)
        self.assertNotIn('travel', s['journey'])
        validate_state(s)
        pub = public_state(s)['journey']['travel']
        self.assertEqual((pub['stamps'], pub['cards'], pub['trips']), ({}, [], 0))
        self.assertNotIn('book', pub)
        s, _ = book(story(5000), ahead=1)
        p = public_state(s)['journey']['travel']['book']
        self.assertEqual((p['to'], p['left']), ('da_lat', 1))
        self.assertRegex(p['code'], r'^MA\d{3}$')
        self.assertTrue(1 <= p['gate'] <= 24)
        self.assertEqual(p, public_state(s)['journey']['travel']['book'])   # the same ticket every time

    def test_strict_shape(self):
        s, _ = book(story(5000))
        for bad in (lambda b: b.update(v=2), lambda b: b['book'].update(day='x'), lambda b: b['stamps'].update(da_lat=-1),
                    lambda b: b.update(cards=['dl_ho', 'dl_ho']), lambda b: b['log'].append({'to': 'x'}),
                    lambda b: b.update(trip=dict(to='da_lat', cls='eco', day=1, ph='moon', meal='', seen=[], xu=0, sp=0)),
                    lambda b: b.pop('souv')):
            x = copy.deepcopy(s)
            bad(TV(x))
            with self.assertRaises(GameError):
                validate_state(x)

    def test_newer_build_keys_kept_and_upgrade(self):
        s, _ = book(story(5000))
        TV(s)['future'] = {'x': 1}
        validate_state(s)
        s, _ = act(s, 'jr_seen', ids=['x'])
        self.assertEqual(TV(s)['future'], {'x': 1})
        j = copy.deepcopy(s['journey'])
        j['travel']['cards'] = ['dl_ho', 'dl_ho', 'BAD']
        j['travel']['stats'] = 'x'
        tv.upgrade(j)
        self.assertEqual(j['travel']['cards'], ['dl_ho'])
        self.assertEqual(j['travel']['stats'], {k: 0 for k in tv.STATS})
        self.assertEqual(j['travel']['future'], {'x': 1})
        j['travel'] = 'broken'
        tv.upgrade(j)
        self.assertEqual(j['travel'], tv.initial())

    def test_unknown_place_from_a_newer_build_is_kept_quietly(self):
        s, _ = book(story(5000))
        TV(s)['book']['to'] = 'sao_hoa'
        validate_state(s)
        self.assertNotIn('book', public_state(s)['journey']['travel'])
        refused(self, s, 'jr_trip_board', 'locked')
        s, _ = act(s, 'jr_trip_cancel', confirm=True)   # still refundable

    def test_story_only(self):
        from game.engine import new_state
        s = new_state()
        s['journey']['story'] = False
        with self.assertRaises(GameError):
            act(s, 'jr_trip_book', to='da_lat', cls='eco', day=1, confirm=True)


if __name__ == '__main__':
    unittest.main()
