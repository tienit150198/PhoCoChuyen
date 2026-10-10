# Top lỗ Hội chợ theo tuần

Người dùng chọn chỉ tính lỗ phát sinh từng tuần. Đưa Top lỗ cạnh Top lời ở Bảng vàng Chợ đen. Top 1 nhận Vua đen đủi, top 2–10 Hội đen đủi, không thưởng xu. Danh hiệu vĩnh viễn như top lời, xét lại thứ Hai 00:00 Việt Nam, grace 60 giây. Quyền ẩn tên giữ nguyên.

Architecture: schema 36 thêm fair_loss_week (sid, week, net, since); mỗi command lưu thành công ghi delta số dư fair.money_of trong cùng giao dịch save. Chỉ ghi các hành động hợp lệ, bỏ import/reset, không hồi tố dữ liệu cũ vì không có lịch sử tuần đủ tin cậy. Net là lời trừ lỗ trong tuần, leaderboard hiển thị -net khi net<0. Không quét JSON saves và không rebuild bảng cũ. Ranh giới tuần dùng thời điểm ghi trong giao dịch. Kết quả tuần/cursor và grant title atomic, idempotent, bounded catchup. Xóa tài khoản xóa ledger/pending grants và ẩn snapshot.

API GET /api/leaderboard?board=fair-loss: shape board,total,rows,me,weekly=null,fair. rows rank,name,guest,score,xu (loss positive),days=0,me; me net (signed),xu (loss positive),rank,visible. fair loss=true,weekly=true,next,week,started,tiers,winners,crowned,settled. Người chưa lỗ không xếp hạng.

Tasks: root owns schema/storage/game fair_loss module/API/title registration and integration tests. UI worker owns public/js/v4/fair.js plus a pure renderer if useful, CSS and UI tests; must support loading/error/privacy/current winner snapshots and tabs. Independent final review checks specification then transaction/privacy/rolling safety. Reuse PostgreSQL test-only cluster; run targeted old fair/leaderboard/storage regressions, compatibility gate and Safari. Release silently per ongoing preference, no WhatsNew edits. Deploy with verified live baseline and preserve backup.
