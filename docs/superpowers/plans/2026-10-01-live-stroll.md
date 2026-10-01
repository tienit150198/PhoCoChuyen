# Plan: Chat v1.0, phase 2: "Đi dạo khu phố" (01/10/2026)

Spec: `docs/superpowers/specs/2026-09-30-live-chat-street-design.md` ("Phase 2"). Phase 1: `2026-10-01-live-chat-v1.md`
(the live service, its extension points). Branch `live-stroll` (from `live` 765828b). Switch `LIVE_STREET`. No version
bump, no whats_new entry, no tutorial, guide page, coach mark or intro screen (owner, 01/10): the menu entry opens
straight into the place.

## What players see

- **Menu "Đi dạo"** (icon map), only while the live service has the street on. It opens a full-screen scene on
  the last place they strolled (else the busiest, else Bờ hồ). The header names the place and how many people are
  there; tapping it shows the four places with their counts (Bờ hồ 🌊, Chợ đêm 🏮, Công viên 🌳, Phố đi bộ ⛲).
- **The scene**: a top-down canvas in the game's pastel style, phone first (600 × 900 world, letterboxed on wider
  screens). Everyone is drawn from their wardrobe look (`look.js` painters), with a name tag and their title.
  Tap to walk (around the lake, the fountain, the stalls); others glide there at 60 fps.
