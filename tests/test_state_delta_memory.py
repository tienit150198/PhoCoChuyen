"""Delta encoding must release request-owned data without waiting for cyclic GC."""
import gc
import sys
import unittest
import weakref
from unittest.mock import patch

from game import fastjson as fj
from game import state_delta as sd


class KnownParts(frozenset):
    """A weak-referenceable client hash set, including stale hashes."""


BACKENDS = [('stdlib', None)]
if fj.orjson is not None:
    BACKENDS.append(('orjson', fj.orjson))


@unittest.skipUnless(sys.implementation.name == 'cpython', 'checks immediate reference-counted release')
class EncodingOwnership(unittest.TestCase):
    def setUp(self):
        self.gc_enabled = gc.isenabled()
        gc.collect()
        gc.disable()
        self.addCleanup(self.restore_gc)

    def restore_gc(self):
        gc.collect()
        if self.gc_enabled:
            gc.enable()

    def test_completed_encoding_releases_known_without_cyclic_gc(self):
        state = {'held': 'a' * 300, 'split': [{'text': str(i) * 300} for i in range(20)]}
        for name, backend in BACKENDS:
            with self.subTest(backend=name), patch.object(fj, 'orjson', backend):
                held = sd.digest(fj.dumps_body(state['held']))
                known = KnownParts([held, *(f'{i:08x}' for i in range(sd.MAX_KNOWN - 1))])
                reference = weakref.ref(known)
                body, delta = sd.encode(state, known)
                self.assertEqual(delta['refs'], [[['held'], held]])
                self.assertTrue(delta['keys'])
                del known, body, delta
                self.assertTrue(reference() is None, 'completed encoding retains the client hash set')

    def test_unsplit_root_releases_known_without_cyclic_gc(self):
        for name, backend in BACKENDS:
            for state in ({}, [], {1: 'text'}, None):
                with self.subTest(backend=name, state=state), patch.object(fj, 'orjson', backend):
                    known = KnownParts(['stale000'])
                    reference = weakref.ref(known)
                    body, delta = sd.encode(state, known)
                    self.assertEqual(body, fj.dumps_body(state))
                    self.assertEqual(delta, {'refs': [], 'keys': []})
                    del known, body, delta
                    self.assertTrue(reference() is None, 'unsplit encoding retains the client hash set')

    def test_failed_encoding_releases_known_without_cyclic_gc(self):
        for name, backend in BACKENDS:
            with self.subTest(backend=name), patch.object(fj, 'orjson', backend):
                known = KnownParts(['stale000'])
                reference = weakref.ref(known)
                with self.assertRaises(TypeError):
                    sd.encode({'valid': 'a' * 300, 'invalid': object()}, known)
                del known
                self.assertTrue(reference() is None, 'failed encoding retains the client hash set')


if __name__ == '__main__':
    unittest.main()
