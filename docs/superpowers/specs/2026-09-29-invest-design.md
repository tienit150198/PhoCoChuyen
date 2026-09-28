# Đầu tư cá nhân (personal investing): design

Status: implemented in `game/invest.py`, `public/js/v4/invest.js`,
`public/css/invest.css` and `tests/test_invest.py`. The lead wires it into
`engine.py` and `journey.js` (see "Wiring").

## Why

The owner asked for this: "when you have enough money, try investing in crypto,
and sometimes you suddenly lose money, sometimes you suddenly profit". It should
be educational, fun and fair. Money is in-game **xu**. It has no real value and
cannot be bought or cashed out.

The lessons the feature teaches without lecturing:

1. **Savings are slow but safe.** Interest is small and adds up, and taking the
   money out early costs you the interest.
2. **A volatile asset can jump or crash overnight.** Fees make it expensive to
   trade in and out all the time. Nothing is realised until you sell.
3. **A "guaranteed high return" is a scam.** It pays a little first to build
   trust, then disappears with the money (a rug pull). Saying no is the win.

## Unlock

Investing opens once the wallet has held **≥ 500 xu at least once**
(`journey.stats.max_wallet`, which only goes up). Before that, the wallet sheet
shows a teaser card: "Khi ví từng có 500 xu…", a progress bar and the Mây Coin
sparkline as a preview. The market moves every life day even while locked, so
the chart is already alive when the player unlocks it.

## State: `s['journey']['invest']`

It lives under the journey, next to the wallet it moves money in and out of.
`journey.validate()` accepts extra keys, and `journey.public()` does not copy
raw keys, so nothing leaks. It is added by `invest.migrate(s)`, which is
idempotent and uses setdefault for older invest dicts. `validate` and `public`
tolerate its absence (for example `engine.new_state()` before the first
migration).

```
version   1
day       last life day the market/savings/scam were advanced to
price     Mây Coin price in hundredths of a xu (10000 = 100 xu)
prices    ≤ 30 recent prices, oldest first, last == price
coin      {units (thousandths of a coin), basis (xu paid incl. fees, for units held),
           realised (xu), fees (xu), trades}
saving    {balance, term_day (life day the current 7-day term began),
           pending (thousandths of a xu, accrued this term), earned, forfeited}
scam      None | {kind, stage: offer|joined|declined|expired, day, stake, paid,
                  pay_days (1..2), paid_days}
log       ≤ 20 rows {day, kind, text}
stats     {declined, joined, lost, next_scam}
badges    ['scam_spotter', 'rug_lesson', 'first_interest', 'first_coin']
```

All numbers are ints. Fractions use fixed-point units (hundredths of a xu for
the price, thousandths of a coin, thousandths of a xu for accrued interest).

## Rules

### Savings ("Gửi tiết kiệm", neighbourhood bank)

* Interest is **0.3 % per life day** on the balance. It accrues in `pending`
  and is added to the balance every **7-day term** (so it compounds weekly).
* You can deposit or withdraw at any time. Withdrawing during a term
  **forfeits the pending interest of that term**. The client shows the exact
  amount before you confirm. The principal is never lost.
* Deposits need 1 xu or more (or "all"), and never more than the wallet holds.

### Mây Coin (fictional crypto)

* Base price is 100 xu, with 20 seeded days of history created at migration.
* Each life day it moves once. The RNG is `random.Random(f"may|{seed}|{day}")`:
  * 4 %: **crash** −30…−50 %
  * 5 %: **pump** +25…+45 %
  * otherwise a normal move of gauss(+0.4 %, 5.5 %), clamped to ±15 %
    (typical daily swings of about ±8 %)
  * plus a gentle pull toward the base price, `+4 % × ln(base/price)`, so the
    walk stays in a playable band
  * the price is clamped between 1 xu and 100,000 xu.
* **Fee: 2 %** on every buy and sell (minimum 1 xu). The minimum trade is
  10 xu.
* Buy `{amount}` or `{all}`: the wallet pays `amount`, and `amount − fee`
  becomes coins. The cost basis includes the fee.
* Sell `{amount}` (xu value to sell) or `{all}`. Asking for more than the
  holdings are worth is rejected. Proceeds are gross − fee. Realised P&L is
  proceeds − the proportional basis. Unrealised P&L is value − basis.
* When the player holds coins, big days (pump or crash) add a line to the
  `end_day` effects.

