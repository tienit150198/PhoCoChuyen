# Phát hành production 2.0.0 — 11/10/2026

Đã triển khai lên https://phocochuyen.io.vn trên máy chủ được chủ game chỉ định. Thời gian trong báo cáo là UTC+7.

## Bản đang chạy

- Rolling hoàn tất lúc **10:33:33**, mã thoát 0. HTTP và live đều chạy từ `/opt/mot-ngay-lam-nghe/releases/2.0.0-20261011103230`; public health trả `2.0.0`, build `2.0.0+a5873c6b4ff6`.
- Source ứng viên: `253bc53c91eb6fdbeab14ea7381ebe08ccee2f19`. Các commit tài liệu sau đó không thay đổi mã trong gói.
- Gói `mnl-2.0.0-dual-interface.zip`: 103.267.831 byte, SHA-256 `6d17685e35cb780a41a276578decc54c3d3805a241eb14ac7983074ca9a87f8b`.
- Manifest production đã tải về `MANIFEST.json`: SHA-256 `eb822c13a05b204c6cde23133411aa76351d77fb47083d0d5c4d7e1ff58d5528`.
- 1.525 file runtime còn lại sau bước loại tests/artifacts của rolling đều khớp mã băm. Trước rollout, baseline 1.9.48 thực trên máy chủ cũng khớp manifest đã kiểm.

## Dữ liệu, dependency và cấu hình

- Backup PostgreSQL 3,1 GB: `/var/backups/mot-ngay-lam-nghe-pg/release-2.0-20261011/phocochuyen-20261011-032125.dump`; backup thoát 0, đọc mục lục bằng `pg_restore -l` thành công. Chưa thực hiện diễn tập phục hồi dump này vào database khác.
- Giữ toàn bộ release cũ với `KEEP=999`. Bản trước: `/opt/mot-ngay-lam-nghe/releases/1.9.48-20261010230537`.
- Lưu cấu hình cũ và rolling script tại `/root/mnl-release-2.0-20261011/`. Không đưa thông tin xác thực vào source, log nghiệm thu hoặc tài liệu.
- Cài Pillow 12.3.0 có WebP trong `/opt/mot-ngay-lam-nghe/shared/release-2.0-python`, không thay Python hệ thống. Đã kiểm trong môi trường thật của service.
- File `/etc/mot-ngay-lam-nghe/release-2.0.env` và drop-in `zzzzzz-release-2.0.conf` cho HTTP/live bật `LIVE_TOWN`, `LIVE_TOWN_TREASURE`, `LIVE_HOME`, `LIVE_VISITS`, bổ sung đường dẫn dependency. Cả HTTP và live xác nhận nhận đúng cờ.
- Nginx giữ giới hạn body 16m; `LAZY_SAVES=0` được giữ. Không sửa site khác trên máy chủ.
- PostgreSQL `max_connections=200`; canonical 8 worker × pool tối đa 12, bridge 8 × tối đa 3, live pool 8 và một LISTEN. Bridge đặt pool khởi đầu 1, `MemoryMax=3G`; canonical giữ 8G, live 768M. Đây là ngân sách rollout, không phải kết quả thử tải 1.000 CCU.

## Kiểm tra production

