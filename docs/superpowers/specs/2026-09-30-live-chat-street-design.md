# Live: chat, online presence, strolling the phố, dates (design, 30/09/2026)

Owner request (30/09): 1) chat: private with friends, a server-wide channel, groups; 2) "đi dạo khu phố":
online players stroll a place together, can join "bạn muốn hẹn hò?" to be matched for an in-game date, or just
talk. Only players who are online can do these. "Hẹn hò" is an in-game date, not real dating: open to everyone.
Approved: a separate live service over **WebSocket**, built in three phases. Each phase ships quietly behind a
switch; a "Có gì mới" note only when the owner says so.

## Goals and non-goals

- Messages and moves feel instant (< 300 ms on 4G), and the game server gets **no extra load**: the live
  service never reads or writes a save.
- Hundreds to a few thousand concurrent connections on the new server (9 vCPU, 15 GB) within a small budget
  (`CPUQuota=150%`, `MemoryMax=768M`).
- Keep all chat (owner rule: never delete player data); a player's own "delete" really removes their message
  text, as the existing "clear chat" does.
- Not in scope: voice, images or files in chat, real-money anything, real-world dating features.

## Architecture

```
browser ── wss://phocochuyen.io.vn/live ──> nginx ──> mnl-live (127.0.0.1:8770, asyncio + websockets)
                                                         │  PostgreSQL (chat tables, profiles, friends, blocks)
browser ── https /api/* ──> nginx ──> game server (unchanged; applies live rewards on load, phase 3)
```

- **`live/` package, one process** (`python3 -m live`): asyncio, the `websockets` library (vendored into
  `shared/pyvendor` like orjson), psycopg 3 async pool (max 8 connections). One process keeps presence and rooms
  in memory; no cross-process fan-out is needed at this scale. Bounded: at most `LIVE_MAX_CONN` (5,000)
  connections, 20 players per street room, and per-channel ring buffers of the last 50 messages.
- **nginx** `location /live { proxy_pass http://127.0.0.1:8770; proxy_http_version 1.1; Upgrade/Connection
  headers; proxy_read_timeout 75s; }`. The client pings every 25 s.
- **systemd** `mnl-live.service` (User=mnl, same sandbox as the game, the `pg.env` EnvironmentFile,
  `PYTHONPATH=pyvendor`). Deploys: the rolling release restarts it after the game. Clients reconnect with
  backoff (1, 2, 4… 15 s) and resume by last message id, so nothing is lost.
- **Auth:** the WebSocket handshake carries the `mnl_session` cookie (same origin). The service resolves it
  exactly like `Store.resolve` (sha256 → `logins` → sid, else the guest sid) and loads `profiles` (pid, name,
  avatar). No save parsing. The origin must be the site's; per-message CSRF is not needed on a same-origin
  socket, and the Origin check blocks cross-site sockets.
- **Protocol:** JSON frames `{t: type, ...}`. Client → server: `hello`, `ping`, `send`, `read`, `history`,
  `del`, `report`, `block`, `join`, `leave`, `move`, `emote`, `say`, `queue`, `answer`, `heart`. Server → client:
  `welcome` (flags, my pid, unread counts, online friends), `msg`, `deleted`, `presence`, `room`, `moved`,
  `emote`, `said`, `match`, `date`, `error`. Frames ≤ 4 KB; malformed or oversized frames close the socket.

## Data (PostgreSQL, new tables only; nothing existing changes)

- `chat_channels(id text pk, kind text, title text, owner_pid text, created float)`: kinds `town` (one row,
  "Cả phố"), `dm` (id `dm:<pidA>:<pidB>`, sorted), `group` (id `g:<n>`).
- `chat_members(channel text, pid text, role text, joined float, last_read bigint, muted_until float,
  primary key(channel, pid))`: for dm and group only.
- `chat_messages(id bigserial pk, channel text, pid text, text text, at float, hidden int default 0,
  deleted int default 0)`, index `(channel, id)`.
- `chat_mutes(pid text pk, until float, by text, reason text)`: admin mutes.
- Reports reuse `reports` (kind `chat`, target = message id); blocks reuse `blocks`; friendship reuses
  `friends`; names and avatars come from `profiles`.

## Rules

- **Who:** anyone with a session, guests included (the owner wants it open). A guest must have named their
  character. New sessions (< 10 minutes old) can read "Cả phố" but not post there yet (anti-spam).
- **Private chat** only between friends (`friends` both ways); a friend who is offline reads it later (unread
  badge in the game, and a web push via the existing push queue at most once per 10 minutes per chat).
- **Groups:** created by a player, members invited from their friends, max 20, owner can remove members.
- **"Cả phố"** (server-wide, the "world" channel): online players only; slow mode **1 message / 10 s per player**
  (owner, 30/09; the client shows the countdown on the send button), 300 characters,
  the last 50 on join plus "Xem cũ hơn" paging.
- **Filters:** phone numbers, URLs and "zalo/fb/…" handles are masked (`•••`); a short list of slurs is masked;
  repeated identical messages are dropped. Blocked players never see each other's messages, and a DM with a
  blocked player is closed.