### Scam offers ("Dự án lãi khủng")

* An offer can appear only when investing is unlocked, no other scam is
  running, and the life day is ≥ `next_scam`. The daily chance is 8 %,
  seeded by `scam|{seed}|{day}`. There are four fictional projects
  (MoonMây Token, Vàng Số 4.0, Nông Trại Ảo X100, Trà Sữa Coin). Each one
  promises "lãi 30 %/tuần" and gives a bonus for inviting friends.
* The offer stays open for 3 life days. The card lists the red flags:
  guaranteed high return, "không rủi ro", referral bonus, and pressure to hurry.
* **Join** (`iv_scam_join {amount}`, 20 xu up to the wallet): the stake leaves
  the wallet. For the next 1–2 life days (seeded), the project pays **4 % of
  the stake** per day into the wallet, which is real money used as bait. On
  the following day it **vanishes**: the stake is gone. The log and
  `end_day` effects explain what happened. The player gets the badge
  "Bài học đắt giá" (`rug_lesson`).
* **Decline** (`iv_scam_decline`): the player gets the badge "Tỉnh táo trước
  lãi khủng" (`scam_spotter`) and a short explanation. If the offer is
  declined or simply expires, a line a few days after the offer day says the
  project collapsed and everyone who joined lost their money. That confirms
  the lesson.
* After a scam ends there is a 10-day cooldown before the next one.

### Invariants

* Money moves only between the journey wallet and the invest holdings. Every
  wallet change goes through `journey._wallet()`, so the history rows,
  `max_wallet`, debt flags and titles all work. The history kind is the
  existing `'invest'` (📈 in the wallet log), with a clear label ("Mua Mây
  Coin", "Gửi tiết kiệm", "Lãi từ dự án …").
* No command can make the wallet negative. Every amount is an int with
  bounds. Any failure raises `GameError` before anything is changed.
* Everything is deterministic from `journey.seed` and the life day.
  `on_life_day(s)` catches up from `invest.day` to `journey.life_day`, so it
  is idempotent and safe to call after any action.

## API

```python
invest.initial(seed=0, day=1) -> dict
invest.migrate(s) -> s                 # setdefault s['journey']['invest']
invest.validate(s) -> None             # strict; no-op when absent
invest.on_life_day(s, result=None) -> list[str]   # catch up; notes go to result['effects']
invest.apply(s, name, payload) -> dict            # mutates s, raises GameError
invest.action(s, name, payload) -> (s, result)    # apply + journey.after + validate_state
invest.public(s) -> dict                          # served as state.invest (root of the public state)
invest.unlocked(s) -> bool
```

The commands, all prefixed `iv_`:

| Command | Payload |
|---|---|
| `iv_save` | `{amount:int}` or `{all:true}` |
| `iv_withdraw` | `{amount:int}` or `{all:true}` |
| `iv_buy` | `{amount:int ≥ 10}` or `{all:true}` |
| `iv_sell` | `{amount:int ≥ 10}` or `{all:true}` |
| `iv_scam_join` | `{amount:int ≥ 20}` |
| `iv_scam_decline` | `{}` |

## Client

`public/js/v4/invest.js`:

* `investView(env)`: the full "Đầu tư" sheet. It shows the wallet strip, a
  savings card, a Mây Coin card with an inline-SVG sparkline and P&L, the
  risk note "Tiền ảo có thể mất trắng. Chỉ dùng tiền nhàn rỗi.", the scam
  card when there is an offer, recent notes and badges. The amount chips are
  50/100/200/Tất cả.
* `investEntry(env)`: a small card for the wallet sheet. It is a teaser when
  locked, and a button with a "lời mời mới" badge otherwise.
* `investAction(action, data, el, env)`: handles the `iv*` data-actions (chip
  selection, confirm-then-send). Commands go through `env.cmd`, and the app
  re-renders on its own on `state`.

The styles are in `public/css/invest.css`. They use theme tokens only and
are phone first (390 px), with container queries on `sheet`.

## Wiring (done by the lead)

See the final report. There is one import and about one line each in
`migrate_state`, `validate_state`, `apply_action` (routing and
`on_life_day`), `public_state`, `journey.js` (view, entry, action) and
`index.html` (the css link). No `journey.py` change is required, because the
history kind `'invest'` already exists. An optional journey title is proposed
in the report.
