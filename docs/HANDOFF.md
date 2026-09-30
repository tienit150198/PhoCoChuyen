# Handoff — state of Phố Có Chuyện (30/09/2026, ~19:00)

Read this first if you pick the project up. It says what is live, what is half-done, which branch holds
what, and what to do next, in order. Details live in the linked docs; this file is the map.

## 1. What is live

- **Production:** https://phocochuyen.io.vn runs **0.9.7** (`main` = `e7e4e83`), 23 careers, PostgreSQL 16.
- **Traffic (30/09 18:41):** ~270 players active in 5 min, ~1,150 in 1 h, ~17,700 in 24 h; 22,900 saves,
  1,800 accounts; ~27–30 commands/s at the evening peak.
- **Speed (server side, 18:41):** command p50 ≈ 90 ms, p90 ≈ 250 ms. At 16:00 on 0.9.4 it was p50 918 ms,
  p90 3 s. Slow *page loads* on weak mobile networks are the main remaining complaint (see §4.1).
- **Peak hours:** 17:30–20:00 (Vietnam time). Avoid heavy work on the server then; hotfixes may still go out
  (the rolling release has no gap).

### What 0.9.5 → 0.9.7 added (30/09)
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

## 2. Rules the owner set (do not break)

1. **Never delete or alter player data.** Old history goes to the archive (paged "Xem cũ hơn"); money and
   balances must stay exact. Guest-save pruning is **off** in production (`PRUNE_GUEST_DAYS=0`); a player's own
   "clear chat" really erases it.
2. **Less text**, focus on the task, the one next action and the experience; phone first (390 px).
3. **Deploy with no gap** (`deploy/rolling_release.sh`, `docs/DEPLOY_ROLLING.md`); announce fixes in "Có gì mới"
   (`game/whats_new.py`: every release needs an entry).
4. **Memory:** any in-process cache must be bounded (bytes + rows); RAM is 8 GB shared with PostgreSQL.
5. **No credentials in the repo or in commits.** Server access comes from the owner.

## 3. Branches (local and on GitHub)

| Branch | State | What it is |
|---|---|---|
| `main` | **live 0.9.7** | = `rel096` |
| `rel098` | **in progress** | 0.9.8: housing (+20% prices, 4 apartment types, 2 villas, grouped listing) + rel095 QA fixes (spouse "tab khác" retry, joint-fund signs, "Free size", credit gauge, English pack ~450 strings) + **pre-deploy task-compatibility gate** (`scripts/check_task_compat.py`) + a **"Tiền của bạn"** money sheet (labelled 🏪 Quỹ / 👛 Ví chips, every pocket in one place). Not deployed yet. |
| `coldload` | **in progress** | Faster cold page load on weak mobile networks: bundle the critical modules, lazy fonts, split `/api/content`, service-worker precache. Target: visible < 3 s on slow 4G. |
| `housing2`, `rel095`, `integ`, `perf-*`, `save-size`, `admin-pg`, `ux-work` | merged | Kept for history. |
| `origin/f094-gift` | **WIP, untested** | A 150 xu gift (open2026). Not in any release. Finish + test before shipping, or drop. |
| `origin/f095-perf-rel` 21e2435 | **WIP, untested** | A per-worker parsed-save cache. Not used; only take it if bounded and fully tested. |
| other `origin/f095-*` | merged | The 0.9.5 feature branches. |

## 4. What to do next, in order

1. **Ship 0.9.8 + coldload together, after 20:00 (one deploy = one cold reload for everyone).**
   - Merge `coldload` into `rel098`.
   - Run the full checklist (§5), including `scripts/check_task_compat.py <live tree> <new tree>`.
   - Package with `scripts/package.py` from a clean `git archive`, then `mnl-rolling-release <zip>`.
   - Afterwards, watch 5xx/400 rates and the slow-cmd log for 10 minutes.
2. **Deploy less often.** Each deploy makes the changed files cold for everyone. Batch changes; hotfixes excepted.
3. **English pack.** Older screens still have ~15k untranslated strings (English players see Vietnamese).
   `scripts/i18n_extract.py` (extract → translate → build).
4. **Known issues, not yet fixed:**
   - `browser_deploy.py` is flaky under machine load (a service-worker fetch during the restart gap).
   - The news ticker covers the phone header for a few seconds.
   - A same-day loan can be used to raise the credit score.
   - A read-only validation of recent saves once flagged 23 `mother_baby` saves with "Thiếu hoặc sai phiên bản
     Sổ tiệm". It is probably an artefact of validating outside the storage path, but confirm it.
5. **AI cost / speed decision (owner).** The gateway model `claude-opus-4-8` always "thinks" (~450 hidden tokens),
   so `LLM_THINKING_TOKENS=1024` headroom was added in 0.8.9 (replies take 3–7 s). Haiku / Sonnet 4.6 are not
   enabled for the current key. If the provider enables `claude-haiku-4-5`, switch `LLM_MODEL` in
   `/etc/mot-ngay-lam-nghe/game.env` (no code change).
6. **More save shrinking (optional).** About 21 KB of starting stock per never-played workplace, feed labels
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
Then: bump `game/__init__.py`, add the `game/whats_new.py` entry, run `python -m game.whats_new`, and add a
CHANGELOG entry.

## 6. Production map (no secrets)

- **Units:** `mot-ngay-lam-nghe.service` on 127.0.0.1:8765 with `WORKERS=4`, `CPUQuota=350%`, `MemoryMax=3G`
  (drop-ins: `50-postgres.conf`, `workers.conf`, `assets.conf`, `keepdata.conf`, `zz-pyvendor.conf`).
  A transient `mot-ngay-lam-nghe-bridge` exists only during a rolling release (:8766).
- **nginx site** `/etc/nginx/sites-enabled/phocochuyen`: HTTP/2, static `/js /css /i18n /icons /music /fonts`
  served directly, `?v=` assets from `/opt/mot-ngay-lam-nghe/shared/_v` (immutable), a timing log for
  `/api/` in `/var/log/nginx/phocochuyen_api.log`. dk_bike sites share the host: never touch them.
- **Python extras** in `/opt/mot-ngay-lam-nghe/shared/pyvendor` (psycopg C, orjson 3.12.0).
- **PostgreSQL:** max_connections 60 (canonical 4×12 + bridge 4×3 during a release); nightly `mnl-pg-backup.timer`.
- **Admin:** https://phocochuyen.io.vn/admin (ADMIN_USERS in game.env). The save-scan stats are deliberately
  held at peak (`mnl-adminstats-hold`); the "Trực tiếp" counters are always live.
- **Debugging slowness:** `journalctl -u mot-ngay-lam-nghe | grep slow-` gives phase timings per command;
  in the nginx timing log, `urt` is server time and `rt` is total time (the difference is the network).
