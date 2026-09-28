# Plugin careers (v0.4)

A plugin career is one Python module `game/careers/<id>.py` (server rules) plus one
ES module `public/js/careers/<id>.js` (workbench UI) plus one test file
`tests/test_career_<id>.py`. The engine owns money, reviews, turns, validation,
saves and multiplayer; a plugin only changes **its own task fields** and
**`c['ext']['data']`** through `game/careers/kit.py`. Reference implementation:
`game/careers/restaurant.py` + `public/js/careers/restaurant.js` +
`tests/test_career_restaurant.py`. Read those three files first.

Everything is fictional game content (coins "xu", fictional places/companies,
fictional laws/tax rates marked as game rules). Vietnamese is the source language.

## 1. Server module contract

```python
from . import kit
ID = '<id>'                      # must match the file name and SPEC['id']
FIXED = ('needs', ...)           # task keys that must never change after make_task
SPEC = dict(...)                 # see below
def make_task(day, slot, serial) -> dict      # deterministic from (day, slot) only
def initial() -> dict                        # initial c['ext']['data'] for this career
def handle(s, c, name, p) -> dict            # every action starting with SPEC['prefix']
def validate_task(t, original) -> None       # type/range checks of mutable task fields
def feedback(c, t) -> dict                   # dict(criteria=[dict(key,label,score 1..5,note)], [stars], [cap])
# optional hooks
def validate_data(c) -> None                 # validate c['ext']['data']
def known_request(c, t) -> str               # text revealed by the engine's 'ask' action
def public_task(t) -> dict                   # hide secrets; default strips keys starting with '_'
def public_data(c) -> dict                   # projection of c['ext']['data'] for the client
def on_task(s, c, t) -> None                 # after a task is created (e.g. freeze quoted price)
def on_start(s, c) -> None                   # when a shift opens
def on_close(s, c) -> dict | None            # when a shift closes (summary['career'])
def assist(s, c, employee, t) -> str | None  # hired staff helping; roles from SPEC['roles']
def hint(c, t) -> str                        # assistant/hint text
def content() -> dict                        # static data for the client: content.careers[<id>]
```

### Tasks
* Build tasks with `kit.base_task(ID, day, slot, serial, npc_index, title, opening, **fields)`.
  `npc_index` indexes `SPEC['people']` (0-based). Use `kit.rng(ID, day, slot)` for
  deterministic variety. **Never** depend on player state in `make_task` — the
  validator regenerates every task from `(career, day, slot, created_turn)` and compares
  every key in `FIXED` plus `npc/title/opening/kind/needs/variant/solution/value/evidence`.
* Task statuses: `new` → (`ask` sets `known=True`, `understood`) → `in_progress`
  (`kit.start_work(t)`) → `completed` / `referred` / `cancelled`. Do not invent other statuses.
* Finish a task exactly once with `kit.complete(s, c, t, reward, narrative, status='completed')`.
  It pays the reward, writes a memory, creates the **persona review** (via your
  `feedback()`), updates streaks, tips and the next active task.
* `t['mistakes'] += 1` for real mistakes (wrong item, wrong step). Mistakes lower patience
  and feed the review. Allow imperfect completion where real life would (customer still
  pays but complains) and refuse where real life would (allergen, wrong document, illegal).
* Hide answers: either keep them under keys starting with `_` (stripped by default) or
  implement `public_task`. Before `t['known']` hide the order/needs like restaurant does.
* `validate_task` must type/range-check every mutable field (ints with `kit.integer`,
  ids in known sets, list lengths bounded). Saves are imported from JSON.

### Actions
* All actions start with `SPEC['prefix']` (2–3 letters + `_`, unique; taken: `rs_`,
  `shop_ ph_ ac_ cs_ lesson_ tour_ tea_ life_ ops_ inv_ sit_ fb_ job_`).
* The engine requires an open shift for plugin actions unless listed in
  `SPEC['free_actions']`. Every action advances one turn unless in `SPEC['no_tick']`.
* Raise errors with `kit.need(cond, 'Vietnamese message')`. Validate every payload value
  (`kit.one_of`, `kit.integer`, `kit.text`, `kit.id_list`, `kit.confirm(p)` for actions that
  spend coins or are irreversible). Never trust client numbers for money.
* Return `dict(message='…')`, optionally `celebrate=True`.
* Money: `kit.money(s, c, ±amount, reason, ref, category)`. Stock: see inventory below.
* Real-time mechanics (cooking, drying, baking) use `kit.now()` (wall clock seconds, tests
  replace `kit.clock`). Store timestamps as floats in the task; compute results on the
  action that ends the timer.

