# Xin việc cho thêm bảy nghề (hiring for more careers)

## Goal

The owner: pharmacy, customer care, tour guide and the hired trades (salon, pet care, repair, delivery)
should also go through hiring before the first shift, like the teacher and the three office careers.

| Career | What the player goes through | Who decides |
|---|---|---|
| `pharmacy` | **exam** "Chứng chỉ Nhân viên quầy thuốc" → CV → interview | cô Thu, người phụ trách Quầy Bình An |
| `tour_guide` | **exam** "Thẻ hướng dẫn viên khu phố" (neighbourhood knowledge + group safety) → CV → letter → interview | anh Hải, điều phối Công ty Lữ hành Mây Lang Thang |
| `customer_care` | CV → letter → interview → **situational test** with a difficult customer (role-played by the shift lead) | chị Mai, trưởng ca Trạm Lắng Nghe |
| `salon` | CV → **trial** (làm thử tại tiệm) | chị Phượng, chủ Salon Tóc Gió |
| `pet_care` | CV → **trial** | chị Nhàn, chủ Pet Care Mèo Mập |
| `repair` | CV → **trial** | Chú Tư, Tiệm Sửa Đồ Chú Tư |
| `delivery` | CV → **trial** (one practice run) | chị Hạnh, điều phối bưu cục Giao Nhanh Mây Chiều |

Scope: `game/employment.py`, new `game/employment_content.py` (postings, questions, exams), the job-application
sheet `jobView` in `public/js/v4/views.js`, a marked section at the end of `public/css/app.css`,
`tests/test_employment_*.py`. Engine/journey/tests outside that list are untouched; the lines they need are in §7.

## 1. The pipeline is data

Every posting may carry `stages`, an ordered list. Postings without it (teacher, office) keep the old
`('cv', 'letter', 'interview')` and their scoring is byte-for-byte the same.

| Stage | Action | Content key on the posting | Notes |
|---|---|---|---|
| `exam` | `job_exam {question, option}` | `exam` (career id of the exam) | 5 questions drawn from a bank (seeded by career, attempt and day), one right answer each, pass mark 4/5. Skipped when the career's certificate is already held. |
| `cv` | `job_cv` | `wants` | unchanged |
| `letter` | `job_letter` | – | unchanged |
| `interview` | `job_answer` | `questions` | unchanged |
| `test` | `job_answer` | `test` | scenario steps, same shape as interview questions |
| `trial` | `job_answer` | `trial` | hands-on steps at the shop, same shape |

`job_answer` accepts a question only when it belongs to the **current** stage and the application is still
`applying` (this also closes an old gap: after a lucky direct offer the interview could still be answered).
When a stage's last step is answered the application moves to the next stage; after the last one it is scored.

**Exam.** Answer key and explanations are not sent in the bootstrap content; after grading, `public()` adds
`exam_review` (your pick, the right option, why) so the result card can teach. Pass → a certificate
`job.certs[] = {id, day, score}` is kept for good (also after quitting or a rejected interview), so
re-applying skips the exam. Fail → application closed, status `rejected`, retake from the next day
(`cooldown_day = day + 1`), a different draw next time.

