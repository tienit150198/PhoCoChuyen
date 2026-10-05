"""game/fastjson.py: orjson when installed, the standard library otherwise, same results.

Runs with and without orjson (PYTHONPATH=<dir with orjson> to test the fast path). The
stored save must stay byte for byte json.dumps(raw, ensure_ascii=False, separators=(",", ":")):
its per-career digests (raw["check"]) decide which careers a command re-validates."""
import hashlib
import json
import math
import random
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import fastjson as fj
from game import storage
from game.engine import new_state, GameError
from game.storage import Store, serialize, SEPARATORS

STD = dict(ensure_ascii=False, separators=SEPARATORS)


def std_bytes(obj) -> bytes:
    return json.dumps(obj, allow_nan=False, **STD).encode()


def digest(text: str) -> str:
    return hashlib.blake2b(text.encode(), digest_size=10).hexdigest()


def random_floats(r, n):
    for i in range(n):
        k = i % 3
        if k == 0:
            f = struct.unpack('d', struct.pack('Q', r.getrandbits(64)))[0]
        elif k == 1:
            f = r.uniform(-1, 1) * 10 ** r.randint(-12, 20)
        else:
            f = round(r.uniform(-1e6, 1e6), r.randint(0, 6))
        if math.isfinite(f):
            yield f


def random_text(r):
    ranges = [(0, 0x7f), (0x80, 0x7ff), (0x800, 0xd7ff), (0xe000, 0xffff), (0x10000, 0x10ffff)]
    return ''.join(chr(r.randint(*r.choice(ranges))) for _ in range(r.randint(0, 12)))


class DumpsTrustedTests(unittest.TestCase):
    def test_floats_are_written_as_json_writes_them(self):
        r = random.Random(7)
        floats = list(random_floats(r, 60000)) + [0.0, -0.0, 1e-5, 1.234e-5, 1e-6, 3.3e-8, 9.99e-10, 1e-10, 1e-4,
                                                  1e15, 1e16, 1.2345678901234567e16, 1e22, 5e-324, 1.7976931348623157e308]
        for f in floats:
            self.assertEqual(fj.dumps_trusted(f), std_bytes(f), repr(f))
        self.assertEqual(fj.dumps_trusted(floats), std_bytes(floats))
        self.assertEqual(fj.dumps_trusted({'a': floats[:500], 'b': {'c': -1.5e-7}}), std_bytes({'a': floats[:500], 'b': {'c': -1.5e-7}}))

    def test_text_ints_and_the_rest(self):
        r = random.Random(3)
        for _ in range(3000):
            s = random_text(r)
            obj = {s: [s, {'k': s}, r.randint(-2 ** 63, 2 ** 64 - 1), True, False, None]}
            self.assertEqual(fj.dumps_trusted(obj), std_bytes(obj))
        every = ''.join(chr(c) for c in range(0x10000) if not 0xd800 <= c < 0xe000)
        self.assertEqual(fj.dumps_trusted(every), std_bytes(every))
        # json decides what orjson refuses: huge ints, non-str keys, tuples of a subclass...
        for obj in ({'big': 2 ** 70, 'neg': -2 ** 64}, {1: 'a', 'b': {2: 3}}, (1, 2), {'t': (1, [2, (3,)])}, [],
                    {}, '', 'e-5 1e-6 0.00001 "0.0000"', {'text': 'lê-5 3e-7 x:0.00001'}):
            self.assertEqual(fj.dumps_trusted(obj), std_bytes(obj), obj)

    def test_float_format_detector(self):
        self.assertTrue(fj._float_format_differs(b'[1e-6]'))
        self.assertTrue(fj._float_format_differs(b'{"a":0.00001}'))
        self.assertTrue(fj._float_format_differs(b'[-0.000012]'))
        self.assertTrue(fj._float_format_differs(b'0.00005'))
        self.assertTrue(fj._float_format_differs(b'{"x":"one-e-way","y":2.5e-9}'))
        for same in (b'[1e-10]', b'[1e-05]', b'[0.0001]', b'{"a":"re-e-do"}', b'[1e+16]', b'"abc"', b''):
            self.assertFalse(fj._float_format_differs(same), same)


class LoadsTests(unittest.TestCase):
    def test_same_values_as_json(self):
        r = random.Random(5)
        values = [{'a': [1, 2.5, None, True, 'Phở'], 'b': {'c': -0.0}}, list(random_floats(r, 3000)),
                  [random_text(r) for _ in range(500)], [2 ** 63, 2 ** 64 - 1, -2 ** 63], 'x', 0, [], {}]
        for v in values:
            for text in (json.dumps(v, ensure_ascii=False), json.dumps(v), json.dumps(v, **STD)):
                self.assertEqual(fj.loads(text), json.loads(text))
                self.assertEqual(fj.loads(text.encode()), json.loads(text))

    def test_what_orjson_refuses_is_parsed_by_json(self):
        self.assertEqual(fj.loads('"\\ud800"'), '\ud800')        # a lone surrogate
        self.assertEqual(fj.loads('[1e400]'), [math.inf])
        self.assertTrue(math.isnan(fj.loads('NaN')))
        for depth in (1200, 3000):   # deeper than orjson's limit (1024)
            deep = '[' * depth + ']' * depth
            try:
                expected = json.loads(deep)
            except RecursionError:
                with self.assertRaises(RecursionError):
                    fj.loads(deep)
            else:
                actual = fj.loads(deep)
                # Check every level without unittest's recursive list comparison.
                for _ in range(depth - 1):
                    self.assertEqual(len(actual), 1)
                    self.assertEqual(len(expected), 1)
                    actual, expected = actual[0], expected[0]
                self.assertEqual(actual, expected)
        for bad in ('', '[1,', '{"a":1,}', '"\x00"', 'nul'):
            with self.assertRaises(ValueError):
                fj.loads(bad)
            with self.assertRaises(json.JSONDecodeError):
                fj.loads(bad)


    def test_ints_beyond_64_bits(self):
        """The one documented difference: orjson reads an int outside [-2**63, 2**64) as a float
        (the game's validated numbers stay far below; json still writes such ints exactly)."""
        text = fj.dumps([2 ** 80])
        self.assertEqual(text, '[1208925819614629174706176]')
        self.assertEqual(fj.loads(text), [2 ** 80] if not fj.FAST else [float(2 ** 80)])


