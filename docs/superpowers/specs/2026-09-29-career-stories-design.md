# Career stories: every workplace has its own arc

Date: 2026-09-29 · Sub-project 4 (scenes → work screens → care mechanics → career stories)

## Problem

The game has one story: the neighbourhood journey (`game/journey.py`, `docs/JOURNEY.md`), six chapters about
moving in and growing up. Inside a workplace nothing unfolds. The same customers come and go, and day 30
at the classroom feels like day 3. Nobody at the workplace has a story of their own.

## Goal

Each of the 20 careers gets **one short arc of 5 beats** with a small recurring cast. The beats unfold as you
keep working there. Examples: a shy pupil who performs at the year-end show, a stormy rainy season and the first
organic certificate, an elderly woman who waits for letters from her grandson abroad, a couple who come back to
the same homestay room every year, and in the offices a first audit, a fake invoice and a promotion.

The arcs run alongside the journey and never gate it. They carry no difficulty, never cost money and cannot
fail.

## Design

### Content (`game/career_stories.py`)

```python
ARCS[cid] = dict(
    title='Tiếng hát của Minh', emoji='🎤',
    keepsake=dict(emoji='🎨', name='Bức vẽ của Minh', desc='…'),   # shown when the arc is complete
    cast={'minh': dict(name='Minh', emoji='🙈', role='Học sinh bàn cuối', npc='teacher_npc_02'), …},
    beats=[dict(id='teacher_1', title=…, emoji=…, hint=…,          # hint = teaser while it is the next beat
                when=dict(served=1, days=0, level=1, gap=0, metric=None),
                lines=[('minh', 'text'), ('me', 'text'), …],       # 3–6 lines
                choice=None | dict(prompt=…, options=[dict(id='a', label=…, reply=[lines], rel='minh', coins=0), …])), …])
```

* **Speakers** are ids from the arc's own `cast`, or `'me'` (the player: their name and avatar). Cast members
  reuse the career's existing NPC names (Minh and Cô Hạ at Mầm Nắng, Chú Tám at Đồi Gió, Chị Hạnh at the
  post office…), and `npc` links a cast member to its `NPC_INDEX` id so a choice can warm that relationship.
* **Gender-aware text.** A line is a string with tokens, or a `dict(male=, female=, none=)` like journey lines.
  Tokens: `{anh}`/`{Anh}` (anh, chị, bạn), `{thay}`/`{Thay}` (thầy, cô, cô) and `{name}`. The server resolves
  them with the journey gender, so the client receives plain text.
* **Triggers** read the real save for that workplace: `served` (tasks finished, `metrics.served`), `days`
  (closed days, `day - 1`), `level` (`1 + xp // 90`), an optional `metric=(key, n)`, and `gap`, the minimum
  number of workplace days since the previous beat fired. Beats are strictly ordered: beat *n+1* is only
  considered after beat *n* was seen. The default rhythm is: beat 1 after the first finished task, then roughly
  days 2, 4, 6 and 9, with a gap of at least one day, so a workplace shows at most one beat per day.
* **Choices** (on 1–2 beats per arc) have exactly two options, and both are decent people's answers (in the
  office dilemmas both options refuse the fake invoice, in two different ways). An option's effect is only
  flavour: 1–2 reply lines, `rel` (+6 relationship with a linked NPC) and at most a few coins
  (`coins ≤ 10`, booked to the workplace fund as `story_reward`). A later line can depend on an earlier choice
  with `('who', 'text', ('beat_id', 'option_id'))`.

### State (root `s['stories']`, like `s['journey']`)

```python
dict(version=1, seq=0,
     queue=[dict(id='s7', career='farm', beat='farm_3', day=5)],     # due beats, oldest first
     arcs={'farm': dict(seen=['farm_1', 'farm_2'], picks={'farm_2': 'a'}, last=4)})
```

* `seen` is always a prefix of the arc's beat ids. `picks` only holds beats with a choice, and only after they
  were seen. `last` is the workplace day the latest beat fired.
* A career has at most one queued beat at a time, and a queued beat is always the next unseen one.
* `initial()` goes into `engine.new_state()`. `migrate(s)` uses setdefault inside `engine.migrate_state` (old
  saves load with an empty book, and their arcs start from beat 1 at the next action, one beat per workplace
  day). `validate(s)` checks all of the above from `engine.validate_state`, so bad imported saves are rejected.
