# The interviewer talks back (AI interviewer)

Date: 2026-09-29 · Branch: care-wave1 · Status: implemented

Builds on `2026-09-29-ai-characters-design.md` (personas, `ai.persona_reply`, guardrails,
AI on by default). Everything here is fictional; wages are game coins.

## Why

Hiring (teacher, the office careers, pharmacy, customer care, tour guide, salon, pet care,
repair, delivery) was a quiz: pick A/B/C, read a fixed note. The owner wants the person
across the table to feel real: cô Thu, Chú Tư, anh Hải, chị Mai… ask about what *you*
said and wrote in your CV, and owners react to what you do in a trial.

## What the player sees

- Interview (`interview` stage): after each scripted answer — except the last question of
  the stage, and at most `MAX_ASKS = 2` per interview — the interviewer asks **one** short
  follow-up in a speech bubble. The first follow-up is about the answer just picked (good /
  middling / weak answer templates), the second about the CV (an experience line that needs
  proof → a strength → "mới vào nghề"). The player types a reply (≤ 200 characters) or
  presses **Bỏ qua**. The interviewer reacts in one line; a small chip shows the points
  (e.g. `+3 điểm · có ví dụ cụ thể · nêu lý do`).
- Trial (`trial`, salon/pet care/repair/delivery) and situational test (`test`, customer
  care, chị Mai playing the angry customer): after each step the owner / "customer" reacts
  in character. Flavour only; the step's score is the option's score as before.
- AI lines carry the `AI` badge (title = the scripted line). While the server works, the
  player's words appear as a pending bubble and the interviewer shows typing dots.
- Everything works identically without AI: the same scripted lines, same scores.

## Interviewer personas (game/employment_content.py `INTERVIEWERS`)

Keyed by posting id first, then career. Fields: `name, role, self, you, style, face, npc,
region, particles, cares`.

| who | where | voiced through |
| --- | --- | --- |
| Cô Thu (`pharmacy_npc_01`), Chị Mai (`customer_care_npc_06`), Anh Hải (`tour_guide_npc_06`), Chị Hạnh (`delivery_npc_07`, `corp_accounting_npc_01`), Chị Hồng (`tax_payroll_npc_01`), Chị Mai Anh (`group_accounting_npc_01`) | town characters | `ai.persona_reply(state, career, npc, said, purpose='interview', context=…, canonical=…, history=…)` — their own persona card and memory |
| Chú Tư, Chị Phượng, Chị Nhàn, Cô Ngọc (Mầm Nắng), Chị Thùy (Sao Nhỏ), Bác Sáu (Góc Phố) | not NPCs | `employment._local_reply`: the same prompt (`ai._persona_system(card, 'interview', …)`), `ai.chat`, `ai.redact`, `ai.clean_reply` and number check, with the card from `INTERVIEWERS` |

For NPC-backed interviewers the scripted lines use the persona's own address words
(`personas.persona(...)['address']`), so cô Thu says "con", chị Mai says "em".
Postings expose a public `interviewer {name, role, face}` in `content.employment.postings`.

## Data (application record, `c.job.application.talk`)

Bounded list (`TALK_MAX = 16`), validated strictly by `employment._validate_talk` (exact key
sets, lengths, enums, step ids answered in this posting, only the last entry may be open):

```
ask:   {kind:'ask', stage, q, who, text, mode:'scripted'|'ai', canonical,
        status:'open'|'answered'|'skipped', reply (≤200, redacted) | null,
        bonus (-3..3), rules [rule ids], react | null, react_mode | null, react_canonical | null}
react: {kind:'react', stage, q, who, text, mode, canonical}
```

`canonical` is always the scripted line; `text`/`react` hold the AI wording only when it
passed the guards (`mode`/`react_mode` = `ai`). Older saves simply have no `talk`.

## Commands (game/employment.py)

- `job_answer {question, option}` — unchanged scoring. Also: auto-skips an open follow-up
  (moving on is allowed; no penalty), then opens a follow-up (`interview`) or records a
  reaction (`trial`/`test`). Result carries `talk` = index of the new entry.
- `job_followup {text}` | `{skip:true}` — only while the last entry is an open ask and the
  application is `applying`. The reply is normalised (one line, no control characters,
  URLs/e-mails/phone numbers → `[đã ẩn]`), scored by the rules below, and answered with a
  scripted reaction picked by the strongest rule. Evaluation never waits for a follow-up.

## Scoring rule (rule-based, never AI)

`employment.score_reply(state, c, career, text) -> (bonus, rules)`; labels in
`REPLY_RULES` (also sent to the client as `content.employment.reply_rules`).

| rule | points | fires when the reply… |
| --- | --- | --- |
| `rude` | −3 | contains disrespectful words (`ngu`, `mặc kệ`, `hỏi làm gì`, `liên quan gì`, `im đi`…) or anything `ai.abusive` flags (includes `social.BANNED`) |
| `overclaim` | −2 | boasts (`nhiều năm`, `lâu năm`, `hàng trăm`, `chuyên gia`, `chưa bao giờ sai`…) while no career in the save has 15+ finished jobs — what a reference check would expose |
| `blame` | −1 | puts it on others (`lỗi của khách/đồng nghiệp/sếp`, `không phải lỗi của em`…) |
| `short` | 0 | has fewer than 3 words; blocks the positive rules |
| `example` | +2 | *(only if no rule above fired)* has a digit or a concrete-story marker (`ví dụ`, `có lần`, `lần trước`, `hôm qua`, `tuần trước`, `lúc đó`, `kết quả là`, `for example`…) |
| `reason` | +1 | *(only if no negative/short rule fired)* explains why (`vì`, `bởi`, `để`, `nên`, `because`, `so that`…) |

