# Đồ độc bản và Top nhà sưu tầm

## Kết quả

- Vẽ lại 10 tranh cũ theo chủ đề riêng; bổ sung 4 tranh mới: **Long vân sơn mài**, **Hạc trên nền ngọc**, **Vịnh ngọc ban mai**, **Ngân hà khảm trai**.
- Hình SVG dùng chung ở nhà đấu giá và tranh treo trong nhà. Mỗi tranh có tác giả, năm, chất liệu, câu chuyện và độ hiếm. Không tải hình từ bên ngoài.
- Làm lại cách trình bày biển số, SIM, danh hiệu và danh thắng. Hàng chọn phiên có ảnh thu nhỏ, cuộn ngang; Của tôi hiển thị phòng tranh.
- Thêm **Top nhà sưu tầm** ở nhà đấu giá và tab **Sưu tầm** trong Bảng xếp hạng. Bảng hiển thị điểm, số độc bản, số món huyền thoại và vị trí của bạn.

## Giá trị sưu tầm

| Độ hiếm | Điểm / món |
|---|---:|
| Phổ thông | 10 |
| Quý hiếm | 40 |
| Huyền thoại | 120 |

Chỉ tính món trong danh mục đã nhận vào bản lưu. Bằng điểm: nhiều món hơn, nhiều huyền thoại hơn, rồi ai đạt điểm trước. Không quy đổi điểm thành xu; giá trả và tiền đang giữ không tăng điểm. Bốn tranh mới dùng giá khởi điểm hiện có: hai món 50.000 xu, hai món 500.000 xu. Biển số/SIM do quản trị tự đặt ngoài danh mục vẫn sở hữu được nhưng chưa tính điểm.

## Tương thích

- Giữ nguyên mọi ID cũ, quyền sở hữu, giá chốt và cơ chế giữ/hoàn tiền. Không thay schema.
- Phân biệt độ hiếm trong danh mục với mức giá phiên mà quản trị có thể tùy chỉnh.
- Bảng mới dùng quyền hiện/ẩn tên chung. Người ẩn tên vẫn xem điểm và vị trí giả định của mình.
- Leaderboard VERSION 4 tự bổ sung điểm cho người đã sở hữu đồ. Lệnh sau nâng cấp tự phục hồi hàng top nếu máy chủ cũ xóa hàng khi chạy xen kẽ.
- Migration phục hồi đúng một tranh vào túi nếu máy chủ cũ đã ghi nhận thắng nhưng chưa biết ID đồ trang trí; không nhân đôi tranh đang có.

## Kiểm chứng

- PostgreSQL 17 riêng, chỉ nghe localhost, Python 3.12 + websockets 17.1 theo phiên bản thư viện dự án.
- **117/117 test Python đạt**: auction, auction_collections, leaderboard, live_auction, deco, deco_more, deco_viet.
- JavaScript: 14 bố cục khác nhau sau khi bỏ màu, 6 danh thắng, tranh treo nhà dùng chung SVG; escaping và trạng thái tải/rỗng/lỗi/ẩn tên.
- Kiểm tra Safari 15: 311/311 file; cú pháp các module sửa; git diff --check.
- UI thật ở 390×844 và desktop bằng dữ liệu mẫu cục bộ: phiên, phòng tranh, bảng top và tab Sưu tầm. Không có lỗi console.
- Sửa race trong test hủy theo dõi đấu giá: chờ pong trên cùng socket trước khi phát sự kiện NOTIFY từ kết nối khác.
- Code review đã kiểm tra sửa lỗi khôi phục tranh và phân biệt độ hiếm/mức giá.

Ảnh kiểm chứng: `output/auction-preview/collection-detail.jpg`, `mobile-lot.jpg`, `mobile-top.jpg`, `mobile-board.jpg`. Nhật ký kiểm thử: `output/auction-final-tests.log`.

Chưa triển khai lên production.
