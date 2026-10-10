# Giải kéo co chó sủa hằng tuần

Người dùng chọn trò kéo co bằng micro, giải theo tuần; điều chỉnh bản 1.9.45: bỏ ngưỡng 30 trận, xếp mọi tài khoản có trận hợp lệ. Phạm vi này đi cùng 30 tranh đấu giá, nâng cấp thu nhập, tăng nhẹ xác suất Chợ đen và bỏ phí vào cổng.

## Luật

- Tuần Việt Nam: thứ Hai 00:00 đến thứ Hai tuần kế tiếp. Trận thuộc tuần theo lúc kết thúc.
- Tỷ lệ = thắng / (thắng + thua + hòa); cả trận người chơi và chó nhà Mây. Mọi tài khoản có trận đã thực sự bắt đầu đều được xét, không yêu cầu đạt một số trận tối thiểu. Người chưa chơi không có tỷ lệ để xếp hạng. Hủy, chưa có mic hoặc thoát trước khi dây bắt đầu không giúp lên top.
- Bằng tỷ lệ chính xác: nhiều thắng hơn, đạt kết quả sớm hơn, khóa ổn định cuối cùng. Chỉ tài khoản có tên hợp lệ và bật hiện tên mới dự giải.
- Hạng 1–5 nhận 2.000.000 / 1.000.000 / 500.000 / 250.000 / 100.000 xu, mỗi hạng có danh hiệu lâu dài. Các hạng hiển thị tiếp theo không có tiền thưởng.
- Chốt sau hết tuần 60 giây. Thưởng vào ví lúc người chơi tải game; chốt lại hoặc nhận lại không tăng tiền lần hai.
- Sảnh hiển thị top, số thắng/tổng trận, tỷ lệ cá nhân và số trận đã chơi, mức giải, kết quả tuần trước; tự tải lại khi sảnh mở, giữ phần chi tiết người chơi đang xem.

## Lưu trữ và tương thích

- Schema 35 thêm `bark_tickets.competitive`, mặc định false. Live server mới đánh dấu dựa trên thời gian thực sự đã chạy của dây; không nhận kết quả từ client. Dữ liệu cũ không đủ để phân biệt trận chưa bật mic, nên không hồi tố chúng vào giải.
- Truy vấn theo chỉ mục thời điểm kết thúc vé; không quét JSON bản lưu. So tỷ lệ bằng phân số chính xác.
- Con trỏ tuần, kết quả chốt và phần thưởng cùng một giao dịch; khóa con trỏ điều phối nhiều worker. Bắt kịp tối đa 8 tuần mỗi lượt maintenance, không trao các tuần trước khi tính năng được bật.
- Loại `bark_weekly` dùng đường trả thưởng có xác nhận trong giao dịch bản lưu. Máy chủ cũ để nguyên phần thưởng chờ. Xóa tài khoản cũng xóa thưởng chưa nhận và ẩn liên kết tài khoản trong kết quả chốt.
- Máy chủ cũ vẫn ghi vé được, mặc định không đủ xác minh dự giải. Phải cập nhật cả game server và live service khi deploy.
- Sau khi đã nhận danh hiệu mới, rollback về máy chủ có registry danh hiệu cũ không an toàn; cần bản rollback vẫn hiểu danh hiệu và effect mới.

## Triển khai

Đã triển khai bản 1.9.44 lên đúng production 103.195.238.178 lúc 21:49 ngày 10/10/2026 (giờ Việt Nam). Game server và live service đều chạy release mới; schema 35, con trỏ giải tuần và API phần thưởng đã kiểm tra. Chi tiết sao lưu, mã gói và kiểm chứng: [DEPLOY_1.9.44_2026-10-10.md](DEPLOY_1.9.44_2026-10-10.md).

Đã xác minh tương thích 49.440 nhiệm vụ của 50 nghề từ base 09f630c4. Mỗi lần deploy cần kiểm tra lại base và phiên bản production, dùng `scripts/release_from_live.py`, kiểm tra cả API health và phiên bản live service sau chuyển đổi.

## Kiểm chứng đã hoàn tất

- 9 test PostgreSQL giải tuần và migration 34 → 35; 4 test WebSocket trận thật, hòa, chưa bật mic và bỏ trước trận.
- Test sảnh vẫn dùng được khi bảng top lỗi; test UI escaping, tiến độ, tỷ lệ và giải. Review độc lập đã kiểm tra lại bản sửa loại kèo chưa bắt đầu.
- Review Chợ đen: 28 test Python và 8 test JS độc lập đạt. Các test tập trung của phần cân bằng đạt; mô phỏng một triệu lượt mỗi trò giữ kỳ vọng trả thưởng dưới 100%.
- 312 module JS qua kiểm tra Safari 15. Giao diện 390×844: top, tỷ lệ cá nhân, chi tiết không bị đóng khi sảnh cập nhật; không lỗi console.
- Kiểm thử rộng có các assertion cũ về phí/xác suất đã được sửa và chạy lại đúng nhóm, đạt. Test riêng `fair_shell_render.mjs` còn lỗi có sẵn `otChip is not defined`, nằm ngoài phần thay đổi này.

Ảnh mẫu cục bộ: `output/auction-preview/bark-weekly-mobile.jpg`, `output/auction-preview/paintings-16.jpg`.

Cập nhật 1.9.45 đã live lúc 22:05 ngày 10/10: bỏ ngưỡng 30 trận và thông báo bốn mục theo chủ game. Xem [báo cáo triển khai](DEPLOY_1.9.45_2026-10-10.md).
