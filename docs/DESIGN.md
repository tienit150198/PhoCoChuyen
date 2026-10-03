# Design system (v0.5)

All game UI is styled by one stylesheet, `public/css/app.css`. The old v0.2–v0.4 files (`game.css`, `boba.css` and `cozy.css`) are now stubs, kept only so old links, tests and tooling still resolve. Career modules may add `public/css/careers/<id>.css`. Those files may use **only the tokens below**, so they work in every theme and layout.

The direction is "a small, warm neighbourhood": warm and playful, but clean. It uses:

- soft surfaces and rounded 16px cards;
- one strong accent per theme;
- emoji and small illustrations for character, never for meaning alone.

The font is Be Vietnam Pro (OFL, self-hosted in `public/fonts/`). It has 4 weights, 400/600/700/800, with Latin and Vietnamese subsets.

## 1. Tokens

Colours come only from tokens. Never hard-code a colour for chrome such as backgrounds, text, borders or states. The only exceptions are illustrations that stay the same in every theme: the chalkboard, the maps, the milk-tea shelf and the restaurant bowl. Even these are dimmed by `--scene-filter` in the dark theme.

### Required tokens

Every theme defines these. Career CSS relies on them.

| Token | Use |
|---|---|
| `--bg` | Page background behind everything |
| `--surface` | Cards, sheets, bars |
| `--surface-2` | Quiet panels, hover, inputs on cards, tab tracks |
| `--ink` | Main text (≥ 4.5:1 on `--bg`, `--surface`, `--surface-2`, `--surface-3`) |
| `--muted` | Secondary text (≥ 4.5:1 on `--bg`, `--surface`, `--surface-2`, `--surface-3`) |
| `--line` | Hairlines and card borders (decorative) |
| `--accent` | Primary buttons, selected state, highlights |
| `--accent-ink` | Text or icons on `--accent` (≥ 4.5:1) |
| `--good` `--warn` `--bad` `--info` | State colours; readable as text on `--surface` (≥ 4.5:1) |
| `--radius` `--radius-sm` | 16px cards / 10px small parts |
| `--shadow` | Raised elements (sheet cards, HUD) |

### Extra tokens

All themes define these too.

| Token | Use |
|---|---|
| `--surface-3` | Deeper panel, empty meters |
| `--ink-2` | Body text one step softer than `--ink` |
| `--line-strong` | Visible borders for buttons, tiles and chips |
| `--field-line` | Input and checkbox borders (≥ 3:1 against surfaces) |
| `--accent-strong` | Hover/pressed accent, 3D button edge |
| `--accent-soft` | Selected backgrounds |
| `--accent-text` | Accent-coloured text on light surfaces (≥ 4.5:1) |
| `--second` `--second-soft` | Secondary hue (teal, clay, orange, lavender, mint) |
| `--good-soft` `--warn-soft` `--bad-soft` `--info-soft` | Tinted backgrounds; the matching state colour stays ≥ 4.5:1 on them |
| `--on-bad` | Text on a solid `--bad` (error toast) |
| `--star` | Rating stars |
| `--focus` | Focus ring colour (`:focus-visible`, 3px) |
| `--inverse` `--on-inverse` | Toasts |
| `--overlay` | Dialog backdrop |
| `--shadow-sm` `--shadow-lg` | Small / dialog elevation |
| `--scene-filter` | CSS filter for canvas and illustrated panels; dims them in the dark theme |
| `--radius-lg` `--radius-pill` | 22px panels / pills |
| `--career` `--career-strong` `--career-soft` `--career-ink` `--career-text` | The current career's accent family. See section 2b. |
| `--font` | Font stack |
| `--safe-t` `--safe-r` `--safe-b` `--safe-l` | `env(safe-area-inset-*)` |

## 2. Themes

Themes are set as `html[data-theme]` by `public/js/v4/shell.js` from `settings.uiTheme`. The last theme used is cached in `localStorage` (`mnl.theme`), so a reload does not flash the light theme first.

