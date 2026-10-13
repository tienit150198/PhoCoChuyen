# Service careers: read-only expansion audit

Scope: 18 careers, local checkout only. No product code, database, deployment, or saved game changed. Evidence lines refer to this checkout. Proposed packages below are **new sellable work units**, not claims that every underlying action is new. Related actions already present are explicitly acknowledged.

## Shared evidence and design constraints

- Plugin level is `1 + xp // 90` (`game/careers/kit.py:154-155`); day difficulty bands are days 1–2, 3–5, 6–9, 10+ (`:375-377`). These are different gates and must not be conflated.
- Inventory buy guards enforce catalog `unlock` (`game/inventory.py:954`, `:1231`, `:1301`); FIFO stock consumption returns recorded cost (`game/careers/kit.py:174-177`). Merely adding a paid catalog item will not make existing task generators request it.
- Completion has a separate `bonus_base` for margin-based equipment bonuses (`game/careers/kit.py:144-147`). Keep reimbursements, deposits, COD and client budgets out of earned margin.
- Recommended entitlement: career-specific paid package + existing skill/day requirements + required gear/capacity + successful practical assessment. Do not buy away safety, identity, allergy, consent, or quality checks. Gate generation and server commands as well as UI.
- Preserve old task `GEN`/`FIXED` contracts; add new versioned variants, migrate only missing defaults, never regenerate existing jobs against a new catalog. Deterministic generation must consider owned services and available capacity before offering a payable job.
- Existing career amounts are mostly 6–85 xu, whereas the convenience unlock ladder is 3,000 / 9,000 / 30,000 / 100,000 / 350,000 / 1,200,000 / 4,000,000 / 12,000,000 / 35,000,000 / 100,000,000. Applying the ladder to unchanged wages would create extreme payback times. Example: 3,000 / 20 net = 150 jobs before counting time or consumables. This report does not assert those prices are balanced for services.
- For all proposals, A/B/C mean increasing work and commercial value, **not** the first three ladder nodes. Suggested prototype economics using each career's median successful current-job net `B`: A revenue 2.5B, direct cost 0.5B, net 2B; B revenue 6B, cost 2B, net 4B; C revenue 15B, cost 6B, net 9B. Target work time approximately 1.5x / 2.5x / 4x the baseline. These are hypotheses for simulation, not observed figures. For employed roles use project bonus, employer-funded tooling and staff time rather than charging applicants/customers; for babysitting `B` is per full day, not per subtask. For household work client procurement budgets are separate from pay. Equipment amortization, refund reserves and staff wages must be added before final pricing.
- Calibrate unlock payback from **incremental net per active minute**, acceptance probability and capacity; not from gross revenue. A/B/C across all 18 can occupy selected ladder nodes, with remaining nodes providing distinct services, not multipliers. No recommendation here to deploy or alter the agreed convenience ladder.

## 18 explicit career audits

### 1. customer_care

Evidence: `game/desk.py:27` base pay 55 xu; `:170-172` adds 5 per task tier and applies grade share. `game/desk_content.py:1286-1288` opens guide/wrong/lost day 1, double/window/fraud/angry day 2, VIP/takeover/viral day 3, threat day 4. Existing dossier work checks identity, evidence, implementation and closing; classic tasks also remain (`game/engine.py:2384`, `:2528`). No physical premium-stock catalog to extend honestly.

- A: **Split-order reconciliation service**: three parcel IDs, partial delivery quantities, one replacement reservation; assemble evidence matrix, calculate remaining entitlement, execute replacement once and verify receipt. New linked order work rather than another lost-order story.
- B: **Subscription billing repair**: month-by-month invoices, cancellation effective date, prorated credit, next-bill verification. Consume a paid sandbox/verification credit; issue authorization-limited adjustment and wait for the next simulated billing result.
- C: **Enterprise incident recovery desk**: linked cases across several accounts, incident grouping, batch remedy approval, individual notifications and sample verification; pay milestone bonus only after affected accounts reconcile. Capacity and specialist coordination costs, not a huge one-click refund.

