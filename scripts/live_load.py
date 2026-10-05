#!/usr/bin/env python3
"""Load test of the live service (live/): N WebSocket clients against a live service started on a THROWAWAY
database, so production data is never touched.

  # local disposable PostgreSQL (TEST_DATABASE_URL):
  python scripts/live_load.py --conns 2000
  # on the server: a scratch PostgreSQL database next to the real one
  sudo -u postgres createdb -O <game db user> mnl_loadtest
  PYTHONPATH=/opt/mot-ngay-lam-nghe/shared/pyvendor python3 scripts/live_load.py \\
      --db-url postgresql://<user>@127.0.0.1:5432/mnl_loadtest --conns 2000
  sudo -u postgres dropdb mnl_loadtest

What it does
  1. creates N guest saves in that database (sessions, a name, born before today) and pairs some of them as
     friends, with the game's own schema (game/pg_schema.py);
  2. starts `python3 -m live` on a free port against that isolated PostgreSQL schema (LIVE_CHAT=1);
  3. opens N sockets (spread over --procs client processes). The first --strollers of them stroll (Đi dạo,
     LIVE_STREET=1): groups of 20 walk into the four places (so 500 strollers fill 25 instances), each moves to a
     random walkable spot every --move-every seconds and says something every --say-every seconds. The others
     join Cả phố: `--rate` messages per second are posted there by enough chatters to respect the 10 s slow mode,
     `--churn` idle sockets per second disconnect and come back (presence: their friends get green dots on and off);
  4. after --duration seconds reports: sockets open, messages sent, deliveries, p50/p95/p99 delivery latency
     (send → every receiver, Cả phố), the same for moves (a stroller's `move` → the `walk` diff on the screens of
     the others in its instance), errors, and the live process's CPU (average and peak, % of one core) and RSS.
     With --weddings N (LIVE_WEDDING=1), the first N × (--guests + 2) sockets are N couples and their guests at N live
     wedding parties booked for now (60 visible each, the rest watch): they move, cheer and are counted like strollers;
     the report has their move-delivery latency apart.
The spec's budget: p95 < 300 ms at 2,000 sockets: 500 strolling in 25 rooms, 1,500 in chat, Cả phố at 5 messages/s
(docs/superpowers/specs/2026-09-30-live-chat-street-design.md).

💕 Dates (--dates N, LIVE_DATING=1): 2N more players sit on the dating bench at once (Nam/Nữ, mostly "ai cũng
được"), so N café dates run at the same time; each bot plays the whole date like a person (picks after 0.2–2 s,
orders, one chat line, ❤️ or 👋) and sits down again after the end (the 24 h rule makes it meet someone new). The
report adds: dates finished and mutual, the most dates at once (from the bots' own start/end times), the wait on the bench (sit → matched), the answer
round trip (a pick → my updated view) and the chat round trip (date_say → my message back), p50/p95/p99.
  python scripts/live_load.py --conns 0 --strollers 0 --dates 200 --duration 90
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import multiprocessing as mp
import os
import random
import resource
import secrets
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def raise_fd_limit(n: int = 65536) -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    want = min(n, hard) if hard != resource.RLIM_INFINITY else n
    if soft < want:
        resource.setrlimit(resource.RLIMIT_NOFILE, (want, hard))


def most_at_once(spans) -> int:
    """The most (start, end) intervals open at the same moment."""
    spans = list(spans)
    ev = sorted([(a, 1) for a, _ in spans] + [(b, -1) for _, b in spans], key=lambda x: (x[0], x[1]))
    n = best = 0
    for _, d in ev:
        n += d
        best = max(best, n)
    return best


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------- 1. players in a throwaway database
def sid_of(token: str) -> str:
    """The save behind a load player's cookie (an account signed in on this device: logins.token = sha256(cookie))."""
    return hashlib.sha256(('acct:' + token).encode()).hexdigest()


