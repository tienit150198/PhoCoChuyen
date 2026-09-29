# Player feedback ("Góp ý") — design

Date: 2026-09-29 · Branch: care-wave1

## Goal

Players can leave a short note from inside the game: a bug, an idea, praise, or
"this was hard to use". The operator (the owner) reads the notes in an in-game
inbox, marks them seen/done and can write one short reply that the player sees
next to their note. Nothing here touches game state, money or the save.

## Data

One SQLite table, created in `Store.__init__` (`game/storage.py`), so every
server, test and script that opens a `Store` has it:

```sql
CREATE TABLE IF NOT EXISTS player_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sid TEXT NOT NULL,            -- the save id (same one sessions.sid uses)
  account TEXT,                 -- username when signed in, else NULL
  kind TEXT NOT NULL,           -- bug | idea | praise | hard
  text TEXT NOT NULL,           -- 3..1000 chars after cleaning
  context TEXT NOT NULL DEFAULT '{}',  -- JSON, see below
  status TEXT NOT NULL DEFAULT 'new',  -- new | seen | done
  reply TEXT,                   -- operator reply, <= 300 chars
  created_at REAL NOT NULL, updated_at REAL NOT NULL, replied_at REAL
);
CREATE INDEX IF NOT EXISTS player_feedback_sid ON player_feedback(sid, id);
CREATE INDEX IF NOT EXISTS player_feedback_status ON player_feedback(status, id);
```

Times are epoch seconds (like `game/social.py`).

### Context

The context is a small JSON object. The server builds most of it from what it
already knows, so a client cannot fake the career or day:

| key | source |
|---|---|
| `career`, `day` | current career id and its day, from the save |
| `life_day` | `journey.life_day`, from the save |
| `lang` | `settings.lang`, from the save |
| `version` | server `__version__` |
| `ua` | `User-Agent` header, trimmed to 200 chars |
| `view` | client, `[A-Za-z0-9_-]{1,40}` (the sheet or screen that was open) |
| `layout` | client, `phone` / `tablet` / `desktop` |
| `screen` | client, `"390x844"` style, digits only |

Unknown client keys are dropped. Bad values are dropped, never an error.

### Cleaning and privacy

`game/player_feedback.py` cleans the text like the street does
(`social.clean` rules: NFC, control chars removed, spaces squeezed) but
**redacts instead of rejecting**: a bug report may well contain a link or a
number. It reuses, read-only:

- `game.ai.redact` — e-mails, links and phone-like numbers become `[đã ẩn]`;
- `game.social.BANNED` — rude words become `•••` (same whole-word rule).

The operator reply goes through the same cleaning. Feedback is private: only
the author (same save, or same account) and admins can read it.

## Module `game/player_feedback.py`

- `KINDS = ('bug','idea','praise','hard')`, `STATUSES = ('new','seen','done')`
- `class FeedbackError(Exception)` with `message, code, status` (like `SocialError`).
- `clean_text(text, limit, minimum, field)` → cleaned + redacted text.
- `clean_context(client: dict|None, state: dict, ua: str, version: str)` → dict.
- `submit(store, token, state, data, ua, version)` → `{ok, id, message}`.
- `list_mine(store, token, limit=20)` → newest first, only rows with this save's
  sid or this account's username.
- `list_admin(store, status=None, kind=None, before=None, limit=50)` →
  `{items, next, counts}`; `items` carry context (parsed), account, a short
  opaque player tag (never the sid itself).
- `update(store, fid, status=None, reply=None)` → the updated item.
- `admin_users()` → set from env `ADMIN_USERS` (comma list, lower-cased; empty
  by default = nobody); `is_admin(store, token)` → only a **signed-in** account
  whose username is in that set.
- `forget(store, token)` — deletes this save's and account's feedback (used by
  "Xóa dữ liệu của tôi").
- `prune(store, days=730)` — feedback older than two years goes.

## HTTP routes (`server.py`)

