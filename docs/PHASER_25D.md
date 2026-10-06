# Phaser 2.5D client: kept on `main`, not wired (since 1.8.0)

`main` runs what production runs. From release 1.8.0 on, every shipped file (`server.py`, `game/`, `live/`,
`public/`, `scripts/`, `i18n/`, the tests of that code, `package.json`, `MANIFEST.json`) is byte-identical to branch
`integ-1.8`, which is built on `live-1.7.15` (the tree of release `1.7.15-hai-thousand`, see `docs/LIVE_BASE.md`).
Production never ran the Phaser 2.5D isometric client. It still runs `BobaWorld` (`public/js/boba-world.js`).

The 2.5D work from the other session (commits `6250463`, `429b409`, `f3ada34`, `9892ada`, `b307563`) is **kept in the
repo, unreferenced**: nothing the game loads imports it. This page lists what is kept, which hooks were taken out,
which commits hold them, and how to wire the client back.

## What is kept, and where

| Area | Files |
|---|---|
| Phaser scene (TypeScript source) | `client/isometric/*.ts`, `tsconfig.isometric.json` |
| Built client modules | `public/js/isometric/*.js` (incl. the bundled `phaser-world.js`), `public/js/isometric-shell.js`, `isometric-movement.js`, `isometric-town.js`, `public/js/illustrated-icons.js`, `public/js/pixel/*.js`, `public/js/careers/delivery_isometric.js` |
| Styles, art, fonts | `public/css/isometric.css`, `public/css/cozy-reference.css`, `public/icons/{isometric,cozy-v2,cozy-v3,pixel}/`, `public/fonts/vt323-*` |
| Standalone preview | `public/preview25d/` (served at `/preview25d/`, linked from nowhere) |
| Server side | `game/leisure.py` (private fishing/boat/pool rounds), `game/town_layout.json`, `live/town.py` (shared town presence) |
| Toolchain | `package-lock.json` (Phaser 3.90.0, esbuild, sharp, TypeScript), `scripts/build_isometric.mjs`, `scripts/prepare_isometric_assets.mjs`, `scripts/package_cozy_reference.mjs`, `scripts/package_town_buildings.mjs` |
| Tests | `tests/isometric-*.mjs`, `tests/isometric-*.cjs`, `tests/leisure-*.mjs`, `tests/pixel-*.mjs`, `tests/cozy-portraits.mjs`, `tests/delivery_isometric.mjs`, `tests/illustrated-icons.mjs`, `tests/preview25d.mjs`, `tests/town-*.mjs`, `tests/test_leisure.py`, `tests/test_live_town*.py`, and the guard `tests/phaser25d-wired.mjs` |
| Docs | `docs/cozy-reference-assets/`, `docs/superpowers/plans/2026-10-05-main-soft-25d.md`, `2026-10-06-town-polish.md`, `2026-10-06-capacity-lag.md`, `docs/performance/` |

Kept from `main` that is not 2.5D: `scripts/capacity/` (the 1,000-player load rig of `9892ada`/`b307563`) and
`docs/performance/`. The runtime part of `b307563` (command memory bound, HTTP slot release) was ported as `d9ead13`
and is in 1.8.0.

Not kept: `public/css/pixel.css`. On `main` it was already a retired, comment-only stub, and its name matches the
ad-blocker pattern of `tests/test_asset_names.py` (`pixel.`), so that test failed. It is in `b307563` if you need it.

`package.json` is 1.8.0's (it ships). `main`'s 2.5D version adds the scripts `build:isometric`,
`assets:isometric`, `typecheck:isometric`, `test:isometric`, `assets:reference`, plus the dependency `phaser 3.90.0` and the
devDependencies `esbuild 0.25.11`, `sharp 0.35.5` and `typescript 5.9.3`. `package-lock.json` matches that version, not 1.8.0's.
Restore it with `git show b307563:package.json > package.json`, then run `npm ci`.

### Side effects of keeping the files in `public/`

* They are served as static files but loaded by nothing.
* `game/webassets.py` versions every file under `public/{js,css,icons,…}`. So the 18 kept `.js`/`.css` files get
  entries in the page's import map (about 2 KB more HTML), and the 36 kept images join the content-addressed store
  and the build hash. Players download none of them.
* `scripts/release_from_live.py --ref main` ships every file that differs from the live base. A release built from
  `main` therefore also carries these files (unreferenced). Build 1.8.0 from `integ-1.8` if you want a byte-minimal zip.

## Hooks that are not in the 1.8.0 runtime

Production (`live-1.7.15`, commit `e2abe23`) took these out of `6250463`. The later commits changed some of them.