- One reply: clamp to **[−3, +3]**. All replies of one application: clamp to **[−5, +5]**.
- Added to the 0–100 score in `_evaluate` before the existing caps: the reference-check cap
  (40) and the unsafe-step cap (45) still apply, so the bonus can never rescue a dishonest CV
  or an unsafe trial move. A feedback line explains it, e.g.
  `Trả lời thêm với Cô Thu: +5 điểm (có ví dụ cụ thể +2, nêu lý do +1).`
- Skipping is always 0. The AI wording of any line has no effect on the score (tested).

## Route `POST /api/ai/interview` (server.py `Handler.ai_interview`)

Guarded like every POST (Host, session cookie, `X-Game-CSRF`, Origin / Sec-Fetch-Site,
64 KiB body cap, the per-session command rate limit).

```
request  {career, step:'answer'|'reply'|'skip', question?, option?, text? (1..200),
          request_id? (8..100), expected_revision?}
response {state, revision, result, mode:'ai'|'scripted', reason, line}
```

1. `employment.voice_command` validates the body → `job_answer` / `job_followup`, run through
   `Store.command` (revision-checked, idempotent by `request_id`; 409 returns the fresh
   state; invalid moves are 400 like any command).
2. If the result names a talk entry (`result.talk`) and it is still scripted
   (`employment.pending_voice`), and `aiConsent`, `ai.available()`, the player's words are
   not abusive, and `Handler.ai_chat_budget(token)` allows it (the shared chat budget:
   `AI_CHAT_PER_MINUTE`, `AI_CHAT_PER_DAY`, `AI_GLOBAL_PER_MINUTE`), `employment.voice`
   asks the model.
3. The line is stored by `_store_interview_line` in one small transaction only if talk[idx]
   still holds the same scripted canonical (`employment.apply_voice`), then the career is
   re-validated; revision +1. Otherwise the scripted line stays (`reason`).

`reason` values: `replayed`, `nothing_to_voice`, `no_consent`, `not_configured`,
`unsafe_request`, `rate_limit`, `superseded`, and the guard reasons below.

## Guardrails

Everything from the AI-characters spec (player text as quoted data, redaction, no numbers
outside the facts, no state-change claims, no "I am an AI", length/sentence caps, timeout →
scripted), plus:

- Context sent: posting (org, title, stage, culture, wage range as the only salary numbers),
  the interviewer card, the CV (strength names, claim lines), the question, the picked
  answer and its note, a goal and a tone. Never the score, never the player's name (it is
  replaced by the address word before sending).
- `promise` — lines that promise hiring or money (`nhận em luôn`, `được nhận`, `trúng tuyển`,
  `chắc chắn đậu`, `tăng lương`, `thưởng thêm`, `lương sẽ…`, `điểm của em`, "you're hired"…)
  fall back.
- `not_a_question` — a follow-up must contain `?`.
- Abusive replies are never sent; the scripted rude-reply reaction stands and the rule
  applies −3.
- Personal data: replies are redacted before they are stored or sent; the prompt tells the
  interviewer never to ask for phone numbers, addresses or ID papers.

## Client (public/js/v4/views.js `stepCard`, `jbSend`; public/css/app.css hiring section)

- Option buttons use `data-action="v4JbAnswer"`. AI on → `POST /api/ai/interview` queued
  behind `api.queue` (same ordering as commands), 409 retried once, network failure falls
  back to the plain command; AI off → the plain command.
- One exchange at a time: the latest answer's note or the owner's reaction, the follow-up
  bubble, then the reply form (textarea `maxlength=200` + live counter, **Bỏ qua**, **Gửi**,
  a hint listing the point rules) or the reply + reaction + points chip. The next question
  appears once the follow-up is answered or skipped.
- Phone first (390 px), theme tokens only (`--surface-2`, `--good-soft`, `--bad-soft`, …),
  reuses `.bubble`, `.ai-badge`, `.typing` from the chat.

## Tests

`tests/test_employment_interview.py`: each rule and the clamps, overclaim needs the record,
redaction; follow-up placement (never after the last question, ≤2), auto-skip, one reply,
validation of replies; bounded score effect (+5/−5 on the same answers) and the reference
cap still winning; trial reactions (Chú Tư), customer-care interview → test, teacher and
office interviewers, a one-question interview; tampered `talk` rejected; `apply_voice` only
rewords the same scripted line once; NPC interviewers go through `persona_reply`
(`purpose='interview'`), others through the local card; guard fallbacks (promise, invented
salary, not a question, breaking character), no consent, timeout; the HTTP route with a fake
LLM (voiced question and reaction stored with canonical, AI wording never changes the
score, bad output kept scripted, rude replies and skips never reach the provider, trial
reaction, no consent, budget, validation/CSRF, revision conflict).