**Scoring** (0–100, offer from 60 as before). Answer points (interview + test + trial, max 3 each) weigh 55,
the letter 25 and matched strengths 20 — the old formula. Pipelines without a letter: answers 80, strengths 20.
Lying on the CV still caps the score at 40 when the posting checks references.
Some test/trial options are marked `fatal` (touching a live fan, forcing a scared cat under the dryer, riding
through a flood, snooping in a customer's phone, snapping back at an abusive caller): the score is capped at
45 and the owner says why. That is the "hands-on" part: one unsafe move fails a trial however polite the rest was.

**Luck.** A boss's direct offer can still skip CV/interview/trial, but never a licence exam: pharmacy and
tour guide only get lucky offers once the certificate is held. Bosses of the new postings are named people
with their own wording ("Chú Tư", "chị Hạnh"…).

## 2. Postings and wages

Measured with the test helper (3 good tasks a day): pharmacy's fund earns ~80–140 xu/day, customer care
~190, tour guide ~160–260; teacher ~200 plus a 35–90 salary. The trades earn 20–40 xu per service minus
supplies and rent.

Decision (no double pay):
- **Desk/service careers** (pharmacy, customer care, tour guide) are paid like the teacher: task pay keeps going
  to the workplace fund, plus a modest daily wage that the journey moves to the wallet
  (`salary_to_wallet`). Wages sit below the teacher's and far below office jobs.
- **Hired trades** (salon, pet care, repair, delivery) get a small **base wage** (15–28 xu) and the shop's
  takings keep going to the shop fund as today. The wage is what makes "being taken on" feel real,
  not a second income.
- Because the journey treats every job that needs hiring as "làm thuê", these workplaces now cost no idle
  upkeep and cannot be paused (`journey._employed` = `employment.required`). That matches the story: you
  work at someone else's shop, the owner pays the rent.

| Career | Posting id | Org | Title | Wage xu/day | Probation | Wants | Stages |
|---|---|---|---|---|---|---|---|
| pharmacy | `ph-day` | Quầy thuốc Bình An | Nhân viên quầy thuốc (ca ngày) | 40–55 | 3 | careful, calm, communication | exam · cv · interview |
| pharmacy | `ph-evening` | Quầy thuốc Bình An · ca tối | Nhân viên quầy ca tối (bán thời gian) | 32–42 | 2 | careful, patience | exam · cv · interview |
| customer_care | `cc-station` | Trạm Lắng Nghe | Nhân viên chăm sóc khách hàng | 38–52 | 3 | communication, calm, patience | cv · letter · interview · test |
| customer_care | `cc-hotline` | Trạm Lắng Nghe · tổng đài ca tối | Nhân viên tổng đài (bán thời gian) | 30–40 | 2 | calm, patience | cv · interview · test |
| tour_guide | `tg-company` | Công ty Lữ hành Mây Lang Thang | Hướng dẫn viên tour phố | 38–55 | 3 | communication, teamwork, learning | exam · cv · letter · interview |
| tour_guide | `tg-collab` | Mây Lang Thang · cộng tác viên cuối tuần | Hướng dẫn viên cộng tác | 30–42 | 2 | communication, learning | exam · cv · interview |
| salon | `sl-assist` | Salon Tóc Gió | Thợ phụ gội sấy | 18–26 | 2 | patience, communication, creative | cv · trial |
| salon | `sl-color` | Salon Tóc Gió · bàn màu | Thợ phụ màu (học việc) | 20–28 | 2 | careful, creative | cv · trial |
| pet_care | `pc-groom` | Pet Care Mèo Mập | Phụ tắm sấy thú cưng | 16–24 | 2 | patience, calm, careful | cv · trial |
| pet_care | `pc-kennel` | Pet Care Mèo Mập · khu lưu trú | Chăm chuồng lưu trú | 15–22 | 1 | patience, careful | cv · trial |
| repair | `rp-apprentice` | Tiệm Sửa Đồ Chú Tư | Thợ phụ học việc | 18–26 | 2 | careful, tech, learning | cv · trial |
| repair | `rp-phone` | Tiệm Sửa Đồ Chú Tư · quầy điện thoại | Thợ phụ sửa điện thoại | 20–28 | 2 | careful, tech | cv · trial |
| delivery | `dl-rider` | Giao Nhanh Mây Chiều | Tài xế giao hàng khu phố | 15–24 | 2 | calm, careful, communication | cv · trial |
| delivery | `dl-evening` | Giao Nhanh Mây Chiều · ca tối | Tài xế ca tối (bán thời gian) | 14–20 | 1 | calm, careful | cv · trial |

Probation pays 85% as before; the day's wage is paid only if at least one job was finished that day.

## 3. Content

`game/employment_content.py` holds the postings, the interview/test/trial questions (prefixed ids, same
`{text, options[{id,label,score,note,fatal?}]}` shape so `question()` finds them) and the two exam banks
(9 questions each, `{text, options[{id,label}], answer, why}`). Exams test procedure and safety only —
read the code, lot and expiry; never give a dose; ask about other medicines; privacy; storage; lost visitor;
crossing a busy road; heat; the game's own landmarks (Lối Bờ Mây closes in rain, the three-leaf vase…).

## 4. Save compatibility and validation

- New job field `certs` (list). Older saves without it stay valid (`validate` treats it as optional,
  code uses `.get`).
- Application may carry `exam = {qs, answers, score, passed, attempt}`.
- `validate` is stricter: stage must exist; while `applying` it must belong to the posting's pipeline;
  answers must be questions of the posting with valid options; exam questions must come from the bank, the right
  count, unique, answers only for drawn questions; a certificate must be a known exam of this career with a
  sane day/score.

## 5. Migration: nobody who already worked there is locked out

`employment.migrate(s)`: for every career that now needs hiring, if the save had **started** it (or finished
work there) and the job record was never used (`status == 'none'`, no application, empty history), the
record becomes `hired_record(...)` — signed, no probation, the posting's top wage — and exam careers get their
certificate. Idempotent; a player who later quits has a history row, so they are never silently re-hired.

It runs before the `start_day` gate: `engine.migrate_state` calls `emp.migrate(s)` right after
`cst.migrate(s)` (so both `apply_action` and `public_state` see the migrated record).

## 6. UI (jobView)

- Posting cards show the pipeline as small steps ("📝 Thi chứng chỉ → 📄 CV → 🤝 Phỏng vấn"), the wage
  note for trades ("lương cứng; tiền công tiệm vẫn vào quỹ tiệm") and "✓ Đã có chứng chỉ" when held.
- While applying: a stepper (done / current / next) at the top of the sheet.
- Exam: "Câu 2/5" + progress bar + pass mark, one question card, full-width answer buttons.
- Trial: the owner's line in a speech bubble, "Bước 1/3 · Làm thử tại tiệm", the owner's reaction to the last step.
- Test: the customer's line in a bubble, "Tình huống 1/3".
- Result card: exam score vs pass mark (and each question ✓/✗ with the reason), or the hiring score
  bar /100 with the last feedback lines, the next step and the retake day.
All colours from theme tokens; laid out for a 390 px phone.

## 7. Changes outside the employment files

- **engine.py** — one line in `migrate_state`, after `cst.migrate(s)` (CRLF kept):
  `emp.migrate(s)  # xin việc: nơi đã làm trước khi cần tuyển dụng thì coi như đã ký hợp đồng`.
- **tests/test_accounts.py** (`test_login_replaces_save_and_two_devices_share_it`): the second device's
  own progress is now played on `florist` instead of `pharmacy` (pharmacy needs hiring on a fresh save;
  the test checks device separation, not the career).
- **tests/test_journey.py** (`Wallet.test_reopen_paid_by_wallet_or_free_when_stuck`): no longer starts and
  pauses `delivery` to build the "nowhere else to work" situation — delivery is a hired job now (no upkeep,
  cannot be paused) and an unhired delivery already is not "somewhere else to work". The rule under test
  (free reopen when stuck) is unchanged.
- Optional polish in `app.js` (not done): the empty-state card says "Gửi CV, phỏng vấn, nhận thư mời rồi
  đi làm." for every hired career; trades could read "Làm thử một buổi với chủ tiệm rồi nhận việc.".