def make_players(n: int, db_url: str | None, db_path: str | None, friends_every: int) -> list[str]:
    """N accounts (1.0.1: only accounts post, date and count at weddings) with named saves born before today, each
    signed in on its own device (a `logins` row); every `friends_every`-th pair are friends. Returns their cookie
    tokens (sid_of(token) is the save)."""
    if not db_url:
        raise SystemExit('A disposable PostgreSQL URL is required')
    os.environ.pop('DATABASE_URL', None)
    os.environ['TEST_DATABASE_URL'] = db_url
    from game import admin_stats, push, social
    from game.storage import Store
    store = Store(db_path)
    social.ensure(store)
    push.ensure(store)
    admin_stats.ensure(store)
    tokens = [secrets.token_hex(32) for _ in range(n)]
    sids = [sid_of(tok) for tok in tokens]
    t = time.time()

    def run(db):
        for i, sid in enumerate(sids):
            db.execute("INSERT INTO sessions(sid, csrf, state) VALUES(?, ?, '{}')", (sid, secrets.token_hex(8)))
            db.execute('INSERT INTO leaderboard_players(sid, name, updated) VALUES(?, ?, ?)', (sid, f'Thử tải {i}', t))
            db.execute("INSERT INTO stat_births(sid, day) VALUES(?, '2026-01-01') ON CONFLICT(sid) DO UPDATE SET day=excluded.day", (sid,))
            db.execute('INSERT INTO accounts(username, display, pw, sid) VALUES(?, ?, ?, ?)', (f'load_{i}_{sid[:8]}', f'Thử tải {i}', 'x', sid))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?, ?, ?)', (hashlib.sha256(tokens[i].encode()).hexdigest(), sid, 'c'))
        for i in range(0, n - 1, max(2, friends_every)):
            a, b = sids[i], sids[i + 1]
            db.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?)', (a, b, t))
            db.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?)', (b, a, t))
    store.transaction(run)
    store.close_pool()
    return tokens


def make_weddings(tokens: list, n: int, per: int, db_url: str | None, db_path: str | None) -> list:
    """N couples (the first two of each group of per + 2 tokens) with a party booked a minute from now (open). Returns
    the wedding ids."""
    if not db_url:
        raise SystemExit('A disposable PostgreSQL URL is required')
    os.environ.pop('DATABASE_URL', None)
    os.environ['TEST_DATABASE_URL'] = db_url
    from game.storage import Store
    store = Store(db_path)
    t = time.time()
    ids = []

    def run(db):
        for k in range(n):
            a, b = (sid_of(x) for x in tokens[k * (per + 2):k * (per + 2) + 2])
            wid = 900000 + k
            db.execute("INSERT INTO couples(id, a, b, status, since) VALUES(?, ?, ?, 'engaged', ?)", (wid, a, b, t))
            db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) VALUES(?, ?, ?, ?, ?, 'booked', ?)", (wid, wid, a, b, t + 60, t))
            ids.append(wid)
    store.transaction(run)
    store.close_pool()
    return ids


# ---------------------------------------------------------------- 2. the service
def start_live(port: int, db_url: str | None, db_path: str | None, origin: str, log_path: str, dating: bool = False, speed: float = 1.0):
    env = dict(os.environ, LIVE_CHAT='1', LIVE_STREET='1', LIVE_WEDDING='1', LIVE_PORT=str(port), LIVE_ORIGINS=origin, LIVE_PER_IP='1000000',
               LIVE_HANDSHAKES_PER_IP='1000000', LIVE_PER_PLAYER='5', QUIET='1', LIVE_DATING='1' if dating else '0',
               LIVE_DATE_SPEED=str(speed))
    env.pop('DATABASE_URL', None)
    if db_url:
        env['DATABASE_URL'] = db_url
    from game.storage import Store
    schema = Store(db_path).pg.schema
    args = [sys.executable, '-m', 'live', '--schema', schema]
    log = open(log_path, 'w')
    p = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=log, preexec_fn=lambda: raise_fd_limit())
    end = time.time() + 60
    while time.time() < end:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/live/health', timeout=1)
            return p
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    p.terminate()
    raise SystemExit('the live service did not start: see ' + log_path)