- **Moderation:** report → admin "Chat" tab (message, context, reporter count); admin can hide a message and
  mute a player 1 h / 24 h / 7 d. Three distinct reports on one message hide it until reviewed.
- **Online** = an open socket with a ping in the last 60 s. Friends see a green dot. A player can turn
  "hiện online" off in settings (they then see and are seen as offline in presence, but can still chat).

## Phase 2: strolling the phố ("Đi dạo")

- **Places:** Bờ hồ, Chợ đêm, Công viên, Phố đi bộ; each a small top-down canvas scene (the game's existing
  scene style, phone first). A place has instances of up to 20 players; joining picks the fullest instance with
  room so it feels alive.
- **Avatars:** the client sends its public look (hair, outfit colours, shoes, accessory ids: the wardrobe's
  public fields) on `join`; the server only validates shape and known ids. Name tag + title.
- **Moving:** tap a spot → `move {x,y}`; the server clamps to walkable areas, stamps a start time and broadcasts;
  clients interpolate at 60 fps. At most 4 moves/s per player; the server sends room diffs at most 10 times/s.
- **Talking:** `say` shows a speech bubble for 6 s and goes to the room's log (stored like chat, same filters).
  Emotes: 👋 ❤️ 😂 😮 🙏. Tap a player → card: kết bạn, nhắn riêng (if friends), rủ đi cà phê (opens a 1:1
  table: a private room with the two of them).
- **Bàn tám chuyện:** a table seats 3–4; sitting deals a topic card from the phố ("Hôm nay khách khó nhất là
  ai?", "Món ăn vặt đầu hẻm ngon nhất?"). A new card every 2 minutes or when everyone taps "đổi chủ đề".
- **Little happenings** (server-driven, per instance, at most one per 10 minutes): a lion-dance troupe crosses
  the street; a street vendor shouts; a lucky red envelope appears and the first to tap it gets a few xu
  (capped per player per day, paid through the phase-3 reward path).

## Phase 3: "Bạn muốn hẹn hò?" (in-game dates)

- **Queue:** sit on the "Góc hẹn hò" bench. Optional preference: with a boy / a girl / anyone (by the
  character's gender). The matcher pairs the two longest-waiting compatible players who are online, have not
  blocked each other and have not dated each other in the last 24 h. Waiting shows a gentle timer, can be left
  any time.
- **The date (5 minutes, at a café table):**
  1. Three icebreaker cards ("Sáng nay uống gì?", "Nghề mơ ước hồi nhỏ?", "Đi biển hay lên núi?"): each picks
     privately, both reveal together → "Hợp nhau 2/3".
  2. A small game: "Chọn món cho nhau": each orders for the other from a short menu; the other says if it is
     right (the answer they gave privately).
  3. Free chat for the last minute, then each privately taps ❤️ or 👋.
- **After:** mutual ❤️ → they become friends (if not yet) and get "Đang tìm hiểu 💕" on each other's cards; a
  small spirit boost for both. One-sided or 👋 → a kind line ("Hôm nay chưa hợp, phố còn đông người mà!"), no
  one learns who declined. Leaving early ends the date for both, gently.
- **Rewards and the save:** the live service never writes saves. It inserts rows in `live_effects(id, sid,
  kind, amount, data, status, at, applied_at)`; the game server applies pending effects on load (the same
  pattern as `marriage_effects` and `marriage.on_load`), with daily caps. Save change: none beyond what those
  effects already touch (spirit, wallet, closeness).
- **Link to marriage:** "Đang tìm hiểu" couples can later use the existing ring + proposal flow; nothing there
  changes.

## Performance and safety budget

- Chat send: one INSERT + fan-out to members online (in memory). Street move: memory only (no database).
- Load test before launch: 2,000 simulated sockets (500 strolling in 25 rooms, 1,500 idle in chat, "Cả phố" at
  5 messages/s), measure p95 delivery latency (< 300 ms target), CPU and memory of `mnl-live`, and confirm the
  game's command p50/p90 does not move.
- Everything bounded (connections, rooms, buffers, per-player rate limits); a slow client whose send buffer is
  over 256 KB is disconnected.

## Rollout

1. **Phase 1:** the live service, presence (green dots), friend DMs, "Cả phố", the admin Chat tab. Switch
   `LIVE_CHAT=1`.
2. **Phase 2:** Đi dạo (places, avatars, moving, bubbles, emotes), tám chuyện tables, groups, little
   happenings. Switch `LIVE_STREET=1`.
3. **Phase 3:** the dating bench, the 5-minute date, `live_effects`. Switch `LIVE_DATING=1`.

Each phase: unit tests (filters, rate limits, auth, channel access, matcher), two-browser tests (two players
chatting, strolling, a full date), the load test above, the release checklist in docs/HANDOFF.md §5, then a
quiet deploy. The client shows an entry point only when `welcome.flags` has the switch on, so a phase can be
turned off without a deploy.

## Risks

- Mobile networks that break WebSockets: rare on 443 with TLS; the client falls back to reconnecting and shows
  "Đang kết nối lại…". If field data shows a real problem, add a long-poll fallback.
- Spam and abuse on "Cả phố": the 10 s slow mode, filters, reports, mutes, and new-session read-only from day one.
- Load: presence and moves never touch the database; the load test gates each phase.
