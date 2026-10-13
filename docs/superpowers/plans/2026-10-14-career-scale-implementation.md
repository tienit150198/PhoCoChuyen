# Career scale implementation and two releases

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Complete tasks with focused regression tests, spec review and code-quality review; do not pause between tasks for permission already granted by the owner.

**Goal:** First publish the completed 2.3.1 changes; then implement the approved 54-career expansion design and publish its tested implementation.

**Architecture:** Keep the authoritative command reducer and PostgreSQL receipts. Add small modules for immutable scale content, owned sites/resources, management contracts and account-wide daily quotas. Reuse career money, paid stock/order rights, business certificates, inventory accounting, real-time progress, NPC competition and existing navigable 2.5D interiors. New sidecars are optional on old saves; no legacy task generation changes.

**Tech Stack:** Python authoritative game engine, PostgreSQL storage/receipts, ES modules, current 2.5D renderer and WebSocket presence, unittest/pytest and Node/browser checks.

Approved spec: `docs/superpowers/specs/2026-10-14-career-scale-design.md`. The 54-ID matrix and exact proposed prices are in `career-scale-evidence/`; analysis files must not become runtime dependencies.

## Release A — existing completed changes

- [x] Confirm live version/path/manifest, health, disk reserve and rolling preconditions.
- [x] Compare live task generation against current source: all 53,280 rows pass.
- [x] Run Node order/social/lawyer/marriage UI regressions.
- [x] Finish targeted Python regression checks and verify freshly extracted release over HTTP.
- [x] Upload exact verified 2.3.1 ZIP; validate SHA and disk reserve. Roll inside tmux with `KEEP=999`, preserving old releases and DB.
- [x] Verify public health, service states, runtime hashes, changed static assets and logs; record source ref/manifest in deployment report.

## Task 1 — source contracts and immutable catalogue

Ownership: `game/career_scale_content.py`, focused content tests, generated translation sidecar only. No edits to engine, storage, deployment or frontend.

- [x] Export the approved 54 IDs, groups, eight scale titles, price factors, resource nouns and management evidence into an immutable runtime catalogue, independent of docs imports.
- [x] For every offered stage define purchasable benefit, site/resource totals, prerequisites, new contract types, resource roles and actual material/service units. New high-price retail lines must describe a real bundle/quality rather than multiply an unchanged item's price.
- [x] Add career-specific planning, allocation, exception and acceptance evidence. Public-service stages describe assignment scope, not purchased rank; pagoda stages have no capital price or cash yield.
- [x] Test `set(PROFILES) == set(CAREERS)`, 8 stages each, integer final prices, 402,300,000 grocery cumulative capital, resource totals not multiplied by site count, and well-defined costs for every catalogue item.

## Task 2 — owned scale, sites and progression

Ownership: `game/career_scale.py`, `game/career_scale_resources.py`, `tests/test_career_scale.py`. Engine hooks remain the integrator's responsibility.

- [x] Implement optional sidecar read/validate/public/action APIs: `public(s,c,cid,now=None)`, `action(s,c,cid,name,p,now=None)`, `validate(c,cid)`, and manual-work progress hooks. Keep explicit bounded schemas; reject booleans as integer prices, counts or timestamps.
- [x] Upgrade sequentially, checking expected tier, personal career funds, earned certificates, real qualified days and clean work before debit. Price and result derive exclusively from server catalogue. Record the exact capital receipt.
- [x] Plan site activation separately from buying scale. Reuse shared purchased secondary-location rights and count all occupied sites; preserve grandfathered assets. Each active site needs assigned resource and qualified NPC crew. No extra per-career allowance.
- [x] Model resource IDs, assignment, occupation/release and maintenance. Preserve larger existing resources. A machine, room, vehicle or worker cannot belong to two active jobs. Do not raise physical safety limits by buying generic capacity.
- [x] Count real-day qualifications from server time and witnessed manual work; retain established clean-work counters without fabricating timestamp history. Old saves remain playable.
- [x] Test exact debit, duplicate/stale purchase, missing certificate, insufficient funds, preserved stock/tasks/rights, invalid sidecars, capacity preservation and replay through Store.

## Task 3 — management contract accounting

Ownership: `game/career_scale_contracts.py`, `game/career_scale_inventory.py`, contract regression tests. Coordinate data/API names with Tasks 1–2 before edits.

