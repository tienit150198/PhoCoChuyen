# Lớp học Mầm Nắng — a class that lasts, and pupils and parents with a voice

Date: 2026-09-29 · Branch: care-wave1 · Career `teacher` · Files: `game/classroom.py`,
`game/teach_lesson.py`, `server.py` (`/api/ai/class`), `public/js/v4/classroom.js`,
`public/js/v4/teach-tour.js` (teacher part), `public/css/teach.css` (teacher part),
`tests/test_teacher_care.py`.

## Goal

Periods used to stand alone. Now the class is the same eight grade-2 pupils every day:
who is falling behind, who needs encouragement, and whether shy Minh (the career story's
"cậu bé bàn cuối") starts to speak up all carry over. Homework comes back the next day to be
marked, each parent expects a word about once a week, and the seat plan changes how pupils
learn. Pupils and parents talk in their own voice through the AI helper, but every effect is
a rule on the save. The model only rewords lines.

## 1. The care book (`data.class.care`, server-authoritative)

| key | meaning |
| --- | --- |
| `pupils[kid]` | `prog` per subject (`math` Toán, `read` Tiếng Việt, `think` Tư duy, 0–100), `well` (wellbeing 0–100), `voice` (0–5: Im lặng → Dẫn lời cả lớp) |
| `seats` | the 8 pupils in seat order: seat *i* is desk `i // 2` counted from the board, the even seat is by the window |
| `hw` | homework given today `{day, subject, size: light|full, kids}` |
| `books` | handed-in exercise books `{id, day, kid, subject, size, kind, mark}` (`kind` stays server-side) |
| `parents[kid]` | `trust` 0–10, `last` contact day, `sent` last day the teacher wrote first |
| `threads[kid]` | message lines `{who: parent|teacher, text, mode: scripted|ai|guard, canonical?, day, ask?, topic?, subject?, late?, q?}` (≤ 12) |
| `day`, `taught`, `subject`, `seen`, `mailed`, `called`, `seq`, `log` | sync day, today's teaching, contacts today, a short class log |

