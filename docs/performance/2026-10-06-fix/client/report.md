# Client frame-pacing investigation — 2026-10-06

## Scope and outcome

Inspected `client/isometric/phaser-world.ts`, the navigation/character-cache model and `public/js/isometric-town.js`. Used the existing local preview at `127.0.0.1:18891` in a separate guest browser. No saved economy actions, production writes, server changes, or client runtime changes were made for this investigation.

Initial and follow-up walking measurements did not reproduce a sustained client frame-pacing bottleneck: every scenario had a 13.4 ms frame p95, with no measured rAF interval above 50 ms. There were isolated 26–40 ms intervals in CPU-throttled runs, so this is not a zero-jitter claim. The scene's existing static ground cache, reused character textures and sleep-on-idle behavior worked. No speculative client optimization is justified by this evidence.

## Environment and method

- Host CPU: Intel Core i7-12700K, 12 physical cores / 20 logical processors; Windows.
- Browser: headed Chromium 154.0.8037.95, viewport initially 1280 × 720, device pixel ratio 1.
- Observed refresh cadence: approximately 75 Hz (13.3 ms rAF interval), despite Phaser's configured target of 60.
- CPU throttling: DevTools `Emulation.setCPUThrottlingRate`, rates 1 and 4. This slows main-thread execution; it is not a physical phone or GPU test.
- The parent agent paused the server stress load during timed samples. Preview API/live services remained available.
- Each sample warms the scene for 1.2 seconds, then walks the same horizontal road for 6 seconds. Local player moves from about x=6.2 to x=20.5 at y=6.2, preserving route/collision behavior.
- Crowd: 29 synthetic local renderer peers updated every 270 ms, matching the existing room cap of 30 including the local player. These are renderer fixtures, not authenticated network clients. Total 1,000 CCU is a separate server-capacity measurement.
- Collected actual rAF deltas, long tasks, main-thread/CDP metrics, timed Phaser render/update/cache methods, actor reuse and scene sleep. These are warm-scene diagnostics, not initial-download/load benchmarks.

## Initial results

| Peers | CPU throttle | Frames | Frame p95 | Max frame | Frames >25 ms | Render p95 | Peer sync p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1× | 449 | 13.4 ms | 26.6 ms | 1 | 0.9 ms | — |
| 29 | 1× | 450 | 13.4 ms | 13.5 ms | 0 | 1.5 ms | 0.9 ms |
| 0 | 4× | 449 | 13.4 ms | 26.7 ms | 2 | 6.0 ms | — |
| 29 | 4× | 450 | 13.4 ms | 14.3 ms | 0 | 7.0 ms | 4.5 ms |

Raw measurements: `before-1x.json` and `before-4x.json`. All four samples reuse the player sprite. After clearing movement/peers, the renderer sleeps; the ordinary scene contains 532 objects and the crowd scene 590. The initial crowd remained on the same road while the local camera moved away, so these rows prove 29 active peer updates but do **not** prove all 29 remain visible throughout. Follow-up fixtures correct that limitation by keeping the crowd near the local player and recording its visibility count.

## Follow-up: 29 peers inside the camera throughout

Every sampled frame reported exactly 29 peer sprite centers inside the camera world-view rectangle. This does not assert that overlapping names or buildings never occlude them.

| Viewport / actual zoom | CPU throttle | Frames | Frame p95 | Max frame | Frames >25 ms | Render p95 | Peer sync p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1280 × 720 / 0.8 | 4× | 445 | 13.4 ms | 40.1 ms | 4 | 7.1 ms | 4.0 ms |
| 360 × 780 / 0.64 | 1× | 450 | 13.4 ms | 13.5 ms | 0 | 1.4 ms | 1.0 ms |
| 360 × 780 / 0.64 | 4× | 447 | 13.4 ms | 26.7 ms | 3 | 6.3 ms | 4.2 ms |

Files: `before-visible-desktop-4x.json`, `before-visible-mobile-1x.json`, `before-visible-mobile-4x.json`. No long tasks were captured. The largest timed canvas-render call was 45.5 ms in the desktop 4× run; the largest ground-cache call was 14.4 ms. These isolated costs are worth retaining in the evidence, but the short test cannot attribute a one-off browser scheduling/GC interruption to a repeatable application defect.

An extra `before-visible-zoommax-4x.json` requested zoom 1.6, but the recorded actual zoom was reset to 0.8 during viewport settling. It is **excluded as maximum-zoom evidence**; the label describes the attempted fixture, not a verified camera state. Maximum-zoom frame pacing remains unverified.

## Functional and visual checks

`functional.json` records real keyboard movement/release, camera zoom in/out, whole-island overview and recenter, settings open/Escape, and 390 × 844 / 1280 × 720 viewport resizes. The player moved, the loop slept after release, the canvas bitmap matched both viewport sizes, no document overflow appeared and no JavaScript errors were observed. Settings were opened with movement already stopped; this check alone does not certify interrupting a held movement key.

Screenshots `desktop-final.png` and `mobile.png` were inspected. The soft 2.5D art, smooth sprites and main HUD remain rendered. The mobile resize intentionally resets the camera to the existing fitted initial view; the earlier player position can be outside that view until recentering. This is existing camera behavior, not a frame-rate issue or a new change.

`npm run typecheck:isometric` and `npm run test:isometric` passed (the icon suite's optional live-server catalogue check was skipped, as reported by that existing test). No runtime fix/build artifact was changed, so there is no fabricated before/after improvement claim.

## Reproduction

Copy `sample.cjs`, `run-sample.ps1` and `functional.cjs` from this folder into `output/client-perf-20261006/` before running the commands below; generated measurements remain outside tracked source. From the worktree, open a separate guest browser and dismiss the changelog through its normal UI:

```powershell
npx --yes --package '@playwright/cli' playwright-cli '-s=frame-diagnosis' open 'http://127.0.0.1:18891/?isometricdebug=1' --headed
& 'output/client-perf-20261006/run-sample.ps1' -Label before -Rate 1
& 'output/client-perf-20261006/run-sample.ps1' -Label before -Rate 4
& 'output/client-perf-20261006/run-sample.ps1' -Label before-visible-desktop -Rate 4 -FollowPeers
& 'output/client-perf-20261006/run-sample.ps1' -Label before-visible-mobile -Rate 1 -FollowPeers -Width 360 -Height 780
& 'output/client-perf-20261006/run-sample.ps1' -Label before-visible-mobile -Rate 4 -FollowPeers -Width 360 -Height 780
```

Run only with server stress load paused. The harness resets renderer position/peer fixtures and returns CPU throttling to 1×. It makes no economy calls. It uses an explicitly enabled `isometricdebug` object for repeatable staging; normal keyboard/camera control checks are separate in `functional.cjs`.

## Limits

Short warm-scene routes do not certify every device, real network interpolation/jitter, corner-crossing A* paths, every career/effect, first asset decode, cold-cache startup, GPU limits, battery/thermal throttling, high-DPI phones or long gameplay sessions. Potential code costs such as repeated remote appearance serialization and depth sorting remain hypotheses: measured update costs here were below the frame budget, so they were not changed.