Seam: new case builders/`CASES` in desk_content, explicit dependencies and result evidence in desk.py; carry service entitlement into generation. Preserve classic/new desk routing and callback SLA behavior.

### 2. tour_guide

Evidence: `game/tour_trip.py:31` base fee 70; `:677-688` adds saving bonus and settles reaction. Museum ticket 6, market 2, cafe 3 (`:35`, `:43`, `:51`); tickets use group fund, overspend may reach guide wallet (`:446-448`). Existing group travel begins day 3 (`:305`, `:310-322`); walking routes, weather, rest, head counts and multi-day group care already exist.

- A: **Night audio-history walk**: rent/count receiver kits, test channels, book two timed entries, manage hearing/access preferences, recover all equipment and reconcile deposit.
- B: **Accessible craft-and-tasting circuit**: book ramp-equipped transport, verify entrances and vendor slots, track signed-off dietary portions, handle a lift outage by rebooking equivalent accessible service. More than a generic rest stop.
- C: **Corporate learning excursion**: parallel workshop groups, transport manifests, vendor deposits, regroup deadlines, joint attendance reconciliation and supplier invoice settlement.

Seam: versioned trip package beside PLACE/route constraints and group state; new reservation/asset manifests. Do not inflate guide earnings by counting the travelers' entire fund as sales.

### 3. repair

Evidence: phone labor 30 (`game/careers/repair.py:73-74`); compatible screen cost 22/sale 38 and genuine screen cost 40/sale 62, unlock level 2 (`:242-243`); motor unlock level 3 (`:249`). Return-unrepaired check fee 10 (`:36-37`). Part guards `:1283-1284`; completion `:1500`. Existing phone/fan/cooker/bike/headphone/laptop diagnosis, quote consent, used-part tests and warranty are already substantial.

- A: **Mechanical keyboard rebuild**: new switches/stabilizers; per-key matrix test, isolate failing rows, replace selected switches, tune stabilizers and certify full-key test.
- B: **Robot vacuum overhaul**: lidar module, wheel encoder, filter/seal stock; diagnose map drift vs drive fault, pair sensor calibration, leak/dust path check, mapped-room acceptance test.
- C: **Studio projector optical rebuild**: costly optical/lamp module; log dust pattern, test color channels, replace approved module, align image geometry and run heat-soak before warranty handover.

Seam: DEVICES/FAULTS/TESTS/ITEMS plus device-specific bench stages, quote and warranty state. New safety and calibration actions require UI/server work, not data-only item additions.

### 4. delivery

Evidence: `game/careers/delivery.py:750-765` fee = 8 food / 10 parcel + 2 per map-distance, rain +5, fragile +2, late -4; `:840` pays fee, not COD value. Coldpack costs 3, strap costs 2 and unlocks level 2 (`:95-96`). Load max 20kg and COD cap 250 (`:63-64`); stock gate `:1248-1249`. Existing chilled/fragile/oversize deliveries, weather and redirects already exist.

- A: **Sealed legal-document round trip**: numbered seals and receipt sleeves; verify named recipient, record custody transfers, collect signed original and deliver it back before final payout.
- B: **Calibrated chilled-food route**: insulated crate and temperature logger; precondition crate, read logger at pickup/each stop, manage exposure budget and segregate spoiled units. Adds actual temperature evidence beyond existing coldpack use.
- C: **Scheduled fragile exhibition transfer**: reusable foam cases, shock indicators, two-person loading; condition photographs/manifest, capacity reservation, delivery appointment, unpack acceptance, return hired cases.

Seam: new ORDERS flags, manifest/return leg/quality telemetry under run state; route scheduling and packaging stock. Preserve COD hand-in separation and road safety.

### 5. homestay

Evidence: room prices 28–48, breakfast 12, guide 8 (`game/careers/homestay.py:3503`); linen cost 4, towel 2, amenities 1 (`:114-116`). Lake room unlock level 3 (`:52`, guard `:734-735`). Existing reservations, breakfast, cleaning, room maintenance and anniversary care must not be relabeled premium features.

