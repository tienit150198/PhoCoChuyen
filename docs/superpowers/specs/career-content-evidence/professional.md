# Professional/public-service career expansion audit — 18 careers

Read-only design audit, 2026-10-13. Repository: `D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410`. No product code, deployment, or database changed. All source references below are repository-relative with exact current line numbers. New examples are proposals, not existing features or real professional advice.

## Common design contract

The agreed nominal paid-skill price ladder for ten NEW content tiers is 3,000 / 9,000 / 30,000 / 100,000 / 350,000 / 1,200,000 / 4,000,000 / 12,000,000 / 35,000,000 / 100,000,000 xu. Do not silently convert existing free duties into paid access. Keep advanced work as a separate purchase + qualification track. The three detailed examples per career below are ordered A → B → C; they describe new work, not renamed existing tasks. The ten-tier catalog at the end expands these into concrete project labels; root owns final economy calibration.

Suggested qualification shape: A requires a paid training/workbench package plus clean foundational assessments; B additionally requires successful A work on several different days plus a scenario assessment; C additionally requires audited B work and a capstone. Charge for training/workbench capability, not authority, access to victims, treatment priority, blessings, or a guaranteed outcome. Exact prices, skill thresholds, and work fees need the parent economy design; no numbers here claim to be balanced.

Higher income must be awarded after verified new deliverables, with distinct per-contract/task awards and a stated payer. Avoid buying a permanent multiplier on all old easy tasks. Existing wages are often only 40–140/day and task bonuses 5–30; purchases in millions are not supportable by merely adding 5 xu. Measure incremental net income, task duration and expected payback for each new tier before choosing prices. Preserve baseline salaries, existing free content, and salary-cap semantics while designing a separate advanced-contract ledger.

Public-service payer = employer/agency/project budget; recipient care, rescue, police service, and pagoda visits/blessings stay free. Do not reward arrests, fines, rescues counted, medical interventions counted, or manufactured urgency. Valid prevention, safe cancellation, escalation and refusal of unsafe work must also count as successful paid work.

## 01 accounting — Góc Sổ Xinh

- Existing money: recurring bookkeeping client cô Hoa has fee **80 xu**, with other clients 70/75/85 (`game/engine.py:2170`–2173). Quality shares are 100/75/40/0% (`:2180`). These are actual bookkeeping service fees, not values on an invoice exercise.
- Existing gate/content: ongoing-client track starts at earliest day 2 (`game/engine.py:2184`–2185), staggered clients and five-day accounting months (`:2167`, `:2170`–2173); source follow-up waits for promised arrival (`:2323`). Existing checks already cover duplicate receipts, personal expenses, rounding and cash matching (`:2176`). Core dossier factory is `game/content.py:127`, accounting branch `:161`.
- A NEW: **Marketplace payout reconciliation**: reconcile order-level sales, platform fees, returns and one combined bank settlement; output a receivable bridge. Mechanic: many orders → one payout, with timing differences. Accounting office pays for accepted reconciliation.
- B NEW: **Seasonal cash-runway plan**: map dated receivables, committed payments and minimum cash; compare a delayed-customer scenario and schedule affordable purchases. Mechanic: multi-day cash timeline with bounded assumptions; accounting office pays for a complete forecast, not a favorable result.
- C NEW: **Multi-location bookkeeping handover**: normalize two stores' opening balances, map account codes, identify duplicated opening balances and deliver a reconciled migration pack. Mechanic: versioned source mapping + opening/closing invariants. Employer project allowance on acceptance.
- Safe seam: separate versioned advanced dossier builders beside `content.make_task`; recurring-contract state beside `_ac_fresh`/`_ac_case` in `engine.py`, with explicit new IDs rather than altering AC_CLIENTS fees or old generated keys. Keep accounting-school educational topics separate from actual commissioned work.

## 02 teacher

