# Free rowing implementation plan

> Execute inline with superpowers:executing-plans, systematic-debugging and test-driven-development. The user explicitly requested removing numbered checkpoints and unrestricted rowing; no new approval gate or commit is needed.

**Goal:** Chèo tự do trong mặt nước, không vòng thi, không mốc, không lưu thành tích; lên/xuống thuyền vẫn đúng vị trí bến.

**Architecture:** Boat movement and boarding are local simulation; existing public leisure presence still publishes positions. Fishing and pool retain their current server-backed rounds. Keep legacy boat receipts and server validation for old clients/saves. Avoid an API request per marker and keep the existing sleeping render lifecycle.

**Tech stack:** JavaScript simulation, Canvas illustrated scene, existing WebSocket public presence, Node regression tests, CUA browser verification.

## Findings

- `createPixelPlay.step()` sends checkpoints for boats, setting `busy` and freezing steering until HTTP completes; expired rounds change the player to return mode.
- The boat HUD shows numbered circles, a disabled save button and a lap counter despite promising free play.
- `drawPlaceActor()` draws a newly moored hull as soon as exit starts, even when the actual exit starts away from the exact mooring. It can visibly jump while the avatar crosses the water.

## Tasks

- [x] Add failing simulation tests in `tests/pixel-places.mjs`: boarding/steering/passing former markers/long idle/exit make no HTTP requests; boarding from shore still requires the dock; legacy malformed boat rounds cannot trigger checkpoint handling; exit hull stays at its actual position.
- [x] Update `public/js/pixel/places.js`: boat boards with `geometry.entry` and `round=null`; checkpoint and finish paths only apply to pool/fishing; boat interaction invokes physical exit; return retains a local entry without round proof; hide boat records/secondary button and draw no numbered marker/route arrows. Preserve steering and collisions.
- [x] Update keyboard/dialog regressions in `tests/leisure-keyboard.mjs`: boat primary button exits without finish request, pool save still works, canvas/joystick Space retain contextual behavior. Assert boat HUD has no save/lap/marker text and only the contextual action.
- [x] Run `node --test tests/pixel-places.mjs tests/leisure-keyboard.mjs tests/water-poses.mjs tests/leisure-art.mjs`, then `npm run test:isometric` and `npm run check`.
- [x] Use the local browser to verify boarding, former marker traversal, directional movement, pier collision, physical exit, reopening and mobile joystick. Capture screenshots and record observed limitations.

## Acceptance

Boat UI has no 1–4 circles, route demand, lap counter or save button. Player can continue beyond the previous round expiry without an HTTP round. Interacting far offshore only guides toward the pier, without moving the boat. Exiting animates from the actual boat position. Pool and fishing keep their independent behavior.


## Results

- New regression assertions failed on the old implementation (round creation, checkpoint freeze, HUD and mooring jump), then passed with the fix.
- 50 focused tests passed; full `npm run test:isometric` passed (one existing live-server test skipped). `npm run check`: 1036 JS files and 333 legacy Safari syntax targets passed. Scoped whitespace check passed.
- Browser desktop: crossed old checkpoint positions, circled the pier, held movement against its head, continued steering, requested exit offshore without teleporting, returned physically, disembarked and reboarded.
- Browser 390×844: joystick boarding, diagonal rowing, return and exit all exercised; no numbered markers, no lap/save HUD. Guidance switches between top and bottom to avoid the local actor.
- Long rowing session beyond the old expiry was verified using the simulation clock, not a one-hour browser wait. No live multiplayer load test was run.
- No new image requests, polling, animation loop or server mutations for boat rounds. Existing leisure presence still owns multiplayer updates.
- Evidence: `output/free-rowing-20261010/mobile.jpg` and `desktop.jpg`; logs `output/free-rowing-targeted.log`, `free-rowing-suite.log`, `free-rowing-check.log`.