- **342 mẫu HTTP health, không mẫu lỗi**, quan sát chuyển 1.9.48 → 2.0.0. Lấy mẫu khoảng hai giây một lần, không chứng minh không có lỗi giữa các mẫu.
- Live khởi động lại, đóng kết nối cũ bằng 1012; healthy sau khoảng 7 giây, không có lần restart lỗi. Đã thấy kết nối người chơi trở lại. Không có Traceback/CRITICAL/RuntimeError/ModuleNotFoundError trong kiểm tra log khởi động.
- Kiểm tra cuối lúc 10:42: HTTP/live healthy, cả hai service active và `NRestarts=0`; live có 79 kết nối, bộ nhớ HTTP khoảng 2,14 GiB, live khoảng 121 MiB; load average một phút 2,12 trên máy 9 core, đĩa còn 30 GB. Đây là ảnh chụp tải thực tại thời điểm kiểm tra, không phải bài tải cực đại.
- Bảy nhóm smoke HTTPS/WSS đạt: health/static, mặc định giao diện mới, đổi cũ/mới và tải lại giữ nghề/tiến trình, export đủ 50 nghề, hai người thấy nhau và nhận đổi trang phục ngay trong phòng, rương có đợt 3–5 chiếc, góp ý ba ảnh có phân quyền.
- Ảnh PNG/JPEG/WebP của góp ý kiểm thử **335** được đọc bởi chủ ảnh; người khác bị 404, cache riêng `no-store`. Không xóa ảnh; giữ đúng yêu cầu chỉ xóa khi chủ game yêu cầu.
- Trình duyệt production hiển thị phố 2.5D, công tắc **Cài đặt → Giao diện → Giao diện mới**, bố cục desktop và tin ghim 2.0. Console ở lượt kiểm tra trước khi mở settings không có error.
- Hai lần probe đầu so sánh ví ngay trước quà hệ thống của phiên quay lại gây báo lỗi kiểm thử. Sau khi đọc lại bootstrap để ổn định quà hiện có, probe cuối đạt; không sửa luật tiền hoặc mã game để làm test qua.

Báo cáo/log/ảnh cục bộ nằm trong `output/release-2.0-local/`: `production-smoke-report.json`, `production-smoke.log`, `production-health-watch.jsonl`, `production-settings-2.0.png`, `production-release-announcement.png`, `production-2.0.png`. Thư mục này không đóng gói hoặc commit. Kiểm tra source, ZIP, viewport mô phỏng mobile/tablet và giới hạn bao phủ ở [readiness](RELEASE_2.0.0_READINESS.md) và [hai giao diện](qa/dual-interface-2026-10-11.md). Chưa chứng minh FPS trên mọi thiết bị hoặc khả năng phục vụ 1.000 CCU.

## Hai ngày vàng và thông báo

- Kích hoạt bằng script vận hành **sau khi smoke production đạt**: từ **10:39:43 ngày 11/10/2026** đến **10:39:43 ngày 13/10/2026** (đủ 172.800 giây).
- Marker `fair_golden_days_20261011` có starts `1791689983`, ends `1791862783`. Chạy kích hoạt lại không thay đổi thời hạn. Assertion của wrapper ban đầu so cả trường `created` nên báo lỗi sau khi publish thành công; đọc lại starts/ends và dữ liệu ghim trực tiếp đã xác nhận đúng. Không kéo dài sự kiện.
- Tin quản trị **33045** đã đăng và ghim ở kênh `town`; marker `release_notice_2_0_0` trỏ đúng tin này. Đã đọc lại database và thấy thông báo thật trong trình duyệt người chơi.
- Nội dung giới thiệu giao diện mới, nơi làm nghề, avatar/phụ kiện, nhà 3D; hướng dẫn tắt giao diện mới trong Cài đặt; góp ý tối đa ba ảnh; hai ngày vàng áp dụng Chiếu trong, lô tô, vé cào. Thông báo công khai ghi thời hạn **10:39 ngày 13/10/2026**, không công bố xác suất.

## Quay lui khi cần

Chạy rolling với bản cũ đã giữ, sau đó kiểm tra HTTP, live, tiến trình đang mở và ảnh góp ý. Không phục hồi database cũ một cách tự động vì sẽ mất tiến trình mới của người chơi.

```bash
KEEP=999 BRIDGE_PG_POOL=1 BRIDGE_PG_POOL_MAX=3 BRIDGE_MEMORY_MAX=3G \
  /usr/local/sbin/mnl-rolling-release --to /opt/mot-ngay-lam-nghe/releases/1.9.48-20261010230537
```

Rollback mã không tự xóa sự kiện hoặc thông báo đã phát hành; cần cập nhật thông báo vận hành nếu tính năng không còn phục vụ. Bằng chứng tương thích save với 1.9.48 được ghi trong readiness. Giữ ảnh góp ý đã nhận; không chạy lệnh dọn dữ liệu hoặc release cũ trong đợt này.
