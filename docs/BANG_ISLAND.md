# ⚔️ Đảo bang — the bang's island (owner-approved 19/10/2026)

A bang owns one island ("lãnh địa"): its seven facilities stand on fixed slots, its members (and the guests it lets
in) walk there together in real time. This branch builds **only the island side**. Every bang fact (who is in which
bang, roles, levels, build timers, the fund) belongs to the Bang branch, which plugs in through the small contract
below. The Bang side ships with it (`game/bang_island_source.py`, §2b), so the switch is **on by default**;
`MNL_BANG_ISLAND=0` (game server and live service) hides the menu entry, answers 404 on the routes and refuses the live
frames (`off`). No table, no save key: a rollback loses nothing.

| Piece | File |
|---|---|
| Contract, derived view, provider registry, stub, HTTP | `game/bang_island.py` |
| Live room (room per bang, cap 40) | `live/bang_island.py` (`BangIslandFeature`, welcome flag `bisle`) |
| Map (slots, plots, spots, geometry) shared by both interfaces | `public/js/bang-island-layout.js` |
| New interface (2.5D Phaser) | `client/isometric/bang-island.ts` → bundle `public/js/isometric/phaser-world.js` (`BangIslandRenderer`) |
| Old interface (2D walk) | `public/js/v4/bang-island-walk.js` |
| Scene controller, dialog, facility panel | `public/js/v4/bang-island-scene.js` |
| Live client | `public/js/v4/bang-island-live.js` |
| Entry + button hooks | `public/js/v4/bang-island.js` (`data-action="bangIsland"`, `openBangIsland`, `registerBangIslandAction`) |
| Styles | `public/css/bang-island.css` |
| Tests | `tests/test_bang_island.py`, `tests/test_live_bang_island.py`, `tests/bang-island.mjs` |

## 1. The input: `BangIslandView` (what the Bang branch provides)

Python (`game/bang_island.py`, `TypedDict`):

```python
class FacilityView(TypedDict, total=False):
    id: str                                # one of FACILITY_IDS; an unknown id is ignored (a newer Bang build)
    level: int                             # 0..max, the level in effect NOW (0: not built yet)
    max: int                               # optional, 1..10 (default 10): this facility's top level (a Bang facility: 5 or 10)
    state: Literal['building', 'done']     # building: level + 1 is being built (default 'done')
    ready_at: float | None                 # epoch SECONDS when that build finishes (required while building)
    note: str                              # optional, ≤ 120 chars: one line the panel shows (what the next level brings)

class BangIslandView(TypedDict, total=False):
    bang_id: str                           # [a-z0-9_-]{1,32}  (a numeric id: str(id))
    name: str                              # 1..40 characters
    emoji: str                             # 1..16 characters (the bang's sign, usually one emoji)
    color: str                             # '#rrggbb' — the flag on the gate, the hall, the arena, the boat's sail
    level: int                             # the bang's own level, 1..99
    facilities: list[FacilityView]         # at most 32 entries; a facility left out = level 0, done
    members_online: int                    # optional, ≥ 0
```

Facility ids (never renamed): `dai_sanh` (Đại sảnh, centre), `kho_bang` (Kho bang), `xuong_may` (Xưởng may),
`san_pet` (Sân luyện pet), `den_vang` (Đền vàng), `tuong_bang` (Tượng bang, plaza), `cong_bang` (Cổng bang, at the pier).
Look bands: level 0 empty staked plot · 1–3 wood · 4–6 stone · 7–10 gold (a facility with `max` < 10 is scaled onto
the ten levels: a 5-level facility is gold at 4 and 5); `state == 'building'` adds bamboo scaffolding.

