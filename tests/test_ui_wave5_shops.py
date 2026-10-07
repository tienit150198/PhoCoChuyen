"""UI wave 5, the shops (docs/UI_KIT.md "Disabled with a reason"): the pre-checks the work screens dim buttons with say
exactly what the command refuses with, from the same rule (game/careers/kit.py check), and they are view fields only.

- clothing: public_data can.ao_pick, the sizes a pick would be refused for ("Giá treo hết quần jean size 29…", the top
  clothing refusal 04–06/10);
- salon: public_data can.sl_mix, out of gloves ("Hết Găng tay…");
- repair: public_task can.rp_show (the water tag read white) and public_data can.rp_fix (a supply the repair uses up);
- pet_care: public_task can.pc_nails & co. (the pet is panicking), with the break as the fix."""
import json
import unittest
from unittest import mock

from game.careers import kit
from game.careers import clothing as AO
from game.careers import pet_care as PC
from game.careers import repair as RP
from game.careers import salon as SL
from game.engine import GameError
from tests.helpers import Journey


def refusal(fn, *args):
    try:
        fn(*args)
    except GameError as e:
        return str(e)
    return None


def fit_job():
    for day in range(1, 40):
        for slot in range(12):
            if (day, slot) in AO.STORY:
                continue
            t = AO.make_task(day, slot, 1)
            if t['kind'] == 'fit':
                j = Journey('clothing', slot=slot, day=day)
                j.act('ask', task=j.task['id'])
                return j
    raise AssertionError('no fit task')


class ClothingPick(unittest.TestCase):
    def test_a_sold_out_size_is_said_before_the_tap(self):
        j = fit_job()
        t = j.task
        line = t['needs']['lines'][0]
        item, size = line['item'], AO.SIZES[line['item']][0]
        g = j.c['ext']['data']['grid'][item]
        kit.take(j.c, item, g[size])
        g[size] = 0
        can = AO.public_data(j.c)['can']['ao_pick']
        self.assertIn(f'{item}:{size}', can)
        with self.assertRaises(GameError) as err:
            j.act('ao_pick', task=t['id'], item=item, size=size, colour=line['colour'])
        self.assertEqual(can[f'{item}:{size}']['why'], str(err.exception))
        self.assertEqual(can[f'{item}:{size}']['fix']['act'], 'v4Restock')
        json.dumps(can)

    def test_a_size_on_the_rack_is_not_listed_and_the_counter_holds_count(self):
        j = fit_job()
        t = j.task
        line = t['needs']['lines'][0]
        item = line['item']
        size = next(s for s in AO.SIZES[item] if j.c['ext']['data']['grid'][item].get(s, 0) == 1) if any(
            j.c['ext']['data']['grid'][item].get(s, 0) == 1 for s in AO.SIZES[item]) else None
        if size is None:   # make one size hold exactly one piece
            size = AO.SIZES[item][0]
            g = j.c['ext']['data']['grid'][item]
            kit.take(j.c, item, g[size] - 1)
            g[size] = 1
        self.assertNotIn(f'{item}:{size}', AO.public_data(j.c)['can']['ao_pick'])
        j.act('ao_pick', task=t['id'], item=item, size=size, colour=line['colour'])
        # The last piece is on this counter now: a second tap would be refused, and the view says so.
        self.assertIn(f'{item}:{size}', AO.public_data(j.c)['can']['ao_pick'])


class SalonGloves(unittest.TestCase):
    def test_out_of_gloves(self):
        j = Journey('salon')
        self.assertIs(SL.public_data(j.c)['can']['sl_mix'], True)
        kit.take(j.c, 'gloves', kit.stock(j.c, 'gloves'))
        can = SL.public_data(j.c)['can']['sl_mix']
        self.assertEqual(can['why'], 'Hết Găng tay. Mở Kho để nhập thêm nhé.')
        self.assertEqual(can['why'], refusal(SL._gloves_rules, j.c))
        self.assertEqual(can['fix']['data']['items'], 'gloves')


class RepairShowAndSupplies(unittest.TestCase):
    def test_a_white_water_tag(self):
        t = dict(bench=dict(tests=[dict(id='water_tag', reading='Tem báo nước còn trắng tinh')], shown=False), _fault='screen')
        can = kit.check(RP._show_rules, t)
        self.assertEqual(can['why'], refusal(RP._show_rules, t))
        self.assertTrue(can['why'].startswith('Tem báo nước còn trắng'))
        self.assertIs(kit.check(RP._show_rules, dict(t, _fault='water')), True)
        self.assertIn('Soi tem', kit.check(RP._show_rules, dict(t, bench=dict(tests=[], shown=False)))['why'])

    def test_a_supply_that_is_out(self):
        j = Journey('repair')
        fd = RP._fault_def('phone', 'water')
        self.assertIs(kit.check(RP._supply_rules, j.c, fd), True)
        kit.take(j.c, 'ipa', kit.stock(j.c, 'ipa'))
        can = kit.check(RP._supply_rules, j.c, fd)
        self.assertEqual(can['why'], refusal(RP._supply_rules, j.c, fd))
        self.assertTrue(can['why'].startswith('Hết ') and can['why'].endswith('Mở Kho để nhập thêm nhé.'))
        self.assertIs(kit.check(RP._supply_rules, j.c, RP._fault_def('phone', 'screen')), True)   # no supplies
        self.assertIn('rp_fix', RP.public_data(j.c)['can'])


class PetCalm(unittest.TestCase):
    def test_a_panicking_pet(self):
        t = dict(id='t1', g=dict(stress=PC.STRESS_STOP))
        can = kit.check(PC._calm_enough, t)
        self.assertEqual(can['why'], refusal(PC._calm_enough, t))
        self.assertEqual(can['fix']['cmd'], 'pc_calm')
        self.assertEqual(can['fix']['payload'], dict(task='t1', how='break'))
        self.assertIs(kit.check(PC._calm_enough, dict(t, g=dict(stress=PC.STRESS_STOP - 1))), True)

    def test_the_body_language_never_the_number(self):
        t = dict(id='t2', gen=True, g=dict(stress=PC.STRESS_STOP + 5))
        with mock.patch.object(PC, '_mood_line', return_value='gầm gừ, nhe răng'):
            can = kit.check(PC._calm_enough, t)
            self.assertEqual(can['why'], refusal(PC._calm_enough, t))
        self.assertTrue(can['why'].startswith('Bé đang hoảng: gầm gừ, nhe răng.'))
        self.assertNotIn(str(PC.STRESS_STOP + 5), can['why'])


if __name__ == '__main__':
    unittest.main()