* If `reset_career` sends a workplace back to day 1, the arc keeps its progress. The gap check treats a day
  earlier than `last` as "enough time passed".

### Engine hooks (`game/engine.py`, hooks only)

* import `career_stories as cst`; `new_state()` adds `stories=cst.initial()`; `migrate_state` calls `cst.migrate(s)`;
  `needs_migration` also checks for `'stories'`.
* `apply_action`: `st_*` commands route to `cst.action()`, like `jr_*`. After every career action,
  `cst.after(s, career, action, result)` runs next to `jr.after()`. It queues the acting workplace's next beat
  when that beat is due and puts `result['story']` on the result.
* `public_state` sets `v['stories'] = cst.public(s)`; `validate_state` calls `cst.validate(s)`.

### Commands

* `st_seen {id}`: acknowledges a queued beat that has no choice. It is marked seen, and the journal of that
  workplace gets a line: "Truyện nghề · <title>".
* `st_choose {id, option}`: answers a queued beat that has a choice. It applies the option's effect and returns
  `result['story'] = dict(reply=[lines], note=…)`, so the client can show the reply.
* Both reject ids that are not queued, a choice on a plain beat and a plain seen on a choice beat.

### Public view

```python
stories = dict(
  due=[dict(id, career, beat, step, total, title, emoji, arc, place, lines=[dict(who, name, emoji, text)],
            choice=dict(prompt, options=[dict(id, label)]) | None, last=bool, keepsake=… if last)],
  arcs=[dict(career, title, emoji, seen, total, done, hint, pending, keepsake, beats=[dict(title, emoji, pick)])])
```

Arcs are listed for every workplace, and the client only shows the ones you have started. Only the text of
due beats goes to the client, so the view stays small.

### Client

* `public/js/v4/stories.js` + `public/css/stories.css` (one `<link>` in `index.html`).
* **Scene.** Its own `<dialog id="stScene" class="jr-scene st-scene">` reuses the journey scene frame and speech
  bubbles (`.jr-scene`, `.jr-line`, `.jr-bubble`). A header strip in the workplace colour shows the place,
  "Truyện nghề · 2/5", a large beat emoji and the title. Lines appear one at a time with "Tiếp"; "Xem hết"
  shows them all, and reduced motion shows them all at once. At the end come the two choice cards, or
  "Khép lại". After a choice, the reply lines and the effect note follow. The last beat shows the keepsake.
* **Trigger.** It is wired like the journey scenes: `journeyBoot` calls `storiesBoot`, and the journey's
  `maybeScene` hands over to `maybeStory()` when it has nothing to show. A journey chapter always goes first. Only the beat of the workplace you are at opens on its own; beats of other workplaces wait on the journey home.
  A dismissed scene (Esc) is snoozed for this page load and stays reachable from the journey home.
* **Journey home.** Under the chapter card sits a "Truyện nghề" card. It lists every started workplace's arc:
  emoji, arc title, progress pips (5), the next hint or "Có chuyện mới · Xem" when a beat is due, and the
  keepsake when the arc is done.
* Client actions are named `jrArc*` (not `jrSt*`: `jrStory` already exists) so they route through `journeyAction` without touching `app.js`.

## Tests (`tests/test_career_stories.py`)

* All 20 careers have 5 beats, unique ids, 3–6 lines per beat, valid speakers, 2-option choices, valid `rel`
  links and coins ≤ 10.
* Triggers fire in order, never twice, at most one per workplace at a time, and respect `gap`.
* `st_seen` and `st_choose` work and reject misuse. Choices apply their relationship and coins, and replies and
  variant lines follow the pick.
* A save without `stories` migrates and validates. `validate_state` rejects broken queues and picks, and a
  `seen` list that is not a prefix of the arc.
* Gender tokens resolve for all three variants.

## Out of scope

Replaying seen beats (the card lists their titles and choices), new journey titles for arcs (keepsakes stand
in), and English text (the i18n pack is rebuilt by the lead with `scripts/i18n_extract.py`).