| id | Name | Feel | bg / accent / second |
|---|---|---|---|
| `kem` | Kem sữa (default) | Warm cream, terracotta, teal | `#faf3e8` / `#c44b30` / `#3f8f7a` |
| `tra_xanh` | Trà xanh | Fresh matcha green, clay | `#eef5e9` / `#40772f` / `#c9793a` |
| `bien` | Biển chiều | Sea blue, sunset orange | `#ecf3f9` / `#226ca0` / `#e8913a` |
| `keo` | Kẹo ngọt | Pastel candy pink, lavender | `#fff1f6` / `#bf3f6d` / `#7a6ad8` |
| `dem` | Phố đêm | Dark night street, coral lantern, mint | `#15141b` / `#ff8a6b` / `#7fd1b9` |

Every pair listed in section 1 is checked for contrast (WCAG AA). If you add a theme, copy a whole block in section 2 of `app.css` and re-check the pairs.

### 2b. Career accent

Each career tints a few pieces of chrome with its own colour, so the 20 workplaces don't look alike. The theme still owns surfaces, text, lines and the rail.

`public/js/v4/shell.js` (`applyCareer`, called by `renderMain` through `shell.career(meta)` and again when the theme changes) sets `html[data-career="<id>"]` and five inline tokens on `<html>`. It starts from `meta.color` in the catalogue, the same colour source the scenes paint with, and fits it to the theme (`careerPalette`):

| Token | Light themes | Dark theme (`dem`) |
|---|---|---|
| `--career` | `meta.color` darkened in HSL lightness (same hue) until white reads ≥ 4.6:1 on it | Lifted (saturation capped at 78%) to a relative luminance ≥ 0.32 |
| `--career-ink` | `#ffffff` | A deep shade of the same hue, ≥ 4.6:1 on `--career` |
| `--career-strong` | `--career` 8 points darker (3D edge, pressed) | `--career` 10 points darker |
| `--career-soft` | 13% `--career` over `--surface` (selected fills, the step chip) | 20% `--career` over `--surface` |
| `--career-text` | `--career`, darkened further until ≥ 4.6:1 on `--bg`, `--surface`, `--surface-2` and `--career-soft` | Lightened until the same holds |

Before a career is known, the tokens fall back to the theme's `--accent` family.

**Where it shows:** the task card's primary button (`.task-hud`), the phone dock's "Thêm" dot, the `.scene-mark` emoji badge (from `emojiOf` in `v4/journey.js`), `.sheet-head .eyebrow` and everything inside `.career-job`. Since the calm screen (3b) the dock and title card no longer carry accent fills or rings: the accent is kept for the primary action. These containers re-point `--accent`, `--accent-strong`, `--accent-soft`, `--accent-text` and `--accent-ink` at the `--career-*` tokens. Components inside them stay on the plain accent tokens and pick up the career colour.

Rules:

- Put text only in `--career-text`. Text on a `--career` fill uses `--career-ink`.
- To tint a new piece of chrome, add its container to the re-pointing rule in `app.css` rather than using `--career` directly.
- Places that show another workplace (journey cards, stories) set their own `style="--career:…"` inline, for decoration only.

The pairs above are checked for all 20 careers × 5 themes (`careerPalette` is pure; lift it from `shell.js` to re-check after a colour change).

`shell.js` also toggles two classes on `<html>`:

- `.reduce-motion` stops all animations and transitions. `prefers-reduced-motion` does the same.
- `.large-text` raises the root size from 15px to 17px. Everything is sized in `rem`, so it scales.

## 3. Layout modes

`html[data-layout]` is set by `shell.js`:

- **phone:** width < 700, or a coarse pointer with a short side < 500.
- **tablet:** width < 1100.
- **desktop:** anything wider.

The player can force a mode in Settings → Giao diện. A forced desktop falls back to tablet below 760px, and a forced tablet falls back to phone below 560px. `html[data-orientation]` is `portrait` or `landscape`. When the mode changes, the window receives `layoutchange`, and `app.js` then resizes the canvas and re-renders.

