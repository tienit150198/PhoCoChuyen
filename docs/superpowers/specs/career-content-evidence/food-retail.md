# Paid career content: food, retail and art audit (18 careers)

Read-only source audit, 2026-10-13. No product edit, deployment or database action. Source paths and line numbers refer to this checkout. All amounts below are **game xu**, never real currency. Existing values are evidence; proposed values are design inputs requiring economy review.

**Integration update:** the root design uses ten sequential paid tiers at 3k/9k/30k/100k/350k/1.2m/4m/12m/35m/100m. `food-retail-tiers.json` provides all 180 Vietnamese content labels, ten for each career. The first three map to the detailed A/B/C anchors below. Root per-career price profiles and gate rules supersede this audit's provisional numerical examples; none are claimed live-balanced. Large tiers are bespoke batches or actual multi-stage contracts. Root is introducing a typed price envelope for the legacy price-cap incompatibility.

## Shared findings and proposed purchase rules

The current stock model pays wholesale cost on purchase; consuming a lot returns its recorded cost for reporting, without charging it again (`game/inventory.py:946–978,804–814`). Opening stock has zero historical cost (`:773–775`), so use replacement cost for balance calculations. Supplier discounts, shipping, wastage, staff, gear and paid-day rules mean the examples below are not guaranteed final take-home income.

Three proposed paid content levels per career: **A = 3,000 xu + 10 good completed jobs; B = 9,000 xu + A + 30 good jobs; C = 30,000 xu + B + 80 good jobs**. For new art/farm multi-stage jobs, count delivered commissions/contracts, never individual clicks. These are permanent access purchases; they unlock named recipes/SKUs/services and their actual work. They do not grant stock, generate automatic money, replace the old free menu, or merely multiply rewards. Add each career's specific prerequisite below. Limit premium jobs initially to 1 A, 1 B and 1 C per paid day (three total), subject to ingredient availability and accepted bookings; tune after simulation. Costs in the examples are per completed unit/contract, separate from purchase fees.

The previous convenience tiers (3k,9k,30k,100k,350k,1.2m,4m,12m,35m,100m) are purchase-price context, **not a proven conversion rate for customer bills**. Do not force the tiny tea stall's glass price to 100m. Higher purchase tiers need broader authored collections, equipment/capacity and long contracts, with separately measured demand and payback. Even the proposed A/B/C fees are discretionary content spending: their payback from *incremental* margin could be long. The parent design should retain the user's economy intent rather than silently assume all tiers are affordable from base jobs.

Purchase state should be per career and server-authoritative: content ID/version, paid fee, purchase transaction ID and milestone snapshot. Charge once atomically with entitlement; idempotent retry, no staff/AI purchase, no refund-by-save-restore. Require cash for ingredients separately. A offered job's recipe, price and entitlement version must be snapshotted; do not change active jobs when a pack is purchased.

**Compatibility blockers:**

- `game/experiences.py:242,425` caps edited and saved price entries at 1,000. New clothing customer prices above that need explicit bounds/schema changes; simply adding PRICES rows fails validation. `:427` caps milk-tea ingredient unit costs at 20.
- `game/inventory.py:1543,1558–1559` limits lot unit cost to 10,000 and order cost to 1m; large future catalog values must check all transaction/bill/COD caps too. Clothing return-price cap is 100k (`game/careers/clothing.py:2476`), online label totals 1m (`:2446–2447`).
- `make_task(day,slot,serial)` usually has no ownership context. Enforce eligibility during server task setup and all consuming/serving actions, then persist the chosen content ID. Do not leak premium orders into baseline pure day-based generation or make saved tasks irreproducible. Keep existing `FIXED` and gen-version validation; migrate additive state with defaults. Relevant regenerating validation is `game/engine.py:1487–1507`.
- `kit.complete(..., bonus_base=...)` feeds engine settlement (`game/careers/kit.py:143–147`). Gear should use earned service margin rather than costly merchandise pass-through. Clothing already deliberately does that and removes markup from the bonus base (`clothing.py:764–783`); its recent wholesale increase was an intentional earnings nerf (`:56–57`). Preserve this policy.
- Do not copy stale prose prices: clothing situation text says dress260/cost115 (`:2620`) but live tables say265/170 (`:62,89`). Live catalog and actual settlement are authoritative.

## 1. mother_baby — Tiệm mẹ & bé