- Existing money: lesson award = **45 + 5×stars + up to 10 for understanding + 5 patience bonus + grade pay step** (`game/teach_lesson.py:616`–619); paid through task completion (`:705`–706). Classroom market-math activity already pays 20 (`game/classroom.py:36`).
- Existing gate/content: higher grades unlock at career levels, then principal offer/player choice (`game/teach_grades.py:24`–27, `:42`, `:422`–425). Existing advanced grades already add 5 xu/grade. Classroom events are month/year gated (`game/classroom.py:445`–462), and already include field trip, parent meetings, science, arts, fire drill and observed lessons. Do not sell those again.
- A NEW: **Six-session targeted learning plan**: diagnose a fictional pupil's misconception, choose exercises, revisit an exit ticket later, then revise plan. Mechanic: persistent baseline/intervention/retest evidence. School-funded completion award; no charging children for essential support.
- B NEW: **Accessible lesson-material studio**: produce matching print, large-print and audio-supported versions of a new lesson; check equivalent goals and accessible assessment. Mechanic: transform one objective into different material constraints, then test usability. School resource-development contract.
- C NEW: **Inter-school assessment moderation**: calibrate anonymized sample work against a rubric, reconcile two graders and audit feedback consistency. Mechanic: disagreement resolution + rubric evidence; no buying grades. School-network project award.
- Safe seam: new multi-session activity IDs in `classroom.ACTIVITIES` (`game/classroom.py:36` onward) plus distinct persistent project state; use `teach_lesson.reward_for` only for existing lesson pay. Respect grade-room compatibility described in `teach_grades.py:8`–13; validate new state separately from existing 0–200 lesson reward bound (`teach_lesson.py:1213`).

## 03 corp_accounting

- Existing money: first employer salary **75–100/day** (`game/careers/corp_accounting.py:2813`); dossier performance pay is adjusted for deadlines and actual errors (`:1537`–1554).
- Existing gate/content: basic accounting certificate required for new story-mode entrants; grandfathered worked/hired saves retain access (`game/accounting_jobs.py:6`–19, `:35`). Certified shift check is 2/3 correct (`:38`); salary x3/x5 capped 600 (`:37`, `:99`–108). Five-day work schedule already covers invoices, journal, bank reconciliation, ageing, petty cash, inventory, depreciation, trial balance and close (`corp_accounting.py:78`–82).
- A NEW: **Production job costing**: attribute material issues, labor and machine overhead to work orders, distinguish unfinished goods and calculate completed-unit cost. Mechanic: quantity/cost flow across stages. Employer costing-project award.
- B NEW: **Construction-in-progress capitalization pack**: reconcile project invoices and commissioning records, split eligible asset costs from expense and transfer completed components. Mechanic: evidence-tagged capitalization with dates and roll-forward invariants.
- C NEW: **Accounting-system migration rehearsal**: map legacy account codes, run trial import, resolve rejected records, reconcile control totals and produce rollback/acceptance documentation. Mechanic: deterministic import-validation cycle rather than another journal quiz.
- Safe seam: `KINDS` + `GENERATORS` + `make_task` (`:1320`), separate new gen/version and immutable source docs; preserve legacy serial branch (`:1321`) and task validator (`:1878`). Extend milestone system without increasing required legacy milestone count silently. Awards through `_finish`, not invoice asset value.

## 04 tax_payroll

- Existing money: payslip 30, transfer 20, VAT 25, year-end 25 bonuses (`game/careers/tax_payroll.py:489`–494); grid settlement accounts for errors and deadlines (`:1107`–1111). Salary **60–85** (`:2256`).
- Existing gate/content: payslip/transfer/question day 1; VAT/calendar day 2; year-end day 3 (`:489`–491). Grid staff count grows with days (`:581`); new errors enter days 3/4/8 (`:705`, `:707`, `:725`). This career is not in the two-career certificate mapping (`game/accounting_jobs.py:35`).
- A NEW: **Retroactive salary amendment**: recompute only affected months after an approved pay change, compare already-paid values and create an auditable difference payment. Mechanic: effective-date recalculation, not simply another current payslip.
- B NEW: **Split assignment and benefit allocation**: apportion one employee's work between two cost centers without double-paying benefits or tax withholding. Mechanic: allocation matrix + unique-person reconciliation under fictional rule cards.
- C NEW: **Payroll-provider transition**: reconcile year-to-date earnings, deductions and leave balances between old/new providers, find duplicate employee IDs and approve a trial payroll. Mechanic: parallel-run reconciliation with privacy-safe export. Employer-funded project fee.
- Safe seam: new `FORMS` builders (`:489`) and advanced selection before normal pool (`make_task :987`), plus dedicated project state. Retain existing rule-card disclaimer, source-backed answer checking, calendar/claim handling and versioned legacy branch. Never equate transferred payroll funds with player income.

## 05 group_accounting

