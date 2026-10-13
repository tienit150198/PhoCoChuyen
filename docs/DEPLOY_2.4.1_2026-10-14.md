# Phát hành 2.4.1 — chuyên môn nghề và sửa chat/zoom

Đã phát hành lúc 06:00:24 UTC+7 ngày 14/10/2026 tại https://phocochuyen.io.vn.

- Source: `40999f121be087940f6c1709c2115d5f02fb80bd`; base cho lần phát hành tiếp theo.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.4.1-20261014055922`.
- Build: `2.4.1+5a413747ada1`.
- ZIP: `C:/Users/ADMIN/AppData/Local/Temp/mnl-scale-20261014/mnl-2.4.1.zip`, 104.510.970 byte.
- SHA-256: `c6db0555e64938d63e49b0646883b650dc6f315a180c033a777c4c5b693d6aec`.

## Nội dung

Map 2.5D: khung Nói gần đây dành khoảng riêng phía trên bộ điều khiển máy ảnh, kể cả khi mở zoom. Chat, reaction, phím nhập và nút máy ảnh hoạt động ở màn hình nhỏ, ngang và desktop.

Vào nghề → Thăng tiến → Chuyên môn nghề: đủ 54 nghề × 10 gói, có định lượng, ba bước thao tác và kiểm bàn giao riêng. Học phí tuần tự 3.000 đến 100.000.000 xu, tổng 152.692.000 xu mỗi nghề thu phí; chùa miễn phí. Cần kinh nghiệm, việc sạch và ngày thực đủ chuẩn. Thực hành đạt ít nhất 80%, bắt buộc đúng định lượng và kiểm bàn giao; thử lại miễn phí.

Mở gói rồi nhận đơn chuyên môn, mua và nhận vật tư, cam kết, làm năm bước và quyết toán. Kho dùng quyền sức chứa/nhập đã mua; hàng đang về/giữ cho đơn vẫn chiếm chỗ. Giá vốn FIFO, tiền công và thuế có biên nhận. Dự toán là khi đúng 100%; trước khi bắt đầu hiển thị khoản còn lại ở 80% và rủi ro mất vật tư/công khi làm sai. Biên nhận ghi tỷ lệ nghiệm thu và bước đúng/sai. Công vụ nhận hiện vật và phụ cấp; chùa tăng tinh thần trong trần100. Đơn dùng chung suất quản lý: khởi đầu1, +4/ngày thực, tối đa12; một người trực tiếp làm một đơn chuyên môn mỗi lần.

## Kiểm chứng

- 596 kiểm thử chuyên môn/catalogue/build đạt, gồm 540 luồng thực thi đủ nghề × bậc. Bao gồm học phí, thử lại, kho đang về/giữ chỗ, giá vốn lịch sử, nhập bản lưu sai sức chứa, quyết toán sai, Store stale/replay/reload/rollback, quyền việc làm và DTO.
- 52 ca hồi quy scale/quota/kho/hợp đồng/Store/hạn mức nhập đạt. Node UI kiểm tra hiển thị, escaping, validation và chống gửi hai lần đạt.
- 53.280 mẫu nhiệm vụ khớp bản2.4.0. Danh mục có1.620 chuỗi thao tác khác nhau, tiêu đề khớp danh mục đã duyệt; ba JSON bắt buộc và tham gia build fingerprint.
- Review độc lập tìm và sửa giới hạn kho khi nhập save, thông tin rủi ro nghiệm thu và lý do khóa học bị chặn. Đồng bộ đặc tả mức đạt80%.
- Gói được xây từ ZIP2.4.0 chính xác;2.422 hash khớp. HTTP từ bản giải nén đạt tạo nhân vật/mở ca/replay/export. Browser thực với PostgreSQL ở390/1280px đạt trọn luồng học/nhập/nhận/làm/quyết toán trên source và chính gói đã nén.
- Map dùng Phaser/shell/social thực, mô phỏng riêng transport:6 viewport390×844,320×568,844×390,1280×860,768×1024,390×500. Không chồng chat/zoom, nút zoom thay đổi camera, gửi chat/emote/reaction được, nhập phím không di chuyển nhân vật.390×500 là viewport thu nhỏ, không phải thử bàn phím OS thật.
- Rolling exit0; game/live active, bridge inactive.1.664 hash runtime đúng;758 file tests bị installer bỏ có chủ đích.7 asset quaHTTPS khớp. Health đúng2.4.1/54nghề. Browser public390/1280 trả200, app hiện, không pageerror.
- Journal game/live từ05:59:20 không có Traceback/CRITICAL/ModuleNotFoundError/No space left/ERROR. Live process bật town/chat/treasure. Còn5.607.821.312byte trống sau deploy.

MANIFEST.json lấy từ release đang chạy; giữ bản cũ và DB. Đã dừng scratch PostgreSQL55433, các HTTP kiểm thử tự dừng. Bằng chứng ở thư mục C temp nêu trên và output/playwright trong source/gói giải nén.

## Giới hạn và khôi phục

Gói chuyên môn phục vụ nhánh đơn riêng, không thay công thức/kho/nhiệm vụ cũ. Nhãn chính có English; nội dung tình huống mới hiện fallback tiếng Việt. Tiến trình ngày thực kiểm tra bằng fixture, không giả đã chơi280ngày; không khẳng định thời lượng thực tế mỗi đơn. Thao tác là mô phỏng game, không hướng dẫn hành nghề ngoài đời.

Không đổi schema DB nhưng có dữ liệu chuyên môn mới. Khi người chơi đã dùng, ưu tiên bản sửa tiến tương thích2.4.1; không làm theo gợi ý rollback cuối rolling log để hạ mù về2.4.0, không khôi phục DB để quay mã.