### SPEC keys
| key | meaning |
|---|---|
| `id`, `prefix` | career id, action prefix |
| `category` | `food`, `shop`, `service`, `office`, `outdoor` (catalogue grouping) |
| `meta` | `short, place, tagline, icon, color, light, weather, work, station, greeting, caption, map_label` (map_label like `'09 · TIỆM HOA NẮNG'`) |
| `people` | 5–7 tuples `(name, role, personality, persona)`; persona ∈ `sour bossy warm picky genz quiet` (`parent_*` for teacher-like). NPC ids become `<id>_npc_01…` |
| `staff` | 4 tuples `(name, role, bio, speed, precision)` for hiring; roles from `roles` |
| `roles` | `{role_id: 'Vietnamese role name'}` (a `patrol` role is added automatically) |
| `inventory` | `dict(items=[...], capacity=40)` or omit (service careers). Item: `id, name, emoji, group, unit, cost, [price], [life] days, [start] qty, [unlock] level, [allergen]` |
| `prices` | `{key: base_price}` player may tune ±25% before a shift (`life_price`) |
| `tip` | coins tipped for a perfect job (0–3) |
| `physical` | actions that make *other* waiting customers lose patience |
| `free_actions`, `no_tick` | see above |
| `waste_items` | extra ids allowed in waste log (e.g. `'bowl'`) |
| `activity` | `(emoji, label, [(card, bin)×4], [step×4])` → 4 mini-games |
| `stories` | 3 × `(title, (beat1, beat2, beat3))` short Vietnamese story chapters |
| `review_asides` | 4 short funny lines appended to perfect reviews |
| `situations` | 5–8 real-life situations (format below) |
| `employment` | only for employed jobs (accountants…): `dict(postings=[...], questions={...})`, see `game/employment.py` `POSTINGS`/`TEACHER_QUESTIONS` |
| `guide` | one-line how-to |

### Situations (real-life, many perspectives)
```python
dict(id='XX-S01', title='…', npc=<people index>, tone='gentle'|'tense', min_day=1,
     opening='…', swap='(optional) you are now the customer: …',
     facts=[dict(id, title, source, text)],            # player reads facts before deciding
     options=[dict(id, label, requires=[fact ids], cost=0..80, reward=0..60,
                   quality='good'|'ok'|'bad', stars=1..5 (optional → posts a review),
                   review='review text if stars', outcome='what happened',
                   perspectives=[dict(who, emoji, text), ...])],  # 2–3 viewpoints
     lesson='one sentence takeaway')
```
Write situations from real work life of that job: difficult customers, suppliers, staff,
inspections, mistakes, ethics (honesty, privacy, safety), money disputes, emergencies.
Good options are not always free; bad options are tempting shortcuts. Every option shows
how at least two different people experienced it.

### Inventory (trade careers)
`SPEC['inventory']` enables the shared stock system (`game/inventory.py`): suppliers
(market/partner/express with different price, lead time, short-delivery rate), order →
count on arrival → claim short delivery → rate supplier; lots expire by game day.
In `handle` use `kit.stock(c, item)`, `kit.take(c, item, qty)` (returns cost of used
units; accumulate it on the task for waste accounting) and `kit.waste(...)`.
Opening stock comes from each item's `start`.

### Employment (office jobs)
If `SPEC['employment']` exists the shift cannot open until the player is hired (CV →
letter → interview → offer → probation). Postings: `dict(id, org, kind, title,
salary=(min,max), probation_days, wants=[strength ids], perks=[...], culture, questions=[qid...],
reference=True)`; `questions={qid: dict(text, options=[dict(id,label,score 0..3,note)])}`.
Salary is paid by the engine at day close. Task rewards for employed jobs should be small
performance bonuses (10–30).

### Procedures (paperwork careers)
`game/procedures.py` gives a step engine for accounting/tax/payroll: build
`t['proc']=[procedures.step(...)]` in `make_task` (answers in `_key`), `t['proc_state']=
procedures.initial_state()`. In `handle`: `ok,msg=procedures.submit(t, p.get('step'),
p.get('answer'))`; `procedures.done(t)`. In `public_task`: `steps,state=procedures.public(t)`.
In `validate_task`: `procedures.validate(t, original)`. Step kinds: `choice multi number
order match fields entry` (see module docstring). Put `'proc'` in `FIXED`.
Build steps from lists/dicts only (no tuples): `validate` compares the steps after a JSON
round-trip. `entry` answers are `[{debit, credit, amount}]`; a voucher split into
different debit/credit pairs is accepted when every account's debit and credit totals match.

