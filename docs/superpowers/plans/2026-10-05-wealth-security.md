# Security costs based on player assets

User authorized local balancing and selected houses, vehicles and investments in addition to cash. User subsequently authorized deployment after implementing random 1–20% incident pricing.

## Rules

- Wealth includes positive wallet, bank balances and deposits, investment savings, gold and coin at current quotes, owned homes at current value, vehicles at resale value, owned workplace funds, counter funds/tills. Employer funds and other players' assets are excluded.
- Price multiplier is `1 + max(0, wealth - 10_000) / 100_000`, capped at 1,000. Positive charges round up; free choices stay free.
- Counter protection fees use a saved daily quote. Settle elapsed time with the previous quote before publishing the next quote, so offline time and polling cannot reprice already elapsed service. New counters quote immediately; migration never retrospectively increases fees.
- Newly generated shop incidents capture the saved day/shift wealth quote; protection-racket stories capture wealth when opened. Their displayed choices and actual charges use that capture. Existing events and receipts retain old prices. Shop losses still cannot exceed 10% of the local cash available.
- Personal theft/hack exposure includes all selected asset types; existing liquid-fund floors and monthly loss budgets remain authoritative. No forced sale of property.
- Shop insurance premium scales per closed shift; already-issued invoices retain their amount.

## Execution and verification

1. Add a pure `game/wealth_pricing.py` helper and tests for each asset source, no double count, exclusions, fractional rounding and free choices.
2. Integrate daily counter quotes, expose the same rates through existing public fields, validate optional saved quote metadata; test offline/polling equality and no retroactive billing.
3. Integrate captured shop-event costs and optional metadata validation; test advertised versus charged cost, legacy history and retry rejection.
4. Integrate racket-story quotes, insurance and personal-risk exposure; test actual payment and asset-only rich players.
5. Run relevant economy/risk/incident tests and JS syntax checks. Record verification and leave all changes local.

## Approved follow-up

Random 1–20% of total assets applies to newly opened theft, bank-hack and racket events. Recurring protection remains progressive. Quotes are deterministic server draws persisted per event, legacy pending events retain prices, actual losses cannot overdraw the relevant account or force asset sales. New personal theft/hack monthly ceiling is 20% of the captured asset basis; other incident budgets remain unchanged. Deploy compatible readers before activating new writers. Preserve the existing announcement.
