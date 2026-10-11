# Phát hành phạt/trộm nhẹ 2.0.3 — 11/10/2026

Đã triển khai âm thầm tại https://phocochuyen.io.vn. Thời gian trong log là UTC+7.

## Bản chạy

- Release: `/opt/mot-ngay-lam-nghe/releases/2.0.3-20261011132357`. Health `2.0.3`, build `2.0.3+032cb631e2e5`.
- Source cuối `e53d4587093b998fdc415675664a98cf3d992ef1`: thay đổi phạt/trộm `45c94be5` và bản Chợ đen `cb0b4a47` đã tích hợp. Không ghi đè module hội chợ bằng bản cũ.
- ZIP `mnl-2.0.3-gentle-losses.zip`: 103,339,276 byte; SHA-256 `2b252a235900e62f72fb663c4affd9b86da6ce3c9f7299fd9ded248481bf7d7a`. Mã băm file tải lên được kiểm trước rolling.
- Dựng từ ZIP live 2.0.2 đã xác minh, base source `22be33b0ed6ceec017022f720880ba8fb986b9ba`: 1.736 file giống nguyên byte, 469 asset tái tạo đúng từ source. So với 2.0.2.1 đang chạy, chỉ 89 file được duyệt khác nhau; không xóa file.
- Lần thử đầu dừng ngay tại guard vì live đã chuyển từ 2.0.2 sang 2.0.2.1 trong lúc tải ZIP. Không thay dịch vụ trong lần bị chặn. Sau đó fast-forward main, giữ hotfix mới, chạy lại 17 kiểm thử kết hợp và dựng lại ZIP.
- Guard lần cuối kiểm symlink và manifest 2.0.2.1 (`f72b30a651cecb5dd5aaf353a9838b9910852346b8364ee2b8000985f1ac7867`) trước chuyển bản. Root MANIFEST được tải từ release mới sau xác minh.

## Hành vi

- Phạt bắt buộc tối đa 2% số dư nguồn bị tác động và 2.000 xu; trộm/hack/lừa đảo/bảo kê tối đa 1% và 1.000 xu. Giữ 100 xu hoặc toàn bộ nếu có ít hơn; không thanh lý tiết kiệm/đầu tư hoặc truy đòi nguồn tiền khác.
- Áp dụng ở bước thực thu, kể cả cảnh báo cũ; các khoản bắt buộc trong cùng sự cố chia sẻ trần. Biên nhận và sổ thu chi ghi số thực trả.
- Ván hội chợ bị công an dừng hủy cược chưa chơi; tiền phóng dao đã đặt được hoàn đúng một lần. Thua cược bình thường không thuộc thay đổi.
- Không tiếp tục truy thu nợ phạt giao thông quầy cũ từ doanh thu sau. Giữ khoản đã trả, miễn phần chưa trả và đối chiếu chi phí/thuế một lần.
- Tắt `mnl-mishap-sweep.timer`, xác minh disabled/inactive. Trước thay đổi có 79 hiệu ứng đã áp dụng, 180 đã hủy, không pending. Không tự hoàn tiền hoặc sửa lịch sử người chơi.

## Kiểm chứng

- Lượt kiểm thử lõi 84, đời thường 34, nghề liên quan 292, lượt cuối 93 đều đạt; các bộ có phần trùng nhau. Hội chợ 89 focused có PostgreSQL và 124 functional đạt (mỗi bộ một skip fixture cũ, có kiểm thử thay thế ngân hàng giàu). UI hội chợ 32, hai script biên nhận và UI quầy 4 đạt. Chi tiết [QA](qa/gentle-losses-2026-10-11.md).
- Rà soát độc lập sửa và kiểm lại tương thích biên nhận giao thông/chủ quầy bằng validator 2.0.2 nguyên trạng; cả lượt bản cũ giao hàng rồi quay về bản mới. Lịch sử sự cố hiển thị số thực trả. Không còn phát hiện critical/important trong diff rà soát.
- Gate nhiệm vụ: 49.440 mẫu của 50 nghề, 40 ngày đều khớp baseline. Một bài rollback tới 1.4.31 đã hỏng trên chính baseline 2.0.2 do bảng giá cũ; không tính là đã qua.
- 30 mẫu health trong rolling, 0 mẫu lỗi. Lấy mẫu không chứng minh mọi request không lỗi. HTTP/live active, cwd đúng release; live health đạt.
- 1537 file runtime khớp manifest; installer chủ động bỏ thư mục tests. Các JS phục vụ công khai khớp ZIP. Không thấy Traceback/CRITICAL/ModuleNotFoundError trong tối đa 500 dòng log mỗi dịch vụ kể từ khởi động mới.
- Rolling vẫn ghi cảnh báo fork từ tiến trình đa luồng và một số thao tác chậm trên bản lưu lớn; không coi các vấn đề hiệu năng đó là đã được sửa trong đợt này.
- Kiểm helper giới hạn ở số dư 0/1/99/100/101/999/1.000/100k/10M trên runtime. Xác minh giữ hotfix Chợ đen, mốc Hai ngày vàng 1791689983–1791862783, top kéo co 30 trận và giải top5. Không đổi Có gì mới hoặc kích hoạt lại sự kiện.
- Giữ backup trước hotfix 2.0.1: `/var/backups/mot-ngay-lam-nghe-pg/hotfix-2.0.1-20261011/phocochuyen.dump`, 3.327.536.576 byte; đọc `pg_restore --list` thành công. Chưa diễn tập restore. Không đổi schema. Cluster PostgreSQL kiểm thử cục bộ đã dừng.

## Giới hạn và quay lui

Đã cập nhật phản hồi góp ý 332 sau khi xác minh bản chạy, bằng điều kiện updated_at để tránh ghi đè thay đổi khác. Giữ câu trả lời đối chiếu cũ, bổ sung chính sách mới và tiếp tục để seen vì khoản mất lịch sử cụ thể chưa xác định. Không hứa đã hoàn xu hoặc kết luận toàn bộ khoản mất cũ là lỗi.

Cược phóng dao cũ ở màn từ 2 trở lên có thể thiếu ngày gốc. Ví, tổng lỗ và bảng tuần hoàn đúng; daily net/cap giữ phần debit cũ theo hướng thận trọng. Lịch sử cũ chỉ có tổng hỗn hợp không bị suy đoán lại thành từng khoản.

Giữ các release với KEEP=999. Quay lui nguyên bản 2.0.2.1 sẽ mất chính sách phạt nhẹ; nếu cần rollback, giữ các validator tương thích và các hotfix đang chạy. Không khôi phục DB cũ để quay lui mã. Log và dữ liệu vận hành riêng ở output/, không commit thông tin xác thực hoặc bản lưu người chơi.
