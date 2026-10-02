# TikTok Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Add TikTok login and account linking while preserving existing password login and game saves.

**Architecture:** A dedicated server OAuth module validates a short-lived browser-bound flow and connects verified TikTok identities to existing accounts/logins. Existing password authentication remains intact. The UI adds a separate TikTok action and backend metadata; production deployment uses an overlay of the changed files on the current release.

**Tech Stack:** Python standard library, SQLite/PostgreSQL abstraction, vanilla JavaScript modules, unittest, TikTok OAuth v2, nginx/systemd rolling deploy.

## Task 1: Implement and test additive authentication

Files: create `game/tiktok_auth.py`, `tests/test_tiktok_auth.py`; modify `game/storage.py`, `game/pg_schema.py`, `game/accounts.py`, `server.py`, `public/js/api.js`, `public/js/v4/account.js`, `public/privacy.html`, `.env.example`; add targeted frontend tests if supported by the existing test harness.

- [ ] Write failing tests for unavailable config, authorized start, cross-origin/CSRF rejection, flow-cookie binding, expired/replayed state, account creation preserving guest save, linking preserving password, identity conflict, second-device login and progress confirmation, provider failures, deletion and unchanged password login.
- [ ] Run `python -m unittest tests.test_tiktok_auth -v`; confirm failures are caused by absent functionality.
- [ ] Implement environment config and OAuth request helpers. Authorization URL is `https://www.tiktok.com/v2/auth/authorize/`; token URL is `https://open.tiktokapis.com/v2/oauth/token/`; user info URL is `https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name`. HTTPS callback is fixed by config. No redirects from provider requests and no provider response text is passed to users or logs.
- [ ] Add DB schema for identities and flows on both SQLite and PostgreSQL. Guard transactions with the existing row-lock helpers; store hash identifiers, one-use phases and expiry.
- [ ] Add a CSRF-guarded `POST /api/account/tiktok/start` accepting mode login/link. Set a temporary Lax cookie and return an authorization URL. Add callback and confirmation routes preserving the game Strict cookie policy. Bind callback to the original active session and flow cookie. Validate state before exchanging code. Use safe fixed error messages and strip query secrets from logs.
- [ ] Reuse account registration/login token rotation. Link only explicitly from an authenticated account. Never match accounts by display name or blindly overwrite progress. Do not store provider access or refresh tokens.
- [ ] Add TikTok button next to normal forms; keep existing form validation, actions, fields and password routes. Show linked status for local accounts; show usable account controls for TikTok-only accounts. Capture callback error/status in the account screen and remove those query parameters from the address after display.
- [ ] Update bilingual privacy policy and environment documentation without secrets.
- [ ] Run `python -m unittest tests.test_tiktok_auth tests.test_accounts tests.test_http tests.test_http_v4 tests.test_storage tests.test_pg_schema -v` (use existing module names; if no test_pg_schema exists, run the relevant PG backend schema tests). Verify JavaScript syntax and frontend behavior with the existing Node harness.
- [ ] Implementer self-review, then independent spec compliance and code-quality reviews; fix findings and rerun affected tests.

## Task 2: Configure, deploy and verify

Owned by coordinator; implementation worker must not access production or browser secrets.

- [ ] Read Sandbox client key/secret through the existing browser UI into a temporary private transfer file, without printing values; transfer to a root-readable environment file and remove the temporary file.
- [ ] Inspect current live release and hashes. Copy that release to a new directory; overlay changed files only and apply an additive DB schema. Check syntax, new imports and deploy preconditions before traffic moves.
- [ ] Add safe nginx logging for the callback path; retain access status/IP logs without query values. Keep the domain verification exact location.
- [ ] Run the existing rolling release script under its lock, with the current release available for rollback.
- [ ] Verify public health, both login methods and the real TikTok authorization screen. Add the user's own Target User if the browser offers account authorization; hand off only a required user login/CAPTCHA/legal consent step.
- [ ] Save browser screenshot proof, update nonsecret handoff notes and report exact completed/remaining status.
