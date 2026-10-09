"""🐕 Kéo co chó sủa (owner 10/10): a tug-of-war won by barking into the microphone. A standalone activity (not part of
the Chợ đen: no fair police, no Lộc trời cho, no fair board), with its own entry beside Phòng hát. Switch LIVE_DOG_BARK
(both servers read it: this module for the command and the page's microphone header, live/config.py for the socket).

How a match runs
* The player picks a stake (MIN_STAKE .. the wallet; STAKE_MAX only keeps a payout inside one Sổ ví row) and taps
  "Tìm đối thủ": the command `jr_bark_join {stake}` takes the stake from the wallet (escrow) and command_commit writes
  the ticket row (`bark_tickets`, status 'wait') in the same transaction, after the rules that need the database: an
  account with a birth year (account_birth, game/karaoke_mic.py) of someone MIN_AGE or older, no other open ticket,
  today's caps (MATCH_DAY, JOIN_DAY), the win-streak cool-down (STREAK wins in a row: COOL_S). Any refusal rolls the
  whole command back: nothing is taken.
* The live service (live/dog_bark.py) matches waiting tickets of the same stake at random, never two players from the
  same IP (a salted hash, in memory only) and never the same two players more than PAIR_MAX matches in a row
  (PairBook). After DOG_AFTER seconds without a human, the match starts against the house dog ("🐕 Chó nhà Mây · Mực"),
  clearly labelled, never shown as a player, while today's dog caps allow it (DOG_DAY matches, DOG_WIN_DAY net xu won).
* The match: a rope with a marker in the middle (Rope). Each side's level is the mean of its loudness samples of the
  last WINDOW seconds (Voice: 0..100, clamped, at most RATE_MAX a second, a flat run of identical values counts as
  silence); every TICK the marker moves K × (level A − level B). An end wins; at MATCH_S the side the marker is on wins,
  the middle (|x| < DRAW_BAND) is a draw. A player whose page is gone for more than GONE_S, or who quits, loses.
* The house dog (HouseDog): a random breed and name each match, and a pull that follows the player's own level times a
  strength that wanders (a base drawn per match, bursts, pauses, a second wind or a tired spell): truly random, about
  50/50 over time for a player who barks, never a fixed script. A quiet player loses (the dog barks on its own).
* Money: only the live service settles, once per ticket: the ticket flips 'play'/'dog' -> 'done' under a guarded
  UPDATE, and its one payout row `live_effects` 'bark:<ticket>' (kind 'bark') is inserted in the same transaction. The
  game server pays it like an auction refund (game/live_effects.py, fx_commit flips the row in the save's own
  transaction). Win: both stakes (the system pays the pot, FEE_PCT 0). Draw, cancel, a lost live service: the stake
  back. Loss: nothing (the stake is gone: to the winner, or burned against the dog).
* Housekeeping (server.py, every 30 s): a ticket still waiting after WAIT_MAX or in a match after STUCK_MAX (the live
  service restarted) is refunded, under the same guarded UPDATE.

No save key: the stake leaves the wallet with a Sổ ví row and comes back through live_effects. An older build ignores
the 'bark' rows (they stay pending until a build that knows them loads the save) and never sees the table.
Table: bark_tickets (game/pg_schema.py, SCHEMA_VERSION 34).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import random
import re
import secrets
import threading
import time
from collections import OrderedDict, deque

COMMANDS = ('jr_bark_join',)
FX = 'bark'                        # live_effects kind
KIND = 'life'                      # wallet history kind (journey.HISTORY_KINDS): every build knows it
LABEL = '🐕 Kéo co chó sủa'
HOUSE = 'Chó nhà Mây'              # the house dog's tag: "🐕 Chó nhà Mây · Mực"
MIN_STAKE = 100
STAKE_MAX = 5_000_000              # a win pays 2× in one Sổ ví row, which every validator keeps within 10**7
FEE_PCT = 0                        # owner: "win thì hệ thống trả lại": the winner gets both stakes
MIN_AGE = 16
# the day's caps (Vietnam day)
MATCH_DAY = 60                     # matches started (any opponent)
JOIN_DAY = 200                     # tickets opened, cancelled ones too (join/cancel spam)
DOG_DAY = 20                       # matches against the house dog
DOG_WIN_DAY = 5_000                # net xu won against the house dog; a dog match's stake fits what is left of it
# the win-streak rule (like Ông Hai's table, without the police): STREAK wins in a row, then COOL_S seconds off
STREAK, COOL_S = 4, 900
# matching
DOG_AFTER = 20.0                   # seconds without a human before the house dog steps in
WAIT_LIVE = 180.0                  # the live service gives a ticket back after this long without any match
PAIR_MAX, PAIR_COOL = 3, 7200      # the same two players at most 3 matches in a row; forgotten after 2 h
# the match
TICK = 0.1                         # seconds per physics step (10 Hz)
MATCH_S = 45.0
END = 100.0                        # the marker runs in [-END, END]; +END is side A's end
K = 0.05                           # marker units per tick per point of level difference
DRAW_BAND = 1.0
WINDOW = 0.5                       # seconds of samples a level averages
RATE_MAX = 16                      # samples a second at most (more are ignored)
BATCH_MAX = 6                      # samples in one frame
FLAT_RUN = 30                      # this many identical non-zero samples in a row count as silence (not a voice)
QUIET = 8.0                        # a level under this is silence
GONE_S = 10.0                      # a player whose page is gone this long loses
PULL_MAX = 150.0                   # the dog's pull may pass 100 (a player pinned at 100 can still lose)
# housekeeping (game server)
WAIT_MAX = 300.0
STUCK_MAX = 600.0
TICKET_RE = re.compile(r'k[0-9a-f]{20}')
VN = datetime.timezone(datetime.timedelta(hours=7))
DAY = 86400
OPEN = ('wait', 'play', 'dog')

# 🐕 The house dog: breeds (id, name, emoji, the bark samples public/audio/bark/*.mp3, playback rate range, size)
BREEDS = (
    ('cho_ta', 'Chó ta', '🐕', ('a', 'c', 'd'), (0.9, 1.1), 'm'),
    ('phu_quoc', 'Phú Quốc', '🐕', ('a', 'd', 'e'), (0.95, 1.12), 'm'),
    ('corgi', 'Corgi', '🐕', ('b', 'e', 'f'), (1.05, 1.25), 's'),
    ('shiba', 'Shiba', '🐕', ('c', 'e', 'b'), (1.0, 1.18), 'm'),
    ('husky', 'Husky', '🐺', ('a', 'c'), (0.8, 0.95), 'l'),
    ('golden', 'Golden', '🦮', ('a', 'd'), (0.82, 0.98), 'l'),
    ('becgie', 'Béc-giê', '🐕‍🦺', ('c', 'a'), (0.72, 0.88), 'l'),
    ('pom', 'Phốc sóc', '🐩', ('g', 'f', 'b'), (1.2, 1.45), 's'),
    ('chihuahua', 'Chihuahua', '🐕', ('g', 'f'), (1.3, 1.55), 's'),
    ('lap_xuong', 'Lạp xưởng', '🌭', ('b', 'f', 'e'), (1.1, 1.3), 's'),
    ('poodle', 'Poodle', '🐩', ('f', 'b', 'g'), (1.15, 1.35), 's'),
    ('bac_ha', 'Bắc Hà', '🐕', ('d', 'a', 'c'), (0.85, 1.0), 'l'),
)
NAMES = ('Mực', 'Vàng', 'Vện', 'Lu', 'Lu Lu', 'Bông', 'Ki', 'Ki Ki', 'Bơ', 'Mít', 'Na', 'Đốm', 'Cún', 'Bin', 'Bi', 'Milo', 'Tôm',
         'Ớt', 'Gấu', 'Sữa', 'Mochi', 'Kem', 'Chè', 'Xôi', 'Tiêu', 'Muối', 'Bắp', 'Khoai', 'Mận', 'Đậu', 'Su Su', 'Cốm', 'Bánh Bao',
         'Sóc', 'Bột', 'Than', 'Lạc', 'Nắng', 'Bé Na', 'Cà Rốt', 'Mè', 'Nếp', 'Tofu', 'Pín', 'Lì', 'Cáo', 'Mướp', 'Bon', 'Chíp',
         'Gạo', 'Phở', 'Bún', 'Rô', 'Tũn', 'Ú', 'Mỡ', 'Bánh Mì', 'Kẹo', 'Sún', 'Bầu')

_rng = random.SystemRandom()       # tests replace it with a seeded random.Random


def now() -> float:
    return time.time()


def enabled() -> bool:
    """The switch, as the game server sees it (the command, the page's microphone header, the routes)."""
    return os.environ.get('LIVE_DOG_BARK', '0').strip().lower() in ('1', 'true', 'yes', 'on')


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _core():
    from . import engine
    return engine


def vn_day_start(t: float | None = None) -> float:
    d = datetime.datetime.fromtimestamp(now() if t is None else t, VN).date()
    return datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()


def week_start(t: float | None = None) -> float:
    """Monday 00:00 Vietnam time of the week of t."""
    t = now() if t is None else t
    d = datetime.datetime.fromtimestamp(t, VN).date()
    d -= datetime.timedelta(days=d.weekday())
    return datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()


def pot(stake: int) -> int:
    """What the winner of a match between humans gets: both stakes, less FEE_PCT."""
    return 2 * stake - (2 * stake * FEE_PCT) // 100


# ---------------------------------------------------------------- the voice (pure)
class Voice:
    """One side's loudness: samples 0..100 (clamped), at most RATE_MAX a second, the mean of the last WINDOW seconds."""

    def __init__(self):
        self.s: deque = deque(maxlen=64)
        self.sec: deque = deque()
        self.last = None
        self.run = 0
        self.n = 0                     # samples accepted (for the dog's "lazy" factor)
        self.sum = 0.0

    @staticmethod
    def clamp(v) -> float | None:
        if type(v) not in (int, float) or v != v or v in (float('inf'), float('-inf')):
            return None
        return max(0.0, min(100.0, float(v)))

    def add(self, vals, t: float) -> int:
        """Samples of one frame, received at t. Returns how many were kept."""
        if not isinstance(vals, list):
            return 0
        kept = 0
        while self.sec and self.sec[0] <= t - 1.0:
            self.sec.popleft()
        for raw in vals[:BATCH_MAX]:
            v = self.clamp(raw)
            if v is None:
                continue
            if len(self.sec) >= RATE_MAX:
                break
            self.sec.append(t)
            v = round(v, 1)
            self.run = self.run + 1 if v == self.last else 1
            self.last = v
            if self.run >= FLAT_RUN and v > 0:   # a held identical number is not a voice
                v = 0.0
            self.s.append((t, v))
            self.n += 1
            self.sum += v
            kept += 1
        return kept

    def level(self, t: float) -> float:
        vals = [v for at, v in self.s if t - at <= WINDOW]
        return sum(vals) / len(vals) if vals else 0.0

    def mean(self) -> float:
        return self.sum / self.n if self.n else 0.0


# ---------------------------------------------------------------- the rope (pure)
class Rope:
    """The marker: x in [-END, END]; +END is side A's end. step() returns 'a', 'b', 'draw' or None (going on)."""

    def __init__(self, limit: float | None = None):
        self.x, self.t, self.limit = 0.0, 0.0, MATCH_S if limit is None else limit

    def step(self, a: float, b: float) -> str | None:
        self.x = max(-END, min(END, self.x + K * (a - b)))
        self.t += TICK
        if self.x >= END:
            return 'a'
        if self.x <= -END:
            return 'b'
        if self.t >= self.limit - 1e-9:
            return 'a' if self.x >= DRAW_BAND else 'b' if self.x <= -DRAW_BAND else 'draw'
        return None


# ---------------------------------------------------------------- the house dog (pure)
DOG_BASE = (0.875, 1.135)          # the strength drawn per match, relative to the player's own level (scripts: ~49-50% won)
IDLE = (22.0, 34.0)                # the dog's own bark while the player is quiet


class HouseDog:
    """"🐕 Chó nhà Mây": a random breed and name each match, a pull that wanders around the player's own level."""

    def __init__(self, rng: random.Random, avoid: tuple = ()):
        names = [n for n in NAMES if n not in avoid] or list(NAMES)
        self.rng = rng
        self.name = rng.choice(names)
        self.breed = rng.choice(BREEDS)
        self.base = rng.uniform(*DOG_BASE)
        self.idle = rng.uniform(*IDLE)
        self.seed = rng.getrandbits(31)
        self.state, self.left, self.m = 'steady', rng.uniform(1.0, 3.0), self.base
        self.late = False
        self.t = 0.0

    def view(self) -> dict:
        b = self.breed
        return dict(house=True, tag=HOUSE, name=self.name, breed=b[0], kind=b[1], emoji=b[2], barks=list(b[3]),
                    rate=list(b[4]), size=b[5], seed=self.seed)

    def _next(self) -> None:
        r, base = self.rng, self.base
        if not self.late and self.t >= 0.6 * MATCH_S:   # once, late: a second wind or a tired spell (as likely)
            self.late = True
            if r.random() < 0.5:
                self.state, self.left, self.m = 'wind', r.uniform(2.0, 3.5), base * r.uniform(1.2, 1.35)
            else:
                self.state, self.left, self.m = 'tired', r.uniform(2.0, 3.5), base * r.uniform(0.68, 0.8)
            return
        x = r.random()
        if x < 0.45:
            self.state, self.left, self.m = 'steady', r.uniform(1.5, 4.0), base * r.uniform(0.96, 1.04)
        elif x < 0.75:
            self.state, self.left, self.m = 'burst', r.uniform(0.6, 1.8), base * r.uniform(1.15, 1.35)
        else:
            self.state, self.left, self.m = 'pause', r.uniform(0.4, 1.4), base * r.uniform(0.45, 0.7)

    def pull(self, p: float, mean: float = 50.0) -> float:
        """The dog's pull this tick, the player's level being p (mean: the player's average so far)."""
        self.t += TICK
        self.left -= TICK
        if self.left <= 0:
            self._next()
        jitter = 1.0 + self.rng.uniform(-0.06, 0.06)
        if p < QUIET:   # the player is quiet: the dog barks on its own, in its rhythm
            return max(0.0, self.idle * min(1.4, self.m) * jitter)
        lazy = 1.0 + max(0.0, min(0.3, (30.0 - mean) / 100.0))   # a lazy bark (a whole match under 30) tires the rope
        return max(0.0, min(PULL_MAX, self.m * lazy * p * jitter))

    def shown(self, pull: float) -> float:
        return min(100.0, pull)


def simulate(rng: random.Random, voice, seconds: float | None = None) -> str:
    """One match against the house dog with a scripted player: voice(t, rng) -> level. 'a' the player wins, 'b' the dog,
    'draw'. For the tests and scripts (the long-run odds)."""
    dog = HouseDog(rng)
    rope = Rope(seconds)
    total, n = 0.0, 0
    while True:
        t = rope.t
        p = max(0.0, min(100.0, voice(t, rng)))
        total += p
        n += 1
        out = rope.step(p, dog.pull(p, total / n))
        if out:
            return out


# ---------------------------------------------------------------- the pairs (pure; the live service's memory)
class PairBook:
    """The same two players at most PAIR_MAX matches in a row. A pair is forgotten once both have played someone else
    (a human) since, or PAIR_COOL seconds after its last match. Bounded (cap pairs, least recent out first)."""

    def __init__(self, cap: int = 50000):
        self.d: OrderedDict = OrderedDict()   # (a, b) sorted -> {n, at, moved: set}
        self.by: dict = {}                    # sid -> set of pair keys
        self.cap = cap

    @staticmethod
    def key(a: str, b: str) -> tuple:
        return (a, b) if a <= b else (b, a)

    def _drop(self, k: tuple) -> None:
        self.d.pop(k, None)
        for s in k:
            ks = self.by.get(s)
            if ks is not None:
                ks.discard(k)
                if not ks:
                    self.by.pop(s, None)

    def count(self, a: str, b: str, t: float) -> int:
        k = self.key(a, b)
        e = self.d.get(k)
        if e and t - e['at'] >= PAIR_COOL:
            self._drop(k)
            return 0
        return e['n'] if e else 0

    def ok(self, a: str, b: str, t: float) -> bool:
        return self.count(a, b, t) < PAIR_MAX

    def played(self, a: str, b: str | None, t: float) -> None:
        """a played b (None: the house dog, which resets nothing)."""
        if b is None:
            return
        k = self.key(a, b)
        n = self.count(a, b, t)
        for s in (a, b):   # every other pair of a and b: that player played someone else
            for o in list(self.by.get(s, ())):
                if o == k:
                    continue
                e = self.d.get(o)
                if e is None:
                    continue
                e['moved'].add(s)
                if e['moved'] >= set(o):
                    self._drop(o)
        self.d[k] = dict(n=n + 1, at=t, moved=set())
        self.d.move_to_end(k)
        for s in k:
            self.by.setdefault(s, set()).add(k)
        while len(self.d) > self.cap:
            self._drop(next(iter(self.d)))


def ip_hash(salt: bytes, ip: str) -> str:
    """A salted hash of the request IP (the live service keeps it in memory only, never in a save or a log)."""
    return hashlib.sha256(salt + str(ip).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- the command (the save)
def new_ticket() -> str:
    return 'k' + secrets.token_hex(10)


def action(s: dict, name: str, p: dict) -> dict:
    """`jr_bark_join {stake}`: the stake leaves the wallet (escrow); command_commit writes the ticket."""
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Kéo co chó sủa chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(enabled(), 'Kéo co chó sủa đang tạm nghỉ.', 'bark_off')
    need(isinstance(p, dict) and set(p) == {'stake'}, 'Thông tin không hợp lệ.')
    stake = p['stake']
    need(type(stake) is int and MIN_STAKE <= stake, f'Cược ít nhất {fmt(MIN_STAKE)} xu nha.', 'bark_stake')
    need(stake <= STAKE_MAX, f'Cược tối đa {fmt(STAKE_MAX)} xu một kèo.', 'bark_stake')
    need(j['wallet'] >= stake, 'Ví không đủ cho kèo này.', 'not_enough')
    ticket = new_ticket()
    from . import journey as jr
    jr._wallet(j, -stake, KIND, f'{LABEL} · đặt cược')
    return dict(message=f'🐕 Đã đặt {fmt(stake)} xu. Đang tìm đối thủ…', bark=dict(ticket=ticket, stake=stake))


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'bark' live_effects row paid into the save (game/live_effects.py apply): a win, a draw's or a cancel's stake."""
    e = _core()
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    what, ticket = data.get('what'), data.get('ticket')
    e.need(what in ('win', 'draw', 'back') and isinstance(ticket, str) and TICKET_RE.fullmatch(ticket), 'Dữ liệu kéo co không hợp lệ.')
    from . import journey as jr
    j = s['journey']
    label = {'win': 'thắng kèo', 'draw': 'hòa, trả cược', 'back': 'trả lại cược'}[what]
    jr._wallet(j, amount, KIND, f'{LABEL} · {label}')
    if what == 'win':
        return f'🐕 Thắng kèo kéo co! +{fmt(amount)} xu vào ví.'
    return f'🐕 {fmt(amount)} xu cược đã về ví.'


def fx_commit(db, sid: str, result) -> None:
    """live_fx of a 'bark' row, in the save's transaction: the row flips pending → applied here, once (a GameError rolls
    the payment back)."""
    live = (result or {}).get('live') if isinstance(result, dict) else None
    if not isinstance(live, dict) or live.get('kind') != FX or live.get('already'):
        return
    _core().need(db.execute("UPDATE live_effects SET status='applied', applied_at=? WHERE id=? AND sid=? AND status='pending'",
                            (now(), live.get('id'), sid)).rowcount == 1, 'Khoản này đã xử lý rồi.', 'bark_sync')


# ---------------------------------------------------------------- the database rules (shared with the live service)
def age_ok(year, t: float | None = None) -> bool:
    from .karaoke_mic import vn_year, YEAR_MIN
    return type(year) is int and YEAR_MIN <= year and vn_year(t) - year - 1 >= MIN_AGE


def who_why(row) -> tuple[str, str]:
    """(code, reason) for an accounts ⟕ account_birth row (None: no account); ('', '') when the player may play."""
    if not row:
        return 'bark_account', 'Kéo co chó sủa cần tài khoản đã đăng ký.'
    if row['year'] is None:
        return 'bark_birth', 'Cho biết năm sinh trước khi bật mic nha.'
    if not age_ok(int(row['year'])):
        return 'bark_young', f'Kéo co bằng mic dành cho bạn từ {MIN_AGE} tuổi nha.'
    return '', ''


WHO_SQL = 'SELECT a.created_at, b.year FROM accounts a LEFT JOIN account_birth b ON b.sid=a.sid WHERE a.sid=?'
TODAY_SQL = ("SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN status<>'back' THEN 1 ELSE 0 END), 0) AS played, "
             "COALESCE(SUM(CASE WHEN opp='dog' AND status<>'back' THEN 1 ELSE 0 END), 0) AS dog_n, "
             "COALESCE(SUM(CASE WHEN opp='dog' AND status='done' THEN pay-stake ELSE 0 END), 0) AS dog_net "
             "FROM bark_tickets WHERE sid=? AND created>=?")
LAST_SQL = "SELECT result, ended FROM bark_tickets WHERE sid=? AND status='done' AND result<>'' ORDER BY ended DESC LIMIT ?"


def cool_left(rows: list, t: float) -> int:
    """Seconds of the win-streak cool-down left, from the player's last decided matches (newest first)."""
    if len(rows) < STREAK or any(r['result'] != 'win' for r in rows[:STREAK]):
        return 0
    return max(0, int(float(rows[0]['ended'] or 0) + COOL_S - t))


def dog_room(today: dict) -> int:
    """The biggest stake the house dog takes today (0: none: DOG_DAY matches played, or DOG_WIN_DAY won)."""
    if int(today['dog_n']) >= DOG_DAY:
        return 0
    return max(0, DOG_WIN_DAY - max(0, int(today['dog_net'])))


def command_commit(db, sid: str, action: str, result) -> None:
    """jr_bark_join in the save's transaction (game/storage.py): the rules that need the database, then the ticket row.
    A GameError rolls the whole command back (the stake never left)."""
    if action not in COMMANDS:
        return
    e = _core()
    need = e.need
    r = (result or {}).get('bark') if isinstance(result, dict) else None
    if not isinstance(r, dict) or not r.get('ticket'):
        return
    t = now()
    code, why = who_why(db.execute(WHO_SQL, (sid,)).fetchone())
    need(not code, why, code or 'bark')
    need(db.execute("SELECT 1 FROM bark_tickets WHERE sid=? AND status IN ('wait','play','dog') LIMIT 1", (sid,)).fetchone() is None,
         'Bạn đang có một kèo rồi, chơi xong kèo đó nha.', 'bark_open')
    today = dict(db.execute(TODAY_SQL, (sid, vn_day_start(t))).fetchone())
    need(int(today['played']) < MATCH_DAY, f'Hôm nay kéo {MATCH_DAY} kèo rồi, mai sủa tiếp nha 🐕', 'bark_day')
    need(int(today['n']) < JOIN_DAY, 'Hôm nay đặt rồi hủy nhiều quá, mai quay lại nha.', 'bark_day')
    left = cool_left([dict(x) for x in db.execute(LAST_SQL, (sid, STREAK)).fetchall()], t)
    need(not left, f'Thắng liền {STREAK} kèo rồi! Cho cổ họng nghỉ {max(1, -(-left // 60))} phút nha 🐕', 'bark_cool')
    db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created) VALUES(?,?,?,'wait',?)", (r['ticket'], sid, int(r['stake']), t))
    from . import live_chat
    live_chat.notify(db, dict(op='bark_ticket'))   # the live service looks at its queue now (the page also tells it)


