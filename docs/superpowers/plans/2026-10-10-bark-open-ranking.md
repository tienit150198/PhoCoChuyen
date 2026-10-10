# Bỏ ngưỡng trận và thông báo cập nhật

Người dùng đã chốt: top tỷ lệ thắng tuần của mọi người có trận hợp lệ, không ngưỡng 30 trận; giữ mức giải và luật hòa/tie-break/quyền riêng tư. Người chưa chơi không có tỷ lệ để xếp hạng. Giữ trường minimum=1 để client cũ tương thích; giao diện mới không trình bày ngưỡng.

Thông báo đúng bốn ý được yêu cầu: làm đẹp sàn đấu giá; nâng cấp vật dụng tăng khách; vào Chợ đen miễn phí; top kéo co với giải thưởng lớn. Bản 1.9.45 dùng cơ chế Có gì mới hiện có, hiện một lần cho người chơi quay lại.

- Viết và chạy test hồi quy một trận thắng được xếp top/nhận giải; chưa chơi không xếp hạng; cập nhật kiểm tra UI.
- Sửa chính sách máy chủ, mô tả danh hiệu và UI; thêm bốn dòng thông báo và sinh bản JS.
- Chạy test PostgreSQL bảng top, thông báo, JS, gate tương thích; build từ manifest live 1.9.44.
- Rolling release, kiểm tra API/tài nguyên/health, lưu manifest và đồng bộ Git.