**Existing economy and gate.** Bunny costs36, sells75 (39 replacement margin), `game/content.py:56`; diaper60/cost34 and formula95/cost55, `game/careers/mother_baby.py:63–64`. The family-care corner opens day2 (`:46`); trust-dependent tips (`:67–71`), age, weight, formula stages and recalls are already implemented. Gifts have safety labels, budgets, returns and registry; do not resell those existing mechanics as new premium work.

**New paid content:** A, fitted baby-carrier sale, C170/R260/M90: compare printed age/weight eligibility, adjust strap diagram, demonstrate buckle order, check fit and hand over care card. B, convertible feeding-chair assembly, C380/R560/M180: select age-appropriate configuration, reconcile parts, assemble lock sequence, stability check and serial handover. C, travel stroller commissioning, C850/R1,250/M400: clarify folding/storage needs, select model, assemble wheels, test brakes and folding interlock, log serial/warranty. Extra gate: 10 safety-clean gift deliveries; B/C pass a product assembly practice. These are product services, not infant medical advice.

**Seam/risk.** Extend `giftshop.NEW_PRODUCTS/LABELS` (`game/giftshop.py:35–42`) with new distinct use groups plus assembly task states; keep family consumables in `mother_baby.py` separate. `giftshop.validate_task:1312` and public renderer need new states. Premium catalog R1,250 exceeds shared saved-price cap. Never treat formula upselling or more volume as premium progression.

## 2. pharmacy — Quầy Bình An

**Existing economy and gate.** Fictional labeled boxes cost8 (`game/content.py:79`); checked handover pays40 and referral25 (`game/engine.py:858–873`), not product retail revenue. Recurring pickup pays30 (`:1800`) and existing cold storage/recalls span `:1792–1808`; care starts from day2 (`:1812`). Three checks and proper handover/referral are the existing procedural gate.

**New paid content:** A, home first-aid kit packing, C24/R70/M46: match an authorized non-drug contents card, count sealed supplies, expiry sort, label compartments, verify recipient. B, home measuring-device setup, C85/R150/M65: match the device on an approved request, verify model/accessories, install battery, run manufacturer self-test, explain only its printed controls. C, clinic supply delivery contract, C180/R320/M140: reconcile multiple signed supply requests, partition by recipient, trace lots, pack seals, verify transport checklist and receipt. Extra gate: 15 clean verifications and no unresolved recall; supervisor-authorized request for B/C.

**Seam/risk.** Original engine career, not normal plugin: keep new task kinds outside the fixed P-01…P-06 medical-like box loop, implement server-known contents and settlement; `ensure_pharmacy` at `engine.py:429`, care actions `:1904`, validator `:2129`. Already-existing cold-chain checks cannot alone justify a new paid unlock. Price is service/supplies fee, never higher margin for risky advice; premium must not bypass mandatory checks/referral.

## 3. milk_tea — Trà Mây & Trân Châu

**Existing economy and gate.** Base milk tea30, topping5, flavor6, large+7 (`game/boba.py:28–29,335–338`): M milk+pearls35 before other modifiers. Ingredient milk4 and pearls2 (`game/extra_content.py:27,37`), plus cup pack4/20 (`boba.py:37`); batch yield means do not claim a simplistic exact six-xu actual cost. Skill tiers count cups, not XP: 0/3/10/18/28/40/55/72/92 (`:163–178`); ingredients already unlock through level5 (`extra_content.py:26–48`).

**New paid content:** A, roasted rice tea latte, C18/R58/M40: toast rice at a stop window, brew measured tea, strain, mix and seal. B, pandan layered milk tea, C30/R95/M65: cook pandan extract, cool separately, choose density order, pour three layers, check layer collapse. C, six-cup jasmine fruit tasting flight, C120/R260/M140: brew two strengths, split batch to six labeled preferences, coordinate chill and tray pickup, verify all labels. Extra gate: counter skill3/5/7 respectively; no ownership without basic skill.

**Seam/risk.** `boba.setup_task:474`, menu filtering `:269–300`, validator `:2412,2468`, base/flavor/topping catalogs. Premium recipes need a recipe ID and explicit batch states; a new topping alone is inadequate. Keep menu-off fallback and regular orders valid, correct actual yield costs, cup stock, allergies and reheating life. Ingredient cost cap20 requires multi-ingredient recipes or reviewed bound changes.

## 4. restaurant — Quán mì cay

