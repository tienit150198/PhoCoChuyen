# Handoff — state of Phố Có Chuyện (30/09/2026, ~22:00)

Read this first if you pick the project up. It says what is live, where it runs, what is half-done, which
branch holds what, and what to do next, in order. Details live in the linked docs; this file is the map.

## 1. What is live

- **Production:** https://phocochuyen.io.vn runs **1.4.3** (02/10 12:20; see "1.3.0" below), 33 careers, PostgreSQL 16,
  on the **new server 103.195.238.178** since 30/09 21:00 (see §6 and §7).
- **Traffic (30/09 21:20):** ~370 players active in 5 min, ~560 in 15 min, ~1,340 in 1 h; 24,500 saves,
  ~2,000 accounts. Busiest minute so far: 30/09 20:59, 3,427 API requests (57/s, 41 commands/s).
- **Speed (server side, 21:50 on the new server):** command p50 ≈ 55 ms, p90 ≈ 105 ms at ~44 commands/s.
  On the old server the same evening: p50 130–180 ms, p90 400–590 ms. At 16:00 on 0.9.4 it was p50 918 ms.
  Slow *page loads* on weak mobile networks remain the main complaint (branch `coldload`, §4).
- **Capacity (measured 21:20 on live traffic):** one API request costs ~46 ms of CPU (game 38, PostgreSQL 6,
  nginx 1). At 54 requests/s the box uses 2.5 of 9 cores (28%). At 75% CPU it serves ~148 requests/s, i.e.
  **~2.6× the busiest minute so far**; the hard ceiling is ~200 requests/s. If traffic grows past ~2×, cut the
  38 ms of game CPU per request (profile `server.py` command path, save parse/validate) or add cores.
  A synthetic test with a light command (settings) reached 120 commands/s at p50 32 ms; do not use that
  number for capacity, real commands are heavier.
- **Peak hours:** 17:30–20:00 (Vietnam time). Avoid heavy work on the server then; hotfixes may still go out
  (the rolling release has no gap).

### What 1.3.0 added (02/10 03:47, branch rel-1.3, no DDL)
- **Hội chợ dân gian** (`game/fair*.py`, `public/js/v4/fair.js`): opens 03/10 for 5 days (`MNL_FAIR_START`,
  `MNL_FAIR_DAYS`; prod uses the defaults). Ô ăn quan and ring toss earn coins (90 + 45 xu/day); bầu cua, lô tô,
  chiếu trong (4% police raid) are small bets, max net loss 150 xu/day. Board `fair20261003`; 60 s after the fair
  closes, Top 1 gets 👑 Vua trò chơi and Top 2–10 🎪 Cao thủ hội chợ, once (`leaderboard_meta` `fair:<edition>`).
  Saves gain `journey.fair` and a `fair` ledger kind: **an older build rejects them, do not roll back past 1.3.0
  after 03/10** without a script.
- **Nghề bán kem** (`ice_cream`, chapter 3): apprenticeship with cô Hiền, homemade batches, Chứng chỉ làm kem.
- **Ký túc xá Hẻm 7** (`rent.kind = 'ky_tuc_xa'`, older builds reject it too).
- Chat per-conversation mute (`chat_members.muted_until`), group web push, dating-corner wait panel and 📣 invite.
- Ting ting (CC0 `public/audio/sfx/ting.mp3`) + speechSynthesis amount; nginx now serves `/audio/` like `/music/`
  (backup `/root/phocochuyen.nginx.bak130`).
- Wedding party: new lion, speakers, disco lights, feast tray, bouquet toss (20 xu), dance, fireworks, 10 CC0 tracks,
  groom picks the music.
