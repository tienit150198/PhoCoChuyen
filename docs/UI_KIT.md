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
- the pilot (`pl-cta`) and the flight attendant (`tv-cta`), wave 2. Their hook is not `pl-bar`: palette.css owns a
  `.pl-bar` (the colour count's progress bar) once the palette has been opened.
- the office desks (`office_kit.js bar`, hook `ok-bar`: the six Cánh Diều / Mây Tre Xanh / Sông Hồng / Minh Bạch desks),
  the pet shop (`ps-bar`, via `stepBar`) and the support desk (`cs-bar`, customer_care) — wave 3
- wave 5: the classic desks (`dw-bar`: pharmacy, accounting; `dk-bar`), mother & baby (`mb-ctabar`), delivery (`dl-bar`),
  farm (`fa-bar`), homestay (`hs-bar`), grocery (`gr-billbar`), salon (`sl-bar`), pet care (`pc-bar`), clothing (`ao-bar`)

- milk tea (`fk-bar mt-bar`: the mini cup and "Còn n bước" in the left slot) and cafe (`fk-bar cb-dock`: what is in hand in
  the left slot; the wide side column no longer repeats the button) — wave 4, via `barParts` + `actBar`.

Not yet migrated (they keep their own bar with the phone rules in compact.css): `td-bar`.

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
Wave 2: police `can.cap_topic` (a fourth topic), nurse `can.dd_send` (the patient said no to the operation),
lifeguard `can.hb_reopen` (the storm has not come), oil `can.dk_bleed` / `can.dk_verify` (a point not locked, not bled
yet), pilot `can.pl_takeoff` (checklist, the delay announcement) and `can.pl_around` (fuel for this approach only), and
the flight attendant's `can.fa_give`: one map for the row being served, `{seat: {item: {why, fix}}}`, with only the
refusals in it (a seat left to sleep, a dish it already has). A sleeper woken, peanuts in the allergy row and a hot drink
for a child stay scored mistakes, never refusals.
Wave 3: every office desk's `room.data.office.can.work` (game/careers/office.py `need_open`: after 17:30 the work is
dimmed with the refusal's own words and a fix that points at the overtime button; `office_kit.shutWork` draws it), and
the payroll row's `can.tp_flag` (tax_payroll: a full row's other cells say "tối đa 3 ô").
Wave 4 (from the 04–06/10 refusal counts): milk tea `can.tea_swap[item]` (only a bought syrup/topping of the order: the
counter offered to swap pearls it could not cook, 80 refusals), restaurant `can.rs_sub[item]` (a substitute that ran out
too is not offered again, 148) and `can.rs_touch[touch]` (the extra soup only once the bowl has broth, 82), homemaker
`can.nt_close` (every chore that belongs in the day, 110), garbage `can.rac_load` (sweep a late lane first; the fix is
the sweep, 96), fruit `can.tc_weigh` (anh Lâm's min–max, 138), and `can.open` in nail / photobooth / ice cream
`public_data` (a customer picked before "Mở tiệm"; the fix is `task_select` on the morning set-up, 90 + 119).
Wave 5: the classic desks' guards live once in `game/desk_can.py` (engine runs them to refuse, the view runs them through
`kit.check`): pharmacy `can.ph_check` (the tray against the slip), accounting `can.ac_match` / `can.ac_complete`;
delivery `can.dl_signal` (a crossing off the leg, no destination yet) and `can.dl_ride`; homestay `can.hs_assign` (a room
whose app booking still waits to sync, fix "📥 Đơn chờ") and `can.hs_pick` (the most places to suggest); clothing
`can.ao_pick` (a size the rack is out of), salon `can.sl_mix`, repair `can.rp_show` / `can.rp_fix`, pet care `can.pc_*`.

## Typed quantity: `qtyBox({...})` (qty-input.js)

Owner, 07/10: "mấy cái con số nhập hàng, mua vàng,.. đang phải bấm cộng mệt quá, cho nhập số nhé". Every "− N +" stepper
draws its number with `qtyBox`, never as `<b>`/`<output>` text. The − / + buttons and the quick chips stay.

```js
import {qtyBox,QTY} from '../qty-input.js';
// a field the screen reads (as it read its old <input>):
qtyBox({value:qty,min:1,max:Math.max(1,max),label:'Số lượng',cls:'input',attrs:'id="order-qty" data-v4-qty'})
// the number was text: the box does what a tap does, with the typed number where QTY sits
qtyBox({value:n,min:0,max:KEEP_MAX,label:'Số giữ lại',go:attrs(QTY)})                       // a command
qtyBox({value:Math.floor(n/10),min:0,max:MAX_PHAN/10,label:'Số chỉ vàng',live:true,go:`data-action="ivGoldQty" data-chi="${QTY}"`})
```

