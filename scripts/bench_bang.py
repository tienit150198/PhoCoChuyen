"""⚔️ Server timing of the Bang endpoints (game/bang.py get_view / post) on a realistic dataset (dev tool, a disposable
PostgreSQL through TEST_DATABASE_URL): a bang of 30 members (hall 5) and 15 others, 250 000 bang_points rows over 8
weeks, 60 000 log rows, 20 000 stints, 20 000 other saves and accounts. Prints, per endpoint, the median and worst ms,
the SQL statements and the BEGINs (a write) per call, the answer's size; then the launch-week case (NOWIN: nobody can
have won last week). JSON to argv[1] (optional). bang-smooth 21/10 numbers: CHANGELOG.md.

    TEST_DATABASE_URL=postgresql://… python scripts/bench_bang.py [out.json]
"""
import json, os, random, secrets, statistics, sys, tempfile, time  # noqa: E401
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import bang, promotion
from game import bang_content as C
from game import marriage as mr
from game import db as dbm
from game.storage import Store

QN = [0]
_real = dbm.PgConnection.execute
def counted(self, sql, params=(), **k):
    QN[0] += 1
    return _real(self, sql, params, **k)
dbm.PgConnection.execute = counted
TX = [0]
_begin = dbm.PgConnection.begin
def begin(self, *a, **k):
    TX[0] += 1
    return _begin(self, *a, **k)
dbm.PgConnection.begin = begin

tmp = tempfile.TemporaryDirectory()
store = Store(Path(tmp.name) / 's.db', story=True)
T = [time.time()]
patch.object(bang, 'now', lambda: T[0]).start()
from game import live_chat
patch.object(live_chat, 'notify', lambda db, e: None).start()
N = [0]

def player(name):
    token, _, _ = store.session()
    store.read(token)
    sid = store.key(token)
    def fn(s):
        s['name'] = name; s['journey']['wallet'] = 80_000_000
        promotion.record(s, 'milk_tea', True)['rank'] = 2
    mr._mutate(store, {sid: fn})
    login = secrets.token_hex(32)
    born = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 60 * 86400))
    with store.connect() as db:
        db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?, ?, ?, ?, ?)', ('u' + secrets.token_hex(5), name, 'x', sid, born))
        db.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'c')", (store.digest(login), sid))
    mr.ensure_person(store, sid)
    return login

def cmd(token, action, **p):
    N[0] += 1
    return store.command(token, f'bench-{N[0]:08d}-{os.getpid()}', store.read(token)[1], None, action, p)

def mine(token):
    with store.connect() as db:
        return bang._mine(db, store.key(token))

t0 = time.time()
print('seeding…', flush=True)
lead = player('Trùm')
cmd(lead, 'jr_bang_found', name='Rồng Đỏ', emoji='🐉', color='do', motto='Đoàn kết', open=True, confirm=True)
BID = mine(lead)['bang']
store.transaction(lambda db: db.execute("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'dai_sanh', 5) ON CONFLICT(bang, fac) DO UPDATE SET level=5", (BID,)))
store.transaction(lambda db: db.execute("UPDATE bangs SET fund=900000000 WHERE id=?", (BID,)))
for f in ('kho', 'den_vang', 'xuong_may', 'tuong', 'cong'):
    store.transaction(lambda db, f=f: db.execute("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, ?, 3) ON CONFLICT(bang, fac) DO UPDATE SET level=3", (BID, f)))
mem = []
for i in range(29):
    tk = player(f'Thành viên {i}')
    bang.post(store, tk, 'join', dict(bang=BID))
    mem.append(tk)
others = []
for b in range(15):
    tk = player(f'Trùm {b}')
    cmd(tk, 'jr_bang_found', name=f'Bang Số {b}', emoji='🐯', color='xanh' if 'xanh' in C.COLORS else 'do', motto='', open=True, confirm=True)
    others.append(tk)
    for i in range(4):
        bang.post(store, player(f'Lính {b}-{i}'), 'join', dict(bang=mine(tk)['bang']))
print('players done', round(time.time() - t0, 1), flush=True)
# bulk history: points (8 weeks), log, stints, fund; filler sessions
with store.connect() as db:
    bangs = [r['id'] for r in db.execute("SELECT id FROM bangs").fetchall()]
    sids = [r['sid'] for r in db.execute("SELECT sid, bang FROM bang_members WHERE status='in'").fetchall()]
    msid = {r['sid']: r['bang'] for r in db.execute("SELECT sid, bang FROM bang_members WHERE status='in'").fetchall()}
def bulk(db):
    rows = []
    now = T[0]
    for k in range(250_000):
        sid = random.choice(sids); b = msid[sid]
        at = now - random.random() * 56 * 86400
        rows.append((f'x:{k}', b, sid, random.choice(('give', 'checkin', 'work', 'buy')), random.randint(1, 50) * (1 if random.random() < .9 else -1),
                     bang.vn_week(at), bang.vn_day(at), at))
    db.executemany('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?)', rows)
    db.executemany('INSERT INTO bang_log(bang, sid, kind, text, at) VALUES(?,?,?,?,?)',
                   [(random.choice(bangs), '', 'join', 'Một ai đó vào bang và làm gì đó rất dài dòng.', now - random.random() * 30 * 86400) for _ in range(60_000)])
    db.executemany('INSERT INTO bang_stints(bang, sid, joined, left_at, why) VALUES(?,?,?,?,?)',
                   [(random.choice(bangs), random.choice(sids), now - 40 * 86400, now - 30 * 86400, 'leave') for _ in range(20_000)])
    db.executemany("INSERT INTO sessions(sid, csrf, state) VALUES(?, 'c', ?)", [(secrets.token_hex(32), '{"x":' + '1' * 2000 + '}') for _ in range(20_000)])
    db.executemany("INSERT INTO accounts(username, display, pw, sid) VALUES(?, ?, 'x', ?)", [('f' + secrets.token_hex(6), 'Filler', secrets.token_hex(32)) for _ in range(20_000)])