def ps(pid: int) -> tuple[float, float]:
    """(CPU seconds used so far, RSS in MB) of a process, from ps (macOS and Linux)."""
    out = subprocess.run(['ps', '-o', 'time=,rss=', '-p', str(pid)], capture_output=True, text=True).stdout.split()
    if len(out) < 2:
        return 0.0, 0.0
    parts = [float(x) for x in out[0].replace('-', ':').split(':')]
    secs = 0.0
    for x in parts:
        secs = secs * 60 + x
    return secs, int(out[1]) / 1024


# ---------------------------------------------------------------- 3. clients (one process each)
def client_proc(idx, url, origin, items, every, churn_per_s, duration, ramp_per_s, move_every, say_every, q):
    raise_fd_limit()
    asyncio.run(_clients(idx, url, origin, items, every, churn_per_s, duration, ramp_per_s, move_every, say_every, q))


def pid_of_token(token: str) -> str:
    return hashlib.sha256(('pid:' + sid_of(token)).encode()).hexdigest()[:16]


async def _clients(idx, url, origin, items, every, churn_per_s, duration, ramp_per_s, move_every, say_every, q):
    """items: (role, token, place) per socket; role 'walk' (a stroller), 'chat' (posts on Cả phố) or 'idle'."""
    from websockets.asyncio.client import connect
    from live.street import GEO
    lat: list = []
    mlat: list = []
    stats = dict(open=0, failed=0, sent=0, recv=0, errors=0, closed=0, presence=0, reconnects=0, moves=0, move_recv=0, said=0, says=0,
                 walk_frames=0, walk_in=0, wed_moves=0, wed_recv=0)
    sent_at: dict = {}
    moved_at: dict = {}             # (pid, x, y) -> when this process sent that move
    wed_moved: dict = {}            # the same for moves in a wedding party
    wlat: list = []
    codes: dict = {}                # error ref:code -> count
    stop = asyncio.Event()
    socks: dict = {}
    roles = {i: r for i, (r, _, _) in enumerate(items)}

    async def stroll(ws, token, place, reader, wedding=None):
        pid, g = pid_of_token(token), GEO['wedding' if wedding else place]
        sent = wed_moved if wedding else moved_at
        if wedding:
            await ws.send(json.dumps({'t': 'wed_in', 'id': wedding, 'look': None, 'g': random.choice(['male', 'female'])}))
        else:
            await ws.send(json.dumps({'t': 'walk_in', 'place': place, 'look': None, 'g': random.choice(['male', 'female'])}))
        stats['walk_in'] += 1
        await asyncio.sleep(random.random() * move_every)
        next_say = time.monotonic() + random.uniform(0.3, 1.0) * say_every
        while not stop.is_set() and not reader.done():
            x, y = g.random_point(25)
            sent[(pid, x, y)] = time.monotonic()
            await ws.send(json.dumps({'t': 'move', 'x': x, 'y': y}))
            stats['wed_moves' if wedding else 'moves'] += 1
            if time.monotonic() >= next_say:
                await ws.send(json.dumps({'t': 'say', 'text': f'dạo phố tí {random.randint(1, 10 ** 6)}'}))
                stats['says'] += 1
                next_say = time.monotonic() + say_every * random.uniform(.8, 1.2)
            await asyncio.sleep(move_every * random.uniform(.8, 1.2))

    async def one(i, token, role, place):
        chatter = role == 'chat'
        while not stop.is_set():
            try:
                ws = await connect(url, origin=origin, additional_headers={'Cookie': f'mnl_session={token}'},
                                   open_timeout=20, ping_interval=None, max_size=2 ** 20, compression=None)
            except Exception:  # noqa: BLE001
                stats['failed'] += 1
                await asyncio.sleep(1 + random.random())
                continue
            socks[i] = ws
            stats['open'] += 1
            try:
                await ws.send('{"t":"hello","v":1}')
                if role not in ('walk', 'wed'):
                    await ws.send('{"t":"join","ch":"town"}')
                reader = asyncio.ensure_future(read(ws))
                pinger = asyncio.ensure_future(ping(ws))
                if role == 'walk':
                    await stroll(ws, token, place, reader)
                elif role == 'wed':
                    await stroll(ws, token, None, reader, wedding=place)
                elif chatter:
                    await asyncio.sleep(random.random() * every)
                    while not stop.is_set() and not reader.done():
                        seq = f'{idx}-{i}-{stats["sent"]}'
                        sent_at[seq] = time.monotonic()
                        await ws.send(json.dumps({'t': 'send', 'ch': 'town', 'text': f'lt {seq} chào cả phố', 'cid': seq}))
                        stats['sent'] += 1
                        await asyncio.sleep(every * random.uniform(1.0, 1.15))
                await asyncio.wait([reader, asyncio.ensure_future(stop.wait())], return_when=asyncio.FIRST_COMPLETED)
                pinger.cancel()
                reader.cancel()
            finally:
                socks.pop(i, None)
                stats['open'] -= 1
                await ws.close()
            if stop.is_set():
                return
            stats['reconnects'] += 1

    async def read(ws):
        try:
            async for raw in ws:
                now = time.monotonic()
                f = json.loads(raw)
                t = f.get('t')
                if t == 'msg' and f.get('ch') == 'town':
                    seq = f['text'].split(' ', 2)[1] if f['text'].startswith('lt ') else None
                    at = sent_at.get(seq)
                    stats['recv'] += 1
                    if at is not None and not f.get('cid'):
                        lat.append(now - at)
                elif t == 'walk':
                    stats['walk_frames'] += 1
                    for e in f['ev']:
                        if e['k'] == 'mv':
                            end = e['p'][-1]
                            at = moved_at.get((e['pid'], end[0], end[1]))
                            if at is not None:
                                stats['move_recv'] += 1
                                mlat.append(now - at)
                            at = wed_moved.get((e['pid'], end[0], end[1]))
                            if at is not None:
                                stats['wed_recv'] += 1
                                wlat.append(now - at)
                elif t == 'said':
                    stats['said'] += 1
                elif t == 'error':
                    stats['errors'] += 1
                    k = f"{f.get('ref')}:{f.get('code')}"
                    codes[k] = codes.get(k, 0) + 1
                elif t == 'presence':
                    stats['presence'] += 1
        except Exception:  # noqa: BLE001
            stats['closed'] += 1

    async def ping(ws):
        while True:
            await asyncio.sleep(25)
            await ws.send('{"t":"ping"}')

    async def churn():
        while not stop.is_set():
            await asyncio.sleep(1)
            for _ in range(churn_per_s):
                victims = [k for k in socks if roles[k] == 'idle']
                if victims:
                    ws = socks.get(random.choice(victims))
                    if ws:
                        await ws.close()

    tasks = []
    for i, (role, tok, place) in enumerate(items):
        tasks.append(asyncio.ensure_future(one(i, tok, role, place)))
        if ramp_per_s:
            await asyncio.sleep(1 / ramp_per_s)
    q.put(('ready', idx, stats['open']))
    ch = asyncio.ensure_future(churn()) if churn_per_s else None
    t0 = time.monotonic()
    while time.monotonic() - t0 < duration:
        await asyncio.sleep(1)
    stop.set()
    if ch:
        ch.cancel()
    await asyncio.wait(tasks, timeout=10)
    q.put(('done', idx, dict(stats, lat=lat, mlat=mlat, wlat=wlat, codes=codes)))


