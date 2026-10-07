"""fb_reply 409s (06/10): the reviews' AI writes (/api/ai/feedback, /api/ai/review) wait their turn in the command
queue, the taps after them wait AI_WAIT at most (tests/fb_queue.mjs)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FeedbackAiQueueClient(unittest.TestCase):
    def test_ai_writes_are_queued(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'fb_queue.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_double_tap_behind_an_ai_write(self):
        """07/10: a tap waiting behind an AI write is busy at once, an identical second tap is the same command, and
        the review reply form is off while its reply is on its way (tests/fb_double_tap.mjs)."""
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'fb_double_tap.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