- Payroll desk explains every cell (feedback #71); office date boxes auto-insert / and : with a 📅 picker;
  salon "cắt thêm" after layering (feedback #67).
- **1.3.1** (02/10 03:59): accessory colours (feedback #70): save key `wardrobe_colors`, live frames carry `look.tint`
  (web and live must roll forward/back together).
- **1.3.2** (02/10 04:21): room decor on a grid (`game/deco.py`, save `journey.deco`; `reno` kept in its 1.2.0 shape).
- **1.3.3 + 1.3.4** (deployed together 02/10 05:27): one colour palette (save root `colors = {v, have, wear, deco}`,
  40 xu/colour, 60 metallic; furniture tints by uid outside deco/reno; `wardrobe_colors` kept in its 1.3.1 shape),
  and real diplomas + souvenir photo for certificates (optional `earned_on`; album accepts JPEG).
- **1.4.0** (02/10 06:47): free drag-and-drop decor (`journey.decor` block; `journey.deco` kept as the 1.3.2 grid
  shadow so 1.3.2 still loads), wallpapers/floors/sheets, cats. `DECO_PER_MINUTE` (150).
- **1.4.1** (02/10 07:09): hunger/sleep bars, lunch strip and evening screen (`game/needs.py`, `journey.needs`,
  journey only; feedback #72).
- **1.4.2 + 1.4.3** (deployed together 02/10 12:20, rollback target 1.4.1-20261002070851):
  - 1.4.2: admin "Tổng quan đầu tư" (9 tabs, CSV, printable report; `docs/ADMIN_METRICS.md`,
    `scripts/verify_admin_metrics.sql`), new tables `stat_counters`, `stat_kpi_daily`, `stat_players` (created by
    admin_stats.ensure); optional consented Firebase/GA (inert until `SITE_URL` + `FIREBASE_*` are set; not set on
    prod); milk_tea.js 'reading data' crash fixed.
  - 1.4.3: 🍢 Ăn thêm (`jr_needs_snack`, paid, no new state). **Player statistics are kept forever** (owner 02/10):
    no time-based deletes by default (`ADMIN_STATS_*_DAYS`, `RETENTION_*_DAYS` = 0), and a deleted save keeps
    its stat rows (the PostgreSQL `mnl_stat_*_gone` functions were replaced by no-ops at startup: verified
    `deletes = f` on prod). Privacy page says so. Idle anonymous saves are still deleted after 180 days
    (`SESSION_IDLE_DAYS`); the owner was asked whether to keep those too.
- Known, pre-existing: `/api/ai/review` answers 400 for ~70 calls/hour (many clients; harmless: the client
  falls back to the scripted review). Cause not found yet (not the career check).
- In progress (02/10 afternoon): worktrees `wt-tax`, `wt-milktea`, `wt-grocery`, `wt-shops`, `wt-faq`
  (branches `ux/*` from 2074c20): disable/explain actions the server rejects (data: stat_actions errors), inline
  hints for tax/accounting, an in-game "Hỏi nhanh". Merge into rel-1.3, then release 1.4.4.
- Someone left uncommitted Firebase/telemetry work in the main checkout (.env.example, game/webassets.py,
  public/js/telemetry.js, public/privacy.html, tests/test_webassets.py); not ours, not released.

### What 1.2.1 → 1.2.3 added (01–02/10)
- **1.2.1** (01/10 23:50, quiet, no "Có gì mới"): admins (`ADMIN_USERS`, now also in `/etc/mot-ngay-lam-nghe/live.env`)
  post on Cả phố unfiltered with a "📢 Quản trị" badge and clickable links; tap a message → "📌 Ghim tin này".
  Schema 10: `chat_messages.adm`, `chat_pins`. The TikTok group message (chat_messages 5496) is pinned;
  `scripts/chat_pin.py --show/--msg/--unpin` (source pg.env for DATABASE_URL, PYTHONPATH=shared/pyvendor).
- **1.2.2** (02/10 00:32): long-press reactions ❤️ 😂 😮 😢 👍 🔥 in all chats; admin › Chat › "Tin nhắn" with
  search, filters, 200/page and the original text of masked messages (`chat_messages.raw`, from this release on).
  Schema 11: `chat_reacts`, `chat_messages.raw`. Daily-goals card explains how each goal counts (feedback #69, replied).
- **1.2.3** (02/10 00:38): hotfix, marriage.js `planner()` crashed (`reading 'venue'`) for engaged couples whose
  plan was sent/confirmed.

### What 0.9.5 → 0.9.12 added (30/09)
- **0.9.5:** buying homes with a bank mortgage, term savings, wardrobe, money chip, claim for short deliveries,
  calmer UI, admin "Trực tiếp" live counters. Performance work:
  - smaller saves: the overflow of long lists moves to the `archive` table and is **never deleted**;
  - orjson fast JSON;
  - a PostgreSQL pool without connection churn;
  - a cheaper public view.
  Also customers are ~20% more patient (`game/patience.py` `PATIENCE_FACTOR = 1.2`) and compensation is
  ~20% lower (`game/compensation.py` `COMPENSATION_FACTOR = 0.8`).
- **0.9.6:** pinned order cards (milk tea, clothing/assembly careers), public view 2.5× faster, fewer static
  re-stats, and a limit on slow logs. The Trung thu class programme accepts "phá cỗ" before "rước đèn", and a
  wrong order says which slot is wrong (`game/procedures.py` `ALT_ORDERS`).
- **0.9.7 (hotfix):** tasks created before 0.9.6 validate again. 0.9.6 had added display-only keys `ask`/`told`
  to clothing lines, so old open orders failed with "Dữ kiện gốc của nhiệm vụ không hợp lệ" and players were
  blocked everywhere. See `engine.LATE_TASK_KEYS` and `tests/test_late_task_keys.py`.
- **0.9.8, 0.9.9, 0.9.10:** notice-only releases ("Có gì mới"): the 20:00–0:00 infrastructure upgrade, the
  21:00–21:10 maintenance, and "upgrade done". No game logic changed.
- **0.9.11 (hotfix):** heartbreak life cards no longer invent a lover. Players reported "có bồ mà không biết"
  after the move; the data was fine (every save was compared, §7), the cause was cards like "Bị chia tay" that
  assume a partner. `game/life.py` `PARTNER_STORIES` are never drawn (still defined for saves holding one),
  engaged/married players (`_taken`) get no heartbreak card, and the "bị bỏ" rumour only follows being ghosted
  (`DUMPED`). Tests: `tests/test_life_heartbreak.py`. Checked on 3,000 real saves before shipping (0 failures).
- **0.9.12 (hotfix):** certificate self-study: answering a practice question or opening a hint no longer
  scrolls the sheet to the top and closes the open sections (`certificates.js`: `renderSheet()` keeps them;
  `renderSheet(false)` is for switching screens only). Its "Có gì mới" note, like 0.9.11's, was removed at the
  owner's request (no server-wide notice for fixes); both are described in the CHANGELOG.

### 0.9.13 → 0.9.15 (01/10, night)
- **0.9.13:** homes (villas, 4 apartment types, +20% prices), "Tiền của bạn" money sheet, faster cold load (minified
  release), payroll names the empty box and shows whole numbers as 12400. Notes: new features only (homes, money).
- **0.9.14:** admin "Thời gian chơi" (stat_play, exact from 01/10 00:31).
- **0.9.15:** five careers: bán trái cây `fruit`, thu gom rác `garbage`, thông ống cống `drain` (chapter 3), phi công
  `pilot`, tiếp viên `flight_attendant` (chapter 4, own airline UI); each save grows ~15 KB. System gifts:
  `scripts/grant_gift.py` grants coins with a private popup ("Quà từ Phố Có Chuyện"), paid once through the game's
  own command path; first use: 100 xu to the one player hit by the 01/10 00:33 502s (`sorry-20261001-910d8b7f`).

## 2. Rules the owner set (do not break)

1. **Never delete or alter player data.** Old history goes to the archive (paged "Xem cũ hơn"); money and
   balances must stay exact. Guest-save pruning is **off** in production (`PRUNE_GUEST_DAYS=0`); a player's own
   "clear chat" really erases it.
2. **Less text**, focus on the task, the one next action and the experience; phone first (390 px).
3. **Deploy with no gap** (`deploy/rolling_release.sh`, `docs/DEPLOY_ROLLING.md`).
   **"Có gì mới" only when the owner says so** (30/09): an entry pops up for every player, so fixes and small
   releases ship quietly (bump the version, write the CHANGELOG, no `game/whats_new.py` entry). A big release
   with new features gets a note (01/10), and the note lists **new features only**: no fixes, no price changes.
4. **Memory:** any in-process cache must be bounded (bytes + rows). The new server has 15 GB; PostgreSQL takes
   3 GB of shared buffers and the game is capped at 8 GB (`MemoryMax`).
5. **No credentials in the repo or in commits.** Server access comes from the owner.
6. **Every career, now and future, needs MANY awkward, annoying, strange demands** (01/10): from customers,
   bosses, neighbours, family, everything around the job; the more exasperating from outsiders the better, while
   the UI stays easy to read. This is a standing requirement for all career work.

## 3. Branches (local and on GitHub)

| Branch | State | What it is |
|---|---|---|
| `main` | **live 0.9.12** | Notice releases 0.9.8–0.9.10, the 0.9.11 heartbreak hotfix and the 0.9.12 certificate-scroll fix on top of `rel096`. |
| `rel098` | **in progress → ships as 0.9.13** | Housing (+20% prices, 4 apartment types, 2 villas, grouped listing) + rel095 QA fixes (spouse "tab khác" retry, joint-fund signs, "Free size", credit gauge, English pack ~450 strings) + **pre-deploy task-compatibility gate** (`scripts/check_task_compat.py`) + a **"Tiền của bạn"** money sheet (labelled 🏪 Quỹ / 👛 Ví chips). Merged `main` (quiet release: no whats_new entry of its own) and `coldload`; numbered **0.9.13**. Pushed, not deployed. |
| `coldload` | **merged into `rel098` (0.9.13)** (`7cb07fb`) | Faster cold page load on weak mobile networks: minified release, catalogue in parts, first workplace preloaded. Slow 4G first screen 5.7 s → 3.9 s (new player), 563 → 394 KB; target < 3 s needs ~100–150 KB less first-screen code (lazy modules). `package.py` now needs node/npx (or `--no-minify`); the first minified release makes every URL cold once. Ships in 0.9.13 via `rel098`. |
| `careers-street` | **in progress** | New careers: bán trái cây (fruit seller), dọn rác (garbage collector), thông ống cống (drain cleaner). Worktree `../PhoCoChuyen-careers-street`. |
| `careers-air` | **in progress** | New careers: phi công (pilot), tiếp viên hàng không (flight attendant). Worktree `../PhoCoChuyen-careers-air`. Registry files will conflict with `careers-street` at merge; merge one, then the other. |
| `lb-titles` | **live as 1.1.2 (01/10 14:20)** | 🏅 Weekly leaderboard titles (game/lb_titles.py, table `lb_weekly`, SCHEMA_VERSION 9; refreshed once a Vietnam day, the week frozen on Monday 00:00), a 🎖️ Danh hiệu board (leaderboard VERSION 2: the first start rebuilds every row in the background, weekly titles wait for it), and up to 3 titles + certificates worn at once (`journey.worn`; the old `equipped` becomes the first). No "Có gì mới". |
| `housing2`, `rel095`, `rel096`, `integ`, `perf-*`, `save-size`, `admin-pg`, `ux-work` | merged | Kept for history. |
| `origin/f094-gift` | **WIP, untested** | A 150 xu gift (open2026). Not in any release. Finish + test before shipping, or drop. |
| `origin/f095-perf-rel` 21e2435 | **WIP, untested** | A per-worker parsed-save cache. Not used; only take it if bounded and fully tested (it is the obvious lever for the 38 ms of game CPU per request). |
| other `origin/f095-*` | merged | The 0.9.5 feature branches. |

## 4. What to do next, in order

1. **Ship 0.9.13 = `rel098` + `coldload` together, off-peak (one deploy = one cold reload for everyone).**
   - Merge `main` into `rel098`, then `coldload`; renumber to 0.9.13.
   - Run the full checklist (§5), including `scripts/check_task_compat.py <live tree> <new tree>`, and
     validate ~3,000 real saves with the new code on the server, read-only (as done for 0.9.11).
   - Package with `scripts/package.py` from a clean `git archive`, then `mnl-rolling-release <zip>` **on the
     new server**. While the old server still forwards (§7), mirror the release to it (§7).
   - Afterwards, watch 5xx/400 rates and the slow-cmd log for 10 minutes.
2. **Onboarding shipped in 0.9.16 (01/10 02:12, quiet):** one intro screen, day 1 opens on the first customer, first
   delivery after 10 presses (was 23), no modal before the 3rd customer, tip + level 2 at customer 3 + day-1 gift,
   one-time hints. Measure it: the 30/09 cohort had 53% picking a workplace and 39% serving a customer; compare the
   01/10+ cohorts (admin "Thời gian chơi", new players' first day).
   **0.9.17 (01/10 07:23, quiet):** `street2` + `air2`: player-led haggling, quotes, debts, fees and replies with
   NPCs deciding from hidden traits (deterministic from the task seed + the player's input), overcharging, grumbling
   owners, theft, unpaid tabs, night vandals, seduction/harassment handled PG-13 (giving in never rewarded,
   reporting always protected), storms for pilots.
   **0.9.18 (01/10 08:04, quiet):** retention logging + admin "Giữ chân" (game/retention.py; milestones backfilled
   from 30/09 with scripts/milestones_backfill.py: 81,925 rows). `RETENTION_LOG=0` turns it off.
   **0.9.19 (01/10 09:26, quiet):** "Thêm" menu 25 → 11–12 entries in hubs, guides only on demand (one-time
   "Bỏ qua / Xem hướng dẫn" per career, "?" on every work screen), salon colour-mixing preview + 6×6 chart.
   **1.0.0 (01/10 10:16, announced):** chat (friends, groups ≤20, Cả phố 10 s/msg, online dots) + Đi dạo khu phố.
   The live service `mnl-live.service` (127.0.0.1:8770, `python3 -m live`, websockets 17.1 in shared/pyvendor via
   scripts/vendor_websockets.sh), switches in `/etc/mot-ngay-lam-nghe/live.env` (LIVE_CHAT=1, LIVE_STREET=1,
   LIVE_DATING=0; `systemctl restart mnl-live` applies), nginx `location = /live` on both servers (the old one
   forwards it), the game's drop-in `live.conf` sets `LIVE_URL=/live`. `mnl-rolling-release` restarts mnl-live.
   **01/10 later:** 1.0.1 chat first in the menu, only accounts post, Cả phố keeps 2,000 messages, pages of 30;
   1.0.2 merged supplier orders (shipping fees approved by the owner); 1.0.3 dating (LIVE_DATING=1, schema 7,
   accounts only; announced); 1.0.4 UX fixes from the retention logs + the grocery bulk-quote fix (#49, ShinMi
   compensated 2 × 100 xu with private popups); 1.0.5 the weak-network loading error (jobView skeleton, retries),
   double taps, injected-script noise, client error stacks in the admin.
   1.0.6 hotfix: grocery bulk quotes from the standard price list (raised shelf prices made every bulk order
   impossible; 39 orders were lost that way across players before the fix; ShinMi got 300 xu more).
   **1.1.0 (01/10 12:50, announced):** live weddings (LIVE_WEDDING=1, schema 8, accounts are counted guests,
   others watch from the gate), anniversaries, "Khách mời của tuần" (scripts/wedding_week.py settles weekly).
   1.1.1 hotfix: wedding plan errors shown at the send button, too-soon times blocked, a server-wide "sắp cưới"
   news line with the date and time. Anti-flood limits on nginx + fail2ban + SYN cookies (deploy/ddos/, 01/10).
   1.1.2 (01/10 14:20, quiet): weekly leaderboard titles, a Danh hiệu board, up to 3 titles/certificates worn.
   1.1.3 (01/10 16:24, notice): the wedding party reworked (10 min, everyone recorded on entry, 20 xu a minute,
   15 xu a guest for the couple, any couple books its party for free, the show in wedfeast.js), 🧧 red envelopes
   and the "Lời chúc" board (feedback #56). 1.1.4 (01/10 17:56, notice): a guest counts after 2 minutes
   (`GUEST_MIN_MINUTES`); the bà Sáu bulk order fix with stuck saves answered on load (#57, `heal_save` in
   `migrate_state`). Both packaged on Windows (scripts/build_static.py batches esbuild; a comment-only stylesheet
   keeps its bytes). **Never deploy while a wedding party is open or within ~20 min of one** (mnl-live restarts).
   Waiting for version 2: branches `house-reno` (view/repair/decorate), `office-jobs` (3 office positions) and a
   homemaker career, plus the #59 dorm idea (owner to decide).
   1.2.0 (01/10 23:06, notice): inside the house (game/reno.py: view, repair, decorate), the homemaker career,
   three office desks at Cánh Diều (hr_admin, secretary, it_helpdesk, chapter 5) and six accounting situations.
   The office and house texts have no English yet. A TikTok group announcement was inserted into Cả phố as
   pid 'admin' (chat_messages 5419, 5496; mnl-live restarted to reload the buffer). Next: admin pin + admin
   posting in Cả phố (in progress), quiet release.
   Tested first on a staging copy of PG (`phoco_stage`, port 8799, dropped after): the leaderboard VERSION 2
   rebuild took ~3.5 min there and ~4 min live. A staging server MUST run with `PUSH_DISABLED=1` (its
   housekeeping would otherwise deliver the copied push queue to real phones). Was next: 1.1.0 weddings
   (`live-wedding`, spec docs/superpowers/specs/2026-10-01-live-wedding-design.md). Earlier plan text:
   (Chat v1.0 →
   release 1.0.0 with notes: chat, presence, Cả phố 10 s, strolling, dating bench; no tutorial for chat).
3. **Next versions, in the owner's order:** (a) chat phase 1 (design `docs/superpowers/specs/2026-09-30-live-chat-street-design.md`
   on branch `live`; the owner said not yet on 01/10), then (b) seven careers: nhân viên gác chắn và bảo trì đường sắt,
   cán bộ lưu trữ và thư viện, điều dưỡng, thợ dầu khí, trực tổng đài cứu hộ, người gác hải đăng, cứu hộ hồ bơi,
   bán kem (added 01/10, feedback #51),
   together with (c) many more awkward, annoying demands in every existing career (rule 6).
3. **Retire the old server's role (after 3–7 days, ~03–07/10):** see §7.
4. **Deploy less often.** Each deploy makes the changed files cold for everyone. Batch changes; hotfixes excepted.
5. **English pack.** Older screens still have ~15k untranslated strings (English players see Vietnamese).
   `scripts/i18n_extract.py` (extract → translate → build).
6. **Known issues, not yet fixed:**
   - `browser_deploy.py` is flaky under machine load (a service-worker fetch during the restart gap).
   - The news ticker covers the phone header for a few seconds.
   - A same-day loan can be used to raise the credit score.
   - A read-only validation of recent saves once flagged 23 `mother_baby` saves with "Thiếu hoặc sai phiên bản
     Sổ tiệm". It is probably an artefact of validating outside the storage path, but confirm it. (The 0.9.11
     check of 3,000 recent saves found no failure.)
7. **AI cost / speed decision (owner).** The gateway model `claude-opus-4-8` always "thinks" (~450 hidden tokens),
   so `LLM_THINKING_TOKENS=1024` headroom was added in 0.8.9 (replies take 3–7 s). Haiku / Sonnet 4.6 are not
   enabled for the current key. If the provider enables `claude-haiku-4-5`, switch `LLM_MODEL` in
   `/etc/mot-ngay-lam-nghe/game.env` (no code change).
8. **More save shrinking (optional).** About 21 KB of starting stock per never-played workplace, feed labels
   copied into reviews, and ~8 KB per finished corp_accounting job (see the save-size report).

## 5. Release checklist

```
python3.12 -m unittest discover -s tests -t .      # ~3,400 tests
node scripts/check_js.mjs && node scripts/check_nav.mjs
python scripts/check_task_compat.py <live-tree> <new-tree>   # from 0.9.8: must pass
venv/bin/python scripts/browser_first_day.py        # 7 PASS (story mode, phone)
venv/bin/python scripts/browser_features_095.py     # 0 problems
venv/bin/python scripts/browser_text_check.py --engines chromium,webkit --careers milk_tea,clothing --lang vi
venv/bin/python scripts/browser_v04.py --careers milk_tea,grocery,restaurant,clothing,homestay,teacher --report out.json
venv/bin/python scripts/browser_deploy.py           # versioned assets never mix
```
Then: bump `game/__init__.py` and add a CHANGELOG entry. Only if the owner asked for a notice: add the
`game/whats_new.py` entry and run `python -m game.whats_new`.

## 6. Production map (no secrets) — new server 103.195.238.178

- **Host:** Ubuntu 24.04, 9 vCPU (Xeon Platinum 8163), 15 GB RAM, 140 GB SSD, InterDigi (HCMC); game only.
  ufw allows 22/80/443; fail2ban (sshd). Root has an SSH key from the operator's Mac; password login is still on.
- **Clock:** the provider blocks NTP (UDP 123). `mnl-timesync.timer` (every 15 min) sets the clock from HTTPS
  `Date` headers (`/usr/local/sbin/mnl-timesync-https`, ~50 ms). Ask the provider to open UDP 123, then
  remove it and use systemd-timesyncd (config in `/etc/systemd/timesyncd.conf.d/ipv4.conf` is ready).
- **Units:** `mot-ngay-lam-nghe.service` on 127.0.0.1:8765 with `WORKERS=8`, `CPUQuota=800%`, `MemoryMax=8G`
  (drop-ins: `50-postgres.conf` with `PG_POOL=6 PG_POOL_MAX=12`, `workers.conf`, `assets.conf`, `keepdata.conf`,
  `zz-pyvendor.conf`). A transient `mot-ngay-lam-nghe-bridge` exists only during a rolling release (:8766).
  `mnl-selfheal.service`, `mnl-pg-backup.timer` (03:40), `certbot.timer`.
- **Deploy:** `mnl-rolling-release <zip>` (same script as before, `deploy/rolling_release.sh`). `package.py` now
  minifies (needs node/npx). `/etc/nginx/nginx.conf` has `worker_shutdown_timeout 20s` (01/10): without it an old
  nginx worker kept one player's HTTP/2 connection pinned to the stopped bridge for minutes after a release
  (52 × 502 for that player on 01/10 00:34).
- **Play time:** `stat_play` (one row per player per Vietnam day, trigger on `receipts`, ~12 µs per command) feeds
  the admin "Thời gian chơi" card. Exact from 01/10 00:31; 29–30/09 were backfilled from receipts as estimates
  (`scripts/playtime_backfill.py`, idempotent).
- **Giữ chân (branch `retention`, not live yet):** `game/retention.py` records funnel steps (`stat_milestones`, kept),
  commands per player per day (`stat_actions`, buffered in memory and written every 15 s, 60 days, then
  `stat_actions_daily`), leave/error/load/acquisition beacons (`POST /api/beacon`, 60 days); admin view "Giữ chân"
  (`game/admin_retention.py`, CSV with `&format=csv`). SCHEMA_VERSION 5 creates the tables at start-up; then run
  `scripts/milestones_backfill.py` once off-peak (seeds the 30/09+ cohorts). `RETENTION_LOG=0` turns recording off.
  `stat_play` per-player rows are now kept 60 days (`ADMIN_STATS_PLAY_DAYS`), older days summed into `stat_play_daily`.
- **nginx site** `/etc/nginx/sites-enabled/phocochuyen` (same as the old server): HTTP/2, static
  `/js /css /i18n /icons /music /fonts` served directly, `?v=` assets from `/opt/mot-ngay-lam-nghe/shared/_v`
  (immutable), a timing log for `/api/` in `/var/log/nginx/phocochuyen_api.log`. `/etc/nginx/conf.d/mnl-realip.conf`
  trusts `X-Forwarded-For` only from the old server's IP (while it forwards), so per-IP limits see players.
- **TLS:** Let's Encrypt `phocochuyen.io.vn` + `www` (copied from the old server, valid to 27/12/2026; renewal
  dry-run succeeded on the new server). DNS: zonedns.vn, A records `@` and `www`, TTL 300 (owner has access).
- **Python extras** in `/opt/mot-ngay-lam-nghe/shared/pyvendor` (psycopg C, orjson 3.12.0).
- **PostgreSQL 16:** `max_connections 200` (8×12 + bridge 8×6 + tools), `shared_buffers 3GB`,
  `effective_cache_size 9GB`, SSD settings; config in `/etc/postgresql/16/main/conf.d/mnl.conf`. Promoted from a
  streaming replica of the old server at the move (the replica config lines left in `postgresql.auto.conf` are
  inert).
- **Old player data** from the old server's `/var/lib/mot-ngay-lam-nghe` (the pre-PostgreSQL `game.sqlite3`,
  backups, `pre-pg-*`): `/var/lib/mot-ngay-lam-nghe/from-old-server/var-lib/` (4.1 GB, verified byte-identical).
- **Admin:** https://phocochuyen.io.vn/admin (ADMIN_USERS in game.env). The save-scan stats hold
  (`mnl-adminstats-hold`) existed only on the old server; the new one has room to run it.
- **Debugging slowness:** `journalctl -u mot-ngay-lam-nghe | grep slow-` gives phase timings per command;
  in the nginx timing log, `urt` is server time and `rt` is total time (the difference is the network).
  CPU per request: compare `cpu.stat` of the unit cgroups with the request count in the timing log.

## 7. The move of 30/09 and the old server 103.179.190.51

- **How it went:** streaming replica over an SSH tunnel (built 20:00–20:16 at 15 MB/s), tested on a
  throwaway copy (browser + load test), maintenance notice 21:00–21:10, then at 21:00:23 the old game stopped,
  the replica confirmed the last WAL position and was promoted, the new game started and the old nginx began
  forwarding: **11 s of interruption**. DNS moved at 21:01 and was visible on 8.8.8.8 / 1.1.1.1 by 21:04.
- **Data check:** all 51 tables have as many or more rows on the new server; of the 24,353 saves on the old
  server, 23,983 were byte-identical, 369 had been played further, 0 were older, 1 was deleted by its owner
  (account delete, "XOA"), plus new saves. Marriage state changed for one save only (a real proposal accepted
  at 21:26).
- **Old server now:** the game unit and `mnl-selfheal` are stopped and **disabled** (never start them: its
  database is a frozen copy as of 21:00 and writes there would fork the data). nginx forwards everything to the
  new server (`/root/nginx-cutover/phocochuyen.to-new`; the previous site is `phocochuyen.before`).
  Its clock is ~62 s slow and not NTP-synced. dk_bike shares that host: never touch it.
- **While it forwards, mirror each release to it** with `/usr/local/sbin/mnl-mirror-old` on the new server (01/10:
  copies the release and `_v`, verifies, only then switches the old `current`; run it right after each
  `mnl-rolling-release`, never from a directory you are deleting). Background:
  `rsync` the new `/opt/mot-ngay-lam-nghe/releases/<rel>` and `shared/_v/` to it, then switch its `current`
  symlink (the commands are in the 0.9.10–0.9.12 deploys: the new server holds an SSH key limited to its IP,
  `/root/.ssh/mnl_old`).
- **Retire (after 3–7 days):** when the old api log shows ~no forwarded requests, keep one final
  `pg_dump -Fc` of its frozen database, stop PostgreSQL's game database there (not dk_bike's), restore its nginx
  site to a plain redirect or remove it, remove the `mnl-migrate-from-new` key from its `authorized_keys`, and
  drop `/etc/nginx/conf.d/mnl-realip.conf` and `mnl-pg-tunnel.service` (already disabled) on the new server.
- **Owner to-dos:** ask InterDigi to open UDP 123; rotate the root passwords of both servers and the zonedns
  password (they were shared in chat).