- **Talking**: "Nói gì đó…" puts a bubble over your head for 6 s; 😊 opens 👋 ❤️ 😂 😮 🙏.
- **Bàn tám chuyện**: tap a table to sit (3-4 seats); a topic card slides in at the top ("Deadline dí thì bạn xử
  lý kiểu gì?"); a new card every 2 minutes (a thin bar runs down) or when everyone tapped "Đổi chủ đề";
  "Đứng dậy", or simply walk away.
- **Tap a player**: their card (portrait, name, title): Kết bạn (accounts, the game's friends API), Nhắn riêng
  (friends: opens the phase 1 DM), Rủ đi cà phê (the other gets "… rủ bạn đi cà phê ☕ · Đi / Để sau"; yes takes
  both to a private café for two with its own topic card; ← goes back to the street), ⋯ Báo cáo lời vừa nói / Chặn.
- **Little happenings** (≤ 1 per instance per 10 minutes): a lion-dance troupe crosses ("Tùng tùng cắc! 🦁"), a
  vendor calls out ("Kem Tràng Tiền đâyyy, mát lạnh luôn!"), or a red envelope 🧧 glows for 45 s: the first tap
  gets 3-8 xu (≤ 30 xu a day per player), "+n" floats over the winner, the wallet moves at once.
- Night (the "Phố đêm" theme) dims the scene and lights the lamps and lanterns; Chợ đêm is always a little dusky.

## Server (`live/street.py`, data in `live/street_data.py`)

| Frame (client → server) | Rate (per player) | Reply / broadcast |
|---|---|---|
| `walk_places {}` | 10 / 10 s | `walk_places {places: [{id, name, icon, n}], here}` |
| `walk_in {place, look, g, title}` | 8 / min | `walk_room {place, room, me, people, tables, geo, hap, env, speed, at}` |
| `walk_out {}` | 10 / min | `walk_left {why: 'out'}` |
| `move {x, y}` | **4 / s** | room diff `walk {ev: [{k: 'mv', pid, p: path, at}]}` |
| `say {text}` | 5 / 10 s | `said {ch, pid, id, text, at}` to the room (stored, filtered) |
| `emote {e}` | 4 / 4 s | `emoted {pid, e}` |
| `sit {table}` `stand {}` `topic {}` | 6 / 10 s, 6 / 30 s | diffs `mv`, `tb {i, seats, topic, until, votes}` |
| `card {pid}` | 20 / min | `card {pid, name, ti, lk, g, friend, account, code, cafe}` |
| `invite {pid}` | 4 / min | `invite_sent {id}`; the other: `invited {id, pid, name, lk, g, ttl}` |
| `invite_reply {id, ok}` | 10 / min | both: `walk_room` of `walk:cafe:<hex>`; or the inviter: `invite_no` |
| `grab {id}` | 6 / 10 s | `grabbed {id, n}`; the room: `happen_end {id, pid, name, n}` |

Server pushes: `walk` (diffs: `mv`, `in`, `out`, `tb`), `said`, `emoted`, `happen {k: vendor|lion|env, ...}`,
`happen_end`, `walk_left {why: 'other'}` (a second tab took over).

- **Instances**: rooms `walk:<place>:<n>`, at most 20 players, at most 250 per place; `walk_in` picks the fullest
  with room that holds nobody blocked either way. One room per player (all tabs).
- **Moves**: memory only. The target is clamped into the place's walkable rectangles and routed through the
  junctions between them (Dijkstra over ≤ 4 points); the server stamps `at` and clients interpolate at 170 units/s.
  Diffs are queued per room and flushed at most every 100 ms (≤ 10 frames/s); several moves of one player in a
  window send only the last. Blocks: a block during the stroll sends each side an `out` for the other (tick), and
  every diff, bubble and emote is filtered both ways.
- **Bubbles**: `app.chat.store_message(p, <room id>, text, 120, 2)` (filters: phone numbers, links, handles and
  heavy profanity masked, GenZ slang kept; mutes; duplicates) and `app.chat.route('walk:', …)` so `del`, `report`
  (3 → hidden) and the admin's hide/keep reach the room. A player may report bubbles of the last 6 rooms they were in.
- **Tables**: 72 topic cards (`TOPICS`), a shuffled deck per table.
- **Happenings**: tick; the first comes 1-4 minutes after an instance opens, then every 10-15 minutes; the café
  has none. The envelope is paid with `live/effects.grant(db, sid, 'coins', n, key='env:<room>:<id>', cap=30)`.
- **Cards**: the player code (`marriage_people.code`) of an account, created like a friends search would when the
  account never opened Bạn bè / Hôn nhân, so the client can call `POST /api/marriage/friend_request {code}`.
- Bounded: 20 per room, 250 rooms per place, cafés ≤ players / 2, 400 queued events per room, 2,000 invites,
  6 rooms remembered per player, a 72-card deck per table.

## Game server

- `game/live_effects.py` (new, both phases): pays `live_effects` rows on `/api/bootstrap` (after the system gifts)
  and on `POST /api/live/effects` (the stroll calls it right after an envelope). The system_gift pattern: one
  internal command `live_fx` per row with the fixed request id `live-<hash>`, the save keeps the last 60 hashes
  (`journey.live_fx`, validated), the row flips pending → applied. `coins` → wallet + a history row ("🧧 Lì xì dạo
  phố", kind `life`); `spirit` → `journey.life.spirit` (0-100). Other kinds stay pending for a later build.
- `game/engine.py` (the internal action), `game/journey.py` (validate), `server.py` (the load hook and the route).

## Client

- `public/js/v4/walk.js` (the dialog, frames, input, drawing), `public/js/scenes/stroll.js` (the places, tables,
  happenings), `public/css/walk.css`; `public/js/app.js`: one `navItems` line and one action line.

### Hook for phase 3 (the dating bench lives in this scene)

Every public place has a named spot `bench` (`geo.spots.bench`, a plain bench is drawn there). Phase 3 attaches to it
from the client without touching walk.js:

```js
const {walk}=await import('./walk.js');
walk.addSpot({id:'dating-bench', place:'*', at:'bench', r:44,
  draw(c,{x,y,t,night,place}){/* world units, on the ground under people */},
  tap({x,y,place,room}){/* open the "Bạn muốn hẹn hò?" sheet; return false to just walk there */}});
walk.on('enter',({place,room,private})=>{});  walk.on('leave',…);  walk.spot('bench');  walk.state();  walk.moveTo(x,y);
```

Server side, `app.by_name['street']` gives `spot(place, 'bench')` and `where(player) → (place, room)`. A date can
reuse the café: `StreetFeature._cafe(street_room, [player_a, player_b], now)` moves two strollers into a private
room for two with a table and a topic card (phase 3 may want its own `walk:date:<id>` room instead).

## Tests

- `tests/test_live_street.py`: data (wardrobe ids and titles match the game, 60+ topics, every place's geometry
  connected, seats and spots walkable), moves (clamped, routed around the lake, coalesced, 4/s, never touch the
  database, ≤ 10 diffs/s), instances (fullest with room, capacity 20, a second tab), bubbles (masking, delete,
  report → hidden, outsiders cannot report), mutes, emotes, tables (deal, full, votes, timer, stand), happenings
  (≤ 1 per 10 minutes), the envelope (paid once, the daily cap leaves it for others, expiry), blocks (vanish, never
  the same instance again), cards (friend, code), coffee (decline, accept, expiry), the switch off.
- `tests/test_live_effects_apply.py`: the applier (paid once, retries, crash + pruned receipts, two tabs, the real
  grant, spirit, unknown kinds stay pending, client refused, bad lists refused, non-story saves, HTTP).
- `scripts/browser_live_walk.py`: three phones in one place (move, bubble, emote, table, envelope, lion, vendor,
  friend request, coffee, report, block, places, dark theme); screenshots.
- `scripts/live_load.py --strollers 500` (default): 500 strollers in 25 instances (a move every ~2 s, a bubble
  every ~45 s) + 1,500 in Cả phố at 5 messages/s; reports move-delivery p50/p95/p99 next to the chat's.

## Production (beyond phase 1's steps)

1. The release carries `game/live_effects.py` and `POST /api/live/effects`; no schema change (`live_effects` came
   with phase 1's SCHEMA_VERSION 6).
2. Turn it on: `LIVE_STREET=1` in `/etc/mot-ngay-lam-nghe/live.env`, `systemctl restart mnl-live`. Off again:
   `LIVE_STREET=0` and restart (the menu entry disappears on the next welcome; nothing else changes).
3. Run the load test with strollers on the scratch database first (phase 1's step 8; `--strollers 500` is the default).
