# Top lỗ Hội chợ theo tuần

Chủ game chọn chỉ tính lỗ phát sinh trong tuần. Bảng vàng có hai lựa chọn Top lời và Top lỗ. Top lời giữ cách tính tích lũy hiện tại; Top lỗ dùng sổ riêng `fair_loss_week` (schema 36).

- Tuần từ thứ Hai 00:00 đến thứ Hai kế tiếp, giờ Việt Nam. Lỗ ròng = tiền thua trừ tiền thắng và xu kiếm trong tuần tại Hội chợ. Tiền vốn tặng, vay và trả nợ không tính. Chỉ số âm mới xếp hạng. Khoản thu/chi tính tại thời điểm ghi nhận, kể cả vé mua và nhận thưởng khác tuần.
- Top 1 nhận `f_loss_king` — 🥀 Vua đen đủi; Top 2–10 nhận `f_loss_club` — ☔ Hội đen đủi. Danh hiệu giữ vĩnh viễn, không thưởng xu. Đồng lỗ xếp theo lần đạt số dư đó trước, sau đó SID để ổn định.
- Chốt sau ranh giới tuần 60 giây, qua maintenance hoặc lượt đọc Bảng vàng. Snapshot, con trỏ tuần và hiệu ứng danh hiệu cùng giao dịch; ID cố định cho phép chạy lại an toàn. Khi server ngừng lâu, xử lý tối đa 8 tuần mỗi lượt.
- Quyền ẩn tên áp dụng cả xếp hạng và xét danh hiệu; tên trong vinh danh cũ tuân theo quyền riêng tư hiện tại. Xóa tài khoản xóa sổ, hiệu ứng đang chờ và ẩn SID trong snapshot.
- Ghi delta trong cùng giao dịch lệnh/lưu/receipt, cả đường optimistic và khóa; import/reset không làm phát sinh lời/lỗ. Shared advisory lock theo tuần cùng kiểm tra lại đồng hồ sau khóa bảo vệ kết quả đã chốt. Không đọc lại tất cả save.
- Bổ sung 1.9.48 theo yêu cầu chủ game: tuần đầu 05–11/10 lấy tổng lời/lỗ hiện có của từng save làm mốc, để Top lỗ có số liệu ngay. Đây là ảnh chụp số dư hiện tại, không phải phục dựng giao dịch tuần trước. Các tuần sau chỉ tính delta trong tuần. `fair.seeded` chỉ bật ở đúng tuần đã seed.

API: `GET /api/leaderboard?board=fair-loss&limit=20`. `rows[].xu/score` là trị tuyệt đối số lỗ; `me.net` có dấu; `fair.week/next/started/tiers/winners` cho giao diện tuần. Không trả SID.

Seed thủ công: `python scripts/seed_fair_loss.py --week 2026-10-05`. Mỗi lô tối đa 50 save, khóa tất cả save theo SID trước khóa tuần, đọc số dư hiện tại, thay mốc của tuần đầu rồi lưu con trỏ trong cùng giao dịch. Gián đoạn chạy lại tiếp tục từ con trỏ, không cộng trùng; khi hoàn thành gọi lại không đổi gì. Tiền thắng/thua sau lúc chụp từng save tiếp tục tính bình thường. Không đổi save, ví hoặc cấp danh hiệu sớm. Reset/import trước khi chụp được phản ánh theo số dư đang lưu. Công cụ từ chối tuần đã qua, không tự chạy ở tuần sau.

Triển khai âm thầm theo yêu cầu, không đổi Có gì mới. Giữ ngưỡng 30 trận hợp lệ cho bảng kéo co micro; ngưỡng đó không áp dụng cho Top lỗ.

Rollback: schema chỉ thêm bảng. Trước lần trao đầu tiên (thứ Hai 12/10/2026) có thể về code cũ; sau khi save đã nhận danh hiệu mới, rollback phải giữ hai ID trong registry danh hiệu để save còn hợp lệ. Không xóa bảng hoặc sửa save khi rollback. Khoảng dùng code cũ sẽ không ghi sổ Top lỗ.

Kiểm thử: PostgreSQL thực cho bù trừ/chuyển tuần, retry/rollback lệnh, cả đường lưu, dữ liệu cũ/import/reset, riêng tư/xóa tài khoản, chốt đồng thời, trao đúng một lần không đổi ví, rollback snapshot/hiệu ứng và writer bị trì hoãn qua tuần. UI kiểm tra đổi bảng/response cũ, lỗi/thử lại, số có dấu, tên escape và mobile Chromium/WebKit.
