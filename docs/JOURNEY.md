# Hành trình (journey layer)

One person, one small neighbourhood, many workplaces. The journey turns the
collection of careers into a single life story: chapters with short neighbour
dialogue, workplaces that open chapter by chapter, a personal wallet with daily
living costs, a maturity level, skills and titles.

Rules live in `game/journey.py`. The client (`public/js/v4/journey.js`,
`public/css/journey.css`) only renders `state.journey` and sends `jr_*`
commands.

## Story on/off

`s['journey']['story']` decides whether the rules bite.

| Where the state comes from | `story` | Effect |
|---|---|---|
| `engine.new_state()` (unit tests, tools, sandbox) | `False` | Every workplace open, no wallet costs, no gating, no scenes. Day luck still rolls. |
| New session on the real server (`Store(story=True)`) | `True` | Full journey. |
| `MNL_DEV=1` server (browser sweeps) | `False` | Same as tests, so sweeps can open every career. |
| Imported save / old save migrated on load | `True` | Started workplaces stay open, chapters fast-forward. |

`server.py` builds `Store(db, story=os.environ.get("MNL_DEV") != "1")`.

## State (`s['journey']`, no schema bump)

`version, story, seed, gender (None|'male'|'female'), intro, chapter (1..7),
done[], unlocked[], wallet, life_day, paused{career: day}, titles{id: day},
equipped, history[≤120], news[≤12], news_seq, clean_days, in_debt, days[≤60],
stats{...}`. Added with `setdefault` in `migrate_state`; validated in
`journey.validate()` (called from `validate_state`).

## Chapters and unlocks

| # | Chapter | Goals (read from the real save) | Opens |
|---|---|---|---|
| 1 | Chuyển tới khu phố | close 1 day · 3 tasks | milk_tea, grocery, delivery (from the start) |
| 2 | Hàng xóm quen mặt | work at 2 places · 10 tasks · withdraw to the wallet once | cafe_bakery, florist, mother_baby, restaurant |
| 3 | Có nghề trong tay | level 3 somewhere · 3 debt-free life days in a row · 3 places | pet_care, salon, repair, farm, homestay |
| 4 | Được tin cậy | 5 places · 6 titles · maturity 5 | customer_care, pharmacy, tour_guide, teacher, accounting |
| 5 | Bước vào văn phòng | hired at an office · 3 office days · 5 debt-free days | corp_accounting, tax_payroll |
| 6 | Người của khu phố | 8 places · maturity 8 · 15 titles | group_accounting |

Finishing chapter *n* opens the workplaces of chapter *n+1*. Office jobs still
need a real application (`employment.py`); the story mentions the CV line
"Có kinh nghiệm ở một nghề khác trong phố". `employment._unlocked()` asks
`journey.is_unlocked(s, career)`.

Locked workplaces are refused server-side on every non-internal career action
(`select_career`, `start_day`, …) with code `locked`. Before the intro is done,
`select_career` needs a chosen gender (code `no_profile`). A paused workplace
refuses `start_day` (code `paused`). `life_mode` is always refused.

Old saves: `migrate()` turns story on, keeps every started workplace unlocked
and fast-forwards chapters whose goals are already met (goals that need play
after the journey begins, `clean` and `draw`, are skipped during the
fast-forward).

## Money

* **Ví của bạn** starts at 60 xu. It is separate from each workplace's fund
  (the career `money` with its own ledger).
* **Ngày sống** goes up by one on every `end_day`, wherever it happens.
* **Living costs** per life day: 10 xu in chapter 1, +2 per chapter (max 20);
  60 % rent, 40 % meals. Paid from the wallet.
* **Idle upkeep**: every other started, unlocked, not-paused, not-employed
  workplace costs 4/7/11 xu (cozy/sunny/garden property tier) from its own
  fund (ledger category `upkeep`); anything the fund cannot cover comes from
  the wallet. The workplace you played that day pays its own ops bills
  instead, so nothing is charged twice.
