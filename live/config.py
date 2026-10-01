"""Settings of the live service, from the environment (systemd: pg.env + live.env) and the command line.

| Variable | Default | Meaning |
|---|---|---|
| `LIVE_HOST`, `LIVE_PORT` | 127.0.0.1, 8770 | where it listens (nginx proxies `/live` here) |
| `LIVE_CHAT`, `LIVE_STREET`, `LIVE_DATING` | 0 | the switches of the three phases, sent to clients in `welcome.flags` |
| `LIVE_ORIGINS` | the local game | allowed `Origin` values, comma-separated (`https://phocochuyen.io.vn,...`) |
| `LIVE_TRUST_PROXY` | 0 | 1 behind nginx: the client IP is `X-Real-IP` (set by nginx), else the socket peer |
| `LIVE_MAX_CONN` | 5000 | open sockets at most; more are refused (503) |
| `LIVE_PER_PLAYER` | 5 | sockets per player (tabs); the oldest is closed for a new one |
| `LIVE_PER_IP` | 40 | sockets per IP |
| `LIVE_PG_POOL` | 8 | PostgreSQL connections at most (plus one for LISTEN) |
| `DATABASE_URL` | unset | PostgreSQL (production); without it `--db <sqlite file>` (dev, tests) |
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field


def _flag(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, '') or default)
    except ValueError:
        return default


@dataclass
class Config:
    host: str = '127.0.0.1'
    port: int = 8770
    path: str = '/live'
    chat: bool = False
    street: bool = False
    dating: bool = False
    origins: frozenset = frozenset({'http://localhost:8765', 'http://127.0.0.1:8765'})
    trust_proxy: bool = False
    max_conn: int = 5000
    per_player: int = 5
    per_ip: int = 40
    handshakes_per_ip: int = 60      # per minute
    db_url: str | None = None
    db_path: str | None = None       # SQLite (dev, tests)
    db_schema: str | None = None     # PostgreSQL search_path (tests)
    pool_max: int = 8
    max_frame: int = 4096            # bytes; bigger frames close the socket (1009)
    slow_bytes: int = 256 * 1024     # a client whose send buffer is over this is cut off
    idle_secs: float = 70.0          # no frame for this long (the client pings every 25 s): closed
    presence_grace: float = 12.0     # a reconnect within this does not flicker the green dot
    town_every: float = 10.0         # Cả phố slow mode: one message per player per 10 s (owner, 30/09)
    town_len: int = 300
    text_len: int = 1000             # DMs and groups
    new_secs: float = 600.0          # sessions younger than this read Cả phố but cannot post there yet
    buffer: int = 50                 # messages kept in memory per channel
    buffers_max: int = 2000          # channels with a buffer (LRU)
    group_max: int = 20              # members of a group, owner included
    flags_extra: dict = field(default_factory=dict)

    def flags(self) -> dict:
        return dict(chat=self.chat, street=self.street, dating=self.dating, **self.flags_extra)

    def any_on(self) -> bool:
        return self.chat or self.street or self.dating


def from_env(argv=None) -> Config:
    ap = argparse.ArgumentParser(prog='python3 -m live', description='Phố Có Chuyện live service (chat, presence)')
    ap.add_argument('--host', default=os.environ.get('LIVE_HOST', '127.0.0.1'))
    ap.add_argument('--port', type=int, default=_int('LIVE_PORT', 8770))
    ap.add_argument('--db', default=os.environ.get('GAME_DB'), help='SQLite game database (dev); ignored when DATABASE_URL is set')
    args = ap.parse_args(argv)
    url = (os.environ.get('DATABASE_URL') or '').strip() or None
    if url and not url.startswith(('postgresql://', 'postgres://')):
        raise SystemExit('[live] DATABASE_URL is set but is not a postgresql:// URL')
    origins = [o.strip().rstrip('/') for o in (os.environ.get('LIVE_ORIGINS') or '').split(',') if o.strip()]
    cfg = Config(host=args.host, port=args.port, chat=_flag('LIVE_CHAT'), street=_flag('LIVE_STREET'), dating=_flag('LIVE_DATING'),
                 trust_proxy=_flag('LIVE_TRUST_PROXY'), max_conn=_int('LIVE_MAX_CONN', 5000), per_player=_int('LIVE_PER_PLAYER', 5),
                 per_ip=_int('LIVE_PER_IP', 40), pool_max=max(1, _int('LIVE_PG_POOL', 8)), db_url=url,
                 db_path=None if url else (args.db or 'storage/game.sqlite3'))
    if origins:
        cfg.origins = frozenset(origins)
    return cfg
