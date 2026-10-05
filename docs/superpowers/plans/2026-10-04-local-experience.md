# Local experience implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Deliver a playable local preview with clearer goals, fair learning, understandable promotion and a story pilot that remembers choices.

**Architecture:** Extend existing Python public-state projections and vanilla JavaScript screens, preserving old saves and existing economy rules. Build on current story beats rather than replacing the narrative engine. Run against an isolated local SQLite database.

**Tech Stack:** Python, unittest, vanilla JavaScript, Node test harnesses, Playwright.

## 1. Fair learning and promotion

Files: game/boba.py, game/promotion.py, public/js/careers/milk_tea.js, public/js/v4/promo.js, tests/test_experience_clarity.py.

- [x] Write and run failing tests for repeated self-check without mistakes and promotion ratio blockers.
- [x] Make So phiếu a free learning check; retain consequences for actual wrong delivery and waste.
- [x] Project and show every promotion requirement including good-day ratio and retry wait.
- [x] Run focused existing and new tests.

## 2. Story pilot

Files: game/career_stories.py, public/js/v4/stories.js, associated story CSS, tests/test_story_experience.py.

- [x] Test recap, next unlock requirements, remembered choices and legacy-save safety.
- [x] Add recap and legible next-step information to story cards without revealing future plot.
- [x] Give milk tea/Linh and repair/radio specific callbacks to earlier choices with visible story consequences.
- [x] Run existing story tests and new tests.

## 3. Actionable goals

Files: public/js/v4/journey.js, public/js/app.js, journey CSS, game/journey.py if necessary, tests/journey_experience.mjs.

- [x] Test goal CTA routing and mobile ordering.
- [x] Place current goals ahead of secondary journey content and attach truthful actionable navigation.
- [x] Clarify Đổi nơi làm in existing navigation, preserving destinations.
- [x] Run existing navigation tests and new tests.

## 4. Integration and local preview

Files: game/guide_content.py, generated public/js/tutorial/guide-content.js, i18n/overrides.json, public/i18n/en.json, public/js/v4/dayclock.js if needed.

- [x] Update instructions that conflict with changed mechanics and clarify game-time labels.
- [x] Review spec compliance, then code quality; repair material issues.
- [x] Run relevant Python/Node regression tests and git diff --check.
- [x] Start local server with DATABASE_URL removed and isolated SQLite; inspect desktop/mobile and story pilot.
- [x] Open local preview for user and leave it running. Do not deploy.
