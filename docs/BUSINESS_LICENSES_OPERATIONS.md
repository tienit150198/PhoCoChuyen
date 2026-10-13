# Vận hành chứng chỉ kinh doanh — 2.1.0

## Phạm vi

Ba khóa bắt buộc học trả phí theo thứ tự. Giá cơ sở 500 / 2.000 / 5.000; với chỉ số giá 1,1 là 550 / 2.200 / 5.500 xu. Thi lại nửa học phí hiện hành. Không thưởng tiền hoặc nhân doanh thu khi đỗ.

Một xe đẩy không cần giấy; nhiều xe đẩy hoặc sạp cần cơ bản; một đến hai ki-ốt cần nâng cao; từ ba ki-ốt cần quản lý chuỗi. Kiểm tra đếm mọi quầy sở hữu, kể cả tự đóng. Từ ba quầy thiếu giấy, biên bản được giao một lần khi chủ vào phiên chơi, có 72 giờ thực để bổ sung. Không truy thu, không tự thu học phí, không phạt lần đầu.

Sau hạn chỉ chặn phần vượt quyền. Chủ cũ giữ một quầy sinh kế khi chưa đủ quyền nào. Chủ được chọn thứ tự quầy ưu tiên. Quầy bị hạn chế ngừng chi phí tự động; đơn đã nhận tính giá vốn, thuế và công trực tiếp. Giữ đơn của chủ, đơn online, đơn khách người chơi và nghĩa vụ ca thuê đã ký quỹ trước hạn. Không cho đăng ca thuê mới sau hạn. Đỗ chứng chỉ gỡ phần hạn chế tương ứng, không mở lại quầy chủ tự đóng.

## Lưu trữ và tắt tính năng

Không thay đổi bảng DB. Hồ sơ tùy chọn `journey.quay.business_license` giữ danh sách quầy cũ, thứ tự ưu tiên và mốc biên bản; các mốc lưu bằng mili giây, API công khai trả giây. Bản lưu trước tính năng được nâng cấp khi truy cập, không sửa hàng loạt DB.

- `MNL_BUSINESS_LICENSES_OFF=1`: bỏ điều kiện chứng chỉ khi mở/nâng cấp.
- `MNL_BUSINESS_INSPECTIONS_OFF=1`: ngừng giao biên bản mới và ngừng cưỡng chế. Quầy được phục hồi khi quyết toán tiếp theo, không bán bù thời gian bị hạn chế; trạng thái tự đóng được giữ nguyên.

**Tắt tính năng dùng mã hiện tại 2.1.0 cùng hai cờ OFF. Không quay về 2.0.7 hoặc cũ hơn:** bản cũ không biết bốn nghề mới, bậc thăng tiến mở rộng hoặc các mã chứng chỉ tương ứng. Không xóa chứng chỉ/hồ sơ/đơn hàng để ép bản lưu tương thích mã cũ.

Chuẩn bị cờ bằng EnvironmentFile cuối cùng của unit, rồi dùng rolling release trên chính thư mục mã tương thích đang chạy để bridge và canonical đều nhận cấu hình mới:

```bash
printf '%s\n' 'MNL_BUSINESS_LICENSES_OFF=1' 'MNL_BUSINESS_INSPECTIONS_OFF=1' > /etc/mnl-business-licenses-rollback.env
mkdir -p /etc/systemd/system/mot-ngay-lam-nghe.service.d
printf '%s\n' '[Service]' 'EnvironmentFile=/etc/mnl-business-licenses-rollback.env' > /etc/systemd/system/mot-ngay-lam-nghe.service.d/99-business-licenses-rollback.conf
systemctl daemon-reload
release_path=$(readlink -f /opt/mot-ngay-lam-nghe/current)
tmux new-session -d -s business-licenses-disable "/usr/local/sbin/mnl-rolling-release --to '$release_path' >> /root/business-licenses-disable.log 2>&1"
```

Lệnh `--to` nhận đường dẫn release thực đã đọc từ current. Hai cờ chỉ tắt cơ chế, không gia hạn biên bản. Trước khi bật lại, xem các hạn đã tồn tại và thông báo thời điểm bật; hạn cũ không tự đặt lại.

## Nghiệm thu

Chạy DB thử với `TEST_DATABASE_URL`, tuyệt đối không đặt DB production cho test. Bộ kiểm thử bao gồm mốc trước/đúng/sau hạn, chủ 12 ki-ốt, đọc thuần không giao biên bản, giao trong phiên chủ, định giá thi lại, ưu tiên quầy không bỏ đơn đã nhận, khách người chơi và ký quỹ, tắt cờ/validate bản lưu, không bán bù.

`scripts/browser_business_licenses.py` dùng tài khoản tổng hợp trong namespace PostgreSQL riêng, kiểm tra 390×844 và 1280×860: biên bản, quá hạn, khóa trả phí tuần tự, 8.250 xu tổng phí, khôi phục quyền, nút chặn và trở lại phần nâng cấp quầy thứ ba. Ảnh và báo cáo ở `output/playwright/business-licenses/`.

Không thêm popup Có gì mới toàn hệ thống; chủ bị kiểm tra thấy biên bản riêng. Nội dung chuyên ngành, công cụ quản lý chuỗi mới và thay đổi lợi nhuận sạp nằm ngoài đợt này.
