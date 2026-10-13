# Expand paid capacity to existing career stock systems

**Goal:** Carry the user's capacity addition into every existing stock career, locally only. 24 shared inventories + milk tea join the two existing legacy paid warehouses. Review all54 careers and name other real resources without selling nonfunctional upgrades.
**Architecture:** Shared capacity_progression helper reads warehouse_storage_<career>_<tier> from owned upgrades. Ten sequential prices reuse progression_prices. Pure baseline calls retain original capacity; state-aware callers derive paid capacity. Engine buy_upgrade already handles payment/prerequisites/replay. Catalogue adds capacity units to existing equipment UI.
**Tech Stack:** Python reducer/PostgreSQL, ES modules, Node/browser tests.

User's latest instruction adds capacity to the previously presented paid progression. No new paid-day budget is implemented by this change. No deployment, package, upload or main push.

- [x] Root: write failing catalog/purchase tests for24shared+milk, no irrelevantwarehouse fees, sequentialcost/exacttier10 bounds.
- [x] Root: create game/capacity_progression.py. Ratios (8,12,18,26,38,55,80,120,180,260,400)/8, ceiling arithmetic; base80→4000, com120→6000, milk60→3000 and cups120→6000. Catalogue uses effect_units/effect_previous; buys only warehouse_storage group. Add catalogue in game/convenience.py without changing existing legacy logistics ownership.
- [x] Shared worker: inventory.capacity(career,c=None), stock_limit stateaware. Update cart/order/receive/events/returns/save validation and all consumers; line80 stays. Preserve purchased stock, incoming and held portions; block impossible receipts before mutation. Cover high-tier stock and out-of-tier rejection.
- [x] Milk worker: use helper on shelf/cup capacity across order/prepare/receive/event/public/validation. Preserve live pantry lots, reserve incoming, no paid shipment truncation. Existing recipe and order batch constraints stay.
- [x] Root: add warehouse_storage units section in work-equipment.js. Render base/next/price accurately; add English sources. Verify Node units and browser390/1280.
- [x] Read-only audit: classify all54 resources, distinguish operational stock/machine/room from safety/puzzle constraints. Update capacity-design appendix linked to54career spec, with explicit implemented/planned status.
- [x] Integration: focused Python/Node/save/browser, live task compatibility, whitespace respecting originalCRLF. Record evidence and known historical failures; stop localtestDB after allworkers finish.
- [x] Commit local changes only and report exact scope. 540newcontent packs remain design work, not claimimplemented by capacitypatch.

- [x] Scope follow-through: same owned storage track also expands farm cold store/lot slots/nest/garden store and bakery/restaurant/com prepared buffers. Fixed farm and bakery whole-lot waste records; reviewed grocery inspection references. Pho free refill, physical rooms/machines and safety/puzzle limits remain separate as documented.