* **Tạm đóng** (`jr_pause`, confirm, shift closed, not for employed places)
  stops upkeep; **Mở lại** (`jr_reopen`) costs 15 xu from the fund, else the
  wallet, and is free only if nowhere else is playable.
* **Rút về ví** (`jr_withdraw`): at most `fund − unpaid bills − 80 xu`.
  Ledger category `owner_draw`.
* **Góp vốn** (`jr_invest`): wallet → fund, category `owner_capital`.
* **Salary**: on payday the office salary moves from the career to the
  wallet (`salary_to_wallet`).
* Transfers go through `engine.money()` so the ledger invariant holds, then
  are removed from the career's earnings/costs/day totals: they are not
  income or expenses and are not taxable.
* **Debt**: the wallet may go negative (no game over). While it is negative
  the story does not advance; the home shows a clear notice and the way out.

## Growth

* **Maturity XP** = total career XP + 80 per workplace actually worked at.
  Level L needs `60·L·(L−1)` XP (max 30), names from "Người mới tới" to
  "Trưởng thành".
* **Skills** (the nine `employment.STRENGTHS`) grow from tasks served,
  weighted per career; levels 0–6.
* **Titles**: 59 (6 story, 10 journey, 20 career at level 3, 9 skill, 6 money,
  8 secret). Awarded once with the life day, celebrated by a scene, equippable
  (`jr_equip`), shown under the name on the journey home and on the stage HUD.

## Day luck

At every `end_day` the next day's pace is rolled per career:
calm 25 % / normal 55 % / festival 20 %, seeded by `journey.seed`, career and
day (`random.Random(f"mode|{seed}|{career}|{day}")`), day 1 always normal.
Calm days target 2 tasks, normal 3, festival 4. `settings.mode` is still
accepted (old clients) but ignored.

## Commands

All `jr_*` actions ignore the command envelope's `career`, like `settings`.

| Action | Payload |
|---|---|
| `jr_profile` | `{name?, gender?}` (gender `male`/`female`) |
| `jr_equip` | `{title: id \| null}` |
| `jr_seen` | `{ids: [news id, …]}` (acknowledge scenes) |
| `jr_withdraw` / `jr_invest` | `{career, amount}` |
| `jr_pause` / `jr_reopen` | `{career, confirm: true}` |

`result.journey = {chapters: [...], titles: [...]}` when something was
earned; `summary.journey` on `end_day` holds the life day costs.

## Public data

`state.journey` (per request, trimmed): story, gender, intro, chapter, done,
finale, unlocked, wallet, debt, life_day, living, places{fund, upkeep, paused,
employed, unpaid, withdraw_max}, titles [[id, day]], equipped,
equipped_title, secret (earned secrets only), maturity, skills, goals,
progress_paused, clean_days, history (last 30), news, suggested, tasks,
worked, stats.

`content.journey` (bootstrap): chapters with dialogue, cast, title
categories, titles (unearned secrets reduced to `{id, cat, secret}`), skills,
levels, reserve, reopen_fee, start_wallet, unlock_chapter.

## Client

* First run: arrive → "Bạn là ai?" (Nam/Nữ cards with a preview, name) →
  pick the first job among chapter 1.
* Journey home (the `home` sheet): character card, chapter card with
  objectives and one primary button to the suggested workplace, workplaces
  grid (fund, upkeep, paused, "💌 Có thư mời"), locked silhouettes.
* Sheets inside the home: titles, wallet, profile (name/gender change).
* Scenes (`<dialog id="jrScene">`): chapter complete → next chapter intro,
  new titles, one-time gender prompt for old saves, story replay. Scenes come
  from the server's `news` queue, so they survive reloads.
* Stage HUD (`#jrHud`): avatar, name, equipped title, wallet; opens the home.

Tests: `tests/test_journey.py`.
