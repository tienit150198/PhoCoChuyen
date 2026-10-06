"""Per-phase micro-benchmark of one command on large synthetic saves (POST /api/command's Store path).

    TEST_DATABASE_URL=postgresql://user@127.0.0.1:PORT/db python scripts/bench_command.py [options]

Builds synthetic saves of about 225 KB, 1.4 MB and 3 MB from the real save structure (the game's own
actions: careers played for several days, staff hired and paid by the server clock, journals, reviews
with comments, chats, memories, cash books and a few album photos). No real save is read. Each save is
stored in a throw-away schema (test mode of game/db.py, dropped at exit), then a mix of commands runs
through Store.command with a fake clock that advances between commands (so staff orders fall due and
business settlement touches many careers, as on the live server). Every phase is timed by wrapping the
functions that do it, so the same script measures any tree:

    python scripts/bench_command.py --tree /path/to/other/checkout      # "before" numbers

Phases (ms, median over the runs, per save size). CPU time of the command's thread for the Python
phases (a loaded machine inflates wall time), wall time for the database ones:
  fetch      wall: SELECT of the save + receipt (the command's snapshot query)
  parse      cpu: Store.parse_state (fastjson.loads)
  apply      cpu: engine.apply_action (settle, reducer, reconcile, scoped validate_state)
  ser+val    cpu: storage.serialize / serialize_bytes (orjson, digests) incl. validate_career of moved careers
  validate   cpu: validate_career / validate_state wherever they run (part of apply and ser+val)
  places     cpu: work_visits.places, computed before the row lock (trees that have it)
  hooks      cpu: rentals / work_visits / home_guests commit hooks, inside the row lock
  lock       wall: the row lock held in Store._store (SELECT .. FOR UPDATE until COMMIT)
  update     wall: the UPDATE sessions statement
  view       cpu: engine.public_state
  delta      cpu: state_delta.encode of the view (server.py answers with it)
  total      wall time of Store.command;  cpu: thread CPU time of all of it

Options: --sizes 225,1400,3000 (KB) --runs 12 --mix settings,ask,advance --cache DIR --json FILE.
The run's revisions that land on a periodic full validation (FULL_EVERY) are left out of the medians.

Each size also prints a run fingerprint: the hash of every stored save (without the build stamp,
which names the tree), result and public view of the run. The same saves (--cache) and the same
fake clock give the same fingerprint on two trees that behave the same: a differential check.
--cache keeps the built saves as JSON (delete the folder afterwards).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import secrets
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _args():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--tree', default=str(ROOT), help='checkout whose game/ is measured (default: this one)')
    p.add_argument('--sizes', default='225,1400,3000', help='target save sizes in KB')
    p.add_argument('--runs', type=int, default=12, help='commands per action and size')
    p.add_argument('--mix', default='settings,ask,advance', help='actions to time')
    p.add_argument('--cache', default='', help='directory to keep the built saves between runs (deleted by --clean)')
    p.add_argument('--json', default='', help='also write the medians to this JSON file')
    return p.parse_args()


A = _args() if __name__ == '__main__' else None
if A is not None:
    sys.path.insert(0, os.path.abspath(A.tree))

from unittest.mock import patch  # noqa: E402

# ---------------------------------------------------------------- a fake, advancing clock
CLOCK = [1_900_000_000.0]


def fake_time():
    return CLOCK[0]


# ---------------------------------------------------------------- building a synthetic save
VI = ('Chị Hoa ghé quầy hỏi lại món hôm qua, dặn ít đá nhiều trân châu, nói chuyện vui vẻ cả buổi 🙂. ',
      'Anh shipper đến trễ mười phút, khách hơi cáu nhưng em xin lỗi khéo nên ổn rồi nha. ',
      'Bác bảo vệ khen quán sạch sẽ, hẹn tuần sau dẫn cả nhà tới ăn thử món mới 🍜. ',
      'Khách nhỏ tuổi đòi đổi món ba lần, cuối cùng chọn lại đúng món ban đầu luôn vl 😅. ')


def _text(rng, n):
    out = ''
    while len(out) < n:
        out += rng.choice(VI)
    return out[:n]


def _photo(rng, size):
    raw = bytes(rng.getrandbits(8) for _ in range(size * 3 // 4))
    return 'data:image/webp;base64,' + base64.b64encode(raw).decode()[:size]


def build_save(target_kb: int, seed: int = 7) -> dict:
    """A valid save of about target_kb KB, built with the game's own actions (deterministic)."""
    from game import engine, employment as emp, operations as ops, workplace_business as wb
    from game.engine import apply_action, GameError, new_state, NPC_INDEX
    rng = random.Random(seed)
    # Share of the size: played careers (tasks, journals, business), reviews, chats, album photos.
    played = max(3, min(41, target_kb // 70))
    days = 2 if target_kb < 500 else 3
    s = new_state()
    careers = list(s['careers'])
    rng.shuffle(careers)
    chosen = careers[:played]
    CLOCK[0] = 1_900_000_000.0
    with patch('time.time', fake_time):
        for cid in chosen:
            c = s['careers'][cid]
            if emp.required(cid):
                c['job'] = emp.hired_record(cid, None, 1)
            def act(a, p=None):
                nonlocal s
                try:
                    s, _ = apply_action(s, cid, a, p or {}, owned=True)
                    return True
                except GameError:
                    return False
            act('select_career')
            for _ in range(days):
                act('start_day')
                for _ in range(6):
                    c = s['careers'][cid]
                    act('more_work')
                    for t in list(c['tasks'])[-2:]:
                        if t['status'] in ('completed', 'referred', 'cancelled'):
                            continue
                        act('task_select', {'task': t['id']})
                        act('ask', {'task': t['id']})
                    act('advance')
                    CLOCK[0] += 300
                act('end_day')
        # Staff paid by the server clock (most played shops of real saves have them).
        for cid in chosen:
            c = s['careers'][cid]
            if cid in wb.ORDERS:
                if c['money'] < 5000:  # owner's capital, through the cash book
                    add = 5000 - c['money']
                    c['money'] += add
                    ops.record_money(c, add, 'Góp vốn chủ tiệm', None, 'other_income')
                try:
                    ops.action(s, c, cid, 'ops_hire', {'candidate': cid + '-staff-1', 'confirm': True})
                except GameError:
                    pass
        # Some hours of staff orders (cash book, receipts, stock use, bonuses).
        for _ in range(6):
            CLOCK[0] += 600
            wb.settle(s)
    npcs = {}
    for k, v in NPC_INDEX.items():
        npcs.setdefault(v['career_id'], []).append(k)
    def size():
        from game import fastjson as fj
        return len(fj.dumps_raw(s))
    # Reviews with comments, memories and chats on the played careers, until the target size.
    i = 0
    while size() < target_kb * 1024 * 0.8 and i < 400:
        cid = chosen[i % len(chosen)]
        c = s['careers'][cid]
        npc = rng.choice(npcs[cid])
        if len(c['feed']) < 90:
            post = engine.add_feed(s, c, npc, _text(rng, 260), 'review', stars=rng.randint(3, 5))
            post['comments'] = [dict(author=NPC_INDEX[npc]['display_name'], text=_text(rng, 160), day=c['day'], npc=npc)
                                for _ in range(rng.randint(1, 4))]
        if len(c['memories']) < 60:
            engine.remember(s, c, npc, _text(rng, 140))
        chat = c['chats'].setdefault(npc, [])
        if len(chat) < 36:
            for _ in range(4):
                chat.append(dict(role='user', text=_text(rng, 90)))
                chat.append(dict(role='npc', text=_text(rng, 180)))
        i += 1
    # Album photos make up the rest (base64 strings, like real saves).
    j = 0
    while size() < target_kb * 1024 * 0.98 and j < 6 * len(chosen):
        c = s['careers'][chosen[j % len(chosen)]]
        if len(c['album']) < 6:
            gap = int(target_kb * 1024 - size())
            c['album'].append(dict(id=f'photo-{j}', image=_photo(rng, max(2000, min(120000, gap))), day=c['day'], title=_text(rng, 40)))
        j += 1
    s['current'] = chosen[0]
    engine.validate_state(s)
    return s


# ---------------------------------------------------------------- phase timers
PH: dict = {}          # phase -> seconds inside the current command
_DEPTH: dict = {}      # phase -> nesting depth (a nested call is counted once)


def _timed(phase, fn):
    def wrapper(*a, **k):
        if _DEPTH.get(phase):
            return fn(*a, **k)
        _DEPTH[phase] = 1
        t = time.thread_time()
        try:
            return fn(*a, **k)
        finally:
            PH[phase] = PH.get(phase, 0.0) + time.thread_time() - t
            _DEPTH[phase] = 0
    wrapper.__wrapped__ = fn
    return wrapper


def _wrap(obj, name, phase):
    fn = getattr(obj, name, None)
    if fn is not None:
        setattr(obj, name, _timed(phase, fn))


def instrument():
    from game import storage, engine, rentals, work_visits, home_guests, db as dbm
    _wrap(storage.Store, 'parse_state', 'parse')
    _wrap(storage, 'apply_action', 'apply')
    for name in ('serialize', 'serialize_bytes'):
        _wrap(storage, name, 'ser+val')
    for mod in (storage, engine):
        _wrap(mod, 'validate_career', 'validate')
        _wrap(mod, 'validate_state', 'validate')
    _wrap(rentals, 'command_commit', 'hooks')
    _wrap(work_visits, 'command_commit', 'hooks')
    _wrap(work_visits, 'sync', 'hooks')
    _wrap(work_visits, 'places', 'places')  # the save's projection, computed before the lock (this tree)
    _wrap(home_guests, 'command_commit', 'hooks')
    _wrap(storage, 'public_state', 'view')
    execute = dbm.PgConnection.execute
    commit = dbm.PgConnection.commit
    lock = [None]

    def ex(self, sql, params=(), *a, **k):
        t = time.perf_counter()
        try:
            return execute(self, sql, params, *a, **k)
        finally:
            d = time.perf_counter() - t
            if sql.startswith('SELECT s.revision AS revision,s.state'):
                PH['fetch'] = PH.get('fetch', 0.0) + d
            elif sql.startswith('UPDATE sessions SET state'):
                PH['update'] = PH.get('update', 0.0) + d
            if 'FROM sessions WHERE sid=? FOR UPDATE' in sql and lock[0] is None:
                lock[0] = t

    def cm(self):
        try:
            return commit(self)
        finally:
            if lock[0] is not None:
                PH['lock'] = PH.get('lock', 0.0) + time.perf_counter() - lock[0]
                lock[0] = None
    dbm.PgConnection.execute = ex
    dbm.PgConnection.commit = cm
    admitted = storage.Store._admitted_command

    def adm(self, *a, **k):
        c0 = time.thread_time()
        try:
            return admitted(self, *a, **k)
        finally:
            PH['cpu'] = time.thread_time() - c0
    storage.Store._admitted_command = adm


# ---------------------------------------------------------------- the benchmark
PHASES = ('fetch', 'parse', 'apply', 'ser+val', 'validate', 'places', 'hooks', 'lock', 'update', 'view', 'delta', 'total', 'cpu')


def _payload(action, view, n):
    cur = view.get('current')
    if action == 'settings':
        return None, {'musicVolume': 20 + n % 60}
    if action == 'ask':
        c = (view.get('careers') or {}).get(cur) or {}
        tid = c.get('active_task')
        return cur, ({'task': tid} if tid else {})
    return cur, {}


def _load(kb, cache):
    path = Path(cache) / f'save-{kb}.json' if cache else None
    if path and path.exists():
        return json.loads(path.read_text())
    state = build_save(kb)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False))
    return state


