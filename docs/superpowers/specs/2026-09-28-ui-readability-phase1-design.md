# UI readability, phase 1: shared kit + Quán mì cay

Date: 2026-09-28 · Branch: `ui-readability`

## Problem

Players find the game hard to read:

- orders, situations and hints are long run-on sentences;
- screens hold too many things with no clear order;
- there is no place to look up menu, prices, stock or rules;
- phones feel cramped.

The root cause is missing information hierarchy, not tokens or fonts. `docs/DESIGN.md` is fine and stays.

## Roll-out (one spec + plan per phase)

1. Shared kit + Quán mì cay (this spec).
2. Trà sữa, Tiệm bánh & cà phê.
3. Shop/service careers.
4. Paperwork careers.
5. Shell screens (situations, reviews, home, journey).

## Phase 1 design

### Shared kit: `public/js/ui-kit.js` + section in `public/css/app.css`

- `reqList(rows, esc)`: the requirement list. Each row is `{ok, icon, label, value, note, tone}`.
  - `ok`: `true` ✓ / `false` ✗ / `null` ○.
  - `value`: short right-aligned text, e.g. `1/2`.
  - `tone`: `'danger' | 'warn'` for alert rows (allergy, vegetarian) that always stand out.
  - Renders `<ul class="req-list">` with a `.req-row` per row.
- `fold(summary, body, open)`: a `<details class="fold">` with a one-line summary, for guest quotes, stories and tips. Closed by default.
- `refTable(groups, esc)`: groups of `{title, rows:[{icon, name, price, stock, tags:[{label,tone}], locked}]}` for look-up sheets.
- `.ref-tag` chips for seafood / veg / meat.

### Quán mì cay

- **One order card.** The prose order (`say()`) and the separate "Kiểm tô" checklist are merged into one requirement list inside the order card. It shows live ✓/✗/○ from `checklistRows()`, which is extended with icons. The collapsed "Kiểm tô" details block is removed.
- The guest's own words (`n.note`) and the story move into `fold()`.
- **Picture** and **"như mọi khi"** orders keep hiding the spec on purpose. The picture row stays in emoji, and the masked order keeps its recall/re-ask buttons. Nothing the server hides is revealed.
- **Open orders** ("tô tùy quán") become rows: budget, spice range, broths allowed, must-have, avoid, vegetarian, minimum toppings.
- **"📖 Thực đơn" sheet**: new dock entry `menu` → `refTable`, with:
  - broths (price, pot portions, unlock level, seafood tag);
  - toppings (price, stock, unlock, seafood/meat/veg tags);
  - 4 short rules: boil window, 1 pump = 1 spice level, swap when out of stock, takeaway needs a lid.

  It is rendered client-side from `x.cc` + `x.room`; no server change.
- **Phone:**
  - order text is at least 15px, with roomier rows;
  - the day strip is a single line once the shift has started;
  - the sticky "next step + Giao" bar stays.

### Not changing

Game rules, server, grading, and the difficulty of picture and masked orders.

## Testing

- `node scripts/check_js.mjs` and `python3 scripts/run_checks.py`.
- `python3 scripts/i18n_extract.py` for new strings.
- Screenshots at 390px and 1280px in the `kem` and `dem` themes, taken with playwright installed into the scratchpad.
