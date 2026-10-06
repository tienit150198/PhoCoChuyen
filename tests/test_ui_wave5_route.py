"""UI wave 5 (docs/UI_KIT.md "Disabled with a reason"): the courier's pre-checks the page uses before it asks.

- can.dl_signal: only the refusals. "<stop>" for the stop the scooter stands at ("Chọn điểm đến trước khi lái.", 155
  refusals 04–06/10) and "<stop>:<i>,<j>" for a lit junction off the planned next leg ("Ngã tư này ngoài chặng đang
  giao…", 420). The street view never sends those.
- can.dl_ride: the planned next leg by the main road; the fuel refusal (128) with a fix to the petrol station.
All are view fields of delivery.public_data: computed, never saved."""
import unittest

from game import traffic
from game.careers import delivery as D
from game.engine import GameError
from tests.helpers import Journey


def refusal(jr, action, **payload):
    try:
        jr.act(action, **payload)
    except GameError as e:
        return str(e.args)
    return None


class SignalCan(unittest.TestCase):
    def setUp(self):
        self.j = Journey('delivery')

    def can(self):
        return D.public_data(self.j.c)['can']

    def test_the_stop_you_stand_at_says_why(self):
        at = self.j.c['ext']['data']['at']
        sig = self.can()['dl_signal']
        self.assertEqual(sig[at], dict(why='Chọn điểm đến trước khi lái.', fix=None))
        self.assertEqual([k for k in sig if ':' not in k], [at], 'only the current stop is refused as a target')
        self.assertIn(sig[at]['why'], refusal(self.j, 'dl_signal', target=at, i=1, j=1, axis='x'))

    def test_off_leg_junctions_match_the_command(self):
        self.j.act('dl_plan', route=['alley'])     # a short leg: some lit junctions lie off it
        sig = self.can()['dl_signal']
        off = on = 0
        for i, jj in sorted(traffic.LIT):
            said = refusal(self.j, 'dl_signal', target='alley', i=i, j=jj, axis='x')
            key = f'alley:{i},{jj}'
            if said is None:
                self.assertNotIn(key, sig)
                on += 1
            else:
                self.assertIn(sig[key]['why'], said)
                off += 1
        self.assertTrue(on and off, 'both kinds of junction exist on this leg')

    def test_no_route_no_leg_checks(self):
        self.assertFalse([k for k in self.can()['dl_signal'] if ':' in k])

    def test_view_only(self):
        self.can()
        self.assertNotIn('can', self.j.c['ext']['data'])


class RideCan(unittest.TestCase):
    def setUp(self):
        self.j = Journey('delivery')
        self.j.act('dl_plan', route=['apt'])
        self.d = self.j.c['ext']['data']

    def need(self, to):
        return D._leg(self.j.c, self.d['at'], to, self.d['clock'])['fuel']

    def test_full_tank_can_ride(self):
        self.assertIs(D.public_data(self.j.c)['can']['dl_ride'], True)

    def test_short_of_fuel_says_why_with_a_fix_to_the_petrol_station(self):
        self.assertLess(self.need('gas'), self.need('apt'))
        self.d['fuel'] = self.need('gas')
        can = D.public_data(self.j.c)['can']['dl_ride']
        self.assertTrue(can['why'].startswith('Không đủ xăng tới Chung cư Mây Xanh'))
        self.assertEqual(can['fix'], dict(cmd='dl_plan', payload=dict(route=['gas', 'apt']), label='⛽ Ghé cây xăng'))
        self.assertIn(can['why'], refusal(self.j, 'dl_ride', way='main'))

    def test_too_little_even_for_the_station_has_no_fix(self):
        self.d['fuel'] = 0
        can = D.public_data(self.j.c)['can']['dl_ride']
        self.assertIsNone(can['fix'])

    def test_no_route_means_nothing_to_check(self):
        self.d['route'] = []
        self.assertIs(D.public_data(self.j.c)['can']['dl_ride'], True)


if __name__ == '__main__':
    unittest.main()