def bench(sizes, runs, mix, cache=''):
    from game import storage, state_delta, fastjson as fj
    from game.engine import BUILD
    instrument()
    tmp = tempfile.mkdtemp(prefix='bench-command-')
    store = storage.Store(Path(tmp) / 'bench.db', story=False)
    out = {}
    with patch('time.time', fake_time):
        for kb in sizes:
            state = _load(kb, cache)
            state.pop('check', None)
            text = storage.serialize(state, None, True)  # stamped by the measured tree's build
            token = secrets.token_hex(32)
            sid = store.digest('acct:' + token)  # an account save signed in on one device
            with store.connect() as db:
                db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', (sid, 'x' * 48, text))
                db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)', (f'bench{kb}', f'Bench {kb}', 'disabled', sid))
                db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (store.digest(token), sid, 'x' * 48))
            # The server clock of the save: its staff's next orders fall due during the run.
            due = [p['at'] for c in state['careers'].values() for p in ((c.get('ops') or {}).get('business') or {}).get('pending', {}).values()]
            CLOCK[0] = float(min(due)) - 60 if due else 1_900_000_000.0
            rev = 0
            holder = state_delta.Holder()
            res = {}
            r = None
            fp = hashlib.sha256()
            out_fp = ''
            for n in range(2):  # warm up (imports, caches)
                r = store.command(token, secrets.token_hex(8), rev, None, 'settings', {'musicVolume': 30 + n})
                rev = r['revision']
                holder.take(*_delta(state_delta, fj, r['state'], holder))
            for action in mix:
                rows = []
                for n in range(runs):
                    CLOCK[0] += 120
                    career, payload = _payload(action, r['state'], n)
                    PH.clear()
                    t0 = time.perf_counter()
                    try:
                        r2 = store.command(token, secrets.token_hex(8), rev, career, action, payload)
                    except Exception:  # noqa: BLE001 - a refused action is left out
                        continue
                    PH['total'] = time.perf_counter() - t0
                    r = r2
                    rev = r['revision']
                    t = time.thread_time()
                    body, delta = state_delta.encode(r['state'], state_delta.parse_known(holder.known()))
                    PH['delta'] = time.thread_time() - t
                    holder.take(fj.loads(body), delta)
                    rows.append((dict(PH), rev % storage.FULL_EVERY == 0))
                    _fingerprint(fp, store, sid, r)
                if action == mix[-1]:
                    out_fp = fp.hexdigest()[:16]
                ok = [p for p, full in rows if not full]
                res[action] = {ph: round(1000 * statistics.median([p.get(ph, 0.0) for p in ok]), 1) for ph in PHASES} if ok else {}
                res[action]['n'] = len(ok)
            with store.connect() as db:
                size = db.execute('SELECT octet_length(state) AS b FROM sessions WHERE sid=?', (sid,)).fetchone()
            out[kb] = dict(bytes=size['b'], actions=res, fingerprint=out_fp)
    store.close_pool()
    return out, BUILD


