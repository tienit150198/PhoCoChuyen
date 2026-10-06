# UI kit: the shared pieces for a clean work screen

Owner, 06/10: "gọn hơn, clean hơn, ít chữ hơn, dễ chơi hơn". This page lists the shared parts every new or
reworked screen uses. The code is in `public/js/ui-kit.js` and `public/js/v4/guide.js`. The styles are in
`public/css/app.css`, section 27e.

## Rules for a screen

| | Cap |
|---|---|
| Visible words, career work screen | **25** |
| Visible words, career intro | **30** |
| Visible words, life sheet | 30 |
| Words in a toast | **8** (`toast-lines.js` shows the first 8; ▾ opens the rest) |
| Main buttons (`.btn.primary`) | exactly **one**, and it sits in the bottom bar |
| Pinned things in a sheet | the header and the bar only; order cards scroll, and their digest is a header chip |
| Tap targets | at least 44 × 44 px |
| Rules, formulas, long intros | 0 words on screen: put them behind "?" (`helpBtn`) |

How to check:
- **Dev builds** (localhost, or `localStorage['mnl.wordcap']='1'`) log `text budget: N words…` in the console when a
  work screen goes over its cap.
- **Sweep:** `python scripts/check_word_caps.py --careers a,b` (needs `TEST_DATABASE_URL` and playwright).
  - It fails when a toast goes over 8 words, a street-kit intro over 30, or a screen listed in `WORK_DONE` over 25.
  - When your screen passes, add the career to `WORK_DONE` so it stays under the cap.

## Tokens (`app.css :root`)

- **Spacing:** `--sp-1` 4px, `--sp-2` 8px, `--sp-3` 12px, `--sp-4` 16px, `--sp-5` 24px.
  - `--gap-1..4` are aliases of these. Phone cards: padding `--sp-3`, gap `--sp-2`.
- **Type:**
  - `--fs-1` .75rem: meta and chips.
  - `--fs-2` .875rem: body on a phone.
  - `--fs-3` 1rem: buttons and card titles.
  - `--fs-4` 1.25rem: one hero number or the title.
  - Line height: `--lh` 1.3, and `--lh-btn` 1.2 for buttons.
- **Colour:**
  - Theme tokens only (`--surface`, `--surface-2`, `--line`, `--ink-2`, `--warn`…).
  - The career accent is `--career`, `--career-soft` and `--career-text`.
  - Do not add new hex literals.

New CSS uses these instead of literal px or rem values.

## Bottom bar: `actBar({next, main, top, cls})` (ui-kit.js)

```js
import {actBar} from '../ui-kit.js';
actBar({next:'<span class="ui-note">3/6 ✓</span>', main:x.cmd('💐 Trao hoa','fl_deliver',{task},'primary big'), cls:'fl-bar'});
```

- It renders one row: the next step on the left (it ellipsises) and the main button on the right (40–62% wide).
- With no `next`, the main button takes the whole row.
- `top` adds a full-width row above, for route totals or the last reading.
- `cls` keeps your old class as a hook. Do not give that class layout styles: `.ui-bar` already lays out the bar.

With guide steps, use **`stepBar(x, steps, final, {cls, top, note})`** (guide.js). It picks the slots for you:
- The next step is a command: it becomes the main button. Finishing early, when allowed, shows as a quiet
  "hoặc …" link on the left.
- The next step only points (`go.sel`): "👆 Chạm: …" goes on the left and the finishing button on the right.
- Nothing is left: the finishing button stands alone.
- `note` fills the left slot when the guide leaves it empty, for example a count.

`barParts(x, steps, final)` returns just `{next, main}` if you build the bar yourself.