- Existing money: group accountant salary **90–120** (`game/careers/group_accounting.py:2291`), actual dossier award `max(0, base+deadline adjustment)` (`:1220`–1234). Accounting-school salary cap/multipliers apply as above.
- Existing gate/content: vn_business certificate plus daily 2/3 knowledge check (`game/accounting_jobs.py:35`–38). Five-day quarter schedule (`group_accounting.py:79`–85), six close milestones (`:64`–65). Already includes intercompany matching, sales/profit/dividend elimination, FX translation, consolidated worksheet, NCI, PBC and variance; those are not new packs.
- A NEW: **Business acquisition opening pack**: compare purchase consideration with identifiable net assets, map opening fair-value adjustments and produce a fictional acquisition reconciliation. Mechanic: acquisition-date worksheet distinct from periodic NCI.
- B NEW: **Change of ownership without loss of control**: reconcile before/after ownership, equity transfer and NCI movement using an explicit fictional policy card. Mechanic: time-varying ownership ledger, not static percentage multiplication.
- C NEW: **Group cash-flow consolidation**: map subsidiary cash flows, eliminate internal cash movements, separate FX movement and reconcile opening/closing cash. Mechanic: graph of intra-group flows + reconciliation invariants.
- Safe seam: `GENERATORS :1096`, `make_task :1112`, `FIXED :89`, `validate_task :1461`. New schema/IDs avoid mutating deterministic old matching boards. Do not present TT99-related proposed calculations as verified current law; use internally complete educational rules.

## 06 pagoda

- Existing money: explicit allowance **yard 6, kitchen 8, ceremony 10 xu**, setup 0 (`game/careers/pagoda.py:50`–52). Existing policy explicitly does not cut modest allowance for mistakes. `_end` selects allowance (`:549`–557), completion pays once (`:584`).
- Existing gate/content: day-one curated plan (`:78`); variants filtered by min_day, daily modifier and no duplicates (`:81`–90); setup first slot (`:224`–241). Existing content includes yard, hall, visitor guidance, vegetarian kitchen, donation accounting, listening, ceremonies, care and incidents (`pagoda_content.py:382`–387).
- A NEW: **Reusable community-kitchen logistics kit**: forecast portions from registrations, reconcile pantry stock and distribute leftovers safely according to scenario cards. Mechanic: forecast/stock/dispatch quantities across one event, not a normal cooking task.
- B NEW: **Heritage preservation inventory**: photograph/catalog fictional historic objects, assign condition flags and arrange qualified conservation review. Mechanic: condition comparison across visits and chain of custody; no player restoration of sacred objects without oversight.
- C NEW: **Flood-shelter coordination at the pagoda**: organize accessible sleeping areas, volunteer shifts, donated goods and family reunification records across several simulated days. Mechanic: capacity/resource planning plus safeguarded handover.
- Income/purchases: pagoda is an exception to mandatory paid-skill gates. New scripture/archive/community-project experiences unlock through demonstrated experience; books and personal equipment may be optional paid purchases. Successful real work may receive a stated modest temple/community-project stipend. Visitors, worship, rituals, blessings and shelter remain free; donations stay in the charitable ledger, never player revenue. No donation-to-wallet or profit multiplier. Preserve existing no-deduction allowance policy.
- Safe seam: new variants and step schemas in `pagoda_content.py`, selectors `_eligible`/`_day_plan`, new project-kind allowance separate from existing `PAY`, immutable `_key`/`needs` (`pagoda.py:244`).

## 07 library

- Existing money: task allowance **8 desk / 10 catalog / 8 room / 12 archive**, archive certificate supplement 3 (`game/careers/library.py:55`–58). Ward allowance completes via `:434`–454. Reader fines/card fees are institution money, not suggested player income.
- Existing gate/content: archive requests min-day filter (`:303`–307); archive training must be answered correctly (`:1032`–1041), and archive decision requires training (`:1065`). `archive_craft` certificate provides allowance; non-story fallback day 6 (`:56`–58, `:125`). Already has borrowing/return/recommendation, cataloging, room rules, archive copying/privacy and preservation basics.
- A NEW: **Community oral-history catalog**: verify narrator consent, index recording segments, separate public/restricted metadata and publish a finding aid. Mechanic: consent-scoped metadata, not another archive-copy request.
- B NEW: **Digital preservation ingest**: verify file checksums, name/version files, find corrupt copies and test restore from a second copy. Mechanic: integrity manifest + recovery verification.
- C NEW: **Inter-library loan network**: choose available lending institution, reserve transit capacity, track due dates and resolve a delayed return without duplicate reservation. Mechanic: multi-institution state machine. Institution/project-funded awards.
- Safe seam: `MAKERS :318`, `make_task :321`, content tables and training state; add digital-project schemas without mixing new fees into fines or ordinary public access.

## 08 pilot