- A: **Workation room package**: rent monitor/router UPS stock, test desk power/Wi-Fi, configure requested work hours and track equipment return; add equipment inspection after checkout.
- B: **Private craft weekend**: reserve instructor/material kits and breakfast slots, stage participant workstations, reconcile attendance and finished kits; manage room and workshop capacities together.
- C: **Whole-property retreat contract**: rooming list plus breakout timetable, supplier deposits, room-turnover waves and group departure audit. Charge accepted contract milestones and reconcile damages/deposits separately.

Seam: reservation/calendar and room-capacity engine with package subjobs; reusable gear ledger and consumable lots. Existing room-rate/OTA settlement must not double-book package revenue.

### 6. pet_care

Evidence: grooming small 18/medium 24/large 32/cat 22; boarding dog 20/cat 16 (`game/careers/pet_care.py:3053-3054`). Sensitive shampoo cost 2 and conditioner cost 2 unlock level 2 (`:142-143`); window cat pen level 2 (`:68`); eligibility `:809`. Existing temperament, medications per instruction, adoption, vaccination and boarding care are already represented.

- A: **Cooperative-care training visits**: target mat/clicker/low-allergen rewards, record consent to each handling step, reward voluntary approach and stop below stress threshold; owner receives a reproducible care plan.
- B: **Specialist double-coat deshedding**: undercoat tool/filter stock, divide coat into zones, track skin check and tool-pass count, control dryer heat and stress, verify coat condition before return.
- C: **Long-stay enrichment suite**: independent quiet-space reservation, puzzle kits and individually portioned diet, daily activity/weight/intake logs, rest days, owner-approved changes and final multi-day report.

Seam: grooming step tables, boarding occupancy and longitudinal owner/animal records. Add work/stock genuinely specific to packages; medical escalation remains available regardless of purchase.

### 7. salon

Evidence: cut 30/color 60/bleach 70/toner 25/treatment 35 (`game/careers/salon.py:49`); dye costs 6, developers 2–3, keratin 8 (`:134-145`). Existing retail shampoo cost 12/sale 25 (`:148`) demonstrates premium stock is already present. Existing consent, patch-test gating (`:1514-1520`), zone processing, appointments and retouches are not new content.

- A: **Precision curl-shape service**: curl-pattern consultation, dry section mapping, individual curl cutting, shrinkage prediction and symmetrical dry check; dedicated styling stock.
- B: **Tape-in hair extensions**: new length/weight/color stock, strand compatibility test, section/weight map, bond placement, pull comfort check and scheduled maintenance.
- C: **Custom hair-system fitting**: cap measurements, custom ordered hairpiece deposit, fitting session, hairline blending, attachment practice and take-home maintenance stock; supplier lead time and rework risk.

Seam: SERVICES/PRICES/ITEMS plus new fitting stages and multi-visit bookings; do not simply raise color price or resell existing keratin treatment.

### 8. garbage

Evidence: route base 14 + 3 per stop (`game/careers/garbage.py:54`, `:936`), clean recyclable bag earns 2 (`:53`, `:965`); gloves 2 and mask 1 consumed per shift (`:58`, `:85-86`). Cart compartment caps 8/8/10 and hazard cap 8 (`:49-50`); weather day 2, wedding waste day 3 (`:103-105`). Hazardous items and unusual waste already appear.

- A: **Booked electronics collection**: labeled crates, device serial manifest and battery separation; confirm collection ownership and documented transfer to authorized processor. Revenue is pickup fee, not fictional valuable scrap yield.
- B: **Apartment recycling-quality contract**: reusable weighing bins, building sampling plan, contamination tags, repeated resident feedback, weighed acceptance receipt at processor.
- C: **Festival waste station operation**: pre-position color stations, schedule attendants and cart trips, track peak fill/contamination, clean site and reconcile processor weights before event contract settlement.