All follow the existing patterns: Host check on every request, the session
cookie, JSON bodies ≤ 64 KB, CSRF header + Origin/Sec-Fetch-Site checks on
POST (`guarded()`), in-memory rate limits.

| Route | Who | Body / query | Answer |
|---|---|---|---|
| `POST /api/feedback` | any session | `{kind, text, context}` | `{ok, id, message:"Đã ghi nhận, cảm ơn bạn!"}` |
| `GET /api/feedback/mine` | any session | – | `{items:[{id,kind,text,status,reply,created_at,updated_at,replied_at}], admin}` |
| `GET /api/admin/feedback` | admin | `?status=&kind=&before=` | `{items, next, counts}` (50 per page, newest first) |
| `POST /api/admin/feedback` | admin | `{id, status?, reply?}` | `{ok, item}` |

- Rate limits: `FEEDBACK_PER_10MIN` (default 5) per session per 10 minutes,
  `FEEDBACK_PER_DAY` (default 30) per session per rolling day, and 4× the
  10-minute budget per IP (cheap new sessions cannot multiply it). `mine`:
  60/min per session. Admin routes: 120/min per session.
- Admin gating: the admin GET also requires the CSRF header (the client
  sends it), so a plain cookie is not enough. Non-admins get **403**
  `forbidden` for both admin routes; the client never renders the inbox unless
  the bootstrap flag says so, and the server checks again on every call.
- `GET /api/bootstrap` gains `admin: true|false` (a boolean only; which
  usernames are admins is never sent).
- `POST /api/account/delete` also deletes the player's feedback.
- The maintenance thread prunes feedback older than two years.

## Client

- `public/js/v4/feedback.js` (new) exports `feedbackPageView(env)`,
  `feedbackAction(...)`, `feedbackSubmit(...)`, `feedbackInput(...)`;
  `public/css/feedback.css` (new, linked in `index.html`), tokens only.
- Entry points: a **Góp ý** item (chat icon) at the bottom of the rail, which is
  also the phone "Thêm" menu, and a "💬 Góp ý cho nhà làm game" link in
  Settings → Dữ liệu (and Cách chơi). Both open the sheet `gopy`.
- The sheet (phone-first, 390 px):
  1. kind chips: 🐞 Lỗi · 💡 Ý tưởng · 💖 Khen · 🤔 Khó dùng;
  2. a textarea (1000 max) with a live `n/1000` counter;
  3. "Gửi kèm: Quán mì · ngày 3 · điện thoại" — the auto context line, built
     from the same data the server will store;
  4. Send button → success state ("Đã ghi nhận, cảm ơn bạn!" + "Viết thêm");
  5. "Góp ý của bạn": the last 20 notes with a status pill (Đã gửi / Đã xem /
     Đã xử lý) and the owner's reply in a quoted box.
- Admin (flag only): a "📥 Hộp góp ý" tab in the same sheet: status and kind
  filters, counts, newest first, "Xem thêm" paging (`before`), each entry
  expands (`<details>`) to show the context as a small key/value list, status
  buttons (Mới / Đã xem / Xong) and a reply box (300 max).
- Player text and replies are wrapped in `data-no-translate` so the English
  layer never rewrites them.

## Tests (`tests/test_player_feedback.py`)

Module: submit + validation (kind, length, type), redaction of e-mail/link/
phone, banned words masked, context whitelisting and server-derived fields,
account linkage, `mine` isolation between saves, admin list filters/paging,
update validation, forget. HTTP (real `GameServer` on a temp DB): submit and
mine, CSRF required, rate limits (10-minute and daily knobs via env),
isolation between two browsers, admin gating (anonymous 403, signed-in
non-admin 403, admin in `ADMIN_USERS` can list and update), bootstrap
`admin` flag, the reply shows up in the author's `mine`, delete-my-data wipes
feedback.

## Out of scope

E-mail notifications to the operator, attachments/screenshots, player
editing or deleting a single note (they can e-mail or use "Xóa dữ liệu").
