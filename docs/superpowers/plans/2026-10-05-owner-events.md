# Owner events implementation plan

Goal: Add recurring, choice-driven shop events to private counters and career shops, with camera halving theft probability.

Architecture: Optional shop_events state managed by a shared authoritative module; existing shop command paths and cash ledgers remain responsible for spending. One pending event per business, deterministic outcomes and no offline event backlog. Existing security cases remain resolvable.

Tech stack: Python game engine, PostgreSQL persistence, vanilla JavaScript UI.

- [x] Implement shared events with at least ten varied, contextual scenarios and two or three clear choices.
- [x] Integrate real work/staff orders, camera purchase, public state and validated commands into Quầy riêng and Sổ tiệm.
- [x] Add a compact Việc cần xử lý card that shows consequences and available choices; show recent results and camera state without forcing modal interruptions.
- [x] Verify probability reduction, persistence, one-time settlement, insufficient cash, old-save migration and offline limits.
- [x] Verify mobile layout and an actual command flow; review changes before completion.

User authorized implementation. Do not commit unrelated shared-worktree changes. Deployment of this new batch is not assumed from the completed investment release.
