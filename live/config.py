"""Settings of the live service, from the environment (systemd: pg.env + live.env) and the command line.

| Variable | Default | Meaning |
|---|---|---|
| `LIVE_HOST`, `LIVE_PORT` | 127.0.0.1, 8770 | where it listens (nginx proxies `/live` here) |
| `LIVE_CHAT`, `LIVE_STREET`, `LIVE_DATING` | 0 | the switches of the three phases, sent to clients in `welcome.flags` |
| `LIVE_WEDDING` | 0 | live wedding parties, the reminder and the weekly guest race (live/wedding.py) |
| `LIVE_FAIR` | as `LIVE_STREET` | players walking the hội chợ's fairground see each other (live/fair.py), and its photobooth's shared rooms (live/booth.py, welcome flag `booth`) |
| `LIVE_HOME` | as `LIVE_STREET` | married players in the same home see each other and share gestures (live/home.py) |
| `LIVE_TOWN` | 0 | real player presence on the shared 2.5D town map, independent of chat (live/town.py) |
| `LIVE_KARAOKE` | 0 | 🎤 Phòng hát: public karaoke rooms with a synced YouTube video, a queue, the stage and 🧩 Đoán bài (live/karaoke.py, welcome flag `kara`) |
| `LIVE_KARAOKE_MIC` | 0 | 🎙️ the stage singer's live mic in those rooms (welcome flag `kara_mic`; needs `LIVE_KARAOKE=1` and the four LIVEKIT_* below, else it stays off). The game server reads the same switch for its headers (server.py) |
| `LIVEKIT_URL` | unset | what browsers open for the mic (the SFU's signal URL, `wss://phocochuyen.io.vn/sfu`; deploy/livekit) |
| `LIVEKIT_API_URL` | http://127.0.0.1:7880 | the SFU's server API (create / delete rooms, remove a listener) |
| `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | unset | the SFU's key pair (`/etc/livekit/keys.yaml`); tokens are signed with it |
| `LIVE_DOG_BARK` | 0 | 🐕 Kéo co chó sủa: the lobby, matching and the tug-of-war (live/dog_bark.py, welcome flag `bark`). The game server reads the same switch (game/dog_bark.py: the command, the page's microphone header) |
| `LIVE_ORIGINS` | the local game | allowed `Origin` values, comma-separated (`https://phocochuyen.io.vn,...`) |
| `LIVE_TRUST_PROXY` | 0 | 1 behind nginx: the client IP is `X-Real-IP` (set by nginx), else the socket peer |
| `LIVE_MAX_CONN` | 5000 | open sockets at most; more are refused (503) |
| `LIVE_PER_PLAYER` | 5 | sockets per player (tabs); the oldest is closed for a new one |
| `LIVE_PER_IP` | 40 | sockets per IP |
| `LIVE_HANDSHAKES_PER_IP` | 60 | new sockets per IP per minute |
| `LIVE_PG_POOL` | 8 | PostgreSQL connections at most (plus one for LISTEN) |
| `LIVE_NEW_SECS` | 600 | sessions younger than this read Cả phố but cannot post there yet |
| `ADMIN_USERS` | unset | admin account usernames, comma-separated, any case (the game server's rule, game/player_feedback.py): they post on Cả phố without slow mode, wait, mute or masking, and pin a message there |
| `DATABASE_URL` | required | PostgreSQL connection URL |
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
    wedding: bool = False
    fair: bool = False               # 🏮 the fairground's crowd (live/fair.py); from_env: LIVE_FAIR, else as LIVE_STREET
    home: bool = False               # private presence in a verified shared home
    visits: bool = False             # workplace visits with persisted access checks
    town: bool = False               # 🏝️ shared 2.5D town map (live/town.py); explicitly LIVE_TOWN=1
    kara: bool = False               # 🎤 Phòng hát (live/karaoke.py); explicitly LIVE_KARAOKE=1, off by default
    kara_mic: bool = False           # 🎙️ its live mic (LIVE_KARAOKE_MIC=1 and the SFU configured); off by default
    bark: bool = False               # 🐕 Kéo co chó sủa (live/dog_bark.py); LIVE_DOG_BARK=1, off by default
    sfu_url: str = ''                # LIVEKIT_URL: the signal URL browsers open
    sfu_api: str = 'http://127.0.0.1:7880'
    sfu_key: str = ''
    sfu_secret: str = ''
    origins: frozenset = frozenset({'http://localhost:8765', 'http://127.0.0.1:8765'})
    trust_proxy: bool = False
    max_conn: int = 5000
    per_player: int = 5
    per_ip: int = 40
    handshakes_per_ip: int = 60      # per minute
    db_url: str | None = None
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
    admins: frozenset = frozenset()  # ADMIN_USERS, lower case: post freely on Cả phố and pin a message there (owner, 01/10)
    admin_len: int = 500             # an admin's Cả phố message: 500 characters, 6 lines
    admin_lines: int = 6
    buffer: int = 50                 # messages kept in memory per channel
    buffers_max: int = 2000          # channels with a buffer (LRU)
    group_max: int = 20              # members of a group, owner included
    flags_extra: dict = field(default_factory=dict)

    def flags(self) -> dict:
        return dict(chat=self.chat, street=self.street, dating=self.dating, wedding=self.wedding, fair=self.fair, home=self.home, visits=self.visits, town=self.town, kara=self.kara,
                    kara_mic=self.kara and self.kara_mic, bark=self.bark, **self.flags_extra)

    def any_on(self) -> bool:
        return self.chat or self.street or self.dating or self.wedding or self.fair or self.home or self.visits or self.town or self.kara or self.bark


def admin_users(raw: str | None = None) -> frozenset:
    """ADMIN_USERS as game/player_feedback.py admin_users() reads it: comma-separated, trimmed, lower case."""
    raw = os.environ.get('ADMIN_USERS', '') if raw is None else raw
    return frozenset(u.strip().lower() for u in raw.split(',') if u.strip())


def from_env(argv=None) -> Config:
    ap = argparse.ArgumentParser(prog='python3 -m live', description='Phố Có Chuyện live service (chat, presence)')
    ap.add_argument('--host', default=os.environ.get('LIVE_HOST', '127.0.0.1'))
    ap.add_argument('--port', type=int, default=_int('LIVE_PORT', 8770))
    ap.add_argument('--schema', help='PostgreSQL schema for the live service search_path')
    args = ap.parse_args(argv)
    url = (os.environ.get('DATABASE_URL') or '').strip() or None
    if not url or not url.startswith(('postgresql://', 'postgres://')):
        raise SystemExit('[live] DATABASE_URL is required and must be a postgresql:// URL')
    origins = [o.strip().rstrip('/') for o in (os.environ.get('LIVE_ORIGINS') or '').split(',') if o.strip()]
    street = _flag('LIVE_STREET')
    cfg = Config(host=args.host, port=args.port, chat=_flag('LIVE_CHAT'), street=street, dating=_flag('LIVE_DATING'), wedding=_flag('LIVE_WEDDING'),
                 fair=_flag('LIVE_FAIR', '1' if street else '0'),
                 home=_flag('LIVE_HOME', '1' if street else '0'),
                 visits=_flag('LIVE_VISITS', '1' if street else '0'),
                 town=_flag('LIVE_TOWN'), kara=_flag('LIVE_KARAOKE'), bark=_flag('LIVE_DOG_BARK'),
                 trust_proxy=_flag('LIVE_TRUST_PROXY'), max_conn=_int('LIVE_MAX_CONN', 5000), per_player=_int('LIVE_PER_PLAYER', 5),
                 per_ip=_int('LIVE_PER_IP', 40), pool_max=max(1, _int('LIVE_PG_POOL', 8)), db_url=url, new_secs=float(_int('LIVE_NEW_SECS', 600)),
                 handshakes_per_ip=_int('LIVE_HANDSHAKES_PER_IP', 60), admins=admin_users(), db_schema=args.schema)
    if origins:
        cfg.origins = frozenset(origins)
    cfg.sfu_url = (os.environ.get('LIVEKIT_URL') or '').strip()
    cfg.sfu_api = (os.environ.get('LIVEKIT_API_URL') or '').strip() or cfg.sfu_api
    cfg.sfu_key = (os.environ.get('LIVEKIT_API_KEY') or '').strip()
    cfg.sfu_secret = (os.environ.get('LIVEKIT_API_SECRET') or '').strip()
    want = _flag('LIVE_KARAOKE_MIC')
    cfg.kara_mic = want and cfg.kara and bool(cfg.sfu_url and cfg.sfu_key and cfg.sfu_secret)
    if want and not cfg.kara_mic:
        print('[live] LIVE_KARAOKE_MIC=1 ignored: needs LIVE_KARAOKE=1, LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET', flush=True)
    return cfg
