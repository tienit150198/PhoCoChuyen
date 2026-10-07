"""🛏️ Ký túc xá Hẻm 7 (game/housing.py DORM, feedback #59): renting a bed in a shared bunk room, its price against
Bà Tám's attic, moving between rooms, the roommates' everyday moments (game/life.py kind 'dorm'), the bunk room on
the home card, old saves and validation."""
import copy
import unittest

from game import housing as hs
from game import journey as jr
from game import life as lf
from game.engine import GameError, migrate_state, public_state, validate_state
from game.life_content import CATS, DORM, DORM_LINES, ROOMMATES
from tests.test_bank import act, story

DORM_ID = 'ky_tuc_xa'
LOOK_SLOTS = {'hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc'}


def H(s):
    return s['journey']['home']


def L(s):
    return s['journey']['life']


def live(s, n=1, salary=20, career='teacher'):
    """Close `n` life days in the engine's order: journey bumps life_day, the home catches up, then life rolls."""
    for _ in range(n):
        j = s['journey']
        j['days'] = (j['days'] + [dict(d=j['life_day'], c=career, m='normal')])[-60:]
        if salary:
            jr._wallet(j, salary, 'salary', 'Lương ngày')
        j['life_day'] += 1
        hs.on_life_day(s)
        lf.on_life_day(s, dict(summary=dict(completed=3)), career)
        validate_state(s)
    return s


def in_dorm(wallet=100, seed=4242):
    s = story(wallet=wallet, seed=seed)
    lf.migrate(s)
    s, r = act(s, 'jr_home_rent', kind=DORM_ID, confirm=True)
    return s, r


def until_dorm_card(s, limit=40):
    for _ in range(limit):
        live(s)
        card = L(s)['pending']
        if card and card['kind'] == 'dorm':
            return card
    raise AssertionError('no roommate moment in %d days' % limit)


class Listing(unittest.TestCase):
    def test_the_bed_is_listed_with_the_rented_rooms(self):
        H_ = hs.HOMES[DORM_ID]
        self.assertEqual((H_['kind'], H_['group'], H_['emoji'], H_['name']), ('rent', 'rent', '🛏️', 'Ký túc xá Hẻm 7'))
        self.assertEqual((H_['rent'], H_['deposit'], H_['comfort']), (7, 20, 0))
        self.assertEqual(hs.DORM, DORM_ID)
        self.assertIn(DORM_ID, hs.RENT)
        self.assertNotIn(DORM_ID, hs.OWN)
        rents = [k for k in hs.HOMES if hs.HOMES[k]['kind'] == 'rent']
        self.assertEqual(rents, sorted(rents, key=lambda k: hs.HOMES[k]['rent']))     # cheapest first in Phòng thuê
        row = next(m for m in hs.catalogue()['homes'] if m['id'] == DORM_ID)
        self.assertEqual((row['rent'], row['deposit'], row['comfort'], row['perk']), (7, 20, 0, H_['perk']))
        self.assertNotIn('price', row)

    def test_price_against_the_attic_and_the_room(self):
        """One xu dearer than Bà Tám's attic in chapter 1, the same in chapter 2, cheaper from chapter 3 on;
        always well under the closed room, with a smaller deposit and no comfort bonus."""
        bed, room = hs.HOMES[DORM_ID], hs.HOMES['tro_moi']
        attic = {ch: hs.attic_rent(dict(chapter=ch)) for ch in jr.LIVING}
        self.assertEqual(attic, {1: 6, 2: 7, 3: 9, 4: 10, 5: 12, 6: 13, 7: 13})   # 💹 07/10: LIVING indexed (the bed stays 7)
        self.assertGreater(bed['rent'], attic[1])
        self.assertEqual(bed['rent'], attic[2])
        for ch in range(3, jr.LAST + 1):
            self.assertLess(bed['rent'], attic[ch], ch)
        self.assertLess(bed['rent'] * 2, room['rent'] + 1)
        self.assertLess(bed['deposit'], room['deposit'])
        self.assertLess(bed['comfort'], room['comfort'])


