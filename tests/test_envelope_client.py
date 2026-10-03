"""🧧 The wedding envelope's client side (public/js/v4/walk.js sendEnvelope, public/js/v4/envelope-send.js):
the request id across a lost answer (tests/envelope_send.mjs, run with node), and the wiring a later edit must keep:
- the send is re-sent with the same rid when no answer came (the server pays one rid once: tests/test_wedding_live.py);
- the send button keeps its own busy state and is out of app.js's tap guard, which held a re-enabled button "pending"
  while any other request was out and swallowed its next tap without a word (the browser smoke's lost envelope)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EnvelopeClient(unittest.TestCase):
    def test_request_id_rules(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'envelope_send.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_wired_in(self):
        walk = (ROOT / 'public/js/v4/walk.js').read_text(encoding='utf-8')
        send = walk.split('async function sendEnvelope(){')[1].split('\n}\n')[0]
        self.assertIn("from './envelope-send.js'", walk)
        self.assertIn('envRid(S.envk,envKey(w.id,v.n,e.wish))', send)          # the kept rid, outliving the panel
        self.assertIn("retry:true", send)                                       # no answer: the same rid again
        self.assertIn('envSettle(S.envk,error)', send)
        self.assertIn('api.refresh()', send)                                    # "already sent" / unknown: the real wallet
        self.assertNotIn('e.rid=null', send)                                    # an unanswered rid is never dropped
        self.assertIn('data-wk="envSend" data-own-busy', walk)
        self.assertIn("'🧧 Đang gửi…'", walk)                                    # its own pending state
        app = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
        self.assertIn("tap.el=el&&!el.disabled&&!el.hasAttribute('data-own-busy')?el:null", app)


if __name__ == '__main__':
    unittest.main()