**Existing economy and gate.** Base kimchi35; beef topping15/cost6; noodle cost3 (`game/careers/restaurant.py:65,72,2131`). Kimchi broth pack9 makes6 portions (`:51,68`); illustrative base+beef receipt50 before modifiers. Cheese broth unlock3, seafood4 (`:45,80`); actions enforce actual level (`:899,1056`). Group bowls, vegetarian, allergy, overnight stock and pots already exist.

**New paid content:** A, sesame miso noodle bowl, C26/R80/M54: toast/grind sesame, dissolve miso without overheating, choose separate allergen utensils, drain noodles and finish. B, braised short-rib noodles, C80/R190/M110: sear, batch braise, test tenderness, reserve portions and pair ready noodles with hot rib stock. C, seafood hotpot for four, C250/R520/M270: customer ingredient sheet, separated raw platters, broth stages, timed cooking per ingredient, individual sauces and whole-table check. Extra gate: hygiene A and ten consecutive clean food jobs; C requires pot capacity reservation.

**Seam/risk.** `BROTHS/ITEMS/ORDERS` (`:41,64,110`), make-task kind and group handling; add premium recipe variants with new preparation states. Do not repurpose existing `seafood` topping into a high-price reskin. Preserve hygiene hazards, patience and pack-to-pot yield; bill once per whole table.

## 5. cafe_bakery — Tiệm bánh & cà phê

**Existing economy and gate.** Croissant batch6 uses flour1,butter2,egg1 (`game/careers/cafe_bakery.py:121–122`), nominal inputs2+8+1=11 (`:198–200`), sells22 each (`:2842`):132 full-batch revenue before spoilage/packaging. Decaf level2, condensed and matcha3; bakes already include peach tart, salted-egg sponge, cookies, cakes (`:82–138`).

**New paid content:** A, espresso tonic, C18/R65/M47: extract shot, chill to target, measure tonic and ice, slow pour to avoid overflowing foam. B, pistachio macarons six-pack, C65/R170/M105: sift, whip meringue, fold to texture, pipe equal discs, rest surface, bake, pair/fill. C, opera cake commission, C210/R480/M270: bake thin layers, portion coffee syrup, alternate buttercream/ganache, chill each stage, cut exact portions, package with allergen card. Extra gate: barista/bake skill checks and six successful timing windows; C refrigerator space reserved.

**Seam/risk.** `DRINKS/BAKES/ITEMS`, oven/proof/cold storage and `SPEC.prices` (`:93–138,191–209,2840–2843`). New lamination/layering must not collide with sponge/cake branch. Batch cost must be allocated per sale, not charged both at mix and delivery. Nuts add distinct allergy validation.

## 6. florist — Tiệm hoa

**Existing economy and gate.** Red rose5 wholesale/14 retail (`game/careers/florist.py:127`). Existing wedding preorder240, deposit80, exact17-stem recipe (`:1748–1751`); existing funeral/opening/anniversary preorders and recurring subscription are already present (`:1752–1769`). Vase/carnation unlock2 (`:86,97`); day3 set orders (`:269–272`).

**New paid content:** A, preserved-flower glass dome, C75/R160/M85: condition dry stems, trim to dome clearance, arrange without water, secure base and seal dust-free. B, office living-wall panel, C200/R390/M190: survey light, select compatible plants, mount pockets, plan watering zones, load-test and label maintenance. C, freestanding floral event arch, C600/R1,100/M500: measure doorway clearance, ballast/support plan, hydrate modules, distribute stem weight, assemble safely and record venue signoff. Extra gate: 10 fresh, on-time orders; C two successful modular jobs.

**Seam/risk.** Existing order generation/GEN2 (`:165,314`), `FORMATS`, fresh-lot state, preorders; add installation-type state rather than reuse wedding bouquet. New dry/living materials have different ageing. C exceeds shared price cap and MAX_STEMS30 (`:48`); represent modules with bounded per-module stems, not unchecked giant arrays.

## 7. grocery — Tiệm tạp hóa

**Existing economy and gate.** Rice14/kg wholesale versus18/kg sale (`game/careers/grocery.py:86,103`), nominal margin4/kg. Gas voucher cost310 unlock2 (`:99`); generator filters item unlock by level (`:213`). Goods, age-restricted products, weighing, refunds, debt and shared till already exist.

