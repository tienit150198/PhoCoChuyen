# Chuyện đời thường & tình làng nghĩa xóm: design

Status: implemented in `game/life.py` (rules), `game/life_content.py` (content),
`public/js/v4/life.js`, `public/css/life.css` and `tests/test_life.py`.

## Why

The owner asked for this: "being bullied at work, getting scammed, parents
bullying the teacher… then you have to blow off steam, lose money or spend
money. Heartbreak, and then everyone comforts you and invites you out. After a
scam the neighbours chip in or bring a gift. More tình nghĩa. Make it happen
OFTEN." A later request added **bị đặt điều**: rumours from the street's
"camera chạy bằng cơm", always based on something the player really did.

## State: `s['journey']['life']`

It is added by `life.migrate(s)` (setdefault only, no retro events: old scam
losses are marked as already seen). `validate` and `public` tolerate its absence.

```
version  1
day      last life day processed (catch-up like invest)
spirit   tinh thần 0–100, starts at 70
mark     spirit at the last day close (for the summary delta)
bonds    {cast id: 0–100} for the journey CAST (Bà Tám, Cô Ba, Cô Lụa, Anh Khoa, Chú Tư, Bé Tí, Bà Sáu)
pending  the life card (see below) or None
seq, log ≤ 40 rows (Nhật ký đời thường), recent {variant id: day}
queue    ≤ 4 scams lost elsewhere, waiting for the neighbours
seen     keys of scams already handled; iv_lost (invest stats.lost already seen)
hangover life day the hangover lands; coped: life day of the last xả stress
outing   {day, who} last outing with a neighbour (fact for a rumour)
rumour   life day of the last rumour
stats    hard, warm, outings, given, received, spent, scams, rumours, coped
```

Warmth (tình làng nghĩa xóm) is the mean of the bonds.

## The day turns

`life.after()` runs in `engine.apply_action` after `journey.after` and
`invest.on_life_day`. When the life day moved (an `end_day`):

1. Spirit recovers a little: +4 below 40, +2 below 55, +1 below 70; +2 on a
   calm (rest) day, +1 on a festival day, +1 when 3+ jobs were done. A hangover
   costs 6.
2. A card still undecided from the previous day takes its defaults (the free,
   gentle choice at each stage), so nothing is ever stuck.
3. Scam losses elsewhere are picked up: an incident whose `last.lines` has a
   `scam_loss` wallet/fund line, and Mây Coin's `stats.lost` going up (a rug
   pull). They queue a **scam** card that goes straight to *cả xóm góp*.
4. The new day's card is rolled (seeded `life|seed|day|…`, deterministic):

| Order | Card | When | Chance |
|---|---|---|---|
| 1 | scam help | a queued scam loss | always |
| – | nothing | life day 1–2 | – |
| 2 | ốm (sick) | spirit < 15 | 50 % |
| 3 | buồn quá tiêu tiền | spirit < 35, day > 5 | 35 % |
| 4 | bị đặt điều | a real fact, ≥ 5 days since the last one | 30 % |
| 5 | hard day | days 3–5: 18 % (mild variants only); later 36 % (halved below spirit 30) | |
| 6 | hàng xóm rủ đi chơi | spirit < 40 | 60 % |
| 7 | hàng xóm gặp chuyện | day > 5 | 13 % |
| 8 | chuyện vui nho nhỏ | | 16 % |

Measured over 60 days (tests): about 0.5 cards per life day, 0.3–0.4 hard days
per day. No identical variant within 10 days (20 for neighbours in trouble).
The workplace of the day that closed picks the hard-day pool: its own variants
weigh 2.5, group variants 1.6, everyone's 1.

Story mode only: with the story off, the layer only keeps its day in sync.

## Cards and stages

A card walks through stages; each stage has 2–9 choices, each with a visible
cost and effect (`−40 xu · tinh thần +25`). Paid choices need the money in
the wallet: disabled with the reason ("Ví còn 12 xu", "Ví đang nợ 50 xu").

```
hard:   react → gop (bị lừa 85 %, big xui 45 %) | comfort (75 %, 95 % when spirit < 45,
        always after thất tình and bị đặt điều) | done
        comfort → yes (outing, bond +) | self → cope | no
scam:   gop → done           (a loss elsewhere; spirit −8 when the news spreads)
ask:    big | small | a hand | "kẹt quá" → done   (bond +8/+5/+4)
joy:    ok → done            (spirit + when it happens)
impulse: all | one | clear → done
sick:   rest | doctor → comfort (someone brings cháo) → done
invite: comfort → …
done:   the trail + net chips; lf_close clears it
```

On firing, a hard day lands its spirit hit (authored × 1.6) and its forced loss
(capped by what the wallet holds). Comfort outings give their authored spirit ×
0.7. **Cả xóm góp** gives back 40–90 % of the loss (more when warmth is high)
from 3–5 neighbours, listed by name with amounts, or a gift (a phone after a
stolen phone, a bag of rice, a basket of food, flowers + a card).

## Content (game/life_content.py)

