"""🧰 Review fixes of the restoration workshop (game/careers/restore.py): Chú Khải, the owner, never brings a ticket; a
piece is brought by someone who would own it; the right finish is read off the surface written on the ticket; paper and
cloth never get paint words; the workshop's own styles stay inside the workshop (the 🧰 Bàn thợ dialog and the research
career use .rs-* names too)."""
import re
import unittest
from pathlib import Path

from game.careers import PLUGINS, kit
from game.careers import restore_content as C

ROOT = Path(__file__).resolve().parents[1]
R = PLUGINS.get('restore')


@unittest.skipUnless(R, 'restore filtered out by MNL_CAREERS')
class Tickets(unittest.TestCase):
    def test_the_owner_never_brings_a_ticket_and_each_piece_has_a_fitting_owner(self):
        seen = set()
        for day in range(1, 60):
            for slot in range(10):
                t = R.make_task(day, slot, 1)
                who = int(t['npc'].rsplit('_', 1)[1]) - 1
                self.assertNotEqual(C.PEOPLE[who][0], C.OWNER)
                self.assertIn(who, C.OWNERS[t['kind']])
                seen.add(who)
        self.assertEqual(seen, set(range(1, len(C.PEOPLE))))
        self.assertEqual(set(C.OWNERS), {x[0] for x in C.ITEMS})
        self.assertTrue(all(0 not in v for v in C.OWNERS.values()))

    def test_the_finish_follows_the_surface_on_the_ticket(self):
        for kind, title, _, material, damages, finish, parts in C.ITEMS:
            surface = C.SURFACE[kind][0]
            self.assertEqual(C.FINISH_BY_SURFACE[surface], finish, kind)
        for day in range(1, 60):
            for slot in range(4):
                t = R.make_task(day, slot, 1)
                n = t['needs']
                self.assertEqual(n['surface'], C.SURFACE[t['kind']][1])
                self.assertEqual(n['surface_kind'], C.SURFACES[C.SURFACE[t['kind']][0]])
                wished = [C.DEMANDS[d['id']][4].get('finish') for d in n['demands'] if C.DEMANDS[d['id']][4].get('finish')]
                want = wished[0] if wished else C.FINISH_BY_SURFACE[C.SURFACE[t['kind']][0]]
                self.assertEqual(t['_key']['finish'], want)
        self.assertTrue(any('bề mặt' in r for r in C.RULES))

    def test_paper_and_cloth_get_no_paint_words(self):
        for kind, title, _, material, damages, finish, parts in C.ITEMS:
            if material in ('paper', 'fabric'):
                self.assertNotIn('flake', damages, kind)
                for d in damages:
                    self.assertNotIn('sơn', C.DAMAGES[d][1])
        self.assertEqual(C.FIXES['stain'], 'spot_clean')
        self.assertIn('spot_clean', {k for k, _ in C.FIX_OPTIONS})


class Styles(unittest.TestCase):
    def test_restore_css_is_scoped_to_the_workshop(self):
        css = (ROOT / 'public/css/careers/restore.css').read_text(encoding='utf-8')
        for sel in re.findall(r'([^{}]+)\{', css):
            sel = sel.strip()
            if sel.startswith('@'):
                continue
            for part in sel.split(','):
                if '.rs-' in part:
                    self.assertRegex(part, r'(^|\s)\.rs\s', part)

    def test_the_bench_take_line_names_the_giao_do_button(self):
        js = (ROOT / 'public/js/v4/restore.js').read_text(encoding='utf-8')
        self.assertIn('🎁 Giao đồ', js)
        self.assertIn("op==='take'", js)


if __name__ == '__main__':
    unittest.main()