## 2. Client module contract (`public/js/careers/<id>.js`)

```js
export default {
  id: '<id>',
  // Main workbench HTML for the active task (inside the job sheet body).
  job(t, x) { return `...html...`; },
  // Short "next step" text for the task card.
  next(t, x) { return '…'; },
  // Optional: called every 200 ms while the job sheet is open (real-time bars).
  tick(root, x) {},
  // Optional: input/change events inside .career-job (keep typed values in x.ui so
  // they survive re-renders). Return true to stop the default handlers.
  input(el, x, type) { if (el.name === 'qty') { x.ui.qty = el.value; return true; } },
  // (Without input(): a changed <select|input data-car="name"> calls actions.name({...dataset, value}, el, x).)
  // Optional: <form> submit inside .career-job. Return true when handled.
  async submit(form, x) { await x.send('xx_save', {text: form.elements.text.value}); return true; },
  // Optional: HTML for this career's part of the day-close summary
  // (receives the dict returned by the server module's on_close).
  summary(data, x) { return `...html...`; },
  // Optional: panel shown when there is no active task or it just ended
  // (cash settlement, refuel, field chores…). Wrap it in `.career-job` like `job()`.
  idle(x) { return `...html...`; },
  // Optional scoped stylesheet public/css/careers/<id>.css (theme tokens only).
  css: true,
  // Optional custom handlers for data-action="car:<name>" (local UI state).
  actions: { async pick(data, el, x) { x.ui.selected = data.item; x.render(); } },
  // Optional: extra dock buttons [action, icon, label, sub]
  dock: [],
};
```
`x` (context) provides: `x.state` (public state), `x.room` (current career public state:
`tasks, data, inventory, job, situation, feed, life, ops, money, day, level…`),
`x.content` (public content; note `x.state.careers[other]` is only a `{summary:true,…}` stub for careers that are not current), `x.cc` (= `content.careers[id]`), `x.ui` (a plain object
kept between renders for this career), `x.esc(s)`, `x.icon(name, size)`, `x.pill(label, kind)`,
`x.button(label, action, data, style, disabled)`, `x.cmd(label, command, payload, style, disabled)`
(button that sends a server command; add `{confirm:true}` in payload only when the user
already confirmed), `x.confirmCmd(label, command, payload, question, style)` (asks a
confirmation dialog then sends with `confirm:true`), `x.fmt(n)`, `x.money(n)`,
`x.now()` (server-synced seconds), `x.render()` (re-render sheet), `x.send(command, payload)`
(returns result or null), `x.toast(msg)`, `x.npc(id)`, `x.portrait(npc, size)`,
`x.t(text)` (translation), `x.stock(itemId)`, `x.procedure(steps, command, extra)` (renders
`procedures.public` steps with the shared step UI; submit/order-picking handled globally).
A command result with `correct: false` is shown as an error toast.
Server `on_close(s, c)` may return `lines: [str]` and/or `note: str`; without a client
`summary()` hook those and known numeric keys are listed in the day summary.

HTML conventions: use existing classes for consistency — layout `row spread wrap grow stack
space-top`, text `eyebrow muted small`, controls `btn primary ghost danger small full`,
`tag green amber blue danger`, cards `card`, grids `tile-grid` with `tile` buttons
(`<button class="tile" …><span class="tile-emoji">🥩</span><b>Bò Mỹ</b><small>5</small></button>`,
add `locked`/`selected`/`empty` classes), `bar` progress (`<div class="bar"><i style="width:40%"></i></div>`),
`kv` key/value lists, `workbench` two-column layout (`<div class="workbench"><section class="wb-main">…</section><aside class="wb-side">…</aside></div>`).
Always escape user/NPC text with `x.esc`. No inline event handlers (CSP): use
`data-command`/`data-payload` or `data-action`. Touch targets ≥ 44 px. Must work at 360 px width.

## 3. Tests (`tests/test_career_<id>.py`)
Use `tests.helpers.Journey('<id>')` (auto-hires employed careers). Cover at least:
full happy path to `completed` with a review; each validation error path; hidden info
not in `public_state` before `ask`; save round-trip `validate_state(json.loads(json.dumps(state)))`;
tampered FIXED field rejected by `validate_state`; inventory decrement and waste on
dump; every situation can be read/chosen/confirmed (`sit_practice` then `sit_read`,
`sit_choose`, `sit_confirm`) without errors; employed careers: start_day blocked until
hired. Run `python scripts/run_checks.py` — all tests must pass.
