"""UI wave 2 (docs/UI_KIT.md): the server pre-checks sent as can[action] for the uniformed careers say exactly what the
command refuses with (game/careers/kit.py check), and the public views stay JSON."""
import json
import unittest
from unittest import mock

from game.careers import kit
from game.careers import flight_attendant as FA
from game.careers import lifeguard as LG
from game.careers import nurse as NU
from game.careers import oil as OIL
from game.careers import pilot as PL
from game.careers import police as POL
from game.engine import GameError
from tests.helpers import Journey


def refusal(fn, *args):
    try:
        fn(*args)
    except GameError as e:
        return str(e)
    return None


class PoliceTopic(unittest.TestCase):
    def test_a_fourth_topic_says_the_limit(self):
        full = dict(topics=['a', 'b', 'c'][:POL.PC.TOPIC_MAX])
        can = kit.check(POL._add_topic_rules, full)
        self.assertEqual(can['why'], refusal(POL._add_topic_rules, full))
        self.assertIn(str(POL.PC.TOPIC_MAX), can['why'])
        self.assertIs(kit.check(POL._add_topic_rules, dict(topics=[])), True)


class NurseSend(unittest.TestCase):
    def test_no_to_the_operation_is_said_before_the_tap(self):
        t = dict(seen=['consent'], said=None)
        with mock.patch.object(NU, '_case_of', return_value=dict(variant='refuse')), mock.patch.object(NU, '_who', return_value='Anh Tuấn'):
            can = kit.check(NU._send_rules, t)
            self.assertEqual(can['why'], refusal(NU._send_rules, t))
            self.assertTrue(can['why'].startswith('Anh Tuấn đã nói không mổ'))
            self.assertIs(kit.check(NU._send_rules, dict(t, said='pushed')), True)   # talked round: a scored mistake, not a refusal
            self.assertIs(kit.check(NU._send_rules, dict(t, seen=[])), True)
        with mock.patch.object(NU, '_case_of', return_value=dict(variant='ok')), mock.patch.object(NU, '_who', return_value='Bà Tư'):
            self.assertIs(kit.check(NU._send_rules, t), True)


class LifeguardReopen(unittest.TestCase):
    def test_before_the_storm(self):
        t = dict(marks={})
        with mock.patch.object(LG, '_thunder_at', return_value=None):
            can = kit.check(LG._reopen_rules, t)
            self.assertEqual(can['why'], refusal(LG._reopen_rules, t))
            self.assertEqual(can['why'], 'Dông chưa tới: chờ, xem trời đã.')
            self.assertIs(kit.check(LG._reopen_rules, dict(marks={'shelter': 'hall'})), True)
        with mock.patch.object(LG, '_thunder_at', return_value=840):
            self.assertIs(kit.check(LG._reopen_rules, t), True)


class OilIsolation(unittest.TestCase):
    def task(self, locks, bled=False):
        job = next(j for j in OIL.K.JOBS if j['bleed'] and j['prove'])
        return dict(needs=dict(job=job['id']), locks=locks, bled=bled), job

    def test_bleed_and_prove_zero_wait_for_the_locks(self):
        t, job = self.task([])
        can = kit.check(OIL._bleed_rules, t)
        self.assertEqual(can['why'], refusal(OIL._bleed_rules, t))
        self.assertEqual(can['why'], 'Khóa đủ các van cô lập rồi mới xả.')
        self.assertEqual(kit.check(OIL._verify_rules, t)['why'], refusal(OIL._verify_rules, t))
        every = [p[0] for p in job['points']]
        t, _ = self.task(every)
        self.assertIs(kit.check(OIL._bleed_rules, t), True)
        self.assertEqual(kit.check(OIL._verify_rules, t)['why'], 'Xả áp trước rồi mới kiểm về không.')
        t, _ = self.task(every, bled=True)
        self.assertIs(kit.check(OIL._verify_rules, t), True)
        self.assertEqual(kit.check(OIL._bleed_rules, t)['why'], 'Đã xả rồi.')


class PilotTakeoffAround(unittest.TestCase):
    def test_takeoff(self):
        t = dict(switches=[], delay=0, pa=None)
        can = kit.check(PL._takeoff_rules, t)
        self.assertEqual(can['why'], refusal(PL._takeoff_rules, t))
        t = dict(switches=list(PL.ORDER), delay=15, pa=None)
        self.assertEqual(kit.check(PL._takeoff_rules, t)['why'], 'Chuyến bay chậm: thông báo cho khách trước đã.')
        self.assertIs(kit.check(PL._takeoff_rules, dict(t, pa='clear')), True)

    def test_around_at_the_alternate(self):
        t = dict(arounds=PL.MAX_AROUNDS, at='Rạch Giá')
        can = kit.check(PL._around_rules, t)
        self.assertEqual(can['why'], refusal(PL._around_rules, t))
        self.assertIs(kit.check(PL._around_rules, dict(arounds=0, at=None)), True)


class FlightAttendantCart(unittest.TestCase):
    def task(self, seat, given=(), skipped=(), nut=None):
        return dict(skipped=list(skipped), given={seat['seat']: list(given)} if given else {}, row=0,
                    needs=dict(ssr=dict(nut=nut) if nut else {}, rows=[dict(row=3, seats=[seat])]))

    def test_a_dish_the_seat_already_has(self):
        st = dict(seat='3A', kind='adult', drink='tea', snack='cake')
        t = self.task(st, given=['tea'])
        can = kit.check(FA._give_rules, t, st, 'tea')
        self.assertEqual(can['why'], refusal(FA._give_rules, t, st, 'tea'))
        self.assertEqual(can['why'], 'Ghế 3A đã có trà nóng rồi.')
        self.assertIs(kit.check(FA._give_rules, t, st, 'cake'), True)    # still due
        self.assertIs(kit.check(FA._give_rules, t, st, 'water'), True)   # wrong dish: a mistake the purser catches, not a refusal

    def test_mistakes_stay_mistakes(self):
        kid = dict(seat='3B', kind='kid', drink='tea', snack=None)
        self.assertIs(kit.check(FA._give_rules, self.task(kid), kid, 'coffee'), True)
        sleeper = dict(seat='3C', kind='sleep', drink='tea', snack=None)
        self.assertIs(kit.check(FA._give_rules, self.task(sleeper), sleeper, 'tea'), True)
        self.assertEqual(kit.check(FA._give_rules, self.task(sleeper, skipped=['3C']), sleeper, 'tea')['why'], 'Ghế này đã để khách ngủ.')
        st = dict(seat='3D', kind='adult', drink='water', snack='nuts')
        self.assertIs(kit.check(FA._give_rules, self.task(st, given=['water', 'nuts'], nut=3), st, 'nuts'), True)


class PublicViews(unittest.TestCase):
    def test_views_stay_json(self):
        for mod, cid in ((POL, 'police'), (NU, 'nurse'), (LG, 'lifeguard'), (OIL, 'oil'), (PL, 'pilot'), (FA, 'flight_attendant')):
            for slot in range(4):
                j = Journey(cid, slot=slot, day=3)
                v = mod.public_task(j.task)
                json.dumps(v)
                for can in (v.get('can') or {}).values():
                    self.assertTrue(can is True or isinstance(can, dict), (cid, can))


if __name__ == '__main__':
    unittest.main()
