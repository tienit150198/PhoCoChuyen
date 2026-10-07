"""B10 (07/10): three iPhone commands were refused as too large (>256 KB) and nobody knew which action sent them.
server._log_big_command writes one line with the action, the size and the biggest payload fields by name and size,
never a value."""
import contextlib
import io
import unittest

import server


class BigCommandLog(unittest.TestCase):
    def line(self, data, length):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            server._log_big_command(data, length)
        return err.getvalue()

    def test_names_sizes_never_values(self):
        photo = 'data:image/jpeg;base64,' + 'A' * 300000
        out = self.line(dict(action='jr_lux_photo', career=None, payload=dict(photo=photo, caption='bí mật', n=1)), 300123)
        self.assertTrue(out.startswith('[cmd-413] action=jr_lux_photo career=- bytes=300123 photo='), out)
        self.assertIn('caption=', out)
        self.assertNotIn('AAAA', out)
        self.assertNotIn('bí mật', out)
        self.assertEqual(out.count('\n'), 1)

    def test_odd_input_is_clipped_and_safe(self):
        out = self.line(dict(action='x y="z"\n' + 'k' * 100, payload=['not', 'a', 'dict']), 270000)
        self.assertEqual(out.count('\n'), 1)
        self.assertIn('action=x?y??z??', out)
        self.assertLess(len(out), 120)