def refund_rows(db, rows, t: float, why: str) -> int:
    """Give these tickets' stakes back ('back'), each once: the guarded UPDATE, then its one payout row."""
    n = 0
    for x in rows:
        if db.execute("UPDATE bark_tickets SET status='back', result='', ended=?, pay=stake WHERE id=? AND status=?",
                      (t, x['id'], x['status'])).rowcount != 1:
            continue
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT DO NOTHING",
                   (f'bark:{x["id"]}', x['sid'], FX, int(x['stake']), json.dumps(dict(ticket=x['id'], what='back', why=why, src='bark')), t))
        n += 1
    return n


def cancel(store, token: str, d: dict) -> dict:
    """POST /api/dogbark/cancel {ticket}: give a waiting ticket back (the page when the live socket is down)."""
    from .social import SocialError
    ticket = (d or {}).get('ticket')
    if not (isinstance(ticket, str) and TICKET_RE.fullmatch(ticket)):
        raise SocialError('Không có kèo này.', 'bad_ticket')
    sid = store.key(token)
    t = now()

    def run(db):
        rows = [dict(x) for x in db.execute("SELECT id, sid, stake, status FROM bark_tickets WHERE id=? AND sid=? AND status='wait' FOR UPDATE",
                                            (ticket, sid)).fetchall()]
        return refund_rows(db, rows, t, 'cancel')
    return dict(ok=True, back=bool(store.transaction(run)))