- Existing money: new flight award **random 8–20 + 2 if full** (`game/careers/pilot.py:404`–411); salary **85–110** (`:1455`). Completion safety/error adjustments at `_park :985`–1022.
- Existing gate/content: day 1 normal/technical flights; later storm/fog/medical deck (`:414`–423). Existing content already covers fuel reserves, alternate/divert, defects, weather, stabilized approach and go-around. Daily flights vary 2–5 after first day (`:399`–401).
- A NEW: **Cargo loading and balance endorsement**: load pallet positions, respect compartment limits and compute center-of-gravity envelope from supplied fictional aircraft data. Mechanic: spatial weighted balance, not just fuel amount.
- B NEW: **Multi-leg duty planning**: build a legal-in-game crew/duty and fuel plan across several legs, allow a maintenance interruption and choose a safe stop. Mechanic: time/resource graph across flights.
- C NEW: **Simulator instructor debrief**: observe a trainee's recorded approach sequence, mark actual deviations and create a targeted retraining session. Mechanic: evidence-based trace review with assessed trainee recovery.
- Income: operator-paid advanced mission or instructor fee after accepted work, including safe cancellation; never speed or unsafe landing bonuses. Safe seam: new endorsement/mission builders beside `make_task :466`; preserve legacy bonus and `on_task` behavior, explicit new fixed facts/public fields and `validate_task :1340`.

## 09 flight_attendant

- Existing money: task base bonus **8 xu** (`game/careers/flight_attendant.py:47`); salary **65–85** (`:1494`); actual finish at `:1097`–1112.
- Existing gate/content: day 1 boarding/demo/service, day 2 difficult passenger, day 3 medical (`:455`–470). Existing service already includes dietary requests, cabin safety, turbulence, medical and conflict handling; do not resell generic service or first aid.
- A NEW: **Cabin inventory handover**: reconcile sealed carts, special-meal allocation and returned stock between legs; identify seal/temperature exception from fictional cards. Mechanic: conservation of inventory and evidence-backed handover.
- B NEW: **Connection-disruption assistance desk**: match affected passengers' connection needs, accessible routes and authorized airline options, then produce a verified handoff. Mechanic: constraint matching across passenger groups; no making immigration/legal promises.
- C NEW: **Cabin crew training assessment**: assign trainee roles in a scripted evacuation simulation, evaluate communication/checklist trace and write debrief. Mechanic: team coordination review, not live emergency farming.
- Income: airline task/instructor awards. Safe seam: new `KINDS`/builders under `make_task :579`, explicit action/stage handlers `ACTIONS :1141`, validators `:1387`; retain turbulence interruption and no-physical-action restrictions.

## 10 oil

- Existing money: work-permit task **15 xu**, round/drill 10, shore 0 (`game/careers/oil.py:55`); salary **110–140** (`:1688`).
- Existing gate/content: rotation phase selects outbound/wait/home/stay tasks; later days add drill (`:117`–135). Existing tasks already include induction, toolbox talk, permits, isolation/gas checks, rounds, muster/drill, storm securing and handover. Not a blank platform for generic safety-training upsells.
- A NEW: **Vibration-trend inspection**: compare repeated pump measurements, identify trend versus transient sensor fault and request maintenance. Mechanic: time series and corroborating readings, no dangerous operational instructions.
- B NEW: **Spare-parts criticality plan**: rank failures from downtime/safety evidence, choose an inventory within budget and plan replenishment lead time. Mechanic: constrained inventory decision with documented tradeoffs.
- C NEW: **Shutdown maintenance coordination**: schedule compatible jobs around shared isolation boundaries and crew availability, then validate staged handback. Mechanic: dependency graph and conflicting permits under supplied simulation rules.
- Income: employer specialist-project awards; safe stops remain rewarded. Safe seam: `plan_of :117`, task factory `:321`, new content beside `oil_content.JOBS :136`; version new schedules and keep existing rotation/fatigue, stop-work, permit validation mandatory.

## 11 railway

- Existing money: train handling base **10 + 2×crowd + capped push complexity + late/second-train extras** (`game/careers/railway.py:59`, `:273`); salary **62–80** (`:1388`).
- Existing gate/content: first slot shift setup; patrol from day 2 in selected conditions (`:109`–114). Existing work already includes barrier equipment, readback, waiting crowds, pushy passersby, second train, line patrol and defect reporting.
- A NEW: **Crossing inspection trend report**: compare repeated barrier timings/fault logs, separate duplicate reports and propose maintenance priority. Mechanic: historical anomaly tracking, not a single fault checklist.
- B NEW: **Temporary engineering possession plan**: allocate a fictional maintenance window between movements, assign verification roles and reconcile release acknowledgements. Mechanic: time-window scheduling with strict stop conditions; never buy override authority.
- C NEW: **Multi-crossing disruption exercise**: coordinate communications and handovers for two affected crossings with unavailable equipment. Mechanic: distributed acknowledgement board and conflict-free reopening.
- Income: railway employer project/assessment award independent of train throughput. Safe seam: `make_task :188`, content tables, new plan kinds and state; keep closure/readback/interlocks checked in server action handlers and actual completion `:1054`.

