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


class InvalidDataLog(unittest.TestCase):
    """23/10 (Kai): "Dữ liệu không đúng cấu trúc" told nobody which command broke. server._log_invalid_data writes
    the route, action, career, exception type and the last frames, never a payload value."""

    def line(self, data, err):
        out = io.StringIO()
        server._bad_budget[:] = [0.0, 0]
        with contextlib.redirect_stderr(out):
            server._log_invalid_data('/api/command', data, err)
        return out.getvalue()

    def test_action_type_and_frames(self):
        def boom(d):
            return d['missing']
        try:
            boom({})
        except KeyError as e:
            out = self.line(dict(action='inv_receive', career='canteen', payload=dict(note='bí mật')), e)
        self.assertTrue(out.startswith('[cmd-400] /api/command action=inv_receive career=canteen KeyError @ '), out)
        self.assertIn('test_command_413_log.py:', out)
        self.assertIn(':boom', out)
        self.assertNotIn('bí mật', out)
        self.assertEqual(out.count('\n'), 1)

    def test_not_a_dict_and_the_cap(self):
        out = self.line(None, ValueError('x'))
        self.assertIn('action=- career=- ValueError', out)
        err = io.StringIO()
        server._bad_budget[:] = [0.0, 0]
        with contextlib.redirect_stderr(err):
            for _ in range(40):
                server._log_invalid_data('/api/command', {}, ValueError('x'))
        self.assertEqual(err.getvalue().count('\n'), 30)
