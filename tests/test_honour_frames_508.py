"""🖼️ Player feedback #508 (lii, 23/10): "khung đấu giá vật phẩm đèn lồng mà không thấy trong danh sách khung để đổi",
"vật phẩm đấu giá có ghi khung độc bản thì sẽ là 1 khung không ai có được".

* A title won at the auction house (journey.uniq.own, kind 'title') reaches the client's state as it always did, the
  frame chooser (public/js/v4/honour-frames.js choices) lists it and jr_frame keeps the pick: no save is rewritten.
* Every auction title has its own drawn frame in honour-frames.js (UQ): one row per catalogue title, its emoji, colours
  that no other title shares. The frame follows the title's id, and the database sells each item once
  (auction_lots_item), so it has one holder ever."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import auction as au
from game import auction_content as C
from game.engine import apply_action, public_state, validate_state
from tests.test_bank import act, story

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'public/js/v4/honour-frames.js'
ROW = re.compile(r"^\s*(dh_[a-z0-9_]+):\['([^']+)','(#[0-9a-f]{6})','(#[0-9a-f]{6})','(#[0-9a-f]{6})','([a-z]+)',(\d+)\],$", re.M)


def uq_rows() -> dict:
    src = JS.read_text(encoding='utf-8')
    block = src[src.index('const UQ={'):src.index('};', src.index('const UQ={'))]
    return {m[1]: m.groups()[1:] for m in ROW.finditer(block)}


def won_lantern():
    s = story(60_000)
    s, _ = act(s, 'jr_auc_bid', lot='20261023-1', amount=6_000)
    au.apply_fx(s, dict(data=dict(lot='20261023-1', what='win', item='dh_den_long', kind='title',
                                  text='Chủ Nhân Đèn Lồng Vàng')), 6_000)
    validate_state(s)
    return s


class UniqueFrames(unittest.TestCase):
    def test_every_auction_title_has_its_own_frame(self):
        rows, titles = uq_rows(), {it['id']: it for it in C.ITEMS if it['kind'] == 'title'}
        self.assertTrue(titles)
        self.assertEqual(set(rows), set(titles), 'a row per catalogue title, nothing else')
        for iid, (emoji, *_rest) in rows.items():
            self.assertEqual(emoji, titles[iid]['emoji'], iid)
        palettes = [r[1:4] for r in rows.values()]
        self.assertEqual(len(set(palettes)), len(palettes), 'no two titles share colours')
        self.assertEqual(len({r[2] for r in rows.values()}), len(rows), 'nor their main colour')
        self.assertEqual(len({r[1:] for r in rows.values()}), len(rows))

    def test_an_item_is_sold_once(self):
        schema = (ROOT / 'game/pg_schema.py').read_text(encoding='utf-8')
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS auction_lots_item ON auction_lots(item) WHERE status IN ('open', 'sold')", schema)

    def test_never_a_top_boards_art(self):
        src = JS.read_text(encoding='utf-8')
        self.assertNotIn("return {n:'60',tier:4}", src, "every auction title used to wear the 🏺 collection top 1's art")


class WonTitleInChooser(unittest.TestCase):
    def test_state_and_pick(self):
        s = won_lantern()
        own = public_state(s)['journey']['uniq']['own']
        self.assertEqual(own['dh_den_long'], dict(k='title', t='Chủ Nhân Đèn Lồng Vàng', p=6_000))
        s2, r = apply_action(s, None, 'jr_frame', dict(id='dh_den_long'))
        self.assertEqual(s2['journey']['hf_pick'], 'dh_den_long')
        validate_state(s2)
        s3, _ = apply_action(s2, None, 'jr_frame', dict(id='auto'))   # and back: unequipped
        self.assertNotIn('hf_pick', s3['journey'])

    @unittest.skipUnless(shutil.which('node'), 'node')
    def test_the_client_lists_it(self):
        s, _ = apply_action(won_lantern(), None, 'jr_frame', dict(id='dh_den_long'))
        journey = public_state(s)['journey']
        script = ("const m=await import(process.argv[1]);const J=JSON.parse(process.argv[2]);"
                  "const api={state:{journey:J},content:{journey:{auction:{items:[{id:'dh_den_long',kind:'title',emoji:'🏮'}]}}},lbTitles:[]};"
                  "console.log(JSON.stringify({ids:m.choices(api).map(x=>x.id),html:m.chooser(api)}));")
        out = subprocess.run(['node', '--input-type=module', '-e', script, JS.as_uri(), json.dumps(journey)],
                             capture_output=True, text=True, encoding='utf-8', timeout=60, check=True)
        got = json.loads(out.stdout)
        self.assertEqual(got['ids'], ['dh_den_long'])
        self.assertRegex(got['html'], r'class="hf-opt on" data-action="jrFrame" data-id="dh_den_long" aria-pressed="true"')
        self.assertIn('Chủ Nhân Đèn Lồng Vàng', got['html'])
        self.assertIn('hf-uq', got['html'])


if __name__ == '__main__':
    unittest.main()
