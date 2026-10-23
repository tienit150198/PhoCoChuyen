"""Career command prefixes: a new plugin must not reuse another career's prefix or a core one.

The engine dispatches a command by its career first (game/engine.py apply_action: `plugin_action` is the CURRENT
career's prefix), so the pairs already shipped are safe and stay as they are (renaming would break saves with a job in
progress). The singer's `cs_` equals customer_care's core prefix: the core open-shift rule must not catch the singer's
free `cs_intro` (fixed with this test; the client's shutWork in public/js/app.js follows the same rule).
"""
import re
import unittest
from pathlib import Path

from tests.helpers import Journey
from game.careers import PLUGINS
from game.engine import GameError, apply_action, new_state

# Shipped before this guard, safe because dispatch is by career. Never add to this list: pick a free prefix.
KNOWN_SHARED = {'rs_': {'restaurant', 'research'}, 'fa_': {'farm', 'flight_attendant'}, 'dx_': {'tuning', 'car_dealer'}}
KNOWN_CORE = {'cs_': {'singer'}}
# Prefixes the engine/core careers own (engine.py, experiences.NEW_ACTION_PREFIXES, desk, journey, life layers…).
CORE = ('shop_', 'ac_', 'cs_', 'ph_', 'cl_', 'desk_', 'lesson_', 'tour_', 'tea_', 'life_', 'gift_', 'ops_', 'inv_', 'sit_',
        'fb_', 'job_', 'soc_', 'inc_', 'hap_', 'pm_', 'jr_', 'scale_', 'payk_', 'mastery_', 'competition_')


def _clash(a: str, b: str) -> bool:
    return a.startswith(b) or b.startswith(a)


class Prefixes(unittest.TestCase):
    def test_no_new_shared_prefix_between_plugins(self):
        ids = sorted(PLUGINS)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pa, pb = PLUGINS[a].SPEC['prefix'], PLUGINS[b].SPEC['prefix']
                if not _clash(pa, pb):
                    continue
                allowed = KNOWN_SHARED.get(pa) if pa == pb else None
                self.assertTrue(allowed and {a, b} <= allowed, f'{a} ({pa}) and {b} ({pb}) share a command prefix')

    def test_no_new_plugin_on_a_core_prefix(self):
        for cid, mod in PLUGINS.items():
            p = mod.SPEC['prefix']
            self.assertRegex(p, r'^[a-z]{2,5}_$', cid)
            for core in CORE:
                if _clash(p, core):
                    self.assertIn(cid, KNOWN_CORE.get(core, ()), f'{cid} ({p}) overlaps the core prefix {core}')


@unittest.skipIf('singer' not in PLUGINS, 'singer filtered out by MNL_CAREERS')
class SingerIntroWithShiftClosed(unittest.TestCase):
    def _closed(self, career):
        s = new_state()
        from game.employment import hired_record, required
        if required(career):
            s['careers'][career]['job'] = hired_record(career)
        s, _ = apply_action(s, career, 'select_career', {})
        self.assertFalse(s['careers'][career]['open'])
        return s

    def test_singer_intro_is_free(self):
        s = self._closed('singer')
        self.assertIn('cs_intro', PLUGINS['singer'].SPEC['free_actions'])
        s, r = apply_action(s, 'singer', 'cs_intro', {})
        self.assertTrue(s['careers']['singer']['ext']['data']['intro'])
        self.assertFalse(s['careers']['singer']['open'])

    def test_singer_work_still_needs_the_shift(self):
        s = self._closed('singer')
        with self.assertRaisesRegex(GameError, 'Mở ca'):
            apply_action(s, 'singer', 'cs_step', {})

    def test_customer_care_still_needs_the_shift(self):
        s = self._closed('customer_care')
        with self.assertRaisesRegex(GameError, 'Mở ca'):
            apply_action(s, 'customer_care', 'cs_identity', {})

    def test_customer_care_open_shift_still_works(self):
        j = Journey('customer_care')
        self.assertTrue(j.c['open'])
        j.solve()


class ClientShiftGate(unittest.TestCase):
    """public/js/app.js shutWork: the current career's plugin gate decides its own prefix first."""

    def test_plugin_gate_before_core_regex(self):
        src = (Path(__file__).resolve().parents[1] / 'public/js/app.js').read_text(encoding='utf-8')
        line = next(x for x in src.splitlines() if 'needs=op=>' in x)
        self.assertRegex(line, re.escape('needs=op=>g&&op.startsWith(g.prefix)?!g.free.includes(op):SHUT_WORK.test(op)'))


if __name__ == '__main__':
    unittest.main()