**New paid content:** A, refill household-cleaner station, C45/R85/M40: identify allowed container, tare it, pump requested mass, cap/leak-test and attach batch label. B, chilled picnic box contract, C110/R220/M110: assemble dietary-labeled portions, separate cleaning goods, check dates, pack cold compartment and verify pickup slot. C, apartment move-in pantry contract, C300/R550/M250: inventory customer's list, substitute only with approval, reconcile multi-box counts, schedule floor delivery and sign off shortages. Extra gate: 10 correct scales/tills; B controlled cold storage; C successful delivery record.

**Seam/risk.** `ITEMS/PRICES`, generator `:188`, setup `:451`, GEN2 `:1256`, validators `:3153,3227`; contract kind can reuse till and stock. Refill changes units and must not mix grams with existing rice/produce scaling. Picnic food requires a genuinely new prepared-goods state, not plain basket text.

## 8. farm — Nông trại

**Existing economy and gate.** Tomato seed6, nominal yield6, sale12/kg (`game/careers/farm.py:101,140,152`):72 harvest revenue before inputs/loss/packing. Main cucumber unlock2/herbs3 (`:102–103`). **Also audit farm_plus:** existing strawberry, dragonfruit, mango, coffee, dairy cow/pig/duck, greenhouse350 and VietGAP450+15 grade-A lots already exist (`game/careers/farm_plus.py:60–93`); do not propose them as new.

**New paid content:** A, oyster mushroom grow bags, C35/R85/M50 per harvested batch: sterilized-substrate verification, spawn placement, humidity/airflow balance, harvest flush and grade. B, hydroponic microgreen trays, C90/R190/M100: seed density, nutrient mixing to target, light schedule, cut-height/tare and restaurant freshness label. C, grafted premium melon greenhouse contract, C240/R460/M220: graft alignment, healing humidity, train vine, pollination record, fruit thinning and sweetness/size grade. Extra gate: farm-plus level3/5/7; greenhouse for B/C, clean traceability for C.

**Seam/risk.** Use the separate farm-plus extension/store/level system, not shoehorn into base six beds (`farm_plus.py:171,285–310`). Real-minute crop clock, grade A/B, buyer constraints and storage capacity already differ from main farm day clock. No infinite unattended harvest; cost per planted batch and failed harvest remains a loss. Cross-career buyers are NPC contracts, not real stock transfer unless explicitly implemented.

## 9. clothing — Shop quần áo

**Existing economy and gate.** Ao dai cost285/sells420, margin135 (`game/careers/clothing.py:63,89`); blazer270/390, sneaker225/350 (`:74,80,91–92`). Expanded SKUs already exist and start0, unlocked by stocking rather than a paid model-license (`:69–84`). Existing fitting, alteration, outfits, returns, online orders and display are task kinds (`:196–198`); wish mechanic starts day2 (`:901–902`).

**New paid content:** A, pure-silk evening dress model, C780/R1,200/M420: measure bust/waist/length, select lining, inspect fabric grain and transparency, fit hem and steam at fabric-safe setting. B, wool tuxedo made-to-measure, C2,350/R3,600/M1,250: choose lapel/body shape, take independent chest/shoulder/inseam measurements, cut pattern allowances, fit jacket and trousers, adjust sleeve balance. C, hand-embroidered bridal ao dai set, C8,200/R12,000/M3,800: agree motif placement and fabric quantity, collect staged deposit, prepare pattern, embroider panels in order, conduct two fittings, attach lining and final inspection. Extra gate: 10 correct fittings; B five clean alterations; C three completed made-to-measure jobs and fitting bookings.

**Seam/risk.** Add catalog, prices, sizes, colors, fit rules, stock/grid synchronization and new workshop state, not just ITEMS (`:58–129,649,1239–1284`). Keep high prices visible on new labels and invoice line items. Purchase fee buys design access, material stock purchased separately, deposits offset final receipt. Extend all price/till/refund/COD caps deliberately. Preserve `_takings` margin-only gear/abroad commissions (`:770–783`), and account for tailor share40% (`:143–144`). The proposed margins exclude overhead; do not multiply whole12k receipt for gear. Old task budget520 cannot silently order a3,600 tuxedo.

## 10. pet_shop — Tiệm thú nhỏ

**Existing economy and gate.** 60L tank130 cost/220 sale (`game/careers/pet_shop.py:81`); kitten feed25/40 (`:60`). Stages require day+good-work milestones (2/2,4/6,6/12) (`:535–540`) and welfare check (`:807`). Aquarium selection, live fish, adoption, illness referral, food sensitivities and care already exist. Puppies/kittens remain adoption, not sales (`:127`).

