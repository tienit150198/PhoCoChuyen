# Paid Convenience Implementation Plan

**Goal:** Dùng xu mở tiện ích và giới hạn theo 10 bậc, có mục tiêu cho người sở hữu hàng trăm triệu xu; xử lý feedback mới 368 và 369.

**Architecture:** Giá chung mỗi bậc 3.000 / 9.000 / 30.000 / 100.000 / 350.000 / 1.200.000 / 4.000.000 / 12.000.000 / 35.000.000 / 100.000.000 xu, tổng 152.692.000 mỗi nhánh. Mua tuần tự, không cộng dồn hiệu ứng cùng nhánh, server tính quyền từ sở hữu. Giữ tài sản hiện có, giới hạn thấp hơn chỉ chặn mua thêm; không xóa hàng đặt trước hoặc hàng giữ cho khách. Không thay lợi nhuận/xác suất để tạo tiền trả nâng cấp. Chùa và quyền riêng tư không thu phí.

**Tech Stack:** Python reducer/Store, PostgreSQL thử riêng, ES modules, Node/Playwright.

## Warehouse track

Ownership: worker kho owns new game/convenience.py, content.py catalogue wiring, engine.py stock/upgrade integration, operations.py capacity, pharmacy validation if needed, public/js/app.js stock UI, public/js/v4/views.js counting, public/js/v4/work-equipment.js rendering, focused tests/browser script. No quay edits.

- [ ] Write red tests for sequential buying, insufficient funds rollback, wrong career, max tier, persisted ownership; quantity/capacity overflow including incoming and pharmacy lots; no duplicate receive.
- [ ] Add paid count track across shared countable warehouses: 1 base, then 2/3/5/8/12/20/30/45/65/100 items per action/hold tick. Preserve typing, manual counts and already-free shared tray10. Legacy mother_baby/pharmacy missing hold integration is fixed; paid tiers accelerate rather than auto-receive or skip final confirmation.
- [ ] Legacy logistics track (mother_baby/pharmacy): per-line 6 base then 8/12/16/24/32/48/64/96/128/200; per-code capacity max(existing shelf/property, 24/36/48/72/96/144/192/288/384/600). Increase hard save bounds safely, public authoritative limits, pending shipments count toward room. Each track has same price ladder; costs debit career fund through buy_upgrade.
- [ ] Render actual units/current→next/price/cumulative max, lock prerequisites, no repeated 100% labels for unit upgrades. Test both warehouse interfaces, touch hold cancel/release, paid batch bounds, typed counts and successful receipt.

## Player-owned quay tracks

Ownership: worker quay owns game/quay*.py and optional game/quay_progression.py, public/js/v4/quay*.js, tests for paid quay progression. No global content/engine/app edits.

- [ ] Red tests for atomic buy, exact expected tier, prerequisites, wallet+bank funds, replay/insufficient funds, max caps; stock/reservations and old over-cap assets unchanged.
- [ ] Independent per-stall storage and restock tiers, plus owner-level slot tier. Same 10-price ladder each. Base storage500, then750/1000/1500/2500/4000/6000/9000/13000/17000/20000 total portions; absolute technical max20000 unchanged. Restock action base5, then10/20/35/60/100/160/250/400/700/1000 aggregate portions. Slots base1, then2/3/4/6/8/12/18/26/38/50. Existing quays above allowance remain; next opening needs room. Existing storage above purchased cap can sell/fulfill but cannot restock beyond new cap.
- [ ] Keep existing paid place upgrade xe→sap→kiot and certificate enforcement. Spend upgrades through quay._take wallet/bank (100m safe local log max), not stall fund. Limits include reserved visitor portions. UI quote, repeat order, manage restock and purchase all use server limits with fallback for older server.
- [ ] Test new/old saves, highest tier, existing many quays, full stock/reservations, managed repeat restock and physical expansion; browser viewport390/1280 if practical.

## Integration, feedback, release

- [ ] Root owns game/progression_prices.py shared ladder, global translations/version/docs, feedback read/replies and release. Confirm369 against wealth/housing/lux rules; reply factually, no gift/refund.
- [ ] Review integration independently and run focused Python/Node/browser coverage. Test_store uses TEST_DATABASE_URL only. Verify career task compatibility against live2.2.1.
- [ ] Build next version from live2.2.1 source24a910f3, verify extracted package, guarded rolling deploy, live hashes/health. Preserve old releases/backups; no full dump on nearly full production disk.
- [ ] Reply368 only after actual tested release; keep deferred old requests seen rather than claim done. Record release baseline and push main.