* 56 hard days: bị ăn hiếp chỗ làm 9, khách làm khó 9, bị lừa 8, chuyện xui 8,
  bị đặt điều 8, phụ huynh làm khó 7, thất tình 7. Career groups: EMPLOYED
  (hired careers), OWNERS, FACING (customer-facing), STOCKED, teacher-only.
  Every career has at least 3 hard days of its own.
* 16 comfort visits (6 of them "advice" for rumours: "Kệ người ta, sống thật là
  được."), 4 gifts, 9 ways to xả stress (karaoke, trà sữa + shopping, Đà Lạt,
  Vũng Tàu, online order with a 50 % "hàng không giống ảnh" twist, uống một
  mình with a hangover, bờ hồ, ngủ nướng, gọi mẹ), 8 neighbours in trouble,
  10 small joys, 5 impulse buys, 3 sick days.
* Tokens `{anh}`, `{ay}` (the ex: cô ấy / anh ấy), `{place}`, `{gossip}`,
  `{who_name}`; texts may be `dict(male=…, female=…, none=…)`.

### Bị đặt điều (rumours)

Only from facts `life.facts()` reads from the real save:

| fact | when | example |
|---|---|---|
| `late` | 5+ jobs in the closed day, or 3 workplaces on 3 consecutive days | "Đêm nào cũng về khuya…" |
| `spend` | ≥ 60 xu out of the wallet on life/invest in 3 days | "Tiêu hoang thế…" |
| `draw` | ≥ 150 xu withdrawn in 3 days | "Rút tiền liên tục…" |
| `seen` | an outing with Anh Khoa in the last 3 days (not for male players) | "Có gì với nhau…" |
| `breakup` | a thất tình card in the last 10 days | "Nghe nói bị bỏ vì…" |
| `stock` | a stock delivery booked on the closed day (shops, farm) | "Hàng về tối ngày…" |

Innuendo only; the story always treats the gossip as wrong. Choices: kệ, nói
chuyện nhỏ nhẹ, đăng giải thích, nhờ Bà Sáu / Cô Lụa, mời ly cà phê. A warm
neighbour always follows with short advice. Gossips: Cô Hai Loa, Thím Bảy,
Chị Tư Zalo.

## Record shape (for other modules, e.g. the neighbourhood board)

Every finished card appends a log row, plain JSON:

```
{id: 'lf-12', day: 14, kind: 'hard'|'scam'|'ask'|'joy'|'impulse'|'sick'|'invite'|'cope',
 cat: 'an_hiep'|'phu_huynh'|'khach'|'lua'|'that_tinh'|'xui'|'dat_dieu'|'xom'|'vui'|'buon'|'om'|'ru'|'xa',
 title: str ≤ 80, emoji: str, who: [neighbour ids involved: CAST ids, 'work', 'friends'],
 text: short outcome ≤ 160, spirit: net int, money: net int (xu),
 fact: None | 'late'|'spend'|'draw'|'seen'|'breakup'|'stock',   # rumours only
 gossip: None | 'co_hai_loa'|'thim_bay'|'chi_tu_zalo'}          # rumours only
```

A rumour is a row with `cat == 'dat_dieu'`, its `fact` and its `gossip`.
`life.GOSSIPS` and `journey.CAST` give names and emoji.

## Commands (prefix `lf_`, routed in `engine.apply_action`)

| Command | Payload |
|---|---|
| `lf_choose` | `{id, choice}`: the pending card's current stage |
| `lf_cope` | `{choice}`: xả stress on your own, once per life day, when no card is waiting |
| `lf_close` | `{id}`: clear a finished card (or a joy card) |

`life.action` = apply + `journey.after` + validate, like `invest.action`. Money
goes through `journey._wallet` with the new history kind `'life'` (🌿).

## Client

* `life.js` owns a `<dialog id="lfScene">` (styled like the journey scenes).
  It opens by itself at a calm moment: no other dialog open, the sheet closed or
  on the journey home, no live shift decision (it waits while a shift is open
  with work done, an incident, a happening or a case). So after `end_day` it
  appears when the day summary is closed, or right after opening the next day.
  "Để sau" (×) puts it off for the session; it stays on the journey home.
* Journey home: a card with the spirit meter, warmth, the waiting story and
  "Xả stress" / "Nhật ký đời thường". Wallet: an entry row. Sheet
  `jrView='life'`: xả stress grid, neighbours with hearts, the log.
* The day summary shows "Tinh thần 62/100 · Ổn áp (+3)" and the waiting story.
* The HUD shows a small blinking dot while a card waits.

## Wiring

`engine.py`: import, `migrate_state`, the `lf_` route, `after` hook,
`public_state` (`state.life`), `validate_state`. `journey.py`: `'life'` in
`HISTORY_KINDS`. `journey.js`: view, home card, wallet entry, action prefix,
boot, history emoji, HUD dot. `app.js`: one summary line. `index.html`: css.

## Not done

The optional AI "Tâm sự" chat was skipped: persona AI needs a career NPC and
a new server route, and another agent is reworking the persona prompt.