Seam: route stops/bag model and dump receipts, add mass/custody and capacity contracts. Existing wedding-event dialogue is not this full event service.

### 9. drain

Evidence: sink 15, main pipe 35, manhole 45 (`game/careers/drain.py:65-67`); night list-price multiplier 150% (`:49`); siphon cost 6/gloves 2 (`:101-103`). Five bike tool slots (`:48`), day/weather/kind generation (`:475`, `:491`), quoted bill `:962`. Camera diagnosis, gas measurement and high-pressure unclogging already exist.

- A: **Documented pipe survey**: locator beacon and marked plan; trace line, measure lengths/depth, annotate camera defects and deliver customer-accepted map. Sell reporting deliverable beyond current camera check.
- B: **Grease-trap maintenance contract**: replacement seals/filter media, isolation, staged collection into measured containers, safe disposal manifest, flow test and next-visit schedule.
- C: **Trenchless liner repair**: measured liner/resin kit and rented curing equipment; diagnose suitable segment, quote measured material, prepare pipe, cure with timer/temperature, inspect and load-test. Complex specialist gameplay with a real reject/referral path.

Seam: CALLS/PLACES/TOOLS/ITEMS and new measured-job substages; guarded quotation and accepted extra scope. Keep confined-space controls obligatory.

### 10. homemaker

Evidence: cook pay 22, market 18, ordinary cleaning 16, Tet 30 (`game/careers/homemaker.py:58`); customer discount/refund rules `:60`; day/variant gating `:103-106`, daily planner `:116-151`. Client market budget is real task evidence, e.g. 40 with ingredients priced 3/4 (`game/careers/homemaker_content.py:168-171`), not shop profit. Existing separate dietary portions, elder care and Tet work already exist.

- A: **Five-day meal-prep service**: plan portions across days, consolidate shopping, batch cooking, dated container labels and reheating handover; consume premium reusable containers/labels while reconciling client grocery budget.
- B: **Household move-in setup**: inventory cartons, create room map, stage essential first-night items, reconcile missing items and set maintenance calendar; packing/label stock and paid helper time.
- C: **Managed multi-home domestic schedule**: negotiated weekly scope for several households, key/access ledger, substitute-helper briefing, expense reconciliation and quality visits. Earnings for completed managed work, no idle automatic cash.

Seam: content V()/step builders and PAY, but long-lived client plans need new state. Keep expense advances and home assets separate from the worker's money.

### 11. nail

Evidence: regular polish 8, gel 15, extension 20, French 4, flowers 5, stones 4 (`game/careers/nail.py:95`); gel bottles cost 8, tips 3, LED bulb 6 (`:77`, `:88`, `:93`). Orders unlock days 1–4 (`:125-157`); pool filter `:420`; curing times and lamp strength `:43-51`. Bridal tips/extensions/stones already exist.

- A: **Magnetic cat-eye design**: new magnetic pigment and magnet tool; layer thickness, magnet angle/distance, repeatable pattern placement and curing per nail.
- B: **Sculpted builder-gel set**: builder stock/forms, fit each form, build apex and length, check sidewalls/stress point and cure; distinct from current preformed tips.
- C: **Custom reusable press-on commission**: client sizing impressions, detachable nail blanks, multi-session art proof, fitting tray, adhesive kit and labeled replacement sizes; charge deposit and completed approved set.

Seam: service/ART tables, dose stock and per-nail state. Premium purchase never overrides infection referral or sanitation.

### 12. photobooth

Evidence: strip 14/double 20/big 30 (`game/careers/photobooth.py:78`), papers 1/2/3 and frame 5, ink roll 8/24 prints (`:71-79`). Apprentice first 3 jobs (`:229`); day-1 fixed orders then min_day/mod pool (`:444-449`). Existing props, layouts, filters, framed prints and timed expressions already exist.

