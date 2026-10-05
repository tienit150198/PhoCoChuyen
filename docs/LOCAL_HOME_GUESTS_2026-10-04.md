# Mời bạn về nhà — bản local 2026-10-04

Chưa deploy. Không thay phiên bản hoặc Có gì mới trong thay đổi này.

## Người chơi

- Nút Mời bạn về nhà ngay khu nhà ở trong Hành trình và Nhà của bạn; cũng mở từ Bạn bè, Nhà & Gia đình.
- Mời vào chơi: quyền 2 giờ kể từ khi người nhận đồng ý.
- Mời ở chung: quyền lâu dài, vào được khi chủ offline, không cần kết hôn.
- Người nhận đồng ý/từ chối; chủ thu hồi; khách rời nhà. Cần chủ đang ở căn nhà mình sở hữu.
- Cùng thấy phòng/nội thất hiện tại và nhiều nhân vật. Ôm/hôn/thả tim có chọn người và phản hồi.
- Khách xem nhà bằng dữ liệu riêng, giữ nhân vật/tiền/nhà/bản trang trí nháp của mình. Khách không sửa nội thất của chủ.

## Kỹ thuật

PostgreSQL schema 20: home_guest_invites. HTTP /api/home-guests và các endpoint invite/answer/revoke/leave/view dùng session, CSRF, rate limit; ID lời mời dạng chuỗi opaque.
Quyền gắn đúng nhà và người nhận; kiểm tra ở HTTP/WebSocket. Bán/chuyển nhà, import save, chặn/hủy kết bạn chấm dứt quyền cũ. Ghép bạn lại hoặc bỏ chặn không tự phục hồi lời mời.
Phòng live khóa theo chủ và căn nhà, tối đa 12 người kết nối; giữ cơ chế nhà vợ chồng. Kiểm tra lại quyền sau các thao tác bất đồng bộ trước khi trả người trong phòng.

## Kiểm chứng

- 55 kiểm thử PostgreSQL backend/live cuối cùng: PASS (18 home_guests + 37 live home), 108.485 giây, output/home-guests-final.log.
- 57 kiểm thử HTTP/storage/family/shared decor/schema liên quan: PASS, output/home-guests-integration.log.
- 12 kiểm thử bạn bè/chặn vợ chồng: PASS, output/home-guests-friend-regression.log.
- Node home_guests, home_crowd, family_ux, family, home_affection, home_view, home_redraw, home_wardrobe: PASS.
- Trình duyệt hai tài khoản local chưa kết hôn: gửi/nhận lời mời ở chung, vào phòng thấy 2 món trang trí, cả hai thấy nhau, hôn và Đáp lại, chủ đóng tab rồi bạn vẫn vào lại được, thu hồi khi khách đang ở trong phòng khiến phòng đóng; gửi/nhận tiếp lời mời vào chơi 2 giờ.
- Màn hình 390x844: không tràn ngang, thấy hai nhân vật và nút tương tác; không có lỗi console trong luồng thử.
- Kiểm thử hồi quy cho lỗi ID bị ép số, thu hồi giữa lúc join, chủ đã cưới nhưng ở riêng, kiểm tra đủ hai bản ghi hôn nhân đều tái hiện thất bại trước sửa và đã qua sau sửa.

Môi trường thử dùng PostgreSQL local riêng; không đọc/ghi production.
