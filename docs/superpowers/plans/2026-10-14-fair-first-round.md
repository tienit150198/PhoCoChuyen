# Tỷ lệ chợ đen: lượt đầu 55%

## Thiết kế đã chốt theo yêu cầu

Chủ game yêu cầu tăng nhẹ lên 55% ban đầu rồi giảm như hiện tại, và sửa rõ chỉ **một lượt đầu**, không phải mười lượt. Áp dụng chiếu trong, lô tô và vé cào: lượt đầu một đợt 55%; từ lượt hai giảm 1,5 điểm phần trăm/lượt đến sàn cũ (chiếu trong 40,4%; lô tô/vé cào 40%). Giữ luật thắng liên tiếp, cược từ 50.000 xu tối đa 40%, reset đợt chơi, công an, thưởng và sự kiện đã hết hạn. Ném vòng, bầu cua, đua chó và trò kỹ năng giữ nguyên.

55% là xác suất thắng của lượt rút kết quả; vé cào vẫn tính hoàn vốn là trúng. Với thưởng cũ, lượt đầu chiếu trong/lô tô có kỳ vọng dương cho người chơi. Không còn khẳng định mọi lượt đều có lợi cho nhà cái. Tỷ lệ không hiển thị trên giao diện.

## Kế hoạch

- [x] Viết và chạy kiểm thử đỏ: lượt 1/2/3/đến sàn, chuỗi thắng, cược lớn, lịch sử cũ, reset đợt, trò ngoài phạm vi.
- [x] Sửa cấu hình/hàm tỷ lệ trong game/fair.py và alias vé cào trong game/fair_scratch.py.
- [x] Cập nhật mô phỏng, kiểm thử kỳ vọng và tài liệu để phản ánh đúng 55% và giảm ngay từ lượt hai. Mô phỏng phải ghi rõ phạm vi trước công an, không dùng khẳng định nhà cái luôn thắng đã hết hiệu lực.
- [x] Chạy các bộ kiểm thử fair có liên quan và mô phỏng; rà soát độc lập.
- [x] Lưu commit, giữ nhánh hiện tại. Chưa deploy trong lượt này.
