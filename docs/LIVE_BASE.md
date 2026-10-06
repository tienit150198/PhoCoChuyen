# Branch `live-1.7.15`: the tree production runs

Production (103.195.238.178) runs release **1.7.15-hai-thousand-final-20261005234904**
(`/opt/mot-ngay-lam-nghe/current`). GitHub `main` had moved on (Phaser 2.5D work, not deployed), and no
commit held what production runs. This branch does. It starts from `6250463` ("Archive pixel-era working
state…"), the closest commit, and takes every file from the release itself.

## How it was built (2026-10-06)

The release's `MANIFEST.json` lists 1,348 files with the sha256 of the **bytes shipped**. Every file in the
release directory hashed to its MANIFEST entry, so the copy was complete and unmodified.

Compared with `6250463`, 1,287 files were identical, 58 differed and 3 were missing.

* **36 changed or missing files shipped as source** (Python, docs, tests, `package.json`, `deploy/live/live.env.example`,
  `public/index.html`, 8 JS/CSS files) were copied byte for byte.
* **22 JS/CSS files were shipped minified** (`esbuild@0.28.2`, the flags of `scripts/build_static.py`). For these the MANIFEST
  holds the hash of the minified bytes, not of a source. The release's MANIFEST says `"minified": 0`, but the files
  are minified anyway: the release was packaged from a tree that already held minified copies. The minified text is
  **not** committed. Each source was found as follows:
  * 20 files: `6250463`'s source, minified, gives exactly the shipped bytes.
  * `public/js/v4/fair.js` (the hai-thousand change): `6250463`'s source plus the 1,000 xu tiers, which are
    `CHIPS`/`XD_STAKES` `…,500,1000`, `TIER_NAME.nghin='Vé ngàn lộc'` and `max_stake||1000` (3×). Rebuilt by hand.
  * `public/js/app.js`: `6250463`'s source with its isometric/pixel hooks taken out. Those hooks are the
    `PhaserWorld`/`isometric-*` imports and boot calls, `updateIsometricShell`, the town `cancel`/`home` paths,
    `world.setMode('work')`, the `career:`/`outing:` taps, `leisurePlace` and the town-first boot sheet. Production
    still runs `BobaWorld`. Rebuilt by hand.

  Both rebuilt sources are proven: minifying them gives exactly the shipped bytes. Minifying drops comments and
  layout, so where the operator's own copy of these two files differs, it can differ only in comments or
  formatting. The code is the same.
* **Runtime files of `6250463` that production does not have were removed (84):** the isometric/pixel client
  (`public/js/isometric*`, `public/js/pixel/`, `public/css/{isometric,pixel,cozy-reference}.css`, `public/icons/{isometric,cozy-v2,pixel}/`,
  `public/fonts/vt323-*`, `public/preview25d/`, `client/`), `game/leisure.py`, `game/town_layout.json`, `live/town.py`,
  the scripts and tests that go with them, `tsconfig.isometric.json` and `package-lock.json`. The production code
  references none of them. Docs, `i18n/todo/` (never packaged) and `reference/MANIFEST.json` were kept.
* `MANIFEST.json` at the root is the release's own.

## Verification

For each of the 1,348 MANIFEST entries, the file on this branch hashes to the MANIFEST sha256, except the 22
files below. Each of those, minified with `esbuild@0.28.2` and the flags of `scripts/build_static.py`, does
hash to it. Run `python3 scripts/release_from_live.py --live <release dir> --check-base` to check this.

## Files shipped minified (source on this branch, verified by reproduction)

| Path | Shipped bytes | MANIFEST sha256 (minified bytes) |
|---|---|---|
| `public/css/admin/admin.css` | 41561 | `6ca27a5643e588d7f4f6fc30078191171536f3feab92c4cdd393e0d8375a602b` |
| `public/css/fair.css` | 64791 | `b1c4b2e54b516bfa771332ae109d95afb0bc577be2981c3d748f5959e4332d53` |
| `public/css/invest.css` | 8648 | `7bcc9df6cc876d4ba039a2d8502b657ac7e9e810673ffb56a42d765e505beb3a` |
| `public/js/admin/main.js` | 27353 | `9eb98a783912499b09f8784837fe13ef8cc2c95d3664fe7a8ca6f7676f417426` |
| `public/js/admin/users.js` | 10481 | `5a9e9c7cf41c163d7a392bb4fb464b53f60ad8fd252052cd06b064586222553b` |
| `public/js/api.js` | 13831 | `f64bc00b0a160b6505a7aca5a20677c8266c891e0287fc36e0d333574758629c` |
| `public/js/app.js` (source rebuilt) | 160188 | `5e2bac53ea8406bc6fc72fafc90eeaabf680991732da88f462fd539326b9c1ed` |
| `public/js/operations-ui.js` | 24559 | `ece0cd152c926494bbce10c6460b390065349c5164822dabbe6a3a52f705743c` |
| `public/js/telemetry.js` | 8313 | `6af1a6a84f628f9734fa9c4a47329949ca6a4363b8865e239dc968eff388a16d` |
| `public/js/tutorial/guide-content.js` | 358777 | `159b661f7b64a1c369d5b8e29f51e30d8075d8963da8a9b1d2688f7630a4f8d6` |
| `public/js/v4/business-economy-ui.js` | 1540 | `77869778b66d729f597b4fbba5888d95449936f7d3ecb85725aef8ae31465e62` |
| `public/js/v4/fair-booth.js` | 35621 | `42098fe20fa562a5584ff9c9bbca55c69a18b824b3d7866568b9dd7ad2fa389a` |
| `public/js/v4/fair-knife.js` | 20186 | `924f479252eb7401338ca30429f8ae22df7998b33ea674976054e56fe10daa1e` |
| `public/js/v4/fair-scratch.js` | 9152 | `496569c8806049cb74ff80fa6377175012e777314c0af9d1219726d23f7a7c41` |
| `public/js/v4/fair.js` (source rebuilt) | 83249 | `ae3b0398841ddd81b8b040b8901803aa9db3916c1e315867f7d8a9654e815e8b` |
| `public/js/v4/invest-chart.js` | 2958 | `ffcf13c39847d340e837c439c48204a07351b7d4848627be2b7476efc6914c27` |
| `public/js/v4/invest-market.js` | 3034 | `18ed2ccc464b38c94fc635be5f2108a30c8fcb8bc4faa3ab94751de50e79b09a` |
| `public/js/v4/invest.js` | 18331 | `e40862aa0394286c38d7e4542418f5d3f7deeb5d62ce485b0a7a28ba95ac6ce3` |
| `public/js/v4/quay-sync.js` | 1272 | `c6e92bbfd154f7d06bf6564ed349277c1e6ea142f183493b2d7c75c793a08670` |
| `public/js/v4/quay.js` | 65514 | `1a3243a02c5cec53b67d59af5550a86ce5fdefdcf0d823cfe2e315401c9eba82` |
| `public/js/v4/rui.js` | 15032 | `32c6c3fa8365d7c5a82469a452d6aba99337a5ae6485ce235a436fe3c0ef628d` |
| `public/js/v4/work-equipment.js` | 1955 | `f0fcc4db21ba8a5ea14c4a16f0ed975f2026224bf4d04cccccab2dee02dec4b3` |

## Minified-only files (no source)

None. `scripts/release_from_live.py` reads the table below. It refuses to build a release that changes a
file listed there, because no source for it exists. If production ever ships a file whose source cannot be
found, add it here as `` | `path` | sha256 | ``. The operator who deployed it holds that source.

<!-- minified-only:begin -->
| Path | MANIFEST sha256 |
|---|---|
<!-- minified-only:end -->

## Releasing from this branch

Do not `scripts/package.py` this branch for production. It would re-minify every JS/CSS file, so every URL
changes and players re-download the whole front end. Use `scripts/release_from_live.py` instead. It starts from
the live release, replaces only the files that differ between this branch and the ref you name, minifies those
the way `package.py` does, and rewrites their MANIFEST entries. The task-compatibility gate still applies:
`python3 scripts/check_task_compat.py <tree of live-1.7.15> <tree of your ref>`.
