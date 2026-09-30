"""The pre-deploy task compatibility gate (scripts/check_task_compat.py).

The diff rules are tested directly. The gate itself runs against the live release (LIVE_REF) when
this is a git checkout that has that commit: tasks the live server generated must still validate here.
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The release players are on: bump it to the new live commit after each release (0.9.12 = main bded2ef).
LIVE_REF = 'bded2efc852158ccc86a13dbc74f1c7f60f7686a'

spec = importlib.util.spec_from_file_location('check_task_compat', ROOT / 'scripts' / 'check_task_compat.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
LATE = frozenset({'ask', 'told'})


def rows(needs, **top):
    return {'1/0/desk': dict(id='x', needs=needs, **top)}


class DiffRules(unittest.TestCase):
    def test_same_output_passes(self):
        a = rows({'lines': [{'item': 'tee', 'size': 'M'}]})
        self.assertEqual(gate.compare_career('clothing', a, a, LATE, ['needs']), [])

    def test_late_key_missing_in_old_is_allowed_inside_a_tolerant_field(self):
        old = rows({'lines': [{'item': 'tee'}]})
        new = rows({'lines': [{'item': 'tee', 'ask': 'mặc size M', 'told': 'M'}]})
        self.assertEqual(gate.compare_career('clothing', old, new, LATE, ['needs']), [])

    def test_late_key_outside_a_tolerant_field_fails(self):
        old = {'1/0/desk': dict(id='x', proc=[{'step': 1}])}
        new = {'1/0/desk': dict(id='x', proc=[{'step': 1, 'ask': 'hỏi'}])}
        self.assertTrue(gate.compare_career('pharmacy', old, new, LATE, []))

    def test_changed_value_of_a_late_key_fails(self):
        old = rows({'lines': [{'item': 'tee', 'told': 'M'}]})
        new = rows({'lines': [{'item': 'tee', 'told': 'L'}]})
        self.assertTrue(gate.compare_career('clothing', old, new, LATE, ['needs']))

    def test_new_key_that_is_not_late_fails(self):
        old = rows({'item': 'tee'})
        new = rows({'item': 'tee', 'hint': 'x'})
        self.assertTrue(gate.compare_career('clothing', old, new, LATE, ['needs']))

    def test_new_top_level_key_fails_even_if_late(self):
        # engine.validate_career needs set(original) <= set(stored task)
        self.assertTrue(gate.compare_career('clothing', rows({}), rows({}, ask='x'), LATE, ['needs']))

    def test_text_list_and_type_changes_fail(self):
        for old, new in (({'say': 'size F'}, {'say': 'Free size'}), ({'q': [1, 2]}, {'q': [1, 2, 3]}),
                         ({'q': [1]}, {'q': {'__tuple__': [1]}}), ({'ok': 1}, {'ok': True})):
            with self.subTest(old=old, new=new):
                self.assertTrue(gate.compare_career('clothing', rows(old), rows(new), LATE, ['needs']))

    def test_a_row_the_new_tree_no_longer_generates_fails(self):
        self.assertTrue(gate.compare_career('clothing', rows({}), {}, LATE, ['needs']))


@unittest.skipUnless(shutil.which('git') and (ROOT / '.git').exists(), 'needs a git checkout')
class AgainstLiveRelease(unittest.TestCase):
    def test_tasks_from_the_live_release_still_match(self):
        have = subprocess.run(['git', 'cat-file', '-e', LIVE_REF + '^{commit}'], cwd=ROOT, capture_output=True)
        if have.returncode != 0:
            self.skipTest(f'{LIVE_REF[:7]} is not in this clone')
        with tempfile.TemporaryDirectory(prefix='live-') as d:
            archive = subprocess.run(['git', 'archive', LIVE_REF], cwd=ROOT, capture_output=True, check=True).stdout
            subprocess.run(['tar', '-x', '-C', d], input=archive, check=True)
            p = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_task_compat.py'), d, str(ROOT), '--show', '5'],
                               cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout[-4000:] + p.stderr[-2000:])
        self.assertIn('OK:', p.stdout)


if __name__ == '__main__':
    unittest.main()