Lesson topics map to subjects: Toán vui / Đếm hình / Đo lường → Toán; Đọc hiểu / Đọc bảng →
Tiếng Việt; Quan sát / Phân loại → Tư duy. Starting values are fixed per pupil (Tú reads at 40
and is new, Bảo's maths is 42, Minh's voice is 0, Linh's wellbeing 45…), so someone is close
to falling behind from day one.

**Day rollover is lazy.** Every class action (`cl_*`, `lesson_*`) first brings the book up to
`c.day` (at most 7 steps). The public projection syncs a copy, so reading never writes the
save and the next action gives the same result (everything is seeded by kid and day).
Per day passed: yesterday's homework is handed in, marked books leave, books unmarked for 3
days go home without a word (−1 wellbeing), wellbeing drifts 2 towards 55, a parent not
contacted for more than 6 days loses 1 trust (never below 1), and a parent's message left
unanswered for 2 days loses 1 trust once (`late`).

**Migration.** Old saves have no `care`: it is created on first use. A pupil's old notebook
trust counts (+2 wellbeing per trust point, up to +10). Existing commands and payloads are
unchanged; old rooms without `ask` stay valid.

## 2. After each period (`classroom.after_period`, called from `teach_lesson._finish`)

For the lesson's subject, per pupil of the period:

| exit ticket | right mark | wrong mark |
| --- | --- | --- |
| right / slip (understood) | +4 progress, +1 wellbeing | +2, −2 |
| copy | +1, +1 | −1, −2 |
| wrong (not helped, away) | −2, +1 | −2, −2 |
| absent (sick, missing) | −1 progress | |

Seat effects are added (below). Band crossings ("tiến bộ", "đang hổng") go into the log and
the close message. Every notebook trust change (roll call, classroom moments, help) also
moves wellbeing by 2× the change, and +2 trust moves voice +1.

**Parents write after class** (once a day, at most two): the pupil is sad (wellbeing < 35) →
`sad`; falling behind (a subject < 40) → `worry`; yesterday's homework came back tired or
missing → `hw`; improved a band or reached a story beat → `thanks`; not heard from for 4 days →
`check`. The text is a scripted line built from the real data (per-parent flavour for Bố Tú,
Bà nội Khoa, Mẹ Vy), stored `ask: true`.

## 3. Parents: messages and the weekly rhythm (`cl_parent {kid, option | text}`)

A game day is a school week in the planner's calendar. Each parent is due after 4 days
without contact; two parents a day keeps everyone in rhythm, and the second contact of the
day gives +4 XP. `cl_parent` either answers the waiting message or (once a day per parent)
starts one.

* Scripted choices (neutral ids `a|b|c`, seeded order, quality never sent to the client):
  a reply built from the child's data (specific: the subject, the band, how the teacher will
  help — the kid's learning style only if the notebook knows it — and a home tip), a vague
  "yên tâm, con vẫn ổn", and a blaming comparison. Starting a message: good news (good if a
  subject ≥ 60 or wellbeing ≥ 60), asking the family to help (good if a subject < 55 or
  wellbeing < 45), or a short hello (ok).
* Typed text (≤ 200 chars) is judged by rules: naming another pupil mid-sentence →
  `privacy`; blame or comparison words → `poor`; the child's name or a subject (+2), a
  concrete next step (+1), warmth (+1) → `good` at 3, `ok` otherwise.
* Effects: good +1 trust (+1 more when answering a message the same day), and the pupil +2
  wellbeing (+4 for a `sad` message); ok 0; poor −1 trust, −1 wellbeing; privacy −2 trust.
  A parent at trust ≤ 1 after a poor reply posts in the feed.
* Trust feeds back into homework: trust ≤ 2 makes a missing book more likely, ≥ 8 less.

## 4. Homework (`cl_hw {size}`, `cl_hw_mark {book, mark}`)

After at least one period today, give the day's subject as light (3 questions) or full (6)
to the pupils seen in class. The next day each book comes back seeded by kid, day and size:
`missing` (4 % + sad + low parent trust + full), `tired` (full only; Mai +40 % — she helps her
mother's phở stall at dawn — and Linh +12 %), else `good` or `some` by progress. The book shows
a clue ("Làm đủ, sai hai câu cùng một chỗ"); the teacher marks:

| kind | right mark | effect | wrong mark |
| --- | --- | --- | --- |
| good | Khen cụ thể | +1/+2 progress, +2 wellbeing, +1 XP | Chữa → −2 wellbeing; Hỏi riêng → −1 |
| some | Chữa cùng con | +2/+3 progress, +1 wellbeing | Khen → nothing learned; Hỏi riêng → −1 |
| missing / tired | Hỏi riêng vì sao | reveals the reason (per pupil), +1 wellbeing | Khen/Chữa → −3 wellbeing, parent −1 trust |

## 5. Seats (`cl_seat {a, b}` swaps two pupils; not during teach/check)

Applied to each present pupil at every period close and shown live on the seat chart:
look-style pupils (Minh, Khoa) −2 progress on desks 3–4, +1 on desk 1; short-attention
pupils (Bảo, Linh) −2 by the window, +1 on desk 1 away from it. Deskmates: Minh+Vy (Minh +2
wellbeing, from the story), An+Tú (+1/+2 wellbeing), Khoa+Minh (+1 progress each); Bảo+Vy
(−2 progress each), Bảo+Tú (−2 wellbeing each), Linh+Vy (Linh −2 wellbeing, Vy −1). The
default plan puts Minh at the back next to Vy and Bảo by the window, so there is something
to fix.

## 6. A raised hand (`teach_lesson`: `lesson_invite`, `lesson_answer {task, option | text}`)

When the plan is locked, one pupil who is not part of a classroom moment is picked (seeded by
day and slot; weight 1 + voice, shy pupils 3, Minh 4). They ask a question about the lesson
during the main activity (phase 1). A pupil with voice < 2 does not raise a hand: they write
it on scrap paper (`quiet`) and the teacher may walk over and invite it (`lesson_invite`).

The teacher taps one of three scripted answers (neutral ids) or types ≤ 200 chars. Rules,
never the model, decide the quality: dismissive words ("nói rồi", "chú ý vào", "hỏi gì"…) or
abuse → `poor` and a mistake on the period; the lesson's key idea (+2), a method (+1, +1 more
if it fits the pupil's learning style), warmth (+1) → `good` at 3; otherwise `ok` (or `poor`
if very short). Effects: good +3 progress, +1 trust (→ +2 wellbeing), +1 voice; ok +1
progress; poor −1 trust, −1 voice. Moving on with the hand still up lowers it (−2
wellbeing, −1 voice); the button asks to confirm. Minh opening up is visible in the
notebook ("Dám hỏi khi được mời", "Hay giơ tay") and in "Cần để ý".

Stored in `room.ask = {kid, q, phase, state: quiet|up|done|down, lines, result, shy}` and
validated strictly (present pupil, the lesson's question, consistent state/result, ≤ 4
lines). The projection shows options without their quality.

## 7. AI route: `POST /api/ai/class`

Guarded like every POST (Host, session cookie, `X-Game-CSRF`, Origin / Sec-Fetch-Site), plus
the command rate limit.

```
request  {kind: "pupil"|"parent", pupil: <kid id>, task?: <task id, pupil only>,
          op?: "reply"|"voice", text?: str(1..200) | option?: "a"|"b"|"c",
          request_id?, expected_revision?}
response {state, revision, result: {message, reply, quality?, …}, mode: "ai"|"scripted",
          reason, reply}
```

1. `op: "reply"` (default) runs `lesson_answer` / `cl_parent` through `Store.command`
   (revision-checked, idempotent by `request_id`): the rules apply and the scripted reaction is
   stored. `op: "voice"` changes nothing but the wording of the newest pupil question or
   parent message.
2. If the line is still scripted, `aiConsent` is on, `ai.available()` and
   `ai_chat_budget` (shared with free chat: per minute, per day, server-wide) allow it, and the
   teacher's text is not abusive, `teach_lesson.voice()` asks for the line in character.
3. A reply that passes `ai.clean_reply` (no new numbers, links, contact data, state claims,
   "I am an AI", ≤ 3 sentences) replaces the stored text in a small transaction only if the
   line is unchanged (`mode: "ai"`, `canonical` keeps the scripted line). Revision +1.
4. Otherwise the scripted line stands with `reason` (`no_consent`, `not_configured`,
   `rate_limit`, `unsafe_request`, `new_numeric_claim`, `nothing_to_voice`, `superseded`…).
   409 on a revision conflict returns the fresh state.

`teach_lesson.voice(state, who, said, *, context, canonical, history, purpose, direction)`
uses `ai.persona_reply` for pupils that exist as NPCs (Minh, An, Vy, Bảo: their card, memory
and relationship come from `game/personas.py`, the turn's direction goes in `context`). The
other pupils and all eight parents have no NPC entry, so they get a card of the same shape
(`pupil_card`, `parent_card`: name, age, how they address the teacher, region and particles,
temperament from `ai.STYLE_GUIDE` plus a personal line — Bố Tú is curt and from Quảng Ngãi,
Bà nội Khoa types slowly, Mẹ Bảo "knows" education…) and the same prompt
(`ai._persona_system`), redaction, guards and timeout as `persona_reply`. Context is data
only: the lesson, the question, the answer quality in words, the child's progress bands
("cần kèm thêm (48/100)"), mood, voice, the parent's trust in words. The player's name never
leaves the server.

## UI (390 px first, theme tokens)

* Lesson (teach stage): the asking pupil's desk carries a bobbing "🙋 ?" bubble (✏️ when
  quiet); a panel shows the thread (question, the teacher's answer, the reaction), `AI` badges
  on AI lines (the title shows the scripted line), a typing indicator, three full-width answer
  choices and a 200-char box (Enter sends, Shift+Enter new line). The sticky bar says who is
  raising a hand. The ready stage links to the planner when parents are waiting.
* Planner (Kế hoạch lớp): "Cần để ý" (behind, sad, needs encouragement, Minh opening up, the
  class log), "Phụ huynh" (one fold per parent in a fixed order, status tag, trust bar, thread,
  choices and box; "Tuần này x/2"), "Bài về nhà" (give light/full, books to mark with three
  buttons), "Sơ đồ chỗ ngồi" (four desks, window marker, the seat notes, "Đổi chỗ" folds), and
  the notebook now shows subject bars, mood and voice.
* `teach-tour.js` has no `env`: it keeps the app's `GameAPI` instance (a thin wrapper on
  `GameAPI.prototype.accept`; `classroomView` also binds it) and handles its own
  `[data-cl]` clicks / `form[data-cl-form]` submits in the capture phase.

## Tests

`tests/test_teacher_care.py`: seeded hand-raise and hidden option quality; rules for typed
answers and parent messages; dismissive answers count as mistakes; invalid payloads leave the
save untouched; shy invite; ignored hand; tampered `ask` / care book rejected; old-save
migration without writes on read; period effects and parents writing; reply trust and the
daily contact limit; privacy; overdue and late-reply decay; homework hand-in, seeded results,
marks, expiry; seat notes and no swapping mid-lesson; the public view hides kinds and
qualities. With a fake OpenAI-compatible endpoint: pupil reply voiced and stored with
`canonical`; the NPC path (persona_reply) and the card path both used; voicing twice is a
no-op; parent message voiced and reply ruled by the rules; invented numbers and no consent
fall back; abusive text never reaches the provider; budget, bad input and CSRF.

## Not in this change

* English strings for the new lines (the i18n pack is regenerated by its owner).
* app.js could pass `env` to `lessonV2` so teach-tour.js would not need the `GameAPI`
  wrapper.