| File | Hook | Where it is |
|---|---|---|
| `public/js/app.js` | imports of `PhaserWorld` (`./isometric/phaser-world.js`), `bootIsometricShell`/`updateIsometricShell`/`isometricAction` (`./isometric-shell.js`), `bootIsometricMovement`, `bootIsometricTown`, `bootCozyPortraits`; `new PhaserWorld(...)` instead of `new BobaWorld(...)`; `updateIsometricShell(env())` in `renderMain` and `renderSheet`; the town case of the `#sheet` cancel handler; `world.setMode('work')` in `selectCareer`; the `career:`/`outing:` taps in `interact`; `leisurePlace`, `home`→`isoTown` and `isometricAction` at the top of `handleAction`; the boot calls; the town-first boot (`townOn`) | `6250463` (all of them). `git diff e2abe23 6250463 -- public/js/app.js` shows exactly these hunks |
| `public/index.html` | `<link rel="stylesheet">` for `/css/isometric.css` and `/css/cozy-reference.css` | `6250463` |
| `game/webassets.py` | `/icons/isometric/*` in the import map | `6250463` |
| `game/content.py` | `c['playable'] = c['id'] in CAREERS` in `public_content()` (the island shows playable careers only) | `6250463` |
| `game/journey.py` | `from . import leisure as ls`; `jr_leisure_*` → `ls.action`; `leisure=ls.public(s)` and `leisure=ls.content()`; `ls.validate(s)` | `6250463` (lines 51, 838, 928, 955, 1023) |
| `live/app.py`, `live/config.py`, `live/hub.py` | `TownFeature` in `FEATURES`; `LIVE_TOWN` / `Config.town` flag; `_broadcast` (text frames) | `6250463` |
| `public/js/v4/live.js` | `live.flags.town` keeps the socket open when only the town is on | `6250463`, changed in `429b409` |
| `public/js/careers/delivery.js`, `delivery_drive.js`, `public/css/careers/delivery.css` | the isometric driving view (`look`, `player` options, `.dd-isometric`) | `6250463` |
| `public/js/v4/look.js` | `data-cozy-portrait` markers (`cozyPortraitData`) | `6250463` |
| `public/js/v4/chat.js`, `public/css/chat.css` | the 2.5D-era chat sheet (`#townChat`, reconnect button, chat-off states, new header) | `6250463`, `429b409`, `f3ada34` |
| `public/js/icons.js` | illustrated icons via `illustrated-icons.js` (`careerIconNames`) | `f3ada34` |
| `game/careers/{clothing,com,giupviec,ice_cream,nail,naucom,pagoda,pho,pilot}.py`, `game/extra_content.py` | career/experience `icon` names for the illustrated set (e.g. `com`: `cake` → `com`) | `f3ada34` |

The whole 2.5D client as it last stood is the tree of `b307563` (origin/main on 06/10/2026).

## Wiring it back

1. Toolchain: restore `package.json` from `b307563` (see above) and run `npm ci`.
2. Re-apply the hooks above on top of the current `main`. Do not check out `b307563`'s runtime files whole: that would
   drop every 1.8.0 change (careers, WP1–WP10, i18n, fair stakes up to 1,000, Ông Hai 6-ply). Port hunk by hunk:
   * `git diff e2abe23 6250463 -- public/js/app.js public/index.html game/webassets.py game/content.py live/app.py live/config.py live/hub.py public/js/v4/live.js public/js/careers/delivery.js public/js/careers/delivery_drive.js public/css/careers/delivery.css public/js/v4/look.js public/js/v4/chat.js public/css/chat.css`
     (production-only differences such as the fair or `journey.py` are left out of this list. Add the five
     `journey.py` leisure lines by hand);
   * `git show 429b409 -- public/js/v4/live.js public/css/chat.css`;
   * `git show f3ada34 -- public/js/icons.js public/js/v4/chat.js public/css/chat.css game/careers game/extra_content.py`.
3. Careers added since: `library`, `nurse`, `oil` and `railway` have no entry in `client/isometric/building-art.ts`
   (`BUILDING_ART`). Add them, and check `game/town_layout.json` / `live/town.py` for the larger grid.
4. Rebuild the scene: `node scripts/build_isometric.mjs` (writes `public/js/isometric/phaser-world.js`).
5. Saves: wiring `leisure` adds a `leisure` block to the public state and its validation. Keep old saves (without
   the block) loading, and run the task-compat gate (`scripts/check_task_compat.py`) as for any release.
6. Tests run again by themselves once the hooks are back:
   * Python: `tests/test_leisure.py` runs when `game/journey.py` imports `game.leisure`, and `tests/test_live_town*.py`
     when `live.config.Config` has a `town` field (the broadcast test: when `live.hub._broadcast` exists).
     `test_grid_bounds_roads_and_nonfinite_values` is skipped outright: the town grid grows with the career count,
     and with 1.8.0's careers the point (6, 51) is inside it. Pick a new out-of-bounds point.
   * Node: the tests that import `tests/phaser25d-wired.mjs` print `skipped` and exit 0 until `public/js/app.js`
     imports `./isometric/phaser-world.js` again. They are `cozy-portraits`, `delivery_isometric`, `illustrated-icons`,
     `town-map-contract` and `town-art-polish`.
   * Need `npm ci`: `isometric-texture-frames`, `isometric-world`, `town-polish` and `town-map-contract` (esbuild),
     plus `town-art-polish` (sharp).
   * `tests/isometric-hud-layout.cjs` and `tests/isometric-renderer-browser.cjs` are `playwright-cli run-code`
     snippets, run by hand against a page with the 2.5D client on.