**New paid content:** A, custom cat climbing wall kit, C90/R160/M70: measure wall/support constraints, choose modular spacing by animal mobility, assemble, load-test and hand over. B, planted aquarium aquascape, C240/R430/M190: map hardscape stability, layer substrate, plant foreground/background, plan filtration/light timer and staged setup record before stocking. C, aviary habitat installation, C560/R900/M340: measure enclosure, select species-compatible spacing/perches, arrange washable feed zones, predator/escape check and maintenance handover. Extra gate: stage2, no unresolved welfare incident; C two successful habitat builds.

**Seam/risk.** Existing tank schema assumes10/30/60L and a small animal compatibility map (`:114–125`). Add habitat/workshop branch rather than multiplying animal price or inventing rare-coat premium sales. Heavy glass shipping already has constraints (`:87–92`); installation needs logistics cost. Animal care mechanics are fictional game checks, not clinical instructions.

## 11. tra_da — Quán trà đá

**Existing economy and gate.** Tea3/tea-lemon6; dry tea2 per handful (`game/careers/tra_da.py:84,95`), ice4 per block (`:85`), so revenue3 is not net3. Setup then glass/tab day1, settlement every3 days and match orders on football modifier (`:571–582`). Existing stools/glasses/umbrella/banner upgrades8/6/30/20 (`:244–247`).

**New paid content:** A, ginger lemongrass infusion, C7/R18/M11: bruise aromatics, simmer time, strain and distinguish hot/cold requests. B, salted lemon preserve drink, C16/R38/M22: inspect dated preserve jar, portion pulp, dissolve before ice and balance requested salt/sweetness. C, neighborhood meeting tea urn service, C65/R130/M65: reserve urn and cup count, brew to headcount, stage thermos refills, serve staggered arrivals and settle shared bill. Extra gate: 10 balanced bills, then B infusion check/C one clean group service.

**Seam/risk.** Add recipe/prep states to existing glass/tab flow; keep old debt and day schedule. Tiny stall premium margin deliberately remains lower than boutique clothing; high purchase tiers cannot be justified by raising every glass to luxury prices. Tobacco and gambling-like social scenarios must not be the premium progression reward.

## 12. fruit — Sạp trái cây

**Existing economy and gate.** Mango cost3/fruit, mass380g, price14/kg (`game/careers/fruit.py:55`): theoretical5.32 revenue before scale rounding, not14 per fruit. Existing grapes10 per500g/32 perkg (`:60`). All7 fruits already there; day2 bulk, special altar day, return every3rd day (`:542–552`).

**New paid content:** A, peeled pomelo gift box, C30/R65/M35: inspect ripe lot, separate membrane without crushing, tare box, portion and freshness label. B, tropical fruit carving platter, C80/R160/M80: choose firmness, map edible cuts/waste, carve safe shapes, arrange portions and cold delivery slot. C, premium imported-fruit tasting hamper, C240/R420/M180: verify origin/lot and ripeness windows, sort fragile berries separately, proportion tasting guide, reconcile mass and delivery receipt. Extra gate: 10 correct tare weighings; B trimming practice; C traceability and cool-storage capacity.

**Seam/risk.** FRUITS stores unit cost, gram mass and perkg sale price (`:55–66`); avoid unit conversion inflation. New processed fruit needs cut-at time and shorter expiry; current whole-fruit ripeness stages insufficient. Altar tray already exists and is not a new premium mechanic. Current return and bulk flow must preserve exact gross/discount attribution.

## 13. ice_cream — Tiệm kem

**Existing economy and gate.** Popsicle2 cost/5 sale; normal scoop6 and avocado7 (`game/careers/ice_cream.py:99,103`). Coconut purchased tub16, recipe homemade coconut cost7 (`:72,131`); no one-scoop=one-tub confusion. Homemade taro requires craft certificate or sandbox day5 (`:146,154–155,1212–1217`); existing coconut/avocado/taro recipes, churn/temperature/weight work already extensive.

**New paid content:** A, mango passionfruit sorbet, C22/R60/M38 per tasting tub: measure fruit/syrup, check soluble-solids game meter, chill, churn and test scoop texture. B, pistachio gelato, C60/R140/M80: roast/grind nuts, blend custard base, cool, churn slowly, label nuts and dense portions. C, layered semifreddo celebration loaf, C180/R360/M180: whip/fold base, alternate fruit and biscuit layers, set in mold, unmold at serving firmness, slice and cold-package. Extra gate: existing craft certificate plus three successful homemade batches; C reserved freezer mold slot.