- A: **Lenticular motion keepsake**: multi-angle capture alignment, motion-frame selection, lenticular sheet stock, registration/trim check.
- B: **Mini photo-book commission**: contact-sheet selection, sequence/layout proof, premium paper/signature folding, binding stock and final page-order audit.
- C: **Portable event photo station**: location power/light assessment, backdrop transport, time-slot guest groups, branded approved layout, consumables planning and queue handling; reconcile event deliverables and rented kit.

Seam: package catalog plus new multi-shot/print-finishing substages and external venue setup. No new fee just for an existing filter/frame.

### 13. giupviec

Evidence: room base 12, regular bonus 4, Tet +6 (`game/careers/giupviec.py:69-71`), settlement room-count formula `:664`; cleaning bottle costs 3–4 (`:63-67`), bottle gives 12 wipes (`:72`). Day-1 first 3 jobs, then day/mod eligible pool (`:120-129`); room count expands by day tier (`:139-143`); practical apprenticeship gate `:258-260`. Existing top-down wiping and fragile-object care are not premium additions.

- A: **Upholstery extraction service**: fabric compatibility test, stain map, measured detergent, extractor passes and dryness/ventilation verification; new machine rental and extraction solution.
- B: **Post-renovation fine-dust clean**: HEPA bags, dust containment, surface-by-surface residue checks, staged cleaning so clean rooms do not recontaminate; contractor sign-off.
- C: **Multi-unit move-out turnaround**: key/room inventory, damage evidence before work, prioritized rooms across units, team assignment, consumables allocation and owner acceptance checklist.

Seam: HOMES/JOBS/SPOTS/products plus machine and completion measurements; expanded room lists alone would repeat existing work.

### 14. babysitter

Evidence: Bin full-day rate 70, Na 75, Sóc 85 (`game/careers/babysitter.py:70-75`); family gates day 2/3/4 (`:81-82`). Day total adds trust*4 and care bonus (`:1302-1309`), optional tip at handover (`:1326-1328`). Apprentice 2 (`:262`); existing allergies, activities, naps, household safety, handover and child-specific care already exist. Do not pay a full day's advanced wage for every care subtask.

- A: **School-pickup care session**: authorized pickup list, identity/password, belongings checklist, timed route and parent receipt; activity pack and transport cost.
- B: **Sibling coordinated-care session**: two children with independent meal/nap/activity timelines, split safe play zones, conflict mediation and individual handover reports; capacity cap and assistant when required.
- C: **Event childcare room**: pre-registered small group, caregiver ratio, child-to-guardian tokens, age-zoned materials, staggered snacks, emergency contact ledger and verified individual pickup.

Seam: family/plan/needs generation with multi-child state and explicit shift contract. New work expands supervision complexity, never monetizes relaxation of supervision or medical decisions.

### 15. hr_admin

Evidence: CV/timesheet/contract bonuses 25, interview 30 at day 2, case 20 at day 3 (`game/careers/hr_admin.py:665-669`); employment salary bands 55–80 and 50–70 (`:703`, `:708`). Shared generator filters min_day (`game/careers/office_work.py:859-875`) and reduces bonus for errors/heavy errors/hints (`:1001-1007`). Existing CV filtering, contracts, interview scheduling and employee cases are already implemented.

- A: **Employee onboarding dossier**: join-date checklist linking signed offer, equipment assignment, training booking and acknowledged policy; reconcile missing signatures before closing.
- B: **Benefits-enrollment reconciliation**: employee elections, effective dates, dependent documentation, payroll deductions and provider confirmation; batch import with individual exception queue.
- C: **Multi-site workforce rollout**: approved role plan, roster capacity by site, staggered onboarding/training, budget reconciliation, transfer exceptions and manager acceptance report.

Seam: FORMS/build functions into OfficeJob, new linked papers and work validators. Paid unlock is access to a specialist project track/tool training; employer pays operating costs and milestones. No fees charged to job seekers and no treating payroll total as player income.

### 16. secretary

