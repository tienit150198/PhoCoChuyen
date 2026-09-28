> Lịch sử phạm vi v0.2, không phải trạng thái v0.3.

# Phạm vi thực tế v0.2.0

Bản thiết kế gốc là định hướng dài hạn. Bảng dưới đây mô tả **mã đang chạy trong ZIP**, không đánh đồng dữ liệu seed với tính năng production.

| Nhóm | Có trong bản này | Giới hạn / chưa làm |
|---|---|---|
| Danh mục | 4 nghề chơi được, 12 nghề khóa có giới thiệu | 12 nghề sau không có engine hoặc nhiệm vụ chơi |
| Cảnh game | Canvas mặt tiền boba/pastel, bố cục ngang/dọc, nhân vật đi bằng tìm đường, hitbox đồ vật, nhân viên/khách/mèo và công an NPC | Vector nguyên bản; chưa phải tranh chibi nhiều lớp theo ảnh tham khảo. Chưa có bản đồ nhiều khu phố |
| Thao tác nghề | Bốn bàn tương tác có luật khác nhau, xác nhận và sửa trước chốt | Tương tác chi tiết chủ yếu nằm trong cửa sổ bàn nghề; chưa có animation tay lấy từng vật hay mini-game kéo thả mọi món trong cảnh |
| Tiệm mẹ & bé | 8 mã hàng, giỏ giữ tồn, yêu cầu/ngân sách/màu, giấy+nơ+thiệp, kiểm, giao, review | Đơn online và lịch nhận nhiều khung giờ chưa thành một hệ thống riêng; hẹn hiện là giữ việc sang lúc khác |
| Nhà thuốc | 6 mã hư cấu, 18 lô mẫu, kiểm nhãn/số lượng/hiệu lực, ba dấu kiểm, chuyển người phụ trách, nhập kho | Không có chẩn đoán/thuốc thật. `ph_quarantine` / `ph_release` có luật backend và test; chưa có màn quản lý lô riêng cho tất cả thao tác này |
| Kế toán | Nhiều-một, một-nhiều, trùng nguồn, lỗi số, thiếu nguồn, khoản hoàn; nhóm đối chiếu và lý do từ nguồn | Chưa có trình thiết kế báo cáo, bộ phiên bản báo cáo hoặc hệ thống kế toán thực |
| CSKH | Xác minh, chứng cứ, phương án, thực thi qua nhịp game, kiểm kết quả, đóng, bàn giao | Hẹn và phối hợp là mô phỏng ngắn theo lượt, không tích hợp kho/giao hàng hoặc CRM thật |
| Chat | Nút nhanh và tự gõ; trả lời theo từ khóa/ngữ cảnh nghề; ghi lịch sử; ký ức có event nguồn | Không phải LLM đầy đủ ở mặc định, không hiểu mọi câu. AI adapter chỉ diễn đạt câu chuẩn |
| Sự kiện | 96 vignette được biên dịch từ 96 seed; mỗi vignette có hai chứng cứ, hai lựa chọn và hai bước thực hiện; có một số kịch bản chuyên biệt | **Không phải 96 mini-game riêng biệt.** Các bước thực hiện dùng bộ khung chung, không mô phỏng mọi vật lý/điều tra/nhánh truyện trong tài liệu |
| Điều phối | Một chuyện nổi bật sau việc đầu; chọn theo nghề, ngày và chế độ; có nhắn nối tiếp ngày sau; một sự kiện đang mở | Chưa có hệ mô phỏng xã hội quy mô lớn hoặc đạo diễn truyện tự sinh |
| Diễn tập | Mở 24 tình huống/nghề từ Sổ tay, giữ rõ nhãn, không tác động xu/XP/quan hệ | Không cộng vào thành tích chơi thật |
| Tuyến truyện | 12 tuyến mục tiêu, ba milestone/tuyến, thưởng một lần và kỷ vật | Bản này là tiến trình theo cột mốc; chưa hiện thực hóa toàn bộ đối thoại phân nhánh/cutscene/tổ chức hội chợ của tài liệu |
| Review và feed | Review NPC từ việc hoàn thành; bài người chơi local; NPC bình luận; trả lời và dấu yêu thích | Chưa có tài khoản, review người thật hay mạng xã hội. Nút xem vụ review mở vignette kiểm tra, không làm hoàn tiền/gửi bù tự động |
| Trang trí | Tông phòng, cây, thảm, đèn, ghế, tranh và các vị trí đặt hỗ trợ; có ảnh canvas thật | Không phải editor kéo-thả không giới hạn, chưa có đường đi mới cho NPC trên mọi đồ trang trí |
| Nhân viên v0.2 | 16 ứng viên, tuyển, lịch ca, phân công, nghỉ, hướng dẫn, thưởng, nhắc nhở, chấm công theo hành động, trao đổi, kết thúc hợp tác; nhân vật trong cảnh | Tự động hóa theo quy tắc và nhịp game, không phải LLM tự làm mọi nghề hoặc hệ thị trường tuyển dụng |
| Sai sót / phá đồ | 4 loại sự cố, đọc nguồn/nghe giải thích, sửa có hóa đơn, tạm ngừng giúp, kiểm kết quả; có sự cố tự nhiên và diễn tập | Dùng hệ sự kiện, không có mô phỏng vật lý đập/vỡ 3D hoặc vô số cutscene |
| Chi phí / thuế / thuê | Lương ca có thực làm, điện nước, bảo vệ, sửa; thuê theo từng ca, kết kỳ 7 ca, thuế game 5%, biên nhận, gia hạn, đối chiếu ví | Tham số hư cấu. Chưa cưỡng chế nợ/đuổi tiệm, không có vay/lãi, không mô phỏng thuế pháp lý thật |
| Mặt bằng | 3 cấp thay đổi thuê, sức chứa, số chỗ nhân viên và vật thể trong cảnh | Không phải 3 địa chỉ/map riêng, chưa có nhiều chi nhánh đồng thời |
| An ninh v0.2 | Để nhầm/quên thanh toán/trộm/giật túi NPC; kiểm chứng, công an NPC, thu hồi đúng tài sản, thưởng giới hạn, hồ sơ lưu; camera/chuông/khóa/đèn | NPC/công an/quỹ thưởng là hư cấu. Không truy đuổi/bạo lực, không tích hợp dịch vụ thật, không PvP |
| Hỗ trợ thiệt hại | Phí gói theo ca; phải bật trước vụ; bù 60% phần chưa thu hồi; chặn bồi hoàn trùng | Không phải bảo hiểm pháp lý hay giao dịch tiền thật |
| Công cụ / phụ tá cũ | Giữ nguyên nâng cấp và hỗ trợ một lần/ngày của v0.1 để tương thích | Không tự chuyển thành nhân viên có lương; bảng hẹn chưa phải lịch hẹn đầy đủ |
| Ngày và nhịp | 2/3/4 việc tùy chọn, thêm việc có giới hạn, giữ việc sang ca, không phạt nghỉ; tiến nhịp theo thao tác | Ba chế độ chủ yếu khác số việc và lọc sự kiện; chưa cân bằng theo playtest người thật hoặc có time-pressure nâng cao |
| Lưu | SQLite, phiên cookie, revision, chống gửi lặp, export/import v1/v2, migration schema 1→2 không hồi tố chi phí, reset riêng nghề | Chưa có đăng nhập, cloud sync, anti-cheat cho hệ thống cạnh tranh; bản backup người chơi sở hữu không phải chứng nhận thành tích |
| Mobile | Bố cục portrait, nút chạm, thanh cuộn, chữ lớn, giảm chuyển động | Đã kiểm viewport Chromium mô phỏng; chưa kiểm trên iPhone/Safari vật lý, chưa là ứng dụng native |
| Triển khai | Server Python stdlib, script Windows/macOS/Linux; Docker recipe bổ sung | Local/LAN playtest, chưa được harden cho Internet; Docker chưa build trong môi trường này |

## Cách mở rộng mà không phá game hiện có

Giữ các hành động kinh tế trong `game/engine.py` và `game/operations.py`; UI chỉ gửi ý định và payload. Nội dung mới có thể dùng `game/content.py`, `game/events.py` và baseline `reference/data/`. Đổi cấu trúc save phải tăng phiên bản schema và thêm đường migrate/test. Không sửa file seed rồi cho rằng trạng thái đã lưu tự động cập nhật an toàn.

`reference/data/command.schema.json`, `command_examples.json`, backlog và acceptance tests là tài liệu thiết kế cũ, **không phải hợp đồng HTTP đang chạy**. Hợp đồng hiện hành ở `docs/API.md`, reducer và các test.

Để chuyển sang phát hành có người dùng thật, cần một vòng riêng về tài khoản, HTTPS, kiểm duyệt, quyền riêng tư, load test, quản trị, backup/migration, chống abuse và kiểm thử trên thiết bị đích.