**Seam/risk.** RECIPES (`:130–155`), action stages1243 onward and strict batch-key validators (`:1697–1705`). New recipes need explicit stages beyond existing ingredient substitution. Distinguish revenue per tub/loaf from scoop price; preserve mass, container tare, melt/refreeze checks and failed-batch disposal.

## 14. pho — Quán phở

**Existing economy and gate.** Regular bowl30/large38/takeaway32 (`game/careers/pho.py:108`); noodles2 and rare beef6 (`:95–96`), plus shared bone-broth cost8 per batch (`:105`). Thus simple rare-beef bowl30 before garnish/broth allocation, not net22 guaranteed. Setup, serve, take and crew already exist (`:201`), crew schedule starts day3 (`:438–447`).

**New paid content:** A, free-range chicken pho, C28/R75/M47: poach batch, skim, shred portion by cut, switch chicken stock and garnish separately. B, red-wine braised beef pho, C65/R150/M85: sear and braise cubes, test tenderness, finish sauce concentration, coordinate hot noodles and separate herbs. C, tableside marrow-bone pho set for two, C160/R330/M170: reserve bones, roast marrow tray, clarify broth, portion two bowls and time tableside handover. Extra gate: 10 correct hot-broth deliveries, B braise practice, C two clean double orders.

**Seam/risk.** Add recipe/stock family rather than new beef-cut ID only; current main pot and meat list assume beef pho. `_bowl`, `_dip`, `_meat` and `_pour` (`:734,752,777,838`) need explicit broth family, prep timing and shared-pot contamination checks. Preserve existing volume and heat windows; don't overwrite active beef pot when chicken pack is purchased.

## 15. com — Quán cơm

**Existing economy and gate.** Rice4+pork rib6 =10 receipt (`game/careers/com.py:103`); rice pot4 and rib2 costs (`:90,92`), allocate rice-pot yield rather than subtract whole pot per plate. Current menu already includes pork, egg, braised fish/meat, vegetables/tofu (`:63–71`). Group kind scheduled day3/every3 days (`:383–392`); setup gates cooking.

**New paid content:** A, lemongrass chicken broken rice, C14/R36/M22: marinate, grill skin/flip timing, portion rice, cut chicken and pack sauce separately. B, clay-pot salmon rice, C45/R100/M55: sear fish, portion rice/water, set clay-pot heat, add fish at the correct stage, finish crust without burning. C, six-box premium office bento, C180/R360/M180: plan protein/veg sides, stagger batch cook times, divide weight fairly, label restrictions and seal all boxes to one dispatch. Extra gate: 10 correctly cooked plates; B dedicated clay-pot station; C successful multi-order service.

**Seam/risk.** TOPS/ITEMS/PRICES and station source types (`:63–103`) currently assume grill/tray/pan. Add explicit cookable recipe state for new station, not an instant tray entry. Bento rows need atomic stock reservations and one settlement, while keeping individual quality. Do not count six boxes as six independent premium-contract quota rewards.

## 16. naucom — Nấu cơm gia đình

**Existing economy and gate.** Wage30+4*people+loyalty capped6 (`game/careers/naucom.py:185–189,1003–1004`): first clean3-person meal42. Family shopping money is task purse, never player wallet (`:30,635`); leftover returned at settlement (`:1023–1046`). Existing meals include20 mains/soups/veg plus porridge/che; methods have cook windows (`:92–125`). Families become available days1/2/3 (`:165–171`).

**New paid content:** A, family dim-sum brunch, market budget90/actual75, wage80: select fillings for household restrictions, fold/count dumplings, stack steamer order, cook and settle receipt/15 returned. B, three-day chilled meal prep, budget220/actual195, wage150: plan shared ingredients, batch-cook, portion dated containers, cool/store in order, write reheating labels and return25. C, twelve-guest home banquet, budget520/actual460, wage300: negotiate menu/service times, shop with approved substitutions, schedule burners, stagger hot courses, audit receipts and return60. Extra gate: 10 honest shopping reconciliations, B clean cooling/label practice, C two on-time family menus.