Evidence: inbox 25/calls 20/letters 25, meeting 30 and prep 20 from day 2, case 20 from day 3 (`game/careers/secretary.py:731-736`); salary bands `:755`, `:760`; shared settlement `game/careers/office_work.py:1001-1007`. Existing schedules, letters, phone notes and planning already exist.

- A: **Controlled board-pack assembly**: collect versioned documents, match agenda to pages, mask restricted annexes, verify recipient permissions and distribution receipt.
- B: **Executive travel desk**: compare itinerary constraints, reserve transport/hotels against approval limits, recover from cancellation, reconcile receipts and unused deposits.
- C: **Shareholder/conference secretariat**: invitation eligibility, RSVP quorum, seating/resource plan, timed proceedings, resolution/action records and follow-up evidence.

Seam: new FORMS builders with shared paper/sequence interfaces; cross-document dependencies and revision/change events. Project bonuses and employer costs, not event attendee funds as profit.

### 17. it_helpdesk

Evidence: ticket bonus 25, fix/asset 20 from day 1; patch/access 25 from day 2; case 20 from day 3 (`game/careers/it_helpdesk.py:604-609`); salary bands `:628`, `:633`; common error/hint deductions in OfficeJob `:1001-1007`. Existing network patching, account permissions, assets and phishing scenarios are already present.

- A: **Backup restoration acceptance**: choose approved restore point, validate checksum/sample files in sandbox, compare missing files, get owner sign-off and close with evidence. Not just a ticket label.
- B: **Managed device rollout**: approved image/license stock, hardware manifest, staged provisioning, encryption key escrow, policy verification and user acceptance; failure returns device to repair queue.
- C: **Small-office migration project**: dependency map, test cohort, scheduled cutover, rollback checkpoint, mailbox/file permission comparison and post-cutover checks; rented lab/cloud capacity and project milestones.

Seam: new FORMS/builders and multi-stage task state, not destructive real-system actions. Simulated execution must produce verifiable outputs. User data never becomes sellable stock.

### 18. laundry

Evidence: material/catalog gates already include silk day 4, wool/waterproof day 10, curtains/tablecloth day 20, hotel towels/room linens/heirloom fabrics day 40 (`game/careers/laundry.py:21-35`). Generator uses day eligibility and 2–4 garments (`:65-70`). At day 1, quantity 2: cost=4, net=16, gross=20 (`:88-93`); completion pays net+cost, deducts cost once and bonuses only net (`:166-167`). This is an explicit pass-through model to preserve.

- A: **Structured suit care**: intake measurements and interfacing check, specialist cleaning process selection, shaped pressing forms, sleeve/lapel restoration and final dimensional check; special carrier/cleaning consumables.
- B: **Down sleeping-bag restoration**: shell/fill inspection, measured down detergent, controlled rinse/dry cycles, fill-loft redistribution and moisture check; oversize machine scheduling.
- C: **Beaded bridal-gown preservation**: photograph bead map, test hidden seam, protect detachable ornaments, sectional stain treatment, form drying, acid-free packing and signed preservation inventory.

Seam: ORDERS/MATERIALS/OPTIONS/STAINS plus measurement/protection/packing state; new specialist stages and machine limits. Do not propose hotel linen, silk or wool as absent premium content: all are already present.

## Economy and implementation handoff

## Full ten-tier content mapping

Ordered T1→T10; unlock prices respectively 3k, 9k, 30k, 100k, 350k, 1.2m, 4m, 12m, 35m, 100m. This is the requested **content mapping**, not a claim that existing wages support those prices. Root design owns final economics. The three detailed anchors above supply the core new-work mechanics; higher rows must be expanded into bespoke deliverables and dependencies, never repeat the same task with a multiplier. Names that touch existing themes mean the stated new contract/deliverable, not purchase-gating existing baseline actions. Employer awards apply to customer_care and office roles.