# ---------------------------------------------------------------- 3b. 💕 date bots (one process each)
def date_proc(idx, url, origin, tokens, duration, ramp_per_s, q):
    raise_fd_limit()
    asyncio.run(_daters(idx, url, origin, tokens, duration, ramp_per_s, q))


async def _daters(idx, url, origin, tokens, duration, ramp_per_s, q):
    from websockets.asyncio.client import connect
    rng = random.Random(idx)
    st = dict(open=0, failed=0, errors=0, dates=0, mutual=0, left=0, sits=0, says=0, codes={})
    lat = dict(match=[], ack=[], say=[], length=[], spans=[])
    stop = asyncio.Event()
    tasks: set = set()

    def later(delay, coro):
        async def run():
            await asyncio.sleep(delay)
            if not stop.is_set():
                try:
                    await coro
                except Exception:  # noqa: BLE001 - the socket went away meanwhile
                    pass
        t = asyncio.ensure_future(run())
        tasks.add(t)
        t.add_done_callback(tasks.discard)

    async def bot(i, token):
        g = 'm' if (i + idx) % 2 else 'f'
        pref = 'any' if rng.random() < 0.7 else ('f' if g == 'm' else 'm')
        while not stop.is_set():
            try:
                ws = await connect(url, origin=origin, additional_headers={'Cookie': f'mnl_session={token}'},
                                   open_timeout=20, ping_interval=None, max_size=2 ** 20, compression=None)
            except Exception:  # noqa: BLE001
                st['failed'] += 1
                await asyncio.sleep(1 + rng.random())
                continue
            st['open'] += 1
            cur: dict = {}
            sent: dict = {}

            async def send(frame):
                await ws.send(json.dumps(frame))

            async def sit():
                sent['sit'] = time.monotonic()
                st['sits'] += 1
                await send({'t': 'queue', 'op': 'sit', 'pref': pref, 'g': g})

            async def pick(d, i):
                sent[('pick', d, i)] = time.monotonic()
                await send({'t': 'answer', 'date': d, 'step': 'card', 'i': i, 'pick': rng.randrange(3)})

            async def chat(d):
                cid = f'{idx}-{i}-{st["says"]}'
                sent[('say', cid)] = time.monotonic()
                st['says'] += 1
                await send({'t': 'date_say', 'date': d, 'text': rng.choice(('chào nha 😆', 'cùng gu ghê', 'haha vl', 'lần sau đi tiếp nhé')) + f' {cid}', 'cid': cid})
                await asyncio.sleep(rng.uniform(0.5, 1.5))
                await send({'t': 'answer', 'date': d, 'step': 'chat'})

            try:
                await send({'t': 'hello', 'v': 1})
                await sit()
                pinger = asyncio.ensure_future(ping(ws))
                async for raw in ws:
                    now = time.monotonic()
                    f = json.loads(raw)
                    t = f.get('t')
                    if t == 'date':
                        d, step = f['id'], f['step']
                        if cur.get('id') != d and step != 'end':
                            cur.clear()
                            cur.update(id=d, start=now, acted=set())
                            if 'sit' in sent:
                                lat['match'].append(now - sent.pop('sit'))
                        acted = cur.get('acted', set())
                        if step == 'card':
                            k = ('pick', d, f['i'])
                            if f.get('mine') is not None and k in sent:
                                lat['ack'].append(now - sent.pop(k))
                            if not f.get('shown') and f.get('mine') is None and ('card', f['i']) not in acted:
                                acted.add(('card', f['i']))
                                later(rng.uniform(0.2, 2.0), pick(d, f['i']))
                        elif step == 'menu' and not f.get('shown') and f.get('give') is None and 'menu' not in acted:
                            acted.add('menu')
                            items = [m['id'] for m in f['menu']]
                            later(rng.uniform(0.5, 2.5), send({'t': 'answer', 'date': d, 'step': 'menu', 'want': rng.choice(items), 'give': rng.choice(items)}))
                        elif step == 'chat' and 'chat' not in acted:
                            acted.add('chat')
                            later(rng.uniform(0.3, 1.5), chat(d))
                        elif step == 'vote' and f.get('mine') is None and 'vote' not in acted:
                            acted.add('vote')
                            later(rng.uniform(0.3, 1.5), send({'t': 'heart', 'date': d, 'v': 'heart' if rng.random() < 0.6 else 'wave'}))
                        elif step == 'end':
                            st['dates'] += 1
                            st['mutual'] += f.get('how') == 'match'
                            st['left'] += f.get('how') in ('left', 'gone')
                            if 'start' in cur:
                                lat['length'].append(now - cur['start'])
                                lat['spans'].append((time.time() - (now - cur['start']), time.time()))
                            cur.clear()
                            later(rng.uniform(0.5, 2.0), sit())
                    elif t == 'msg' and f.get('cid'):
                        k = ('say', f['cid'])
                        if k in sent:
                            lat['say'].append(now - sent.pop(k))
                    elif t == 'error':
                        st['errors'] += 1
                        st['codes'][f.get('code')] = st['codes'].get(f.get('code'), 0) + 1
                    if stop.is_set():
                        break
                pinger.cancel()
            except Exception:  # noqa: BLE001
                pass
            finally:
                st['open'] -= 1
                await ws.close()

    async def ping(ws):
        while True:
            await asyncio.sleep(25)
            await ws.send('{"t":"ping"}')

    bots = []
    for i, tok in enumerate(tokens):
        bots.append(asyncio.ensure_future(bot(i, tok)))
        if ramp_per_s:
            await asyncio.sleep(1 / ramp_per_s)
    q.put(('ready', idx, st['open']))
    t0 = time.monotonic()
    while time.monotonic() - t0 < duration:
        await asyncio.sleep(1)
    stop.set()
    for t in list(tasks):
        t.cancel()
    await asyncio.wait(bots, timeout=10)
    q.put(('done', idx, dict(st, lat=lat, kind='dates')))


