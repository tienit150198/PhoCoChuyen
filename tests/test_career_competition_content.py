"""Content contract and localized NPC leadership cases for every career."""
import importlib
import importlib.util
import json
from pathlib import Path
import unittest

from game.content import CAREERS

ROOT = Path(__file__).resolve().parents[1]


class CompetitionContentTests(unittest.TestCase):
    def profiles(self):
        self.assertIsNotNone(importlib.util.find_spec('game.career_competition_content'),
                             'NPC career competition content is not implemented')
        return importlib.import_module('game.career_competition_content').PROFILES

    def test_every_career_has_three_named_peers_and_three_complete_cases(self):
        profiles = self.profiles()
        self.assertEqual(59, len(CAREERS))   # 🔑 reception the 58th, 🧰 restore the 59th (other branches add theirs: add each one here)
        self.assertEqual(set(CAREERS), set(profiles))
        ids, narratives = set(), set()
        for career, profile in profiles.items():
            with self.subTest(career=career):
                self.assertTrue(profile['recognizer'])
                self.assertTrue(profile['focus'])
                self.assertEqual(3, len(profile['rivals']))
                self.assertEqual(3, len({r['name'] for r in profile['rivals']}))
                for rival in profile['rivals']:
                    self.assertNotIn(rival['id'], ids)
                    ids.add(rival['id'])
                    self.assertGreater(len(rival['strength']), 10)
                self.assertEqual(3, len(profile['scenarios']))
                self.assertEqual({f'{career}_{kind}' for kind in ('assignment', 'inspection', 'commendation')},
                                 {s['id'] for s in profile['scenarios']})
                for case in profile['scenarios']:
                    self.assertNotIn(case['id'], ids)
                    ids.add(case['id'])
                    self.assertNotIn(case['text'], narratives)
                    narratives.add(case['text'])
                    self.assertGreater(len(case['text']), 70)
                    self.assertEqual(3, len(case['options']))
                    self.assertEqual({'a', 'b', 'c'}, {o['id'] for o in case['options']})
                    self.assertEqual({0, 50, 100}, {o['score'] for o in case['options']})
                    self.assertEqual(3, len({o['label'] for o in case['options']}))
                    for option in case['options']:
                        self.assertIs(type(option['score']), int)
                        self.assertGreater(len(option['label']), 15)
                        self.assertGreater(len(option['feedback']), 25)

    def test_all_display_strings_have_english_translations(self):
        profiles = self.profiles()
        source = json.loads((ROOT / 'output/career-competition/content-en.json').read_text(encoding='utf-8'))
        self.assertEqual({'strings', 'patterns'}, set(source))
        strings = source['strings']
        for profile in profiles.values():
            lines = [profile['recognizer'], profile['focus']]
            lines += [r[key] for r in profile['rivals'] for key in ('name', 'strength')]
            lines += [s[key] for s in profile['scenarios'] for key in ('title', 'text')]
            lines += [o[key] for s in profile['scenarios'] for o in s['options'] for key in ('label', 'feedback')]
            for line in lines:
                self.assertIn(line, strings, line)
                self.assertTrue(strings[line].strip())

    def test_authority_and_pagoda_boundaries(self):
        profiles = self.profiles()
        self.assertIn('Hạnh', profiles['garbage']['recognizer'])
        for career, profile in profiles.items():
            if career != 'police':
                text = json.dumps(profile, ensure_ascii=False).lower()
                for term in ('bắt giữ', 'khám xét', 'quyền xử phạt', 'truy nã'):
                    self.assertNotIn(term, text)
        pagoda = json.dumps(profiles['pagoda'], ensure_ascii=False).lower()
        self.assertIn('công quả', pagoda)
        self.assertNotIn('cúng nhiều', pagoda)

    def test_module_has_no_engine_or_content_dependency(self):
        self.profiles()
        source = (ROOT / 'game/career_competition_content.py').read_text(encoding='utf-8')
        self.assertNotIn('from .content', source)
        self.assertNotIn('import engine', source)
        self.assertNotIn('from .engine', source)
