# HTTP API v0.4

This is an extension of `API.md` (v0.2) and `API_V03.md`. The command envelope, cookie, CSRF, Host/Origin and error codes stay the same. Everything is same-origin, with no public CORS.

## Common changes

- Every JSON response now carries `server_time` (epoch seconds). The client uses it to estimate clock drift.
- `GET /api/bootstrap` returns extra fields:
  - `social`: `{me, unread, community, stickers, reactions, board_kinds, report_reasons}`
  - `push`: `{enabled, key}`, where `key` is the base64url VAPID public key.
  - `ai.configured`: true when the server has an LLM configured.
- `GET /api/save/export` returns format `mot-ngay-lam-nghe/save-v4` (schema 4). Import accepts v1 through v4. Old saves are migrated, and careers added later are filled in with their initial state.
- Pages: `/privacy` (privacy policy) and `/terms` (terms of use).
- Static files have an ETag and gzip. `sw.js` is sent with `Service-Worker-Allowed: /`.

## Trimmed state

`state.careers[id]` has the full view only for the career currently being played (`state.current`, or `mother_baby` when no career has been chosen yet). Every other career has only a summary:

```json
{"summary": true, "started": true, "open": false, "day": 3, "xp": 120, "level": 2, "money": 410,
 "job": {"required": true, "status": "hired"}, "inventory": true, "life": {"shop_name": "…"}}
```

The full view of a career arrives in the response to `select_career`. This keeps each response at about 10–20 KB instead of about 200 KB.

## Internal commands

The actions `fb_resolve`, `fb_voice` and every `soc_*` action run **only from inside the server** (`Store.command(..., internal=True)`). Sending them through `/api/command` returns 400 `forbidden`.

