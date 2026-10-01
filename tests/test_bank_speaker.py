"""Loa báo tiền: transfers into the player's shop ride along the command result as `bank`
(game/bank_speaker.py), once per payment; the three sound switches are synced settings."""
import unittest

from game import bank_speaker
from game.engine import GameError, apply_action, new_state, validate_state
from tests.test_career_grocery import journey, scan_all


def checkout(title):
    j = journey(title)
    j.act('ask')
    scan_all(j)
    j.act('gr_total')
    return j


class GroceryTransferTest(unittest.TestCase):
    def test_checked_transfer_is_announced_once_when_it_lands(self):
        j = checkout('Bữa sáng mang đi')
        total = j.task['total']
        self.assertEqual(j.act('gr_verify')['bank'], [total])
        self.assertNotIn('bank', j.act('gr_verify'))          # checking the app again: no second announcement
        self.assertNotIn('bank', j.act('gr_pay', confirm=True))

    def test_unchecked_transfer_is_announced_at_the_till(self):
        j = checkout('Bữa sáng mang đi')
        total = j.task['total']
        self.assertEqual(j.act('gr_pay', confirm=True)['bank'], [total])

    def test_typo_then_top_up(self):
        j = checkout('Quán cơm nhập gấp')
        total, screen = j.task['total'], j.task['pay']['screen']['amount']
        self.assertEqual(j.act('gr_verify')['bank'], [screen])
        self.assertEqual(j.act('gr_transfer_fix')['bank'], [total - screen])
        self.assertNotIn('bank', j.act('gr_pay', confirm=True))

    def test_pending_transfer_speaks_when_it_arrives(self):
        j = checkout('Đồ cho buổi họp nhóm')
        self.assertNotIn('bank', j.act('gr_verify'))
        self.assertEqual(j.act('gr_verify')['bank'], [j.task['total']])
        self.assertNotIn('bank', j.act('gr_pay', confirm=True))

    def test_steps_before_payment_say_nothing(self):
        j = journey('Bữa sáng mang đi')
        self.assertNotIn('bank', j.act('ask'))
        with self.assertRaises(GameError):
            j.act('gr_verify')                                  # bill not locked yet: rolled back, no event


class GroceryRegularsTest(unittest.TestCase):
    def test_weekly_bag_paid_by_transfer_is_announced_cash_is_not(self):
        from game.careers import grocery as G
        from tests.test_career_grocery import GroceryListTests
        day = GroceryListTests()._day
        j = day(3)                                               # Bà Sáu: cash
        j.act('gr_pack', npc='grocery_npc_05')
        self.assertNotIn('bank', j.act('end_day', carry_event=True))
        j = day(4)                                               # key 6: "chị chuyển khoản"
        self.assertEqual(G.LISTS[6]['pay'], 'transfer')
        j.act('gr_pack', npc='grocery_npc_07')
        value = G._list_value(j.c, G._list_for(6, 4))
        self.assertEqual(j.act('end_day', carry_event=True).get('bank'), [value])


class HomestayTransferTest(unittest.TestCase):
    def arrive(self, **extra):
        from tests.helpers import Journey
        j = Journey('homestay')
        j.c['ext']['data']['bookings'] = [dict(id='bk-t', rooms=['gac'], start=j.c['day'], nights=2, guests=3, name='Đoàn thử',
                                               total=72, deposit=22, task=None, **extra)]
        return j.act('end_day')

    def test_ota_payout_is_announced_direct_arrival_is_not(self):
        self.assertEqual(self.arrive(ota='Mây Travel').get('bank'), [50])
        self.assertNotIn('bank', self.arrive())                 # pays the rest at the desk: no transfer

    def test_the_anniversary_couple_transfers_their_deposit(self):
        from game.careers import homestay as H
        from tests.helpers import Journey
        j = Journey('homestay')
        j.c['ext']['data']['bookings'] = []
        heard = []
        while j.c['day'] < H.ANNIV_FIRST - H.ANNIV_LEAD:
            heard += j.act('end_day', carry_event=True).get('bank', []) + j.act('start_day').get('bank', [])
        b = next(b for b in j.c['ext']['data']['bookings'] if b.get('anniv'))
        self.assertIn(b['deposit'], heard)


class CollectTest(unittest.TestCase):
    def test_outside_a_command_is_ignored_and_amounts_are_clean(self):
        bank_speaker.transfer(10)                              # no command running: nothing to attach to
        _s, r = bank_speaker.collect(lambda: ({}, dict(message='x')))
        self.assertNotIn('bank', r)

        def run():
            for a in (12, 0, -3, 1.5, True, 30):
                bank_speaker.transfer(a)
            return {}, dict(message='ok')
        _s, r = bank_speaker.collect(run)
        self.assertEqual(r['bank'], [12, 30])


class SoundSettingsTest(unittest.TestCase):
    KEYS = ('npcVoices', 'detailSfx', 'bankVoice', 'moneyTing')

    def test_defaults_on_and_toggle(self):
        s = new_state()
        for k in self.KEYS:
            self.assertIs(s['settings'][k], True)
        s, _ = apply_action(s, None, 'settings', dict(bankVoice=False, npcVoices=False))
        self.assertIs(s['settings']['bankVoice'], False)
        self.assertIs(s['settings']['npcVoices'], False)
        with self.assertRaises(GameError):
            apply_action(s, None, 'settings', dict(detailSfx='yes'))

    def test_older_save_gains_the_switches(self):
        s = new_state()
        for k in self.KEYS:
            del s['settings'][k]
        s, _ = apply_action(s, None, 'settings', dict(bankVoice=False))
        self.assertIs(s['settings']['bankVoice'], False)
        self.assertIs(s['settings']['npcVoices'], True)
        validate_state(s)


class MoneyInContractTest(unittest.TestCase):
    """public/js/v4/sounds.js (moneyIn) hears money coming in from the state alone: journey.wallet, journey.life_day
    and journey.history, newest row first, each with its amount and kind ('salary' is read as pay)."""

    def test_new_wallet_rows_lead_the_view(self):
        from game import journey as jr
        from game.engine import public_state
        s = new_state()
        before = public_state(s)['journey']
        jr._wallet(s['journey'], 120, 'salary', 'Lương ngày 1 · thử')
        jr._wallet(s['journey'], -40, 'living', 'Tiền ăn ở')
        after = public_state(s)['journey']
        self.assertEqual(after['wallet'] - before['wallet'], 80)
        self.assertEqual([(r['amount'], r['kind']) for r in after['history'][:2]], [(-40, 'living'), (120, 'salary')])
        self.assertEqual(after['history'][2:], before['history'][:len(after['history']) - 2])
        self.assertIn('life_day', after)


class TingFileTest(unittest.TestCase):
    """The recorded bell ships small, as MP3 (iOS), with its licence written down."""

    def test_file_size_and_credit(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'public' / 'audio' / 'sfx'
        data = (root / 'ting.mp3').read_bytes()
        self.assertLess(len(data), 30 * 1024)
        self.assertTrue(data[:3] == b'ID3' or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0))
        self.assertLessEqual(sum(p.stat().st_size for p in root.iterdir() if p.is_file()), 500 * 1024)
        credits = (root / 'CREDITS.md').read_text(encoding='utf-8')
        self.assertIn('ting.mp3', credits)
        self.assertIn('CC0', credits)


if __name__ == '__main__':
    unittest.main()