class BodyAndReceiptTests(unittest.TestCase):
    def test_body_is_the_same_json(self):
        obj = dict(state={'a': [1, 2.5, 'Chào'], 'n': None}, result={1: 'int key', 'x': (1, 2)}, big=2 ** 70)
        body = fj.dumps_body(obj)
        self.assertIsInstance(body, bytes)
        self.assertEqual(json.loads(body), json.loads(json.dumps(obj, ensure_ascii=False)))
        self.assertIn('Chào'.encode(), body)   # UTF-8, not \\u escapes
        self.assertEqual(json.loads(fj.dumps_body({'x': math.nan, 'y': [math.inf], 'z': 1.5})), {'x': None, 'y': [None], 'z': 1.5})

    def test_receipts_parse_back_as_json_wrote_them(self):
        for obj in ({'message': 'Đã lưu', 'n': [1, 2.5, None]}, {'a': math.inf, 'b': [math.nan]}, {3: 'x'}, [2 ** 63, -2 ** 63]):
            text = fj.dumps(obj)
            self.assertIsInstance(text, str)
            back, want = fj.loads(text), json.loads(json.dumps(obj, ensure_ascii=False))
            self.assertEqual(json.dumps(back, sort_keys=True, default=str), json.dumps(want, sort_keys=True, default=str))


class StoredSaveTests(unittest.TestCase):
    """The stored text and its digests are exactly json's (with or without orjson)."""

    def assert_canonical(self, text: str):
        raw = json.loads(text)
        self.assertEqual(text, json.dumps(raw, **STD))
        check = raw.get('check')
        if check:
            for cid, c in raw['careers'].items():
                self.assertEqual(check['careers'][cid], digest(json.dumps(c, **STD)), cid)

    def test_serialize_full_and_known(self):
        raw = new_state()
        cid = next(iter(raw['careers']))
        raw['careers'][cid]['tiny'] = [1.5e-05, -3e-07, 2.5e-9, 1e-10, 0.1]   # floats orjson writes differently
        text = serialize(raw, None, True)
        self.assert_canonical(text)
        known = json.loads(text)['check']['careers']
        # nothing changed: every career keeps its digest and none is re-validated
        with mock.patch.object(storage, 'validate_career', side_effect=AssertionError('validated')):
            again = serialize(json.loads(text), known, False)
        self.assertEqual(again, text)
        # one career changed: only that one is validated, the text is still json's
        changed = json.loads(text)
        changed['careers'][cid]['tiny'].append(7e-06)
        with mock.patch.object(storage, 'validate_career') as v:
            out = serialize(changed, known, False)
        self.assertEqual([c.args[1] for c in v.call_args_list], [cid])
        self.assert_canonical(out)

    def test_non_finite_numbers_are_still_refused(self):
        raw = new_state()
        cid = next(iter(raw['careers']))
        known = json.loads(serialize(raw, None, True))['check']['careers']
        for bad in (math.nan, math.inf):
            broken = json.loads(serialize(raw, None, True))
            broken['careers'][cid]['money'] = bad
            with self.assertRaises(GameError):
                serialize(broken, known, False)
            broken = json.loads(serialize(raw, None, True))
            broken['careers'][cid]['money'] = bad
            with self.assertRaises((GameError, ValueError)):
                serialize(broken, None, False)
            broken = json.loads(serialize(raw, None, True))
            broken['settings']['x'] = bad
            with self.assertRaises(ValueError):
                serialize(broken, known, False)

    def test_commands_store_json_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'g.db')
            token, _, _ = store.session()
            rev = store.read(token)[1]
            career = next(iter(store.read(token)[0]['careers']))
            for i, (action, payload) in enumerate([('settings', {'sound': False}), ('start_day', {}), ('advance', {}), ('advance', {})]):
                try:
                    out = store.command(token, f'fastjson-{i:04d}', rev, career, action, payload)
                    rev = out['revision']
                except GameError:
                    rev = store.read(token)[1]
                with store.connect() as db:
                    row = db.execute('SELECT state FROM sessions WHERE sid=?', (store.key(token),)).fetchone()
                    self.assert_canonical(row['state'])
                    receipts = [r['result'] for r in db.execute('SELECT result FROM receipts WHERE sid=?', (store.key(token),))]
                for r in receipts:
                    self.assertEqual(fj.loads(r), json.loads(r))
            self.assertTrue(receipts)
            # a replayed command answers with the stored receipt
            again = store.command(token, 'fastjson-0000', None, career, 'settings', {'sound': False}, internal=True)
            self.assertTrue(again['replayed'])


if __name__ == '__main__':
    unittest.main()