class RentAndLeave(unittest.TestCase):
    def test_rent_daily_rent_no_comfort_then_leave(self):
        s = story(wallet=100)
        lf.migrate(s)
        attic = jr.living_cost(s['journey'])
        with self.assertRaises(GameError):
            act(s, 'jr_home_rent', kind=DORM_ID)                              # no confirm
        s, r = act(s, 'jr_home_rent', kind=DORM_ID, confirm=True)
        self.assertEqual(s['journey']['wallet'], 80)                          # the 20 xu deposit
        self.assertIn('tiền giường 7 xu/ngày', r['message'])
        self.assertEqual(H(s)['rent'], dict(kind=DORM_ID, since=s['journey']['life_day'], deposit=20))
        cost = jr.living_cost(s['journey'])
        self.assertEqual((cost['rent'], cost['meals'], cost['where']), (7, attic['meals'], 'rent'))
        self.assertEqual(cost['label'], 'Tiền giường ký túc xá và cơm nước')
        sp = L(s)['spirit']
        for _ in range(3):                                                    # the home itself adds no tinh thần
            s['journey']['life_day'] += 1
            hs.on_life_day(s)
        self.assertEqual(L(s)['spirit'], sp)
        self.assertEqual((H(s)['stats']['rent_days'], H(s)['stats']['comfort']), (3, 0))
        validate_state(s)
        s, r = act(s, 'jr_home_leave', confirm=True)
        self.assertEqual((s['journey']['wallet'], H(s)['rent']), (100, None))
        self.assertIn('Đã trả giường', r['message'])
        self.assertIn('nhận lại 20 xu', H(s)['log'][-1]['text'])
        self.assertEqual(jr.living_cost(s['journey']), attic)
        with self.assertRaises(GameError) as e:
            act(story(wallet=19), 'jr_home_rent', kind=DORM_ID, confirm=True)
        self.assertEqual(e.exception.code, 'not_enough')

    def test_the_living_cost_the_day_takes(self):
        s, _ = in_dorm(wallet=100)
        before = s['journey']['wallet']
        jr._wallet(s['journey'], -jr.living_cost(s['journey'])['total'], 'living', jr.living_cost(s['journey'])['label'])
        self.assertEqual(before - s['journey']['wallet'], 7 + jr.living_cost(s['journey'])['meals'])
        validate_state(s)

    def test_moving_between_the_bed_and_the_room(self):
        s, _ = in_dorm(wallet=100)
        with self.assertRaises(GameError):
            act(s, 'jr_home_rent', kind=DORM_ID, confirm=True)                # already here
        poor = copy.deepcopy(s)
        poor['journey']['wallet'] = 39                                        # 39 + the 20 back < the room's 60
        with self.assertRaises(GameError) as e:
            act(poor, 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertEqual(e.exception.code, 'not_enough')
        row = next(m for m in hs.public(poor)['market'] if m['id'] == 'tro_moi')
        self.assertEqual(row['missing'], 1)                                   # the deposit coming back counts
        s, r = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertEqual((s['journey']['wallet'], H(s)['rent']['kind'], H(s)['rent']['deposit']), (80 + 20 - 60, 'tro_moi', 60))
        self.assertIn('Đã trả giường ký túc xá Hẻm 7, nhận lại 20 xu', r['message'])
        s, r = act(s, 'jr_home_rent', kind=DORM_ID, confirm=True)             # and back: 60 in, 20 out
        self.assertEqual((s['journey']['wallet'], H(s)['rent']['kind']), (40 + 60 - 20, DORM_ID))
        validate_state(s)

    def test_buying_a_home_ends_the_bed(self):
        s, _ = in_dorm(wallet=2200)
        price = hs.HOMES['tap_the']['price']
        s, r = act(s, 'jr_home_buy', kind='tap_the', down=price, confirm=True)
        self.assertTrue(r['approved'])
        self.assertIsNone(H(s)['rent'])
        self.assertEqual(s['journey']['wallet'], 2200 - price - hs.buy_fee(price) - hs.tax('tap_the'))   # the 20 xu came back
        validate_state(s)


class HomeCard(unittest.TestCase):
    def test_bunk_room_and_line_of_the_day(self):
        s, _ = in_dorm()
        view = public_state(s)['journey']['home']
        place = view['place']
        self.assertEqual((place['where_id'], place['kind'], place['comfort']), ('rent', DORM_ID, 0))
        d = place['dorm']
        self.assertEqual([m['id'] for m in d['mates']], list(ROOMMATES))
        beds = [m['bed'] for m in d['mates']] + [d['you']]
        self.assertEqual(sorted(beds), sorted(hs.BEDS))                      # four beds, one each
        for m in d['mates']:
            self.assertEqual(set(m['look']), LOOK_SLOTS)
            self.assertIn(m['gender'], ('male', 'female'))
        self.assertIn(d['line']['text'], DORM_LINES[d['line']['who']])
        self.assertEqual(hs.dorm_view(s), d)                                  # the same all day
        lines = set()
        for _ in range(12):
            s['journey']['life_day'] += 1
            lines.add(hs.dorm_view(s)['line']['text'])
        self.assertGreater(len(lines), 3)                                     # another one most days
        self.assertNotIn('dorm', H(s))                                        # computed, never stored
        other = story(wallet=100)
        self.assertNotIn('dorm', hs.public(other)['place'])
        other, _ = act(other, 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertNotIn('dorm', hs.public(other)['place'])

    def test_renovation_is_for_owned_homes_only(self):
        from game import reno as rn
        s, _ = in_dorm()
        with self.assertRaises(GameError):
            act(s, 'jr_reno_fix', part='wall')
        self.assertNotIn('reno', s['journey'])
        rn.public(s)                                                          # the view still builds


class RoommateMoments(unittest.TestCase):
    def test_authored_moments_are_small(self):
        self.assertEqual(len(ROOMMATES), 3)
        self.assertEqual(len({m['name'] for m in ROOMMATES.values()}), 3)
        self.assertIn('ktx', CATS)
        ids = [x['id'] for x in DORM]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(DORM), 8)
        for x in DORM:
            with self.subTest(x['id']):
                self.assertIn(x['who'], ROOMMATES)
                self.assertTrue(set(x.get('also', ())) <= set(ROOMMATES))
                self.assertLessEqual(len(x['title']), 80)
                self.assertTrue(1 <= len(x['lines']) <= 2)
                self.assertEqual(len(x['choices']), 2)
                self.assertEqual(sum(1 for c in x['choices'] if c['default']), 1)
                for c in x['choices']:
                    self.assertTrue(-3 <= c['spirit'] <= 3)
                    self.assertTrue(-5 <= c['money'] <= 5)
                    self.assertLessEqual(len(c['text']), 160)
                    if c['default']:
                        self.assertGreaterEqual(c['money'], 0)               # left undecided: never costs xu
        self.assertEqual(set(DORM_LINES), set(ROOMMATES))

    def test_moments_come_only_while_in_the_dorm_and_are_deterministic(self):
        s, _ = in_dorm()
        twin = copy.deepcopy(s)
        seen_a, seen_b = [], []
        for st, seen in ((s, seen_a), (twin, seen_b)):
            for _ in range(60):
                live(st)
                c = L(st)['pending']
                seen.append((c['kind'], c['ref']) if c else None)
        self.assertEqual(seen_a, seen_b)
        dorm = [x for x in seen_a if x and x[0] == 'dorm']
        self.assertGreaterEqual(len(dorm), 8)                                 # about a quarter of the days
        self.assertLessEqual(len(dorm), 30)
        self.assertGreaterEqual(len({r for _, r in dorm}), 6)                 # varied
        days = [i for i, x in enumerate(seen_a) if x and x[0] == 'dorm']
        for a in range(len(days)):                                           # the same moment not within DORM_RECENT
            for b in range(a + 1, len(days)):
                if seen_a[days[a]] == seen_a[days[b]]:
                    self.assertGreaterEqual(days[b] - days[a], lf.DORM_RECENT)
        attic = story(wallet=100)
        lf.migrate(attic)
        live(attic, 60)
        self.assertFalse(any(r['kind'] == 'dorm' for r in L(attic)['log']))

    def test_the_attic_never_asks_the_dorm(self):
        """A player who does not live there never reaches the dorm's roll: their cards are exactly as before."""
        a = story(wallet=100)
        lf.migrate(a)
        orig = lf._roll_dorm

        def boom(*x):
            raise AssertionError('the dorm rolled for a player in the attic')
        lf._roll_dorm = boom
        try:
            live(a, 40)
        finally:
            lf._roll_dorm = orig

    def test_choose_a_moment(self):
        s, _ = in_dorm(wallet=100)
        card = until_dorm_card(s)
        view = lf.public(s)['pending']
        self.assertEqual((view['kind'], view['stage'], view['cat']), ('dorm', 'dorm', 'ktx'))
        self.assertIn(view['speaker']['id'], ROOMMATES)
        self.assertEqual(set(view['speaker']['look']), LOOK_SLOTS)
        x = lf.DORM_INDEX[card['ref']]
        pick = next(c for c in x['choices'] if not c['default'])
        sp, w = L(s)['spirit'], s['journey']['wallet']
        s, r = act(s, 'lf_choose', id=card['id'], choice=pick['id'])
        self.assertEqual(L(s)['spirit'], max(0, min(100, sp + pick['spirit'])))
        self.assertEqual(s['journey']['wallet'], w + pick['money'])
        self.assertEqual(L(s)['pending']['stage'], 'done')
        row = L(s)['log'][-1]
        self.assertEqual((row['kind'], row['cat'], row['who'][0]), ('dorm', 'ktx', x['who']))
        s, _ = act(s, 'lf_close', id=card['id'])
        self.assertIsNone(L(s)['pending'])
        validate_state(s)
        log = lf.public(s)['log'][0]
        self.assertEqual(log['who'][0]['name'], ROOMMATES[x['who']]['name'])

    def test_undecided_takes_the_free_default(self):
        s, _ = in_dorm(wallet=100)
        card = until_dorm_card(s)
        x = lf.DORM_INDEX[card['ref']]
        d = next(c for c in x['choices'] if c['default'])
        sp = L(s)['spirit']
        s['journey']['wallet'] = 0                                            # broke: still fine
        lf._auto(s, L(s), card)
        self.assertEqual(card['stage'], 'done')
        self.assertEqual(card['money'], d['money'])
        self.assertEqual(s['journey']['wallet'], d['money'])
        self.assertEqual(L(s)['spirit'], max(0, min(100, sp + d['spirit'])))

    def test_paid_choice_needs_the_money(self):
        s, _ = in_dorm(wallet=100)
        for _ in range(80):
            card = until_dorm_card(s)
            x = lf.DORM_INDEX[card['ref']]
            paid = next((c for c in x['choices'] if c['money'] < 0), None)
            if paid:
                break
            act(s, 'lf_choose', id=card['id'], choice=x['choices'][0]['id'])
        s['journey']['wallet'] = 0
        view = next(c for c in lf.public(s)['pending']['choices'] if c['id'] == paid['id'])
        self.assertFalse(view['ok'])
        with self.assertRaises(GameError) as e:
            act(s, 'lf_choose', id=card['id'], choice=paid['id'])
        self.assertEqual(e.exception.code, 'not_enough')

    def test_leaving_keeps_a_pending_moment_valid(self):
        s, _ = in_dorm(wallet=100)
        until_dorm_card(s)
        s, _ = act(s, 'jr_home_leave', confirm=True)
        validate_state(s)
        live(s, 2)                                                            # settled by default, no new ones
        self.assertFalse(L(s)['pending'] and L(s)['pending']['kind'] == 'dorm')


class Saves(unittest.TestCase):
    def test_old_saves_load_and_validate(self):
        s = story(wallet=300)                                                 # never rented: no home block at all
        self.assertNotIn('home', s['journey'])
        validate_state(migrate_state(copy.deepcopy(s)))
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)          # an older rented room: unchanged
        old = copy.deepcopy(s)
        again = migrate_state(copy.deepcopy(s))
        validate_state(again)
        self.assertEqual(again['journey']['home'], old['journey']['home'])

    def test_the_bed_survives_migration_and_bad_saves_are_refused(self):
        s, _ = in_dorm()
        until_dorm_card(s)
        again = migrate_state(copy.deepcopy(s))
        validate_state(again)
        self.assertEqual(again['journey']['home']['rent']['kind'], DORM_ID)
        self.assertEqual(again['journey']['life']['pending'], s['journey']['life']['pending'])
        for mutate in (lambda t: H(t)['rent'].__setitem__('deposit', 60),          # the dorm's deposit is 20
                       lambda t: H(t)['rent'].__setitem__('kind', 'ky_tuc_xa_2'),
                       lambda t: L(t)['pending'].__setitem__('ref', 'ktx_khong_co'),
                       lambda t: L(t)['pending'].__setitem__('stage', 'react'),
                       lambda t: L(t)['pending']['who'].append('ktx_nguoi_la')):
            bad = copy.deepcopy(s)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)


if __name__ == '__main__':
    unittest.main()
