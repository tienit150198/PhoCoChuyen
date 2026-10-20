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

The `order` dict given to hooks: `{id, career, service, buyer, provider (sids), buyer_pid, provider_pid, qty, price, fee,
paid, note, input (what the provider sent with deliver), result, created_at}`.

Example (the childbirth room): `sm.register('nurse', 'birth_room', dict(name='Phòng sinh', icon='🍼', base=200_000,
floor=500_000, unit='lượt', requires=dict(married=True), deliver=assist_birth, on_buyer=add_baby_card))`.

Dev only: `MNL_SVC_DEMO=1` registers 🧋 Pha trà tại nhà (milk_tea) for the browser walk-through.

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