JSON schema (draft 2020-12):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://phocochuyen.io.vn/schemas/bang-island-view.json",
  "type": "object",
  "required": ["bang_id", "name", "emoji", "color", "level", "facilities"],
  "properties": {
    "bang_id": {"type": "string", "pattern": "^[a-z0-9_-]{1,32}$"},
    "name": {"type": "string", "minLength": 1, "maxLength": 40},
    "emoji": {"type": "string", "minLength": 1, "maxLength": 16},
    "color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
    "level": {"type": "integer", "minimum": 1, "maximum": 99},
    "members_online": {"type": "integer", "minimum": 0},
    "facilities": {
      "type": "array", "maxItems": 32,
      "items": {
        "type": "object", "required": ["id", "level"],
        "properties": {
          "id": {"type": "string"},
          "level": {"type": "integer", "minimum": 0, "maximum": 10},
          "max": {"type": "integer", "minimum": 1, "maximum": 10, "default": 10},
          "state": {"enum": ["building", "done"], "default": "done"},
          "ready_at": {"type": ["number", "null"], "exclusiveMinimum": 0, "maximum": 4102444800},
          "note": {"type": "string", "maxLength": 120}
        },
        "if": {"properties": {"state": {"const": "building"}}, "required": ["state"]},
        "then": {"required": ["ready_at"], "properties": {"level": {"maximum": 9}, "ready_at": {"type": "number"}}}
      }
    }
  }
}
```

`validate_view(raw)` enforces exactly this (plus: one entry per id, text trimmed and `<`/`>` neutralised); a broken
view raises `ContractError`, is logged (`[bang-island] …`) and the player gets 502 "Đảo bang đang bận sửa".

Example:

```json
{"bang_id": "b42", "name": "Long Môn Các", "emoji": "🐉", "color": "#b8282e", "level": 7, "members_online": 12,
 "facilities": [{"id": "dai_sanh", "level": 8, "state": "done", "ready_at": null},
                {"id": "kho_bang", "level": 4, "state": "building", "ready_at": 1792650000.0, "note": "Cấp 5: quỹ tối đa 2 triệu"}]}