store.transaction(bulk)
with store.connect() as db:
    db.execute('ANALYZE')
print('seeded', round(time.time() - t0, 1), 's', flush=True)

RES = {}
def measure(label, fn, n=15, prep=None):
    ts, qs, xs = [], [], []
    for i in range(n):
        if prep: prep(i)
        q0 = QN[0]; x0 = TX[0]; a = time.perf_counter()
        try:
            out = fn(i)
        except bang.BangError as e:
            print('  !', label, e.code, e); out = None
        ts.append((time.perf_counter() - a) * 1000); qs.append(QN[0] - q0); xs.append(TX[0] - x0)
    RES[label] = (statistics.median(ts), max(ts), statistics.median(qs), len(json.dumps(out, ensure_ascii=False)) if out else 0, statistics.median(xs))
    print(f'{label:28s} median {RES[label][0]:7.1f} ms  max {RES[label][1]:7.1f}  queries {RES[label][2]:4.0f}  BEGINs {RES[label][4]:3.0f}  bytes {RES[label][3]}', flush=True)

def cold(i): bang._VIEW.clear()
g = lambda q: (lambda i: bang.get_view(store, lead, q))
measure('GET view (warm cache)', g({}))
measure('GET view (cold cache)', g({}), prep=cold)
measure('GET view member', lambda i: bang.get_view(store, mem[0], {}))
measure('GET ?q= search', g({'q': ''}), prep=cold)
measure('GET ?board=1', g({'board': '1'}), prep=cold)
measure('GET ?friends=1', g({'friends': '1'}))
measure('GET ?careers=1', g({'careers': '1'}))
measure('GET ?id= peek', lambda i: bang.get_view(store, others[0], {'id': BID}))
measure('GET ?found=1', lambda i: bang.get_view(store, others[0], {'found': '1'}))
measure('GET /me', lambda i: bang.me_view(store, lead))
# checkin: one per member per day
measure('POST checkin', lambda i: bang.post(store, mem[i], 'checkin', {}), n=15)
def reset_build(i):
    def run(db):
        db.execute("UPDATE bang_facilities SET target=NULL, ready_at=NULL WHERE bang=?", (BID,))
        db.execute("DELETE FROM bang_fund WHERE bang=? AND kind='build'", (BID,))   # bench database only
    store.transaction(run)
measure('POST build', lambda i: bang.post(store, lead, 'build', dict(fac='kho', confirm=True)), prep=reset_build)
store.transaction(lambda db: db.execute("UPDATE bang_members SET points=100000000 WHERE status='in'"))
measure('POST buy (phao)', lambda i: bang.post(store, lead, 'buy', dict(item='phao', rid='bench-' + secrets.token_hex(6))))
measure('POST wear', lambda i: bang.post(store, mem[1], 'wear', dict(item='ao', on=i % 2 == 0)), prep=lambda i: i == 0 and bang.post(store, mem[1], 'buy', dict(item='ao', rid='bench-ao-' + secrets.token_hex(4))))
pid = bang.pid_of(store.key(mem[2]))
measure('POST role', lambda i: bang.post(store, lead, 'role', dict(pid=pid, role='tinh' if i % 2 == 0 else 'tv')))
measure('POST kick', lambda i: bang.post(store, lead, 'kick', dict(pid=bang.pid_of(store.key(mem[10 + i])), confirm=True)), n=8)
measure('POST join (back)', lambda i: bang.post(store, mem[10 + i], 'join', dict(bang=BID)), n=8)
measure('POST set motto', lambda i: bang.post(store, lead, 'set', dict(motto=f'Đoàn kết {i}')))
# the launch week (production now): last week has no points, so no 👑 winner row
def nowin(db):
    db.execute('DELETE FROM bang_week_win')
    db.execute('DELETE FROM bang_points WHERE week=?', (bang.prev_week(T[0]),))
store.transaction(nowin)
bang._VIEW.clear()
measure('NOWIN GET view (warm)', g({}))
measure('NOWIN GET view (cold)', g({}), prep=cold)
measure('NOWIN GET ?q= search (cold)', g({'q': ''}), prep=cold)
measure('NOWIN POST role', lambda i: bang.post(store, lead, 'role', dict(pid=pid, role='tinh' if i % 2 == 0 else 'tv')))
measure('NOWIN POST wear', lambda i: bang.post(store, mem[1], 'wear', dict(item='ao', on=i % 2 == 0)))
json.dump(RES, open(sys.argv[1] if len(sys.argv) > 1 else '/dev/null', 'w'))
store.close_pool()