**Seam/risk.** Extend `DISHES`, family constraints and `make_task:486`; add brunch/multi-day/banquet state. The player pays for access and any own transport/consumables, never recognizes the client's90/220/520 advance as revenue. Listed wage is player revenue before own overhead, **not wage minus client's shopping costs**. Banquet headcount, bowls12 (`:137`), burners2 (`:135`), warm90s (`:134`) require explicit capacity design, not relaxed validators.

## 17. zpop — Tiệm album Mây Pop

**Existing economy and gate.** Pink version14 cost/20 sale (`game/careers/zpop_content.py:50`), lightstickv2 45/62 (`:73`). Open display copy costs14 but sells12 (`:64`), an intentional markdown. First3 sales apprenticeship; setup limited copies/person2 on comeback else3, preorder closes with real stock cost (`game/careers/zpop.py:6–22`). Cases startday2, share18% (`:50`); no paid catalog gate in current SKU list.

**New paid content:** A, archival album display framing, C45/R90/M45: get permission before opening customer-supplied goods, count inserts, select acid-free mount, protect signed surface, seal and handover checklist. B, numbered vinyl collector box, C180/R320/M140: match catalog/pressing number, inspect seal and warp indicator, verify sleeves/booklet, explain playback compatibility and pack upright. C, fan-club group order fulfillment service, C400/R700/M300: reconcile member-paid ledger, enforce per-person limits, allocate exact variants without promises, pack named parcels and close with missing-item reconciliation. Extra gate: 10 accurate baskets, B authenticity checklist, C three accurate preorder closures.

**Seam/risk.** Content SKUS/SELL/PRICES (`zpop_content.py:49–85`) feed inventory; task kinds limited setup/sale/case (`zpop.py:43`). Extend kinds and validators for customer property and contract ledger. Fictional artists only; never sell guaranteed random inclusions or fansign wins. Fan-club prepayments are liabilities until goods delivered, no duplicate chart scans or duplicate ownership credits.

## 18. art_studio — Xưởng vẽ Màu Nắng

**Existing economy and gate.** First commission gross28/cost6/net22; phase4 gross36/cost10/net26 (`game/careers/art_studio.py:51,56,119–131`). Cost is charged at delivery after receipt, intentionally allowing empty funds (`:127–130`). All16 commissions are already day-gated1/4/10/20/40/45 (`:24–40`); exhibition day45/good140/active35 (`:42–43`). Existing triptychs, posters, civic murals and exhibition sets cannot be re-labeled as premium unlocks.

**New paid content:** A, commissioned linocut edition, C35/R90/M55: approve reversed sketch, mark carve-safe lines, carve layers, register paper, print/test and number editions. B, gold-leaf icon-free decorative commission, C110/R240/M130: prepare gesso, lay adhesive at tack stage, place leaf, burnish, paint detail and seal. C, stained-glass window panel design/build, C320/R650/M330: approve measured pattern, assign glass pieces/colors, score/break, foil joins, solder order, edge-frame and inspect transmitted-light gaps. Extra gate: 10 good art commissions; B clean surface practice; C frame/tool qualification and made-to-order booking.

**Seam/risk.** Existing small module exposes OPTIONS/LAYERS, make_task47, handle86, validators167/192. New media demand distinct action graphs and proof criteria, not simply extra palette choices. Keep recipe schema versions and exact saved `_key` validation; premium materials should be reserved/paid at start to make high-cost commission risk meaningful, unlike current small delivery-funded materials. Portfolio cap12 (`:126`) should not erase ownership or lifetime qualification counters.

## Coverage and validation of this audit

Covered exactly: mother_baby, pharmacy, milk_tea, restaurant, cafe_bakery, florist, grocery, farm, clothing, pet_shop, tra_da, fruit, ice_cream, pho, com, naucom, zpop, art_studio. 54 proposed content examples, each with different work mechanics, proposed revenue/cost or client-purse/wage model, current evidence and gating.

Novelty is against the actual catalog/action families read here; names alone are not the criterion. Explicitly excluded false-new proposals: farm-plus strawberry/coffee/greenhouse, florist wedding bouquet/subscription, cafe peach tart/matcha drinks, clothing blazer/maxi/shoes, ice-cream coconut/avocado/taro craft, art exhibition/triptych. Before implementation, search all localized UI content and exact mechanic branches for any additional overlap, then simulate the complete entitlement→stock→task→refund→save-reload→paid-day flow. This audit did not run gameplay or mutate accounts.