```

## 2. How the Bang branch plugs in

Ship `game/bang_island_source.py` with `PROVIDER = YourProvider()` (found on first use), or call
`bang_island.register(provider)` at import. The provider (`BangIslandProvider` protocol):

| Method | Called by | Returns |
|---|---|---|
| `bang_of(store, sid) -> str \| None` | GET without `?bang=` | the player's own bang id, None: in no bang |
| `view(store, bang_id) -> Mapping \| None` | GET, after every button | a `BangIslandView`, None: no such bang (404) |
| `access(store, sid, bang_id) -> Access \| None` | GET / POST | `{'kind': 'member', 'role': 'bang_chu'…}` or `{'kind': 'guest', 'role': None}`; None: refused (403) |
| `async access_live(db, sid, bang_id) -> Access \| None` | live: join, every 10 s per player, on a notice | same answer; `db` is `live.db` (`await db.fetchrow(sql, args)`, `?` placeholders) |
| *(optional)* `act(store, sid, bang_id, facility, op, data) -> dict` | POST `/api/bang-island/act` | `{message, …}` shown in the panel; raise `BangIslandError(msg, code, status)` to refuse |

`store` is `game.storage.Store`, `sid` the save id (never sent to clients). Roles: `bang_chu, pho_bang, truong_lao,
tinh_anh, thanh_vien` (badges 👑 ⭐ 🎖️ ✨; a guest shows 🧳). Guests (invitations) are the Bang branch's data: just
answer `kind: 'guest'` in `access`/`access_live`; the client opens a bang other than the player's own with
`openBangIsland(env, {bang})` or `data-action="bangIsland" data-bang="<id>"`.

Notices to the live service (`SELECT pg_notify('mnl_live', json)`), all optional but make changes instant:

* `{"op": "bang_island", "why": "left" | "kicked" | "role" | "guest" | "join", "sid": "<sid>", "bang": "<id>"}` — re-check that player now (off the island at once if refused, `bisl_left {why: changed}`).
* `{"op": "bang_island", "why": "view", "bang": "<id>"}` — facilities changed (an upgrade started/finished): everyone there refetches and repaints.
* `{"op": "bang_island", "why": "disband", "bang": "<id>"}` — close the island (`bisl_left {why: ended}`).

Without notices, access is re-checked every 10 s (at most 200 checks per second in total) and the client refetches
by itself when a build timer reaches 0. Movement never touches the database or the provider.

Facility buttons (ops; placeholders until wired): `nang_cap` (every facility), `thanh_vien` (hall), `gop_quy` (vault),
`xuong_may` (workshop), `dau_truong`, `luyen_pet` (pet yard — the pet-arena branch), `gio_vang` (temple),
`xep_hang` (statue), `moi_khach` (gate). Wire them either on the server (`provider.act`) or in the client:
`registerBangIslandAction('gop_quy', async ({env, bang, facility, op}) => { openFundSheet(env); })` (or the key
`'kho_bang:gop_quy'`); a returned `{message}` shows in the panel, `{bang, now}` (the GET answer) repaints.

Entry: the Bang UI's button is `<button data-action="bangIsland">⚔️ Đảo bang</button>`. While the switch is on, the
bootstrap content carries `bang_island` and both interfaces list "Đảo bang" in the menus (Ngân hàng & nhà / Tiện ích).

## 2b. The real provider (this build)

`game/bang_island_source.py` (`PROVIDER = BangIslandSource()`), on the Bang tables (game/bang.py):

* Facility ids: Bang `dai_sanh, kho, xuong_may, san_pet, den_vang, tuong, cong` → island `dai_sanh, kho_bang, xuong_may,
  san_pet, den_vang, tuong_bang, cong_bang`; `max` from game/bang_content.py (5 or 10); a build whose time is up is
  shown done at once; `note` = what the next level brings. The bang's `level` is its Đại sảnh level.
* Roles: `chu, pho, lao, tinh, tv` → `bang_chu, pho_bang, truong_lao, tinh_anh, thanh_vien`.
* Access: a member of an active bang (also while an operator hid it: like its page); a **guest** = a player with an
  open invitation of that bang (not hidden); everyone else none. A disbanded bang has no island (404, the room closes).
* Notices (game/bang.py `_isle`): join, left (leave, switch, erase), kicked, role (appoint, handover), guest (invite,
  decline), view (build started or finished, emoji/colour, an operator's rename/hide), disband.
* Buttons: ⬆️ `nang_cap` runs the bang's own build (Phó bang and up, the fund, the hall gate, the build slots), asked
  first: the answer `done.confirm = {title, text, label}` makes the client confirm, then send `data: {confirm: true}`.
  The others open a sheet on top of the island (public/js/v4/bang-island.js `DEFAULT_HOOKS`): 👥 members and 💌
  invitations → Bang › Thành viên, 🪙 fund and ✨ golden hour → Bang › Bang của tôi, 👘 → Cửa hàng bang, 🏆 →
  Xếp hạng tuần, 🏟️ → the pet arena's 🛡️ Bang chiến tab, 🎯 → its 🎯 Thử thách. A guest is told to join first.
* Entry: the Bang sheet's 🏯 Đảo bang button and the menus; a player in no bang who opens it gets the Bang sheet.
* `MNL_BANG_ISLAND_STUB` is only read when the real provider is missing and never with `DATABASE_URL` set.

## 3. HTTP and live frames

* `GET /api/bang-island[?bang=<id>]` → `{now, cap, me: {kind, role, role_name}, bang: {id, name, emoji, color, level,
  members_online?, facilities: [{id, name, emoji, desc, level, max, band, band_name, state, ready_at, left, to, next,
  next_band, note, actions: [{op, emoji, label}]}]}}`, or `{bang: null, why}` for a player in no bang.
* `POST /api/bang-island/act {bang, facility, op, data?}` → `{done: {placeholder?, message}, …the GET answer}`.
* Live (`live/bang_island.py`): `bisl_in {bang, look, g, x?, y?}` → `bisl_room {room, bang, me, kind, role, cap, people}`;
  `bisl_out`, `bisl_mv {p, ms}`, `bisl_emote {e}` (wave heart laugh wow bow cheers fight), `bisl_say {text}` (chat store,
  channel `bisl:<bang>`), `bisl_do {s}` (a facility or spot); pushes `bisl {room, ev}` and `bisl_left {why}`.

## 4. Dev

`MNL_BANG_ISLAND=1 MNL_BANG_ISLAND_STUB=1 [MNL_BANG_ISLAND_STUB_SET=low|mid|high|build|empty|mix]` on both the game
server and the live service: every signed-in player is a member of the fake "bang_thu". Never set the stub in production.
