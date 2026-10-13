# Creative and Civic Careers Implementation Plan

> **For agentic workers:** Follow test-driven-development for owned modules. Independent career domains may be implemented in parallel under dispatching-parallel-agents; parent integrates shared registries and reviews.

**Goal:** Four distinct, durable careers with progressive complexity and balanced pay.

**Architecture:** Existing Python career plugin contract and lazy JS career modules. Each career owns content, deterministic task factory, commands, public projection, persistence validation and UI; parent owns shared registries, town layout, balance audit, release and translations.

**Tech Stack:** Python engine/PostgreSQL, JavaScript ES modules, TypeScript isometric renderer, pytest, Node and Playwright.

## 1. Independent career implementations

- [x] Lawyer: create `game/careers/lawyer.py`, optional `lawyer_content.py`, `public/js/careers/lawyer.js`, `public/css/careers/lawyer.css`, `tests/test_career_lawyer.py`.
- [x] Laundry: corresponding files named `laundry`.
- [x] Post office: corresponding files named `post_office`.
- [x] Art studio: corresponding files named `art_studio` (parent).

Each owner first runs a failing registration/behavior assertion, implements the plugin contract from `game/careers/kit.py` and `pagoda.py`, then verifies a complete correct path, wrong decision outcome, repeated completion refusal, out-of-order action refusal, immutable generated fields, public hidden-state filtering and JSON validation. Run `python -m pytest tests/test_career_<id>.py -q`. Save player-facing rules and progression in public content; never generate tasks from mutable wall time. Parent alone edits ORDER so others test with temporary in-process registration when necessary.

## 2. Shared integration

- [x] Add IDs to `game/careers/__init__.py`, `game/journey.py` chapter unlocks and required backend role/taxonomy maps.
- [x] Add scene/vocabulary/guide definitions and safe town positions in existing map registries. Update count contracts to the explicit 54-ID catalogue rather than weakening uniqueness checks for existing assets.
- [x] Verify `set(new_state()['careers'])` has all four and old-state migration adds them without altering old tasks.
- [x] Ensure story-mode income is paid through the appropriate shop/hired path, not duplicated. Simulate full jobs at days 1,4,10,20,40,60 and compare work/reward ratios; record exact outcomes and unlock requirements.

## 3. Review and acceptance

- [x] Parent reviews all changes and independent reviewer checks save/transaction/progression safety.
- [x] Browser exercise each career through real UI at 390px and desktop with a local test database; validate no page errors/overflow and live task progress survives reload.
- [x] Run scoped career, registry, migration, JS/typecheck/isometric build tests and old-task compatibility against live2.0.7.
- [x] Translate added user-facing text into English, verify pack, add release notes, package from live bytes, verify fresh installation, deploy guarded rolling release and verify public health/assets.
- [x] Record what shipped, numerical balance evidence, known limits and compatible rollback route; do not roll back to a server that rejects the four career IDs.