`cl_*` (teacher's Class plan) and plugin actions (`<prefix>_*`) are regular commands. They need a shift to be open.

## Customer feedback and AI personas

| Route | Body | Result |
|---|---|---|
| `POST /api/command` `fb_reply` | `{post, text, offer: none/gift/refund}` | The owner replies to a review. The customer goes into `awaiting`. |
| `POST /api/ai/feedback` | `{career, post}` | The server decides how the customer reacts: `revise_up`/`revise_down` (change stars within the range the facts allow), `keep` or `argue` (push back at the owner). It uses the AI when the player allowed AI and the server has an LLM, and falls back to a script otherwise. Returns `{state, revision, result, mode: ai/scripted/none}`. |
| `POST /api/ai/review` | `{career, post}` | Rewrites the review text in the persona's voice, once per review. It never changes stars or facts. Returns `mode: ai/none`. |
| `POST /api/command` `fb_close` | `{post}` | Closes the conversation. |

**Personas:** customers are `sour` (sharp-tongued), `bossy` (know-it-all), `warm` (warm and funny), `picky`, `genz` and `quiet`. For the teacher, the reviewers are parents: `parent_worried`, `parent_strict` and `parent_kind`. Each post keeps `feedback.persona`.

**AI guardrails:**
- Stars proposed by the AI are clamped to the allowed range (`feedback._bounds`).
- Text containing a link, markup or an instruction injection is discarded and the script is used instead.
- There are at most three exchange rounds per review.

**Rate limits:** `AI_PER_MINUTE` per session and `AI_GLOBAL_PER_MINUTE` for the whole server.

## Class plan (teacher)

| Action | Payload |
|---|---|
| `cl_start` | `{activity}`. The activity must be in `classroom.offers` for today. |
| `cl_submit` | `{step, answer}`. Returns `{correct, done}`. A wrong answer counts as a mistake. |
| `cl_finish` | `{}`. Grades the work great/ok/rough. The reward scales with the grade. |
| `cl_quit` | `{}` |

The career state includes `classroom`: `{offers, active, history, recap, calendar, month, month_index}`. Answers (`_key`) and explanations for unsolved steps are never sent to the client.

## Plugin careers

Each plugin career declares its own `ACTIONS` with a prefix (see `PLUGIN_CAREERS.md`). Shared subsystems:

- **Inventory:** `inventory` (goods, batches, shelf life, restocking).
- **Situations:** `situations` (real-life situations with several perspectives).
- **Hiring:** `employment` (applications and interviews).
- **Procedures:** `procedures` (multi-step paperwork, as in accounting and tax).

## Phố nghề (multiplayer)

Every route needs the session cookie. POST routes also need `X-Game-CSRF`. Errors use the format `{error, code}` with status 400/403/404/429.

### Read: `GET /api/social/<route>`

| Route | Query | Returns |
|---|---|---|
| `me` | – | `{me, unread, community}`. `me` is null until a display name is set. |
| `directory` | `career?`, `q?`, `filter=following?` | `{players[], community}` |
| `shop` | `pid` | `{profile, visits, rating, reviews[], listings[], can_review, can_gift}`. Also records a visit (once per day) and notifies the shop owner. |
| `board` | `career?`, `kind?` | `{posts[]}` with reactions and comments |
| `market` | `career?` | `{listings[], mine[], notes[], rules}`. Settles expired items and payouts first. |
| `inbox` | – | `{items[], unread, gifts[], notes[]}` |
| `community` | – | `{community, top[]}`: the weekly goal of all players combined. |

### Write: `POST /api/social/<route>`

| Route | Body | Rules |
|---|---|---|
| `profile` | `{name, bio?, avatar, visible}` | Name: 2–24 characters, unique (case- and accent-insensitive). Other routes need a name first. |
| `review` | `{pid, stars 1–5, text}` | Requires a visit within 24h. At most one review per shop per day. |
| `reply` | `{id, text}` | The shop owner replies once. |
| `gift` | `{pid, sticker, coins: 0/10/20, note?}` | 5 gifts/day. 1 gift/day for the same person. A recipient gets at most 100 coins/day. |
| `list` | `{career, item, qty 1–50, price}` | Price must be 0.5×–3× the cost. At most 5 active items and 12 listings/day. Goods leave your stock right away (escrow) and keep their shelf life. Listings expire after 3 days and the goods come back. |
| `unlist` | `{id}` | The goods come back, minus the days that passed. |
| `buy` | `{id}` | Checks coins and room in your stock. The item is locked while you pay. The seller receives coins the next time they open the game. |
| `board` | `{career, kind: tip/story/ask/trade, text}` | 10 posts/day. |
| `comment` | `{post, text}` | 30/hour. 30 per post. |
| `react` | `{post, emoji}` | Toggles on/off. |
| `delete_post` | `{post}` | Your own posts only. |
| `follow` · `unfollow` · `block` · `unblock` | `{pid}` | Blocking hides both sides and removes follows. |
| `report` | `{kind: profile/review/board/comment/listing, id, reason}` | Content reported by 3 different players is hidden automatically. |
| `inbox_read` | `{}` | Marks everything as read. |

Free text is filtered: links, emails and phone numbers are blocked, and profanity is masked. A player's `pid` is a one-way hash of the session and does not reveal the cookie.

## Web push

| Route | Body | Notes |
|---|---|---|
| `POST /api/push/subscribe` | `{subscription: PushSubscription.toJSON(), prefs: {social, daily, hour, tz}}` | Only accepts endpoints from known push services (FCM, Mozilla, Windows, Apple). Up to 5 devices per player. |
| `POST /api/push/unsubscribe` | `{subscription?}` | With no subscription, turns off every device. |
| `GET /api/push/pending` | – | The service worker calls this after receiving an **empty** push (no payload). Returns `{items: [{title, body, url, tag}]}`. |

VAPID uses ES256 (P-256), written in pure Python. The key lives in `VAPID_PRIVATE_KEY` or `storage/vapid.json`. Push content stays on the server and never passes through the push service.

## Account

`POST /api/account/delete` `{confirm: "XOA"}`. Deletes the save, the Phố nghề profile, posts, reviews, gifts, unsold listings, player feedback and push subscriptions, then clears the cookie. Items already sold stay in the buyer's history but no longer name the seller.

## Player feedback ("Góp ý")

Private notes from players to the operator (spec: `docs/superpowers/specs/2026-09-29-player-feedback-design.md`).

| Route | Who | Body / query | Answer |
|---|---|---|---|
| `POST /api/feedback` | any session (CSRF) | `{kind: bug\|idea\|praise\|hard, text: 3..1000, context?: {view, layout, screen}}` | `{ok, id, message: "Đã ghi nhận, cảm ơn bạn!"}` |
| `GET /api/feedback/mine` | any session | – | `{items: [{id, kind, text, status, reply, created_at, updated_at, replied_at}], admin}` (last 20, this save or account) |
| `GET /api/admin/feedback` | admin (CSRF header too) | `?status=new\|seen\|done&kind=…&before=<id>` | `{items: [...with context, account, player tag], next, counts}` (50 per page, newest first) |
| `POST /api/admin/feedback` | admin (CSRF) | `{id, status?, reply?}` (`reply: ""` clears; ≤ 300) | `{ok, item}` |
| `GET /api/admin/stats/summary` | admin (CSRF header too) | `?range=7\|30\|90&fresh=1?` | first screen of `/admin`: `{range, today, players, feedback, ai, server, names, generated_at, took_ms, cached, age}`. Small-table SQL only, read-only, time budget 1.5 s in all (`ADMIN_STATS_REQUEST_MS`; PostgreSQL: statement_timeout = the time left, at most `ADMIN_STATS_STATEMENT_MS`), cached 30 s per range, one computation shared by concurrent calls. Over budget (a cold or busy disk): the background job's copy with `stale: true` (it recomputes every range each minute with a longer budget), or `{pending: true, retry_ms, range}` before its first copy. Wakes the background stats job |
| `GET /api/admin/stats/section` | admin (CSRF header too) | `?name=saves\|system&fresh=1?` | served from the background job's result file, never computed on the request. `saves`: `{play, economy, life, board, sample, generated_at}` (only saves whose revision changed are re-read, in small throttled chunks, about every 60 s while an admin is active). `system`: `{server: {…, tables: [{name, rows, approx}], db_bytes, database}}` (every 120 s, large tables estimated). Before the job's first pass: `{pending: true, retry_ms, progress?: {done, total}}` |
| `GET /api/admin/stats` | admin (CSRF header too) | `?range=7\|30\|90` | everything in one payload (in-game "Thống kê" tab): summary + the job's last result (`pending: true` with empty save cards before its first pass), cached 60 s |

The server fills `context.career/day/life_day/lang/version/ua` itself; only `view`, `layout` and `screen` come from the client. Text and replies have e-mails, links and phone-like numbers replaced by `[đã ẩn]` and rude words by `•••`. Admin = a signed-in account whose username is in `ADMIN_USERS`; everyone else gets 403. `GET /api/bootstrap` carries `admin: true|false`. Rate limits: `FEEDBACK_PER_10MIN` (5) and `FEEDBACK_PER_DAY` (30) per session, 4 × the 10-minute budget per IP.