| Career | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 |
|---|---|---|---|---|---|---|---|---|---|---|
| customer_care | Split-order quantity reconciliation | Recurring-delivery schedule repair | Linked warranty entitlement dossier | Subscription proration and next-bill check | Accessibility accommodation fulfillment | Cross-store exchange settlement | Approved product-recall outreach cohort | Shared incident with account-specific remedies | Service migration continuity plan | Enterprise incident recovery and closure audit |
| tour_guide | Night audio-history walk | Printmaking studio visit with kit return | Bicycle route with rental condition ledger | Accessible craft-and-tasting circuit | Stargazing excursion with equipment/weather fallback | Photography expedition with location permits | School discovery circuit with activity stations | Artisan residency with multi-day project delivery | Multi-venue cultural delegation itinerary | Corporate learning excursion with parallel workshops |
| repair | Mechanical keyboard rebuild | Game-controller drift calibration | Sewing-machine stitch/tension repair | Robot-vacuum sensor overhaul | Camera lens aperture/alignment service | Espresso machine pressure-system refurbishment | Vintage amplifier channel restoration | Custom home-cinema device integration and acceptance | Music studio equipment restoration project | Projector optical rebuild with calibrated commissioning |
| delivery | Sealed-document return route | Made-to-measure clothing fitting-and-return courier | Rental instrument custody transfer | Logged chilled-food route | Timed wedding-cake case delivery | Exhibition mounting-kit pickup and return | Event consumables replenishment schedule | Film-location equipment manifest rounds | Store-opening staged fixture delivery | Fragile exhibition transfer with unpack acceptance |
| homestay | Workation monitor/UPS package | Telescope evening stay with equipment checkout | Artist easel room with material kit | Private craft weekend | Family genealogy weekend with archive-room booking | Cycling camp with secure gear wash/storage | Writing residency with room/studio allocations | Small film crew location-stay contract | Visiting workshop series with rotating instructors | Whole-property retreat with breakout timetable |
| pet_care | Cooperative-care training visit | Scent-enrichment session with owner log | Carrier acclimation course | Double-coat deshedding service | Harness fitting and walking-skills handover | Individual feline climbing/enrichment room | Senior pet low-impact activity plan from owner/vet instructions | Multi-pet household transition visits | Relocation boarding with custody/transport preparation | Long-stay enrichment suite and multi-day care report |
| salon | Precision curl-shape service | Barber beard contour consultation | Hairpiece trim and fit | Tape-in extension installation | Custom color-matched extension ordering | Theatrical wig setting and continuity record | Braided protective-style commission | Editorial shoot hair continuity service | Bridal party trial-to-event styling schedule | Custom hair-system fitting and maintenance plan |
| garbage | Booked electronics collection | Restaurant glass color separation route | Cardboard pickup with measured baling | Apartment recycling-quality contract | Reusable cup return and sorting station | Campus furniture reuse inventory collection | Market organics segregation and processor transfer | Venue packaging recovery contract | Multi-building renovation waste transfer plan | Festival waste stations and final weight reconciliation |
| drain | Documented pipe survey | Floor-drain trap seal replacement and odor verification | Rainwater filter basket installation | Grease-trap maintenance contract | Downpipe network flow-balancing inspection | Small restaurant drainage retrofit | Courtyard rainwater diversion commissioning | Apartment stack maintenance with resident scheduling | Heritage-property low-disruption drainage renewal | Trenchless liner repair and post-cure inspection |
| homemaker | Five-day meal preparation and dated packing | Pantry purchase-cycle and expiry plan | Family wardrobe inventory and seasonal rotation | Household move-in setup | Guest-week logistics and room/meals schedule | Home-maintenance vendor appointment coordination | Extended family holiday hosting project | Two-household caregiver handover plan | Seasonal residence opening/closing operation | Managed multi-home domestic schedule and quality visits |
| nail | Magnetic cat-eye design | Chrome-powder sealed finish | Layered translucent watercolor nail art | Sculpted builder-gel set | Custom inlay and encapsulated-art set | Fitted replacement-nail library | Trial-to-event nail wardrobe | Stage-performance quick-change nail collection | Luxury gift press-on collection with fitted sizes | Custom reusable press-on commission with proof and fitting |
| photobooth | Lenticular motion keepsake | Accurate ID-photo proof sheet | Transparent-overlay souvenir card | Mini photo-book commission | Stop-motion photo flipbook | Mat-mounted portrait triptych | Approved branded event photo template production | Mobile group portrait studio | Multi-day guest book with consent-linked portraits | Portable event station with kit and deliverable reconciliation |
| giupviec | Upholstery extraction service | Mattress surface extraction and moisture check | Venetian blind dismantle/clean/reinstall | Post-renovation fine-dust clean | Stone-floor protection test and finish | Small office after-hours cleaning plan | Short-stay property linen/room turnover contract | School-holiday room reset project | Furniture-storage move-in cleaning coordination | Multi-unit move-out turnaround and owner acceptance |
| babysitter | Authorized school pickup session | Library activity outing with guardian approval | Child travel packing and supervised journey handover | Sibling coordinated-care session | Holiday craft-day plan with age-separated materials | Visiting-family acclimation care plan | School-break multi-day activity program | Wedding rehearsal/event childcare schedule | Residential retreat childcare team rota | Event childcare room with individual verified pickup |
| hr_admin | Linked onboarding dossier | Probation review evidence pack | Employee training enrollment and completion reconciliation | Benefits-enrollment reconciliation | Internal transfer handover dossier | Workforce skills matrix with validated evidence | Seasonal hiring cohort onboarding | New-site policy rollout and acknowledgements | Multi-company benefits transition project | Multi-site workforce rollout with manager acceptance |
| secretary | Controlled board-pack assembly | Versioned approval-circulation dossier | Visitor delegation protocol package | Executive travel desk | Minutes-to-action evidence tracker | Supplier meeting and sample evaluation logistics | Annual leadership calendar with dependency review | International delegation itinerary and document coordination | Multi-venue conference secretariat | Shareholder/conference proceedings and resolution follow-up |
| it_helpdesk | Sandbox backup restoration acceptance | Approved printer-fleet profile rollout | Meeting-room AV commissioning checklist | Managed device provisioning rollout | Shared-drive permission migration | Multi-factor enrollment support campaign | Branch network commissioning and asset acceptance | Office platform migration with rollback rehearsal | Merger workspace integration project | Small-office migration with verified cutover and post-checks |
| laundry | Structured suit care | Pleated garment shape preservation | Outdoor technical-shell reproofing after label check | Down sleeping-bag restoration | Leather-trim textile specialist coordination | Theatrical costume condition/repair ledger | Boutique uniform pickup-to-return contract | Museum loan textile cleaning coordination | Wedding wardrobe restoration and storage project | Beaded bridal-gown preservation and signed inventory |

