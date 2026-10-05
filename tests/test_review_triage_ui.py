"""Review list tells first replies apart from open follow-ups and pending/closed threads."""
import json
import subprocess
import unittest
from pathlib import Path

from game.content import public_content
from game.engine import public_state
from tests import test_feedback_police as review_fixture


class ReviewTriage(unittest.TestCase):
    def test_review_status_labels_and_reply_forms(self):
        f = review_fixture.PoliceReportTests()
        f.setUp()
        post = f.post('plain')
        initial = public_state(f.j.state)
        f.j.act('fb_reply', post=post['id'], text='Cảm ơn, tiệm sẽ kiểm lại quy trình.', offer='none')
        pending = public_state(f.j.state)
        for _ in range(2):
            f.j.act('advance')
        after = public_state(f.j.state)
        payload = dict(content=public_content(), initial=initial, pending=pending, after=after, post=post['id'])
        run = subprocess.run(['node', str(Path(__file__).with_suffix('.mjs'))], input=json.dumps(payload),
                             capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
