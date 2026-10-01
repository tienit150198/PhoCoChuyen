#!/usr/bin/env python3
"""Load test of the live service (live/): N WebSocket clients against a live service started on a THROWAWAY
database, so production data is never touched.

  # local (SQLite, a temporary file):
  python scripts/live_load.py --conns 2000
  # on the server: a scratch PostgreSQL database next to the real one
  sudo -u postgres createdb -O <game db user> mnl_loadtest
  PYTHONPATH=/opt/mot-ngay-lam-nghe/shared/pyvendor python3 scripts/live_load.py \\
      --db-url postgresql://<user>@127.0.0.1:5432/mnl_loadtest --conns 2000
  sudo -u postgres dropdb mnl_loadtest

What it does
  1. creates N guest saves in that database (sessions, a name, born before today) and pairs some of them as
     friends, with the game's own schema (game/pg_schema.py / game/storage.py);
  2. starts `python3 -m live` on a free port against it (LIVE_CHAT=1), or uses --url for one already running;
  3. opens N sockets (spread over --procs client processes): all join Cả phố, `--rate` messages per second are
     posted on Cả phố by enough chatters to respect the 10 s slow mode, `--churn` sockets per second disconnect
     and come back (presence: their friends get green dots on and off);
  4. after --duration seconds reports: sockets open, messages sent, deliveries, p50/p95/p99 delivery latency
     (send → every receiver), errors, and the live process's CPU (average and peak, % of one core) and RSS.
The spec's budget: p95 < 300 ms at 2,000 sockets and 5 messages/s (docs/superpowers/specs/...-design.md).

💕 Dates (--dates N, LIVE_DATING=1): 2N more players sit on the dating bench at once (Nam/Nữ, mostly "ai cũng
được"), so N café dates run at the same time; each bot plays the whole date like a person (picks after 0.2–2 s,
orders, one chat line, ❤️ or 👋) and sits down again after the end (the 24 h rule makes it meet someone new). The
report adds: dates finished and mutual, the most dates at once, the wait on the bench (sit → matched), the answer
round trip (a pick → my updated view) and the chat round trip (date_say → my message back), p50/p95/p99.
  python scripts/live_load.py --conns 0 --dates 200 --duration 90
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


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------- 1. players in a throwaway database
def make_players(n: int, db_url: str | None, db_path: str | None, friends_every: int) -> list[str]:
    """N guest saves with names, born before today; every `friends_every`-th pair are friends. Returns their
    cookie tokens (sha256(token) = sid, like an anonymous player)."""
    if db_url:
        os.environ['DATABASE_URL'] = db_url
    from game import admin_stats, push, social
    from game.storage import Store
    store = Store(db_path or 'loadtest.sqlite3')
    social.ensure(store)
    push.ensure(store)
    admin_stats.ensure(store)
    tokens = [secrets.token_hex(32) for _ in range(n)]
    sids = [hashlib.sha256(t.encode()).hexdigest() for t in tokens]
    t = time.time()

    def run(db):
        for i, sid in enumerate(sids):
            db.execute("INSERT INTO sessions(sid, csrf, state) VALUES(?, ?, '{}')", (sid, secrets.token_hex(8)))
            db.execute('INSERT INTO leaderboard_players(sid, name, updated) VALUES(?, ?, ?)', (sid, f'Thử tải {i}', t))
            db.execute("INSERT INTO stat_births(sid, day) VALUES(?, '2026-01-01') ON CONFLICT(sid) DO UPDATE SET day=excluded.day", (sid,))
        for i in range(0, n - 1, max(2, friends_every)):
            a, b = sids[i], sids[i + 1]
            db.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?)', (a, b, t))
            db.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?)', (b, a, t))
    store.transaction(run)
    store.close_pool()
    return tokens


# ---------------------------------------------------------------- 2. the service
def start_live(port: int, db_url: str | None, db_path: str | None, origin: str, log_path: str, dating: bool = False, speed: float = 1.0):
    env = dict(os.environ, LIVE_CHAT='1', LIVE_PORT=str(port), LIVE_ORIGINS=origin, LIVE_PER_IP='1000000',
               LIVE_HANDSHAKES_PER_IP='1000000', LIVE_PER_PLAYER='5', QUIET='1', LIVE_DATING='1' if dating else '0',
               LIVE_DATE_SPEED=str(speed))
    env.pop('DATABASE_URL', None)
    if db_url:
        env['DATABASE_URL'] = db_url
    args = [sys.executable, '-m', 'live'] + ([] if db_url else ['--db', db_path])
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
def client_proc(idx, url, origin, tokens, chat_n, every, churn_per_s, duration, ramp_per_s, q):
    raise_fd_limit()
    asyncio.run(_clients(idx, url, origin, tokens, chat_n, every, churn_per_s, duration, ramp_per_s, q))


async def _clients(idx, url, origin, tokens, chat_n, every, churn_per_s, duration, ramp_per_s, q):
    from websockets.asyncio.client import connect
    lat: list = []
    stats = dict(open=0, failed=0, sent=0, recv=0, errors=0, closed=0, presence=0, reconnects=0)
    sent_at: dict = {}
    stop = asyncio.Event()
    socks: dict = {}

    async def one(i, token, chatter):
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
                await ws.send('{"t":"join","ch":"town"}')
                reader = asyncio.ensure_future(read(ws))
                pinger = asyncio.ensure_future(ping(ws))
                if chatter:
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
                elif t == 'error':
                    stats['errors'] += 1
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
                victims = [k for k in socks if k >= chat_n]
                if victims:
                    ws = socks.get(random.choice(victims))
                    if ws:
                        await ws.close()

    tasks = []
    for i, tok in enumerate(tokens):
        tasks.append(asyncio.ensure_future(one(i, tok, i < chat_n)))
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
    q.put(('done', idx, dict(stats, lat=lat)))


# ---------------------------------------------------------------- 3b. 💕 date bots (one process each)
def date_proc(idx, url, origin, tokens, duration, ramp_per_s, q):
    raise_fd_limit()
    asyncio.run(_daters(idx, url, origin, tokens, duration, ramp_per_s, q))


async def _daters(idx, url, origin, tokens, duration, ramp_per_s, q):
    from websockets.asyncio.client import connect
    rng = random.Random(idx)
    st = dict(open=0, failed=0, errors=0, dates=0, mutual=0, left=0, sits=0, says=0, codes={})
    lat = dict(match=[], ack=[], say=[], length=[])
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
    ap.add_argument('--db-url', help='a THROWAWAY PostgreSQL database (never the game database)')
    ap.add_argument('--url', help='a live service already running against the same throwaway database')
    ap.add_argument('--pid', type=int, help='its process id (CPU, RSS) with --url')
    ap.add_argument('--every', type=float, default=10.0, help="a chatter's pause between messages (slow mode: >= 10)")
    ap.add_argument('--dates', type=int, default=0, help='💕 café dates at the same time (2 more players each; LIVE_DATING=1)')
    ap.add_argument('--date-speed', type=float, default=1.0, help='LIVE_DATE_SPEED of the service it starts (1 = real time)')
    args = ap.parse_args()
    raise_fd_limit()
    if args.db_url and 'loadtest' not in args.db_url:
        raise SystemExit('--db-url must name a scratch database whose name contains "loadtest" (never the game database)')
    tmp = tempfile.mkdtemp(prefix='mnl-live-load-')
    db_path = None if args.db_url else os.path.join(tmp, 'load.sqlite3')
    t0 = time.time()
    tokens = make_players(args.conns + 2 * args.dates, args.db_url, db_path, args.friends_every)
    tokens, daters = tokens[:args.conns], tokens[args.conns:]
    print(f'players: {len(tokens)} in {time.time() - t0:.1f}s', file=sys.stderr)
    origin = 'http://load.test'
    live = None
    if args.url:
        url, pid = args.url, args.pid
    else:
        port = free_port()
        live = start_live(port, args.db_url, db_path, origin, os.path.join(tmp, 'live.log'), dating=bool(args.dates), speed=args.date_speed)
        url, pid = f'ws://127.0.0.1:{port}/live', live.pid
    chat_n = max(1, round(args.rate * args.every))
    q = mp.Queue()
    parts = [tokens[i::args.procs] for i in range(args.procs)]
    chat_parts = [len(range(i, chat_n, args.procs)) for i in range(args.procs)]
    procs = [mp.Process(target=client_proc, args=(i, url, origin, parts[i], chat_parts[i], args.every, max(0, round(args.churn / args.procs)),
                                                  args.duration, max(1, args.ramp // args.procs), q)) for i in range(args.procs)] if tokens else []
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
    results, done, max_rooms = [], 0, 0
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
                    max_rooms = max(max_rooms, int(h.get('rooms', 0)))
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
    tot = {k: sum(r[k] for r in results) for k in ('sent', 'recv', 'errors', 'failed', 'presence', 'reconnects', 'closed')}
    pct = lambda p: round(1000 * lat[min(len(lat) - 1, int(p * len(lat)))], 1) if lat else None
    steady = samples[2:] or samples
    report = dict(conns=args.conns, ramp_s=round(ramp, 1), duration_s=args.duration, chatters=chat_n, target_rate=args.rate,
                  sent=tot['sent'], deliveries=tot['recv'], rate_measured=round(tot['sent'] / max(1, args.duration), 2),
                  latency_ms=dict(p50=pct(.5), p95=pct(.95), p99=pct(.99), max=round(1000 * lat[-1], 1) if lat else None, n=len(lat)),
                  errors=tot['errors'], connect_failures=tot['failed'], reconnects=tot['reconnects'], presence_frames=tot['presence'],
                  live_cpu_pct=dict(avg=round(statistics.mean(steady), 1) if steady else None, peak=round(max(steady), 1) if steady else None),
                  live_rss_mb=round(peak_rss, 1), live_cpu_s_total=round((last[0] - cpu0), 1) if pid else None, health=health,
                  db='postgresql' if args.db_url else 'sqlite')
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
                               most_at_once=max(0, max_rooms - 1),   # rooms = Cả phố + one per date in progress
                               bench_wait_ms=ms('match'), answer_rtt_ms=ms('ack'), chat_rtt_ms=ms('say'),
                               date_length_s=round(statistics.median(lengths), 1) if lengths else None,
                               errors=sum(r['errors'] for r in dres), error_codes=codes, connect_failures=sum(r['failed'] for r in dres))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)   # the SQLite file and the service's log


if __name__ == '__main__':
    mp.set_start_method('spawn')
    main()
