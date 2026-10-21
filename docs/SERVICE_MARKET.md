# 🛎️ Phố dịch vụ — players serve players (owner 21/10)

Code: `game/service_market.py` (rules, registry, escrow, settlement, reputation, anti-laundering, admin),
legacy workplace orders in `game/work_visits.py` + `game/player_service_tasks.py`, client `public/js/v4/service-market.js`
(+ `public/css/service-market.css`), admin `public/js/admin/svc.js`. Tables: SCHEMA_VERSION 63 (`game/pg_schema.py`).
Tests: `tests/test_service_market.py`, `tests/test_service_market_compat.py`, `tests/test_service_market_http.py`;
browser walk-through `scripts/browser_service_market.py`.

## Rules and numbers (all constants at the top of `game/service_market.py`)

| What | Number |
|---|---|
| Player price, default | NPC price × `DEFAULT_MULT` = **×3** |
| Provider's choice per service | ×`MULT_MIN`…×`MULT_MAX` = **×1–×10**, or 🤝 thương lượng |
| Price bounds (per unit) | **max(floor, NPC price) … min(NPC price × 10, max_price ÷ qty)**; a negotiation stays inside them |
| Fee on a completed deal | **5 %** (`FEE_PCT`), rounded up (≥ 1 xu), **burned** (paid to nobody) |
| Provider receives | price − fee (95 %) |
| Negotiation | at most `MAX_ROUNDS` = **6** offers in all; the price is locked into escrow at acceptance |
| Talk with no answer | expires after `TALK_HOURS` = **12 h** (no money moved) |
| Paid order never taken | refunded after `HOLD_HOURS` = **24 h** |
| Taken order never delivered | refunded after the spec's `work_hours` (default `WORK_HOURS` = **72 h**) |
| Delivered, buyer silent | auto-confirmed after `CONFIRM_HOURS` = **24 h** (provider paid) |
| Report window | `FLAG_HOURS` = **24 h** after delivery → admin view, nothing automatic |
| One order | ≤ `MAX_PRICE` = **50,000,000 xu** unless the spec declares a higher `max_price`; legacy orders ≤ `LEGACY_MAX` = **1,000,000** (the save's `player_order.price` range in every build) |
| Pair caps (buyer–provider) | **5 deals / Vietnam day** (`PAIR_DAY`), **60,000,000 xu / Vietnam week** (`PAIR_WEEK_XU`; a spec with max_price > 50 M allows one such order a week). Both kinds of orders count. |
| New accounts (< 7 real days) | share `bank_xfer.NEW_DAY_MAX` = **500,000 xu/day** with bank transfers and every other player-to-player route (`bank_xfer.count_out`) |
| Same network | buyer and provider seen on one network within `NET_DAYS` = **3 days** never trade (keyed tags: `lixi.ip_tag` in `svc_net` and `lixi_grabs`, `pet_arena.ip_tag` in `pet_arena`; a refused attempt still records the tag) |
| Spouses (a married couple) | **allowed** to trade on one network, **counted** in every cap |
| Self / blocked | never (either block direction, `marriage_blocks` or `blocks`) |
| Open orders | buyer ≤ 20, provider ≤ 50 (svc orders; legacy keeps its own 20/50) |
| Ratings | only a completed, paid order; **one counted rating per buyer–provider pair per 7 days**, from accounts ≥ 3 days old |
| Online | played within 5 minutes (`stat_play.last_at`) |

Money: escrow comes from the wallet, then the bank account (never debt, never the credit card); wallet history rows are
≤ 10,000,000 xu each. Pay-outs go to the wallet (to the bank account past the wallet's maximum) or, for a spec with
`pay_to='career'`, to that career's fund. Refunds go to the wallet in full.

Exactly once: each money move is ONE transaction — the save(s) under their revision guard (`marriage._mutate`) and the
order row's status flip guarded by its old status. Status steps that move no money (take, deliver, confirm, expire)
are DB-only; the money step (`ready → done`, `refund → refunded`) follows in the same request, the next poll of either
player, or the housekeeping (`run_housekeeping`, about once a minute from the server's maintenance loop) — so a provider is paid
while both players are offline.

## Order states (`svc_orders.status`)

```
talk ──accept──▶ working ──done──▶ delivered ──confirm / 24 h──▶ ready ──▶ done (95 % paid, 5 % burned)
  │                 │  ▲              (a spec with deliver + confirm 'auto' goes working → ready at once)
  │ decline/cancel  │  └── take ◀── held ◀── order (fixed price: paid at once)
  ▼ /12 h           ▼ decline/72 h        │ cancel/decline/24 h
declined/cancelled/expired   refund ──▶ refunded (100 % back)
'wo' talks (legacy):  talk ──accept──▶ linked  (a work_service_orders row at the agreed price, its own flow)
```

Legacy workplace orders (`work_service_orders`) keep their states (requested → accepted → ready → completed, or
refund_pending → cancelled/declined). Orders created by this build carry `data.market = 1`: priced ×mult, paid 95 % with
`work_service_orders.fee` = the burned 5 %. Orders made before this build keep their old terms (100 %, no fee).

## API contract for career modules

```python
from game import service_market as sm

sm.register(career: str, service_id: str, spec: dict) -> dict      # at import time of the career module
sm.get_spec(career, service_id) -> dict | None
sm.quote(db, provider_sid, career, service_id, qty=1) -> dict       # {base, mult, mode, price|None, lo, hi, qty, on, fair, usual}
# 🎪 fair: the percent off while the provider's Hội chợ việc làm booth for that career is open (game/town_fair.py
# discount; legacy_quote too), never below lo; usual: the price without it. 0 / the same price outside a fair.
sm.bounds(spec, base, qty=1) -> (lo, hi)
sm.open_orders(db, provider_sid, career=None, service=None) -> list[dict]   # paid orders waiting: status 'held' | 'working'
sm.order_of(db, order_id) -> dict | None
sm.deliver(store, provider_sid, order_id, result: dict | None = None) -> dict   # the provider finished (runs the hooks; idempotent)
sm.deliver_in_commit(db, provider_sid, order_id, result=None) -> str            # same, inside your own transaction
# or, from a game command: result['svc_done'] = [{'order': id, 'result': {...}}]  (storage.py → sm.command_commit)
sm.fee_of(price) -> int ; sm.FEE_PCT ; sm.ServiceError (a refusal: ServiceError(message, code, status))
```

`spec` keys (only `name` and `base` required; unknown keys raise `ValueError`):

| key | type | meaning |
|---|---|---|
| `name` | str ≤ 60 | what the buyer sees |
| `base` | int ≥ 1, or `callable(db, provider_sid) -> int` | the NPC price of one unit (cheap: ≤ one indexed query; it runs per directory card) |
| `icon`, `desc`, `unit`, `note_hint` | str | emoji, one line, unit name ("đêm", "tấm ảnh"), the note box's placeholder |
| `duration` | int minutes | shown |
| `floor` | int xu | lowest unit price ever (negotiation included); e.g. a birth room `floor=500_000` |
| `max_price` | int xu | most one order may cost (default 50 M; higher only when declared) |
| `qty_max` | 1…30 | units per order (nights) |
| `work_hours` | int | hours a taken order may wait before the buyer is refunded |
| `deliver` | `callable(db, provider_sid, buyer_sid, order) -> dict \| None` | the real effect, inside the transaction that marks the work done; raise `ServiceError` to refuse (order stays open); its dict (JSON ≤ 4 KB) is kept as `order['result']` and shown to both |
| `on_buyer` / `on_provider` | `callable(state, order)` | change the buyer's / provider's save inside the settlement transaction, once |
| `confirm` | `'auto'` \| `'buyer'` | 'auto' (needs `deliver`): paid at once; 'buyer': the buyer confirms (or 24 h). Default 'auto' with deliver |
| `requires` | dict of `life_day`, `chapter`, `story`, `married` | what the buyer needs |
| `check` | `callable(db, buyer_sid, buyer_state) -> str` | '' or the refusal shown to the buyer |
| `can_provide` | `callable(provider_state) -> str` | '' or why this player cannot sell it (default: the career is started) |
| `pay_to` | `'wallet'` \| `'career'` | where the provider's 95 % goes |
| `open` | `{action, data, label}` | **own-flow listing**: the module books, holds and pays; the card's button runs this client action (app.js `handleAction`, allowlisted in service-market.js) with `data` + the provider row's `data` |
| `providers` | `callable(db, limit, offset) -> [row]` | own-flow: the providers listed now; row = `{sid, price, on, stars (sum), rated, deals, at, data, title?, why?}` |
| `offer` | `callable(db, provider_sid) -> row \| None` | own-flow: one provider's row, listed (`on`) or not (`why`), for the provider card and 🧰 |
| `setup` | `{action, data, label}` | own-flow: where the provider sets price and open / closed (🧰 links there) |
| `note_check` | `callable(note) -> str` | '' or why the buyer's note is refused, checked at the order / offer before any money moves (📻 a ticker line is moderated before escrow, game/radio_station.py) |

The `order` dict given to hooks: `{id, career, service, buyer, provider (sids), buyer_pid, provider_pid, qty, price, fee,
paid, note, input (what the provider sent with deliver), result, created_at}`.

Example (the childbirth room): `sm.register('nurse', 'birth_room', dict(name='Phòng sinh', icon='🍼', base=200_000,
floor=500_000, unit='lượt', requires=dict(married=True), deliver=assist_birth, on_buyer=add_baby_card))`.

## Own-flow listings (🏥 player birth rooms, 📸 player photographers)

`game/birth.py` (birth_stays, SCHEMA 65) and `game/photo_studio.py` (photo_orders, SCHEMA 66) keep their own booking,
escrow and payout. They register **listings** here with `open` (`birth.install()`: `('homestay' | 'hotel', 'phong_sinh')`;
`photo_studio.install()`: `('photobooth', <package>)` for each of the five packages). `server.py` calls
`service_market.install_own()` at start and the market's seed calls it too; a refused spec is logged, never a crash
(`install(strict=True)` raises: the tests).

* Directory: own-flow rows come from `providers` (not svc_settings) and merge into the same sort (⭐ uy tín with the
  module's stars, 💰 giá, 🟢 online, 🤝 nhiều đơn = births / photos delivered) and pages. A birth room: open rooms of
  that career (`birth_rooms.career`; only homestay owners may open one today, the hotel listing stays empty). A
  photographer: a **public** photobooth place, the studio open, the account ≥ `ACCOUNT_DAYS` (3) old, each package at
  that studio's price.
* The card opens the module's sheet: 🏥 Nhà & Gia đình › 👶 Đón con chung with that room preselected
  (`marriage` `{tab:'family', section:'children', room}`); 📸 the order sheet of that studio and package
  (`photoStudio` `{tab:'order', place, pkg}`).
* Refused here (409): `POST order` / `offer` (`own_flow`), `settings` (`own_settings`), `sm.quote` (`own_flow`): never a
  second payment path or a second escrow. Hooks `deliver`, `on_buyer`, `on_provider`, `confirm`, `pay_to`, `legacy` and
  `qty_max` > 1 are refused at register.
* 🧰 Dịch vụ của tôi shows them (listed or not, and why) with a button to the module's settings (birth room: price ≥
  500 000, ≤ 5 000 000, open; photo: ×1–×5 of the NPC base, open); no ×N, no switch.
* No table, column or save key (works on SCHEMA 68 as is).

Dev only: `MNL_SVC_DEMO=1` registers 🧋 Pha trà tại nhà (milk_tea) for the browser walk-through.

## 🏍️ Bảo dưỡng xe máy and 🩺 khám / tiêm thú cưng (moto, vet: worked at the bench)

`game/moto_service.py` registers `('moto', 'bao_duong')` (base 50 xu, one motorbike per order: qty_max 1, since the
market's `check` cannot see qty; needs a motorbike in the garage) and `game/vet_service.py` registers `('vet', 'kham')` / `('vet', 'tiem')` (base = the NPC clinic's own price in
`pets_content.VET` / `VACCINE`, one pet per order, needs a pet that needs it). The ×3 default price, escrow and the 5 % fee are the
market's own.

* The provider takes the order, opens it in the career's 🛎️ orders card and works three server-graded steps
  (`xm_svc` / `ty_svc` `{order, service, step, value}`; tyre pressure + oil + safety picks / weighing + exam order +
  advice, or weighing + temperature + injection order). The finished job lands in the career's `svc_ok` list (grade
  1–3 from the slips). `{order, drop: true}` throws away an untouched stale job (cancelled / refunded order): no money, no xp.
* `deliver` reads the provider's **committed** save and refuses (`moto_bench` / `vet_bench`) until that order is in
  `svc_ok`: a hand-made `done` cannot fake the work.
* Buyer's save, once: 🏍️ the warned bike first, then the others: `journey.xe_care = {v:1, cars:{vid: last_day}}` for
  `CARE_DAYS` (10) days, and a pending 🎲 "xe sắp hỏng" warning on that bike is cleared as prevented; `rui` halves the
  chance of a breakdown of a cared-for bike. 🩺 the same effect as the NPC clinic (pets.py `jr_pet_vet` / vaccine),
  with the same bond / week points / tricks (`pets._care`).
* 🩺 only a vet still hired at the clinic is listed (`can_provide`). A job may be dropped only while untouched; a started
  one is finished to leave the book (its mistakes stay in the grade).
* 🛑 `MNL_MOTO_SVC_OFF=1` / `MNL_VET_SVC_OFF=1`: `done` refused (`moto_off` / `vet_off`); orders keep settling and
  refunding as usual. No table, no column; `journey.xe_care` is optional and 2.4.71 keeps it untouched.

## 🔧 Độ xe cho người chơi (tuning: worked at the bench, 2.5.2)

`game/tuning_service.py` registers `('tuning', 'do_dong_co')` ⚙️ độ map động cơ (base 120 xu), `('tuning', 'do_khung_gam')`
🔩 chỉnh khung gầm (base 120 xu) and `('tuning', 'bao_duong_do')` 🧰 bảo dưỡng xe độ (base 80 xu); one vehicle per order
(qty_max 1). `check` needs a motorbike or car that can race (game/racing.py `owned`); 🧰 also needs a fitted part that is worn.

* What a player sells is what the NPC garage (🔧 Xưởng Tư Pít-tông, `jr_tune_buy`) does not: a hand-tuned map
  (+`racing.FX_POWER` 3 % power) or a chassis set-up (+`racing.FX_GRIP` 4 grip) for the next `racing.FX_RACES` 10 races of
  that vehicle, or a full service (every fitted part back to 100 %). Stages are only sold by the garage, so nobody buys a
  stage cheaper from a player.
* The tuner works the order in 🔧 Xưởng độ xe → Xe của người chơi (`dx_svc {order, service, step, value}`, three
  server-graded steps, the illegal fits refused at the bench); the finished job lands in `careers.tuning.ext.data.svc_ok`
  and `deliver` reads the tuner's **committed** save and refuses (`tuning_bench`) until that order is there.
* Buyer's save, once: `racing.service_apply` on the vehicle being ridden when it can race, else the one with the most
  parts (`journey.tune.cars[vid].fx` or the wear reset).
* 🛑 `MNL_TUNING_SVC_OFF=1`: `done` refused (`tuning_off`); orders keep settling and refunding as usual. No table, no
  column; `journey.tune` is optional and 2.5.1 keeps it untouched.

## HTTP

GET `/api/svc/dir?career=&service=&sort=rating|price|online|deals&offset=` · `/api/svc/provider?pid=` · `/api/svc/inbox`
· `/api/svc/mine` (reads the save: which careers the player can sell) · `/api/svc/catalog`.
POST `/api/svc/order {pid, career, service, qty?, note?, rid, expected_price?, place?, offer_id?}` ·
`offer {…, price}` · `answer {order, op: accept|counter|decline|cancel, price?, ask?}` · `take|decline|cancel|confirm {order}` ·
`done {order, result?}` · `rate {order, stars, comment?}` · `flag {order, text}` · `settings {career, service, on, mode, mult, note?}` · `receive {}`.
Admin: GET `/api/admin/svc`, POST `/api/admin/svc {op:'close', order, note}`. The ticker (`/api/news` → `me.svc`) carries the badge.

## Legacy workplace orders (today's orders keep working)

* Registered as `(career, 'job')` for every career of `workplace_business.ORDERS` and `('quay', 'dish')`.
* The place card and `/api/work-visits/place` show the player price (`offers[].price` = NPC × mult, `base` = NPC price,
  `nego`, `lo`, `hi`) and `market` (provider's pid, listed, mode, mult, ⭐ reputation).
* A provider who turns a legacy service on in 🧰 lists it in the directory: anyone may order there, whatever the place's
  visibility (never a blocked player, never a closed place).
* Exploit guards kept: the quầy visitor profit bonus stays capped at 2× the dish's base price
  (`player_service_tasks.VISIT_BONUS_RATIO`) and is computed on what the counter receives; the workplace staff profit
  bonus (40 %) counts only the real margin at the NPC price (`min(paid, base) − costs`), never a friend's overpayment.
* Escrow now comes from the wallet, then the bank account; the 5 % fee is burned at settlement.

## Rollback (2.4.66)

Additive only: new tables, one column with a constant default (`work_service_orders.fee`), indexes; no save key, no FK, no
backfill. 2.4.66 on a database at 63: startup runs no DDL; it validates saves holding ×3 `player_order` prices (≤ 1 M),
reads the new rows, and settles a ready legacy order at its own terms (100 %, no fee). An order made by this build that
2.4.66 has not accepted is refused there as a changed offer (`stale_offer` / `service_unavailable`); the buyer cancels it
for a full refund. Generic `svc_orders` are invisible to 2.4.66: their escrow waits in the table and settles when this
build is back. (`tests/test_service_market_compat.py`)

## Rollback runbook (to 2.4.68, live)

2.4.68 (289df99d) knows none of this release's tables or careers. Its startup runs no DDL on a database at 75 and every
table here stays (nothing is dropped), but it must never meet money this build still holds:

* a legacy workplace order made here (`work_service_orders.data.market = 1`, priced ×3…×10 of the NPC price) would be
  settled by 2.4.68 at its own terms: paid in full **and** the 40 % staff profit bonus computed on the whole price
  (`work_visits.py` → `player_service_tasks.credit_staff_bonus` without `base`);
* `svc_orders`, `photo_orders`, `birth_stays`, `hotel_stays` escrow is invisible to 2.4.68 (frozen until a roll forward),
  and a pending `live_effects` row of kind `photo` stays pending there.

Steps, in order, on this build:

1. Stop new money coming in: set `MNL_SVC_OFF=1`, `MNL_BIRTH_OFF=1`, `MNL_HOTEL_OFF=1`, `MNL_PHOTO_DIRECT_OFF=1` (also
   `MNL_WEDSVC_OFF`, `MNL_RADIO_OFF`, `MNL_RESTORE_OFF`, `MNL_RESEARCH_OFF`, `MNL_MOTO_SVC_OFF`, `MNL_VET_SVC_OFF`,
   `MNL_FAIR_OFF` if wanted; use `1`, which every
   switch reads as on) and restart. Paid orders keep settling and refunding meanwhile.
2. Look: `python scripts/svc_drain.py` (dry run: what is held, per table and status, in xu).
3. Drain: `python scripts/svc_drain.py --write`. Hotel stays are refunded through `hotel_stay._refund_db`; talks
   cancelled; held / working orders refunded in full; delivered work confirmed and paid (95 % / 5 % burned); every ready
   and refund row settled now; this build's legacy market orders refunded (requested / accepted) or settled at 95 / 5
   with the real-margin bonus (ready); photo orders declined with the price back and every pending `photo` refund paid
   into its save; birth bookings refunded to the payer (a `marriage_effects` 'wallet' row, which 2.4.68 applies). It
   prints the counts again: everything should be 0 (exit code 1 otherwise, with the rows that refused in `log`; run
   it again, a busy save just retries).
4. Strip the new careers from the saves (an older build refuses a save with a career it does not know):
   `python scripts/strip_new_careers.py strip --careers reception,teller,restore,research,radio,moto,vet --db --archive removed.jsonl`
   (counts), then the same with `--write` (that list is the script's default). Keep `removed.jsonl`: `restore` puts it
   back after rolling forward.
5. Deploy 2.4.68.

Rolling forward again: deploy this build, then `python scripts/strip_new_careers.py restore --db --archive removed.jsonl --write`.
