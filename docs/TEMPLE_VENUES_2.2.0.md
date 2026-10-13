# Đi chùa và không gian đi chơi — 2.2.0

## Người chơi vào bằng cách nào

Trong phần nhân vật có nút **Vào chùa** và **Đi chơi & làm đẹp**. Cửa chùa/quán/spa/rạp trên phố cũng mở thẳng cảnh đi bộ. Cảnh có nhân vật, đồ đạc cản đường, các góc tương tác và lối ra; chạm sàn, dùng mũi tên/WASD hoặc cần di chuyển. Đến một góc mới mở hoạt động tương ứng. Đóng bảng dịch vụ quay lại phòng ở vị trí vừa đứng.

Chùa gồm sân, chánh điện và nhà ăn. Có thắp hương, đánh chuông, ngồi tĩnh tâm, viết lời nguyện, quét sân, khấn, tụng kinh và cơm chay khi có phục vụ. Nút công đức giữ chức năng quyên góp cũ.

## Lặp hoạt động và lời chúc

- Bỏ hạn mức việc/ngày và hạn mỗi loại một lần. Người chơi vẫn làm được khi tinh thần đã đầy; tinh thần giữ thang 0–100 và kết quả chỉ báo phần thực tăng.
- Cơm chay giữ điều kiện rằm/mùng một và bụng chưa no. Các điều kiện dịch vụ ngoài chùa không đổi.
- Lời chúc chọn người nhận, điều cầu mong, tên riêng tối đa 40 ký tự và lời nhắn tối đa 140 ký tự. Có lựa chọn may mắn cho người đang sống.
- Thẻ mặc định riêng tư. 40 thẻ gần nhất theo bản lưu; thẻ cũ lưu ở archive và đọc bằng **Xem cũ hơn**. Đây là giới hạn tải một lần, không phải giới hạn số thẻ được viết. Thẻ giữ khi sang ngày và tải lại; lệnh gửi trùng không tạo thẻ thứ hai.
- Không thêm cơ chế cầu may tăng tiền/xác suất trúng thưởng; hiệu quả trong phiên bản này là tinh thần.

## Các phòng đi chơi

14 không gian: quán cà phê, spa, rạp phim, karaoke, sân chơi thú cưng, salon, làm móng, thủ công, hiệu sách, xưởng vẽ, phòng nhạc, thư viện, vườn cộng đồng và góc gia đình. Vào cửa và xem dịch vụ miễn phí; giao dịch thực vẫn dùng giá và xác nhận hiện có. Các buổi sinh hoạt cộng đồng giữ quy tắc lưu một buổi/ngày sống.

Câu cá, chèo thuyền, bơi đã có cảnh riêng; đường vào nay dùng chung cho giao diện cũ/mới. Công viên, hội chợ và nhà ở giữ cảnh sẵn có. Ngân hàng, sổ nghề và các mục quản lý vẫn là bảng chức năng.

## Dữ liệu và vận hành

Không đổi bảng DB hoặc sửa hàng loạt hồ sơ. Bản chùa v1 cũ không có cards vẫn hợp lệ; trường cards là tùy chọn, archive ghi nguyên tử cùng lệnh. Sau khi hồ sơ đã có cards hoặc hơn bốn loại hoạt động trong ngày, không chạy lại bộ kiểm tra chùa 2.1.0: dùng bản sửa tiến tương thích 2.2.x.

## Kiểm chứng trước phát hành

- 72 bài chùa/dịch vụ/đi chơi/cộng đồng đạt; kiểm tra thực PostgreSQL có lặp 43 thẻ, chống gửi trùng, quyền riêng tư, lưu trữ và phân trang.
- 26 bài tài nguyên và bản dịch đạt. Bộ lưu trữ/mã bảo vệ đạt 47 bài, một assertion mã lỗi nhập bản lưu đã thất bại y hệt trên baseline 2.1.0 (`import_other` thay vì `import_richer`); không sửa ngoài phạm vi.
- Chùa: bốn lượt trình duyệt thật 390/1280px, giao diện cũ/mới, sáng/tối/giảm chuyển động; lặp hương, lời chúc, cầu may, đọc lại sau tải lại/sang ngày. Lượt riêng 43 thẻ đọc được thẻ đầu tiên và đóng/mở công đức giữ vị trí. 1.756 đường đi đạt.
- Phòng: cả 14 bố trí kiểm tra vật cản/đường đi; thử phím, cảm ứng, cửa ra và tạm dừng/tiếp tục. 13 kiểm tra đường vào trong ứng dụng đạt, ví không đổi khi chỉ tham quan và đóng dịch vụ về đúng vị trí, không lỗi trình duyệt.
- Ảnh và báo cáo ở `output/temple-walk/` trong máy phát triển; không đưa dữ liệu người chơi thật vào kiểm thử.
