# Nâng cấp hạn mức nhập hàng mỗi lần

**Goal:** Mua nâng cấp bằng quỹ nghề để đặt hơn 80 món/mã/lần trong kho nghề dùng inventory chung, giữ sức chứa và giới hạn nhập độc lập.

**Architecture:** Nhánh equipment mới `warehouse_order`, 10 bậc riêng từng nghề, dùng cơ chế buy_upgrade đã có. Quyền hạn mức đọc từ upgrades của nghề phía server; inventory DTO truyền line_cap và thông tin nâng cấp cho UI. Không đổi logistics của mẹ & bé/nhà thuốc hay kho quầy vì các nhánh đó đã có nâng hạn mức; trà sữa không dùng đơn nhập inventory chung.

**Prices and benefits:** Bậc 0–10 = 80/120/200/350/550/800/1200/1800/2500/3200/4000 món/mã/dòng. Giá bậc 1–10 = 3000/9000/30000/100000/350000/1200000/4000000/12000000/35000000/100000000 xu; tổng 152692000 xu. Bậc cao cần đủ bậc trước. Không tự mua, không cấp miễn phí do đã nâng sức chứa. Giá đồng bộ hệ thống progression_prices đã được người dùng yêu cầu trước đây. Đã đối chiếu sức chứa cuối: 23 nghề 4000, cơm 6000; mức đặt cuối 4000 bảo đảm mỗi bậc đều sử dụng được khi nâng đủ kho.

**Example:** Kho quần áo 550, có 22, không hàng đang về/dự thảo khác/giữ chỗ, mua đến bậc 4 (tổng 142000 xu) thì được đặt 528 cùng lúc. Chưa mua vẫn 80. Bậc 4 hạn mức550 không tự mở sức chứa550.

## Work

- [x] Backend: tests đỏ về mua thật/tiền/trình tự/độc lập nghề và capacity; direct/cart/bulk/save validation/delivery/refund; thực thi tất cả lối nhập và projection.
- [x] Frontend: nhóm thiết bị mới, hiển thị hạn mức đặt và sức chứa riêng trong kho; nút nâng cấp; quantity input/chips/cart sử dụng cap server không hardcode80. Không thu tiền từ client.
- [x] Regression: inventory/cart/clothing/capacity/convenience và các mức tiền lớn; test UI phản ánh mua xong/reload; không thay đổi bản lưu cũ khi chưa mua.
- [x] Browser: kho550/stock22/cap80 trước mua; mua từng bậc đến4, trừ142000; chọn528, đặt đơn thật; nhận/lưu/reload/không vượt kho. Mobile/desktop.
- [x] Ghi kết quả và lưu cùng commit triển khai sau kiểm chứng. Tính năng tương tác2.5D commit51d46142 vẫn nằm trong cùng nhánh, chưa deploy; phát hành production riêng khi được yêu cầu.

## Verification — 2026-10-14

- Python: `tests/test_order_progression.py`, `test_inventory_flow.py`, `test_inventory_cart.py`, `test_inventory_cart_40.py`, `test_inventory_lead_times.py`, `test_capacity_catalog.py`, `test_warehouse_convenience.py`, `test_career_clothing.py`, `test_clothing_staff_stock.py`: **179 passed, 1 deselected** (89.51s), local PostgreSQL 55432.
- Excluded only `tests/test_inventory_cart.py::Cancel::test_saves_after_a_cancel_load_on_the_rollback_release`: rollback target `a9777863` lacks current careers; same failure reproduced on unchanged HEAD. This is not a paid-upgrade regression or evidence of rollback support.
- Node: `order_limits.mjs`, `warehouse_convenience.mjs`, `capacity_equipment.mjs`, `fit_draft.mjs` passed; changed JS syntax and `git diff --check` passed. Order tests cover actual renderer max80/528, draft reservations, upgrade navigation, exact goods/shortages across pages up to 8000 for stress coverage (purchasable maximum4000).
- `warehouse_convenience_browser.mjs` passed 390/1280px on mother_baby, pharmacy and common inventory: touch hold/release/cancel, typed counts, paid count step, receipt; preserved legacy behavior.
- `scripts/browser_order_progression.py`: real local game/API/DB, normal CSP, 390/1280px; sequential paid purchases142000, cap80→550, storage550 unchanged, stock22, direct order528, paginated tally retained, receipt528, reload preserved stock550 and purchased tier4; no page errors. Evidence `output/playwright/order-progression/report.json` and screenshots.
- Large crates mount at most100 slots per item at a time; paging neither counts automatically nor resets the player's tally. Paid counting upgrades keep their own behavior.
- Spec review identified and resolved held same-supplier size reservations and milk-tea wording. Re-review approved final4000 ladder.
- Independent quality review approved with no actionable findings; reviewer additionally verified all24 eligible careers through a4000-unit direct order → receipt → discard flow with JSON validation after each stage, plus10 Python order tests and Node order tests.

Paid order and storage upgrades remain independent. New saves containing orders over80 require this release or a forward fix; do not roll such saves back to an older validator. No production deployment in this task.
