# Teacher and tour-guide work screens (workplace scenes, sub-project 2)

Date: 2026-09-29 · Branch: `workplace-scenes`

## Goal

The teacher ("Lớp học Mầm Nắng") and tour-guide ("Chuyến đi Mây Lang Thang")
work sheets looked like a shop counter: one long column of cards, with the main
button far below the content. They should feel like the job instead: a
classroom with pupils at their desks, and a trip with a map, a group and a
route.

This is a render-only change. The server rules, commands and payloads are the
same as before (`lesson_*`, `tour_*`, `cl_*`, and the local `lessonStep`,
`lessonReset`, `lessonPlan`, `tourRoute` and `tourReset` actions in `app.js`).

## Files

| File | Role |
|---|---|
| `public/js/v4/teach-tour.js` | `lessonV2` (teacher period) and `tripV2` (trip); both exports and their signatures are unchanged |
| `public/js/v4/classroom.js` | "Kế hoạch lớp" sheet, now laid out as a planner |
| `public/css/teach.css` | All styles, scoped to `.tt` (work screens) and `.cp` / `.nb` (planner) |

`experience-ui.js` needed no change. `extendedJob` already hands v2 tasks to
`lessonV2` and `tripV2`. The v1 fallbacks (`teacherJob`, `guideJob`) only run
for old saves that made v1 progress, and they are untouched.

## Shared pieces

- **Sticky action bar (`.tt-bar`).** It always shows the next step in one line
  and the main button, and it stays pinned above the sheet footer, like the
  food kit's `actionBar`. The footer height comes from `keepBarAboveFooter`
  (imported from `careers/food_kit.js`). Teacher and tour are not plugin
  careers, so they have no `tick` hook. Instead, a `MutationObserver` on
  `#sheetContent` re-measures after every render (and on `resize` /
  `layoutchange`). The CSS fallback is 68px on phones.
- **Section heads (`.tt-sec`).** Each section has a title on the left and a
  live count on the right ("4/5 có mặt", "2/5 điểm", "3/5 đã chấm").
- **Event cards.** Classroom moments and road situations are labelled "Cần bạn
  quyết". Choosing an option sends the same command as before.
- **Accessibility.** All text is at least 14px (`--tt-s: max(14px,.875rem)`),
  every tap target is at least 44px, and the illustrations have ARIA labels:
  the chalk step dots, the map (it reads the route order) and the seats list.

## Teacher: a classroom

Top to bottom:

1. **Timetable strip.** It lists today's periods (plus any unfinished ones
   carried over) as "Tiết N · môn" with a status: ✓ Đã dạy, ● Đang dạy, Dạy dở
   or Chưa vào. Tapping another period opens it (`data-action="job"`, which is
   already in `app.js`). The strip scrolls so the current period is in view.
2. **Chalkboard.** It shows the period, the subject and the difficulty stars,
   then the question. Once the plan is set, it also shows the three activities,
   with the current one outlined ("▶ Đang dạy"). The footer has the class condition (e.g. "Vừa hết giờ ra chơi")
   and the five chalk step dots ("3/5 · Dạy"). The board is an illustration, so
   its colours are fixed and dimmed with `--scene-filter`.
3. **Class mood meter**, and the talk button.
4. **Seating chart (Sơ đồ lớp).** There is a teacher's desk, then one desk per
   pupil. What each desk says depends on the step:
   - roll: Đang ngồi / Xin nghỉ ốm / Đến muộn / Ghế trống, then the recorded
     result;
   - plan: the pupil's learning style, if the class notebook knows it. It gets
     a ✓ when the plan covers that style. Otherwise the desk shows "❓ Chưa rõ"
     and the pupil's trait as a hint;
   - teach: Theo kịp / 🙋 Cần giúp / 💡 Đã hiểu / 🚪 Ra ngoài;
   - check and ready: 🎫 Chờ chấm / the mark given.

   Absent pupils are shown as dashed empty desks marked "Vắng". Every cue comes
   straight from `t.room`. Nothing is shown that the server hides: ticket
   correctness, for example, is never revealed.
5. **The step's work:**
   - roll: "Sổ điểm danh" cards, only for the pupils who need a decision; the
     bar holds "✓ Có mặt · N bạn";
   - plan: a lesson planner with three numbered slots (Mở đầu / Hoạt động chính
     / Kiểm tra cuối tiết) and the learning styles covered so far, then the
     activity cards. The bar shows "⏱ 27/35′ · 3/3", the reason the plan cannot
     be set yet (or "Chốt nhé!"), "↶ Chọn lại" and "Chốt giáo án";
   - teach: the classroom moment first, then "Bạn cần giúp" cards with four
     method buttons in a 2×2 grid. The bar holds "Sang hoạt động N" / "Thu
     phiếu", and it is blocked while a moment is still open, as before;
   - check: the correct answer, then one ticket card per pupil with three
     feedback buttons. The bar shows how many tickets are left;
   - ready: a result card (stars, pupils who understood, mood, moments log).
     The bar holds "Khép tiết" and keeps the old confirm step.

