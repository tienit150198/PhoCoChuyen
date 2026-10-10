# Living districts, 3D homes and shared treasure implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development and dispatching-parallel-agents for independent owners below. Existing user authorization is to implement and test locally; no deployment, release message, commit or push in this pass.

**Goal:** Make existing social/leisure/housing systems discoverable and usable in the illustrated world, add a real 3D home presentation with shared residents, and server-authoritative recurring treasure.

**Architecture:** Existing Python/PostgreSQL save/economy and live authorization remain authoritative. Phaser retains the outdoor island. Three.js is bundled separately and loaded only when the 3D home is opened. Housing/decoration/children/pets use existing records, with no duplicate save by renderer. Ambient NPCs are deterministic cosmetic prefabs reused locally; real people use authorized room presence. Global treasure waves are persisted, single-winner, and proximity validated, independent of how many clients are open.

**Tech Stack:** Phaser + TypeScript, lazily bundled Three.js, existing JS/SVG art, Python + PostgreSQL + live WebSocket service.

## Decisions and scope

- Four housing groups come from `game/housing.py`: rented rooms/dorm, apartments, townhouses, villas. District shapes and colors differ; do not invent owned properties or expose private interiors to arbitrary visitors.
- 3D home supports orbit/zoom, floor movement, furniture selection/place/move/rotate/store, existing paint and repair commands, outdoor rooms, existing children/pets, and current authorized roommates/visitors. Preserve old UI fallback when WebGL is absent.
- Tenants sharing a physical rental see the same authorized room and furniture; shared rental/public neighborhood presence is separate from private home access.
- Fair, dog race, dog tug, home decoration, garage/motorbike/car and existing activities keep distinct actions and eligibility. No duplicate economy/minigame implementations.
- Ambient crowd has reusable models/textures and a bounded visible pool. Movement is cosmetic, is paused when hidden/covered, does not write saves or use per-NPC network traffic. Player updates are batched and scoped to the active room/map; use existing capacities instead of rendering the entire server population.
- Treasure: one shared wave per UTC 600-second bucket, 3–5 random valid public locations, 10,000 journey-wallet xu per chest, first eligible nearby authenticated player only, idempotent retries. Chest expires at next bucket; no accumulation or restart catch-up payouts. Server retains bounded claim audit and replay protection. Feature defaults off until rollout configuration; local test activation only. In-game wave notice is implemented; no release announcement sent.
- Occluding buildings fade to a visible alpha floor (~0.35), never zero; restore when player leaves. Camera culling of off-screen objects is separate and retained.

## Work ownership and verification

### A — True 3D home (worker)

Own `client/home3d/*`, `public/js/v4/home-3d.js`, integration in `public/js/v4/reno.js`, relevant home styles and new home3d tests. Extend home presence only if necessary, coordinating `live/home.py` with parent. Parent owns package/dependency setup and island renderer.

- [ ] Read actual deco room/skin/placed item models, visitor/rental access and crowd contracts before changing anything.
- [ ] Write and run failing tests for 3D layout coordinates, item selection/edit adapter and lifecycle disposal; then implement.
- [ ] Render structural floor/walls/furniture geometry, warm lighting, distinct indoor/outdoor rooms; support orbit/zoom/raycast instead of drawing the old whole room on a plane.
- [ ] Route 3D pointer operations through existing checked commands; retain ownership restrictions and error feedback.
- [ ] Reuse existing home-crowd live data, children and pet records; remove listeners/resources when closed and render only when necessary.
- [ ] Build and test own module; provide exact integration API and manual browser checklist.

### B — Shared treasure backend (worker)

Own new `game/town_treasure.py`, `live/town_treasure.py`, HTTP routes in `server.py`, necessary feature registration/config and new tests. Coordinate before touching `live/town.py`; parent owns town client hooks.

- [ ] Write and run failing tests for 3–5 globally stable spawns per 10-minute bucket, expiry/restart, proximity, single-winner concurrency and reward idempotency.
- [ ] Persist wave/claims transactionally in existing schema; no caller-supplied wallet amount or trusted raw coordinates.
- [ ] Schedule waves on server, bound cleanup/history and caches, disable production activation by default. Serve active waves and in-game notifications without repeated per-frame queries.
- [ ] Claim checks authenticated identity plus recent authoritative live position, locks claim and wallet mutation together, returns normal state/revision.
- [ ] Provide client contract, authorization and activation instructions, run isolated PostgreSQL tests.

### C — Existing facilities and district inventory (worker)

Own `game/town_layout.json`, `public/js/isometric/town-utilities.js`, new amenity/district data and tests; no edits to parent Phaser renderer or B server routes.

- [ ] Compare existing fair/dog/garage/housing/household/pet actions with map/guide. Report full mapping, not just requested examples.
- [ ] Add distinct safe approaches/plots for fairground and dog racing, home decoration and housing districts based on actual housing groups; preserve routes/footprints and explicit fair versus black-market routing.
- [ ] Add clear guide/actions for vehicles, children/pets and existing events; only register implemented features with correct gates.
- [ ] Create illustrated art where needed with built-in imagegen, inspect references first, preserve alpha and keep static assets small. Do not substitute repeated generic houses.
- [ ] Test every approach reachable and no road/door collisions, with client/server data parity.

### Parent — World integration, performance and verification

Own `client/isometric/phaser-world.ts`, `visibility.ts`, `model.ts` as needed, new district/prefab/client treasure modules, package/build files and integration checks.

- [ ] Regression test occluder visible floor and restoration, then fix alpha target.
- [ ] Integrate housing district scenes/routes with genuine saved/public property data, safe pagination/privacy; coordinate backend additions if needed.
- [ ] Build client chest views and pickup UX against worker B API; announcements stay in game and feature disabled by default.
- [ ] Reusable ambient NPC/vehicle pool with fixed archetypes, shared textures/models, capped movement/network updates and hidden/idle cleanup. Keep real people distinguished from ambient NPCs.
- [ ] Integrate lazily bundled 3D scene and visually inspect with actual local state, desktop/mobile input, decorations/paint, family/pets, renters and visitors where test fixtures permit.
- [ ] Run focused regressions, build/typecheck, source syntax/Safari checks where supported, server race and isolation tests. Review spec coverage, then independent quality review.
- [ ] Save screenshot evidence and explicit verified/unverified limits. No deployment or release notification.

## Acceptance examples

`spawn(now=600*n)` produces the same 3–5 chests in two server workers; moving to the next bucket expires previous chests. Two simultaneous claims on one id yield one wallet increment of exactly 10,000, and a retry returns the same result. Stale/off-map/remote positions cannot claim.

Opening a rented room and then a villa produces different room geometry from the existing catalogue. Moving an owned chair and painting through 3D retains the change after reload and through the original renderer. An unauthorized visitor cannot edit another person's room. The house continues to appear at reduced opacity when it covers the player.

Existing uncommitted work is preserved; workspace is the existing linked worktree `wt-feedback-0410` on the user-selected `main` branch.

## Execution record — 2026-10-11

Code and automated verification have been implemented in this workspace. The checklist above is the original implementation plan; the actual tested behavior and remaining visual/load limits are recorded in [the verification report](2026-10-11-living-districts-verification.md). Real browser checks cover the apartment courtyard, entering the existing attic, opening the decor editor, walking on the 3D floor and returning to the island. Production deployment and release announcements remain unperformed as requested.
