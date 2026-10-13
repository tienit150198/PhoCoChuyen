# Chợ đen: 55% ở một lượt đầu

## Phạm vi

Theo chỉnh lại của chủ game, chỉ một lượt đầu mỗi đợt chơi có tỷ lệ cơ bản 55%; không giữ 55% trong mười lượt. Áp dụng chiếu trong, lô tô, vé cào. Lượt 2/3/4 lần lượt 53,5%/52%/50,5%, tiếp tục giảm 1,5 điểm phần trăm đến sàn cũ.

Các mức này còn chịu giới hạn thắng liên tiếp và cược lớn. Một đợt được tính theo cơ chế nghỉ/đổi trò đang có; không reset lịch sử chơi cũ khi phát hành. Không đổi thưởng, công an, luật sự kiện, các trò xúc xắc/trọng số cố định hoặc trò kỹ năng.

Vé cào vẫn tính hoàn vốn là trúng: ở lượt đầu, xác suất có lời theo bảng giải hiện tại là 55% × 34,5% = 18,975%, trước công an và Lộc.

## Kiểm chứng

- Trước sửa: bộ hồi quy mới có 5 ca thất bại đúng yêu cầu mới (tỷ lệ đầu, giảm ngay, điều kiện reset và kết quả lệnh); ca giữ nguyên ném vòng đã đạt.
- Sau sửa: 6/6 kiểm thử mới đạt, gồm lệnh chiếu trong/lô tô/vé cào thật ở ranh giới thắng/thua của bốn lượt đầu; kiểm tra lịch sử cũ, nghỉ 600/601 giây, ba lượt đổi trò đủ tiền, cược lớn, chuỗi thắng và ném vòng. Bộ tập trung ban đầu 33 ca đạt trong 38,66 giây.
- Tổng cộng **244 ca được chọn đã kiểm chứng đạt qua nhiều lượt chạy có giới hạn**, không phải một lần chạy toàn bộ cuối cùng. Sau sửa fixture, nhóm StoreLoc + Arrest chạy cuối đạt **15 passed, 6,82 giây**; các nhóm đã đạt và không thay đổi không chạy lại. Phạm vi chọn là 244/261, loại 17 ca OAQ/ảnh/bản rất cũ ngoài phạm vi, gồm hai ca tương thích nghề cũ được phân tích riêng bên dưới. PostgreSQL cục bộ được dùng cho các ca lưu/đọc và idempotency.
- Rà soát yêu cầu và chất lượng độc lập đều đạt. Các phép kiểm kỳ vọng cũ được thay bằng số chính xác của cấu hình mới, không nới sai số để che lỗi.
- Bộ rộng bị dừng ở 35% được đối chiếu thứ tự thu thập và chạy lại: hai lỗi ở `test_fair_dog::OldServer` và `test_fair_forever::OlderServers` do bản rất cũ không chấp nhận danh sách nghề mới. Cả hai vẫn lỗi khi khôi phục toàn bộ tỷ lệ/grace cũ trong tiến trình kiểm thử (2 failed, 14,50 giây); không sửa production hoặc bỏ qua như thể đã đạt.
- Nhóm Board phụ thuộc ngày thật cũng tái hiện lỗi với cấu hình cũ. Chỉ sửa fixture của nhóm đó để `fair_board.now` dùng đồng hồ giả lập hiện có; giữ nguyên các khẳng định trao danh hiệu đúng một lần.
- Ca vé cào so sánh ảnh hưởng lợi nhuận cần nghỉ đủ giữa từng lần so sánh để tách khỏi giảm do chơi liên tục. Ca StoreLoc dùng chuỗi rút cũ có lượt dẹp chiếu cho cược nhỏ, cũng lỗi khi dùng tỷ lệ cũ; sửa chuỗi giả lập đúng thứ tự hiện tại, giữ các khẳng định số dư/thống kê khi retry. Ca RNG công an tắt rồi khôi phục context Lộc để phép đo không lẫn lượt rút thưởng Lộc của bài trước. Rà soát độc lập các fixture cuối cũng đạt.

Mô phỏng một triệu lượt cho mỗi trò/mỗi cách chơi, dùng hàm rút kết quả và thưởng thật, trước công an:

| Trò | Nghỉ đủ giữa các lượt | Chơi liên tục | Tăng cược khi chưa bị hạ do chuỗi thắng | Nghỉ đủ, thêm Lộc |
|---|---:|---:|---:|---:|
| Chiếu trong | 108,50% | 80,90% | 110,01% | 110,07% |
| Lô tô | 113,92% | 84,04% | 115,39% | 115,31% |
| Vé cào | 97,49% | 72,14% | 98,73% | 98,07% |
| Bầu cua | 95,24% | 95,47% | 95,21% | 96,63% |
| Đua chó | 93,52% | 93,92% | 93,76% | 94,09% |

Đây là tỷ lệ tổng tiền trả về/tổng tiền cược, không phải xác suất thắng. Giả lập giữ giới hạn chuỗi thắng kể cả khi nghỉ đủ; mô hình Lộc giả định cổng luôn sẵn sàng. Không bao gồm bắt/phạt hay hành vi toàn server. 20.000 lượt tạo bảng lô tô thực: 55,66% được rút cho người chơi, bảng khớp kết quả rút 100%. Với luật reset hiện tại, nghỉ hoặc đổi trò hợp lệ có thể duy trì kỳ vọng dương ở chiếu trong/lô tô trước công an; không khẳng định nhà cái luôn thắng.

## Phát hành

Chưa deploy. Không thay schema, số dư hoặc dữ liệu người chơi trên production.