- [x] Add a common account quota: four new advanced/management starts per real day, stored at most 12, initial one; cross-career use shares one counter. A reserved offer has stable identity/seed and cancellation cannot reroll it. No reset from career-day advancement.
- [x] Implement offer → budget/stock allocation → staffing/resource scheduling → exception response → acceptance → settlement. Persist partially completed work. Distinct career evidence and material requirements must affect outcome.
- [x] New material stock follows actual paid storage/order rights; reserve transit/drafts/contracts, preserve quantities and cost through movements. Existing stock must only be consumed once. Service/agency procurement uses its correct ledger; no fake warehouse for a job without goods.
- [x] Debit confirmed working capital once, hold escrow, then book consumed inputs, wages, premises, loss and exactly one tax treatment. Returned materials retain cost basis. Refund unused escrow; losses cannot exceed committed capital. No automatic borrowing.
- [x] Pay the realized contract result once, with no old staff/day/equipment multipliers. Agency budgets are nonwithdrawable and only earned personal allowances are credited; pagoda creates no new cash reward. Do not count new project income again in NPC competition bonuses.
- [x] Test full/80%/60% demand, partial resources, failed acceptance, cancellation, reload, global quota/day boundary, refund, malformed/stale payloads, exact cost basis, stock reservations, clock catch-up and Store idempotency.

## Task 4 — engine and frontend integration

Ownership: root integrator for `game/engine.py`, journey validation, shared slot integration; UI worker for a new `public/js/v4/career-scale.js`, scoped CSS and bounded entry-point changes agreed before edits.

- [x] Hook scale actions into no-tick command routing, project authoritative DTO only for focused career, validate sidecars, and record real-work evidence after authoritative task completion. Preserve legacy task generation and command shapes.
- [x] Provide comparison of current/next scale: final fee, actual resources, capacity, per-order limit, working capital, prerequisites and expected net under stated assumptions. Missing requirements disable the buy command with an actionable explanation.
- [x] Implement site selection, crew/resource assignments, stock purchases/movements and every contract stage as actual commands; never expose correct answer/hidden outcome in DTO.
- [x] Use existing Góp vốn for fund transfers; do not create implicit wallet withdrawal. Keep purchased convenience functional. Unsupported future content is non-purchasable.
- [x] Translate core navigation and finance labels; retain Vietnamese fallback for authored scenarios. Node checks cover escaping, large values, empty/locked states and duplicate clicks. Full English scenario translation is not claimed.

## Task 5 — navigable sites and social context

Ownership assigned after inspecting the current interior adapter; no changes to shared live protocol without separate tests.

- [x] Reuse each career's navigable interior with a stable owned-site context and visible stations/NPCs matching actual assignments. Add site selector and return route to chain overview; no fullscreen management-only substitute.
- [x] Bind interactions to the selected site and active resource/contract. Switching sites must not leak another location's actions, occupants, chat or reactions.
- [x] Verify mobile touch walking and desktop movement, station interaction, correct site labels, ownership checks, social privacy and reconnects. Use deterministic local test accounts; no production player-state mutation for screenshots.

## Task 6 — balance, review and Release B

- [x] Obtain read-only aggregate production liquidity/earnings evidence, excluding player identities. Compare proposed payouts with current income sources and existing paid upgrades; record assumptions and any justified tuning.
- [x] Use implemented commands to simulate every offered career/stage, reconcile all ledgers and confirm no multiplicative rewards or capacity duplication. CSV targets alone do not count as proof.
- [x] Run independent spec review, then code-quality/security-of-transactions review. Resolve findings and rerun affected checks.
- [x] Run task compatibility against the actual Release A source, all new focused suites, existing money/inventory/certificate/competition/social regressions, and real mobile/desktop browser flows.
- [ ] Build from verified live Release A bytes and its exact source ref; verify extracted package/HTTP. Publish only implemented, tested stages; do not charge for placeholders or report omitted stages as complete.
- [ ] Rolling deploy with package hash, disk, DB-connection and rollback-compatibility guards. Verify service/public health, assets, hashes, logs and representative read-only projections.
- [ ] Document both deployments and remaining limitations, stop local test services, leave source clean and report actual deployed behavior.

## Review boundaries

Do not edit existing task generators or silently reprice existing purchases. Do not infer 540 authored packages have been implemented merely by adding stage labels. Keep all 54 career paths in scope; a staged internal implementation is not permission to end after grocery alone. A compatibility-breaking sidecar requires a forward-compatible recovery build rather than restoring the database or blindly rolling code backward.
