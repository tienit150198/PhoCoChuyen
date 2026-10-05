import pathlib
import shutil
import subprocess
import unittest


class FeedbackHelp(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'node is required for module navigation checks')
    def test_salary_and_trust_help_open_their_real_destinations(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        result = subprocess.run([shutil.which('node'), 'tests/feedback_help.mjs'], cwd=root,
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