## 12 nurse

- Existing money: task base **10** (`game/careers/nurse.py:50`) plus salary **55–72** (`:1540`); completion `:1131`.
- Existing gate/content: triage from day 2, procedure preparation/discharge from day 3 (`:137`, `:147`). Already has vital signs, medication checks/holding, bells, triage, procedure preparation and discharge education.
- A NEW: **Shift continuity reconciliation**: reconcile care-plan tasks, outstanding tests and follow-up ownership across shifts, flag omitted handover items. Mechanic: cross-shift dependency ledger, not repeat discharge questions.
- B NEW: **Ward infection-prevention audit**: inspect fictional environment/checklist evidence, cluster process failures and produce an improvement plan. Mechanic: sample audit + measurable follow-up, no incentivized interventions.
- C NEW: **Discharge coordination conference**: schedule equipment, caregiver teaching and referral appointments for a fictional multi-need patient, then confirm safe handoff. Mechanic: multi-party resource/consent constraints distinct from existing bedside discharge checklist.
- Income: hospital salary supplement/project award after assessed work; no selling treatment priority or charging patients for safety. Safe seam: `make_task :218`, `nurse_content` new tables and new state; preserve medication safety gates and validate actual competency before advanced tasks.

## 13 lighthouse

- Existing money: dawn/weather 8, sea 14, supply 6, dusk 10 (`game/careers/lighthouse.py:53`); salary **66–84** (`:1554`).
- Existing gate/content: day 1 dawn/weather/visitor/dusk, day 2 sea, later extra work (`:137`–146). Supply starts day 3 then every 7 (`lighthouse_content.py:357`–358). Already includes light faults, weather, maritime radio assistance, visitor access, fuel/supply and isolation wellbeing.
- A NEW: **Backup-power endurance plan**: calculate fictional battery autonomy from load and capacity sheets, choose safe maintenance sequence and verify reserve. Mechanic: energy budget over time, distinct from topping up fuel.
- B NEW: **Optical performance survey**: compare logged visibility/inspection readings, distinguish weather loss from optical fault and prepare a calibration request. Mechanic: multi-source signal diagnosis with no unauthorized lamp alteration.
- C NEW: **Regional beacon continuity exercise**: plan coverage while one neighboring beacon is unavailable, coordinate authority notices and verify restoration acknowledgments. Mechanic: coverage map + multi-station state.
- Income: maritime authority project award, never a fee to boats in distress. Safe seam: `plan_of :137`, `make_task :274`, separate authority/project state; keep existing light-character, visitor permissions and safety-zeroing reward (`:415`) intact.

## 14 rescue

- Existing money: **10/call** (`game/careers/rescue.py:41`) plus **52–68 salary** (`:1261`), actual award `:885`.
- Existing gate/content: case pools expand day 1/day 2/full later (`:134`–139). Already includes doubtful/prank calls, geolocation, caller calming, selecting units, pre-arrival instructions and several simultaneously ringing lines (`:158`–169). Simple multi-call triage is already implemented.
- A NEW: **Duplicate incident fusion**: link several calls describing one event without discarding a separate nearby incident; preserve caller-specific hazards. Mechanic: entity resolution with merge/split evidence.
- B NEW: **Agency mutual-aid resource board**: manage unit availability, travel delays and confirmed handoffs across neighboring dispatch centers. Mechanic: persistent resources with acknowledgement, distinct from choosing teams on one call.
- C NEW: **Communications-outage exercise**: switch to fallback records/radio, reconcile delayed updates and restore one authoritative incident timeline. Mechanic: eventual reconciliation and conflict resolution after outage.
- Income: agency readiness/project awards; help stays free and no pay-per-casualty/per-rescue escalation. Safe seam: `make_task :178`, `_fresh_board` state, new content; preserve response urgency, safety guards and actual completion checks.

## 15 lifeguard

