"""Private leisure rounds validate outcomes, persistence and replay without minting money."""
import copy
import json
import math
import unittest
from unittest.mock import patch

from game import journey, leisure
from game.engine import GameError, apply_action, new_state, public_state, validate_state

# Release 1.8.0 keeps game/leisure.py (private pixel fishing/boat/pool rounds) but does not wire it: game/journey.py
# neither imports it nor routes jr_leisure_* actions, and saves carry no `leisure` block. See docs/PHASER_25D.md.
LEISURE_WIRED = any(module is leisure for module in vars(journey).values())


@unittest.skipUnless(LEISURE_WIRED, 'game/leisure.py is not wired into game/journey.py in 1.8.0 (no jr_leisure_* '
                     'actions); see docs/PHASER_25D.md')
class Leisure(unittest.TestCase):
    def setUp(self):
        self.s = new_state()
        self.now = 100000.0
        self.clock = patch('game.leisure.time.time', lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def act(self, name, **payload):
        self.s, result = apply_action(self.s, None, 'jr_leisure_' + name, payload)
        return result

    def test_fishing_server_species_timing_and_idempotent_finish(self):
        wallet = self.s['journey']['wallet']
        money = {k: c['money'] for k, c in self.s['careers'].items()}
        round = self.act('start', kind='fishing')['leisure_round']
        with self.assertRaises(GameError):
            self.act('finish', round=round['id'])
        self.now = round['bite_at'] + .2
        result = self.act('finish', round=round['id'])
        fish = result['leisure']['fish']
        self.assertEqual(sum(fish.values()), 1)
        duplicate = self.act('finish', round=round['id'])
        self.assertTrue(duplicate['duplicate'])
        self.assertEqual(sum(self.s['journey']['leisure']['fish'].values()), 1)
        self.assertEqual(self.s['journey']['wallet'], wallet)
        self.assertEqual({k: c['money'] for k, c in self.s['careers'].items()}, money)
        validate_state(self.s)
        self.assertEqual(public_state(self.s)['journey']['leisure']['fish'], fish)
        exported = json.loads(json.dumps(self.s))
        validate_state(exported)
        self.assertEqual(leisure.public(exported)['fish'], fish)

    def test_forged_ids_extra_fields_early_finish_and_expired_fishing(self):
        for payload in ({'kind': 'fishing', 'money': 9999}, {'kind': 'private-villa'}, {'kind': ['boat']}):
            with self.assertRaises(GameError):
                self.act('start', **payload)
        round = self.act('start', kind='fishing')['leisure_round']
        with self.assertRaises(GameError):
            self.act('finish', round='0'*32)
        with self.assertRaises(GameError):
            self.act('finish', round=round['id'], fish='ca_vang')
        self.now = round['bite_at'] + round['bite_window'] + 1
        with self.assertRaises(GameError):
            self.act('finish', round=round['id'])
        self.assertEqual(sum(leisure.public(self.s)['fish'].values()), 0)

    def test_boat_and_pool_require_ordered_reachable_timed_checkpoints(self):
        funds = {k: c['money'] for k, c in self.s['careers'].items()}
        wallet = self.s['journey']['wallet']
        for kind, key in (('boat', 'boat_laps'), ('pool', 'swim_laps')):
            round = self.act('start', kind=kind)['leisure_round']
            with self.assertRaises(GameError):
                self.act('finish', round=round['id'])
            with self.assertRaises(GameError):
                self.act('checkpoint', round=round['id'], index=1, x=0, y=0)
            first = round['checkpoints'][0]
            with self.assertRaises(GameError):
                self.act('checkpoint', round=round['id'], index=0, x=first[0], y=first[1])
            last = round['entry']
            for index, (x, y) in enumerate(round['checkpoints']):
                self.now += math.hypot(x-last[0], y-last[1])/leisure.MAX_SPEED + .5
                self.act('checkpoint', round=round['id'], index=index, x=x, y=y)
                replay = self.act('checkpoint', round=round['id'], index=index, x=x, y=y)
                self.assertTrue(replay['duplicate'])
                last = [x, y]
            self.now += round['min_seconds']
            self.act('finish', round=round['id'])
            self.act('finish', round=round['id'])
            self.assertEqual(leisure.public(self.s)[key], 1)
        validate_state(self.s)
        self.assertEqual(self.s['journey']['wallet'], wallet)
        self.assertEqual({k: c['money'] for k, c in self.s['careers'].items()}, funds)

    def test_rounds_are_private_and_replace_old_active_round(self):
        other = new_state()
        round = self.act('start', kind='boat')['leisure_round']
        with self.assertRaises(GameError):
            apply_action(other, None, 'jr_leisure_finish', {'round': round['id']})
        newer = self.act('start', kind='pool')['leisure_round']
        self.assertNotEqual(round['id'], newer['id'])
        with self.assertRaises(GameError):
            self.act('finish', round=round['id'])
        self.assertNotIn('leisure', other['journey'])
        self.assertEqual(leisure.public(other)['boat_laps'], 0)

    def test_invalid_persisted_data_is_rejected_and_old_saves_remain_valid(self):
        leisure.validate(self.s)
        self.act('start', kind='pool')
        damaged = copy.deepcopy(self.s)
        damaged['journey']['leisure']['swim_laps'] = True
        with self.assertRaises(GameError):
            validate_state(damaged)