| | Desktop ≥ 1100 | Tablet 700–1099 | Phone < 700 |
|---|---|---|---|
| Grid | `brand top top / rail stage side / foot foot foot` | `brand top / rail stage / rail dock / foot foot` | `top / stage / dock` |
| Navigation | 88px rail with icons and labels | 76px rail with icons and short labels | The rail becomes the **Thêm** bottom menu (`html.menu-open`, opened from the dock) |
| Task HUD | Right side panel (`.side`), scrolls | Floats over the stage: top-right (landscape) or a swipe row above the dock (portrait) | Swipe cards above the tab dock. Compact: title, next step and main button |
| Scene actions (`#dock`) | 2-column tiles under the HUD | Scrollable bottom bar | Scrollable tab bar with icon pill and 11px label, safe-area aware |
| Sheets | Centred modal; the settings sheet is a right **drawer** | Near full-width modal; drawer for settings | Full-height **bottom sheet** with grabber |
| Footer | Save state and links | Save state and links | Hidden; only the offline pill shows |

Rules for all modes:

- The page never scrolls; the only scrollers are `#sheet`, `.side`, the rail and the dock. At 360px there is no horizontal page scroll.
- A sheet's `.sheet-head` and `.sheet-foot` (and `.preparation-topline` / `.life-sticky`) are sticky inside the dialog. The dialog itself is the scroll container: `renderSheet` keeps its `scrollTop`.
- **Container queries:** `.sheet-body` and `.life-content` are `container: sheet / inline-size`. Two-column layouts (`.workbench`, `.fb-layout`, `.work-layout`, `.doc-board`, `.tea-working`, etc.) are single-column first and add columns with `@container sheet (min-width: …)`. So they respond to the **sheet** width (drawer, modal, phone), not the window width. Use the same pattern in career CSS.
- **Phone targets:**
  - touch targets are ≥ 44px;
  - inputs use 16px text (no iOS zoom);
  - `env(safe-area-inset-*)` pads the top bar, the dock, the sheet foot and the menu.
- **Toasts:** they are `position: fixed`. `toast()` moves them into the open dialog so they stay above the backdrop. Dialogs therefore must not have a `transform` at rest; animate with keyframes only.
- **Dark theme:** the canvas draws fixed light colours, so it is dimmed with `filter: var(--scene-filter)`. Overlays on the stage (`.scene-heading`, badges, hint) are small surface plates, so they stay readable on any scene.

### 3b. The calm main screen (v0.8.1)

Players said the main screen was "rối mắt". The rule is **one primary thing at a time, few words**: show what to do next, not what things are.

