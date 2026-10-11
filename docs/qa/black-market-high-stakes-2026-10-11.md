# Chợ đen: cược lớn trong Hai ngày vàng — 11/10/2026

## Quy tắc chủ game đã chốt

- Giữ sự kiện Hai ngày vàng và thời điểm kết thúc hiện tại.
- Xét tiền cược của **một ván**, không xét số dư ví, tiền lời hoặc tổng cược nhiều ván.
- Dưới 300.000 xu: giữ tỷ lệ sự kiện 70%.
- Từ 300.000 xu trở lên (bao gồm đúng 300.000): tỷ lệ lượt quay thắng là 40%.
- Các quy tắc công an và thanh toán vẫn áp dụng. Tỷ lệ này là lượt quay của trò chơi, trước các nhánh công an.

## Nguyên nhân và bản vá

`fair.luck_p` trước đây trả 70% cho mọi mức cược trong sự kiện, bỏ qua cơ chế giảm tỷ lệ khi chơi liên tục. Xóc đĩa cho cược đến 1 triệu xu/ván nên mức thưởng tăng rất nhanh. Vé cào trong sự kiện có tiền trả kỳ vọng khoảng 232,52% giá vé do nhóm trúng loại giải hoàn vốn; giữ nguyên theo yêu cầu giữ sự kiện, không áp trần lời mới.

Máy chủ nay chọn 40% khi tiền cược của ván đạt 300.000 xu trong cửa sổ sự kiện. Lô tô và vé cào hiện chỉ cho tối đa 1.000 xu/ván nên vẫn hưởng ưu đãi. Bầu cua và đua chó không thuộc ba trò hưởng sự kiện. Hết sự kiện, quy tắc thường trở lại như trước. Không thêm trạng thái lưu hoặc thay đổi database.

## Xác minh

- Trước vá, kiểm thử tái hiện ván 300.000 xu vẫn có tỷ lệ 70%; mô phỏng 20.000 lượt cược lớn cho 70,11% thắng.
- Sau vá, 50 kiểm thử qua, gồm ranh giới 299.000/299.999/300.000/300.001/1.000.000, đổi cược giữa các ván, số dư lớn, chuỗi thắng/chơi liên tục, mô phỏng 20.000 lượt và hết hạn sự kiện.
- Lệnh: `python -m unittest tests.test_fair_high_stakes tests.test_fair_golden_days.GoldenDraws tests.test_fair_bc_honest tests.test_fair_house_edge.HouseEdge tests.test_fair_house_edge.Reopen tests.test_fair_scratch tests.test_fair_even_balance -q`.
- Hai ca `tests.test_fair_house_edge.ReopenBoard` cần PostgreSQL chưa chạy được do thiếu `TEST_DATABASE_URL`; không dùng database production để chạy kiểm thử.
- Đã triển khai production 2.0.2.1 lúc 13:12:44 UTC+7 ngày 11/10/2026; xem `docs/DEPLOY_2.0.2.1_2026-10-11.md`.
