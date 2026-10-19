"""⚔️ Bang sheet, smooth taps (owner 21/10 "bang bấm còn giật giật lắm nên sửa lại đi"): the server side of it (no
write transaction under the week's lock on a page read in the launch week, 👑 kept across a member's write while
the lists and boards are dropped) and the client's contract (public/js/v4/bang.js patches the sheet in place,
marks only the tapped button pending, keeps the chosen amount, keys the lists, ⏰ Đền vàng as a call to action).
Measured with scripts/browser_bang_perf.py; the browser checks are there and in scripts/browser_bang.py."""
import re
import unittest
from pathlib import Path

from game import bang
from tests.test_bang import Base, T0

ROOT = Path(__file__).resolve().parents[1]


class Crown(Base):
    def counting(self):
        calls = []
        real = self.store.transaction

        def tx(fn, *a, **k):
            calls.append(fn)
            return real(fn, *a, **k)
        self.store.transaction = tx
        self.addCleanup(lambda: setattr(self.store, 'transaction', real))
        return calls

    def test_launch_week_reads_only(self):
        """Every bang was founded this week: nobody can have won last week, so 👑 is a plain read (before: a write
        transaction under pg_advisory_xact_lock for every page drawn after any write)."""
        a = self.player(name='Lan')
        self.found(a)
        calls = self.counting()
        bang._VIEW.clear()
        self.assertIsNone(bang.crown(self.store))
        bang._VIEW.clear()
        view = bang.get_view(self.store, a, {})
        self.assertFalse(view['page']['crowned'])
        self.assertEqual(calls, [])
        self.assertEqual(self.rows('SELECT * FROM bang_week_win'), [])

    def test_a_bang_of_last_week_still_freezes(self):
        a = self.player(name='Lan')
        x = self.found(a)
        self.give(a, 2_000_000)
        self.t[0] = T0 + 7 * 86400      # next week: Rồng Đỏ was there last week
        bang._VIEW.clear()
        self.assertEqual(bang.crown(self.store), x)
        self.assertEqual(self.one('SELECT bang FROM bang_week_win')['bang'], x)

    def test_a_write_keeps_the_crown_and_drops_the_boards(self):
        a = self.player(name='Lan')
        self.found(a)
        bang._VIEW.clear()
        bang.get_view(self.store, a, {})
        bang.search(self.store, None)
        keys = {k[0] for k in bang._VIEW}
        self.assertEqual(keys, {'crown', 'board', 'search'})
        self.store.transaction(lambda db: db.execute('UPDATE bangs SET isle=1'))   # ⭐ +1 level (🏝️), behind the cached board
        calls = self.counting()
        out = self.op(a, 'checkin')
        self.assertIn('Điểm danh', out['done']['message'])
        self.assertEqual(len(calls), 1)                                     # the check-in; 👑 from the cache
        self.assertNotIn('search', {k[0] for k in bang._VIEW})             # the lists show counts: drawn again
        from game import bang_content as BC
        self.assertEqual(out['board']['top'][0]['score'], 2 * BC.LEVEL_SCORE)   # the board drawn again: hall 1 + island 1 (cống hiến never counts)
        self.assertIn('crown', {k[0] for k in bang._VIEW})


class Client(unittest.TestCase):
    src = (ROOT / 'public/js/v4/bang.js').read_text(encoding='utf-8')
    css = (ROOT / 'public/css/bang.css').read_text(encoding='utf-8')

    def test_patched_in_place(self):
        self.assertNotIn('innerHTML=page()', self.src)
        self.assertIn('morph(root,page())', self.src)
        self.assertNotRegex(self.src, r"S\.busy\?' disabled'")              # the sheet is never greyed as a whole
        self.assertNotRegex(self.src, r'S\.busy\|\|why')
        self.assertIn('is-pending', self.src)
        self.assertIn('.bg-dock', self.css)

    def test_lists_are_keyed(self):
        for key in ('data-k="m:${x.pid}"', 'data-k="f:${f.id}"', 'data-k="i:${s.id}"', 'data-k="b:${esc(c.id)}"', 'data-k="fund"', 'data-k="golden"'):
            self.assertIn(key, self.src)

    def test_the_amount_stays(self):
        give = re.search(r"case'give':\{(.*?)return;\}", self.src, re.S).group(1)
        self.assertNotIn('S.amount=0', give)

    def test_den_vang_call_to_action(self):
        self.assertIn("if(!lv.den_vang)return denVang(p);", self.src)
        for text in ('🏗️ Xây ', 'Quỹ còn thiếu', '🙌 Góp quỹ', 'xong là chọn được giờ vàng', 'Nhờ Bang chủ/Phó bang xây'):
            self.assertIn(text, self.src)


if __name__ == '__main__':
    unittest.main()
