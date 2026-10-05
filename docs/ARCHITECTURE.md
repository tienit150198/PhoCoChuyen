> Tài liệu nền v0.2 được giữ để tra cứu. Phần bổ sung hiện hành ở V03_GUIDE.md, API_V03.md và README.md; số lượng nghề/schema trong lịch sử không mô tả v0.3.

# Kiến trúc triển khai

## Thành phần

Frontend JavaScript ES modules không framework, CSS responsive, Canvas 2D cho cảnh và SVG inline cho icon/vật phẩm. Python stdlib phục vụ static/API; PostgreSQL là nơi lưu state, kết nối qua psycopg. Không cần bước build frontend để chạy. Hình và âm đều tạo tại máy.

Luồng:

```text
Click / touch / câu chat
       │
       ▼
app.js → api.js (hàng đợi, request_id, expected_revision)
       │ HTTP JSON + cookie + X-Game-CSRF
       ▼
server.py → storage.Store.command
       │ SELECT … FOR UPDATE + kiểm idempotency/revision
       ▼
engine.apply_action(copy(state), career, action, payload)
       │ kiểm nghề, bước, chứng cứ, tồn, giá và điều kiện
       ▼
state mới + event journal + kết quả
       │ COMMIT chung với command receipt
       ▼
public_state → app.js / world.js → cảnh + phản hồi
```

Một lệnh không hợp lệ không thay đổi bản state đầu vào. Chống gửi lặp nằm ở kho dữ liệu, không dựa vào nút bị disable trên giao diện. PostgreSQL khóa dòng bản lưu; receipt và state cùng giao dịch. Revision ngăn tab cũ ghi đè. Khi mất kết nối không giả rằng một thao tác đã thành công.

## Các loại trạng thái

Root gồm schema/name/current/settings và state riêng của bốn nghề. Mỗi nghề có day/turn/open, ví/xp, kho, task, shipment, feed, chat, memory, upgrade/decor, event/pending, quest và album. Task kết thúc vẫn có ID để đối chiếu review và ngăn thưởng lặp.

Thời gian nghiệp vụ là **lượt thao tác**. Hàng nhập tới sau hai nhịp nhưng chưa vào kho cho tới khi kiểm nhận. Kết quả phối hợp CSKH về sau nhịp nhưng chưa đóng cho tới khi kiểm. Những việc đó không chạy theo giờ ngoài đời và không phạt người nghỉ.

Dữ liệu công khai che phần chưa khám phá: nhu cầu trước khi hỏi, nội dung chứng cứ chưa đọc, bản gốc chưa xem, đáp án phương án CSKH. Bản xuất backup chứa state đầy đủ của phiên và có thể bao gồm dữ liệu giả lập chưa lộ; đây là trò một người không cạnh tranh, không coi backup là anti-cheat boundary.

## Vòng nghề khác nhau

Tiệm giữ tồn theo giỏ, kiểm nhu cầu/giá/gói trước xuất. Nhà thuốc giữ theo lô, không cho xuất lô tạm giữ/hết hiệu lực. Kế toán ghép cả tập mã tham chiếu và tổng, không chỉ chọn tổng bằng nhau; loại trùng/correct gắn nguồn. CSKH không cho đóng vụ chỉ vì câu nói đã hứa, cần trạng thái thực thi rồi xác nhận.

## Sự kiện và ký ức

`game/events.py` biến baseline thành vignette có dữ kiện ổn định, lựa chọn và các bước cụ thể. Sự kiện có một trạng thái đang mở, trước khi commit một lựa chọn phải đọc chứng cứ và xác nhận. Diễn tập gắn cờ practice và chặn mọi tiến triển kinh tế/quan hệ. Việc thật hoàn thành có journal, memory.source, feed và pending follow-up ngày sau.

Ký ức là tóm tắt sự kiện đã chạy, không phải phần AI tự viết vào DB. Câu chat không được trở thành kết luận “đã thanh toán” hoặc “khách đã lấy đồ” nếu reducer chưa xác nhận.

## AI

Baseline lời thoại được engine tạo từ câu người chơi và state. Adapter server có thể diễn đạt lại duy nhất câu đó, sau quyền đồng ý, endpoint do chủ server đặt, key ở server. AI không có write tools. Thất bại, timeout, vượt lượt hoặc câu trả lời không hợp lệ dùng câu gốc. Kiểm số chỉ là hàng rào cơ bản, không phải bộ chứng minh ngữ nghĩa; câu chuẩn vẫn hiện được trong UI.

## Renderer

Lõi World giữ đường đi và hit-test; BobaWorld v0.2 chiếu ô sàn vào cảnh chính diện, với bố cục portrait riêng. Hitbox là đồ vật/NPC, đường đi tìm trên lưới tránh vật cản. Có đường click tương đương cho bàn nghề nên gameplay không phụ thuộc điều khiển chính xác trong canvas. Việc giảm chuyển động rút ngắn/loại animation, không đổi luật. Ảnh album được xuất từ renderer đang dùng state thật.

## Thêm nghề

Thêm định nghĩa nội dung, factory task, luật/validation/public projection, bàn UI, props của cảnh, hướng dẫn và tests. Chỉ bỏ trạng thái khóa trong catalogue khi vòng chơi đã chạy end-to-end. Không sao chép nghề bán hàng rồi đổi nhãn để giả thành nghề mới.

## v0.2 business layer

`operations.py` owns fictional rules, employee records, premises, bills, staff assistance, security cases, proof-gated conclusions, recovery and reward. `engine.apply_action` runs these on a deep-copied candidate state then validates; `Store.command` commits once under `SELECT … FOR UPDATE`, expected revision and request receipt.

`money()` appends to the operations ledger for every asset-related cash mutation. The invariant is `opening_balance + sum(ledger.amount) == career.money`. Compaction rolls pruned amounts into the opening balance. Bills have stable IDs by day/person/period or incident; paying is separate from accruing and cannot repeat. Tax is a fictional 5% ceil of earned career revenue; other rewards and restitution have distinct categories.

Staff have no independent timer/network loop. Work actions feed `ops.tick`; assistance may modify a checked source or draft basket, never perform the final payment/delivery/case closure. Actual attendance earns one wage bill/day; existing obligations survive dismissal. Incidents stop the affected worker and carry over safely between days. Rehearsal effects do not charge or reward.

Security fixed truth/roll are chosen at creation, stored privately, and public projection redacts unopened evidence. Theft loss excludes reserved stock; report/restitution/reward/insurance are separate gated transitions. Natural events observe modes, cooldown and other open incidents. Equipment installed later does not backfill evidence or eligibility.

`migrate_state` upgrades schema 1 with an opening balance equal to the current wallet and period beginning at the current day. `Store.read` serializes migration under transaction and increases revision once. Other gameplay data stays intact; keep a v0.1 backup for downgrade.

`BobaWorld` extends the original world interface/pathfinding/snapshot engine. It supplies a new frontal scene and portrait composition, profession-specific props, visible staff and security. `operations-ui.js` renders only; DOM buttons send commands. Nothing in the renderer is authoritative for money or facts.