- **Top bar:** only the day and the money. Tapping the day opens the **status sheet** (`ui.view='status'`, `statusView` in `app.js`): pause, clock and tasks left, rating, weather/mode, wallet, spirit, Nhóm phố, Phố nghề, settings, plus the "Cần để ý" list. A small dot on the day means something new is inside. A rating change shows as a brief pop, not a permanent chip.
- **Title card:** the emoji mark and the shop name on a faint pill. No eyebrow, tagline, status/weather badges or ambient quote. The walking hint shows on day 1 only (desktop/tablet) and fades.
- **Task card:** the next step on one line (two on phone) with the customer's portrait, and one verb button. Closed: one "Chuẩn bị ngày mới" button. Other notes collapse to a bell with a count (phone/tablet); desktop lists them quietly in the side column.
- **Canvas:** name tags only for the customer in hand (and events/officer); others on hover. A single "+" marker on the station while a task is in hand, none elsewhere. Speech bubbles are one at a time, at most two lines, a few seconds long. No welcome-back bubble.
- **Dock:** phone keeps 3 scene actions (the workbench always) + "Thêm"; only the ones the dock has no room for appear in the Thêm menu's "Trong tiệm". No sub-lines.
- **Menu (phone "Thêm" sheet, desktop/tablet rail), 01/10:** the work pages in sight (Hành trình, Chuẩn bị, Sổ tiệm or the career's log, Đánh giá, Việc làm), then five hubs one tap away: **Khu phố** (Nhóm phố, Chuyện phố, Phố nghề, Bản đồ phố, Xếp hạng), **Quan hệ** (Người quen, Bạn bè, Hôn nhân), **Tiền & nhà** (Tiền của bạn, Ngân hàng, Nhà của bạn), **Chuyện của bạn** (Tình huống, Chuyện đời), **Của mình** (Tủ đồ, Kỷ niệm, Hộ chiếu, Trò nhỏ, Sổ tay); a footer row: Góp ý, Cài đặt. A hub carries its entries' badges (numbers add up, a dot stays a dot). Phone: a hub fills the sheet with a back button; desktop/tablet: it opens in place under its button. Every entry stays in the markup (hidden when folded), so `data-action` deep links still find it. `app.js` `RAIL_MAIN` / `RAIL_GROUPS`; an id in no group joins the work pages. The guides are not in the menu: the "?" of each work screen, Cài đặt, and one "Xem hướng dẫn / Bỏ qua" card the first time at a workplace (`tutorial/announce.js`).
- **Toasts:** one at a time, newest wins (a hint never replaces an error), 2.4–4.5 s.

## 4. Components

Use the shared classes. A career module should not need new chrome.

| Pattern | Classes |
|---|---|
| Buttons | `.btn` with `.primary` / `.ghost` / `.cream` / `.danger` / `.danger-soft`. Sizes: `.small`, `.big`, `.jumbo`, `.full`. Also `.left` and `.icon-btn`. Disabled uses the `disabled` attribute (never only a class). |
| Tags and chips | `.tag` with `.green` / `.amber` / `.blue` / `.danger`. `.chip`, where `.selected` / `.active` is the selected state. `.chip-row` |
| Notices | `.notice` with `.amber` / `.blue` / `.danger` / `.success` (icon + `<div>`). `.empty` for empty states |
| Tabs | `.pill-tabs` (sheet sub-tabs), `.segmented` (small either/or), `.settings-tabs`, `.soc-tabs` |
| Forms | `label.field` (label above control), `.input`, `select`, `textarea`, `.switch-row` (label > text + `input[role=switch]` + `<i>`), `.check-label`, `.small-input` |
| Cards | `.card`, `.note-card` (HUD), `.kv` / `.kv-row` (key–value list), `.bar` (`.low`, `.big`) / `.progress` meters |
| Workbench | `.career-job.<prefix>` > `.card.ticket` + `.workbench` > `.wb-main` / `.wb-side`, `.section-title` step headings |
| Tiles | `.tile-grid` > `button.tile` (`.selected`, `.wanted`, `.empty`, `.locked`, `.wide`) with `.tile-emoji`, `<b>`, `<small>`, `.tile-count`, `.tile-flag` |
| Choices | `.choice-grid` / `.choice-list` > `.choice` (button with `.selected`, or `label.choice` with a radio/checkbox) |
| Checklists | `ul.checklist > li.ok / li.bad` (span mark + label + small note) |
| Steps | `.proc-steps` (shared procedure engine) |

### States

- **Hover:** a stronger border or `--surface-2`.
- **Active:** press by 1px.
- **Focus:** a 3px `--focus` ring on `:focus-visible` (never removed).
- **Selected:** `--accent-soft` fill + `--accent` border.
- **Disabled:** 55% opacity and a `not-allowed` cursor.
- **Loading:** `body.busy` shows the progress cursor.
- **Danger:** `--bad` / `--bad-soft`.

## 5. Rules for career modules

1. Scope everything under `.career-job.<prefix>` and use a short prefix (`rs`, `cb`, `fa`, …). Never style `#app`, `.sheet`, `.btn` or `.tile` globally from career CSS.
2. **Tokens only:**
   - Use `var(--surface)`, `var(--accent)` and the other tokens for chrome.
   - Illustration colours are fine inside an art element. Wrap it with `filter: var(--scene-filter)` when it is a big light area.
   - Set per-element colours with inline custom properties, such as `style="--broth:#c8743a"`. The CSP allows inline style attributes.
3. Use container queries on `sheet`, not `@media`, for columns. Mobile first: one column must work at 330px of sheet width.
4. Keep text in markup, not in CSS `content`, so the English i18n layer can translate it. English can be about 30% longer, so do not use fixed widths on text.
5. Emoji carry flavour; always pair them with a text label.
6. Respect `.reduce-motion`: wrap looping animations in `@media (prefers-reduced-motion: no-preference)` and `html:not(.reduce-motion)`.