## Tour guide: a trip

1. **Chips** for weather, group fund (and wallet top-up), clock and difficulty,
   then a four-step trail (Lộ trình, Điểm hẹn, Tham quan, Về bến), then the
   group mood meter.
2. **Group roster (Đoàn hôm nay).**
   - When planning: each person shows their wish, with a ✓ once the route
     covers it. Older people also show their note, and "⛰️ Ngại dốc" appears if
     the hill is on the route.
   - On the road: one pill per person. Anyone at the centre of an open
     situation is highlighted with it ("⏰ Chưa ra điểm hẹn", "🥵 Choáng vì
     nắng"). Everyone else shows the story style they like, or ✓.
3. **Plan.** The map shows the pins numbered in route order, and the place list
   below uses the same numbers ("＋" when a place is not picked). On wide sheets
   the map and the list sit side by side. The sticky route summary shows
   ⏱ time/limit, 🎟 tickets/fund and 😊 happy/total, the first warning or "đủ
   điều kiện", "↶ Chọn lại" and **Chốt lộ trình**, so confirming is always one
   tap away.
4. **Gather.** The late-arrival situation, the roster headcount, then the
   chosen route (map plus an itinerary with walking time, visit time and
   tickets). The bar holds "Xuất phát", blocked until everyone is there.
5. **Stop (the trip in progress).**
   - A smaller map: the walked legs are drawn solid green, done stops are
     ticked, and the current stop pulses ("đang ở đây"; the pulse is off under
     reduce-motion).
   - The "Điểm i/n · đang ở đây" card, then any road situations.
   - "Kể gì cho đoàn nghe?", where each style shows how many people like it.
   - The compact roster.
   - The bar shows the next stop and "Đếm đoàn & đi tiếp / về bến".
6. **Ready.** A result card with stamps, time, fund left and the log, then the
   full itinerary with every stop ticked. The bar holds "Khép chuyến" and keeps
   the old confirm step.

## Class planner (Kế hoạch lớp)

The sheet now reads like a teacher's notebook:

- a date line ("📅 Tháng 10 · Tuần 3 · Ngày 7 của năm học"; a game month has
  four days, so each day stands for a week);
- month tabs with that month's events (past months faded, the current one
  highlighted);
- ruled pages with a margin line:
  - "Việc hôm nay" has one row per offer: kind tag + subject, title, intro,
    "N bước · +xu" and **Bắt đầu**;
  - while an activity is open: an "Đang soạn" page, a "📌 Ghi chú cần đọc" fold
    above the steps, then the procedure steps, "Hoàn thành hoạt động" and
    "Tạm gác";
  - "Nhận xét sau giờ" (the recap), the "Sổ chủ nhiệm" fold, and "Đã làm gần
    đây" (the log).

## Layout

- **Phone (390px).** One column; seats in three columns (two while planning, so
  the trait hints fit); the group roster in two columns; learning-method
  buttons in a 2×2 grid. There is no horizontal page scroll. The only
  horizontal scrollers are the timetable and month strips.
- **Wide sheets** (container query on `sheet`). 4–5 desks per row, three-column
  roster and cards, the map beside the place list, and bar buttons that keep
  their width.
- **Themes.** Chrome uses tokens only. The chalkboard and the map are
  illustrations and are dimmed by `--scene-filter` in the `dem` theme.

## Verification

- `node scripts/check_js.mjs`
- `scripts/run_checks.py` (full suite)
- `scripts/browser_v04.py --careers teacher,tour_guide,milk_tea`: 0 problems
- A scripted phone play-through that uses the UI buttons. It covers one full
  period and one full trip at tier 1 and tier 3, in the `kem`, `bien` and `dem`
  themes, on phone and desktop (1440px). Every step's action was reachable, and
  there was no overflow, no text under 14px and no tap target under 44px in
  the new screens.

## Follow-ups (outside this change)

- **English pack.** The new Vietnamese strings (section titles, seat cues,
  roster cues, bar texts, planner labels) need `scripts/i18n_extract.py` and
  translations. Until then they show in Vietnamese in English mode. Wherever an
  existing string fitted, it was reused.