- Existing money: **10/task** (`game/careers/lifeguard.py:52`), **50–66 salary** (`:1679`); rescue/watch, lessons, aid and storm closure already pay via finish (`:793`, `:995`, `:1181`).
- Existing gate/content: day 1 easy equipment fault, later potential stop faults (`:136`–146); lessons from day 2 (`:150`–157). Already includes pool chemistry checks, gate screening, water rescue, child bands/lessons, first aid and thunderstorm evacuation.
- A NEW: **Inclusive swimming session plan**: allocate lanes, assistants and rest stations from individual fictional needs, verify capacity and consent. Mechanic: simultaneous accessibility/capacity constraints; training may be purchased, rescue never charged.
- B NEW: **Event water-safety staffing plan**: map blind spots and rotations for a sports event, test coverage while one staff member is occupied. Mechanic: coverage optimization with relief scheduling.
- C NEW: **Facility near-miss investigation**: connect anonymized observation logs, equipment issues and crowd patterns, implement a prevention change and re-audit. Mechanic: causal evidence/retest across days.
- Income: facility-funded advanced work award; avoiding incidents counts as success. Safe seam: `make_task :214`, new `lifeguard_content` tables/state, preserve pool closure thresholds and no reopening until safety checks pass.

## 16 police

- Existing money: **10/task** (`game/careers/police.py:72`), existing ring case **30** (`:1505`), salary **55–72** (`:2072`).
- Existing gate/content: calls/disputes/child day 2, talks/posts/inspection day 3 (`:137`–140); ring cases from day 4 (`police_content.py:1152`). Already contains stolen/lost-property return, family reunification, mediation, patrol, scam education, online posts, inspection and ring cases. Do not claim investigation itself is new.
- A NEW: **Evidence-custody audit**: reconcile sealed item IDs, sign-out/return entries and authorized access; flag a broken custody link. Mechanic: append-only custody trace, not guessing guilt.
- B NEW: **Event accessibility and safety plan**: assign clearly marked pedestrian routes, accessible exits and liaison roles, then adapt to a blocked route. Mechanic: crowd-route constraints under proportionate safety rules, no monetized permits/enforcement.
- C NEW: **Cross-case fraud-pattern analysis pack**: connect redacted reports by verified indicators, distinguish coincidence and produce a supervisor-reviewed referral. Mechanic: confidence-based graph with false-positive review; no reward for accusing more people.
- Income: agency training/project award only. Safe seam: `make_task :277`, new immutable case kinds in content and supervisor handoff, preserve privacy/evidence checks and completion `:1533`; never link purchased rank to police authority or fines.

## 17 lawyer

- Existing money: task bonus **max(2, number of steps−1−failed steps)** (`game/careers/lawyer.py:100`), salary **50–75** (`:195`). Baseline five-step clean dossier therefore pays 4; daily salary paid when closing shift (`:108`).
- Existing gate/content: day 4 hearing, day 10 three cost items/cap/duplicate invoice, day 20 scope/conflict, day 40 final audit (`:46`–75); milestone requires 120 clean cases, 30 active days and clean task day ≥40 (`:105`). Existing 12 civil-service dispute cases already cover evidence/timeline/remedy/claim amount.
- A NEW: **Contract clause comparison**: compare three drafts, detect inconsistent definitions and align obligations with a client's documented requirements. Mechanic: version diff + clause dependencies, beyond selecting an existing dispute remedy.
- B NEW: **Licensing-rights chain dossier**: map author/owner/license grants and permitted uses, flag a missing permission and prepare a scope-limited recommendation. Mechanic: rights graph with explicit fictional rules.
- C NEW: **Multi-party settlement implementation plan**: reconcile agreed obligations, milestone evidence and releases across several parties; track performance without promising enforceability or outcome. Mechanic: dependency workflow after agreement.
- Income: law-firm accepted-work commission/project fee, separate from disputed sums or settlement proceeds. Safe seam: expand case schema beyond the tuple-based CASES (`:15`) into versioned builders beside `make_task :42`; preserve `_key`, sequential answer validation and explicit fictional-law disclaimer (`:29`).

## 18 post_office

- Existing money: task bonuses **5 normal / 6 fragile-collection-return / 9 three-parcel batch** (`game/careers/post_office.py:86`), reduced by mistakes with floor 4 (`:137`). Postage goes to the post-office ledger; bonus to player (`:145`). Salary **50–65** (`:246`).
- Existing gate/content: scenario min-day filter (`:28`); registered day 4, fragile day 10, pickup/returns day 20, three-item batch day 40 (`post_office_content.py:17`–29). Existing tariff already rounds weight by 500g, service, zone and oversize (`post_office.py:49`). Milestones 18 jobs/6 days, 65/20, 180/45+12 advanced (`post_office_content.py:40`–42).
- A NEW: **Cash-on-delivery reconciliation**: match collected funds, partial return, remit-to-sender and signed receipts while isolating held exceptions. Mechanic: custody of customer funds and batch reconciliation; collections never become player money.
- B NEW: **International-document precheck**: match a fictional destination's declared-content/document cards, identify missing fields and select authorized handoff. Mechanic: per-destination requirements; no asserted real customs law.
- C NEW: **Route disruption recovery desk**: reassign a stalled batch to capacity-limited routes, honor promised deadlines, issue traceable updates and reconcile delivery proof. Mechanic: constrained routing with persistent exceptions, beyond existing three-parcel classification.
- Income: postal employer contract/task award, not a share of customer postage/COD. Safe seam: scenario/content file plus `make_task :26`, new kind-specific builders with immutable answer keys, validation `:204`; do not change existing tariff answers or scenario tuple meaning.