def _fingerprint(h, store, sid, r):
    """Every stored save (without the build stamp, which names the tree; the career digests stay),
    result and public view of the run: two trees that behave the same print the same fingerprint."""
    from game import fastjson as fj
    with store.connect() as db:
        text = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()['state']
    saved = fj.loads(text)
    check = saved.pop('check', None)
    h.update(fj.dumps_raw(saved) + b'\0' + fj.dumps_raw((check or {}).get('careers')) + b'\0')
    h.update(json.dumps([r['result'], r['revision']], sort_keys=True, ensure_ascii=False).encode() + b'\0')
    h.update(fj.dumps_raw(r['state']) + b'\0')


def _delta(state_delta, fj, view, holder):
    body, delta = state_delta.encode(view, state_delta.parse_known(holder.known()))
    return fj.loads(body), delta


def main():
    from game import fastjson
    sizes = [int(x) for x in A.sizes.split(',') if x]
    mix = [x for x in A.mix.split(',') if x]
    out, build = bench(sizes, A.runs, mix, A.cache)
    print(f'tree {A.tree}  build {build}  orjson {fastjson.FAST}')
    for kb, r in out.items():
        print(f'\n== save ~{kb} KB ({r["bytes"] / 1024:.0f} KB stored)  run fingerprint {r["fingerprint"]}')
        print('action      ' + ''.join(f'{p:>9}' for p in PHASES) + '      n')
        for action, ph in r['actions'].items():
            print(f'{action:<12}' + ''.join(f'{ph.get(p, 0):>9}' for p in PHASES) + f'{ph.get("n", 0):>7}')
    if A.json:
        Path(A.json).write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