def housekeeping(store, t: float | None = None) -> int:
    """Refund tickets left waiting (WAIT_MAX) or stuck in a match (STUCK_MAX: the live service restarted). Idempotent."""
    t = now() if t is None else t

    def run(db):
        rows = [dict(x) for x in db.execute(
            "SELECT id, sid, stake, status FROM bark_tickets WHERE (status='wait' AND created<?) OR (status IN ('play','dog') AND started<?) "
            'ORDER BY created LIMIT 200 FOR UPDATE SKIP LOCKED', (t - WAIT_MAX, t - STUCK_MAX)).fetchall()]
        return refund_rows(db, rows, t, 'stale')
    return store.transaction(run)


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s). Never raises."""
    import sys
    if not enabled():
        return
    try:
        n = housekeeping(store)
        if n:
            sys.stderr.write(f'[dog_bark] refunded {n} stale tickets\n')
    except Exception as e:  # noqa: BLE001 - housekeeping never takes the server down
        sys.stderr.write(f'[dog_bark] housekeeping: {type(e).__name__}\n')


# ---------------------------------------------------------------- the page (GET /api/dogbark)
_KING: dict = {}
_KING_LOCK = threading.Lock()
KING_SECS = 60


def king(store, t: float | None = None) -> dict | None:
    """🐕 Vua sủa: this week's biggest net winner (humans and the dog), its display name and xu. Cached KING_SECS."""
    t = now() if t is None else t
    wk = week_start(t)
    with _KING_LOCK:
        hit = _KING.get('k')
        if hit and hit[0] == wk and time.monotonic() - hit[1] < KING_SECS:
            return hit[2]
    out = None
    with store.connect() as db:
        r = db.execute("SELECT sid, SUM(pay-stake) AS net FROM bark_tickets WHERE status='done' AND ended>=? AND sid<>'' "
                       'GROUP BY sid HAVING SUM(pay-stake)>0 ORDER BY net DESC, sid LIMIT 1', (wk,)).fetchone()
        if r:
            a = db.execute('SELECT display FROM accounts WHERE sid=?', (r['sid'],)).fetchone()
            name = str(a['display'])[:24] if a and a['display'] else ''
            from .accounts import offensive_name
            out = dict(name='' if offensive_name(name) else name, xu=int(r['net']), title='🐕 Vua sủa')
    with _KING_LOCK:
        _KING.clear()
        _KING['k'] = (wk, time.monotonic(), out)
    return out