## Cross-cutting implementation cautions grounded in this audit

1. Most task factories depend on `(day, slot, serial)` and regenerate immutable answers. A wallet purchase can occur after generation; never let current unlock state retrospectively change old tasks. Snapshot selected advanced pack/version on new tasks and validate against that snapshot.
2. Corporate/group/tax explicitly preserve legacy serial branches. Teacher has an existing second-generation grade layer. Keep those migration strategies, not a blanket regeneration of all pending work.
3. Fee-bearing examples in dossiers are not player earnings. This matters for payroll, donations, fines, cargo value, lawyer claims and postal postage/COD.
4. A common purchase record can be shared, but content/gameplay must remain distinct. Every tier above names a deliverable and an interaction; a catalog row plus multiplier is insufficient.
5. New public-service content needs error-sensitive assessment while safeguarding base access. Buying training does not replace skill checks or confer legal authority.
6. Source audit is local code evidence, not proof of current deployed behavior. No gameplay/economy simulations, production checks or tests were executed in this read-only design task.

## Ten concrete content tiers per career

Columns are T1→T10 in the agreed nominal cost order. These are compact NEW project briefs, not claims that content already exists. All professional income comes from employer/project allowances on accepted deliverables. Paid access alone never substitutes for prerequisites: require success in prior tier, a new assessed skill, and role-specific safety/accuracy criteria. Pagoda uses experience access and optional personal books/equipment purchases instead of obligatory payments for religious/community access.

