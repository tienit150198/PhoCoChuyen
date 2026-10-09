#!/usr/bin/env python3
"""🐕 Rollback proof for Kéo co chó sủa (game/dog_bark.py): saves and a database written by this build work on an
older build (an archive of the release it would roll back to), and come back intact.

  TEST_DATABASE_URL=postgresql://… python scripts/dog_bark_rollback_check.py OLD_TREE   # e.g. `git archive rel-1.9.40`

Step 1 (this tree): saves that put a stake in escrow (jr_bark_join: the wallet and a Sổ ví row, no save key), then got
a pot and a stake back (live_effects 'bark' paid: journey.live_fx hashes); and, in a fresh PostgreSQL namespace at
SCHEMA_VERSION 34, a player with a waiting ticket and a pending 'bark' payout row.
Step 2 (OLD_TREE, a separate `python -I`): migrate_state + validate_state, a few commands (a new life day included),
public_state and the player card, the saves written back; on the database: the old build starts on schema 34 without
DDL, loads the player, leaves the 'bark' row pending (a kind it does not know) and plays a command.
Step 3 (this tree): the saves the old tree wrote validate here with the same money; the pending row is paid once.
Exit 0 = OK.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build() -> dict:
    sys.path.insert(0, HERE)
    os.environ['LIVE_DOG_BARK'] = '1'   # the switch on, as on a server running it
    from game import dog_bark as G
    from game.engine import apply_action, new_state, validate_state
    from game import journey as jr

    def story(wallet):
        s = new_state()
        jr.enable_story(s, 4242)
        s['journey']['gender'] = 'female'
        s['journey']['wallet'] = wallet
        validate_state(s)
        return s

    saves = {}
    s, r = apply_action(story(5_000), None, 'jr_bark_join', dict(stake=1_000))
    saves['escrow'] = s
    s, r = apply_action(story(5_000), None, 'jr_bark_join', dict(stake=700))
    t1 = r['bark']['ticket']
    s, _ = apply_action(s, None, 'live_fx', dict(id=f'bark:{t1}', kind='bark', amount=1_400, data=dict(ticket=t1, what='win')), internal=True)
    s, r = apply_action(s, None, 'jr_bark_join', dict(stake=300))
    t2 = r['bark']['ticket']
    s, _ = apply_action(s, None, 'live_fx', dict(id=f'bark:{t2}', kind='bark', amount=300, data=dict(ticket=t2, what='back')), internal=True)
    validate_state(s)
    assert s['journey']['wallet'] == 5_700, s['journey']['wallet']
    saves['paid'] = s
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
    s, _ = apply_action(s, None, 'jr_seen', {'ids': ['y']})
    validate_state(s)
    public_state(s)
    snapshot(s)
    try:
        apply_action(s, None, 'jr_bark_join', {'stake': 100})
        print('old build: jr_bark_join ACCEPTED (unexpected)'); sys.exit(1)
    except Exception as e:
        print(f'old build: jr_bark_join refused ({type(e).__name__})')
    out[k] = s
    print(f'old build: {k} ok, wallet {s["journey"]["wallet"]}')
json.dump(out, open(sys.argv[2], 'w'))
'''

OLD_DB = r'''
import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from game.storage import Store
from game import live_effects, pg_schema
store = Store(Path(sys.argv[2]), story=True)
with store.connect() as db:
    v = int(db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0])
print(f'old build: schema {v} installed, its own {pg_schema.SCHEMA_VERSION}: no DDL')
token = sys.argv[3]
state, rev, _ = store.read(token)
paid = live_effects.on_load(store, token, state)
with store.connect() as db:
    st = db.execute("SELECT status FROM live_effects WHERE kind='bark'").fetchone()[0]
print(f'old build: on_load paid={paid}, bark row {st}')
assert not paid and st == 'pending'
store.command(token, 'old-0001', rev, None, 'jr_seen', {'ids': ['z']})
print(f'old build: a command on the save ok, wallet {store.read(token)[0]["journey"]["wallet"]}')
store.close_pool()
'''


def money(s) -> int:
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def db_check(old: str, tmp: str) -> bool:
    if not (os.environ.get('TEST_DATABASE_URL') or '').strip():
        print('database step skipped: no TEST_DATABASE_URL')
        return True
    import json as _j
    import time
    from game.storage import Store
    from game import marriage as mr, live_effects
    path = Path(tmp) / 'rb.db'
    store = Store(path, story=True)
    token, _, _ = store.session()
    store.read(token)
    sid = store.key(token)

    def fn(s):
        s['name'] = 'Lan'
        s['journey']['wallet'] = 4_000
    mr._mutate(store, {sid: fn})
    with store.connect() as db:
        db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created) VALUES('k00000000000000000001', ?, 500, 'wait', ?)", (sid, time.time()))
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES('bark:k00000000000000000002', ?, 'bark', 800, ?, 'pending', ?)",
                   (sid, _j.dumps(dict(ticket='k00000000000000000002', what='win', src='bark')), time.time()))
    store.close_pool()
    r = subprocess.run([sys.executable, '-I', '-c', OLD_DB, old, str(path), token], cwd=old, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=''))
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr[-3000:])
        return False
    store = Store(path, story=True)
    state = store.read(token)[0]
    ok = live_effects.on_load(store, token, state) and store.read(token)[0]['journey']['wallet'] == 4_800
    ok = ok and not live_effects.on_load(store, token, store.read(token)[0])
    print(f'new build: the pending pot paid once after the roll forward: {"ok" if ok else "FAILED"}')
    with store.connect() as db:
        db.execute('DROP SCHEMA IF EXISTS ' + store.pg.schema + ' CASCADE')
    store.close_pool()
    return bool(ok)


def main() -> int:
    if len(sys.argv) != 2 or not os.path.isdir(os.path.join(sys.argv[1], 'game')):
        print(__doc__)
        return 2
    old = os.path.abspath(sys.argv[1])
    saves = build()
    from game.engine import migrate_state, validate_state
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'saves.json')
        json.dump(saves, open(path, 'w'))
        r = subprocess.run([sys.executable, '-I', '-c', OLD, old, path], cwd=old, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print(r.stderr[-3000:])
            return 1
        back = json.load(open(path))
        for k, s in saves.items():
            t = migrate_state(back[k])
            validate_state(t)
            same = money(t) == money(s) and t['journey'].get('live_fx') == s['journey'].get('live_fx') and 'bark' not in t['journey']
            print(f'new build: {k} {"ok" if same else "CHANGED"} (money {money(t)})')
            bad += not same
        bad += not db_check(old, tmp)
    print('OK' if not bad else 'FAILED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
