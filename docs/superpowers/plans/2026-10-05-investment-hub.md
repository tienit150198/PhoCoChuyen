# Investment hub implementation plan

Goal: one visible Đầu tư entry for Mây Coin and gold, multi-day fictional market news with more upward than downward episodes, quiet deployment.

Architecture: retain existing authoritative coin/gold trades and holdings. Add deterministic market regimes on their existing clocks (coin life days; gold VN dates). Price projection is read-only. Gold history through2026-10-05 and existing coin history are anchors. UI uses current journey sheet and existing command path; no new DB schema.

Tech stack: Python, PostgreSQL, browser JavaScript/CSS.

- [ ] Backend owner: game/invest.py, game/vang.py, optional market_trends.py; add deterministic/regime/migration tests. No holdings, fees, savings or scam mechanics changes.
- [ ] UI owner root: app navigation, journey investment entry, invest.js hub/cards/actions and invest.css. Gold and coin available on same screen; preserve coin unlock while gold remains available to new players. Saved sources/costs retained. Existing gold links remain usable.
- [ ] Test existing investment/risk/money behaviour, backwards validation1.7.10, seeded long-run price distributions and bounded performance.
- [ ] Actual mobile browser320/390/430: menu entry, coin locked/unlocked, buy/sell both instruments, headlines escaped, no overflow or duplicate orders.
- [ ] Build1.7.11 over verified1.7.10 baseline; no changes to game/whats_new.py or whatsnew-data.js, no gifts or global notifications.
- [ ] Verify extracted package, deploy under tmux, check live build/assets/health/logs and preserved1.7.10 news.

User has expressly authorized implementation and deployment, with no release announcement. Routine implementation decisions above use that authorization; no extra approval gate. New features are fictional game investments, not market data or real financial guidance.
