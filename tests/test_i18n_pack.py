"""Checks on the English language pack (public/i18n/en.json).

The browser compiles every pattern with `new RegExp('^'+source+'$','u')` and
silently drops the ones that fail, so a bad escape here means untranslated text
in the game rather than an error.
"""
import json
import re
import unittest
from pathlib import Path

from game.social import BANNED

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'public' / 'i18n' / 'en.json'
# Escapes a unicode-mode RegExp accepts as identity escapes.
SYNTAX = set('^$\\.*+?()[]{}|/')


@unittest.skipUnless(PACK.exists(), 'run scripts/i18n_extract.py build first')
class EnglishPackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding='utf-8'))

    def test_shape(self):
        self.assertIsInstance(self.pack['strings'], dict)
        self.assertIsInstance(self.pack['patterns'], list)
        self.assertGreater(len(self.pack['strings']), 10000)
        for key, value in self.pack['strings'].items():
            self.assertIsInstance(value, str, key)
            self.assertTrue(value.strip(), key)

    def test_patterns_are_valid_unicode_regexps(self):
        for source, out in self.pack['patterns']:
            escapes = set(re.findall(r'\\(.)', source))
            self.assertLessEqual(escapes, SYNTAX, source)
            groups = source.count('(.+?)')
            self.assertGreater(groups, 0, source)
            re.compile('^' + source + '$')
            used = {int(n) for n in re.findall(r'\$(\d)', out)}
            self.assertTrue(used <= set(range(1, groups + 1)), (source, out))

    def test_specific_patterns_come_first(self):
        literal = [len(re.sub(r'\(\.\+\?\)|\\', '', s)) for s, _ in self.pack['patterns']]
        self.assertEqual(literal, sorted(literal, reverse=True))

    def test_moderation_words_are_not_shipped(self):
        for word in BANNED:
            self.assertNotIn(word, self.pack['strings'])

    def test_ui_basics(self):
        s = self.pack['strings']
        self.assertEqual(s.get('Cài đặt'), 'Settings')
        self.assertEqual(s.get('Phố nghề'), 'Job Street')
        self.assertEqual(s.get('lượt'), 'turn')


if __name__ == '__main__':
    unittest.main()