For T7–T10 the paid work unit is a project spanning distinct intake, procurement/booking, execution, exception resolution and acceptance tasks. Save project progress across days. Outsourced skilled work remains an expense and requires a verifiable handover; it does not become an instant completion button.

### Group economy notes

Physical shops (repair, salon, nail, photobooth, laundry): use actual purchased lot costs, reusable-equipment amortization, machine/seat/time capacity and rework reserve. Mobile services (delivery, garbage, drain, giupviec, tour): account travel, site time, equipment return and third-party disposal/admission; custody funds are liabilities. Accommodation/care (homestay, pet_care, babysitter): pay over occupied nights/shifts, enforce capacity and staff ratios, do not mint revenue for every repeated care click. Office/household services (customer_care, homemaker, hr_admin, secretary, it_helpdesk): separate client/employer budget from fee/bonus; tools are access/capacity purchases, not compulsory fictional inventory for every task.

Before implementation, record baseline active seconds/job, successful net/job, actions/job and failure/refund rate for each career. For each new package show purchase fee, consumable/outsourced costs, duration, gross, expected net, capacity and expected payback in the purchase panel. Test generator eligibility, stock exhaustion, capacity collisions, cancelled work, retry/double-submit, saved old tasks and margin-only bonuses. No balancing simulation or implementation has been performed in this audit.