| Career | T1 · 3k | T2 · 9k | T3 · 30k | T4 · 100k | T5 · 350k | T6 · 1.2m | T7 · 4m | T8 · 12m | T9 · 35m | T10 · 100m |
|---|---|---|---|---|---|---|---|---|---|---|
| accounting | Marketplace payout bridge | Gift-voucher liability roll-forward | Consignment stock ownership reconciliation | Membership-prepayment schedule | Seasonal cash-runway forecast | Project grant restricted-fund reconciliation | Franchise royalty evidence pack | Store-opening control-total migration | Multi-store chart-of-accounts mapping | Two-store books migration and audited handover |
| teacher | Six-session misconception intervention | Accessible large-print lesson conversion | Audio-description learning-material pack | Newcomer language-support sequence | Equivalent accessible assessment studio | Anonymous rubric calibration workshop | Two-class collaborative research unit | Learning-resource pilot with pre/post evidence | Peer-coaching observation and action cycle | Inter-school assessment moderation project |
| corp_accounting | Work-order material cost tracing | Labor-hour cost-center allocation | Machine-overhead absorption worksheet | Work-in-progress completion reconciliation | Construction-in-progress capitalization pack | Asset-component commissioning roll-forward | Lease-payment schedule under supplied game rules | Import rejection/control-total repair | Legacy chart mapping and trial conversion | Full accounting-system migration rehearsal |
| tax_payroll | Effective-date salary amendment | Retroactive deduction correction bridge | Paid-leave liability reconciliation | Approved benefit eligibility reconciliation | Two-cost-center assignment payroll allocation | Midyear merger employee-ID deduplication | Retroactive variable-pay true-up | Year-to-date provider opening balances | Old/new provider parallel-run exceptions | Complete payroll-provider transition pack |
| group_accounting | Acquisition opening evidence pack | Purchase consideration reconciliation | Acquisition fair-value adjustment roll-forward | Acquisition-date goodwill bridge under game rules | Ownership-change equity/NCI movement | Step-acquisition pre/post perimeter comparison | Disposal perimeter cut-off reconciliation | Group cash-flow mapping | Intra-group cash-flow elimination graph | Consolidated cash-flow and FX reconciliation |
| pagoda* | Community-kitchen registration forecast | Donated pantry stock trace | Accessible meal-distribution timetable | Oral-history consent catalog | Historic-object condition inventory | Scripture-edition metadata comparison | Archive digitization checksum manifest | Volunteer shelter shift roster | Family-safe shelter goods/records handover | Multi-day community shelter coordination |
| library | Oral-history consent metadata | Recording segment subject indexing | Public/restricted catalog export | File-format migration comparison | Digital-preservation checksum ingest | Corrupt-copy recovery verification | Digital collection version provenance | Inter-library reservation availability map | Transit delay/loan extension reconciliation | Network-wide inter-library loan project |
| pilot | Pallet station/load-sheet matching | Compartment structural-limit review | Center-of-gravity envelope calculation | Load change and fuel balance revision | Multi-leg crew-duty planning | Remote-airfield dispatch data audit | Cross-leg maintenance recovery plan | Recorded approach deviation annotation | Trainee retraining objective design | Simulator instructor assessment and debrief |
| flight_attendant | Sealed-cart stock handover | Special-meal count reconciliation | Galley temperature-exception evidence | Multi-leg cabin defect handover | Connection-disruption assistance plan | Accessible connection handoff coordination | Cabin-resource staffing allocation | Trainee briefing quality assessment | Simulated evacuation team-role evaluation | Instructor-led cabin simulation and debrief |
| oil | Pump vibration trend baseline | Sensor fault versus equipment trend review | Lubricant sample trend evidence pack | Equipment maintenance-priority ranking | Critical-spare stock optimization | Procurement lead-time contingency plan | Shared-isolation job dependency mapping | Crew/permit conflict detection | Staged shutdown handback verification | Full maintenance shutdown coordination project |
| railway | Barrier timing trend report | Repeated fault incident deduplication | Crossing inspection evidence sampling | Preventive-maintenance priority pack | Engineering window possession plan | Worksite release acknowledgement reconciliation | Neighboring-crossing outage communication plan | Temporary coverage staffing exercise | Conflicting release-message resolution | Multi-crossing disruption recovery exercise |
| nurse | Outstanding-task shift handover | Pending-test follow-up ownership map | Care-plan omission reconciliation | Patient belongings/consent transfer audit | Ward infection-prevention sample audit | Improvement-cycle reassessment | Home-equipment discharge readiness plan | Caregiver teaching confirmation schedule | Referral appointment/resource coordination | Multi-party discharge coordination conference |
| lighthouse | Backup-power load inventory | Battery endurance calculation | Reserve-power maintenance sequencing | Remote sensor consistency check | Optical performance trend survey | Weather-versus-optics fault comparison | Neighboring-beacon outage coverage map | Authority notice acknowledgement register | Multi-station restoration verification | Regional beacon continuity exercise |
| rescue | Duplicate-call same-incident linking | Nearby separate-incident split review | Caller hazard evidence merge | Incident identity correction audit | Mutual-aid unit availability board | Cross-agency arrival/handoff reconciliation | Unit-turnaround resource forecast | Fallback dispatch record synchronization | Conflicting delayed update resolution | Communications-outage recovery exercise |
| lifeguard | Accessible lane-session plan | Assistant capacity/rest-station allocation | Inclusive-session readiness assessment | Venue sightline/obstruction map | Event safety staffing coverage plan | Staff-relief rotation constraint exercise | Anonymized near-miss timeline analysis | Equipment/crowd evidence correlation | Prevention-change re-audit | Facility-wide near-miss improvement project |
| police | Sealed-item custody inventory | Authorized evidence access reconciliation | Broken-custody-link supervisor referral | Accessible event pedestrian route map | Event safety and liaison staffing plan | Blocked-exit contingency exercise | Redacted fraud-report indicator matching | Coincidence versus corroboration review | Cross-case false-positive audit | Supervisor-reviewed fraud-pattern referral pack |
| lawyer | Contract draft clause comparison | Definition-reference inconsistency repair | Milestone obligation clause mapping | Author/owner permission source register | Licensing-rights chain dossier | Scope-limited license exception report | Multi-party obligation dependency map | Settlement milestone evidence register | Conditional release evidence reconciliation | Multi-party settlement implementation plan |
| post_office | COD receipt-to-parcel matching | Partial-return collection reconciliation | Sender remittance exception pack | Fictional destination document precheck | Declared-content/document consistency audit | Cross-border handoff evidence pack | Disrupted-route parcel priority map | Capacity-limited alternate route assignment | Delayed delivery proof reconciliation | Route disruption recovery and close-out |

*Pagoda column amounts are reference positions in the shared catalog, not mandatory prices for temple activities. Use experience milestones for these ten projects; optional personal books/equipment may occupy appropriate shop price bands, with no income multiplier or access charge to visitors.

The three expanded anchors above are approximately T1, T5 and T10 for each career, with neighboring tiers forming distinct preparatory deliverables. Novelty is assessed against the inspected local task/content paths; a full implementation should additionally inspect shared certificate/education catalogs to avoid teaching-topic duplication, while retaining these new paid-work mechanics.