# ---------------------------------------------------------------- 4. the run
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--conns', type=int, default=2000)
    ap.add_argument('--rate', type=float, default=5.0, help='Cả phố messages per second, all chatters together')
    ap.add_argument('--churn', type=int, default=5, help='sockets per second that drop and come back (presence)')
    ap.add_argument('--duration', type=int, default=60, help='seconds of steady load after the ramp')
    ap.add_argument('--procs', type=int, default=max(2, min(8, (os.cpu_count() or 4) // 2)))
    ap.add_argument('--ramp', type=int, default=400, help='new sockets per second while ramping up')
    ap.add_argument('--friends-every', type=int, default=4, help='every n-th pair of players are friends')
    ap.add_argument('--db-url', default=os.environ.get('TEST_DATABASE_URL'), help='a THROWAWAY PostgreSQL database (never the game database)')
    ap.add_argument('--url', help='unsupported: this harness starts a service on its isolated PostgreSQL schema')
    ap.add_argument('--pid', type=int, help='unsupported existing-service option')
    ap.add_argument('--every', type=float, default=10.0, help="a chatter's pause between messages (slow mode: >= 10)")
    ap.add_argument('--strollers', type=int, default=500, help='sockets strolling (Đi dạo) in groups of 20 per instance')
    ap.add_argument('--weddings', type=int, default=0, help='live wedding parties (LIVE_WEDDING), each with --guests guests and the couple')
    ap.add_argument('--guests', type=int, default=60, help='guests per wedding party')
    ap.add_argument('--move-every', type=float, default=2.0, help="a stroller's pause between two moves (seconds)")
    ap.add_argument('--say-every', type=float, default=45.0, help="a stroller's pause between two speech bubbles (seconds)")
    ap.add_argument('--dates', type=int, default=0, help='💕 café dates at the same time (2 more players each; LIVE_DATING=1)')
    ap.add_argument('--date-speed', type=float, default=1.0, help='LIVE_DATE_SPEED of the service it starts (1 = real time)')
    args = ap.parse_args()
    if args.url is not None or args.pid is not None:
        raise SystemExit('--url/--pid are unsupported: this harness creates an isolated PostgreSQL schema and starts its matching live service')
    raise_fd_limit()
    if not args.db_url:
        raise SystemExit('Set TEST_DATABASE_URL or pass --db-url for a disposable PostgreSQL database')
    if not os.environ.get('TEST_DATABASE_URL') and 'loadtest' not in args.db_url:
        raise SystemExit('--db-url must name a scratch database whose name contains "loadtest" (never the game database)')
    tmp = tempfile.mkdtemp(prefix='mnl-live-load-')
    db_path = os.path.join(tmp, 'load')
    t0 = time.time()
    tokens = make_players(args.conns + 2 * args.dates, args.db_url, db_path, args.friends_every)
    tokens, daters = tokens[:args.conns], tokens[args.conns:]
    print(f'players: {len(tokens)} in {time.time() - t0:.1f}s', file=sys.stderr)
    origin = 'http://load.test'
    port = free_port()
    live = start_live(port, args.db_url, db_path, origin, os.path.join(tmp, 'live.log'), dating=bool(args.dates), speed=args.date_speed)
    url, pid = f'ws://127.0.0.1:{port}/live', live.pid
    from live.street_data import PUBLIC
    per = args.guests + 2
    wed_n = min(len(tokens), args.weddings * per)
    weds = make_weddings(tokens, args.weddings, args.guests, args.db_url, db_path) if args.weddings else []
    rest = tokens[wed_n:]
    walkers = min(args.strollers, len(rest))
    chat_n = max(1, round(args.rate * args.every))
    items = [('wed', t, weds[i // per]) for i, t in enumerate(tokens[:wed_n])]
    items += [('walk', t, PUBLIC[(i // 20) % len(PUBLIC)]) if i < walkers else ('chat' if i - walkers < chat_n else 'idle', t, None)
              for i, t in enumerate(rest)]
    q = mp.Queue()
    parts = [items[i::args.procs] for i in range(args.procs)]
    procs = [mp.Process(target=client_proc, args=(i, url, origin, parts[i], args.every, max(0, round(args.churn / args.procs)),
                                                  args.duration, max(1, args.ramp // args.procs), args.move_every, args.say_every, q))
             for i in range(args.procs)] if tokens else []
    if daters:
        dprocs = max(1, min(args.procs, len(daters) // 50))
        procs += [mp.Process(target=date_proc, args=(100 + i, url, origin, daters[i::dprocs], args.duration, max(1, args.ramp // dprocs), q))
                  for i in range(dprocs)]
    cpu0, _ = ps(pid) if pid else (0, 0)
    t_ramp = time.monotonic()
    for p in procs:
        p.start()
    ready = 0
    while ready < len(procs):
        kind, *_ = q.get(timeout=600)
        ready += kind == 'ready'
    ramp = time.monotonic() - t_ramp
    time.sleep(2)
    samples, last, health = [], ps(pid) if pid else (0, 0), None
    peak_rss = last[1]
    t_last = time.monotonic()
    results, done = [], 0
    while done < len(procs):
        try:
            kind, idx, data = q.get(timeout=1)
            if kind == 'done':
                results.append(data)
                done += 1
        except Exception:  # noqa: BLE001 - queue.Empty: sample the service
            pass
        if pid and time.monotonic() - t_last >= 1 and done == 0:
            if len(samples) % 5 == 4:   # the service's own counters while the load runs
                try:
                    h = json.loads(urllib.request.urlopen(url.replace('ws://', 'http://') + '/health', timeout=3).read())
                    if not health or h.get('conns', 0) >= health.get('conns', 0):
                        health = h
                except Exception:  # noqa: BLE001
                    pass
            now = ps(pid)
            dt = time.monotonic() - t_last
            samples.append(100 * (now[0] - last[0]) / dt)
            peak_rss = max(peak_rss, now[1])
            last, t_last = now, time.monotonic()
    for p in procs:
        p.join(5)
    if live:
        live.send_signal(signal.SIGTERM)
        live.wait(15)
    dres = [r for r in results if r.get('kind') == 'dates']
    results = [r for r in results if r.get('kind') != 'dates']
    lat = sorted(x for r in results for x in r['lat'])
    mlat = sorted(x for r in results for x in r['mlat'])
    wlat = sorted(x for r in results for x in r['wlat'])
    tot = {k: sum(r[k] for r in results) for k in ('sent', 'recv', 'errors', 'failed', 'presence', 'reconnects', 'closed', 'moves', 'move_recv',
                                                   'said', 'says', 'walk_frames', 'walk_in', 'wed_moves', 'wed_recv')}

    def pcts(xs):
        at = lambda p: round(1000 * xs[min(len(xs) - 1, int(p * len(xs)))], 1)
        return dict(p50=at(.5), p95=at(.95), p99=at(.99), max=round(1000 * xs[-1], 1), n=len(xs)) if xs else None
    pct = lambda p: round(1000 * lat[min(len(lat) - 1, int(p * len(lat)))], 1) if lat else None
    steady = samples[2:] or samples
    report = dict(conns=args.conns, ramp_s=round(ramp, 1), duration_s=args.duration, chatters=chat_n, target_rate=args.rate,
                  sent=tot['sent'], deliveries=tot['recv'], rate_measured=round(tot['sent'] / max(1, args.duration), 2),
                  latency_ms=dict(p50=pct(.5), p95=pct(.95), p99=pct(.99), max=round(1000 * lat[-1], 1) if lat else None, n=len(lat)),
                  strollers=walkers, moves_sent=tot['moves'], move_deliveries_measured=tot['move_recv'], walk_frames=tot['walk_frames'],
                  move_latency_ms=pcts(mlat), bubbles_sent=tot['says'], bubbles_received=tot['said'],
                  weddings=len(weds), wedding_sockets=wed_n, wedding_moves_sent=tot['wed_moves'], wedding_move_deliveries_measured=tot['wed_recv'],
                  wedding_move_latency_ms=pcts(wlat),
                  errors=tot['errors'], error_codes={k: sum(r['codes'].get(k, 0) for r in results) for k in {c for r in results for c in r['codes']}},
                  connect_failures=tot['failed'], reconnects=tot['reconnects'], presence_frames=tot['presence'],
                  live_cpu_pct=dict(avg=round(statistics.mean(steady), 1) if steady else None, peak=round(max(steady), 1) if steady else None),
                  live_rss_mb=round(peak_rss, 1), live_cpu_s_total=round((last[0] - cpu0), 1) if pid else None, health=health,
                  db='postgresql')
    if dres:
        def ms(key):
            xs = sorted(x for r in dres for x in r['lat'][key])
            at = lambda p: round(1000 * xs[min(len(xs) - 1, int(p * len(xs)))], 1) if xs else None   # noqa: E731
            return dict(p50=at(.5), p95=at(.95), p99=at(.99), n=len(xs))
        codes: dict = {}
        for r in dres:
            for k, v in r['codes'].items():
                codes[k] = codes.get(k, 0) + v
        lengths = sorted(x for r in dres for x in r['lat']['length'])
        report['dates'] = dict(pairs=args.dates, players=2 * args.dates, speed=args.date_speed,
                               finished=sum(r['dates'] for r in dres) // 2, mutual=sum(r['mutual'] for r in dres) // 2,
                               ended_early=sum(r['left'] for r in dres) // 2, sits=sum(r['sits'] for r in dres),
                               most_at_once=most_at_once(x for r in dres for x in r['lat']['spans']) // 2,   # both players report each date
                               bench_wait_ms=ms('match'), answer_rtt_ms=ms('ack'), chat_rtt_ms=ms('say'),
                               date_length_s=round(statistics.median(lengths), 1) if lengths else None,
                               errors=sum(r['errors'] for r in dres), error_codes=codes, connect_failures=sum(r['failed'] for r in dres))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)   # temporary logs; PostgreSQL schemas are cleaned at exit


if __name__ == '__main__':
    mp.set_start_method('spawn')
    main()