def view(store, token: str | None) -> dict:
    """The lobby's numbers for this player: can they play (account, birth year, age), today's caps, the cool-down, an
    open ticket, the house dog's room, and the week's Vua sủa."""
    t = now()
    out = dict(on=enabled(), min=MIN_STAKE, max=STAKE_MAX, match_s=MATCH_S, dog_after=DOG_AFTER, house=HOUSE,
               caps=dict(day=MATCH_DAY, dog=DOG_DAY, dog_win=DOG_WIN_DAY, streak=STREAK, cool=COOL_S))
    try:
        housekeeping(store, t)
    except Exception:  # noqa: BLE001 - a page never fails because of the housekeeping
        pass
    try:
        out['king'] = king(store, t)
    except Exception:  # noqa: BLE001
        out['king'] = None
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    if not sid:
        return out
    with store.connect() as db:
        code, why = who_why(db.execute(WHO_SQL, (sid,)).fetchone())
        today = dict(db.execute(TODAY_SQL, (sid, vn_day_start(t))).fetchone())
        left = cool_left([dict(x) for x in db.execute(LAST_SQL, (sid, STREAK)).fetchall()], t)
        o = db.execute("SELECT id, stake, status, created FROM bark_tickets WHERE sid=? AND status IN ('wait','play','dog') "
                       'ORDER BY created DESC LIMIT 1', (sid,)).fetchone()
    out['me'] = dict(code=code, why=why, played=int(today['played']), dog_n=int(today['dog_n']), dog_net=int(today['dog_net']),
                     dog_room=dog_room(today), cool=left,
                     open=dict(ticket=o['id'], stake=int(o['stake']), status=o['status'], at=float(o['created'])) if o else None)
    return out


def forget(db, sid: str) -> None:
    """A player erased their data: their tickets go (their escrow went with the save)."""
    db.execute('DELETE FROM bark_tickets WHERE sid=?', (sid,))
