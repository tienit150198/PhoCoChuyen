# Rental market implementation plan

Goal: Owner-defined property rent, NPC and player tenants, and fictional news that changes resale value and rental demand.

Architecture: Existing housing save and NPC ledger remain; an authoritative PostgreSQL rental module handles inter-player contracts and payments. Player leases are prepaid in five tenant life-day periods unless the user selects a different clock. Prices are locked per contract. The shared property_market module supplies deterministic calendar quotes; acquired market multiplier prevents instant resale profit from a current positive event.

Tech stack: Python, PostgreSQL atomic sorted-session transactions, vanilla JavaScript house UI.

- [x] Shared market quote with varied planning, neighborhood, tourist, flood, construction and haunting-rumor events; bounded prices and gradual recovery.
- [x] Raise suggested rents, preserve current signed rents, permit custom asks and reduce NPC demand as ask/reference rises; no relisting rerolls.
- [x] Player market/listing/accept/renew/leave API with ownership, account, funds, blocks, one tenant per property, one active lease per tenant and one payment per action.
- [x] Actual rental residence, tenant-owned decoration, expiry and safe owner sale/move/import guards.
- [x] House UI with market tab, clear price reference/demand, listing form, lease terms and entry/renewal/return controls.
- [x] Verify old housing saves, NPC demand, simultaneous acceptance, receipts, payment conservation, expiry, stale quotes and mobile interaction.
- [x] Independent review; record any verified limits. This batch remains local until requested deployment.

No unrelated schema cleanup, no real financial data/news, no alteration of marriage/friend free-stay permissions.
