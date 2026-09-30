# Handoff — state of Phố Có Chuyện (30/09/2026, ~22:00)

Read this first if you pick the project up. It says what is live, where it runs, what is half-done, which
branch holds what, and what to do next, in order. Details live in the linked docs; this file is the map.

## 1. What is live

- **Production:** https://phocochuyen.io.vn runs **0.9.16** (`main` = `f0080cc`), 28 careers, PostgreSQL 16,
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
   01/10+ cohorts (admin "Thời gian chơi", new players' first day). In progress: `street2` / `air2` (many annoying
   demands and player-initiated actions for the five 0.9.15 careers), then a quiet 0.9.17.
3. **Next versions, in the owner's order:** (a) chat phase 1 (design `docs/superpowers/specs/2026-09-30-live-chat-street-design.md`
   on branch `live`; the owner said not yet on 01/10), then (b) seven careers: nhân viên gác chắn và bảo trì đường sắt,
   cán bộ lưu trữ và thư viện, điều dưỡng, thợ dầu khí, trực tổng đài cứu hộ, người gác hải đăng, cứu hộ hồ bơi,
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
- **While it forwards, mirror each release to it** (its nginx serves static files from its own disk):
  `rsync` the new `/opt/mot-ngay-lam-nghe/releases/<rel>` and `shared/_v/` to it, then switch its `current`
  symlink (the commands are in the 0.9.10–0.9.12 deploys: the new server holds an SSH key limited to its IP,
  `/root/.ssh/mnl_old`).
- **Retire (after 3–7 days):** when the old api log shows ~no forwarded requests, keep one final
  `pg_dump -Fc` of its frozen database, stop PostgreSQL's game database there (not dk_bike's), restore its nginx
  site to a plain redirect or remove it, remove the `mnl-migrate-from-new` key from its `authorized_keys`, and
  drop `/etc/nginx/conf.d/mnl-realip.conf` and `mnl-pg-tunnel.service` (already disabled) on the new server.
- **Owner to-dos:** ask InterDigi to open UDP 123; rotate the root passwords of both servers and the zonedns
  password (they were shared in chat).
