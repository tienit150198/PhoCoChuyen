# Phát hành chứng chỉ kinh doanh 2.0.6 — 13/10/2026

Đã triển khai tại https://phocochuyen.io.vn, hoàn tất lúc 10:48:49 UTC+7.

## Bản chạy

- Release `/opt/mot-ngay-lam-nghe/releases/2.0.6-20261013104746`.
- Health `2.0.6`, build `2.0.6+b46878d51540`; source `ca19d423afe224d0545839908fcbca4c33ed6682` đã push main trước phát hành.
- ZIP 103.497.826 byte, SHA-256 `e9b736176c458b44a5b499cbca17a2af78da65a43580f646383278ad6d6aafbe`.
- Dựng từ bản live 2.0.5, baseline tái tạo `b18d14456b654a0dc123a8910cb530f991c89544`: 1.752 file giống nguyên byte và 471 asset minify tái tạo đúng. Baseline bổ sung 38 file tài liệu/test lịch sử đúng manifest, không thay runtime bằng phỏng đoán.
- Gói mới có 2.234 file trong manifest, thay/thêm 75 file, không xóa file; phần ngoài tính năng là tài liệu/test lịch sử đã có trên main. Chỉ minify 7 asset thay đổi, giữ nguyên asset còn lại của live.
- Guard kiểm release cũ, manifest cũ và mã băm ZIP trước rolling. `KEEP=999` giữ các release cũ. Không thay đổi bảng DB hoặc sửa hàng loạt bản lưu người chơi.

## Hành vi đã bật

Ba khóa kinh doanh đóng học phí lần lượt 550 / 2.200 / 5.500 xu tại chỉ số giá hiện tại; thi lại nửa phí. Xe đầu miễn giấy, nhiều quầy nhỏ cần cơ bản, tối đa hai ki-ốt cần nâng cao, từ ba ki-ốt cần quản lý chuỗi. Không có thưởng xu hoặc nhân lợi nhuận khi đỗ.

Chủ từ ba quầy thiếu giấy nhận biên bản trong phiên chơi, 72 giờ thực kể từ lần nhận đầu tiên. Trong hạn quầy cũ tiếp tục bán. Quá hạn chỉ chặn phần vượt quyền, ngừng chi phí tự động, giữ đơn đã nhận và một quầy sinh kế cho chủ cũ. Đi học và thi đủ sẽ khôi phục quyền tương ứng; không tự mở quầy chủ đã đóng. Có chọn quầy ưu tiên và đường dẫn đi học/quay lại giao dịch đang xem.

Nội dung và thông báo có tiếng Anh. Không thêm popup Có gì mới toàn hệ thống. Chi tiết vận hành/cờ tắt ở [BUSINESS_LICENSES_OPERATIONS.md](BUSINESS_LICENSES_OPERATIONS.md).

## Bằng chứng kiểm thử

- Lượt nghiệm thu cuối: **103 kiểm thử Python đạt**, gồm chứng chỉ, điều kiện/biên bản, quầy liên tục, hàng khách của chủ và lưu trữ PostgreSQL (DB thử cục bộ riêng).
- Các lượt backend trước đó: 70 và 89 kiểm thử đạt, có phần trùng; bao gồm truy cập chủ, cache, khách người chơi và cạnh tranh quyết toán. Không cộng các lượt thành số test duy nhất.
- Đối chiếu nhiệm vụ live 2.0.5 → mã mới: **49.440 mẫu, 50 nghề, 40 ngày**, không khác dữ kiện nhiệm vụ cũ.
- Node UI chứng chỉ/quầy đạt; 349/349 file JS đạt cú pháp và tương thích Safari/iOS 15. Có 5 kiểm thử bản dịch, toàn bộ 299 chuỗi nội dung khóa và các mẫu động đã kiểm tra.
- Browser thật ở **390×844 và 1280×860**: giao biên bản một lần, hạn chế đúng hai trong ba ki-ốt, nút đứng quầy bị chặn, học/thi đủ ba khóa, trừ đúng 8.250 xu, khôi phục ba quầy; kiểm tra danh sách khóa bắt buộc của ba xe đẩy và trở về phần nâng cấp quầy thứ ba. Không có lỗi pageerror hoặc tràn ngang trong luồng này.
- Rà soát riêng theo đặc tả và chất lượng đã qua. Đã sửa phí thi lại, khóa không cần thiết trong biên bản, vị trí quay lại, nút quầy bị hạn chế và trường hợp đổi quầy ưu tiên làm mất quyền phục vụ đơn vừa nhận.
- Gói ZIP giải nén mới kiểm đúng toàn bộ hash, khởi động server với PostgreSQL riêng, chạy HTTP tạo nhân vật/mở ngày, kiểm request lặp và xuất bản lưu thành công.

Các kiểm thử historical-server không được coi là đã qua: validator 1.4.31/1.5.2 đã không hiểu dữ liệu nghề/giá hiện tại; validator 1.9.34/35 không hiểu chứng chỉ mới. Một kiểm tra profit bonus kỳ cũ có chênh lệch baseline 36 so với 0. Không sửa/xóa các kiểm tra đó để che kết quả. Đường quay lui được hỗ trợ là mã mới với cờ OFF, đã kiểm JSON/migrate/validate giữ đủ ba chứng chỉ và không bán bù.

## Kiểm chứng sau triển khai

- Canonical game và `mnl-live` active, cwd đều trỏ đúng release mới; bridge đã dừng. Hai cờ OFF không được đặt, cơ chế đang bật.
- 12 mẫu health công khai, 0 lỗi, đều trả 2.0.6. Lấy mẫu không chứng minh mọi request trong rolling đều thành công.
- 1.550 file còn trên máy chủ khớp manifest; 684 file test/artifact được installer chủ động bỏ. Không có file runtime sai hash.
- Nội dung API công khai trả đủ ba khóa, đúng phí, chỉ cho mode class và đúng khóa tiên quyết. Sáu asset công khai (UI chứng chỉ/quầy/thông báo/CSS/bản dịch) khớp ZIP.
- Log sau triển khai được kiểm tối đa 1.000 dòng mỗi dịch vụ: thực tế 23 dòng game và 7 dòng live tại thời điểm kiểm; không có Traceback, CRITICAL hoặc ModuleNotFoundError.
- Root MANIFEST trong repository tải từ release mới. Bản ghi này và cập nhật LIVE_BASE là bằng chứng sau triển khai, không phải source ref của gói đã chạy.

## Quay lui tương thích

Đã đặt script `/root/mnl-business-licenses-disable.sh`, kiểm cú pháp, **chưa chạy**. Script giữ mã 2.0.6, đặt hai cờ OFF và rolling lại để bảo toàn chứng chỉ/hồ sơ. Không dùng lệnh rollback về 2.0.5 mà rolling tool in mặc định. Không khôi phục DB cũ để quay lui mã.
