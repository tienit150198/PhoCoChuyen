# Temple and Public Venues Implementation Plan

> **For agentic workers:** Use TDD for owned behavior changes. Independent backend, temple UI, and public room work is delegated under dispatching-parallel-agents. Root owns routing/integration/release.

**Goal:** Unlimited temple visits with persistent family wishes, and physical movement inside public leisure destinations.

**Architecture:** Existing chua reducer and three-area canvas; optional archived cards; shared local venue room around existing server-authoritative transactions. Both classic and isometric routes enter the same scene.

**Tech Stack:** Python/PostgreSQL; JavaScript Canvas/ES modules; existing avatar/movement helpers; pytest/Node/Playwright.

- [ ] Backend worker: write failing repeat and persistence tests in tests/test_chua.py and tests/test_chua_cards.py; change game/chua.py and chua.cards registration in game/archive.py; verify 100 repeats, old save, rollover, spirit clamp, payload validation, request replay and archived overflow.
- [ ] Temple UI worker: update public/js/v4/chua.js, chua-visit.js, scenes/chua-place.js and css/chua.css. Render card composer at fence, saved cards and unlimited wording. Verify movement/blocked routes, repeats and reload through node and browser_chua.py.
- [ ] Public room worker: create v4/venue-visit.js, scenes/venue-place.js and css/venue-visit.css with pure navigation tests. Verify reachability, obstacle collision, range check, keyboard/touch, exit/dispose and responsive rendering.
- [ ] Root: wire spendChua directly to existing openChua; route spending, public outings and live game venue entries through openVenue. Add internal station dispatch distinct from entrance dispatch to prevent loops; preserve existing payment confirmations. Correct classic leisurePlace route.
- [ ] Root: update shared translations using supplied sidecars, add routing/parity tests and a browser matrix with real doors, avatar movement and station interaction. Run affected Python suites and JS/typecheck/build checks.
- [ ] Root: review changes, update version/release notes; reconstruct package from live2.1.0 bytes; verify clean install and old task compatibility. Guard live hash and free space, deploy, verify full HTTP bodies/asset hashes/services and record release evidence.
