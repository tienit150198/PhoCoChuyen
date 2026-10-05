"""Large multilingual saves must not amplify JSON buffers excessively.

An emoji promotes a whole Python string to four-byte characters. The budget
allows the final string, UTF-8 fragments and decoding workspace, but excludes
repeated full-save Unicode copies. Timing is deliberately not asserted.
"""
import json
import tracemalloc
import unittest
from game import fastjson, storage
from game.engine import new_state


class SerializeMemoryTests(unittest.TestCase):
    @unittest.skipUnless(fastjson.FAST, 'production fast JSON dependency')
    def test_large_multilingual_save_has_bounded_temporary_buffers(self):
        raw=new_state()
        for career in raw['careers'].values():
            career['sample_text']='x'*100000+'🎉'
        storage.serialize(raw,full=True)
        known=raw['check']['careers'].copy()
        expected=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=storage.SEPARATORS)
        encoded_bytes=len(expected.encode())
        tracemalloc.start()
        try:
            actual=storage.serialize(raw,known)
            _,peak=tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(actual,expected)
        self.assertEqual(raw['check']['careers'],known)
        self.assertLess(peak,encoded_bytes*10)
