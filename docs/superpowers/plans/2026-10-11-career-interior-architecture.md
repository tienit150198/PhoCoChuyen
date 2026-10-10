# Career Interior Architecture Implementation Plan

> **For agentic workers:** Execute the authorized interior subtask sequentially in the existing shared worktree. Do not commit, deploy, build bundles, or alter the town renderer.

**Goal:** Give all 50 career rooms recognizable physical architecture while preserving saved decoration and gameplay navigation.

**Architecture:** A typed registry authors each cutaway envelope, wall materials, apertures and occupational fittings. Architectural solids stay within existing furniture footprints or outside the navigable room. A pure drawing adapter feeds the existing Phaser static ground cache; nothing is added to the animation loop.

**Tech Stack:** TypeScript, Phaser Graphics, esbuild, Node assertions.

### Task 1: Lock down the contract

- [x] Add `tests/isometric-work-architecture.mjs`: all 50 registered careers; unique structural geometry without names/colors; material and aperture diversity; unchanged window anchors; solids contained by existing furniture; station/actor routes with saved decor.
- [x] Run the test and record the expected missing-architecture failure (`milk_tea: physical architecture must accompany the occupational plan`). A second red test proved platform lifting was absent before it was implemented.

### Task 2: Author physical rooms

- [x] Create `client/isometric/work-architecture.ts` with explicit career envelopes, occupational fittings, and pure static drawing commands.
- [x] Attach resolved architecture in `client/isometric/work-layout.ts` after all legacy stations exist. Preserve station IDs, approaches and spawn.
- [x] Integrate only the interior `work()` rendering section in `client/isometric/phaser-world.ts`, replacing common two-wall shell with authored architecture.

### Task 3: Verify

- [x] Run the new architecture test, existing work-layout test and TypeScript typecheck; inspect rendered architecture contact sheets. Passed 50 architecture plans and 51 navigation plans (including fallback); typecheck passed after the independently owned gallery errors were resolved.
- [x] Check the scoped diff and report exact results and limitations to the parent. No bundle, commit or deployment. Contact sheets are architectural studies with neutral furniture massing, not full browser screenshots.