- **The box:** `type="text" inputmode="numeric" pattern="[0-9]*" autocomplete="off"`, min/max from the same limits the
  stepper (and the server) use. Font ≥ 16px so iOS does not zoom; it is as wide as the largest number allowed.
- **Typing:** digits only (a paste of "1.000" is 1000). Focus selects the whole number, so typing replaces it.
- **Enter or leaving the box:** clamps to [min, max]; empty or 0 is the minimum; `step` (lux guests by 5) rounds to it.
  Never NaN. A field box then fires an `input` event, so the screen's live totals update as after a tap; Enter inside a
  `<form>` still submits it, with the clamped number.
- **`go`:** an attribute string or a whole button's HTML, made by the stepper's own `attrs(q)` / `x.cmd(…)` with `QTY`.
  On commit a hidden button with those attributes is clicked where the box sits, so the page's usual click routing does
  the work (app commands, `car:` actions, a dialog's own `data-qy` / `data-rui` / `data-lx` / `data-au` handler). A
  delta-only handler needs a `set` variant (quay `step`/`tables`, pet care `step`, air kit `oddNSet`, lux `guestsSet`).
- **`live`:** also on every keystroke, for a page-only number whose price should follow the typing (gold, wages, milk tea
  order, grocery order size). Only on screens that redraw by morph (the app sheet, quay); an innerHTML dialog uses the
  commit only, and redraws with `afterTap(render)` so the button being tapped is not replaced under the finger (lux,
  auction), or patches its labels instead of redrawing (rui).
- **`money`:** 1.000 separators while not typing. Read such a box with `qtyVal(el)`, never `Number(el.value)`; use it only
  where the screen reads its own state, not the field.
- A − / + tapped right after a typed number went out (before the redraw) steps from the typed number.
- The server stays the authority: every command a box sends refuses out-of-range, fractional, string and bool numbers
  (`tests/test_typed_qty.py`).

Players 07–08/10 (fb08): gold is typed as chỉ + odd phân (two boxes, "Mua tối đa" and "Cả … đang giữ" chips); the
mother & baby shelf order is typed up to what the shelf still takes (server 1..12, saved as parcels of ≤ 4 so older
servers still validate the save); trà đá ice 0–6, the farm's wholesale "Số khác" and the library donation are typed too.
In Kho a bin already in a draft order turns calm green with "✓ Đã thêm · N", one on its way calm blue: the red ones left
are the ones still to order.

Left as buttons on purpose: ranges of ten taps or fewer where the step is the game (salon parts and cm, clothing cm, cafe
grams 12–24, pet care meals 1–4) and counts the server takes one at a time (homestay bill lines `hs_line ±1`, florist
stems, zpop, basket picks, ice cream `kem_adjust`, cash-note keypads). Chip-only choices (fair stakes, lì xì, the
fireworks sizes, the scam offer) stay chips; fields that were already typed (bank, house, rentals, journey, social
market, marriage money) are unchanged.

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

## Never fold a deciding cue (non-negotiable)

Fold away only explanations, descriptions and flavour. A clue that decides right from wrong stays visible on the
work screen, without opening "?". Before cutting a screen:

1. For each step, list the facts the server scores or checks the answer against: the customer's words, the
   job's place, a time, a direction, a trap's tell.
2. Keep each one on screen, in a short form if needed.
3. If that needs the room, the screen may take up to 30 words (`WORK_CAP` in `check_word_caps.py`).

Rules of thumb:
- **Curated short labels** keep the deciding part ("Mở loa ra đường 4h", "Sát mép đường", "Dây 5m"). A label not in
  the map shows in full, never cut by a guess.
- **A customer's opening** stays: it is their ask ("Tượng gỗ sơn son, lau nhẹ tay"). Only a morning set-up scene
  folds.
- **Logbook notes** that tell what to refuse or watch stay, in a few words ("Cô Mận xin ghế sát ray: đừng cho").
- **A timetable keeps direction and time.** A rule's numbers stay next to what they apply to ("🌅 05:32 · +15′").
  Wave 2 did this for a rule card the player had to open before: the nurse's alarm limits sit on each sign's tile
  (`🚨 ≥38,0 · ≤35,5`), the pool's Clo and pH ranges beside the strip's reading (`Clo 2 (1–3)`), the storm's wait beside the
  last thunder (`⚡ 14:05 +30′`), and the pilot's fuel list has the storm hold as its own row.
- **Who says it, then what they ask.** An opening "Chị Thu mở cửa tàu: “…”" shows "Chị Thu" and the quote; the scene
  before the colon folds (air_kit `splitSay`). A scene with a number or a sentence of its own is never split ("Xả áp
  xong, đồng hồ vẫn 4 bar. Thợ bảo: …" keeps its reading).

## Cutting a screen to 25 words (wave 1 recipe)

The ten worst street screens went from 47–131 words to 17–30 this way. Every helper is a no-op on the classic layout, so
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

## Office desks (wave 3)

The six office careers (`office_kit.js`) and the three hands-on desks (`office_work.js`) share these:

- `bar(x, t, next, g, always, {top})`: the shared bar. Pass the `guideOf` result `g` (not `g.cta`): its pointer or
  its reason fills the left slot. Choices that belong to the bar (the stamps, the reasons for a gap) go in `top`, a
  full-width row above; it hides on the other tabs of a phone, like the main button.
- `envelope(x, t, {empty, extra})`: the 📂 tab before the dossier is received. Clean layout: who asks and their words
  (a long ask shows its first sentence; the rest and the brief go to "?"), so the first screen is the job, not the inbox.
- `note(text, title)`: an explanation line (a formula 📐, a rule of thumb, a cost): as before on the classic layout,
  listed in "?" on the clean one. `deskHelp(x, …)`: that "?", at the end of the status row.
- The status row is icons and numbers (🕗 08:00 · trust bar · 🔋 · ⏰ 10:30 · 📅 5); tabs keep only the open tab's word.

What stays on the desks' screens, whatever the count: the ask, every paper's data, the ledger lines' cues (the
buyer's own number "Nhập theo HĐ-45", "xuất kho 29/03", "lập 16:00", "Bán cho <outsider>", NM × rate), the tray rules
("Sếp dặn"), the timesheet's work-hour rule, the step's prompt, the support options' "Khi …" lines and the 📌 basis.

## Shops and street kit B (wave 4)

The food counters (milk tea, cafe, restaurant, florist) and the eight street-kit careers wave 1/2 left (ice cream,
homemaker, garbage, fruit, nail, nấu cơm, photobooth, library). What the wave added, for the next screens:

- **The one pinned box is the bar.** Milk tea's order ticket no longer sticks (`--mt-stick`); its digest is a header chip
  (`🧾 k/n`) that opens it over the counter. Restaurant: the order card already lists every part as steps, so the
  compact copy (asm_kit `reqPin`) waits behind its chip instead of repeating the order in the flow (restaurant.css).
- **`dayStrip(…, {tight})` / `queue(…, {tight})`** (food_kit, opt-in): the day as its emoji, only the served guest's name
  under the faces. Other callers (clothing, grocery) are unchanged.
- **`dayNote(x, note, title)`** (in each street career): the morning note folds to "?" only on a plain day (`mod.id ===
  'normal'`); on a rain / outage / hot day it is the day's cue ("mang ủng", "căng bạt", "sạc sẵn đèn pin") and stays.
- **`say2(full, short)`**: a panel button that repeats the bar's step reads two words on the clean layout ("🌡️ Ẩm kế");
  the full label is in an `sr-only` span.
- **Curated short forms, keyed by step / option id** (homemaker `SHORT_TEXT`, `SHORT_OPT`): the morning money keeps
  its amount and its bills (`💵 “80 xu” · 4 tờ gấp đôi`), each answer keeps what it does ("Cất ví riêng, nhắn “nhận 80
  xu”"). Unknown ids show in full; the full text is the control's label and is listed under "?".
- **Choices that wait** (nấu cơm's menu): only the dish group whose turn it is is open (the first without a dish, or
  one whose dish clashes with the family's rule); the others are one line with the chosen dish.
- **Nail's disabled buttons** (`btn`, `pick`): on the clean layout dimmed but tappable (ui-kit `withWhy`) instead of a
  reason printed under each; the bench is no longer lined with "Không có sơn cũ".
- **Header title ≤ 4 words** now also for the four counters (app.js `header`); every cue it cut is on the order card
  once the order is heard (the allergy row, "mang về", the occasion tag).
- ui-kit `placeChips` keeps header chips whose card is still on the page when a pass finds no chip left in the body (a
  re-render with unchanged markup skips the DOM): the milk tea chip vanished on the counter's repeated passes.

Kept on screen, whatever the count: the ice-cream weight band beside the scale (`chuẩn 60–70 g`), the knob's target
tile and the thermometer's `🎛️ 4 → −18°`; the bag's look ("⚠️ trông lạ") and the clue; which cover each tile is for
("Che nắng / Che mưa"), the empty scale's reading, the bruised fruit; the client's service, shape, length, photo and
the nail facts; the family's chips and rule ("Bé không ăn cay, sợ xương cá…"), dish tags and costs, "1 phần = 2 người";
the photobooth order chips and the customer's words; the humidity range beside the reading; every row of the drink /
bowl / bouquet order, "Không sữa bò", the guest's quote and temper, the occasion and "Nhận tại tiệm".

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

## Waves

Each wave owns its screens and their files; no other wave edits them.

| Wave | Branch | Screens | Files owned |
|---|---|---|---|
| Foundation + 1 (shipped 1.9.7) | `rel-1.9.7` | drain, com, lighthouse, railway, tra_da, babysitter, pho, pagoda, rescue, giupviec | shared kit files; those 10 careers |
| **2: uniformed** (audit plan W2, `air_kit`; lighthouse, railway and rescue went out in wave 1) | `ui-wave2` | **police, nurse, lifeguard, oil, pilot, flight_attendant** | `careers/air_kit.js` + `.css`, `pilot_tutor.js`, `pilot_fly.js`; `public/js/careers/<id>.js` + `public/css/careers/<id>.css` and `game/careers/<id>.py` of those 6 |
| 3 (shipped 1.9.8) | `ui-wave3` | the six office desks, customer_care, pet_shop | `office_kit`, `office_work`, `desks.css`; those 8 careers |
| **4: shops + street kit B** (from rel-1.9.8) | `ui-wave4` | **milk_tea, cafe_bakery, restaurant, florist** (the food-kit counters) and **ice_cream, homemaker, garbage, fruit, nail, naucom, photobooth, library** (the street-kit careers not done in wave 1/2) | `careers/food_kit.js` + `.css` (`actionBar`/bar CSS only: delivery, pet_care, grocery, salon, clothing, pet_shop import its other helpers, which stay as they are); `public/js/careers/<id>.js` + `public/css/careers/<id>.css` of those 12; their server files `game/boba.py` (milk tea), `game/careers/<id>.py` of the other 11, `homemaker_content.py`, `library_content.py` |
| 5 (in parallel) | `ui-wave5` | everything else (delivery, pet_care, grocery, salon, clothing, repair, homestay, mother_baby, farm, teacher, tour_guide, desks, life screens…): not any screen above | not any file above. Shared and not edited by wave 4: `street_kit.js`/`.css`, `asm_kit.js`, `stage_fold.js`, `till.js`, `tomorrow_kit.js`, `plan_kit.js`, `ui-kit.js`, `guide.js`, `app.css`, `compact.css`, i18n |
| 3 | `ui-wave3` | the rest: not any screen above | not any file above |
| **5: the last screens** (from rel-1.9.8, in parallel with wave 4; wave 4's list wins on a clash) | `ui-wave5` | work: **mother_baby, pharmacy, accounting, teacher, tour_guide, grocery, repair, farm, delivery, homestay, pet_care, salon, clothing**; life (cap 30): **town map, house, bank, fair, wardrobe, stall (quầy), HUD, karaoke, spending (Đi chơi)** | `public/js/careers/<id>.js` + `public/css/careers/<id>.css` and `game/careers/<id>.py` of those careers (`game/desk_content.py` and the desk section of `app.js` for pharmacy/accounting; `v4/teach-tour.js`, `teach.css` for teacher/tour guide; `delivery_*.js`, `farm_walk.js`, `salon_mix.js`, `asm_kit.js`, `stage_fold.js`, `till.js`); life: `v4/house.js`, `bank.js`, `fair*.js` + `fair.css`, `wardrobe.js`, `quay*.js`, `town-walk.js`, `journey.js`, `karaoke.js`, `spend.js`. Not `food_kit.js`/`.css` (wave 4) |

Wave 2, done (ui-wave2): police 84 → 23 visible words, nurse 78 → 19, lifeguard 67 → 25, oil 42 → 22, pilot 135 → 30
(cap 30: the opening at the cockpit door stays whole), flight attendant 172 → 25, on a 390 × 844 phone. The pilot and
the flight attendant now use the street kit's short intro (`introCard`, 24–29 words, was 135–172 inside the work
sheet) and the shared bar. Shared helpers added to `air_kit.js`: `crewDay` (the crew's day line with "?") and
`splitSay`.

Wave 2 does not edit `street_kit.js`/`.css`, `ui-kit.js`, `guide.js`, `app.css`, `compact.css` or the i18n catalogues.

Wave 4, done (ui-wave4), first work screen on a 390 × 844 phone (`check_word_caps.py`, clean layout): milk tea 22
(the last screen with 3 pinned boxes: now header + bar), cafe 19, restaurant 24, florist 22, ice cream 22, homemaker 30,
garbage 23, fruit 28, nail 25, nấu cơm 13, photobooth 24, library 21 (audit harness before: 35–109). Capped at 30:
homemaker (the morning money: amount, bills and three answers) and fruit (what each cover is for, the empty scale,
the bruised fruit). Outside its own files wave 4 changed one line of `app.js` (the four counters join the ≤ 4-word header)
and `ui-kit.js placeChips` (header chips survive a pass over unchanged markup); `food_kit` helpers changed only behind
the opt-in `{tight}`.
Wave 5, done (ui-wave5), first work screen on a 390 × 844 phone: delivery 128 → 30 (cap 30: the customer's ask stays
whole; the other open orders stay as one line each: from→to, ⏰ deadline, 💵 COD ⚠️ fragile ❄️ cold), pharmacy 90 → 24, teacher 87 → 24, accounting 83 → 22, tour guide 82 → 23, clothing 60 → 25, grocery 43 → 18,
homestay 41 → 18, repair 40 → 24, salon 37 → 26 (cap 30: the title is the customer's demand), pet care 34 → 18,
mother & baby 32 → 21, farm 26 → 16. `app.js header` shortens the title for clothing, grocery and pet care only (a repair
or salon title is the symptom or the demand: never cut); delivery and farm shorten their own (`shortHead`).
Cap 30 also for pharmacy (deeper steps show each lot's state) and mother & baby (an occasion order's ask, day 2+).
Accepted exceptions, not failures: the paperwork case screens of `desk.js` once the papers are taken (pharmacy ~70,
accounting ~75 words: every line is document data the answer is checked against), and the farm's "⏩ Bấm nhanh" board
(~97: six plot cards with their ripeness and keep-until day; the default "🚶 Tự đi" screen is 16), left for a redesign.

## Life sheets (wave 5)

Cap 30 visible words on a phone (`python scripts/check_word_caps.py --life`: a new story-mode player, the HUD and every
sheet below, plus one step further where there is one). The same switch (`clean()`) gates every change; desktop and the
classic layout keep their text.

- **House** (`v4/house.js`, `home-items.js`): the place card is its name and `🏠 6 · 🍚 4 xu/ngày`, the cosy score rides
  on "🚪 Vào phòng"; the inventory, the home listings (with the rental market's button inside) are one fold each; the
  savings card is not drawn twice when the next-step line already says "open the bank". 115 → 29.
- **Town map** (`journey.js chapterCard({compact})`, `town-walk.js`): the goal and its button, the count beside the
  chapter, the "why this place" line left out; the new player's pointer in four words. 51 → 29.
- **Fair** (`fair.js`): the gift card says "Đã bỏ vô ví 👛" and is the whole screen until "Vào hội"; "không có tiền thật"
  always shows, in its short form. 66 → 25 (gift) / 28 (gate). The ring game never replays a round the server already
  closed (`S.ring.dead`: the `fair_ring_over` loop, 534 refusals in 3 days).
- **Bank** (`bank.js`): icon tabs with the open tab's word, `STK …` in the header, the default way to pay as one fold, the
  amount's label as its placeholder, empty-state tile lines dropped, a good-news line fades after 6 s (text only, a typed
  amount stays). With an account: 144 → 27.
- **Quầy** (`quay.js why()`): the explanation paragraphs (a shift's money, invites, receipts, tax, supplies, stock) fold
  behind the quầy's own "?" (44 px on the phone).
- Already within the cap at 1.9.8 and unchanged: stall's first screen (24), wardrobe (25), spending (16), karaoke (15),
  HUD (16–20).

## Stock room order card (kho-compact, 10/10)

Owner: "cái này dài quá, dài dòng quá" (the "Nhập …" card every career with a stock room shares, `views.js orderCard`).
113–131 → 26–31 words (`python scripts/check_word_caps.py --kho`: cap 35 on 360 × 780 and 390 × 844, title not cut, no
sideways scroll). Kept on the card: the total, the wholesale tag, a ship tag only when it costs, when it arrives, the
shelf `📦 n/cap` and the "Đầy kệ · N" chip, and the reason it cannot go (a red line, plus the dimmed "Đặt ngay" with a
"Lấy N" fix). Behind the card's `helpBtn`: each supplier's hours, notes and terms, how ordering works, what "Tự chia"
does. Suppliers are one-line radio rows with curated short names (`SUP_SHORT`; the full name is the label). On a phone
the stock sheet's money chip shows the fund only (`.inv-sheet`): orders never touch the wallet.