Migrated so far:
- the street kit (`street_kit.js bottom`: 21 careers plus pho's pour gauge)
- `food_kit.actionBar`
- the florist (`fl-bar`), restaurant (`rs-bar`), repair (`rp-bar`) and clothing (`ao-bar`) bars
- teacher and tour guide (`teach-tour.js bar`)

Not yet migrated (they keep their own bar with the phone rules in compact.css): `dw-bar`, `ok-bar`, `dl-bar`,
`tv-bar`, `fa-bar`, `mb-ctabar`, `pl-bar`, `td-bar`, `hs-bar`, `ps-bar`, `gr-billbar`, `sl-bar`, `pc-bar`,
milk tea's `fk-bar` and cafe's `cb-dock`.

## Disabled with a reason

A button that cannot go yet is **dimmed but tappable**. A tap shows one line, `⚠ <why>`, plus a fix button in the
bar's left slot for 5 s. It never shows a toast, and it never sends the command.

- **Client:** add `whyAttrs(can)` to the button, or call `withWhy(html, can)`.
  - `can` is `true`, or `{why, fix}`.
  - `fix` is a guide `go` plus a label: `{cmd, payload, label}`, `{act, data, label}` or `{sel, label}`.
  - Street-kit tiles take it as their last argument: `tile(x, cmd, payload, inner, cls, disabled, can)`.
- **Guide final button:** set `final.can` (from the server). It wins over the page's own `ready`/`why`.
  - A final with `ready:false` and no `can` is also dimmed but tappable now, never `disabled`.
- **Server:** write the guard once and run it in two modes:

```python
def _deliver_rules(t, need=kit.need):
    need(done(t), 'Hoa chưa cắm/bó xong…', fix=dict(act='car:tab', data=dict(tab='design'), label='💐 Cắm & gói'))

def _deliver(s, c, d, pl, t, p):
    _deliver_rules(t)                      # refuses, as before
    ...

def public_task(t):
    v['can'] = dict(fl_deliver=kit.check(_deliver_rules, v))   # True | {'why', 'fix'}
```

Rules for the server side:
- `kit.check` reads only. It stops at the first failing rule, and it returns `True` if the rules crash.
- Keep the same messages and the same order as the refusal.
- Never use it to change task generation (`check_task_compat.py` must stay OK).
- `can` is a view field. It is never saved.

Done so far: giúp việc `can.gv_wipe` (tool, product, empty bottle) and the florist's `can.fl_deliver`.

## Header chip for a pinned card: `headChip(icon, text, selector)`

```js
`${headChip('🧾', '3/6', '.asm-pin', {label:'Khách cần: 3/6 xong', tone:'bad'|'ok'|''})}<section class="asm-pin">…</section>`
```

With the clean layout on, `guide.js applyGuide` moves the chip into the sheet header. The card itself stops pinning
and scrolls with the work. A tap on the chip opens the card as a popover under the header. A second tap, or a tap
outside, closes it. With the clean layout off, the chip is hidden and the card behaves as before.
`asm_kit.reqPin` does this already (florist, repair, restaurant, clothing).

## "?" sheet: `helpBtn(key, title, sections)`

```js
helpBtn('intro-drain', '🧰 Thợ thông cống', [{title:'Giới thiệu', body:'<p>…</p>', open:true}, {title:'Công việc gồm…', body:'<ul class="ui-rows">…</ul>'}])
```

- It returns a 44 px "?" button. The tap opens a small sheet: a bottom sheet on a phone, a centred dialog elsewhere.
- Each section folds. Put rules, formulas, the long intro and the hint flow here.
- `helpBody(sections)` renders the same list inline.

The street-kit intro uses it:
- The card shows the job's name and three icon rows of 5 words or fewer. The rows come from `intro.short`, or else
  from the first three `work` lines cut to their first clause.
- The lead and the three lists live behind "?".
- The start button is the bar's main button.

## Cutting a screen to 25 words (wave 1 recipe)

The ten worst street screens went from 50–120 words to 17–24 this way. Every helper is a no-op on the classic layout, so
desktop keeps its text.

- **Explanations go behind "?":** wrap a rule, a tile's description, a lead paragraph or a story in
  `tip(htmlSafeText, 'what it explains', tag)` (ui-kit; the street kit re-exports it).
  - On the clean layout it is hidden.
  - The day line's "?" lists it under "Trên màn này" (`helpBtn(..., {tips:true})`), followed by the day's hint and
    the intro.
- **Labels in a word or two:** `few(label, max)` cuts at the first clause, then at `max` words, and never ends on
  "lúc", "cùng" and similar little words. Numbers are free.
  - Where a cut reads badly, use a small curated map instead (drain's `SHORT`, the railway and lighthouse `EQ_WORD`,
    rescue's `UNIT_WORD`, giúp việc's `BOTTLE_WORD`).
  - Always keep the full name as the control's `aria-label`.
  - Keep what the player decides with: customer demands, a spot's danger mark, a child's temper. Shorten how it is
    said, not what is asked.
- **Icons and numbers, not words**, for state such as `🍵 0/12 · 🧊 0/24`, gear and fill buttons, and the knuckle
  buttons `½ · 1 · 1½`. Put the words in `aria-label`.
- **Reference cards become chips:** a card the player only checks now and then (an appointment book, the step
  checklist) gets `headChip(icon, '3 hẹn', '.card-sel', {flow:true})`, and the card gets the class `ui-chipped`.
  - On the clean layout the card is hidden and the chip opens it as a popover.
  - `flow:true` puts the chip in the screen's in-flow chip row (the street kit's day line), so the pinned header stays
    one row.
  - `stepRows(x, steps, label, {chip:true})` does this for the checklist.
- **Choices that wait:** a set of choices only needed after other steps can sit behind one `pane()` line that opens
  by itself when its turn comes (babysitter greetings, rescue's units on pause).
- **The header** shows the task title in at most 4 words on the clean layout (`app.js header`). The full title stays
  in `title=` and `aria-label`.
- **Notes (toasts)** go into the bar's left slot for a few seconds (guide.js `barNote`). They never cover the work and
  never count toward the screen's 25. Their own cap is 8 (toast-lines.js `toastHead`).

Measure with the audit harness or `scripts/check_word_caps.py --careers <id>`. When a screen passes, add it to
`WORK_DONE`.

## The switch: `html[data-clean]`

`v4/shell.js applyClean` sets it.
- **Player:** Cài đặt → Giao diện → "Giao diện gọn": Tự động (phones only, the default), Bật (every size) or Tắt.
  It is stored in `localStorage['mnl.clean']`.
- **Server kill switch:** `MNL_CLEAN_UI=off` in the server environment, then restart. Bootstrap sends
  `ui.clean=false` and every page turns the layout off at its next load.
- **What the switch gates:**
  - header chips and cards that no longer stick
  - toasts placed under the header instead of in its title row
  - one filled main button (other primaries on the screen look secondary)
- **What does not change with the switch** (no layout risk): the bar component, the dimmed-with-reason buttons, the
  short intro and the 44 px tap targets.
