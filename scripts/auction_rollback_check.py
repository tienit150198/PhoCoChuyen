#!/usr/bin/env python3
"""🔨 Rollback proof for the auction house (game/auction.py): saves written by this build open, validate, play a life
day and save again on an older build (an archive of the release it would roll back to), and come back intact.

  python scripts/auction_rollback_check.py OLD_TREE     # e.g. a `git archive rel-1.9.11` extracted somewhere

Step 1 (this tree): saves with `journey.uniq` (escrow held on two lots, a plate, a phone number, a title worn from
Phong cách, a painting in the bag, a landmark), written to a temporary file.
Step 2 (OLD_TREE, a separate `python -I`): migrate_state + validate_state, a few commands (a new life day included),
public_state and the player card, the save written back.
Step 3 (this tree): the saves the old tree wrote validate here, `journey.uniq` and the money are unchanged.
Exit 0 = OK.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build() -> dict:
    sys.path.insert(0, HERE)
    from game import auction as au
    from game.engine import apply_action, new_state, validate_state
    from game import journey as jr

    def story(wallet):
        s = new_state()
        jr.enable_story(s, 4242)
        s['journey']['gender'] = 'female'
        s['journey']['wallet'] = wallet
        validate_state(s)
        return s

    def act(s, name, **p):
        return apply_action(s, None, name, p)[0]

    saves = {}
    s = story(2_000_000)
    s = act(s, 'jr_auc_bid', lot='20261007-1', amount=5_000, label='Mây-0001')
    saves['holding'] = s
    s = story(3_000_000)
    s = act(s, 'jr_bk_open')
    s = act(s, 'jr_bk_deposit', amount=1_000_000)
    for lot, item, kind, text, price in (('20261007-1', 'pl_may0001', 'plate', 'Mây-0001', 5_000),
                                         ('20261007-2', 'ph_0909090909', 'phone', '0909.090.909', 60_000),
                                         ('20261007-3', 'dh_mat_trang', 'title', 'Người đầu tiên lên Mặt Trăng Phố Mây', 700_000),
                                         ('20261008-1', 'tr_sen_ho', 'art', 'Sen hồ Mây', 9_000),
                                         ('20261008-2', 'dt_ho', 'land', 'Hồ Lan Mây', 520_000)):
        s = act(s, 'jr_auc_bid', lot=lot, amount=price)
        au.apply_fx(s, dict(data=dict(lot=lot, what='win', item=item, kind=kind, text=text)), price)
    s = act(s, 'jr_auc_bid', lot='20261009-1', amount=8_000)          # still held
    s = act(s, 'jr_auc_bid', lot='20261009-2', amount=70_000)
    s = act(s, 'jr_spend_wear', kind='title', id='dh_mat_trang')                 # the one-of-a-kind title worn
    validate_state(s)
    saves['winner'] = s
    return saves


OLD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from game.engine import apply_action, migrate_state, public_state, validate_state
from game.social import snapshot
saves = json.load(open(sys.argv[2]))
out = {}
for k, s in saves.items():
    s = migrate_state(s)
    validate_state(s)
    s, _ = apply_action(s, None, 'jr_seen', {'ids': ['x']})
    s['journey']['life_day'] += 1
    s, _ = apply_action(s, None, 'jr_seen', {'ids': ['y']})            # the morning's catch-up of every block
    validate_state(s)
    public_state(s)                                                   # the page's view and the player card
    snapshot(s)
    out[k] = s
    print(f'old build: {k} ok, uniq kept: {s["journey"].get("uniq") is not None}')
json.dump(out, open(sys.argv[2], 'w'))
'''


def money(s) -> int:
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def main() -> int:
    if len(sys.argv) != 2 or not os.path.isdir(os.path.join(sys.argv[1], 'game')):
        print(__doc__)
        return 2
    old = os.path.abspath(sys.argv[1])
    saves = build()
    from game.engine import migrate_state, validate_state
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'saves.json')
        json.dump(saves, open(path, 'w'))
        r = subprocess.run([sys.executable, '-I', '-c', OLD, old, path], cwd=old, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print(r.stderr[-3000:])
            return 1
        back = json.load(open(path))
    bad = 0
    for k, s in saves.items():
        t = migrate_state(back[k])
        validate_state(t)
        same = t['journey'].get('uniq') == s['journey'].get('uniq') and money(t) == money(s)
        if k == 'winner':
            same = same and any(x['k'] == 'uq_tr_sen_ho' for x in t['journey']['reno']['items']) \
                and t['journey']['spend']['own'].get('dh_mat_trang') == s['journey']['spend']['own']['dh_mat_trang']
        print(f'new build: {k} {"ok" if same else "CHANGED"} (held {sum(h["a"] for h in t["journey"]["uniq"]["hold"].values())} xu, '
              f'{len(t["journey"]["uniq"]["own"])} items, money {money(t)})')
        bad += not same
    print('OK' if not bad else 'FAILED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
